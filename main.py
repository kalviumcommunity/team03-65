import json
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException

# Import cleaning and analytical functions from the analysis module
from analysis import (
    clean_viewing_data,
    get_data_diagnostics,
    calculate_engagement_metrics,
    calculate_retention_analysis,
    segment_viewers,
    calculate_content_performance,
    generate_acquisition_recommendations
)

app = FastAPI(
    title="Streaming Retention & Content Acquisition API",
    description="Analytics backend correlating viewer engagement behavior to retention outcomes.",
    version="1.0.0"
)

DATA_FILE = Path(__file__).parent / "data" / "viewing_data.csv"

def load_raw_dataframe() -> pd.DataFrame:
    """Helper to load the raw CSV dataset safely."""
    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="Data file viewing_data.csv not found.")
    try:
        return pd.read_csv(DATA_FILE)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading CSV file: {str(e)}")

def load_cleaned_dataframe() -> pd.DataFrame:
    """Helper to load and clean the dataset."""
    raw_df = load_raw_dataframe()
    try:
        return clean_viewing_data(raw_df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning data: {str(e)}")

@app.get("/api/health")
def get_health():
    """Simple API health check endpoint."""
    return {"status": "healthy", "data_file_exists": DATA_FILE.exists()}

@app.get("/api/data/summary")
def get_data_summary():
    """Returns diagnostics and summary details of the raw vs cleaned records."""
    raw_df = load_raw_dataframe()
    try:
        diagnostics = get_data_diagnostics(raw_df)
        return diagnostics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing data diagnostics: {str(e)}")

@app.get("/api/viewing-data")
def get_viewing_data():
    """Preserved endpoint returning the cleaned records in JSON format."""
    cleaned = load_cleaned_dataframe()
    return json.loads(cleaned.to_json(orient="records"))

@app.get("/api/analytics/engagement")
def get_engagement_metrics():
    """Returns overall calculated viewer engagement metrics."""
    cleaned = load_cleaned_dataframe()
    try:
        metrics = calculate_engagement_metrics(cleaned)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating engagement metrics: {str(e)}")

@app.get("/api/analytics/retention")
def get_retention_analysis():
    """Returns detailed comparison of engagement metrics between retained and non-retained users."""
    cleaned = load_cleaned_dataframe()
    try:
        analysis = calculate_retention_analysis(cleaned)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating retention analysis: {str(e)}")

@app.get("/api/analytics/segments")
def get_viewer_segments():
    """Returns viewer distribution and retention rates across engagement segments."""
    cleaned = load_cleaned_dataframe()
    try:
        segments = segment_viewers(cleaned)
        return segments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error segmenting viewers: {str(e)}")

@app.get("/api/analytics/content-performance")
def get_content_performance():
    """Returns aggregated engagement and retention metrics for each content item."""
    cleaned = load_cleaned_dataframe()
    try:
        performance = calculate_content_performance(cleaned)
        return performance
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating content performance: {str(e)}")

@app.get("/api/analytics/recommendations")
def get_acquisition_recommendations():
    """Returns evidence-backed acquisition recommendations for content items."""
    cleaned = load_cleaned_dataframe()
    try:
        recommendations = generate_acquisition_recommendations(cleaned)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")
