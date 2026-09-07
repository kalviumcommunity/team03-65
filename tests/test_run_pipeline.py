"""Tests for scripts/run_pipeline.py (LU 2.58 coverage)."""

import argparse
from pathlib import Path

import pandas as pd
import pytest

import run_pipeline as rp


def run_main(monkeypatch, tmp_path, raw_csv, extra_args=None):
    """Run the orchestrator inside a tmp CWD with isolated directories.

    Returns (exit_code, processed_dir, generated_dir, reports_dir).
    """
    monkeypatch.chdir(tmp_path)
    processed = "processed"
    generated = "generated"
    argv = [
        "--input", str(raw_csv),
        "--processed-dir", processed,
        "--generated-dir", generated,
    ]
    if extra_args:
        argv.extend(extra_args)
    exit_code = rp.main(argv)
    return (
        exit_code,
        tmp_path / processed,
        tmp_path / generated,
        tmp_path / "output" / "reports",
    )


class TestResolveStages:
    def test_all_returns_both_stages_in_order(self):
        assert rp.resolve_stages("all", False) == ["normalize", "generate"]

    def test_subset_keeps_requested_order(self):
        assert rp.resolve_stages("generate,normalize", False) == [
            "normalize", "generate",
        ]

    def test_unknown_stage_raises(self):
        with pytest.raises(ValueError, match="Unknown stage"):
            rp.resolve_stages("normalize,load_db", False)

    def test_skip_generation_removes_generate(self):
        assert rp.resolve_stages("all", True) == ["normalize"]

    def test_skip_generation_removing_every_stage_raises(self):
        with pytest.raises(ValueError, match="No stages to run"):
            rp.resolve_stages("generate", True)


class TestEndToEnd:
    def test_full_pipeline_from_raw_csv(self, monkeypatch, tmp_path, raw_csv):
        """One command produces catalog, sessions, retention and reports."""
        code, processed, generated, reports = run_main(
            monkeypatch, tmp_path, raw_csv
        )
        assert code == 0

        catalog = pd.read_csv(processed / "content_catalog.csv")
        assert len(catalog) == 6

        sessions = pd.read_csv(generated / "viewer_sessions.csv")
        retention = pd.read_csv(generated / "viewer_retention.csv")
        assert not sessions.empty
        assert not retention.empty

        for name in (
            "intake_report", "profile_report", "validation_report",
            "generation_metadata",
        ):
            assert (reports / f"{name}.json").exists()

    def test_normalize_only_via_skip_generation(
        self, monkeypatch, tmp_path, raw_csv
    ):
        """--skip-generation runs normalize alone, reusing no stale data."""
        code, processed, generated, _ = run_main(
            monkeypatch, tmp_path, raw_csv, ["--skip-generation"]
        )
        assert code == 0
        assert (processed / "content_catalog.csv").exists()
        assert not (generated / "viewer_sessions.csv").exists()

    def test_generate_only_after_normalize(
        self, monkeypatch, tmp_path, raw_csv
    ):
        """--stages generate uses the existing catalog without re-running it."""
        code, processed, _, _ = run_main(
            monkeypatch, tmp_path, raw_csv, ["--skip-generation"]
        )
        assert code == 0
        # remove a report normalize would recreate, then run generate only
        reports = tmp_path / "output" / "reports"
        (reports / "intake_report.json").unlink()

        code, _, generated, _ = run_main(
            monkeypatch, tmp_path, raw_csv, ["--stages", "generate"]
        )
        assert code == 0
        assert (generated / "viewer_sessions.csv").exists()
        # normalize stage was skipped: its report was not recreated
        assert not (reports / "intake_report.json").exists()

    def test_seed_is_forwarded_to_generator(
        self, monkeypatch, tmp_path, raw_csv
    ):
        """Different seeds produce different session data."""
        code, _, gen_a, _ = run_main(
            monkeypatch, tmp_path, raw_csv, ["--seed", "123"]
        )
        assert code == 0
        sessions_a = pd.read_csv(gen_a / "viewer_sessions.csv")

        code, _, gen_b, _ = run_main(
            monkeypatch, tmp_path, raw_csv, ["--seed", "999"]
        )
        assert code == 0
        sessions_b = pd.read_csv(gen_b / "viewer_sessions.csv")

        pd.testing.assert_frame_equal(sessions_a, sessions_a)
        assert not sessions_a.equals(sessions_b)


class TestFailures:
    def test_missing_input_exits_nonzero(
        self, monkeypatch, tmp_path, raw_csv
    ):
        code, _, _, _ = run_main(
            monkeypatch, tmp_path, tmp_path / "missing.csv"
        )
        assert code == 1

    def test_generate_without_catalog_exits_nonzero(
        self, monkeypatch, tmp_path, raw_csv
    ):
        """--stages generate with no normalized catalog fails fast."""
        monkeypatch.chdir(tmp_path)
        code = rp.main(
            [
                "--input", str(raw_csv),
                "--processed-dir", "processed",
                "--generated-dir", "generated",
                "--stages", "generate",
            ]
        )
        assert code == 1

    def test_unknown_stage_flag_exits_nonzero(
        self, monkeypatch, tmp_path, raw_csv
    ):
        code, _, _, _ = run_main(
            monkeypatch, tmp_path, raw_csv, ["--stages", "load_db"]
        )
        assert code == 1


class TestVerifyOutputs:
    def make_args(self, processed_dir="processed", generated_dir="generated"):
        return argparse.Namespace(
            processed_dir=processed_dir, generated_dir=generated_dir
        )

    def test_missing_output_raises(self, tmp_path):
        args = self.make_args(str(tmp_path))
        with pytest.raises(RuntimeError, match="was not created"):
            rp.verify_outputs("normalize", args)

    def test_empty_output_raises(self, tmp_path):
        (tmp_path / "content_catalog.csv").write_text("")
        args = self.make_args(str(tmp_path))
        with pytest.raises(RuntimeError, match="empty file"):
            rp.verify_outputs("normalize", args)

    def test_missing_columns_raise(self, tmp_path):
        pd.DataFrame({"content_id": [1]}).to_csv(
            tmp_path / "content_catalog.csv", index=False
        )
        args = self.make_args(str(tmp_path))
        with pytest.raises(RuntimeError, match="missing expected columns"):
            rp.verify_outputs("normalize", args)

    def test_valid_outputs_pass(self, tmp_path):
        df = pd.DataFrame(
            {
                "content_id": [1], "title": ["x"],
                "release_date": ["2020-01-01"], "runtime_minutes": [100],
                "vote_average": [7.0], "vote_count": [10],
                "popularity": [1.0], "genres": ["Action"],
                "original_language": ["en"], "overview": ["o"],
            }
        )
        df.to_csv(tmp_path / "content_catalog.csv", index=False)
        reports = Path("output/reports")
        rp.DEFAULT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        for name in ("intake_report", "profile_report", "validation_report"):
            (rp.DEFAULT_REPORTS_DIR / f"{name}.json").write_text("{}")
        try:
            args = self.make_args(str(tmp_path))
            rp.verify_outputs("normalize", args)
        finally:
            import shutil

            shutil.rmtree("output", ignore_errors=True)
