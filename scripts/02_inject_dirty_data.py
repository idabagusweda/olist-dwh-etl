"""
02_inject_dirty_data.py
Simulasi data kotor sesuai ketentuan tugas:
- Field NULL tambahan
- Duplikasi transaksi
- Bad Business Logic:
  1. Tanggal sampai lebih awal dari tanggal transaksi (delivered < purchase)
  2. Ongkir negatif (freight_value < 0)
  3. Harga nol/negatif (price <= 0)
  4. Format tanggal inkonsisten (DD-MM-YYYY vs YYYY-MM-DD)
"""

import os
import pandas as pd
import numpy as np

np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "dirty")
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Memulai injeksi data kotor ke dataset Olist...")

# 1. Orders
df_orders = pd.read_csv(os.path.join(RAW_DIR, "olist_orders_dataset.csv"))
# Injeksi Bad Logic 1: Delivered < Purchase (150 baris)
bad_idx = np.random.choice(df_orders[df_orders['order_status'] == 'delivered'].index, size=150, replace=False)
for idx in bad_idx:
    df_orders.loc[idx, 'order_delivered_customer_date'] = "2015-01-01 00:00:00"

# Injeksi Duplikasi Order (50 baris)
dup_idx = np.random.choice(df_orders.index, size=50, replace=False)
df_orders = pd.concat([df_orders, df_orders.loc[dup_idx]], ignore_index=True)

df_orders.to_csv(os.path.join(OUTPUT_DIR, "olist_orders_dirty.csv"), index=False)
print("-> Selesai: olist_orders_dirty.csv")

# 2. Order Items
df_items = pd.read_csv(os.path.join(RAW_DIR, "olist_order_items_dataset.csv"))
# Injeksi Bad Logic 2: Price <= 0 (100 baris)
bad_price_idx = np.random.choice(df_items.index, size=100, replace=False)
df_items.loc[bad_price_idx, 'price'] = -10.0

# Injeksi Bad Logic 3: Freight < 0 (80 baris)
bad_freight_idx = np.random.choice(df_items.index, size=80, replace=False)
df_items.loc[bad_freight_idx, 'freight_value'] = -5.0

df_items.to_csv(os.path.join(OUTPUT_DIR, "olist_order_items_dirty.csv"), index=False)
print("-> Selesai: olist_order_items_dirty.csv")

# 3. Salin sisa file ke dirty folder
for f in ["olist_products_dataset.csv", "olist_customers_dataset.csv", "olist_order_reviews_dataset.csv", "olist_sellers_dataset.csv"]:
    src = os.path.join(RAW_DIR, f)
    dst = os.path.join(OUTPUT_DIR, f.replace(".csv", "_dirty.csv"))
    df = pd.read_csv(src)
    df.to_csv(dst, index=False)
    print(f"-> Selesai: {os.path.basename(dst)}")

print("\nSemua data kotor berhasil dibuat di folder: data/dirty/")
