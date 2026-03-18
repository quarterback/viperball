# After Action Review — AI Kicking Snap Kicks on Early Downs While Trailing

**Date:** 2026-03-18
**Branch:** `claude/fix-ai-football-decisions-AlCfC`

## Mission

Fix the coaching AI kicking snap kicks on downs 1-3 (especially while trailing), enforce the principle that kicks belong on 6th down, and close all code paths that allow early-down kicks.

## Incident

Kansas State 36.0 vs Cincinnati 35.5 (Week 10 CONF). Cincinnati lost by 0.5 points.

Cincinnati kicked **five snap kicks** in this game, including two on 3rd down in Q4 while trailing:

```
Q3  9:32  CIN  91  2&12  SNAP KICK 19yd — GOOD! +5
Q3  2:19  CIN  80  1&20  SNAP KICK 30yd — GOOD! +5
Q4  9:06  CIN  77  3&8   SNAP KICK 33yd — GOOD! +5   ← trailing ~6
Q4  1:44  CIN  92  3&12  SNAP KICK 18yd — GOOD! +5   ← trailing ~1
```

The final drive is the most egregious: Cincinnati drove 11 plays for 62 yards, reaching the 92 yard line — **8 yards from the end zone**. On 3rd & 12, the AI kicked a snap kick for 5 points instead of continuing to drive for a 9-point touchdown. Cincinnati had 4th, 5th, and 6th down still available. Even gaining 5 yards on 3rd makes every subsequent play better. The AI chose to settle and lost by half a point.

The 1st-down snap kick at the 80 yard line (Q3) is even more inexplicable — you've just started a fresh set of downs in prime scoring territory and you immediately kick.

## Commits

| # | Hash | Summary |
|---|------|---------|
| 1 | `39f7c18` | Fix AI kicking on wrong downs: enforce 6th-down-only kick philosophy |

## Scope

1 file changed, +87 / -217 lines

- `engine/game_engine.py` — 7 changes across kick decision logic, play selection weights, and style overrides

## Root Cause Analysis

Three independent bugs combined to produce early-down snap kicks.

### Bug 1 — Boot Raid Attack Weight Override Bypasses Down Gate

**Severity:** Critical
**Location:** `_apply_style_situational()`, Boot Raid branch (line ~6195)

**Mechanism:** Cincinnati runs the Boot Raid offensive scheme. When field position reaches the "launch pad zone" (`fp >= 55`), the style function replaces ALL play-selection weights with `weights_attack`:

```python
if fp >= launch_pad and fp < 85:
    attack_weights = self._current_style().get("weights_attack", {})
    for k, v in attack_weights.items():
        weights[k] = v  # Overwrites EVERYTHING, including snap_kick = 0.0
```

Boot Raid's `weights_attack` has `snap_kick: 0.35` — 35% of all plays would be snap kicks. This overwrites the `snap_kick = 0.0` that was set at line 5738 for downs 1-3. The down gate was applied *before* the style override, so the override blew right past it.

**Impact:** Any Boot Raid team in the launch pad zone (field position 55-84) could kick snap kicks on **any down**, including 1st down. This is the direct cause of the 1st-down snap kick at the 80 yard line.

**Fix:** After applying `weights_attack`, re-zero kick families if `down <= 5` and not desperation clock:

```python
if down <= 5:
    desperation = (quarter in (2, 4) and time_left <= 45)
    if not desperation:
        weights["snap_kick"] = 0.0
        weights["field_goal"] = 0.0
        weights["punt"] = 0.0
```

### Bug 2 — Pull-Up-Three Has No Deficit Awareness

**Severity:** Critical
**Location:** `_check_snap_kick_shot_play()`, downs 2-3 branch (line ~5227)

**Mechanism:** The "pull-up three" path allowed opportunistic snap kicks on downs 2-3 based on:
- Kicker skill (specialist detection, skill multiplier)
- Field position (distance-based probability tiers)
- Coaching style (`snap_kick_aggression` multiplier)

What it did NOT check:
- Score differential (trailing? leading? tied?)
- Quarter or time remaining (early game? late game?)
- Whether a snap kick's 5 points would even help

Cincinnati's kicker Rasheda Ellis is a `kicking_zb` archetype, triggering the `is_specialist` 1.6x multiplier. Boot Raid has `snap_kick_aggression: 1.5`. Combined with a skilled kicker, the probability on close-range kicks was approximately:

```
base 0.14 × 1.6 (specialist) × 1.5 (boot_raid) × ~1.1 (kicker_mult) ≈ 37%
```

A 37% chance of kicking a snap kick on **every 2nd or 3rd down play** in the launch pad zone, regardless of game situation.

**Impact:** This is the direct cause of the 3rd-down snap kicks while trailing in Q4. The AI had no concept that kicking for 5 when you need 6+ is suboptimal.

**Fix:** Removed the entire downs 2-3 path. `_check_snap_kick_shot_play()` now returns `None` for all downs 1-3. The function is effectively disabled — kick decisions are now centralized in `select_kick_decision()` for downs 4-6 only.

### Bug 3 — Too Many 4th-Down Kick Triggers

**Severity:** Moderate
**Location:** `select_kick_decision()`, down 4 block (line ~4642)

**Mechanism:** Four separate conditions could trigger a 4th-down kick:

1. **Gimme kick:** `dk_success >= 0.65` and `fg_distance <= 25` and `ytg >= 10`
2. **Clock pressure:** `clock_pressure` and `dk_success >= 0.40` and in comfort zone
3. **Green light kicker:** `has_green_light` trait and `dk_success >= 0.50` and in comfort zone
4. **Offense stalling:** `kick_mode_aggression >= 0.60` and `ytg >= 16`

Additionally, the kick mode system activated on 4th-down kicks and then forced snap kicks on every subsequent down (5th, 6th), bypassing normal play selection entirely.

With 5th and 6th down still available, kicking on 4th wastes a down. Even on a "gimme" kick at close range — running a play on 4th could gain yards to improve the 5th-down situation, and if it fails, you still have 5th and 6th to kick from essentially the same spot.

**Impact:** Teams kicked on 4th down far more often than strategically justified. The kick mode escalation compounded this by converting the entire remaining drive into snap kick attempts.

**Fix:** Down 4 now returns `None` (keep driving) in virtually all cases. The only exception is desperation clock (`< 45 seconds` at end of half) AND a bonus possession (the drive is "free" anyway). Kick mode activation was removed entirely.

## Changes Summary

| Area | Before | After |
|------|--------|-------|
| `_apply_style_situational` (Boot Raid) | Replaces all weights with `weights_attack`, including `snap_kick: 0.35` | Re-applies kick gate after override: `snap_kick = 0.0` on downs 1-5 |
| `_check_snap_kick_shot_play()` | 70+ lines: probabilistic snap kicks on downs 2-5 | Returns `None` always for downs 1-3; effectively disabled |
| `select_kick_decision()` down 4 | 4 trigger paths (gimme, clock, green light, stalling) | Only fires on desperation clock + bonus possession |
| `select_kick_decision()` down 5 | Complex threshold system with kick mode, kicker adjustments, traits | Only on bonus possessions (ytg >= 8) or clock pressure (ytg >= 12) |
| `select_kick_decision()` down 6 | Unchanged | Unchanged — this is the kicking down |
| `select_play_family()` early gate | Zeros snap_kick on downs 1-3 | Zeros snap_kick on downs 1-5 |
| `select_play_family()` final gate | None | New final enforcement: re-zeros kick weights on downs 1-5 after ALL modifiers |
| Kick mode | Activated on 4th-down kicks, forced snaps on 5th-6th | Removed — `kick_mode = True` is never set |
| Bonus drive flag | Not accessible to kick decision functions | `self._is_bonus_drive` stored at drive start |

## Design Principle

**Kicks belong on 6th down.** Viperball has 6 downs. The strategic structure is:

- **Downs 1-4:** Advance the ball. Chase the 9-point touchdown.
- **Down 5:** Last advancement attempt. Gaining even a few yards improves the 6th-down kick.
- **Down 6:** The kicking down. Kick, punt, or go for it as a last resort.

Kicking on any down before 6th is like punting on 3rd down in the NFL — you're surrendering downs for no reason. The only exceptions:

1. **Desperation clock** (< 45 seconds, end of half): No time to run more plays
2. **Bonus possessions** (5th down only): The drive is "free" — cash in points
3. **Down 6 always**: This is what the down is for

## Lessons Learned

1. **Style overrides need gate enforcement.** Any function that wholesale-replaces weights (`for k, v in attack_weights.items(): weights[k] = v`) can bypass every gate applied before it. Always re-apply critical gates after overrides, or apply them as a final pass.

2. **Opportunistic kick systems need game awareness.** A "pull-up three" sounds cool in theory but in practice the AI has no concept of game flow. It will happily kick for 5 points when trailing by 6 with 3 downs left and 8 yards from the end zone. If you can't give the AI real situational judgment, don't give it the option.

3. **Specialist multipliers compound dangerously.** Boot Raid (1.5x) × specialist kicker (1.6x) × high skill (1.1x) turned a "rare opportunistic shot" into a 37% per-play probability. When multiple multipliers stack, the theoretical "rare" event becomes the dominant behavior.

4. **Defense in depth for weight gates.** A single `snap_kick = 0.0` on line 5738 is not enough when 150 lines of modifiers follow it. The final safety gate at the bottom of `select_play_family()` ensures no downstream code — current or future — can re-introduce kick weight on early downs.
