from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional

# Настройки подключения к PostgreSQL (замените на свои)
DATABASE_URL = "postgresql+psycopg2://song_user:ваш_пароль@localhost:5432/songs_db"

# Создаем движок SQLAlchemy
engine = create_engine(DATABASE_URL)

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

# Функция для получения сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic модель для валидации данных
class SongBase(BaseModel):
    title: str
    text: Optional[str] = None
    audio_file: Optional[str] = None
    region: str

class SongCreate(SongBase):
    pass

class Song(SongBase):
    id: int

    class Config:
        from_attributes = True  # Ранее orm_mode = True

# Функция для добавления песни
def create_song(db: Session, song: SongCreate):
    db_song = Song(**song.dict())
    db.add(db_song)
    db.commit()
    db.refresh(db_song)
    return db_song

# Функция для получения всех песен
def get_all_songs(db: Session):
    return db.query(Song).all()

# Функция для поиска песен по области
def get_songs_by_region(db: Session, region: str):
    return db.query(Song).filter(Song.region.ilike(f"%{region}%")).all()

# Функция для поиска песни по названию
def search_by_title(db: Session, title: str):
    return db.query(Song).filter(Song.title.ilike(f"%{title}%")).all()

# Функция для поиска песни по тексту
def search_by_text(db: Session, text: str):
    return db.query(Song).filter(Song.text.ilike(f"%{text}%")).all()

# Создаем приложение FastAPI
app = FastAPI()

# Инициализация базы данных при запуске
init_db()

# Добавление песни
@app.post("/songs/", response_model=Song)
def add_song(song: SongCreate, db: Session = Depends(get_db)):
    return create_song(db, song)

# Получение всех песен
@app.get("/songs/", response_model=list[Song])
def list_songs(db: Session = Depends(get_db)):
    return get_all_songs(db)

# Поиск песен по названию
@app.get("/songs/search_title/", response_model=list[Song])
def search_song_by_title(title: str, db: Session = Depends(get_db)):
    return search_by_title(db, title)

# Поиск песен по тексту
@app.get("/songs/search_text/", response_model=list[Song])
def search_song_by_text(text: str, db: Session = Depends(get_db)):
    return search_by_text(db, text)

# Поиск песен по области
@app.get("/songs/search_region/", response_model=list[Song])
def search_song_by_region(region: str, db: Session = Depends(get_db)):
    return get_songs_by_region(db, region)