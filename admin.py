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
        [
            KeyboardButton("Редактировать"),
            KeyboardButton("Удалить")
        ],
        [KeyboardButton("Помощь")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = "Этнографический архив песен\nВыберите действие:"
    await update.message.reply_text(text, reply_markup=reply_markup)

async def show_confirm_delete_menu(update: Update, context: CallbackContext, song_info: dict):
    keyboard = [
        [KeyboardButton("Да, удалить")],
        [KeyboardButton("Нет, отменить")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = (
        f"Подтверждение удаления\n\n"
        f"ID: {song_info['id']}\n"
        f"Название: {song_info['title']}\n"
        f"Регион: {song_info['region']}\n\n"
        f"Вы уверены что хотите удалить эту запись?"
    )
    await update.message.reply_text(text, reply_markup=reply_markup)

async def show_edit_menu(update: Update, context: CallbackContext, song_info: dict):
    keyboard = [
        [KeyboardButton("Название")],
        [KeyboardButton("Регион и место")],
        [KeyboardButton("Текст песни")],
        [KeyboardButton("Назад")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = (
        f"Редактирование песни\n\n"
        f"ID: {song_info['id']}\n"
        f"1. Название: {song_info['title']}\n"
        f"2. Регион: {song_info['region']}\n"
        f"3. Текст: {song_info['text'][:50]}...\n\n"
        f"Что вы хотите изменить?"
    )
    await update.message.reply_text(text, reply_markup=reply_markup)

async def show_search_menu(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton("По названию")],
        [KeyboardButton("По тексту")],
        [KeyboardButton("По месту записи")],
        [KeyboardButton("Назад")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = "Поиск песен\nВыберите тип поиска:"
    await update.message.reply_text(text, reply_markup=reply_markup)

# Command handlers
async def start(update: Update, context: CallbackContext) -> None:
    await show_main_menu(update, context)

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "Этнографический архив песен\n\n"
        "Используйте кнопки меню для работы с ботом:\n\n"
        "Добавить песню - новая запись в архив\n"
        "Поиск - найти песни по разным критериям\n"
        "Список всех песен - просмотр всего архива\n"
        "Редактировать - изменить существующую запись\n"
        "Удалить - удалить запись из архива\n\n"
        "Для возврата в главное меню нажмите Назад"
    )
    await update.message.reply_text(help_text)

async def add_song_handler(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни:')
    context.user_data['state'] = 'awaiting_title'
    context.user_data['action'] = 'add'

async def search_title_handler(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите название песни для поиска:')
    context.user_data['state'] = 'search_title'

async def search_text_handler(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите текст песни для поиска:')
    context.user_data['state'] = 'search_text'

async def search_place_handler(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Введите место записи для поиска:')
    context.user_data['state'] = 'search_place'

async def list_songs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = next(get_db())
    try:
        songs = get_all_songs(db)
        if not songs:
            await update.message.reply_text("В базе данных пока нет песен.")
            return

        keyboard = []
        for song in songs:
            category, place = parse_region(song.region)
            button_text = f"{song.title}"
            if place and place != "не указано":
                button_text += f" ({place})"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"song_{song.id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Список всех песен:",
            reply_markup=reply_markup
        )
            
    except Exception as e:
        logger.error(f"Error in list_songs: {e}")
        await update.message.reply_text("Произошла ошибка при получении списка песен.")
    finally:
        db.close()

async def update_song_handler(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Введите ID песни для изменения:")
    context.user_data['state'] = 'awaiting_song_id_for_update'
    context.user_data['action'] = 'update'

async def delete_song_handler(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Введите ID песни для удаления:")
    context.user_data['state'] = 'awaiting_song_id_for_delete'
    context.user_data['action'] = 'delete'

async def confirm_delete(update: Update, context: CallbackContext) -> None:
    if update.message.text == "Да, удалить":
        if 'song_to_delete' not in context.user_data:
            await update.message.reply_text("Нет данных для удаления")
            return
        
        db = None
        try:
            db = next(get_db())
            song_id = context.user_data['song_to_delete']['id']
            
            # Проверяем существование песни перед удалением
            song = get_song_by_id(db, song_id)
            if not song:
                await update.message.reply_text(f"Песня с ID {song_id} не найдена")
                return
                
            # Удаляем песню
            delete_song(db, song_id)
            
            await update.message.reply_text(
                f"Песня успешно удалена!\n"
                f"ID: {song_id}\n"
                f"Название: {context.user_data['song_to_delete']['title']}\n"
            )
        except Exception as e:
            logger.error(f"Ошибка при удалении песни: {e}", exc_info=True)
            await update.message.reply_text("Произошла ошибка при удалении песни")
        finally:
            if db:
                db.close()
            context.user_data.clear()
            await show_main_menu(update, context)
    else:
        await show_main_menu(update, context)

async def cancel_action(update: Update, context: CallbackContext) -> None:
    if 'action' in context.user_data:
        await update.message.reply_text("Действие отменено")
        context.user_data.clear()
    await show_main_menu(update, context)

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text
    user_state = context.user_data.get('state')

    # Обработка кнопок главного меню
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
    elif user_input == "Редактировать":
        await update_song_handler(update, context)
        return
    elif user_input == "Удалить":
        await delete_song_handler(update, context)
        return
    elif user_input == "Помощь":
        await help_command(update, context)
        return
    elif user_input in ["Назад", "Нет, отменить"]:
        await cancel_action(update, context)
        return
    elif user_input == "Да, удалить":
        await confirm_delete(update, context)
        return

    if not user_state:
        await update.message.reply_text("Используйте меню для взаимодействия с ботом.")
        await show_main_menu(update, context)
        return

    try:
        if user_state == 'awaiting_title':
            context.user_data['title'] = user_input
            await update.message.reply_text('Введите категорию:')
            context.user_data['state'] = 'awaiting_region'

        elif user_state == 'awaiting_region':
            context.user_data['region'] = user_input
            await update.message.reply_text('Введите место записи (например, "Село Вятское Ярославской области"):')
            context.user_data['state'] = 'awaiting_place'

        elif user_state == 'awaiting_place':
            context.user_data['place'] = user_input
            await update.message.reply_text('Отправьте текст песни:')
            context.user_data['state'] = 'awaiting_text'

        elif user_state == 'awaiting_text':
            context.user_data['text'] = user_input
            await save_song(update, context)

        elif user_state == 'search_title':
            db = next(get_db())
            results = search_by_title(db, user_input)
            await display_results(update, results, f"по названию '{user_input}'", context)

        elif user_state == 'search_text':
            db = next(get_db())
            results = search_by_text(db, user_input)
            await display_results(update, results, f"по тексту '{user_input}'", context)

        elif user_state == 'search_place':
            db = next(get_db())
            results = [song for song in get_all_songs(db) 
                      if '|' in song.region and user_input.lower() in song.region.lower().split('|')[1]]
            await display_results(update, results, f"по месту записи '{user_input}'", context)

        elif user_state == 'awaiting_song_id_for_update':
            try:
                song_id = int(user_input)
                db = next(get_db())
                song = get_song_by_id(db, song_id)
                if not song:
                    await update.message.reply_text(f"Песня с ID {song_id} не найдена")
                    context.user_data.clear()
                    return

                context.user_data['song_id'] = song_id
                context.user_data['current_song'] = {
                    'title': song.title,
                    'region': song.region,
                    'text': song.text
                }
                await show_edit_menu(update, context, {
                    'id': song.id,
                    'title': song.title,
                    'region': song.region,
                    'text': song.text
                })
            except ValueError:
                await update.message.reply_text("ID должен быть числом")
                context.user_data.clear()

        elif user_state == 'awaiting_song_id_for_delete':
            try:
                song_id = int(user_input)
                db = next(get_db())
                song = get_song_by_id(db, song_id)
                if not song:
                    await update.message.reply_text(f"Песня с ID {song_id} не найдена")
                    context.user_data.clear()
                    return
                
                context.user_data['song_to_delete'] = {
                    'id': song_id,
                    'title': song.title,
                    'region': song.region
                }
                
                await show_confirm_delete_menu(update, context, {
                    'id': song_id,
                    'title': song.title,
                    'region': song.region
                })
                context.user_data['state'] = 'confirm_delete'
            except ValueError:
                await update.message.reply_text("ID должен быть числом")
                context.user_data.clear()

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        context.user_data.clear()
        await show_main_menu(update, context)

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
        )
        context.user_data.clear()
    except Exception as e:
        logger.error(f"Ошибка при сохранении песни: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        context.user_data.clear()
    finally:
        db.close()
        await show_main_menu(update, context)

async def display_results(update: Update, results, search_description, context: CallbackContext):
    if results:
        keyboard = []
        for song in results:
            category, place = parse_region(song.region)
            button_text = f"ID: {song.id} - {song.title}"  # Добавляем ID в текст кнопки
            if place and place != "не указано":
                button_text += f" ({place})"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"song_{song.id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Найдены песни {search_description}:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(f"По запросу {search_description} ничего не найдено.")
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
            response_text = f"ID: {song.id}\n\n"  # Добавляем ID песни
            response_text += f"Название: {song.title}\n\n"
            response_text += f"Категория: {category}\n\n"
            if place and place != "не указано":
                response_text += f"Место записи: {place}\n\n"
            response_text += f"Текст:\n{song.text}\n\n"
            
            keyboard = [
                [InlineKeyboardButton("Редактировать", callback_data=f"edit_{song.id}")],
                [InlineKeyboardButton("Удалить", callback_data=f"delete_{song.id}")],
                [InlineKeyboardButton("Назад к результатам", callback_data="back_to_results")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                response_text,
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("Песня не найдена")
    except Exception as e:
        logger.error(f"Ошибка при получении текста песни: {e}")
        await query.edit_message_text("Произошла ошибка. Попробуйте позже.")
    finally:
        db.close()

async def handle_callback_query(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("edit_"):
        song_id = int(query.data.split("_")[1])
        db = next(get_db())
        try:
            song = get_song_by_id(db, song_id)
            if song:
                context.user_data.update({
                    'song_id': song_id,
                    'current_song': {
                        'id': song.id,
                        'title': song.title,
                        'region': song.region,
                        'text': song.text
                    },
                    'state': 'edit_menu'
                })
                await show_edit_menu(update, context, {
                    'id': song.id,
                    'title': song.title,
                    'region': song.region,
                    'text': song.text
                })
            else:
                await query.edit_message_text("Песня не найдена")
        except Exception as e:
            logger.error(f"Ошибка при редактировании песни: {e}")
            await query.edit_message_text("Произошла ошибка")
        finally:
            db.close()
            
    elif query.data.startswith("delete_"):
        song_id = int(query.data.split("_")[1])
        db = next(get_db())
        try:
            song = get_song_by_id(db, song_id)
            if song:
                context.user_data['song_to_delete'] = {
                    'id': song_id,
                    'title': song.title,
                    'region': song.region
                }
                await show_confirm_delete_menu(update, context, {
                    'id': song_id,
                    'title': song.title,
                    'region': song.region
                })
            else:
                await query.edit_message_text("Песня не найдена")
        except Exception as e:
            logger.error(f"Ошибка при удалении песни: {e}")
            await query.edit_message_text("Произошла ошибка")
        finally:
            db.close()
            
    elif query.data == "back_to_results":
        await query.delete_message()

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(ADMIN_API_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Register message handlers for menu buttons
    application.add_handler(MessageHandler(filters.Text(["Добавить песню"]), add_song_handler))
    application.add_handler(MessageHandler(filters.Text(["Поиск по названию"]), search_title_handler))
    application.add_handler(MessageHandler(filters.Text(["Поиск по тексту"]), search_text_handler))
    application.add_handler(MessageHandler(filters.Text(["Поиск по месту"]), search_place_handler))
    application.add_handler(MessageHandler(filters.Text(["Список всех песен"]), list_songs_handler))
    application.add_handler(MessageHandler(filters.Text(["Редактировать"]), update_song_handler))
    application.add_handler(MessageHandler(filters.Text(["Удалить"]), delete_song_handler))
    application.add_handler(MessageHandler(filters.Text(["Помощь"]), help_command))
    application.add_handler(MessageHandler(filters.Text(["Назад", "Нет, отменить"]), cancel_action))
    application.add_handler(MessageHandler(filters.Text(["Да, удалить"]), confirm_delete))

    # Register other message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()