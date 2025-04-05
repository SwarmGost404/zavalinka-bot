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
        '/update - изменить песню\n'
        '/delete - удалить песню\n'
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
        '/update - изменить песню\n'
        '/delete - удалить песню\n'
        '/help - справка'
    )

async def add(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни:')
    context.user_data['awaiting_input'] = 'awaiting_title'
    context.user_data['action'] = 'add'

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
            region_parts = song['region'].split('|') if '|' in song['region'] else [song['region'], '']
            response += f"Категория: {region_parts[0]}\n"
            if region_parts[1]:
                response += f"Место записи: {region_parts[1]}\n"
            response += "\n"

        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in list_songs: {e}")
        await update.message.reply_text("Произошла ошибка при получении списка песен.")
    finally:
        db.close()

async def update_song_start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите ID песни для изменения:')
    context.user_data['awaiting_input'] = 'update_id'
    context.user_data['action'] = 'update'

async def delete_song_start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите ID песни для удаления:')
    context.user_data['awaiting_input'] = 'delete_id'
    context.user_data['action'] = 'delete'

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text

    if 'awaiting_input' not in context.user_data:
        await update.message.reply_text("Используйте команды для взаимодействия с ботом.")
        return

    try:
        current_state = context.user_data['awaiting_input']
        
        if current_state == 'awaiting_title':
            context.user_data['title'] = user_input
            await update.message.reply_text('Введите категорию:')
            context.user_data['awaiting_input'] = 'awaiting_region'

        elif current_state == 'awaiting_region':
            context.user_data['region'] = user_input
            await update.message.reply_text('Введите место записи (например, "Село Вятское Ярославской области"):')
            context.user_data['awaiting_input'] = 'awaiting_place'

        elif current_state == 'awaiting_place':
            context.user_data['place'] = user_input
            await update.message.reply_text('Отправьте текст песни:')
            context.user_data['awaiting_input'] = 'awaiting_text'

        elif current_state == 'awaiting_text':
            context.user_data['text'] = user_input
            await save_song(update, context)

        elif current_state == 'search_title':
            db = next(get_db())
            results = search_by_title(db, user_input)
            await display_results(update, results, f"по названию '{user_input}'")

        elif current_state == 'search_text':
            db = next(get_db())
            results = search_by_text(db, user_input)
            await display_results(update, results, f"по тексту '{user_input}'")

        elif current_state == 'search_place':
            db = next(get_db())
            results = [song for song in get_all_songs(db) 
                      if '|' in song.region and user_input.lower() in song.region.lower().split('|')[1]]
            await display_results(update, results, f"по месту записи '{user_input}'")

        elif current_state == 'update_id':
            try:
                song_id = int(user_input)
                db = next(get_db())
                song = get_song_by_id(db, song_id)
                if not song:
                    await update.message.reply_text(f"Песня с ID {song_id} не найдена.")
                    context.user_data.clear()
                    return
                
                context.user_data['song_id'] = song_id
                await update.message.reply_text(
                    f"Редактирование песни ID: {song_id}\n"
                    f"Текущее название: {song.title}\n"
                    f"Введите новое название (или точку . чтобы оставить текущее):"
                )
                context.user_data['awaiting_input'] = 'update_title'
            except ValueError:
                await update.message.reply_text("ID должен быть числом. Попробуйте снова.")
                context.user_data.clear()

        elif current_state == 'update_title':
            if user_input != '.':
                context.user_data['new_title'] = user_input
            await update.message.reply_text(
                "Введите новую категорию (или точку . чтобы оставить текущую):"
            )
            context.user_data['awaiting_input'] = 'update_region'

        elif current_state == 'update_region':
            if user_input != '.':
                context.user_data['new_region'] = user_input
            await update.message.reply_text(
                "Введите новое место записи (или точку . чтобы оставить текущее):"
            )
            context.user_data['awaiting_input'] = 'update_place'

        elif current_state == 'update_place':
            if user_input != '.':
                context.user_data['new_place'] = user_input
            await update.message.reply_text(
                "Введите новый текст песни (или точку . чтобы оставить текущий):"
            )
            context.user_data['awaiting_input'] = 'update_text'

        elif current_state == 'update_text':
            db = next(get_db())
            try:
                song_id = context.user_data['song_id']
                update_data = {}
                
                if 'new_title' in context.user_data:
                    update_data['title'] = context.user_data['new_title']
                
                if 'new_region' in context.user_data or 'new_place' in context.user_data:
                    current_song = get_song_by_id(db, song_id)
                    current_region, current_place = parse_region(current_song.region)
                    
                    new_region = context.user_data.get('new_region', current_region)
                    new_place = context.user_data.get('new_place', current_place)
                    update_data['region'] = f"{new_region}|{new_place}"
                
                if user_input != '.':
                    update_data['text'] = user_input
                
                if update_data:
                    updated_song = update_song(db, song_id, **update_data)
                    await update.message.reply_text(
                        f"Песня ID {song_id} успешно обновлена!\n"
                        f"Название: {updated_song.title}\n"
                        f"Категория: {parse_region(updated_song.region)[0]}\n"
                        f"Место записи: {parse_region(updated_song.region)[1]}\n"
                        f"/start"
                    )
                else:
                    await update.message.reply_text("Ничего не изменено.")
                
                context.user_data.clear()
            except Exception as e:
                logger.error(f"Ошибка при обновлении песни: {e}")
                await update.message.reply_text("Произошла ошибка при обновлении.")
                context.user_data.clear()
            finally:
                db.close()

        elif current_state == 'delete_id':
            try:
                song_id = int(user_input)
                db = next(get_db())
                song = get_song_by_id(db, song_id)
                if not song:
                    await update.message.reply_text(f"Песня с ID {song_id} не найдена.")
                    context.user_data.clear()
                    return
                
                await update.message.reply_text(
                    f"Вы уверены, что хотите удалить песню?\n"
                    f"ID: {song.id}\n"
                    f"Название: {song.title}\n"
                    f"Категория: {parse_region(song.region)[0]}\n"
                    f"Место записи: {parse_region(song.region)[1]}\n\n"
                    f"Подтвердите удаление командой /confirm_delete или отмените /cancel"
                )
                context.user_data['song_id'] = song_id
                context.user_data['awaiting_input'] = 'confirm_delete'
            except ValueError:
                await update.message.reply_text("ID должен быть числом. Попробуйте снова.")
                context.user_data.clear()

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.\n/start")
        context.user_data.clear()

async def confirm_delete(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('awaiting_input') != 'confirm_delete':
        return
    
    db = next(get_db())
    try:
        song_id = context.user_data['song_id']
        delete_song(db, song_id)
        await update.message.reply_text(f"Песня с ID {song_id} успешно удалена.\n/start")
    except Exception as e:
        logger.error(f"Ошибка при удалении песни: {e}")
        await update.message.reply_text("Произошла ошибка при удалении.")
    finally:
        context.user_data.clear()
        db.close()

async def cancel_action(update: Update, context: CallbackContext) -> None:
    if 'action' in context.user_data:
        await update.message.reply_text("Действие отменено.\n/start")
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
    application.add_handler(CommandHandler("update", update_song_start))
    application.add_handler(CommandHandler("delete", delete_song_start))
    application.add_handler(CommandHandler("confirm_delete", confirm_delete))
    application.add_handler(CommandHandler("cancel", cancel_action))

    # Register message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register callback handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()