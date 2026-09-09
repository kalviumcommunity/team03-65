"""SQL Business Queries & Mathematical Parity Engine (Senior Designer Architecture).

Designed to Snowflake / Databricks governance standards:
- Verified mathematical consistency between Python and SQLite relational queries
- High-contrast SQL query syntax explorer
- Clean relational result dataframes
"""

import streamlit as st
import pandas as pd
import sqlite3
from typing import Dict, Any

from analysis.sql_analytics import (
    get_db_connection,
    load_data_to_sqlite,
    query_content_highest_retention,
    query_segment_summaries,
    query_funnel_steps,
    verify_python_sql_consistency
)
from src.app.components.html_utils import clean_html

def render_sql_audit_workbench(df: pd.DataFrame) -> None:
    """Render the senior relational SQL analytics workbench."""
    st.markdown("### Relational SQL Engine & Mathematical Parity Audit")
    st.caption("Validates analytical consistency across Python/Pandas and SQLite relational queries under identical business rules.")

    if df.empty:
        st.info("No viewer data available to execute SQL queries.")
        return

    # Run consistency check
    with st.spinner("Executing mathematical parity verification..."):
        parity_report = verify_python_sql_consistency(df)

    is_consistent = parity_report.get("consistent", False)

    # Clean Parity Status Line
    if is_consistent:
        st.markdown(
            clean_html("""
            <div style="display: flex; align-items: center; justify-content: space-between; background: #ffffff; border: 1px solid #e4e4e7; border-radius: 6px; padding: 10px 16px; margin-bottom: 18px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="color: #16a34a; font-size: 10px;">●</span>
                    <span style="font-size: 13px; font-weight: 600; color: #09090b;">Mathematical Parity Certified (0.000 Discrepancy)</span>
                    <span style="color: #a1a1aa;">—</span>
                    <span style="font-size: 12px; color: #52525b;">Python Pandas aggregations and SQLite relational queries yield identical metrics.</span>
                </div>
                <span style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: #15803d; background: #f0fdf4; padding: 2px 8px; border-radius: 4px;">Audit Verified</span>
            </div>
            """),
            unsafe_allow_html=True
        )
    else:
        st.warning("⚠️ Parity discrepancies observed between Python and SQL implementations.")
        st.json(parity_report)

    # Connect to SQLite for live queries
    conn = get_db_connection()
    load_data_to_sqlite(df, conn)

    tab_q1, tab_q2, tab_q3 = st.tabs([
        "Query 1: Content Retention",
        "Query 2: Segment CTE",
        "Query 3: Funnel Steps"
    ])

    with tab_q1:
        st.markdown("#### Content Retention Grouped Aggregation")
        st.caption("Aggregates distinct viewers, completion rate, duration, pauses, and retention rate grouped by title (user-level outcomes).")

        sql_code_1 = """SELECT
    content_id,
    COUNT(DISTINCT user_id) AS viewer_count,
    ROUND(AVG(completion_rate), 2) AS avg_completion_rate,
    ROUND(AVG(watch_duration), 2) AS avg_watch_duration,
    ROUND(AVG(pause_count), 2) AS avg_pause_count,
    ROUND(AVG(sessions_per_week), 2) AS avg_sessions_per_week,
    ROUND(AVG(CAST(retained AS REAL)), 4) AS retention_rate
FROM viewing_records
GROUP BY content_id
ORDER BY retention_rate DESC, viewer_count DESC;"""

        with st.expander("View SQL Definition", expanded=False):
            st.code(sql_code_1, language="sql")

        res_df_1 = query_content_highest_retention(conn)
        st.dataframe(res_df_1, width="stretch", hide_index=True)

    with tab_q2:
        st.markdown("#### Viewer Segment Classification CTE")
        st.caption("Classifies viewers into behavioral tiers using SQL CASE logic and computes group statistics.")

        sql_code_2 = """WITH classified_viewers AS (
    SELECT
        user_id,
        AVG(completion_rate) AS completion_rate,
        AVG(watch_duration) AS watch_duration,
        AVG(pause_count) AS pause_count,
        MIN(sessions_per_week) AS sessions_per_week,
        MAX(retained) AS retained,
        CASE
            WHEN AVG(completion_rate) >= 80.0 AND MIN(sessions_per_week) >= 5 THEN 'Highly Engaged'
            WHEN AVG(completion_rate) < 50.0 OR MIN(sessions_per_week) <= 2 THEN 'At Risk / Low Engagement'
            ELSE 'Moderately Engaged'
        END AS segment
    FROM viewing_records
    GROUP BY user_id
),
total_count AS (
    SELECT COUNT(*) AS total FROM classified_viewers
)
SELECT 
    c.segment,
    COUNT(*) AS viewer_count,
    ROUND((CAST(COUNT(*) AS REAL) / (SELECT total FROM total_count)) * 100.0, 2) AS viewer_pct,
    ROUND(AVG(c.completion_rate), 2) AS avg_completion_rate,
    ROUND(AVG(c.watch_duration), 2) AS avg_watch_duration,
    ROUND(AVG(c.pause_count), 2) AS avg_pause_count,
    ROUND(AVG(c.sessions_per_week), 2) AS avg_sessions_per_week,
    ROUND(AVG(CAST(c.retained AS REAL)), 4) AS retention_rate
FROM classified_viewers c
GROUP BY c.segment;"""

        with st.expander("View SQL Definition", expanded=False):
            st.code(sql_code_2, language="sql")

        res_df_2 = query_segment_summaries(conn)
        st.dataframe(res_df_2, width="stretch", hide_index=True)

    with tab_q3:
        st.markdown("#### Lifecycle Funnel Milestone Conversion")
        st.caption("Calculates milestone stage counts and conversion percentages using SQL UNION ALL.")

        sql_code_3 = """WITH per_user AS (
    SELECT
        user_id,
        MAX(completion_rate) AS completion_rate,
        MAX(CASE WHEN finished = 1 THEN 1 ELSE 0 END) AS finished,
        MAX(retained) AS retained
    FROM viewing_records
    GROUP BY user_id
),
stage_counts AS (
    SELECT
        COUNT(*) AS total_records,
        SUM(CASE WHEN completion_rate > 0 THEN 1 ELSE 0 END) AS started_count,
        SUM(CASE WHEN completion_rate >= 25.0 THEN 1 ELSE 0 END) AS watched_25_count,
        SUM(CASE WHEN completion_rate >= 50.0 THEN 1 ELSE 0 END) AS watched_50_count,
        SUM(CASE WHEN completion_rate >= 75.0 THEN 1 ELSE 0 END) AS watched_75_count,
        SUM(CASE WHEN finished = 1 OR completion_rate >= 90.0 THEN 1 ELSE 0 END) AS finished_count,
        SUM(CASE WHEN retained = 1 THEN 1 ELSE 0 END) AS retained_count
    FROM per_user
)
SELECT 'Started' AS stage, started_count AS count, 100.0 AS percentage_of_total FROM stage_counts
UNION ALL
SELECT '25% watched', watched_25_count, ROUND((CAST(watched_25_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
UNION ALL
SELECT '50% watched', watched_50_count, ROUND((CAST(watched_50_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
UNION ALL
SELECT '75% watched', watched_75_count, ROUND((CAST(watched_75_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
UNION ALL
SELECT 'Finished', finished_count, ROUND((CAST(finished_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
UNION ALL
SELECT 'Retained', retained_count, ROUND((CAST(retained_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts;"""

        with st.expander("View SQL Definition", expanded=False):
            st.code(sql_code_3, language="sql")

        res_df_3 = query_funnel_steps(conn)
        st.dataframe(res_df_3, width="stretch", hide_index=True)

    conn.close()
