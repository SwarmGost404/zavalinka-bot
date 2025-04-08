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

async def setup_commands(application: Application):
    """Set up the bot commands for the menu"""
    commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("add", "Добавить новую песню"),
        BotCommand("search_title", "Поиск по названию"),
        BotCommand("search_text", "Поиск по тексту"),
        BotCommand("search_place", "Поиск по месту"),
        BotCommand("all", "Список всех песен"),
        BotCommand("edit", "Редактировать песню"),
        BotCommand("delete", "Удалить песню"),
        BotCommand("help", "Помощь и инструкции")
    ]
    await application.bot.set_my_commands(commands)
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

async def start(update: Update, context: CallbackContext) -> None:
    help_text = (
        "🎵 Этнографический архив песен\n\n"
        "Доступные команды:\n\n"
        "/add - Добавить новую песню\n"
        "/search_title - Поиск по названию\n"
        "/search_text - Поиск по тексту\n"
        "/search_place - Поиск по месту\n"
        "/all - Список всех песен\n"
        "/edit - Редактировать песню\n"
        "/delete - Удалить песню\n"
        "/help - Помощь и инструкции\n\n"
        "Используйте команды из меню или вводите вручную"
    )
    await update.message.reply_text(help_text)

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "🎵 Этнографический архив песен\n\n"
        "Связь с создателем: @SwarmGost\n\n"
        "Доступные команды:\n\n"
        "/start - Начать работу с ботом\n"
        "/add - Добавить новую песню\n"
        "/search_title - Поиск по названию\n"
        "/search_text - Поиск по тексту\n"
        "/search_place - Поиск по месту\n"
        "/all - Список всех песен\n"
        "/edit - Редактировать песню\n"
        "/delete - Удалить песню\n"
        "/help - Эта справка\n\n"
        "Нажмите кнопку меню внизу слева, чтобы увидеть все команды"
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

async def cancel_action(update: Update, context: CallbackContext) -> None:
    if 'action' in context.user_data:
        await update.message.reply_text("Действие отменено")
    context.user_data.clear()
    await start(update, context)

async def show_song_details(update, song, edit_mode=False):
    """Показать детали песни с кнопками действий"""
    if '|' in song.region:
        category, place = song.region.split('|', 1)
    else:
        category, place = song.region, "не указано"
    
    response_text = f"ID: {song.id}\n\n"
    response_text += f"Название: {song.title}\n\n"
    response_text += f"Категория: {category}\n\n"
    response_text += f"Место записи: {place}\n\n"
    response_text += f"Текст:\n{song.text[:200]}..." if len(song.text) > 200 else f"Текст:\n{song.text}"
    
    if edit_mode:
        keyboard = [
            [InlineKeyboardButton("Название", callback_data="edit_title")],
            [InlineKeyboardButton("Регион и место", callback_data="edit_region")],
            [InlineKeyboardButton("Текст песни", callback_data="edit_text")],
            [InlineKeyboardButton("Отмена", callback_data="cancel_edit")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("Редактировать", callback_data=f"edit_{song.id}")],
            [InlineKeyboardButton("Удалить", callback_data=f"delete_{song.id}")],
            [InlineKeyboardButton("Назад", callback_data="back")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update, Update):  # Если пришло сообщение
        await update.message.reply_text(response_text, reply_markup=reply_markup)
    else:  # Если пришел callback query
        await update.edit_message_text(response_text, reply_markup=reply_markup)

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text
    user_state = context.user_data.get('state')

    if not user_state:
        await update.message.reply_text("Используйте команды для взаимодействия с ботом. /help - для списка команд")
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
                
                await show_song_details(update, song, edit_mode=True)
                
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
                
                keyboard = [
                    [InlineKeyboardButton("Да, удалить", callback_data="confirm_delete")],
                    [InlineKeyboardButton("Нет, отменить", callback_data="cancel_delete")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"Подтвердите удаление:\n\n"
                    f"ID: {song_id}\n"
                    f"Название: {song.title}\n"
                    f"Регион: {song.region}\n\n"
                    f"Вы уверены что хотите удалить эту запись?",
                    reply_markup=reply_markup
                )
            except ValueError:
                await update.message.reply_text("ID должен быть числом")
                context.user_data.clear()

        elif user_state == 'editing_title':
            if 'song_id' not in context.user_data:
                await update.message.reply_text("Ошибка: не найден ID песни")
                context.user_data.clear()
                return
                
            song_id = context.user_data['song_id']
            db = next(get_db())
            try:
                update_song(db, song_id, title=user_input)
                await update.message.reply_text(f"Название песни успешно изменено на: {user_input}")
                
                if 'current_song' in context.user_data:
                    context.user_data['current_song']['title'] = user_input
                    
                song = get_song_by_id(db, song_id)
                await show_song_details(update, song, edit_mode=True)
                
            except Exception as e:
                logger.error(f"Ошибка при обновлении названия: {e}")
                await update.message.reply_text("Произошла ошибка при обновлении")
            finally:
                db.close()
                
        elif user_state == 'editing_region':
            if 'song_id' not in context.user_data:
                await update.message.reply_text("Ошибка: не найден ID песни")
                context.user_data.clear()
                return
                
            if '|' not in user_input or not user_input.split('|')[0].strip():
                await update.message.reply_text(
                    "Неверный формат. Введите как: Категория|Место\n\n"
                    "Примеры:\n"
                    "Русские народные|Деревня Петровка\n"
                    "Казачьи|Станица Вешенская\n"
                    "Современные|Город Москва"
                )
                return
                
            song_id = context.user_data['song_id']
            db = next(get_db())
            try:
                update_song(db, song_id, region=user_input)
                await update.message.reply_text("Регион и место успешно обновлены!")
                
                if 'current_song' in context.user_data:
                    context.user_data['current_song']['region'] = user_input
                    
                song = get_song_by_id(db, song_id)
                await show_song_details(update, song, edit_mode=True)
                
            except Exception as e:
                logger.error(f"Ошибка при обновлении региона: {e}")
                await update.message.reply_text("Произошла ошибка при обновлении")
            finally:
                db.close()
                context.user_data['state'] = 'edit_menu'
                
        elif user_state == 'editing_text':
            if 'song_id' not in context.user_data:
                await update.message.reply_text("Ошибка: не найден ID песни")
                context.user_data.clear()
                return
                
            song_id = context.user_data['song_id']
            db = next(get_db())
            try:
                update_song(db, song_id, text=user_input)
                await update.message.reply_text("Текст песни успешно обновлен")
                
                if 'current_song' in context.user_data:
                    context.user_data['current_song']['text'] = user_input
                    
                song = get_song_by_id(db, song_id)
                await show_song_details(update, song, edit_mode=True)
                
            except Exception as e:
                logger.error(f"Ошибка при обновлении текста: {e}")
                await update.message.reply_text("Произошла ошибка при обновлении")
            finally:
                db.close()

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        context.user_data.clear()

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

async def display_results(update: Update, results, search_description, context: CallbackContext):
    if results:
        keyboard = []
        for song in results:
            category, place = parse_region(song.region)
            button_text = f"ID: {song.id} - {song.title}"
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

async def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    db = None  # Initialize db outside try block
    try:
        if query.data.startswith("song_"):
            try:
                song_id = int(query.data.split("_")[1])
                db = next(get_db())
                song = get_song_by_id(db, song_id)
                if song:
                    await show_song_details(query, song)
                else:
                    await query.edit_message_text("Песня не найдена")
            except (ValueError, IndexError):
                await query.edit_message_text("Ошибка: некорректный ID песни")
            except Exception as e:
                logger.error(f"Ошибка при получении песни: {e}")
                await query.edit_message_text("Произошла ошибка. Попробуйте позже.")
                
        elif query.data.startswith("edit_"):
            try:
                song_id = int(query.data.split("_")[1])
                db = next(get_db())
                song = get_song_by_id(db, song_id)
                if song:
                    context.user_data.update({
                        'song_id': song_id,
                        'current_song': {
                            'title': song.title,
                            'region': song.region,
                            'text': song.text
                        },
                        'state': 'edit_menu'
                    })
                    await show_song_details(query, song, edit_mode=True)
                else:
                    await query.edit_message_text("Песня не найдена")
            except (ValueError, IndexError):
                await query.edit_message_text("Ошибка: некорректный ID песни")
            except Exception as e:
                logger.error(f"Ошибка при редактировании песни: {e}")
                await query.edit_message_text("Произошла ошибка")
                
        elif query.data.startswith("delete_"):
            try:
                song_id = int(query.data.split("_")[1])
                db = next(get_db())
                song = get_song_by_id(db, song_id)
                if song:
                    context.user_data['song_to_delete'] = {
                        'id': song_id,
                        'title': song.title,
                        'region': song.region
                    }
                    
                    keyboard = [
                        [InlineKeyboardButton("Да, удалить", callback_data="confirm_delete")],
                        [InlineKeyboardButton("Нет, отменить", callback_data="cancel_delete")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"Подтвердите удаление:\n\n"
                        f"ID: {song_id}\n"
                        f"Название: {song.title}\n"
                        f"Регион: {song.region}\n\n"
                        f"Вы уверены что хотите удалить эту запись?",
                        reply_markup=reply_markup
                    )
                else:
                    await query.edit_message_text("Песня не найдена")
            except (ValueError, IndexError):
                await query.edit_message_text("Ошибка: некорректный ID песни")
            except Exception as e:
                logger.error(f"Ошибка при удалении песни: {e}")
                await query.edit_message_text("Произошла ошибка")
                
        elif query.data in ["edit_title", "edit_region", "edit_text"]:
            context.user_data['state'] = f'editing_{query.data.split("_")[1]}'
            if query.data == "edit_region":
                await query.edit_message_text(
                    "Введите регион и место в формате: Категория|Место\n\n"
                    "Примеры:\n"
                    "Русские народные|Деревня Петровка\n"
                    "Казачьи|Станица Вешенская\n"
                    "Современные|Город Москва"
                )
            else:
                await query.edit_message_text(f"Введите новый {query.data.split('_')[1]} песни:")
            
        elif query.data == "confirm_delete":
            if 'song_to_delete' not in context.user_data:
                await query.edit_message_text("Нет данных для удаления")
                return
            
            try:
                db = next(get_db())
                song_id = context.user_data['song_to_delete']['id']
                delete_song(db, song_id)
                await query.edit_message_text(
                    f"Песня успешно удалена!\n"
                    f"ID: {song_id}\n"
                    f"Название: {context.user_data['song_to_delete']['title']}"
                )
                context.user_data.clear()
            except Exception as e:
                logger.error(f"Ошибка при удалении песни: {e}")
                await query.edit_message_text("Произошла ошибка при удалении")
                
        elif query.data in ["cancel_edit", "cancel_delete", "back"]:
            await query.delete_message()
            context.user_data.clear()
            
        else:
            await query.edit_message_text("Неизвестная команда")
            logger.warning(f"Неизвестные callback данные: {query.data}")
            
    except Exception as e:
        logger.error(f"Необработанная ошибка в button_callback: {e}")
        await query.edit_message_text("Произошла непредвиденная ошибка")
        
    finally:
        if db is not None:
            db.close()

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(ADMIN_API_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_song_handler))
    application.add_handler(CommandHandler("search_title", search_title_handler))
    application.add_handler(CommandHandler("search_text", search_text_handler))
    application.add_handler(CommandHandler("search_place", search_place_handler))
    application.add_handler(CommandHandler("all", list_songs_handler))
    application.add_handler(CommandHandler("edit", update_song_handler))
    application.add_handler(CommandHandler("delete", delete_song_handler))

    # Register message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register callback handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Set up commands menu
    application.post_init = setup_commands

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()