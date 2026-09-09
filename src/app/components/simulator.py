"""Strategic What-If Retention & Financial Simulator (Senior Designer Architecture).

Modeled after FP&A and growth forecasting tools at Stripe & Netflix:
- Sensitivity projections on viewer completion and playback friction
- Net retained subscribers and ARR financial modeling
- Precision typography and minimal structural containers
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any

from analysis.correlation import calculate_correlation_matrix, to_user_level
from analysis.kpis import calculate_kpis
from src.app.components.html_utils import clean_html

def render_what_if_simulator(df: pd.DataFrame) -> None:
    """Render the senior executive What-If Retention & Financial Simulator."""
    st.markdown("### Strategic Sensitivity & Growth Simulator")
    st.caption("Forecast the retained subscriber lift and annual recurring revenue (ARR) gained from targeted product optimizations.")

    if df.empty or "retained" not in df.columns:
        st.info("Insufficient telemetry data to run sensitivity model.")
        return

    # User-level grain: one row per viewer for retention math (AGENTS context
    # section 8); a viewer with many sessions must not count multiple times.
    user_df = to_user_level(df)

    # Baseline calculations
    total_viewers = len(user_df)
    retained_defined = pd.to_numeric(user_df["retained"], errors="coerce").dropna()
    baseline_retention = float(retained_defined.mean()) if len(retained_defined) > 0 else 0.0
    avg_comp = float(user_df["completion_rate"].mean()) if "completion_rate" in user_df.columns else 60.0
    avg_pause = float(user_df["pause_count"].mean()) if "pause_count" in user_df.columns else 3.5

    # Sensitivity slopes via correlation
    corr_data = calculate_correlation_matrix(user_df)
    r_comp = corr_data.get("completion_rate", {}).get("retained", 0.85) if isinstance(corr_data, dict) else 0.85
    r_pause = abs(corr_data.get("pause_count", {}).get("retained", -0.85)) if isinstance(corr_data, dict) else 0.85

    std_ret = float(user_df["retained"].std()) if float(user_df["retained"].std()) > 0 else 0.25
    std_comp = float(user_df["completion_rate"].std()) if "completion_rate" in user_df.columns and float(user_df["completion_rate"].std()) > 0 else 20.0
    std_pause = float(user_df["pause_count"].std()) if "pause_count" in user_df.columns and float(user_df["pause_count"].std()) > 0 else 2.0

    col_sim_left, col_sim_right = st.columns([1, 2])

    with col_sim_left:
        st.markdown(
            clean_html("""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 16px; margin-bottom: 14px;">
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #71717a; margin-bottom: 4px;">Model Controls</div>
                <div style="font-size: 12px; color: #71717a; margin-bottom: 14px;">Adjust targeted operational lifts.</div>
            </div>
            """),
            unsafe_allow_html=True
        )

        comp_lift = st.slider(
            "Target Completion Uplift (% pts)",
            min_value=0.0,
            max_value=25.0,
            value=5.0,
            step=0.5,
            help="Simulate the impact of structural pacing improvements or recap cards."
        )

        pause_reduction = st.slider(
            "Target Pause Reduction (pauses/session)",
            min_value=0.0,
            max_value=4.0,
            value=1.0,
            step=0.2,
            help="Simulate the impact of CDN edge caching and player buffer optimization."
        )

        arpu = st.number_input(
            "Monthly Subscription ARPU ($)",
            min_value=1.0,
            max_value=100.0,
            value=12.99,
            step=1.0,
            help="Average revenue per subscriber per month."
        )

    # Statistical projection model
    delta_r_comp = (comp_lift / std_comp) * r_comp * std_ret
    delta_r_pause = (pause_reduction / std_pause) * r_pause * std_ret
    combined_delta_r = (delta_r_comp + delta_r_pause) * 0.75

    simulated_retention = min(0.98, max(baseline_retention, baseline_retention + combined_delta_r))
    retention_lift_pct = (simulated_retention - baseline_retention) * 100.0

    baseline_retained_users = int(round(total_viewers * baseline_retention))
    simulated_retained_users = int(round(total_viewers * simulated_retention))
    incremental_subscribers = max(0, simulated_retained_users - baseline_retained_users)
    annual_arr_uplift = incremental_subscribers * arpu * 12.0

    with col_sim_right:
        # Minimalist 4-Metric Grid
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(
            clean_html(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 14px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.02);">
                <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #71717a;">Baseline Retention</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #09090b; margin-top: 2px; font-variant-numeric: tabular-nums;">{baseline_retention:.1%}</div>
                <div style="font-size: 11px; color: #a1a1aa; margin-top: 2px;">{baseline_retained_users:,} subscribers</div>
            </div>
            """),
            unsafe_allow_html=True
        )

        c2.markdown(
            clean_html(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 14px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.02);">
                <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #71717a;">Simulated Retention</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #09090b; margin-top: 2px; font-variant-numeric: tabular-nums;">{simulated_retention:.1%}</div>
                <div style="font-size: 11px; color: #16a34a; font-weight: 600; margin-top: 2px;">+{retention_lift_pct:.1f}% lift</div>
            </div>
            """),
            unsafe_allow_html=True
        )

        c3.markdown(
            clean_html(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 14px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.02);">
                <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #71717a;">Subscribers Saved</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #09090b; margin-top: 2px; font-variant-numeric: tabular-nums;">+{incremental_subscribers:,}</div>
                <div style="font-size: 11px; color: #71717a; margin-top: 2px;">Retained delta</div>
            </div>
            """),
            unsafe_allow_html=True
        )

        c4.markdown(
            clean_html(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 14px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.02);">
                <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #71717a;">Projected ARR Lift</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #09090b; margin-top: 2px; font-variant-numeric: tabular-nums;">${annual_arr_uplift:,.0f}</div>
                <div style="font-size: 11px; color: #71717a; margin-top: 2px;">at ${arpu:.2f}/mo</div>
            </div>
            """),
            unsafe_allow_html=True
        )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # Plotly Comparison
        categories = ["Baseline Cohort", "Simulated Optimization"]
        ret_vals = [baseline_retention * 100.0, simulated_retention * 100.0]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Retention Rate (%)",
            x=categories,
            y=ret_vals,
            text=[f"{v:.1f}%" for v in ret_vals],
            textposition="auto",
            marker_color=["#d4d4d8", "#18181b"],
            width=0.45
        ))

        fig.update_layout(
            title={
                "text": "<b>Retention Rate Sensitivity: Baseline vs Optimized Model</b>",
                "font": {"family": "Plus Jakarta Sans", "size": 13, "color": "#09090b"}
            },
            template="plotly_white",
            height=280,
            margin=dict(l=40, r=20, t=50, b=30),
            yaxis=dict(title="Retention Rate (%)", range=[0, 100], gridcolor="#f4f4f5"),
            xaxis=dict(gridcolor="#f4f4f5"),
            showlegend=False
        )

        st.plotly_chart(fig, width="stretch")

    # Executive Assessment
    st.markdown(
        clean_html(f"""
        <div style="background: #f4f4f5; border: 1px solid #e4e4e7; border-radius: 6px; padding: 12px 16px; margin-top: 10px; font-size: 12px; color: #3f3f46; line-height: 1.5;">
            <span style="font-weight: 600; color: #09090b;">Strategic Synthesis:</span>
            A <b>+{comp_lift:.1f}% title completion lift</b> combined with a <b>-{pause_reduction:.1f} playback pause reduction</b> is projected to preserve <b>+{incremental_subscribers:,} subscribers</b>, defending <b>${annual_arr_uplift:,.0f} in annualized subscription revenue</b>.
        </div>
        """),
        unsafe_allow_html=True
    )
