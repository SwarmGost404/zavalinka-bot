from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
from env import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL)

try:
    connection = engine.connect()
    logger.info("Подключение к базе данных успешно установлено!")
    connection.close()
except Exception as e:
    logger.error(f"Ошибка подключения к базе данных: {e}")
    raise

Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Song(Base):
    __tablename__ = "folk_songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    text = Column(Text)
    region = Column(String, nullable=False)
    category = Column(String)

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Таблицы созданы (если их не было)")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def add_song(db, title: str, region: str, text: str = None):
    try:
        if not title or not region:
            raise ValueError("Название и область не могут быть пустыми")

        song = Song(title=title, text=text, region=region)
        db.add(song)
        db.commit()
        db.refresh(song)
        logger.info(f"Добавлена песня: {song.title}")
        return song
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при добавлении песни: {e}")
        raise

def get_all_songs(db):
    try:
        return db.query(Song).all()
    except Exception as e:
        logger.error(f"Ошибка при получении списка песен: {e}")
        raise

def get_songs_by_region(db, region: str):
    try:
        return db.query(Song).filter(Song.region.ilike(f"%{region}%")).all()
    except Exception as e:
        logger.error(f"Ошибка при поиске песен по области: {e}")
        raise

def delete_song(db, song_id: int):
    try:
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
        raise

def get_all_songs_with_id(db):
    try:
        songs = db.query(Song.id, Song.title, Song.text, Song.region, Song.category).all()
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

def search_by_title(db, title: str):
    try:
        return db.query(Song).filter(Song.title.ilike(f"%{title}%")).all()
    except Exception as e:
        logger.error(f"Ошибка при поиске песни по названию: {e}")
        raise

def search_by_text(db, text: str):
    try:
        return db.query(Song).filter(Song.text.ilike(f"%{text}%")).all()
    except Exception as e:
        logger.error(f"Ошибка при поиске песни по тексту: {e}")
        raise

def get_song_by_id(db, song_id: int):
    try:
        return db.query(Song).filter(Song.id == song_id).first()
    except Exception as e:
        logger.error(f"Ошибка при поиске песни по ID: {e}")
        raise

if __name__ == "__main__":
    init_db()
