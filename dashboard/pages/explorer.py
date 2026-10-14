"""
dashboard/pages/explorer.py — Fact & Dimension Table Explorer page.
Browse, filter, search, paginate, and download DWH table data.
"""

import streamlit as st
import pandas as pd
from dashboard import db


def render():
    st.title("🗄️ Fact & Dimension Explorer")

    if not db.db_exists():
        st.error("⚠️ Database not found. Run the ETL pipeline first.")
        return

    # ── Table selector ───────────────────────────────────────
    col_sel, col_info = st.columns([1, 2])

    with col_sel:
        st.markdown("### Select Table")

        # Group tables by role
        st.markdown("**Fact Tables**")
        fact_list = sorted(db.FACT_TABLES)
        st.markdown("**Dimension Tables**")
        dim_list = sorted(db.DIMENSION_TABLES)

        all_tables = fact_list + dim_list
        table_labels = {t: f"{'📊 ' if t in db.FACT_TABLES else '📐 '}{t}" for t in all_tables}

        selected_table = st.selectbox(
            "Table",
            options=all_tables,
            format_func=lambda t: table_labels.get(t, t),
            label_visibility="collapsed",
        )

    with col_info:
        st.markdown("### Table Information")
        role = "**Fact Table**" if selected_table in db.FACT_TABLES else "**Dimension Table**"
        row_count = db.get_table_row_count(selected_table)
        desc = db.TABLE_DESCRIPTIONS.get(selected_table, "No description available.")

        st.markdown(f"**Role:** {role}")
        st.markdown(f"**Total Rows:** {row_count:,}")
        st.markdown(f"**Description:** {desc}")

    st.markdown("---")

    # ── Schema info ───────────────────────────────────────────
    st.subheader("📋 Column Schema")

    cols = db.get_table_columns(selected_table)
    fks = db.get_table_foreign_keys(selected_table)
    fk_map = {fk["from"]: f"{fk['table']}({fk['to']})" for fk in fks}

    schema_data = []
    for c in cols:
        constraints = []
        if c["pk"]:
            constraints.append("🔑 PRIMARY KEY")
        if c["notnull"]:
            constraints.append("NOT NULL")
        if c["name"] in fk_map:
            constraints.append(f"🔗 FK → {fk_map[c['name']]}")
        if c["default"] is not None:
            constraints.append(f"DEFAULT {c['default']}")

        schema_data.append({
            "Column": c["name"],
            "Type": c["type"],
            "Constraints": ", ".join(constraints) if constraints else "—",
        })

    df_schema = pd.DataFrame(schema_data)
    st.dataframe(df_schema, use_container_width=True, hide_index=True)

    if fks:
        st.markdown("**Foreign Key Relationships:**")
        for fk in fks:
            st.markdown(
                f"- `{fk['from']}` → `{fk['table']}`(`{fk['to']}`) "
                f"*(enforced by SQLite FK constraint)*"
            )

    st.markdown("---")

    # ── Search & filter ───────────────────────────────────────
    st.subheader("🔍 Data Preview")

    col_f1, col_f2, col_f3 = st.columns([1, 2, 1])

    with col_f1:
        page_size = st.selectbox(
            "Rows per page",
            options=[10, 25, 50, 100],
            index=1,
        )

    col_names = [c["name"] for c in cols]

    with col_f2:
        search_col = st.selectbox(
            "Search column",
            options=[""] + col_names,
            format_func=lambda x: "— select column —" if x == "" else x,
        )

    with col_f3:
        search_term = st.text_input("Search term", value="", placeholder="Type to filter...")

    # Filtered row count
    effective_search = search_term if search_col else ""
    effective_col = search_col if search_term else ""
    filtered_count = db.get_filtered_row_count(
        selected_table, effective_search, effective_col
    )

    total_pages = max(1, (filtered_count + page_size - 1) // page_size)

    col_page, col_nav = st.columns([1, 2])

    with col_page:
        current_page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
        )

    with col_nav:
        st.markdown(
            f"**Showing page {current_page} of {total_pages}** "
            f"({filtered_count:,} matching rows)"
        )

    offset = (current_page - 1) * page_size

    df_preview = db.get_table_preview(
        selected_table,
        limit=page_size,
        offset=offset,
        search=effective_search,
        search_column=effective_col,
    )

    if not df_preview.empty:
        st.dataframe(df_preview, use_container_width=True, hide_index=True)
    else:
        st.info("No records match the current filter.")

    # ── Download option ───────────────────────────────────────
    st.markdown("---")
    with st.expander("📥 Download Preview Data"):
        st.markdown(
            "Download the currently displayed preview (filtered & paginated) as CSV."
        )
        if not df_preview.empty:
            csv = df_preview.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name=f"{selected_table}_preview.csv",
                mime="text/csv",
            )
        else:
            st.info("No data to download.")
