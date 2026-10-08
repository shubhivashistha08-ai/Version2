"""Build data/scenario_baseline.csv: the Baseline originations behind the Scenario Planner page.

Grain matches UX_V2.xlsx Sheet1's output table, minus the dimensions no data exists for
(H Tactic, Detail Tactic): State x Customer Type x Channel x Product x Month, Mar 2026 - Feb 2027.

Sources, per customer type:
  NON_NEW  actuals Mar-Jun 2026 + hazard forecast Sep 2026 onward, both from
           data/combined_non_new_actuals_and_forecast.csv. Jul-Aug 2026 has no data (left blank).
  NEW      actuals Mar-Jun 2026 from data/source/tblActuals.csv, forecast Jul 2026 onward from
           data/source/new_volume_forecast_for_hazard_2026-09-19.csv.

Only originations exist. Applications and approvals are not in any source file.

The two source files and the output are client data and are gitignored (this repo is public). Copy them
into data/source/ locally, then run from the repo root:  python scripts/build_scenario_baseline.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

MONTHS = pd.date_range("2026-03-01", "2027-02-01", freq="MS")
ACTUALS_END = pd.Timestamp("2026-06-01")
PRODUCT_LABELS = {"ILP": "ILP", "PDL": "Payday Loan"}
KEYS = ["State", "Customer Type", "Channel", "Product"]


def non_new() -> pd.DataFrame:
    df = pd.read_csv(DATA / "combined_non_new_actuals_and_forecast.csv", parse_dates=["Date"])
    df["Source"] = df["Data Type"].map({"Historical": "Actual", "Forecast": "Forecast"})
    df["Customer Type"] = "NON_NEW"
    return df.rename(columns={"Date": "Month", "Volume": "Originations"})


def new() -> pd.DataFrame:
    act = pd.read_csv(DATA / "source" / "tblActuals.csv", encoding="utf-8-sig")
    act.columns = ["Year", "MonthName", "State", "Product", "Channel", "Customer Type", "Originations"]
    act = act[(act["Customer Type"] == "NEW") & act["State"].notna() & act["Channel"].notna()]
    act["Month"] = pd.to_datetime(act["Year"].astype(str) + "-" + act["MonthName"], format="%Y-%b")
    act = act[act["Month"] <= ACTUALS_END]
    act = act.groupby(["Month", "State", "Channel", "Product", "Customer Type"], as_index=False)["Originations"].sum()
    act["Source"] = "Actual"

    fc = pd.read_csv(DATA / "source" / "new_volume_forecast_for_hazard_2026-09-19.csv")
    fc = fc.rename(columns={"STATE_CD": "State", "CHANNEL_CD": "Channel", "PRODUCT_CD": "Product", "NEW_CNT": "Originations"})
    fc["Month"] = pd.to_datetime(fc["PERIOD"] + "-01")
    fc = fc[fc["Month"] > ACTUALS_END]
    fc["Customer Type"] = "NEW"
    fc["Source"] = "Forecast"
    return pd.concat([act, fc], ignore_index=True)


def main() -> None:
    cols = KEYS + ["Month", "Originations", "Source"]
    df = pd.concat([non_new(), new()], ignore_index=True)
    df["Product"] = df["Product"].map(PRODUCT_LABELS)
    df = df[df["Month"].isin(MONTHS)][cols]

    # Full lane x month grid, so months with no source data show up as blank rows instead of vanishing.
    lanes = df[KEYS].drop_duplicates()
    grid = lanes.merge(pd.DataFrame({"Month": MONTHS}), how="cross")
    out = grid.merge(df, on=KEYS + ["Month"], how="left")
    out["Source"] = out["Source"].fillna("No data")
    out["Originations"] = out["Originations"].round(2)
    out = out.sort_values(KEYS + ["Month"])
    out["Month"] = out["Month"].dt.strftime("%Y-%m")
    out.to_csv(DATA / "scenario_baseline.csv", index=False)
    print(f"wrote {len(out):,} rows, {len(lanes):,} lanes")
    print(out.groupby(["Customer Type", "Source"]).size())


if __name__ == "__main__":
    main()
