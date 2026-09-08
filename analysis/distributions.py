import numpy as np
import pandas as pd

# Schema mapping dictionary to document standard names vs dataset column names
COLUMN_MAPPING = {
    "completion_rate": "completion_pct / completion rate",
    "watch_duration": "watch_duration / watch_duration_min",
    "pause_count": "pause_count",
    "sessions_per_week": "sessions_per_week"
}

def classify_skewness(skew_val: float) -> str:
    """Classify the direction and severity of distribution skewness."""
    if pd.isna(skew_val):
        return "undefined"
    if skew_val > 1.0:
        return "highly positive (right-skewed)"
    elif skew_val > 0.5:
        return "moderately positive (right-skewed)"
    elif skew_val < -1.0:
        return "highly negative (left-skewed)"
    elif skew_val < -0.5:
        return "moderately negative (left-skewed)"
    else:
        return "approximately symmetric"

def calculate_metric_distribution(series: pd.Series, metric_name: str = "", bins: int = 5) -> dict:
    """Calculate descriptive statistics, central tendency, dispersion, skewness,
    outliers, and histogram bins for a given numeric metric series.
    """
    clean_series = pd.to_numeric(series, errors="coerce").dropna()
    clean_series = clean_series.replace([np.inf, -np.inf], np.nan).dropna()

    if clean_series.empty:
        return {
            "metric": metric_name,
            "display_name": COLUMN_MAPPING.get(metric_name, metric_name),
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "mode": [],
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "range": 0.0,
            "q25": 0.0,
            "q75": 0.0,
            "iqr": 0.0,
            "skewness": 0.0,
            "skewness_classification": "undefined",
            "outlier_bounds": {"lower": 0.0, "upper": 0.0},
            "outliers": [],
            "outlier_count": 0,
            "histogram": []
        }

    count = int(len(clean_series))
    mean_val = float(clean_series.mean())
    median_val = float(clean_series.median())
    std_val = float(clean_series.std()) if count > 1 else 0.0
    min_val = float(clean_series.min())
    max_val = float(clean_series.max())
    range_val = float(max_val - min_val)

    # Mode calculation
    mode_series = clean_series.mode()
    modes = [float(m) for m in mode_series.tolist()] if not mode_series.empty else []

    # Quantiles & IQR
    q25 = float(clean_series.quantile(0.25))
    q75 = float(clean_series.quantile(0.75))
    iqr = float(q75 - q25)

    # Outliers via 1.5x IQR method
    lower_bound = float(q25 - 1.5 * iqr)
    upper_bound = float(q75 + 1.5 * iqr)
    outlier_values = clean_series[(clean_series < lower_bound) | (clean_series > upper_bound)].tolist()
    outliers = [float(v) for v in outlier_values]

    # Skewness
    if count > 2 and std_val > 0:
        skew_val = float(clean_series.skew())
    else:
        skew_val = 0.0
    skew_class = classify_skewness(skew_val)

    # Histogram generation
    histogram = []
    if range_val > 0 and bins > 0:
        counts, bin_edges = np.histogram(clean_series, bins=bins)
        for i in range(len(counts)):
            low = float(bin_edges[i])
            high = float(bin_edges[i + 1])
            b_count = int(counts[i])
            pct = round((b_count / count * 100), 2)
            histogram.append({
                "bin_index": i + 1,
                "range_min": round(low, 2),
                "range_max": round(high, 2),
                "label": f"{low:.1f} - {high:.1f}",
                "count": b_count,
                "percentage": pct
            })
    elif count > 0:
        histogram.append({
            "bin_index": 1,
            "range_min": round(min_val, 2),
            "range_max": round(max_val, 2),
            "label": f"{min_val:.1f} - {max_val:.1f}",
            "count": count,
            "percentage": 100.0
        })

    return {
        "metric": metric_name,
        "display_name": COLUMN_MAPPING.get(metric_name, metric_name),
        "count": count,
        "mean": round(mean_val, 4),
        "median": round(median_val, 4),
        "mode": modes,
        "std": round(std_val, 4),
        "min": round(min_val, 4),
        "max": round(max_val, 4),
        "range": round(range_val, 4),
        "q25": round(q25, 4),
        "q75": round(q75, 4),
        "iqr": round(iqr, 4),
        "skewness": round(skew_val, 4),
        "skewness_classification": skew_class,
        "outlier_bounds": {
            "lower": round(lower_bound, 4),
            "upper": round(upper_bound, 4)
        },
        "outliers": outliers,
        "outlier_count": len(outliers),
        "histogram": histogram
    }

def calculate_all_distributions(df: pd.DataFrame, bins: int = 5) -> dict:
    """Analyze distributions across all key engagement metrics in the dataset."""
    if df.empty:
        return {
            "total_records": 0,
            "column_mapping": COLUMN_MAPPING,
            "distributions": {}
        }

    target_columns = ["completion_rate", "watch_duration", "pause_count", "sessions_per_week"]
    distributions = {}

    for col in target_columns:
        if col in df.columns:
            distributions[col] = calculate_metric_distribution(df[col], metric_name=col, bins=bins)

    return {
        "total_records": len(df),
        "column_mapping": COLUMN_MAPPING,
        "distributions": distributions
    }
