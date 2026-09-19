"""Single-lane view matching the workbook's own 'Lane Chart' sheet — State + Channel + Product
dropdowns driving one historical-vs-forecast line.

The Excel sheet has two bugs this page deliberately does NOT reproduce:

1. Its SUMIFS-based volume formula returns NA() whenever a lane's monthly total is exactly 0,
   which turns real zero-volume months (e.g. a product wound down in that state) into gaps that
   look like missing data. 34 of the 96 lanes mix zero and non-zero months and are affected.
   This page plots true zeros as zero.
2. Combined!F5473 (LA / PHYSICAL / ILP, Oct 2027) has a blank Data Type cell in the source
   workbook, which makes the sheet's formula mislabel that one forecast row as Historical.
   The data behind this app backfills that cell from the date instead.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))
from lib import DASH, load_data  # noqa: E402

st.set_page_config(page_title="Lane Chart", layout="wide")

df = st.cache_data(load_data)()

st.title("Lane Chart")
st.caption(
    "Pick one State, Channel, and Product to see that lane's full history and forecast, "
    "the way the workbook's own Lane Chart sheet does — with two of its known display bugs fixed "
    "(see the notes in the sidebar)."
)

states = sorted(df["State"].unique())
channels = sorted(df["Channel"].unique())
products = sorted(df["Product"].unique())

with st.sidebar:
    st.header("Lane")
    state = st.selectbox("State", states, index=states.index("AL") if "AL" in states else 0)
    channel = st.selectbox("Channel", channels, index=channels.index("DIGITAL") if "DIGITAL" in channels else 0)
    product = st.selectbox("Product", products, index=products.index("ILP") if "ILP" in products else 0)

    st.divider()
    st.markdown(
        "**Fixed vs. the workbook:**\n"
        "- Zero-volume months are plotted as 0, not hidden as gaps.\n"
        "- One mislabeled Data Type cell (LA/PHYSICAL/ILP, Oct 2027) is corrected from the date."
    )

lane_df = df[(df["State"] == state) & (df["Channel"] == channel) & (df["Product"] == product)].sort_values("Date")

st.subheader(f"{state} / {channel} / {product}")

if lane_df.empty:
    st.warning("This lane has no rows at all in the source data (not present in the workbook either).")
    st.stop()

if (lane_df["Volume"] == 0).all():
    st.info("Every month for this lane is exactly zero — it's a dormant lane in both history and forecast.")

fig = go.Figure()
for data_type, width in [("Historical", 2.5), ("Forecast", 2.5)]:
    seg = lane_df[lane_df["Data Type"] == data_type]
    if seg.empty:
        continue
    fig.add_trace(
        go.Scatter(
            x=seg["Date"],
            y=seg["Volume"],
            mode="lines+markers",
            name=data_type,
            line=dict(dash=DASH[data_type], width=width),
            hovertemplate="%{x|%b %Y}<br>%{y:,.2f}<extra>" + data_type + "</extra>",
        )
    )

fig.update_layout(
    height=520,
    hovermode="x unified",
    xaxis_title="Month",
    yaxis_title="Volume (loans)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=60, b=40),
)
st.plotly_chart(fig, use_container_width=True)

gap_start, gap_end = pd.Timestamp("2026-07-01"), pd.Timestamp("2026-08-01")
if lane_df["Date"].min() < gap_start and lane_df["Date"].max() > gap_end:
    st.caption("Note: Jul–Aug 2026 is a genuine gap in the source data — actuals stop at Jun 2026 and the forecast starts Sep 2026.")

with st.expander("Underlying rows for this lane"):
    st.dataframe(
        lane_df[["Date", "Data Type", "Volume"]],
        use_container_width=True,
        hide_index=True,
    )
