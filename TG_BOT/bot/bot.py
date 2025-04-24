import asyncpg
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.client.bot import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

# # # Токен Настоящего бота
API_TOKEN = "7560925634:AAEOwzxMM_j9gi2rE72kWaNNAMoS4TkFSkI"



# Бот для тестов
# API_TOKEN = "7802809540:AAFC8kFdP22BP4Q5sA3e839paZUhMFZgX4Y"
 # #

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

DB_USER = 'cafe_user'
DB_PASSWORD = 'secure_password'
DB_NAME = 'cafe_db'
DB_HOST = 'db'  

db_pool = None
chef_chat_id = None
user_carts = {}

async def create_db_pool():
    return await asyncpg.create_pool(
        user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port='5432'
    )

async def get_categories():
    async with db_pool.acquire() as connection:
        return await connection.fetch("SELECT DISTINCT category FROM menu")

async def get_dishes_by_category(category):
    async with db_pool.acquire() as connection:
        return await connection.fetch("SELECT item_id, name, price FROM menu WHERE category = $1", category)

async def save_order(customer_id, menu_item_id, order_price):
    async with db_pool.acquire() as connection:
        await connection.execute(
            "INSERT INTO orders (customer_id, menu_item_id, order_price) VALUES ($1, $2, $3)",
            customer_id, menu_item_id, order_price
        )

async def save_user(telegram_id):
    async with db_pool.acquire() as connection:
        existing_user = await connection.fetchrow("SELECT * FROM customers WHERE telegram_id = $1", telegram_id)
        if not existing_user:
            await connection.execute(
                "INSERT INTO customers (telegram_id) VALUES ($1)",
                telegram_id
            )



##########################################################################################################################



# Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: Message):
    categories = await get_categories()
    keyboard = InlineKeyboardBuilder()

    for category in categories:
        keyboard.row(
            types.InlineKeyboardButton(
                text=f"{category['category']} 🍽️", callback_data=f"category_{category['category']}"
            )
        )

    await message.answer("Добро пожаловать в наше кафе! 😊\nПожалуйста, выберите категорию меню:", reply_markup=keyboard.as_markup())

@dp.callback_query(F.data.startswith("category_"))
async def handle_category(call: CallbackQuery):
    category = call.data.split("_", 1)[1]
    dishes = await get_dishes_by_category(category)
    keyboard = InlineKeyboardBuilder()

    for dish in dishes:
        keyboard.row(
            types.InlineKeyboardButton(
                text=f"{dish['name']} - {dish['price']}₸ 🥗", callback_data=f"dish_{dish['item_id']}"
            )
        )

    keyboard.row(
        types.InlineKeyboardButton(text="🔙 Вернуться к категориям", callback_data="back_to_categories"),
        types.InlineKeyboardButton(text="💳 Оплатить", callback_data="checkout")
    )
    
    await call.message.edit_text(f"Вы смотрите блюда из категории: {category} 🍽️", reply_markup=keyboard.as_markup())


@dp.callback_query(F.data == "back_to_categories")
async def back_to_categories(call: CallbackQuery):
    categories = await get_categories()
    keyboard = InlineKeyboardBuilder()

    for category in categories:
        keyboard.row(
            types.InlineKeyboardButton(
                text=f"{category['category']} 🍴", callback_data=f"category_{category['category']}"
            )
        )

    await call.message.edit_text("Выберите категорию меню: 🍽️", reply_markup=keyboard.as_markup())




async def update_category_keyboard(call: CallbackQuery, category: str, message: str):
    dishes = await get_dishes_by_category(category)
    user_id = call.from_user.id
    cart = user_carts.get(user_id, [])

    cart_counts = {item['item_id']: item['quantity'] for item in cart}

    keyboard = InlineKeyboardBuilder()

    for dish in dishes:
        quantity = cart_counts.get(dish['item_id'], 0)
        button_text = f"{dish['name']} - {dish['price']}₸ 🥗 {f'({quantity} шт.)' if quantity > 0 else ''}"
        keyboard.row(
            types.InlineKeyboardButton(
                text=button_text, callback_data=f"dish_{dish['item_id']}"
            )
        )

    keyboard.row(
        types.InlineKeyboardButton(text="🔙 Вернуться к категориям", callback_data="back_to_categories"),
        types.InlineKeyboardButton(text="💳 Оплатить", callback_data="checkout")
    )

    await call.message.edit_text(f"Вы смотрите блюда из категории: {category} 🍽️", reply_markup=keyboard.as_markup())
    await call.answer(message)


@dp.callback_query(F.data.startswith("category_"))
async def handle_category(call: CallbackQuery):
    category = call.data.split("_", 1)[1]
    await update_category_keyboard(call, category, f"Вы смотрите блюда из категории: {category} 🍽️")

async def get_dishes_by_category(category):
    async with db_pool.acquire() as connection:
        return await connection.fetch("SELECT item_id, name, price, category FROM menu WHERE category = $1", category)




@dp.callback_query(F.data.startswith("dish_"))
async def handle_dish(call: CallbackQuery):
    item_id = int(call.data.split("_", 1)[1])
    user_id = call.from_user.id

    async with db_pool.acquire() as connection:
        dish = await connection.fetchrow("SELECT item_id, name, price, category FROM menu WHERE item_id = $1", item_id)

    if user_id not in user_carts:
        user_carts[user_id] = []

    found = False
    for item in user_carts[user_id]:
        if item['item_id'] == dish['item_id']:
            item['quantity'] += 1
            found = True
            break

    if not found:
        user_carts[user_id].append({
            'item_id': dish['item_id'],
            'name': dish['name'],
            'price': dish['price'],
            'quantity': 1
        })

    # Обновляем клавиатуру категории
    await update_category_keyboard(call, dish['category'], f"🎉 {dish['name']} добавлено в корзину! 🛒")




##########################################################################################################################




async def use_customer_bonus(user_id, total_price):
    """
    Использует бонусы клиента для уменьшения суммы заказа.

    :param user_id: Telegram ID клиента
    :param total_price: Общая сумма заказа
    :return: (оставшаяся сумма заказа, количество использованных бонусов)
    """
    async with db_pool.acquire() as connection:
        customer = await connection.fetchrow("SELECT bonus_points FROM customers WHERE telegram_id = $1", user_id)
        bonus_points = customer['bonus_points']

        used_bonus = min(bonus_points, total_price)

        await connection.execute(
            "UPDATE customers SET bonus_points = bonus_points - $1 WHERE telegram_id = $2",
            used_bonus, user_id
        )

        remaining_price = total_price - used_bonus

    return remaining_price, used_bonus




@dp.callback_query(F.data == "checkout")
async def handle_checkout(call: CallbackQuery):
    user_id = call.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await call.answer("Ваша корзина пуста! 🛒", show_alert=True)
        return

    used_bonus = sum(item['price'] for item in cart if item['name'] == "Бонусы")
    total_price = sum(item['price'] * item['quantity'] for item in cart if item['name'] != "Бонусы")

    final_price = total_price + used_bonus 

    order_summary = "\n".join(
        f"{idx + 1}. {item['name']} x{item['quantity']} - {item['price']}₸ (за штуку)"
        for idx, item in enumerate(cart) if item['name'] != "Бонусы"
    )
    if used_bonus:
        order_summary += f"\nБонусы: {used_bonus}₸"

    order_summary += f"\n\n💰 Итого: {final_price}₸"

    async with db_pool.acquire() as connection:
        customer = await connection.fetchrow("SELECT bonus_points FROM customers WHERE telegram_id = $1", user_id)
        available_bonuses = customer['bonus_points'] if customer else 0

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        types.InlineKeyboardButton(text="Оплатить картой kaspi💳", callback_data="give_paying_by_card")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="Оплатить на месте 💵", callback_data="pay_on_site"),
    )
    if not used_bonus:  
        keyboard.row(
            types.InlineKeyboardButton(text=f"Использовать бонусы 🎁 ({available_bonuses}₸)", callback_data="use_bonus")
        )
        keyboard.row(
        types.InlineKeyboardButton(text="Оплатить telegram wallet✈️", callback_data="give_paying_by_ton"),
    )
    keyboard.row(
        types.InlineKeyboardButton(text="Отмена ❌", callback_data="cancel_order")
    )

    await call.message.edit_text(f"🛒 Ваш заказ:\n{order_summary}", reply_markup=keyboard.as_markup())


@dp.callback_query(F.data == "use_bonus")
async def handle_use_bonus(call: CallbackQuery):
    user_id = call.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await call.answer("Ваша корзина пуста! 🛒", show_alert=True)
        return

    total_price = sum(item['price'] for item in cart)

    remaining_price, used_bonus = await use_customer_bonus(user_id, total_price)

    cart.append({'name': 'Бонусы', 'price': -used_bonus})
    user_carts[user_id] = cart

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        types.InlineKeyboardButton(text="Оплатить на месте 💵", callback_data="pay_on_site"),
    )
    keyboard.add(
        types.InlineKeyboardButton(text="Оплатить картой kaspi💳", callback_data="give_paying_by_card")
    )
    keyboard.row(
        types.InlineKeyboardButton(text="Оплатить telegram wallet✈️", callback_data="give_paying_by_ton"),
    )
    keyboard.row(
        types.InlineKeyboardButton(text="Отмена ❌", callback_data="cancel_order")
    )

    order_summary = "\n".join(f"{idx + 1}. {item['name']} : {item['price']}₸" for idx, item in enumerate(cart))
    order_summary += f"\n\n💰 Итого с учетом бонусов: {remaining_price}₸"

    await call.message.edit_text(f"🛒 Ваш заказ:\n{order_summary}", reply_markup=keyboard.as_markup())


@dp.callback_query(F.data == "give_paying_by_card")
async def handle_payment_by_card(call: CallbackQuery):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        types.InlineKeyboardButton(text="kaspi ссылка для оплаты 💳", url="https://pay.kaspi.kz/pay/17daeycr")  
    )
    keyboard.row(
        types.InlineKeyboardButton(text="Уже оплатил ✅", callback_data="pay_by_card"),
        types.InlineKeyboardButton(text="Отмена ❌", callback_data="cancel_order")
    )

    await call.message.edit_text("Перейдите по ссылке для оплаты и нажмите 'Уже оплатил' после завершения 💸.", reply_markup=keyboard.as_markup())


                


@dp.callback_query(F.data == "give_paying_by_ton")
async def handle_payment_by_card(call: CallbackQuery):
    name=(await bot.get_chat(chef_chat_id)).username
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        types.InlineKeyboardButton(text="телеграмм повара",url=f"https://t.me/"+name) 
    )
    keyboard.row(
        types.InlineKeyboardButton(text="Уже оплатил ✅", callback_data="pay_by_ton"),
        types.InlineKeyboardButton(text="Отмена ❌", callback_data="cancel_order")
    )

    await call.message.edit_text("Перейдите по ссылке , оплатите заказ через telegram wallet и нажмите 'Уже оплатил' после завершения 💸.", reply_markup=keyboard.as_markup())

@dp.callback_query(F.data == "cancel_order")
async def handle_cancel_order(call: CallbackQuery):
    user_id = call.from_user.id
    if user_id in user_carts:
        del user_carts[user_id]

    categories = await get_categories()
    keyboard = InlineKeyboardBuilder()

    for category in categories:
        keyboard.row(
            types.InlineKeyboardButton(
                text=f"{category['category']} 🍴", callback_data=f"category_{category['category']}"
            )
        )

    await call.message.edit_text("Выберите категорию меню: 🍽️", reply_markup=keyboard.as_markup())
    await call.answer("Ваш заказ был отменён! ❌", show_alert=True)



@dp.callback_query(F.data == "delete_item")
async def handle_delete_item(call: CallbackQuery):
    user_id = call.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await call.answer("Ваша корзина пуста!", show_alert=True)
        return

    keyboard = InlineKeyboardBuilder()
    for idx, item in enumerate(cart):
        if idx % 2 == 0: 
            keyboard.row(
                types.InlineKeyboardButton(
                    text=f"Удалить {item['name']}", callback_data=f"remove_{idx}"
                )
            )
        else:
            keyboard.add(
                types.InlineKeyboardButton(
                    text=f"Удалить {item['name']}", callback_data=f"remove_{idx}"
                )
            )
    keyboard.row(
        types.InlineKeyboardButton(text="Назад к оплате", callback_data="checkout")
    )
    keyboard.add(
        types.InlineKeyboardButton(text="Добавить блюдо", callback_data="back_to_categories")
    )

    await call.message.edit_text("Выберите блюдо для удаления:", reply_markup=keyboard.as_markup())

@dp.callback_query(F.data.startswith("remove_"))
async def handle_remove_item(call: CallbackQuery):
    user_id = call.from_user.id
    item_index = int(call.data.split("_")[1])

    if user_id in user_carts and 0 <= item_index < len(user_carts[user_id]):
        removed_item = user_carts[user_id].pop(item_index)
        await call.answer(f"Блюдо {removed_item['name']} удалено из корзины.")
    else:
        await call.answer("Не удалось удалить блюдо.", show_alert=True)

    await handle_checkout(call)




##########################################################################################################################



async def add_cashback_to_customer(user_id, total_price):

    cashback = int(total_price * 0.01)  

    # Обновляем данные в базе
    async with db_pool.acquire() as connection:
        await connection.execute(
            "UPDATE customers SET bonus_points = bonus_points + $1 WHERE telegram_id = $2",
            cashback, user_id
        )
    return cashback


@dp.callback_query(F.data == "pay_on_site")
async def handle_payment(call: CallbackQuery):
    user_id = call.from_user.id
    cart = user_carts.pop(user_id, [])
    username = call.from_user.username or "Неизвестный пользователь"
    total_price = sum(item['price'] for item in cart)

    for item in cart:
        if item['name'] != 'Бонусы':  
            await save_order(user_id, item['item_id'], item['price'])

    cashback = await add_cashback_to_customer(user_id, total_price)

    await call.answer("Ваш заказ принят! Мы уведомим вас, когда он будет готов.")

    if chef_chat_id:
        order_summary = "\n".join(f"{item['name']} : {item['price']}₸" for item in cart)
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            types.InlineKeyboardButton(text="Через 5 минут", callback_data=f"ready_5_{user_id}"),
            types.InlineKeyboardButton(text="Через 10 минут", callback_data=f"ready_10_{user_id}"),
            types.InlineKeyboardButton(text="Через 20 минут", callback_data=f"ready_20_{user_id}")
        )
        keyboard.add(
            types.InlineKeyboardButton(text="Готово", callback_data=f"order_ready_{user_id}")
        )

        await bot.send_message(
            chef_chat_id,
            f"Новый заказ от @{username} (ID: {user_id}):\n{order_summary}\n\nИтого: {total_price}₸\nОплата: На месте",
            reply_markup=keyboard.as_markup()
        )

    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        types.InlineKeyboardButton(text="Вернуться и сделать заказ", callback_data="back_to_categories")
    )

    await call.message.edit_text(
        f"Спасибо за ваш заказ! 😊 Повар скоро сообщит, когда всё будет готово.\n"
        f"💳 Вам начислено {cashback} бонусов. Желаем вам отличного дня!",
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data == "pay_by_card")
async def handle_payment(call: CallbackQuery):
    username = call.from_user.username or "Неизвестный пользователь"
    user_id = call.from_user.id
    cart = user_carts.pop(user_id, [])

    total_price = sum(item['price'] for item in cart)

    for item in cart:
        if item['name'] != 'Бонусы': 
            await save_order(user_id, item['item_id'], item['price'])

    cashback = await add_cashback_to_customer(user_id, total_price)

    await call.answer("Ваш заказ принят! Мы уведомим вас, когда он будет готов.")

    if chef_chat_id:
        order_summary = "\n".join(f"{item['name']} : {item['price']}₸" for item in cart)
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            types.InlineKeyboardButton(text="Через 5 минут", callback_data=f"ready_5_{user_id}"),
            types.InlineKeyboardButton(text="Через 10 минут", callback_data=f"ready_10_{user_id}"),
            types.InlineKeyboardButton(text="Через 20 минут", callback_data=f"ready_20_{user_id}")
        )
        keyboard.add(
            types.InlineKeyboardButton(text="Готово", callback_data=f"order_ready_{user_id}")
        )

        await bot.send_message(
            chef_chat_id,
            f"Новый заказ от @{username} (ID: {user_id}):\n{order_summary}\n\nИтого: {total_price}₸\nОплата: Картой",
            reply_markup=keyboard.as_markup()
        )

    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        types.InlineKeyboardButton(text="Вернуться и сделать заказ", callback_data="back_to_categories")
    )

    await call.message.edit_text(
        f"Спасибо за ваш заказ! 😊 Повар скоро сообщит, когда всё будет готово.\n"
        f"💳 Вам начислено {cashback} бонусов. Желаем вам отличного дня!",
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(F.data == "pay_by_ton")
async def handle_payment(call: CallbackQuery):
    username = call.from_user.username or "Неизвестный пользователь"
    user_id = call.from_user.id
    cart = user_carts.pop(user_id, [])

    total_price = sum(item['price'] for item in cart)

    for item in cart:
        if item['name'] != 'Бонусы':  
            await save_order(user_id, item['item_id'], item['price'])

    cashback = await add_cashback_to_customer(user_id, total_price)

    await call.answer("Ваш заказ принят! Мы уведомим вас, когда он будет готов.")

    if chef_chat_id:
        order_summary = "\n".join(f"{item['name']} : {item['price']}₸" for item in cart)
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            types.InlineKeyboardButton(text="Через 5 минут", callback_data=f"ready_5_{user_id}"),
            types.InlineKeyboardButton(text="Через 10 минут", callback_data=f"ready_10_{user_id}"),
            types.InlineKeyboardButton(text="Через 20 минут", callback_data=f"ready_20_{user_id}")
        )
        keyboard.add(
            types.InlineKeyboardButton(text="Готово", callback_data=f"order_ready_{user_id}")
        )

        await bot.send_message(
            chef_chat_id,
            f"Новый заказ от @{username} (ID: {user_id}):\n{order_summary}\n\nИтого: {total_price}₸\nОплата: telegram wallet",
            reply_markup=keyboard.as_markup()
        )

    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        types.InlineKeyboardButton(text="Вернуться и сделать заказ", callback_data="back_to_categories")
    )

    await call.message.edit_text(
        f"Спасибо за ваш заказ! 😊 Повар скоро сообщит, когда всё будет готово.\n"
        f"💳 Вам начислено {cashback} бонусов. Желаем вам отличного дня!",
        reply_markup=keyboard.as_markup()
    )



@dp.callback_query(F.data.startswith("ready_"))
async def handle_ready_time(call: CallbackQuery):
    parts = call.data.split("_")
    if len(parts) != 3:
        await call.answer("Ошибка: Неверные данные (callback).", show_alert=True)
        return

    time_option = parts[1]
    user_id = int(parts[2])

    if time_option == "5":
        await bot.send_message(user_id, "Ваш заказ будет готов через 5 минут!")
    elif time_option == "10":
        await bot.send_message(user_id, "Ваш заказ будет готов через 10 минут!")
    elif time_option == "20":
        await bot.send_message(user_id, "Ваш заказ будет готов через 20 минут!")

    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        types.InlineKeyboardButton(text="Готово", callback_data=f"order_ready_{user_id}")
    )

    await call.message.edit_reply_markup(reply_markup=keyboard.as_markup())
    await call.answer("Сообщение отправлено покупателю.")

@dp.callback_query(F.data.startswith("order_ready_"))
async def handle_order_ready(call: CallbackQuery):
    parts = call.data.split("_")
    if len(parts) != 3:
        await call.answer("Ошибка: Неверные данные(callback)", show_alert=True)
        return

    user_id = int(parts[2])

    await bot.send_message(user_id, "Ваш заказ готов! Заберите его, пожалуйста.")
    await call.message.edit_text("Сообщение отправлено покупателю.")
    await call.answer("Сообщение отправлено покупателю.")







##########################################################################################################################







@dp.message(Command("admin"))
async def admin_command(message: Message):
    await message.answer("Введите пароль:")

@dp.message(F.text == "admin6421")
async def admin_login(message: Message):
    global chef_chat_id
    chef_chat_id = message.from_user.id
    await message.answer("Вы вошли как администратор. Теперь вы будете получать уведомления о новых заказах.")

@dp.callback_query(F.data.startswith("order_ready_"))
async def handle_order_ready(call: CallbackQuery):
    user_id = int(call.data.split("_", 2)[2])
    await bot.send_message(user_id, "Ваш заказ готов! Заберите его, пожалуйста.")
    await call.answer("Сообщение отправлено покупателю.")





##########################################################################################################################


offsets = {
    "menu": 0,
    "customers": 0,
    "orders": 0
}
LIMIT = 20  

def create_navigation_keyboard(table_name):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        types.InlineKeyboardButton(text="Предыдущие 20", callback_data=f"{table_name}_prev"),
        types.InlineKeyboardButton(text="Следующие 20", callback_data=f"{table_name}_next")
    )
    return keyboard

@dp.message(Command("show_menu"))
async def show_menu_command(message: Message):
        async with db_pool.acquire() as connection:
            data = await connection.fetch("SELECT * FROM menu OFFSET $1 LIMIT $2", offsets["menu"], LIMIT)
        
        if not data:
            await message.answer("В таблице 'menu' нет данных.")
            return

        response = "Данные из таблицы 'menu':\n"
        for item in data:
            response += f"{item['item_id']}: {item['name']} ({item['category']}) - {item['price']}₸\n"

        keyboard = create_navigation_keyboard("menu")
        await message.answer(response, reply_markup=keyboard.as_markup())


@dp.message(Command("show_customers"))
async def show_customers_command(message: Message):

        async with db_pool.acquire() as connection:
            data = await connection.fetch("SELECT * FROM customers OFFSET $1 LIMIT $2", offsets["customers"], LIMIT)
        
        if not data:
            await message.answer("В таблице 'customers' нет данных.")
            return

        response = "Данные из таблицы 'customers':\n"
        for customer in data:
            response += f"ID: {customer['customer_id']}, Telegram ID: {customer['telegram_id']}, Заказы: {customer['order_count']}, Бонусы: {customer['bonus_points']}\n"

        keyboard = create_navigation_keyboard("customers")
        await message.answer(response, reply_markup=keyboard.as_markup())


@dp.message(Command("show_orders"))
async def show_orders_command(message: Message):

        async with db_pool.acquire() as connection:
            data = await connection.fetch("SELECT * FROM orders OFFSET $1 LIMIT $2", offsets["orders"], LIMIT)
        
        if not data:
            await message.answer("В таблице 'orders' нет данных.")
            return

        response = "Данные из таблицы 'orders':\n"
        for order in data:
            response += f"ID заказа: {order['order_id']}, ID клиента: {order['customer_id']}, Позиция: {order['menu_item_id']}, Цена: {order['order_price']}₸, Дата: {order['order_datetime']}\n"

        keyboard = create_navigation_keyboard("orders")
        await message.answer(response, reply_markup=keyboard.as_markup())


@dp.callback_query(F.data.endswith("_prev") | F.data.endswith("_next"))
async def handle_navigation(call: CallbackQuery):
    table_name = call.data.split("_")[0]
    direction = call.data.split("_")[1]

    if direction == "next":
        offsets[table_name] += LIMIT
    elif direction == "prev" and offsets[table_name] >= LIMIT:
        offsets[table_name] -= LIMIT

    if table_name == "menu":
        await show_menu_command(call.message)
    elif table_name == "customers":
        await show_customers_command(call.message)
    elif table_name == "orders":
        await show_orders_command(call.message)

    await call.answer("")


##########################################################################################################################





@dp.message(Command("inject1"))
async def inject_sql_command(message: Message):
    sql_code = """
INSERT INTO menu (name, category, price, rating) VALUES

    ('Сыр', 'Сендвичи', 60, 0),
    ('Моцарелла', 'Сендвичи', 60, 0),
    ('Сырный соус', 'Сендвичи', 100, 0),
    ('Халапенью', 'Сендвичи', 50, 0),
    ('Соленные огурцы', 'Сендвичи', 50, 0),
    ('Огурцы', 'Сендвичи', 50, 0),
    ('Помидоры', 'Сендвичи', 60, 0);

    """
    
    try:
        async with db_pool.acquire() as connection:
            await connection.execute(sql_code)
            await message.answer("SQL-код выполнен успешно!")
    except Exception as e:
        await message.answer(f"Произошла ошибка при выполнении SQL-кода:\n{e}")











async def on_startup():
    global db_pool
    db_pool = await create_db_pool()
    print("Подключение к базе данных установлено")

async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


   