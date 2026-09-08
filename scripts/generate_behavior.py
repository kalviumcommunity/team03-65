"""Generate synthetic viewer behaviour data deterministically.

Pipeline position
-----------------
data/processed/content_catalog.csv
    -> THIS SCRIPT -> data/generated/viewer_sessions.csv
                      data/generated/viewer_retention.csv
                      output/reports/generation_metadata.json

What it generates
-----------------
viewer_sessions   one row per user x content session:
                  user_id, session_id, content_id, started_at,
                  watch_duration_minutes (<= catalog runtime),
                  pause_count (int >= 0), completion_pct (0..100),
                  finished (completion_pct >= 90)

viewer_retention  one row per user x observation month:
                  user_id, observation_date,
                  eligible_for_30d_retention, retained_30d
                  (eligible = >= 1 session on or before the observation
                  date; retained = eligible AND any session within the
                  30 days after the observation date)

How it works (the retired Google Sheets formula spec, reimplemented in code)
----------------------------------------------------------------------------
Content priors are computed from the real catalog:
  rating_score     = vote_average / 10                      (quality prior, 0..1)
  popularity_score = log1p(popularity), min-max normalised  (exposure prior)
  vote_confidence  = percentile rank of vote_count          (sampling proxy)

A user's sessions are sampled per month: the number of sessions depends on
an engagement propensity, content is chosen by popularity-weighted sampling,
completion is drawn from a beta distribution shaped by rating_score with
deterministic per-(user, content) noise, watch duration is derived from
completion and runtime, pauses rise as completion falls.

Retention is then a genuine user-level outcome computed from the session
records: a user is eligible for an observation month if they had at least
one session on or before the observation date, and retained_30d if, being
eligible, they have any session in the following 30 days. Engagement ->
retention association emerges from behaviour, never from per-movie
formulas. A burn-in month of sessions before the first observation
ensures the first observed cohort has eligible users.

Determinism: a single numpy Generator seeded from SEED drives every draw.
Two runs with the same seed and inputs produce byte-identical outputs.

This data is synthetic and must be disclosed as such in any presentation.
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# --- configuration constants -------------------------------------------------

SEED = 42
FORMULA_VERSION = "2.1.0-retention-eligibility-fix"

NUM_USERS = 5000
OBSERVATION_MONTHS = 6
OBSERVATION_START = "2026-03-01"
# Sessions are generated from this month; the month(s) before the first
# observation act as burn-in so the first observed cohort has eligibles.
SESSIONS_START = "2026-02-01"
SESSIONS_LEAD_MONTHS = 1

SESSIONS_BASE_LOW = 0
SESSIONS_BASE_HIGH = 8
SESSIONS_PARETO_SHAPE = 1.4

COMPLETION_CONCENTRATION = 12.0
NOISE_SCALE = 0.06
ENGAGEMENT_COMPLETION_COUPLING = 0.3

PAUSE_BASE_LOW = 0
PAUSE_BASE_HIGH = 3
PAUSE_MAX = 12

MIN_RUNTIME_MINUTES = 10
MAX_WATCH_DURATION_FRACTION = 1.0

RETENTION_OBSERVATION_DAY = 1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("generate_behavior")


# --- priors --------------------------------------------------------------------

def compute_content_priors(catalog: pd.DataFrame) -> pd.DataFrame:
    """Compute the content-level sampling priors from the real catalog.

    Args:
        catalog: Normalized content catalog.

    Returns:
        Catalog copy with rating_score, popularity_score and
        vote_confidence columns added; invalid rows (zero runtime,
        unparsable popularity) are excluded.

    Raises:
        ValueError: If no catalog rows survive the runtime filter.
    """
    df = catalog.copy()
    df = df[df["runtime_minutes"] >= MIN_RUNTIME_MINUTES].copy()

    if df.empty:
        raise ValueError(
            "No catalog rows with runtime >= "
            f"{MIN_RUNTIME_MINUTES} minutes; cannot generate sessions."
        )

    df["rating_score"] = (df["vote_average"] / 10.0).clip(0.0, 1.0)

    log_pop = np.log1p(df["popularity"].clip(lower=0.0))
    span = log_pop.max() - log_pop.min()
    if span == 0:
        df["popularity_score"] = 0.5
    else:
        df["popularity_score"] = (log_pop - log_pop.min()) / span

    df["vote_confidence"] = df["vote_count"].rank(pct=True)

    log.info(
        "Priors computed for %d usable titles (of %d catalog rows)",
        len(df), len(catalog),
    )
    return df


# --- generation ----------------------------------------------------------------

def generate_users(rng: np.random.Generator) -> pd.DataFrame:
    """Generate per-user engagement propensities.

    Args:
        rng: Seeded numpy Generator.

    Returns:
        Dataframe with user_id and propensity columns.
    """
    user_ids = [f"U{idx:05d}" for idx in range(1, NUM_USERS + 1)]
    users = pd.DataFrame({"user_id": user_ids})

    users["engagement_propensity"] = rng.beta(
        a=2.0, b=2.5, size=NUM_USERS
    ).clip(0.02, 1.0)
    users["taste_noise"] = rng.normal(0.0, NOISE_SCALE, NUM_USERS)

    log.info("Generated %d users", NUM_USERS)
    return users


def generate_sessions(
    priors: pd.DataFrame, users: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    """Generate one row per user x content viewing session.

    Content choice is popularity-weighted with deterministic per-user
    noise; completion is beta-distributed around the content quality prior;
    watch duration scales with completion and runtime; pauses rise as
    completion falls.

    Args:
        priors: Catalog with prior columns and usable runtimes.
        users: User propensity dataframe.
        rng: Seeded numpy Generator.

    Returns:
        viewer_sessions dataframe.
    """
    content_ids = priors["content_id"].to_numpy()
    weights = (
        0.15 + 0.85 * priors["popularity_score"].to_numpy()
    )
    weights = weights / weights.sum()
    runtimes = priors.set_index("content_id")["runtime_minutes"]
    rating_scores = priors.set_index("content_id")["rating_score"]

    months = pd.period_range(
        SESSIONS_START,
        periods=SESSIONS_LEAD_MONTHS + OBSERVATION_MONTHS,
        freq="M",
    )

    rows = []
    session_counter = 0

    for _, user in users.iterrows():
        propensity = user["engagement_propensity"]
        taste_noise = user["taste_noise"]

        for month in months:
            rate_scale = 0.5 + 5.0 * propensity
            base_draw = rng.pareto(SESSIONS_PARETO_SHAPE)
            n_sessions = int(min(base_draw * rate_scale, SESSIONS_BASE_HIGH))

            if n_sessions <= 0:
                continue

            chosen = rng.choice(
                content_ids, size=n_sessions, p=weights, replace=True
            )
            for content_id in chosen:
                session_counter += 1
                runtime = float(runtimes.loc[content_id])

                quality = float(rating_scores.loc[content_id])
                effective = np.clip(
                    quality
                    + ENGAGEMENT_COMPLETION_COUPLING * (propensity - 0.5)
                    + taste_noise,
                    0.05, 0.95,
                )

                alpha = COMPLETION_CONCENTRATION * effective
                beta = COMPLETION_CONCENTRATION * (1.0 - effective)
                completion = float(rng.beta(alpha, beta))

                day = int(rng.integers(1, month.days_in_month + 1))
                started_at = datetime(
                    month.year, month.month, day,
                    hour=int(rng.integers(6, 24)),
                    minute=int(rng.integers(0, 60)),
                )

                watch_fraction = np.clip(
                    0.15 + 0.85 * completion + rng.normal(0.0, 0.05), 0.05, 1.0
                )
                watch_duration = round(
                    runtime * watch_fraction * MAX_WATCH_DURATION_FRACTION, 1
                )
                watch_duration = max(0.5, watch_duration)

                pause_level = np.clip(
                    PAUSE_BASE_LOW + (1.0 - completion) * PAUSE_BASE_HIGH
                    + rng.normal(0.0, 0.5), 0.0, float(PAUSE_MAX)
                )
                pause_count = int(round(pause_level))

                completion_pct = round(completion * 100.0, 1)
                finished = bool(completion_pct >= 90.0)

                rows.append(
                    {
                        "user_id": user["user_id"],
                        "session_id": f"S{session_counter:07d}",
                        "content_id": int(content_id),
                        "started_at": started_at.strftime("%Y-%m-%d %H:%M"),
                        "watch_duration_minutes": watch_duration,
                        "pause_count": pause_count,
                        "completion_pct": completion_pct,
                        "finished": finished,
                    }
                )

    sessions = pd.DataFrame(rows)
    log.info("Generated %d session rows", len(sessions))
    return sessions


def generate_retention(
    sessions: pd.DataFrame,
    retention_all_users: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Derive user-level retention outcomes from the session records.

    Semantics (documented simulation assumptions):
      eligible_for_30d_retention = the user was an active viewer on or
      before the observation date (>= 1 session to date, comparing
      calendar dates). Ineligible users (never watched) are kept in the
      denominator with retained_30d=False.
      retained_30d = the user started >= 1 session in the 30 days after
      the observation date. Only eligible users can be retained; a user
      whose first session falls inside the window is not part of that
      month's cohort yet. A user may be retained without finishing any
      movie: retention means returning to the platform.

    Args:
        sessions: Generated session dataframe.
        retention_all_users: Full user list from generate_users.
        rng: Seeded numpy Generator (kept for interface symmetry).

    Returns:
        viewer_retention dataframe covering every user x observation month.
    """
    sessions = sessions.copy()
    sessions["started_dt"] = pd.to_datetime(sessions["started_at"])
    # Calendar dates: a session any time on the observation date is
    # "on or before" it (timestamps carry an hour-of-day, dates do not).
    sessions["started_date"] = sessions["started_dt"].dt.normalize()

    months = pd.period_range(
        OBSERVATION_START, periods=OBSERVATION_MONTHS, freq="M"
    )

    session_by_user = {
        user: group["started_date"].sort_values().reset_index(drop=True)
        for user, group in sessions.groupby("user_id")
    }
    window = np.timedelta64(30, "D")
    rows = []
    for month in months:
        observation_np = np.datetime64(
            f"{month.year:04d}-{month.month:02d}-{RETENTION_OBSERVATION_DAY:02d}"
        )
        window_end_np = observation_np + window
        observation_label = str(observation_np)

        for user in retention_all_users["user_id"]:
            started = session_by_user.get(user)
            if started is None:
                eligible = False
                retained = False
            else:
                started_np = started.to_numpy()
                eligible = bool((started_np <= observation_np).any())
                if not eligible:
                    retained = False
                else:
                    in_window = (started_np > observation_np) & (
                        started_np <= window_end_np
                    )
                    retained = bool(in_window.any())

            rows.append(
                {
                    "user_id": user,
                    "observation_date": observation_label,
                    "eligible_for_30d_retention": eligible,
                    "retained_30d": retained,
                }
            )

    retention = pd.DataFrame(rows)
    log.info("Generated %d retention rows", len(retention))
    return retention


# --- validation ----------------------------------------------------------------

def validate_generated(
    sessions: pd.DataFrame,
    retention: pd.DataFrame,
    catalog: pd.DataFrame,
    users: pd.DataFrame,
) -> dict:
    """Check the generated data against the domain rules before writing.

    Args:
        sessions: Generated sessions.
        retention: Generated retention records.
        catalog: Normalized catalog (join parent).

    Returns:
        Validation summary dict; raises ValueError on rule violations.
    """
    runtime_map = catalog.set_index("content_id")["runtime_minutes"]

    checks = {
        "sessions_non_empty": len(sessions) > 0,
        "watch_duration_within_runtime": bool(
            (
                sessions["watch_duration_minutes"]
                <= sessions["content_id"].map(runtime_map)
            ).all()
        ),
        "watch_duration_non_negative": bool(
            (sessions["watch_duration_minutes"] >= 0).all()
        ),
        "pause_count_non_negative": bool((sessions["pause_count"] >= 0).all()),
        "completion_within_0_100": bool(
            sessions["completion_pct"].between(0, 100).all()
        ),
        "finished_matches_rule": bool(
            (
                sessions["finished"]
                == (sessions["completion_pct"] >= 90.0)
            ).all()
        ),
        "no_orphan_content_ids": bool(
            sessions["content_id"].isin(catalog["content_id"]).all()
        ),
        "retention_users_match_sessions": bool(
            set(retention["user_id"])
            == set(users["user_id"])
        ),
        "retention_boolean_fields": bool(
            retention["eligible_for_30d_retention"].isin([True, False]).all()
            and retention["retained_30d"].isin([True, False]).all()
        ),
        "retained_implies_eligible": bool(
            (
                ~retention["retained_30d"]
                | retention["eligible_for_30d_retention"]
            ).all()
        ),
    }

    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(
            "Generated data failed validation: " + ", ".join(failed)
        )

    log.info("Generated data passed all %d validation checks", len(checks))
    return checks


# --- output --------------------------------------------------------------------

def write_outputs(
    sessions: pd.DataFrame,
    retention: pd.DataFrame,
    checks: dict,
    catalog_path: Path,
    generated_dir: Path,
    reports_dir: Path,
    seed: int,
) -> None:
    """Write generated tables and the generation metadata JSON.

    Args:
        sessions: Validated session dataframe.
        retention: Validated retention dataframe.
        checks: Validation check dict for the metadata record.
        catalog_path: Path of the input catalog (recorded in metadata).
        generated_dir: Destination directory for the generated CSVs.
        reports_dir: Destination directory for the metadata JSON.
        seed: Seed used for the generation run.
    """
    generated_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    sessions_path = generated_dir / "viewer_sessions.csv"
    retention_path = generated_dir / "viewer_retention.csv"

    sessions.to_csv(sessions_path, index=False)
    retention.to_csv(retention_path, index=False)

    metadata = {
        "seed": seed,
        "formula_version": FORMULA_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_catalog": str(catalog_path),
        "row_counts": {
            "viewer_sessions": len(sessions),
            "viewer_retention": len(retention),
        },
        "parameters": {
            "num_users": NUM_USERS,
            "observation_months": OBSERVATION_MONTHS,
            "observation_start": OBSERVATION_START,
            "sessions_start": SESSIONS_START,
            "sessions_lead_months": SESSIONS_LEAD_MONTHS,
            "sessions_pareto_shape": SESSIONS_PARETO_SHAPE,
            "sessions_month_cap": SESSIONS_BASE_HIGH,
            "completion_concentration": COMPLETION_CONCENTRATION,
            "noise_scale": NOISE_SCALE,
            "engagement_completion_coupling": ENGAGEMENT_COMPLETION_COUPLING,
            "pause_cap": PAUSE_MAX,
            "min_runtime_minutes": MIN_RUNTIME_MINUTES,
        },
        "assumptions": [
            "Content priors use vote_average (quality), log-scaled popularity",
            "(exposure) and vote_count percentile rank (confidence proxy).",
            "They bias sampling only; they are not observed causes of",
            "retention. All behaviour data is synthetic.",
            "Sessions are generated from sessions_start, one burn-in month",
            "before the first observation, so the first observed cohort",
            "contains eligible users.",
            "retained_30d = eligible user with at least one session in the",
            "30 days after the observation date; a user whose first",
            "session falls inside the window is not in that cohort yet.",
            "eligible_for_30d_retention = user had at least one session on",
            "or before the observation date (calendar-date comparison);",
            "never-active users remain in the denominator with",
            "retained_30d=False.",
            "Higher user engagement moderately increases completion",
            f"(coupling={ENGAGEMENT_COMPLETION_COUPLING}); the",
            "engagement-retention association is a simulation assumption.",
            "Users may be retained without finishing a movie: retention",
            "means returning to the platform, not completing an item.",
        ],
        "validation_checks": checks,
        "sessions_sha256": hashlib.sha256(
            sessions_path.read_bytes()
        ).hexdigest(),
        "retention_sha256": hashlib.sha256(
            retention_path.read_bytes()
        ).hexdigest(),
    }

    metadata_path = reports_dir / "generation_metadata.json"
    with metadata_path.open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)

    log.info("Wrote %s", sessions_path)
    log.info("Wrote %s", retention_path)
    log.info("Wrote metadata %s", metadata_path)


# --- orchestration ---------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Run the synthetic behaviour generation stage.

    Args:
        argv: Optional CLI arguments (defaults to sys.argv[1:]).

    Returns:
        Process exit code: 0 on success, 1 on failure.
    """
    parser = argparse.ArgumentParser(
        description="Generate synthetic viewer sessions and retention data."
    )
    parser.add_argument(
        "--catalog", default="data/processed/content_catalog.csv",
        help="Path to the normalized content catalog CSV",
    )
    parser.add_argument(
        "--output", default="data/generated",
        help="Directory for generated data (default: data/generated)",
    )
    parser.add_argument(
        "--seed", type=int, default=SEED,
        help=f"Random seed (default: {SEED})",
    )
    args = parser.parse_args(argv)

    catalog_path = Path(args.catalog)
    generated_dir = Path(args.output)
    reports_dir = Path("output/reports")

    try:
        if not catalog_path.exists():
            raise FileNotFoundError(
                f"Normalized catalog not found at '{catalog_path}'. "
                "Run scripts/normalize_catalog.py first."
            )

        log.info("Stage 1/4: loading catalog and computing priors")
        catalog = pd.read_csv(catalog_path)
        priors = compute_content_priors(catalog)

        rng = np.random.default_rng(args.seed)
        log.info("Stage 2/4: generating users and sessions (seed=%d)", args.seed)
        users = generate_users(rng)
        sessions = generate_sessions(priors, users, rng)

        log.info("Stage 3/4: deriving retention from session records")
        retention = generate_retention(sessions, users, rng)

        log.info("Stage 4/4: validating generated data")
        checks = validate_generated(sessions, retention, catalog, users)

        write_outputs(
            sessions, retention, checks,
            catalog_path, generated_dir, reports_dir, args.seed,
        )
        log.info("Generation finished successfully.")
        return 0
    except (FileNotFoundError, ValueError) as exc:
        log.error("Generation failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
