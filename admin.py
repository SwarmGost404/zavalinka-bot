from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import logging
from database import (
    init_db, get_db, add_song, get_all_songs, get_song_by_id,
    delete_song, update_song, search_by_title, search_by_text, get_songs_by_region
)
from env import ADMIN_API_TOKEN

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

async def start(update: Update, context: CallbackContext) -> None:
    """Handler for /start command"""
    await update.message.reply_text(
        "🎵 Менеджер народных песен\n\n"
        "Доступные команды:\n"
        "/add - Добавить новую песню\n"
        "/list - Показать все песни\n"
        "/search_title - Поиск по названию\n"
        "/search_text - Поиск по тексту\n"
        "/search_region - Поиск по региону\n"
        "/help - Помощь"
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Handler for /help command"""
    await update.message.reply_text(
        "📖 Помощь по командам:\n\n"
        "/add - Добавить новую песню\n"
        "/list - Показать все песни с ID\n"
        "/edit - Редактировать песню\n"
        "/delete - Удалить песню\n"
        "/search_title - Поиск по названию\n"
        "/search_text - Поиск по тексту\n"
        "/search_region - Поиск по региону"
    )

async def add_song_handler(update: Update, context: CallbackContext) -> None:
    """Handler for adding new song"""
    await update.message.reply_text("Введите название песни:")
    context.user_data['state'] = 'awaiting_title'

async def list_songs_handler(update: Update, context: CallbackContext) -> None:
    """Handler for listing all songs with IDs"""
    db = next(get_db())
    try:
        songs = get_all_songs(db)
        if not songs:
            await update.message.reply_text("В базе пока нет песен.")
            return

        message = "📋 Список всех песен:\n\n"
        for song in songs:
            message += f"ID: {song.id}\nНазвание: {song.title}\nРегион: {song.region}\n\n"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error listing songs: {e}")
        await update.message.reply_text("Ошибка при получении списка песен")
    finally:
        db.close()

async def delete_song_handler(update: Update, context: CallbackContext) -> None:
    """Handler for deleting song by ID"""
    await update.message.reply_text("Введите ID песни для удаления:")
    context.user_data['state'] = 'awaiting_song_id_for_delete'

async def edit_song_handler(update: Update, context: CallbackContext) -> None:
    """Handler for editing song"""
    await update.message.reply_text("Введите ID песни для редактирования:")
    context.user_data['state'] = 'awaiting_song_id_for_edit'

async def search_title_handler(update: Update, context: CallbackContext) -> None:
    """Handler for searching by title"""
    await update.message.reply_text("Введите название для поиска:")
    context.user_data['state'] = 'search_title'

async def search_text_handler(update: Update, context: CallbackContext) -> None:
    """Handler for searching by text"""
    await update.message.reply_text("Введите текст для поиска:")
    context.user_data['state'] = 'search_text'

async def search_region_handler(update: Update, context: CallbackContext) -> None:
    """Handler for searching by region"""
    await update.message.reply_text("Введите регион для поиска:")
    context.user_data['state'] = 'search_region'

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Main message handler"""
    user_input = update.message.text
    user_state = context.user_data.get('state')

    if not user_state:
        await update.message.reply_text("Используйте команды для работы с ботом")
        return

    try:
        if user_state == 'awaiting_title':
            context.user_data['title'] = user_input
            await update.message.reply_text("Введите регион происхождения:")
            context.user_data['state'] = 'awaiting_region'

        elif user_state == 'awaiting_region':
            context.user_data['region'] = user_input
            await update.message.reply_text("Введите текст песни:")
            context.user_data['state'] = 'awaiting_text'

        elif user_state == 'awaiting_text':
            db = next(get_db())
            try:
                song = add_song(
                    db,
                    title=context.user_data['title'],
                    region=context.user_data['region'],
                    text=user_input
                )
                await update.message.reply_text(
                    f"✅ Песня добавлена!\nID: {song.id}\n"
                    f"Название: {song.title}\nРегион: {song.region}"
                )
            except Exception as e:
                await update.message.reply_text(f"Ошибка: {str(e)}")
            finally:
                db.close()
                context.user_data.clear()

        elif user_state == 'awaiting_song_id_for_delete':
            try:
                song_id = int(user_input)
                db = next(get_db())
                if delete_song(db, song_id):
                    await update.message.reply_text(f"✅ Песня с ID {song_id} удалена")
                else:
                    await update.message.reply_text(f"❌ Песня с ID {song_id} не найдена")
            except ValueError:
                await update.message.reply_text("ID должен быть числом")
            except Exception as e:
                await update.message.reply_text(f"Ошибка: {str(e)}")
            finally:
                db.close()
                context.user_data.clear()

        elif user_state == 'awaiting_song_id_for_edit':
            try:
                song_id = int(user_input)
                db = next(get_db())
                song = get_song_by_id(db, song_id)
                if song:
                    context.user_data['song_id'] = song_id
                    keyboard = [
                        [InlineKeyboardButton("Название", callback_data="edit_title")],
                        [InlineKeyboardButton("Регион", callback_data="edit_region")],
                        [InlineKeyboardButton("Текст", callback_data="edit_text")],
                        [InlineKeyboardButton("Отмена", callback_data="cancel_edit")]
                    ]
                    await update.message.reply_text(
                        f"Редактирование песни ID: {song_id}\n"
                        f"Выберите что изменить:",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                else:
                    await update.message.reply_text(f"❌ Песня с ID {song_id} не найдена")
            except ValueError:
                await update.message.reply_text("ID должен быть числом")
            except Exception as e:
                await update.message.reply_text(f"Ошибка: {str(e)}")
            finally:
                db.close()

        elif user_state == 'search_title':
            db = next(get_db())
            try:
                songs = search_by_title(db, user_input)
                await display_search_results(update, songs, "по названию")
            except Exception as e:
                await update.message.reply_text(f"Ошибка поиска: {str(e)}")
            finally:
                db.close()
                context.user_data.clear()

        elif user_state == 'search_text':
            db = next(get_db())
            try:
                songs = search_by_text(db, user_input)
                await display_search_results(update, songs, "по тексту")
            except Exception as e:
                await update.message.reply_text(f"Ошибка поиска: {str(e)}")
            finally:
                db.close()
                context.user_data.clear()

        elif user_state == 'search_region':
            db = next(get_db())
            try:
                songs = get_songs_by_region(db, user_input)
                await display_search_results(update, songs, "по региону")
            except Exception as e:
                await update.message.reply_text(f"Ошибка поиска: {str(e)}")
            finally:
                db.close()
                context.user_data.clear()

    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text("Произошла ошибка")
        context.user_data.clear()

async def display_search_results(update: Update, songs, search_type):
    """Display search results"""
    if not songs:
        await update.message.reply_text(f"По запросу {search_type} ничего не найдено")
        return
    
    message = f"🔍 Результаты поиска {search_type}:\n\n"
    for song in songs:
        message += f"ID: {song.id}\nНазвание: {song.title}\nРегион: {song.region}\n\n"
    
    await update.message.reply_text(message)

async def button_callback(update: Update, context: CallbackContext) -> None:
    """Handler for inline buttons"""
    query = update.callback_query
    await query.answer()

    try:
        if query.data.startswith("edit_"):
            field = query.data.split("_")[1]
            context.user_data['edit_field'] = field
            context.user_data['state'] = f'editing_{field}'
            await query.edit_message_text(f"Введите новое значение для {field}:")
        
        elif query.data == "cancel_edit":
            await query.edit_message_text("Редактирование отменено")
            context.user_data.clear()
    
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")
        await query.edit_message_text("Произошла ошибка")
        context.user_data.clear()

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(ADMIN_API_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_song_handler))
    application.add_handler(CommandHandler("list", list_songs_handler))
    application.add_handler(CommandHandler("delete", delete_song_handler))
    application.add_handler(CommandHandler("edit", edit_song_handler))
    application.add_handler(CommandHandler("search_title", search_title_handler))
    application.add_handler(CommandHandler("search_text", search_text_handler))
    application.add_handler(CommandHandler("search_region", search_region_handler))

    # Register message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register callback handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()