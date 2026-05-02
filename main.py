# Для чего нужен этот файл?
# Тут храняться сохранения, админ панель, и тд. Без него сайт работать будет некорекктно!
# При повторном сливе, указывать автора: @x3layka или в телеграм: @coderingonelove

import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import json
import requests
import os
import threading
import random

TOKEN = "8356402633:AAEMJqxjjiBGTrLIubQIQgRWfw0DkJ0Qxg0"
ADMIN_ID = 8795006636
WEB_APP_URL = "https://heroic-stardust-8cdd1b.netlify.app/"
DATA_FILE = 'data.json'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "users": {},
            "flags": {
                "100_per_rarity_super": False,
                "100_per_rarity": False,
                "double_chances": False,
                "trible_chances": False,
            },
            "event": None
        }
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "users": {},
            "flags": {
                "100_per_rarity_super": False,
                "100_per_rarity": False,
                "double_chances": False,
                "trible_chances": False,
            },
            "event": None
        }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(user_id):
    data = load_data()
    user = data["users"].get(str(user_id))
    if not user:
        user = {
            "balance": 10000,
            "inventory": [],
            "stats": {
                "cases_opened": 0,
                "best_drop": None,
                "case_open_stats": {}
            }
        }
        data["users"][str(user_id)] = user
        save_data(data)
    return user

@app.route('/api/get_user_data', methods=['GET'])
def get_user_data():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    data = load_data()
    user = get_user(user_id)
    return jsonify({
        "user_data": user,
        "flags": data["flags"],
        "event": data["event"]
    })

@app.route('/api/debug', methods=['GET'])
def debug():
    return jsonify(load_data())

@app.route('/api/open_case', methods=['POST'])
def open_case():
    try:
        data = request.json
        user_id = data.get('user_id')
        case_id = data.get('case_id')
        cases_data = data.get('cases_data')

        if not user_id or not case_id or not cases_data:
            return jsonify({"error": "Invalid data"}), 400

        user_data = get_user(user_id)
        flags = load_data()["flags"]
        current_case = next((c for c in cases_data if c['id'] == case_id), None)

        if not current_case:
            return jsonify({"error": "Case not found"}), 404

        if user_data['balance'] < current_case['price']:
            return jsonify({"error": "Insufficient balance"}), 402

        user_data['balance'] -= current_case['price']

        modified_items = []
        if flags.get('100_per_rarity_super'):
            modified_items = [item for item in current_case['items'] if item['rarity_color'] == 'super-legendary']
        elif flags.get('100_per_rarity'):
            modified_items = [item for item in current_case['items'] if item['rarity_color'] in ['super-legendary', 'legendary']]
        elif flags.get('trible_chances'):
            rare_and_above = [item for item in current_case['items'] if item['rarity_color'] in ['super-legendary', 'legendary', 'epic', 'rare']]
            common_and_unusual = [item for item in current_case['items'] if item['rarity_color'] in ['common', 'unusual']]
            total_rare_chance = sum(item['chance'] for item in rare_and_above)
            total_common_chance = sum(item['chance'] for item in common_and_unusual)
            for item in rare_and_above:
                item['chance'] *= 3
            new_total_rare_chance = sum(item['chance'] for item in rare_and_above)
            adjustment = new_total_rare_chance - total_rare_chance
            adjustment_ratio = (total_common_chance - adjustment) / total_common_chance if total_common_chance > 0 else 0
            for item in common_and_unusual:
                item['chance'] *= adjustment_ratio
            modified_items = rare_and_above + common_and_unusual
        elif flags.get('double_chances'):
            rare_and_above = [item for item in current_case['items'] if item['rarity_color'] in ['super-legendary', 'legendary', 'epic', 'rare']]
            common_and_unusual = [item for item in current_case['items'] if item['rarity_color'] in ['common', 'unusual']]
            total_rare_chance = sum(item['chance'] for item in rare_and_above)
            total_common_chance = sum(item['chance'] for item in common_and_unusual)
            for item in rare_and_above:
                item['chance'] *= 2
            new_total_rare_chance = sum(item['chance'] for item in rare_and_above)
            adjustment = new_total_rare_chance - total_rare_chance
            adjustment_ratio = (total_common_chance - adjustment) / total_common_chance if total_common_chance > 0 else 0
            for item in common_and_unusual:
                item['chance'] *= adjustment_ratio
            modified_items = rare_and_above + common_and_unusual
        else:
            modified_items = current_case['items']

        total_chance = sum(item['chance'] for item in modified_items)

        if total_chance == 0:
            winning_item = current_case['items'][0]
        else:
            try:
                rand_text = requests.get('http://www.random.org/decimal-fractions/?num=1&dec=10&format=plain&rnd=new', timeout=3).text
                rand_num = total_chance * float(rand_text)
            except:
                rand_num = total_chance * random.random()

            winning_item = None
            current_chance = 0
            for item in modified_items:
                current_chance += item['chance']
                if rand_num < current_chance:
                    winning_item = item
                    break

        if not winning_item:
            winning_item = modified_items[-1]

        user_data['inventory'].append(winning_item)
        user_data['stats']['cases_opened'] += 1
        if winning_item.get('price') and (user_data['stats']['best_drop'] is None or winning_item['price'] > user_data['stats']['best_drop']['price']):
            user_data['stats']['best_drop'] = winning_item
        user_data['stats']['case_open_stats'][case_id] = user_data['stats']['case_open_stats'].get(case_id, 0) + 1

        all_data = load_data()
        all_data['users'][str(user_id)] = user_data
        save_data(all_data)

        return jsonify({"success": True, "winning_item": winning_item, "new_balance": user_data['balance']})
    except Exception as e:
        logger.error(f"Error in open_case: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ========== ИГРЫ ==========

@app.route('/api/game/rocket', methods=['POST'])
def game_rocket():
    """Ракета: ставка, летит до случайного множителя"""
    data = request.json
    user_id = data.get('user_id')
    action = data.get('action')  # 'start' или 'cashout'
    bet = data.get('bet', 100)

    user = get_user(user_id)
    all_data = load_data()

    if action == 'start':
        if user['balance'] < bet:
            return jsonify({"error": "Недостаточно монет"}), 402
        user['balance'] -= bet
        # Генерируем множитель взрыва
        crash = round(random.uniform(0.8, 30), 2)
        if crash < 1:
            crash = 1

        all_data['users'][str(user_id)] = user
        all_data[f'rocket_{user_id}'] = {
            'bet': bet,
            'crash': crash,
            'active': True,
            'points': []  # для графика
        }
        # Генерируем точки графика
        points = []
        for x in range(0, 101, 2):
            y = round(1 + (crash - 1) * (x / 100) ** 2, 2)
            points.append({'x': x, 'y': min(y, crash)})
            if y >= crash:
                break
        all_data[f'rocket_{user_id}']['points'] = points

        save_data(all_data)
        return jsonify({
            "success": True,
            "balance": user['balance'],
            "bet": bet,
            "crash": crash,
            "points": points
        })

    elif action == 'cashout':
        game = all_data.get(f'rocket_{user_id}')
        if not game or not game.get('active'):
            return jsonify({"error": "Нет активной игры"}), 400

        multiplier = data.get('multiplier', 1.0)
        crash = game['crash']

        if multiplier > crash:
            game['active'] = False
            all_data[f'rocket_{user_id}'] = game
            save_data(all_data)
            return jsonify({"success": False, "crashed": True, "crash_at": crash, "balance": user['balance']})

        win = int(game['bet'] * multiplier)
        user['balance'] += win
        game['active'] = False
        all_data[f'rocket_{user_id}'] = game
        all_data['users'][str(user_id)] = user
        save_data(all_data)
        return jsonify({
            "success": True,
            "win": win,
            "multiplier": multiplier,
            "balance": user['balance']
        })

    return jsonify({"error": "Неверное действие"}), 400


@app.route('/api/game/mines', methods=['POST'])
def game_mines():
    """Сапёр: поле 5x5, 5 мин, открываешь безопасные клетки"""
    data = request.json
    user_id = data.get('user_id')
    action = data.get('action')  # 'start', 'reveal', 'cashout'
    bet = data.get('bet', 50)
    cell = data.get('cell')  # номер клетки 0-24

    user = get_user(user_id)
    all_data = load_data()
    game_key = f'mines_{user_id}'

    if action == 'start':
        if user['balance'] < bet:
            return jsonify({"error": "Недостаточно монет"}), 402
        user['balance'] -= bet

        # Создаём поле: 5 мин из 25 клеток
        mines = random.sample(range(25), 5)
        revealed = []
        multipliers = {0: 1.2, 1: 1.5, 2: 2.0, 3: 3.0, 4: 5.0, 5: 8.0, 6: 12.0, 7: 18.0, 8: 25.0,
                       9: 35.0, 10: 50.0, 11: 70.0, 12: 100.0, 13: 150.0, 14: 200.0, 15: 300.0,
                       16: 500.0, 17: 750.0, 18: 1000.0, 19: 2000.0, 20: 5000.0}

        all_data['users'][str(user_id)] = user
        all_data[game_key] = {
            'bet': bet,
            'mines': mines,
            'revealed': [],
            'active': True,
            'multipliers': multipliers
        }
        save_data(all_data)
        return jsonify({
            "success": True,
            "balance": user['balance'],
            "bet": bet,
            "revealed": [],
            "safe_count": 20
        })

    elif action == 'reveal':
        game = all_data.get(game_key)
        if not game or not game.get('active'):
            return jsonify({"error": "Нет активной игры"}), 400

        if cell is None:
            return jsonify({"error": "Выберите клетку"}), 400

        if cell in game['revealed']:
            return jsonify({"error": "Клетка уже открыта"}), 400

        game['revealed'].append(cell)

        if cell in game['mines']:
            # Взорвался
            game['active'] = False
            all_data[game_key] = game
            save_data(all_data)
            return jsonify({
                "success": False,
                "bomb": True,
                "mines": game['mines'],
                "balance": user['balance'],
                "opened": len(game['revealed'])
            })

        # Безопасная клетка
        opened = len(game['revealed'])
        current_mult = game['multipliers'].get(opened, 1.0)

        all_data[game_key] = game
        all_data['users'][str(user_id)] = user
        save_data(all_data)

        return jsonify({
            "success": True,
            "bomb": False,
            "opened": opened,
            "multiplier": current_mult,
            "cell": cell,
            "safe_count": 20 - opened
        })

    elif action == 'cashout':
        game = all_data.get(game_key)
        if not game or not game.get('active'):
            return jsonify({"error": "Нет активной игры"}), 400

        opened = len(game['revealed'])
        mult = game['multipliers'].get(opened, 1.0)
        win = int(game['bet'] * mult)

        user['balance'] += win
        game['active'] = False
        all_data[game_key] = game
        all_data['users'][str(user_id)] = user
        save_data(all_data)
        return jsonify({
            "success": True,
            "win": win,
            "opened": opened,
            "multiplier": mult,
            "balance": user['balance'],
            "mines": game['mines']
        })

    return jsonify({"error": "Неверное действие"}), 400


# ========== АДМИНКА ==========

@app.route('/api/admin/give_balance', methods=['POST'])
def admin_give_balance():
    data = request.json
    admin_id = data.get('admin_id')
    user_id = data.get('user_id')
    amount = data.get('amount')
    if int(admin_id) != ADMIN_ID:
        return jsonify({"error": "Access denied"}), 403
    user_data = get_user(user_id)
    user_data['balance'] += int(amount)
    all_data = load_data()
    all_data['users'][str(user_id)] = user_data
    save_data(all_data)
    return jsonify({"success": True, "new_balance": user_data['balance']})

@app.route('/api/admin/set_flags', methods=['POST'])
def admin_set_flags():
    data = request.json
    admin_id = data.get('admin_id')
    flag = data.get('flag')
    value = data.get('value')
    if int(admin_id) != ADMIN_ID:
        return jsonify({"error": "Access denied"}), 403
    all_data = load_data()
    for key in all_data['flags']:
        all_data['flags'][key] = False
    if value == 'true':
        all_data['flags'][flag] = True
    save_data(all_data)
    return jsonify({"success": True, "flags": all_data['flags']})

@app.route('/api/admin/create_event', methods=['POST'])
def admin_create_event():
    data = request.json
    admin_id = data.get('admin_id')
    event_data = data.get('event_data')
    if int(admin_id) != ADMIN_ID:
        return jsonify({"error": "Access denied"}), 403
    all_data = load_data()
    all_data['event'] = event_data
    save_data(all_data)
    return jsonify({"success": True, "event": all_data['event']})


# ========== TELEGRAM BOT ==========

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[
        InlineKeyboardButton("Открыть сайт", web_app={"url": WEB_APP_URL})
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Нажмите кнопку ниже, чтобы открыть GiftRunner!",
        reply_markup=reply_markup
    )

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Ваш Telegram ID: {update.effective_user.id}")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Доступ запрещён")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "📋 Админ-команды:\n\n"
            "/admin give [user_id] [amount] — выдать баланс\n"
            "/admin setbal [user_id] [amount] — установить баланс\n"
            "/admin info [user_id] — инфо о пользователе\n"
            "/admin users — список всех пользователей\n"
            "/admin flag [название] [true/false] — включить/выключить буст\n"
            "/admin flags — посмотреть все флаги\n"
            "/admin event [название] [множитель] — создать ивент\n"
            "/admin event_off — удалить ивент"
        )
        return

    command = args[0]
    all_data = load_data()

    if command == "give" and len(args) >= 3:
        user_id = args[1]
        amount = int(args[2])
        user = get_user(user_id)
        user['balance'] += amount
        all_data['users'][str(user_id)] = user
        save_data(all_data)
        await update.message.reply_text(f"✅ +{amount} монет [{user_id}]\n💰 Баланс: {user['balance']}")

    elif command == "setbal" and len(args) >= 3:
        user_id = args[1]
        amount = int(args[2])
        user = get_user(user_id)
        old = user['balance']
        user['balance'] = amount
        all_data['users'][str(user_id)] = user
        save_data(all_data)
        await update.message.reply_text(f"✅ Баланс [{user_id}]\n📉 {old} → 📈 {amount}")

    elif command == "info" and len(args) >= 2:
        user_id = args[1]
        user = get_user(user_id)
        await update.message.reply_text(
            f"👤 [{user_id}]\n💰 {user['balance']}\n🎒 {len(user['inventory'])} предметов"
        )

    elif command == "users":
        users = all_data.get('users', {})
        text = "👥 Пользователи:\n"
        for uid, u in users.items():
            text += f"ID: {uid} | 💰 {u['balance']}\n"
        await update.message.reply_text(text[:4000])

    elif command == "flags":
        flags = all_data.get('flags', {})
        text = "🚩 Флаги:\n"
        for k, v in flags.items():
            text += f"{'✅' if v else '❌'} {k}\n"
        await update.message.reply_text(text)

    elif command == "flag" and len(args) >= 3:
        flag_name = args[1]
        value = args[2]
        for key in all_data['flags']:
            all_data['flags'][key] = False
        if value == 'true':
            all_data['flags'][flag_name] = True
        save_data(all_data)
        await update.message.reply_text(f"✅ {flag_name} = {value}")

    elif command == "event" and len(args) >= 2:
        name = args[1]
        mult = int(args[2]) if len(args) >= 3 else 1
        all_data['event'] = {"name": name, "multiplier": mult}
        save_data(all_data)
        await update.message.reply_text(f"✅ Ивент: {name} (x{mult})")

    elif command == "event_off":
        all_data['event'] = None
        save_data(all_data)
        await update.message.reply_text("✅ Ивент удалён")

    else:
        await update.message.reply_text("❌ Неверная команда")


def run_flask_app():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def main() -> None:
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
