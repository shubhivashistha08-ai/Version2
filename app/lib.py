"""Shared data loading for the Streamlit pages."""

from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "combined_non_new_actuals_and_forecast.csv"

PALETTE = [
    "#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2",
    "#B279A2", "#FF9DA6", "#9D755D", "#BAB0AC", "#EECA3B",
]
DASH = {"Historical": "solid", "Forecast": "dash"}


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["Date"])
    df["Lane"] = df["State"] + " / " + df["Channel"] + " / " + df["Product"]
    return df
