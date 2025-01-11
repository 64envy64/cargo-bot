# bot/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config

class Keyboards:
    @staticmethod
    def main_menu(is_subscribed: bool = False) -> InlineKeyboardMarkup:
        """Главное меню бота"""
        keyboard = [
            [
                InlineKeyboardButton("📦 Отследить заказ", callback_data='track'),
                InlineKeyboardButton("🚚 Доставка", callback_data='delivery')
            ],
            [
                InlineKeyboardButton("✅ Проверить адрес", callback_data='check_address'),
                InlineKeyboardButton("↩️ Возврат", callback_data='refund')
            ],
            [
                InlineKeyboardButton("❓ Частые вопросы", callback_data='faq'),
                InlineKeyboardButton("👨‍💻 Оператор", url=config.WHATSAPP_REDIRECT)
            ]
        ]
        
        # Добавляем кнопку подписки/отписки
        if is_subscribed:
            keyboard.append([
                InlineKeyboardButton("🔔 Отписаться от рассылки", callback_data='unsubscribe')
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("🔔 Подписаться на рассылку", callback_data='subscribe')
            ])
            
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def operator_redirect() -> InlineKeyboardMarkup:
        """Кнопка для связи с оператором"""
        keyboard = [[
            InlineKeyboardButton("👨‍💻 Связаться с оператором", url=config.WHATSAPP_REDIRECT)
        ]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def address_check_menu() -> InlineKeyboardMarkup:
        """Меню проверки адреса"""
        keyboard = [
            [InlineKeyboardButton("✅ Проверить другой адрес", callback_data='check_address')],
            [InlineKeyboardButton("👨‍💻 Нужна помощь", url=config.WHATSAPP_REDIRECT)],
            [InlineKeyboardButton("« Назад", callback_data='main_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)