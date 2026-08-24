# Product Requirements Document

## Streaming Retention & Content Acquisition

## 1. Problem Statement

A subscription-based streaming platform captures viewer activity such as watch duration, completion rate, pause behaviour, and viewing frequency. However, the content acquisition team needs a clear analytical view connecting these behaviours with retention and content performance.

The product will provide a centralized decision-support dashboard connecting viewer engagement, retention outcomes, behavioural viewer segments, content performance, and acquisition insights.

---

## 2. Product Goal

Build a data-driven analytics product that helps content acquisition teams:

- Understand engagement patterns associated with viewer retention.
- Compare retained and churned/non-retained viewer cohorts.
- Identify behavioural viewer segments.
- Compare content using multiple engagement and retention indicators.
- Provide transparent acquisition insights using defined recommendation categories.
- Validate uploaded data before analytical results are presented.

The product supports human decision-making and does not automatically approve or reject acquisitions.

---

## 3. Target Users

### Primary User — Content Acquisition Team

Content acquisition professionals who evaluate content opportunities and decide which content should receive acquisition attention.

### Secondary User — Project Analyst

Analysts responsible for preparing, validating, analysing, and interpreting viewer engagement and retention data.

---

## 4. Core Business Questions

1. Which engagement patterns are associated with viewer retention?
2. How do retained and churned/non-retained viewers differ in engagement behaviour?
3. Which behavioural viewer segments show stronger or weaker retention?
4. Which content performs best across engagement and retention metrics?
5. Which content should be prioritized, investigated, or monitored?
6. What evidence supports each acquisition insight?

---

## 5. Key Metrics

### Overview KPI Cards

The Overview screen displays:

- Overall Retention Rate
- Average Completion Rate
- Average Watch Duration
- Average Pause Count

### Supporting Metrics

The product also uses:

- Viewer count
- Average watch duration
- Average completion rate
- Average pause count
- Average sessions per week
- Retention rate

The analysis must only calculate metrics supported by the available dataset.

---

## 6. Viewer Segmentation

The Viewer Segments screen uses four behavioural viewer segments.

### 6.1 Highly Engaged

Viewers demonstrating consistently strong engagement and frequent viewing behaviour.

### 6.2 Steady Viewers

Viewers demonstrating consistent, moderate engagement and regular viewing behaviour.

### 6.3 Casual Viewers

Viewers demonstrating lower or less consistent engagement and viewing frequency.

### 6.4 Low / At-Risk

Viewers demonstrating weak engagement patterns and/or signals associated with lower retention.

For each segment, the dashboard should show:

- Segment size / viewer count
- Retention rate
- Completion behaviour
- Pause frequency
- Viewing frequency

---

## 7. Engagement & Retention Analysis

The Engagement & Retention screen compares retained and churned cohorts using the available engagement metrics.

It should include:

- Retained Cohort vs Churned Cohort comparison
- Average completion rate
- Average watch duration
- Average pause count
- Average sessions per week
- Engagement pattern summary
- Completion Rate vs Retention visualization
- Pause Frequency vs Retention visualization

The purpose is to make observed relationships between engagement behaviour and retention easy to understand.

---

## 8. Content Performance

The Content Performance screen provides a scorecard/table for comparing content using multiple engagement and retention metrics.

For each content item, display:

| Field | Requirement |
|---|---|
| Content ID & Title | Identify the content item |
| Viewers | Show viewer count |
| Avg Watch Duration | Compare viewing depth |
| Avg Completion % | Compare completion behaviour |
| Avg Pauses | Identify interruption/friction |
| Avg Sessions / Wk | Compare viewing frequency |
| Retention Rate | Compare retention outcomes |
| Status Badge | Summarize content performance |

The selected content detail view should contain:

- Retention Impact
- Completion & Engagement
- Acquisition Decision

---

## 9. Acquisition Insights & Recommendation Categories

The Acquisition Insights screen presents evidence-based content recommendations.

The recommendation categories are:

### 9.1 Prioritize

Content showing strong overall engagement and favourable retention evidence and therefore suitable for higher acquisition attention.

### 9.2 Investigate

Content showing useful engagement evidence but requiring further investigation because retention or another indicator is less favourable.

### 9.3 Monitor

Content that does not currently justify prioritization or investigation and should be observed using the available evidence.

Each recommendation card should display:

- Content identifier/title
- Recommendation category
- Retention evidence
- Engagement evidence
- Supporting metrics
- Explanation of why the category was assigned
- View Evidence action where applicable

Recommendations are decision-support outputs only. They do not automatically approve or reject acquisitions.

---

## 10. Data Upload & Validation

The product includes a dedicated upload and validation flow before analytical results are presented.

The system must:

1. Accept the supported CSV viewer dataset.
2. Show the required columns before upload.
3. Validate the selected file format.
4. Validate required columns.
5. Show a validation preview after file selection.
6. Display record counts and validation status.
7. Show processing/loading progress.
8. Show a success state when the dataset is ready.
9. Provide recovery actions when validation or processing fails.
10. Prevent invalid data from silently replacing a previously valid dataset.

### Current Dataset Fields

- User ID
- Content ID
- Watch duration
- Completion rate
- Pause count
- Sessions per week
- Retention status

---

## 11. Dashboard Information Architecture

The dashboard follows the five-section structure represented in the mock UI:

1. Overview
2. Engagement & Retention
3. Content Performance
4. Viewer Segments
5. Acquisition Insights

### 11.1 Overview

The Overview screen contains:

- Overall Retention Rate KPI
- Avg Completion Rate KPI
- Avg Watch Duration KPI
- Avg Pause Count KPI
- Key Behavioral Takeaways
- Engagement Distribution Chart
- Catalog Performance Summary
- Navigation cards to analytical sections
- Content, Retention, and Metric filters where applicable

### 11.2 Engagement & Retention

Contains:

- Retained vs Churned Cohort table
- Completion Rate vs Retention visualization
- Pause Frequency vs Retention visualization
- Engagement metric comparison

### 11.3 Content Performance

Contains:

- Content Performance Scorecard
- Sortable content comparison
- Selected Content Detail Panel
- Retention Impact
- Completion & Engagement
- Acquisition Decision

### 11.4 Viewer Segments

Contains:

- Highly Engaged
- Steady Viewers
- Casual Viewers
- Low / At-Risk
- Segment population distribution
- Retention likelihood
- Segment-level engagement indicators

### 11.5 Acquisition Insights

Contains:

- Evidence-based acquisition decision cards
- Prioritize / Investigate / Monitor categories
- Supporting metrics
- Retention and engagement evidence
- View Evidence action

---

## 12. Functional Requirements

- **FR1 — Data Ingestion:** Load the supported viewer activity CSV dataset.
- **FR2 — File Validation:** Validate file format and required columns before processing.
- **FR3 — Data Cleaning:** Identify and handle missing, invalid, and inconsistent values.
- **FR4 — Engagement Analysis:** Calculate the defined engagement metrics.
- **FR5 — Retention Analysis:** Compare retained and churned/non-retained viewer behaviour.
- **FR6 — Viewer Segmentation:** Classify viewers into the four segments represented in the mock UI.
- **FR7 — Content Analysis:** Aggregate engagement and retention metrics by content.
- **FR8 — Acquisition Insights:** Assign Prioritize, Investigate, or Monitor using multiple indicators.
- **FR9 — Evidence:** Display the metrics and explanation supporting each acquisition insight.
- **FR10 — Dashboard:** Present results through KPIs, charts, tables, segment cards, and recommendation cards.
- **FR11 — API Access:** Make analytical results available through REST APIs.
- **FR12 — Reproducibility:** Produce consistent results for the same dataset and documented processing logic.

---

## 13. API Requirements

Expected REST endpoints:

- `GET /api/health`
- `GET /api/data/summary`
- `GET /api/analytics/engagement`
- `GET /api/analytics/retention`
- `GET /api/analytics/segments`
- `GET /api/analytics/content-performance`
- `GET /api/analytics/recommendations`

The APIs will return structured JSON responses suitable for dashboard consumption.

---

## 14. Data Requirements

The current dataset contains:

- User ID
- Content ID
- Watch duration
- Completion rate
- Pause count
- Sessions per week
- Retention status

The analysis must only calculate metrics supported by the available data.

---

## 15. Technical Requirements

### Current Prototype

- Python
- Pandas
- FastAPI
- CSV

### Data Analysis

- NumPy
- Pandas
- Matplotlib / Seaborn where required
- scikit-learn where required for analytical segmentation

### Dashboard

- React
- Vite
- Tailwind CSS
- Recharts or Chart.js
- Axios

### Backend & Storage — Planned

- Node.js
- Express.js
- MongoDB

### Collaboration

- GitHub
- Branches
- Pull Requests
- Code Reviews
- GitHub Issues / Projects

---

## 16. End-to-End Product Flow

1. Open the Overview dashboard.
2. Upload the supported viewer dataset.
3. Validate file format and required columns.
4. Show validation preview and data-quality status.
5. Process and clean valid data.
6. Display Overview KPIs and behavioural takeaways.
7. Explore Engagement & Retention.
8. Explore Content Performance.
9. Explore Viewer Segments.
10. Explore Acquisition Insights and supporting evidence.

---

## 17. Success Criteria

The product will be considered successful when:

- The upload flow clearly communicates file validity and data readiness.
- The Overview displays the four KPI cards defined in the mock UI.
- Engagement and retention can be compared using the defined metrics.
- Every valid viewer is assigned to one of the four dashboard viewer segments.
- Each segment displays meaningful engagement and retention information.
- Content can be compared using viewer count, watch duration, completion, pauses, sessions per week, and retention.
- Each analyzed content item can receive a Prioritize, Investigate, or Monitor category.
- Each recommendation exposes supporting evidence and reasoning.
- The dashboard follows the five-section information architecture represented in the mock UI.
- The analytical pipeline remains reproducible and documented.

---

## 18. Non-Functional Requirements

### Usability

The dashboard should allow a content acquisition stakeholder to understand major insights without requiring technical knowledge.

### Reliability

Invalid or missing records should not cause the entire analytical pipeline to fail.

### Transparency

Recommendations must show the underlying metrics and reasoning.

### Maintainability

Analytics logic should remain separated from API routing and dashboard presentation.

### Reproducibility

The same input dataset and documented processing logic should produce consistent analytical results.

---

## 19. Risks & Mitigation

| Risk | Mitigation |
|---|---|
| Small sample size | Treat findings as observations from the available dataset and avoid unsupported causal claims. |
| Missing/invalid data | Validate and clean data before analysis and report data-quality issues. |
| Correlation misinterpretation | Describe engagement-retention relationships as observed associations rather than causation. |
| Recommendation bias | Expose supporting metrics and keep final acquisition decisions with human stakeholders. |

---

## 20. Out of Scope

The following remain outside the current product scope:

- Real-time engagement tracking
- Predictive retention modelling
- Personalized viewer recommendations
- A/B testing
- Automated acquisition decisions
- Integration with live production streaming-platform data
- Continuous model retraining

---

## 21. Expected Outcome

The final product will provide content acquisition teams with a clear analytical view of:

- Viewer engagement
- Retention
- Content performance
- Behavioural viewer segments
- Acquisition insights

The PRD and mock UI/UX use the same:

- Dashboard sections
- Overview KPIs
- Viewer segmentation categories
- Content performance fields
- Acquisition recommendation categories
- Upload and validation workflow

**Rework scope: PRD only. No mock UI redesign is required for this rework.**
