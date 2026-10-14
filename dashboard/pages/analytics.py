"""
dashboard/pages/analytics.py — Interactive analytical charts page.
All data comes from SQL queries against the DWH database, not hardcoded.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from dashboard import db


def render():
    st.title("📈 Analytics Dashboard")

    if not db.db_exists():
        st.error("⚠️ Database not found. Run the ETL pipeline first.")
        return

    # ── Filters ───────────────────────────────────────────────
    st.markdown("### 🔍 Filters")
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        years = db.query_df(
            "SELECT DISTINCT year FROM dim_date WHERE date_key IN (SELECT DISTINCT date_key FROM fact_orders) ORDER BY year"
        )
        available_years = years["year"].tolist() if not years.empty else []
        selected_years = st.multiselect(
            "Year(s)",
            options=available_years,
            default=available_years,
        )

    with filter_col2:
        states = db.query_df("""
            SELECT DISTINCT c.state
            FROM dim_customer c
            WHERE c.customer_key IN (SELECT DISTINCT customer_key FROM fact_orders)
            ORDER BY c.state
        """)
        available_states = states["state"].tolist() if not states.empty else []
        selected_states = st.multiselect(
            "Customer State(s)",
            options=available_states,
            default=[],
            placeholder="All states",
        )

    with filter_col3:
        statuses = db.query_df(
            "SELECT DISTINCT order_status FROM fact_orders ORDER BY order_status"
        )
        available_statuses = statuses["order_status"].tolist() if not statuses.empty else []
        selected_statuses = st.multiselect(
            "Order Status",
            options=available_statuses,
            default=[],
            placeholder="All statuses",
        )

    # Build WHERE clause dynamically
    conditions = []
    params = []

    if selected_years:
        placeholders = ",".join(["?"] * len(selected_years))
        conditions.append(f"d.year IN ({placeholders})")
        params.extend(selected_years)

    if selected_states:
        placeholders = ",".join(["?"] * len(selected_states))
        conditions.append(f"c.state IN ({placeholders})")
        params.extend(selected_states)

    if selected_statuses:
        placeholders = ",".join(["?"] * len(selected_statuses))
        conditions.append(f"f.order_status IN ({placeholders})")
        params.extend(selected_statuses)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Need to know if state filter is applied (requires customer join)
    needs_customer_join = bool(selected_states)

    st.markdown("---")

    # ── Chart 1: Monthly Order Trends ────────────────────────
    st.subheader("📊 Monthly Order Trends")

    customer_join = "JOIN dim_customer c ON f.customer_key = c.customer_key" if needs_customer_join else ""

    df_monthly = db.query_df(f"""
        SELECT d.year || '-' || printf('%02d', d.month) AS month_label,
               d.year, d.month, d.month_name,
               COUNT(DISTINCT f.order_id) AS total_orders,
               ROUND(SUM(f.total_value), 2) AS total_revenue,
               COUNT(*) AS total_items
        FROM fact_orders f
        JOIN dim_date d ON f.date_key = d.date_key
        {customer_join}
        {where}
        GROUP BY d.year, d.month, d.month_name
        ORDER BY d.year, d.month
    """, tuple(params))

    if not df_monthly.empty:
        tab1, tab2 = st.tabs(["Orders", "Revenue"])

        with tab1:
            fig = px.line(
                df_monthly,
                x="month_label",
                y="total_orders",
                title="Orders per Month",
                labels={"month_label": "Month", "total_orders": "Orders"},
                markers=True,
            )
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis_tickangle=-45,
                height=400,
            )
            fig.update_traces(
                line=dict(color="#818cf8", width=2.5),
                marker=dict(size=6),
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig = px.bar(
                df_monthly,
                x="month_label",
                y="total_revenue",
                title="Revenue per Month (R$)",
                labels={"month_label": "Month", "total_revenue": "Revenue (R$)"},
            )
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis_tickangle=-45,
                height=400,
            )
            fig.update_traces(marker_color="#6366f1")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

    st.markdown("---")

    # ── Chart 2 & 3: Status + Review Distribution ────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📦 Orders by Status")

        df_status = db.query_df(f"""
            SELECT f.order_status AS status,
                   COUNT(DISTINCT f.order_id) AS orders
            FROM fact_orders f
            JOIN dim_date d ON f.date_key = d.date_key
            {customer_join}
            {where}
            GROUP BY f.order_status
            ORDER BY orders DESC
        """, tuple(params))

        if not df_status.empty:
            fig = px.pie(
                df_status,
                values="orders",
                names="status",
                title="Order Status Distribution",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.4,
            )
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=380,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available.")

    with col_right:
        st.subheader("⭐ Review Score Distribution")

        # Review scores — filtered by year only (reviews don't have state directly in a simple way)
        review_conditions = []
        review_params = []
        if selected_years:
            placeholders = ",".join(["?"] * len(selected_years))
            review_conditions.append(f"d.year IN ({placeholders})")
            review_params.extend(selected_years)

        review_where = "WHERE " + " AND ".join(review_conditions) if review_conditions else ""

        df_scores = db.query_df(f"""
            SELECT r.review_score AS score,
                   COUNT(*) AS reviews
            FROM fact_reviews r
            JOIN dim_date d ON r.date_key = d.date_key
            {review_where}
            GROUP BY r.review_score
            ORDER BY r.review_score
        """, tuple(review_params))

        if not df_scores.empty:
            colors = ["#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e"]
            fig = px.bar(
                df_scores,
                x="score",
                y="reviews",
                title="Review Score Distribution",
                labels={"score": "Score", "reviews": "Reviews"},
                color="score",
                color_discrete_sequence=colors,
            )
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                height=380,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No review data available.")

    st.markdown("---")

    # ── Chart 4: Top 10 Product Categories ───────────────────
    st.subheader("🏷️ Top 10 Product Categories by Revenue")

    product_customer_join = "JOIN dim_customer c ON f.customer_key = c.customer_key" if needs_customer_join else ""

    df_categories = db.query_df(f"""
        SELECT COALESCE(p.category_name_english, p.category_name, 'unknown') AS category,
               COUNT(DISTINCT f.order_id) AS orders,
               ROUND(SUM(f.price), 2) AS revenue,
               ROUND(AVG(f.price), 2) AS avg_price
        FROM fact_orders f
        JOIN dim_product p ON f.product_key = p.product_key
        JOIN dim_date d ON f.date_key = d.date_key
        {product_customer_join}
        {where}
        GROUP BY category
        ORDER BY revenue DESC
        LIMIT 10
    """, tuple(params))

    if not df_categories.empty:
        fig = px.bar(
            df_categories,
            x="revenue",
            y="category",
            orientation="h",
            title="Top 10 Categories by Revenue (R$)",
            labels={"revenue": "Revenue (R$)", "category": "Category"},
            text="revenue",
            color="revenue",
            color_continuous_scale="Viridis",
        )
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
            height=450,
        )
        fig.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available.")

    st.markdown("---")

    # ── Chart 5: Geographic Distribution ──────────────────────
    col_geo1, col_geo2 = st.columns(2)

    with col_geo1:
        st.subheader("🌍 Orders by Customer State")

        df_geo = db.query_df(f"""
            SELECT c.state,
                   COUNT(DISTINCT f.order_id) AS orders,
                   ROUND(SUM(f.total_value), 2) AS revenue
            FROM fact_orders f
            JOIN dim_customer c ON f.customer_key = c.customer_key
            JOIN dim_date d ON f.date_key = d.date_key
            {"" if not selected_statuses and not selected_years else ""}
            {where.replace("c.state IN (" + ",".join(["?"] * len(selected_states)) + ")", "1=1") if selected_states else where}
            GROUP BY c.state
            ORDER BY orders DESC
            LIMIT 15
        """, tuple([p for i, p in enumerate(params) if p not in selected_states] if selected_states else params))

        if not df_geo.empty:
            fig = px.bar(
                df_geo,
                x="state",
                y="orders",
                title="Top 15 States by Order Volume",
                labels={"state": "State", "orders": "Orders"},
                color="orders",
                color_continuous_scale="Blues",
            )
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                coloraxis_showscale=False,
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available.")

    with col_geo2:
        st.subheader("🚚 Avg Delivery Days by State")

        df_delivery = db.query_df("""
            SELECT c.state,
                   COUNT(DISTINCT f.order_id) AS orders,
                   ROUND(AVG(f.delivery_days), 1) AS avg_delivery
            FROM fact_orders f
            JOIN dim_customer c ON f.customer_key = c.customer_key
            WHERE f.delivery_days IS NOT NULL
            GROUP BY c.state
            HAVING orders >= 10
            ORDER BY avg_delivery DESC
            LIMIT 15
        """)

        if not df_delivery.empty:
            fig = px.bar(
                df_delivery,
                x="state",
                y="avg_delivery",
                title="Average Delivery Days by State (Top 15 Slowest)",
                labels={"state": "State", "avg_delivery": "Avg Days"},
                color="avg_delivery",
                color_continuous_scale="Reds",
            )
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                coloraxis_showscale=False,
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No delivery data available.")

    st.markdown("---")

    # ── Chart 6: Top Sellers ─────────────────────────────────
    st.subheader("🏪 Top 10 Sellers by Revenue")

    df_sellers = db.query_df(f"""
        SELECT s.seller_key,
               s.city || ', ' || UPPER(s.state) AS seller_location,
               COUNT(DISTINCT f.order_id) AS orders,
               ROUND(SUM(f.price), 2) AS revenue
        FROM fact_orders f
        JOIN dim_seller s ON f.seller_key = s.seller_key
        JOIN dim_date d ON f.date_key = d.date_key
        {product_customer_join}
        {where}
        GROUP BY s.seller_key, s.city, s.state
        ORDER BY revenue DESC
        LIMIT 10
    """, tuple(params))

    if not df_sellers.empty:
        fig = px.bar(
            df_sellers,
            x="revenue",
            y="seller_location",
            orientation="h",
            title="Top 10 Sellers by Revenue (R$)",
            labels={"revenue": "Revenue (R$)", "seller_location": "Seller Location"},
            text="revenue",
            color="revenue",
            color_continuous_scale="Teal",
        )
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
            height=450,
        )
        fig.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No seller data available.")

    st.markdown("---")

    # ── Chart 7: Average Review Score Over Time ───────────────
    st.subheader("⭐ Average Review Score Over Time")

    df_review_trend = db.query_df(f"""
        SELECT d.year || '-' || printf('%02d', d.month) AS month_label,
               d.year, d.month,
               ROUND(AVG(r.review_score), 2) AS avg_score,
               COUNT(*) AS total_reviews
        FROM fact_reviews r
        JOIN dim_date d ON r.date_key = d.date_key
        {review_where}
        GROUP BY d.year, d.month
        HAVING total_reviews >= 10
        ORDER BY d.year, d.month
    """, tuple(review_params))

    if not df_review_trend.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_review_trend["month_label"],
            y=df_review_trend["avg_score"],
            mode="lines+markers",
            name="Avg Score",
            line=dict(color="#f59e0b", width=2.5),
            marker=dict(size=6),
        ))
        fig.update_layout(
            title="Monthly Average Review Score",
            xaxis_title="Month",
            yaxis_title="Avg Score",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(range=[1, 5]),
            xaxis_tickangle=-45,
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No review trend data available.")
