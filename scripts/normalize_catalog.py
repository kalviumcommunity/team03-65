"""Normalize the raw TMDB movie catalog into the working content catalog.

Pipeline position
-----------------
raw catalog (data/raw/) -> THIS SCRIPT -> data/processed/content_catalog.csv
                                        output/reports/intake_report.json
                                        output/reports/profile_report.json
                                        output/reports/validation_report.json
                                        output/reports/validation_failures.csv

Stages (each fails fast with an actionable error):
1. Intake validation     - file exists, non-empty, readable, expected columns.
2. Profiling             - nulls, duplicates, dtypes, numeric ranges.
3. Normalization         - rename id->content_id, runtime->runtime_minutes,
                           parse release_date, split genres into a list,
                           keep the 10 catalog columns defined in the data model.
4. Domain validation     - unique non-null content IDs, positive runtime,
                           vote_average range, non-negative vote_count/popularity,
                           parsed release dates. Failures are isolated to a CSV,
                           never silently dropped.

The raw file is never modified.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd

# --- configuration constants -------------------------------------------------

RAW_COLUMNS = [
    "id", "title", "vote_average", "vote_count", "status", "release_date",
    "revenue", "runtime", "adult", "backdrop_path", "budget", "homepage",
    "imdb_id", "original_language", "original_title", "overview",
    "popularity", "poster_path", "tagline", "genres",
    "production_companies", "production_countries", "spoken_languages",
    "keywords",
]

REQUIRED_COLUMNS = [
    "id", "title", "vote_average", "vote_count", "release_date",
    "runtime", "popularity", "genres", "original_language", "overview",
]

CATALOG_COLUMNS = [
    "content_id", "title", "release_date", "runtime_minutes",
    "vote_average", "vote_count", "popularity", "genres",
    "original_language", "overview",
]

RENAME_MAP = {"id": "content_id", "runtime": "runtime_minutes"}

VOTE_AVERAGE_RANGE = (0.0, 10.0)
POSITIVE_RUNTIME_MIN = 1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("normalize_catalog")


# --- intake -------------------------------------------------------------------

def validate_intake(raw_path: Path) -> dict:
    """Check that the raw file exists, is non-empty and is a supported format.

    Args:
        raw_path: Path to the raw catalog CSV.

    Returns:
        A dict of baseline intake metrics (rows, columns, file size in MB).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is empty or not a CSV.
    """
    if not raw_path.exists():
        raise FileNotFoundError(
            f"Raw catalog not found at '{raw_path}'. "
            "Place the source CSV in data/raw/ before running the pipeline."
        )
    if raw_path.stat().st_size == 0:
        raise ValueError(f"Raw catalog '{raw_path}' is empty (0 bytes).")

    size_mb = raw_path.stat().st_size / (1024 * 1024)
    if raw_path.suffix.lower() != ".csv":
        raise ValueError(
            f"Unsupported format '{raw_path.suffix}'. Only .csv is supported."
        )

    header = pd.read_csv(raw_path, nrows=0)
    columns = list(header.columns)
    missing = [c for c in REQUIRED_COLUMNS if c not in columns]

    if missing:
        raise ValueError(
            "Schema validation failed. Missing required columns: "
            + ", ".join(missing)
        )
    extra = [c for c in columns if c not in RAW_COLUMNS]
    if extra:
        log.warning("Unexpected extra columns present: %s", ", ".join(extra))

    row_count = sum(1 for _ in raw_path.open(encoding="utf-8")) - 1

    report = {
        "file": str(raw_path),
        "size_mb": round(size_mb, 2),
        "format": "csv",
        "encoding": "utf-8",
        "row_count": row_count,
        "column_count": len(columns),
        "columns": columns,
        "missing_columns": [],
        "extra_columns": extra,
        "status": "passed",
    }
    log.info(
        "Intake passed: %d rows, %d columns, %.2f MB",
        report["row_count"], report["column_count"], report["size_mb"],
    )
    return report


# --- profiling ----------------------------------------------------------------

def profile_catalog(df: pd.DataFrame) -> dict:
    """Profile the raw catalog before any cleaning decision is made.

    Args:
        df: Raw catalog dataframe (as read).

    Returns:
        Completeness, uniqueness, type and range statistics per column.
    """
    total_rows = len(df)
    numeric_cols = ["vote_average", "vote_count", "runtime", "popularity",
                    "revenue", "budget"]

    null_counts = df.isna().sum().to_dict()
    completeness = {
        col: {
            "null_count": int(n),
            "null_pct": round(100.0 * n / total_rows, 2),
        }
        for col, n in null_counts.items()
    }

    exact_duplicates = int(df.duplicated().sum())
    duplicate_ids = int(df["id"].duplicated().sum())

    numeric_ranges = {}
    for col in numeric_cols:
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            numeric_ranges[col] = {
                "min": None if pd.isna(s.min()) else float(s.min()),
                "max": None if pd.isna(s.max()) else float(s.max()),
                "mean": None if pd.isna(s.mean()) else round(float(s.mean()), 3),
                "median": None if pd.isna(s.median()) else float(s.median()),
            }

    report = {
        "total_rows": total_rows,
        "completeness": completeness,
        "exact_duplicate_rows": exact_duplicates,
        "duplicate_content_ids": duplicate_ids,
        "duplicate_row_pct": round(100.0 * exact_duplicates / total_rows, 2)
        if total_rows else 0.0,
        "numeric_ranges": numeric_ranges,
        "date_parse_failures": int(
            pd.to_datetime(df["release_date"], errors="coerce").isna().sum()
        ),
        "status": "completed",
    }
    log.info(
        "Profile complete: %d rows, %d exact duplicates, %d duplicate ids, "
        "%d date parse failures",
        report["total_rows"], report["exact_duplicate_rows"],
        report["duplicate_content_ids"], report["date_parse_failures"],
    )
    return report


# --- normalization ------------------------------------------------------------

def normalize_catalog(df: pd.DataFrame) -> pd.DataFrame:
    """Transform the raw catalog into the working content catalog.

    Renames id->content_id and runtime->runtime_minutes, parses
    release_date, splits the comma-separated genres field into a list,
    and selects the 10 catalog columns from the data model.

    Args:
        df: Raw catalog dataframe.

    Returns:
        Normalized catalog dataframe with CATALOG_COLUMNS columns.

    Raises:
        ValueError: If required columns are missing after rename.
    """
    df = df.copy()
    df = df.rename(columns=RENAME_MAP)

    missing = [c for c in CATALOG_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "Normalization failed. Missing columns after rename: "
            + ", ".join(missing)
        )

    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["genres"] = (
        df["genres"]
        .fillna("")
        .astype(str)
        .apply(lambda s: [g.strip() for g in s.split(",") if g.strip()])
    )
    df["content_id"] = pd.to_numeric(df["content_id"], errors="coerce")
    df["vote_average"] = pd.to_numeric(df["vote_average"], errors="coerce")
    df["vote_count"] = pd.to_numeric(df["vote_count"], errors="coerce")
    df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce")
    df["runtime_minutes"] = pd.to_numeric(df["runtime_minutes"], errors="coerce")
    df["title"] = df["title"].astype(str).str.strip()
    df["overview"] = df["overview"].fillna("").astype(str).str.strip()
    df["original_language"] = (
        df["original_language"].fillna("unknown").astype(str).str.strip()
    )

    df = df[CATALOG_COLUMNS]
    log.info("Normalized catalog: %d rows x %d columns", *df.shape)
    return df


# --- domain validation ---------------------------------------------------------

def validate_catalog(df: pd.DataFrame) -> dict:
    """Apply domain validation rules to the normalized catalog.

    Rules: unique non-null content_id; positive runtime; vote_average in
    0..10; non-negative vote_count and popularity; parsed release_date.

    Args:
        df: Normalized catalog dataframe.

    Returns:
        Validation report with per-rule pass/fail counts and overall status.
    """
    rules = {
        "content_id_unique": df["content_id"].is_unique,
        "content_id_not_null": df["content_id"].notna().all(),
        "runtime_positive": (
            df["runtime_minutes"].dropna() >= POSITIVE_RUNTIME_MIN
        ).all(),
        "vote_average_in_range": (
            df["vote_average"]
            .dropna()
            .between(*VOTE_AVERAGE_RANGE, inclusive="both")
            .all()
        ),
        "vote_count_non_negative": (df["vote_count"].dropna() >= 0).all(),
        "popularity_non_negative": (df["popularity"].dropna() >= 0).all(),
        "release_date_parsed": (
            df["release_date"].notna().sum() > 0
        ),
    }

    failures = pd.DataFrame(index=df.index)
    failures["invalid_content_id"] = df["content_id"].isna() | df["content_id"].duplicated()
    failures["invalid_runtime"] = (
        df["runtime_minutes"].isna() | (df["runtime_minutes"] < POSITIVE_RUNTIME_MIN)
    )
    failures["invalid_vote_average"] = (
        df["vote_average"].isna()
        | ~df["vote_average"].between(*VOTE_AVERAGE_RANGE, inclusive="both")
    )
    failures["invalid_vote_count"] = df["vote_count"].isna() | (df["vote_count"] < 0)
    failures["invalid_popularity"] = df["popularity"].isna() | (df["popularity"] < 0)
    failures["invalid_release_date"] = df["release_date"].isna()

    any_failure = failures.any(axis=1)

    report = {
        "total_records": len(df),
        "rules": {name: bool(ok) for name, ok in rules.items()},
        "records_passed": int((~any_failure).sum()),
        "records_failed": int(any_failure.sum()),
        "status": "passed" if not any_failure.any() else "failed",
    }
    log.info(
        "Validation: %d/%d records passed (%s)",
        report["records_passed"], report["total_records"], report["status"],
    )
    return report, failures[any_failure]


# --- output --------------------------------------------------------------------

def write_outputs(
    df: pd.DataFrame,
    failures: pd.DataFrame,
    reports: dict,
    processed_path: Path,
    reports_dir: Path,
) -> None:
    """Write the normalized catalog and all validation reports.

    Args:
        df: Normalized catalog dataframe.
        failures: Dataframe of records failing any domain rule.
        reports: Dict of report name -> report dict.
        processed_path: Destination for the normalized catalog CSV.
        reports_dir: Destination directory for JSON reports.
    """
    reports_dir.mkdir(parents=True, exist_ok=True)
    processed_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(processed_path, index=False)
    log.info("Wrote %d rows to %s", len(df), processed_path)

    for name, payload in reports.items():
        target = reports_dir / f"{name}.json"
        with target.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)
        log.info("Wrote report %s", target)

    failures_path = reports_dir / "validation_failures.csv"
    failures.to_csv(failures_path, index=False)
    log.info("Wrote %d failed records to %s", len(failures), failures_path)


# --- orchestration -------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Run the catalog normalization pipeline.

    Args:
        argv: Optional CLI arguments (defaults to sys.argv[1:]).

    Returns:
        Process exit code: 0 on success, 1 on failure.
    """
    parser = argparse.ArgumentParser(
        description="Normalize the raw TMDB catalog into the working content catalog."
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to the raw catalog CSV (e.g. data/raw/tmdb_catalog.csv)",
    )
    parser.add_argument(
        "--output", default="data/processed",
        help="Directory for the processed catalog (default: data/processed)",
    )
    args = parser.parse_args(argv)

    raw_path = Path(args.input)
    processed_dir = Path(args.output)
    processed_path = processed_dir / "content_catalog.csv"
    reports_dir = Path("output/reports")

    try:
        log.info("Stage 1/4: intake validation")
        intake = validate_intake(raw_path)

        log.info("Stage 2/4: profiling")
        df = pd.read_csv(raw_path)
        profile = profile_catalog(df)

        log.info("Stage 3/4: normalization")
        catalog = normalize_catalog(df)

        log.info("Stage 4/4: domain validation")
        validation, failures = validate_catalog(catalog)

        write_outputs(
            catalog, failures,
            {
                "intake_report": intake,
                "profile_report": profile,
                "validation_report": validation,
            },
            processed_path, reports_dir,
        )

        log.info("Pipeline finished successfully.")
        return 0
    except (FileNotFoundError, ValueError) as exc:
        log.error("Pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
