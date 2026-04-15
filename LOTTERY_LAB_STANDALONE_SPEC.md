# Lottery Lab — Standalone Repo Spec

A self-contained NBA draft lottery scenario simulator. Build this as its **own repo** — do not try to wedge it into another project. Greenfield. No legacy code to navigate.

## Why standalone

Previous attempts to build this inside the viperball repo kept stalling because agents got lost exploring the existing codebase before writing any code. A fresh repo eliminates that failure mode: there's nothing to read, only files to create.

## Stack

- **Python 3.11+**
- **FastAPI** (web framework)
- **Jinja2** (server-side templates)
- **Uvicorn** (ASGI server)
- **No JS framework.** Inline SVG for charts, vanilla JS for any interactivity.
- **No database.** Sims run in-process; results live in memory or a query string.

## Aesthetic

Bloomberg-terminal dark theme. Monospace fonts. Dense tables. CSS custom properties for theming. All CSS in a single `base.html` template — no external stylesheets.

Color palette starting point:
```
--bg: #0a0a0a
--bg-alt: #141414
--fg: #e8e8e8
--fg-dim: #888
--accent: #ff8c00
--green: #4ade80
--red: #f87171
--border: #2a2a2a
```

Font stack: `'Berkeley Mono', 'IBM Plex Mono', 'SF Mono', Consolas, monospace`. Base size 12px.

## Repo layout

```
lottery-lab/
├── README.md
├── pyproject.toml          # or requirements.txt
├── .gitignore              # python defaults
├── Dockerfile              # for deployment
├── main.py                 # uvicorn entry: app = FastAPI()
├── engine/
│   ├── __init__.py
│   └── lottery_sim.py      # ALL simulation logic here
├── web/
│   ├── __init__.py
│   ├── router.py           # FastAPI routes
│   └── templates/
│       ├── base.html       # master template + all CSS
│       ├── index.html      # config form
│       └── results.html    # comparison view
└── tests/
    └── test_lottery_sim.py # smoke tests for the engine
```

## The 8 lottery systems to model

| # | System | Mechanic |
|---|---|---|
| 1 | **Current NBA** (baseline) | Bottom-3 each get 14% odds for #1, descending after that. Status quo. |
| 2 | **Flat bottom** | All non-playoff teams get equal odds for every pick. Removes bottom-out incentive entirely. |
| 3 | **Play-in boost** | Play-in teams get equal-or-better odds than teams that finished worse. Making the play-in is itself the reward. |
| 4 | **UEFA coefficient** | Odds set by a rolling 3-year weighted performance score, not single-season record. Kills one-year tanking. |
| 5 | **RCL (Rolling Competitive Lottery)** | Multi-year coefficient + intra-tier head-to-head bonus + hard caps (no #1 more than once in 5 years, no top-3 more than twice in 5). Spec below. |
| 6 | **Lottery tournament** | Bottom 8 non-playoff teams play single-elim after the regular season. Winning the tournament = #1 pick. |
| 7 | **Pure inversion** | Best non-playoff team gets best odds. Worst gets worst. Rewards competitive failure. |
| 8 | **Gold Plan (PWHL)** | Draft order = wins accumulated *after* a team is mathematically eliminated from playoff contention. Most post-elimination wins picks first. **Already deployed by the PWHL — only proposal here with real-world data.** |

## RCL spec (system #5)

```
LC = (Y1 * 0.5) + (Y2 * 0.3) + (Y3 * 0.2)

Year score Y = Base + Tier Performance
  Base = rank among non-playoff teams (best non-playoff = 10 pts, worst = 1)
  Tier Performance = (wins vs lottery teams) - (losses vs lottery teams)

Hard caps:
  - No #1 pick more than once in 5 years
  - No top-3 pick more than twice in 5 years
  - Min-win threshold: teams under X wins take an LC penalty
```

## Engine API contract

`engine/lottery_sim.py` should expose roughly:

```python
@dataclass
class Team:
    id: int
    name: str
    true_talent: float        # 0–100
    tank_propensity: float    # 0–1, set by team archetype

@dataclass
class SeasonResult:
    standings: list[tuple[int, int, int]]   # (team_id, wins, losses)
    head_to_head: dict[tuple[int, int], tuple[int, int]]  # (a,b) → (a_wins, b_wins)
    eliminated_week: dict[int, int]         # team_id → week eliminated

class LotterySystem(Protocol):
    name: str
    def draft_order(self, history: list[SeasonResult], constraints: DraftConstraints) -> list[int]: ...

def simulate_run(
    system: LotterySystem,
    seasons: int = 15,
    games_per_season: int = 82,
    seed: int | None = None,
) -> RunResult: ...

def monte_carlo(
    system: LotterySystem,
    runs: int = 100,
    **sim_kwargs,
) -> MetricsBundle: ...
```

`MetricsBundle` should include:
- Late-season effort (win % of bottom teams in final 20 games vs first 60)
- Repeat-#1-pick frequency
- Pick distribution (Gini coefficient on top-5 picks)
- Tank cycles (count of teams that intentionally bottom out)
- Competitive balance (stddev of wins, year over year)
- Average wins of teams receiving top-3 picks

## Tanking behavior model

This is the crucial part — without it the sim is meaningless.

- Each team has a `tank_propensity` (0–1).
- Each week, a team's "effort multiplier" is computed from:
  - How likely they are to make the playoffs (sigmoid on current standing)
  - How much their lottery position improves by losing more games (system-dependent)
  - Their `tank_propensity`
- Effort multiplier scales their `true_talent` for that week's game.
- This means each lottery system produces *different* late-season win patterns. That's the whole point.

## Build order — one file per commit

1. **`engine/lottery_sim.py`** — pure Python. League model, season sim, all 8 systems, Monte Carlo runner, tanking behavior. Test from a REPL: `from engine.lottery_sim import *; monte_carlo(CurrentNBA(), runs=10)`. **Commit.**
2. **`tests/test_lottery_sim.py`** — smoke tests. Each system runs without crashing, returns sane outputs. **Commit.**
3. **`main.py` + `web/router.py` + `web/templates/base.html` + `web/templates/index.html`** — minimum viable web app. Form with system pickers and sim count. Renders but does nothing yet. Verify it loads. **Commit.**
4. **`web/templates/results.html` + POST handler in router** — wire form → run sim → render basic tables. No charts. **Commit.**
5. **Inline SVG bar charts** in results.html. No JS lib. **Commit.**
6. **Side-by-side comparison view** — pick two systems, render together. **Commit.**
7. **`Dockerfile` + deploy config** — Fly.io, Render, or Railway. Whichever is fastest to ship. **Commit.**

## Rules for the building agent

- **Don't explore.** This spec is the only context needed.
- **One file per turn.** Then commit.
- **No "while I'm here" edits.** Each commit does one thing.
- **Verify in browser after each step.** If the page doesn't load, stop and fix before moving on.
- **If a step is bigger than ~300 lines, split it.**
- **Don't add features not in this spec.** No auth, no DB, no user accounts, no analytics.

## The question the sim is supposed to answer

> **Are you punishing failure, or rewarding competitive failure?**

That's it. Every system on the list is a different answer to that question. The tool exists to make the trade-offs visible.
