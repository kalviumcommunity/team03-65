"""Day 15 — SQL Business Queries and Python-vs-SQL Validation Layer.

Executes business queries against SQLite database:
1. Content with highest retention
2. Segment summaries
3. Funnel steps / funnel analysis

Provides a verification harness confirming Python and SQL aggregations yield
consistent numerical outcomes under identical business rules.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from analysis.correlation import normalize_dataframe_columns
from analysis.segments import calculate_segment_comparison
from analysis.funnel import calculate_funnel_metrics

REPO_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = REPO_ROOT / "sql"
SCHEMA_PATH = SQL_DIR / "schema.sql"
QUERIES_PATH = SQL_DIR / "business_queries.sql"

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create an SQLite database connection (in-memory if path not provided)."""
    conn = sqlite3.connect(db_path or ":memory:")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn: sqlite3.Connection, schema_sql: Optional[str] = None) -> None:
    """Initialize database tables using the schema file."""
    if schema_sql is None and SCHEMA_PATH.exists():
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    if schema_sql:
        conn.executescript(schema_sql)
        conn.commit()

def load_data_to_sqlite(df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    """Load normalized viewing records DataFrame into SQLite viewing_records table."""
    init_db(conn)
    norm_df = normalize_dataframe_columns(df).copy()

    # Required columns
    col_defaults = {
        "user_id": "U0000",
        "content_id": 0,
        "watch_duration": 0.0,
        "completion_rate": 0.0,
        "pause_count": 0,
        "sessions_per_week": 1.0,
        "retained": 0,
        "finished": 0
    }

    for col, default in col_defaults.items():
        if col not in norm_df.columns:
            norm_df[col] = default

    if "finished" not in norm_df.columns or norm_df["finished"].isna().all():
        norm_df["finished"] = (norm_df["completion_rate"] >= 90.0).astype(int)
    else:
        norm_df["finished"] = norm_df["finished"].astype(int)

    norm_df["retained"] = pd.to_numeric(norm_df["retained"], errors="coerce").fillna(0).astype(int)

    cols_to_insert = ["user_id", "content_id", "watch_duration", "completion_rate", "pause_count", "sessions_per_week", "retained", "finished"]
    insert_df = norm_df[cols_to_insert].copy()

    insert_df.to_sql("viewing_records", conn, if_exists="replace", index=False)
    conn.commit()

def query_content_highest_retention(conn: sqlite3.Connection) -> pd.DataFrame:
    """Query content items ordered by retention rate descending."""
    sql = """
    SELECT 
        content_id,
        COUNT(DISTINCT user_id) AS viewer_count,
        ROUND(AVG(completion_rate), 2) AS avg_completion_rate,
        ROUND(AVG(watch_duration), 2) AS avg_watch_duration,
        ROUND(AVG(pause_count), 2) AS avg_pause_count,
        ROUND(AVG(sessions_per_week), 2) AS avg_sessions_per_week,
        ROUND(AVG(CAST(retained AS REAL)), 4) AS retention_rate
    FROM viewing_records
    GROUP BY content_id
    ORDER BY retention_rate DESC, viewer_count DESC;
    """
    return pd.read_sql_query(sql, conn)

def query_segment_summaries(conn: sqlite3.Connection) -> pd.DataFrame:
    """Query viewer segment summaries using SQL CTE."""
    sql = """
    WITH classified_viewers AS (
        SELECT
            user_id,
            completion_rate,
            watch_duration,
            pause_count,
            sessions_per_week,
            retained,
            CASE
                WHEN completion_rate >= 80.0 AND sessions_per_week >= 5 THEN 'Highly Engaged'
                WHEN completion_rate < 50.0 OR sessions_per_week <= 2 THEN 'At Risk / Low Engagement'
                ELSE 'Moderately Engaged'
            END AS segment
        FROM viewing_records
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
    GROUP BY c.segment
    ORDER BY 
        CASE c.segment
            WHEN 'Highly Engaged' THEN 1
            WHEN 'Moderately Engaged' THEN 2
            ELSE 3
        END;
    """
    return pd.read_sql_query(sql, conn)

def query_funnel_steps(conn: sqlite3.Connection) -> pd.DataFrame:
    """Query funnel steps from SQLite."""
    sql = """
    WITH stage_counts AS (
        SELECT
            COUNT(*) AS total_records,
            SUM(CASE WHEN completion_rate > 0 THEN 1 ELSE 0 END) AS started_count,
            SUM(CASE WHEN completion_rate >= 25.0 THEN 1 ELSE 0 END) AS watched_25_count,
            SUM(CASE WHEN completion_rate >= 50.0 THEN 1 ELSE 0 END) AS watched_50_count,
            SUM(CASE WHEN completion_rate >= 75.0 THEN 1 ELSE 0 END) AS watched_75_count,
            SUM(CASE WHEN completion_rate >= 90.0 OR finished = 1 THEN 1 ELSE 0 END) AS finished_count,
            SUM(CASE WHEN retained = 1 THEN 1 ELSE 0 END) AS retained_count
        FROM viewing_records
    )
    SELECT 'Started' AS stage, started_count AS count, 100.0 AS pct_of_initial FROM stage_counts
    UNION ALL
    SELECT '25% watched', watched_25_count, ROUND((CAST(watched_25_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
    UNION ALL
    SELECT '50% watched', watched_50_count, ROUND((CAST(watched_50_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
    UNION ALL
    SELECT '75% watched', watched_75_count, ROUND((CAST(watched_75_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
    UNION ALL
    SELECT 'Finished', finished_count, ROUND((CAST(finished_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts
    UNION ALL
    SELECT 'Retained', retained_count, ROUND((CAST(retained_count AS REAL) / started_count) * 100.0, 2) FROM stage_counts;
    """
    return pd.read_sql_query(sql, conn)

def verify_python_sql_consistency(df: pd.DataFrame) -> Dict[str, Any]:
    """Compare Python calculations vs SQL query results and assert consistency.

    Returns diagnostic report showing comparison results.
    """
    conn = get_db_connection()
    load_data_to_sqlite(df, conn)

    # 1. Compare Segments
    py_segments = calculate_segment_comparison(df, use_4_segments=False).set_index("segment")
    sql_segments = query_segment_summaries(conn).set_index("segment")

    segment_matches = True
    segment_diffs = []

    for seg in py_segments.index:
        if seg in sql_segments.index:
            py_row = py_segments.loc[seg]
            sql_row = sql_segments.loc[seg]
            if py_row["viewer_count"] != sql_row["viewer_count"] or abs(py_row["retention_rate"] - sql_row["retention_rate"]) > 0.001:
                segment_matches = False
                segment_diffs.append(f"{seg}: Py count={py_row['viewer_count']} vs SQL={sql_row['viewer_count']}")
        else:
            segment_matches = False
            segment_diffs.append(f"Missing {seg} in SQL results")

    # 2. Compare Funnel
    py_funnel = calculate_funnel_metrics(df)["stages"]
    py_funnel_map = {s["stage"]: s["count"] for s in py_funnel}
    sql_funnel = query_funnel_steps(conn).set_index("stage")["count"].to_dict()

    funnel_matches = True
    funnel_diffs = []
    for stage, count in py_funnel_map.items():
        sql_count = sql_funnel.get(stage, -1)
        if count != sql_count:
            funnel_matches = False
            funnel_diffs.append(f"{stage}: Py count={count} vs SQL count={sql_count}")

    conn.close()

    return {
        "consistent": segment_matches and funnel_matches,
        "segment_consistency": segment_matches,
        "segment_diffs": segment_diffs,
        "funnel_consistency": funnel_matches,
        "funnel_diffs": funnel_diffs
    }
