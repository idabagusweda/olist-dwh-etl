"""
app.py — Olist Data Warehouse Dashboard
Main entry point for the Streamlit dashboard.
Launch: streamlit run app.py
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Page config — MUST be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Olist DWH Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Imports (after set_page_config)
# ---------------------------------------------------------------------------
from dashboard import db, styles
from dashboard.pages import (
    overview,
    analytics,
    explorer,
    star_schema,
    scheduler,
    etl_logs,
)

# ---------------------------------------------------------------------------
# Apply custom CSS
# ---------------------------------------------------------------------------
styles.inject_css()

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
PAGES = {
    "📋 Overview": overview,
    "📈 Analytics": analytics,
    "🗄️ Fact & Dimension Explorer": explorer,
    "⭐ Star Schema": star_schema,
    "⏰ ETL Scheduler": scheduler,
    "📝 ETL Logs / Data Quality": etl_logs,
}

with st.sidebar:
    st.markdown("## 📊 Olist DWH")
    st.markdown("---")
    selection = st.radio(
        "Navigation",
        list(PAGES.keys()),
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Olist Data Warehouse Dashboard v1.0")
    st.caption("Database: `data/processed/olist_dwh.db`")

# ---------------------------------------------------------------------------
# Render selected page
# ---------------------------------------------------------------------------
page_module = PAGES[selection]
page_module.render()
