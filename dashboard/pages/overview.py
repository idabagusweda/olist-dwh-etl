"""
dashboard/pages/overview.py — Executive Summary / KPI Overview page.
"""

import streamlit as st
from dashboard import db


def render():
    st.title("📋 Executive Overview")

    if not db.db_exists():
        st.error(
            "⚠️ Database not found. Run the ETL pipeline first:\n\n"
            "```bash\npython scripts/06_run_etl_pipeline.py\n```"
        )
        return

    st.markdown("High-level KPIs from the Olist Data Warehouse.")

    # ── Row 1: Core counts ───────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_orders = db.query_scalar(
            "SELECT COUNT(DISTINCT order_id) FROM fact_orders"
        )
        st.metric("Total Orders", f"{total_orders:,}")

    with col2:
        total_reviews = db.query_scalar("SELECT COUNT(*) FROM fact_reviews")
        st.metric("Total Reviews", f"{total_reviews:,}")

    with col3:
        total_customers = db.query_scalar("SELECT COUNT(*) FROM dim_customer")
        st.metric("Total Customers", f"{total_customers:,}")

    with col4:
        total_products = db.query_scalar("SELECT COUNT(*) FROM dim_product")
        st.metric("Total Products", f"{total_products:,}")

    with col5:
        total_sellers = db.query_scalar("SELECT COUNT(*) FROM dim_seller")
        st.metric("Total Sellers", f"{total_sellers:,}")

    st.markdown("---")

    # ── Row 2: Revenue & delivery metrics ─────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_revenue = db.query_scalar(
            "SELECT ROUND(SUM(total_value), 2) FROM fact_orders"
        )
        if total_revenue:
            st.metric("Total Revenue (R$)", f"R$ {total_revenue:,.2f}")
        else:
            st.metric("Total Revenue (R$)", "N/A")

    with col2:
        avg_order_value = db.query_scalar("""
            SELECT ROUND(AVG(order_total), 2)
            FROM (
                SELECT order_id, SUM(total_value) AS order_total
                FROM fact_orders
                GROUP BY order_id
            )
        """)
        if avg_order_value:
            st.metric("Avg Order Value (R$)", f"R$ {avg_order_value:,.2f}")
        else:
            st.metric("Avg Order Value (R$)", "N/A")

    with col3:
        avg_delivery = db.query_scalar(
            "SELECT ROUND(AVG(delivery_days), 1) FROM fact_orders WHERE delivery_days IS NOT NULL"
        )
        if avg_delivery:
            st.metric("Avg Delivery Days", f"{avg_delivery:.1f}")
        else:
            st.metric("Avg Delivery Days", "N/A")

    with col4:
        avg_score = db.query_scalar(
            "SELECT ROUND(AVG(review_score), 2) FROM fact_reviews"
        )
        if avg_score:
            st.metric("Avg Review Score", f"⭐ {avg_score:.2f}")
        else:
            st.metric("Avg Review Score", "N/A")

    st.markdown("---")

    # ── Row 3: Table stats ────────────────────────────────────
    st.subheader("📊 Data Warehouse Table Summary")

    table_data = []
    for tname in sorted(db.ALLOWED_TABLES):
        row_count = db.get_table_row_count(tname)
        cols = db.get_table_columns(tname)
        role = "Dimension" if tname in db.DIMENSION_TABLES else "Fact"
        table_data.append({
            "Table": tname,
            "Role": role,
            "Rows": f"{row_count:,}",
            "Columns": len(cols),
            "Description": db.TABLE_DESCRIPTIONS.get(tname, ""),
        })

    import pandas as pd
    df_tables = pd.DataFrame(table_data)
    st.dataframe(df_tables, use_container_width=True, hide_index=True)

    # ── Row 4: Order status breakdown ─────────────────────────
    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📦 Orders by Status")
        df_status = db.query_df("""
            SELECT order_status AS "Status",
                   COUNT(DISTINCT order_id) AS "Orders"
            FROM fact_orders
            GROUP BY order_status
            ORDER BY "Orders" DESC
        """)
        if not df_status.empty:
            st.dataframe(df_status, use_container_width=True, hide_index=True)
        else:
            st.info("No order data available.")

    with col_right:
        st.subheader("⭐ Review Score Distribution")
        df_scores = db.query_df("""
            SELECT review_score AS "Score",
                   COUNT(*) AS "Reviews",
                   ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fact_reviews), 1) AS "Percentage (%)"
            FROM fact_reviews
            GROUP BY review_score
            ORDER BY review_score
        """)
        if not df_scores.empty:
            st.dataframe(df_scores, use_container_width=True, hide_index=True)
        else:
            st.info("No review data available.")

    # ── Row 5: Date range info ────────────────────────────────
    st.markdown("---")
    st.subheader("📅 Data Coverage")
    col1, col2 = st.columns(2)

    with col1:
        date_range = db.query_df("""
            SELECT MIN(d.full_date) AS "Earliest Order",
                   MAX(d.full_date) AS "Latest Order"
            FROM fact_orders f
            JOIN dim_date d ON f.date_key = d.date_key
        """)
        if not date_range.empty:
            st.dataframe(date_range, use_container_width=True, hide_index=True)

    with col2:
        top_states = db.query_df("""
            SELECT c.state AS "State",
                   COUNT(DISTINCT f.order_id) AS "Orders"
            FROM fact_orders f
            JOIN dim_customer c ON f.customer_key = c.customer_key
            GROUP BY c.state
            ORDER BY "Orders" DESC
            LIMIT 5
        """)
        if not top_states.empty:
            st.markdown("**Top 5 Customer States**")
            st.dataframe(top_states, use_container_width=True, hide_index=True)
