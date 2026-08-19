import json
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI


app = FastAPI()
DATA_FILE = Path(__file__).parent / "data" / "viewing_data.csv"
NUMERIC_RULES = {
    "watch_duration": {"minimum": 0, "maximum": 1440, "integer": False},
    "completion_rate": {"minimum": 0, "maximum": 100, "integer": False},
    "pause_count": {"minimum": 0, "maximum": None, "integer": True},
    "sessions_per_week": {"minimum": 0, "maximum": 7, "integer": True},
}
BOOLEAN_VALUES = {
    "true": True,
    "1": True,
    "yes": True,
    "y": True,
    "false": False,
    "0": False,
    "no": False,
    "n": False,
}


def clean_viewing_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return viewing data with consistent, API-safe values."""
    cleaned = data.copy()

    for column in ("user_id", "content_id"):
        cleaned[column] = cleaned[column].astype("string").str.strip()
        cleaned[column] = cleaned[column].replace("", pd.NA)
    cleaned = cleaned.dropna(subset=["user_id", "content_id"])

    for column, rules in NUMERIC_RULES.items():
        values = pd.to_numeric(cleaned[column], errors="coerce")
        values = values.replace([np.inf, -np.inf], np.nan)
        median = values.median()
        values = values.fillna(0 if pd.isna(median) else median)
        values = values.clip(lower=rules["minimum"], upper=rules["maximum"])
        cleaned[column] = values.round().astype(int) if rules["integer"] else values.round(2)

    retained = (
        cleaned["retained"].astype("string").str.strip().str.lower().map(BOOLEAN_VALUES)
    ).astype("boolean")
    most_common = retained.mode()
    cleaned["retained"] = retained.fillna(
        False if most_common.empty else most_common.iloc[0]
    ).astype(bool)

    return cleaned.drop_duplicates().reset_index(drop=True)


@app.get("/api/viewing-data")
def get_viewing_data():
    cleaned = clean_viewing_data(pd.read_csv(DATA_FILE))
    return json.loads(cleaned.to_json(orient="records"))
