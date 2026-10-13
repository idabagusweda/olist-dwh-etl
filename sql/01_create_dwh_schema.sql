-- ============================================================
-- DDL: Star Schema Data Warehouse Olist Brazilian E-Commerce
-- ============================================================
-- DWH terdiri dari:
--   4 Tabel Dimensi : dim_date, dim_customer, dim_product, dim_seller
--   2 Tabel Fakta   : fact_orders, fact_reviews
-- ============================================================

-- ========================
-- DROP (urutan: fact dulu, baru dim)
-- ========================
DROP TABLE IF EXISTS fact_reviews;
DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_seller;

-- ========================
-- DIMENSI 1: dim_date
-- ========================
CREATE TABLE dim_date (
    date_key        INTEGER PRIMARY KEY,  -- format YYYYMMDD
    full_date       DATE NOT NULL,
    year            INTEGER NOT NULL,
    quarter         INTEGER NOT NULL,     -- 1-4
    month           INTEGER NOT NULL,     -- 1-12
    month_name      VARCHAR(15) NOT NULL,
    day             INTEGER NOT NULL,     -- 1-31
    day_of_week     VARCHAR(10) NOT NULL, -- Monday..Sunday
    is_weekend      BOOLEAN NOT NULL
);

-- ========================
-- DIMENSI 2: dim_customer
-- ========================
CREATE TABLE dim_customer (
    customer_key        INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id         VARCHAR(50) NOT NULL UNIQUE,
    customer_unique_id  VARCHAR(50) NOT NULL,
    zip_code_prefix     VARCHAR(10),
    city                VARCHAR(100),
    state               VARCHAR(5)
);

-- ========================
-- DIMENSI 3: dim_product
-- ========================
CREATE TABLE dim_product (
    product_key             INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id              VARCHAR(50) NOT NULL UNIQUE,
    category_name           VARCHAR(100),
    category_name_english   VARCHAR(100),
    weight_g                REAL,
    length_cm               REAL,
    height_cm               REAL,
    width_cm                REAL
);

-- ========================
-- DIMENSI 4: dim_seller
-- ========================
CREATE TABLE dim_seller (
    seller_key          INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id           VARCHAR(50) NOT NULL UNIQUE,
    zip_code_prefix     VARCHAR(10),
    city                VARCHAR(100),
    state               VARCHAR(5)
);

-- ========================
-- FAKTA 1: fact_orders
-- Grain: 1 baris = 1 item dalam 1 pesanan
-- ========================
CREATE TABLE fact_orders (
    order_item_key      INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id            VARCHAR(50) NOT NULL,
    order_item_id       INTEGER NOT NULL,
    date_key            INTEGER NOT NULL REFERENCES dim_date(date_key),
    customer_key        INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    product_key         INTEGER NOT NULL REFERENCES dim_product(product_key),
    seller_key          INTEGER NOT NULL REFERENCES dim_seller(seller_key),
    -- Measures
    price               REAL NOT NULL,
    freight_value       REAL NOT NULL,
    total_value         REAL NOT NULL,       -- price + freight_value
    delivery_days       INTEGER,             -- NULL jika belum terkirim
    order_status        VARCHAR(30)
);

-- ========================
-- FAKTA 2: fact_reviews
-- Grain: 1 baris = 1 ulasan dari 1 pesanan
-- ========================
CREATE TABLE fact_reviews (
    review_key          INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id           VARCHAR(50) NOT NULL,
    order_id            VARCHAR(50) NOT NULL,
    date_key            INTEGER NOT NULL REFERENCES dim_date(date_key),
    customer_key        INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    product_key         INTEGER NOT NULL REFERENCES dim_product(product_key),
    -- Measures
    review_score        INTEGER NOT NULL,    -- 1-5
    has_comment         BOOLEAN NOT NULL     -- TRUE jika ada komentar
);
