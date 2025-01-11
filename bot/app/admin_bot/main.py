# app/admin_bot/main.py
import os
import logging
import asyncio
import requests
from datetime import datetime
import nest_asyncio
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from app.database.operations import DatabaseManager
from app.ai.chat import ChatManager
from app.config import AUTHORIZED_OPERATORS, ADMIN_BOT_TOKEN, DATABASE_URL, TELEGRAM_TOKEN

# Состояния для ConversationHandler
AWAITING_REPLY = 1
CONFIRM_REPLY = 2
AWAITING_BROADCAST = 3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nest_asyncio.apply()

SECRET_KEY = os.getenv("SECRET_KEY", "MYSECRET")
MAIN_BOT_URL = os.getenv("MAIN_BOT_URL", "http://silkway-bot:8000")

db_manager = DatabaseManager(DATABASE_URL)

class AdminHandlers:
    def __init__(self):
        self.db_manager = DatabaseManager(DATABASE_URL)
        self.chat_manager = ChatManager(self.db_manager)

    def get_admin_keyboard(self):
        """Основная клавиатура админа"""
        return ReplyKeyboardMarkup([
            ['📥 Новые заявки'],
            ['✅ Отвеченные', '🔄 В процессе', '❌ Неотвеченные'],
            ['📢 Управление рассылкой']
        ], resize_keyboard=True)

    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in AUTHORIZED_OPERATORS:
            await update.message.reply_text("У вас нет доступа к этому боту.")
            return
            
        await update.message.reply_text(
            "👋 Добро пожаловать в панель администратора!\n\n"
            "Используйте кнопки меню для навигации:",
            reply_markup=self.get_admin_keyboard()
        )

    async def show_requests(self, update: Update, context: ContextTypes.DEFAULT_TYPE, status='pending'):
        """Показывает список заявок с определенным статусом"""
        user_id = update.effective_user.id
        if user_id not in AUTHORIZED_OPERATORS:
            return

        if status == 'pending':
            sessions = self.db_manager.get_pending_sessions()
            status_text = "новых"
        elif status == 'answered':
            sessions = self.db_manager.get_answered_sessions()
            status_text = "отвеченных"
        elif status == 'in_progress':
            sessions = self.db_manager.get_in_progress_sessions()
            status_text = "в процессе"
        else:
            sessions = self.db_manager.get_unanswered_sessions()
            status_text = "неотвеченных"

        if not sessions:
            await update.message.reply_text(f"Нет заявок {status_text}.")
            return

        for session in sessions:
            try:
                user = await context.bot.get_chat(session.user_id)
                username = user.username or "Без username"
                
                msg = (
                    f"📝 Обращение №{session.id}\n"
                    f"От: <a href='tg://user?id={session.user_id}'>{username}</a>\n"
                    f"ID: <code>{session.user_id}</code>\n"
                    f"⏰ Создано: {session.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"Сообщение:\n{getattr(session, 'last_message', 'Нет сообщения')}\n"
                )

                keyboard = [
                    [InlineKeyboardButton("✍️ Ответить", callback_data=f"reply_{session.user_id}")],
                    [InlineKeyboardButton("❌ Закрыть", callback_data=f"close_{session.user_id}")]
                ]

                await update.message.reply_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error showing request for user {session.user_id}: {e}")
                continue

    async def handle_broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды управления рассылкой"""
        keyboard = [
            [
                InlineKeyboardButton("📝 Создать рассылку", callback_data='create_broadcast'),
                InlineKeyboardButton("📊 Статистика", callback_data='broadcast_stats')
            ]
        ]
        await update.message.reply_text(
            "📢 Управление рассылкой\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback-запросов для рассылки"""
        query = update.callback_query
        await query.answer()

        if query.data == 'create_broadcast':
            await query.message.edit_text(
                "📝 Введите текст для рассылки:\n"
                "Поддерживается Markdown разметка.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Отмена", callback_data='cancel_broadcast')
                ]])
            )
            return AWAITING_BROADCAST
            
        elif query.data == 'broadcast_stats':
            subscribers = self.db_manager.get_subscribers_count()
            active = self.db_manager.get_active_subscribers_count()
            
            await query.message.edit_text(
                f"📊 Статистика подписчиков\n\n"
                f"Всего подписчиков: {subscribers}\n"
                f"Активных подписчиков: {active}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data='back_to_broadcast')
                ]])
            )

    async def send_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка рассылки"""
        message = update.message.text
        subscribers = self.db_manager.get_active_subscribers()
        
        logger.info(f"Starting broadcast to {len(subscribers)} subscribers")
        
        success = 0
        failed = 0
        
        # Создаем клиент для основного бота
        main_bot = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
        
        for subscriber in subscribers:
            try:
                logger.info(f"Attempting to send broadcast to user {subscriber.user_id}")
                # Отправляем через основной бот
                await main_bot.bot.send_message(
                    chat_id=subscriber.user_id,
                    text=message,
                    parse_mode='Markdown'
                )
                logger.info(f"Successfully sent broadcast to user {subscriber.user_id}")
                success += 1
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to send broadcast to {subscriber.user_id}: {e}")
                failed += 1
        
        # Закрываем клиент основного бота
        await main_bot.shutdown()
        
        status_text = (
            f"📢 Рассылка завершена\n\n"
            f"✅ Успешно отправлено: {success}\n"
            f"❌ Ошибок: {failed}\n"
            f"📊 Всего подписчиков: {len(subscribers)}"
        )
        
        logger.info(status_text)
        await update.message.reply_text(status_text)
        return ConversationHandler.END

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых команд с клавиатуры"""
        text = update.message.text
        
        if text == "📥 Новые заявки":
            await self.show_requests(update, context, 'pending')
        elif text == "✅ Отвеченные":
            await self.show_requests(update, context, 'answered')
        elif text == "🔄 В процессе":
            await self.show_requests(update, context, 'in_progress')
        elif text == "❌ Неотвеченные":
            await self.show_requests(update, context, 'pending')
        elif text == "📢 Управление рассылкой":
            await self.handle_broadcast_command(update, context)

    async def check_new_requests(self, context: ContextTypes.DEFAULT_TYPE):
        """Периодическая проверка новых запросов"""
        try:
            # Проверяем новые заявки
            pending_sessions = self.db_manager.get_pending_sessions()
            if pending_sessions:
                for admin_id in AUTHORIZED_OPERATORS:
                    try:
                        for session in pending_sessions:
                            user = await context.bot.get_chat(session.user_id)
                            username = user.username or "Без username"
                            
                            msg = (
                                f"📝 Новое обращение!\n"
                                f"От: <a href='tg://user?id={session.user_id}'>{username}</a>\n"
                                f"ID: <code>{session.user_id}</code>\n"
                                f"Сообщение: {getattr(session, 'last_message', 'Нет сообщения')}\n"
                            )
                            
                            keyboard = [[InlineKeyboardButton("✍️ Ответить", callback_data=f"reply_{session.user_id}")]]
                            
                            await context.bot.send_message(
                                chat_id=admin_id,
                                text=msg,
                                reply_markup=InlineKeyboardMarkup(keyboard),
                                parse_mode='HTML'
                            )
                    except Exception as e:
                        logger.warning(f"Не удалось отправить уведомление о новой заявке оператору {admin_id}: {e}")

            # Проверяем обращения в процессе с новыми сообщениями
            in_progress_sessions = self.db_manager.get_in_progress_sessions()
            if in_progress_sessions:
                for admin_id in AUTHORIZED_OPERATORS:
                    try:
                        for session in in_progress_sessions:
                            if session.last_activity and (datetime.utcnow() - session.last_activity).seconds < 30:
                                user = await context.bot.get_chat(session.user_id)
                                username = user.username or "Без username"
                                
                                msg = (
                                    f"🔄 Новое сообщение в обращении «В процессе»!\n"
                                    f"От: <a href='tg://user?id={session.user_id}'>{username}</a>\n"
                                    f"ID: <code>{session.user_id}</code>\n"
                                    f"Сообщение: {getattr(session, 'last_message', 'Нет сообщения')}\n"
                                )
                                
                                keyboard = [[InlineKeyboardButton("✍️ Ответить", callback_data=f"reply_{session.user_id}")]]
                                
                                await context.bot.send_message(
                                    chat_id=admin_id,
                                    text=msg,
                                    reply_markup=InlineKeyboardMarkup(keyboard),
                                    parse_mode='HTML'
                                )
                    except Exception as e:
                        logger.warning(f"Не удалось отправить уведомление о сообщении в процессе оператору {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Error checking requests: {e}")

    async def handle_close_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатия кнопки 'Закрыть'"""
        query = update.callback_query
        await query.answer()
        
        user_id = int(query.data.split('_')[1])
        
        try:
            self.db_manager.close_session(user_id)
            await query.message.edit_text(
                f"✅ Обращение пользователя {user_id} закрыто",
                reply_markup=None
            )
        except Exception as e:
            logger.error(f"Error closing session: {e}")
            await query.message.reply_text("❌ Ошибка при закрытии обращения")

    async def check_main_bot_availability(self):
        """Проверка доступности основного бота"""
        try:
            r = requests.get(f"{MAIN_BOT_URL}/health", timeout=5)
            return r.status_code == 200
        except:
            return False

    async def check_inactive_sessions(self, context: ContextTypes.DEFAULT_TYPE):
        """Проверка неактивных сессий"""
        try:
            inactive_sessions = self.db_manager.get_inactive_sessions()
            for session in inactive_sessions:
                try:
                    # Отправляем сообщение пользователю
                    await context.bot.send_message(
                        chat_id=session.user_id,
                        text=(
                            "👋 Здравствуйте! Мы заметили, что в вашем обращении не было активности "
                            "более 12 часов. Если ваш вопрос решен, обращение будет закрыто. "
                            "Если у вас появятся новые вопросы, пожалуйста, создайте новое обращение."
                        )
                    )
                    # Закрываем сессию
                    self.db_manager.set_session_answered(session.user_id)
                except Exception as e:
                    logger.error(f"Error handling inactive session {session.user_id}: {e}")
        except Exception as e:
            logger.error(f"Error checking inactive sessions: {e}")

def main():
    app = ApplicationBuilder().token(ADMIN_BOT_TOKEN).build()
    handlers = AdminHandlers()

    # Создаем ConversationHandler для рассылки
    broadcast_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^📢 Управление рассылкой$'), handlers.handle_broadcast_command),
            CallbackQueryHandler(handlers.handle_broadcast_callback, pattern='^create_broadcast$')
        ],
        states={
            AWAITING_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.send_broadcast)]
        },
        fallbacks=[
            CallbackQueryHandler(handlers.handle_broadcast_command, pattern='^cancel_broadcast$'),
            CommandHandler('cancel', handlers.handle_broadcast_command)
        ]
    )

    # Добавляем обработчики
    app.add_handler(CommandHandler("start", handlers.start_cmd))
    app.add_handler(broadcast_conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text))
    
    if app.job_queue:
        app.job_queue.run_repeating(handlers.check_new_requests, interval=30)
        app.job_queue.run_repeating(handlers.check_inactive_sessions, interval=3600)
    else:
        logger.warning("JobQueue не доступен. Периодические проверки отключены.")
    
    app.run_polling()

if __name__ == "__main__":
    main()
