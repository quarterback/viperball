# Anti-Tanking Draft Lottery Simulator — Project Brief

## What I wanted to build

An interactive web tool — hosted at **viperball.fly.dev** in the existing **viperball.xyz / `/stats`** style (FastAPI + Jinja2 + Bloomberg-terminal aesthetic, **not** NiceGUI) — that lets me play with different NBA draft lottery proposals and see how they actually behave over time.

This is a **standalone simulation lab**, not tied to the WVL game mode. The viperball repo is just the host because it already has the infra.

## The core problem I'm modeling

NBA tanking exists because the expected value of a top pick exceeds the value of marginal wins. Every "fix" the league has tried tweaks incentives at the margin without changing the underlying loop. I want to test, in simulation, whether structural changes actually shift behavior — or just smooth tanking out.

## Lottery systems I want to compare

| # | System | Mechanic |
|---|---|---|
| 1 | **Current NBA** (baseline) | Bottom-3 share 14% odds for #1, descending after that |
| 2 | **Flat bottom** | All non-playoff teams get equal odds |
| 3 | **Play-in boost** | Play-in appearance > finishing last; play-in teams get meaningful odds |
| 4 | **UEFA coefficient** | Rolling 3–5 year weighted performance score determines odds |
| 5 | **RCL (Rolling Competitive Lottery)** — my full proposal | Multi-year coefficient + intra-tier head-to-head bonus + #1 pick cap (no repeat #1 in 5 years, no top-3 more than twice in 5) |
| 6 | **Lottery tournament** | Bottom 8 teams play single-elim; winning gets you better picks |
| 7 | **Pure inversion** | Best non-playoff team gets the best odds — rewards competitive failure, not failure |
| 8 | **Gold Plan (PWHL)** | Draft order = wins accumulated *after* a team is mathematically eliminated from playoff contention. The team with the most post-elimination wins picks first. Already in live use by the PWHL — provides real-world behavioral data, not just theory. |

### Why the Gold Plan matters

The Gold Plan is the only system on this list that has been **actually deployed** in a top-tier pro league. It's also the most surgical fix — it doesn't replace the lottery framework, it just changes what determines order *within* the non-playoff group. That makes it incrementally adoptable in a way that RCL, inversion, or a tournament are not. The simulator should treat it as a near-baseline alongside Current NBA, since it's the realistic policy alternative an actual league might adopt.

## RCL spec (the one I'm actually pushing)

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

**The point:** stop rewarding losing, start rewarding *competitive failure*.

## What the simulator needs to do

1. **Model an NBA-shaped league** — 30 teams, 2 conferences, true-talent ratings, 82-game seasons sim'd as cheap probabilistic matchups (not full game sims).
2. **Model tanking behavior** — teams adjust late-season effort based on how much losing helps them under the active lottery system. This is the whole point; the sim has to *react* to incentives or it proves nothing.
3. **Run multi-year Monte Carlo** — 10–20 seasons per run, 100+ runs per system. Drafted talent feeds back into team strength next year.
4. **Output behavior metrics, not just draft order:**
   - Late-season effort (win % of bottom teams in March vs January)
   - Repeat-#1-pick frequency
   - Pick distribution across the league (Gini-style)
   - How long bad teams stay bad
   - Competitive balance variance over time
   - "Tank cycles" — teams that deliberately bottom out
5. **Side-by-side comparison UI** — pick two systems, see them rendered next to each other across all metrics.

## Architecture I had planned

- `engine/lottery_sim.py` — pure Python Monte Carlo engine. Pluggable `LotterySystem` interface so adding a new rule = one class.
- `stats_site/lottery_router.py` — FastAPI router mounted at `/stats/lottery/`. Form controls → POST → run sim → render results template.
- `stats_site/templates/lottery/index.html` — config page (pick systems, set knobs: # seasons, # sims, tanking sensitivity).
- `stats_site/templates/lottery/results.html` — comparison view, server-rendered tables + inline SVG bar charts.
- Wire into `api/main.py` next to the existing `stats_router` include.
- Branch: `claude/anti-tanking-lottery-proposals-ydZF5`.

## The decision the sim is supposed to surface

Every lottery system collapses into one question:

> **Are you punishing failure, or rewarding competitive failure?**

Current NBA punishes failure softly (which incentivizes tanking). RCL/inversion reward competitive failure. The simulator's job is to show, empirically, which proposals actually change team behavior vs which just rearrange the deck chairs.
