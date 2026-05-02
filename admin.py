import requests
import json

BASE_URL = "https://bestrunner-production.up.railway.app"  # Замените на ваш URL
ADMIN_ID = 8795006636

def give_balance(user_id, amount):
    """Выдать баланс пользователю"""
    r = requests.post(f"{BASE_URL}/api/admin/give_balance", json={
        "admin_id": ADMIN_ID,
        "user_id": str(user_id),
        "amount": int(amount)
    })
    data = r.json()
    if data.get("success"):
        print(f"✅ Выдано {amount} монет пользователю {user_id}")
        print(f"Новый баланс: {data.get('new_balance')}")
    else:
        print(f"❌ Ошибка: {data.get('error')}")

def set_flag(flag_name, value="true"):
    """Включить/выключить буст"""
    r = requests.post(f"{BASE_URL}/api/admin/set_flags", json={
        "admin_id": ADMIN_ID,
        "flag": flag_name,
        "value": value
    })
    data = r.json()
    if data.get("success"):
        print(f"✅ Флаг {flag_name} = {value}")
        print(f"Все флаги: {data.get('flags')}")
    else:
        print(f"❌ Ошибка: {data.get('error')}")

def create_event(name, multiplier=1):
    """Создать ивент"""
    r = requests.post(f"{BASE_URL}/api/admin/create_event", json={
        "admin_id": ADMIN_ID,
        "event_data": {
            "name": name,
            "multiplier": int(multiplier)
        }
    })
    data = r.json()
    if data.get("success"):
        print(f"✅ Ивент '{name}' создан")
        print(f"Данные: {data.get('event')}")
    else:
        print(f"❌ Ошибка: {data.get('error')}")

def get_user_data(user_id):
    """Посмотреть данные пользователя"""
    r = requests.get(f"{BASE_URL}/api/get_user_data", params={"user_id": str(user_id)})
    data = r.json()
    if "error" in data:
        print(f"❌ Ошибка: {data['error']}")
    else:
        user = data.get("user_data", {})
        print(f"👤 Пользователь: {user_id}")
        print(f"💰 Баланс: {user.get('balance')}")
        print(f"🎒 Инвентарь: {len(user.get('inventory', []))} предметов")
        print(f"📦 Открыто кейсов: {user.get('stats', {}).get('cases_opened')}")
        best = user.get('stats', {}).get('best_drop')
        if best:
            print(f"🏆 Лучший дроп: {best.get('name')} ({best.get('price')} монет)")
        print(f"🚩 Флаги сервера: {data.get('flags')}")
        print(f"🎪 Ивент: {data.get('event')}")

def show_menu():
    """Показать меню"""
    print("""
╔══════════════════════════════════╗
║        АДМИН-ПАНЕЛЬ              ║
╠══════════════════════════════════╣
║ 1. Выдать баланс                 ║
║ 2. Посмотреть пользователя      ║
║ 3. Включить буст                 ║
║ 4. Выключить все бусты           ║
║ 5. Создать ивент                 ║
║ 6. Выход                         ║
╚══════════════════════════════════╝
    """)

def main():
    while True:
        show_menu()
        choice = input("Выберите действие (1-6): ").strip()

        if choice == "1":
            user_id = input("ID пользователя: ").strip()
            amount = input("Сумма: ").strip()
            give_balance(user_id, amount)

        elif choice == "2":
            user_id = input("ID пользователя: ").strip()
            get_user_data(user_id)

        elif choice == "3":
            print("\nДоступные флаги:")
            print("1. 100_per_rarity_super (100% супер-легендарки)")
            print("2. 100_per_rarity (100% легендарки+)")
            print("3. double_chances (двойные шансы)")
            print("4. trible_chances (тройные шансы)")
            flag_choice = input("Выберите флаг (1-4): ").strip()
            flags_map = {
                "1": "100_per_rarity_super",
                "2": "100_per_rarity",
                "3": "double_chances",
                "4": "trible_chances"
            }
            if flag_choice in flags_map:
                set_flag(flags_map[flag_choice], "true")
            else:
                print("❌ Неверный выбор")

        elif choice == "4":
            confirm = input("Выключить все бусты? (y/n): ").strip().lower()
            if confirm == "y":
                set_flag("none", "false")
            else:
                print("Отменено")

        elif choice == "5":
            name = input("Название ивента: ").strip()
            multiplier = input("Множитель (число): ").strip()
            create_event(name, multiplier)

        elif choice == "6":
            print("Выход...")
            break

        else:
            print("❌ Неверный выбор")

        input("\nНажмите Enter для продолжения...")

if __name__ == "__main__":
    main()