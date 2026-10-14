"""
dashboard/pages/etl_logs.py — ETL Logs and Data Quality page.
Shows execution logs, cleansing metrics, and data quality indicators.
"""

import streamlit as st
import pandas as pd
from dashboard import db
from dashboard.scheduler_engine import get_run_history


def render():
    st.title("📝 ETL Logs & Data Quality")

    if not db.db_exists():
        st.error("⚠️ Database not found. Run the ETL pipeline first.")
        return

    # ── Tab layout ───────────────────────────────────────────
    tab_logs, tab_quality, tab_row_audit = st.tabs([
        "📜 Execution Logs",
        "🔍 Data Quality Checks",
        "📊 Row Count Audit",
    ])

    # ────────────────────────────────────────────────────────
    # TAB 1: Execution Logs
    # ────────────────────────────────────────────────────────
    with tab_logs:
        st.subheader("Recent ETL Executions")

        history = get_run_history(limit=50)

        if not history:
            st.info(
                "No ETL execution logs found. "
                "Use the **ETL Scheduler** page to run the pipeline."
            )
        else:
            for run in history:
                status_emoji = {
                    "success": "✅",
                    "error": "❌",
                    "running": "🔄",
                    "pending": "⏳",
                }.get(run["status"], "❓")

                header = (
                    f"{status_emoji} **{run['run_id']}** — "
                    f"{run['trigger'].capitalize()} | "
                    f"{run['status'].upper()} | "
                    f"{run.get('duration_seconds', 0):.1f}s"
                )

                with st.expander(header, expanded=(run == history[0])):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f"**Started:** {run.get('started_at', '—')[:19]}")
                    with col2:
                        st.markdown(f"**Finished:** {run.get('finished_at', '—')[:19]}")
                    with col3:
                        st.markdown(f"**Duration:** {run.get('duration_seconds', 0):.1f}s")
                    with col4:
                        st.markdown(f"**Exit Code:** {run.get('return_code', '—')}")

                    if run.get("error_message"):
                        st.error(f"**Error:** {run['error_message']}")

                    if run.get("stdout"):
                        st.markdown("**Pipeline Output:**")
                        st.code(run["stdout"], language="text")

                    if run.get("stderr"):
                        st.markdown("**Stderr:**")
                        st.code(run["stderr"], language="text")

    # ────────────────────────────────────────────────────────
    # TAB 2: Data Quality Checks
    # ────────────────────────────────────────────────────────
    with tab_quality:
        st.subheader("Data Quality Indicators")
        st.markdown(
            "These checks are run **live** against the current state of the DWH database."
        )

        checks = []

        # Check 1: NULL values in key columns
        st.markdown("### 🔑 Key Column Integrity")

        key_null_queries = [
            ("fact_orders", "date_key", "Date key NULLs in fact_orders"),
            ("fact_orders", "customer_key", "Customer key NULLs in fact_orders"),
            ("fact_orders", "product_key", "Product key NULLs in fact_orders"),
            ("fact_orders", "seller_key", "Seller key NULLs in fact_orders"),
            ("fact_reviews", "date_key", "Date key NULLs in fact_reviews"),
            ("fact_reviews", "customer_key", "Customer key NULLs in fact_reviews"),
            ("fact_reviews", "product_key", "Product key NULLs in fact_reviews"),
        ]

        for table, col, desc in key_null_queries:
            null_count = db.query_scalar(
                f"SELECT COUNT(*) FROM [{table}] WHERE [{col}] IS NULL"
            )
            checks.append({
                "Check": desc,
                "Result": f"{null_count:,} NULLs",
                "Status": "✅ Pass" if null_count == 0 else "⚠️ Warning",
            })

        df_key_checks = pd.DataFrame(checks)
        st.dataframe(df_key_checks, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Check 2: Orphan key detection
        st.markdown("### 🔗 Referential Integrity")

        orphan_checks = []

        # fact_orders orphans
        for fk_col, dim_table, dim_col in [
            ("date_key", "dim_date", "date_key"),
            ("customer_key", "dim_customer", "customer_key"),
            ("product_key", "dim_product", "product_key"),
            ("seller_key", "dim_seller", "seller_key"),
        ]:
            orphan_count = db.query_scalar(f"""
                SELECT COUNT(*) FROM fact_orders f
                WHERE f.[{fk_col}] NOT IN (SELECT [{dim_col}] FROM [{dim_table}])
            """)
            orphan_checks.append({
                "Fact Table": "fact_orders",
                "FK Column": fk_col,
                "Referenced Table": dim_table,
                "Orphan Rows": f"{orphan_count:,}",
                "Status": "✅ Pass" if orphan_count == 0 else "❌ Fail",
            })

        # fact_reviews orphans
        for fk_col, dim_table, dim_col in [
            ("date_key", "dim_date", "date_key"),
            ("customer_key", "dim_customer", "customer_key"),
            ("product_key", "dim_product", "product_key"),
        ]:
            orphan_count = db.query_scalar(f"""
                SELECT COUNT(*) FROM fact_reviews r
                WHERE r.[{fk_col}] NOT IN (SELECT [{dim_col}] FROM [{dim_table}])
            """)
            orphan_checks.append({
                "Fact Table": "fact_reviews",
                "FK Column": fk_col,
                "Referenced Table": dim_table,
                "Orphan Rows": f"{orphan_count:,}",
                "Status": "✅ Pass" if orphan_count == 0 else "❌ Fail",
            })

        df_orphans = pd.DataFrame(orphan_checks)
        st.dataframe(df_orphans, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Check 3: Business logic validation
        st.markdown("### 📏 Business Rule Validation")

        biz_checks = []

        # Negative prices
        neg_price = db.query_scalar(
            "SELECT COUNT(*) FROM fact_orders WHERE price <= 0"
        )
        biz_checks.append({
            "Rule": "No negative or zero prices",
            "Violations": f"{neg_price:,}",
            "Status": "✅ Pass" if neg_price == 0 else "❌ Fail",
        })

        # Negative freight
        neg_freight = db.query_scalar(
            "SELECT COUNT(*) FROM fact_orders WHERE freight_value < 0"
        )
        biz_checks.append({
            "Rule": "No negative freight values",
            "Violations": f"{neg_freight:,}",
            "Status": "✅ Pass" if neg_freight == 0 else "❌ Fail",
        })

        # Review score range
        bad_scores = db.query_scalar(
            "SELECT COUNT(*) FROM fact_reviews WHERE review_score < 1 OR review_score > 5"
        )
        biz_checks.append({
            "Rule": "Review scores between 1-5",
            "Violations": f"{bad_scores:,}",
            "Status": "✅ Pass" if bad_scores == 0 else "❌ Fail",
        })

        # Negative delivery days
        neg_delivery = db.query_scalar(
            "SELECT COUNT(*) FROM fact_orders WHERE delivery_days < 0"
        )
        biz_checks.append({
            "Rule": "No negative delivery days",
            "Violations": f"{neg_delivery:,}",
            "Status": "✅ Pass" if neg_delivery == 0 else "⚠️ Warning",
        })

        # total_value = price + freight_value (tolerance check)
        total_mismatch = db.query_scalar("""
            SELECT COUNT(*) FROM fact_orders 
            WHERE ABS(total_value - (price + freight_value)) > 0.01
        """)
        biz_checks.append({
            "Rule": "total_value = price + freight_value",
            "Violations": f"{total_mismatch:,}",
            "Status": "✅ Pass" if total_mismatch == 0 else "⚠️ Warning",
        })

        df_biz = pd.DataFrame(biz_checks)
        st.dataframe(df_biz, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Check 4: Duplicate detection
        st.markdown("### 🔄 Duplicate Detection")

        dup_checks = []

        dup_orders = db.query_scalar("""
            SELECT COUNT(*) FROM (
                SELECT order_id, order_item_id, COUNT(*) AS cnt
                FROM fact_orders
                GROUP BY order_id, order_item_id
                HAVING cnt > 1
            )
        """)
        dup_checks.append({
            "Table": "fact_orders",
            "Duplicate Key": "order_id + order_item_id",
            "Duplicates": f"{dup_orders:,}",
            "Status": "✅ Pass" if dup_orders == 0 else "⚠️ Warning",
        })

        dup_reviews = db.query_scalar("""
            SELECT COUNT(*) FROM (
                SELECT review_id, COUNT(*) AS cnt
                FROM fact_reviews
                GROUP BY review_id
                HAVING cnt > 1
            )
        """)
        dup_checks.append({
            "Table": "fact_reviews",
            "Duplicate Key": "review_id",
            "Duplicates": f"{dup_reviews:,}",
            "Status": "✅ Pass" if dup_reviews == 0 else "⚠️ Warning",
        })

        df_dups = pd.DataFrame(dup_checks)
        st.dataframe(df_dups, use_container_width=True, hide_index=True)

    # ────────────────────────────────────────────────────────
    # TAB 3: Row Count Audit
    # ────────────────────────────────────────────────────────
    with tab_row_audit:
        st.subheader("📊 Row Count Audit")
        st.markdown(
            "Current row counts for all DWH tables. Compare against expected "
            "values from the last ETL run output."
        )

        audit_data = []
        for table_name in sorted(db.ALLOWED_TABLES):
            row_count = db.get_table_row_count(table_name)
            col_count = len(db.get_table_columns(table_name))
            role = "Fact" if table_name in db.FACT_TABLES else "Dimension"
            audit_data.append({
                "Table": table_name,
                "Role": role,
                "Row Count": f"{row_count:,}",
                "Columns": col_count,
            })

        df_audit = pd.DataFrame(audit_data)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Historical note
        st.info(
            "📌 **Note:** Historical cleansing metrics (e.g., NULLs handled, duplicates removed) "
            "are available in the ETL execution logs above. The existing ETL scripts print "
            "detailed cleansing statistics to stdout during each run. These are captured and "
            "stored in the `etl_log` table for future reference.\n\n"
            "Pre-existing ETL runs (before this dashboard was added) do not have log entries. "
            "Run the ETL pipeline via the Scheduler page to generate tracked execution logs."
        )
