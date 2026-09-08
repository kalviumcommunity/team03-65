"""Day 20 — KPI Alert Monitoring and Risk Detection Module.

Monitors core platform KPIs and segment distributions against defined operational thresholds:
- Retention Rate < 30.0% -> CRITICAL alert (major platform churn risk)
- Completion Rate < 50.0% -> WARNING alert (high early abandonment)
- Average Pause Count > 4.0 -> WARNING alert (viewer friction / disruption)
- At-Risk Segment > 40.0% -> WARNING alert (unhealthy viewer cohort distribution)

Returns structured alert diagnostics without spamming when metrics are healthy.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from analysis.kpis import calculate_kpis
from analysis.segments import calculate_segment_comparison

ALERT_THRESHOLDS = {
    "min_retention_rate": 0.30,       # 30% minimum acceptable retention
    "min_completion_rate": 50.0,      # 50% minimum average completion rate
    "max_pause_count": 4.0,           # 4 pauses maximum before flagging friction
    "max_at_risk_segment_pct": 40.0   # 40% max allowable at-risk viewers
}

def evaluate_kpi_alerts(
    kpis: Optional[Dict[str, Any]] = None,
    segment_summary: Optional[pd.DataFrame] = None,
    df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """Evaluate operational health thresholds on computed KPIs and segment distributions.

    Returns:
    {
        "has_alerts": bool,
        "critical_count": int,
        "warning_count": int,
        "alerts": [
            {
                "level": "CRITICAL" | "WARNING" | "INFO",
                "metric": str,
                "current_value": float,
                "threshold_value": float,
                "title": str,
                "message": str,
                "recommendation": str
            },
            ...
        ]
    }
    """
    if kpis is None and df is not None:
        kpis = calculate_kpis(df)
    if segment_summary is None and df is not None:
        segment_summary = calculate_segment_comparison(df)

    if not kpis or kpis.get("total_viewers", 0) == 0:
        return {
            "has_alerts": False,
            "critical_count": 0,
            "warning_count": 0,
            "alerts": []
        }

    alerts = []

    # 1. Retention Rate Alert
    retention_val = kpis["overall_retention_rate"]["value"]
    if retention_val < ALERT_THRESHOLDS["min_retention_rate"]:
        alerts.append({
            "level": "CRITICAL",
            "metric": "overall_retention_rate",
            "current_value": retention_val,
            "threshold_value": ALERT_THRESHOLDS["min_retention_rate"],
            "title": "Critical Subscriber Retention Deficit",
            "message": (
                f"Overall 30-day retention is currently {retention_val:.1%}, "
                f"falling below the critical threshold of {ALERT_THRESHOLDS['min_retention_rate']:.0%}."
            ),
            "recommendation": "Review high-churn content titles and accelerate acquisition of top-tier engaging content."
        })

    # 2. Completion Rate Alert
    completion_val = kpis["average_completion_rate"]["value"]
    if completion_val < ALERT_THRESHOLDS["min_completion_rate"]:
        alerts.append({
            "level": "WARNING",
            "metric": "average_completion_rate",
            "current_value": completion_val,
            "threshold_value": ALERT_THRESHOLDS["min_completion_rate"],
            "title": "Low Viewer Completion Rate",
            "message": (
                f"Average completion rate is {completion_val:.1f}%, "
                f"below the operational target of {ALERT_THRESHOLDS['min_completion_rate']:.0f}%."
            ),
            "recommendation": "Inspect drop-off points in the funnel to identify early content bounce or runtime fatigue."
        })

    # 3. Pause Count Alert (Friction Indicator)
    pause_val = kpis["average_pause_count"]["value"]
    if pause_val > ALERT_THRESHOLDS["max_pause_count"]:
        alerts.append({
            "level": "WARNING",
            "metric": "average_pause_count",
            "current_value": pause_val,
            "threshold_value": ALERT_THRESHOLDS["max_pause_count"],
            "title": "Elevated Viewing Friction Detected",
            "message": (
                f"Average pause count per session is {pause_val:.1f}, "
                f"exceeding the friction ceiling of {ALERT_THRESHOLDS['max_pause_count']:.1f} pauses."
            ),
            "recommendation": "Investigate stream buffering, subtitle legibility, or title pacing disruptions."
        })

    # 4. At-Risk Segment Proportion Alert
    if segment_summary is not None and not segment_summary.empty:
        at_risk_row = segment_summary[segment_summary["segment"].str.contains("At Risk|Low", case=False, na=False)]
        if not at_risk_row.empty:
            at_risk_pct = float(at_risk_row.iloc[0]["viewer_pct"])
            if at_risk_pct > ALERT_THRESHOLDS["max_at_risk_segment_pct"]:
                alerts.append({
                    "level": "WARNING",
                    "metric": "at_risk_segment_pct",
                    "current_value": at_risk_pct,
                    "threshold_value": ALERT_THRESHOLDS["max_at_risk_segment_pct"],
                    "title": "High Concentration of At-Risk Viewers",
                    "message": (
                        f"{at_risk_pct:.1f}% of active viewers currently belong to the At-Risk / Low Engagement segment "
                        f"(threshold: {ALERT_THRESHOLDS['max_at_risk_segment_pct']:.0f}%)."
                    ),
                    "recommendation": "Target at-risk viewers with personalized re-engagement campaigns and high-completion titles."
                })

    critical_count = sum(1 for a in alerts if a["level"] == "CRITICAL")
    warning_count = sum(1 for a in alerts if a["level"] == "WARNING")

    return {
        "has_alerts": len(alerts) > 0,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "alerts": alerts
    }
