import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from env import API_TOKEN
from database import init_db, get_db, add_song, get_all_songs, get_songs_by_region, search_by_title, search_by_text, get_song_by_id

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
        # Если место - это просто точка или пустое, возвращаем только категорию
        if place.strip() in ("", "."):
            return category, ""
        return category, place
    return region_str, ""

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Привет! Я хранитель текстов этнографических песен\n'
        'Используй команды:\n'
        '/add - добавить песню\n'
        '/search_title - найти по названию\n'
        '/search_text - найти по тексту\n'
        '/search_place - найти по месту записи\n'
        '/list - все песни\n'
        '/list_by_region - найти по категориям\n'
        '/help - справка'
    )

async def help(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Привет! Я хранитель текстов этнографических песен\n'
        'Я (Создатель бота) хочу развивать удобство и получение народных песен. '
        'Я сделал этого бота на свои деньги и своими руками. Связь со мной @SwarmGost\n\n'
        'Команды:\n'
        '/add - добавить песню (название, категория, место записи, текст)\n'
        '/search_title - найти по названию\n'
        '/search_text - найти по тексту\n'
        '/search_place - найти по месту записи\n'
        '/list - все песни\n'
        '/list_by_region - найти по категориям\n'
        '/help - справка'
    )

async def add(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни:')
    context.user_data['awaiting_input'] = 'awaiting_title'

async def search_title(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни:')
    context.user_data['awaiting_input'] = 'search_title'

async def search_text(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите текст песни для поиска:')
    context.user_data['awaiting_input'] = 'search_text'

async def search_place(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите место записи для поиска:')
    context.user_data['awaiting_input'] = 'search_place'

async def list_songs(update: Update, context: CallbackContext) -> None:
    db = next(get_db())
    try:
        results = get_all_songs(db)
        if results:
            keyboard = []
            for result in results:
                category, place = parse_region(result.region)
                # Формируем текст кнопки без скобок, если место пустое
                button_text = result.title
                if place:
                    button_text = f"{result.title} ({place})"
                
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"song_{result.id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Список песен:", reply_markup=reply_markup)
        else:
            await update.message.reply_text('В базе данных нет песен.\n/start')
    except Exception as e:
        logger.error(f"Ошибка при получении списка песен: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.\n/start")

async def list_by_region(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите категорию:')
    context.user_data['awaiting_input'] = 'awaiting_region'

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text

    if 'awaiting_input' not in context.user_data:
        await update.message.reply_text("Используйте команды для взаимодействия с ботом.")
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
            # Если пользователь ввел точку или пустую строку, не добавляем место
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
            # Search for place in the region field (after | separator)
            results = [song for song in get_all_songs(db) 
                      if '|' in song.region and user_input.lower() in song.region.lower().split('|')[1]]
            await display_results(update, results, f"по месту записи '{user_input}'")

        elif context.user_data['awaiting_input'] == 'awaiting_region':
            db = next(get_db())
            results = get_songs_by_region(db, user_input)
            await display_results(update, results, f"в категории '{user_input}'")

    except ValueError:
        await update.message.reply_text("Неверный формат ввода. Попробуйте снова.\n/start")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.\n/start")
    finally:
        if context.user_data['awaiting_input'] not in ['awaiting_title', 'awaiting_region', 'awaiting_place', 'awaiting_text']:
            context.user_data.clear()

async def display_results(update: Update, results, search_description):
    if results:
        keyboard = []
        for song in results:
            category, place = parse_region(song.region)
            # Формируем текст кнопки без скобок, если место пустое
            button_text = song.title
            if place:
                button_text = f"{song.title} ({place})"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"song_{song.id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Найдены песни {search_description}:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(f"По запросу {search_description} ничего не найдено.\n/start")

async def save_song(update: Update, context: CallbackContext) -> None:
    db = next(get_db())
    try:
        title = context.user_data['title']
        region = context.user_data['region']
        place = context.user_data.get('place', '')
        text = context.user_data.get('text', '')
        
        # Если место не указано или это точка, сохраняем только категорию
        if place.strip() in ("", "."):
            full_region = region
        else:
            full_region = f"{region}|{place}"
        
        song = add_song(db, title=title, region=full_region, text=text)
        
        # Формируем сообщение без места, если оно не указано
        response_message = f'Песня "{title}" успешно добавлена!\nКатегория: {region}\n'
        if place:
            response_message += f'Место записи: {place}\n'
        response_message += '/start'
        
        await update.message.reply_text(response_message)
        context.user_data.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении песни: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.\n/start")
        context.user_data.clear()

async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    song_id = int(query.data.split("_")[1])
    db = next(get_db())
    
    try:
        song = get_song_by_id(db, song_id)
        if song:
            category, place = parse_region(song.region)
            response_text = f"Название: {song.title}\n\nКатегория: {category}\n\n"
            if place:
                response_text += f"Место записи: {place}\n\n"
            response_text += f"Текст:\n{song.text}\n\n/start"
            
            await query.edit_message_text(response_text)
        else:
            await query.edit_message_text("Песня не найдена.\n/start")
    except Exception as e:
        logger.error(f"Ошибка при получении текста песни: {e}")
        await query.edit_message_text("Произошла ошибка. Попробуйте позже.\n/start")

def main():
    application = Application.builder().token(API_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("search_title", search_title))
    application.add_handler(CommandHandler("search_text", search_text))
    application.add_handler(CommandHandler("search_place", search_place))
    application.add_handler(CommandHandler("list", list_songs))
    application.add_handler(CommandHandler("list_by_region", list_by_region))

    # Register message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register callback handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()