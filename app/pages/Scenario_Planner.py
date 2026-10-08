"""Scenario Planner: replica of UX_V2.xlsx Sheet1 — filter dropdowns, a Products checkbox group, three
scenario blocks of Marketing / Credit and Pricing levers, and the Baseline vs Scenario 1-3 funnel table
(Applications / Approvals / Originations by month, Mar 2026 - Feb 2027).

The workbook is a layout mock: its form controls have no linked cells or list ranges. Only originations
exist in the data, so everything the sheet shows that has no source is rendered but marked:

- Applications, Approvals, H Tactic, Detail Tactic: no data -> shown as "—"; those filters are disabled.
- Products FLC / Line of Credit / Not Funded: no data -> checkboxes disabled.
- Marketing Levers: no spend, touchpoint, or tactic data and no response curve -> sliders disabled.
- Credit and Pricing Levers: read as a relative % lift on that funnel rate. With applications held fixed,
  originations = applications x approval rate x origination rate, so originations scale by
  (1 + approval lift) x (1 + origination lift). The lift's unit is an assumption, not taken from the sheet.
  Levers apply to Forecast months only; Actual months (Mar-Jun 2026) pass through unchanged.
"""

import html

import pandas as pd
import streamlit as st

from lib import SCENARIO_BASELINE_PATH, load_scenario_baseline

st.set_page_config(page_title="Scenario Planner", layout="wide")

if not SCENARIO_BASELINE_PATH.exists():
    st.error(
        "Missing data/scenario_baseline.csv. It holds client data, so it is gitignored and has to be built "
        "locally: put tblActuals.csv and new_volume_forecast_for_hazard_2026-09-19.csv in data/source/, then "
        "run `python scripts/build_scenario_baseline.py` from the repo root."
    )
    st.stop()

df = st.cache_data(load_scenario_baseline)()

SCENARIOS = ["Scenario 1", "Scenario 2", "Scenario 3"]
MARKETING_LEVERS = ["Paid Search", "Paid Social", "Prescreen", "Referrals", "Lead Generation", "Sweepstakes"]
CREDIT_LEVERS = ["Approval Rate", "Origination Rate"]
PRODUCTS = ["ILP", "FLC", "Line of Credit", "Payday Loan", "Not Funded"]
PRODUCTS_WITH_DATA = set(df["Product"].unique())
NO_DATA = "No data in any source file yet."

with st.container(border=True):
    st.title("Scenario Planner")
    st.caption(
        "Non-new and new customer originations, Mar 2026 – Feb 2027. Mar–Jun 2026 are actuals; later months "
        "are forecasts. Non-new Jul–Aug 2026 has no data (actuals stop at Jun, the forecast starts Sep)."
    )


def labelled_multiselect(label: str, options, **kwargs) -> list:
    # Label to the left of the dropdown, as on the sheet.
    label_col, input_col = st.columns([1, 3], vertical_alignment="center")
    label_col.markdown(label)
    return input_col.multiselect(label, options, label_visibility="collapsed", **kwargs)


# ---- Filters (C7:F16) and Products group box (G6:I16) ----------------------------------------------
filter_col, product_col, _ = st.columns([2, 1, 1])
with filter_col:
    st.caption("Leave a filter empty to include everything. Each allows multiple selections.")
    state = labelled_multiselect("State", sorted(df["State"].unique()), placeholder="All")
    customer_type = labelled_multiselect("Customer Type", sorted(df["Customer Type"].unique()), placeholder="All")
    channel = labelled_multiselect("Channel", sorted(df["Channel"].unique()), placeholder="All")
    labelled_multiselect("H Tactic", [], placeholder="No data", disabled=True, help=NO_DATA)
    labelled_multiselect("Detail Tactic", MARKETING_LEVERS, placeholder="No data", disabled=True, help=NO_DATA)

with product_col:
    with st.container(border=True):
        st.markdown("**Products**")
        products = [
            p
            for p in PRODUCTS
            if st.checkbox(
                p,
                value=p in PRODUCTS_WITH_DATA,
                disabled=p not in PRODUCTS_WITH_DATA,
                help=None if p in PRODUCTS_WITH_DATA else NO_DATA,
                key=f"product_{p}",
            )
        ]

# ---- Scenario 1-3 lever blocks (E20:N36) -----------------------------------------------------------
st.write("")
levers = {}
for col, name in zip(st.columns(3), SCENARIOS):
    with col, st.container(border=True):
        st.markdown(f"**{name}**")
        with st.container(border=True):
            st.markdown("Marketing Levers")
            for lever in MARKETING_LEVERS:
                st.slider(lever, 0, 100, 0, disabled=True, key=f"{name}_{lever}", help="No marketing spend, touchpoint, or tactic data yet.")
        with st.container(border=True):
            st.markdown("Credit and Pricing Levers")
            levers[name] = {
                lever: st.slider(lever, 0, 100, 0, format="+%d%%", key=f"{name}_{lever}", help="Relative lift on this rate (assumed unit).")
                for lever in CREDIT_LEVERS
            }

# ---- Output table (B41:T54) ------------------------------------------------------------------------
mask = df["Product"].isin(products)
for column, selected in [("State", state), ("Customer Type", customer_type), ("Channel", channel)]:
    if selected:
        mask &= df[column].isin(selected)
view = df[mask].copy()

is_forecast = view["Source"] == "Forecast"
for name in SCENARIOS:
    lift = (1 + levers[name]["Approval Rate"] / 100) * (1 + levers[name]["Origination Rate"] / 100)
    view[name] = view["Originations"].where(~is_forecast, view["Originations"] * lift)
view = view.rename(columns={"Originations": "Baseline"})

st.write("")
groups = ["Baseline"] + SCENARIOS
for col, name in zip(st.columns(4), groups):
    total = view.loc[is_forecast, name].sum()
    base = view.loc[is_forecast, "Baseline"].sum()
    delta = f"{total - base:+,.0f}" if round(total - base) else None
    col.metric(f"{name} — forecast originations", f"{total:,.0f}", delta)

if view.empty:
    st.info("No rows match these filters.")
    st.stop()


def fmt(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:,.0f}"


DIMS = ["State", "Customer Type", "Channel", "H Tactic", "Detail Tactic", "Product", "Month"]
METRICS = ["Applications", "Approvals", "Originations"]

head = "".join(f'<th rowspan="2">{d}</th>' for d in DIMS)
head += "".join(f'<th colspan="3" class="grp">{g}</th>' for g in groups)
sub = "".join(f"<th>{m}</th>" for _ in groups for m in METRICS)
body = []
for r in view.to_dict("records"):
    month = pd.Timestamp(r["Month"]).strftime("%b-%y")
    dims = [r["State"], r["Customer Type"], r["Channel"], "—", "—", r["Product"], month]
    cells = "".join(f"<td>{html.escape(str(v))}</td>" for v in dims)
    cells += "".join(f'<td class="n na">—</td><td class="n na">—</td><td class="n">{fmt(r[g])}</td>' for g in groups)
    body.append(f'<tr class="{r["Source"].replace(" ", "-").lower()}">{cells}</tr>')

st.html(
    f"""
<style>
.sp-wrap {{ max-height: 640px; overflow: auto; border: 1px solid rgba(128,128,128,.35); }}
.sp-table {{ border-collapse: collapse; font-size: 13px; width: 100%; }}
.sp-table th, .sp-table td {{ border: 1px solid rgba(128,128,128,.3); padding: 4px 8px; white-space: nowrap; }}
.sp-table thead th {{ position: sticky; background: var(--sp-head, #f0f2f6); z-index: 1; }}
.sp-table thead tr:first-child th {{ top: 0; }}
.sp-table thead tr:nth-child(2) th {{ top: 27px; }}
.sp-table th.grp {{ text-align: center; }}
.sp-table td.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
.sp-table td.na, .sp-table tr.no-data td.n {{ opacity: .45; }}
.sp-table tr.actual td {{ font-style: italic; }}
@media (prefers-color-scheme: dark) {{ .sp-table {{ --sp-head: #262730; }} }}
</style>
<div class="sp-wrap"><table class="sp-table">
<thead><tr>{head}</tr><tr>{sub}</tr></thead>
<tbody>{''.join(body)}</tbody>
</table></div>
"""
)
st.caption(
    f"{len(view):,} rows. Italic rows are actuals (levers don't change them). \"—\" = no data: applications and "
    "approvals aren't in any source file, and H Tactic / Detail Tactic don't exist in the data."
)

st.download_button(
    "Download table as CSV",
    view.to_csv(index=False),
    file_name="scenario_planner.csv",
    mime="text/csv",
)
