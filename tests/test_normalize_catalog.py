"""Tests for scripts/normalize_catalog.py (LU 2.14/2.16/2.24 coverage)."""

from pathlib import Path

import pandas as pd
import pytest

import normalize_catalog as nc


class TestIntake:
    def test_intake_passes_on_valid_file(self, raw_csv):
        report = nc.validate_intake(raw_csv)
        assert report["status"] == "passed"
        assert report["row_count"] == 6
        assert report["column_count"] == 13
        assert report["missing_columns"] == []

    def test_intake_fails_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            nc.validate_intake(tmp_path / "nope.csv")

    def test_intake_fails_on_empty_file(self, tmp_path):
        empty = tmp_path / "empty.csv"
        empty.write_text("")
        with pytest.raises(ValueError, match="empty"):
            nc.validate_intake(empty)

    def test_intake_fails_on_missing_columns(self, tmp_path):
        bad = tmp_path / "bad.csv"
        bad.write_text("id,title,runtime\n1,Some Movie,100\n")
        with pytest.raises(ValueError, match="Missing required columns"):
            nc.validate_intake(bad)

    def test_intake_fails_on_wrong_format(self, tmp_path):
        bad = tmp_path / "bad.xlsx"
        bad.write_text("x")
        with pytest.raises(ValueError, match="Unsupported format"):
            nc.validate_intake(bad)


class TestProfiling:
    def test_profile_reports_counts(self, raw_csv):
        df = pd.read_csv(raw_csv)
        profile = nc.profile_catalog(df)
        assert profile["total_rows"] == 6
        assert profile["exact_duplicate_rows"] == 0
        assert profile["duplicate_content_ids"] == 0
        assert "runtime" in profile["numeric_ranges"]
        assert profile["numeric_ranges"]["runtime"]["min"] == 117.0


class TestNormalization:
    def test_renames_and_selects_columns(self, raw_csv):
        df = pd.read_csv(raw_csv)
        out = nc.normalize_catalog(df)
        assert list(out.columns) == nc.CATALOG_COLUMNS
        assert out["content_id"].tolist() == [27205, 157336, 155, 603, 597, 122]
        assert (out["runtime_minutes"] == [148, 169, 152, 117, 155, 179]).all()

    def test_genres_become_lists(self, raw_csv):
        df = pd.read_csv(raw_csv)
        out = nc.normalize_catalog(df)
        assert out.loc[0, "genres"] == ["Action", "Science Fiction", "Adventure"]
        assert isinstance(out.loc[1, "genres"], list)

    def test_release_date_parsed(self, raw_csv):
        df = pd.read_csv(raw_csv)
        out = nc.normalize_catalog(df)
        parsed = pd.to_datetime(out["release_date"], errors="coerce")
        assert parsed.notna().all()
        assert parsed.iloc[0] == pd.Timestamp("2010-07-15")


class TestDomainValidation:
    def test_all_rules_pass_on_clean_fixture(self, raw_csv):
        df = pd.read_csv(raw_csv)
        catalog = nc.normalize_catalog(df)
        report, failures = nc.validate_catalog(catalog)
        assert report["status"] == "passed"
        assert report["records_failed"] == 0
        assert len(failures) == 0

    def test_zero_runtime_is_isolated(self, raw_csv):
        df = pd.read_csv(raw_csv)
        df.loc[0, "runtime"] = 0
        catalog = nc.normalize_catalog(df)
        report, failures = nc.validate_catalog(catalog)
        assert report["status"] == "failed"
        assert report["records_failed"] == 1
        assert failures["invalid_runtime"].iloc[0]

    def test_duplicate_id_is_flagged(self, raw_csv):
        df = pd.read_csv(raw_csv)
        df.loc[1, "id"] = df.loc[0, "id"]
        catalog = nc.normalize_catalog(df)
        report, failures = nc.validate_catalog(catalog)
        assert report["rules"]["content_id_unique"] is False
        assert report["records_failed"] >= 1


class TestPipelineEndToEnd:
    def test_main_writes_outputs(self, tmp_path, raw_csv, monkeypatch):
        monkeypatch.chdir(tmp_path)
        processed = tmp_path / "processed"
        reports = tmp_path / "reports"
        exit_code = nc.main(
            ["--input", str(raw_csv), "--output", str(processed)]
        )
        assert exit_code == 0
        catalog = pd.read_csv(processed / "content_catalog.csv")
        assert len(catalog) == 6
        reports = tmp_path / "output" / "reports"
        for name in ("intake_report", "profile_report", "validation_report"):
            assert (reports / f"{name}.json").exists()
        assert (reports / "validation_failures.csv").exists()
