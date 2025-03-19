import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import sqlite3

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Функция для подключения к базе данных
def get_db_connection():
    conn = sqlite3.connect('songs.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Для доступа к данным по имени столбца
    return conn

# Функция для инициализации базы данных
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            region TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Функция для добавления песни в базу данных
def add_song(title: str, text: str, region: str) -> None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO songs (title, text, region) VALUES (?, ?, ?)', (title, text, region))
        conn.commit()
        logger.info(f"Песня '{title}' успешно добавлена.")
    except Exception as e:
        logger.error(f"Ошибка при добавлении песни: {e}")
        raise
    finally:
        if conn:
            conn.close()

# Функция для получения всех песен
def get_all_songs() -> list:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM songs')
        results = cursor.fetchall()
        return results
    except Exception as e:
        logger.error(f"Ошибка при получении всех песен: {e}")
        raise
    finally:
        if conn:
            conn.close()

# Функция для поиска песни по названию
def search_by_title(title: str) -> list:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM songs WHERE title LIKE ?', (f'%{title}%',))
        results = cursor.fetchall()
        return results
    except Exception as e:
        logger.error(f"Ошибка при поиске по названию: {e}")
        raise
    finally:
        if conn:
            conn.close()

# Функция для поиска песни по тексту
def search_by_text(text: str) -> list:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM songs WHERE text LIKE ?', (f'%{text}%',))
        results = cursor.fetchall()
        return results
    except Exception as e:
        logger.error(f"Ошибка при поиске по тексту: {e}")
        raise
    finally:
        if conn:
            conn.close()

# Обработчик команды /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Привет! Я бот для хранения текстов песен. Используй команды:\n'
        '/add - добавить песню\n'
        '/search_title - найти по названию\n'
        '/search_text - найти по тексту\n'
        '/list - показать все песни'
    )

# Обработчик команды /add
async def add(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни, область и текст через запятую:')
    context.user_data['awaiting_input'] = 'add_song'

# Обработчик команды /search_title
async def search_title(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни для поиска:')
    context.user_data['awaiting_input'] = 'search_title'

# Обработчик команды /search_text
async def search_text(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите текст песни для поиска:')
    context.user_data['awaiting_input'] = 'search_text'

# Обработчик команды /list
async def list_songs(update: Update, context: CallbackContext) -> None:
    try:
        results = get_all_songs()
        if results:
            for result in results:
                await update.message.reply_text(
                    f"Название: {result['title']}\nТекст: {result['text']}\nОбласть: {result['region']}"
                )
        else:
            await update.message.reply_text('В базе данных нет песен.')
    except Exception as e:
        logger.error(f"Ошибка при получении списка песен: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text
    if 'awaiting_input' not in context.user_data:
        await update.message.reply_text("Используйте команды для взаимодействия с ботом.")
        return

    try:
        if context.user_data['awaiting_input'] == 'add_song':
            title, text, region = map(str.strip, user_input.split(",", 2))
            add_song(title, text, region)
            await update.message.reply_text('Песня успешно добавлена!')
        elif context.user_data['awaiting_input'] == 'search_title':
            results = search_by_title(user_input)
            if results:
                for result in results:
                    await update.message.reply_text(
                        f"Название: {result['title']}\nТекст: {result['text']}\nОбласть: {result['region']}"
                    )
            else:
                await update.message.reply_text('Ничего не найдено.')
        elif context.user_data['awaiting_input'] == 'search_text':
            results = search_by_text(user_input)
            if results:
                for result in results:
                    await update.message.reply_text(
                        f"Название: {result['title']}\nТекст: {result['text']}\nОбласть: {result['region']}"
                    )
            else:
                await update.message.reply_text('Ничего не найдено.')
    except ValueError:
        await update.message.reply_text("Неверный формат ввода. Попробуйте снова.")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
    finally:
        context.user_data['awaiting_input'] = None

# Основная функция
def main():
    # Инициализация базы данных
    init_db()

    # Вставьте сюда свой токен
    application = Application.builder().token("7419619496:AAGcipjLK1nvQWpmW1JgivJAZcNQen6OqiE").build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("search_title", search_title))
    application.add_handler(CommandHandler("search_text", search_text))
    application.add_handler(CommandHandler("list", list_songs))

    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    application.run_polling()

# Запуск приложения
if __name__ == '__main__':
    main()