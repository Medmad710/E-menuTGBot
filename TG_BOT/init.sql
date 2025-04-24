
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'cafe_db') THEN
      CREATE DATABASE cafe_db;
   END IF;
END
$$;

\connect cafe_db;

CREATE TABLE IF NOT EXISTS menu (
    item_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price INTEGER NOT NULL,
    rating NUMERIC(3, 2) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    order_count INTEGER DEFAULT 0,
    bonus_points INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id BIGINT ,
    menu_item_id INTEGER REFERENCES menu(item_id),
    order_price NUMERIC(7, 2) NOT NULL,
    order_datetime TIMESTAMP DEFAULT NOW()
);





INSERT INTO menu (name, category, price, rating) VALUES
    ('Онигири с курицей', 'Онигири', 650, 0),
    ('Онигири с сыром', 'Онигири', 650, 0),
    ('Онигири с семгой', 'Онигири', 750, 0),
    ('Онигири с тунцом', 'Онигири', 750, 0),
    ('Онигири с креветкой', 'Онигири', 750, 0),

    ('Тропический цитрус', 'Лимонады', 590, 0),
    ('Ягодно цитрусовый взрыв', 'Лимонады', 590, 0),
    ('Синий лайм', 'Лимонады', 590, 0),
    ('Персиковый цитрус', 'Лимонады', 590, 0),

    ('Americano S', 'Кофе', 490, 0),
    ('Americano M', 'Кофе', 590, 0),
    ('Americano L', 'Кофе', 690, 0),
    ('Latte S', 'Кофе', 790, 0),
    ('Latte M', 'Кофе', 890, 0),
    ('Latte L', 'Кофе', 990, 0),
    ('Cappuccino S', 'Кофе', 799, 0),
    ('Cappuccino M', 'Кофе', 890, 0),
    ('Cappuccino L', 'Кофе', 990, 0),
    ('Flat White M', 'Кофе', 1190, 0),
    ('RAF M', 'Кофе', 1090, 0),
    ('RAF L', 'Кофе', 1190, 0),
    ('Mocha M', 'Кофе', 1090, 0),
    ('Mocha L', 'Кофе', 1190, 0),

    ('Ice Latte', 'Ice drink', 990, 0),
    ('Ice Americano', 'Ice drink', 800, 0),
    ('Ice Matcha', 'Ice drink', 990, 0),
    ('Espresso Tonik', 'Ice drink', 1190, 0),

    ('Черный чай M', 'Чай', 350, 0),
    ('Черный чай L', 'Чай', 450, 0),
    ('Зеленый чай M', 'Чай', 350, 0),
    ('Зеленый чай L', 'Чай', 450, 0),
    ('Фруктовый чай M', 'Чай', 550, 0),
    ('Фруктовый чай L', 'Чай', 650, 0),
    ('Сезонный чай M', 'Чай', 550, 0),
    ('Сезонный чай L', 'Чай', 650, 0),

    ('Какао M', 'Напитки', 790, 0),
    ('Какао L', 'Напитки', 890, 0),
    ('Горячий шоколад M', 'Напитки', 790, 0),
    ('Горячий шоколад L', 'Напитки', 890, 0),
    ('Milk Waves', 'Напитки', 500, 0),

    ('Сендвич с колбасой', 'Сендвичи', 350, 0),
    ('Сендвич с курицей', 'Сендвичи', 380, 0),
    ('Сыр', 'Сендвичи', 60, 0),
    ('Моцарелла', 'Сендвичи', 60, 0),
    ('Сырный соус', 'Сендвичи', 100, 0),
    ('Халапенью', 'Сендвичи', 50, 0),
    ('Соленные огурцы', 'Сендвичи', 50, 0),
    ('Огурцы', 'Сендвичи', 50, 0),
    ('Помидоры', 'Сендвичи', 60, 0),

    ('Сникерс', 'Сладости', 350, 0),
    ('Марс', 'Сладости', 350, 0),
    ('Твикс', 'Сладости', 350, 0);
