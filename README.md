# **Streaming Retention & Content Acquisition Backend**

An analytics engine and API that connects viewer engagement patterns to platform retention outcomes, providing data-supported recommendations to help content acquisition teams make optimal purchasing decisions.

---

## **1. Project Purpose**

A subscription-based streaming platform captures raw engagement details (watch duration, pause frequency, episode completion rate), but acquisition teams historically greenlighted content without understanding which viewer engagement patterns correlate with long-term retention. 

This project implements a reproducible Python data cleaning pipeline, calculates robust viewer metrics, segments users by engagement level, evaluates content performance, and runs a rule-based content recommendation system exposed via a clean FastAPI REST backend.

---

## **2. Dataset Schema**

The raw source dataset is located at [data/viewing_data.csv](file:///Users/sanjeevms/Documents/team03-65/data/viewing_data.csv). It contains the following columns:

| Field Name | Description | Validation Rule / Range |
| :--- | :--- | :--- |
| `user_id` | Unique string identifying the viewer | String, non-empty, whitespaces stripped |
| `content_id` | Unique string identifying the streaming title | String, non-empty, whitespaces stripped |
| `watch_duration` | Time spent watching in minutes | Non-negative numeric [0, 1440] |
| `completion_rate` | Content completion percentage | Percentage numeric [0, 100] |
| `pause_count` | Number of times playback was paused | Non-negative integer |
| `sessions_per_week` | Number of viewing sessions per week | Non-negative integer [0, 7] |
| `retained` | Indicator of user retention | Boolean value mapped from `true/false`, `yes/no`, `y/n`, `1/0` |

---

## **3. How to Run the Project**

### **Prerequisites**
- Python 3.10+ installed.

### **Step 1: Install Dependencies**
Initialize the virtual environment and install the required libraries:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### **Step 2: Run the FastAPI Server**
Start the development server using `uvicorn`:
```bash
uvicorn main:app --reload
```
The server will start on `http://127.0.0.1:8000`. You can access the interactive API docs at `http://127.0.0.1:8000/docs`.

---

## **4. Data Cleaning Pipeline**

The data cleaning pipeline in [analysis/cleaning.py](file:///Users/sanjeevms/Documents/team03-65/analysis/cleaning.py) ensures input data is sanitized without altering the original CSV:
1. Strips all whitespaces and quotes from text identifiers (`user_id`, `content_id`). Removes records with null or missing identifiers.
2. Converts numeric columns to actual numbers. Replaces invalid or out-of-bounds metrics (e.g. negative values, `unknown`, `N/A`, duration > 1440 mins) with the **median** of the valid records for that column to prevent skew.
3. Normalizes boolean retained variations (case-insensitive `true/false`, `yes/no`, `y/n`, `1/0`). Imputes missing values with the most common retention status (mode).
4. Drops identical duplicate rows.

---

## **5. API Endpoints and Example Responses**

### **GET `/api/health`**
Verifies API status and database presence.
**Example Response:**
```json
{
  "status": "healthy",
  "data_file_exists": true
}
```

### **GET `/api/data/summary`**
Provides statistics on dataset rows, including counts of valid vs dirty records.
**Example Response:**
```json
{
  "total_records": 71,
  "unique_users": 70,
  "unique_content_items": 50,
  "valid_records": 59,
  "missing_invalid_records": 12
}
```

### **GET `/api/analytics/engagement`**
Aggregates overall platform engagement averages.
**Example Response:**
```json
{
  "average_watch_duration": 39.79,
  "average_completion_rate": 71.64,
  "average_pause_count": 3.46,
  "average_sessions_per_week": 3.89,
  "retention_rate": 0.60
}
```

### **GET `/api/analytics/retention`**
Compares engagement metrics grouped by user retention status to identify correlations.
**Example Response:**
```json
{
  "retained": {
    "count": 42,
    "percentage": 60.0,
    "average_watch_duration": 52.21,
    "average_completion_rate": 88.93,
    "average_pause_count": 1.90,
    "average_sessions_per_week": 5.19
  },
  "non_retained": {
    "count": 28,
    "percentage": 40.0,
    "average_watch_duration": 21.14,
    "average_completion_rate": 45.70,
    "average_pause_count": 5.79,
    "average_sessions_per_week": 1.93
  },
  "retention_rate": 0.60
}
```

### **GET `/api/analytics/segments`**
Segments viewers based on completion rate and weekly session frequency.
*   **Highly Engaged**: Completion Rate $\ge$ 80% AND Sessions/Week $\ge$ 5
*   **At Risk / Low Engagement**: Completion Rate $<$ 50% OR Sessions/Week $\le$ 2
*   **Moderately Engaged**: Remaining users
**Example Response:**
```json
[
  {
    "segment": "Highly Engaged",
    "viewer_count": 28,
    "viewer_percentage": 40.0,
    "retention_rate": 1.0
  },
  {
    "segment": "Moderately Engaged",
    "viewer_count": 22,
    "viewer_percentage": 31.43,
    "retention_rate": 0.64
  },
  {
    "segment": "At Risk / Low Engagement",
    "viewer_count": 20,
    "viewer_percentage": 28.57,
    "retention_rate": 0.0
  }
]
```

### **GET `/api/analytics/content-performance`**
Aggregates and formats all indicators on a per-content basis.
**Example Response:**
```json
[
  {
    "content_id": "C001",
    "viewer_count": 3,
    "average_watch_duration": 34.0,
    "average_completion_rate": 71.67,
    "average_pause_count": 4.0,
    "average_sessions_per_week": 3.67,
    "retention_rate": 0.6667
  }
]
```

### **GET `/api/analytics/recommendations`**
Returns evidence-supported acquisition priorities for content items based on engagement and retention metrics.
*   **HIGH PRIORITY**: Average Completion Rate $\ge$ 75% AND Retention Rate $\ge$ 70%
*   **INVESTIGATE**: Average Completion Rate $\ge$ 75% AND Retention Rate $<$ 70%
*   **LOW PRIORITY**: Average Completion Rate $<$ 75% AND Retention Rate $<$ 50%
*   **STANDARD**: Default baseline performance

**Example Response:**
```json
[
  {
    "content_id": "C005",
    "recommendation": "HIGH PRIORITY",
    "reason": "Strong engagement profile (completion rate: 86.33%) coupled with high viewer retention (100.0%). Acquiring similar content is highly recommended to sustain platform growth.",
    "metrics": {
      "viewer_count": 3,
      "average_watch_duration": 48.33,
      "average_completion_rate": 88.0,
      "average_pause_count": 2.0,
      "average_sessions_per_week": 5.33,
      "retention_rate": 1.0
    }
  }
]
```

### **GET `/api/analytics/distributions`**
Returns descriptive statistics, central tendency (mean, median, mode), dispersion, skewness, outlier detection (IQR 1.5x rule), and binned histogram frequencies for core engagement metrics.

**Example Response:**
```json
{
  "total_records": 70,
  "column_mapping": {
    "completion_rate": "completion_pct / completion rate",
    "watch_duration": "watch_duration / watch_duration_min",
    "pause_count": "pause_count",
    "sessions_per_week": "sessions_per_week"
  },
  "distributions": {
    "completion_rate": {
      "metric": "completion_rate",
      "display_name": "completion_pct / completion rate",
      "count": 70,
      "mean": 71.6357,
      "median": 79.5,
      "mode": [100.0],
      "std": 24.8816,
      "min": 8.0,
      "max": 100.0,
      "range": 92.0,
      "q25": 52.5,
      "q75": 92.0,
      "iqr": 39.5,
      "skewness": -0.7838,
      "skewness_classification": "moderately negative (left-skewed)",
      "outlier_bounds": {"lower": -6.75, "upper": 151.25},
      "outliers": [],
      "outlier_count": 0,
      "histogram": [
        {"bin_index": 1, "range_min": 8.0, "range_max": 26.4, "label": "8.0 - 26.4", "count": 6, "percentage": 8.57},
        {"bin_index": 2, "range_min": 26.4, "range_max": 44.8, "label": "26.4 - 44.8", "count": 7, "percentage": 10.0},
        {"bin_index": 3, "range_min": 44.8, "range_max": 63.2, "label": "44.8 - 63.2", "count": 10, "percentage": 14.29},
        {"bin_index": 4, "range_min": 63.2, "range_max": 81.6, "label": "63.2 - 81.6", "count": 13, "percentage": 18.57},
        {"bin_index": 5, "range_min": 81.6, "range_max": 100.0, "label": "81.6 - 100.0", "count": 34, "percentage": 48.57}
      ]
    }
  }
}
```

### **GET `/api/analytics/correlation`**
Calculates the correlation of each engagement metric against user retention, providing coefficients, relationship direction, strength, qualitative interpretation, and key acquisition takeaways.

**Example Response:**
```json
{
  "retention_correlations": [
    {
      "metric": "completion_rate",
      "metric_label": "Completion Rate (%)",
      "target": "retained",
      "target_label": "User Retention (Boolean/Binary)",
      "correlation_coefficient": 0.8574,
      "direction": "positive",
      "strength": "very strong positive",
      "interpretation": "Very strong positive correlation (r = 0.8574). Viewers who complete a higher percentage of their content are overwhelmingly more likely to remain active subscribers."
    },
    {
      "metric": "sessions_per_week",
      "metric_label": "Sessions Per Week",
      "target": "retained",
      "target_label": "User Retention (Boolean/Binary)",
      "correlation_coefficient": 0.8371,
      "direction": "positive",
      "strength": "very strong positive",
      "interpretation": "Strong positive correlation (r = 0.8371). High weekly viewing cadence is one of the strongest predictors of sustained user retention and platform habit formation."
    },
    {
      "metric": "pause_count",
      "metric_label": "Pause Count",
      "target": "retained",
      "target_label": "User Retention (Boolean/Binary)",
      "correlation_coefficient": -0.8041,
      "direction": "negative",
      "strength": "very strong negative",
      "interpretation": "Strong negative correlation (r = -0.8041). High pause frequency is a strong indicator of viewer friction, disinterest, or distraction, strongly correlating with user churn."
    },
    {
      "metric": "watch_duration",
      "metric_label": "Watch Duration (mins)",
      "target": "retained",
      "target_label": "User Retention (Boolean/Binary)",
      "correlation_coefficient": 0.7911,
      "direction": "positive",
      "strength": "strong positive",
      "interpretation": "Strong positive correlation (r = 0.7911). Longer watch times per session indicate higher viewer investment and strongly correlate with long-term user retention."
    }
  ],
  "summary_takeaway": "Completion rate (r = 0.8574) and weekly viewing frequency (r = 0.8371) are the strongest positive predictors of user retention. Conversely, high pause count (r = -0.8041) is a strong negative indicator signaling content disengagement."
}
```

### **GET `/api/analytics/correlation/matrix`**
Returns the full pairwise Pearson correlation matrix and structured heatmap coordinates formatted for charting components (e.g. Recharts, Chart.js, D3) alongside ASCII visualization.

---

## **6. Day 11 Analytical Findings**

### **Distribution Analysis Summary (2.28)**

| Metric | Dataset Column | Mean | Median | Mode | Std Dev | Min | Max | Range | Skewness | Classification | Outliers (IQR 1.5x) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Completion Rate** | `completion_rate` | 71.64% | 79.50% | 100.0% | 24.88% | 8.0% | 100.0% | 92.0% | -0.7838 | Moderately negative (left-skewed) | 0 (cleaned bounds) |
| **Watch Duration** | `watch_duration` | 39.79 min | 38.00 min | 38.0 min | 19.38 min | 8.0 min | 84.0 min | 76.0 min | +0.3106 | Approximately symmetric | 0 (cleaned bounds) |
| **Pause Count** | `pause_count` | 3.46 | 3.00 | 2.0 | 2.38 | 0 | 9 | 9 | +0.5683 | Moderately positive (right-skewed) | 0 (cleaned bounds) |
| **Sessions / Week** | `sessions_per_week` | 3.89 | 4.00 | 5.0 | 1.92 | 1 | 7 | 6 | +0.0159 | Approximately symmetric | 0 (cleaned bounds) |

*Key Distribution Takeaway*: The completion rate is negatively skewed (-0.7838) with almost 48.6% of sessions finishing in the 81.6%–100.0% band. Pause count is moderately right-skewed (+0.5683), where most engaged users pause $\le$ 2 times, while churning users exhibit long tails of frequent pauses.

---

### **Correlation Analysis Summary & Heatmap (2.29)**

| Metric A | Metric B | Correlation ($r$) | Direction | Strength | Interpretation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Completion Rate** | User Retention | **+0.8574** | Positive | Very Strong | Highest single predictor of retention; viewers completing episodes stay subscribed. |
| **Sessions Per Week** | User Retention | **+0.8371** | Positive | Very Strong | Habitual frequency reinforces long-term retention. |
| **Pause Count** | User Retention | **-0.8041** | Negative | Very Strong | Excessive pausing reflects viewer friction and strongly predicts churn. |
| **Watch Duration** | User Retention | **+0.7911** | Positive | Strong | Longer session immersion positively correlates with platform commitment. |
| **Completion Rate** | Pause Count | **-0.9587** | Negative | Near Perfect | High pausing strongly inhibits episode completion. |
| **Completion Rate** | Sessions/Week | **+0.9316** | Positive | Very Strong | Frequent viewers systematically finish more content. |

#### **Pairwise Correlation Heatmap Matrix**
```
Metric              compl_   watch_   pause_   sessio   retain
--------------------------------------------------------------
completion_rate     1.0000   0.8614  -0.9587   0.9316   0.8574
watch_duration      0.8614   1.0000  -0.8432   0.9324   0.7911
pause_count        -0.9587  -0.8432   1.0000  -0.9126  -0.8041
sessions_per_week   0.9316   0.9324  -0.9126   1.0000   0.8371
retained            0.8574   0.7911  -0.8041   0.8371   1.0000
```

