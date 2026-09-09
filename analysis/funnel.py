"""Day 13 — Drop-Off Detection and Funnel Analysis module.

Models viewer progression through defined viewing stages:
1. Started (> 0% watched)
2. 25% watched (>= 25% completed)
3. 50% watched (>= 50% completed)
4. 75% watched (>= 75% completed)
5. Finished (>= 90% completed / finished)
6. Retained (retained == True / 1)

Calculates stage volumes, stage-to-stage drop-off rates, identifies the
critical friction bottleneck automatically, and produces an actionable narrative.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from analysis.correlation import normalize_dataframe_columns

FUNNEL_STAGES = [
    "Started",
    "25% watched",
    "50% watched",
    "75% watched",
    "Finished",
    "Retained"
]

def calculate_funnel_metrics(df: pd.DataFrame) -> dict:
    """Calculate funnel counts, stage-over-stage drop-offs, and identify the biggest bottleneck.

    Returns:
    {
        "total_initial": int,
        "stages": [
            {
                "stage": str,
                "count": int,
                "percentage_of_total": float,
                "drop_count": int,
                "drop_rate": float,
                "conversion_from_prev": float
            },
            ...
        ],
        "biggest_drop": {
            "from_stage": str,
            "to_stage": str,
            "drop_count": int,
            "drop_rate": float
        },
        "bottleneck_narrative": str
    }
    """
    if df.empty:
        empty_stages = [
            {
                "stage": st,
                "count": 0,
                "percentage_of_total": 0.0,
                "drop_count": 0,
                "drop_rate": 0.0,
                "conversion_from_prev": 0.0
            }
            for st in FUNNEL_STAGES
        ]
        return {
            "total_initial": 0,
            "stages": empty_stages,
            "biggest_drop": {
                "from_stage": "None",
                "to_stage": "None",
                "drop_count": 0,
                "drop_rate": 0.0
            },
            "bottleneck_narrative": "No session or retention data available to evaluate viewer funnel drop-off."
        }

    norm_df = normalize_dataframe_columns(df)

    # Funnel stages describe viewer progression, so a user's furthest
    # completion (MAX) determines the stage they reached; retention is
    # user-level. Collapse to one row per user (AGENTS context section 8/11).
    if not norm_df.empty and "user_id" in norm_df.columns:
        agg_map = {}
        if "completion_rate" in norm_df.columns:
            agg_map["completion_rate"] = ("completion_rate", "max")
        if "finished" in norm_df.columns:
            agg_map["finished"] = ("finished", "max")
        if "retained" in norm_df.columns:
            agg_map["retained"] = ("retained", "max")
        if agg_map:
            norm_df = norm_df.groupby("user_id", as_index=False).agg(**agg_map)

    # Ensure completion_rate and retained columns exist and are numeric
    if "completion_rate" not in norm_df.columns:
        norm_df["completion_rate"] = 0.0
    else:
        norm_df["completion_rate"] = pd.to_numeric(norm_df["completion_rate"], errors="coerce").fillna(0.0)

    if "retained" in norm_df.columns:
        norm_df["retained_numeric"] = pd.to_numeric(norm_df["retained"], errors="coerce").fillna(0).astype(int)
    else:
        norm_df["retained_numeric"] = 0

    total_records = len(norm_df)

    # Calculate stage counts
    # Stage 1: Started
    count_started = int(len(norm_df[norm_df["completion_rate"] > 0])) if total_records > 0 else 0
    # If no records have >0, treat total records as started
    if count_started == 0 and total_records > 0:
        count_started = total_records

    # Stage 2: 25% watched
    count_25 = int(len(norm_df[norm_df["completion_rate"] >= 25.0]))
    # Stage 3: 50% watched
    count_50 = int(len(norm_df[norm_df["completion_rate"] >= 50.0]))
    # Stage 4: 75% watched
    count_75 = int(len(norm_df[norm_df["completion_rate"] >= 75.0]))
    # Stage 5: Finished (>=90% or finished column if present)
    if "finished" in norm_df.columns:
        finished_mask = (norm_df["finished"] == True) | (norm_df["completion_rate"] >= 90.0)
        count_finished = int(len(norm_df[finished_mask]))
    else:
        count_finished = int(len(norm_df[norm_df["completion_rate"] >= 90.0]))

    # Stage 6: Retained (distinct users; NaN outcomes already zeroed above)
    count_retained = int(len(norm_df[norm_df["retained_numeric"] == 1]))

    stage_counts = [
        ("Started", count_started),
        ("25% watched", count_25),
        ("50% watched", count_50),
        ("75% watched", count_75),
        ("Finished", count_finished),
        ("Retained", count_retained)
    ]

    stages_data = []
    max_drop_rate = -1.0
    biggest_drop_info = {
        "from_stage": "None",
        "to_stage": "None",
        "drop_count": 0,
        "drop_rate": 0.0
    }

    prev_count = None
    prev_stage_name = None

    for idx, (stage_name, count) in enumerate(stage_counts):
        pct_of_total = round((count / total_records) * 100, 2) if total_records > 0 else 0.0

        if prev_count is None:
            drop_count = 0
            drop_rate = 0.0
            conv_rate = 100.0 if count > 0 else 0.0
        else:
            drop_count = max(0, prev_count - count)
            drop_rate = round((drop_count / prev_count) * 100, 2) if prev_count > 0 else 0.0
            conv_rate = round((count / prev_count) * 100, 2) if prev_count > 0 else 0.0

            if drop_rate > max_drop_rate:
                max_drop_rate = drop_rate
                biggest_drop_info = {
                    "from_stage": prev_stage_name,
                    "to_stage": stage_name,
                    "drop_count": drop_count,
                    "drop_rate": drop_rate
                }

        stages_data.append({
            "stage": stage_name,
            "count": count,
            "percentage_of_total": pct_of_total,
            "drop_count": drop_count,
            "drop_rate": drop_rate,
            "conversion_from_prev": conv_rate
        })

        prev_count = count
        prev_stage_name = stage_name

    # Data-driven narrative based on the actual observed bottleneck
    if biggest_drop_info["from_stage"] != "None" and biggest_drop_info["drop_rate"] > 0:
        bottleneck_narrative = (
            f"The largest viewer drop-off occurs between '{biggest_drop_info['from_stage']}' and "
            f"'{biggest_drop_info['to_stage']}', with a loss of {biggest_drop_info['drop_count']} viewers "
            f"({biggest_drop_info['drop_rate']:.1f}% drop-off). "
        )
        if biggest_drop_info["to_stage"] == "25% watched":
            bottleneck_narrative += "This indicates early-content friction or mismatched title expectations leading to immediate bounce."
        elif biggest_drop_info["to_stage"] in ["50% watched", "75% watched"]:
            bottleneck_narrative += "This suggests pacing slowdowns during mid-title consumption."
        elif biggest_drop_info["to_stage"] == "Finished":
            bottleneck_narrative += "Viewers drop before the conclusion, signaling weak climaxes or runtime fatigue."
        elif biggest_drop_info["to_stage"] == "Retained":
            bottleneck_narrative += "While users complete content, long-term 30-day retention does not follow, highlighting catalog depth or follow-up engagement issues."
    else:
        bottleneck_narrative = "Funnel conversion is steady across all observation stages with no major drop-off detected."

    return {
        "total_initial": total_records,
        "stages": stages_data,
        "biggest_drop": biggest_drop_info,
        "bottleneck_narrative": bottleneck_narrative
    }

def create_funnel_chart(funnel_data: dict):
    """Build an interactive Plotly Funnel visualization."""
    import plotly.graph_objects as go

    stages = funnel_data.get("stages", [])
    if not stages or funnel_data.get("total_initial", 0) == 0:
        fig = go.Figure()
        fig.update_layout(
            title="Viewer Drop-Off Funnel (No Data Available)",
            annotations=[{
                "text": "No viewer data available for funnel visualization.",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 14}
            }]
        )
        return fig

    stage_names = [s["stage"] for s in stages]
    counts = [s["count"] for s in stages]
    drop_rates = [f"-{s['drop_rate']:.1f}% drop" if s["drop_rate"] > 0 else "Baseline" for s in stages]

    fig = go.Figure(go.Funnel(
        y=stage_names,
        x=counts,
        textinfo="value+percent initial",
        texttemplate="<b>%{value:,}</b> viewers (%{percentInitial:.1%})",
        hoverinfo="x+y+percent previous",
        hovertemplate="<b>%{y}</b><br>Active Volume: <b>%{x:,}</b><br>Stage Drop: <b>%{customdata}</b><extra></extra>",
        customdata=drop_rates,
        marker={"color": ["#4f46e5", "#6366f1", "#0284c7", "#0ea5e9", "#059669", "#10b981"]}
    ))

    biggest = funnel_data.get("biggest_drop", {})
    subtext = (
        f"Critical Friction Point: <b>{biggest.get('from_stage')} ➔ {biggest.get('to_stage')}</b> "
        f"(-{biggest.get('drop_rate', 0):.1f}% drop)"
        if biggest.get("drop_rate", 0) > 0 else "Consistent conversion across all funnel observation stages"
    )

    fig.update_layout(
        title=f"<b>Viewer Lifecycle & Drop-Off Funnel</b><br><span style='font-size:12px;color:#64748b'>{subtext}</span>",
        height=450,
        template="plotly_white",
        font_family="Inter, -apple-system, sans-serif",
        hoverlabel=dict(bgcolor="#ffffff", font_size=12, font_family="Inter, sans-serif", bordercolor="#e2e8f0"),
        margin={"l": 90, "r": 50, "t": 75, "b": 40}
    )
    return fig
