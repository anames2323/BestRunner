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
WEB_APP_URL = "https://effulgent-starburst-85120c.netlify.app"
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
            "event": None,
            "custom_cases": []
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
            "event": None,
            "custom_cases": []
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

@app.route('/api/debug', methods=['GET'])
def debug():
    return jsonify(load_data())

@app.route('/api/get_cases', methods=['GET'])
def get_cases():
    data = load_data()
    cases = data.get("custom_cases", [])
    if not cases:
        cases = [
            {
                "id": "w", "name": "We Openned!", "image": "we_open.png", "price": 2500,
                "items": [
                    {"name": "Plush Pepe", "file": "GiftStickersByAutoGiftNews_1.gif", "price": 900000, "rc": "super-legendary", "rr": "Супер-Легендарный", "chance": 0.2},
                    {"name": "Heart Lockets", "file": "GiftStickersByAutoGiftNews_2.gif", "price": 200000, "rc": "legendary", "rr": "Легендарный", "chance": 0.5},
                    {"name": "Signet Ring", "file": "GiftStickersByAutoGiftNews_70.gif", "price": 4627, "rc": "epic", "rr": "Эпический", "chance": 3},
                    {"name": "Hanging Star", "file": "GiftStickersByAutoGiftNews_76.gif", "price": 700, "rc": "rare", "rr": "Редкий", "chance": 15},
                    {"name": "B-Day Candle", "file": "GiftStickersByAutoGiftNews_21.gif", "price": 150, "rc": "unusual", "rr": "Необычный", "chance": 80}
                ]
            },
            {
                "id": "d", "name": "Durov Cap Farm", "image": "durovfarm.png", "price": 800,
                "items": [
                    {"name": "Durov Cap", "file": "GiftStickersByAutoGiftNews_77.gif", "price": 100000, "rc": "super-legendary", "rr": "Супер-Легендарный", "chance": 0.2},
                    {"name": "Heroic Helmets", "file": "GiftStickersByAutoGiftNews_6.gif", "price": 20000, "rc": "legendary", "rr": "Легендарный", "chance": 0.5},
                    {"name": "Vintage Cigars", "file": "GiftStickersByAutoGiftNews_84.gif", "price": 2805, "rc": "epic", "rr": "Эпический", "chance": 5},
                    {"name": "Hanging Star", "file": "GiftStickersByAutoGiftNews_76.gif", "price": 700, "rc": "rare", "rr": "Редкий", "chance": 25},
                    {"name": "B-Day Candle", "file": "GiftStickersByAutoGiftNews_21.gif", "price": 150, "rc": "unusual", "rr": "Необычный", "chance": 68}
                ]
            }
        ]
    return jsonify({"cases": cases})

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
        modified_items = current_case['items']
        total_chance = sum(item['chance'] for item in modified_items)
        if total_chance == 0:
            winning_item = current_case['items'][0]
        else:
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
        all_data = load_data()
        all_data['users'][str(user_id)] = user_data
        save_data(all_data)
        return jsonify({"success": True, "winning_item": winning_item, "new_balance": user_data['balance']})
    except Exception as e:
        logger.error(f"Error in open_case: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/sell_item', methods=['POST'])
def sell_item():
    data = request.json
    user_id = data.get('user_id')
    item_index = data.get('item_index')
    if item_index is None:
        return jsonify({"error": "No item index"}), 400
    user = get_user(user_id)
    if item_index >= len(user['inventory']):
        return jsonify({"error": "Item not found"}), 404
    item = user['inventory'].pop(item_index)
    sold_price = int(item['price'] * 0.8)
    user['balance'] += sold_price
    all_data = load_data()
    all_data['users'][str(user_id)] = user
    save_data(all_data)
    return jsonify({"success": True, "sold_price": sold_price, "balance": user['balance']})

@app.route('/api/admin/give_balance', methods=['POST'])
def admin_give_balance():
    data = request.json
    if int(data.get('admin_id', 0)) != ADMIN_ID:
        return jsonify({"error": "Access denied"}), 403
    user = get_user(data.get('user_id'))
    user['balance'] += int(data.get('amount', 0))
    all_data = load_data()
    all_data['users'][str(data.get('user_id'))] = user
    save_data(all_data)
    return jsonify({"success": True, "new_balance": user['balance']})

@app.route('/api/admin/set_flags', methods=['POST'])
def admin_set_flags():
    data = request.json
    if int(data.get('admin_id', 0)) != ADMIN_ID:
        return jsonify({"error": "Access denied"}), 403
    all_data = load_data()
    for key in all_data['flags']:
        all_data['flags'][key] = False
    if data.get('value') == 'true':
        all_data['flags'][data.get('flag')] = True
    save_data(all_data)
    return jsonify({"success": True, "flags": all_data['flags']})

@app.route('/api/admin/create_case', methods=['POST'])
def admin_create_case():
    d = request.json
    if int(d.get('admin_id', 0)) != ADMIN_ID:
        return jsonify({"error": "Access denied"}), 403
    data = load_data()
    if "custom_cases" not in data:
        data["custom_cases"] = []
    new_case = {
        "id": str(random.randint(1000, 9999)),
        "name": d.get("name", "Новый кейс"),
        "image": d.get("image", ""),
        "price": int(d.get("price", 500)),
        "items": d.get("items", [])
    }
    data["custom_cases"].append(new_case)
    save_data(data)
    return jsonify({"success": True, "case": new_case})

@app.route('/api/admin/delete_case', methods=['POST'])
def admin_delete_case():
    d = request.json
    if int(d.get('admin_id', 0)) != ADMIN_ID:
        return jsonify({"error": "Access denied"}), 403
    data = load_data()
    data["custom_cases"] = [c for c in data.get("custom_cases", []) if c["id"] != d.get("case_id")]
    save_data(data)
    return jsonify({"success": True})

@app.route('/api/game/rocket', methods=['POST'])
def game_rocket():
    data = request.json
    user_id = data.get('user_id')
    action = data.get('action')
    bet = data.get('bet', 100)
    user = get_user(user_id)
    all_data = load_data()
    if action == 'start':
        if user['balance'] < bet:
            return jsonify({"error": "Недостаточно монет"}), 402
        user['balance'] -= bet
        crash = round(random.uniform(0.8, 30), 2)
        if crash < 1: crash = 1
        all_data['users'][str(user_id)] = user
        all_data[f'rocket_{user_id}'] = {'bet': bet, 'crash': crash, 'active': True}
        save_data(all_data)
        return jsonify({"success": True, "balance": user['balance'], "crash": crash})
    elif action == 'cashout':
        game = all_data.get(f'rocket_{user_id}')
        if not game or not game.get('active'):
            return jsonify({"error": "Нет игры"}), 400
        mult = data.get('multiplier', 1.0)
        if mult > game['crash']:
            game['active'] = False
            all_data[f'rocket_{user_id}'] = game
            save_data(all_data)
            return jsonify({"success": False, "crashed": True, "crash_at": game['crash']})
        win = int(game['bet'] * mult)
        user['balance'] += win
        game['active'] = False
        all_data[f'rocket_{user_id}'] = game
        all_data['users'][str(user_id)] = user
        save_data(all_data)
        return jsonify({"success": True, "win": win, "balance": user['balance']})
    return jsonify({"error": "Неверное действие"}), 400

@app.route('/api/game/mines', methods=['POST'])
def game_mines():
    data = request.json
    user_id = data.get('user_id')
    action = data.get('action')
    bet = data.get('bet', 50)
    mines_count = data.get('mines_count', 5)
    user = get_user(user_id)
    all_data = load_data()
    gk = f'mines_{user_id}'
    if action == 'start':
        if user['balance'] < bet:
            return jsonify({"error": "Недостаточно монет"}), 402
        user['balance'] -= bet
        mines = random.sample(range(25), mines_count)
        mults = {0:1.2,1:1.5,2:2,3:3,4:5,5:8,6:12,7:18,8:25,9:35,10:50}
        all_data['users'][str(user_id)] = user
        all_data[gk] = {'bet': bet, 'mines': mines, 'revealed': [], 'active': True, 'multipliers': mults}
        save_data(all_data)
        return jsonify({"success": True, "balance": user['balance'], "safe_count": 25 - mines_count})
    elif action == 'reveal':
        game = all_data.get(gk)
        if not game or not game.get('active'): return jsonify({"error": "Нет игры"}), 400
        cell = data.get('cell')
        if cell is None: return jsonify({"error": "Выбери клетку"}), 400
        if cell in game['revealed']: return jsonify({"error": "Уже открыта"}), 400
        game['revealed'].append(cell)
        if cell in game['mines']:
            game['active'] = False
            all_data[gk] = game
            save_data(all_data)
            return jsonify({"success": False, "bomb": True, "mines": game['mines'], "opened": len(game['revealed'])})
        opened = len(game['revealed'])
        mult = game['multipliers'].get(opened, 1.0)
        all_data[gk] = game
        save_data(all_data)
        return jsonify({"success": True, "bomb": False, "opened": opened, "multiplier": mult, "safe_count": 25 - len(game['mines']) - opened})
    elif action == 'cashout':
        game = all_data.get(gk)
        if not game or not game.get('active'): return jsonify({"error": "Нет игры"}), 400
        opened = len(game['revealed'])
        mult = game['multipliers'].get(opened, 1.0)
        win = int(game['bet'] * mult)
        user['balance'] += win
        game['active'] = False
        all_data[gk] = game
        all_data['users'][str(user_id)] = user
        save_data(all_data)
        return jsonify({"success": True, "win": win, "balance": user['balance'], "multiplier": mult})
    return jsonify({"error": "Неверное действие"}), 400

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Открыть сайт", web_app={"url": WEB_APP_URL})]]
    await update.message.reply_text("Нажмите кнопку ниже, чтобы открыть GiftRunner!", reply_markup=InlineKeyboardMarkup(keyboard))

def run_flask_app():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def main() -> None:
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
