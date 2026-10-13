"""
03_etl_extract.py
TAHAP E (Extract): Baca semua file kotor dari data/dirty/
dan lakukan preview + validasi jumlah baris.
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRTY_DIR = os.path.join(BASE_DIR, "data", "dirty")

def extract_all():
    files = {
        "orders":       "olist_orders_dirty.csv",
        "order_items":  "olist_order_items_dirty.csv",
        "products":     "olist_products_dataset_dirty.csv",
        "customers":    "olist_customers_dataset_dirty.csv",
        "reviews":      "olist_order_reviews_dataset_dirty.csv",
        "sellers":      "olist_sellers_dataset_dirty.csv",
    }

    dfs = {}
    print("=" * 60)
    print("EXTRACT: Membaca data dari folder data/dirty/")
    print("=" * 60)

    for name, filename in files.items():
        path = os.path.join(DIRTY_DIR, filename)
        if not os.path.exists(path):
            print(f"[SKIP] File tidak ada: {filename}")
            continue
        df = pd.read_csv(path, low_memory=False)
        dfs[name] = df
        print(f"  OK  {name:15s} -> {len(df):>7,} baris, {len(df.columns)} kolom")

    print("-" * 60)
    print("Extract selesai.\n")
    return dfs

# alias untuk import dari pipeline master
def etl_extract(): return extract_all()

if __name__ == "__main__":
    data = extract_all()
