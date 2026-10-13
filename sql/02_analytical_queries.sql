-- ============================================================
-- Analytical Queries: Olist DWH Star Schema
-- Jalankan setelah pipeline ETL selesai
-- ============================================================

-- Q1: Total omzet per kategori produk (Top 10)
SELECT
    p.category_name_english         AS kategori,
    COUNT(DISTINCT f.order_id)      AS total_pesanan,
    SUM(f.price)                    AS total_omzet,
    ROUND(AVG(f.price), 2)          AS rata_harga
FROM fact_orders f
JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.category_name_english
ORDER BY total_omzet DESC
LIMIT 10;

-- ============================================================

-- Q2: Tren penjualan bulanan (tahun 2017-2018)
SELECT
    d.year              AS tahun,
    d.month             AS bulan,
    d.month_name        AS nama_bulan,
    COUNT(*)            AS total_transaksi,
    SUM(f.total_value)  AS total_pendapatan
FROM fact_orders f
JOIN dim_date d ON f.date_key = d.date_key
WHERE d.year IN (2017, 2018)
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

-- ============================================================

-- Q3: Rata-rata skor review per kategori produk
SELECT
    p.category_name_english         AS kategori,
    COUNT(r.review_key)             AS total_ulasan,
    ROUND(AVG(r.review_score), 2)   AS rata_skor,
    SUM(CASE WHEN r.has_comment = 1 THEN 1 ELSE 0 END) AS ulasan_dengan_komentar
FROM fact_reviews r
JOIN dim_product p ON r.product_key = p.product_key
GROUP BY p.category_name_english
ORDER BY rata_skor DESC
LIMIT 10;

-- ============================================================

-- Q4: Performa pengiriman (rata-rata hari pengiriman per state pelanggan)
SELECT
    c.state                         AS state_pelanggan,
    COUNT(*)                        AS total_pesanan,
    ROUND(AVG(f.delivery_days), 1)  AS rata_hari_kirim
FROM fact_orders f
JOIN dim_customer c ON f.customer_key = c.customer_key
WHERE f.delivery_days IS NOT NULL
GROUP BY c.state
ORDER BY rata_hari_kirim ASC
LIMIT 15;

-- ============================================================

-- Q5: Top 10 seller berdasarkan total omzet
SELECT
    s.city                          AS kota_seller,
    s.state                         AS state_seller,
    COUNT(DISTINCT f.order_id)      AS total_pesanan,
    ROUND(SUM(f.price), 2)          AS total_omzet
FROM fact_orders f
JOIN dim_seller s ON f.seller_key = s.seller_key
GROUP BY s.seller_key, s.city, s.state
ORDER BY total_omzet DESC
LIMIT 10;
