import logging
import random
import json
import uuid # Добавлено для генерации уникальных ID игр
import os # Добавлено для работы с путями
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, User, CallbackQuery, error as telegram_error # Импортируем telegram.error, User, CallbackQuery
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, PicklePersistence

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Имя пользователя вашего бота (без @) - ЗАМЕНИТЕ НА ВАШЕ!
BOT_USERNAME = "Krestiki_Nolik_iBot" # <--- ЗАМЕНИТЕ НА ИМЯ ПОЛЬЗОВАТЕЛЯ ВАШЕГО БОТА

# --- ИЗМЕНЕНИЕ НАЧАТО ---
# Абсолютный путь к файлу таблицы лидеров
LEADERBOARD_FILE_PATH = '/kubok758/Krestiki_Nolik_iBot/leaderboard.json'
# --- ИЗМЕНЕНИЕ ОКОНЧЕНО ---

# Вспомогательная функция для обеспечения полной структуры данных пользователя
def get_complete_user_data(user_data_from_file, current_username_or_fallback):
    if user_data_from_file is None:
        return {
            'username': current_username_or_fallback,
            'total': {'wins': 0, 'losses': 0, 'draws': 0},
            'easy': {'wins': 0, 'losses': 0, 'draws': 0},
            'medium': {'wins': 0, 'losses': 0, 'draws': 0},
            'hard': {'wins': 0, 'losses': 0, 'draws': 0}
        }
    username_to_use = user_data_from_file.get('username', current_username_or_fallback)
    complete_data = {
        'username': username_to_use,
        'total': {
            'wins': user_data_from_file.get('total', {}).get('wins', 0),
            'losses': user_data_from_file.get('total', {}).get('losses', 0),
            'draws': user_data_from_file.get('total', {}).get('draws', 0),
        }
    }
    for mode in ['easy', 'medium', 'hard']:
        complete_data[mode] = {
            'wins': user_data_from_file.get(mode, {}).get('wins', 0),
            'losses': user_data_from_file.get(mode, {}).get('losses', 0),
            'draws': user_data_from_file.get(mode, {}).get('draws', 0),
        }
    return complete_data

# --- ИЗМЕНЕНИЕ НАЧАТО ---
def load_leaderboard():
    try:
        # Проверяем, существует ли директория, если нет - это не критично для чтения,
        # но важно для понимания, почему файл может отсутствовать.
        leaderboard_dir = os.path.dirname(LEADERBOARD_FILE_PATH)
        if not os.path.exists(leaderboard_dir):
            logger.warning(f"Директория для таблицы лидеров '{leaderboard_dir}' не существует.")
            return {} # Если директории нет, то и файла там быть не может

        with open(LEADERBOARD_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Таблица лидеров успешно загружена из '{LEADERBOARD_FILE_PATH}'.")
            return data
    except FileNotFoundError:
        logger.info(f"Файл таблицы лидеров '{LEADERBOARD_FILE_PATH}' не найден. Будет создан новый при первом сохранении.")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Ошибка декодирования JSON из файла '{LEADERBOARD_FILE_PATH}'. Возвращена пустая таблица. ПРОВЕРЬТЕ СОДЕРЖИМОЕ ФАЙЛА!")
        # В качестве меры предосторожности, можно бэкапить "сломанный" файл
        # import shutil
        # broken_file_path = LEADERBOARD_FILE_PATH + ".broken." + str(uuid.uuid4())[:8]
        # try:
        #     shutil.copy(LEADERBOARD_FILE_PATH, broken_file_path)
        #     logger.info(f"Поврежденный файл таблицы лидеров сохранен как '{broken_file_path}'.")
        # except Exception as e_backup:
        #     logger.error(f"Не удалось забэкапить поврежденный файл таблицы лидеров: {e_backup}")
        return {}
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при загрузке таблицы лидеров из '{LEADERBOARD_FILE_PATH}': {e}")
        return {}

def save_leaderboard(data):
    try:
        # Убедимся, что директория для файла существует
        leaderboard_dir = os.path.dirname(LEADERBOARD_FILE_PATH)
        if not os.path.exists(leaderboard_dir):
            os.makedirs(leaderboard_dir)
            logger.info(f"Создана директория для таблицы лидеров: '{leaderboard_dir}'")

        with open(LEADERBOARD_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Таблица лидеров успешно сохранена в '{LEADERBOARD_FILE_PATH}'.")
    except PermissionError as e:
        logger.error(f"Ошибка прав доступа при сохранении таблицы лидеров в '{LEADERBOARD_FILE_PATH}': {e}. Проверьте права на запись для бота.")
    except Exception as e:
        logger.error(f"Не удалось сохранить таблицу лидеров в '{LEADERBOARD_FILE_PATH}': {e}")
# --- ИЗМЕНЕНИЕ ОКОНЧЕНО ---

def update_leaderboard(user_id: int, username: str, result: str, difficulty: str):
    leaderboard = load_leaderboard()
    user_id_str = str(user_id)
    raw_user_data_from_file = leaderboard.get(user_id_str)
    user_data = get_complete_user_data(raw_user_data_from_file, username)
    user_data['username'] = username # Обновляем имя пользователя на случай, если оно изменилось

    if result == 'win':
        user_data['total']['wins'] += 1
    elif result == 'loss':
        user_data['total']['losses'] += 1
    elif result == 'draw':
        user_data['total']['draws'] += 1

    # Обновление статистики для конкретного режима сложности (easy, medium, hard)
    # Игры 2P (если бы они вызывали эту функцию с difficulty='2_player') не будут здесь обновлены,
    # так как '2_player' нет в user_data по умолчанию из get_complete_user_data
    # и комментарий в коде ("Games via link won't call this function") это подтверждает.
    if difficulty in user_data:
        if result == 'win':
            user_data[difficulty]['wins'] += 1
        elif result == 'loss':
            user_data[difficulty]['losses'] += 1
        elif result == 'draw':
            user_data[difficulty]['draws'] += 1

    leaderboard[user_id_str] = user_data
    save_leaderboard(leaderboard)

class TicTacToe:
    def __init__(self, player_symbol, difficulty): # difficulty can be '2_player'
        self.board = [[' ' for _ in range(3)] for _ in range(3)]
        self.player_symbol = player_symbol # For AI games: human, For 2P: player1 (❌)
        self.bot_symbol = '⭕' if player_symbol == '❌' else '❌' # For AI games: bot, For 2P: player2 (⭕)
        self.current_turn = '❌' # Always start with X
        self.difficulty = difficulty # 'easy', 'medium', 'hard', or '2_player'

    def make_move(self, row, col, symbol):
        if self.board[row][col] == ' ':
            self.board[row][col] = symbol
            return True
        return False

    def check_winner(self):
        lines = [
            [self.board[0][0], self.board[0][1], self.board[0][2]],
            [self.board[1][0], self.board[1][1], self.board[1][2]],
            [self.board[2][0], self.board[2][1], self.board[2][2]],
            [self.board[0][0], self.board[1][0], self.board[2][0]],
            [self.board[0][1], self.board[1][1], self.board[2][1]],
            [self.board[0][2], self.board[1][2], self.board[2][2]],
            [self.board[0][0], self.board[1][1], self.board[2][2]],
            [self.board[0][2], self.board[1][1], self.board[2][0]],
        ]
        for line in lines:
            if line[0] == line[1] == line[2] != ' ':
                return line[0]
        return 'draw' if all(cell != ' ' for row in self.board for cell in row) else None

    def minimax(self, depth, is_maximizing):
        # Minimax is only relevant for AI difficulties
        result = self.check_winner()
        # In minimax, self.bot_symbol is the AI, self.player_symbol is the opponent (human)
        if result == self.bot_symbol: # AI wins
            return 1
        if result == self.player_symbol: # Human wins
            return -1
        if result == 'draw':
            return 0

        if is_maximizing: # AI's turn (bot_symbol)
            best_score = -float('inf')
            for i in range(3):
                for j in range(3):
                    if self.board[i][j] == ' ':
                        self.board[i][j] = self.bot_symbol
                        score = self.minimax(depth + 1, False)
                        self.board[i][j] = ' '
                        best_score = max(score, best_score)
            return best_score
        else: # Human's turn (player_symbol)
            best_score = float('inf')
            for i in range(3):
                for j in range(3):
                    if self.board[i][j] == ' ':
                        self.board[i][j] = self.player_symbol
                        score = self.minimax(depth + 1, True)
                        self.board[i][j] = ' '
                        best_score = min(score, best_score)
            return best_score

    def get_best_move(self):
        # This is only for AI
        if self.difficulty == 'easy':
            empty_cells = [(i, j) for i in range(3) for j in range(3) if self.board[i][j] == ' ']
            return random.choice(empty_cells) if empty_cells else None
        elif self.difficulty == 'medium':
            if random.random() < 0.5: # 50% шанс случайного хода
                empty_cells = [(i, j) for i in range(3) for j in range(3) if self.board[i][j] == ' ']
                if empty_cells:
                    return random.choice(empty_cells)
        # For hard or the other 50% of medium
        best_score = -float('inf')
        best_move = None
        empty_cells = [(i, j) for i in range(3) for j in range(3) if self.board[i][j] == ' ']
        if not empty_cells: return None

        for i, j in empty_cells:
            self.board[i][j] = self.bot_symbol # AI makes a hypothetical move
            score = self.minimax(0, False) # False because next turn is human's (minimizing)
            self.board[i][j] = ' '
            if score > best_score:
                best_score = score
                best_move = (i, j)

        if best_move is None and empty_cells: # Fallback if minimax yields no preference
            return random.choice(empty_cells)
        return best_move

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        game_id = args[0]
        if await handle_join_game(update, context, game_id):
            return

    keyboard = [
        [InlineKeyboardButton("Играть!", callback_data='play')],
        [InlineKeyboardButton("Статистика", callback_data='stats')],
        [InlineKeyboardButton("🏆 Лидеры", callback_data='leaderboard_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(
            "Привет! Я бот для игры в Крестики-Нолики.\nВыберите действие:",
            reply_markup=reply_markup
        )
    elif update.callback_query:
         await update.callback_query.edit_message_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )

async def handle_join_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id: str):
    if 'pending_games' not in context.bot_data:
        context.bot_data['pending_games'] = {}
    if 'active_games' not in context.bot_data:
        context.bot_data['active_games'] = {}

    pending_game_details = context.bot_data['pending_games'].get(game_id)
    if not pending_game_details:
        if update.message:
            await update.message.reply_text("Игра не найдена или уже началась.")
        return False

    player2 = update.effective_user
    if player2.id == pending_game_details['player1_id']:
        if update.message:
            await update.message.reply_text("Вы не можете присоединиться к своей же игре. Поделитесь ссылкой с другом.")
        await start(update, context) # Возврат в главное меню или начальное состояние
        return True # Указываем, что обработка завершена

    player2_username = player2.username or player2.full_name or player2.first_name or f"User_{player2.id}"
    player1_username = pending_game_details['player1_username']

    game_instance = TicTacToe(player_symbol='❌', difficulty='2_player') # Player1 всегда ❌

    active_game_details = {
        'player1_id': pending_game_details['player1_id'],
        'player1_username': player1_username,
        'player1_chat_id': pending_game_details['player1_chat_id'],
        'player1_message_id': pending_game_details['player1_initial_message_id'],
        'player1_symbol': '❌',
        'player2_id': player2.id,
        'player2_username': player2_username,
        'player2_chat_id': update.effective_chat.id,
        'player2_message_id': None, # Будет установлено после отправки доски
        'player2_symbol': '⭕',
        'game': game_instance,
        'current_player_id': pending_game_details['player1_id'], # P1 (❌) ходит первым
        'game_mode': '2_player' # Указываем режим игры
    }
    context.bot_data['active_games'][game_id] = active_game_details
    if game_id in context.bot_data['pending_games']: # Проверка перед удалением
        del context.bot_data['pending_games'][game_id]

    # Обновление сообщения для игрока 1
    text_for_p1 = f"Игрок @{player2_username} присоединился!\nИгра против @{player2_username}.\nВаш ход (❌)."
    await send_or_edit_2p_board(context, game_id, active_game_details['player1_chat_id'], active_game_details['player1_message_id'], text_for_p1, is_edit=True)

    # Отправка доски игроку 2
    text_for_p2 = f"Вы присоединились к игре @{player1_username}!\nИгра против @{player1_username}.\nХод @{player1_username} (❌)."
    await send_or_edit_2p_board(context, game_id, active_game_details['player2_chat_id'], None, text_for_p2, is_edit=False) # Отправляем новое сообщение

    return True


async def send_or_edit_2p_board(context: ContextTypes.DEFAULT_TYPE, game_id: str, chat_id: int, message_id: int | None, text: str, is_edit: bool):
    active_games = context.bot_data.get('active_games', {}) # Безопасное получение
    if game_id not in active_games: # Проверка существования игры
        logger.warning(f"Attempted to send/edit board for non-existent/inactive 2P game: {game_id} for chat {chat_id}")
        try:
            # Уведомляем игрока, что игра неактивна, если пытаемся отредактировать его сообщение
            if is_edit and message_id:
                 await context.bot.edit_message_text("Эта игра была отменена или завершена.", chat_id=chat_id, message_id=message_id, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("В главное меню", callback_data='main_menu')]]))
            # Если это новая отправка для игры, которой нет, то просто логируем, т.к. это может быть race condition при завершении игры
        except telegram_error.BadRequest as e: # Сообщение могло быть уже удалено
            logger.info(f"Message {message_id} in chat {chat_id} for game {game_id} not found for editing about ended game: {e}")
        except Exception as e: # Другие ошибки
            logger.error(f"Error notifying player in chat {chat_id} about ended 2P game {game_id}: {e}")
        return

    game_details = active_games[game_id]
    game = game_details['game']

    keyboard_layout = []
    for i in range(3):
        row_buttons = []
        for j in range(3):
            cell_text = game.board[i][j] if game.board[i][j] != ' ' else '⬜'
            # В callback_data добавляем game_id для идентификации игры
            row_buttons.append(InlineKeyboardButton(cell_text, callback_data=f'2p_move_{i}_{j}_{game_id}'))
        keyboard_layout.append(row_buttons)

    keyboard_layout.append([InlineKeyboardButton("🏳️ Сдаться", callback_data=f'surrender_2p_{game_id}')])
    reply_markup = InlineKeyboardMarkup(keyboard_layout)

    try:
        if is_edit and message_id:
            sent_message = await context.bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
        else:
            sent_message = await context.bot.send_message(chat_id, text, reply_markup=reply_markup)

        # Сохраняем message_id для последующих обновлений доски
        if chat_id == game_details['player1_chat_id']:
            game_details['player1_message_id'] = sent_message.message_id
        elif chat_id == game_details['player2_chat_id']:
            game_details['player2_message_id'] = sent_message.message_id
    except telegram_error.BadRequest as e:
        logger.error(f"BadRequest sending/editing 2P board for game {game_id}, chat {chat_id}, msg {message_id}: {e}. Text: {text}")
        # Если сообщение не найдено, возможно, игрок его удалил или заблокировал бота
        if "message to edit not found" in str(e).lower() or "chat not found" in str(e).lower() or "bot was blocked by the user" in str(e).lower() :
            logger.warning(f"Player in chat {chat_id} might have blocked bot or deleted message for game {game_id}.")
            # Уведомить другого игрока и завершить игру
            if game_id in context.bot_data.get('active_games', {}): # Проверяем, существует ли игра еще
                other_player_chat_id = game_details['player2_chat_id'] if chat_id == game_details['player1_chat_id'] else game_details['player1_chat_id']
                other_player_message_id = game_details['player2_message_id'] if chat_id == game_details['player1_chat_id'] else game_details['player1_message_id']
                try:
                    fallback_text_other = "Соперник не может получить обновление игры (возможно, заблокировал бота или удалил чат). Игра завершена."
                    if other_player_message_id:
                        await context.bot.edit_message_text(fallback_text_other, chat_id=other_player_chat_id, message_id=other_player_message_id, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("В главное меню", callback_data='main_menu')]]))
                    else: # Если у другого игрока еще не было сообщения (маловероятно)
                        await context.bot.send_message(other_player_chat_id, fallback_text_other, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("В главное меню", callback_data='main_menu')]]))
                except Exception as e_inner:
                    logger.error(f"Error notifying other player of communication failure: {e_inner}")
                if game_id in context.bot_data.get('active_games', {}): # Повторная проверка перед удалением
                     del context.bot_data['active_games'][game_id] # Завершаем игру
    except Exception as e: # Другие неожиданные ошибки
        logger.error(f"Unexpected error sending/editing 2P board for game {game_id}, chat {chat_id}: {e}")
        # Общая логика обработки ошибок, возможно, также завершение игры
        if game_id in context.bot_data.get('active_games', {}): # Проверяем, существует ли игра еще
            try:
                p1_chat_id_err = context.bot_data['active_games'][game_id]['player1_chat_id']
                p2_chat_id_err = context.bot_data['active_games'][game_id]['player2_chat_id']
                # Отправляем новые сообщения, т.к. редактирование могло вызвать ошибку
                await context.bot.send_message(p1_chat_id_err, "Произошла ошибка в игре. Игра завершена.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("В главное меню", callback_data='main_menu')]]))
                await context.bot.send_message(p2_chat_id_err, "Произошла ошибка в игре. Игра завершена.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("В главное меню", callback_data='main_menu')]]))
            except Exception as final_err:
                logger.error(f"Failed to notify players of critical game error: {final_err}")
            if game_id in context.bot_data.get('active_games', {}): # Повторная проверка перед удалением
                del context.bot_data['active_games'][game_id]


async def handle_2p_game_over(context: ContextTypes.DEFAULT_TYPE, game_id: str, winner_symbol_or_draw: str):
    active_games = context.bot_data.get('active_games', {})
    if game_id not in active_games:
        logger.warning(f"Attempted to handle game over for non-existent 2P game: {game_id}")
        return

    game_details = active_games[game_id]
    game_obj: TicTacToe = game_details['game'] # Явно указываем тип для подсказок

    p1_chat_id = game_details['player1_chat_id']
    p2_chat_id = game_details['player2_chat_id']
    p1_msg_id = game_details['player1_message_id']
    p2_msg_id = game_details['player2_message_id']

    text_p1, text_p2 = "", ""

    if winner_symbol_or_draw == 'draw':
        result_text = "🤝 Ничья!"
        text_p1 = result_text
        text_p2 = result_text
    elif winner_symbol_or_draw == game_details['player1_symbol']: # P1 (❌) победил
        text_p1 = f"🎉 Вы победили @{game_details['player2_username']}!"
        text_p2 = f"💀 Вы проиграли @{game_details['player1_username']}."
    elif winner_symbol_or_draw == game_details['player2_symbol']: # P2 (⭕) победил
        text_p1 = f"💀 Вы проиграли @{game_details['player2_username']}."
        text_p2 = f"🎉 Вы победили @{game_details['player1_username']}!"
    else: # Не должно происходить, например, если кто-то сдался и передал не символ
        logger.error(f"Unknown winner symbol in 2P game over: {winner_symbol_or_draw} for game {game_id}")
        text_p1 = "Игра завершена." # Общее сообщение
        text_p2 = "Игра завершена."

    # Формирование отображения финальной доски
    final_board_text_display = "\n\nФинальная доска:\n"
    for r_idx in range(3):
        row_display = [game_obj.board[r_idx][c_idx] if game_obj.board[r_idx][c_idx] != ' ' else '⬜' for c_idx in range(3)]
        final_board_text_display += " ".join(row_display) + "\n"

    # Клавиатура для финальной доски (неинтерактивная)
    final_board_keyboard_list = []
    for i in range(3):
        row_btns = [InlineKeyboardButton(game_obj.board[i][j] if game_obj.board[i][j] != ' ' else '⬜', callback_data='game_over_cell') for j in range(3)]
        final_board_keyboard_list.append(row_btns)
    final_reply_markup = InlineKeyboardMarkup(final_board_keyboard_list)

    # Кнопки для действий после игры
    menu_after_game_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Играть снова (с ботом)", callback_data='play')], # Предлагаем общие опции
        [InlineKeyboardButton("Создать новую игру (2 игрока)", callback_data='play_2p_link')],
        [InlineKeyboardButton("В главное меню", callback_data='main_menu')]
    ])

    # Вспомогательная функция для отправки/редактирования сообщений об окончании игры
    async def send_final_message(chat_id, message_id, text_result, board_display, board_markup, menu_markup):
        full_message_text = f"{text_result}{board_display}"
        try:
            if message_id: # Если есть message_id, пытаемся редактировать
                await context.bot.edit_message_text(
                    full_message_text,
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=board_markup # Показываем финальную доску
                )
            else: # Если message_id нет (например, игрок 2 еще не получил доску)
                 await context.bot.send_message(chat_id, full_message_text, reply_markup=board_markup)
            # Отправляем меню "Что дальше?" новым сообщением
            await context.bot.send_message(chat_id, "Что дальше?", reply_markup=menu_markup)
        except telegram_error.BadRequest as e_bad_req:
            logger.warning(f"BadRequest sending/editing game over to chat {chat_id} for game {game_id}: {e_bad_req}. Retrying with send_message.")
            try: # Фоллбэк: отправить все новыми сообщениями, если редактирование не удалось
                await context.bot.send_message(chat_id, full_message_text, reply_markup=board_markup)
                await context.bot.send_message(chat_id, "Что дальше?", reply_markup=menu_markup)
            except Exception as e_send_fallback:
                logger.error(f"Fallback send_message error to chat {chat_id} for game {game_id}: {e_send_fallback}")
        except Exception as e:
            logger.error(f"Generic error sending/editing game over to chat {chat_id} for game {game_id}: {e}")


    # Отправка результатов обоим игрокам
    await send_final_message(p1_chat_id, p1_msg_id, text_p1, final_board_text_display, final_reply_markup, menu_after_game_kb)
    await send_final_message(p2_chat_id, p2_msg_id, text_p2, final_board_text_display, final_reply_markup, menu_after_game_kb)

    # Удаление игры из активных
    if game_id in context.bot_data.get('active_games', {}): # Проверяем еще раз перед удалением
        del context.bot_data['active_games'][game_id]


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # Пытаемся ответить на запрос как можно раньше
        await query.answer()
    except telegram_error.BadRequest as e:
        # Логируем ошибку, если ответ не удался (например, запрос устарел)
        logger.warning(f"Не удалось ответить на callback query (ID: {query.id}): {e}. Продолжаем обработку.")
        # Бот все равно должен попытаться обработать данные, если они есть

    user = query.from_user
    current_display_name = user.username or user.full_name or user.first_name or f"User_{user.id}"

    # Инициализация хранилищ, если их нет (на всякий случай)
    if 'pending_games' not in context.bot_data:
        context.bot_data['pending_games'] = {}
    if 'active_games' not in context.bot_data:
        context.bot_data['active_games'] = {}

    # Обработка конкретных callback_data
    if query.data == 'play':
        keyboard = [
            [InlineKeyboardButton("Играть за ❌", callback_data='choose_x')],
            [InlineKeyboardButton("Играть за ⭕", callback_data='choose_o')],
            [InlineKeyboardButton("2 игрока (по ссылке)", callback_data='play_2p_link')],
            [InlineKeyboardButton("Назад", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите сторону или режим:", reply_markup=reply_markup)
        return # <<< Явный выход

    elif query.data == 'play_2p_link':
        game_id = str(uuid.uuid4()) # Генерируем уникальный ID для игры
        if BOT_USERNAME == "YOUR_BOT_USERNAME" or not BOT_USERNAME: # Проверка на случай, если не заменено
            logger.error("BOT_USERNAME не настроен правильно в коде!")
            # await query.answer("Ошибка конфигурации бота. Не удалось создать ссылку.", show_alert=True) # query.answer уже был вызван
            try:
                await query.edit_message_text(
                    "Ошибка конфигурации бота. Свяжитесь с администратором.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("В главное меню", callback_data='main_menu')]])
                )
            except Exception as e_conf:
                logger.error(f"Не удалось даже отправить сообщение об ошибке конфигурации: {e_conf}")
            return # <<< Явный выход

        invite_link = f"https://t.me/{BOT_USERNAME}?start={game_id}"
        text = (
            f"Вы создали игру\\! Вы играете за ❌\\.\n"
            f"Отправьте эту ссылку второму игроку:\n\n"
            f"`{invite_link}`\n\n"
            f"Ожидание второго игрока\\.\\.\\."
        )
        share_button = InlineKeyboardButton("🔗 Отправить другу", url=f"https://t.me/share/url?url={invite_link}&text=Сыграем в крестики-нолики?")
        cancel_button = InlineKeyboardButton("Отменить создание", callback_data=f'cancel_pending_{game_id}')
        reply_markup = InlineKeyboardMarkup([[share_button], [cancel_button]])

        try:
            sent_message = await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='MarkdownV2')
            # Сохраняем информацию об ожидающей игре
            if 'pending_games' not in context.bot_data: context.bot_data['pending_games'] = {} # Дополнительная проверка
            context.bot_data['pending_games'][game_id] = {
                'player1_id': user.id, 'player1_username': current_display_name,
                'player1_chat_id': query.message.chat_id, 'player1_initial_message_id': sent_message.message_id,
                'invite_link': invite_link
            }
        except telegram_error.BadRequest as e: # Ошибка парсинга MarkdownV2
            logger.error(f"Ошибка парсинга MarkdownV2: {e}. Текст был: '{text}'")
            # Попытка отправить без MarkdownV2
            fallback_text = (
                f"Вы создали игру! Вы играете за X.\n"
                f"Отправьте эту ссылку второму игроку:\n\n{invite_link}\n\n"
                f"Ожидание второго игрока..."
            )
            try:
                sent_message = await query.edit_message_text(fallback_text, reply_markup=reply_markup) # Без parse_mode
                if 'pending_games' not in context.bot_data: context.bot_data['pending_games'] = {}
                context.bot_data['pending_games'][game_id] = {
                    'player1_id': user.id, 'player1_username': current_display_name,
                    'player1_chat_id': query.message.chat_id, 'player1_initial_message_id': sent_message.message_id,
                    'invite_link': invite_link
                }
            except Exception as fallback_e:
                logger.error(f"Ошибка при отправке запасного варианта (без MarkdownV2): {fallback_e}")
                # await query.answer("Произошла серьезная ошибка при создании игры.", show_alert=True) # query.answer уже был
        except Exception as ex: # Другие непредвиденные ошибки
            logger.error(f"Непредвиденная ошибка при создании игры по ссылке: {ex}")
            # await query.answer("Произошла ошибка при создании игры.", show_alert=True) # query.answer уже был
        return # <<< Явный выход

    elif query.data.startswith('cancel_pending_'):
        game_id_to_cancel = query.data.split('_')[2] # Получаем game_id из callback_data
        pending_games = context.bot_data.get('pending_games', {})
        if game_id_to_cancel in pending_games:
            # Убедимся, что отменяет создатель игры
            if pending_games[game_id_to_cancel]['player1_id'] == user.id:
                del context.bot_data['pending_games'][game_id_to_cancel]
                await query.edit_message_text("Создание игры отменено.")
                # Возвращаем в главное меню новым сообщением, т.к. edit_message_text уже использован
                keyboard = [
                    [InlineKeyboardButton("Играть!", callback_data='play')],
                    [InlineKeyboardButton("Статистика", callback_data='stats')],
                    [InlineKeyboardButton("🏆 Лидеры", callback_data='leaderboard_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text("Выберите действие:", reply_markup=reply_markup) # Используем reply_text
            else:
                # await query.answer("Это не ваша игра для отмены.", show_alert=True) # query.answer уже был
                # Можно отправить alert через context.bot.answer_callback_query если нужно показать его
                await context.bot.answer_callback_query(query.id, "Это не ваша игра для отмены.", show_alert=True)
        else:
            await query.edit_message_text("Эта игра уже неактивна для отмены.") # Могла быть начата или уже отменена
        return # <<< Явный выход

    elif query.data == 'stats':
        leaderboard = load_leaderboard()
        user_id_str = str(user.id)
        raw_user_data_from_file = leaderboard.get(user_id_str) # Получаем "сырые" данные
        # Используем get_complete_user_data для обеспечения полной структуры и дефолтных значений
        user_data_for_display = get_complete_user_data(raw_user_data_from_file, current_display_name)

        text = "📊 Ваша статистика:\n"
        text += (f"\nВсего игр:\n"
                 f"🏆 Побед: {user_data_for_display['total']['wins']}\n"
                 f"💀 Поражений: {user_data_for_display['total']['losses']}\n"
                 f"🤝 Ничьих: {user_data_for_display['total']['draws']}\n")

        modes = {'easy': 'Лёгкий 🐢', 'medium': 'Средний 🚶', 'hard': 'Сложный 🔥'}
        for mode_key, mode_name in modes.items():
            stats = user_data_for_display[mode_key] # user_data_for_display гарантированно содержит эти ключи
            text += f"\nРежим {mode_name}:\n🏆 {stats['wins']} | 💀 {stats['losses']} | 🤝 {stats['draws']}\n"

        keyboard = [[InlineKeyboardButton("Назад", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return # <<< Явный выход

    elif query.data == 'main_menu':
        # Очистка состояния игры с ботом, если оно было
        if 'game' in context.user_data: del context.user_data['game']
        if 'selected_symbol' in context.user_data: del context.user_data['selected_symbol']
        if 'game_mode' in context.user_data: del context.user_data['game_mode']
        # Не очищаем bot_data здесь, так как там могут быть активные 2P игры

        keyboard = [
            [InlineKeyboardButton("Играть!", callback_data='play')],
            [InlineKeyboardButton("Статистика", callback_data='stats')],
            [InlineKeyboardButton("🏆 Лидеры", callback_data='leaderboard_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите действие:", reply_markup=reply_markup)
        return # <<< Явный выход

    elif query.data == 'leaderboard_menu':
        keyboard = [
            [InlineKeyboardButton("🏆 Лидеры 'Лёгкий'", callback_data='leaderboard_easy')],
            [InlineKeyboardButton("🏆 Лидеры 'Средний'", callback_data='leaderboard_medium')],
            [InlineKeyboardButton("🏆 Лидеры 'Сложный'", callback_data='leaderboard_hard')],
            [InlineKeyboardButton("🏅 Общий рейтинг", callback_data='leaderboard_total')],
            [InlineKeyboardButton("Назад", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите список лидеров:", reply_markup=reply_markup)
        return # <<< Явный выход

    elif query.data.startswith('leaderboard_'):
        difficulty_map = {
            'leaderboard_easy': ('easy', "Лёгкий 🐢"), 'leaderboard_medium': ('medium', "Средний 🚶"),
            'leaderboard_hard': ('hard', "Сложный 🔥"), 'leaderboard_total': ('total', "Общий рейтинг")
        }
        mode_key, mode_name = difficulty_map.get(query.data, (None, None))

        if not mode_key: # На случай если callback_data не соответствует ключам
            logger.warning(f"Неизвестный leaderboard_ callback: {query.data}")
            await query.edit_message_text("Неверный выбор списка лидеров.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='leaderboard_menu')]]))
            return # <<< Явный выход

        leaderboard_data = load_leaderboard()
        # Обрабатываем данные, чтобы убедиться в полноте структуры для каждого пользователя
        processed_leaderboard_values = []
        for user_id_key, raw_user_entry in leaderboard_data.items():
            # current_display_name здесь не очень подходит, так как это данные из файла,
            # а не текущего пользователя. Используем имя из файла или fallback.
            username_fallback = raw_user_entry.get('username', f"User_{user_id_key}")
            complete_entry = get_complete_user_data(raw_user_entry, username_fallback)
            # Убедимся, что mode_key (например, 'total') существует с дефолтной структурой,
            # если get_complete_user_data его не создал (хотя должен был для 'total', 'easy', etc.)
            if mode_key not in complete_entry:
                complete_entry[mode_key] = {'wins': 0, 'losses': 0, 'draws': 0}
            processed_leaderboard_values.append(complete_entry)


        # Сортировка: сначала по победам (убывание), потом по ничьим (убывание), потом по поражениям (возрастание)
        sorted_users = sorted(
            processed_leaderboard_values,
            key=lambda x: (-x[mode_key]['wins'], -x[mode_key]['draws'], x[mode_key]['losses'])
        )[:10] # Берем топ-10

        text = f"🏆 Топ игроков - Режим: {mode_name}\n\n"
        if not sorted_users or all(user_stat[mode_key]['wins'] == 0 and user_stat[mode_key]['draws'] == 0 and user_stat[mode_key]['losses'] == 0 for user_stat in sorted_users):
            text = f"Пока здесь пусто для режима '{mode_name}'. Сыграйте и займите первое место!"
        else:
            has_entries = False
            for i, user_stat in enumerate(sorted_users, 1):
                # Показываем пользователя, даже если у него 0 во всех категориях, если это Общий рейтинг или он есть в списке
                # Для режимов easy/medium/hard, если все нули, можно пропустить, если это не единственный результат.
                # Однако, если пользователь попал в топ-10, значит у него есть какие-то данные.
                # Проверяем, что хотя бы одна из стат не ноль, чтобы не выводить пустые строки, если такое возможно
                if user_stat[mode_key]['wins'] == 0 and user_stat[mode_key]['draws'] == 0 and user_stat[mode_key]['losses'] == 0 and mode_key != 'total':
                     # Для 'total' показываем всегда, если попал в топ
                     # Для других режимов - если все нули, можно было бы пропустить, но если он в топ-10, то пусть будет
                     pass # Не пропускаем, если уже отсортировано

                has_entries = True # Если хоть кто-то есть, ставим флаг
                text += (f"{i}. {user_stat['username']} — "
                         f"🏆{user_stat[mode_key]['wins']} | "
                         f"🤝{user_stat[mode_key]['draws']} | "
                         f"💀{user_stat[mode_key]['losses']}\n")
            if not has_entries: # Если после фильтрации (если бы она была строже) ничего не осталось
                 text = f"Пока здесь пусто для режима '{mode_name}'. Сыграйте и займите первое место!"


        keyboard = [[InlineKeyboardButton("Назад к выбору лидеров", callback_data='leaderboard_menu')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return # <<< Явный выход

    elif query.data in ['choose_x', 'choose_o']:
        context.user_data['selected_symbol'] = '❌' if query.data == 'choose_x' else '⭕'
        keyboard = [
            [
                InlineKeyboardButton("Лёгкий 🐢", callback_data='difficulty_easy'),
                InlineKeyboardButton("Средний 🚶", callback_data='difficulty_medium'),
                InlineKeyboardButton("Сложный 🔥", callback_data='difficulty_hard')
            ],
            [InlineKeyboardButton("Назад", callback_data='play')] # Кнопка "Назад" на выбор символа/режима
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите уровень сложности:", reply_markup=reply_markup)
        return # <<< Явный выход

    elif query.data.startswith('difficulty_'): # Начало игры с ботом
        difficulty = query.data.split('_')[1]
        symbol = context.user_data.get('selected_symbol')
        if not symbol:
            # Это состояние не должно достигаться, если пользователь следовал по кнопкам
            await query.edit_message_text("Ошибка: символ не выбран. Пожалуйста, начните заново.",
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("В главное меню", callback_data='main_menu')]]))
            return # <<< Явный выход
        game = TicTacToe(symbol, difficulty)
        context.user_data['game'] = game
        context.user_data['game_mode'] = 'vs_bot' # Указываем режим игры (против бота)

        if symbol == '⭕': # Если игрок выбрал 'O', бот (X) ходит первым
            await bot_move(query, context) # query здесь это callback_query от выбора сложности
        else: # Игрок выбрал 'X', он ходит первым
            await draw_board(query, context) # query здесь это callback_query от выбора сложности
        return # <<< Явный выход

    elif query.data.startswith('move_'): # Ход в игре с ботом (1 игрок)
        game = context.user_data.get('game')
        # Проверяем, что игра существует и это игра с ботом
        if not game or context.user_data.get('game_mode') != 'vs_bot':
            await query.edit_message_text("Игра не найдена или это не ваша игра с ботом. Начните новую.",
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("В главное меню", callback_data='main_menu')]]))
            return # <<< Явный выход

        if game.current_turn != game.player_symbol:
            # await query.answer("Сейчас не ваш ход!") # query.answer уже был
            await context.bot.answer_callback_query(query.id, "Сейчас не ваш ход!", show_alert=True)
            return # <<< Явный выход
        try:
            _, row_str, col_str = query.data.split('_')
            row, col = int(row_str), int(col_str)
        except ValueError:
            logger.error(f"Неверный формат callback_data для хода: {query.data}")
            # await query.answer("Ошибка данных хода.", show_alert=True) # query.answer уже был
            return # <<< Явный выход

        if game.board[row][col] != ' ':
            # await query.answer("Эта клетка уже занята!") # query.answer уже был
            await context.bot.answer_callback_query(query.id, "Эта клетка уже занята!", show_alert=True)
            return # <<< Явный выход

        if game.make_move(row, col, game.player_symbol):
            winner = game.check_winner()
            if winner:
                await handle_game_over(query, context, winner) # Передаем query
                return # <<< Явный выход
            # Если победителя нет, ход переходит к боту
            game.current_turn = game.bot_symbol
            await bot_move(query, context) # Передаем query
        # else: # Ход не сделан (клетка занята) - уже обработано выше
        return # <<< Явный выход

    elif query.data.startswith('2p_move_'): # Ход в игре на двоих
        try:
            # Ожидаемый формат: '2p_move_ROW_COL_GAMEID'
            parts = query.data.split('_')
            if len(parts) != 5 or parts[0] != '2p' or parts[1] != 'move': # Проверка формата
                logger.error(f"Неверный формат callback_data для 2p_move: {query.data}")
                await context.bot.answer_callback_query(query.id, "Ошибка данных хода.", show_alert=True)
                return # <<< Явный выход

            action_prefix, move_token, row_str, col_str, game_id = parts
            row = int(row_str)
            col = int(col_str)
        except ValueError: # Если row/col не числа
            logger.error(f"Не удалось разобрать row/col/game_id из 2p_move: {query.data}")
            await context.bot.answer_callback_query(query.id, "Ошибка координат хода.", show_alert=True)
            return # <<< Явный выход
        except IndexError: # Если частей меньше, чем ожидалось
            logger.error(f"Недостаточно частей в 2p_move callback_data: {query.data}")
            await context.bot.answer_callback_query(query.id, "Ошибка формата данных хода.", show_alert=True)
            return # <<< Явный выход


        active_games = context.bot_data.get('active_games', {})
        if game_id not in active_games:
            # Игра могла завершиться или быть удалена
            await query.edit_message_text("Эта игра больше не активна или была завершена.",
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("В главное меню", callback_data='main_menu')]]))
            return # <<< Явный выход

        game_details = active_games[game_id]
        game_obj: TicTacToe = game_details['game'] # Явно указываем тип

        # Проверяем, тот ли игрок нажал на кнопку
        if user.id != game_details['current_player_id']:
            await context.bot.answer_callback_query(query.id, "Сейчас не ваш ход!", show_alert=True)
            return # <<< Явный выход

        # Определяем символ текущего игрока на основе его ID
        current_player_symbol = game_details['player1_symbol'] if user.id == game_details['player1_id'] else game_details['player2_symbol']

        # Дополнительная проверка на синхронизацию хода (на случай расхождений)
        if game_obj.current_turn != current_player_symbol:
            logger.warning(f"Расхождение ходов! game_details говорит, что ходит игрок {user.id} ({current_player_symbol}), "
                           f"но game_obj.current_turn = {game_obj.current_turn}. Game_ID: {game_id}. "
                           f"Предполагается, что game_obj.current_turn более авторитетен.")
            # Можно просто обновить доску, возможно, игрок нажал не на свое сообщение или произошел сбой
            # Определяем, чей ход сейчас по game_obj.current_turn (более надежно)
            text_for_p1_resync, text_for_p2_resync = "", ""
            if game_obj.current_turn == game_details['player1_symbol']: # Ход P1
                text_for_p1_resync = f"Игра с @{game_details['player2_username']}. Ваш ход ({game_details['player1_symbol']})."
                text_for_p2_resync = f"Игра с @{game_details['player1_username']}. Ход @{game_details['player1_username']} ({game_details['player1_symbol']})."
            else: # Ход P2
                text_for_p1_resync = f"Игра с @{game_details['player2_username']}. Ход @{game_details['player2_username']} ({game_details['player2_symbol']})."
                text_for_p2_resync = f"Игра с @{game_details['player1_username']}. Ваш ход ({game_details['player2_symbol']})."

            # Обновляем доски с актуальным состоянием
            await send_or_edit_2p_board(context, game_id, game_details['player1_chat_id'], game_details['player1_message_id'], text_for_p1_resync, is_edit=True)
            await send_or_edit_2p_board(context, game_id, game_details['player2_chat_id'], game_details['player2_message_id'], text_for_p2_resync, is_edit=True)

            await context.bot.answer_callback_query(query.id, "Сейчас не ваш ход! (доска обновлена)", show_alert=True)
            return # <<< Явный выход

        if game_obj.board[row][col] != ' ':
            await context.bot.answer_callback_query(query.id, "Эта клетка уже занята!", show_alert=True)
            return # <<< Явный выход

        if game_obj.make_move(row, col, current_player_symbol):
            winner_symbol = game_obj.check_winner()

            if winner_symbol: # Если есть победитель или ничья
                await handle_2p_game_over(context, game_id, winner_symbol)
                return # <<< Явный выход
            else:
                # Смена хода
                next_player_id = ""
                next_player_symbol = ""
                # current_player_display_name = "" # Имя того, кто только что сходил
                # next_player_display_name = "" # Имя того, чей ход следующий

                if game_details['current_player_id'] == game_details['player1_id']: # Ходил игрок 1
                    game_details['current_player_id'] = game_details['player2_id']
                    game_obj.current_turn = game_details['player2_symbol'] # Обновляем ход в объекте игры
                    # next_player_id = game_details['player2_id']
                    # next_player_symbol = game_details['player2_symbol']
                    # current_player_display_name = game_details['player1_username']
                    # next_player_display_name = game_details['player2_username']

                else: # Ходил игрок 2
                    game_details['current_player_id'] = game_details['player1_id']
                    game_obj.current_turn = game_details['player1_symbol'] # Обновляем ход в объекте игры
                    # next_player_id = game_details['player1_id']
                    # next_player_symbol = game_details['player1_symbol']
                    # current_player_display_name = game_details['player2_username']
                    # next_player_display_name = game_details['player1_username']


                # Формируем текст для каждого игрока
                text_for_p1 = f"Игра с @{game_details['player2_username']}. "
                text_for_p2 = f"Игра с @{game_details['player1_username']}. "

                if game_details['current_player_id'] == game_details['player1_id']: # Теперь ход P1
                    text_for_p1 += f"Ваш ход ({game_details['player1_symbol']})."
                    text_for_p2 += f"Ход @{game_details['player1_username']} ({game_details['player1_symbol']})."
                else: # Теперь ход P2
                    text_for_p1 += f"Ход @{game_details['player2_username']} ({game_details['player2_symbol']})."
                    text_for_p2 += f"Ваш ход ({game_details['player2_symbol']})."

                # Обновляем доски для обоих игроков
                await send_or_edit_2p_board(context, game_id, game_details['player1_chat_id'], game_details['player1_message_id'], text_for_p1, is_edit=True)
                await send_or_edit_2p_board(context, game_id, game_details['player2_chat_id'], game_details['player2_message_id'], text_for_p2, is_edit=True)
        # Нет else, т.к. game_obj.make_move вернет False только если клетка занята, что проверяется выше
        return # <<< Явный выход

    elif query.data == 'game_over_cell': # Неинтерактивная ячейка после окончания игры
        # await query.answer("Игра окончена.") # query.answer уже был
        await context.bot.answer_callback_query(query.id, "Игра окончена.") # Достаточно простого ответа
        return # <<< Явный выход

    # Если ни один из if/elif не сработал, это неизвестный callback_data
    # (кроме тех, что обрабатываются отдельными хэндлерами по pattern)
    logger.warning(f"Неизвестный callback_data получен в основном обработчике 'button': {query.data} от пользователя {user.id}")
    # await query.answer("Неизвестная команда.", show_alert=True) # query.answer уже был


async def bot_move(query_or_update, context): # Принимает CallbackQuery или Update
    game = context.user_data.get('game')
    if not game: return # Игра не найдена в user_data

    # Определяем, query это CallbackQuery или Update (для первого хода бота после выбора сложности)
    query = None
    if isinstance(query_or_update, CallbackQuery):
        query = query_or_update
    # Если bot_move вызывается из start_game, где query_or_update это Update, а query.message это Message
    # Нам нужен CallbackQuery, если он есть, для edit_message_text.
    # Если это первый ход бота, query_or_update будет CallbackQuery от выбора сложности.
    elif hasattr(query_or_update, 'callback_query') and query_or_update.callback_query:
        query = query_or_update.callback_query # Это если передали Update, у которого есть callback_query
    else: # Если это update без callback_query (маловероятно для bot_move в текущей логике, но для безопасности)
        logger.error("bot_move вызван без подходящего query_or_update объекта для edit_message_text")
        # Если query нет, мы не сможем обновить сообщение с доской через edit_message_text
        # Можно было бы отправить новое сообщение, но это изменит логику.
        return


    if game.current_turn != game.bot_symbol:
        logger.warning(f"bot_move вызван, но сейчас не ход бота. Текущий ход: {game.current_turn}")
        if query: await draw_board(query, context) # Обновить доску на всякий случай
        return

    move = game.get_best_move() # Получаем лучший ход от AI
    if move:
        i, j = move
        if game.make_move(i, j, game.bot_symbol): # make_move проверяет, свободна ли клетка
            winner = game.check_winner()
            if winner:
                if query: await handle_game_over(query, context, winner)
                else: logger.error("Не удалось вызвать handle_game_over в bot_move: отсутствует query")
                return
            # Если победителя нет, ход переходит к игроку
            game.current_turn = game.player_symbol
    else: # Нет доступных ходов для бота (например, доска заполнена)
        winner = game.check_winner() # Проверяем, не ничья ли
        if winner: # Обычно 'draw'
            if query: await handle_game_over(query, context, winner)
            else: logger.error("Не удалось вызвать handle_game_over для ничьи в bot_move: отсутствует query")
            return
        else: # Этого не должно происходить: нет ходов, но и не ничья/победа
            logger.error("У бота нет ходов, но победитель/ничья не определены. Это ошибка в логике игры.")
            if query: await handle_game_over(query, context, "draw") # Завершаем как ничью на всякий случай
            return

    # После хода бота обновляем доску
    if query: await draw_board(query, context)


async def draw_board(query: CallbackQuery, context): # query теперь явно CallbackQuery
    game = context.user_data.get('game')
    if not game:
        logger.warning("draw_board вызвана без активной игры в user_data (1P)")
        # Можно уведомить пользователя, если query есть
        # await query.edit_message_text("Ошибка: игра не найдена. Начните заново.", reply_markup=...)
        return

    keyboard = []
    for i in range(3):
        row_buttons = []
        for j in range(3):
            text = game.board[i][j] if game.board[i][j] != ' ' else '⬜'
            row_buttons.append(InlineKeyboardButton(text, callback_data=f'move_{i}_{j}'))
        keyboard.append(row_buttons)
    keyboard.append([InlineKeyboardButton("Сдаться и выйти", callback_data='surrender_game')]) # Для 1P игр

    message_text = "Ваш ход:" if game.current_turn == game.player_symbol else "Ход бота..."

    try:
        await query.edit_message_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except telegram_error.BadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.info("Доска (1P) не изменена, пропуск edit_message_text.")
        else: # Другие BadRequest ошибки
            logger.error(f"Ошибка BadRequest при обновлении доски (1P): {e}. Message_id: {query.message.message_id if query.message else 'N/A'}")
            # Здесь можно добавить фоллбэк на отправку нового сообщения, если редактирование критично
    except Exception as e: # Другие ошибки
         logger.error(f"Неожиданная ошибка при обновлении доски (1P): {e}")


async def handle_game_over(query: CallbackQuery, context, winner_symbol_or_draw): # query теперь явно CallbackQuery
    game = context.user_data.get('game')
    if not game:
        logger.warning("handle_game_over вызвана без активной игры в user_data (1P)")
        return

    user = query.from_user
    username = user.username or user.full_name or user.first_name or f"User_{user.id}"
    text = ""
    leaderboard_result = "" # 'win', 'loss', 'draw'

    if winner_symbol_or_draw == 'draw':
        leaderboard_result = 'draw'
        text = "🤝 Ничья!"
    elif winner_symbol_or_draw == game.player_symbol:
        leaderboard_result = 'win'
        text = "🎉 Вы победили!"
    else: # winner_symbol_or_draw == game.bot_symbol
        leaderboard_result = 'loss'
        text = "💀 Вы проиграли!"

    # Формируем финальную доску (неинтерактивную)
    final_board_keyboard_list = []
    for i in range(3):
        row_btns = [InlineKeyboardButton(game.board[i][j] if game.board[i][j] != ' ' else '⬜', callback_data='game_over_cell') for j in range(3)]
        final_board_keyboard_list.append(row_btns)
    final_reply_markup = InlineKeyboardMarkup(final_board_keyboard_list)

    try:
        await query.edit_message_text(f"{text}\n\nФинальная доска:", reply_markup=final_reply_markup)
    except telegram_error.BadRequest as e:
        logger.error(f"Error editing message for game over (1P): {e}. Sending new message as fallback.")
        # Фоллбэк на отправку нового сообщения, если редактирование не удалось
        try:
            await context.bot.send_message(query.message.chat_id, f"{text}\n\nФинальная доска:", reply_markup=final_reply_markup)
        except Exception as e_send:
            logger.error(f"Error sending new message for game over (1P) after edit failed: {e_send}")
    except Exception as e: # Другие ошибки
        logger.error(f"Unexpected error editing message for game over (1P): {e}")


    # Обновляем статистику только если это игра с ботом и есть game.difficulty
    if game.difficulty and game.difficulty in ['easy', 'medium', 'hard']:
        update_leaderboard(user.id, username, leaderboard_result, game.difficulty)
    else:
        logger.warning(f"Статистика для игры с difficulty='{game.difficulty}' не будет обновлена (user: {user.id}).")


    # Очистка данных игры из user_data
    if 'game' in context.user_data: del context.user_data['game']
    if 'selected_symbol' in context.user_data: del context.user_data['selected_symbol']
    if 'game_mode' in context.user_data: del context.user_data['game_mode']

    # Кнопки для действий после игры
    keyboard_after_game = [
        [InlineKeyboardButton("Играть снова", callback_data='play')], # Предлагаем общие опции
        [InlineKeyboardButton("В главное меню", callback_data='main_menu')]
    ]
    try:
        # Отправляем как новое сообщение, так как предыдущее было финальной доской
        await query.message.reply_text("Что дальше?", reply_markup=InlineKeyboardMarkup(keyboard_after_game))
    except Exception as e:
        logger.error(f"Error sending 'Что дальше?' message after 1P game over: {e}")


async def surrender_game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): # Для 1P игр
    query = update.callback_query
    # await query.answer() # query.answer уже был вызван в button или будет вызван в surrender_2p_game_handler
    # Ответ на callback query должен быть сделан в `button` перед вызовом этого хендлера,
    # либо здесь, если это отдельный CallbackQueryHandler с pattern.
    # Поскольку surrender_game обрабатывается в button, то answer там.
    # Если бы это был отдельный хендлер с pattern='^surrender_game$', то здесь нужен был бы await query.answer()

    game = context.user_data.get('game')
    user = query.from_user
    username = user.username or user.full_name or user.first_name or f"User_{user.id}"
    text_message = "Активной игры (против бота) для сдачи не найдено." # Сообщение по умолчанию

    if game and context.user_data.get('game_mode') == 'vs_bot': # Убедимся, что это игра с ботом
        # Засчитываем поражение
        if game.difficulty and game.difficulty in ['easy', 'medium', 'hard']:
             update_leaderboard(user.id, username, 'loss', game.difficulty)
        text_message = "Вы сдались в игре против бота. Поражение засчитано."
        # Очистка данных игры
        if 'game' in context.user_data: del context.user_data['game']
        if 'selected_symbol' in context.user_data: del context.user_data['selected_symbol']
        if 'game_mode' in context.user_data: del context.user_data['game_mode']
    elif game: # Если игра есть, но это не игра с ботом (маловероятно, если surrender_game только для 1P)
        text_message = "Вы сдались в текущей игре." # Общее сообщение
        # Очищаем на всякий случай, если это какая-то другая игра из user_data
        if 'game' in context.user_data: del context.user_data['game']
        if 'selected_symbol' in context.user_data: del context.user_data['selected_symbol']
        if 'game_mode' in context.user_data: del context.user_data['game_mode']


    keyboard = [
        [InlineKeyboardButton("Играть!", callback_data='play')],
        [InlineKeyboardButton("Статистика", callback_data='stats')],
        [InlineKeyboardButton("🏆 Лидеры", callback_data='leaderboard_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Редактируем сообщение, на котором была кнопка "Сдаться"
    try:
        await query.edit_message_text(f"{text_message}\nВыберите действие:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения после сдачи (1P): {e}")
        # Фоллбэк на отправку нового сообщения
        await query.message.reply_text(f"{text_message}\nВыберите действие:", reply_markup=reply_markup)


async def surrender_2p_game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # await query.answer() # Ответ должен быть здесь, если это прямой хендлер
    # Но т.к. он вызывается из button, то answer уже был.
    # Для отдельного хендлера с pattern, query.answer() обязателен.
    # Исправляем: т.к. это отдельный хендлер с паттерном, ему нужен свой await query.answer()
    try:
        await query.answer() # <--- ДОБАВЛЕНО для прямого хендлера
    except telegram_error.BadRequest: pass # Если уже ответили или таймаут

    game_id = query.data.split('_')[-1] # Получаем game_id из 'surrender_2p_GAMEID'
    user_who_surrendered = query.from_user

    active_games = context.bot_data.get('active_games', {})
    if game_id not in active_games:
        # await query.answer("Эта игра уже неактивна.", show_alert=True) # query.answer уже был, если из button
        await context.bot.answer_callback_query(query.id, "Эта игра уже неактивна.", show_alert=True) # Используем context.bot...
        try:
            await query.edit_message_text("Эта игра уже неактивна.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("В главное меню", callback_data='main_menu')]]))
        except: pass # Если сообщение уже не отредактировать
        return

    game_details = active_games[game_id]
    surrendering_player_id = user_who_surrendered.id
    winning_player_symbol = None # Символ победителя
    surrenderer_username = ""
    winner_username = "" # Не используется напрямую в handle_2p_game_over, но для логов/уведомлений полезно

    if surrendering_player_id == game_details['player1_id']:
        winning_player_symbol = game_details['player2_symbol'] # Победил P2
        surrenderer_username = game_details['player1_username']
        winner_username = game_details['player2_username']
        # await query.answer(f"Вы сдались. @{winner_username} победил(а).", show_alert=True)
        await context.bot.answer_callback_query(query.id, f"Вы сдались. @{winner_username} победил(а).", show_alert=True)
    elif surrendering_player_id == game_details['player2_id']:
        winning_player_symbol = game_details['player1_symbol'] # Победил P1
        surrenderer_username = game_details['player2_username']
        winner_username = game_details['player1_username']
        # await query.answer(f"Вы сдались. @{winner_username} победил(а).", show_alert=True)
        await context.bot.answer_callback_query(query.id, f"Вы сдались. @{winner_username} победил(а).", show_alert=True)
    else:
        # await query.answer("Вы не являетесь участником этой игры.", show_alert=True)
        await context.bot.answer_callback_query(query.id, "Вы не являетесь участником этой игры.", show_alert=True)
        return

    if winning_player_symbol:
        # Уведомляем другого игрока о сдаче соперника перед вызовом общего обработчика завершения игры
        # Это нужно сделать аккуратно, чтобы не было конфликта с редактированием в handle_2p_game_over
        other_player_chat_id = game_details['player2_chat_id'] if surrendering_player_id == game_details['player1_id'] else game_details['player1_chat_id']
        other_player_message_id = game_details['player2_message_id'] if surrendering_player_id == game_details['player1_id'] else game_details['player1_message_id']
        notification_text = f"Игрок @{surrenderer_username} сдался. Вы победили!"
        try:
            # Вместо редактирования здесь, просто вызовем handle_2p_game_over,
            # он сам обновит сообщения нужным образом.
            # Сообщение о сдаче будет частью текста в handle_2p_game_over.
            # Чтобы это сделать, нужно изменить handle_2p_game_over, чтобы он мог принимать причину завершения.
            # Или просто передать символ победителя, как и раньше.
            # handle_2p_game_over уже корректно обрабатывает символ победителя.
            # Уведомление о сдаче уже сделано через answer_callback_query.
            # Можно добавить в текст handle_2p_game_over, что победа по причине сдачи.
            # Пока оставим как есть: handle_2p_game_over сообщит о победе.
            pass # Уведомление уже через answer_callback_query и будет в handle_2p_game_over

        except Exception as e:
            logger.error(f"Error notifying other player ({other_player_chat_id}) of surrender: {e}")

        # Завершаем игру, передав символ победителя
        await handle_2p_game_over(context, game_id, winning_player_symbol)
    # Очистка игры происходит в handle_2p_game_over


def main():
    if BOT_USERNAME == "YOUR_BOT_USERNAME" or not BOT_USERNAME: # Строгая проверка
        logger.critical("ОШИБКА: ЗАМЕНИТЕ 'YOUR_BOT_USERNAME' в коде на реальное имя пользователя вашего бота (без @)!")
        logger.critical("Бот не будет запущен, пока это не будет исправлено.")
        return

    # persistence = PicklePersistence(filepath='bot_persistence') # Оригинальный persistence
    # Если вы хотите, чтобы user_data и bot_data (кроме leaderboard) также сохранялись в указанной директории:
    persistence_dir = os.path.dirname(LEADERBOARD_FILE_PATH) # Используем ту же директорию
    if not os.path.exists(persistence_dir):
        try:
            os.makedirs(persistence_dir)
            logger.info(f"Создана директория для файла persistence: {persistence_dir}")
        except Exception as e:
            logger.error(f"Не удалось создать директорию для persistence {persistence_dir}: {e}. Файл persistence будет в текущей директории.")
            persistence_dir = "." # Фоллбэк на текущую директорию

    persistence_file_path = os.path.join(persistence_dir, 'bot_persistence.pkl')
    logger.info(f"Файл persistence будет использоваться: {persistence_file_path}")
    persistence = PicklePersistence(filepath=persistence_file_path)


    application = Application.builder().token("7560143109:AAEDok-oVD7DfCy4uQTL-2n7hPHVG6ulVv0").persistence(persistence).build()

    # Инициализация хранилищ при старте, если их нет (на случай чистого запуска без файла persistence)
    if 'pending_games' not in application.bot_data:
        application.bot_data['pending_games'] = {}
    if 'active_games' not in application.bot_data:
        application.bot_data['active_games'] = {}


    application.add_handler(CommandHandler("start", start))
    # Регистрируем обработчики с паттернами до основного CallbackQueryHandler(button)
    # Эти хендлеры должны самостоятельно вызывать query.answer()
    application.add_handler(CallbackQueryHandler(surrender_game_handler, pattern='^surrender_game$')) # Для 1P игр (из user_data)
    application.add_handler(CallbackQueryHandler(surrender_2p_game_handler, pattern='^surrender_2p_')) # Для 2P игр (из bot_data)

    # Основной обработчик кнопок (button) будет обрабатывать все остальные callback_data.
    # Он также должен вызывать query.answer() в начале.
    application.add_handler(CallbackQueryHandler(button))

    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
