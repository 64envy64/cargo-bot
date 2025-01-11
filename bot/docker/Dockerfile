FROM python:3.10-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    cmake \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание директорий
RUN mkdir -p /app/app /app/data /app/logs /app/temp

# Копирование зависимостей
COPY requirements.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "python-telegram-bot[job-queue]" \
    && pip install --no-cache-dir sentencepiece

# Копирование приложения
COPY app /app/app/

# Добавляем путь к модулям в PYTHONPATH
ENV PYTHONPATH=/app:$PYTHONPATH

# Создаем директорию для базы данных и устанавливаем права
RUN mkdir -p /app/data && \
    touch /app/data/bot.db && \
    chmod -R 777 /app/data

CMD ["python", "-u", "app/run.py"]