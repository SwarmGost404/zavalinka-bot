import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    MenuButtonCommands
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler
)
from env import API_TOKEN
from database import (
    init_db, get_db, add_song, get_all_songs,
    get_songs_by_region, search_by_title,
    search_by_text, get_song_by_id
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
init_db()

def parse_region(region_str):
    """Разбирает строку региона на категорию и место"""
    if not region_str:
        return "", ""
    
    if '|' in region_str:
        parts = region_str.split('|')
        category = parts[0]
        place = parts[1] if len(parts) > 1 else ""
        if place.strip() in ("", "."):
            return category, ""
        return category, place
    return region_str, ""

async def setup_commands(application: Application):
    """Настраивает команды бота для меню"""
    commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("add", "Добавить новую песню"),
        BotCommand("search_title", "Поиск по названию"),
        BotCommand("search_text", "Поиск по тексту"),
        BotCommand("search_place", "Поиск по месту"),
        BotCommand("search_category", "Поиск по категории"),
        BotCommand("all", "Список всех песен"),
        BotCommand("help", "Помощь и инструкции")
    ]
    await application.bot.set_my_commands(commands)
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

async def start_command(update: Update, context: CallbackContext):
    """Отправляет приветственное сообщение с доступными командами"""
    help_text = (
        "Этнографический архив песен\n\n"
        "Доступные команды:\n\n"
        "/add - Добавить новую песню\n"
        "/search_title - Поиск по названию\n"
        "/search_text - Поиск по тексту\n"
        "/search_place - Поиск по месту записи\n"
        "/search_category - Поиск по категории\n"
        "/all - Список всех песен\n"
        "/help - Помощь и инструкции\n\n"
        "Вы можете нажать на любую команду, чтобы быстро использовать эту команду\n"
        "Все команды выделяются синим"
    )
    await update.message.reply_text(help_text)

async def help_command(update: Update, context: CallbackContext) -> None:
    """Отправляет справочное сообщение с подробной информацией о командах"""
    help_text = (
        "Этнографический архив песен\n\n"
        "Связь с создателем: @SwarmGost\n\n"
        "Информация про бота: @zavalinkaChannel \n"
        "Доступные команды:\n\n"
        "/start - Начать работу с ботом\n"
        "/add - Добавить новую песню в архив\n"
        "/search_title - Поиск песен по названию\n"
        "/search_text - Поиск песен по тексту\n"
        "/search_place - Поиск песен по месту записи\n"
        "/search_category - Поиск песен по категории\n"
        "/all - Просмотр всего архива\n"
        "/help - Эта справка\n\n"
        "Вы можете нажать на любую команду, чтобы быстро использовать эту команду\n"
        "Все команды выделяются синим"
    )
    await update.message.reply_text(help_text)

async def add_song_handler(update: Update, context: CallbackContext) -> None:
    """Начинает процесс добавления песни"""
    await update.message.reply_text('Введите название песни:')
    context.user_data['awaiting_input'] = 'awaiting_title'

async def search_title_handler(update: Update, context: CallbackContext) -> None:
    """Обрабатывает поиск по названию"""
    await update.message.reply_text('Введите название песни для поиска:')
    context.user_data['awaiting_input'] = 'search_title'

async def search_text_handler(update: Update, context: CallbackContext) -> None:
    """Обрабатывает поиск по тексту"""
    await update.message.reply_text('Введите текст песни для поиска:')
    context.user_data['awaiting_input'] = 'search_text'

async def search_place_handler(update: Update, context: CallbackContext) -> None:
    """Обрабатывает поиск по месту записи"""
    await update.message.reply_text('Введите место записи для поиска:')
    context.user_data['awaiting_input'] = 'search_place'

async def search_category_handler(update: Update, context: CallbackContext) -> None:
    """Обрабатывает поиск по категории"""
    await update.message.reply_text('Введите категорию для поиска:')
    context.user_data['awaiting_input'] = 'search_category'

async def list_songs_handler(update: Update, context: CallbackContext) -> None:
    """Выводит список всех песен с инлайн-кнопками"""
    db = next(get_db())
    try:
        results = get_all_songs(db)
        if results:
            keyboard = []
            for song in results:
                category, place = parse_region(song.region)
                button_text = f"{song.title}"
                if place:
                    button_text += f" ({place})"
                
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"song_{song.id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Все песни в архиве:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("В архиве пока нет песен.")
    except Exception as e:
        logger.error(f"Ошибка при получении списка песен: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
    finally:
        db.close()

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Обрабатывает все некомандные сообщения в зависимости от текущего состояния"""
    if 'awaiting_input' not in context.user_data:
        await update.message.reply_text("Используйте команды для взаимодействия с ботом. /help - для списка команд")
        return

    user_input = update.message.text

    try:
        if context.user_data['awaiting_input'] == 'awaiting_title':
            context.user_data['title'] = user_input
            await update.message.reply_text('Введите категорию:')
            context.user_data['awaiting_input'] = 'awaiting_region'

        elif context.user_data['awaiting_input'] == 'awaiting_region':
            context.user_data['region'] = user_input
            await update.message.reply_text('Введите место записи (например, "Село Вятское Ярославской области"), или точку (.), если не нужно:')
            context.user_data['awaiting_input'] = 'awaiting_place'

        elif context.user_data['awaiting_input'] == 'awaiting_place':
            if user_input.strip() in ("", "."):
                context.user_data['place'] = ""
            else:
                context.user_data['place'] = user_input
            await update.message.reply_text('Отправьте текст песни:')
            context.user_data['awaiting_input'] = 'awaiting_text'

        elif context.user_data['awaiting_input'] == 'awaiting_text':
            context.user_data['text'] = user_input
            await save_song(update, context)

        elif context.user_data['awaiting_input'] == 'search_title':
            db = next(get_db())
            results = search_by_title(db, user_input)
            await display_results(update, results, f"по названию '{user_input}'", context)

        elif context.user_data['awaiting_input'] == 'search_text':
            db = next(get_db())
            results = search_by_text(db, user_input)
            await display_results(update, results, f"по тексту '{user_input}'", context)

        elif context.user_data['awaiting_input'] == 'search_place':
            db = next(get_db())
            results = [song for song in get_all_songs(db) 
                      if '|' in song.region and user_input.lower() in song.region.lower().split('|')[1]]
            await display_results(update, results, f"по месту записи '{user_input}'", context)

        elif context.user_data['awaiting_input'] == 'search_category':
            db = next(get_db())
            results = get_songs_by_region(db, user_input)
            await display_results(update, results, f"в категории '{user_input}'", context)

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        context.user_data.clear()

async def display_results(update: Update, results, search_description, context: CallbackContext):
    """Отображает результаты поиска с инлайн-кнопками"""
    if results:
        keyboard = []
        for song in results:
            category, place = parse_region(song.region)
            button_text = f"{song.title}"
            if place:
                button_text += f" ({place})"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"song_{song.id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Найдены песни {search_description}:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(f"По запросу {search_description} ничего не найдено.")

async def save_song(update: Update, context: CallbackContext) -> None:
    """Сохраняет песню в базу данных"""
    db = next(get_db())
    try:
        title = context.user_data['title']
        region = context.user_data['region']
        place = context.user_data.get('place', '')
        text = context.user_data.get('text', '')
        
        if place.strip() in ("", "."):
            full_region = region
        else:
            full_region = f"{region}|{place}"
        
        song = add_song(db, title=title, region=full_region, text=text)
        
        response_message = (
            f'Песня добавлена!\n\n'
            f'Название: {title}\n'
            f'Категория: {region}\n'
        )
        if place:
            response_message += f'Место записи: {place}\n'
        
        response_message += '\nИспользуйте /help для списка команд'
        
        await update.message.reply_text(response_message)
        context.user_data.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении песни: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
    finally:
        db.close()

async def button_callback(update: Update, context: CallbackContext) -> None:
    """Обрабатывает нажатия инлайн-кнопок для отображения деталей песни"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('song_'):
        song_id = int(query.data.split("_")[1])
        db = next(get_db())
        try:
            song = get_song_by_id(db, song_id)
            if song:
                category, place = parse_region(song.region)
                response_text = (
                    f"Детали песни\n\n"
                    f"Название: {song.title}\n"
                    f"Категория: {category}\n"
                )
                if place:
                    response_text += f"Место записи: {place}\n\n"
                
                response_text += f"Текст:\n{song.text}\n\n"
                response_text += "Используйте /help для списка команд"
                
                await query.edit_message_text(response_text)
            else:
                await query.edit_message_text("Песня не найдена")
        except Exception as e:
            logger.error(f"Ошибка при получении текста песни: {e}")
            await query.edit_message_text("Произошла ошибка. Попробуйте позже.")
        finally:
            db.close()

def main():
    """Запускает бота со всеми обработчиками"""
    application = Application.builder().token(API_TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_song_handler))
    application.add_handler(CommandHandler("search_title", search_title_handler))
    application.add_handler(CommandHandler("search_text", search_text_handler))
    application.add_handler(CommandHandler("search_place", search_place_handler))
    application.add_handler(CommandHandler("search_category", search_category_handler))
    application.add_handler(CommandHandler("all", list_songs_handler))

    # Регистрация обработчика сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Регистрация обработчика колбэков
    application.add_handler(CallbackQueryHandler(button_callback))

    # Настройка меню команд
    application.post_init = setup_commands

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()