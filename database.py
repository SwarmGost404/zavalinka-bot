from sqlalchemy import create_engine, Column, Integer, String, Text, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
from env import DATABASE_URL  # Убедитесь, что DATABASE_URL указан в .env

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем движок SQLAlchemy для PostgreSQL
engine = create_engine(DATABASE_URL)

# Создаем SessionLocal для работы с базой данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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

# Модель для таблицы песен
class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    text = Column(Text)  # Текст песни (опционально)
    region = Column(String, nullable=False)  # Категория и место записи в формате "категория@@место_записи"
    audio_file = Column(LargeBinary)  # Аудиозапись в бинарном формате

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
def add_song(db, title: str, category: str, place: str, text: str = None, audio_file: bytes = None):
    try:
        # Проверяем, что title, category и place не пустые
        if not title or not category or not place:
            raise ValueError("Название, категория и место записи не могут быть пустыми")

        # Формируем значение для столбца region
        region = f"{category}@@{place}"

        # Создаем объект песни
        song = Song(title=title, text=text, region=region, audio_file=audio_file)
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

# Функция для поиска песен по категории
def get_songs_by_category(db, category: str):
    try:
        return db.query(Song).filter(Song.region.ilike(f"%{category}@@%")).all()
    except Exception as e:
        logger.error(f"Ошибка при поиске песен по категории: {e}")
        raise

# Функция для поиска песен по месту записи
def get_songs_by_place(db, place: str):
    try:
        return db.query(Song).filter(Song.region.ilike(f"%@@{place}%")).all()
    except Exception as e:
        logger.error(f"Ошибка при поиске песен по месту записи: {e}")
        raise

# Функция для обновления места записи в существующей песне
def update_song_place(db, song_id: int, new_place: str):
    try:
        song = db.query(Song).filter(Song.id == song_id).first()
        if song is None:
            raise ValueError("Песня не найдена")

        # Разделяем текущее значение region на категорию и место записи
        category, _ = song.region.split("@@")

        # Обновляем место записи
        song.region = f"{category}@@{new_place}"
        db.commit()
        db.refresh(song)
        logger.info(f"Обновлено место записи для песни: {song.title}")
        return song
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при обновлении места записи: {e}")
        raise

# Функция для поиска песни по названию
def search_by_title(db, title: str):
    try:
        return db.query(Song).filter(Song.title.ilike(f"%{title}%")).all()
    except Exception as e:
        logger.error(f"Ошибка при поиске песни по названию: {e}")
        raise

def update_song_audio(db, song_id: int, audio_file: bytes):
    try:
        song = db.query(Song).filter(Song.id == song_id).first()
        if song is None:
            raise ValueError("Песня не найдена")

        song.audio_file = audio_file
        db.commit()
        db.refresh(song)
        logger.info(f"Обновлена аудиозапись для песни: {song.title}")
        return song
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при обновлении аудиозаписи: {e}")
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