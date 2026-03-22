# AAR: Clock Management Overhaul (V2.8)

**Date:** 2026-03-22
**Feature:** Play clock enforcement, timeout decision engine, victory formation rewrite, clock-run mode
**Files Changed:** `engine/game_engine.py`, `engine/coaching.py`

---

## Problem Statement

The engine had per-play time consumption mechanics (15-42 seconds based on tempo), timeouts (3 per half), and a victory formation — but they didn't interact. Three specific failures:

1. **No enforceable play clock.** The engine deducted time per play but never penalized a team for taking too long. The existing delay-of-game penalty was a random 0.5% dice roll with no mechanical basis. A team could stack clock-burn multipliers to 45-second play clocks without consequence.

2. **Victory formation ignored defensive timeouts.** A leading team would kneel, burn 37 seconds, then immediately kneel again. The trailing team never called timeouts to stop the clock and force real plays. The screenshot that triggered this work showed a team kneeling at 0:45, then 0:05, then 0:00 — three kneels in rapid succession with no defensive response.

3. **No clock-run mode.** When leading in Q4 but too early to kneel, teams ran their normal offensive playbook. A 10-point lead with 4 minutes left should produce run-heavy, clock-burning play selection. Instead, teams kept throwing kick passes and risking turnovers.

4. **Timeout decisions were primitive.** Two triggers: fatigued stars (40%) and trailing offense late (60%). No defensive clock-stop strategy, no conservation logic, no coach differentiation. The `timeout_hoarder` and `timeout_sprinter` traits existed in `coaching.py` but had empty effect dicts and were never wired in.

The hockey power-play analogy from the feature request captured it well: the leading team should be "on the power play of time" — methodically grinding out the advantage while the defense scrambles to stop the clock and force turnovers.

## Solution

### 1. Coach `clock_management` Attribute

**File:** `engine/coaching.py` — `compute_gameday_modifiers()`

A new derived composite skill (0.0-1.0) that gates every clock decision in the engine:

```
clock_management = norm(
    instincts * 0.40 +    # game sense — reading situations
    composure * 0.35 +    # poise — not panicking with the clock
    leadership * 0.25     # organizational discipline
)
```

Sub-archetype bonuses:
- `clock_surgeon`: +0.15 (Gameday Manager specialization)
- `economist`: +0.05

This was designed as a derived attribute rather than a new slider to avoid expanding the coach creation surface. A high-instincts, high-composure, disciplined coach naturally manages the clock well. An impulsive, low-composure coach doesn't.

### 2. Play Clock Enforcement

**File:** `engine/game_engine.py` — drive loop, after `base_time` computation

Added `play_clock_limit: 40` to `V2_ENGINE_CONFIG`.

After all tempo modifiers are applied (style, lead management, 3-minute warning, clock burn), the engine checks whether the final play time exceeds 40 seconds. If it does:

1. The coach gets an avoidance roll: `avoidance_chance = 0.55 + 0.40 * clock_management`
2. If avoided: `base_time` clamped to 40 (snapped just in time)
3. If failed: delay-of-game penalty — 5 yards, replay the down, 40 seconds still burned

The old random 0.5% delay-of-game in `PENALTY_CATALOG` was zeroed out (`prob: 0.0`). Delay of game is now purely mechanical: it only happens when the computed play clock actually exceeds the limit, which requires stacking slow tempo + clock burn multipliers + bad variance. This makes it rare (~0-1 per 100 games) but meaningful — exactly like real football.

### 3. Victory Formation Rewrite

**File:** `engine/game_engine.py` — `_should_kneel()`

Old logic was a simple threshold: Q4, <=90s with lead > 5, or <=45s with any lead. No awareness of defensive timeouts or remaining downs.

New logic calculates:
- **Kneels needed:** `ceil(time_remaining / 37)` (each kneel burns 35-40s, avg 37)
- **Downs available:** `7 - current_down` (6-down system, turnover on 7th)
- **Can kneel out:** `kneels_needed <= downs_available`
- **Safe lead margin:** Varies by time remaining:
  - `> 90s`: requires lead > 9 (double-digit)
  - `45-90s`: requires lead > 5
  - `<= 45s`: any lead

This prevents the degenerate case of kneeling with 2+ minutes left on a 3-point lead. It also means the offense won't kneel if it would take more downs than available — they'll run real plays instead.

### 4. Defensive Timeouts on Kneels

**File:** `engine/game_engine.py` — `_call_defensive_timeout_on_kneel()` and kneel handling in drive loop

After each kneel, the trailing defense gets a chance to call timeout:

```
call_prob = 0.70 + 0.25 * clock_management    # 70-95%
```

Modified by traits:
- `timeout_hoarder`: 0.80x (reluctant even in obvious spots)
- `timeout_sprinter`: 1.10x (eager)

The kneel still burns its 35-40 seconds (time already consumed), but the timeout stops the clock and gives the defense 15 energy recovery. If the defense burns all their timeouts and the offense can still kneel it out, the kneels proceed. If not, `_should_kneel()` returns False on subsequent plays and the offense runs real plays.

Verified behavior: in a seed-31 game, Portland (trailing 27-37) called 1 timeout on 2 kneels. Their second timeout roll failed (random). Lake Forest still kneeled it out because 42 seconds with 6 downs available was enough.

### 5. Clock-Run Mode

**File:** `engine/game_engine.py` — `select_play_family()`, after lead management modifier application

When leading in Q4 with `time_remaining > 60` and not in garbage time:

```
cr_intensity = 0.30 + 0.70 * clock_management    # 0.30 to 1.0

Run plays (dive, power, sweep, counter, draw): * (1.0 + 0.60 * cr_intensity)
Kick pass:      * max(0.25, 1.0 - 0.50 * cr_intensity)
Lateral spread: * max(0.20, 1.0 - 0.40 * cr_intensity)
Trick play:     * max(0.15, 1.0 - 0.60 * cr_intensity)
```

This stacks on top of existing lead management (Vault tendency already boosts runs when leading). Punt, snap kick, and field goal weights are untouched — punting for field position and taking safe points are fine.

**Measured impact (30-game sample):**

| Situation | Runs | Kick Pass | Laterals |
|---|---|---|---|
| Q4 Leading | 67% | 23% | 5% |
| Q4 Trailing | 32% | 50% | 9% |
| Q1-Q3 (baseline) | 45% | 36% | 7% |

The 22-point swing between leading (67% runs) and trailing (32% runs) is exactly the behavior the user requested.

### 6. Timeout Decision Engine (5 Categories)

**File:** `engine/game_engine.py` — `call_timeout()` (full rewrite)

Replaced the old 2-trigger system with 5 situational categories, each with coach-skill gating and trait modifiers:

| Category | Trigger | Base Prob | Coach Gate |
|---|---|---|---|
| **Strategic clock stop** (defense) | Q4 trailing by <=14, <5min | 0.20 + urgency ramp | * (0.60 + 0.40 * clock_mgmt) |
| **Star fatigue rest** (offense) | Red zone, star energy <50 | 0.15-0.30 | Inverse: bad managers waste TOs here |
| **Injury timeout** (official) | Any play, any quarter | 0.3% flat | Not coach-gated (official call) |
| **Personnel/scheme** (offense) | Q1-Q3, drive stalled, 2+ TOs | 0.05-0.08 | Bad managers more likely |
| **Offensive clock stop** (offense) | Q2/Q4 trailing, <120s | 0.18-0.53 | * (0.50 + 0.50 * clock_mgmt) |

**Conservation logic:**
- Good clock managers resist spending timeouts on fatigue/personnel issues
- Q4 fatigue timeouts suppressed by 70% for coaches with `clock_management > 0.6`
- Personnel timeouts only available with 2+ TOs and Q1-Q3 (preserve for Q4)

**Trait wiring:**
- `timeout_hoarder`: -30% on all non-Q4 timeouts (saves but may miss opportunities)
- `timeout_sprinter`: +25% on early-game timeouts (aggressive but may not have them late)

**Injury timeout:** 0.3% per play, official-called, not charged to either team. Both teams recover 10 energy. Adds narrative realism without strategic impact.

## Design Decisions

### Why not clock stops on incompletions?

The user chose "keep clock always running" — clock only stops for timeouts, scores, penalties, and the 3-minute warning. This keeps the model simpler and avoids creating an outsized advantage for kick-pass-heavy trailing teams (which are already boosted by chase mode tempo overrides).

### Why derive clock_management instead of adding a new slider?

Three reasons:
1. Keeps the coach creation surface at 6 core attributes + personality sliders
2. Clock management is genuinely a composite skill — it requires game sense (instincts), poise (composure), and organizational discipline (leadership)
3. Existing sub-archetypes (`clock_surgeon`, `economist`) provide differentiation within the derived scale

### Why is delay of game so rare?

By design. In real football, delay of game happens maybe once every 3-4 games. In Viperball, the play clock formula clamps `base_time` to 15-42 seconds normally. Only when clock-burn multipliers push it past 42 AND the ±3 second variance lands high does it exceed 40. Then the coach still has a 55-95% avoidance chance. The result: mechanically-driven delays that only happen when the system legitimately produces a slow play, not random dice rolls.

### Why not let the defense call timeouts in Q1-Q3?

Defensive timeouts are limited to Q4 (and Q2 <60s for halftime situations) because:
1. Stopping the clock in Q1/Q3 has near-zero strategic value — there's too much time remaining
2. Real coaches almost never call defensive timeouts before the 4th quarter
3. It prevents the AI from wasting timeouts early, which is a common complaint about real coaches

### Comeback rarity target

The user specified comebacks via timeout clock management should happen in ~1-2% of games. The system achieves this through:
- Defensive timeouts only fire in Q4 with high urgency
- Good clock managers on the leading team still burn clock effectively even when forced to run plays
- Clock-run mode makes turnovers less likely (67% runs vs 36% kick pass baseline)
- The combination of needing a turnover + scoring + time management makes timeout-driven comebacks naturally rare

## Verification

**30-game batch simulation:**
- 28/30 games had kneels (93%) — most games have a clear winner by Q4
- Average 3.0 timeouts used per game (of 6 available per half)
- 0 delay-of-game penalties (expected — very rare)
- 7/30 games were close (within 9 points)
- Clock-run mode produced 67% run rate for Q4 leaders vs 45% baseline

**10-game batch_sim.py run:** All games completed without errors, play distribution within expected ranges.

## Files Modified

| File | Changes |
|---|---|
| `engine/coaching.py` | +17 lines: `clock_management` derived attribute computation with sub-archetype bonuses |
| `engine/game_engine.py` | +292/-48 lines: play clock enforcement, victory formation rewrite, `_call_defensive_timeout_on_kneel()`, clock-run mode in `select_play_family()`, timeout engine rewrite with 5 categories |

## Integration Points

- **Lead management (V2.7):** Clock-run mode stacks on top of existing Vault/Thermostat tendencies. A Vault coach leading in Q4 gets both the Vault run boost AND the clock-run mode boost.
- **Chase mode:** Trailing teams in chase mode still get tempo overrides that compress play clock, working against the leading team's clock burn.
- **3-minute warning:** Clock-run mode interacts with the 3-minute warning's trailing-team compression and leading-team burn multipliers.
- **Bonus possession:** The V2.8 turnover-cancels-bonus fix (previous commit) interacts with clock-run mode — if a leading team fumbles while grinding clock, the bonus possession system correctly waives any pending bonus.
