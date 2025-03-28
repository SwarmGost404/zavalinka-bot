import json
from datetime import datetime
from sqlalchemy.orm import Session
from database import Song, get_db  # Предполагается, что ваш код находится в models.py

def export_songs_to_json(db: Session, output_file: str = "songs_export.json"):
    try:
        # Получаем все песни из базы данных
        songs = db.query(Song).all()
        
        # Конвертируем в список словарей
        songs_data = []
        for song in songs:
            songs_data.append({
                "id": song.id,
                "title": song.title,
                "text": song.text,
                "region": song.region
            })
        
        # Сохраняем в JSON файл
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(songs_data, f, ensure_ascii=False, indent=2)
        
        print(f"Успешно экспортировано {len(songs_data)} песен в {output_file}")
        return True
    
    except Exception as e:
        print(f"Ошибка при экспорте данных: {e}")
        return False

if __name__ == "__main__":
    # Инициализация базы данных (если ещё не сделано)
    from database import init_db
    init_db()
    
    # Экспорт данных
    db = next(get_db())  # Получаем сессию базы данных
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_songs_to_json(db, f"songs_export_{timestamp}.json")
