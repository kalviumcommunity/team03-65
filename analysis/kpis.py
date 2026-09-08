"""Day 14 — Centralized KPI Computation Layer.

Defines and computes the 5 core project KPIs:
1. Overall Retention Rate:
   Formula: COUNT(retained viewers) / COUNT(total eligible viewers)
2. Average Completion Rate:
   Formula: SUM(completion_rate) / COUNT(sessions/viewers)
3. Average Watch Duration:
   Formula: SUM(watch_duration_minutes) / COUNT(sessions/viewers)
4. Average Pause Count:
   Formula: SUM(pause_count) / COUNT(sessions/viewers)
5. Content Completion Rate:
   Formula: COUNT(sessions where completion >= 90% or finished) / COUNT(total sessions)

Handles empty/invalid datasets safely and supports optional previous-period
delta comparison when genuine temporal cohort data is present.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from analysis.correlation import normalize_dataframe_columns

KPI_METADATA = {
    "overall_retention_rate": {
        "label": "Overall Retention Rate",
        "format": "{:.1%}",
        "unit": "%",
        "description": "Percentage of active viewers retained over 30 days."
    },
    "average_completion_rate": {
        "label": "Avg Completion Rate",
        "format": "{:.1f}%",
        "unit": "%",
        "description": "Average percentage of content completed per viewing session."
    },
    "average_watch_duration": {
        "label": "Avg Watch Duration",
        "format": "{:.1f} min",
        "unit": "min",
        "description": "Average watch duration in minutes per session."
    },
    "average_pause_count": {
        "label": "Avg Pause Count",
        "format": "{:.1f}",
        "unit": "pauses",
        "description": "Average number of pauses per viewing session."
    },
    "content_completion_rate": {
        "label": "Content Completion Rate",
        "format": "{:.1%}",
        "unit": "%",
        "description": "Percentage of sessions where content was completed (>=90%)."
    }
}

def calculate_kpis(df: pd.DataFrame, previous_df: Optional[pd.DataFrame] = None) -> dict:
    """Compute the 5 required platform KPIs from current dataset, with optional genuine deltas.

    Returns:
    {
        "overall_retention_rate": {"value": float, "formatted": str, "delta": Optional[float]},
        "average_completion_rate": {"value": float, "formatted": str, "delta": Optional[float]},
        "average_watch_duration": {"value": float, "formatted": str, "delta": Optional[float]},
        "average_pause_count": {"value": float, "formatted": str, "delta": Optional[float]},
        "content_completion_rate": {"value": float, "formatted": str, "delta": Optional[float]},
        "total_viewers": int,
        "retained_viewers": int
    }
    """
    if df.empty:
        return {
            "overall_retention_rate": {"value": 0.0, "formatted": "0.0%", "delta": None},
            "average_completion_rate": {"value": 0.0, "formatted": "0.0%", "delta": None},
            "average_watch_duration": {"value": 0.0, "formatted": "0.0 min", "delta": None},
            "average_pause_count": {"value": 0.0, "formatted": "0.0", "delta": None},
            "content_completion_rate": {"value": 0.0, "formatted": "0.0%", "delta": None},
            "total_viewers": 0,
            "retained_viewers": 0
        }

    norm_df = normalize_dataframe_columns(df).copy()

    # Sanitize required columns
    total_viewers = len(norm_df)

    # 1. Overall Retention Rate
    if "retained" in norm_df.columns:
        ret_series = pd.to_numeric(norm_df["retained"], errors="coerce").fillna(0).astype(int)
        retained_viewers = int(ret_series.sum())
        retention_rate = float(retained_viewers / total_viewers) if total_viewers > 0 else 0.0
    else:
        retained_viewers = 0
        retention_rate = 0.0

    # 2. Average Completion Rate
    if "completion_rate" in norm_df.columns:
        comp_series = pd.to_numeric(norm_df["completion_rate"], errors="coerce").dropna()
        avg_completion = float(comp_series.mean()) if not comp_series.empty else 0.0
    else:
        avg_completion = 0.0

    # 3. Average Watch Duration
    if "watch_duration" in norm_df.columns:
        dur_series = pd.to_numeric(norm_df["watch_duration"], errors="coerce").dropna()
        avg_duration = float(dur_series.mean()) if not dur_series.empty else 0.0
    else:
        avg_duration = 0.0

    # 4. Average Pause Count
    if "pause_count" in norm_df.columns:
        pause_series = pd.to_numeric(norm_df["pause_count"], errors="coerce").dropna()
        avg_pauses = float(pause_series.mean()) if not pause_series.empty else 0.0
    else:
        avg_pauses = 0.0

    # 5. Content Completion Rate (sessions where >= 90% or finished)
    if "finished" in norm_df.columns:
        finished_series = norm_df["finished"].astype(bool)
        content_comp_rate = float(finished_series.mean()) if not finished_series.empty else 0.0
    elif "completion_rate" in norm_df.columns:
        finished_series = norm_df["completion_rate"] >= 90.0
        content_comp_rate = float(finished_series.mean()) if not finished_series.empty else 0.0
    else:
        content_comp_rate = 0.0

    # Calculate previous period KPIs if previous_df provided
    prev_kpis = None
    if previous_df is not None and not previous_df.empty:
        prev_kpis = calculate_kpis(previous_df, previous_df=None)

    def get_delta(key: str, curr_val: float) -> Optional[float]:
        if prev_kpis and key in prev_kpis:
            return round(curr_val - prev_kpis[key]["value"], 4)
        return None

    return {
        "overall_retention_rate": {
            "value": round(retention_rate, 4),
            "formatted": f"{retention_rate:.1%}",
            "delta": get_delta("overall_retention_rate", retention_rate)
        },
        "average_completion_rate": {
            "value": round(avg_completion, 2),
            "formatted": f"{avg_completion:.1f}%",
            "delta": get_delta("average_completion_rate", avg_completion)
        },
        "average_watch_duration": {
            "value": round(avg_duration, 2),
            "formatted": f"{avg_duration:.1f} min",
            "delta": get_delta("average_watch_duration", avg_duration)
        },
        "average_pause_count": {
            "value": round(avg_pauses, 2),
            "formatted": f"{avg_pauses:.1f}",
            "delta": get_delta("average_pause_count", avg_pauses)
        },
        "content_completion_rate": {
            "value": round(content_comp_rate, 4),
            "formatted": f"{content_comp_rate:.1%}",
            "delta": get_delta("content_completion_rate", content_comp_rate)
        },
        "total_viewers": total_viewers,
        "retained_viewers": retained_viewers
    }
