from datetime import datetime
import json
import os

class Analytics:
    def __init__(self, log_file="analytics.jsonl"):
        self.log_file = log_file
    
    def log_interaction(self, user_id, question, answer, is_handled=True):
        """Логирование взаимодействия с ботом"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "question": question,
            "answer": answer,
            "is_handled": is_handled
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def get_daily_stats(self):
        """Получение простой статистики за день"""
        stats = {
            "total_queries": 0,
            "handled_queries": 0,
            "redirected_to_operator": 0
        }
        
        # Чтение и подсчет статистики
        return stats