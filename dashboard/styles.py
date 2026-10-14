"""
dashboard/styles.py — Custom CSS for the Olist DWH Dashboard.
Injects a polished dark-blue theme with glassmorphism cards.
"""

import streamlit as st


def inject_css():
    st.markdown(
        """
        <style>
        /* ── Import Google Font ───────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        /* ── Base ─────────────────────────────────────────────── */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* ── Metric cards ─────────────────────────────────────── */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid rgba(99, 102, 241, 0.25);
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(99, 102, 241, 0.2);
        }
        div[data-testid="stMetric"] label {
            color: #94a3b8 !important;
            font-weight: 500;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #e2e8f0 !important;
            font-weight: 700;
            font-size: 1.6rem;
        }
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
            color: #6ee7b7 !important;
        }

        /* ── Sidebar ──────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
            border-right: 1px solid rgba(99, 102, 241, 0.15);
        }
        section[data-testid="stSidebar"] .stRadio label {
            color: #cbd5e1 !important;
            font-weight: 500;
            padding: 6px 0;
        }

        /* ── Headers ──────────────────────────────────────────── */
        h1 {
            background: linear-gradient(90deg, #818cf8, #6366f1, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
        }
        h2 {
            color: #c7d2fe !important;
            font-weight: 600;
            border-bottom: 2px solid rgba(99, 102, 241, 0.3);
            padding-bottom: 8px;
        }
        h3 {
            color: #a5b4fc !important;
            font-weight: 600;
        }

        /* ── Tabs ─────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 500;
        }

        /* ── Dataframes ───────────────────────────────────────── */
        .stDataFrame {
            border-radius: 8px;
            overflow: hidden;
        }

        /* ── Info/Success/Warning boxes ────────────────────────── */
        .stAlert {
            border-radius: 8px;
        }

        /* ── Buttons ──────────────────────────────────────────── */
        .stButton > button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }

        /* ── Expanders ────────────────────────────────────────── */
        .streamlit-expanderHeader {
            font-weight: 600;
            color: #a5b4fc !important;
        }

        /* ── Custom status badges ─────────────────────────────── */
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.03em;
        }
        .status-idle {
            background: rgba(148, 163, 184, 0.15);
            color: #94a3b8;
            border: 1px solid rgba(148, 163, 184, 0.3);
        }
        .status-running {
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            border: 1px solid rgba(99, 102, 241, 0.3);
            animation: pulse 2s infinite;
        }
        .status-success {
            background: rgba(34, 197, 94, 0.15);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .status-error {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        /* ── Schema diagram card ──────────────────────────────── */
        .schema-card {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 12px;
            padding: 20px;
            margin: 8px 0;
        }
        .schema-card.dim {
            border-left: 4px solid #818cf8;
        }
        .schema-card.fact {
            border-left: 4px solid #f59e0b;
        }

        /* ── Log viewer ───────────────────────────────────────── */
        .log-entry {
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 0.82rem;
            padding: 8px 12px;
            border-radius: 6px;
            margin: 4px 0;
            background: rgba(15, 23, 42, 0.6);
            border-left: 3px solid #475569;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
