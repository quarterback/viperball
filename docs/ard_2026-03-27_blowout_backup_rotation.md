# Architecture Decision Record: Graduated Blowout Backup Rotation

**Date:** 2026-03-27
**Status:** Implemented
**Branch:** `claude/backup-rotation-blowout-Bk2IG`

---

## Context

The coaching substitution system (2026-03-20) introduced blowout rest as a single trigger: bench all skill-position starters when leading by 25+ points in Q3 or later. While functional, this created two problems observed across seasons:

1. **Starters played full games in 20-24 point leads.** A team up 22 in the 3rd quarter would run its full starting lineup through the end of the game. This inflated individual stat lines, padded scoring totals, and looked unrealistic — no real coaching staff leaves starters in a game that's been decided.

2. **Backups accumulated near-zero stats.** Without meaningful game reps, backup players had no opportunity to build stat profiles. In dynasty mode, this matters: a backup Halfback who never touches the ball has no case for portal interest or development. The roster's depth chart existed on paper only.

3. **Blowout final scores were too high.** With starters running aggressive play-calls (kick passes, laterals, trick plays) deep into decided games, final scores ballooned. The engine had no mechanism to shift to conservative, clock-chewing football when the game was over in all but name.

## Decision

Replace the single-threshold blowout trigger with a **graduated three-tier system** that begins earlier, escalates with the lead, and pairs substitution decisions with conservative play-calling.

### Why graduated tiers instead of a lower flat threshold?

A flat threshold (e.g., lower from 25 to 18) would be too aggressive in many situations. An 18-point lead early in Q3 can evaporate — pulling all starters at that point risks giving the game away. Graduated tiers let coaches respond proportionally: mix in backups at moderate leads, commit to a full bench only when the lead is commanding, and go to the deep bench in true blowouts.

### Why couple play-calling changes with substitutions?

Substitutions alone don't solve the scoring problem. Even with backups in the game, if the play-caller is still dialing up kick passes and trick plays, the offense generates unnecessary scoring opportunities and turnover risk. Conservative play-calling (run-heavy, clock-chewing) is a separate coaching decision that real staffs make independently of who's on the field.

---

## Design

### Tier System

The `_blowout_tier(score_diff)` method returns 0-3 based on lead size, quarter, and time remaining:

| Tier | Name | Trigger | Substitution Action | Play-Calling Shift |
|------|------|---------|--------------------|--------------------|
| 0 | Normal | < 20 pts, or Q1/early Q2 | None | None |
| 1 | Soft Rotation | 20+ pts Q3+, or 25+ pts late Q2 | Rotate 1-2 highest-usage starters out per drive (60% chance each, "drive" duration) | Blowout clock-chew active |
| 2 | Pull Starters | 25+ pts Q3+, or 30+ late Q2, or 20+ pts under 5:00 Q4 | All skill-position starters benched for game | Blowout clock-chew active |
| 3 | Deep Bench | 35+ pts Q3+ | Skill + defensive starters benched for game | Blowout clock-chew active |

**Late Q2 triggers** (with ≤5:00 remaining) let the system act before halftime in runaway first halves. The thresholds are 5 points higher than Q3+ equivalents to account for the half remaining.

**Q4 under-5-minute rule** at tier 2 (20+ pts): There is no competitive reason for starters to be on the field with a 20-point lead and less than 5 minutes in the game. This catches situations where the lead hovered at 20-24 through Q3 — not enough for tier 2 in Q3 — but the game is clearly over by late Q4.

### Soft Rotation Logic (Tier 1)

Tier 1 doesn't pull all starters — it rotates the highest-usage players out for one drive at a time:

1. Filter to skill-position starters (Viper, Zeroback, Halfback, Wingback, Slotback) not already benched/injured
2. Sort by `game_touches` descending — rest the workhorses first
3. For each, 60% chance of being rested for one drive (cap: 2 per evaluation)
4. After tier 1, continue to performance and fatigue checks (tier 1 is additive, not exclusive)

This creates a natural rotation pattern: different starters sit different drives, backups cycle in and accumulate touches, and the starting lineup is never fully absent — just thinned.

### Conservative Play-Calling (Blowout Clock-Chew)

When `_is_blowout()` is true and the team is leading, `select_play_family()` applies aggressive weight shifts:

| Play Family | Weight Multiplier | Rationale |
|-------------|------------------|-----------|
| dive_option, power, counter, draw | 2.0x | Clock-killing ground game |
| sweep_option | 1.4x | Moderate — still a run but has more exposure |
| speed_option | 1.2x | Moderate |
| kick_pass | 0.20x | Heavily suppressed — turnover risk, stops clock |
| lateral_spread | 0.10x | Near-zero — high fumble/INT risk |
| trick_play | 0.05x | Essentially eliminated |
| viper_jet | 0.30x | Suppressed — flashy, unnecessary |
| snap_kick, field_goal | 1.3x | Slightly boosted — safe points |

This stacks on top of existing Q4 clock-run mode (which was previously gated behind `not _is_blowout()` and now applies universally when leading in Q4).

### Tempo: Play Clock Milking

Separately from play selection, the leading team in a blowout now runs the play clock to near-expiration on every play:

- `base_time` floored at 36 seconds (vs. normal 18-38 depending on tempo style)
- Capped at 42 seconds to stay under the play clock limit and avoid delay-of-game penalties
- Stacks with existing 3-minute-warning clock burn logic
- Effectively neutralizes tempo-style teams' speed advantage in garbage time

### `_is_blowout()` Expansion

The boolean helper (used by touch distribution flattening in `_spread_the_love_offense` and `_spread_the_love_defense`) was expanded to cover late Q2:

| Before | After |
|--------|-------|
| 20+ pts, Q3/Q4 only | 20+ pts Q3/Q4, **or** 25+ pts Q2 with ≤5:00 left |

This means backup-friendly touch distribution also kicks in earlier.

---

## Validation

### 20-Game Mismatch Test (Alabama vs Alabama State, seeds 100-119)

| Metric | Value |
|--------|-------|
| Avg home score (Alabama) | 102.5 |
| Avg away score (Alabama State) | 55.5 |
| Avg margin | 47.1 |
| Avg blowout rotation subs (tier 1) | 1.7 per game |
| Avg blowout rest subs (tier 2/3) | 6.9 per game |
| Games reaching tier 1 (soft rotation) | 9 / 20 (45%) |
| Games reaching tier 2 (pull starters) | 20 / 20 (100%) |
| Games reaching tier 3 (deep bench) | 14 / 20 (70%) |
| Games with Q2 blowout trigger | 13 / 20 (65%) |

All 20 mismatch games triggered at least tier 2. 70% hit tier 3 (35+ point lead), which is expected — Alabama vs Alabama State is a massive talent gap. Q2 triggers fired in 65% of games, meaning backups often entered before halftime in these blowouts.

### 20-Game Even Matchup Test (Alabama vs Auburn, seeds 200-219)

| Final Margin | Games | Blowout Subs Triggered |
|-------------|-------|----------------------|
| < 10 pts | 5 / 20 | 2 of 5 (mid-game lead swings) |
| 10-20 pts | 4 / 20 | 4 of 4 |
| 20-35 pts | 5 / 20 | 5 of 5 |
| 35+ pts | 6 / 20 | 6 of 6 |
| **Total** | **20** | **17 / 20 (85%)** |

Even between evenly matched teams, Viperball's high-scoring nature means 20+ point leads in Q3 happen regularly. In the 2 close games where blowout subs still fired (seeds 200, 204), one team built a large mid-game lead that later evaporated — the backup rotation itself may have contributed to the comeback, which is a realistic and desirable emergent behavior.

The 3 games with zero blowout triggers (seeds 202, 214, 217) were wire-to-wire close contests with final margins under 7 points.

---

## Consequences

### Positive

- **Backups accumulate meaningful stats.** Tier 1 rotation gives backups 1-2 drives per blowout in a simplified offensive scheme. Tier 2/3 gives them extended run as the primary unit. Over a season, this produces real stat lines that feed into portal calculations, award consideration, and development tracking.

- **Final scores come down in mismatches.** Conservative play-calling + clock milking + fewer possessions = fewer points for both teams. The leading team scores less because they're running dives and burning clock. The trailing team scores less because they get fewer drives.

- **Comeback potential increases.** When a team pulls starters in Q3 with a 25-point lead, the backups are measurably worse (lower overall ratings drive lower power ratios). The trailing team's starters can close the gap. This creates organic drama without scripting it.

- **Starters stay healthy.** Fewer snaps in decided games means less exposure to the injury system. Over a dynasty season, this marginal reduction in wear compounds.

### Negative / Risks

- **Viperball scores are inherently high.** Even with suppressed play-calling, a team's backups running dives in a 35-point blowout will still score occasionally. The system dampens scoring but doesn't eliminate it. Final scores in mismatches will still look large by football standards.

- **Tier 1 rotation is probabilistic.** The 60% trigger chance and 2-per-drive cap mean tier 1 behavior varies game-to-game. Some games will see aggressive rotation, others almost none, even at the same score differential. This is intentional (coaching variance) but could look inconsistent in small samples.

- **Clock-chew stacks aggressively.** The blowout clock-chew multipliers stack on top of existing lead management modifiers, INT awareness suppression, and Q4 clock-run mode. In theory, a run play's weight could be boosted 4-5x through cascading multipliers while kick pass weight is suppressed to near-zero. This is correct behavior for a blowout, but worth monitoring for games where the lead narrows and the play-caller should open back up.

---

## Alternatives Considered

### Lower flat threshold (20 instead of 25)

Would catch more games but is too aggressive for Q3 20-point leads in a 9-point-TD sport. A 20-point lead is ~2.5 touchdowns — well within comeback range. The tiered approach handles this better: start mixing backups at 20 (tier 1) but don't pull everyone until 25 (tier 2).

### Time-of-possession based trigger

Instead of score differential, trigger on TOP ratio (e.g., if one team has 70%+ possession). Rejected because TOP correlates weakly with game outcome in Viperball's high-scoring format — a team can dominate TOP with field goals while the opponent scores touchdowns on short drives.

### Explicit "garbage time" mode

A formal game state flag that changes all simulation parameters at once. Rejected in favor of composing existing systems (substitutions + play-calling + tempo) because it's more maintainable and each component can be tuned independently.

### Coach personality gating

Only conservative coaches pull starters early; aggressive coaches leave them in. Rejected for the initial implementation because the behavior should be universal — even aggressive coaches pull starters in 35-point blowouts. Future work could modulate the tier thresholds based on coaching personality (e.g., aggressive coaches require 5 more points to trigger each tier).

---

## Files Changed

| File | Lines Changed | Summary |
|------|--------------|---------|
| `engine/game_engine.py` | +136 / -17 | `_blowout_tier()`, updated `_is_blowout()`, graduated substitution logic in `evaluate_coaching_substitutions()`, blowout clock-chew in `select_play_family()`, tempo milking in drive simulation |

## Related Documents

- [Coaching Substitution System AAR](aar_2026-03-20_coaching_substitutions.md) — Original substitution system this builds on
- [Fatigue System Overhaul PRD](prd_fatigue_system_overhaul_2026_03_20.md) — Energy drain and bench-rebench fixes
- [Lead Management Countermeasures AAR](AAR_lead_management_countermeasures.md) — Coach personality-driven lead protection (stacks with blowout system)
