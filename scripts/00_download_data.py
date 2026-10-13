"""
00_download_data.py
Script untuk mengunduh dataset Olist Brazilian E-Commerce secara otomatis
dari mirror GitHub ke folder data/raw/.
"""

import os
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

BASE_URL = "https://raw.githubusercontent.com/Kaaykun/OlistAnalysis/master/data/csv"

FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_products_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]

def download_all():
    print("=" * 60)
    print("MENGUNDUH DATASET OLIST DARI REPOSITORY...")
    print(f"Target folder: {RAW_DIR}")
    print("=" * 60)

    for f in FILES:
        url = f"{BASE_URL}/{f}"
        dest = os.path.join(RAW_DIR, f)

        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            print(f"  [SUDAH ADA] {f} ({size_mb:.2f} MB)")
            continue

        print(f"  [MENGUNDUH] {f}...", end="", flush=True)
        try:
            urllib.request.urlretrieve(url, dest)
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            print(f" Selesai ({size_mb:.2f} MB)")
        except Exception as e:
            print(f" GAGAL: {e}")

    print("-" * 60)
    print("Semua dataset siap di data/raw/.\n")

if __name__ == "__main__":
    download_all()
