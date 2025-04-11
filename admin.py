from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import logging
from database import (
    get_db, 
    delete_song, 
    update_song, 
    get_all_songs_with_id, 
    search_by_title,
    get_song_by_id,
    init_db
)
from env import ADMIN_API_TOKEN  # Убедитесь, что TELEGRAM_TOKEN указан в .env

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
init_db()

# Функция для получения сессии базы данных
def get_db_session():
    return next(get_db())

# Команда /start
def start(update: Update, context: CallbackContext):
    help_text = """
    Добро пожаловать в бот для работы с базой народных песен!

    Доступные команды:
    /list - Показать все песни с ID
    /search - Поиск песен по названию
    /delete - Удалить песню по ID
    /edit - Редактировать песню
    """
    update.message.reply_text(help_text)

# Команда /list - Показать все песни с ID
def list_songs(update: Update, context: CallbackContext):
    try:
        db = get_db_session()
        songs = get_all_songs_with_id(db)
        
        if not songs:
            update.message.reply_text("В базе нет песен.")
            return
            
        response = "Список всех песен:\n\n"
        for song in songs:
            response += (
                f"ID: {song['id']}\n"
                f"Название: {song['title']}\n"
                f"Регион: {song['region']}\n"
                f"Категория: {song.get('category', 'не указана')}\n"
                f"Текст: {song['text'][:50] + '...' if song['text'] else 'нет текста'}\n"
                "------------------------\n"
            )
            
        update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка при получении списка песен: {e}")
        update.message.reply_text("Произошла ошибка при получении списка песен.")

# Команда /search - Поиск по названию
def search_songs(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Пожалуйста, укажите название для поиска. Например: /search частушка")
        return
    
    search_query = " ".join(context.args)
    try:
        db = get_db_session()
        songs = search_by_title(db, search_query)
        
        if not songs:
            update.message.reply_text("Песни с таким названием не найдены.")
            return
            
        response = f"Результаты поиска по '{search_query}':\n\n"
        for song in songs:
            response += (
                f"ID: {song.id}\n"
                f"Название: {song.title}\n"
                f"Регион: {song.region}\n"
                "------------------------\n"
            )
            
        update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка при поиске песен: {e}")
        update.message.reply_text("Произошла ошибка при поиске песен.")

# Команда /delete - Удаление песни по ID
def delete_song_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Пожалуйста, укажите ID песни для удаления. Например: /delete 5")
        return
    
    try:
        song_id = int(context.args[0])
        db = get_db_session()
        
        # Проверяем существование песни перед удалением
        song = get_song_by_id(db, song_id)
        if not song:
            update.message.reply_text(f"Песня с ID {song_id} не найдена.")
            return
            
        if delete_song(db, song_id):
            update.message.reply_text(f"Песня с ID {song_id} успешно удалена.")
    except ValueError:
        update.message.reply_text("Пожалуйста, укажите корректный ID (целое число).")
    except Exception as e:
        logger.error(f"Ошибка при удалении песни: {e}")
        update.message.reply_text("Произошла ошибка при удалении песни.")

# Команда /edit - Редактирование песни
def edit_song(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Пожалуйста, укажите ID песни для редактирования. Например: /edit 5")
        return
    
    try:
        song_id = int(context.args[0])
        db = get_db_session()
        song = get_song_by_id(db, song_id)
        
        if not song:
            update.message.reply_text(f"Песня с ID {song_id} не найдена.")
            return
            
        # Создаем клавиатуру для выбора атрибута
        keyboard = [
            [InlineKeyboardButton("Название", callback_data=f"edit_title_{song_id}")],
            [InlineKeyboardButton("Текст", callback_data=f"edit_text_{song_id}")],
            [InlineKeyboardButton("Регион", callback_data=f"edit_region_{song_id}")],
            [InlineKeyboardButton("Категория", callback_data=f"edit_category_{song_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"Выберите атрибут песни (ID: {song_id}) для редактирования:",
            reply_markup=reply_markup
        )
        
        # Сохраняем ID песни в контексте пользователя
        context.user_data['editing_song_id'] = song_id
    except ValueError:
        update.message.reply_text("Пожалуйста, укажите корректный ID (целое число).")
    except Exception as e:
        logger.error(f"Ошибка при начале редактирования: {e}")
        update.message.reply_text("Произошла ошибка при начале редактирования.")

# Обработчик выбора атрибута для редактирования
def edit_attribute_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    data = query.data
    song_id = int(data.split('_')[-1])
    attribute = data.split('_')[1]
    
    # Сохраняем выбранный атрибут и ID песни в контексте пользователя
    context.user_data['editing_attribute'] = attribute
    context.user_data['editing_song_id'] = song_id
    
    query.edit_message_text(
        f"Введите новое значение для {attribute} песни с ID {song_id}:"
    )
    
    # Устанавливаем состояние ожидания ввода нового значения
    return 'waiting_for_new_value'

# Обработчик ввода нового значения атрибута
def save_new_attribute_value(update: Update, context: CallbackContext):
    user_data = context.user_data
    new_value = update.message.text
    
    if 'editing_attribute' not in user_data or 'editing_song_id' not in user_data:
        update.message.reply_text("Ошибка: не найден контекст редактирования.")
        return
    
    attribute = user_data['editing_attribute']
    song_id = user_data['editing_song_id']
    
    try:
        db = get_db_session()
        
        # Создаем словарь с обновляемыми полями
        update_data = {}
        if attribute == 'title':
            update_data['title'] = new_value
        elif attribute == 'text':
            update_data['text'] = new_value
        elif attribute == 'region':
            update_data['region'] = new_value
        elif attribute == 'category':
            update_data['category'] = new_value
            
        # Обновляем песню
        updated_song = update_song(db, song_id, **update_data)
        
        if updated_song:
            update.message.reply_text(
                f"Песня с ID {song_id} успешно обновлена!\n"
                f"Новое значение {attribute}: {new_value}"
            )
        else:
            update.message.reply_text("Не удалось обновить песню.")
            
    except Exception as e:
        logger.error(f"Ошибка при обновлении песни: {e}")
        update.message.reply_text("Произошла ошибка при обновлении песни.")
    
    # Очищаем контекст пользователя
    user_data.pop('editing_attribute', None)
    user_data.pop('editing_song_id', None)
    
    return -1  # Завершаем состояние FSM

# Обработчик ошибок
def error_handler(update: Update, context: CallbackContext):
    logger.error(msg="Ошибка в обработчике Telegram:", exc_info=context.error)
    if update.message:
        update.message.reply_text("Произошла ошибка при обработке вашего запроса.")

def main():
    # Создаем Updater и передаем ему токен
    updater = Updater(ADMIN_API_TOKEN)
    
    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher
    
    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("list", list_songs))
    dp.add_handler(CommandHandler("search", search_songs, pass_args=True))
    dp.add_handler(CommandHandler("delete", delete_song_command, pass_args=True))
    dp.add_handler(CommandHandler("edit", edit_song, pass_args=True))
    
    # Регистрируем обработчики CallbackQuery
    dp.add_handler(CallbackQueryHandler(edit_attribute_choice, pattern='^edit_.*'))
    
    # Регистрируем обработчик сообщений для ввода новых значений
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command,
        save_new_attribute_value,
        pass_user_data=True
    ))
    
    # Регистрируем обработчик ошибок
    dp.add_error_handler(error_handler)
    
    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()