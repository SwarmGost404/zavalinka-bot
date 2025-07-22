import json
from datetime import datetime
from typing import List, Dict
from database import get_db, Song  # Импортируем ваши функции из db.py

def export_songs_to_json(filename: str = None) -> str:
    """
    Экспортирует все песни из базы данных в JSON файл.
    
    Args:
        filename (str, optional): Имя файла для сохранения. Если не указано, будет сгенерировано автоматически.
    
    Returns:
        str: Путь к сохраненному файлу
    """
    # Получаем сессию базы данных
    db = next(get_db())
    
    try:
        # Получаем все песни
        songs: List[Song] = db.query(Song).all()
        
        # Преобразуем в список словарей
        songs_data: List[Dict] = [
            {
                "id": song.id,
                "title": song.title,
                "text": song.text,
                "region": song.region,
                "category": song.category
            }
            for song in songs
        ]
        
        # Генерируем имя файла, если не указано
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"folk_songs_export_{timestamp}.json"
        
        # Сохраняем в JSON файл
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(songs_data, f, ensure_ascii=False, indent=2)
        
        print(f"Успешно экспортировано {len(songs_data)} песен в файл {filename}")
        return filename
    
    except Exception as e:
        print(f"Ошибка при экспорте данных: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Пример использования
    export_songs_to_json("folk_songs_backup.json")