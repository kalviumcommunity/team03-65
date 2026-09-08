"""KPI Operational Alerts Component (Senior Designer Architecture).

Designed to Datadog / Vercel enterprise status standards:
- Minimalist status bar with subtle indicator dots
- High-signal incident hierarchy (Critical vs Warning)
- Clear separation of telemetry trigger from operational action
"""

import streamlit as st
from typing import Dict, Any, List

def clean_html(raw_html: str) -> str:
    """Normalize HTML to prevent Markdown parser from interpreting indented lines as code blocks."""
    return " ".join(line.strip() for line in raw_html.splitlines() if line.strip())

def render_alert_banners(alerts_payload: Dict[str, Any]) -> None:
    """Render structured KPI alerts in a senior executive monitoring layout."""
    if not alerts_payload:
        return

    has_alerts = alerts_payload.get("has_alerts", False)
    alerts = alerts_payload.get("alerts", [])

    if not has_alerts or not alerts:
        # Minimalist healthy status bar
        html = """
        <div style="display: flex; align-items: center; gap: 8px; background: #ffffff; border: 1px solid #e4e4e7; border-radius: 6px; padding: 8px 14px; margin-bottom: 16px; font-size: 12px; color: #52525b;">
            <span style="color: #16a34a; font-size: 10px;">●</span>
            <span style="font-weight: 600; color: #18181b;">System Health Nominal</span>
            <span style="color: #a1a1aa;">—</span>
            <span>All retention, completion, and friction telemetry satisfy operational SLA baselines.</span>
        </div>
        """
        st.markdown(clean_html(html), unsafe_allow_html=True)
        return

    # When active alerts exist
    header_html = f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
        <div style="display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #71717a;">Operational Risk Queue</span>
            <span style="font-size: 11px; font-weight: 600; background: #f4f4f5; color: #18181b; padding: 1px 6px; border-radius: 9999px; font-variant-numeric: tabular-nums;">{len(alerts)}</span>
        </div>
    </div>
    """
    st.markdown(clean_html(header_html), unsafe_allow_html=True)

    for alert in alerts:
        level = alert.get("level", "WARNING")
        title = alert.get("title", "Operational Notice")
        msg = alert.get("message", "")
        rec = alert.get("recommendation", "")

        is_critical = (level == "CRITICAL")
        status_dot = "#dc2626" if is_critical else "#d97706"
        badge_bg = "#fef2f2" if is_critical else "#fffbeb"
        badge_fg = "#991b1b" if is_critical else "#92400e"
        badge_text = "Critical SLA Breach" if is_critical else "Attention Required"

        alert_html = f"""
        <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 6px; padding: 12px 16px; margin-bottom: 10px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="color: {status_dot}; font-size: 10px;">●</span>
                    <span style="font-size: 13px; font-weight: 600; color: #09090b;">{title}</span>
                </div>
                <span style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: {badge_fg}; background: {badge_bg}; padding: 2px 6px; border-radius: 4px;">{badge_text}</span>
            </div>
            <div style="font-size: 12px; color: #52525b; line-height: 1.5; margin-bottom: 8px;">{msg}</div>
            <div style="font-size: 11px; color: #71717a; background: #f4f4f5; padding: 6px 10px; border-radius: 4px; display: flex; align-items: baseline; gap: 6px;">
                <span style="font-weight: 600; color: #27272a;">Action Directive:</span>
                <span>{rec}</span>
            </div>
        </div>
        """
        st.markdown(clean_html(alert_html), unsafe_allow_html=True)
