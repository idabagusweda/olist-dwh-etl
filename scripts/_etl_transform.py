"""
04_etl_transform.py
TAHAP T (Transform / Data Cleansing):
Implementasi 3 teknik wajib + 1 bonus:
  Teknik 1 - Handle NULL values
  Teknik 2 - Remove duplicates
  Teknik 3 - Fix bad business logic (invalid dates, negative price/freight)
  Teknik 4 - Standardisasi format (bonus, nilai tambah di laporan)
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ================================================================
# TEKNIK 1: Handle NULL Values
# ================================================================

def cleanse_null_orders(df: pd.DataFrame) -> pd.DataFrame:
    before = df.isnull().sum().sum()

    # NULL order_approved_at → isi dengan order_purchase_timestamp
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'], errors='coerce')
    df['order_approved_at'] = pd.to_datetime(df['order_approved_at'], errors='coerce')
    mask = df['order_approved_at'].isnull()
    df.loc[mask, 'order_approved_at'] = df.loc[mask, 'order_purchase_timestamp']

    # NULL tanggal pengiriman → boleh dibiarkan (pesanan memang belum terkirim)
    # Tandai saja dengan kolom flag
    df['is_delivered'] = df['order_delivered_customer_date'].notnull()

    after = df.isnull().sum().sum()
    _log("TEKNIK 1 - Handle NULL (orders)", before, after)
    return df


def cleanse_null_products(df: pd.DataFrame) -> pd.DataFrame:
    before = df.isnull().sum().sum()

    # NULL product_category_name → isi 'unknown'
    df['product_category_name'] = df['product_category_name'].fillna('unknown')

    # NULL dimensi fisik (weight, length, height, width) → isi median
    for col in ['product_weight_g', 'product_length_cm', 'product_height_cm', 'product_width_cm']:
        median_val = df[col].median()
        df[col] = df[col].fillna(median_val)

    # NULL product_name_lenght, product_description_lenght, photos → isi 0
    for col in ['product_name_lenght', 'product_description_lenght', 'product_photos_qty']:
        df[col] = df[col].fillna(0).astype(int)

    after = df.isnull().sum().sum()
    _log("TEKNIK 1 - Handle NULL (products)", before, after)
    return df


# ================================================================
# TEKNIK 2: Remove Duplicates
# ================================================================

def cleanse_duplicates_orders(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)

    # Duplikasi order_id → keep baris paling awal
    df = df.drop_duplicates(subset=['order_id'], keep='first')

    after = len(df)
    _log("TEKNIK 2 - Hapus Duplikasi (orders)", before, after, unit="baris")
    return df


def cleanse_duplicates_reviews(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)

    # Duplikasi review_id → keep baris paling awal
    df = df.drop_duplicates(subset=['review_id'], keep='first')

    after = len(df)
    _log("TEKNIK 2 - Hapus Duplikasi (reviews)", before, after, unit="baris")
    return df


# ================================================================
# TEKNIK 3: Fix Bad Business Logic
# ================================================================

def cleanse_bad_logic_orders(df: pd.DataFrame) -> pd.DataFrame:
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'], errors='coerce')
    df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'], errors='coerce')

    before = len(df)

    # Hapus baris di mana tanggal sampai < tanggal beli
    mask_bad_date = (
        df['order_delivered_customer_date'].notnull() &
        (df['order_delivered_customer_date'] < df['order_purchase_timestamp'])
    )
    bad_count = mask_bad_date.sum()
    df = df[~mask_bad_date].copy()

    print(f"  [Teknik 3] Bad Logic Ditemukan (Tgl Sampai < Tgl Beli): {bad_count} baris → dihapus")
    after = len(df)
    _log("TEKNIK 3 - Fix Bad Logic Tanggal (orders)", before, after, unit="baris")
    return df


def cleanse_bad_logic_items(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)

    # Hapus baris price <= 0
    bad_price = (df['price'] <= 0).sum()
    df = df[df['price'] > 0].copy()

    # Hapus baris freight_value < 0
    bad_freight = (df['freight_value'] < 0).sum()
    df = df[df['freight_value'] >= 0].copy()

    print(f"  [Teknik 3] Bad Logic Ditemukan (Price <= 0): {bad_price} baris → dihapus")
    print(f"  [Teknik 3] Bad Logic Ditemukan (Freight < 0): {bad_freight} baris → dihapus")
    after = len(df)
    _log("TEKNIK 3 - Fix Bad Logic Price/Freight (order_items)", before, after, unit="baris")
    return df


# ================================================================
# TEKNIK 4 (Bonus): Standardisasi Format
# ================================================================

def standardize_text_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
    return df


# ================================================================
# MAIN TRANSFORM PIPELINE
# ================================================================

def transform_all(dfs: dict) -> dict:
    print("=" * 60)
    print("TRANSFORM: Data Cleansing (3 Teknik Wajib + 1 Bonus)")
    print("=" * 60)

    cleaned = {}

    # --- Orders ---
    df_orders = dfs['orders'].copy()
    df_orders = cleanse_null_orders(df_orders)
    df_orders = cleanse_duplicates_orders(df_orders)
    df_orders = cleanse_bad_logic_orders(df_orders)
    cleaned['orders'] = df_orders

    # --- Order Items ---
    df_items = dfs['order_items'].copy()
    df_items = cleanse_bad_logic_items(df_items)
    # Tambah kolom total_value
    df_items['total_value'] = df_items['price'] + df_items['freight_value']
    cleaned['order_items'] = df_items

    # --- Products ---
    df_products = dfs['products'].copy()
    df_products = cleanse_null_products(df_products)
    df_products = standardize_text_columns(df_products, ['product_category_name'])
    cleaned['products'] = df_products

    # --- Customers (Teknik 4: standardisasi kota/state) ---
    df_customers = dfs['customers'].copy()
    df_customers = standardize_text_columns(df_customers, ['customer_city', 'customer_state'])
    cleaned['customers'] = df_customers

    # --- Reviews ---
    df_reviews = dfs['reviews'].copy()
    df_reviews = cleanse_duplicates_reviews(df_reviews)
    # Tandai apakah ada komentar (NULL → False)
    df_reviews['has_comment'] = df_reviews['review_comment_message'].notnull()
    cleaned['reviews'] = df_reviews

    # --- Sellers ---
    df_sellers = dfs['sellers'].copy()
    df_sellers = standardize_text_columns(df_sellers, ['seller_city', 'seller_state'])
    cleaned['sellers'] = df_sellers

    print("\nTransform selesai.\n")
    return cleaned


# ================================================================
# HELPER
# ================================================================

def _log(label, before, after, unit="nilai NULL"):
    removed = before - after
    print(f"\n  {label}")
    print(f"    Sebelum : {before:,} {unit}")
    print(f"    Sesudah : {after:,} {unit}")
    print(f"    Dibersihkan : {removed:,} {unit}")


if __name__ == "__main__":
    from scripts.etl_extract import extract_all
    data = extract_all()
    cleaned = transform_all(data)
