import easyocr
from dataclasses import dataclass
import re

@dataclass
class Address:
    client_code: str
    phone: str
    province: str
    full_address: str

class AddressChecker:
    def __init__(self):
        self.reader = easyocr.Reader(['ch_sim', 'en'])
    
    def extract_client_code(self, text: str) -> str:
        """Извлекает код клиента из текста"""
        # Поиск 6-значного кода
        code_match = re.search(r'\d{6}', text)
        return code_match.group(0) if code_match else None

    def extract_phone(self, text: str) -> str:
        """Извлекает номер телефона из текста"""
        phone_match = re.search(r'\d{11}', text)
        return phone_match.group(0) if phone_match else None

    def validate_address(self, detected_text: str, client_code: str) -> tuple[bool, str]:
        """
        Проверяет правильность адреса
        Returns: (is_valid, message)
        """
        # Эталонный адрес
        reference_address = {
            'province': '广东省',
            'city': '佛山市',
            'district': '南海区',
            'code_prefix': '努尔波'
        }
        
        # Проверяем наличие всех компонентов адреса
        is_valid = all(component in detected_text for component in reference_address.values())
        
        # Проверяем код клиента
        if client_code and f"{reference_address['code_prefix']}{client_code}" not in detected_text:
            return False, f"Неверный код клиента. Ожидается: {client_code}"
        
        if not is_valid:
            return False, "Адрес не соответствует формату. Проверьте правильность заполнения."
            
        return True, "Адрес заполнен верно"

    async def check_image(self, image_path: str, expected_client_code: str) -> tuple[bool, str]:
        """
        Проверяет изображение с адресом
        Args:
            image_path: путь к изображению
            expected_client_code: ожидаемый код клиента
        Returns:
            (is_valid, message)
        """
        try:
            # Распознаем текст
            result = self.reader.readtext(image_path)
            detected_text = ' '.join([text[1] for text in result])
            
            # Проверяем адрес
            is_valid, message = self.validate_address(detected_text, expected_client_code)
            
            if is_valid:
                return True, "✅ Адрес заполнен верно"
            else:
                return False, f"❌ {message}\n\nПравильный формат адреса:\n努尔波[код]\n13078833342\n广东省 佛山市 南海区\n里水镇新联工业区工业大道东一路3号航达В01库区[код]号"
                
        except Exception as e:
            return False, f"Ошибка при проверке адреса: {str(e)}"
