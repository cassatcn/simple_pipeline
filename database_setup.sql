CREATE SCHEMA IF NOT EXISTS raw;

-- USERS_RAW
DROP TABLE IF EXISTS raw.users_raw;
CREATE TABLE raw.users_raw (
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    password_hash TEXT,
    phone_number TEXT,
    date_of_birth TEXT,
    time_on_app TEXT,
    user_type TEXT, 
    is_active TEXT, 
    last_payment_method TEXT,
    reviews TEXT, 
    last_ip TEXT,
    last_coordinates TEXT, 
    last_device TEXT, 
    last_browser TEXT,
    last_os TEXT,
    last_login TEXT,
    last_logout TEXT,
    in_cart TEXT,
    wishlist TEXT,
    last_search TEXT,
    created_date TEXT,
    generated_at TEXT,
    purchase_count TEXT,
    total_spent TEXT
);

-- PURCHASES_RAW
DROP TABLE IF EXISTS raw.purchases_raw;
CREATE TABLE raw.purchases_raw (
    transaction_id TEXT,
    user_email TEXT,
    product_name TEXT,
    product_category TEXT,
    quantity TEXT,
    unit_price TEXT,
    discount_percent TEXT,
    discount_amount TEXT,
    shipping_cost TEXT,
    total_price TEXT,
    purchase_date TEXT,
    purchase_time TEXT,
    payment_method TEXT,
    purchase_status TEXT,
    month TEXT,
    year TEXT
);

-- USERS
CREATE TABLE IF NOT EXISTS users (
    email VARCHAR PRIMARY KEY,
    first_name VARCHAR,
    last_name VARCHAR,
    user_type VARCHAR,
    total_spent DECIMAL,
    purchase_count INTEGER,
    last_device VARCHAR
);

-- PURCHASES
CREATE TABLE IF NOT EXISTS purchases (
    transaction_id VARCHAR PRIMARY KEY,
    user_email VARCHAR REFERENCES users(email),
    product_name VARCHAR,
    product_category VARCHAR,
    total_price DECIMAL,
    purchase_date DATE
);