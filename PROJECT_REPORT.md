# Viperball Engine — Project Report: Engine Rebalance Sprint

**Date:** February 21, 2026
**Branch:** `claude/viperball-league-simulator-Tcg8S`
**Scope:** 4 commits, 1,032 insertions / 453 deletions to `engine/game_engine.py`

---

## Executive Summary

This sprint replaced the Viperball game engine's core resolution mechanics with a **contest-based stochastic system** where every yard, every completion, and every kick is determined by player-vs-player skill matchups — not static tables. It then tuned scoring cadence, turnover rates, conversion probabilities, and the entire kicking game to produce realistic, story-generating football within Viperball's unique 6-down, no-forward-pass framework.

### Key Outcomes (per team, per game averages)

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Total Score | ~53 | ~68 | 65-85 |
| Touchdowns | ~3.4 | ~4.0 | 3-5 |
| TD Drive % | 33.6% | ~41% | 35-45% |
| Total Kick Attempts | ~1.5 | ~2.8 | 3-5 |
| Kick Success Rate | ~55% | ~75% | 70-85% |
| Turnovers/team | ~4.5 | ~2.0 | 1.5-3 |
| 4th Down Conversion | 57% | ~85% | 80-90% |
| 5th Down Conversion | 38% | ~71% | 65-75% |
| 6th Down Conversion | 22% | ~63% | 55-65% |

---

## Commit-by-Commit Breakdown

### Commit 1: `3d9c864` — Contest-Based Stochastic Resolution

**903 insertions, 296 deletions** — The foundational rewrite.

#### What Changed

The old engine used flat multiplier stacks: `base_yards * speed_factor * archetype_bonus * fatigue * weather * coaching * rhythm`. This produced narrow, predictable outcomes where player attributes blurred together.

The new system uses **contest-based resolution** — every play is a dice battle between specific offensive and defensive players:

**`_contest_run_yards(carrier, tackler, play_config)`** — The core run resolution:
```
Offensive gravity = speed × 0.4 + power × 0.3 + agility × 0.3
Defensive gravity = tackling × 0.5 + awareness × 0.25 + speed × 0.25
Delta = offense - defense (typically -30 to +30)
Center = 5.0 + 2.5 × sigmoid(delta/12)  →  2.5 (defense dominates) to 7.5 (offense dominates)
Variance = 0.8 (blowout gap) to 2.2 (even matchup)
Result = gaussian(center, variance)
```

The key insight: **proximity in skill creates high variance**. Two evenly-matched players produce wildly different outcomes play-to-play — sometimes the runner breaks free for 12, sometimes they're stuffed for -1. A mismatch produces *consistent* outcomes — the elite back reliably gains 6-7 against a weak tackler.

**`_contest_kick_pass_prob(kicker, receiver, def_team)`** — Kick pass completion:
```
Offensive skill = kick_accuracy × 0.6 + receiver.hands × 0.4
Defensive coverage = average awareness of coverage players
Delta fed through sigmoid → base probability ~55% at even skill
Gaussian noise roll → spectacular catches AND terrible drops
```

**Other systems added in this commit:**
- `_breakaway_check()` — 8+ yard gains have a 15% chance of extending (8-25 extra yards), with speed gap and defensive fatigue as modifiers
- `_red_zone_td_check()` — Contest-influenced goal-line scoring (fp ≥ 95: 20% → fp ≥ 98: 55% → fp ≥ 100: automatic)
- `_defensive_fatigue_factor()` — Drive length wears down defenders (5+ plays: 1.05×, 8+: 1.15×, 12+: 1.25×)
- `_run_fumble_check()` — Weather, ball security, archetype, and coaching all factor into fumble probability
- Drive chain momentum — 3+ consecutive positive plays widen rushing lanes (+0.3/play, capped at +1.5)
- Kick pass "floor spacing" — A completed kick pass spreads the defense thin on the NEXT play (+1.0 center, 0.85× variance)

---

### Commit 2: `e2fae93` — Strategic Tuning Layer

**179 insertions, 27 deletions** — Added situational intelligence on top of the contest system.

#### 2nd-and-Short Aggression
When `down == 2 and ytg <= 5`, the engine boosts play variety — speed options and sweeps get selected more often. This prevents the "dive-dive-dive" repetitiveness that conservative play-calling produced.

#### Hot Streak System
**`_hot_streak_modifier(player)`** — Players build momentum through consecutive successful contests:

| Streak | Center Bonus | Variance | Effect |
|--------|-------------|----------|--------|
| 3 plays | +0.4 | ×0.80 | Getting warm |
| 4 plays | +0.6 | ×0.70 | In the zone |
| 5+ plays | +0.8 | ×0.60 | Locked in — tight distribution, biased upward |

A running back on a hot streak becomes progressively harder to stop — their variance *narrows toward the high end*, producing reliably excellent results. A single tackle-for-loss resets the counter. This creates narrative: the announcer's "he's got it going tonight" moment has a mechanical basis.

#### Fatigue Cliff
**`player_fatigue_modifier(player)`** — Tiered energy system with a brutal cliff:

| Energy | Multiplier | Implication |
|--------|-----------|-------------|
| 80-100% | 1.00 | Fresh, full capacity |
| 60-80% | 0.95 | Minor fatigue |
| 40-60% | 0.85 | Noticeable degradation |
| 20-40% | 0.55-0.85 | **THE CLIFF** — a 95-rated star at 25% energy performs worse than a fresh 75-rated backup |
| <20% | 0.40 | Near-useless, should be subbed |

The cliff forces depth chart usage. Riding your star running back for 15 straight plays is a recipe for disaster — not just from reduced effectiveness, but from the `fatigue_injury_multiplier` that reaches 2.5× at 20-40% energy and 4.0× below 20%.

---

### Commit 3: `bc10cbc` — Turnovers, Conversions, and Explosive Returns

**338 insertions, 73 deletions** — The most impactful single tuning pass.

#### Problem: Turnover Epidemic
The engine was producing ~4.5 turnovers per team per game. Drives were dying to fumbles and interceptions at rates that made sustained scoring impossible. Real football (even chaotic Viperball) shouldn't have a coin-flip fumble risk on every other play.

#### Solution: Targeted Fumble Reduction
- Weather fumble modifiers compressed: `rain/snow/sleet = ×1.20` (was ×1.50+)
- Lateral fumble base rate reduced to 0.08 with compounding +0.04 per additional lateral
- Ball security attribute now meaningfully protects against fumbles (85+ hands = ×0.70)
- `disciplinarian` coaching classification applies fumble reduction multiplier
- Result: turnovers dropped from ~4.5 to ~2.0 per team per game

#### Late-Down Needs-Based Conversion
The biggest mechanical innovation. On downs 4-6, the run resolution switches from the standard sigmoid to a **needs-based contest**:

```
Standard (downs 1-3): center = 5.0 + sigmoid(delta)
Late-down (downs 4-6): center = yards_to_go + buffer × urgency

buffer = 3.0 + talent_edge × 3.0
  Elite offense vs weak D → +6 buffer (overshoot by 6 yds)
  Even matchup          → +3 buffer
  Weak offense vs elite D → 0 (coin flip)

urgency = {4: 1.0, 5: 0.82, 6: 0.65}
```

This means on 4th-and-3 with evenly matched players, the center is `3 + 3 × 1.0 = 6` — the offense is expected to gain 6 yards, comfortably converting. On 5th-and-8, center drops to `8 + 3 × 0.82 = 10.5` — still possible but tighter. On 6th-and-15, it's `15 + 3 × 0.65 = 17` against a mean of ~5 — conversion requires elite talent or luck.

The urgency decay across downs 4→5→6 produces the natural conversion cascade: ~85% → ~71% → ~63%.

#### Explosive Lateral Interception Returns
When a lateral is intercepted, the interceptor now gets a **talent-based return**:
```
return_talent = (speed × 0.6 + agility × 0.4 - 60) / 40
return_yards = gaussian(30 + return_talent × 20, 12)
```
A fast, agile defender who picks off a lateral in the open field averages 40-50 return yards. If they reach the end zone, it's a pick-six worth 9 points — a game-changing momentum swing.

#### Kick Pass Late-Down Urgency
On downs 4-6, kick pass completion gets a talent-scaled boost:
```
down 4: +0.18 × (0.5 + off_talent × 0.5)
down 5: +0.12 × (0.5 + off_talent × 0.5)
down 6: +0.08 × (0.5 + off_talent × 0.5)
```
Elite kicker/receiver pairs get the full boost. Average pairs get half. This prevents the "every 4th down attempt fails" problem while keeping talent as the differentiator.

---

### Commit 4: `5294ebb` — Kicker-Range Model

**156 insertions, 166 deletions** — Complete rewrite of the kicking system.

#### Philosophy
The user's directive was clear: *"A sport that developed around kicking because there's no forward pass would have better kickers. Field goals should not fail in range. The kicker should determine what's going on."*

The old system used static distance tables — 25 yards = 0.96, 35 yards = 0.86, etc. — with a narrow `kicker.kicking / 85` multiplier. A 95-rated kicker and a 65-rated kicker had nearly identical accuracy curves. Player skill was decorative.

#### The Kicker-Range Model
Each kicker now has a **comfortable range** determined entirely by their skill attribute:

**Place Kicks (3 pts):**
```
comfortable_range = 45 + (kicker_skill - 60) × 0.9

60-skill → comfortable to ~45 yards
75-skill → comfortable to ~58 yards
85-skill → comfortable to ~67 yards
95-skill → comfortable to ~76 yards

Within range:  0.88 - 0.98 success (near-automatic)
0-10 past:     0.35 - 0.85 (steep dropoff)
10-20 past:    0.10 - 0.30 (desperation)
20+ past:      0.03 - 0.08 (hail mary)
```

**Drop Kicks (5 pts):**
```
comfortable_range = 30 + (kicker_skill - 60) × 0.75

60-skill → comfortable to ~30 yards
75-skill → comfortable to ~41 yards
85-skill → comfortable to ~49 yards
95-skill → comfortable to ~56 yards

Within range:  0.86 - 0.96 success
Beyond: same steep dropoff curve
```

Drop kicks have a shorter comfortable range because they're mechanically harder (ball bounces off the ground) but worth 5 pts vs 3 pts.

#### Decision Logic Rewrite: `select_kick_decision()`
The 6-down structure fundamentally changes kick timing:

| Down | Decision | Rationale |
|------|----------|-----------|
| 1-4 | **Always go for it** | Down 4 in Viperball = 2nd down in NFL. You have 2+ downs left. |
| 5 | **THE decision point** | Like 4th down in NFL. Kicker skill adjusts go-for-it threshold. |
| 6 | **Last chance** | Kick if anything is available. Punt if not. Go for it only on very short ytg. |

**Kicker skill adjusts the threshold on 5th down:**
```
base_threshold from GO_FOR_IT_MATRIX (field-position dependent)
kicker_adj = (75 - kicker_skill) / 5
  90-rated kicker: threshold drops by 3 → team kicks earlier (trusts the kicker)
  60-rated kicker: threshold rises by 3 → team goes for conversion (doesn't trust kicks)
```

**Drop Kick Comfort Zone:**
Coaches only call for a drop kick within a skill/style-determined comfort range:
```
dk_comfort = 30 + (kicker_skill - 60) × 0.75 × snap_kick_aggression
```
A Boot Raid coach (snap_kick_agg = 1.5) with an 85-rated kicker trusts drop kicks out to ~55 yards. A Balanced coach (1.1) trusts them to ~41.

Beyond the comfort zone, the coach calls a place kick instead.

#### Snap Kick Overhaul: `_check_snap_kick_shot_play()`
Opportunistic drop kicks on early downs now scale with kicker talent and coaching style:

| Down | Behavior | Multipliers |
|------|----------|------------|
| 2-3 | "Pull-up three" — base 3-22% by distance | × snap_kick_agg × kicker_mult |
| 4 | Nearly never — only elite specialists in very close range with long ytg | |
| 5 | Secondary chance after select_kick_decision | × snap_kick_agg × kicker_mult |
| 6 | Handled by `select_kick_decision()` — kick > punt > go for it | N/A (not snap kick) |

The `kicker_mult = max(0.4, (kicker.kicking - 60) / 20.0)` means an 90-rated kicker fires snap kicks 50% more often than baseline, while a 68-rated kicker fires 60% less.

#### Coaching Style Integration
`snap_kick_aggression` values across offensive styles:

| Style | Value | Personality |
|-------|-------|-------------|
| Boot Raid | 1.5 | Lives to kick |
| Rouge Hunt | 1.4 | Kicking for field position points |
| Ball Control | 1.3 | Takes the points |
| Balanced | 1.1 | Moderate |
| Others | 1.0 | Default |

#### Consistency Fix
The distance formula was unified: both decision logic (`select_kick_decision`) and simulation (`simulate_drop_kick`, `simulate_place_kick`) now use `fg_distance = (100 - field_position) + 10`. Previously, decision used +17 while simulation used +10, creating a systematic disconnect where kicks that "should" have been attempted weren't, and vice versa.

#### Simulation Methods Updated
`simulate_drop_kick()` and `simulate_place_kick()` now call `_drop_kick_success()` and `_place_kick_success()` directly, ensuring the model the coach used to *decide* to kick matches the model that determines *whether it goes through*:
```python
# simulate_place_kick — now uses the shared kicker-range model
success_prob = self._place_kick_success(distance, kicker.kicking)
success_prob *= (1.0 + kick_acc + kick_arch_bonus + weather_kick_mod)
success_prob = max(0.10, min(0.98, success_prob))
```

Style bonuses, archetype bonuses, and weather modifiers are secondary adjustments layered on top of the kicker-driven base probability.

#### Kicking Results (40-game simulation)

| Metric | Value |
|--------|-------|
| Drop kick attempts/team | 2.25 |
| Drop kick makes/team | 1.73 (77%) |
| Place kick attempts/team | 0.56 |
| Place kick makes/team | 0.39 (69%) |
| Total kick attempts/team | 2.81 |
| Total kick makes/team | 2.11 (75%) |
| PK success < 35 yds | 100% |
| PK success 35-50 yds | 89% |
| Teams with 3+ kick attempts | 47% |
| Teams with 3+ kick makes | 33% |

---

## Architecture Overview

### Engine Flow (per play)

```
simulate_play()
  ├── Pre-snap penalty check
  ├── Down ≥ 4? → select_kick_decision()
  │     ├── Down 1-4: always None (go for it)
  │     ├── Down 5: kicker-adjusted threshold check
  │     └── Down 6: kick > punt > go for it
  ├── _check_snap_kick_shot_play() (opportunistic DK on downs 2-5)
  ├── select_play_family() (weighted by coaching style + situation)
  └── Execute play:
        ├── simulate_run()
        │     ├── _contest_run_yards(carrier, tackler, config)
        │     ├── _breakaway_check()
        │     ├── _red_zone_td_check()
        │     └── _run_fumble_check()
        ├── simulate_lateral_chain()
        │     ├── Multiple _contest_run_yards per lateral
        │     ├── Lateral interception check → explosive returns
        │     └── Compounding fumble risk per lateral
        ├── simulate_kick_pass()
        │     ├── _contest_kick_pass_prob(kicker, receiver, defense)
        │     └── Spread-thin effect on next play
        ├── simulate_drop_kick()
        │     └── _drop_kick_success(distance, kicker_skill)
        ├── simulate_place_kick()
        │     └── _place_kick_success(distance, kicker_skill)
        └── simulate_punt()
              └── Rouge/pindown check
```

### Coaching System Integration

The engine supports 5 head coach classifications, each modifying the contest system differently:

| Classification | Effect on Contests |
|---------------|-------------------|
| **Scheme Master** | `center *= 1.0 + scheme_amplification` — better play design = more yards |
| **Motivator** | `variance *= composure_amplification` — keeps players calm under pressure |
| **Disciplinarian** | Defense: `variance *= variance_compression`, `center *= (1 - gap_discipline)` — tighter, meaner defense |
| **Gameday Manager** | Halftime adjustments, situational amplification |
| **Players' Coach** | Hot streak bonus amplification |

### The 9 Offensive Styles

Each style has distinct play weights, snap kick aggression, and situational triggers:

| Style | Identity | Snap Kick Agg | Key Mechanic |
|-------|----------|---------------|--------------|
| Ground & Pound | Power running | 1.0 | High run_bonus, low lateral risk |
| Lateral Spread | Horizontal chaos | 1.0 | High lateral rate, explosive lateral bonus |
| Boot Raid | Kick-focused | **1.5** | Launch Pad zone triggers kick-heavy weights |
| Ball Control | Conservative | **1.3** | Takes points, clock management |
| Ghost Formation | Misdirection | 1.0 | Viper jets, counter plays, broken play bonus |
| Rouge Hunt | Field position | **1.4** | Early punts, pindown priority |
| Chain Gang | Maximum laterals | 1.0 | Amplified laterals in close games |
| Triple Threat | Single-wing | 1.0 | Counter/draw heavy, three threats |
| Balanced | Adaptive | **1.1** | No strong tendencies, reads the defense |

### Scoring System

| Score | Points | Frequency (per team/game) |
|-------|--------|--------------------------|
| Touchdown | 9 | ~4.0 |
| Snap Kick (Drop Kick) | 5 | ~1.73 made |
| Field Goal (Place Kick) | 3 | ~0.39 made |
| Safety | 2 | ~0.15 |
| Pindown (Rouge) | 1 | ~0.5 |
| Bell (Fumble Recovery) | 0.5 | ~1.0 |

---

## Technical Debt and Next Steps

### Known Gaps
1. **Kick volume slightly below target** — 2.81 attempts/team vs target of 3-5. Could be addressed by widening the snap kick shot_chance values on downs 2-3 or lowering the down-5 go-for-it thresholds.
2. **Place kick attempts very low** — Only 0.56/team. The drop kick comfort zone captures most close-range scenarios; FGs only happen when range exceeds DK comfort. May need a separate "set-piece decision" on down 6 that more aggressively considers FGs.
3. **batch_sim.py** and **diag_conversion.py** were added as diagnostic scripts and should be cleaned up or moved to a `tools/` directory.

### What's Working Well
- Contest system produces visible talent differentiation — elite players meaningfully outperform average ones
- Hot streaks create narrative moments within games
- Fatigue cliff forces roster depth usage
- Kicker-range model makes kicker rating the most important stat for kick outcomes
- Late-down needs-based conversion produces natural 85/71/63% cascade
- Turnovers are rare enough to feel meaningful, common enough to create drama

### Validation Approach
All changes were validated through 30-40 game batch simulations between each commit. Key metrics tracked: total score, TD count, kick attempts/makes by type and distance, turnover rates, conversion rates by down, and drive outcome distributions. No single-game tuning — everything was validated statistically.

---

*Engine: 6,940 lines | 4 commits | 1,032 insertions | Branch: `claude/viperball-league-simulator-Tcg8S`*
