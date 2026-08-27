import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from starlette.testclient import TestClient
from main import app

from analysis import (
    clean_viewing_data,
    get_data_diagnostics,
    calculate_engagement_metrics,
    calculate_retention_analysis,
    segment_viewers,
    calculate_content_performance,
    generate_acquisition_recommendations,
    calculate_metric_distribution,
    calculate_all_distributions,
    calculate_metric_correlations,
    calculate_correlation_matrix,
    generate_correlation_report,
    classify_skewness,
    classify_correlation,
    COLUMN_MAPPING
)

def test_distributions_unit():
    """Unit test for distribution functions."""
    # Test on synthetic normal-like and skewed data
    s1 = pd.Series([10, 20, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    res1 = calculate_metric_distribution(s1, "test_metric", bins=5)
    assert res1["count"] == 11
    assert res1["min"] == 10.0
    assert res1["max"] == 100.0
    assert res1["range"] == 90.0
    assert res1["median"] == 50.0
    assert res1["mean"] == round(s1.mean(), 4)
    assert 20.0 in res1["mode"]
    assert len(res1["histogram"]) == 5

    # Outlier test
    s_out = pd.Series([10, 11, 12, 10, 11, 12, 10, 11, 12, 1000])
    res_out = calculate_metric_distribution(s_out, "outlier_metric")
    assert res_out["outlier_count"] == 1
    assert 1000.0 in res_out["outliers"]

    # Empty series test
    res_empty = calculate_metric_distribution(pd.Series([], dtype=float), "empty")
    assert res_empty["count"] == 0
    assert res_empty["mean"] == 0.0
    assert res_empty["outliers"] == []

    # Skewness classification test
    assert classify_skewness(1.5) == "highly positive (right-skewed)"
    assert classify_skewness(0.7) == "moderately positive (right-skewed)"
    assert classify_skewness(-1.2) == "highly negative (left-skewed)"
    assert classify_skewness(-0.6) == "moderately negative (left-skewed)"
    assert classify_skewness(0.1) == "approximately symmetric"

def test_correlations_unit():
    """Unit test for correlation functions."""
    # Synthetic DataFrame
    data = {
        "completion_rate": [20, 40, 60, 80, 100],
        "watch_duration": [10, 25, 35, 50, 70],
        "pause_count": [8, 6, 4, 2, 0],
        "sessions_per_week": [1, 2, 4, 5, 7],
        "retained": [False, False, True, True, True]
    }
    df = pd.DataFrame(data)

    ret_corrs = calculate_metric_correlations(df)
    assert len(ret_corrs) == 4
    for item in ret_corrs:
        assert "metric" in item
        assert "correlation_coefficient" in item
        assert "direction" in item
        assert "strength" in item
        assert "interpretation" in item

    # Check that completion_rate is positively correlated and pause_count is negatively correlated
    comp_corr = next(c for c in ret_corrs if c["metric"] == "completion_rate")
    pause_corr = next(c for c in ret_corrs if c["metric"] == "pause_count")
    assert comp_corr["correlation_coefficient"] > 0.8
    assert comp_corr["direction"] == "positive"
    assert pause_corr["correlation_coefficient"] < -0.8
    assert pause_corr["direction"] == "negative"

    # Correlation matrix test
    mat = calculate_correlation_matrix(df)
    assert "completion_rate" in mat["columns"]
    assert "retained" in mat["columns"]
    assert len(mat["matrix"]) == 5
    assert len(mat["matrix"][0]) == 5
    assert len(mat["heatmap"]) == 25
    assert len(mat["ascii_heatmap"]) > 0

    # Test correlation classification
    dir_pos, str_pos = classify_correlation(0.85)
    assert dir_pos == "positive"
    assert str_pos == "very strong positive"

    dir_neg, str_neg = classify_correlation(-0.804)
    assert dir_neg == "negative"
    assert str_neg == "very strong negative"

    # Empty df handling
    assert calculate_metric_correlations(pd.DataFrame()) == []
    assert calculate_correlation_matrix(pd.DataFrame())["columns"] == []

def test_actual_dataset_analytics():
    """Verify Day 11 analysis results against actual project dataset."""
    raw_df = pd.read_csv("data/viewing_data.csv")
    df = clean_viewing_data(raw_df)

    assert len(df) == 70

    # 1. Distributions verification
    dist_res = calculate_all_distributions(df)
    assert dist_res["total_records"] == 70
    dists = dist_res["distributions"]
    assert "completion_rate" in dists
    assert "watch_duration" in dists
    assert "pause_count" in dists
    assert "sessions_per_week" in dists

    # Verify completion_rate stats
    cr = dists["completion_rate"]
    assert cr["min"] == 8.0
    assert cr["max"] == 100.0
    assert cr["range"] == 92.0
    assert round(cr["mean"], 2) == 71.64
    assert cr["median"] == 79.5
    assert 100.0 in cr["mode"]
    assert cr["skewness"] < 0  # Left-skewed
    assert cr["skewness_classification"] == "moderately negative (left-skewed)"

    # Verify watch_duration stats
    wd = dists["watch_duration"]
    assert wd["min"] == 8.0
    assert wd["max"] == 84.0
    assert wd["range"] == 76.0
    assert round(wd["mean"], 2) == 39.79
    assert wd["median"] == 38.0
    assert wd["skewness"] > 0  # Right-skewed

    # Verify pause_count stats
    pc = dists["pause_count"]
    assert pc["min"] == 0
    assert pc["max"] == 9
    assert pc["range"] == 9
    assert round(pc["mean"], 2) == 3.46
    assert pc["median"] == 3.0
    assert 2.0 in pc["mode"]

    # 2. Correlations verification
    corr_report = generate_correlation_report(df)
    ret_corrs = {item["metric"]: item["correlation_coefficient"] for item in corr_report["retention_correlations"]}

    # Verify actual calculated correlation values
    assert round(ret_corrs["completion_rate"], 2) == 0.86
    assert round(ret_corrs["sessions_per_week"], 2) == 0.84
    assert round(ret_corrs["watch_duration"], 2) == 0.79
    assert round(ret_corrs["pause_count"], 2) == -0.80

    print("\nActual Retention Correlations:")
    for metric, r in ret_corrs.items():
        print(f"  {metric:<20} r = {r:+.4f}")

def test_api_endpoints():
    """Test all FastAPI endpoints including existing and newly added Day 11 endpoints."""
    client = TestClient(app)

    # 1. Existing endpoints
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"

    r = client.get("/api/data/summary")
    assert r.status_code == 200
    assert r.json()["total_records"] == 71

    r = client.get("/api/viewing-data")
    assert r.status_code == 200
    assert len(r.json()) == 70

    r = client.get("/api/analytics/engagement")
    assert r.status_code == 200
    assert round(r.json()["average_watch_duration"], 2) == 39.79

    r = client.get("/api/analytics/retention")
    assert r.status_code == 200
    assert r.json()["retained"]["count"] == 42
    assert r.json()["non_retained"]["count"] == 28

    r = client.get("/api/analytics/segments")
    assert r.status_code == 200
    assert len(r.json()) == 3

    r = client.get("/api/analytics/content-performance")
    assert r.status_code == 200
    assert len(r.json()) > 0

    r = client.get("/api/analytics/recommendations")
    assert r.status_code == 200
    assert len(r.json()) > 0

    # 2. New Day 11 endpoints
    r = client.get("/api/analytics/distributions")
    assert r.status_code == 200
    d_data = r.json()
    assert "distributions" in d_data
    assert "completion_rate" in d_data["distributions"]
    assert "watch_duration" in d_data["distributions"]
    assert "pause_count" in d_data["distributions"]
    assert "sessions_per_week" in d_data["distributions"]

    r = client.get("/api/analytics/correlation")
    assert r.status_code == 200
    c_data = r.json()
    assert "retention_correlations" in c_data
    assert "correlation_matrix" in c_data
    assert "summary_takeaway" in c_data
    assert len(c_data["retention_correlations"]) == 4

    r = client.get("/api/analytics/correlation/matrix")
    assert r.status_code == 200
    m_data = r.json()
    assert "columns" in m_data
    assert "matrix" in m_data
    assert "heatmap" in m_data
    assert "ascii_heatmap" in m_data
    assert len(m_data["matrix"]) == 5
    assert len(m_data["heatmap"]) == 25

    print("\nAll API endpoints verified successfully!")

def test_edge_cases_and_robustness():
    """Verify that edge cases (constant series, NaNs, infinities, single rows) do not crash analytics."""
    # 1. Constant series (zero variance)
    df_const = pd.DataFrame({
        "completion_rate": [50.0, 50.0, 50.0],
        "watch_duration": [30.0, 30.0, 30.0],
        "pause_count": [2, 2, 2],
        "sessions_per_week": [4, 4, 4],
        "retained": [True, True, True]
    })
    d_const = calculate_all_distributions(df_const)
    assert d_const["distributions"]["completion_rate"]["std"] == 0.0
    assert d_const["distributions"]["completion_rate"]["skewness"] == 0.0

    c_const = calculate_metric_correlations(df_const)
    assert len(c_const) == 4
    for c in c_const:
        assert c["correlation_coefficient"] == 0.0

    mat_const = calculate_correlation_matrix(df_const)
    assert len(mat_const["matrix"]) == 5

    # 2. DataFrame with NaNs and infinities
    df_nan = pd.DataFrame({
        "completion_rate": [10.0, np.nan, np.inf, 90.0],
        "watch_duration": [-np.inf, 20.0, 40.0, np.nan],
        "pause_count": [1, 2, np.nan, 5],
        "sessions_per_week": [1, np.nan, 3, 5],
        "retained": [True, False, True, False]
    })
    d_nan = calculate_all_distributions(df_nan)
    assert d_nan["distributions"]["completion_rate"]["count"] == 2
    assert d_nan["distributions"]["watch_duration"]["count"] == 2

    c_nan = calculate_metric_correlations(df_nan)
    assert len(c_nan) == 4

    print("\nEdge cases and robustness verified successfully!")

if __name__ == "__main__":
    test_distributions_unit()
    test_correlations_unit()
    test_actual_dataset_analytics()
    test_api_endpoints()
    test_edge_cases_and_robustness()
    print("\nALL DAY 11 TESTS PASSED SUCCESSFULLY!")

