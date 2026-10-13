import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

print("=" * 70)
print("PROFILING DATA MENTAH OLTP (OLIST BRAZILIAN E-COMMERCE)")
print("=" * 70)

datasets = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv"
}

for name, filename in datasets.items():
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"\n[!] File tidak ditemukan: {filepath}")
        continue
        
    df = pd.read_csv(filepath)
    print(f"\n>>> Tabel: {name} ({filename})")
    print(f"Total Baris  : {len(df):,}")
    print(f"Total Kolom  : {len(df.columns)}")
    
    # 1. Analisis NULL values
    null_counts = df.isnull().sum()
    null_cols = null_counts[null_counts > 0]
    if len(null_cols) > 0:
        print("\n  [Kotor 1] Missing Values (NULL):")
        for col, count in null_cols.items():
            pct = (count / len(df)) * 100
            print(f"    - {col}: {count:,} baris ({pct:.2f}%)")
    else:
        print("  - Tidak ada missing value.")
        
    # 2. Analisis Duplikasi
    dup_count = df.duplicated().sum()
    print(f"\n  [Kotor 2] Duplikasi Baris Penuh: {dup_count} baris")
    
    # Cek duplikasi Primary Key spesifik
    pk_map = {
        "orders": "order_id",
        "products": "product_id",
        "customers": "customer_id",
        "order_reviews": "review_id"
    }
    if name in pk_map:
        pk = pk_map[name]
        pk_dups = df[pk].duplicated().sum()
        print(f"  [Kotor 2] Duplikasi Primary Key ({pk}): {pk_dups} baris")
        
    # 3. Analisis Business Logic Anomalies
    if name == "orders":
        df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'], errors='coerce')
        df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'], errors='coerce')
        
        # Anomali: tanggal sampai lebih awal dari tanggal beli
        invalid_dates = df[df['order_delivered_customer_date'] < df['order_purchase_timestamp']]
        print(f"\n  [Kotor 3] Bad Logic (Tgl Sampai < Tgl Beli): {len(invalid_dates)} baris")
        
    elif name == "order_items":
        invalid_price = df[df['price'] <= 0]
        invalid_freight = df[df['freight_value'] < 0]
        print(f"\n  [Kotor 3] Bad Logic (Price <= 0): {len(invalid_price)} baris")
        print(f"  [Kotor 3] Bad Logic (Freight < 0): {len(invalid_freight)} baris")

print("\n" + "=" * 70)
print("PROFILING SELESAI")
print("=" * 70)
