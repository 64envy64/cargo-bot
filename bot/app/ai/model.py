import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Dict, List, Optional
import logging
from app.knowledge_base.faq import FAQ

logger = logging.getLogger(__name__)

class SilkwayAI:
    def __init__(self, model_path: str = "IlyaGusev/saiga2_7b_lora"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        # Временно отключаем загрузку модели для тестирования
        self.tokenizer = None
        self.model = None
        
        # Инициализируем FAQ
        self.faq = FAQ()
        
        # Определяем разрешенные темы и ключевые слова
        self.allowed_topics = {
            'доставка': [
                'доставка', 'доставить', 'привезти', 'курьер', 'получить',
                'заказ', 'отправление', 'посылка'
            ],
            'трекинг': [
                'трек', 'отследить', 'где', 'статус', 'местоположение',
                'номер', 'посмотреть', 'найти'
            ],
            'адрес': [
                'адрес', 'склад', 'находится', 'расположен', 'контакты',
                'где находится', 'как добраться', 'координаты'
            ],
            'возврат': [
                'возврат', 'вернуть', 'обмен', 'поменять', 'брак',
                'недостача', 'не подошло', 'проблема'
            ],
            'оплата': [
                'оплата', 'оплатить', 'стоимость', 'цена', 'тариф',
                'сколько стоит', 'карта', 'счет'
            ],
            'график': [
                'график', 'время', 'работает', 'открыто', 'закрыто',
                'режим', 'часы работы', 'выходные'
            ]
        }

    def is_allowed_question(self, text: str) -> bool:
        """
        Проверка, относится ли вопрос к разрешенным темам
        """
        text = text.lower()
        
        # Сначала проверяем FAQ
        if self.faq.get_response(text):
            return True
            
        # Проверяем ключевые слова по темам
        for topic_keywords in self.allowed_topics.values():
            if any(keyword in text for keyword in topic_keywords):
                return True
                
        return False

    def generate_response(
        self,
        user_input: str,
        max_length: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Генерация ответа на вопрос пользователя
        """
        # Проверяем наличие ответа в FAQ
        faq_response = self.faq.get_response(user_input)
        if faq_response:
            return faq_response
            
        # Если нет в FAQ, используем заготовленные ответы по темам
        user_input_lower = user_input.lower()
        
        # Словарь базовых ответов по темам
        topic_responses = {
            'доставка': (
                "Мы можем организовать доставку вашего заказа. "
                "Для этого перейдите в раздел «Заказы» в приложении, "
                "выберите опцию «доставка до двери» и укажите адрес. "
                "Стоимость доставки рассчитывается автоматически."
            ),
            'трекинг': (
                "Чтобы отследить ваш заказ, используйте раздел «Заказы» "
                "в мобильном приложении. Там вы увидите текущий статус "
                "и местоположение вашей посылки."
            ),
            'адрес': (
                "Наши склады работают по следующим адресам:\n"
                "Для уточнения графика работы конкретного склада "
            ),
            'возврат': (
                "Для оформления возврата:\n"
                "1. Свяжитесь с продавцом через приложение\n"
                "2. Опишите причину возврата\n"
                "3. Следуйте инструкциям продавца\n\n"
            )
        }
        
        # Проверяем каждую тему
        for topic, keywords in self.allowed_topics.items():
            if any(keyword in user_input_lower for keyword in keywords):
                if topic in topic_responses:
                    return topic_responses[topic]
        
        # Если не нашли конкретный ответ, но тема разрешена
        if self.is_allowed_question(user_input):
            return (
                "Я понимаю ваш вопрос, но для предоставления точной информации "
                "мне нужно перевести вас на оператора. Он сможет помочь вам более детально."
            )
        
        return (
            "Извините, я не могу предоставить информацию по этому вопросу. "
            "Пожалуйста, свяжитесь с оператором для получения помощи."
        )