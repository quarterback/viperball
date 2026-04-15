# Anti-Tanking Lottery Simulator — Handoff Spec

Build a standalone NBA draft lottery scenario simulator at `/stats/lottery/` in the viperball repo (`quarterback/viperball`, branch `claude/anti-tanking-lottery-proposals-ydZF5`). Use the existing `/stats` site style: FastAPI + Jinja2 + Bloomberg-terminal aesthetic. **Not NiceGUI.**

## The 8 lottery systems to model

| # | System | Mechanic |
|---|---|---|
| 1 | **Current NBA** (baseline) | Bottom-3 each get 14% odds for #1, descending after that. The status quo. |
| 2 | **Flat bottom** | All non-playoff teams get equal odds for every pick. Removes the bottom-out incentive entirely. |
| 3 | **Play-in boost** | Play-in teams get equal-or-better odds than teams that finished worse. Making the play-in is *itself* the reward. Tests whether you can move the tanking incentive upward. |
| 4 | **UEFA coefficient** | Odds set by a rolling 3–5 year weighted performance score, not single-season record. Kills one-year tanking but doesn't change *who* benefits. |
| 5 | **RCL (Rolling Competitive Lottery)** | The full proposal: multi-year coefficient + intra-tier head-to-head bonus (beating other lottery teams helps you, losing to them hurts you) + hard caps (no #1 pick more than once in 5 years, no top-3 more than twice in 5). Spec below. |
| 6 | **Lottery tournament** | Bottom 8 non-playoff teams play a single-elim tournament after the regular season. Winning the tournament = #1 pick. Pure inversion of incentive. |
| 7 | **Pure inversion** | Best non-playoff team gets the best odds. Worst non-playoff team gets the worst odds. Rewards competitive failure rather than failure. |
| 8 | **Gold Plan (PWHL)** | Draft order = wins accumulated *after* a team is mathematically eliminated from playoff contention. Most post-elimination wins picks first. **Already deployed by the PWHL — the only proposal here with real-world data.** Treat as a near-baseline alongside Current NBA since it's the realistic incremental policy a league might actually adopt. |

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

## What the simulator must do

1. **Model an NBA-shaped league** — 30 teams, 2 conferences, true-talent ratings, 82-game seasons sim'd as cheap probabilistic matchups (not full game sims).
2. **Model tanking behavior** — teams adjust late-season effort based on how much losing helps them under the active lottery system. The sim has to *react* to incentives or it proves nothing.
3. **Multi-year Monte Carlo** — 10–20 seasons per run, 100+ runs per system. Drafted talent feeds back into team strength next year.
4. **Output behavior metrics:**
   - Late-season effort (win % of bottom teams in March vs January)
   - Repeat-#1-pick frequency
   - Pick distribution across the league (Gini-style)
   - How long bad teams stay bad
   - Competitive balance variance over time
   - Tank cycles
5. **Side-by-side comparison UI** — pick two systems, render them next to each other across all metrics.

## Build order — one file per commit

1. `engine/lottery_sim.py` — pure Python, zero web deps. League model + season sim + all 8 lottery systems + Monte Carlo runner. Testable from a REPL. **Commit.**
2. `stats_site/lottery_router.py` + `templates/lottery/index.html` — form-only page (system dropdowns, season count, sim count). Wire into `api/main.py`. Verify at `/stats/lottery/`. **Commit.**
3. `templates/lottery/results.html` + POST handler — run sim, render tables. No charts. **Commit.**
4. Add inline SVG bar charts to results. No JS library. **Commit.**
5. Side-by-side comparison view (two systems rendered together). **Commit.**

## Rules

- Don't re-read the codebase. This spec is enough context.
- One file per turn, then commit.
- No exploration past step 1 unless something errors.
- Verify each step in the browser before moving on.
- If a step is bigger than ~300 lines, split it.

The decision the sim is supposed to surface: **Are you punishing failure, or rewarding competitive failure?** That's the only question that matters.
