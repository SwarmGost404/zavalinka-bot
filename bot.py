import logging
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
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

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

def parse_region(region_str):
    """Parse region string into category and place"""
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

# Menu functions
async def show_main_menu(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton("Добавить песню")],
        [
            KeyboardButton("Поиск по названию"),
            KeyboardButton("Поиск по тексту")
        ],
        [
            KeyboardButton("Поиск по месту"),
            KeyboardButton("Список всех песен")
        ],
        [KeyboardButton("Поиск по категории")],
        [KeyboardButton("Помощь")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = "🎵 *Этнографический архив песен*\nВыберите действие:"
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "🎵 *Этнографический архив песен*\n\n"
        "Я (Создатель бота) хочу развивать удобство и получение народных песен. "
        "Я сделал этого бота на свои деньги и своими руками. Связь со мной @SwarmGost\n\n"
        "*Используйте кнопки меню для работы:*\n\n"
        "• *Добавить песню* - новая запись в архив\n"
        "• *Поиск по названию* - найти песни по названию\n"
        "• *Поиск по тексту* - найти по тексту песни\n"
        "• *Поиск по месту* - найти по месту записи\n"
        "• *Список всех песен* - просмотр всего архива\n"
        "• *Поиск по категории* - найти по категории\n\n"
        "Для возврата в главное меню используйте команду /start"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def add_song_handler(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни:')
    context.user_data['awaiting_input'] = 'awaiting_title'

async def search_title_handler(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни для поиска:')
    context.user_data['awaiting_input'] = 'search_title'

async def search_text_handler(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите текст песни для поиска:')
    context.user_data['awaiting_input'] = 'search_text'

async def search_place_handler(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите место записи для поиска:')
    context.user_data['awaiting_input'] = 'search_place'

async def list_songs_handler(update: Update, context: CallbackContext) -> None:
    db = next(get_db())
    try:
        results = get_all_songs(db)
        if results:
            keyboard = []
            for result in results:
                category, place = parse_region(result.region)
                button_text = result.title
                if place:
                    button_text = f"{result.title} ({place})"
                
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"song_{result.id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "📋 *Список песен:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text('В базе данных нет песен.')
            await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Ошибка при получении списка песен: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        await show_main_menu(update, context)
    finally:
        db.close()

async def list_by_region_handler(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите категорию:')
    context.user_data['awaiting_input'] = 'awaiting_region'

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text

    # Handle menu buttons
    if user_input == "Добавить песню":
        await add_song_handler(update, context)
        return
    elif user_input == "Поиск по названию":
        await search_title_handler(update, context)
        return
    elif user_input == "Поиск по тексту":
        await search_text_handler(update, context)
        return
    elif user_input == "Поиск по месту":
        await search_place_handler(update, context)
        return
    elif user_input == "Список всех песен":
        await list_songs_handler(update, context)
        return
    elif user_input == "Поиск по категории":
        await list_by_region_handler(update, context)
        return
    elif user_input == "Помощь":
        await help_command(update, context)
        return

    if 'awaiting_input' not in context.user_data:
        await update.message.reply_text("Используйте меню для взаимодействия с ботом.")
        await show_main_menu(update, context)
        return

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
            await display_results(update, results, f"по названию '{user_input}'")

        elif context.user_data['awaiting_input'] == 'search_text':
            db = next(get_db())
            results = search_by_text(db, user_input)
            await display_results(update, results, f"по тексту '{user_input}'")

        elif context.user_data['awaiting_input'] == 'search_place':
            db = next(get_db())
            results = [song for song in get_all_songs(db) 
                      if '|' in song.region and user_input.lower() in song.region.lower().split('|')[1]]
            await display_results(update, results, f"по месту записи '{user_input}'")

        elif context.user_data['awaiting_input'] == 'awaiting_region':
            db = next(get_db())
            results = get_songs_by_region(db, user_input)
            await display_results(update, results, f"в категории '{user_input}'")

    except ValueError:
        await update.message.reply_text("Неверный формат ввода. Попробуйте снова.")
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        await show_main_menu(update, context)
    finally:
        if context.user_data['awaiting_input'] not in ['awaiting_title', 'awaiting_region', 'awaiting_place', 'awaiting_text']:
            context.user_data.clear()

async def display_results(update: Update, results, search_description):
    if results:
        keyboard = []
        for song in results:
            category, place = parse_region(song.region)
            button_text = song.title
            if place:
                button_text = f"{song.title} ({place})"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"song_{song.id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"🔍 *Результаты поиска {search_description}:*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ По запросу {search_description} ничего не найдено.")
    await show_main_menu(update, context)

async def save_song(update: Update, context: CallbackContext) -> None:
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
            f'🎵 *Песня добавлена!*\n\n'
            f'*Название:* {title}\n'
            f'*Категория:* {region}\n'
        )
        if place:
            response_message += f'*Место записи:* {place}\n'
        
        response_message += '\nДля продолжения используйте меню'
        
        await update.message.reply_text(response_message, parse_mode='Markdown')
        context.user_data.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении песни: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    finally:
        db.close()
        await show_main_menu(update, context)

async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    song_id = int(query.data.split("_")[1])
    db = next(get_db())
    
    try:
        song = get_song_by_id(db, song_id)
        if song:
            category, place = parse_region(song.region)
            response_text = (
                f"🎵 *Детали песни*\n\n"
                f"*Название:* {song.title}\n"
                f"*Категория:* {category}\n"
            )
            if place:
                response_text += f"*Место записи:* {place}\n\n"
            
            response_text += f"*Текст:*\n{song.text}\n\n"
            response_text += "Для продолжения используйте меню"
            
            await query.edit_message_text(
                response_text,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Песня не найдена")
    except Exception as e:
        logger.error(f"Ошибка при получении текста песни: {e}")
        await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    finally:
        db.close()

def main():
    application = Application.builder().token(API_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", show_main_menu))
    application.add_handler(CommandHandler("help", help_command))

    # Register message handlers for menu buttons
    application.add_handler(MessageHandler(filters.Text([
        "Добавить песню", "Поиск по названию", "Поиск по тексту",
        "Поиск по месту", "Список всех песен", "Поиск по категории", "Помощь"
    ]), handle_message))

    # Register other message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register callback handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()