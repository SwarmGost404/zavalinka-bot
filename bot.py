import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from database import init_db, get_db, add_song, get_all_songs, get_songs_by_region, search_by_title, search_by_text
from env import API_TOKEN

# Папка для хранения аудиофайлов
AUDIO_FOLDER = "audio_files"
if not os.path.exists(AUDIO_FOLDER):
    os.makedirs(AUDIO_FOLDER)

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
        'Привет! Я бот для хранения текстов и аудиозаписей песен. Используй команды:\n'
        '/add - добавить песню\n'
        '/search_title - найти по названию\n'
        '/search_text - найти по тексту\n'
        '/list - показать все песни\n'
        '/list_by_region - показать песни по области'
    )

# Обработчик команды /add
async def add(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни:')
    context.user_data['awaiting_input'] = 'awaiting_title'

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
    db = next(get_db())
    try:
        results = get_all_songs(db)
        if results:
            # Выводим только названия песен
            songs_list = "\n".join([result.title for result in results])
            await update.message.reply_text(
                f"Список песен:\n{songs_list}\n\n"
                "Отправьте название песни, чтобы увидеть её текст или аудиозапись."
            )
            # Сохраняем список песен в контексте
            context.user_data['songs_list'] = {
                result.title: (result.text, result.audio_file, result.region)
                for result in results
            }
        else:
            await update.message.reply_text('В базе данных нет песен.')
    except Exception as e:
        logger.error(f"Ошибка при получении списка песен: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

# Обработчик команды /list_by_region
async def list_by_region(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите область для поиска песен:')
    context.user_data['awaiting_input'] = 'awaiting_region'

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text

    # Если пользователь выбирает песню из списка
    if 'songs_list' in context.user_data and user_input in context.user_data['songs_list']:
        text, audio_file, region = context.user_data['songs_list'][user_input]
        if audio_file:
            await update.message.reply_audio(audio=open(audio_file, 'rb'))
        elif text:
            await update.message.reply_text(f"Текст песни '{user_input}' (Область: {region}):\n{text}")
        else:
            await update.message.reply_text(f"Песня '{user_input}' не содержит текста или аудиозаписи.")
        context.user_data.pop('songs_list')  # Очищаем список песен
        return

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
            await update.message.reply_text(
                'Отправьте текст песни или аудиозапись (голосовое сообщение или файл):'
            )
            context.user_data['awaiting_input'] = 'awaiting_content'

        elif context.user_data['awaiting_input'] == 'search_title':
            # Поиск по названию
            db = next(get_db())
            results = search_by_title(db, user_input)
            if results:
                for result in results:
                    if result.audio_file:
                        await update.message.reply_audio(audio=open(result.audio_file, 'rb'))
                    elif result.text:
                        await update.message.reply_text(
                            f"Название: {result.title}\nТекст: {result.text}\nОбласть: {result.region}"
                        )
                    else:
                        await update.message.reply_text(f"Песня '{result.title}' не содержит текста или аудиозаписи.")
            else:
                await update.message.reply_text('Ничего не найдено.')
            context.user_data['awaiting_input'] = None

        elif context.user_data['awaiting_input'] == 'search_text':
            # Поиск по тексту
            db = next(get_db())
            results = search_by_text(db, user_input)
            if results:
                for result in results:
                    if result.audio_file:
                        await update.message.reply_audio(audio=open(result.audio_file, 'rb'))
                    elif result.text:
                        await update.message.reply_text(
                            f"Название: {result.title}\nТекст: {result.text}\nОбласть: {result.region}"
                        )
                    else:
                        await update.message.reply_text(f"Песня '{result.title}' не содержит текста или аудиозаписи.")
            else:
                await update.message.reply_text('Ничего не найдено.')
            context.user_data['awaiting_input'] = None

        elif context.user_data['awaiting_input'] == 'awaiting_region':
            # Поиск песен по области
            db = next(get_db())
            results = get_songs_by_region(db, user_input)
            if results:
                # Выводим только названия песен
                songs_list = "\n".join([result.title for result in results])
                await update.message.reply_text(
                    f"Список песен в области '{user_input}':\n{songs_list}\n\n"
                    "Отправьте название песни, чтобы увидеть её текст или аудиозапись."
                )
                # Сохраняем список песен в контексте
                context.user_data['songs_list'] = {
                    result.title: (result.text, result.audio_file, result.region)
                    for result in results
                }
            else:
                await update.message.reply_text(f"В области '{user_input}' нет песен.")
            context.user_data['awaiting_input'] = None

    except ValueError:
        await update.message.reply_text("Неверный формат ввода. Попробуйте снова.")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        context.user_data.clear()  # Очищаем состояние в случае ошибки

# Обработчик голосовых сообщений и аудиофайлов
async def handle_audio(update: Update, context: CallbackContext) -> None:
    if 'awaiting_input' not in context.user_data or context.user_data['awaiting_input'] != 'awaiting_content':
        await update.message.reply_text("Используйте команды для взаимодействия с ботом.")
        return

    try:
        # Получаем аудиофайл
        if update.message.voice:
            audio_file = await update.message.voice.get_file()
        elif update.message.audio:
            audio_file = await update.message.audio.get_file()
        else:
            await update.message.reply_text("Пожалуйста, отправьте голосовое сообщение или аудиофайл.")
            return

        # Сохраняем аудиофайл на сервере
        file_path = os.path.join(AUDIO_FOLDER, f"{context.user_data['title']}.mp3")
        await audio_file.download_to_drive(file_path)

        # Добавляем песню в базу данных
        db = next(get_db())
        add_song(db, title=context.user_data['title'], region=context.user_data['region'], audio_file=file_path)
        await update.message.reply_text('Песня успешно добавлена!')
        # Очищаем состояние
        context.user_data.clear()

    except Exception as e:
        logger.error(f"Ошибка при обработке аудио: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        context.user_data.clear()  # Очищаем состояние в случае ошибки

# Основная функция
def main():
    # Создание приложения и передача токена
    application = Application.builder().token(API_TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("search_title", search_title))
    application.add_handler(CommandHandler("search_text", search_text))
    application.add_handler(CommandHandler("list", list_songs))
    application.add_handler(CommandHandler("list_by_region", list_by_region))

    # Регистрация обработчиков текстовых сообщений и аудио
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))

    # Запуск бота
    application.run_polling()

# Запуск приложения
if __name__ == '__main__':
    main()