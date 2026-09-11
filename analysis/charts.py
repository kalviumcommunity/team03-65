"""Day 17 — Interactive Plotly Charts for Engagement and Retention Analysis (10/10 UI/UX).

Provides executive-grade Plotly visualizations:
1. Completion Rate vs Retention (Box + jitter with refined SaaS styling)
2. Pause Count vs Retention (Friction indicator with distinct cohort colors)
3. Metric Distribution (Clean histogram with custom bins)
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from analysis.correlation import normalize_dataframe_columns, calculate_correlation_matrix, create_correlation_heatmap

COMMON_LAYOUT_KWARGS = dict(
    template="plotly_white",
    font_family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    hoverlabel=dict(
        bgcolor="#ffffff",
        font_size=12,
        font_family="Inter, sans-serif",
        bordercolor="#e2e8f0"
    )
)

def plot_completion_vs_retention(df: pd.DataFrame) -> go.Figure:
    """Generate an interactive Plotly chart comparing Completion Rate between retained and churned cohorts."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="Completion vs Retention (No Data)", **COMMON_LAYOUT_KWARGS)
        return fig

    norm_df = normalize_dataframe_columns(df).copy()
    if "completion_rate" not in norm_df.columns or "retained" not in norm_df.columns:
        fig = go.Figure()
        fig.update_layout(title="Required columns (completion_rate, retained) not found.", **COMMON_LAYOUT_KWARGS)
        return fig

    norm_df["retained_label"] = norm_df["retained"].apply(lambda x: "Retained (Active)" if bool(x) else "Churned (Lost)")
    norm_df["completion_rate"] = pd.to_numeric(norm_df["completion_rate"], errors="coerce")

    # Content/user ID tooltip info if present
    if "user_id" in norm_df.columns:
        norm_df["tooltip_id"] = "User ID: " + norm_df["user_id"].astype(str)
    elif "content_id" in norm_df.columns:
        norm_df["tooltip_id"] = "Content ID: " + norm_df["content_id"].astype(str)
    else:
        norm_df["tooltip_id"] = "Viewer #" + norm_df.index.astype(str)

    duration_str = norm_df["watch_duration"].round(1).astype(str) + " mins" if "watch_duration" in norm_df.columns else "N/A"
    norm_df["tooltip_dur"] = "Watch Duration: " + duration_str

    fig = go.Figure()

    colors = {"Retained (Active)": "#10b981", "Churned (Lost)": "#f43f5e"}

    for cohort in ["Retained (Active)", "Churned (Lost)"]:
        sub = norm_df[norm_df["retained_label"] == cohort]
        if sub.empty:
            continue

        # Cap jitter points to 500 per cohort to keep payload lightweight and browser instant
        plot_sub = sub.sample(500, random_state=42) if len(sub) > 500 else sub

        fig.add_trace(go.Box(
            x=plot_sub["retained_label"],
            y=plot_sub["completion_rate"],
            name=cohort,
            marker_color=colors.get(cohort, "#3b82f6"),
            boxpoints="all",
            jitter=0.25,
            pointpos=-1.8,
            marker=dict(size=6, opacity=0.7),
            line=dict(width=1.8),
            customdata=np.stack((plot_sub["tooltip_id"], plot_sub["tooltip_dur"]), axis=-1),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Cohort: <b>%{x}</b><br>"
                "Completion Rate: <b>%{y:.1f}%</b><br>"
                "%{customdata[1]}<extra></extra>"
            )
        ))

    fig.update_layout(
        title="<b>Viewer Completion Rate Distribution by Cohort</b><br><span style='font-size:12px;color:#64748b'>Higher completion strongly separates retained subscribers from churned users</span>",
        yaxis_title="Completion Rate (%)",
        xaxis_title="",
        height=420,
        showlegend=False,
        margin={"l": 50, "r": 40, "t": 70, "b": 40},
        **COMMON_LAYOUT_KWARGS
    )
    fig.update_yaxes(gridcolor="#f1f5f9", range=[-5, 105])
    fig.update_xaxes(gridcolor="#f1f5f9")
    return fig

def plot_pause_vs_retention(df: pd.DataFrame) -> go.Figure:
    """Generate an interactive Plotly chart comparing Pause Count between retained and churned cohorts."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="Pause Count vs Retention (No Data)", **COMMON_LAYOUT_KWARGS)
        return fig

    norm_df = normalize_dataframe_columns(df).copy()
    if "pause_count" not in norm_df.columns or "retained" not in norm_df.columns:
        fig = go.Figure()
        fig.update_layout(title="Required columns (pause_count, retained) not found.", **COMMON_LAYOUT_KWARGS)
        return fig

    norm_df["retained_label"] = norm_df["retained"].apply(lambda x: "Retained (Active)" if bool(x) else "Churned (Lost)")
    norm_df["pause_count"] = pd.to_numeric(norm_df["pause_count"], errors="coerce")

    if "user_id" in norm_df.columns:
        norm_df["tooltip_id"] = "User ID: " + norm_df["user_id"].astype(str)
    elif "content_id" in norm_df.columns:
        norm_df["tooltip_id"] = "Content ID: " + norm_df["content_id"].astype(str)
    else:
        norm_df["tooltip_id"] = "Viewer #" + norm_df.index.astype(str)

    fig = go.Figure()

    colors = {"Retained (Active)": "#10b981", "Churned (Lost)": "#f43f5e"}

    for cohort in ["Retained (Active)", "Churned (Lost)"]:
        sub = norm_df[norm_df["retained_label"] == cohort]
        if sub.empty:
            continue

        # Cap jitter points to 500 per cohort to keep payload lightweight and browser instant
        plot_sub = sub.sample(500, random_state=42) if len(sub) > 500 else sub

        fig.add_trace(go.Box(
            x=plot_sub["retained_label"],
            y=plot_sub["pause_count"],
            name=cohort,
            marker_color=colors.get(cohort, "#6366f1"),
            boxpoints="all",
            jitter=0.25,
            pointpos=-1.8,
            marker=dict(size=6, opacity=0.7),
            line=dict(width=1.8),
            customdata=plot_sub["tooltip_id"],
            hovertemplate=(
                "<b>%{customdata}</b><br>"
                "Cohort: <b>%{x}</b><br>"
                "Pause Frequency: <b>%{y} pauses</b><extra></extra>"
            )
        ))

    fig.update_layout(
        title="<b>Session Pause Frequency vs Retention</b><br><span style='font-size:12px;color:#64748b'>Excessive pauses indicate friction or distraction, correlating with subscriber churn</span>",
        yaxis_title="Pause Count per Session",
        xaxis_title="",
        height=420,
        showlegend=False,
        margin={"l": 50, "r": 40, "t": 70, "b": 40},
        **COMMON_LAYOUT_KWARGS
    )
    fig.update_yaxes(gridcolor="#f1f5f9")
    fig.update_xaxes(gridcolor="#f1f5f9")
    return fig

def plot_engagement_distribution(df: pd.DataFrame, metric: str = "completion_rate") -> go.Figure:
    """Plot interactive histogram distribution for a selected engagement metric."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title="No data available", **COMMON_LAYOUT_KWARGS)
        return fig

    norm_df = normalize_dataframe_columns(df).copy()
    if metric not in norm_df.columns:
        fig = go.Figure()
        fig.update_layout(title=f"Metric {metric} not found in dataset", **COMMON_LAYOUT_KWARGS)
        return fig

    values = pd.to_numeric(norm_df[metric], errors="coerce").dropna()
    clean_title = metric.replace('_', ' ').title()

    fig = px.histogram(
        values,
        nbins=25,
        title=f"<b>Distribution of {clean_title}</b>",
        labels={"value": clean_title, "count": "Frequency"},
        color_discrete_sequence=["#4f46e5"],
        template="plotly_white"
    )
    fig.update_layout(
        height=380,
        margin={"l": 50, "r": 40, "t": 60, "b": 40},
        bargap=0.08,
        **COMMON_LAYOUT_KWARGS
    )
    fig.update_yaxes(gridcolor="#f1f5f9")
    fig.update_xaxes(gridcolor="#f1f5f9")
    return fig
