import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
    ContextTypes
)
from env import ADMIN_API_TOKEN
from database import (
    init_db,
    get_db,
    add_song,
    get_all_songs,
    get_all_songs_with_id,
    get_songs_by_region,
    search_by_title,
    search_by_text,
    get_song_by_id,
    delete_song,
    update_song
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
    if '|' in region_str:
        parts = region_str.split('|')
        return parts[0], parts[1] if len(parts) > 1 else "не указано"
    return region_str, "не указано"

# Command handlers
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Привет! Я хранитель текстов этнографических песен\n'
        'Используй команды:\n'
        '/add - добавить песню\n'
        '/search_title - найти по названию\n'
        '/search_text - найти по тексту\n'
        '/search_place - найти по месту записи\n'
        '/list - все песни\n'
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

async def list_songs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = next(get_db())
    try:
        songs = get_all_songs_with_id(db)
        if not songs:
            await update.message.reply_text("В базе данных пока нет песен.")
            return

        response = "Список песен:\n\n"
        for song in songs:
            response += f"ID: {song['id']}\n"
            response += f"Название: {song['title']}\n"
            response += f"Регион: {song['region']}\n"
            if song['category']:
                response += f"Категория: {song['category']}\n"
            response += "\n"

        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in list_songs: {e}")
        await update.message.reply_text("Произошла ошибка при получении списка песен.")
    finally:
        db.close()

async def update_song_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 3:
            await update.message.reply_text(
                "ℹ️ Формат команды:\n"
                "/update <id> <поле> <новое_значение>\n"
                "Доступные поля: title, text, region, category"
            )
            return

        song_id = int(context.args[0])
        field = context.args[1].lower()
        new_value = ' '.join(context.args[2:])

        valid_fields = ['title', 'text', 'region', 'category']
        if field not in valid_fields:
            await update.message.reply_text(
                f"❌ Неверное поле. Доступные поля: {', '.join(valid_fields)}"
            )
            return

        db = next(get_db())
        try:
            song = get_song_by_id(db, song_id)
            if not song:
                await update.message.reply_text(f"❌ Песня с ID {song_id} не найдена")
                return

            update_data = {field: new_value}
            updated_song = update_song(db, song_id, **update_data)

            await update.message.reply_text(
                f"✅ Песня обновлена:\n"
                f"ID: {updated_song.id}\n"
                f"Название: {updated_song.title}\n"
                f"Регион: {updated_song.region}\n"
                f"Категория: {updated_song.category}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при обновлении: {str(e)}")
            logger.error(f"Update error: {str(e)}")
        finally:
            db.close()
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом")

async def delete_song_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("ℹ️ Использование: /delete <ID песни>")
            return
            
        song_id = int(context.args[0])
        
        db = next(get_db())
        try:
            delete_song(db, song_id)
            await update.message.reply_text(f"✅ Песня с ID {song_id} успешно удалена")
        except ValueError as e:
            await update.message.reply_text(f"❌ {str(e)}")
        except Exception as e:
            await update.message.reply_text("❌ Произошла ошибка при удалении")
            logger.error(f"Delete error: {str(e)}")
        finally:
            db.close()
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID. Используйте число.")

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
            await update.message.reply_text('Введите место записи (например, "Село Вятское Ярославской области"):')
            context.user_data['awaiting_input'] = 'awaiting_place'

        elif context.user_data['awaiting_input'] == 'awaiting_place':
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
        keyboard = [
            [InlineKeyboardButton(
                f"{song.title} ({parse_region(song.region)[1]})" if '|' in song.region else song.title,
                callback_data=f"song_{song.id}"
            )]
            for song in results
        ]
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
        
        full_region = f"{region}|{place}"
        
        song = add_song(db, title=title, region=full_region, text=text)
        await update.message.reply_text(
            f'Песня "{title}" успешно добавлена!\n'
            f'Категория: {region}\n'
            f'Место записи: {place}\n'
            f'/start'
        )
        context.user_data.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении песни: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.\n/start")
        context.user_data.clear()
    finally:
        db.close()

async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    song_id = int(query.data.split("_")[1])
    db = next(get_db())
    
    try:
        song = get_song_by_id(db, song_id)
        if song:
            category, place = parse_region(song.region)
            await query.edit_message_text(
                f"Название: {song.title}\n\n"
                f"Категория: {category}\n\n"
                f"Место записи: {place}\n\n"
                f"Текст:\n{song.text}\n\n"
                f"/start"
            )
        else:
            await query.edit_message_text("Песня не найдена.\n/start")
    except Exception as e:
        logger.error(f"Ошибка при получении текста песни: {e}")
        await query.edit_message_text("Произошла ошибка. Попробуйте позже.\n/start")
    finally:
        db.close()

def main():
    application = Application.builder().token(ADMIN_API_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("search_title", search_title))
    application.add_handler(CommandHandler("search_text", search_text))
    application.add_handler(CommandHandler("search_place", search_place))
    application.add_handler(CommandHandler("list", list_songs))
    application.add_handler(CommandHandler("update", update_song_handler))
    application.add_handler(CommandHandler("delete", delete_song_handler))

    # Register message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register callback handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
