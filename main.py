from pathlib import Path

import pandas as pd
from fastapi import FastAPI


app = FastAPI()
DATA_FILE = Path(__file__).parent / "data" / "viewing_data.csv"


@app.get("/api/viewing-data")
def get_viewing_data():
    return pd.read_csv(DATA_FILE).to_dict(orient="records")
