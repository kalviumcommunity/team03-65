"""Day 12 — Viewer Segment Comparison module.

Classifies viewers into engagement segments based on project thresholds and
computes comparative metrics across segments:
- Average completion rate
- Average watch duration
- Average pause count
- Sessions per week
- Retention rate
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from analysis.correlation import normalize_dataframe_columns

# Source of truth segment thresholds
SEGMENTATION_THRESHOLDS = {
    "highly_engaged": {
        "completion_rate_min": 80.0,
        "sessions_per_week_min": 5
    },
    "at_risk_low_engagement": {
        "completion_rate_max": 50.0,
        "sessions_per_week_max": 2
    }
}

# 4-Segment PRD classification thresholds (consistent with the 2 core anchor boundaries)
FOUR_SEGMENT_THRESHOLDS = {
    "highly_engaged": {"completion_min": 80.0, "sessions_min": 5},
    "steady_viewers": {"completion_min": 65.0, "sessions_min": 3},
    "casual_viewers": {"completion_min": 50.0, "sessions_min": 2},
}

def classify_viewer_3_segments(completion_rate: float, sessions_per_week: float) -> str:
    """Classify a viewer into the 3 canonical segments from analysis/metrics.py."""
    hi = SEGMENTATION_THRESHOLDS["highly_engaged"]
    lo = SEGMENTATION_THRESHOLDS["at_risk_low_engagement"]

    if completion_rate >= hi["completion_rate_min"] and sessions_per_week >= hi["sessions_per_week_min"]:
        return "Highly Engaged"
    elif completion_rate < lo["completion_rate_max"] or sessions_per_week <= lo["sessions_per_week_max"]:
        return "At Risk / Low Engagement"
    else:
        return "Moderately Engaged"

def classify_viewer_4_segments(completion_rate: float, sessions_per_week: float) -> str:
    """Classify a viewer into the 4 PRD segments (Section 6)."""
    if completion_rate >= 80.0 and sessions_per_week >= 5:
        return "Highly Engaged"
    elif completion_rate >= 65.0 and sessions_per_week >= 3:
        return "Steady Viewers"
    elif completion_rate >= 50.0 and sessions_per_week > 2:
        return "Casual Viewers"
    else:
        return "Low / At-Risk"

def assign_segments(df: pd.DataFrame, use_4_segments: bool = False) -> pd.DataFrame:
    """Assign segment label to each viewer record in dataframe."""
    if df.empty:
        df_out = df.copy()
        df_out["segment"] = pd.Series(dtype=str)
        return df_out

    norm_df = normalize_dataframe_columns(df).copy()

    # Fill defaults for required classification columns if missing
    if "completion_rate" not in norm_df.columns:
        norm_df["completion_rate"] = 0.0
    if "sessions_per_week" not in norm_df.columns:
        norm_df["sessions_per_week"] = 1.0

    classifier = classify_viewer_4_segments if use_4_segments else classify_viewer_3_segments
    norm_df["segment"] = norm_df.apply(
        lambda r: classifier(r["completion_rate"], r["sessions_per_week"]),
        axis=1
    )
    return norm_df

def calculate_segment_comparison(df: pd.DataFrame, use_4_segments: bool = False) -> pd.DataFrame:
    """Compute comparative engagement and retention metrics across viewer segments.

    Returns a DataFrame summary with columns:
    - segment
    - viewer_count
    - viewer_pct
    - avg_completion_rate
    - avg_watch_duration
    - avg_pause_count
    - avg_sessions_per_week
    - retention_rate
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "segment", "viewer_count", "viewer_pct", "avg_completion_rate",
            "avg_watch_duration", "avg_pause_count", "avg_sessions_per_week", "retention_rate"
        ])

    segmented_df = assign_segments(df, use_4_segments=use_4_segments)
    total_viewers = len(segmented_df)

    # Ensure numeric columns are properly typed
    for col in ["completion_rate", "watch_duration", "pause_count", "sessions_per_week"]:
        if col in segmented_df.columns:
            segmented_df[col] = pd.to_numeric(segmented_df[col], errors="coerce")
        else:
            segmented_df[col] = 0.0

    if "retained" in segmented_df.columns:
        segmented_df["retained_numeric"] = pd.to_numeric(segmented_df["retained"], errors="coerce").fillna(0).astype(int)
    else:
        segmented_df["retained_numeric"] = 0

    expected_segments = (
        ["Highly Engaged", "Steady Viewers", "Casual Viewers", "Low / At-Risk"]
        if use_4_segments
        else ["Highly Engaged", "Moderately Engaged", "At Risk / Low Engagement"]
    )

    records = []
    groups = segmented_df.groupby("segment")

    for seg in expected_segments:
        if seg in groups.groups:
            group = groups.get_group(seg)
            count = len(group)
            pct = round((count / total_viewers) * 100, 2) if total_viewers > 0 else 0.0
            avg_comp = round(float(group["completion_rate"].mean()), 2)
            avg_dur = round(float(group["watch_duration"].mean()), 2)
            avg_pauses = round(float(group["pause_count"].mean()), 2)
            avg_sess = round(float(group["sessions_per_week"].mean()), 2)
            ret_rate = round(float(group["retained_numeric"].mean()), 4)
        else:
            count = 0
            pct = 0.0
            avg_comp = 0.0
            avg_dur = 0.0
            avg_pauses = 0.0
            avg_sess = 0.0
            ret_rate = 0.0

        records.append({
            "segment": seg,
            "viewer_count": count,
            "viewer_pct": pct,
            "avg_completion_rate": avg_comp,
            "avg_watch_duration": avg_dur,
            "avg_pause_count": avg_pauses,
            "avg_sessions_per_week": avg_sess,
            "retention_rate": ret_rate
        })

    return pd.DataFrame(records)

def create_segment_comparison_chart(summary_df: pd.DataFrame):
    """Build an interactive Plotly multi-bar comparison chart for viewer segments."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    if summary_df.empty or summary_df["viewer_count"].sum() == 0:
        fig = go.Figure()
        fig.update_layout(
            title="Segment Comparison (No Data Available)",
            annotations=[{
                "text": "No viewer segment data available to display.",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 14}
            }]
        )
        return fig

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Retention Rate by Segment", "Completion Rate & Watch Duration by Segment"),
        specs=[[{"secondary_y": False}, {"secondary_y": True}]]
    )

    # Subplot 1: Retention Rate by segment
    ret_pct = [r * 100 for r in summary_df["retention_rate"]]
    segment_palette = []
    for s in summary_df["segment"]:
        if "High" in s:
            segment_palette.append("#10b981")
        elif "Steady" in s or "Mod" in s:
            segment_palette.append("#3b82f6")
        elif "Casual" in s:
            segment_palette.append("#f59e0b")
        else:
            segment_palette.append("#f43f5e")

    fig.add_trace(
        go.Bar(
            x=summary_df["segment"],
            y=ret_pct,
            name="Retention Rate (%)",
            marker_color=segment_palette,
            text=[f"<b>{v:.1f}%</b>" for v in ret_pct],
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>30-Day Retention: <b>%{y:.1f}%</b><br>Cohort Size: <b>%{customdata:,} viewers</b><extra></extra>",
            customdata=summary_df["viewer_count"]
        ),
        row=1, col=1
    )

    # Subplot 2: Completion Rate & Watch Duration
    fig.add_trace(
        go.Bar(
            x=summary_df["segment"],
            y=summary_df["avg_completion_rate"],
            name="Avg Completion (%)",
            marker_color="#6366f1",
            text=[f"<b>{v:.1f}%</b>" for v in summary_df["avg_completion_rate"]],
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>Avg Completion: <b>%{y:.1f}%</b><extra></extra>"
        ),
        row=1, col=2, secondary_y=False
    )

    fig.add_trace(
        go.Scatter(
            x=summary_df["segment"],
            y=summary_df["avg_watch_duration"],
            name="Avg Duration (min)",
            mode="lines+markers",
            line={"color": "#f59e0b", "width": 3},
            marker={"size": 9, "color": "#f59e0b", "line": {"width": 2, "color": "#ffffff"}},
            hovertemplate="<b>%{x}</b><br>Avg Session Time: <b>%{y:.1f} mins</b><extra></extra>"
        ),
        row=1, col=2, secondary_y=True
    )

    fig.update_layout(
        title="<b>Viewer Segmentation Drivers: Retention, Completion & Watch Duration</b>",
        barmode="group",
        height=450,
        template="plotly_white",
        font_family="Inter, -apple-system, sans-serif",
        hoverlabel=dict(bgcolor="#ffffff", font_size=12, font_family="Inter, sans-serif", bordercolor="#e2e8f0"),
        margin={"l": 50, "r": 50, "t": 70, "b": 50},
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.25, "xanchor": "center", "x": 0.5}
    )

    fig.update_yaxes(title_text="Retention Rate (%)", range=[0, 105], gridcolor="#f1f5f9", row=1, col=1)
    fig.update_yaxes(title_text="Completion Rate (%)", range=[0, 105], gridcolor="#f1f5f9", row=1, col=2, secondary_y=False)
    fig.update_yaxes(title_text="Duration (mins)", gridcolor="#f1f5f9", row=1, col=2, secondary_y=True)

    return fig
