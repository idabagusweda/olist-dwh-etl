"""
dashboard/pages/star_schema.py — Star Schema visual diagram page.
Shows the DWH star schema relationships using a Mermaid-style diagram
rendered via Streamlit's graphviz or manual HTML.
"""

import streamlit as st
from dashboard import db


def render():
    st.title("⭐ Star Schema Diagram")

    if not db.db_exists():
        st.error("⚠️ Database not found. Run the ETL pipeline first.")
        return

    st.markdown(
        "The Olist Data Warehouse uses a **Star Schema** with "
        "**2 fact tables** and **4 dimension tables**. "
        "All relationships shown below are **enforced by SQLite foreign key constraints** "
        "defined in [`01_create_dwh_schema.sql`](sql/01_create_dwh_schema.sql)."
    )

    st.markdown("---")

    # ── Mermaid diagram ──────────────────────────────────────
    st.subheader("📊 Entity Relationship Diagram")

    mermaid_code = """
    erDiagram
        dim_date {
            INTEGER date_key PK "YYYYMMDD"
            DATE full_date
            INTEGER year
            INTEGER quarter
            INTEGER month
            VARCHAR month_name
            INTEGER day
            VARCHAR day_of_week
            BOOLEAN is_weekend
        }

        dim_customer {
            INTEGER customer_key PK "Auto-increment"
            VARCHAR customer_id UK
            VARCHAR customer_unique_id
            VARCHAR zip_code_prefix
            VARCHAR city
            VARCHAR state
        }

        dim_product {
            INTEGER product_key PK "Auto-increment"
            VARCHAR product_id UK
            VARCHAR category_name
            VARCHAR category_name_english
            REAL weight_g
            REAL length_cm
            REAL height_cm
            REAL width_cm
        }

        dim_seller {
            INTEGER seller_key PK "Auto-increment"
            VARCHAR seller_id UK
            VARCHAR zip_code_prefix
            VARCHAR city
            VARCHAR state
        }

        fact_orders {
            INTEGER order_item_key PK "Auto-increment"
            VARCHAR order_id
            INTEGER order_item_id
            INTEGER date_key FK
            INTEGER customer_key FK
            INTEGER product_key FK
            INTEGER seller_key FK
            REAL price
            REAL freight_value
            REAL total_value
            INTEGER delivery_days
            VARCHAR order_status
        }

        fact_reviews {
            INTEGER review_key PK "Auto-increment"
            VARCHAR review_id
            VARCHAR order_id
            INTEGER date_key FK
            INTEGER customer_key FK
            INTEGER product_key FK
            INTEGER review_score
            BOOLEAN has_comment
        }

        dim_date ||--o{ fact_orders : "date_key"
        dim_customer ||--o{ fact_orders : "customer_key"
        dim_product ||--o{ fact_orders : "product_key"
        dim_seller ||--o{ fact_orders : "seller_key"

        dim_date ||--o{ fact_reviews : "date_key"
        dim_customer ||--o{ fact_reviews : "customer_key"
        dim_product ||--o{ fact_reviews : "product_key"
    """

    st.markdown(
        f"""```mermaid
{mermaid_code}
```""",
    )

    st.markdown("---")

    # ── Textual description with cards ────────────────────────
    st.subheader("📐 Table Details")

    # Fact tables
    st.markdown("### Fact Tables")

    for table_name in sorted(db.FACT_TABLES):
        row_count = db.get_table_row_count(table_name)
        cols = db.get_table_columns(table_name)
        fks = db.get_table_foreign_keys(table_name)
        desc = db.TABLE_DESCRIPTIONS.get(table_name, "")

        with st.expander(f"📊 **{table_name}** — {row_count:,} rows", expanded=False):
            st.markdown(f"*{desc}*")

            # Measures vs. dimensions
            fk_cols = {fk["from"] for fk in fks}
            pk_cols = {c["name"] for c in cols if c["pk"]}

            dim_cols = []
            measure_cols = []
            key_cols = []

            for c in cols:
                if c["name"] in pk_cols:
                    key_cols.append(c)
                elif c["name"] in fk_cols:
                    dim_cols.append(c)
                else:
                    measure_cols.append(c)

            if key_cols:
                st.markdown("**Primary Key:**")
                for c in key_cols:
                    st.markdown(f"- `{c['name']}` ({c['type']}) — Auto-increment surrogate key")

            if dim_cols:
                st.markdown("**Dimension Keys (FK):**")
                for c in dim_cols:
                    fk_target = ""
                    for fk in fks:
                        if fk["from"] == c["name"]:
                            fk_target = f" → `{fk['table']}`.`{fk['to']}`"
                    st.markdown(f"- `{c['name']}` ({c['type']}){fk_target}")

            if measure_cols:
                st.markdown("**Measures & Attributes:**")
                for c in measure_cols:
                    st.markdown(f"- `{c['name']}` ({c['type']})")

    # Dimension tables
    st.markdown("### Dimension Tables")

    for table_name in sorted(db.DIMENSION_TABLES):
        row_count = db.get_table_row_count(table_name)
        cols = db.get_table_columns(table_name)
        desc = db.TABLE_DESCRIPTIONS.get(table_name, "")

        with st.expander(f"📐 **{table_name}** — {row_count:,} rows", expanded=False):
            st.markdown(f"*{desc}*")

            for c in cols:
                pk_tag = " 🔑 PK" if c["pk"] else ""
                nn_tag = " NOT NULL" if c["notnull"] else ""
                st.markdown(f"- `{c['name']}` ({c['type']}){pk_tag}{nn_tag}")

    st.markdown("---")

    # ── Relationship summary table ────────────────────────────
    st.subheader("🔗 Relationship Summary")

    relationships = []
    for table_name in sorted(db.FACT_TABLES):
        fks = db.get_table_foreign_keys(table_name)
        for fk in fks:
            relationships.append({
                "Fact Table": table_name,
                "Foreign Key Column": fk["from"],
                "Referenced Dimension": fk["table"],
                "Referenced Column": fk["to"],
                "Constraint Type": "SQLite FK (enforced)",
            })

    import pandas as pd_mod
    df_rels = pd_mod.DataFrame(relationships)
    st.dataframe(df_rels, use_container_width=True, hide_index=True)
