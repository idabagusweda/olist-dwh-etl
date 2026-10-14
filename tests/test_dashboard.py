"""
tests/test_dashboard.py — Validation tests for the Olist DWH Dashboard.

Run: python tests/test_dashboard.py
"""

import os
import sys
import sqlite3
import traceback

# Ensure safe output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Resolve paths relative to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

DB_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "olist_dwh.db")

EXPECTED_TABLES = {
    "dim_date", "dim_customer", "dim_product", "dim_seller",
    "fact_orders", "fact_reviews",
}

PASS = 0
FAIL = 0
TOTAL = 0


def check(name, condition, detail=""):
    global PASS, FAIL, TOTAL
    TOTAL += 1
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}{' - ' + detail if detail else ''}")


def test_db_connection():
    """Test 1: Database connection."""
    print("\n" + "=" * 60)
    print("TEST 1: Database Connection")
    print("=" * 60)

    check("Database file exists", os.path.exists(DB_PATH), f"Expected at: {DB_PATH}")

    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.execute("SELECT 1")
        result = cursor.fetchone()
        check("SQLite connection works", result is not None and result[0] == 1)
        conn.close()
    except Exception as e:
        check("SQLite connection works", False, str(e))


def test_table_discovery():
    """Test 2: Table discovery."""
    print("\n" + "=" * 60)
    print("TEST 2: Table Discovery")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    tables = {r[0] for r in cursor.fetchall()}
    conn.close()

    for t in EXPECTED_TABLES:
        check(f"Table '{t}' exists", t in tables)

    # etl_log may or may not exist yet
    check("All expected tables found", EXPECTED_TABLES.issubset(tables))


def test_row_counts():
    """Test 3: Row counts are non-zero."""
    print("\n" + "=" * 60)
    print("TEST 3: Row Counts")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    for t in sorted(EXPECTED_TABLES):
        cursor = conn.execute(f"SELECT COUNT(*) FROM [{t}]")
        count = cursor.fetchone()[0]
        check(f"Table '{t}' has data ({count:,} rows)", count > 0)
    conn.close()


def test_sql_aggregations():
    """Test 4: SQL aggregation correctness."""
    print("\n" + "=" * 60)
    print("TEST 4: SQL Aggregation Correctness")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH, timeout=10)

    # Total revenue should be positive
    cursor = conn.execute("SELECT SUM(total_value) FROM fact_orders")
    total_rev = cursor.fetchone()[0]
    check("Total revenue > 0", total_rev is not None and total_rev > 0,
          f"Got: {total_rev}")

    # Average review score should be between 1 and 5
    cursor = conn.execute("SELECT AVG(review_score) FROM fact_reviews")
    avg_score = cursor.fetchone()[0]
    check("Avg review score between 1-5",
          avg_score is not None and 1.0 <= avg_score <= 5.0,
          f"Got: {avg_score}")

    # Distinct orders count
    cursor = conn.execute("SELECT COUNT(DISTINCT order_id) FROM fact_orders")
    dist_orders = cursor.fetchone()[0]
    check("Distinct orders > 0", dist_orders > 0, f"Got: {dist_orders}")

    # total_value ≈ price + freight_value
    cursor = conn.execute("""
        SELECT COUNT(*) FROM fact_orders
        WHERE ABS(total_value - (price + freight_value)) > 0.01
    """)
    mismatch = cursor.fetchone()[0]
    check("total_value = price + freight_value (within tolerance)",
          mismatch == 0, f"Mismatches: {mismatch}")

    # No negative prices
    cursor = conn.execute("SELECT COUNT(*) FROM fact_orders WHERE price <= 0")
    neg = cursor.fetchone()[0]
    check("No negative/zero prices", neg == 0, f"Found: {neg}")

    # Review scores in valid range
    cursor = conn.execute(
        "SELECT COUNT(*) FROM fact_reviews WHERE review_score < 1 OR review_score > 5"
    )
    bad = cursor.fetchone()[0]
    check("All review scores in 1-5 range", bad == 0, f"Out of range: {bad}")

    conn.close()


def test_referential_integrity():
    """Test 5: Foreign key referential integrity."""
    print("\n" + "=" * 60)
    print("TEST 5: Referential Integrity")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH, timeout=10)

    fk_checks = [
        ("fact_orders", "date_key", "dim_date", "date_key"),
        ("fact_orders", "customer_key", "dim_customer", "customer_key"),
        ("fact_orders", "product_key", "dim_product", "product_key"),
        ("fact_orders", "seller_key", "dim_seller", "seller_key"),
        ("fact_reviews", "date_key", "dim_date", "date_key"),
        ("fact_reviews", "customer_key", "dim_customer", "customer_key"),
        ("fact_reviews", "product_key", "dim_product", "product_key"),
    ]

    for fact, fk_col, dim, pk_col in fk_checks:
        cursor = conn.execute(f"""
            SELECT COUNT(*) FROM [{fact}] f
            WHERE f.[{fk_col}] NOT IN (SELECT [{pk_col}] FROM [{dim}])
        """)
        orphans = cursor.fetchone()[0]
        check(f"{fact}.{fk_col} → {dim}.{pk_col}",
              orphans == 0, f"Orphan rows: {orphans}")

    conn.close()


def test_dashboard_imports():
    """Test 6: Dashboard module imports."""
    print("\n" + "=" * 60)
    print("TEST 6: Dashboard Module Imports")
    print("=" * 60)

    try:
        from dashboard import db
        check("Import dashboard.db", True)
    except Exception as e:
        check("Import dashboard.db", False, str(e))

    try:
        from dashboard import styles
        check("Import dashboard.styles", True)
    except Exception as e:
        check("Import dashboard.styles", False, str(e))

    try:
        from dashboard.scheduler_engine import (
            run_etl_pipeline, is_etl_running,
            start_scheduler, stop_scheduler,
            get_scheduler_status, get_run_history,
        )
        check("Import dashboard.scheduler_engine", True)
    except Exception as e:
        check("Import dashboard.scheduler_engine", False, str(e))


def test_db_module_functions():
    """Test 7: Dashboard DB module functions."""
    print("\n" + "=" * 60)
    print("TEST 7: Dashboard DB Module Functions")
    print("=" * 60)

    from dashboard import db

    check("db_exists() returns True", db.db_exists())

    try:
        count = db.get_table_row_count("fact_orders")
        check("get_table_row_count('fact_orders')", count > 0, f"Count: {count}")
    except Exception as e:
        check("get_table_row_count('fact_orders')", False, str(e))

    try:
        cols = db.get_table_columns("fact_orders")
        check("get_table_columns('fact_orders')", len(cols) > 0, f"Columns: {len(cols)}")
    except Exception as e:
        check("get_table_columns('fact_orders')", False, str(e))

    try:
        fks = db.get_table_foreign_keys("fact_orders")
        check("get_table_foreign_keys('fact_orders')", len(fks) > 0, f"FKs: {len(fks)}")
    except Exception as e:
        check("get_table_foreign_keys('fact_orders')", False, str(e))

    try:
        df = db.get_table_preview("dim_customer", limit=5)
        check("get_table_preview('dim_customer')", len(df) == 5, f"Rows: {len(df)}")
    except Exception as e:
        check("get_table_preview('dim_customer')", False, str(e))

    try:
        df = db.query_df("SELECT COUNT(*) AS cnt FROM dim_date")
        check("query_df() works", len(df) == 1 and df.iloc[0]["cnt"] > 0)
    except Exception as e:
        check("query_df() works", False, str(e))

    try:
        val = db.query_scalar("SELECT COUNT(*) FROM dim_product")
        check("query_scalar() works", val > 0, f"Value: {val}")
    except Exception as e:
        check("query_scalar() works", False, str(e))

    # Test invalid table name raises error
    try:
        db.get_table_row_count("invalid_table")
        check("Invalid table raises ValueError", False, "No exception raised")
    except ValueError:
        check("Invalid table raises ValueError", True)
    except Exception as e:
        check("Invalid table raises ValueError", False, str(e))


def test_etl_script_exists():
    """Test 8: ETL script existence."""
    print("\n" + "=" * 60)
    print("TEST 8: ETL Scripts Exist")
    print("=" * 60)

    scripts = [
        "scripts/03_etl_extract.py",
        "scripts/04_etl_transform.py",
        "scripts/05_etl_load.py",
        "scripts/06_run_etl_pipeline.py",
        "scripts/_etl_extract.py",
        "scripts/_etl_transform.py",
        "scripts/_etl_load.py",
    ]

    for s in scripts:
        path = os.path.join(PROJECT_ROOT, s)
        check(f"Script exists: {s}", os.path.exists(path))


def test_scheduler_controls():
    """Test 9: Scheduler engine controls."""
    print("\n" + "=" * 60)
    print("TEST 9: Scheduler Controls")
    print("=" * 60)

    from dashboard.scheduler_engine import (
        is_etl_running, get_scheduler_status, get_run_history,
    )

    check("is_etl_running() returns bool", isinstance(is_etl_running(), bool))

    status = get_scheduler_status()
    check("get_scheduler_status() returns dict",
          isinstance(status, dict) and "running" in status)

    history = get_run_history(limit=5)
    check("get_run_history() returns list", isinstance(history, list))


def test_empty_data_handling():
    """Test 10: Dashboard behavior with missing data."""
    print("\n" + "=" * 60)
    print("TEST 10: Empty Data Handling")
    print("=" * 60)

    from dashboard import db

    # Query with impossible filter should return empty df
    df = db.query_df("SELECT * FROM fact_orders WHERE 1=0")
    check("Empty query returns empty DataFrame", len(df) == 0)

    # Search with impossible term
    df = db.get_table_preview("dim_date", search="zzzznotexist", search_column="month_name")
    check("Search with no matches returns empty DataFrame", len(df) == 0)

    count = db.get_filtered_row_count("dim_date", search="zzzznotexist", search_column="month_name")
    check("Filtered count with no matches returns 0", count == 0)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  OLIST DWH DASHBOARD - VALIDATION TESTS")
    print("=" * 60)

    try:
        test_db_connection()
        test_table_discovery()
        test_row_counts()
        test_sql_aggregations()
        test_referential_integrity()
        test_dashboard_imports()
        test_db_module_functions()
        test_etl_script_exists()
        test_scheduler_controls()
        test_empty_data_handling()
    except Exception as e:
        print(f"\n[ERROR] UNEXPECTED ERROR: {e}")
        traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"  RESULTS: {PASS} passed, {FAIL} failed, {TOTAL} total")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)
