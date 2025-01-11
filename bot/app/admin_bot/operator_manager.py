from typing import List
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class OperatorManager:
    def __init__(self, operators_file: str = "operators.json"):
        self.operators_file = Path(operators_file)
        self.operators = self._load_operators()
        
    def _load_operators(self) -> List[int]:
        """Загружает список операторов из файла"""
        if not self.operators_file.exists():
            return []
            
        try:
            with open(self.operators_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading operators: {e}")
            return []
            
    def _save_operators(self):
        """Сохраняет список операторов в файл"""
        try:
            with open(self.operators_file, 'w') as f:
                json.dump(self.operators, f)
        except Exception as e:
            logger.error(f"Error saving operators: {e}")
            
    def add_operator(self, user_id: int, admin_id: int) -> bool:
        if admin_id not in self.operators[:3]:  # Только первые 3 оператора могут добавлять
            return False
            
        if user_id not in self.operators:
            self.operators.append(user_id)
            self._save_operators()
        return True
        
    def remove_operator(self, user_id: int, admin_id: int) -> bool:
        """Удаляет оператора"""
        if admin_id not in self.operators[:3]:
            return False
            
        if user_id in self.operators:
            self.operators.remove(user_id)
            self._save_operators()
        return True
        
    def is_operator(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь оператором"""
        return user_id in self.operators 