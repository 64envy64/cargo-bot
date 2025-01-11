# app/database/operations.py
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
import logging

from app.database.models import Base, Interaction, OperatorSession, Subscriber
from app.config import DATABASE_URL

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_url: str):
        """Инициализация подключения к БД"""
        try:
            # Получаем путь к файлу БД
            db_path = db_url.replace('sqlite:///', '')
            
            # Если путь не абсолютный, делаем его относительно корня проекта
            if not os.path.isabs(db_path):
                db_path = os.path.join('/app', db_path)
            
            # Создаем директорию для БД, если её нет
            db_dir = os.path.dirname(db_path)
            os.makedirs(db_dir, exist_ok=True)
            
            # Создаем подключение
            self.engine = create_engine(f'sqlite:///{db_path}')
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            
            # Создаем таблицы при инициализации
            self.init_database()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    # Метод для обновления схемы БД (использовать только при необходимости)
    def update_schema(self):
        """Обновление схемы базы данных"""
        try:
            Base.metadata.drop_all(self.engine)
            Base.metadata.create_all(self.engine)
            logger.info("Database schema updated successfully")
        except Exception as e:
            logger.error(f"Error updating database schema: {e}")
            raise

    def save_interaction(self, user_id: int, message: str, response: str = None,
                         message_type: str = "text", success: bool = True):
        """
        Сохранение диалога (пользователь -> бот / бот -> пользователь).
        """
        try:
            interaction = Interaction(
                user_id=user_id,
                message=message,
                response=response,
                message_type=message_type,
                success=success
            )
            self.session.add(interaction)
            self.session.commit()
        except Exception as e:
            logger.error(f"Error saving interaction: {e}")
            self.session.rollback()

    def create_operator_session(self, user_id: int, message: str = None):
        """Создать (или обновить существующую) сессию оператора."""
        try:
            sess_obj = self.session.query(OperatorSession).filter_by(user_id=user_id).first()
            if not sess_obj:
                sess_obj = OperatorSession(
                    user_id=user_id,
                    status='pending',
                    last_message=message or "Нет сообщения"  # Добавляем значение по умолчанию
                )
                self.session.add(sess_obj)
            else:
                sess_obj.status = 'pending'
                sess_obj.last_message = message or sess_obj.last_message
                sess_obj.updated_at = datetime.utcnow()
            self.session.commit()
            return sess_obj
        except Exception as e:
            logger.error(f"Error create_operator_session: {e}")
            self.session.rollback()
            return None

    def get_pending_sessions(self):
        """Список пользователей, которые в статусе 'pending'."""
        try:
            return (
                self.session.query(OperatorSession)
                .filter(OperatorSession.status == 'pending')
                .all()
            )
        except Exception as e:
            logger.error(f"Error get_pending_sessions: {e}")
            return []

    def set_session_active(self, user_id: int):
        """Перевести сессию в active."""
        try:
            sess_obj = self.session.query(OperatorSession).filter_by(user_id=user_id).first()
            if sess_obj:
                sess_obj.status = 'active'
                sess_obj.updated_at = datetime.utcnow()
                self.session.commit()
        except Exception as e:
            logger.error(f"Error set_session_active: {e}")
            self.session.rollback()

    def close_session(self, user_id: int):
        """Закрыть сессию (status='closed')."""
        try:
            sess_obj = self.session.query(OperatorSession).filter_by(user_id=user_id).first()
            if sess_obj:
                sess_obj.status = 'closed'
                sess_obj.updated_at = datetime.utcnow()
                self.session.commit()
        except Exception as e:
            logger.error(f"Error close_session: {e}")
            self.session.rollback()

    def get_answered_sessions(self):
        """Получить отвеченные сессии"""
        try:
            return (
                self.session.query(OperatorSession)
                .filter(OperatorSession.status == 'answered')
                .order_by(OperatorSession.updated_at.desc())
                .all()
            )
        except Exception as e:
            logger.error(f"Error get_answered_sessions: {e}")
            return []

    def get_unanswered_sessions(self):
        """Получить неотвеченные сессии"""
        try:
            return (
                self.session.query(OperatorSession)
                .filter(OperatorSession.status == 'pending')
                .order_by(OperatorSession.created_at.desc())
                .all()
            )
        except Exception as e:
            logger.error(f"Error get_unanswered_sessions: {e}")
            return []

    def set_session_answered(self, user_id: int):
        """Пометить сессию как отвеченную"""
        try:
            sess_obj = self.session.query(OperatorSession).filter_by(user_id=user_id).first()
            if sess_obj:
                sess_obj.status = 'answered'
                sess_obj.updated_at = datetime.utcnow()
                self.session.commit()
        except Exception as e:
            logger.error(f"Error set_session_answered: {e}")
            self.session.rollback()

    def get_user_interactions(self, user_id: int, limit: int = 5):
        """Получить последние сообщения пользователя"""
        try:
            return (
                self.session.query(Interaction)
                .filter_by(user_id=user_id)
                .order_by(Interaction.created_at.desc())
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Error get_user_interactions: {e}")
            return []

    def set_session_in_progress(self, user_id: int):
        """Перевести сессию в статус 'в процессе'"""
        try:
            sess_obj = self.session.query(OperatorSession).filter_by(user_id=user_id).first()
            if sess_obj:
                sess_obj.status = 'in_progress'
                sess_obj.updated_at = datetime.utcnow()
                self.session.commit()
        except Exception as e:
            logger.error(f"Error set_session_in_progress: {e}")
            self.session.rollback()

    def update_last_activity(self, user_id: int):
        """Обновить время последней активности"""
        try:
            sess_obj = self.session.query(OperatorSession).filter_by(user_id=user_id).first()
            if sess_obj:
                sess_obj.last_activity = datetime.utcnow()
                self.session.commit()
        except Exception as e:
            logger.error(f"Error update_last_activity: {e}")
            self.session.rollback()

    def get_inactive_sessions(self, hours=12):
        """Получить неактивные сессии"""
        try:
            inactive_time = datetime.utcnow() - timedelta(hours=hours)
            return (
                self.session.query(OperatorSession)
                .filter(
                    OperatorSession.status == 'in_progress',
                    OperatorSession.last_activity < inactive_time
                )
                .all()
            )
        except Exception as e:
            logger.error(f"Error get_inactive_sessions: {e}")
            return []

    def get_in_progress_sessions(self):
        """Получить сессии в процессе"""
        try:
            return (
                self.session.query(OperatorSession)
                .filter(OperatorSession.status == 'in_progress')
                .order_by(OperatorSession.updated_at.desc())
                .all()
            )
        except Exception as e:
            logger.error(f"Error get_in_progress_sessions: {e}")
            return []

    def init_database(self):
        """Инициализация базы данных"""
        try:
            # Создаем все таблицы из моделей
            Base.metadata.create_all(self.engine)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def add_subscriber(self, user_id: int, username: str = None) -> bool:
        """Добавление нового подписчика"""
        try:
            # Проверяем, существует ли уже такой подписчик
            subscriber = (
                self.session.query(Subscriber)
                .filter_by(user_id=user_id)
                .first()
            )
            
            if subscriber:
                # Если существует, обновляем данные
                subscriber.is_active = True
                subscriber.username = username
            else:
                # Если нет, создаем нового
                subscriber = Subscriber(
                    user_id=user_id,
                    username=username,
                    is_active=True
                )
                self.session.add(subscriber)
                
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error adding subscriber: {e}")
            self.session.rollback()
            return False

    def check_subscription(self, user_id: int) -> bool:
        """Проверка подписки пользователя"""
        try:
            subscriber = (
                self.session.query(Subscriber)
                .filter_by(user_id=user_id, is_active=True)
                .first()
            )
            return bool(subscriber)
            
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            return False

    def get_active_subscribers(self):
        """Получить список активных подписчиков"""
        try:
            subscribers = (
                self.session.query(Subscriber)
                .filter_by(is_active=True)
                .all()
            )
            logger.info(f"Found {len(subscribers)} active subscribers")
            # Логируем ID подписчиков для отладки
            subscriber_ids = [s.user_id for s in subscribers]
            logger.info(f"Subscriber IDs: {subscriber_ids}")
            return subscribers
        except Exception as e:
            logger.error(f"Error getting active subscribers: {e}")
            return []

    def get_subscribers_count(self):
        """Получить общее количество подписчиков"""
        try:
            return self.session.query(Subscriber).count()
        except Exception as e:
            logger.error(f"Error getting subscribers count: {e}")
            return 0

    def get_active_subscribers_count(self):
        """Получить количество активных подписчиков"""
        try:
            return (
                self.session.query(Subscriber)
                .filter_by(is_active=True)
                .count()
            )
        except Exception as e:
            logger.error(f"Error getting active subscribers count: {e}")
            return 0

    def unsubscribe(self, user_id: int) -> bool:
        """Отписка пользователя от рассылки"""
        try:
            subscriber = (
                self.session.query(Subscriber)
                .filter_by(user_id=user_id)
                .first()
            )
            
            if subscriber:
                subscriber.is_active = False
                self.session.commit()
                logger.info(f"User {user_id} unsubscribed successfully")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error unsubscribing user {user_id}: {e}")
            self.session.rollback()
            return False

def save_interaction(user_id: int, message: str, response: str = None,
                    message_type: str = "text", success: bool = True):
    """
    Сохранение диалога (пользователь -> бот / бот -> пользователь).
    """
    try:
        db = DatabaseManager(DATABASE_URL)
        db.save_interaction(
            user_id=user_id,
            message=message,
            response=response,
            message_type=message_type,
            success=success
        )
    except Exception as e:
        logger.error(f"Error saving interaction: {e}")
