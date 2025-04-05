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
    
    text = "🎵 *Этнографический архив песен*\nВыберите действие:"
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_confirm_delete_menu(update: Update, context: CallbackContext, song_info: dict):
    keyboard = [
        [KeyboardButton("✅ Да, удалить")],
        [KeyboardButton("❌ Нет, отменить")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = (
        f"❗ *Подтверждение удаления*\n\n"
        f"ID: {song_info['id']}\n"
        f"Название: {song_info['title']}\n"
        f"Регион: {song_info['region']}\n\n"
        f"Вы уверены что хотите удалить эту запись?"
    )
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_edit_menu(update: Update, context: CallbackContext, song_info: dict):
    keyboard = [
        [KeyboardButton("Название")],
        [KeyboardButton("Регион и место")],
        [KeyboardButton("Текст песни")],
        [KeyboardButton("◀ Назад")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = (
        f"✏ *Редактирование песни*\n\n"
        f"ID: {song_info['id']}\n"
        f"1. Название: {song_info['title']}\n"
        f"2. Регион: {song_info['region']}\n"
        f"3. Текст: {song_info['text'][:50]}...\n\n"
        f"Что вы хотите изменить?"
    )
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_search_menu(update: Update, context: CallbackContext):
    keyboard = [
        [KeyboardButton("По названию")],
        [KeyboardButton("По тексту")],
        [KeyboardButton("По месту записи")],
        [KeyboardButton("◀ Назад")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = "🔍 *Поиск песен*\nВыберите тип поиска:"
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Command handlers
async def start(update: Update, context: CallbackContext) -> None:
    await show_main_menu(update, context)

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "🎵 *Этнографический архив песен*\n\n"
        "Используйте кнопки меню для работы с ботом:\n\n"
        "• *Добавить песню* - новая запись в архив\n"
        "• *Поиск* - найти песни по разным критериям\n"
        "• *Список всех песен* - просмотр всего архива\n"
        "• *Редактировать* - изменить существующую запись\n"
        "• *Удалить* - удалить запись из архива\n\n"
        "Для возврата в главное меню нажмите ◀ Назад"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

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
        songs = get_all_songs_with_id(db)
        if not songs:
            await update.message.reply_text("В базе данных пока нет песен.")
            return

        chunk_size = 10
        for i in range(0, len(songs), chunk_size):
            chunk = songs[i:i + chunk_size]
            response = "📋 *Список песен*\n\n"
            
            for song in chunk:
                response += f"🔹 *ID: {song['id']}*\n"
                response += f"📌 *Название:* {song['title']}\n"
                region_parts = song['region'].split('|') if '|' in song['region'] else [song['region'], '']
                response += f"🌍 *Категория:* {region_parts[0]}\n"
                if region_parts[1]:
                    response += f"📍 *Место записи:* {region_parts[1]}\n"
                response += "\n"

            await update.message.reply_text(response, parse_mode='Markdown')
            
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
    if update.message.text == "✅ Да, удалить":
        if 'song_to_delete' not in context.user_data:
            await update.message.reply_text("❌ Нет данных для удаления")
            return
        
        db = None
        try:
            db = next(get_db())
            song_id = context.user_data['song_to_delete']['id']
            
            logger.info(f"Попытка удалить песню с ID: {song_id}")
            
            song = get_song_by_id(db, song_id)
            if not song:
                await update.message.reply_text(f"❌ Песня с ID {song_id} не найдена")
                return
                
            delete_song(db, song_id)
            logger.info(f"Песня с ID {song_id} успешно удалена")
            
            await update.message.reply_text(
                f"✅ *Песня успешно удалена!*\n\n"
                f"ID: {song_id}\n"
                f"Название: {context.user_data['song_to_delete']['title']}\n\n"
                f"Для продолжения используйте меню",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка при удалении песни: {e}", exc_info=True)
            await update.message.reply_text("❌ Произошла ошибка при удалении песни")
        finally:
            if db:
                db.close()
            context.user_data.clear()
            await show_main_menu(update, context)
    else:
        await show_main_menu(update, context)

async def cancel_action(update: Update, context: CallbackContext) -> None:
    if 'action' in context.user_data:
        await update.message.reply_text("❌ Действие отменено")
        context.user_data.clear()
    await show_main_menu(update, context)


async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text
    user_state = context.user_data.get('state')

    # Обработка кнопок редактирования
    if user_state == 'edit_menu':
        if user_input == "Название":
            await update.message.reply_text("Введите новое название:")
            context.user_data['state'] = 'editing_title'
        elif user_input == "Регион и место":
            await update.message.reply_text("Введите новую категорию и место через | (например: Частушки|Ярославская область):")
            context.user_data['state'] = 'editing_region'
        elif user_input == "Текст песни":
            await update.message.reply_text("Введите новый текст песни:")
            context.user_data['state'] = 'editing_text'
        elif user_input == "◀ Назад":
            await cancel_action(update, context)
        return

    # Остальная обработка состояний остается как была
    # ... (предыдущий код обработки состояний)

    # Добавляем новые состояния для редактирования
    elif user_state == 'editing_title':
        context.user_data['new_title'] = user_input
        await apply_changes(update, context)
        
    elif user_state == 'editing_region':
        if '|' not in user_input:
            await update.message.reply_text("❌ Неверный формат. Введите категорию и место через |")
            return
        context.user_data['new_region'] = user_input
        await apply_changes(update, context)
        
    elif user_state == 'editing_text':
        context.user_data['new_text'] = user_input
        await apply_changes(update, context)

async def apply_changes(update: Update, context: CallbackContext) -> None:
    db = None
    try:
        db = next(get_db())
        song_id = context.user_data['song_id']
        current_song = context.user_data['current_song']
        
        update_data = {
            'title': context.user_data.get('new_title', current_song['title']),
            'region': context.user_data.get('new_region', current_song['region']),
            'text': context.user_data.get('new_text', current_song['text'])
        }
        
        updated_song = update_song(
            db,
            song_id=song_id,
            title=update_data['title'],
            region=update_data['region'],
            text=update_data['text']
        )
        
        await update.message.reply_text(
            f"✅ *Песня успешно обновлена!*\n\n"
            f"*ID:* {song_id}\n"
            f"*Название:* {updated_song.title}\n"
            f"*Регион:* {updated_song.region}\n\n"
            f"Для продолжения используйте меню",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении песни: {e}", exc_info=True)
        await update.message.reply_text("❌ Произошла ошибка при обновлении песни")
    finally:
        if db:
            db.close()
        context.user_data.clear()
        await show_main_menu(update, context)

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
            f"🔍 *Результаты поиска {search_description}:*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ По запросу {search_description} ничего не найдено.\n"
            f"Попробуйте изменить параметры поиска."
        )
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
            response = (
                f"🎵 *Детали песни*\n\n"
                f"*ID:* {song.id}\n"
                f"*Название:* {song.title}\n"
                f"*Категория:* {category}\n"
                f"*Место записи:* {place}\n\n"
                f"*Текст:*\n{song.text}\n\n"
            )
            
            # Добавляем кнопки действий для песни
            keyboard = [
                [InlineKeyboardButton("✏ Редактировать", callback_data=f"edit_{song.id}")],
                [InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{song.id}")],
                [InlineKeyboardButton("◀ Назад к результатам", callback_data="back_to_results")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                response,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Песня не найдена")
    except Exception as e:
        logger.error(f"Ошибка при получении текста песни: {e}", exc_info=True)
        await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
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
                await query.edit_message_text("❌ Песня не найдена")
        except Exception as e:
            logger.error(f"Ошибка при редактировании песни: {e}")
            await query.edit_message_text("❌ Произошла ошибка")
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
                await query.edit_message_text("❌ Песня не найдена")
        except Exception as e:
            logger.error(f"Ошибка при удалении песни: {e}")
            await query.edit_message_text("❌ Произошла ошибка")
        finally:
            db.close()
            
    elif query.data == "back_to_results":
        await query.delete_message()
        # Здесь можно реализовать возврат к предыдущим результатам поиска
        # если сохранять их в context.user_data

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(ADMIN_API_TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Регистрация обработчиков кнопок меню
    application.add_handler(MessageHandler(filters.Text(["Добавить песню"]), add_song_handler))
    application.add_handler(MessageHandler(filters.Text(["Поиск по названию"]), search_title_handler))
    application.add_handler(MessageHandler(filters.Text(["Поиск по тексту"]), search_text_handler))
    application.add_handler(MessageHandler(filters.Text(["Поиск по месту"]), search_place_handler))
    application.add_handler(MessageHandler(filters.Text(["Список всех песен"]), list_songs_handler))
    application.add_handler(MessageHandler(filters.Text(["Редактировать"]), update_song_handler))
    application.add_handler(MessageHandler(filters.Text(["Удалить"]), delete_song_handler))
    application.add_handler(MessageHandler(filters.Text(["Помощь"]), help_command))
    application.add_handler(MessageHandler(filters.Text(["◀ Назад"]), cancel_action))
    application.add_handler(MessageHandler(filters.Text(["✅ Да, удалить"]), confirm_delete))
    application.add_handler(MessageHandler(filters.Text(["❌ Нет, отменить"]), cancel_action))

    # Регистрация обработчиков сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Регистрация обработчиков callback-запросов
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()