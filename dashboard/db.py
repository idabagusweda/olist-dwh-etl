"""
dashboard/db.py — Database connection helper for the Olist DWH dashboard.
All dashboard queries go through this module. Uses read-only access
(via PRAGMA query_only) for dashboard reads. The ETL scheduler uses
a separate writable connection.
"""

import os
import sqlite3
import pandas as pd
import streamlit as st
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Paths — resolved relative to project root (one level up from dashboard/)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "olist_dwh.db")

# ---------------------------------------------------------------------------
# Allowed physical table names (whitelist for SQL identifier safety)
# ---------------------------------------------------------------------------
ALLOWED_TABLES = frozenset([
    "dim_date", "dim_customer", "dim_product", "dim_seller",
    "fact_orders", "fact_reviews",
])

DIMENSION_TABLES = frozenset([
    "dim_date", "dim_customer", "dim_product", "dim_seller",
])

FACT_TABLES = frozenset([
    "fact_orders", "fact_reviews",
])

TABLE_DESCRIPTIONS = {
    "dim_date": "Calendar dimension covering 2015–2020. Provides year, quarter, month, day, and day-of-week attributes for date-based analysis.",
    "dim_customer": "Customer dimension. Each row represents one unique customer record with location data (city, state, zip code).",
    "dim_product": "Product dimension. Contains product categories (Portuguese + English), physical dimensions, and weight.",
    "dim_seller": "Seller dimension. Contains seller location information (city, state, zip code).",
    "fact_orders": "Order line-item fact table. Grain: one row per order item. Contains price, freight, total value, delivery days, and order status. Links to dim_date, dim_customer, dim_product, dim_seller.",
    "fact_reviews": "Review fact table. Grain: one row per review. Contains review score and comment flag. Links to dim_date, dim_customer, dim_product.",
}


def _validate_table(table_name: str) -> str:
    """Validate and return a safe table name."""
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name


@contextmanager
def get_connection(readonly: bool = True):
    """Context manager for a SQLite connection.
    
    When readonly=True, sets PRAGMA query_only = ON to prevent
    accidental writes from the dashboard layer.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run the ETL pipeline first: python scripts/06_run_etl_pipeline.py"
        )
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    if readonly:
        conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Execute a read-only query and return a DataFrame."""
    with get_connection(readonly=True) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def query_scalar(sql: str, params: tuple = ()):
    """Execute a read-only query and return a single scalar value."""
    with get_connection(readonly=True) as conn:
        cursor = conn.execute(sql, params)
        row = cursor.fetchone()
        return row[0] if row else None


def get_table_row_count(table_name: str) -> int:
    """Return exact row count for a validated table."""
    safe = _validate_table(table_name)
    return query_scalar(f"SELECT COUNT(*) FROM [{safe}]")


def get_table_columns(table_name: str) -> list[dict]:
    """Return column metadata for a validated table."""
    safe = _validate_table(table_name)
    with get_connection(readonly=True) as conn:
        cursor = conn.execute(f"PRAGMA table_info([{safe}])")
        rows = cursor.fetchall()
        return [
            {
                "cid": r[0],
                "name": r[1],
                "type": r[2],
                "notnull": bool(r[3]),
                "default": r[4],
                "pk": bool(r[5]),
            }
            for r in rows
        ]


def get_table_foreign_keys(table_name: str) -> list[dict]:
    """Return foreign key metadata for a validated table."""
    safe = _validate_table(table_name)
    with get_connection(readonly=True) as conn:
        cursor = conn.execute(f"PRAGMA foreign_key_list([{safe}])")
        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "seq": r[1],
                "table": r[2],
                "from": r[3],
                "to": r[4],
            }
            for r in rows
        ]


def get_table_preview(
    table_name: str,
    limit: int = 25,
    offset: int = 0,
    search: str = "",
    search_column: str = "",
) -> pd.DataFrame:
    """Return a paginated preview of a validated table.
    
    Optionally filter rows where search_column LIKE '%search%'.
    """
    safe = _validate_table(table_name)
    limit = min(max(1, limit), 100)
    offset = max(0, offset)

    where_clause = ""
    params: list = []

    if search and search_column:
        # Validate column name exists in the table
        cols = get_table_columns(safe)
        col_names = {c["name"] for c in cols}
        if search_column in col_names:
            where_clause = f"WHERE [{search_column}] LIKE ?"
            params.append(f"%{search}%")

    sql = f"SELECT * FROM [{safe}] {where_clause} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection(readonly=True) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def get_filtered_row_count(
    table_name: str, search: str = "", search_column: str = ""
) -> int:
    """Return row count after applying optional search filter."""
    safe = _validate_table(table_name)

    where_clause = ""
    params: list = []

    if search and search_column:
        cols = get_table_columns(safe)
        col_names = {c["name"] for c in cols}
        if search_column in col_names:
            where_clause = f"WHERE [{search_column}] LIKE ?"
            params.append(f"%{search}%")

    sql = f"SELECT COUNT(*) FROM [{safe}] {where_clause}"
    with get_connection(readonly=True) as conn:
        cursor = conn.execute(sql, params)
        return cursor.fetchone()[0]


def db_exists() -> bool:
    """Check if the DWH database file exists."""
    return os.path.exists(DB_PATH)
