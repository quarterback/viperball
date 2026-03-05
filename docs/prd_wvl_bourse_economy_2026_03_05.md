# PRD — WVL Owner Mode: Economic Simulation, Bourse Currency & Exchange Rate

**Date**: March 5, 2026
**Commits**: `e31fa8f`, `415afd2`
**Branch**: `claude/fix-wvl-owner-issues-SAgqJ`
**Files Modified**: `engine/wvl_owner.py`, `engine/wvl_dynasty.py`, `engine/bourse.py` (new),
`nicegui_app/pages/wvl_mode.py`, `nicegui_app/pages/dq_mode.py`,
`nicegui_app/pages/pro_leagues.py`, `stats_site/router.py`,
`stats_site/templates/wvl/economy.html` (new), + 6 existing WVL HTML templates

---

## 1. Problem Statement

WVL Owner Mode launched in March 2026 (see `project_report_wvl_owner_mode_upgrade_2026_03_03.md`)
with a functional 5-tab interface and week-by-week simulation, but three gaps remained:

### 1.1 Box Scores Never Opened

Clicking "Box Score" on any completed game in the Schedule tab produced no dialog. The button
appeared to work (no visible error) but nothing happened. Root cause: the click handler was
declared `def _show_box(...)` (synchronous) rather than `async def`. In NiceGUI 2.x, synchronous
click handlers do not receive the client context required to create UI elements such as dialogs.
Every other handler in the file was already `async def`. The fix was a one-word change.

### 1.2 Financials Were Cosmetic

The revenue model used a single flat broadcast-style number regardless of fanbase size, tier
performance, or investment decisions. The breakdown bars in the Finances tab displayed `$0` across
the board because `ClubFinancials.to_dict()` never populated the breakdown keys. The financial
history was inert: it recorded numbers but had no effect on how the simulation behaved.

### 1.3 No Viperball Currency

All monetary values were displayed in USD (`$`), which is narratively inconsistent. The
in-universe currency is the **Bourse** (₯, U+20AF) — a reserve currency pegged loosely to a
synthetic SDR-like basket, with a floating exchange rate that introduces macroeconomic volatility
into club finances.

---

## 2. What Was Built (Session 1 — commit `e31fa8f`)

### 2.1 Box Score Fix

`nicegui_app/pages/wvl_mode.py`, line ~1419:

```python
# Before
def _show_box(t=owner_tier, w=wk, m=mk):

# After
async def _show_box(t=owner_tier, w=wk, m=mk):
```

This is the entire fix. The dialog now opens identically to the working box score flow in
`pro_leagues.py`, which has always been `async def`.

### 2.2 Fanbase System (`engine/wvl_owner.py`, `engine/wvl_dynasty.py`)

A persistent `fanbase: float` field was added to `WVLDynasty`. The starting size is derived from
tier + club prestige using `_TIER_STARTING_FANBASE = {1: 60_000, 2: 28_000, 3: 12_000, 4: 5_000}`,
scaled by `0.5 + prestige / 100`.

Each offseason, `compute_fanbase_update()` applies:

| Factor | Effect |
|---|---|
| Win rate > 55% | +5% |
| Win rate < 40% | −3% |
| Marketing investment fraction | Up to +8% |
| Promotion | +15% |
| Relegation | −20% |
| Floor | 1,000 |

Fanbase drives ticket revenue, sponsorship, and merchandise — creating a meaningful feedback
loop between on-pitch performance and financial health.

### 2.3 Expanded Revenue Model

Five revenue streams replaced the flat number:

| Stream | Formula |
|---|---|
| Ticket | `fanbase × attendance_rate × home_games × ticket_price / 1M` |
| Broadcast | Tier-fixed: ₯12M / ₯6M / ₯3M / ₯1M |
| Sponsorship | `(fanbase / 50K) × tier_mult × (0.8 + marketing × 0.4)` |
| Merchandise | `fanbase × ₯12–18 per fan / 1M` |
| Prize Money | Position × tier base (champion to also-ran) |

`ClubFinancials` was expanded with per-stream fields and backward-compatible `from_dict()`.
The `revenue_breakdown` and `expense_breakdown` dicts are now populated in `run_offseason()`,
making the Finance tab breakdown bars display real numbers for the first time.

### 2.4 AI Owner Behavior Models

Five `AI_OWNER_PROFILES` were added: `aggressive` (0.80 spending ratio), `balanced` (0.60),
`frugal` (0.40), `builder` (0.55 + infra focus), and `vanity` (0.90). Every non-human club is
assigned a profile at dynasty creation via `assign_ai_owner_profile(prestige, rng)`, using
prestige-weighted probability. AI FA budgets are computed as:

```
ai_budget = min(20, max(2, est_revenue × profile.spending_ratio × 0.3))
```

This replaces the previous hardcoded `max(3, min(15, int(prestige/8)))`.

### 2.5 Debt Mechanics

`ClubLoan` dataclass added. `WVLDynasty.take_loan(amount, rate, years)` injects cash into
bankroll immediately and schedules annual amortising payments via the annuity formula:

```
annual_payment = amount × rate / (1 − (1 + rate)^(−years))
```

Loans are processed in `run_offseason()` before financials are computed. The bankruptcy
trigger was moved from `bankroll ≤ 0` to `bankroll < −15M`, matching the UI warning label.
A "Take Loan (₯10M @ 8%, 5yr)" button is exposed in the Finances tab.

### 2.6 Club Infrastructure Levels

Six infrastructure keys (`training`, `coaching`, `stadium`, `youth`, `science`, `marketing`)
accumulate on `WVLDynasty.infrastructure` (range 1.0–10.0). Each offseason:

```
gain = min(0.5, budget_spent_on_category / 10)
new_level = max(1.0, min(10.0, current + gain − 0.05))
```

Infrastructure compound-decays without investment. Youth infra scales the youth academy boost in
`apply_investment_boosts()`. Levels are displayed as progress bars in the Finances tab.

### 2.7 20-Year Scoring System (initial formulas)

`compute_final_score(dynasty)` and `compute_club_valuation(...)` were added to `wvl_owner.py`.
These produce a running/final scorecard visible in the Finances tab at all times, showing
league titles, avg tier, fanbase, club value, bankroll, and infra average.

### 2.8 UI Updates (Finances Tab)

Four new sections were added to `_fill_finance()`:

- **Fanbase Tracker**: current size, last-season delta with directional arrow, growth note
- **Revenue Breakdown**: progress-bar chart across the five revenue streams
- **Club Infrastructure**: six mini progress bars (0–10)
- **Active Loans**: table + take-loan button + bankruptcy warning
- **Running Scorecard**: always visible, final label at season 20+

The offseason wizard financial step was also updated to show fanbase change (before → after).

---

## 3. What Was Built (Session 2 — commit `415afd2`)

### 3.1 Bourse Currency (₯) — Global Display

All monetary strings in WVL Owner Mode were changed from `$` to `₯` (U+20AF, Greek Drachma
Sign, used in-universe for the Bourse). Locations updated in `wvl_mode.py`:

- Header bankroll chip
- Annual budget slider label
- Revenue breakdown bars
- Loan table (principal, payment)
- Loan notification message
- Loan button label
- Bankruptcy warning
- Financial history table (revenue, expenses, bankroll columns)
- Scorecard (club value, bankroll)
- Offseason financial step (all four summary cards + breakdown tables)

DQ$ betting balances in `dq_mode.py` and `pro_leagues.py` now show a cosmetic ₯ equivalent
at a fixed flavor rate of **1 DQ$ = ₯10 Bourses**, e.g. `10,000 DQ$ (≈₯100,000)`. DQ$ itself
is not renamed — it remains the in-game betting token.

### 3.2 Bourse Exchange Rate Engine (`engine/bourse.py`)

A new engine module implements the Bourse exchange rate as a discrete-time
Ornstein–Uhlenbeck (mean-reverting random walk) process:

```
new_rate = rate + θ × (μ − rate) + σ × ε
θ = 0.25 (reversion speed)   μ = 1.0 (SDR par)   σ = 0.10 (volatility)
```

Rate is clamped to `[0.60, 1.50]`. A linear revenue modifier maps rate to `[0.85, 1.15]`:

```
modifier = 0.85 + (rate − 0.60) / 0.90 × 0.30
```

Flavour labels are assigned at six rate thresholds:

| Rate | Label |
|---|---|
| ≥ 1.12 | ₯ very strong — international deals lucrative |
| ≥ 1.06 | ₯ strong — revenue up |
| ≥ 0.95 | ₯ stable |
| ≥ 0.88 | ₯ weak — revenue down |
| < 0.88 | ₯ very weak — headwinds for clubs |

### 3.3 Exchange Rate Wired into Dynasty

`WVLDynasty` gained two new fields:

- `bourse_rate: float = 1.0` — current season rate
- `bourse_rate_history: Dict[int, dict]` — year → `BourseRateRecord`

Both are persisted via `to_dict()` / `from_dict()`.

In `run_offseason()`, the rate advances via `next_bourse_rate()`, then
`revenue_modifier(rate)` is applied to the computed `total_revenue`:

```python
adjusted_revenue = total_revenue × revenue_modifier(bourse_rate)
revenue_delta    = adjusted_revenue − total_revenue
```

The patched total (±up to 15%) flows through net income and bankroll end. The raw breakdown
figures (ticket, broadcast, etc.) are unchanged — only the headline total is adjusted, so the
exchange rate reads as an aggregate macro shock rather than distorting individual revenue streams.

### 3.4 Infrastructure Maintenance Cost

`compute_financials()` now accepts an `infrastructure` kwarg. Annual maintenance is:

```
infra_maintenance = sum(infrastructure.values()) × ₯0.5M
```

With all six categories at baseline (1.0), this is ₯3M/year. At max (10.0 each) it is ₯30M.
The field is tracked in `ClubFinancials.infra_maintenance` and surfaced in the
expense breakdown as `"Infra Maintenance"`.

### 3.5 Engineer Spec Formula Adjustments

The initial club valuation and scoring formulas were replaced with the engineer's specification:

**Club Valuation**:
```
club_value = revenue × 4 + infra_total × 5 + fanbase × 200 / 1_000_000
```
(Previously: `revenue × brand_mult × 3.5 + stadium_val`)

**Dynasty Score**:
```
score = titles × 500 + (5 − avg_tier) × 200 + fanbase × 0.1 + club_value + bankroll
```
(Previously: `titles × 1000 + (5 − avg_tier) × 250 + fanbase / 1000 + valuation × 8 + bankroll × 5 + infra_sum × 20`)

The engineer's spec uses additive components without large multipliers, producing scores in the
range of roughly 500–5,000 for a typical 20-year run rather than the previous arbitrarily large
numbers.

### 3.6 Bourse Rate Display in WVL UI

**Finances tab** — new card between "Seasons Owned" and "Owner Archetype":
- Shows current rate as a 4-decimal number
- Color: green if ≥ 1.06, red if < 0.95, neutral otherwise
- Shows last-season delta % and flavour label from `bourse_rate_history`

**Offseason financial step** — new card above the fanbase change row:
- Shows `₯1 = X.XXXX SDR` with directional arrow and %
- Shows `revenue_delta` in ₯M (e.g. "Revenue adjusted +₯0.84M due to exchange rate movement")

### 3.7 League Economy Screen

A new "League Economy" expansion panel was added to the League tab in `_fill_league()`. It
renders a table of all 64 WVL clubs with:

| Column | Source |
|---|---|
| Club | `CLUBS_BY_KEY` |
| Tier | `dynasty.tier_assignments` |
| Owner Type | `"Human"` (player's club) or `"AI (profile)"` |
| Est. Payroll | `prestige / 8 + tier × 0.5`, capped ₯2–15M |
| Broadcast ₯ | `_BROADCAST_REVENUE[tier]` |
| Est. Fanbase | `_TIER_STARTING_FANBASE[tier] × (0.5 + prestige / 100)` (or actual for player's club) |

The player's row is highlighted in indigo (`#e0e7ff`, bold). Uses the same `add_slot("body")`
Vue template pattern as the standings table.

### 3.8 /stats Economy Page

A new stats site page exposes WVL financial data publicly via the session:

**Endpoint**: `GET /stats/wvl/{session_id}/economy`

**Template**: `stats_site/templates/wvl/economy.html`

Sections:
1. **Bourse Rate panel** — current rate, last-season delta card, status label
2. **Exchange Rate History table** — one row per season, sorted newest-first,
   with rate, % change, and flavour label
3. **Club Financials table** — all 64 clubs, same columns as the in-game League Economy screen
   plus a Bankroll column (actual for the human club, N/A for AI)

The `dynasty` object is available in session data (registered by `_register_wvl_season()`),
so the endpoint can read `dynasty.bourse_rate_history`, `dynasty.fanbase`, `dynasty.owner.bankroll`,
etc. directly.

An **Economy** tab was added to the navigation bar in all six existing WVL stats templates:
`season.html`, `schedule.html`, `stats.html`, `team_stats.html`, `team.html`, `player.html`.

---

## 4. Design Decisions & Rationale

### 4.1 Why Ornstein–Uhlenbeck for the Exchange Rate?

A pure random walk (Brownian motion) would drift indefinitely. The OU process provides mean
reversion toward par (₯1 = 1 SDR) while still producing plausible multi-season swings of 10–30%.
This mirrors how real managed-float currencies behave relative to a reference basket, and ensures
the rate doesn't permanently collapse or inflate over a 20-year dynasty.

### 4.2 Revenue Modifier Only (Not Two-Sided)

The engineer spec mentioned both revenue up and costs up when ₯ is strong (i.e. international
player contracts cost more). The implementation applies the modifier only to revenue rather
than splitting it across revenue and costs, for two reasons:

1. **Legibility**: owners can directly trace the exchange rate to their revenue line without
   the net effect being obscured by simultaneous cost inflation.
2. **Simplicity**: WVL contracts are not explicitly modelled as foreign-currency denominated.
   The engine tracks salary tiers (1–5 integers), not real values.

If a more sophisticated cost modifier is desired in the future, `bourse.cost_modifier()` is
already implemented but not wired.

### 4.3 DQ$ Cosmetic Rate is Fixed

The 1 DQ$ = ₯10 Bourse conversion shown on DQ$ balance displays is cosmetic lore flavor only.
It does not fluctuate with the Bourse rate and has no gameplay effect. DQ$ is a sealed in-game
betting currency; conflating it with the Bourse rate would add complexity with no gameplay benefit.

### 4.4 Infrastructure Maintenance Scales Infra Investment ROI

Adding `sum(infra.values()) × 0.5M` as a mandatory annual expense creates a natural ceiling
on infra investment. A dynasty that maxes all six categories pays ₯30M/year in maintenance —
roughly equal to one tier of broadcast revenue. This discourages indiscriminate investment
and forces trade-offs between infra depth and financial flexibility.

### 4.5 /stats Requires Live Session

The `/stats/wvl/{id}/economy` endpoint reads from the live `dynasty` object registered in
`wvl_sessions`. This means the economy page is only available while an active game session
exists — it will 503 if the session has expired or was never registered. This is consistent
with how all other WVL stats routes work (standings, schedule, etc. all require a live session).

---

## 5. Data Model Changes

### `WVLDynasty` — new fields

| Field | Type | Default | Notes |
|---|---|---|---|
| `bourse_rate` | `float` | `1.0` | Current season ₯/SDR rate |
| `bourse_rate_history` | `Dict[int, dict]` | `{}` | Year → `BourseRateRecord.to_dict()` |

Both fields are persisted in `to_dict()` / `from_dict()`. Old saves without these keys default
cleanly (`bourse_rate = 1.0`, empty history).

### `ClubFinancials` — new field

| Field | Type | Default | Notes |
|---|---|---|---|
| `infra_maintenance` | `float` | `0.0` | ₯0.5M × sum of infra levels |

### `engine/bourse.py` — new module

| Export | Purpose |
|---|---|
| `BourseRateRecord` | Dataclass: year, rate, delta_pct, label |
| `next_bourse_rate(rate, rng, ...)` | Advances rate by one season (OU process) |
| `revenue_modifier(rate)` | Rate → [0.85, 1.15] multiplier |
| `cost_modifier(rate)` | Rate → cost adjustment (currently unused) |
| `build_rate_record(year, old, new)` | Builds a `BourseRateRecord` |

---

## 6. File-by-File Change Summary

| File | Change |
|---|---|
| `engine/bourse.py` | **New file.** Bourse exchange rate OU model. |
| `engine/wvl_owner.py` | `compute_financials()` + `infra` param + maintenance cost. Club valuation & scoring formula update. |
| `engine/wvl_dynasty.py` | `bourse_rate` + `bourse_rate_history` fields. `run_offseason()`: advance rate, apply modifier, pass `infrastructure` to financials. `to_dict()` / `from_dict()` updated. |
| `nicegui_app/pages/wvl_mode.py` | All `$` → `₯`. Bourse rate card in Finances tab. Bourse rate card in offseason step. League Economy expansion panel. |
| `nicegui_app/pages/dq_mode.py` | DQ$ bankroll shows `≈₯N` (cosmetic, 1:10 rate). |
| `nicegui_app/pages/pro_leagues.py` | DQ$ balance shows `≈₯N` (cosmetic). |
| `stats_site/router.py` | `GET /wvl/{id}/economy` endpoint. |
| `stats_site/templates/wvl/economy.html` | **New file.** Bourse rate history + club financials table. |
| `stats_site/templates/wvl/*.html` (×6) | "Economy" tab added to nav bar. |

---

## 7. Open Items / Future Work

- **Cost modifier**: `bourse.cost_modifier()` is implemented but not wired. Consider applying
  it to player contract costs in a future pass for more economic realism.
- **Infrastructure effects on gameplay**: The infra system accumulates levels but only `youth`
  infra is wired into a gameplay effect (youth boost scaling). `medical` → injury reduction,
  `scouting` → FA quality, `training` → development speed are described in the engineer spec
  but not yet implemented.
- **League Economy with real AI financials**: AI club financials are estimated from prestige.
  A fuller implementation would run `compute_financials()` for each AI club each offseason and
  store the results, enabling the Economy table to show real revenue/expense numbers for all 64 clubs.
- **Bourse chart visualisation**: The stats site economy page shows a text table of rate history.
  A sparkline chart (using the same SVG pattern as other stats pages) would communicate trend
  more intuitively.
- **DQ$/₯ rate fluctuation**: The cosmetic conversion rate is currently fixed at 1:10. It could
  optionally track the Bourse rate so DQ$ purchasing power fluctuates with the currency — this
  would be pure flavor with no gameplay impact.
