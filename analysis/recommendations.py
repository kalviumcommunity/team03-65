"""Day 19 — Acquisition Insights and Content Recommendation Module.

Implements evidence-based acquisition decisions for streaming content using
the project's canonical thresholds:
- high_engagement_completion: 75.0%
- high_retention_rate: 0.70 (70%)
- low_retention_rate: 0.50 (50%)

Categories:
- HIGH PRIORITY (Prioritize): High completion (>=75%) AND High retention (>=70%)
- INVESTIGATE: High completion (>=75%) BUT Low/moderate retention (<70%)
- LOW PRIORITY (Monitor): Low completion (<75%) AND Low retention (<50%)
- STANDARD: Balanced/moderate engagement and retention

Generates rich cards with retention evidence, engagement evidence, and actionable explanations.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from analysis.correlation import normalize_dataframe_columns

# Source of truth recommendation thresholds
RECOMMENDATION_THRESHOLDS = {
    "high_engagement_completion": 75.0,
    "high_retention_rate": 0.70,
    "low_retention_rate": 0.50
}

CATEGORY_CONFIG = {
    "HIGH PRIORITY": {
        "badge_color": "#27ae60",
        "label": "HIGH PRIORITY",
        "action_headline": "Prioritize Content Acquisition",
        "summary": "Strong engagement coupled with high subscriber retention."
    },
    "INVESTIGATE": {
        "badge_color": "#e67e22",
        "label": "INVESTIGATE",
        "action_headline": "Investigate Friction Factors",
        "summary": "High initial interest/completion but lower subsequent retention."
    },
    "STANDARD": {
        "badge_color": "#2980b9",
        "label": "STANDARD",
        "action_headline": "Standard Catalog Addition",
        "summary": "Consistent baseline engagement and standard retention performance."
    },
    "LOW PRIORITY": {
        "badge_color": "#7f8c8d",
        "label": "LOW PRIORITY",
        "action_headline": "Deprioritize / Monitor Only",
        "summary": "Weak completion and low retention profile."
    }
}

def classify_content_recommendation(
    completion_rate: float,
    retention_rate: float,
    viewer_count: int = 0
) -> Dict[str, Any]:
    """Classify a single content item into an acquisition category and generate supporting evidence."""
    hi_comp = RECOMMENDATION_THRESHOLDS["high_engagement_completion"]
    hi_ret = RECOMMENDATION_THRESHOLDS["high_retention_rate"]
    lo_ret = RECOMMENDATION_THRESHOLDS["low_retention_rate"]

    if completion_rate >= hi_comp and retention_rate >= hi_ret:
        category = "HIGH PRIORITY"
        reason = (
            f"Exceptional performance: Completion rate of {completion_rate:.1f}% meets the >= {hi_comp:.0f}% high-engagement "
            f"benchmark, and 30-day viewer retention rate of {retention_rate:.1%} meets the >= {hi_ret:.0%} retention threshold. "
            "Acquiring similar content is strongly advised to support subscriber growth."
        )
        retention_evidence = f"Strong viewer retention ({retention_rate:.1%}) significantly exceeds platform targets."
        engagement_evidence = f"High completion rate ({completion_rate:.1f}%) demonstrates compelling viewer satisfaction."

    elif completion_rate >= hi_comp and retention_rate < hi_ret:
        category = "INVESTIGATE"
        reason = (
            f"Mixed signals: Strong completion rate of {completion_rate:.1f}% indicates initial audience interest, "
            f"but retention rate of {retention_rate:.1%} is below the {hi_ret:.0%} benchmark. "
            "Investigate sequel fatigue, pacing drops, or lack of similar follow-up catalog titles before greenlighting."
        )
        retention_evidence = f"Retention rate ({retention_rate:.1%}) trails high-engagement expectations."
        engagement_evidence = f"High completion rate ({completion_rate:.1f}%) proves strong immediate engagement."

    elif completion_rate < hi_comp and retention_rate < lo_ret:
        category = "LOW PRIORITY"
        reason = (
            f"Underperforming profile: Completion rate ({completion_rate:.1f}%) is below {hi_comp:.0f}%, "
            f"and retention rate ({retention_rate:.1%}) falls below {lo_ret:.0%}. "
            "Content with these engagement attributes demonstrates elevated churn risk."
        )
        retention_evidence = f"Critically low retention ({retention_rate:.1%}) signals elevated churn risk."
        engagement_evidence = f"Low completion rate ({completion_rate:.1f}%) signals early viewer fatigue or drop-off."

    else:
        category = "STANDARD"
        reason = (
            f"Stable baseline: Completion rate ({completion_rate:.1f}%) and retention rate ({retention_rate:.1%}) "
            "meet standard operational baselines for catalog filler and moderate audience appeal."
        )
        retention_evidence = f"Retention ({retention_rate:.1%}) aligns with standard platform baseline."
        engagement_evidence = f"Completion rate ({completion_rate:.1f}%) represents consistent average viewing."

    return {
        "category": category,
        "reason": reason,
        "retention_evidence": retention_evidence,
        "engagement_evidence": engagement_evidence,
        "config": CATEGORY_CONFIG[category]
    }

def calculate_content_performance_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate engagement and retention metrics by content_id."""
    if df.empty:
        return pd.DataFrame()

    norm_df = normalize_dataframe_columns(df).copy()

    # If content_id not in dataset, return empty DataFrame
    if "content_id" not in norm_df.columns:
        return pd.DataFrame()

    # Sanitize fields
    for field in ["completion_rate", "watch_duration", "pause_count", "sessions_per_week"]:
        if field in norm_df.columns:
            norm_df[field] = pd.to_numeric(norm_df[field], errors="coerce").fillna(0.0)
        else:
            norm_df[field] = 0.0

    if "retained" in norm_df.columns:
        norm_df["retained_numeric"] = pd.to_numeric(norm_df["retained"], errors="coerce")
    else:
        norm_df["retained_numeric"] = np.nan

    # Viewer count = distinct users (not session rows); retention uses only
    # rows with a defined (eligible) user-level outcome.
    user_col = "user_id" if "user_id" in norm_df.columns else None

    def _rate(x: pd.Series) -> float:
        defined = x.dropna()
        return float(defined.mean()) if len(defined) > 0 else 0.0

    group_key = "content_id"
    base_agg = norm_df.groupby(group_key)
    agg_df = base_agg.agg(
        viewer_count=(("user_id" if user_col else "content_id"), "nunique" if user_col else "count"),
        avg_completion_rate=("completion_rate", "mean"),
        avg_watch_duration=("watch_duration", "mean"),
        avg_pause_count=("pause_count", "mean"),
        avg_sessions_per_week=("sessions_per_week", "mean"),
        retention_rate=("retained_numeric", _rate)
    ).reset_index()

    agg_df["avg_completion_rate"] = agg_df["avg_completion_rate"].round(2)
    agg_df["avg_watch_duration"] = agg_df["avg_watch_duration"].round(2)
    agg_df["avg_pause_count"] = agg_df["avg_pause_count"].round(2)
    agg_df["avg_sessions_per_week"] = agg_df["avg_sessions_per_week"].round(2)
    agg_df["retention_rate"] = agg_df["retention_rate"].round(4)

    return agg_df

def generate_acquisition_recommendations_list(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Produce full list of acquisition recommendation cards with supporting metrics and evidence."""
    perf_df = calculate_content_performance_summary(df)
    if perf_df.empty:
        return []

    recommendations = []
    for _, row in perf_df.iterrows():
        content_id = row["content_id"]
        comp = float(row["avg_completion_rate"])
        ret = float(row["retention_rate"])
        viewers = int(row["viewer_count"])

        decision = classify_content_recommendation(comp, ret, viewers)

        recommendations.append({
            "content_id": content_id,
            "title": f"Content #{content_id}",
            "recommendation": decision["category"],
            "reason": decision["reason"],
            "retention_evidence": decision["retention_evidence"],
            "engagement_evidence": decision["engagement_evidence"],
            "badge_color": decision["config"]["badge_color"],
            "metrics": {
                "viewer_count": viewers,
                "average_completion_rate": comp,
                "average_watch_duration": float(row["avg_watch_duration"]),
                "average_pause_count": float(row["avg_pause_count"]),
                "average_sessions_per_week": float(row["avg_sessions_per_week"]),
                "retention_rate": ret
            }
        })

    # Sort: HIGH PRIORITY, INVESTIGATE, STANDARD, LOW PRIORITY
    priority_rank = {"HIGH PRIORITY": 0, "INVESTIGATE": 1, "STANDARD": 2, "LOW PRIORITY": 3}
    recommendations.sort(key=lambda x: (priority_rank.get(x["recommendation"], 9), -x["metrics"]["retention_rate"]))

    return recommendations
