"""Day 19/20 Extension — Executive Briefing & Dossier Generator (10/10 UI/UX).

Generates a board-ready Markdown analytical briefing summarizing:
- Platform Health & KPI Scorecard
- Churn Bottleneck & Funnel Diagnostics
- Audience Segment Breakdown
- Content Acquisition Portfolio Recommendations
"""

from typing import Dict, Any
import pandas as pd
from datetime import datetime

from analysis.kpis import calculate_kpis
from analysis.funnel import calculate_funnel_metrics
from analysis.segments import calculate_segment_comparison
from analysis.recommendations import generate_acquisition_recommendations_list

def generate_executive_markdown_report(df: pd.DataFrame) -> str:
    """Generate a clean, structured Executive Briefing in Markdown."""
    if df.empty:
        return "# StreamLens Executive Briefing\n\nNo active data available."

    kpis = calculate_kpis(df)
    funnel = calculate_funnel_metrics(df)
    seg = calculate_segment_comparison(df)
    recs = generate_acquisition_recommendations_list(df)

    ret = kpis.get("overall_retention_rate", {}).get("formatted", "N/A")
    comp = kpis.get("average_completion_rate", {}).get("formatted", "N/A")
    dur = kpis.get("average_watch_duration", {}).get("formatted", "N/A")
    pause = kpis.get("average_pause_count", {}).get("formatted", "N/A")
    cont = kpis.get("content_completion_rate", {}).get("formatted", "N/A")

    biggest_drop = funnel.get("biggest_drop", {})
    from_st = biggest_drop.get("from_stage", "25%")
    to_st = biggest_drop.get("to_stage", "50%")
    d_rate = biggest_drop.get("drop_rate", 0.0)
    d_count = biggest_drop.get("drop_count", 0)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    high_prio = [r for r in recs if r["recommendation"] == "HIGH PRIORITY"]
    investigate = [r for r in recs if r["recommendation"] == "INVESTIGATE"]
    low_prio = [r for r in recs if r["recommendation"] == "LOW PRIORITY"]

    report = f"""# 🎬 StreamLens · Executive Retention & Content Acquisition Briefing
**Generated:** {now_str}  
**Analyzed Population:** {len(df):,} viewer sessions across {df['content_id'].nunique() if 'content_id' in df.columns else 1} titles

---

## 1. Executive Key Performance Indicators
- **Overall 30-Day Retention Rate:** {ret} (Target: ≥ 50.0%)
- **Average Title Completion Rate:** {comp} (Target: ≥ 65.0%)
- **Average Watch Duration:** {dur} per session
- **Playback Pause Frequency:** {pause} pauses/session (Benchmark: ≤ 3.0)
- **Finished Episode Rate:** {cont} (Sessions reaching ≥ 90% completion)

---

## 2. Playback Lifecycle & Churn Bottleneck Diagnosis
- **Primary Churn Cliff:** Between `{from_st}` and `{to_st}`
- **Bottleneck Drop-Off Rate:** {d_rate:.1f}% ({d_count:,} viewers lost)
- **Strategic Directive:** {funnel.get('bottleneck_narrative', 'Optimize mid-session content pacing.')}

---

## 3. Behavioral Viewer Segmentation
"""

    for _, row in seg.iterrows():
        report += f"- **{row['segment']}:** {row['viewer_pct']:.1f}% audience share | {row['retention_rate']:.1%} 30-day retention\n"

    report += f"""
---

## 4. Content Acquisition & Licensing Portfolio Decisions
- **High Priority Greenlight Titles ({len(high_prio)}):**
"""
    for h in high_prio[:5]:
        report += f"  - **{h['title']}** (Completion: {h['metrics']['average_completion_rate']:.1f}%, Retention: {h['metrics']['retention_rate']:.1%}) — *{h['reason']}*\n"

    if investigate:
        report += f"\n- **Titles Requiring Investigation ({len(investigate)}):**\n"
        for inv in investigate[:3]:
            report += f"  - **{inv['title']}** — *{inv['reason']}*\n"

    if low_prio:
        report += f"\n- **Low Priority / Deprioritize ({len(low_prio)}):**\n"
        for lp in low_prio[:3]:
            report += f"  - **{lp['title']}** — *{lp['reason']}*\n"

    report += """
---
*Confidential · StreamLens Platform Intelligence Engine*
"""
    return report
