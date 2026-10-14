"""
dashboard/pages/scheduler.py — ETL Scheduler control page.
"""

import streamlit as st
import threading
from datetime import datetime
from dashboard.scheduler_engine import (
    run_etl_pipeline,
    is_etl_running,
    start_scheduler,
    stop_scheduler,
    get_scheduler_status,
    get_last_successful_run,
    get_run_history,
)


def render():
    st.title("⏰ ETL Scheduler")

    st.markdown(
        "Control the Olist ETL pipeline execution. "
        "The pipeline runs `scripts/06_run_etl_pipeline.py` as a subprocess "
        "to extract, transform, and load data into the DWH."
    )

    st.markdown("---")

    # ── Current Status ─────────────────────────────────────────
    st.subheader("📊 Current Status")

    status = get_scheduler_status()
    etl_running = is_etl_running()

    col1, col2, col3 = st.columns(3)

    with col1:
        if etl_running:
            st.markdown(
                '<span class="status-badge status-running">● ETL Running</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="status-badge status-idle">● ETL Idle</span>',
                unsafe_allow_html=True,
            )

    with col2:
        if status["running"]:
            st.markdown(
                '<span class="status-badge status-success">● Scheduler Active</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="status-badge status-idle">● Scheduler Stopped</span>',
                unsafe_allow_html=True,
            )

    with col3:
        if status["next_run"]:
            try:
                next_dt = datetime.fromisoformat(status["next_run"])
                st.metric("Next Scheduled Run", next_dt.strftime("%Y-%m-%d %H:%M:%S"))
            except (ValueError, TypeError):
                st.metric("Next Scheduled Run", str(status["next_run"]))
        else:
            st.metric("Next Scheduled Run", "—")

    # Last successful run
    last_success = get_last_successful_run()
    if last_success:
        col_ls1, col_ls2, col_ls3 = st.columns(3)
        with col_ls1:
            st.metric("Last Success", last_success.get("finished_at", "—")[:19])
        with col_ls2:
            dur = last_success.get("duration_seconds", 0)
            st.metric("Duration", f"{dur:.1f}s")
        with col_ls3:
            st.metric("Trigger", last_success.get("trigger", "—").capitalize())

    st.markdown("---")

    # ── Manual Execution ──────────────────────────────────────
    st.subheader("🚀 Manual Execution")

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button(
            "▶️ Run ETL Now",
            disabled=etl_running,
            use_container_width=True,
            type="primary",
        ):
            with st.spinner("Running ETL pipeline... This may take a few minutes."):
                result = run_etl_pipeline(trigger="manual")

            if result.status == "success":
                st.success(
                    f"✅ ETL completed successfully in {result.duration_seconds:.1f}s"
                )
                with st.expander("📋 Execution Output", expanded=False):
                    st.code(result.stdout, language="text")
                    if result.stderr:
                        st.warning("Stderr output:")
                        st.code(result.stderr, language="text")
            else:
                st.error(f"❌ ETL failed: {result.error_message}")
                with st.expander("📋 Execution Output", expanded=True):
                    if result.stdout:
                        st.code(result.stdout, language="text")
                    if result.stderr:
                        st.code(result.stderr, language="text")

    with col_btn2:
        if etl_running:
            st.warning("⏳ An ETL execution is currently in progress.")

    st.markdown("---")

    # ── Scheduled Execution ──────────────────────────────────
    st.subheader("📅 Automated Scheduler")

    col_sched1, col_sched2 = st.columns([2, 1])

    with col_sched1:
        interval = st.selectbox(
            "Execution Interval",
            options=[
                "Every 30 minutes",
                "Every 1 hour",
                "Every 6 hours",
                "Every 12 hours",
                "Daily",
                "Weekly",
                "Custom (minutes)",
            ],
            index=4,  # Default: Daily
        )

        custom_min = 60
        if interval == "Custom (minutes)":
            custom_min = st.number_input(
                "Custom interval (minutes)",
                min_value=5,
                max_value=10080,
                value=60,
                step=5,
            )

    with col_sched2:
        st.markdown("####")  # spacing

        if st.button(
            "▶️ Start Scheduler",
            disabled=status["running"],
            use_container_width=True,
        ):
            msg = start_scheduler(interval, custom_min)
            st.success(msg)
            st.rerun()

        if st.button(
            "⏹️ Stop Scheduler",
            disabled=not status["running"],
            use_container_width=True,
        ):
            msg = stop_scheduler()
            st.info(msg)
            st.rerun()

    st.markdown("---")

    # ── Execution History ────────────────────────────────────
    st.subheader("📜 Recent Execution History")

    history = get_run_history(limit=20)

    if history:
        import pandas as pd

        df_hist = pd.DataFrame(history)
        display_cols = [
            "run_id", "trigger", "status", "started_at",
            "finished_at", "duration_seconds", "return_code",
        ]
        available = [c for c in display_cols if c in df_hist.columns]
        df_display = df_hist[available].copy()

        # Color-code status
        def status_icon(s):
            icons = {"success": "✅", "error": "❌", "running": "🔄", "pending": "⏳"}
            return f"{icons.get(s, '❓')} {s}"

        df_display["status"] = df_display["status"].apply(status_icon)
        df_display.columns = [
            "Run ID", "Trigger", "Status", "Started At",
            "Finished At", "Duration (s)", "Exit Code",
        ]

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Expandable log detail for the most recent run
        if history:
            latest = history[0]
            with st.expander(f"📋 Detail: Run {latest['run_id']}"):
                if latest.get("stdout"):
                    st.markdown("**Stdout:**")
                    st.code(latest["stdout"], language="text")
                if latest.get("stderr"):
                    st.markdown("**Stderr:**")
                    st.code(latest["stderr"], language="text")
                if latest.get("error_message"):
                    st.markdown(f"**Error:** {latest['error_message']}")
    else:
        st.info("No ETL executions recorded yet. Run the pipeline to see history.")
