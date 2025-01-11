from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, filters, CommandHandler, MessageHandler, CallbackQueryHandler
from app.knowledge_base.faq import FAQ
from app.database.operations import DatabaseManager
from app.bot.keyboards import Keyboards
from app.bot.middlewares import log_handler, rate_limit
from app.ai.ocr import AddressChecker
import logging
from pathlib import Path
from app.ai.chat import ChatManager
import config

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self, chat_manager: ChatManager, db_manager: DatabaseManager):
        """Инициализация компонентов бота"""
        self.chat_manager = chat_manager
        self.db_manager = db_manager
        self.faq = FAQ()
        self.keyboards = Keyboards()
        self.address_checker = AddressChecker()
        self.code_context = {}  # Для хранения контекста ввода кода

    @log_handler
    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Хендлер на команду /start. Приветствует пользователя
        и показывает главное меню.
        """
        user = update.effective_user
        is_subscribed = self.db_manager.check_subscription(user.id)
        
        welcome_text = (
            "👋 Здравствуйте! Я помощник Silkway cargo.\n\n"
            "Я могу помочь вам с:\n"
            "• Отслеживанием заказа\n"
            "• Оформлением доставки\n"
            "• Проверкой адреса склада\n"
            "• Вопросами по возврату\n\n"
            "Выберите интересующий вас вопрос или напишите его в чат:"
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=self.keyboards.main_menu(is_subscribed)
        )
        return True

    @log_handler
    async def callback_query_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback запросов от inline кнопок"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'subscribe':
            user = update.effective_user
            # Проверяем, подписан ли уже пользователь
            if self.db_manager.check_subscription(user.id):
                await query.message.edit_text(
                    "✅ Вы уже подписаны на рассылку!\n\n"
                    "Чтобы вернуться в главное меню, нажмите /start",
                    reply_markup=self.keyboards.main_menu(is_subscribed=True)
                )
                return True
                
            # Если не подписан - подписываем
            if self.db_manager.add_subscriber(user.id, user.username):
                await query.message.edit_text(
                    "✅ Вы успешно подписались на рассылку!\n\n"
                    "Теперь вы будете получать важные уведомления:\n"
                    "• О поступлении новых товаров\n"
                    "• Об изменениях в работе складов\n"
                    "• О специальных акциях\n\n"
                    "Чтобы вернуться в главное меню, нажмите /start",
                    reply_markup=self.keyboards.main_menu(is_subscribed=True)
                )
            else:
                await query.message.edit_text(
                    "❌ Произошла ошибка при подписке.\n"
                    "Пожалуйста, попробуйте позже или обратитесь к оператору.",
                    reply_markup=self.keyboards.operator_redirect()
                )
            return True
        
        elif query.data == 'unsubscribe':
            user = update.effective_user
            if self.db_manager.unsubscribe(user.id):
                await query.message.edit_text(
                    "✅ Вы успешно отписались от рассылки.\n\n"
                    "Вы больше не будете получать уведомления.\n"
                    "Чтобы подписаться снова, нажмите /start",
                    reply_markup=self.keyboards.main_menu(is_subscribed=False)
                )
            else:
                await query.message.edit_text(
                    "❌ Произошла ошибка при отписке.\n"
                    "Пожалуйста, попробуйте позже или обратитесь к оператору.",
                    reply_markup=self.keyboards.operator_redirect()
                )
            return True
        
        responses = {
            'track': (
                "📦 Чтобы отследить заказ:\n\n"
                "1. Откройте мобильное приложение\n"
                "2. Перейдите в раздел «Заказы»\n"
                "3. Выберите «Прибыл в пункт выдачи»"
            ),
            'delivery': (
                "🚚 Для оформления доставки до двери:\n\n"
                "1. Перейдите в раздел «Заказы»\n"
                "2. Выберите «Прибыл в пункт выдачи»\n"
                "3. Поставьте галочку «доставка до двери»\n"
                "4. Заполните адрес и оплатите"
            ),
            'check_address': (
                "✅ Для проверки адреса склада мне понадобится:\n\n"
                "1️⃣ Ваш код клиента (6 цифр)\n"
                "2️⃣ Скриншот страницы с адресом\n\n"
                "Сначала отправьте код командой: `/code ваш_код`\n"
                "Например: `/code 929848`\n\n"
                "После этого отправьте скриншот, и я проверю правильность адреса."
            ),
            'refund': (
                "↩️ Варианты возврата:\n\n"
                "1. При браке товара\n"
                "2. При несоответствии описанию\n"
                "3. При неверном размере/цвете\n"
                "4. При недостаче\n\n"
            ),
            'faq': (
                "❓ Частые вопросы:\n\n"
                "1. Как отследить заказ?\n"
                "2. Как заказать доставку?\n"
                "3. График работы склада\n"
                "4. Как сделать возврат?\n\n"
                "Выберите интересующий вас вопрос или напишите его в чат"
            ),
            'start_check': (
                "Отправьте, пожалуйста, ваш код клиента командой `/code ваш_код`\n"
                "Например: `/code 929848`"
            ),
            'main_menu': (
                "Выберите интересующий вас вопрос:"
            )
        }
        
        response = responses.get(query.data)
        if response:
            keyboard = None
            # Добавляем кнопку "Назад" для всех ответов, кроме проверки адреса
            if query.data not in ['check_address', 'main_menu']:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("« Главное меню", callback_data='main_menu')]
                ])
            elif query.data == 'main_menu':
                keyboard = self.keyboards.main_menu()
            elif query.data == 'check_address':
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Да, проверить адрес", callback_data='start_check')
                ]])

            # Включаем поддержку Markdown для кода
            await query.edit_message_text(
                text=response,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            # Если нет готового ответа, пробуем получить из FAQ
            faq_response = self.faq.get_response(query.data)
            if faq_response:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("« Главное меню", callback_data='main_menu')]
                ])
                await query.edit_message_text(
                    text=faq_response,
                    reply_markup=keyboard
                )
            else:
                await query.edit_message_text(
                    "Извините, данный раздел временно недоступен.\n"
                    "Пожалуйста, свяжитесь с оператором для получения информации.",
                    reply_markup=self.keyboards.operator_redirect()
                )

        # Сохраняем взаимодействие
        self.db_manager.save_interaction(
            user_id=update.effective_user.id,
            message=f"[CALLBACK] {query.data}",
            response=response or faq_response or "Раздел недоступен",
            message_type="callback",
            success=bool(response or faq_response)
        )

    @log_handler
    async def code_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Хендлер для команды /code и контекстного ввода кода
        """
        user_id = update.effective_user.id
        message = update.message.text

        # Проверяем, является ли сообщение командой /code
        if message.startswith('/code'):
            try:
                code = context.args[0] if context.args else None
            except IndexError:
                code = None
        else:
            # Если это не команда, проверяем контекст и само сообщение
            code = message.strip() if message.strip().isdigit() else None
            if not self.code_context.get(user_id):
                # Если нет контекста ввода кода, игнорируем
                return False

        if not code:
            await update.message.reply_text(
                "❌ Пожалуйста, укажите код после команды.\n"
                "Пример: `/code 929848`",
                parse_mode='Markdown'
            )
            # Устанавливаем контекст ожидания кода
            self.code_context[user_id] = True
            return True

        if not code.isdigit() or len(code) != 6:
            await update.message.reply_text(
                "❌ Код должен состоять из 6 цифр.\n"
                "Пример: `/code 929848`",
                parse_mode='Markdown'
            )
            return True

        # Сохраняем код
        context.user_data['client_code'] = code
        # Очищаем контекст ожидания кода
        self.code_context.pop(user_id, None)
        
        await update.message.reply_text(
            f"✅ Отлично! Ваш код {code} сохранен.\n\n"
            "Теперь отправьте скриншот страницы с адресом, и я проверю его правильность.\n"
            "Убедитесь, что на скриншоте видны все детали адреса."
        )
        return True

    @log_handler
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Обработчик для фотографий (проверка адреса)"""
        client_code = context.user_data.get('client_code')
        
        if not client_code:
            instructions = (
                "❌ Для проверки адреса мне нужно знать ваш код клиента.\n\n"
                "Пожалуйста, сначала отправьте код командой:\n"
                "`/code ваш_код`\n"
                "Например: `/code 929848`\n\n"
                "После этого отправьте скриншот еще раз."
            )
            await update.message.reply_text(
                instructions,
                parse_mode='Markdown'
            )
            # Устанавливаем контекст ожидания кода
            self.code_context[update.effective_user.id] = True
            return True
        
        await update.message.reply_text("🔍 Проверяю адрес, пожалуйста, подождите...")
        
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        photo_path = temp_dir / f"{photo.file_id}.jpg"
        
        try:
            await photo_file.download_to_drive(photo_path)
            is_valid, message = await self.address_checker.check_image(str(photo_path), client_code)
            
            if is_valid:
                await update.message.reply_text(
                    message,
                    reply_markup=self.keyboards.address_check_menu()
                )
            else:
                await update.message.reply_text(
                    message,
                    reply_markup=self.keyboards.operator_redirect()
                )

            # Логируем взаимодействие
            self.db_manager.save_interaction(
                user_id=update.effective_user.id,
                message="[PHOTO]",
                response=message,
                message_type="photo",
                success=is_valid
            )
        
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await update.message.reply_text(
                "❌ Извините, произошла ошибка при проверке адреса. "
                "Пожалуйста, убедитесь, что скриншот четкий и содержит всю информацию, "
                "или обратитесь к оператору за помощью.",
                reply_markup=self.keyboards.operator_redirect()
            )
        finally:
            if photo_path.exists():
                photo_path.unlink()

        return True

    @log_handler
    @rate_limit(5, 60) 
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Основной обработчик текстовых сообщений
        """
        user_id = update.effective_user.id
        message = update.message.text

        # Если активен контекст ввода кода и сообщение похоже на код
        if self.code_context.get(user_id) and message.strip().isdigit():
            return await self.code_handler(update, context)
        
        # Обновляем время последней активности
        self.db_manager.update_last_activity(user_id)
        
        try:
            # Обрабатываем сообщение через чат-менеджер
            response, needs_operator = self.chat_manager.process_message(user_id, message)
            
            if needs_operator:
                try:
                    # Создаем сессию с оператором
                    self.db_manager.create_operator_session(user_id, message)
                    
                    # Отправляем сообщение пользователю
                    await update.message.reply_text(
                        "🔄 Перевожу ваш запрос на оператора...\n"
                        "Пожалуйста, подождите. Оператор скоро подключится к диалогу.",
                        reply_markup=self.keyboards.operator_redirect()
                    )
                    
                    # Сохраняем взаимодействие
                    self.db_manager.save_interaction(
                        user_id=user_id,
                        message=message,
                        response="[REDIRECTED TO OPERATOR]",
                        message_type="operator_redirect",
                        success=True
                    )
                except Exception as e:
                    logger.error(f"Error handling operator redirect: {e}")
                    await update.message.reply_text(
                        "❌ Извините, произошла ошибка при перенаправлении запроса. "
                        "Пожалуйста, попробуйте позже."
                    )
            else:
                # Проверяем, запрашивает ли пользователь меню
                reply_markup = (
                    self.keyboards.main_menu() 
                    if "помощь" in message.lower() or "меню" in message.lower()
                    else None
                )
                
                await update.message.reply_text(
                    response,
                    reply_markup=reply_markup
                )
                
                # Сохраняем успешное взаимодействие
                self.db_manager.save_interaction(
                    user_id=user_id,
                    message=message,
                    response=response,
                    message_type="ai",
                    success=True
                )
                
        except Exception as e:
            logger.error(f"Error in message_handler: {e}")
            await update.message.reply_text(
                "❌ Извините, произошла ошибка. Пожалуйста, попробуйте позже или обратитесь к оператору.",
                reply_markup=self.keyboards.operator_redirect()
            )
            
        return True

    def register_handlers(self, application):
        """
        Регистрация всех обработчиков бота
        """
        # Базовые команды
        application.add_handler(CommandHandler("start", self.start_handler))
        application.add_handler(CommandHandler("code", self.code_handler)) 
        
        # Обработка фотографий
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # Обработка callback-запросов (кнопки)
        application.add_handler(CallbackQueryHandler(self.callback_query_handler))
        
        # Обработка текстовых сообщений (должен быть последним)
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.message_handler
        ))

    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user = update.effective_user
        is_subscribed = self.db_manager.check_subscription(user.id)
        
        await update.message.reply_text(
            "👋 Добро пожаловать в бот!\n\n"
            "Выберите интересующий вас вопрос:",
            reply_markup=self.keyboards.main_menu(is_subscribed)
        )