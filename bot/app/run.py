import os
import asyncio
import logging
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from telegram.ext import ApplicationBuilder
from telegram import Update
import uvicorn
import nest_asyncio
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor

from app.bot.handlers import BotHandlers
from app.database.operations import DatabaseManager
from app.ai.chat import ChatManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")
SECRET_KEY = os.getenv("SECRET_KEY", "MYSECRET")

# Инициализируем менеджер БД
db_manager = DatabaseManager(DATABASE_URL)

# Создаём Telegram-приложение (application) глобально
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

chat_manager = ChatManager(db_manager)

bot_handlers = BotHandlers(
    chat_manager=chat_manager,
    db_manager=db_manager
)

bot_handlers.register_handlers(application)

# ----- FastAPI -----
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AdminMessage(BaseModel):
    user_id: int
    text: str

@app.post("/admin/send_message")
async def send_admin_message(data: AdminMessage, request: Request):
    """API endpoint для отправки сообщений от админ-бота"""
    # Проверяем секретный ключ
    secret = request.query_params.get('secret')
    if secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid secret key")
    
    try:
        # Отправляем сообщение пользователю
        await application.bot.send_message(
            chat_id=data.user_id,
            text=data.text
        )
        # Сохраняем в базе
        db_manager.save_interaction(
            user_id=data.user_id,
            message="[ADMIN REPLY]",
            response=data.text,
            message_type="admin",
            success=True
        )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error sending admin message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Запуск Telegram Polling + FastAPI вместе
def main():
    nest_asyncio.apply()
    
    # Создаем новый event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Запускаем FastAPI в отдельном потоке
    def run_fastapi():
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    
    # Создаем пул потоков
    executor = ThreadPoolExecutor(max_workers=2)
    
    try:
        # Запускаем FastAPI в отдельном потоке
        executor.submit(run_fastapi)
        
        # Запускаем телеграм бота в основном потоке
        logger.info("Starting Telegram bot...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        executor.shutdown(wait=True)
        loop.close()

if __name__ == "__main__":
    main()