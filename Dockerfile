FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY bot.py .
COPY database.py .
COPY env.py .

RUN pip install --no-cache-dir -r requirements.txt


CMD ["python", "bot.py"]