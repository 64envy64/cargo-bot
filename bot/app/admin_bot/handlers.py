import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database.operations import DatabaseManager
from app.config import AUTHORIZED_OPERATORS

logger = logging.getLogger(__name__)

class AdminBotHandlers:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - показывает главное меню"""
        # Проверяем, авторизован ли пользователь
        if update.effective_user.id not in AUTHORIZED_OPERATORS:
            await update.message.reply_text(
                "⛔️ У вас нет доступа к админ-панели."
            )
            return

        keyboard = [
            [
                InlineKeyboardButton("📨 Новые заявки", callback_data='new_requests'),
                InlineKeyboardButton("✅ Отвеченные", callback_data='answered')
            ],
            [
                InlineKeyboardButton("🔄 В процессе", callback_data='in_progress'),
                InlineKeyboardButton("❌ Неотвеченные", callback_data='unanswered')
            ],
            [
                InlineKeyboardButton("📢 Управление рассылкой", callback_data='manage_broadcast')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 Добро пожаловать в панель администратора!\n"
            "Выберите нужный раздел:",
            reply_markup=reply_markup
        )

    async def handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка управления рассылкой"""
        query = update.callback_query
        await query.answer()

        keyboard = [
            [
                InlineKeyboardButton("📝 Создать рассылку", callback_data='create_broadcast'),
                InlineKeyboardButton("📊 Статистика", callback_data='broadcast_stats')
            ],
            [
                InlineKeyboardButton("« Назад", callback_data='back_to_main')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "📢 Управление рассылкой\n\n"
            "• Создать новую рассылку\n"
            "• Посмотреть статистику рассылок\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )

    async def send_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка рассылки всем подписчикам"""
        message = update.message.text
        
        try:
            # Получаем всех активных подписчиков
            subscribers = self.db_manager.get_active_subscribers()
            
            if not subscribers:
                await update.message.reply_text(
                    "❌ Нет активных подписчиков для рассылки.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Назад", callback_data='back_to_broadcast')
                    ]])
                )
                return
            
            success = 0
            failed = 0
            
            # Отправляем сообщение каждому подписчику
            for subscriber in subscribers:
                try:
                    await context.bot.send_message(
                        chat_id=subscriber.user_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    success += 1
                    # Небольшая задержка между отправками
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send broadcast to {subscriber.user_id}: {e}")
                    failed += 1
            
            # Отправляем статистику
            status_text = (
                f"📢 Рассылка завершена\n\n"
                f"✅ Успешно отправлено: {success}\n"
                f"❌ Ошибок доставки: {failed}\n"
                f"📊 Всего подписчиков: {len(subscribers)}"
            )
            
            await update.message.reply_text(
                status_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data='back_to_broadcast')
                ]])
            )
            
            # Логируем результат
            logger.info(f"Broadcast completed. Success: {success}, Failed: {failed}")
            
        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при выполнении рассылки.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data='back_to_broadcast')
                ]])
            )
        finally:
            # Очищаем состояние
            context.user_data.pop('state', None)

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback запросов"""
        query = update.callback_query
        
        if update.effective_user.id not in AUTHORIZED_OPERATORS:
            await query.answer("⛔️ У вас нет доступа к этой функции")
            return
        
        # Обработчики для рассылки
        if query.data == 'manage_broadcast':
            await self.handle_broadcast(update, context)
            return
            
        elif query.data == 'create_broadcast':
            await query.message.edit_text(
                "📝 Создание новой рассылки\n\n"
                "Отправьте текст сообщения для рассылки.\n"
                "Поддерживается Markdown разметка.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Отмена", callback_data='back_to_broadcast')
                ]])
            )
            context.user_data['state'] = 'waiting_broadcast_text'
            return
            
        elif query.data == 'broadcast_stats':
            # Получаем статистику из базы данных
            subscribers = self.db_manager.get_subscribers_count()
            active = self.db_manager.get_active_subscribers_count()
            
            await query.message.edit_text(
                f"📊 Статистика рассылок\n\n"
                f"Всего подписчиков: {subscribers}\n"
                f"Активных подписчиков: {active}\n",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Назад", callback_data='back_to_broadcast')
                ]])
            )
            return
            
        elif query.data == 'back_to_broadcast':
            await self.handle_broadcast(update, context)
            return
            
        elif query.data == 'back_to_main':
            keyboard = [
                [
                    InlineKeyboardButton("📨 Новые заявки", callback_data='new_requests'),
                    InlineKeyboardButton("✅ Отвеченные", callback_data='answered')
                ],
                [
                    InlineKeyboardButton("🔄 В процессе", callback_data='in_progress'),
                    InlineKeyboardButton("❌ Неотвеченные", callback_data='unanswered')
                ],
                [
                    InlineKeyboardButton("📢 Управление рассылкой", callback_data='manage_broadcast')
                ]
            ]
            await query.message.edit_text(
                "Выберите нужный раздел:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        if update.effective_user.id not in AUTHORIZED_OPERATORS:
            return
            
        state = context.user_data.get('state')
        
        if state == 'waiting_broadcast_text':
            await self.send_broadcast(update, context)
            context.user_data.pop('state', None) 