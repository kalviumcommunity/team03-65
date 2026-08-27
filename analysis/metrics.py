import pandas as pd

# Explicit thresholds for viewer segmentation
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

# Explicit thresholds for acquisition recommendations
RECOMMENDATION_THRESHOLDS = {
    "high_engagement_completion": 75.0,
    "high_retention_rate": 0.70,
    "low_retention_rate": 0.50
}

def calculate_engagement_metrics(df: pd.DataFrame) -> dict:
    """Calculate overall engagement metrics from the cleaned dataframe."""
    if df.empty:
        return {
            "average_watch_duration": 0.0,
            "average_completion_rate": 0.0,
            "average_pause_count": 0.0,
            "average_sessions_per_week": 0.0,
            "retention_rate": 0.0
        }

    return {
        "average_watch_duration": float(df["watch_duration"].mean()),
        "average_completion_rate": float(df["completion_rate"].mean()),
        "average_pause_count": float(df["pause_count"].mean()),
        "average_sessions_per_week": float(df["sessions_per_week"].mean()),
        "retention_rate": float(df["retained"].mean())
    }

def calculate_retention_analysis(df: pd.DataFrame) -> dict:
    """Compare retained and non-retained viewers on key engagement metrics."""
    if df.empty:
        return {
            "retained": {},
            "non_retained": {},
            "retention_rate": 0.0
        }

    # Split dataset
    retained_df = df[df["retained"] == True]
    non_retained_df = df[df["retained"] == False]

    total_viewers = len(df)
    retained_count = len(retained_df)
    non_retained_count = len(non_retained_df)
    
    retention_rate = retained_count / total_viewers if total_viewers > 0 else 0.0

    # Calculate metrics for retained
    retained_metrics = {
        "count": retained_count,
        "percentage": float(retained_count / total_viewers * 100) if total_viewers > 0 else 0.0,
        "average_watch_duration": float(retained_df["watch_duration"].mean()) if retained_count > 0 else 0.0,
        "average_completion_rate": float(retained_df["completion_rate"].mean()) if retained_count > 0 else 0.0,
        "average_pause_count": float(retained_df["pause_count"].mean()) if retained_count > 0 else 0.0,
        "average_sessions_per_week": float(retained_df["sessions_per_week"].mean()) if retained_count > 0 else 0.0
    }

    # Calculate metrics for non-retained
    non_retained_metrics = {
        "count": non_retained_count,
        "percentage": float(non_retained_count / total_viewers * 100) if total_viewers > 0 else 0.0,
        "average_watch_duration": float(non_retained_df["watch_duration"].mean()) if non_retained_count > 0 else 0.0,
        "average_completion_rate": float(non_retained_df["completion_rate"].mean()) if non_retained_count > 0 else 0.0,
        "average_pause_count": float(non_retained_df["pause_count"].mean()) if non_retained_count > 0 else 0.0,
        "average_sessions_per_week": float(non_retained_df["sessions_per_week"].mean()) if non_retained_count > 0 else 0.0
    }

    return {
        "retained": retained_metrics,
        "non_retained": non_retained_metrics,
        "retention_rate": retention_rate
    }

def classify_viewer(row: pd.Series) -> str:
    """Classify a single viewer based on configured engagement thresholds."""
    completion = row["completion_rate"]
    sessions = row["sessions_per_week"]
    
    hi_thresholds = SEGMENTATION_THRESHOLDS["highly_engaged"]
    lo_thresholds = SEGMENTATION_THRESHOLDS["at_risk_low_engagement"]

    if completion >= hi_thresholds["completion_rate_min"] and sessions >= hi_thresholds["sessions_per_week_min"]:
        return "Highly Engaged"
    elif completion < lo_thresholds["completion_rate_max"] or sessions <= lo_thresholds["sessions_per_week_max"]:
        return "At Risk / Low Engagement"
    else:
        return "Moderately Engaged"

def segment_viewers(df: pd.DataFrame) -> list:
    """Segment viewers into categories and return aggregated segment metrics."""
    if df.empty:
        return []

    # Assign segments to each record
    df_segmented = df.copy()
    df_segmented["segment"] = df_segmented.apply(classify_viewer, axis=1)

    total_viewers = len(df_segmented)
    
    # Group by segment
    segment_groups = df_segmented.groupby("segment")
    results = []

    for name in ["Highly Engaged", "Moderately Engaged", "At Risk / Low Engagement"]:
        if name in segment_groups.groups:
            group = segment_groups.get_group(name)
            count = len(group)
            pct = (count / total_viewers * 100) if total_viewers > 0 else 0.0
            retention_rate = float(group["retained"].mean())
        else:
            count = 0
            pct = 0.0
            retention_rate = 0.0

        results.append({
            "segment": name,
            "viewer_count": count,
            "viewer_percentage": pct,
            "retention_rate": retention_rate
        })

    return results

def calculate_content_performance(df: pd.DataFrame) -> list:
    """Calculate aggregated engagement and retention metrics grouped by content_id."""
    if df.empty:
        return []

    performance = df.groupby("content_id").agg(
        viewer_count=("user_id", "count"),
        average_watch_duration=("watch_duration", "mean"),
        average_completion_rate=("completion_rate", "mean"),
        average_pause_count=("pause_count", "mean"),
        average_sessions_per_week=("sessions_per_week", "mean"),
        retention_rate=("retained", "mean")
    ).reset_index()

    # Convert numeric fields to clean types
    performance["viewer_count"] = performance["viewer_count"].astype(int)
    performance["average_watch_duration"] = performance["average_watch_duration"].round(2)
    performance["average_completion_rate"] = performance["average_completion_rate"].round(2)
    performance["average_pause_count"] = performance["average_pause_count"].round(2)
    performance["average_sessions_per_week"] = performance["average_sessions_per_week"].round(2)
    performance["retention_rate"] = performance["retention_rate"].round(4)

    return performance.to_dict(orient="records")

def generate_acquisition_recommendations(df: pd.DataFrame) -> list:
    """Generate acquisition recommendations for content items based on performance metrics."""
    content_perf = calculate_content_performance(df)
    if not content_perf:
        return []

    recommendations = []

    for item in content_perf:
        content_id = item["content_id"]
        completion = item["average_completion_rate"]
        retention = item["retention_rate"]
        viewers = item["viewer_count"]

        # Rule-based priority determination
        if completion >= RECOMMENDATION_THRESHOLDS["high_engagement_completion"] and retention >= RECOMMENDATION_THRESHOLDS["high_retention_rate"]:
            recommendation = "HIGH PRIORITY"
            reason = (
                f"Strong engagement profile (completion rate: {completion}%) coupled with high viewer retention "
                f"({retention:.1%}). Acquiring similar content is highly recommended to sustain platform growth."
            )
        elif completion >= RECOMMENDATION_THRESHOLDS["high_engagement_completion"] and retention < RECOMMENDATION_THRESHOLDS["high_retention_rate"]:
            recommendation = "INVESTIGATE"
            reason = (
                f"High viewer interest (completion rate: {completion}%) but relatively low viewer retention "
                f"({retention:.1%}). Investigate formatting, sequel fatigue, or drop-off factors before proceeding."
            )
        elif completion < RECOMMENDATION_THRESHOLDS["high_engagement_completion"] and retention < RECOMMENDATION_THRESHOLDS["low_retention_rate"]:
            recommendation = "LOW PRIORITY"
            reason = (
                f"Weak viewer interest (completion rate: {completion}%) and low retention "
                f"({retention:.1%}). Additional content acquisition of this profile is not advised."
            )
        else:
            recommendation = "STANDARD"
            reason = (
                f"Moderate engagement (completion rate: {completion}%) and moderate retention "
                f"({retention:.1%}). Performance meets standard baseline requirements."
            )

        recommendations.append({
            "content_id": content_id,
            "recommendation": recommendation,
            "reason": reason,
            "metrics": {
                "viewer_count": viewers,
                "average_watch_duration": item["average_watch_duration"],
                "average_completion_rate": completion,
                "average_pause_count": item["average_pause_count"],
                "average_sessions_per_week": item["average_sessions_per_week"],
                "retention_rate": retention
            }
        })

    # Sort recommendations by recommendation priority and retention rate for readability
    priority_order = {"HIGH PRIORITY": 0, "INVESTIGATE": 1, "STANDARD": 2, "LOW PRIORITY": 3}
    recommendations.sort(key=lambda x: (priority_order.get(x["recommendation"], 9), -x["metrics"]["retention_rate"]))

    return recommendations
