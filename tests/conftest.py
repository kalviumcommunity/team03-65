"""Shared test fixtures: a small deterministic catalog and helpers."""

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

FIXTURE_CATALOG = pd.DataFrame(
    {
        "id": [27205, 157336, 155, 603, 597, 122],
        "title": ["Inception", "Interstellar", "The Dark Knight",
                  "The Poseidon Adventure", "Gladiator", "The Lord of the Rings"],
        "vote_average": [8.364, 8.417, 8.512, 7.4, 7.9, 8.474],
        "vote_count": [34495, 32571, 30619, 23815, 23637, 22334],
        "status": ["Released"] * 6,
        "release_date": ["2010-07-15", "2014-11-05", "2008-07-16",
                         "1972-10-01", "2000-05-01", "2001-12-31"],
        "revenue": [825532764, 701829331, 1004558443, 0, 457640727, 880000000],
        "runtime": [148, 169, 152, 117, 155, 179],
        "adult": [False] * 6,
        "original_language": ["en"] * 6,
        "overview": ["overview a", "overview b", "overview c",
                     "overview d", "overview e", "overview f"],
        "popularity": [83.952, 140.241, 130.643, 28.0, 102.348, 99.276],
        "genres": ["Action, Science Fiction, Adventure",
                   "Adventure, Drama, Science Fiction",
                   "Drama, Action, Crime, Thriller",
                   "Action, Adventure, Drama",
                   "Action, Adventure, Drama",
                   "Adventure, Fantasy"],
    }
)


@pytest.fixture
def fixture_catalog() -> pd.DataFrame:
    """Return a fresh copy of the deterministic catalog fixture."""
    return FIXTURE_CATALOG.copy()


@pytest.fixture
def raw_csv(tmp_path, fixture_catalog) -> Path:
    """Write the fixture catalog to a temp CSV and return its path."""
    path = tmp_path / "tmdb_catalog.csv"
    fixture_catalog.to_csv(path, index=False)
    return path
