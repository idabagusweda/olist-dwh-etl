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

# Tahap 3: Query Manual & Analitik
# → buka data/processed/olist_dwh.db di SQLite Viewer
# → jalankan query dari sql/02_analytical_queries.sql

# Tahap 4: Dashboard Interaktif & Scheduler
streamlit run app.py

# Tahap 5: Jalankan Pengujian Validasi
python tests/test_dashboard.py
```

> **Catatan:** Jika ingin menjalankan ulang ETL dari awal, hapus dulu file `data/processed/olist_dwh.db` sebelum menjalankan `05_etl_load.py` atau gunakan tombol **Run ETL Now** pada halaman ETL Scheduler di dashboard.

---

## 📊 Dashboard Interaktif & ETL Scheduler

Repositori ini kini dilengkapi dengan web interface modern berbasis **Streamlit**, **Plotly**, dan **APScheduler** untuk mengeksplorasi Data Warehouse, memonitor metrik bisnis, memvisualisasikan Star Schema, dan mengontrol eksekusi pipeline ETL secara terjadwal.

### 1. Struktur Modul Dashboard

```
dashboard/
├── __init__.py
├── db.py                 # Query helper aman, connection pool, PRAGMA query_only
├── styles.py             # Custom CSS dark theme & glassmorphism styling
├── scheduler_engine.py   # APScheduler engine, subprocess execution & SQLite run logs
└── pages/
    ├── overview.py       # 📋 Ringkasan eksekutif (Total order, omzet, review, produk)
    ├── analytics.py      # 📈 Visualisasi tren bulanan, status pesanan, top produk, geografi
    ├── explorer.py       # 🗄️ Eksplorasi fisik tabel Fact & Dimensi (paginasi & filter)
    ├── star_schema.py    # ⭐ Diagram visual ER / Star Schema interaktif & relasi FK
    ├── scheduler.py      # ⏰ Kontrol scheduler (Start/Stop, Run Now, interval kustom)
    └── etl_logs.py       # 📝 Riwayat eksekusi ETL & live audit kualitas data
app.py                    # Entry point aplikasi Streamlit
tests/
└── test_dashboard.py     # Test suite validasi otomatis
```

### 2. Cara Menjalankan Dashboard

Pastikan virtual environment telah aktif dan dependensi terpasang:

```bash
# Aktifkan virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# Atau Linux/macOS:
# source venv/bin/activate

# Install dependensi (jika belum)
pip install -r requirements.txt

# Jalankan dashboard
streamlit run app.py
```

Setelah perintah dijalankan, antarmuka web akan otomatis terbuka di browser pada alamat default `http://localhost:8501`.

---

### 3. Panduan Fitur Setiap Halaman

#### 📋 A. Overview (Ringkasan Eksekutif)
- **KPI Cards:** Menampilkan metrik utama dari database DWH secara langsung:
  - Total Orders (pesanan unik)
  - Total Reviews (ulasan pelanggan)
  - Total Customers & Sellers
  - Total Revenue (R$) dari penjumlahan `total_value` pada `fact_orders`
  - Average Order Value (AOV) & Average Delivery Days
  - Average Review Score (skor rata-rata 1–5)
- **DWH Table Summary:** Ringkasan jumlah baris dan jumlah kolom untuk seluruh 6 tabel.

#### 📈 B. Analytics (Visualisasi Analitik Interaktif)
- **Filter Interaktif:** Multi-select filter berdasarkan Tahun (2016–2018), State Pelanggan, dan Status Pesanan.
- **Visualisasi Plotly:**
  - *Monthly Order & Revenue Trends:* Garis tren volume pesanan dan total omzet per bulan.
  - *Order Status Distribution:* Donut chart proporsi status pesanan (`delivered`, `shipped`, dll).
  - *Geographic Distribution:* Bar chart persebaran pesanan per provinsi/negara bagian pelanggan.
  - *Top 10 Product Categories:* Peringkat kategori produk berdasarkan omzet dan volume item terjual.
  - *Seller Performance:* Konsentrasi pesanan per kota seller.
  - *Review Score Distribution:* Histogram skor ulasan 1 sampai 5.
  - *Review Score Over Time:* Tren kepuasan pelanggan bulanan.

#### 🗄️ C. Fact & Dimension Explorer
- **Pemilihan Tabel:** Dropdown untuk memilih salah satu dari 6 tabel DWH (dikelompokkan rapi antara Fact Table dan Dimension Table).
- **Metadata Skema:** Menampilkan nama kolom, tipe data SQLite, Primary Key (🔑), Foreign Key (🔗), dan batasan Not Null.
- **Paginasi Efisien:** Menampilkan data dengan opsi limit (10, 25, 50, 100 baris per halaman) tanpa memuat seluruh tabel ke memori.
- **Pencarian Kolom:** Filter baris secara dinamis berdasarkan kolom yang dipilih menggunakan parameterized SQL `LIKE`.
- **Ekspor Data:** Fitur download CSV hanya untuk data halaman yang sedang dilihat.

#### ⭐ D. Star Schema Visualizer
- **Diagram ER:** Representasi visual diagram Star Schema menggunakan format Mermaid ER diagram.
- **Detail Entitas:** Accordion interaktif untuk memeriksa Primary Key, Foreign Keys, dan Measure/Attributes tiap tabel.
- **Tabel Ringkasan Relasi:** Daftar lengkap hubungan `fact_orders` dan `fact_reviews` ke tabel dimensi `dim_date`, `dim_customer`, `dim_product`, dan `dim_seller` yang ditegakkan langsung oleh SQLite Foreign Key constraints.

#### ⏰ E. ETL Scheduler
- **Kontrol Eksekusi:**
  - Tombol **Run ETL Now** untuk menjalankan pipeline `scripts/06_run_etl_pipeline.py` secara langsung.
  - Tombol **Start Scheduler** dan **Stop Scheduler** untuk mengaktifkan automasi berkala di background.
  - Pengaturan interval eksekusi: *Every 30 minutes*, *Every 1 hour*, *Every 6 hours*, *Every 12 hours*, *Daily*, *Weekly*, atau *Custom (menit)*.
- **Pencegahan Overlapping Runs:** Menggunakan threading lock internal agar pipeline tidak dijalankan bersamaan saat eksekusi sebelumnya masih berjalan.
- **Isolasi Subprocess:** Pipeline dieksekusi sebagai subprocess Python terpisah sehingga jika terjadi error tidak akan membuat server dashboard crash.
- **Log Execution:** Menampilkan status terkini (Running, Idle, Active), waktu run berikutnya, durasi eksekusi, serta log stdout/stderr detail.

#### 📝 F. ETL Logs & Data Quality
- **Riwayat Run:** Riwayat lengkap eksekusi ETL tersimpan di tabel internal `etl_log`.
- **Live Data Quality Checks:** Melakukan audit langsung terhadap data DWH saat ini:
  - *Key Column Integrity:* Memeriksa nilai NULL pada Foreign Key di fact tables.
  - *Referential Integrity (Orphan Detection):* Memastikan tidak ada foreign key yang tidak ditemukan di tabel dimensi.
  - *Business Logic Checks:* Validasi nilai harga > 0, freight >= 0, skor review antara 1–5, dan tanggal pengiriman valid.
  - *Row Count Audit:* Memantau volume data di seluruh tabel DWH.

---

### 4. Verifikasi dan Pengujian Otomatis

Repositori menyediakan skrip pengujian komprehensif di `tests/test_dashboard.py` untuk memvalidasi:
1. Koneksi SQLite database.
2. Keberadaan seluruh 6 tabel DWH (`dim_date`, `dim_customer`, `dim_product`, `dim_seller`, `fact_orders`, `fact_reviews`).
3. Ketersediaan data (row counts > 0).
4. Kebenaran agregasi SQL (omzet, skor review, formula harga).
5. Integritas referensial (Foreign Key integrity antar tabel fact dan dimensi).
6. Import kelengkapan dependensi modul dashboard.
7. Fungsi-fungsi helper modul database (`query_df`, `get_table_preview`, pagination).
8. Keberadaan skrip entrypoint ETL.
9. Mekanisme lock dan pencegahan overlapping runs scheduler.
10. Penanganan query kosong / filter tanpa hasil match.

Jalankan test suite menggunakan perintah:

```bash
python tests/test_dashboard.py
```

### 5. Batasan & Pertimbangan Teknis (Known Limitations)
- **Konkurensi Database SQLite:** SQLite mengizinkan banyak pembaca (*concurrent reads*) namun mengunci database saat ada proses penulisan (*single writer*). Dashboard mengaktifkan `PRAGMA query_only = ON` pada koneksi read-only dan `timeout=30` agar aktivitas browsing tidak terganggu selama proses ETL berlangsung.
- **Durasi Eksekusi ETL:** Eksekusi pipeline ETL lengkap pada ~100.000+ baris data memerlukan waktu sekitar 20–40 detik. Selama proses ini berlangsung, tombol *Run ETL Now* akan dinonaktifkan untuk mencegah tumpang tindih proses.
