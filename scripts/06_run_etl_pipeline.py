"""
06_run_etl_pipeline.py
MASTER SCRIPT: Jalankan pipeline ETL penuh dari satu perintah.
  E → T → L
Cara pakai:
  (dari root folder dwh_project)
  python scripts/06_run_etl_pipeline.py
"""

import os
import sys

# Tambahkan root project ke sys.path agar import scripts bisa jalan
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import pandas as pd

# Import langsung fungsi dari masing-masing script
from scripts._etl_extract   import extract_all
from scripts._etl_transform  import transform_all
from scripts._etl_load       import load_all

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  PIPELINE ETL - OLIST DWH")
    print("=" * 60 + "\n")

    # STEP 1: Extract
    raw = extract_all()

    # STEP 2: Transform
    cleaned = transform_all(raw)

    # STEP 3: Load
    translation_path = os.path.join(BASE_DIR, "data", "raw", "product_category_name_translation.csv")
    df_translation = pd.read_csv(translation_path)
    load_all(cleaned, df_translation)

    print("=" * 60)
    print("  PIPELINE SELESAI")
    print("=" * 60)
