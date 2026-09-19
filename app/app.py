"""Streamlit app: non-new origination historical vs. forecast, by lane (State + Channel + Product)."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "combined_non_new_actuals_and_forecast.csv"

st.set_page_config(page_title="Non-New Origination Forecast", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["Date"])
    df["Lane"] = df["State"] + " / " + df["Channel"] + " / " + df["Product"]
    return df


df = load_data()

st.title("Non-New Origination — Historical vs. Forecast")
st.caption(
    "Each lane is one State + Channel + Product combination. "
    "Historical actuals run Jan 2022 – Jun 2026; forecast runs Sep 2026 – Dec 2027. "
    "Jul–Aug 2026 have no data in either series (known gap, see PROJECT_UNDERSTANDING.md)."
)

with st.sidebar:
    st.header("Lane filters")
    states = st.multiselect("State", sorted(df["State"].unique()), default=["CA"])
    channels = st.multiselect("Channel", sorted(df["Channel"].unique()), default=list(sorted(df["Channel"].unique())))
    products = st.multiselect("Product", sorted(df["Product"].unique()), default=list(sorted(df["Product"].unique())))

    st.divider()
    split_by_lane = st.checkbox(
        "Show one line per lane (instead of summing the selection)",
        value=len(states) * len(channels) * len(products) <= 8 if states else False,
    )

if not states or not channels or not products:
    st.warning("Select at least one State, Channel, and Product in the sidebar.")
    st.stop()

filtered = df[df["State"].isin(states) & df["Channel"].isin(channels) & df["Product"].isin(products)]

if filtered.empty:
    st.warning("No data for this combination of filters.")
    st.stop()

st.subheader(f"{len(states)} state(s) × {len(channels)} channel(s) × {len(products)} product(s)")

fig = go.Figure()

DASH = {"Historical": "solid", "Forecast": "dash"}
PALETTE = [
    "#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2",
    "#B279A2", "#FF9DA6", "#9D755D", "#BAB0AC", "#EECA3B",
]

if split_by_lane:
    lanes = sorted(filtered["Lane"].unique())
    for i, lane in enumerate(lanes):
        color = PALETTE[i % len(PALETTE)]
        lane_df = filtered[filtered["Lane"] == lane].sort_values("Date")
        for data_type in ["Historical", "Forecast"]:
            seg = lane_df[lane_df["Data Type"] == data_type]
            if seg.empty:
                continue
            fig.add_trace(
                go.Scatter(
                    x=seg["Date"],
                    y=seg["Volume"],
                    mode="lines",
                    name=f"{lane} ({data_type})",
                    legendgroup=lane,
                    line=dict(color=color, dash=DASH[data_type]),
                    hovertemplate="%{x|%b %Y}<br>%{y:,.0f}<extra>" + f"{lane} — {data_type}" + "</extra>",
                )
            )
else:
    agg = filtered.groupby(["Date", "Data Type"], as_index=False)["Volume"].sum()
    for i, data_type in enumerate(["Historical", "Forecast"]):
        seg = agg[agg["Data Type"] == data_type].sort_values("Date")
        if seg.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=seg["Date"],
                y=seg["Volume"],
                mode="lines+markers",
                name=data_type,
                line=dict(color=PALETTE[i], dash=DASH[data_type], width=3),
                hovertemplate="%{x|%b %Y}<br>%{y:,.0f}<extra>" + data_type + "</extra>",
            )
        )

fig.update_layout(
    height=560,
    hovermode="x unified",
    xaxis_title="Month",
    yaxis_title="Volume (loans)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=60, b=40),
)

st.plotly_chart(fig, use_container_width=True)

with st.expander("Underlying data for this selection"):
    st.dataframe(
        filtered.sort_values(["Date", "State", "Channel", "Product"])[
            ["Date", "State", "Channel", "Product", "Data Type", "Volume"]
        ],
        use_container_width=True,
        hide_index=True,
    )

st.divider()
c1, c2, c3 = st.columns(3)
hist_total = filtered.loc[filtered["Data Type"] == "Historical", "Volume"].sum()
fcst_total = filtered.loc[filtered["Data Type"] == "Forecast", "Volume"].sum()
c1.metric("Historical total (Jan 2022 – Jun 2026)", f"{hist_total:,.0f}")
c2.metric("Forecast total (Sep 2026 – Dec 2027)", f"{fcst_total:,.0f}")

last_hist = filtered[filtered["Data Type"] == "Historical"].sort_values("Date").tail(3)["Volume"].mean()
first_fcst = filtered[filtered["Data Type"] == "Forecast"].sort_values("Date").head(3)["Volume"].mean()
if pd.notna(last_hist) and pd.notna(first_fcst) and last_hist:
    delta = (first_fcst - last_hist) / last_hist * 100
    c3.metric("Step at forecast start (3-mo avg)", f"{delta:+.1f}%")
