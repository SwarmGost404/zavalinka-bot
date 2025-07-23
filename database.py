from sqlalchemy import create_engine, Column, Integer, String, Text, LargeBinary
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from models import *

import logging
from env import DATABASE_URL  # Убедитесь, что DATABASE_URL указан в .env

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем движок SQLAlchemy для PostgreSQL
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

class Song(Base):
    __tablename__ = "folk_songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    region = Column(String, nullable=False)
    category = Column(String)

class Audio(Base):
    __tablename__ = "folk_audio"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    audio = Column(LargeBinary)  # Для хранения бинарных данных аудиофайла
    region = Column(String, nullable=False)
    category = Column(String)


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
def add_song(db, NewSong: SongText):
    try:
        # Проверяем, что title и region не пустые
        if not NewSong.title or not NewSong.region or not NewSong.text:
            raise ValueError("Название и область не могут быть пустыми")

        # Создаем объект песни
        song = Song(title=NewSong.title, text=NewSong.text, region=NewSong.region)
        db.add(song)
        db.commit()
        db.refresh(song)
        logger.info(f"Добавлена песня: {song.title}")
        return song
    except Exception as e:
        db.rollback()  # Откатываем транзакцию в случае ошибки
        logger.error(f"Ошибка при добавлении песни: {e}")
        raise  # Пробрасываем исключение дальше

# create audio fucntion
def create_audio(db, song: SongAudio):
    try:
        if not song.title or not song.region or not song.audio:
            raise ValueError("Название и область не могут быть пустыми")
        
        createdSong = Audio(song)
        db.add(createdSong)
        db.commit()
        db.refresh(createdSong)
        logger.info(f"Добавлена запись: {createdSong.title}")
        return createdSong
    except Exception as e:
        db.rollback()  # Откатываем транзакцию в случае ошибки
        logger.error(f"Ошибка при добавлении Записи: {e}")
        raise  # Пробрасываем исключение дальше


# Функция для получения всех песен
def get_all_songs(db):
    try:
        return db.query(Song).all()
    except Exception as e:
        logger.error(f"Ошибка при получении списка песен: {e}")
        raise

def get_all_audio(db):
    try:
        return db.query(Audio).all()
    except Exception as e:
        logger.error(f"Ошибка при получении списка записей: {e}")
        raise

# Функция для поиска песен по области
def get_songs_by_region(db, region: str):
    try:
        return db.query(Song).filter(Song.region.ilike(f"%{region}%")).all()
    except Exception as e:
        logger.error(f"Ошибка при поиске песен по области: {e}")
        raise

def get_audio_by_region(db, region: str):
    try:
        return db.query(Audio).filter(Audio.region.ilike(f"%{region}%")).all()
    except Exception as e:
        logger.error(f"Ошибка при поиске записей по области: {e}")
        raise

# Функция для удаления песни по ID
def delete_song(db, song_id: int):
    try:
        # Логируем попытку удаления
        logger.info(f"Попытка удалить песню с ID: {song_id}")
        
        song = db.query(Song).filter(Song.id == song_id).first()
        if not song:
            logger.warning(f"Песня с ID {song_id} не найдена")
            raise ValueError(f"Песня с ID {song_id} не найдена")

        db.delete(song)
        db.commit()
        logger.info(f"Удалена песня с ID {song_id}: {song.title}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при удалении песни с ID {song_id}: {e}", exc_info=True)
        raise

def delete_song(db, song_id: int):
    try:
        # Логируем попытку удаления
        logger.info(f"Попытка удалить запись с ID: {song_id}")
        
        song = db.query(Audio).filter(Audio.id == song_id).first()
        if not song:
            logger.warning(f"Запись с ID {song_id} не найдена")
            raise ValueError(f"Запись с ID {song_id} не найдена")

        db.delete(song)
        db.commit()
        logger.info(f"Удалена Запись с ID {song_id}: {song.title}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при удалении записи с ID {song_id}: {e}", exc_info=True)
        raise

# Функция для обновления информации о песне
def update_song(
    db,
    song_id: int,
    title: str = None,
    text: str = None,
    region: str = None
):
    try:
        song = db.query(Song).filter(Song.id == song_id).first()
        if not song:
            raise ValueError(f"Песня с ID {song_id} не найдена")

        if title is not None:
            song.title = title
        if text is not None:
            song.text = text
        if region is not None:
            song.region = region

        db.commit()
        db.refresh(song)
        logger.info(f"Успешно обновлена песня с ID {song_id}: title={title is not None}, "
                   f"text={text is not None}, region={region is not None}")
        return song
        
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при обновлении песни ID {song_id}: {str(e)}")
        raise  # Можно заменить на return None, если хотите подавить исключение

# Функция для получения всех песен с их ID и другими полями
def get_all_songs_with_id(db):
    try:
        # Query all songs and return them with all fields including id
        songs = db.query(Song.id, Song.title, Song.text, Song.region, Song.category).all()
        
        # Convert the result to a list of dictionaries for easier handling
        songs_list = [
            {
                "id": song.id,
                "title": song.title,
                "text": song.text,
                "region": song.region,
                "category": song.category
            }
            for song in songs
        ]
        
        return songs_list
    except Exception as e:
        logger.error(f"Ошибка при получении списка песен с ID: {e}")
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

# Функция для поиска песни по ID
def get_song_by_id(db, song_id: int):
    try:
        return db.query(Song).filter(Song.id == song_id).first()
    except Exception as e:
        logger.error(f"Ошибка при поиске песни по ID: {e}")
        raise



# Инициализация базы данных
if __name__ == "__main__":
    init_db()
