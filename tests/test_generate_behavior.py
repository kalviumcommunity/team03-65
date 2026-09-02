"""Tests for scripts/generate_behavior.py (LU 2.24/2.25/2.26 coverage).

Reproducibility of the full 5,000-user dataset (same seed -> identical
checksums) is asserted against the real generated files when they exist;
the synthetic-distribution tests run on a small generated sample for speed.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import generate_behavior as gb

REPO_ROOT = Path(__file__).resolve().parent.parent
SESSIONS = REPO_ROOT / "data" / "generated" / "viewer_sessions.csv"
RETENTION = REPO_ROOT / "data" / "generated" / "viewer_retention.csv"
METADATA = REPO_ROOT / "output" / "reports" / "generation_metadata.json"


@pytest.fixture(scope="module")
def generated_sample():
    """Generate a small deterministic dataset from the catalog fixture."""
    from conftest import FIXTURE_CATALOG

    catalog = nc_normalize(FIXTURE_CATALOG.copy())
    priors = gb.compute_content_priors(catalog)
    rng = np.random.default_rng(42)
    users = pd.DataFrame(
        {
            "user_id": [f"U{i:05d}" for i in range(1, 51)],
            "engagement_propensity": rng.beta(2.0, 2.5, size=50).clip(0.02, 1.0),
            "taste_noise": rng.normal(0.0, 0.06, 50),
        }
    )
    sessions = gb.generate_sessions(priors, users, rng)
    retention = gb.generate_retention(sessions, users, rng)
    return catalog, users, sessions, retention


def nc_normalize(raw: pd.DataFrame) -> pd.DataFrame:
    import normalize_catalog as nc
    return nc.normalize_catalog(raw)


class TestPriors:
    def test_priors_are_bounded(self, generated_sample):
        catalog, _, _, _ = generated_sample
        priors = gb.compute_content_priors(catalog)
        assert priors["rating_score"].between(0, 1).all()
        assert priors["popularity_score"].between(0, 1).all()
        assert priors["vote_confidence"].between(0, 1).all()

    def test_invalid_runtimes_excluded(self, generated_sample):
        catalog, _, _, _ = generated_sample
        broken = catalog.copy()
        broken.loc[0, "runtime_minutes"] = 0
        priors = gb.compute_content_priors(broken)
        assert len(priors) == len(catalog) - 1

    def test_all_invalid_raises(self, generated_sample):
        catalog, _, _, _ = generated_sample
        broken = catalog.copy()
        broken["runtime_minutes"] = 0
        with pytest.raises(ValueError, match="cannot generate"):
            gb.compute_content_priors(broken)


class TestDomainRules:
    def test_sessions_respect_domain_rules(self, generated_sample):
        catalog, _, sessions, _ = generated_sample
        runtime_map = catalog.set_index("content_id")["runtime_minutes"]
        assert (sessions["watch_duration_minutes"] >= 0).all()
        assert (
            sessions["watch_duration_minutes"]
            <= sessions["content_id"].map(runtime_map)
        ).all()
        assert (sessions["pause_count"] >= 0).all()
        assert sessions["completion_pct"].between(0, 100).all()
        assert (
            sessions["finished"] == (sessions["completion_pct"] >= 90)
        ).all()

    def test_retention_covers_all_users_and_months(self, generated_sample):
        _, users, sessions, retention = generated_sample
        # retention covers every generated user (even never-active ones)
        assert set(retention["user_id"]) == set(users["user_id"])
        assert sessions["user_id"].isin(users["user_id"]).all()
        assert retention["observation_date"].nunique() == gb.OBSERVATION_MONTHS
        assert set(retention["retained_30d"].unique()) <= {True, False}

    def test_retention_is_user_level_outcome(self, generated_sample):
        _, _, sessions, retention = generated_sample
        s = sessions.copy()
        s["started_dt"] = pd.to_datetime(s["started_at"])
        sample_user = s["user_id"].iloc[0]
        first_obs = retention[retention["user_id"] == sample_user].iloc[0]
        obs = np.datetime64(first_obs["observation_date"])
        window_end = obs + np.timedelta64(30, "D")
        started = s.loc[s["user_id"] == sample_user, "started_dt"].to_numpy()
        in_window = (started > obs) & (started <= window_end)
        assert bool(in_window.any()) == bool(first_obs["retained_30d"])

    def test_same_seed_same_output(self, generated_sample):
        catalog, _, _, _ = generated_sample
        priors = gb.compute_content_priors(catalog)
        users = pd.DataFrame(
            {
                "user_id": [f"U{i:05d}" for i in range(1, 21)],
                "engagement_propensity": np.full(20, 0.6),
                "taste_noise": np.zeros(20),
            }
        )
        a = gb.generate_sessions(priors, users, np.random.default_rng(7))
        b = gb.generate_sessions(priors, users, np.random.default_rng(7))
        pd.testing.assert_frame_equal(a, b)


class TestFullDatasetReproducibility:
    def test_full_run_checksums_match_metadata(self):
        """Only runs when the full 5,000-user dataset was generated."""
        if not (SESSIONS.exists() and METADATA.exists()):
            pytest.skip("full generated dataset not present")
        meta = json.loads(METADATA.read_text(encoding="utf-8"))
        sessions_sha = hashlib.sha256(SESSIONS.read_bytes()).hexdigest()
        retention_sha = hashlib.sha256(RETENTION.read_bytes()).hexdigest()
        assert sessions_sha == meta["sessions_sha256"]
        assert retention_sha == meta["retention_sha256"]
