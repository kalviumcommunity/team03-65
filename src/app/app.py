"""StreamLens · Streaming Retention & Content Acquisition Platform.

Senior Executive Interface:
- Day 11: Correlation Analysis & Plotly Heatmap
- Day 12: Viewer Segment Comparison & Personas
- Day 13: Funnel Attrition & Bottleneck Diagnostics
- Day 14: Centralized KPI Computation Engine
- Day 15: SQL Analytics Integration & Parity Verification
- Day 16: Executive KPI Scorecard with Benchmark Gauges
- Day 17: Interactive Plotly Visualizations
- Day 18: Defensive Error States & Schema Validation
- Day 19: Acquisition Decision Suite & Evidence Cards
- Day 20: Operational SLA Alert Monitoring
- Extension: Executive Stakeholder Perspective Switcher
- Extension: Strategic What-If Sensitivity Simulator
- Extension: Relational SQL Governance Workbench
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
import pandas as pd
import numpy as np

from analysis.cleaning import clean_viewing_data
from analysis.correlation import (
    calculate_correlation_matrix,
    generate_correlation_report,
    create_correlation_heatmap,
    normalize_dataframe_columns
)
from analysis.segments import (
    calculate_segment_comparison,
    create_segment_comparison_chart
)
from analysis.funnel import (
    calculate_funnel_metrics,
    create_funnel_chart
)
from analysis.kpis import calculate_kpis
from analysis.charts import (
    plot_completion_vs_retention,
    plot_pause_vs_retention,
    plot_engagement_distribution
)
from analysis.validation import (
    validate_csv_upload,
    validate_dataframe_schema,
    safe_run_analysis
)
from analysis.recommendations import (
    generate_acquisition_recommendations_list,
    calculate_content_performance_summary
)
from analysis.alerts import evaluate_kpi_alerts
from src.app.components.html_utils import clean_html
from src.app.components.kpi_cards import render_kpi_cards
from src.app.components.alerts import render_alert_banners
from src.app.components.problem_statements import render_problem_statement_navigator
from src.app.components.simulator import render_what_if_simulator
from src.app.components.sql_audit import render_sql_audit_workbench
from src.app.components.report_generator import generate_executive_markdown_report

# --- Page Configuration ---
st.set_page_config(
    page_title="StreamLens · Retention Intelligence",
    page_icon="■",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Senior Designer Custom CSS (Linear / Stripe / Vercel Aesthetic)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: #09090b;
        background-color: #fafafa;
    }

    /* Container Spacing */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Tabs Architecture */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #f4f4f5;
        padding: 4px;
        border-radius: 8px;
        border: 1px solid #e4e4e7;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 6px 14px;
        font-weight: 500;
        font-size: 13px;
        border-radius: 6px;
        color: #71717a;
        transition: all 0.15s ease;
        border: none !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #18181b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #09090b !important;
        font-weight: 600;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }

    /* Hide redundant elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}
    [data-testid="stHeader"] {background: transparent !important;}
</style>
""", unsafe_allow_html=True)

# --- Data Loading Helper ---
@st.cache_data
def load_default_dataset() -> pd.DataFrame:
    """Load default dataset from project directory with automatic cleaning."""
    candidate_paths = [
        REPO_ROOT / "data" / "generated" / "viewer_sessions.csv",
        REPO_ROOT / "data" / "viewing_data.csv"
    ]
    for p in candidate_paths:
        if p.exists() and p.stat().st_size > 0:
            raw_df = pd.read_csv(p)
            if "viewing_data.csv" in str(p):
                clean_df = clean_viewing_data(raw_df)
                return normalize_dataframe_columns(clean_df)
            else:
                df = raw_df.copy()
                if "retained" not in df.columns and "retained_30d" not in df.columns:
                    ret_path = REPO_ROOT / "data" / "generated" / "viewer_retention.csv"
                    if ret_path.exists():
                        ret_df = pd.read_csv(ret_path)
                        latest_ret = ret_df.groupby("user_id")["retained_30d"].last().reset_index()
                        df = df.merge(latest_ret, on="user_id", how="left")
                return normalize_dataframe_columns(df)
    return pd.DataFrame()

# --- Sidebar Architecture ---
with st.sidebar:
    st.markdown(
        clean_html("""
        <div style="margin-bottom: 18px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <span style="font-size: 13px; font-weight: 700; letter-spacing: 0.06em; color: #09090b;">STREAMLENS</span>
                <span style="font-size: 10px; font-weight: 600; color: #71717a; background: #f4f4f5; padding: 2px 6px; border-radius: 4px; border: 1px solid #e4e4e7;">v2.4</span>
            </div>
            <div style="font-size: 11px; color: #71717a; margin-top: 2px;">Enterprise Telemetry</div>
        </div>
        """),
        unsafe_allow_html=True
    )

    st.markdown("<div style='height: 1px; background: #e4e4e7; margin: 14px 0;'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #71717a; margin-bottom: 8px;'>Telemetry Ingestion</div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload Custom Viewing CSV",
        type=["csv"],
        help="Upload CSV containing viewer activity (Day 18 validation flow)."
    )

    active_df = pd.DataFrame()

    if uploaded_file is not None:
        is_valid, msg, validated_df = validate_csv_upload(uploaded_file)
        if is_valid:
            st.success(f"File verified: {msg}")
            active_df = validated_df
        else:
            st.error(f"Validation failure: {msg}")
            st.info("Reverted to verified baseline dataset.")
            active_df = load_default_dataset()
    else:
        active_df = load_default_dataset()

    filtered_df = active_df.copy()

    if not active_df.empty:
        quick_ret_val = float(active_df["retained"].mean()) if "retained" in active_df.columns else 0.50
        titles_count = int(active_df["content_id"].nunique()) if "content_id" in active_df.columns else 1
        
        st.markdown(
            clean_html(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 6px; padding: 10px 12px; margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px;">
                    <span style="color: #71717a; font-weight: 500;">Active Sessions</span>
                    <span style="font-weight: 700; color: #09090b; font-variant-numeric: tabular-nums;">{len(active_df):,}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; margin-top: 4px;">
                    <span style="color: #71717a; font-weight: 500;">Portfolio Retention</span>
                    <span style="font-weight: 700; color: #16a34a; font-variant-numeric: tabular-nums;">{quick_ret_val:.1%}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; margin-top: 4px;">
                    <span style="color: #71717a; font-weight: 500;">Catalog Depth</span>
                    <span style="font-weight: 700; color: #09090b;">{titles_count} titles</span>
                </div>
            </div>
            """),
            unsafe_allow_html=True
        )

        st.markdown("<div style='font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #71717a; margin-bottom: 8px;'>Cohort Segmentation</div>", unsafe_allow_html=True)

        # Preset Filter
        cohort_preset = st.radio(
            "Viewer Cohort",
            ["All Viewers", "Retained Subscribers", "Churned Users"],
            horizontal=True,
            label_visibility="collapsed"
        )
        if cohort_preset == "Retained Subscribers":
            filtered_df = filtered_df[filtered_df["retained"] == 1]
        elif cohort_preset == "Churned Users":
            filtered_df = filtered_df[filtered_df["retained"] == 0]

        # Content Filter
        if "content_id" in active_df.columns:
            all_content = ["All Titles"] + sorted(list(active_df["content_id"].dropna().unique()))
            selected_content = st.selectbox("Content Title", all_content)
            if selected_content != "All Titles":
                filtered_df = filtered_df[filtered_df["content_id"] == selected_content]

        # Completion Range Filter
        if "completion_rate" in active_df.columns:
            comp_range = st.slider(
                "Completion Window (%)",
                min_value=0.0,
                max_value=100.0,
                value=(0.0, 100.0),
                step=5.0
            )
            filtered_df = filtered_df[
                (filtered_df["completion_rate"] >= comp_range[0]) & 
                (filtered_df["completion_rate"] <= comp_range[1])
            ]

        pct_active = (len(filtered_df) / len(active_df)) if len(active_df) > 0 else 1.0
        st.caption(f"Cohort sample: **{len(filtered_df):,}** of **{len(active_df):,}** ({pct_active:.0%})")

        st.markdown("<div style='height: 1px; background: #e4e4e7; margin: 14px 0;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #71717a; margin-bottom: 8px;'>Governance & Exports</div>", unsafe_allow_html=True)

        sample_csv = active_df.head(20).to_csv(index=False)
        st.download_button(
            "Download CSV Ingestion Template",
            data=sample_csv,
            file_name="sample_viewing_data.csv",
            mime="text/csv",
            width="stretch"
        )

        if st.button("Generate Executive Briefing", width="stretch"):
            briefing_text = generate_executive_markdown_report(filtered_df)
            st.download_button(
                "Export Briefing (Markdown)",
                data=briefing_text,
                file_name="streamlens_briefing.md",
                mime="text/markdown",
                width="stretch"
            )
            with st.expander("Executive Briefing Preview", expanded=True):
                st.markdown(briefing_text)

    st.markdown("<div style='height: 1px; background: #e4e4e7; margin: 14px 0;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="font-size: 11px; color: #a1a1aa; line-height: 1.4;">
            Streamlit · SQLite · Pandas · Plotly<br>
            Deterministic Simulation Engine
        </div>
        """,
        unsafe_allow_html=True
    )

# --- Executive Top Bar ---
hero_col1, hero_col2 = st.columns([3, 1])

with hero_col1:
    st.markdown(
        clean_html("""
        <div style="margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                <span style="font-size: 11px; font-weight: 700; letter-spacing: 0.06em; color: #71717a; text-transform: uppercase;">
                    RETENTION & ACQUISITION PLATFORM
                </span>
                <span style="font-size: 10px; font-weight: 600; color: #16a34a; background: #f0fdf4; border: 1px solid #bbf7d0; padding: 1px 6px; border-radius: 4px;">
                    ● SIMULATION ENGINE ACTIVE
                </span>
            </div>
            <h1 style="margin: 0 0 4px 0; font-size: 1.85rem; font-weight: 700; color: #09090b; letter-spacing: -0.03em;">
                Streaming Retention & Acquisition Intelligence
            </h1>
            <p style="margin: 0; color: #52525b; font-size: 13px; font-weight: 400; max-width: 820px; line-height: 1.5;">
                Bridging viewer consumption telemetry with subscriber retention and acquisition ROI. Analyze completion rates, playback friction, and behavioral cohorts to drive capital allocation.
            </p>
        </div>
        """),
        unsafe_allow_html=True
    )

with hero_col2:
    if not filtered_df.empty:
        quick_ret = float(filtered_df["retained"].mean()) if "retained" in filtered_df.columns else 0.0
        titles_count = int(filtered_df["content_id"].nunique()) if "content_id" in filtered_df.columns else 1
        st.markdown(
            clean_html(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 12px 16px; text-align: right; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);">
                <div style="font-size: 10px; font-weight: 700; color: #71717a; text-transform: uppercase; letter-spacing: 0.05em;">30-Day Cohort Retention</div>
                <div style="font-size: 1.6rem; font-weight: 700; color: #09090b; letter-spacing: -0.02em; font-variant-numeric: tabular-nums;">{quick_ret:.1%}</div>
                <div style="font-size: 11px; color: #71717a; margin-top: 1px;">Across <b>{titles_count}</b> catalog titles</div>
            </div>
            """),
            unsafe_allow_html=True
        )

# --- Empty State Guard ---
if filtered_df.empty:
    st.warning("No records found for current selection.")
    st.info("Adjust filters in the sidebar or upload a valid viewer activity CSV.")
    st.stop()

# --- Senior Perspective Switcher (Linear-Style Dossier) ---
render_problem_statement_navigator(filtered_df)

# --- Primary Tab Navigation ---
(
    tab_overview,
    tab_engagement,
    tab_segments,
    tab_funnel,
    tab_acquisition,
    tab_simulator,
    tab_sql_audit
) = st.tabs([
    "Executive Cockpit",
    "Engagement Drivers",
    "Viewer Segments",
    "Funnel Analysis",
    "Content Portfolio",
    "What-If Model",
    "SQL Parity"
])

# =============================================================================
# TAB 1: EXECUTIVE COCKPIT
# =============================================================================
with tab_overview:
    # 1. Operational Alerts
    kpis_data = calculate_kpis(filtered_df)
    segment_summary = calculate_segment_comparison(filtered_df)
    alerts_data = evaluate_kpi_alerts(kpis=kpis_data, segment_summary=segment_summary)
    render_alert_banners(alerts_data)

    # 2. Scorecard
    render_kpi_cards(kpis_data)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    col_overview_left, col_overview_right = st.columns([3, 2])

    with col_overview_left:
        corr_res = safe_run_analysis(generate_correlation_report, filtered_df)
        takeaway_text = corr_res["data"].get("summary_takeaway", "No correlation data available.") if corr_res["success"] else "Insufficient data."

        st.markdown(
            clean_html(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px;">
                <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #71717a; margin-bottom: 4px;">Strategic Finding</div>
                <div style="font-size: 13px; font-weight: 600; color: #09090b; line-height: 1.5;">{takeaway_text}</div>
                <div style="font-size: 12px; color: #71717a; margin-top: 4px;">Directive: Authorize licensing exclusively for assets exhibiting high completion and uninterrupted playback profiles.</div>
            </div>
            """),
            unsafe_allow_html=True
        )

        st.markdown("#### Metric Distribution Explorer")
        metric_choices = {
            "completion_rate": "Completion Rate (%)",
            "watch_duration": "Watch Duration (minutes)",
            "pause_count": "Pause Frequency (per session)",
            "sessions_per_week": "Viewing Cadence (sessions / week)"
        }
        selected_metric = st.selectbox(
            "Select Telemetry Metric:",
            list(metric_choices.keys()),
            format_func=lambda k: metric_choices[k]
        )
        dist_fig = plot_engagement_distribution(filtered_df, selected_metric)
        st.plotly_chart(dist_fig, width="stretch")

    with col_overview_right:
        st.markdown("#### Segment Distribution Summary")
        if not segment_summary.empty:
            display_seg = segment_summary[["segment", "viewer_count", "viewer_pct", "retention_rate"]].copy()
            display_seg.columns = ["Segment", "Audience Size", "Audience Share", "30D Retention"]
            display_seg["Audience Share"] = display_seg["Audience Share"].apply(lambda v: f"{v:.1f}%")
            display_seg["30D Retention"] = display_seg["30D Retention"].apply(lambda v: f"{v:.1%}")
            st.dataframe(display_seg, width="stretch", hide_index=True)

        st.markdown(
            clean_html("""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 14px 16px; margin-top: 14px;">
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #71717a; margin-bottom: 8px;">Acquisition Governance Criteria</div>
                <div style="font-size: 12px; color: #52525b; line-height: 1.6;">
                    • <b>High Priority:</b> Completion ≥ 75.0% AND Retention ≥ 70.0%<br>
                    • <b>Investigate:</b> Completion ≥ 75.0% BUT Retention &lt; 70.0%<br>
                    • <b>Low Priority:</b> Completion &lt; 75.0% AND Retention &lt; 50.0%<br>
                    • <b>Standard:</b> Catalog baseline performance
                </div>
            </div>
            """),
            unsafe_allow_html=True
        )

# =============================================================================
# TAB 2: ENGAGEMENT DRIVERS
# =============================================================================
with tab_engagement:
    st.markdown("### Engagement Telemetry vs 30-Day Subscriber Retention")
    st.caption("Quantifies statistical associations between viewer session behaviors and subscriber survival.")

    corr_report = generate_correlation_report(filtered_df)

    col_heat, col_corr_table = st.columns([3, 2])

    with col_heat:
        st.markdown("#### Pearson Correlation Matrix")
        matrix_data = calculate_correlation_matrix(filtered_df)
        heat_fig = create_correlation_heatmap(matrix_data)
        st.plotly_chart(heat_fig, width="stretch")

    with col_corr_table:
        st.markdown("#### Statistical Associations")
        corr_list = corr_report.get("retention_correlations", [])
        if corr_list:
            df_corr_table = pd.DataFrame(corr_list)[["metric_label", "correlation_coefficient", "direction", "strength"]]
            df_corr_table.columns = ["Telemetry Metric", "Pearson r", "Direction", "Strength"]
            st.dataframe(df_corr_table, width="stretch", hide_index=True)

            st.markdown(
                clean_html("""
                <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 6px; padding: 10px 12px; font-size: 11px; color: #52525b; margin-top: 10px; line-height: 1.5;">
                    <b>Signal Thresholds:</b><br>
                    • <b>|r| ≥ 0.80:</b> Strongest actionable retention driver<br>
                    • <b>Negative r:</b> Playback friction and churn indicator
                </div>
                """),
                unsafe_allow_html=True
            )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("#### Cohort Behavioral Dispersion (Retained vs Churned)")

    col_box1, col_box2 = st.columns(2)

    with col_box1:
        comp_fig = plot_completion_vs_retention(filtered_df)
        st.plotly_chart(comp_fig, width="stretch")

    with col_box2:
        pause_fig = plot_pause_vs_retention(filtered_df)
        st.plotly_chart(pause_fig, width="stretch")

# =============================================================================
# TAB 3: VIEWER SEGMENTS
# =============================================================================
with tab_segments:
    st.markdown("### Behavioral Audience Segmentation")
    st.caption("Classifies subscribers into distinct viewing profiles based on completion rate and weekly cadence.")

    top_seg_col1, top_seg_col2 = st.columns([3, 1])
    with top_seg_col2:
        use_4_seg = st.toggle("4-Segment Granularity (PRD Section 6)", value=False)

    seg_df = calculate_segment_comparison(filtered_df, use_4_segments=use_4_seg)

    st.markdown("#### Comparative Cohort Performance Matrix")
    formatted_seg = seg_df.copy()
    formatted_seg.columns = [
        "Segment", "Audience Size", "Audience Share (%)",
        "Avg Completion (%)", "Avg Duration (min)", "Avg Pauses",
        "Sessions / Week", "30D Retention"
    ]
    formatted_seg["30D Retention"] = formatted_seg["30D Retention"].apply(lambda v: f"{v:.1%}")
    st.dataframe(formatted_seg, width="stretch", hide_index=True)

    st.markdown("#### Cohort Retention Distribution")
    seg_chart = create_segment_comparison_chart(seg_df)
    st.plotly_chart(seg_chart, width="stretch")

    # Persona Profiles
    st.markdown("#### Behavioral Segment Definitions")
    persona_cols = st.columns(3 if not use_4_seg else 4)

    personas = [
        {
            "name": "Highly Engaged",
            "criteria": "Completion ≥ 80% & Sessions ≥ 5/wk",
            "traits": "Daily binge patterns, low pause friction, primary platform advocates."
        },
        {
            "name": "Steady Viewers" if use_4_seg else "Steady / Moderate",
            "criteria": "Moderate completion & viewing cadence",
            "traits": "Consistent weekly viewing, predictable consumption, loyal baseline."
        },
        {
            "name": "Low / At-Risk" if use_4_seg else "At Risk / Low Engagement",
            "criteria": "Completion < 50% OR Sessions ≤ 2/wk",
            "traits": "Frequent pauses, early abandonment, high immediate churn risk."
        }
    ]

    for p_col, p in zip(persona_cols, personas):
        with p_col:
            st.markdown(
                clean_html(f"""
                <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 14px; min-height: 130px;">
                    <div style="font-weight: 700; color: #09090b; font-size: 13px; margin-bottom: 4px;">{p['name']}</div>
                    <div style="font-size: 11px; font-weight: 600; color: #71717a; text-transform: uppercase;">{p['criteria']}</div>
                    <div style="font-size: 12px; color: #52525b; margin-top: 8px; line-height: 1.4;">{p['traits']}</div>
                </div>
                """),
                unsafe_allow_html=True
            )

# =============================================================================
# TAB 4: FUNNEL ANALYSIS
# =============================================================================
with tab_funnel:
    st.markdown("### Viewer Lifecycle & Drop-Off Detection")
    st.caption("Track title consumption from start through completion and subsequent 30-day retention.")

    funnel_data = calculate_funnel_metrics(filtered_df)
    biggest = funnel_data.get("biggest_drop", {})

    st.markdown(
        clean_html(f"""
        <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 6px; padding: 12px 16px; margin-bottom: 18px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #71717a; margin-bottom: 4px;">Friction Bottleneck Diagnosis</div>
            <div style="font-size: 13px; color: #09090b; font-weight: 600; line-height: 1.5;">{funnel_data.get('bottleneck_narrative', '')}</div>
        </div>
        """),
        unsafe_allow_html=True
    )

    col_fun_chart, col_fun_table = st.columns([3, 2])

    with col_fun_chart:
        funnel_fig = create_funnel_chart(funnel_data)
        st.plotly_chart(funnel_fig, width="stretch")

    with col_fun_table:
        st.markdown("#### Stage Conversion Breakdown")
        stages_df = pd.DataFrame(funnel_data.get("stages", []))
        if not stages_df.empty:
            st_clean = stages_df[["stage", "count", "percentage_of_total", "drop_count", "drop_rate", "conversion_from_prev"]].copy()
            st_clean.columns = ["Stage", "Volume", "% Total", "Drop", "Stage Drop (%)", "Conversion (%)"]
            st.dataframe(st_clean, width="stretch", hide_index=True)

# =============================================================================
# TAB 5: CONTENT PORTFOLIO
# =============================================================================
with tab_acquisition:
    st.markdown("### Content Portfolio Decision Suite")
    st.caption("Translates engagement and retention telemetry into capital greenlighting priorities.")

    recs = generate_acquisition_recommendations_list(filtered_df)

    if not recs:
        st.info("No content records available for evaluation.")
    else:
        categories = [r["recommendation"] for r in recs]

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(
            clean_html(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.02);">
                <div style="font-size: 10px; font-weight: 700; color: #71717a; text-transform: uppercase; letter-spacing: 0.05em;">High Priority</div>
                <div style="font-size: 1.6rem; font-weight: 700; color: #09090b; margin-top: 2px;">{categories.count('HIGH PRIORITY')}</div>
                <div style="font-size: 11px; color: #16a34a;">Greenlight Candidates</div>
            </div>
            """),
            unsafe_allow_html=True
        )
        c2.markdown(
            clean_html(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.02);">
                <div style="font-size: 10px; font-weight: 700; color: #71717a; text-transform: uppercase; letter-spacing: 0.05em;">Investigate</div>
                <div style="font-size: 1.6rem; font-weight: 700; color: #09090b; margin-top: 2px;">{categories.count('INVESTIGATE')}</div>
                <div style="font-size: 11px; color: #d97706;">Mixed Telemetry</div>
            </div>
            """),
            unsafe_allow_html=True
        )
        c3.markdown(
            clean_html(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.02);">
                <div style="font-size: 10px; font-weight: 700; color: #71717a; text-transform: uppercase; letter-spacing: 0.05em;">Standard</div>
                <div style="font-size: 1.6rem; font-weight: 700; color: #09090b; margin-top: 2px;">{categories.count('STANDARD')}</div>
                <div style="font-size: 11px; color: #71717a;">Catalog Baseline</div>
            </div>
            """),
            unsafe_allow_html=True
        )
        c4.markdown(
            clean_html(f"""
            <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.02);">
                <div style="font-size: 10px; font-weight: 700; color: #71717a; text-transform: uppercase; letter-spacing: 0.05em;">Low Priority</div>
                <div style="font-size: 1.6rem; font-weight: 700; color: #09090b; margin-top: 2px;">{categories.count('LOW PRIORITY')}</div>
                <div style="font-size: 11px; color: #dc2626;">Deprioritize</div>
            </div>
            """),
            unsafe_allow_html=True
        )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        filter_col1, filter_col2 = st.columns([2, 1])
        with filter_col1:
            filter_cat = st.selectbox(
                "Filter Portfolio by Priority Category:",
                ["All Categories", "HIGH PRIORITY", "INVESTIGATE", "STANDARD", "LOW PRIORITY"]
            )
        with filter_col2:
            export_records = []
            for r in recs:
                m = r["metrics"]
                export_records.append({
                    "content_id": r["content_id"],
                    "recommendation": r["recommendation"],
                    "viewer_count": m["viewer_count"],
                    "avg_completion_rate": m["average_completion_rate"],
                    "avg_watch_duration": m["average_watch_duration"],
                    "avg_pause_count": m["average_pause_count"],
                    "retention_rate": m["retention_rate"],
                    "rationale": r["reason"]
                })
            export_df = pd.DataFrame(export_records)
            st.download_button(
                "Export Portfolio Dossier (CSV)",
                data=export_df.to_csv(index=False),
                file_name="acquisition_dossier.csv",
                mime="text/csv",
                width="stretch"
            )

        display_recs = [r for r in recs if filter_cat == "All Categories" or r["recommendation"] == filter_cat]

        for item in display_recs:
            badge_fg = "#15803d" if item['recommendation'] == 'HIGH PRIORITY' else "#92400e" if item['recommendation'] == 'INVESTIGATE' else "#991b1b" if item['recommendation'] == 'LOW PRIORITY' else "#18181b"
            badge_bg = "#f0fdf4" if item['recommendation'] == 'HIGH PRIORITY' else "#fffbeb" if item['recommendation'] == 'INVESTIGATE' else "#fef2f2" if item['recommendation'] == 'LOW PRIORITY' else "#f4f4f5"

            with st.container():
                card_html = f"""
                <div style="background: #ffffff; border: 1px solid #e4e4e7; border-radius: 8px; padding: 16px 18px; margin-bottom: 12px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 10px; font-weight: 700; color: #71717a; text-transform: uppercase; letter-spacing: 0.05em;">Catalog Asset</span>
                            <h4 style="margin: 2px 0 0 0; color: #09090b; font-size: 14px; font-weight: 700;">{item['title']}</h4>
                        </div>
                        <span style="background: {badge_bg}; color: {badge_fg}; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; letter-spacing: 0.04em;">{item['recommendation']}</span>
                    </div>
                    <div style="color: #52525b; font-size: 12px; margin: 8px 0; line-height: 1.5;">{item['reason']}</div>
                </div>
                """
                st.markdown(clean_html(card_html), unsafe_allow_html=True)

                with st.expander(f"Telemetry Dossier for {item['title']}"):
                    m = item["metrics"]
                    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
                    col_m1.metric("Audience Sample", f"{m['viewer_count']:,}")
                    col_m2.metric("Completion Rate", f"{m['average_completion_rate']:.1f}%")
                    col_m3.metric("Session Length", f"{m['average_watch_duration']:.1f}m")
                    col_m4.metric("Friction Pauses", f"{m['average_pause_count']:.1f}")
                    col_m5.metric("30D Retention", f"{m['retention_rate']:.1%}")

                    drawer_html = f"""
                    <div style="background: #f4f4f5; border-radius: 6px; padding: 10px 12px; margin-top: 8px; font-size: 12px; color: #3f3f46; line-height: 1.5;">
                        <div>• <b>Retention Telemetry:</b> {item['retention_evidence']}</div>
                        <div style="margin-top: 3px;">• <b>Engagement Telemetry:</b> {item['engagement_evidence']}</div>
                    </div>
                    """
                    st.markdown(clean_html(drawer_html), unsafe_allow_html=True)

# =============================================================================
# TAB 6: WHAT-IF MODEL
# =============================================================================
with tab_simulator:
    render_what_if_simulator(filtered_df)

# =============================================================================
# TAB 7: SQL PARITY
# =============================================================================
with tab_sql_audit:
    render_sql_audit_workbench(filtered_df)
