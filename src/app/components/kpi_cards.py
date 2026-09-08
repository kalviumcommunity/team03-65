"""Executive KPI Cards Component (Senior Designer Architecture).

Designed to Linear / Stripe design standards:
- Precision typographic scale with tabular numerals
- Restrained, high-signal neutral palette with purposeful status accents
- 1px hairline structural borders and subtle micro-elevation
- Clean benchmark progress track and period-over-period delta chips
"""

import streamlit as st
from typing import Dict, Any, Optional

def clean_html(raw_html: str) -> str:
    """Normalize HTML to prevent Markdown parser from interpreting indented lines as code blocks."""
    return " ".join(line.strip() for line in raw_html.splitlines() if line.strip())

def render_kpi_cards(kpis: Dict[str, Any]) -> None:
    """Render the 5 core KPI metric cards in a senior executive scorecard layout."""
    if not kpis or kpis.get("total_viewers", 0) == 0:
        st.info("No viewer data available to compute platform KPIs.")
        return

    # Extract metrics safely
    ret = kpis.get("overall_retention_rate", {"value": 0.0, "formatted": "0.0%", "delta": None})
    comp = kpis.get("average_completion_rate", {"value": 0.0, "formatted": "0.0%", "delta": None})
    dur = kpis.get("average_watch_duration", {"value": 0.0, "formatted": "0.0m", "delta": None})
    pause = kpis.get("average_pause_count", {"value": 0.0, "formatted": "0.0", "delta": None})
    cont = kpis.get("content_completion_rate", {"value": 0.0, "formatted": "0.0%", "delta": None})

    card_definitions = [
        {
            "label": "30-Day Retention",
            "value": ret["formatted"],
            "target": "Target ≥ 50%",
            "benchmark_pct": min(100, max(5, int(ret["value"] * 100))),
            "delta": ret.get("delta"),
            "delta_unit": "%",
            "invert_delta": False,
            "track_color": "#09090b" if ret["value"] >= 0.50 else "#f59e0b" if ret["value"] >= 0.30 else "#ef4444",
        },
        {
            "label": "Avg Completion",
            "value": comp["formatted"],
            "target": "Target ≥ 65%",
            "benchmark_pct": min(100, max(5, int(comp["value"]))),
            "delta": comp.get("delta"),
            "delta_unit": "%",
            "invert_delta": False,
            "track_color": "#09090b" if comp["value"] >= 65.0 else "#f59e0b",
        },
        {
            "label": "Watch Duration",
            "value": dur["formatted"],
            "target": "Target ≥ 30m",
            "benchmark_pct": min(100, max(5, int((dur["value"] / 60.0) * 100))),
            "delta": dur.get("delta"),
            "delta_unit": "m",
            "invert_delta": False,
            "track_color": "#09090b",
        },
        {
            "label": "Playback Friction",
            "value": f"{pause['value']:.2f}" if isinstance(pause.get('value'), (int, float)) else pause["formatted"],
            "target": "Target ≤ 3.0 pauses",
            "benchmark_pct": min(100, max(5, int((pause["value"] / 8.0) * 100))),
            "delta": pause.get("delta"),
            "delta_unit": "",
            "invert_delta": True,  # Lower pause is better
            "track_color": "#10b981" if pause["value"] <= 3.0 else "#f59e0b" if pause["value"] <= 4.5 else "#ef4444",
        },
        {
            "label": "Completion Rate",
            "value": cont["formatted"],
            "target": "Target ≥ 35%",
            "benchmark_pct": min(100, max(5, int(cont["value"] * 100))),
            "delta": cont.get("delta"),
            "delta_unit": "%",
            "invert_delta": False,
            "track_color": "#09090b" if cont["value"] >= 0.35 else "#f59e0b",
        }
    ]

    cols = st.columns(5)

    for col, card in zip(cols, card_definitions):
        with col:
            delta_html = ""
            if card["delta"] is not None:
                d_val = card["delta"]
                is_pos = d_val > 0
                is_good = (is_pos and not card["invert_delta"]) or (not is_pos and card["invert_delta"])
                
                fg = "#15803d" if is_good else "#b91c1c"
                bg = "#f0fdf4" if is_good else "#fef2f2"
                symbol = "+" if d_val > 0 else ""
                
                delta_html = f'<span style="font-size: 11px; font-weight: 600; color: {fg}; background: {bg}; padding: 1px 6px; border-radius: 4px; font-variant-numeric: tabular-nums; letter-spacing: -0.01em;">{symbol}{d_val:.1f}{card["delta_unit"]}</span>'

            html = f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 16px 18px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03); display: flex; flex-direction: column; justify-content: space-between; min-height: 120px; transition: border-color 0.15s ease;">
                <div>
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                        <span style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #71717a;">{card['label']}</span>
                        {delta_html}
                    </div>
                    <div style="font-size: 1.75rem; font-weight: 700; color: #09090b; letter-spacing: -0.03em; line-height: 1.1; font-variant-numeric: tabular-nums;">{card['value']}</div>
                </div>
                <div style="margin-top: 14px;">
                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #a1a1aa; font-weight: 500; margin-bottom: 6px;">
                        <span>{card['target']}</span>
                        <span style="color: #71717a; font-weight: 600;">{card['benchmark_pct']}%</span>
                    </div>
                    <div style="width: 100%; height: 3px; background: #f4f4f5; border-radius: 9999px; overflow: hidden;">
                        <div style="width: {card['benchmark_pct']}%; height: 100%; background: {card['track_color']}; border-radius: 9999px;"></div>
                    </div>
                </div>
            </div>
            """
            st.markdown(clean_html(html), unsafe_allow_html=True)
