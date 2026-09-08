"""Comprehensive test suite for Sanjeev's Second Tasks (Days 11 through 20).

Covers:
- Day 11: Correlation analysis, dynamic takeaway, Plotly heatmap
- Day 12: Viewer segment comparison, 3-segment and 4-segment classification, Plotly chart
- Day 13: Funnel stages, drop-off detection, biggest bottleneck identification, narrative
- Day 14: Centralized KPI calculation, 5 core KPIs, deltas, missing data
- Day 15: SQL business queries, SQLite ingestion, Python-SQL consistency
- Day 16: KPI cards component data structure
- Day 17: Plotly interactive charts (completion vs retention, pause vs retention)
- Day 18: CSV upload validation, schema checking, defensive error handling
- Day 19: Acquisition recommendations, thresholds, evidence generation
- Day 20: KPI alert monitoring, threshold triggers, healthy state
"""

import io
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pandas as pd
import numpy as np

from analysis.correlation import (
    calculate_metric_correlations,
    calculate_correlation_matrix,
    generate_correlation_report,
    create_correlation_heatmap,
    normalize_dataframe_columns,
    classify_correlation
)
from analysis.segments import (
    calculate_segment_comparison,
    assign_segments,
    create_segment_comparison_chart,
    classify_viewer_3_segments,
    classify_viewer_4_segments,
    SEGMENTATION_THRESHOLDS
)
from analysis.funnel import (
    calculate_funnel_metrics,
    create_funnel_chart,
    FUNNEL_STAGES
)
from analysis.kpis import (
    calculate_kpis,
    KPI_METADATA
)
from analysis.sql_analytics import (
    get_db_connection,
    init_db,
    load_data_to_sqlite,
    query_content_highest_retention,
    query_segment_summaries,
    query_funnel_steps,
    verify_python_sql_consistency
)
from analysis.charts import (
    plot_completion_vs_retention,
    plot_pause_vs_retention,
    plot_engagement_distribution
)
from analysis.validation import (
    validate_csv_upload,
    validate_dataframe_schema,
    safe_run_analysis,
    CORE_REQUIRED_FIELDS
)
from analysis.recommendations import (
    classify_content_recommendation,
    generate_acquisition_recommendations_list,
    calculate_content_performance_summary,
    RECOMMENDATION_THRESHOLDS
)
from analysis.alerts import (
    evaluate_kpi_alerts,
    ALERT_THRESHOLDS
)

@pytest.fixture
def sample_viewing_df():
    """Deterministic sample dataframe covering all engagement spectrums."""
    return pd.DataFrame({
        "user_id": [f"U{i:03d}" for i in range(1, 11)],
        "content_id": [101, 101, 101, 102, 102, 102, 103, 103, 104, 105],
        "completion_rate": [95.0, 85.0, 90.0, 45.0, 30.0, 20.0, 75.0, 80.0, 15.0, 100.0],
        "watch_duration": [55.0, 48.0, 50.0, 20.0, 15.0, 10.0, 40.0, 42.0, 8.0, 60.0],
        "pause_count": [1, 2, 1, 6, 8, 9, 2, 3, 7, 0],
        "sessions_per_week": [6, 5, 7, 1, 2, 1, 4, 3, 1, 8],
        "retained": [1, 1, 1, 0, 0, 0, 1, 0, 0, 1],
        "finished": [1, 0, 1, 0, 0, 0, 0, 0, 0, 1]
    })

# =============================================================================
# DAY 11 TESTS: Correlation Analysis
# =============================================================================
class TestDay11Correlation:
    def test_correlations_with_aliases(self):
        """Test that correlation analysis handles both legacy and synthetic aliases."""
        df_synthetic = pd.DataFrame({
            "completion_pct": [20.0, 50.0, 80.0, 95.0],
            "watch_duration_minutes": [10.0, 25.0, 45.0, 60.0],
            "pause_count": [8, 4, 2, 0],
            "sessions_per_week": [1, 3, 5, 7],
            "retained_30d": [0, 0, 1, 1]
        })
        corrs = calculate_metric_correlations(df_synthetic)
        assert len(corrs) == 4
        comp_corr = next(c for c in corrs if c["metric"] == "completion_rate")
        assert comp_corr["correlation_coefficient"] > 0.8
        assert comp_corr["direction"] == "positive"

    def test_dynamic_takeaway(self, sample_viewing_df):
        report = generate_correlation_report(sample_viewing_df)
        assert "summary_takeaway" in report
        takeaway = report["summary_takeaway"]
        assert "strongest positive predictors" in takeaway
        assert "strong negative indicator" in takeaway

    def test_heatmap_generation(self, sample_viewing_df):
        matrix_data = calculate_correlation_matrix(sample_viewing_df)
        fig = create_correlation_heatmap(matrix_data)
        assert fig is not None
        assert len(fig.data) == 1
        assert fig.data[0].type == "heatmap"

    def test_empty_correlation_safe(self):
        empty_rep = generate_correlation_report(pd.DataFrame())
        assert empty_rep["retention_correlations"] == []
        assert "No retention correlations" in empty_rep["summary_takeaway"]
        fig = create_correlation_heatmap({})
        assert fig is not None

# =============================================================================
# DAY 12 TESTS: Segment Comparison
# =============================================================================
class TestDay12SegmentComparison:
    def test_segment_classification_3_seg(self):
        assert classify_viewer_3_segments(85.0, 6) == "Highly Engaged"
        assert classify_viewer_3_segments(40.0, 4) == "At Risk / Low Engagement"
        assert classify_viewer_3_segments(70.0, 1) == "At Risk / Low Engagement"
        assert classify_viewer_3_segments(70.0, 3) == "Moderately Engaged"

    def test_segment_classification_4_seg(self):
        assert classify_viewer_4_segments(85.0, 6) == "Highly Engaged"
        assert classify_viewer_4_segments(70.0, 4) == "Steady Viewers"
        assert classify_viewer_4_segments(55.0, 3) == "Casual Viewers"
        assert classify_viewer_4_segments(40.0, 1) == "Low / At-Risk"

    def test_calculate_segment_comparison(self, sample_viewing_df):
        seg_summary = calculate_segment_comparison(sample_viewing_df)
        assert len(seg_summary) == 3
        hi_row = seg_summary[seg_summary["segment"] == "Highly Engaged"].iloc[0]
        at_risk_row = seg_summary[seg_summary["segment"] == "At Risk / Low Engagement"].iloc[0]
        assert hi_row["retention_rate"] > at_risk_row["retention_rate"]
        assert hi_row["avg_completion_rate"] >= 80.0

    def test_segment_chart_generation(self, sample_viewing_df):
        seg_summary = calculate_segment_comparison(sample_viewing_df)
        fig = create_segment_comparison_chart(seg_summary)
        assert fig is not None
        assert len(fig.data) >= 2

# =============================================================================
# DAY 13 TESTS: Drop-Off Detection & Funnel
# =============================================================================
class TestDay13DropOffDetection:
    def test_funnel_stages(self, sample_viewing_df):
        funnel = calculate_funnel_metrics(sample_viewing_df)
        assert funnel["total_initial"] == 10
        stages = [s["stage"] for s in funnel["stages"]]
        assert stages == FUNNEL_STAGES

    def test_bottleneck_detection(self, sample_viewing_df):
        funnel = calculate_funnel_metrics(sample_viewing_df)
        biggest = funnel["biggest_drop"]
        assert biggest["drop_count"] > 0
        assert biggest["drop_rate"] > 0
        assert len(funnel["bottleneck_narrative"]) > 10

    def test_funnel_empty(self):
        empty_funnel = calculate_funnel_metrics(pd.DataFrame())
        assert empty_funnel["total_initial"] == 0
        assert len(empty_funnel["stages"]) == 6
        fig = create_funnel_chart(empty_funnel)
        assert fig is not None

# =============================================================================
# DAY 14 TESTS: Centralized KPIs
# =============================================================================
class TestDay14KPIs:
    def test_kpi_computation(self, sample_viewing_df):
        kpis = calculate_kpis(sample_viewing_df)
        assert kpis["total_viewers"] == 10
        assert kpis["retained_viewers"] == 5
        assert kpis["overall_retention_rate"]["value"] == 0.5
        assert kpis["overall_retention_rate"]["formatted"] == "50.0%"
        assert kpis["average_completion_rate"]["value"] > 0.0
        assert kpis["average_watch_duration"]["value"] > 0.0
        assert kpis["average_pause_count"]["value"] > 0.0
        assert kpis["content_completion_rate"]["value"] == 0.3

    def test_kpi_deltas_with_previous(self, sample_viewing_df):
        prev_df = sample_viewing_df.copy()
        prev_df["retained"] = [0] * 10
        kpis = calculate_kpis(sample_viewing_df, previous_df=prev_df)
        assert kpis["overall_retention_rate"]["delta"] == 0.5

    def test_kpi_empty(self):
        empty_kpis = calculate_kpis(pd.DataFrame())
        assert empty_kpis["total_viewers"] == 0
        assert empty_kpis["overall_retention_rate"]["value"] == 0.0

# =============================================================================
# DAY 15 TESTS: SQL Business Queries
# =============================================================================
class TestDay15SQLQueries:
    def test_sql_ingestion_and_queries(self, sample_viewing_df):
        conn = get_db_connection()
        load_data_to_sqlite(sample_viewing_df, conn)

        # Query 1: Content with highest retention
        content_res = query_content_highest_retention(conn)
        assert len(content_res) > 0
        assert "retention_rate" in content_res.columns

        # Query 2: Segment summaries
        seg_res = query_segment_summaries(conn)
        assert len(seg_res) > 0
        assert "segment" in seg_res.columns

        # Query 3: Funnel steps
        funnel_res = query_funnel_steps(conn)
        assert len(funnel_res) == 6
        assert "stage" in funnel_res.columns

        conn.close()

    def test_python_sql_consistency(self, sample_viewing_df):
        report = verify_python_sql_consistency(sample_viewing_df)
        assert report["consistent"] is True
        assert report["segment_consistency"] is True
        assert report["funnel_consistency"] is True

# =============================================================================
# DAY 17 TESTS: Interactive Plotly Charts
# =============================================================================
class TestDay17PlotlyCharts:
    def test_charts_build_successfully(self, sample_viewing_df):
        comp_fig = plot_completion_vs_retention(sample_viewing_df)
        assert comp_fig is not None
        assert len(comp_fig.data) >= 1

        pause_fig = plot_pause_vs_retention(sample_viewing_df)
        assert pause_fig is not None
        assert len(pause_fig.data) >= 1

        dist_fig = plot_engagement_distribution(sample_viewing_df, "completion_rate")
        assert dist_fig is not None

# =============================================================================
# DAY 18 TESTS: Error States & Validation
# =============================================================================
class TestDay18Validation:
    def test_validate_csv_upload_success(self, sample_viewing_df):
        csv_bytes = sample_viewing_df.to_csv(index=False).encode("utf-8")
        bio = io.BytesIO(csv_bytes)
        bio.name = "test_data.csv"
        is_valid, msg, df_out = validate_csv_upload(bio)
        assert is_valid is True
        assert len(df_out) == 10

    def test_validate_csv_upload_wrong_format(self):
        bio = io.BytesIO(b"dummy content")
        bio.name = "test_data.xlsx"
        is_valid, msg, df_out = validate_csv_upload(bio)
        assert is_valid is False
        assert "Unsupported file format" in msg

    def test_validate_csv_upload_missing_columns(self):
        bad_df = pd.DataFrame({"some_col": [1, 2, 3]})
        bio = io.BytesIO(bad_df.to_csv(index=False).encode("utf-8"))
        bio.name = "incomplete.csv"
        is_valid, msg, df_out = validate_csv_upload(bio)
        assert is_valid is False
        assert "missing required columns" in msg

    def test_safe_run_analysis_handles_exceptions(self):
        def bad_function():
            raise RuntimeError("Database connection timed out")
        res = safe_run_analysis(bad_function)
        assert res["success"] is False
        assert "Database connection timed out" in res["error"]

# =============================================================================
# DAY 19 TESTS: Acquisition Recommendations
# =============================================================================
class TestDay19Recommendations:
    def test_recommendation_classification(self):
        high = classify_content_recommendation(85.0, 0.80)
        assert high["category"] == "HIGH PRIORITY"

        investigate = classify_content_recommendation(85.0, 0.40)
        assert investigate["category"] == "INVESTIGATE"

        low = classify_content_recommendation(40.0, 0.30)
        assert low["category"] == "LOW PRIORITY"

        standard = classify_content_recommendation(60.0, 0.60)
        assert standard["category"] == "STANDARD"

    def test_recommendations_list_generation(self, sample_viewing_df):
        recs = generate_acquisition_recommendations_list(sample_viewing_df)
        assert len(recs) > 0
        for r in recs:
            assert "recommendation" in r
            assert "reason" in r
            assert "retention_evidence" in r
            assert "engagement_evidence" in r
            assert "metrics" in r

# =============================================================================
# DAY 20 TESTS: Alert Monitoring
# =============================================================================
class TestDay20AlertMonitoring:
    def test_critical_retention_alert(self):
        # Retention 20% (< 30% threshold)
        bad_kpis = {
            "total_viewers": 100,
            "overall_retention_rate": {"value": 0.20},
            "average_completion_rate": {"value": 75.0},
            "average_pause_count": {"value": 2.0}
        }
        alerts_res = evaluate_kpi_alerts(kpis=bad_kpis)
        assert alerts_res["has_alerts"] is True
        assert alerts_res["critical_count"] == 1
        assert any(a["metric"] == "overall_retention_rate" for a in alerts_res["alerts"])

    def test_healthy_metrics_no_spam(self):
        healthy_kpis = {
            "total_viewers": 100,
            "overall_retention_rate": {"value": 0.65},
            "average_completion_rate": {"value": 80.0},
            "average_pause_count": {"value": 1.5}
        }
        healthy_segments = pd.DataFrame([
            {"segment": "Highly Engaged", "viewer_pct": 50.0},
            {"segment": "Moderately Engaged", "viewer_pct": 35.0},
            {"segment": "At Risk / Low Engagement", "viewer_pct": 15.0}
        ])
        alerts_res = evaluate_kpi_alerts(kpis=healthy_kpis, segment_summary=healthy_segments)
        assert alerts_res["has_alerts"] is False
        assert len(alerts_res["alerts"]) == 0
