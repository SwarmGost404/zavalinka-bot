from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from database import Base, DATABASE_URL  # Импортируем Base и DATABASE_URL из database.py

# Подключение к базе данных
engine = create_engine(DATABASE_URL)

# Удаляем все таблицы
def drop_all_tables():
    print("Удаление всех таблиц...")
    Base.metadata.drop_all(bind=engine)
    print("Все таблицы удалены.")

# Создаем все таблицы заново
def create_all_tables():
    print("Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    print("Таблицы созданы.")

# Основная функция
def reset_database():
    print("Очистка базы данных...")
    drop_all_tables()
    create_all_tables()
    print("База данных успешно очищена и пересоздана.")

if __name__ == "__main__":
    reset_database()