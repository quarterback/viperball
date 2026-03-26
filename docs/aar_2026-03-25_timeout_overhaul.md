# AAR: Game Clock, Timeout, Overtime, Referee, Injury & Efficiency Overhaul

**Date:** 2026-03-25
**Branch:** `claude/referee-bias-system-B6KAy`

---

## Overview

Major overhaul touching six systems: game clock model, timeout logic, postseason overtime, referee bias, injury catalog, and KenPom-style efficiency metrics. The common thread: making the simulation behave like a real broadcast game, not a spreadsheet.

---

## 1. Game Clock vs Play Clock

### Problem

The engine treated the game clock and play clock as one number. Every play — including scores, penalties, and incompletions — burned 18-38 seconds of game clock. This meant:

- A TD at 1:01 left the opposing team starting at 0:17 (44 seconds vanished)
- An offsides penalty at 0:03 left no time for another play
- Trailing teams were robbed of comeback time after opponent scores
- Post-score "celebration/setup" code burned an additional hidden 10-15 seconds on top

### Fix

**Game clock** and **play clock** are now distinct:

| Situation | Game Clock Burns |
|-----------|-----------------|
| Normal play (clock running) | Full play clock (18-38s) |
| After a score | Action time only (3-9s) |
| After a penalty | Action time only (3-6s) |
| After incomplete kick pass | Action time only (4-7s) |
| First play of new drive after score | Action time only (clock still stopped from score) |

**Action time varies by play type:**
- Short runs, stuffs: 3-6 seconds
- Medium gains, kick passes: 5-8 seconds
- Big plays (20+ yards), lateral chains (2+ laterals): 6-9 seconds
- Kicking plays (punt, drop kick, place kick): 5-8 seconds

**Clock state persists across drives.** When a drive ends on a TD, the game clock stays stopped through the transition (delta yards, teams getting set, kickoff) until the next snap. The first play of the new drive only burns action time.

Removed hidden 10-15 second post-score time deductions that were stacked on top of the correct stoppage.

### Verified

```
TD at 6:21 → next play at 6:14 (7s elapsed)        ← action time only
Play after at 6:08 (6s elapsed)                      ← clock still stopped
Play after at 5:38 (30s elapsed)                     ← normal play clock resumes
```

---

## 2. Victory Formation

### Problem

Victory formation was triggering with 4+ minutes remaining in Q4. A team with a double-digit lead would kneel from 4:34 down to 0:58 — six consecutive kneels burning the entire final quarter.

### Fix

Hard rule: victory formation ONLY available when `time_remaining <= 50` seconds in Q4. Any lead is sufficient at that point. Before 50 seconds, teams must keep playing.

---

## 3. Timeout System

### Problem

Timeouts were hoarded until the final 2-5 minutes. Games had only 1-2 charged timeouts, almost all in Q4, with both teams ending with 3-4 unused per half.

### New Categories

| Category | Caller | When | Quarters |
|----------|--------|------|----------|
| **Momentum stop** | Defense | After 2+ consecutive opponent scoring drives | Any |
| **Scheme reset** | Offense | After sack/big loss or 2+ consecutive negative plays | Any |
| **Icing the kicker** | Defense | Before kick attempt on 5th-6th down in close games | Any |
| **Fresh legs** | Either | 3+ starters have energy below 40% | Q1-Q3 |
| **Personnel regrouping** | Offense | Stalled drive (4+ plays, ≤3 yards) | Any |
| Strategic clock stop | Defense | Trailing, clock winding down | Q2/Q4 |
| Offensive clock stop | Offense | Trailing, preserve time | Q2/Q4 |
| Defensive kneel stop | Defense | After opponent kneel | Q4 |

### Coaching Intelligence

- 3-minute warning treated as a "free timeout" — coaches budget around it
- Good clock managers save at least 1 TO as reserve
- Q4 crunch time (<3 min) suppresses non-clock categories
- `timeout_hoarder` trait resists 30-60%; `timeout_sprinter` burns 25-50% faster

### Bug Fixes

- `_drive_yards` now actually tracked (was always 0 via `getattr` fallback)
- `_drive_consecutive_negative` tracked for scheme reset logic
- `_consecutive_opponent_scores` tracked per team for momentum stops

### Results (20-game sample)

| Metric | Before | After |
|--------|--------|-------|
| Avg TOs per game | ~2 | 6.3 |
| TOs remaining (avg/team/half) | 3-4 | ~2 |
| Q1-Q3 timeouts | Rare | Common |

Category breakdown: Scheme reset 34%, Momentum 26%, Offensive clock 24%, Strategic 12%, Kneel stop 4%.

---

## 4. Postseason Overtime

### Problem

Playoff games could end in a tie. UTSA 45 — Grambling 45 in a playoff game is unacceptable.

### Fix

Successive 8-minute overtime quarters until someone wins. Only triggers for postseason games (`is_playoff=True`, `week >= 900`). Regular season ties remain as ties.

Each OT period:
- Fresh 4 timeouts per team
- 3-minute warning applies
- Energy recovery (+20 for all players)
- Alternating first possession
- Max 5 OT periods (safety valve)
- OT plays appear as Q5, Q6, etc. in play-by-play

`is_playoff=True` now passed from season.py for all bowl and playoff games. Fast-sim overtime upgraded from random rouge to OT TD (weighted by team strength).

### Results (200-game sample)

- 4.5% of playoff games go to OT
- 0% ties in playoff mode
- Regular season: 3.5% ties (unchanged, no OT)

---

## 5. Punt Logic Fix

### Problem

Trailing teams could punt on 6th down, which is strategically insane — you're giving up when you need to score.

### Fix

A trailing team (`score_diff < 0`) NEVER punts on 6th down. They either kick (if available) or go for it. Also blocks punts with ≤30 seconds left in Q4 regardless of score.

---

## 6. Referee Bias System

### Design

300 named referees generated via the name generator, grouped into 3-person crews. Each has hidden attributes (accuracy 0.905-0.98, home favor, consistency). User only sees crew names.

**Blown call types:** Phantom flag, swallowed whistle, spot error.

**Coach challenge system:** 3 challenges per game per team. Replay always gets the correct call. Coaches challenge ~60% of blown calls they notice. Wasted challenges on correct calls modeled separately (~0.1% per play).

**Calibration:** Most games are completely clean. Season-wide error rate targets 0.5-3% of penalty situations. Playoff games always get top-rated crews.

Officials listed subtly at bottom of box score alongside weather.

---

## 7. Injury Catalog Expansion

Expanded from 83 to 190 entries with OOTP-style metadata:

| Field | Values | Purpose |
|-------|--------|---------|
| `freq` | 1-5 | Frequency weighting (common injuries appear more) |
| `reinjury` | 0-2 | Re-injury risk (same body part = longer recovery) |
| `nagging` | 0-1 | Can flare up after return |
| `surgery` | 0-2 | Surgery requirement |
| `inf_run` | 0-3 | Impact on running/speed |
| `inf_kick` | 0-3 | Impact on kicking |
| `inf_lateral` | 0-3 | Impact on lateral skill |
| `min_weeks`/`max_weeks` | int | Override tier default timelines |

Injury profile shifted toward soccer/basketball (more soft tissue, concussions elevated for no-hard-helmet Viperball). Off-field expanded with realistic college issues (academics, mental health, visa, disciplinary).

### Injury Report UI

- Conference + team dropdown filters
- New metric cards: Nagging, Required Surgery
- Active table shows re-injury risk, nagging, surgery, attribute impact
- "Injuries by Body Part" histogram
- "Nagging / Re-injury Watch" section

---

## 8. KenPom-Style Efficiency Metrics

New per-drive efficiency breakout mapped from basketball analytics to Viperball:

| Metric | Viperball Meaning | KenPom Equivalent |
|--------|------------------|-------------------|
| Raw O | Points per 10 drives | AdjO |
| Raw D | Opponent pts per 10 drives | AdjD |
| EK% | Value-weighted kick success | eFG% |
| TO% | Turnovers per drive | TO% |
| TOD% | Forced turnovers per opp drive | TOD% |
| LR% | Lateral recovery rate | OR% |
| FDR | Penalty first downs per play | FTR |
| RLE | Rush yards per carry | 2P% |
| KP% | Kick pass completion rate | 3P% |
| Adj T | Plays per game | AdjT |

25 new KenPom accumulators on TeamRecord, populated from game_stats. Full glossary at `docs/kenpom_glossary.md`.

---

## 9. Box Score Improvements

- Team names everywhere (no HOME/AWAY labels)
- Individual stat leaders (rushing, kick passing, receiving, defense)
- Time of possession estimate
- Organized stat sections with headers (Rushing, Kick Passing, Laterals, etc.)
- Down conversion percentages
- Declined penalties tracked separately

---

## What's Not Done Yet

- **Opponent-adjusted efficiency** (AdjO/AdjD weighted by schedule strength)
- **Nagging injury flare-ups** (elevated re-injury risk for 2-3 weeks after return)
- **Per-attribute DTD penalties** (use inf_run/kick/lateral for targeted stat reductions)
- **Conference-assigned referee crews** (refs can't officiate their own conference)
- **KenPom UI display** on the stats page (data is in the API, needs frontend)
- **Icing the kicker / fresh legs** categories need more testing with varied rosters
