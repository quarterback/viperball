# After Action Report: Viperball Engine V2 + 4th Down Movement Workstream

**Branch:** `claude/validate-mechanics-spec-7tkGQ`
**Date:** 2026-02-22
**Duration:** ~12 hours (2026-02-21 14:35 UTC → 2026-02-22 02:18 UTC)

---

## 1. Mission Statement

Rebuild the viperball simulation engine to V2 architecture (10-phase spec), then design and implement a 4th down "movement" mechanic inspired by Finnish baseball (pesäpallo) to solve the sport's fundamental drive structure problem: drives had no narrative arc, 4th down conversion was 26.7%, and most possessions stalled into aimless kicks.

---

## 2. What Was Planned

### V2 Engine Architecture (10 phases)
1. Power Ratio Contest Model (replace sigmoid with multiplicative formula)
2. Halo Model (prestige-to-engine team-level baseline)
3. Fatigue Tiers (Elite/Standard/Low drain classification)
4. R/E/C Variance Archetypes (Reliable/Explosive/Clutch)
5. Star Override (pregame designation with performance floor)
6. Hero Ball + Defensive Keying (force-feed stars, counter-strategy)
7. Composure System (dynamic 60-140 range, tilt/surge mechanics)
8. Prestige Decision Matrix (prestige-driven aggression)
9. Prestige Decay (per-game asymmetric adjustments)
10. Narrative Generation (YAR metrics, headlines, composure timeline)

### 4th Down Movement Mechanic + Pesäpallo Rule
- Restructure drives into three phases: advancement (1-3), decision (4), specialist (5-6)
- 4th down becomes a coaching decision point: go for advancement or enter kick mode
- Pesäpallo rule: missed snap kicks retain possession (dead ball at LOS, advance down)
- Per-style `kick_mode_aggression` tuning across all 9 offense styles

### Supporting Work
- Decompose TERRITORY_KICK into explicit SNAP_KICK/FIELD_GOAL/PUNT play families
- Power play (man-advantage) scaffolding to replace penalty yardage
- Late-down conversion urgency tuning
- Batch simulation validation

---

## 3. What Was Delivered

| Deliverable | Status | Commit |
|---|---|---|
| V2 10-phase engine rebuild | Shipped | `e480068` |
| Late-down play_shift fix + archetype clamp | Shipped | `9854308` |
| Late-down conversion urgency tuning | Shipped | `facc660` |
| Play family decomposition (SNAP_KICK/FG/PUNT) | Shipped | `ae56846` |
| Power play scaffolding | Scaffolded (not wired) | `ae56846` |
| 10-minute quarters + 3-minute warning | Shipped | `ae56846` |
| 9-style offense weight rebalancing | Shipped | `ae56846` |
| 4th down movement mechanic | Shipped | `865e87e` |
| Pesäpallo possession retention | Shipped | `865e87e` |
| `kick_mode` state + `_fourth_down_decision()` | Shipped | `865e87e` |
| `MISSED_SNAP_KICK_RETAINED` result type | Shipped | `865e87e` |
| Per-style `kick_mode_aggression` (9 styles) | Shipped | `865e87e` |
| Shot interrupt restriction (downs 2-3 only) | Shipped | `865e87e` |

**6 commits, 2 files changed, ~740 insertions / ~430 deletions net.**

---

## 4. What Worked

### The pesäpallo rule is elegant and solves multiple problems at once
Borrowing from Finnish baseball — where a failed conversion doesn't lose possession — eliminated the biggest drain on drive quality. Snap kicks went from risky interrupts to zero-turnover scoring attempts. Turnovers on downs dropped from a persistent problem to 0.4% of drives. This single rule change made the entire 4th-6th down structure viable.

### Structuring the drive into three phases created narrative
Before: all 6 downs felt the same. Drives meandered. Now there's a clear arc — build yardage on 1-3, make a decisive commitment on 4th, and if you enter kick mode, your specialist gets two clean shots on 5-6. The `kick_mode` flag tracks this state cleanly.

### Per-style `kick_mode_aggression` creates genuine strategic diversity
Boot Raid (0.80) enters kick mode aggressively — it's their identity. Ground & Pound (0.25) almost never does — they want the TD. This means the same field position and down/distance produces different decisions depending on the coaching philosophy, which is exactly what makes the sport interesting.

### The V2 architecture was aggressive but landed
Implementing all 10 V2 phases in a single commit (`e480068`) was bold. The feature flag system (`V2_ENGINE_CONFIG`) made it manageable — each system can be toggled independently. A/B testing showed tighter margins (10.4 vs 13.7 avg) and fewer blowouts (4 vs 8 out of 30 games), indicating the composure and prestige systems are creating more competitive games.

---

## 5. What Didn't Work / Problems Encountered

### TDs per team still below target
Post-implementation batch sim shows 1.9 TDs/team (target 6-8). The pesäpallo rule and 4th down mechanic improved drive structure but didn't solve the underlying touchdown conversion problem. Drives reach scoring position but convert to kicks (5 pts) rather than TDs (9 pts). The scoring gravity zones and red zone mechanics need further tuning — this is the next workstream.

### Total scoring below target
45.1 points/team average vs. 65-85 target. Related to the TD shortage — teams are scoring via kicks (3.1 snap kicks made + 3.0 FGs per team) rather than touchdowns. The variety is there but the volume isn't.

### Power play system not wired
The scaffolding exists (`_start_power_play()`, `get_power_play_bonus()`, `_tick_power_play()`) but the bonus multiplier isn't actually applied during play simulation. This was deprioritized in favor of the 4th down mechanic — correct call — but it's dangling.

### Merge conflict with parallel implementation
While this workstream was in progress, a separate session (`session_019gKQzAiwm4m4WViyKBLSBT`) shipped its own version of the Finnish baseball rule to `origin/main` (commit `5fa1efb`). That version is simpler — retained possession on downs 4-5 for both snap kicks and field goals, without the kick mode decision tree or per-style aggression. This created merge conflicts on the PR. Resolution: accept the incoming (our branch) changes, as the implementation is more complete and matches the original design intent.

### `gh` CLI not available in environment
Couldn't create the PR programmatically. Minor friction.

---

## 6. Key Metrics (10-game batch sim, post-implementation)

| Metric | Result | Target | Assessment |
|---|---|---|---|
| Plays/game | 145 | 140-220 | On target |
| Avg score/team | 45.1 | 65-85 | Below target |
| TDs/team | 1.9 | 6-8 | Below target |
| Snap kicks made/team | 3.1 | 2-4 | On target |
| FGs made/team | 3.0 | 1-3 | On target |
| Turnovers on downs/team | 0.1 | 2-3 | Low (by design) |
| Snap kicks called/team | 5.5 | — | Healthy |
| Kick pass completion % | 55.5% | — | Reasonable |
| 4th down conversion | 30.0% | ~85% | Below target |

**Drive outcomes:**
- `successful_kick`: 44.6% (dominant scoring method)
- `touchdown`: 13.4%
- `punt`: 13.4%
- `missed_snap_kick_retained`: 0.7% (pesäpallo rule active)
- `turnover_on_downs`: 0.4% (nearly eliminated)

---

## 7. Decisions Made

1. **Pesäpallo rule scoped to snap kicks only** — Place kicks (3 pts) can still be blocked, deflected, and recovered by the defense. Only snap kicks (5 pts) get the retention treatment. This preserves risk for the lower-value kick while making the signature scoring play safe to attempt.

2. **4th down decision is probabilistic, not deterministic** — The coaching AI calculates a probability of entering kick mode based on 6 factors (field position, ytg, kicker skill, score differential, quarter, team style). This creates variance between games even with the same matchup.

3. **Power play deprioritized** — The man-advantage system is a separate design thread. The scaffolding is in place but wiring it in was correctly deferred to avoid scope creep during the 4th down implementation.

4. **All 10 V2 phases shipped together** — Risky but enabled by feature flags. The alternative (phase-by-phase with validation between each) would have taken significantly longer. The tradeoff was accepted because the spec was well-defined and the systems are mostly independent.

5. **Shot interrupts restricted to downs 2-3** — Previously, snap kick interrupts fired on downs 2-5, randomly derailing drives. Now they're confined to early downs as "pull-up threes" while 4-6 are handled by the movement system. This was necessary to prevent the old interrupt system from conflicting with kick mode.

---

## 8. What's Next

### Immediate (next session)
- **Resolve merge conflict** — Accept incoming changes on the PR, verify batch sim post-merge
- **TD conversion tuning** — Red zone mechanics, scoring gravity zones, and run play yardage need work to push TDs from 1.9 toward 4-6 per team
- **Wire power play bonus** — Apply `get_power_play_bonus()` multiplier in `simulate_run()`, `simulate_lateral_chain()`, `simulate_kick_pass()`

### Short-term
- **Tune `kick_mode_aggression` values** — Current values are initial estimates; need 100+ game sample to calibrate
- **4th down conversion rate** — 30% is too low for advancement attempts; the late-down urgency multipliers may need further tuning for the new 4th-down-as-decision context
- **Yards per team** — 421 vs. 600-750 target; run play yardage generation is the bottleneck

### Medium-term
- **Validate V2 systems individually** — Composure, hero ball, prestige decay all shipped but haven't been isolated and tested
- **Narrative generation rendering** — YAR metrics and headline generator are in the engine but likely not surfaced in the UI
- **Power play full implementation** — Move from scaffolding to active mechanic

---

## 9. Lessons Learned

**The best rule changes solve multiple problems simultaneously.** The pesäpallo rule wasn't just "keep the ball on a miss" — it eliminated turnover-on-downs as a drive killer, gave snap kicks a natural home in the drive structure, made the kicker a position of genuine strategic value, and created a two-shot mechanic on 5th/6th that produces natural drama. One rule, five outcomes.

**Drive structure matters more than play-level tuning.** We spent significant effort on late-down urgency multipliers (facc660) and they helped marginally. The 4th down restructure was a qualitative change to the flow of the game — it changed what drives *mean*, not just how individual plays resolve. The structural change was worth more than all the scalar tuning combined.

**Parallel workstreams on the same file create conflicts.** The duplicate Finnish baseball implementation on main (5fa1efb) happened because the design conversation wasn't captured in a shared artifact before implementation began. If the design doc had been committed first, the parallel session would have seen it and built on it rather than reimplementing.
