# Viewer Retention Insights

Data product analysing the relationship between streaming viewer engagement and subscriber retention, built for content acquisition teams.

> **Data disclosure:** All viewer behaviour data in this project is **synthetic**, generated deterministically from a documented seed and parameter set. Real-world streaming behaviour was not available. Findings demonstrate the analytical workflow under stated simulation assumptions — they are not real-world streaming conclusions.

## Status

Migrating from the initial FastAPI prototype to the final Streamlit + SQLite architecture (see PLAN.md). This scaffold commit sets up the target structure.

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate        # Windows
python -m pip install -r requirements.txt
```

## Pipeline

```bash
python scripts/run_pipeline.py --input data/raw/tmdb_catalog.csv
```

Stages: catalog intake & validation -> normalization -> synthetic behaviour generation (seeded) -> SQLite build -> KPI views -> dashboard-ready outputs.

Run tests:

```bash
pytest
```

Run the dashboard:

```bash
streamlit run src/app/app.py
```

## Structure

```
data/raw/          unchanged source files (gitignored)
data/processed/    normalized catalog + SQLite DB (gitignored)
data/generated/    synthetic sessions/retention data (gitignored)
scripts/           repeatable command-line pipeline code
sql/               schema and KPI view definitions
src/app/           Streamlit dashboard
tests/             deterministic fixtures and tests
output/reports/    intake/profile/validation reports (gitignored)
notebooks/         exploration only
```

## Data sources

| Table | Grain | Nature |
|---|---|---|
| `content_catalog` | one row per movie (~50k) | real (TMDB-derived catalog) |
| `viewer_sessions` | one row per user × content session | synthetic (seeded generator) |
| `viewer_retention` | one row per user × observation month | synthetic (seeded generator) |

Viewer behaviour metrics are aggregated from synthetic session records; they are never copied from movie ratings or popularity.

## Limitations

- Behaviour data is synthetic; associations reflect generator assumptions, not observed reality.
- No causal claims are made; correlations are descriptive.
- Small-denominator content metrics are flagged in the dashboard.
