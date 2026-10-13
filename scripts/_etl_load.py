"""
05_etl_load.py
TAHAP L (Load): Muat data bersih ke dalam Star Schema DWH (SQLite).
Urutan load: dim_date → dim_customer → dim_product → dim_seller
             → fact_orders → fact_reviews
"""

import os
import sqlite3
import pandas as pd
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "processed", "olist_dwh.db")
SQL_PATH = os.path.join(BASE_DIR, "sql", "01_create_dwh_schema.sql")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ================================================================
# Buat Skema DWH
# ================================================================

def create_schema(conn):
    with open(SQL_PATH, "r") as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()
    print("  OK  Skema DWH berhasil dibuat.")


# ================================================================
# Load dim_date (generate 2015-2020)
# ================================================================

def load_dim_date(conn):
    MONTH_NAMES = [
        '', 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    rows = []
    start = date(2015, 1, 1)
    end   = date(2020, 12, 31)
    current = start
    while current <= end:
        rows.append({
            "date_key":    int(current.strftime("%Y%m%d")),
            "full_date":   current.isoformat(),
            "year":        current.year,
            "quarter":     (current.month - 1) // 3 + 1,
            "month":       current.month,
            "month_name":  MONTH_NAMES[current.month],
            "day":         current.day,
            "day_of_week": current.strftime("%A"),
            "is_weekend":  current.weekday() >= 5
        })
        current += timedelta(days=1)

    df = pd.DataFrame(rows)
    df.to_sql("dim_date", conn, if_exists="append", index=False)
    print(f"  OK  dim_date     -> {len(df):,} baris")


# ================================================================
# Load dim_customer
# ================================================================

def load_dim_customer(conn, df_customers: pd.DataFrame):
    df = df_customers.rename(columns={
        "customer_zip_code_prefix": "zip_code_prefix",
        "customer_city":            "city",
        "customer_state":           "state"
    })[["customer_id", "customer_unique_id", "zip_code_prefix", "city", "state"]]

    df.to_sql("dim_customer", conn, if_exists="append", index=False)
    print(f"  OK  dim_customer -> {len(df):,} baris")
    return df


# ================================================================
# Load dim_product
# ================================================================

def load_dim_product(conn, df_products: pd.DataFrame, df_translation: pd.DataFrame):
    df = df_products.merge(
        df_translation,
        on="product_category_name",
        how="left"
    ).rename(columns={
        "product_category_name_english": "category_name_english",
        "product_category_name":         "category_name",
        "product_weight_g":              "weight_g",
        "product_length_cm":             "length_cm",
        "product_height_cm":             "height_cm",
        "product_width_cm":              "width_cm"
    })[["product_id", "category_name", "category_name_english", "weight_g", "length_cm", "height_cm", "width_cm"]]

    df.to_sql("dim_product", conn, if_exists="append", index=False)
    print(f"  OK  dim_product  -> {len(df):,} baris")


# ================================================================
# Load dim_seller
# ================================================================

def load_dim_seller(conn, df_sellers: pd.DataFrame):
    df = df_sellers.rename(columns={
        "seller_zip_code_prefix": "zip_code_prefix",
        "seller_city":            "city",
        "seller_state":           "state"
    })[["seller_id", "zip_code_prefix", "city", "state"]]

    df.to_sql("dim_seller", conn, if_exists="append", index=False)
    print(f"  OK  dim_seller   -> {len(df):,} baris")


# ================================================================
# Load fact_orders
# ================================================================

def load_fact_orders(conn, df_orders: pd.DataFrame, df_items: pd.DataFrame):
    # Lookup keys dari dim tabel
    cust_map    = pd.read_sql("SELECT customer_id, customer_key FROM dim_customer", conn).set_index("customer_id")["customer_key"]
    product_map = pd.read_sql("SELECT product_id, product_key FROM dim_product", conn).set_index("product_id")["product_key"]
    seller_map  = pd.read_sql("SELECT seller_id, seller_key FROM dim_seller", conn).set_index("seller_id")["seller_key"]

    # Join orders + items
    df = df_items.merge(
        df_orders[["order_id", "customer_id", "order_purchase_timestamp", "order_delivered_customer_date", "order_status", "is_delivered"]],
        on="order_id",
        how="inner"
    )

    # Kalkulasi delivery_days
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'], errors='coerce')
    df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'], errors='coerce')
    df['delivery_days'] = (df['order_delivered_customer_date'] - df['order_purchase_timestamp']).dt.days

    # Map surrogate keys
    df['date_key']     = df['order_purchase_timestamp'].dt.strftime("%Y%m%d").astype(float).astype('Int64')
    df['customer_key'] = df['customer_id'].map(cust_map)
    df['product_key']  = df['product_id'].map(product_map)
    df['seller_key']   = df['seller_id'].map(seller_map)

    # Hapus baris dengan key NULL (produk/seller tidak ditemukan di dim)
    before = len(df)
    df = df.dropna(subset=['customer_key', 'product_key', 'seller_key', 'date_key'])
    dropped = before - len(df)
    if dropped > 0:
        print(f"  WARN fact_orders: {dropped} baris dibuang (orphan key).")

    fact = df[["order_id", "order_item_id", "date_key", "customer_key", "product_key", "seller_key",
               "price", "freight_value", "total_value", "delivery_days", "order_status"]].copy()
    fact["date_key"]     = fact["date_key"].astype(int)
    fact["customer_key"] = fact["customer_key"].astype(int)
    fact["product_key"]  = fact["product_key"].astype(int)
    fact["seller_key"]   = fact["seller_key"].astype(int)

    fact.to_sql("fact_orders", conn, if_exists="append", index=False)
    print(f"  OK  fact_orders  -> {len(fact):,} baris")


# ================================================================
# Load fact_reviews
# ================================================================

def load_fact_reviews(conn, df_reviews: pd.DataFrame, df_orders: pd.DataFrame, df_items: pd.DataFrame):
    cust_map    = pd.read_sql("SELECT customer_id, customer_key FROM dim_customer", conn).set_index("customer_id")["customer_key"]
    product_map = pd.read_sql("SELECT product_id, product_key FROM dim_product", conn).set_index("product_id")["product_key"]

    # Review → order → customer & product (ambil produk pertama dari order)
    first_item = df_items.drop_duplicates(subset=['order_id'], keep='first')[['order_id', 'product_id']]
    df = df_reviews.merge(
        df_orders[['order_id', 'customer_id', 'order_purchase_timestamp']],
        on='order_id', how='inner'
    ).merge(first_item, on='order_id', how='inner')

    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'], errors='coerce')
    df['date_key']     = df['order_purchase_timestamp'].dt.strftime("%Y%m%d").astype(float).astype('Int64')
    df['customer_key'] = df['customer_id'].map(cust_map)
    df['product_key']  = df['product_id'].map(product_map)

    before = len(df)
    df = df.dropna(subset=['customer_key', 'product_key', 'date_key'])
    dropped = before - len(df)
    if dropped > 0:
        print(f"  WARN fact_reviews: {dropped} baris dibuang (orphan key).")

    fact = df[['review_id', 'order_id', 'date_key', 'customer_key', 'product_key', 'review_score', 'has_comment']].copy()
    fact['date_key']     = fact['date_key'].astype(int)
    fact['customer_key'] = fact['customer_key'].astype(int)
    fact['product_key']  = fact['product_key'].astype(int)

    fact.to_sql("fact_reviews", conn, if_exists="append", index=False)
    print(f"  OK  fact_reviews -> {len(fact):,} baris")


# ================================================================
# MAIN
# ================================================================

def load_all(cleaned: dict, df_translation: pd.DataFrame):
    print("=" * 60)
    print("LOAD: Memuat data bersih ke DWH (SQLite)")
    print(f"  Target DB: {DB_PATH}")
    print("=" * 60)

    conn = get_conn()
    create_schema(conn)
    load_dim_date(conn)
    load_dim_customer(conn, cleaned['customers'])
    load_dim_product(conn, cleaned['products'], df_translation)
    load_dim_seller(conn, cleaned['sellers'])
    load_fact_orders(conn, cleaned['orders'], cleaned['order_items'])
    load_fact_reviews(conn, cleaned['reviews'], cleaned['orders'], cleaned['order_items'])

    conn.close()
    print("\nLoad selesai. DWH siap diquery.\n")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, BASE_DIR)
    from scripts.etl_extract import extract_all
    from scripts.etl_transform import transform_all

    raw = extract_all()
    cleaned = transform_all(raw)

    DIRTY_DIR = os.path.join(BASE_DIR, "data", "dirty")
    translation_path = os.path.join(BASE_DIR, "data", "raw", "product_category_name_translation.csv")
    df_translation = pd.read_csv(translation_path)

    load_all(cleaned, df_translation)
