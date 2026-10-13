# DWH Project: Brazilian E-Commerce (Olist)
**Mata Kuliah:** Pangkalan Data / Data Warehouse
**Dataset:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

---

## Struktur Direktori

```
dwh_project/
├── data/
│   ├── raw/              # CSV asli dari Olist (7 file)
│   ├── dirty/            # CSV hasil injeksi data kotor (simulasi ETL)
│   └── processed/
│       └── olist_dwh.db  # Database DWH final (SQLite)
├── scripts/
│   ├── 00_download_data.py       # Unduh dataset Olist otomatis
│   ├── 01_profile_raw_data.py    # Audit/profiling data mentah
│   ├── 02_inject_dirty_data.py   # Injeksi bad logic & anomali
│   ├── 03_etl_extract.py         # E: Extract dari data/dirty/
│   ├── 04_etl_transform.py       # T: Data cleansing (3 teknik)
│   ├── 05_etl_load.py            # L: Load ke Star Schema DWH
│   └── 06_run_etl_pipeline.py    # Master: jalankan E→T→L sekaligus
├── sql/
│   ├── 01_create_dwh_schema.sql  # DDL Star Schema (4 dim, 2 fact)
│   └── 02_analytical_queries.sql # 5 query analitik siap pakai
├── notebooks/                    # Eksplorasi data via Jupyter (opsional)
└── requirements.txt              # Dependensi Python
```

---

## Arsitektur Sistem

```
[OLTP - CSV Olist]
  orders, order_items, products,
  customers, reviews, sellers
        |
        v
  [EXTRACT]  scripts/03_etl_extract.py
  Baca 6 file CSV kotor dari data/dirty/
        |
        v
  [TRANSFORM]  scripts/04_etl_transform.py
  Teknik 1: Handle NULL values
  Teknik 2: Remove duplicates
  Teknik 3: Fix bad business logic
  Teknik 4: Standardisasi format (bonus)
        |
        v
  [LOAD]  scripts/05_etl_load.py
  Muat ke Star Schema DWH (SQLite)
        |
        v
[DWH - data/processed/olist_dwh.db]
  dim_date, dim_customer, dim_product, dim_seller
  fact_orders, fact_reviews
```

---

## Panduan Eksekusi Lengkap

> Semua perintah dijalankan dari root folder `dwh_project/` di terminal IDE.

### Step 0: Unduh Dataset (Wajib Bagi yang Baru Clone Repo)

Dataset tidak disimpan langsung di GitHub agar repositori tetap ringan. Jalankan script ini untuk mengunduh seluruh file CSV ke folder `data/raw/` secara otomatis:

```bash
python scripts/00_download_data.py
```

---

### Persiapan Environment (Satu Kali)

```bash
# 1. Buat virtual environment
python3 -m venv venv

# 2. Aktifkan virtual environment
source venv/bin/activate

# 3. Install dependensi
pip install -r requirements.txt
```

> Tanda `(venv)` akan muncul di awal baris terminal jika berhasil aktif.

---

### Tahap 1: Audit Data Mentah

**Tujuan:** Lihat kondisi data asli sebelum diproses — berapa baris, kolom apa saja, dan apakah ada nilai NULL, duplikat, atau anomali.

```bash
python scripts/01_profile_raw_data.py
```

**Cara membaca output:**
```
>>> Tabel: orders
Total Baris  : 99,441           ← jumlah record
Total Kolom  : 8
[Kotor 1] Missing Values:
  - order_approved_at: 160 (0.16%)  ← kolom dengan NULL + persentasenya
[Kotor 2] Duplikasi: 0 baris        ← 0 = tidak ada duplikat
[Kotor 3] Bad Logic: 0 baris        ← 0 = tidak ada anomali logika
```

---

### Tahap 1 (Lanjut): Injeksi Data Kotor

**Tujuan:** Simulasikan data anomali ke dalam dataset agar semua teknik cleansing bisa didemonstrasikan. Jalankan **satu kali saja**.

```bash
python scripts/02_inject_dirty_data.py
```

**Cara membaca output:**
```
-> Selesai: olist_orders_dirty.csv     ← file kotor berhasil dibuat
-> Selesai: olist_order_items_dirty.csv
...
```

**Cek hasilnya:** Buka folder `data/dirty/` di file explorer IDE — harus ada 6 file CSV.

**Anomali yang disimulasikan:**
| File | Anomali yang Ditambahkan |
|------|--------------------------|
| `olist_orders_dirty.csv` | 150 baris tanggal sampai < tanggal beli, 50 baris duplikat |
| `olist_order_items_dirty.csv` | 100 baris price ≤ 0, 80 baris freight < 0 |

---

### Tahap 2A: Extract

**Tujuan:** Baca semua file CSV kotor dari `data/dirty/` dan validasi jumlah datanya.

```bash
python scripts/03_etl_extract.py
```

**Cara membaca output:**
```
EXTRACT: Membaca data dari folder data/dirty/
  OK  orders          ->  99,491 baris, 8 kolom
  OK  order_items     -> 112,650 baris, 7 kolom
  OK  products        ->  32,951 baris, 9 kolom
  OK  customers       ->  99,441 baris, 5 kolom
  OK  reviews         ->  99,224 baris, 7 kolom
  OK  sellers         ->   3,095 baris, 4 kolom
```

> Angka baris di sini adalah data **sebelum** dibersihkan. Catat angka ini untuk bahan laporan.

---

### Tahap 2B: Transform (Data Cleansing)

**Tujuan:** Bersihkan data dengan 3 teknik wajib + 1 bonus.

```bash
python scripts/04_etl_transform.py
```

**Cara membaca output:**
```
TEKNIK 1 - Handle NULL (orders)
  Sebelum : 4,912 nilai NULL   ← total NULL di seluruh kolom sebelum dibersihkan
  Sesudah : 4,752 nilai NULL   ← setelah NULL order_approved_at diisi fallback
  Dibersihkan : 160 nilai NULL

TEKNIK 2 - Hapus Duplikasi (orders)
  Sebelum : 99,491 baris       ← termasuk 50 baris duplikat yang diinjeksi
  Sesudah : 99,441 baris
  Dibersihkan : 50 baris       ← 50 duplikat berhasil dihapus

[Teknik 3] Bad Logic (Tgl Sampai < Tgl Beli): 150 baris → dihapus
[Teknik 3] Bad Logic (Price <= 0): 100 baris → dihapus
[Teknik 3] Bad Logic (Freight < 0): 80 baris → dihapus
```

**Ringkasan teknik cleansing:**
| Teknik | Aksi | Target |
|--------|------|--------|
| 1 - Handle NULL | Isi fallback / median / `'unknown'` | `order_approved_at`, `product_category_name`, dimensi produk |
| 2 - Deduplication | Drop baris duplikat, keep baris pertama | `order_id`, `review_id` |
| 3 - Bad Logic | Drop baris tidak valid | Tanggal, price, freight |
| 4 - Standardisasi (bonus) | Lowercase + strip spasi | Nama kota, nama state |

---

### Tahap 2C: Load ke DWH

**Tujuan:** Muat data bersih ke database SQLite dengan struktur Star Schema.

```bash
python scripts/05_etl_load.py
```

**Cara membaca output:**
```
LOAD: Memuat data bersih ke DWH (SQLite)
  Target DB: data/processed/olist_dwh.db
  OK  Skema DWH berhasil dibuat.     ← tabel dim & fact berhasil dibuat
  OK  dim_date     -> 2,192 baris    ← kalender 2015–2020
  OK  dim_customer -> 99,441 baris
  OK  dim_product  -> 32,951 baris
  OK  dim_seller   ->  3,095 baris
  OK  fact_orders  -> 112,300 baris  ← grain: 1 baris = 1 item pesanan
  OK  fact_reviews ->  97,395 baris  ← grain: 1 baris = 1 ulasan
Load selesai. DWH siap diquery.
```

**Setelah selesai:** File `data/processed/olist_dwh.db` terbuat. Ini adalah DWH final.

---

### Tahap 3: Buka & Query DWH di VS Code

**Install ekstensi SQLite Viewer:**
1. Tekan `Cmd+Shift+X`
2. Cari **SQLite Viewer** (by Florian Klampfer)
3. Klik **Install**

**Buka database:**
1. Di panel Explorer (kiri) → navigasi ke `data/processed/olist_dwh.db`
2. Klik file → terbuka di tab SQLite Viewer
3. Klik nama tabel untuk preview isi data

**Jalankan query analitik via terminal:**

```bash
# Q1: Top 10 kategori produk berdasarkan omzet
python3 -c "
import sqlite3, pandas as pd
conn = sqlite3.connect('data/processed/olist_dwh.db')
q = '''
  SELECT p.category_name_english AS kategori,
         COUNT(DISTINCT f.order_id) AS total_pesanan,
         ROUND(SUM(f.price), 2) AS total_omzet
  FROM fact_orders f
  JOIN dim_product p ON f.product_key = p.product_key
  GROUP BY p.category_name_english
  ORDER BY total_omzet DESC LIMIT 10
'''
print(pd.read_sql(q, conn).to_string(index=False))
conn.close()
"
```

```bash
# Q2: Tren penjualan bulanan 2017-2018
python3 -c "
import sqlite3, pandas as pd
conn = sqlite3.connect('data/processed/olist_dwh.db')
q = '''
  SELECT d.year AS tahun, d.month AS bulan, d.month_name,
         COUNT(*) AS total_transaksi,
         ROUND(SUM(f.total_value), 2) AS total_pendapatan
  FROM fact_orders f
  JOIN dim_date d ON f.date_key = d.date_key
  WHERE d.year IN (2017, 2018)
  GROUP BY d.year, d.month
  ORDER BY d.year, d.month
'''
print(pd.read_sql(q, conn).to_string(index=False))
conn.close()
"
```

```bash
# Q3: Rata-rata skor review per kategori produk
python3 -c "
import sqlite3, pandas as pd
conn = sqlite3.connect('data/processed/olist_dwh.db')
q = '''
  SELECT p.category_name_english AS kategori,
         COUNT(*) AS total_ulasan,
         ROUND(AVG(r.review_score), 2) AS rata_skor
  FROM fact_reviews r
  JOIN dim_product p ON r.product_key = p.product_key
  GROUP BY p.category_name_english
  ORDER BY rata_skor DESC LIMIT 10
'''
print(pd.read_sql(q, conn).to_string(index=False))
conn.close()
"
```

**Cara membaca hasil query:**
```
         kategori  total_pesanan  total_omzet
health_beauty          9670      1234567.89   ← kategori teratas
watches_gifts          8320       987654.32
...
```
> Setiap baris = 1 kategori produk. `total_omzet` = total harga semua item terjual di kategori tersebut.

---

### Tahap 4: Bahan Laporan

Screenshot output yang perlu disertakan di laporan:

| No | Yang di-screenshot | Dari mana |
|----|-------------------|-----------|
| 1 | Profiling data mentah (NULL, duplikat) | Output `01_profile_raw_data.py` |
| 2 | Hasil inject data kotor | Output `02_inject_dirty_data.py` |
| 3 | Hasil cleansing (sebelum vs sesudah) | Output `04_etl_transform.py` |
| 4 | Tabel DWH berhasil diisi | Output `05_etl_load.py` |
| 5 | Preview tabel di SQLite Viewer | VS Code → olist_dwh.db |
| 6 | Hasil 3 query analitik | Terminal query Q1, Q2, Q3 |

---

## Ringkasan Perintah (Cheat Sheet)

```bash
# Clone & Unduh Data
git clone <URL_REPO>
cd olist-dwh-etl
python scripts/00_download_data.py

# Setup Environment (satu kali)
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Tahap 1: Audit & Injeksi
python scripts/01_profile_raw_data.py   # lihat kondisi data mentah
python scripts/02_inject_dirty_data.py  # buat data kotor (satu kali)

# Tahap 2: ETL
python scripts/03_etl_extract.py        # E: baca data kotor
python scripts/04_etl_transform.py      # T: cleansing
python scripts/05_etl_load.py           # L: load ke DWH

# Tahap 3: Query
# → buka data/processed/olist_dwh.db di SQLite Viewer
# → jalankan query dari sql/02_analytical_queries.sql
```

> **Catatan:** Jika ingin menjalankan ulang ETL dari awal, hapus dulu file `data/processed/olist_dwh.db` sebelum menjalankan `05_etl_load.py`.
