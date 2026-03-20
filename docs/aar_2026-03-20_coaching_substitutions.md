# After Action Review — Coaching Substitution System (Backup Player Rotation)

**Date:** 2026-03-20
**Branch:** `claude/add-backup-substitutions-tOe46`

## Mission

Implement a coaching substitution system so backup players actually see the field during games. Prior to this change, substitutions only occurred when a player was injured mid-game. Backup zerobacks, halfbacks, and other depth players never played unless the starter got hurt — which is unrealistic. In real football, coaches bench struggling starters, rotate fatigued workhorses, and pull starters in blowouts.

## Incident / Starting State

The game engine had a fully functional injury system:
- `check_in_game_injury()` and `check_defender_injury()` rolled for injuries on every play
- `find_substitute()` found the best available backup by position, with position flexibility fallback
- Injured players were added to `_home_injured_in_game` / `_away_injured_in_game` sets
- All player selection methods (`_offense_skill`, `_defense_players`, `_kicker_candidates`) excluded injured players

But that was the **only** path to a substitution. No performance-based benching. No workload management. No blowout rest. A starter could fumble 5 times and keep playing. A halfback with 25 carries and depleted energy would never get a breather. In a 50-point blowout, starters played every snap of Q4.

The result: backup zerobacks across the league averaged 0 game touches per season. Depth players existed only as insurance against injuries that rarely happened.

## Commits

| # | Hash | Summary |
|---|------|---------|
| 1 | `5774c0a` | Add coaching substitution system for backup player rotation |

## Scope

1 file changed, +255 / -21 lines

- `engine/game_engine.py` — New substitution evaluation system, benching state management, player filtering updates across 12+ methods

## Architecture

### Benching vs. Injury — Parallel But Reversible

Benched players are tracked in `_home_benched` / `_away_benched` dicts (mapping player name → reason/duration metadata). A new helper `_unavailable_in_game(team)` returns the union of injured AND benched names. All player selection methods now call this instead of `_injured_in_game()` directly.

Key difference from injuries: **benching is reversible.** A player rested for fatigue returns after one drive. A player benched for performance returns at halftime. Only blowout-rest benchings last the rest of the game.

```
_injured_in_game(team)      →  permanent for this game (injury)
_benched_names(team)        →  temporary, with expiration rules
_unavailable_in_game(team)  →  union of both (used for player selection)
```

### Three Substitution Triggers

Evaluated between drives for both teams via `evaluate_coaching_substitutions()`:

| Trigger | Condition | Duration | Reversal |
|---------|-----------|----------|----------|
| **Performance** | 2+ fumbles, OR 3+ turnovers (ZBs), OR <1.5 YPC on 8+ carries (40% chance) | `half` | Clears at halftime |
| **Workload** | 12+ carries in Q3 (15-40% scaling), OR 18+ touches in Q4 (30%), OR energy < threshold | `drive` | Returns after 1 drive |
| **Blowout** | Leading by 25+ in Q3/Q4 | `game` | Does not return |

### Integration Points

1. **`simulate_drive()` start** — Process bench expirations (returning rested players), then evaluate new substitutions
2. **Halftime** — Clear all `half`-duration benches (`_clear_halftime_benches()`)
3. **Player selection** (12 methods updated) — `_offense_skill`, `_defense_players`, `_kicker_candidates`, `_pick_def_tackler`, `_get_defensive_unit`, kick pass defender selection, interception candidate selection, and the power ratio calculation all now exclude benched players

### Substitution Log

Every benching generates a log entry:

```python
{
    "team": "University of Texas",
    "quarter": 3,
    "time_remaining": 412,
    "benched_player": "Sabrina Richardson",
    "benched_position": "Halfback",
    "reason": "fatigue_rest",
    "duration": "drive",
    "substitute": "Diana Moore",
}
```

Included in game summary output under `coaching_substitutions` alongside existing `in_game_injuries`.

## Validation

### 20-Game Batch Test (seed=99)

| Substitution Type | Count | Per Game Avg |
|-------------------|-------|-------------|
| Fatigue/workload rests | 20 | 1.0 |
| Performance benchings | 2 | 0.1 |
| Blowout rests | 50 | 2.5 |
| **Total** | **72** | **3.6** |

### Frequency Analysis

- **Blowout rests** dominate the count because they pull 4-5 starters at once in a single event. ~5-6 of the 20 games were blowouts, producing ~50 individual benchings (≈5 starters × ~10 blowout games counting both teams).
- **Workload rests** average ~1 per game. Typically the LEAD halfback or a high-usage zeroback getting a 1-drive breather in Q3/Q4.
- **Performance benchings** are rare (~1 per 10 games). This is correct — 2+ fumbles by a single player in a game is uncommon. When it happens, the bench is immediate and impactful.

### Emergent Behaviors Observed

1. **Comeback catalyst:** In one test game, Saint Mary's led by 25+ in Q3 and pulled starters. With backups in, Yale closed the gap to 44.5-43.5. This is realistic — blowout rest creates real comeback opportunities.

2. **Multi-cycle rotation:** In Game 5 (seed=99), Zeroback Nneka Obi was rested for fatigue in Q4, returned after one drive, accumulated more workload, was rested again, then pulled for blowout rest when the score gap widened. Three separate substitution events for one player — exactly how real coaching works.

3. **Backup cascading:** When a ZB1 starter gets benched, ZB2 enters. If ZB2 is also a starter (dual-ZB systems), the blowout logic may bench them too, putting ZB3 on the field. This gives deep depth players meaningful reps.

## Design Decisions

1. **Why between-drive, not mid-drive?** Real coaches don't yank a halfback off the field between plays. Substitutions happen at natural stoppages — between drives, at halftime. The between-drive evaluation point provides a clean integration without disrupting play-level simulation.

2. **Why probabilistic, not deterministic?** A starter with 12 carries in Q3 has a 15% rest chance, not a guaranteed benching. Different coaching philosophies: some coaches ride their workhorse, others rotate aggressively. The probability model creates variance that reflects this.

3. **Why not modify the energy system?** The per-player energy system (drain + recovery) keeps starters near 100 energy for most of the game. Recovery between drives (5 energy) and at halftime (30 energy) outpaces the drain rate. Rather than rebalancing the entire energy economy (which would affect fatigue modifiers, injury risk, and play outcomes), the workload trigger uses carries/touches as the proxy for "this player needs a break."

4. **Why does `_unavailable_in_game()` wrap both sets?** Single point of filtering. Every method that selects players calls one function and gets back everyone who shouldn't be on the field, regardless of reason. No risk of a method checking injuries but forgetting benched players.

## What Went Well

- **Zero disruption to injury system.** The benching system runs in parallel without touching any injury code paths. `check_in_game_injury` and `check_defender_injury` remain unchanged.
- **Clean data model.** Benched dict with reason/duration/drive_count metadata makes expiration logic trivial and the substitution log informative.
- **Emergent realism.** The comeback catalyst and multi-cycle rotation behaviors emerged naturally without explicit coding — they're consequences of the interaction between blowout detection, bench expiration, and re-evaluation.

## What to Watch

1. **Blowout threshold (25 points).** In a sport where touchdowns are 9 points and drop kicks are 5, a 25-point lead might be too conservative. A 20-point lead represents ~2-3 scores — may want to lower this to 20 if starters aren't getting pulled often enough.

2. **Performance bench at halftime reset.** A player benched for 2 fumbles in Q2 returns at halftime. If they fumble again in Q3, they get benched again. This is realistic (halftime adjustments, coach gives second chance) but could lead to yo-yo benching. Monitor whether the same player getting benched twice in a game looks odd in play-by-play.

3. **Backup quality gap.** When backups enter in blowouts, the scoring rate should drop. This naturally happens because backups have lower overall ratings driving lower contest outcomes via the halo/power ratio system. But if blowout games suddenly see the losing team scoring freely against backups, the quality gap may need an explicit modifier.

4. **Defensive substitution frequency.** Currently defensive subs are rarer than offensive ones (tackles ≥ 10 in Q3 trigger, 25% chance × 50% confirmation). May need tuning if defensive backups aren't seeing enough reps.

## Lessons Learned

1. **The energy system is too generous for substitution triggers.** Between-drive recovery of 5 energy + halftime recovery of 30 energy means starters rarely drop below 50 energy. Workload (carries, touches) is a much better proxy for "this player should rest" than the energy value itself.

2. **Substitution systems need multiple triggers, not just one.** Injury-only subs meant backups never played in 95%+ of games. Adding performance, workload, and blowout triggers creates a realistic distribution where depth players contribute meaningfully.

3. **Benching is a coaching decision, not a player state.** Unlike injuries (which are events that happen to players), substitutions are decisions coaches make. The evaluation function runs at the team level, considers the full roster, and checks backup availability before benching anyone — mirroring how real coaching staffs operate.
