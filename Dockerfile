FROM python:3.12-slim

WORKDIR /app

# Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY . .

# Создаём директорию для базы данных
RUN mkdir -p /app/data

# Запускаем бота
CMD ["python", "main.py"]

