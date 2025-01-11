# bot/middlewares.py
import logging
from functools import wraps
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database.operations import save_interaction

logger = logging.getLogger(__name__)


def log_handler(func):
    """
    Декоратор для логирования всех обращений к боту.
    Оборачивает методы класса BotHandlers.
    """
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        start_time = datetime.now()

        # Получаем текст сообщения/команды для логирования
        msg_text = None
        if update.message:
            msg_text = update.message.text
        elif update.callback_query:
            msg_text = update.callback_query.data

        logger.info(
            f"Request from user {user.id if user else '?'} "
            f"({user.username if user else '?'}): {msg_text}"
        )

        try:
            # Вызываем оригинальный обработчик
            response = await func(self, update, context)

            # Логируем успешное взаимодействие
            if update.message and not update.message.photo:
                save_interaction(
                    user_id=user.id,
                    message=msg_text,
                    response=str(response) if response else None,
                    message_type="text",
                    success=True
                )
            elif update.callback_query:
                save_interaction(
                    user_id=user.id,
                    message=msg_text,
                    response=str(response) if response else None,
                    message_type="callback",
                    success=True
                )
            elif update.message and update.message.photo:
                save_interaction(
                    user_id=user.id,
                    message="[PHOTO]",
                    response=str(response) if response else None,
                    message_type="photo",
                    success=True
                )

            return response

        except Exception as e:
            # Логируем ошибку
            logger.error(f"Error in {func.__name__}: {str(e)}")
            
            save_interaction(
                user_id=user.id,
                message=msg_text or "[ERROR]",
                response=str(e),
                message_type="error",
                success=False
            )

            # Отправляем пользователю сообщение об ошибке
            error_message = (
                "Извините, произошла ошибка при обработке вашего запроса. "
                "Пожалуйста, попробуйте позже или обратитесь к оператору."
            )
            try:
                if update.message:
                    await update.message.reply_text(error_message)
                elif update.callback_query:
                    await update.callback_query.answer(error_message)
            except Exception as send_err:
                logger.error(f"Error sending error message: {send_err}")

            return False

        finally:
            # Всегда логируем время обработки
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Request processed in {processing_time:.2f} seconds")

    return wrapper


def rate_limit(limit: int = 1, period: int = 60):
    """
    Декоратор для ограничения частоты запросов от пользователя.
    Args:
        limit: максимальное количество запросов
        period: период в секундах
    """
    def decorator(func):
        CACHE = {}

        @wraps(func)
        async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            current_time = datetime.now()

            # Очищаем старые запросы
            user_requests = CACHE.get(user_id, [])
            user_requests = [
                req for req in user_requests
                if (current_time - req).total_seconds() <= period
            ]

            if len(user_requests) >= limit:
                msg = "Пожалуйста, подождите немного перед следующим запросом."
                if update.message:
                    await update.message.reply_text(msg)
                elif update.callback_query:
                    await update.callback_query.answer(msg)
                return False

            user_requests.append(current_time)
            CACHE[user_id] = user_requests

            return await func(self, update, context)

        return wrapper
    return decorator