import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from env import API_TOKEN
from database import init_db, get_db, add_song, get_all_songs, get_songs_by_region, search_by_title, search_by_text, get_song_by_id

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
init_db()

# Обработчик команды /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Привет!Используй команды:\n'
        '/add - добавить песню\n'
        '/search_title - найти по названию\n'
        '/search_text - найти по тексту\n'
        '/list - показать все песни\n'
        '/list_by_region - показать песни по области\n'
        '/h - справка'
    )

# Обработчик команды /add
async def add(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни:')
    context.user_data['awaiting_input'] = 'awaiting_title'

# Обработчик команды /search_title
async def search_title(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите часть названия песни для поиска:')
    context.user_data['awaiting_input'] = 'search_title'

# Обработчик команды /search_text
async def search_text(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите текст песни для поиска:')
    context.user_data['awaiting_input'] = 'search_text'

# Обработчик команды /list
async def list_songs(update: Update, context: CallbackContext) -> None:
    db = next(get_db())
    try:
        results = get_all_songs(db)
        if results:
            # Создаем список кнопок с названиями песен
            keyboard = [
                [InlineKeyboardButton(result.title, callback_data=f"song_{result.id}")]
                for result in results
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Список песен:", reply_markup=reply_markup)
        else:
            await update.message.reply_text('В базе данных нет песен.\n /start')
    except Exception as e:
        logger.error(f"Ошибка при получении списка песен: {e} \n /start")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже. \n /start")

# Обработчик команды /list_by_region
async def list_by_region(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите область для поиска песен:')
    context.user_data['awaiting_input'] = 'awaiting_region'

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text

    if 'awaiting_input' not in context.user_data:
        await update.message.reply_text("Используйте команды для взаимодействия с ботом.")
        return

    try:
        if context.user_data['awaiting_input'] == 'awaiting_title':
            # Сохраняем название песни
            context.user_data['title'] = user_input
            await update.message.reply_text('Введите область:')
            context.user_data['awaiting_input'] = 'awaiting_region'

        elif context.user_data['awaiting_input'] == 'awaiting_region':
            # Сохраняем область
            context.user_data['region'] = user_input
            await update.message.reply_text('Отправьте текст песни:')
            context.user_data['awaiting_input'] = 'awaiting_text'

        elif context.user_data['awaiting_input'] == 'awaiting_text':
            # Сохраняем текст песни
            context.user_data['text'] = user_input
            await save_song(update, context)  # Функция для сохранения песни

        elif context.user_data['awaiting_input'] == 'search_title':
            # Поиск по части названия
            db = next(get_db())
            results = search_by_title(db, user_input)
            if results:
                # Создаем список кнопок с названиями песен
                keyboard = [
                    [InlineKeyboardButton(result.title, callback_data=f"song_{result.id}")]
                    for result in results
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"Найдены песни по запросу '{user_input}':",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(f"По запросу '{user_input}' ничего не найдено.\n /start")
            context.user_data['awaiting_input'] = None

        elif context.user_data['awaiting_input'] == 'search_text':
            # Поиск по тексту
            db = next(get_db())
            results = search_by_text(db, user_input)
            if results:
                # Создаем список кнопок с названиями песен
                keyboard = [
                    [InlineKeyboardButton(result.title, callback_data=f"song_{result.id}")]
                    for result in results
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"Найдены песни по запросу '{user_input}':",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(f"По запросу '{user_input}' ничего не найдено.\n /start")
            context.user_data['awaiting_input'] = None

        elif context.user_data['awaiting_input'] == 'awaiting_region':
            # Поиск песен по области
            db = next(get_db())
            results = get_songs_by_region(db, user_input)
            if results:
                # Создаем список кнопок с названиями песен
                keyboard = [
                    [InlineKeyboardButton(result.title, callback_data=f"song_{result.id}")]
                    for result in results
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"Список песен в области '{user_input}':",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(f"В области '{user_input}' нет песен.\n /start")
            context.user_data['awaiting_input'] = None

    except ValueError:
        await update.message.reply_text("Неверный формат ввода. Попробуйте снова.\n /start")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e} \n /start", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.\n /start")
        context.user_data.clear()  # Очищаем состояние в случае ошибки

# Функция для сохранения песни
async def save_song(update: Update, context: CallbackContext) -> None:
    db = next(get_db())
    try:
        title = context.user_data['title']
        region = context.user_data['region']
        text = context.user_data.get('text')
        song = add_song(db, title=title, region=region, text=text)
        await update.message.reply_text(f'Песня "{title}" успешно добавлена!')
        context.user_data.clear()  # Очищаем состояние
    except Exception as e:
        logger.error(f"Ошибка при сохранении песни: {e}\n /start")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.\n /start")
        context.user_data.clear()

# Обработчик нажатий на кнопки
async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()  # Ответим на callback, чтобы убрать "часики" на кнопке

    # Извлекаем ID песни из callback_data
    song_id = int(query.data.split("_")[1])

    db = next(get_db())
    try:
        # Ищем песню по ID
        song = get_song_by_id(db, song_id)
        if song:
            await query.edit_message_text(
                f"Название: {song.title}\nТекст: {song.text}\nОбласть: {song.region}\n /start"
            )
        else:
            await query.edit_message_text("Песня не найдена.")
    except Exception as e:
        logger.error(f"Ошибка при получении текста песни: {e}")
        await query.edit_message_text("Произошла ошибка. Попробуйте позже.")

# Основная функция
def main():
    # Создание приложения и передача токена
    application = Application.builder().token(API_TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("h", start))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("search_title", search_title))
    application.add_handler(CommandHandler("search_text", search_text))
    application.add_handler(CommandHandler("list", list_songs))
    application.add_handler(CommandHandler("list_by_region", list_by_region))

    # Регистрация обработчиков текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Регистрация обработчика нажатий на кнопки
    application.add_handler(CallbackQueryHandler(button_callback))

    # Запуск бота
    application.run_polling()

# Запуск приложения
if __name__ == '__main__':
    main()