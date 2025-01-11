# app/database/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Interaction(Base):
    __tablename__ = 'interactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    message = Column(Text)
    response = Column(Text)
    message_type = Column(String(50))
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class OperatorSession(Base):
    __tablename__ = 'operator_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    status = Column(String(20))  # pending, in_progress, answered, closed
    last_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)  # Для отслеживания активности

    def get_chat_history(self, db_manager, limit=5):
        """Получить последние сообщения чата"""
        return db_manager.get_user_interactions(self.user_id, limit)

class Subscriber(Base):
    __tablename__ = 'subscribers'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String(100))
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
