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
