from .model import SilkwayAI
from typing import Dict, List, Optional, Tuple
import logging
from app.database.operations import DatabaseManager
from app.knowledge_base.faq import FAQ

logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self, db_manager: DatabaseManager):
        """Инициализация менеджера чата"""
        self.model = SilkwayAI()
        self.conversations: Dict[int, List[Dict]] = {}
        self.db_manager = db_manager
        self.faq = FAQ()
        
    def add_message(self, user_id: int, message: str, role: str = "user"):
        if user_id not in self.conversations:
            self.conversations[user_id] = []
            
        self.conversations[user_id].append({
            "role": role,
            "content": message
        })
        
        # Ограничиваем историю последними 10 сообщениями
        self.conversations[user_id] = self.conversations[user_id][-10:]

    def get_conversation_context(self, user_id: int) -> str:
        if user_id not in self.conversations:
            return ""
            
        context = "\n".join([
            f"{'Пользователь' if msg['role'] == 'user' else 'Ассистент'}: {msg['content']}"
            for msg in self.conversations[user_id][-3:]  # Берем последние 3 сообщения
        ])
        
        return context

    def get_conversation_history(self, user_id: int, limit: int = 5) -> str:
        if user_id not in self.conversations:
            return "История диалога отсутствует"
            
        history = []
        for msg in self.conversations[user_id][-limit:]:
            role = "👤 Клиент" if msg['role'] == 'user' else "🤖 Бот"
            history.append(f"{role}: {msg['content']}")
            
        return "\n\n".join(history)

    def process_message(self, user_id: int, message: str) -> Tuple[str, bool]:
        try:
            # Добавляем сообщение в историю
            self.add_message(user_id, message)
            
            # Сначала проверяем FAQ
            faq_response = self.faq.get_response(message)
            if faq_response:
                self.add_message(user_id, faq_response, role="assistant")
                return faq_response, False

            # Проверяем, относится ли вопрос к разрешенным темам
            if not self.model.is_allowed_question(message):
                # Возвращаем ответ о переводе на оператора
                return (
                    "🔄 Подождите, пожалуйста. Я перевожу ваш запрос на оператора...\n\n"
                    "Оператор ответит вам в ближайшее время.",
                    True
                )

            # Получаем контекст и генерируем ответ
            context = self.get_conversation_context(user_id)
            response = self.model.generate_response(f"{context}\nПользователь: {message}")
            
            # Если модель не смогла сгенерировать внятный ответ
            if not response or response.strip() == "":
                return (
                    "Извините, я не смог найти подходящий ответ на ваш вопрос. "
                    "Давайте я переведу вас на оператора для более детальной консультации.",
                    True
                )
            
            # Добавляем ответ в историю
            self.add_message(user_id, response, role="assistant")
            
            return response, False

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "Извините, произошла ошибка. Перевожу на оператора...", True

    def clear_conversation(self, user_id: int):
        if user_id in self.conversations:
            del self.conversations[user_id]