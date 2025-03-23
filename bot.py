import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from env import API_TOKEN
from database import (
    init_db, get_db, add_song, get_all_songs, get_songs_by_category,
    get_songs_by_place, search_by_title, search_by_text, get_song_by_id,
    update_song_place, update_song_audio
)

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
        'Привет! Я хранитель текстов этнографических песен \n'
        'Используй команды:\n'
        '/add - добавить песню\n'
        '/search_title - найти по названию\n'
        '/search_text - найти по тексту\n'
        '/list - найти все песни\n'
        '/list_by_category - найти песни по категории\n'
        '/list_by_place - найти песни по месту записи\n'
        '/update_place - обновить место записи\n'
        '/update_audio - обновить аудиозапись\n'
        '/help - справка'
    )

# Обработчик команды /help
async def help(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Привет! Я хранитель текстов этнографических песен \n'
        'Я (Создатель бота) хочу развивать удобство и получение народных песен (И вообще всей народной культуры) Я сделал этого бота на свои деньги и своими руками (Надеюсь вам понравится) Связь со мной @SwarmGost\n'
        'Сейчас я подробно расскажу про команды:\n'
        '/add - добавить песню\n'
        '/search_title - найти по названию\n'
        '/search_text - найти по тексту\n'
        '/list - найти все песни\n'
        '/list_by_category - найти песни по категории\n'
        '/list_by_place - найти песни по месту записи\n'
        '/update_place - обновить место записи\n'
        '/update_audio - обновить аудиозапись\n'
        '/help - справка'
    )

# Обработчик команды /add
async def add(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни:')
    context.user_data['awaiting_input'] = 'awaiting_title'

# Обработчик команды /search_title
async def search_title(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни:')
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

# Обработчик команды /list_by_category
async def list_by_category(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите категорию:')
    context.user_data['awaiting_input'] = 'awaiting_category'

# Обработчик команды /list_by_place
async def list_by_place(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите место записи:')
    context.user_data['awaiting_input'] = 'awaiting_place'

# Обработчик команды /update_place
async def update_place(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите ID песни, для которой хотите обновить место записи:')
    context.user_data['awaiting_input'] = 'awaiting_song_id_for_place'

# Обработчик команды /update_audio
async def update_audio(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите ID песни, для которой хотите обновить аудиозапись:')
    context.user_data['awaiting_input'] = 'awaiting_song_id_for_audio'

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
            await update.message.reply_text('Введите категорию:')
            context.user_data['awaiting_input'] = 'awaiting_category'

        elif context.user_data['awaiting_input'] == 'awaiting_category':
            # Сохраняем категорию
            context.user_data['category'] = user_input
            await update.message.reply_text('Введите место записи:')
            context.user_data['awaiting_input'] = 'awaiting_place'

        elif context.user_data['awaiting_input'] == 'awaiting_place':
            # Сохраняем место записи
            context.user_data['place'] = user_input
            await update.message.reply_text('Отправьте текст песни:')
            context.user_data['awaiting_input'] = 'awaiting_text'

        elif context.user_data['awaiting_input'] == 'awaiting_text':
            # Сохраняем текст песни
            context.user_data['text'] = user_input
            await update.message.reply_text('Отправьте аудиозапись песни (или любое сообщение, чтобы пропустить):')
            context.user_data['awaiting_input'] = 'awaiting_audio'

        elif context.user_data['awaiting_input'] == 'awaiting_audio':
            # Сохраняем аудиозапись (или NULL, если отправлено текстовое сообщение)
            if update.message.audio:
                audio_file = await update.message.audio.get_file()
                audio_bytes = await audio_file.download_as_bytearray()
                await save_song(update, context, audio_bytes)
            else:
                await save_song(update, context, None)  # Сохраняем NULL, если аудио не отправлено
                await update.message.reply_text("Аудиозапись не добавлена.")

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

        elif context.user_data['awaiting_input'] == 'awaiting_category':
            # Поиск песен по категории
            db = next(get_db())
            results = get_songs_by_category(db, user_input)
            if results:
                # Создаем список кнопок с названиями песен
                keyboard = [
                    [InlineKeyboardButton(result.title, callback_data=f"song_{result.id}")]
                    for result in results
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"Список песен в категории '{user_input}':",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(f"В категории '{user_input}' нет песен.\n /start")
            context.user_data['awaiting_input'] = None

        elif context.user_data['awaiting_input'] == 'awaiting_place':
            # Поиск песен по месту записи
            db = next(get_db())
            results = get_songs_by_place(db, user_input)
            if results:
                # Создаем список кнопок с названиями песен
                keyboard = [
                    [InlineKeyboardButton(result.title, callback_data=f"song_{result.id}")]
                    for result in results
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"Список песен с местом записи '{user_input}':",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(f"С местом записи '{user_input}' нет песен.\n /start")
            context.user_data['awaiting_input'] = None

        elif context.user_data['awaiting_input'] == 'awaiting_song_id_for_place':
            # Сохраняем ID песни для обновления места записи
            context.user_data['song_id'] = int(user_input)
            await update.message.reply_text('Введите новое место записи:')
            context.user_data['awaiting_input'] = 'awaiting_new_place'

        elif context.user_data['awaiting_input'] == 'awaiting_new_place':
            # Обновляем место записи
            db = next(get_db())
            song_id = context.user_data['song_id']
            new_place = user_input
            updated_song = update_song_place(db, song_id=song_id, new_place=new_place)
            await update.message.reply_text(f"Место записи для песни '{updated_song.title}' обновлено на '{new_place}'.")
            context.user_data.clear()

        elif context.user_data['awaiting_input'] == 'awaiting_song_id_for_audio':
            # Сохраняем ID песни для обновления аудиозаписи
            context.user_data['song_id'] = int(user_input)
            await update.message.reply_text('Отправьте новую аудиозапись:')
            context.user_data['awaiting_input'] = 'awaiting_new_audio'

        elif context.user_data['awaiting_input'] == 'awaiting_new_audio':
            # Обновляем аудиозапись
            if update.message.audio:
                audio_file = await update.message.audio.get_file()
                audio_bytes = await audio_file.download_as_bytearray()
                db = next(get_db())
                updated_song = update_song_audio(db, song_id=context.user_data['song_id'], audio_file=audio_bytes)
                await update.message.reply_text(f"Аудиозапись для песни '{updated_song.title}' обновлена.")
            else:
                await update.message.reply_text("Пожалуйста, отправьте аудиозапись.")
                return
            context.user_data.clear()

    except ValueError:
        await update.message.reply_text("Неверный формат ввода. Попробуйте снова.\n /start")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e} \n /start", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.\n /start")
        context.user_data.clear()  # Очищаем состояние в случае ошибки

# Функция для сохранения песни
async def save_song(update: Update, context: CallbackContext, audio_bytes: bytes = None) -> None:
    db = next(get_db())
    try:
        title = context.user_data['title']
        category = context.user_data['category']
        place = context.user_data['place']
        text = context.user_data.get('text')
        song = add_song(db, title=title, category=category, place=place, text=text, audio_file=audio_bytes)
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
            # Разделяем region на категорию и место записи
            category, place = song.region.split("@@")
            await query.edit_message_text(
                f"Название: {song.title}\n\nКатегория: {category}\n\nМесто записи: {place}\n\nТекст:\n{song.text}\n /start"
            )
            if song.audio_file:
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=song.audio_file)
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
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("search_title", search_title))
    application.add_handler(CommandHandler("search_text", search_text))
    application.add_handler(CommandHandler("list", list_songs))
    application.add_handler(CommandHandler("list_by_category", list_by_category))
    application.add_handler(CommandHandler("list_by_place", list_by_place))
    application.add_handler(CommandHandler("update_place", update_place))
    application.add_handler(CommandHandler("update_audio", update_audio))

    # Регистрация обработчиков текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Регистрация обработчика аудиозаписей
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))

    # Регистрация обработчика нажатий на кнопки
    application.add_handler(CallbackQueryHandler(button_callback))

    # Запуск бота
    application.run_polling()

# Обработчик аудиозаписей
async def handle_audio(update: Update, context: CallbackContext) -> None:
    if 'awaiting_input' in context.user_data and context.user_data['awaiting_input'] == 'awaiting_audio':
        audio_file = await update.message.audio.get_file()
        audio_bytes = await audio_file.download_as_bytearray()
        await save_song(update, context, audio_bytes)
    elif 'awaiting_input' in context.user_data and context.user_data['awaiting_input'] == 'awaiting_new_audio':
        audio_file = await update.message.audio.get_file()
        audio_bytes = await audio_file.download_as_bytearray()
        db = next(get_db())
        updated_song = update_song_audio(db, song_id=context.user_data['song_id'], audio_file=audio_bytes)
        await update.message.reply_text(f"Аудиозапись для песни '{updated_song.title}' обновлена.")
        context.user_data.clear()
    else:
        await update.message.reply_text("Пожалуйста, используйте команду /add или /update_audio для добавления аудиозаписи.")

# Запуск приложения
if __name__ == '__main__':
    main()