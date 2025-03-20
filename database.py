from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://gen_user:cP%3DSUSZ%5C1fHOsT@2.59.40.244:5432/default_db")

# Создаем движок SQLAlchemy
engine = create_engine(DATABASE_URL)

# Проверяем подключение к базе данных
try:
    connection = engine.connect()
    logger.info("Подключение к базе данных успешно установлено!")
    connection.close()
except Exception as e:
    logger.error(f"Ошибка подключения к базе данных: {e}")

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
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы созданы (если их не было)")

# Функция для получения сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для добавления песни
def add_song(db, title: str, region: str, text: str = None, audio_file: str = None):
    song = Song(title=title, text=text, audio_file=audio_file, region=region)
    db.add(song)
    db.commit()
    db.refresh(song)
    logger.info(f"Добавлена песня: {song.title}")
    return song

# Функция для получения всех песен
def get_all_songs(db):
    return db.query(Song).all()

# Функция для поиска песен по области
def get_songs_by_region(db, region: str):
    return db.query(Song).filter(Song.region.ilike(f"%{region}%")).all()

# Функция для поиска песни по названию
def search_by_title(db, title: str):
    return db.query(Song).filter(Song.title.ilike(f"%{title}%")).all()

# Функция для поиска песни по тексту
def search_by_text(db, text: str):
    return db.query(Song).filter(Song.text.ilike(f"%{text}%")).all()

# Инициализация базы данных
if __name__ == "__main__":
    init_db()