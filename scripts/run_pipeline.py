"""One-command orchestrator for the full data pipeline.

Pipeline position
-----------------
raw catalog (data/raw/)
    -> scripts/normalize_catalog.py    (catalog intake, profiling,
                                        normalization, validation)
    -> scripts/generate_behavior.py    (seeded synthetic sessions +
                                        retention)
    -> [future: scripts/build_db.py]   (SQLite tables + KPI views)

This script chains the existing stage modules through their public
``main(argv) -> int`` entry points, so a single command reproduces every
output and report from the raw source. Each stage's outputs are verified
(exists, non-empty, expected columns) before the run is declared
successful; a stage failure aborts the run with an actionable error
instead of continuing with stale or partial data.

Examples
--------
Full pipeline from the raw catalog::

    python scripts/run_pipeline.py --input data/raw/tmdb_catalog.csv

Same, with an explicit seed::

    python scripts/run_pipeline.py --input data/raw/tmdb_catalog.csv --seed 42

Skip behaviour generation and reuse existing outputs (catalog stage
only, useful when iterating on downstream SQL work)::

    python scripts/run_pipeline.py --input data/raw/tmdb_catalog.csv \\
        --skip-generation

Run only a subset of stages::

    python scripts/run_pipeline.py --stages normalize
    python scripts/run_pipeline.py --stages generate
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_behavior  # noqa: E402
import normalize_catalog  # noqa: E402

# --- configuration constants -------------------------------------------------
# All defaults are CWD-relative, matching the convention of the stage
# scripts (normalize_catalog.py / generate_behavior.py). Run the
# orchestrator from the repository root as documented in the README.

DEFAULT_RAW_INPUT = Path("data/raw/tmdb_catalog.csv")
DEFAULT_PROCESSED_DIR = Path("data/processed")
DEFAULT_GENERATED_DIR = Path("data/generated")
DEFAULT_REPORTS_DIR = Path("output/reports")

STAGES = ("normalize", "generate")

# Stage -> module exposing main(argv) -> int. The build_db stage is
# reserved for the SQL KPI layer PR and will be appended here once
# scripts/build_db.py lands.
STAGE_REGISTRY = {
    "normalize": normalize_catalog,
    "generate": generate_behavior,
}

# Outputs each stage must produce for the run to count as successful.
# Maps stage -> list of (path_builder, required_columns). Reports always
# land in DEFAULT_REPORTS_DIR: the stage scripts hardcode "output/reports"
# relative to CWD, so the orchestrator verifies them at that same path.
STAGE_OUTPUTS = {
    "normalize": [
        (
            lambda args: Path(args.processed_dir) / "content_catalog.csv",
            ["content_id", "title", "release_date", "runtime_minutes",
             "vote_average", "vote_count", "popularity", "genres",
             "original_language", "overview"],
        ),
        (
            lambda args: DEFAULT_REPORTS_DIR / "intake_report.json",
            None,
        ),
        (
            lambda args: DEFAULT_REPORTS_DIR / "profile_report.json",
            None,
        ),
        (
            lambda args: DEFAULT_REPORTS_DIR / "validation_report.json",
            None,
        ),
    ],
    "generate": [
        (
            lambda args: Path(args.generated_dir) / "viewer_sessions.csv",
            ["user_id", "session_id", "content_id", "started_at",
             "watch_duration_minutes", "pause_count", "completion_pct",
             "finished"],
        ),
        (
            lambda args: Path(args.generated_dir) / "viewer_retention.csv",
            ["user_id", "observation_date", "eligible_for_30d_retention",
             "retained_30d"],
        ),
        (
            lambda args: DEFAULT_REPORTS_DIR / "generation_metadata.json",
            None,
        ),
    ],
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("run_pipeline")


# --- output verification --------------------------------------------------------

def verify_outputs(stage: str, args: argparse.Namespace) -> None:
    """Verify that a stage produced all expected, non-empty outputs.

    Args:
        stage: Stage name whose outputs should be checked.
        args: Parsed CLI namespace carrying the output directories.

    Raises:
        RuntimeError: If an expected output file is missing, empty, or
            missing required columns.
    """
    for path_builder, required_columns in STAGE_OUTPUTS[stage]:
        path = path_builder(args)
        if not path.exists():
            raise RuntimeError(
                f"Stage '{stage}' finished but expected output "
                f"'{path}' was not created. Inspect the stage logs above; "
                "the pipeline will not continue with missing data."
            )
        if path.stat().st_size == 0:
            raise RuntimeError(
                f"Stage '{stage}' produced an empty file '{path}'. "
                "The pipeline will not continue with empty data."
            )
        if required_columns is not None:
            header = pd.read_csv(path, nrows=0)
            missing = [
                c for c in required_columns if c not in header.columns
            ]
            if missing:
                raise RuntimeError(
                    f"Stage '{stage}' output '{path}' is missing expected "
                    f"columns: {', '.join(missing)}."
                )
        log.info("Verified output %s", path)


def csv_row_count(path: Path) -> int:
    """Return the data row count of a CSV (excluding the header).

    Args:
        path: Path to a CSV file with a header row.

    Returns:
        Number of data rows.
    """
    with path.open(encoding="utf-8") as fh:
        return sum(1 for _ in fh) - 1


def run_stage(stage: str, args: argparse.Namespace) -> None:
    """Execute one pipeline stage and verify its outputs.

    Args:
        stage: Stage name from STAGES.
        args: Parsed CLI namespace carrying input/output paths and seed.

    Raises:
        RuntimeError: If the stage returns a non-zero exit code or its
            outputs fail verification.
    """
    if stage == "normalize":
        argv = ["--input", str(args.input), "--output", args.processed_dir]
    elif stage == "generate":
        argv = [
            "--catalog",
            str(Path(args.processed_dir) / "content_catalog.csv"),
            "--output",
            args.generated_dir,
            "--seed",
            str(args.seed),
            "--num-users",
            str(args.num_users),
        ]
    else:  # pragma: no cover - guarded by STAGES membership check
        raise RuntimeError(f"Unknown stage '{stage}'.")

    module = STAGE_REGISTRY[stage]
    log.info("=== Stage %s (%s) ===", stage, module.__name__)

    try:
        exit_code = module.main(argv)
    except Exception as exc:  # surface a traceback with stage context
        log.error("Stage '%s' raised %s: %s", stage, type(exc).__name__, exc)
        raise RuntimeError(f"Stage '{stage}' crashed.") from exc

    if exit_code != 0:
        raise RuntimeError(
            f"Stage '{stage}' exited with code {exit_code}. "
            "Fix the reported issue and re-run the pipeline."
        )

    verify_outputs(stage, args)

    if stage == "normalize":
        catalog_path = Path(args.processed_dir) / "content_catalog.csv"
        log.info(
            "Stage '%s' summary: %d catalog rows", stage,
            csv_row_count(catalog_path),
        )
    elif stage == "generate":
        sessions = Path(args.generated_dir) / "viewer_sessions.csv"
        retention = Path(args.generated_dir) / "viewer_retention.csv"
        log.info(
            "Stage '%s' summary: %d session rows, %d retention rows",
            stage, csv_row_count(sessions), csv_row_count(retention),
        )


# --- orchestration ---------------------------------------------------------------

def resolve_stages(requested: str, skip_generation: bool) -> list[str]:
    """Resolve the ordered list of stages to run.

    Args:
        requested: Comma-separated stage names, or "all".
        skip_generation: Whether --skip-generation was passed.

    Returns:
        Ordered list of stage names.

    Raises:
        ValueError: If an unknown stage name was requested, or the
            combination of arguments is contradictory.
    """
    if requested != "all":
        requested_list = [s.strip() for s in requested.split(",") if s.strip()]
        unknown = [s for s in requested_list if s not in STAGES]
        if unknown:
            raise ValueError(
                f"Unknown stage(s): {', '.join(unknown)}. "
                f"Valid stages: {', '.join(STAGES)} (or 'all')."
            )
        # Canonical dependency order, independent of request order.
        stages = [s for s in STAGES if s in requested_list]
    else:
        stages = list(STAGES)

    if skip_generation:
        stages = [s for s in stages if s != "generate"]

    if not stages:
        raise ValueError(
            "No stages to run: --skip-generation removed every requested "
            "stage. Request at least 'normalize' or 'all'."
        )
    return stages


def main(argv: list[str] | None = None) -> int:
    """Run the orchestrated pipeline.

    Args:
        argv: Optional CLI arguments (defaults to sys.argv[1:]).

    Returns:
        Process exit code: 0 on success, 1 on failure.
    """
    parser = argparse.ArgumentParser(
        description="One-command orchestration: raw catalog -> normalized "
        "catalog -> synthetic viewer behaviour data.",
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_RAW_INPUT),
        help=f"Path to the raw catalog CSV (default: {DEFAULT_RAW_INPUT})",
    )
    parser.add_argument(
        "--processed-dir",
        default=str(DEFAULT_PROCESSED_DIR),
        help=f"Directory for processed outputs "
        f"(default: {DEFAULT_PROCESSED_DIR})",
    )
    parser.add_argument(
        "--generated-dir",
        default=str(DEFAULT_GENERATED_DIR),
        help=f"Directory for generated behaviour data "
        f"(default: {DEFAULT_GENERATED_DIR})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=generate_behavior.SEED,
        help=f"Random seed for the behaviour generator "
        f"(default: {generate_behavior.SEED})",
    )
    parser.add_argument(
        "--num-users",
        type=int,
        default=generate_behavior.DEFAULT_NUM_USERS,
        help="Number of synthetic users to generate "
        f"(default: {generate_behavior.DEFAULT_NUM_USERS})",
    )
    parser.add_argument(
        "--stages",
        default="all",
        help="Comma-separated stages to run, or 'all' "
        f"(default: all; valid: {', '.join(STAGES)})",
    )
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Skip the synthetic behaviour generation stage and reuse "
        "existing generated outputs (implies 'normalize' only when stages "
        "is 'all').",
    )
    args = parser.parse_args(argv)

    try:
        stages = resolve_stages(args.stages, args.skip_generation)
    except ValueError as exc:
        log.error("Pipeline failed: %s", exc)
        return 1

    # A generate-only run needs the catalog from a previous normalize run.
    if stages == ["generate"]:
        catalog = Path(args.processed_dir) / "content_catalog.csv"
        if not catalog.exists():
            log.error(
                "Pipeline failed: generation requires the normalized "
                "catalog at '%s', which does not exist. Run the 'normalize' "
                "stage first (--stages normalize or --stages all).",
                catalog,
            )
            return 1

    for stage in stages:
        try:
            run_stage(stage, args)
        except (RuntimeError, FileNotFoundError, ValueError) as exc:
            log.error("Pipeline failed during stage '%s': %s", stage, exc)
            return 1

    log.info("Pipeline finished successfully (%s).", ", ".join(stages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
