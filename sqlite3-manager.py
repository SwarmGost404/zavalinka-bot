import sqlite3

# Создаем соединение с базой данных (файл songs.db)
conn = sqlite3.connect('songs.db')
cursor = conn.cursor()

# Создаем таблицу songs
cursor.execute('''
CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    region TEXT NOT NULL
)
''')

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()