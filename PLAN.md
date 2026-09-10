# **Project Plan — Team03@65**

## **1. Project Overview**

### **Problem Statement**

A subscription-based streaming platform captures watch duration, pause frequency, and episode completion data, but acquisition teams still greenlight content without understanding which viewer engagement patterns correlate with retention.

### **Objective**

Build a data-driven solution that identifies viewer engagement patterns associated with user retention and converts those insights into actionable recommendations for content acquisition teams.

### **Core Question**

**Which viewer engagement patterns are most strongly associated with user retention, and how can these insights help the platform make better content acquisition decisions?**

---

## **2. Proposed Solution**

The system will analyze viewer engagement data such as:

- Watch duration
- Pause frequency
- Episode completion rate
- Number of episodes watched
- Viewing frequency
- Session duration
- Content/genre preferences
- User retention status

The analysis will identify patterns between these engagement metrics and retention.

The final system will provide:

1. Engagement analysis
2. Retention insights
3. Viewer segmentation
4. Retention prediction/risk identification
5. Content-level performance insights
6. Data-driven acquisition recommendations

### **High-Level Flow**

```
Viewer Activity Data
        ↓
Data Cleaning & Preprocessing
        ↓
Feature Engineering
        ↓
Exploratory Data Analysis
        ↓
Engagement Pattern Analysis
        ↓
Retention Analysis / Prediction
        ↓
Content & Viewer Insights
        ↓
Acquisition Recommendations
```

---

# **3. Proposed Tech Stack**

> **Revised 2026-09-02 (supersedes the original React/FastAPI plan; see also PRD.md).** The learning units mandate Streamlit; the full-stack React/Node idea was dropped. PLAN/PRD references to React, Vite, FastAPI, Express, and MongoDB are historical.

## Frontend

- **Streamlit** (Python) — `src/app/app.py` + `src/app/components/`
- Plotly (interactive charts, funnels, heatmaps)

### **Purpose**

The dashboard provides an interactive decision-support interface for acquisition teams to explore:

- Retention metrics
- Engagement patterns
- Content performance
- Viewer segments
- Retention risk
- Acquisition recommendations

---

## Backend

- Python scripts (single-command pipeline: `scripts/run_pipeline.py`)
- Pandas / NumPy (analytical processing)
- SQLite (relational store; KPI views planned)

### **Purpose**

The pipeline reproduces every output from the raw catalog:

```
raw catalog -> normalize_catalog.py -> generate_behavior.py (seeded, synthetic)
            -> [planned: build_db.py — SQLite tables + KPI views]
            -> Streamlit dashboard
```

---

## Data Analysis

- Python
- Pandas
- NumPy
- Plotly
- Catalog priors bias the seeded synthetic generator; correlations are associations, never causal claims

---

## **Development & Collaboration**

- GitHub
- GitHub Issues
- GitHub Projects
- GitHub Pull Requests
- Git branches
- Code reviews

### **Repository**

`kalviumcommunity/team03-65`

---

# **4. Project Modules**

## **Module 1 — Data Collection & Preparation**

Tasks:

- Identify required datasets
- Define data fields (hybrid grain: real TMDB catalog as dimension table + seeded synthetic user-level sessions and retention tables)
- Generate the deterministic synthetic behaviour dataset (seed 42, metadata in `output/reports/generation_metadata.json`)
- Handle missing/invalid records via isolated validation reports (never silently dropped)
- Remove duplicate records
- Detect outliers
- Normalize/transform required fields

### **Expected Output**

A clean and structured dataset ready for analysis (`data/processed/` + `data/generated/`, gitignored, reproducible via `python scripts/run_pipeline.py`).

---

## **Module 2 — Exploratory Data Analysis**

Analyze relationships between:

- Watch duration and retention
- Pause frequency and retention
- Episode completion and retention
- Number of episodes watched and retention
- Session frequency and retention
- Content type and retention

### **Expected Output**

Charts and statistical insights showing which engagement behaviors are associated with retention.

---

## **Module 3 — Feature Engineering**

Create meaningful engagement metrics such as:

- Average watch duration
- Completion rate
- Average pauses per session
- Sessions per week (derived from session records, never typed per row)
- Average session duration
- Finished flag (completion >= 90%)

### **Expected Output**

A user-level feature set for retention analysis (engagement metrics aggregated per viewer; retention is a user-level outcome).

---

## **Module 4 — Viewer Segmentation**

Group viewers according to their engagement behavior.

Implemented segments (3-segment default, 4-segment PRD mode via dashboard toggle):

- Highly Engaged (completion >= 80% AND sessions/week >= 5)
- Moderately Engaged / Steady Viewers
- Casual Viewers
- At-Risk / Low Engagement (completion < 50% OR sessions/week <= 2)

Thresholds are documented in `analysis/segments.py`; recalibration may be explored if the generator's frequency distribution makes a tier empty.

### **Expected Output**

Meaningful viewer segments and their corresponding retention patterns.

---

## **Module 5 — Retention Analysis**

Investigate which engagement features have the strongest relationship with retention.

Approach (as built):

- Retained vs churned cohort comparison (user-level)
- Correlation analysis (Pearson, with strength bands and plain-language interpretation)
- Viewer segmentation with retention rates per segment
- Funnel progression: started → 25% → 50% → 75% → finished → retained

Predictive ML modelling (logistic regression, decision trees) remains future scope; the current product is descriptive/decision-support. Correlations are associations, never causal claims.

### **Expected Output**

A model/analysis that can estimate retention risk or probability based on viewer engagement behavior.

---

## **Module 6 — Content Performance Analysis**

Analyze content using engagement and retention metrics.

For each content title, calculate (from aggregated sessions):

- Distinct viewer count
- Average watch duration
- Average completion rate
- Average pause count
- Average sessions per week
- 30-day retention rate (user-level outcome; undefined outcomes excluded)

### **Expected Output**

Identification of content that demonstrates strong engagement and retention potential.

---

## **Module 7 — Acquisition Recommendation System**

Convert analytical findings into actionable recommendations.

Implemented rule-based categories (`analysis/recommendations.py`):

- HIGH PRIORITY: avg completion >= 75% AND 30-day retention >= 70%
- INVESTIGATE: avg completion >= 75% AND retention < 70%
- LOW PRIORITY: completion < 75% AND retention < 50%
- STANDARD: everything else

The recommendation system considers multiple engagement and retention indicators rather than relying on a single metric; every card exposes its supporting metrics and reasoning. Recommendations are decision-support only — final decisions stay with human stakeholders.

### **Expected Output**

A ranked list or recommendation score for content acquisition.

---

## **Module 8 — Dashboard**

Create an interactive dashboard for acquisition teams. Built as `src/app/app.py` (Streamlit) with a synthetic-data disclosure banner and a problem-statement navigator.

### **Dashboard Sections** (as built — 8 tabs)

#### **Executive Cockpit (Overview)**

- Total viewers, 30-day retention, avg completion, avg watch duration, avg pause count, finished rate
- Operational SLA alerts
- Benchmark gauges with targets

#### **Engagement Drivers**

- Completion vs retention, pause vs retention (cohort comparisons)
- Correlation matrix heatmap + plain-language takeaways

#### **Viewer Segments**

- 3-segment view (default) / 4-segment PRD view (toggle)
- Segment distribution, retention by segment, engagement characteristics

#### **Funnel Analysis**

- Started → 25% → 50% → 75% → Finished → Retained (per-user furthest stage)
- Biggest drop-off / bottleneck narrative

#### **Content Portfolio (Acquisition Recommendations)**

- HIGH PRIORITY / INVESTIGATE / STANDARD / LOW PRIORITY cards
- Supporting engagement + retention evidence per title

#### **What-If Model**

- Sensitivity simulator (completion lift, pause reduction → retention/ARR impact)

#### **SQL Parity**

- Python-vs-SQLite consistency audit workbench

#### **Data Quality & Assumptions**

- Synthetic-data provenance, analytical definitions, limitations, reproducibility

---

# **5. Week-Wise Implementation Plan**

## **Week 1 — Problem Understanding & Planning**

- Understand the problem statement
- Define project objectives
- Identify stakeholders and users
- Define key metrics
- Research relevant retention/engagement concepts
- Finalize project scope
- Create PRD
- Finalize initial tech stack
- Set up GitHub repository
- Create GitHub Issues
- Define team responsibilities

### **Deliverables**

- PRD
- Project plan
- Initial architecture
- GitHub project board

---

## **Week 2 — Data & Exploratory Analysis**

- Identify/create dataset
- Define data schema
- Clean and preprocess data
- Perform exploratory data analysis
- Generate initial visualizations
- Analyze relationships between engagement and retention
- Document important findings

### **Deliverables**

- Clean dataset
- EDA notebook/scripts
- Initial insights
- Data dictionary

---

## **Week 3 — Feature Engineering & Retention Analysis**

- Create engagement metrics
- Calculate retention metrics
- Perform correlation analysis
- Segment viewers
- Experiment with suitable ML models
- Evaluate model performance
- Identify important retention factors

### **Deliverables**

- Feature-engineered dataset
- Viewer segmentation
- Retention analysis
- Initial prediction model
- Model evaluation results

---

## **Week 4 — Backend Development** *(revised)*

The original FastAPI/REST plan was dropped with the 2026-09-02 Streamlit decision. Actual backend work:

- One-command pipeline orchestrator (`scripts/run_pipeline.py`, PR #20)
- SQLite schema (`sql/schema.sql`) + business queries (`sql/business_queries.sql`)
- SQL KPI layer (`scripts/build_db.py`, `sql/kpi_views.sql`) — **planned, not started**

### **Deliverables**

- Reproducible pipeline (normalize → generate, verified outputs)
- Relational store + queries (user-grain parity with pandas)

---

## **Week 5 — Frontend & Dashboard**

- Design dashboard UI
- Implement dashboard layout (Streamlit, PR #21)
- Load data from the generated dataset (CSV; SQL views planned)
- Add charts and visualizations
- Add viewer segmentation views
- Add content analysis
- Add acquisition recommendations
- Add synthetic-data disclosure and assumptions page

### **Deliverables**

- Functional dashboard (Executive Cockpit, Engagement, Segments, Funnel, Content, What-If, SQL Parity, Data Quality tabs)
- Interactive analytics

---

## **Week 6 — Integration, Testing & Refinement**

- Integrate all modules
- Test the dashboard (64 pytest tests green; user-grain SQL parity verified)
- Validate analytical results (eligible-user retention denominators, per-user funnel)
- Test recommendation logic
- Fix bugs (grain fixes merged in PRs #23/#24)
- Improve UI/UX
- Optimize performance
- Perform end-to-end testing

### **Deliverables**

- Integrated application
- Tested system
- Final analytics
- Improved UI/UX

---

## **Week 7 — Finalization & Presentation**

- Finalize documentation
- Prepare project report
- Prepare architecture diagrams
- Prepare demo flow
- Prepare presentation
- Document limitations
- Document future improvements
- Conduct final testing
- Prepare final project demonstration

### **Deliverables**

- Final application
- Documentation
- Presentation
- Demo
- Final project report

---

# **6. Team Workflow**

## **Branching Strategy**

The `main` branch contains stable and reviewed code (protected; Team Lead merges approved PRs only).

Each member works on a separate branch named `type/description`:

```
main
  ├── feature/repo-scaffold          (merged — PR #16)
  ├── feature/data-pipeline          (merged — PR #17)
  ├── feature/pipeline-orchestrator  (merged — PR #20)
  ├── feature/streamlens-analytics-platform (merged — PR #21)
  ├── fix/retention-eligibility-logic      (merged — PR #18)
  └── fix/dashboard-data-alignment         (merged — PRs #23/#24)
```

Full branch/commit/PR rules: see the team workflow doc (in the workspace context folder, gitignored).

## **Pull Request Process**

1. Create/assign a GitHub Issue.
2. Create a feature branch.
3. Implement the assigned task.
4. Commit changes with meaningful messages.
5. Push the branch.
6. Open a Pull Request.
7. Request at least one team-member review.
8. Address review comments.
9. Get approval.
10. Merge into `main`.

Direct pushes to `main` should be avoided.

---

# **7. Initial Task Distribution**

**Area**

**Responsibility**

Project Coordination

Team Lead

Data & EDA

Assigned team member(s)

Machine Learning / Retention Analysis

Assigned team member(s)

Backend & Database

Assigned team member(s)

Frontend & Dashboard

Assigned team member(s)

UI/UX & Visualization

Assigned team member(s)

Documentation & Testing

Assigned team member(s)

The exact ownership will be finalized by the team through GitHub Issues.

---

# **8. Key Success Metrics**

The project will be evaluated based on whether it can:

- Identify engagement patterns associated with retention.
- Explain why particular engagement patterns matter.
- Identify high-risk and highly engaged viewer segments.
- Compare content based on engagement and retention.
- Provide actionable content acquisition recommendations.
- Present insights through an understandable dashboard.
- Maintain reproducible and well-documented analysis.

---

# **9. Future Scope**

Potential future improvements include:

- Real-time engagement tracking
- Real-time retention prediction
- Personalized content recommendations
- Advanced recommendation models
- A/B testing for acquired content
- Churn prediction
- Automated acquisition decision support
- Integration with real streaming-platform data
- Continuous model retraining

---

# **10. Final Goal**

The final system should move the acquisition team from:

**“We think this content will perform well.”**

to:

**“Our data shows that content with these engagement characteristics is strongly associated with retention, so this content has a higher acquisition priority.”**

The project will therefore connect **viewer behavior → retention insights → content performance → acquisition decisions**.
