import numpy as np
import pandas as pd

# Core engagement metrics to correlate with retention
ENGAGEMENT_METRICS = [
    "completion_rate",
    "watch_duration",
    "pause_count",
    "sessions_per_week"
]

COLUMN_ALIASES = {
    "completion_pct": "completion_rate",
    "watch_duration_minutes": "watch_duration",
    "watch_duration_min": "watch_duration",
    "retained_30d": "retained",
    "retention": "retained",
}

METRIC_LABELS = {
    "completion_rate": "Completion Rate (%)",
    "watch_duration": "Watch Duration (mins)",
    "pause_count": "Pause Count",
    "sessions_per_week": "Sessions Per Week",
    "retained": "User Retention (Boolean/Binary)",
    "completion_pct": "Completion Rate (%)",
    "watch_duration_minutes": "Watch Duration (mins)",
    "watch_duration_min": "Watch Duration (mins)",
    "retained_30d": "User Retention (Boolean/Binary)",
    "retention": "User Retention (Boolean/Binary)",
}

def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize project column names (e.g. completion_pct -> completion_rate) and coerce types safely."""
    if df.empty:
        return df.copy()
    rename_dict = {col: COLUMN_ALIASES[col] for col in df.columns if col in COLUMN_ALIASES and COLUMN_ALIASES[col] not in df.columns}
    out_df = df.rename(columns=rename_dict).copy()

    # Sanitize numeric columns (coerces strings like "unknown", "three", "N/A" to NaN)
    for col in ["completion_rate", "watch_duration", "pause_count", "sessions_per_week"]:
        if col in out_df.columns:
            out_df[col] = pd.to_numeric(out_df[col], errors="coerce")

    # Sanitize retained column
    if "retained" in out_df.columns:
        bool_map = {
            True: 1, False: 0, 1: 1, 0: 0, "1": 1, "0": 0,
            "true": 1, "false": 0, "yes": 1, "no": 0, "y": 1, "n": 0
        }
        if out_df["retained"].dtype == object or str(out_df["retained"].dtype).startswith("string"):
            mapped = out_df["retained"].astype(str).str.strip().str.lower().map(bool_map)
            out_df["retained"] = mapped
        out_df["retained"] = pd.to_numeric(out_df["retained"], errors="coerce").fillna(0).astype(int)

    return out_df

def to_user_level(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse a normalized session-grain DataFrame to one row per user.

    Retention is a user-level outcome (AGENTS context section 8): computing it
    at session grain over-weights heavy viewers. Engagement metrics become
    per-user means, sessions_per_week keeps the per-user derived value, and
    `retained` keeps the user's (latest) outcome. Frames without `user_id`
    are returned unchanged — one row is already presumed one viewer.
    """
    if df.empty or "user_id" not in df.columns:
        return df.copy()

    agg_map = {}
    for col in ["completion_rate", "watch_duration", "pause_count"]:
        if col in df.columns:
            agg_map[col] = (col, "mean")
    if "sessions_per_week" in df.columns:
        agg_map["sessions_per_week"] = ("sessions_per_week", "first")
    if "retained" in df.columns:
        agg_map["retained"] = ("retained", "max")
    if "finished" in df.columns:
        agg_map["finished"] = ("finished", "max")
    if not agg_map:
        return df.drop_duplicates(subset=["user_id"]).copy()

    user_df = df.groupby("user_id", as_index=False).agg(**agg_map)
    if "content_id" in df.columns:
        # representative content affiliation (first) + distinct title count
        user_df = user_df.merge(
            df.groupby("user_id", as_index=False)
              .agg(representative_content_id=("content_id", "first"),
                   distinct_titles=("content_id", "nunique")),
            on="user_id", how="left"
        )
        user_df = user_df.rename(columns={"representative_content_id": "content_id"})
    return user_df

def classify_correlation(r: float) -> tuple[str, str]:
    """Classify correlation coefficient into direction and strength."""
    if pd.isna(r):
        return "undefined", "No correlation (zero variance or undefined)"

    direction = "positive" if r > 0 else "negative" if r < 0 else "neutral"
    abs_r = abs(r)

    if abs_r >= 0.80:
        strength = f"very strong {direction}"
    elif abs_r >= 0.60:
        strength = f"strong {direction}"
    elif abs_r >= 0.40:
        strength = f"moderate {direction}"
    elif abs_r >= 0.20:
        strength = f"weak {direction}"
    else:
        strength = f"very weak / negligible {direction}"

    return direction, strength

def generate_relationship_insight(metric: str, r: float) -> str:
    """Generate plain-language interpretation based on the calculated correlation."""
    if pd.isna(r):
        return f"Correlation between {metric} and retention could not be determined due to lack of variance."

    abs_r = abs(r)
    label = METRIC_LABELS.get(metric, metric)

    if metric == "completion_rate":
        if r > 0.6:
            return (
                f"Very strong positive correlation (r = {r:.4f}). Viewers who complete a higher percentage "
                f"of their content are overwhelmingly more likely to remain active subscribers."
            )
        elif r > 0:
            return f"Positive correlation (r = {r:.4f}). Higher completion rate is positively associated with retention."
        else:
            return f"Negative or unexpected correlation (r = {r:.4f}) between completion rate and retention."

    elif metric == "watch_duration":
        if r > 0.6:
            return (
                f"Strong positive correlation (r = {r:.4f}). Longer watch times per session indicate higher "
                f"viewer investment and strongly correlate with long-term user retention."
            )
        elif r > 0:
            return f"Positive correlation (r = {r:.4f}). Watch duration shows a positive association with retention."
        else:
            return f"Negative correlation (r = {r:.4f}) between watch duration and retention."

    elif metric == "pause_count":
        if r < -0.6:
            return (
                f"Strong negative correlation (r = {r:.4f}). High pause frequency is a strong indicator of "
                f"viewer friction, disinterest, or distraction, strongly correlating with user churn."
            )
        elif r < 0:
            return f"Negative correlation (r = {r:.4f}). Higher pause frequency is associated with lower retention."
        else:
            return f"Positive correlation (r = {r:.4f}) between pause count and retention."

    elif metric == "sessions_per_week":
        if r > 0.6:
            return (
                f"Strong positive correlation (r = {r:.4f}). High weekly viewing cadence is one of the strongest "
                f"predictors of sustained user retention and platform habit formation."
            )
        elif r > 0:
            return f"Positive correlation (r = {r:.4f}). Frequent weekly sessions are positively associated with retention."
        else:
            return f"Negative correlation (r = {r:.4f}) between sessions per week and retention."

    return f"Correlation between {label} and retention is r = {r:.4f} ({classify_correlation(r)[1]})."

def calculate_metric_correlations(df: pd.DataFrame) -> list:
    """Calculate correlation between each available engagement metric and retention."""
    if df.empty:
        return []

    clean_df = normalize_dataframe_columns(df)
    if "retained" not in clean_df.columns:
        return []

    # Prepare DataFrame with retained coerced to numeric integer (1/0)
    clean_df = clean_df.copy()
    clean_df["retained_numeric"] = pd.to_numeric(clean_df["retained"], errors="coerce").fillna(0).astype(int)

    results = []
    for metric in ENGAGEMENT_METRICS:
        if metric not in clean_df.columns:
            continue

        valid_data = clean_df[[metric, "retained_numeric"]].dropna()
        if len(valid_data) < 2 or valid_data[metric].std() == 0 or valid_data["retained_numeric"].std() == 0:
            r_val = 0.0
        else:
            r_val = float(valid_data[metric].corr(valid_data["retained_numeric"]))
            if pd.isna(r_val) or np.isinf(r_val):
                r_val = 0.0

        direction, strength = classify_correlation(r_val)
        insight = generate_relationship_insight(metric, r_val)

        results.append({
            "metric": metric,
            "metric_label": METRIC_LABELS.get(metric, metric),
            "target": "retained",
            "target_label": METRIC_LABELS.get("retained", "retained"),
            "correlation_coefficient": round(r_val, 4),
            "direction": direction,
            "strength": strength,
            "interpretation": insight
        })

    return results

def calculate_correlation_matrix(df: pd.DataFrame) -> dict:
    """Calculate full pairwise correlation matrix across all engagement features and retention,

    returning structured matrix, heatmap coordinates, and text representation.
    """
    if df.empty:
        return {
            "columns": [],
            "labels": [],
            "matrix": [],
            "heatmap": [],
            "ascii_heatmap": ""
        }

    norm_df = normalize_dataframe_columns(df)

    # Select existing columns
    columns = [col for col in ENGAGEMENT_METRICS if col in norm_df.columns]
    if "retained" in norm_df.columns:
        columns.append("retained")

    clean_df = norm_df[columns].copy()
    if "retained" in clean_df.columns:
        clean_df["retained"] = clean_df["retained"].astype(int)

    # Sanitize numeric columns
    for col in clean_df.columns:
        clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce").replace([np.inf, -np.inf], np.nan)

    # Compute correlation matrix safely
    corr_df = clean_df.corr(method="pearson").fillna(0.0).replace([np.inf, -np.inf], 0.0)


    # Format 2D matrix
    matrix_data = []
    heatmap_data = []
    labels = [METRIC_LABELS.get(col, col) for col in corr_df.columns]

    for y_idx, row_col in enumerate(corr_df.index):
        row_values = []
        for x_idx, col_name in enumerate(corr_df.columns):
            val = float(corr_df.loc[row_col, col_name])
            val_rounded = round(val, 4)
            row_values.append(val_rounded)
            heatmap_data.append({
                "x_metric": col_name,
                "x_label": METRIC_LABELS.get(col_name, col_name),
                "y_metric": row_col,
                "y_label": METRIC_LABELS.get(row_col, row_col),
                "correlation": val_rounded
            })
        matrix_data.append(row_values)

    # Generate ASCII heatmap for quick viewing
    header = f"{'Metric':<20}" + "".join([f"{col[:6]:>9}" for col in corr_df.columns])
    lines = [header, "-" * len(header)]
    for row_col in corr_df.index:
        line = f"{row_col:<20}"
        for col_name in corr_df.columns:
            val = corr_df.loc[row_col, col_name]
            line += f"{val:>9.4f}"
        lines.append(line)
    ascii_heatmap = "\n".join(lines)

    return {
        "columns": list(corr_df.columns),
        "labels": labels,
        "matrix": matrix_data,
        "heatmap": heatmap_data,
        "ascii_heatmap": ascii_heatmap
    }

def generate_correlation_report(df: pd.DataFrame) -> dict:
    """Generate an end-to-end correlation analysis payload combining individual retention

    correlations, full matrix, and strategic acquisition takeaways.
    """
    metric_correlations = calculate_metric_correlations(df)
    matrix_data = calculate_correlation_matrix(df)

    # Key acquisition takeaway summarizing the findings (derived from computed correlations)
    if metric_correlations:
        pos = sorted(
            (c for c in metric_correlations if c["correlation_coefficient"] > 0),
            key=lambda c: c["correlation_coefficient"],
            reverse=True,
        )
        neg = sorted(
            (c for c in metric_correlations if c["correlation_coefficient"] < 0),
            key=lambda c: c["correlation_coefficient"],
        )

        parts = []
        if pos:
            top_pos = pos[:2]
            parts.append(
                f"{top_pos[0]['metric_label']} (r = {top_pos[0]['correlation_coefficient']:.4f})"
                + (
                    f" and {top_pos[1]['metric_label']} (r = {top_pos[1]['correlation_coefficient']:.4f})"
                    if len(top_pos) > 1
                    else ""
                )
                + " are the strongest positive predictors of user retention."
            )
        if neg:
            top_neg = neg[0]
            parts.append(
                f"Conversely, {top_neg['metric_label']} (r = {top_neg['correlation_coefficient']:.4f}) is a strong negative indicator signaling content disengagement."
            )

        takeaway = " ".join(parts) or "No meaningful retention correlations could be determined from the available data."
    else:
        takeaway = "No retention correlations could be calculated from the available data."

    return {
        "retention_correlations": metric_correlations,
        "correlation_matrix": matrix_data,
        "summary_takeaway": takeaway
    }

def create_correlation_heatmap(matrix_data: dict):
    """Build an interactive Plotly heatmap figure from calculate_correlation_matrix output."""
    import plotly.graph_objects as go

    if not matrix_data or not matrix_data.get("matrix"):
        fig = go.Figure()
        fig.update_layout(
            title="Correlation Matrix (No Data Available)",
            annotations=[{
                "text": "Insufficient data to compute correlation matrix",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 14}
            }]
        )
        return fig

    labels = matrix_data.get("labels", matrix_data.get("columns", []))
    z_values = matrix_data["matrix"]

    # Text annotations for cells
    text_values = [[f"{val:.2f}" for val in row] for row in z_values]

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=labels,
        y=labels,
        text=text_values,
        texttemplate="%{text}",
        textfont={"size": 12, "color": "white"},
        colorscale="RdBu_r",
        zmin=-1.0,
        zmax=1.0,
        colorbar={"title": "Pearson r"}
    ))

    fig.update_layout(
        title="<b>Pearson Correlation Heatmap: Viewer Metrics vs Retention</b><br><span style='font-size:12px;color:#64748b'>Values closer to +1.0 indicate strong retention predictors; negative values indicate churn friction</span>",
        xaxis={"tickangle": -25},
        yaxis={"autorange": "reversed"},
        template="plotly_white",
        font_family="Inter, -apple-system, sans-serif",
        hoverlabel=dict(bgcolor="#ffffff", font_size=12, font_family="Inter, sans-serif", bordercolor="#e2e8f0"),
        margin={"l": 80, "r": 50, "t": 75, "b": 90},
        height=480
    )
    return fig
