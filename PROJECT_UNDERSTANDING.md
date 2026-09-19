# Non-New Customer Origination Forecast — Project Understanding & Handoff

**Snapshot date:** 2026-09-19 · **Purpose of this file:** single source of context for the repo and for whoever picks up the next step.

**Confidence tags used throughout**

| Tag | Meaning |
|---|---|
| **[V]** | Verified by opening/recomputing from the actual files on 2026-09-19 |
| **[R]** | Reported in the project documents (`project_summary.md`, `validation_findings_and_gaps.md`, SOW, proposal). Not re-verified here |
| **[I]** | Inference. Plausible, not confirmed by anyone who owns the data |
| **[?]** | Unknown. Needs an answer from the client or the team |

---

## 0. TL;DR

**What the project is.** Replace the client's Excel single-factor vintage model for *non-new* (returning-customer) loan originations with a multi-factor Python model, forecast at state × product × channel × month through Dec 2027. [R]

**Where it stands.** A non-new forecast file exists (`non_new_hazard_forecast_full_2026-09-19.xlsx`, 1,264 rows, Sep 2026–Dec 2027). It has been stitched to the historical actuals in a `Combined` sheet with slicers. **Nothing in the repo shows the forecast has been backtested, and no method document or code for it was provided.**

**What needs attention before the next step, in priority order:**

1. **The forecast is a cliff, not a continuation. [V]** Average forecast for Sep–Nov 2026 is **209,193/month vs 264,858/month actual in Apr–Jun 2026 (−21.0%)**. The entire drop is Payday (PDL, −28%); Installment (ILP) is +3%. Michigan physical PDL falls from 42,752 (Jun 2026) to 25,477 (Sep 2026) after 20 months of stable 40–50k. FY2027 forecast is 2,451,044 vs FY2025 actual 3,399,095 (**−27.9%**); the 2023→2025 actual trend was about −2% to −4% a year. Either there is a real driver (product wind-down, regulation) that nobody has documented, or the model is wrong. Not decidable from the files.
2. **Jul–Aug 2026 are missing from the Combined sheet. [V]** Actuals stop at Jun 2026; the forecast starts Sep 2026. Any 2026 full-year total is understated, and the chart/slicer views have a hole.
3. **The forecast is smooth; reality is not. [V]** Actual month-to-month swings average 7.4% (a working-day sawtooth, e.g. 268k → 304k → 268k → 304k in late 2025). The forecast's average swing is 0.6%. It has no visible seasonality or working-day effect, which is the exact weakness the proposal cites for moving to weekly granularity.
4. **The slicer "verification" in the latest task does not match the file. [V]** The workbook contains two conflicting position definitions. The live slicers are anchored across the top (rows 1–2, above the table). The layout described in the task (State tallest at left, Channel/Product stacked to the right) matches the *fallback placeholder rectangles*, which are blank boxes. See §7.4.
5. **The chart on `Combined` is broken and sits on top of data rows. [V]** See §7.3.
6. **Two of the project's own documents contradict each other on the regression SQL. [V]** `project_summary.md` §5d labels as "corrected, verified" a script that still has the reversed `months_between()` argument order that `validation_findings_and_gaps.md` identifies as a bug. See §8.3.
7. **Feb 2023 looks like a data problem. [V]** Total non-new volume is 188,804 vs 305,890 (Jan) and 298,875 (Mar), and every large state is at ~0.6× its neighbours. A lag-feature model trained on it will inherit the distortion.

---

## 1. Engagement

### 1.1 Problem [R]

The client forecasts non-new originations in an Excel workbook with one driver: **months since the customer's previous origination**. It is built per state (21 state tabs), tracks 15-month cohort windows by channel and product lane, and applies historical renewal rates to project volume. Limits: Excel does not scale (new state = new tab, what-if = manual rework), the single factor ignores marketing, credit, and loan size, and monthly aggregation hides intra-month seasonality.

### 1.2 The two contract documents do not describe the same job [V]

| Topic | Proposal (Aug 2026, "internal review", terms not final) | Scope of Work (PDF) |
|---|---|---|
| Deliverable | Python **+ Streamlit platform**, validation report, handoff package | **Phase 1: a forecast file** + methodology doc. Streamlit is explicitly **Phase 2** |
| Model approach | "Migration": convert Excel to Python **preserving vintage-curve logic**, then extend | "Rebuild from scratch" with regression (Ridge, distributed lag, or alternative, chosen after EDA) |
| Granularity | **Weekly** base unit, rolled up to monthly | State × product × channel; **no weekly requirement stated** |
| Inputs | Marketing spend + touchpoints, credit score mean/P25/P75, funded amount | Phase 1: prior NEW bookings (primary) + marketing spend + anything that materially helps. Credit/funded amount are **Phase 2, Workstream 3** |
| Horizon | Not stated | Through **Dec 2027** |

Consequences: (a) weekly modelling and the working-day apportionment script (`pf2_all_data`, §8.4) are proposal scope, not SOW Phase 1 scope. Confirm which document governs. (b) The SOW's Phase 1 inputs include **marketing spend**, and no marketing-spend file exists anywhere in the repo. (c) The delivered forecast is called a *hazard* forecast, which is neither of the SOW's named techniques. That is allowed ("or alternative") but needs documenting.

### 1.3 Scope boundaries from the SOW [R]

- **In Phase 1:** non-new bookings by state × product × channel through Dec 2027; forecast file + methodology documentation. Delivery is conditional on the client supplying agreed data on time.
- **Phase 2 (scoped and priced after Phase 1 acceptance):** WS1 limited-data reliability (look-alike states, Bayesian shrinkage, pooling); WS2 what-if launches; WS3 credit/funded-amount variables; WS4 Streamlit front end; WS5 technology implementation.
- **WS5 cap:** two deliverables only (technical requirements doc + a commented reference Python script); maximum **12 hours** of sessions with the client's tech team; tech team owns and rewrites the production code.
- **Out of scope:** forecasting *new* customers; **data extraction, cleansing, or pipeline build from source systems**; real-time integration / automated retraining; ongoing monitoring; states/products/channels not already in scope without a written change request.
- Watch item: the Postgres loading/transform work is useful internally, but the SOW puts pipeline build on the client. Keep it framed as analysis support.

---

## 2. Vocabulary

| Term | Meaning | Tag |
|---|---|---|
| **NEW** | Customer's first loan with the lender (`CUSTOMER_TYPE = 'NEW'`) | [I] Not defined in any file; inferred from usage |
| **NON_NEW** | Customer already has ≥1 prior origination and takes another loan: renewal, refinance, or return after a gap | [I] The Excel model has a "first-time / long ago" gap bucket, so some NON_NEW likely follow multi-year lapses |
| **Blank customer type** | 4,938 rows, but only 13,417 loans in total (0.08% of volume). Mostly zero-count padding rows | [V] |
| **PDL / ILP** | Payday / Installment. The proposal names the four lanes Physical Payday, Digital Payday, Physical Installment, Digital Installment | [I] Abbreviations are never expanded |
| **Channel** | `PHYSICAL`, `DIGITAL`, plus `UNKNOWN` and blank in the raw data | [V] |
| **Lane** | One product + channel + customer-type combination; each has its own renewal curve | [R] |
| **Renewal lanes (4)** | Current product → previous product: ILP→ILP, ILP→PDL, PDL→ILP, PDL→PDL | [R] |
| **Months since previous origination** | The single driver in the Excel model (buckets 0–15, plus first-time/long-ago) | [R] |
| **Pool** | The originating cohort for a month, "new + non-new + unclassified" | [R] |
| **Hazard forecast** | The forecast file name implies a discrete-time hazard/survival-style model (probability a customer returns in month *t* given time since last loan). **No spec or code provided** | [I] |

**Unresolved definitional problem [R/I].** The SOW makes prior *NEW* bookings the primary driver, and the SQL lag matrix lags only `NEW` counts. But the Excel worked example (Alabama ILP physical: 496 originated in Apr 2022, 60 came back as non-new exactly 6 months later, 12.1%) divides by the *total* pool, which includes non-new. Different denominators. A NEW-only driver cannot capture renewal-of-renewal volume, so the regression will not reproduce Excel's rates even if everything else is correct.

---

## 3. Current Excel methodology [R]

Each state tab is a matrix. **Rows** = lane (product + channel + customer type) × previous lane (product + channel) × months-since bucket. **Columns** = calendar month. **Cells** = actual originations for that exact combination.

Forecast for a future month = Σ over month-gaps of (historical originating pool for the cohort exactly *gap* months earlier) × (historical renewal rate at that gap). Each gap pulls a **different** historical pool matched to the target month. It is not one fixed pool × 16 rates. (An earlier infographic got this wrong; it is logged as gap #11 in the validation file.)

**Workbook** `FPA_2026_Origination_Renewal_Model_Renewal_6x6Baseline_7_22_v2_2.xlsx` (27.9 MB, 39 sheets [V]): chart tabs (*All Customer Charts*, *NCs Charts*), marketing/lead-gen tabs (*NCs from Mkting&LeadGen*, *LeadGen*), **21 state tabs** (MS TX FL WI UT OK OH NV MO ID AL DE KY RI WY MI LA IA IN CA CO), pivots/lookups (*Pivot*, *for Pivot*, *LOOKUP*, *Sigma AvB dash*, *Combine All Source for Pivot*), forecast roll-ups (*New& Non_new Rfcst*, *Charts & Pivot*, *PDL&ILP_Combine*, *PDL&ILP_New & Non_new*), and three pre-processed data tabs (*3.1 Refcst Non_new origination*, *3.3 Actual Origination Cnt PM*, *3.4 Actual Origination $ LDR*).

The Excel model has **no tabs for KS, SC, or TN**, but the hazard forecast and the actuals both contain them. [V]

---

## 4. Data inventory

| File | What it is | Grain / size | Status |
|---|---|---|---|
| `tblActuals.csv` | Monthly origination counts, all customer types | 14,142 rows × 7 cols; Jan 2022–Jun 2026 | Loaded to Postgres; identical to Excel `3.3` [R]; identical to the `in` sheet of `tblActuals.xlsx` [V] |
| `tblActuals.xlsx` | Workbook: `in` (raw, 14,142 rows), `Combined` (history + forecast, 5,678 rows, table `CombinedData`, 3 slicers, 1 chart), `Data Sources`, empty `Sheet1` | see §7 | Latest working artifact |
| `non_new_hazard_forecast_full_2026-09-19.xlsx` | Non-new forecast, sheet `in` (+ empty `Sheet1`) | 1,264 rows = 79 lanes × 16 months; Sep 2026–Dec 2027 | **Method undocumented** |
| `combined_non_new_actuals_and_forecast.csv` | Flat export of `Combined` for this repo (Date, State, Channel, Product, Volume, Data Type) | 5,678 rows | Generated 2026-09-19 |
| `FPA_2026_Origination_Renewal_Model_…_v2_2.xlsx` | Client's Excel vintage model | 27.9 MB, 39 sheets | Reference; source of truth for the *current* method |
| `dataUpload.sql` | Creates and loads `public.tblActuals` (camelCase columns) | | Run; the load actually used psql `\copy` [R] |
| `pg.sql` | `tempo_applications` schema: ~100 columns of application, decision, funded amount, credit-bureau scores/attributes, tradeline balances, property values, loan terms | Table exists, **0 rows** | Source CSV `tempoApr26+.csv` **never provided** |
| `project_summary.md` | Prior session summary | | Contains a stale SQL block (§8.3) |
| `validation_findings_and_gaps.md` | Prior validation log | | More recent and more reliable of the two |
| `ScopeOfWork.pdf`, `Marketing_Forecast_Proposal.docx` | Contract documents | | Conflict on scope, §1.2 |

**Missing inputs [V]:** marketing spend (by channel), touchpoint counts, credit attributes (`tempoApr26+.csv`), funded amount, transaction-level bookings (customer/loan ID) needed for Excel sheet `3.1`, `calendar.csv` / `state_cd.csv` / `product_cd.csv` / `channel_cd.csv` / `customer_tp.csv` needed by the `pf2_all_data` script, and any specification or code for the hazard forecast.

---

## 5. Source data profile — `tblActuals` [V]

| Item | Value |
|---|---|
| Rows / columns | 14,142 / 7 (`YEAR`, `MONTHNAME`, `STATE_CD`, `PRODUCT_CD`, `Customer Channel`, `CUSTOMER_TYPE`, `CNT`) |
| Period | Jan 2022 – **Jun 2026** (54 months; 2026 has 6) |
| Total loans (`CNT`) | 17,566,429 |
| NON_NEW | 4,703 rows · 16,141,173 loans (91.9%) |
| NEW | 4,501 rows · 1,411,839 loans (8.0%) |
| Blank type | 4,938 rows · 13,417 loans (0.08%) |
| Products | PDL 7,884 rows; ILP 6,258 rows |
| Channel (rows) | PHYSICAL 5,585 · DIGITAL 5,020 · **UNKNOWN 2,710** · **blank 827** |
| States | 24 real + `NC` (71 rows, all zero-count, blank type) + **10 blank-state rows** (all zero-count, 2026 Jan–Mar) |
| NON_NEW by channel (loans) | PHYSICAL 13,068,641 · DIGITAL 3,072,697 · UNKNOWN **−172** · blank 7 |

**Data-quality findings**

| # | Finding | Effect |
|---|---|---|
| 1 | **Negative counts.** 43 NON_NEW state/product/month rows in channel `UNKNOWN` are negative (e.g. TX ILP Jan 2026 = −29). NEW/UNKNOWN nets to −494 | Corrections/reversals landing in an unclassifiable channel. Any model that takes logs or ratios breaks on these |
| 2 | **`UNKNOWN` and blank channel exist.** 498 NON_NEW rows in total, net ≈ −165 loans. Immaterial in volume, but they sit outside the DIGITAL/PHYSICAL structure the forecast uses | Decide: drop, reallocate, or keep as a third channel |
| 3 | **Feb 2023 anomaly.** Total 188,804 vs 305,890 (Jan) and 298,875 (Mar). Every large state is ~0.59–0.68× its neighbours, in both products and both channels. Feb having 28 days explains ~10%, not 37% | Likely a partial load or extraction gap **[I]**. Confirm with the client before using 2023 for training or lag features |
| 4 | **Structural zeros.** 1,566 of 4,414 non-new rows in `Combined` history are zero; many are lanes that no longer exist (see §6.4) | Zero ≠ missing. Needs an explicit "lane active" flag |
| 5 | **Blank state rows** (10, all zero) and **NC** (71 rows, zero) | Harmless but will break joins on state |

---

## 6. The forecast file [V unless tagged]

### 6.1 Shape

| Item | Value |
|---|---|
| Sheet / columns | `in`: `STATE_CD`, `CHANNEL_CD`, `PRODUCT_CD`, `obs_month` (text `YYYY-MM`), `volume` (float) |
| Rows | 1,264 = 79 lanes × 16 months; Sep 2026 → Dec 2027 |
| Lanes | 96 possible (24 states × 2 channels × 2 products): **50 active**, **29 forecast = 0 in every month**, **17 absent** (mostly ILP lanes and CO/UT digital PDL) |
| Total volume | 838,174 (Sep–Dec 2026) + 2,451,044 (2027) = 3,289,218 |
| Monthly total | 207,918 (Sep 2026) → peak 210,595 (Dec 2026) → trough 199,616 (Jul 2027) → 205,074 (Dec 2027) |
| Nulls / negatives | none |
| Values | Fractional (expected counts); rounded to 2 decimals when copied into `Combined` |

### 6.2 Discontinuity with actuals

| Metric | Actual Apr–Jun 2026 avg/mo | Forecast Sep–Nov 2026 avg/mo | Change |
|---|---:|---:|---:|
| All lanes | 264,858 | 209,193 | **−21.0%** |
| PDL | 203,184 | 145,805 | **−28.2%** |
| ILP | 61,674 | 63,388 | +2.8% |

- Same-month comparison: Sep 2026 forecast is −23.6% vs Sep 2025 actual; Dec 2026 is −30.7% vs Dec 2025.
- Largest lanes: CA physical PDL 55,627 → 40,387 (−27%); MI physical PDL 42,605 → 25,392 (−40%); MI digital PDL −35%; IN, LA, IA, KY, RI, WY physical PDL each −21% to −35%.
- **Not explained by the driver:** NEW bookings in H1 2026 (139,007) are **+10.1%** vs H1 2025 (126,286). NEW PDL has been shrinking (234,510 → 131,663 → 117,544 → 100,563 across 2022–2025), but actual non-new PDL fell only ~5% a year over 2023–2025, and MI and CA physical PDL show no visible downtrend over the last 20 months.
- The Jul–Aug 2026 gap sits between the two series, so the size of the jump cannot be measured on a like-for-like month.

### 6.3 Smoothness

Forecast month-to-month change: mean absolute 0.6%, max 1.4%. Actual last 24 months: mean absolute 7.4%, std 9.2%. Example actual pattern: 2025-09 272k, 2025-10 305k, 2025-11 268k, 2025-12 304k. The forecast is a smooth curve with no seasonality or working-day effect. Whatever the intended forecast error metric, monthly MAPE against actuals will be dominated by this.

### 6.4 Lane structure

- **Dormant lanes are consistent with history.** All 29 zero-forecast lanes had zero actuals in Apr–Jun 2026. PDL wound down in: SC (last volume Mar 2022), AL (Oct 2022), NV (Jun 2023), MO (Feb 2024), KS (Jan 2025). CO, DE, ID, OH, OK, UT, WI never had non-new PDL volume.
- **States with no Excel tab:** KS (FY2027 forecast 42 loans), SC (0), TN (694 vs 5,949 in FY2025, −88%).
- **`CO` and `SC` are forecast at exactly zero in every forecast lane** (both also had zero non-new volume in FY2025).

### 6.5 Method — unknown [?]

The file name says "hazard", the column is `obs_month`, and that is all. There is no spec, code, training window, feature list, backtest, or confidence interval in the repo. The SOW requires methodology documentation as part of the Phase 1 deliverable; that document does not exist yet.

---

## 7. The `Combined` workbook (latest task)

### 7.1 What was built

`tblActuals.xlsx` → sheet **`Combined`**: Excel table `CombinedData` at `A3:F5681` with header `Date | State | Channel | Product | Volume | Data Type`, banded rows, three slicers (State, Channel, Product) on the table, one chart. Rows 1–2 are blank and enlarged (56.25 pt and 54.75 pt) to hold the slicers. A comment on `A3` records provenance.

| Block | Rows in table | Source | Transformation |
|---|---:|---|---|
| Historical | 4,414 (`Data Type` = Historical), Jan 2022–Jun 2026 | `in` sheet, `CUSTOMER_TYPE = 'NON_NEW'` | Grouped by month + state + channel + product, summed |
| Forecast | 1,264 (`Data Type` = Forecast), Sep 2026–Dec 2027 | Uploaded hazard file | Date = `obs_month` + `-01`; volume rounded to 2 dp |

**As-reported task note (verbatim from the request):**

> The image confirms the layout: a properly formatted header row (blue with white text) for Date/State/Channel/Product/Volume/Data Type, banded data rows, and — critically — the three slicers visibly rendered as distinct boxes positioned in the upper-right area, non-overlapping (State box tallest at left, Channel and Product stacked below each other to its right), sitting clear of the table's own columns.
>
> Confirmed visually: the three slicers (State, Channel, Product) render as proper dropdown-style filter panels on the Combined sheet, positioned to the right of the data table without overlapping each other or the table headers.

### 7.2 Reconciliation — passed [V]

| Check | Result |
|---|---|
| Historical block vs `in` (NON_NEW, grouped) | 4,414 rows match on key; **0 value mismatches** |
| Duplicate keys (date/state/channel/product) in `Combined` | 0 |
| Forecast block vs uploaded file | 1,264 of 1,264 rows match on key; max difference 0.005 (the 2-dp rounding) |
| Historical total | 16,141,166 vs NON_NEW in `in` = 16,141,173. **Difference of 7 loans**: 289 raw NON_NEW rows were dropped (283 blank-channel rows netting +7, and 6 blank-state rows of 0). The `Data Sources` tab says "4,703 raw rows → 4,414" but does not mention that rows were dropped or why |

### 7.3 Defects found in the workbook [V]

| # | Defect | Detail | Fix |
|---|---|---|---|
| 1 | **No Jul–Aug 2026 rows** | Historical ends Jun 2026; forecast starts Sep 2026 | Get the actuals (today is 19 Sep 2026, so Jul/Aug should exist) or generate/flag modelled values |
| 2 | **Chart is not a valid chart** | Series name = `F3` (Data Type); values = `F4:F5681`, which is **text** ("Historical"/"Forecast"); categories = `A4:E5681` as a 5-level label. It plots nothing meaningful. One series, stacked line | Rebuild: Date on x-axis, Volume on y, series split by Data Type (needs a pivot or helper columns) |
| 3 | **Chart sits on data** | Anchored at `D5473:J5488`, which is inside the table (data runs to row 5681) and covers Product/Volume/Data Type of ~16 forecast rows | Move it beside/above the table |
| 4 | **`Data Sources` row references are stale by 2 rows** | Says historical = `A2:F4415`, forecast = `A4416:F5679`. Actual: historical `A4:F4417`, forecast `A4418:F5681` (header is row 3) | Correct the tab |
| 5 | **Workbook opens scrolled to row 5467** | `topLeftCell="A5467"`; the slicers (rows 1–2) are off-screen on open | Save with the view at `A1` |
| 6 | **Empty `Sheet1`** in both workbooks | Leftover | Delete |
| 7 | **`UNKNOWN` channel appears as a third slicer value** with negative volumes | 215 rows, net −172 | Decide treatment (§5 finding 2), document in `Data Sources` |
| 8 | **Forecast has 464 exact-zero rows** in the table (29 dormant lanes × 16 months) | Clutters slicer views | Optional: drop or flag dormant lanes |

### 7.4 Slicers — the task's visual claim vs what the file says

I have not seen the screenshot referenced in the task. What the file contains:

| Definition | Where it puts the slicers | Who reads it |
|---|---|---|
| **`twoCellAnchor` (the live slicer)** | Rows 1–2 (above the table header in row 3), across columns A–F: State ≈ A–B, Channel ≈ C–D, Product ≈ D–F, **side by side, roughly equal height** | Desktop Excel (slicer-aware) |
| **`mc:Fallback` rectangle (placeholder)** | State at x≈6.10M EMU, 1.9M × 2.29M (tallest); Channel at x≈8.13M, y≈0.13M, 1.9M × 1.27M; Product at x≈8.13M, **y≈2.54M** (stacked under Channel). White fill, green outline, **no content** | Renderers that don't support slicers (e.g. LibreOffice, some previewers) |

The layout in the task ("State tallest at left, Channel and Product stacked to its right, upper-right area") matches the **fallback placeholders exactly**. **[I]** So the screenshot most likely shows blank placeholder boxes rendered by a non-Excel viewer. That cannot confirm the slicers work. Two further problems with the claim even on its own terms:

- The State placeholder starts around column E (my column-width estimate) and reaches down ~5 rows into the table, so it does **not** sit "clear of the table's own columns".
- Excel table slicers are button-list panels, not dropdowns.

**What "done" should mean here:** open the file in desktop Excel, confirm the three slicers appear in rows 1–2, click a State value, and confirm the table filters. I cannot run Excel, so this remains unverified. Also, the two position definitions disagree, so decide which layout is wanted (top band vs right-hand panel) and re-place the slicers once so both definitions agree.

### 7.5 `Data Sources` tab (as written)

| Written to | Source | Object | Obtained via | Transformation | Rows | Notes |
|---|---|---|---|---|---:|---|
| `Combined!A2:F4415` (historical) *(stale, see 7.3 #4)* | This workbook, sheet `in` | `in!A1:G14143` | Run by Claude via connector | Filter `CUSTOMER_TYPE=NON_NEW`; group by year-month + state + channel + product; sum `CNT` | 4,414 | Aggregated from 4,703 raw NON_NEW rows |
| `Combined!A4416:F5679` (forecast) *(stale)* | Uploaded file | `non_new_hazard_forecast_full_2026-09-19.xlsx`, sheet `in` | Uploaded file | None; volume rounded to 2 dp; `obs_month` + `-01` | 1,264 | Forecast flagged from 2026-09 |

---

## 8. SQL / Postgres work log [R unless tagged]

### 8.1 Task status

| # | Task | Status |
|---|---|---|
| 1 | Understand current methodology | Done |
| 2 | Install PostgreSQL + pgAdmin | Done |
| 3a | Load Excel `3.3 Actual Origination Cnt PM` (14,142 rows) | Done, exact match |
| 3b | Load Excel `3.1 Refcst Non_new origination` | **Blocked**: needs transaction-level data (customer/loan ID, months since previous origination, previous product, principal). `tblActuals` is aggregate-only |
| 4 | SK-sheet pivot queries | Done, exact match on sampled states |
| 5 | Regression-ready lag matrix, all 4 renewal lanes (6,168 rows) | Done, **but see §8.3** |
| 6 | Dimension hierarchies (state→region, product→family, date→fiscal quarter) | Not started; needs business mapping rules |
| 7 | "Look-alike fields" | Undefined; probably borrowing patterns from similar states for sparse lanes (Phase 2 WS1), **[?]** confirm |

**Live table:** `public.tblactuals` in **camelCase** (`origYr`, `origMnth`, `origStateCd`, `productCd`, `customerChannel`, `customerType`, `cn`). A snake_case variant existed in a later script and is not what is loaded. `public.tempo_applications` exists and is empty.

### 8.2 Lag matrix — what it is

For every NON_NEW row (state, product, channel, month) it produces `m01_new_cn … m15_new_cn`: NEW-customer counts in the same state and channel, 1…15 months **earlier**, split by previous product. One row per (month, state, current product, previous product, channel): 6,168 rows; lane split ILP→ILP 1,537, ILP→PDL 1,170, PDL→ILP 1,392, PDL→PDL 2,069.

### 8.3 Bugs and a document conflict

| # | Issue | Status |
|---|---|---|
| A | **WHERE-clause bug (team script):** `where (t1.product_cd='PDL' and t2.product_cd='PDL' or t1.product_cd='PDL' and t2.product_cd='ILP')` keeps only PDL on the non-new side, dropping every ILP non-new row (2 of 4 lanes). Found by reading, never run | Fixed with `where t1."productCd" in ('PDL','ILP') and t2."productCd" in ('PDL','ILP')` |
| B | **`months_between()` argument order reversed.** `months_between(end, start)` = `AGE(end,start)`. Called as `(t2, t1)` with t1 = NON_NEW (later) and t2 = NEW (earlier), the result is negative for a true "N months before" match, so the `= 1..15` tests only matched NEW rows N months **after** the non-new row. Every `mXX_new_cn` value in all 6,168 rows was wrong. Confirmed by 5 independent spot checks (all `non_new_cn` matched, all lag columns mismatched; the "N months after" hypothesis reproduced the SQL output in 5/5) | Fix is to swap to `months_between(t1.bom_orig_dt, t2.bom_orig_dt)` on all 15 columns. **Post-fix rerun not confirmed** |
| C | **Document conflict.** `project_summary.md` §5d is titled "corrected version (verified exact match)" but its SQL still uses `months_between(t2.bom_orig_dt, t1.bom_orig_dt)`, the reversed order from bug B. Its "0 mismatched cells across 201,024" check was against a Python replica; a replica written with the same reversed logic would pass. **Treat §5d as unsafe to copy.** `validation_findings_and_gaps.md` is the later, more careful document **[I]** | Update `project_summary.md` |
| D | **`lookup` key is not unique.** `concat(yymm,state,productCd,prev_productCd)` omits channel | Add channel before joining or deduplicating |

Corrected lag expression (all 15 columns follow this pattern):

```sql
sum(case when months_between(t1.bom_orig_dt, t2.bom_orig_dt) = 1
         then t2."cn" else 0 end) as m01_new_cn
```

### 8.4 `pf2_all_data` calendar/apportionment script (31-Aug/1-Sep) — not validated

- Needs `calendar`, `state_cd` (with region and look-alike state), `product_cd`, `channel_cd`, `customer_tp`. Three are derivable with `SELECT DISTINCT`; `state_cd` mapping and holiday calendar are not.
- **Join regression:** `and t1.product_cd = t2.product_cd` forces same-product joins and silently removes ILP→PDL and PDL→ILP, undoing the 31-Aug changelog line "handle all 4 renewal lanes".
- **Rounding:** apportions monthly counts across working days as `decimal(7,3)`. Round once at final aggregation, not per day (100/22 = 4.545 → 5/day × 22 = 110). Whether summing and rounding once reproduces the original integer is untested.

### 8.5 What has and has not been validated

| Validated | Not validated |
|---|---|
| Source data: `tblactuals` = CSV = Excel `3.3` (0 diffs, 14,142 rows) | Regression matrix vs the **Excel forecast logic** (state tabs, `3.1`). Only checked against raw counts |
| `Combined` history vs `in` (§7.2) | Cross-product lanes (ILP→PDL, PDL→ILP) with independent values |
| | Full independent diff of all 6,168 rows (only 5 spot checks) |
| | `pf2_all_data` (not run) |
| | **The hazard forecast itself** (no backtest anywhere) |

---

## 9. Issues register

| Pri | Issue | Where | Owner needed |
|---|---|---|---|
| **High** | Forecast steps down 21% (PDL −28%) vs recent actuals with no documented cause; no backtest | §6.2 | Modeller + client |
| **High** | Hazard model spec/code absent; SOW requires methodology documentation | §6.5 | Modeller |
| **High** | Jul–Aug 2026 missing | §7.3 #1 | Client data |
| **High** | SOW vs proposal disagree on weekly, Streamlit, vintage-preservation | §1.2 | Engagement lead |
| **High** | Feb 2023 volume anomaly | §5 #3 | Client data |
| **Med** | Marketing spend (SOW Phase 1 input), credit data, transaction-level data not provided | §4 | Client |
| **Med** | `project_summary.md` §5d carries reversed-argument SQL; post-fix spot checks not rerun; cross-product lanes unchecked | §8.3 | Analyst |
| **Med** | Forecast has no seasonality/working-day structure | §6.3 | Modeller |
| **Med** | KS, SC, TN in data and forecast but not in the Excel model | §6.4 | Client |
| **Med** | UNKNOWN/blank channel, negative counts | §5 #1–2 | Client + analyst |
| **Med** | Chart broken and overlapping data; Data Sources rows stale; slicer layout unverified | §7.3–7.4 | Analyst |
| **Low** | Empty `Sheet1`; opens at row 5467; 464 zero rows in table | §7.3 | Analyst |

---

## 10. Recommended next steps (in order)

1. **Backtest before anything else.** Refit (or re-run) the hazard model using data through Dec 2025 only; forecast Jan–Jun 2026; compare by lane (top 10 lanes plus total) against actuals, against the Excel vintage forecast, and against a seasonal-naive baseline (same month last year × recent trend). If the −21% step does not survive this, the forecast is not usable.
2. **Write the method note** for the hazard forecast (inputs, training window, treatment of zeros/UNKNOWN/Feb 2023, output definition). Commit it beside the forecast.
3. **Close the Jul–Aug 2026 gap** with actuals, then re-check the discontinuity. It may shrink or grow.
4. **Ask the client about Feb 2023, the PDL outlook (any wind-down, rule change, or product change planned for 2026–27), UNKNOWN channel, and blank customer types.**
5. **Fix `Combined`:** rebuild the chart, move it off the data, correct `Data Sources`, delete `Sheet1`, set the view to `A1`, agree one slicer layout, and verify in desktop Excel that slicers filter.
6. **Reconcile the two markdown logs;** rerun the 5 spot checks on the corrected lag SQL, add cross-product spot checks, then do the full independent diff.
7. **Decide weekly vs monthly** with the client, and only then finish `pf2_all_data` (fix the join, round once, get the five reference tables).
8. **Request the Phase 1 inputs** that are still missing: marketing spend by channel, the credit/application CSV, and, if the Excel `3.1` sheet must be replicated, transaction-level data.

---

## 11. Open questions

1. Formal definitions of NEW and NON_NEW. Does a customer returning after a long lapse count as NEW again?
2. Does the hazard model use NEW bookings only, or the full pool? What are its other inputs?
3. Why does PDL fall ~28% between Jun 2026 actuals and Sep 2026 forecast? Is a wind-down planned?
4. Is Feb 2023 a load error?
5. What are the correct region groupings, look-alike states, fiscal calendar, and holiday rules?
6. Which document governs: SOW (forecast file, monthly) or proposal (platform, weekly)?
7. Should KS, SC, and TN be forecast at all? Should dormant lanes be delivered as zeros or omitted?
8. What does the client want done with UNKNOWN-channel and negative rows?

---

## Appendix A — Monthly non-new volume

**Actual** (all channels, incl. UNKNOWN; "—" = no data in workbook)

| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 333,323 | 321,771 | 326,691 | 333,656 | 314,813 | 332,006 | 343,200 | 339,902 | 356,899 | 339,067 | 327,690 | 367,938 | 4,036,956 |
| 2023 | 305,890 | 188,804 | 298,875 | 281,616 | 304,322 | 321,516 | 305,771 | 321,965 | 328,675 | 301,913 | 305,100 | 332,798 | 3,597,245 |
| 2024 | 288,400 | 281,475 | 281,617 | 278,288 | 310,518 | 281,806 | 299,639 | 327,872 | 274,265 | 302,017 | 304,642 | 304,871 | 3,535,410 |
| 2025 | 304,619 | 261,668 | 259,191 | 266,558 | 299,521 | 266,266 | 291,887 | 301,112 | 272,059 | 304,924 | 267,575 | 303,715 | 3,399,095 |
| 2026 | 286,767 | 244,912 | 246,208 | 261,937 | 269,454 | 263,182 | — | — | — | — | — | — | 1,572,460 |

**Forecast**

| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026 | — | — | — | — | — | — | — | — | 207,918 | 209,273 | 210,388 | 210,595 | 838,174 |
| 2027 | 210,591 | 209,822 | 208,043 | 205,432 | 202,579 | 200,412 | 199,616 | 200,219 | 201,651 | 203,207 | 204,397 | 205,074 | 2,451,044 |

---

## Appendix B — Annual volume by product × channel

UNKNOWN-channel rows are excluded here (their net is small: −144 in 2026 H1, −35 in 2025, +7 in 2023, 0 in 2022 and 2024), so totals differ slightly from Appendix A.

| Product | Channel | FY2022 | FY2023 | FY2024 | FY2025 | 2026 Jan–Jun (act) | 2026 Sep–Dec (fcst) | FY2027 (fcst) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ILP | DIGITAL | 105,971 | 135,141 | 161,327 | 181,471 | 91,405 | 74,189 | 228,273 |
| ILP | PHYSICAL | 445,561 | 531,167 | 587,687 | 563,615 | 261,769 | 181,598 | 587,677 |
| PDL | DIGITAL | 530,259 | 531,953 | 535,546 | 537,532 | 262,092 | 132,943 | 368,311 |
| PDL | PHYSICAL | 2,955,165 | 2,398,977 | 2,250,850 | 2,116,512 | 957,338 | 449,444 | 1,266,783 |
| **Total** |  | 4,036,956 | 3,597,238 | 3,535,410 | 3,399,130 | 1,572,604 | 838,174 | 2,451,044 |

---

## Appendix C — By state

FY2027 forecast vs FY2025 actual. "Excel tab?" = has a state tab in the client's Excel model.

| State | FY2025 act | Jan–Jun 2026 act | Sep–Dec 2026 fcst | FY2027 fcst | Δ FY27 fcst vs FY25 act | Excel tab? |
|---|---:|---:|---:|---:|---:|---|
| CA | 948,735 | 447,577 | 223,394 | 658,857 | -31% | yes |
| MI | 695,559 | 330,331 | 134,441 | 372,808 | -46% | yes |
| FL | 577,539 | 266,828 | 169,020 | 505,496 | -12% | yes |
| IN | 200,827 | 91,100 | 49,711 | 127,899 | -36% | yes |
| LA | 183,740 | 81,406 | 42,122 | 122,895 | -33% | yes |
| TX | 143,977 | 60,423 | 49,567 | 159,807 | +11% | yes |
| IA | 133,375 | 60,673 | 29,109 | 81,246 | -39% | yes |
| KY | 102,983 | 45,191 | 21,324 | 59,637 | -42% | yes |
| RI | 92,369 | 43,176 | 20,940 | 57,955 | -37% | yes |
| OH | 81,616 | 38,279 | 26,284 | 73,845 | -10% | yes |
| AL | 61,684 | 29,110 | 21,964 | 73,565 | +19% | yes |
| MS | 45,989 | 19,553 | 13,575 | 43,661 | -5% | yes |
| WY | 41,819 | 20,323 | 8,980 | 26,077 | -38% | yes |
| OK | 35,081 | 15,435 | 11,368 | 35,617 | +2% | yes |
| MO | 20,642 | 9,075 | 6,529 | 20,616 | -0% | yes |
| WI | 11,630 | 5,574 | 3,832 | 12,439 | +7% | yes |
| NV | 8,727 | 4,308 | 3,509 | 11,507 | +32% | yes |
| TN | 5,949 | 1,265 | 419 | 694 | -88% | **no** |
| DE | 3,923 | 1,697 | 1,222 | 3,735 | -5% | yes |
| ID | 1,611 | 700 | 542 | 1,657 | +3% | yes |
| UT | 1,027 | 436 | 311 | 989 | -4% | yes |
| KS | 293 | 0 | 10 | 42 | -86% | **no** |
| CO | 0 | 0 | 0 | 0 | n/a | yes |
| SC | 0 | 0 | 0 | 0 | n/a | **no** |
| **Total** | **3,399,095** | **1,572,460** | **838,174** | **2,451,044** | **-28%** |  |

---

## Appendix D — Lane inventory (all 96 state × channel × product combinations)

"Δ" = Sep–Nov 2026 forecast average vs Apr–Jun 2026 actual average (blank when either is zero). Full 5,678-row data is in `combined_non_new_actuals_and_forecast.csv`.

| State | Channel | Product | Forecast status | FY2025 act | Apr–Jun 26 act avg/mo | Sep–Nov 26 fcst avg/mo | Δ | FY2027 fcst |
|---|---|---|---|---:|---:|---:|---:|---:|
| AL | DIGITAL | ILP | active | 10,941 | 877 | 1,035 | +18% | 14,703 |
| AL | DIGITAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| AL | PHYSICAL | ILP | active | 50,744 | 4,271 | 4,383 | +3% | 58,862 |
| AL | PHYSICAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| CA | DIGITAL | ILP | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| CA | DIGITAL | PDL | active | 223,984 | 19,157 | 15,334 | -20% | 175,948 |
| CA | PHYSICAL | ILP | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| CA | PHYSICAL | PDL | active | 724,758 | 55,627 | 40,387 | -27% | 482,910 |
| CO | DIGITAL | ILP | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| CO | DIGITAL | PDL | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| CO | PHYSICAL | ILP | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| CO | PHYSICAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| DE | DIGITAL | ILP | active | 1,237 | 96 | 112 | +17% | 1,252 |
| DE | DIGITAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| DE | PHYSICAL | ILP | active | 2,686 | 196 | 192 | -2% | 2,483 |
| DE | PHYSICAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| FL | DIGITAL | ILP | active | 74,666 | 6,875 | 7,372 | +7% | 93,231 |
| FL | DIGITAL | PDL | active | 29,339 | 1,936 | 1,484 | -23% | 13,379 |
| FL | PHYSICAL | ILP | active | 277,048 | 22,940 | 21,890 | -5% | 286,879 |
| FL | PHYSICAL | PDL | active | 196,485 | 13,484 | 11,482 | -15% | 112,008 |
| IA | DIGITAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| IA | DIGITAL | PDL | active | 24,277 | 2,104 | 1,579 | -25% | 17,901 |
| IA | PHYSICAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| IA | PHYSICAL | PDL | active | 109,099 | 7,932 | 5,709 | -28% | 63,345 |
| ID | DIGITAL | ILP | active | 788 | 71 | 84 | +18% | 935 |
| ID | DIGITAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| ID | PHYSICAL | ILP | active | 824 | 49 | 51 | +3% | 721 |
| ID | PHYSICAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| IN | DIGITAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| IN | DIGITAL | PDL | active | 33,244 | 2,974 | 2,722 | -8% | 27,122 |
| IN | PHYSICAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| IN | PHYSICAL | PDL | active | 167,583 | 12,371 | 9,773 | -21% | 100,778 |
| KS | DIGITAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| KS | DIGITAL | PDL | active | 36 | 0 | 1 | n/a | 9 |
| KS | PHYSICAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| KS | PHYSICAL | PDL | active | 257 | 0 | 2 | n/a | 33 |
| KY | DIGITAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| KY | DIGITAL | PDL | active | 10,393 | 934 | 769 | -18% | 7,916 |
| KY | PHYSICAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| KY | PHYSICAL | PDL | active | 92,590 | 6,357 | 4,572 | -28% | 51,721 |
| LA | DIGITAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| LA | DIGITAL | PDL | active | 30,483 | 2,027 | 1,570 | -23% | 18,625 |
| LA | PHYSICAL | ILP | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| LA | PHYSICAL | PDL | active | 153,257 | 11,408 | 8,928 | -22% | 104,270 |
| MI | DIGITAL | ILP | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| MI | DIGITAL | PDL | active | 153,119 | 12,713 | 8,276 | -35% | 90,691 |
| MI | PHYSICAL | ILP | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| MI | PHYSICAL | PDL | active | 542,440 | 42,605 | 25,392 | -40% | 282,117 |
| MO | DIGITAL | ILP | active | 6,368 | 538 | 622 | +15% | 7,147 |
| MO | DIGITAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| MO | PHYSICAL | ILP | active | 14,274 | 1,065 | 993 | -7% | 13,469 |
| MO | PHYSICAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| MS | DIGITAL | ILP | active | 8,504 | 760 | 839 | +10% | 10,670 |
| MS | DIGITAL | PDL | active | 862 | 11 | 5 | -51% | 37 |
| MS | PHYSICAL | ILP | active | 32,904 | 2,582 | 2,494 | -3% | 32,848 |
| MS | PHYSICAL | PDL | active | 3,721 | 81 | 19 | -76% | 106 |
| NV | DIGITAL | ILP | active | 2,241 | 205 | 259 | +26% | 3,596 |
| NV | DIGITAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| NV | PHYSICAL | ILP | active | 6,487 | 554 | 604 | +9% | 7,911 |
| NV | PHYSICAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| OH | DIGITAL | ILP | active | 20,051 | 1,892 | 1,945 | +3% | 22,466 |
| OH | DIGITAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| OH | PHYSICAL | ILP | active | 61,565 | 5,089 | 4,590 | -10% | 51,379 |
| OH | PHYSICAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| OK | DIGITAL | ILP | active | 10,593 | 826 | 976 | +18% | 12,103 |
| OK | DIGITAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| OK | PHYSICAL | ILP | active | 24,488 | 1,830 | 1,837 | +0% | 23,514 |
| OK | PHYSICAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| RI | DIGITAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| RI | DIGITAL | PDL | active | 11,348 | 1,135 | 884 | -22% | 9,382 |
| RI | PHYSICAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| RI | PHYSICAL | PDL | active | 81,021 | 6,126 | 4,362 | -29% | 48,574 |
| SC | DIGITAL | ILP | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| SC | DIGITAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| SC | PHYSICAL | ILP | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| SC | PHYSICAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| TN | DIGITAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| TN | DIGITAL | PDL | active | 1,431 | 52 | 27 | -49% | 196 |
| TN | PHYSICAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| TN | PHYSICAL | PDL | active | 4,518 | 152 | 84 | -45% | 498 |
| TX | DIGITAL | ILP | active | 40,539 | 3,475 | 4,698 | +35% | 56,470 |
| TX | DIGITAL | PDL | active | 10,988 | 385 | 141 | -63% | 970 |
| TX | PHYSICAL | ILP | active | 85,481 | 6,439 | 7,391 | +15% | 101,882 |
| TX | PHYSICAL | PDL | active | 6,992 | 177 | 61 | -65% | 485 |
| UT | DIGITAL | ILP | active | 821 | 62 | 69 | +11% | 803 |
| UT | DIGITAL | PDL | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| UT | PHYSICAL | ILP | active | 206 | 10 | 7 | -32% | 186 |
| UT | PHYSICAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| WI | DIGITAL | ILP | active | 4,722 | 370 | 387 | +5% | 4,897 |
| WI | DIGITAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| WI | PHYSICAL | ILP | active | 6,908 | 601 | 559 | -7% | 7,542 |
| WI | PHYSICAL | PDL | forecast = 0 all months | 0 | 0 | 0 | n/a | 0 |
| WY | DIGITAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| WY | DIGITAL | PDL | active | 8,028 | 787 | 529 | -33% | 6,136 |
| WY | PHYSICAL | ILP | no forecast rows | 0 | 0 | 0 | n/a | 0 |
| WY | PHYSICAL | PDL | active | 33,791 | 2,649 | 1,715 | -35% | 19,940 |

