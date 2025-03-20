import psycopg2

from env import DATABASE_URL

try:
    conn = psycopg2.connect(DATABASE_URL)
    print("Подключение к базе данных успешно установлено!")
    conn.close()
except Exception as e:
    print(f"Ошибка подключения к базе данных: {e}")