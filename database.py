from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from env import DATABASE_URL

# Создаем движок SQLAlchemy
engine = create_engine(DATABASE_URL)

# Проверяем подключение к базе данных
try:
    connection = engine.connect()
    logger.info("Подключение к базе данных успешно установлено!")
    connection.close()
except Exception as e:
    logger.error(f"Ошибка подключения к базе данных: {e}")
    raise  # Прерываем выполнение, если подключение не удалось

# Создаем базовый класс для моделей
Base = declarative_base()

# Создаем сессию для работы с базой данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Модель для таблицы песен
class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    text = Column(Text)  # Текст песни (опционально)
    audio_file = Column(String)  # Путь к аудиофайлу (опционально)
    region = Column(String, nullable=False)

# Создаем таблицы в базе данных (если их нет)
def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Таблицы созданы (если их не было)")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise  # Прерываем выполнение, если таблицы не созданы

# Функция для получения сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для добавления песни
def add_song(db, title: str, region: str, text: str = None, audio_file: str = None):
    try:
        # Проверяем, что title и region не пустые
        if not title or not region:
            raise ValueError("Название и область не могут быть пустыми")

        # Создаем объект песни
        song = Song(title=title, text=text, audio_file=audio_file, region=region)
        db.add(song)
        db.commit()
        db.refresh(song)
        logger.info(f"Добавлена песня: {song.title}")
        return song
    except Exception as e:
        db.rollback()  # Откатываем транзакцию в случае ошибки
        logger.error(f"Ошибка при добавлении песни: {e}")
        raise  # Пробрасываем исключение дальше

# Функция для получения всех песен
def get_all_songs(db):
    try:
        return db.query(Song).all()
    except Exception as e:
        logger.error(f"Ошибка при получении списка песен: {e}")
        raise

# Функция для поиска песен по области
def get_songs_by_region(db, region: str):
    try:
        return db.query(Song).filter(Song.region.ilike(f"%{region}%")).all()
    except Exception as e:
        logger.error(f"Ошибка при поиске песен по области: {e}")
        raise

# Функция для поиска песни по названию
def search_by_title(db, title: str):
    try:
        return db.query(Song).filter(Song.title.ilike(f"%{title}%")).all()
    except Exception as e:
        logger.error(f"Ошибка при поиске песни по названию: {e}")
        raise

# Функция для поиска песни по тексту
def search_by_text(db, text: str):
    try:
        return db.query(Song).filter(Song.text.ilike(f"%{text}%")).all()
    except Exception as e:
        logger.error(f"Ошибка при поиске песни по тексту: {e}")
        raise

# Инициализация базы данных
if __name__ == "__main__":
    init_db()