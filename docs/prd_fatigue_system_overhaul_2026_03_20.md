# PRD: Fatigue System Overhaul — March 2026

**Status:** Implemented
**Date:** 2026-03-20
**Branch:** `claude/add-fatigue-system-Osihl`

---

## Problem Statement

The fatigue system had three categories of issues: substitution bugs that broke the coaching rotation system, incomplete energy drain coverage that made fatigue irrelevant for most play types, and missing bye week recovery that left no incentive for rest weeks.

### 1. Substitution System Bugs

The coaching substitution system (PR #191) introduced performance-based benching, workload management, and blowout rest — but shipped with several integration issues:

- **Zeroback benching vulnerability:** The team's last available Zeroback could be benched, removing all kicking ability. In Viperball, where snap kicks (5 pts) are the premium scoring play, losing your kicker mid-game is catastrophic.
- **Bench-rebench race condition:** Players rested for one drive were unbenched at the start of the next drive, then immediately re-evaluated and re-benched in the same `evaluate_coaching_substitutions()` call. A fatigued halfback with 13 carries would bounce on and off the bench indefinitely.
- **Benched players leaking into plays:** 8 player selection paths still used `_injured_names()` instead of `_unavailable_in_game()`, allowing benched players to accumulate OL block credits, kick pass hurries, punt/kick return stats, and ST coverage tackles while supposedly on the bench.

### 2. Incomplete Energy Drain

Individual player energy (`game_energy`) only drained on 3 of ~50 play outcomes:

| Play Type | Players Drained | Players NOT Drained |
|-----------|----------------|---------------------|
| Run plays | Carrier, primary tackler | OL blockers, assist tacklers |
| Kick passes | Nobody | Kicker, receiver, defender, sacker, interceptor |
| Trick plays | Nobody | Carrier, tackler |
| Lateral chains | Chain participants | Tackler, interceptor |
| Punts | Nobody | Punter, returner |

This meant kick passes — the primary aerial weapon in Viperball — had zero individual fatigue cost. A Zeroback could throw 25 kick passes with no energy penalty. Defenders covering those passes were never drained either, making the fatigue cliff at 40% energy irrelevant for pass-heavy offenses.

### 3. Defense Recovery Gap

`recover_energy_between_drives()` only restored energy to the offensive team (+5.0 per player). The defensive team received zero recovery between drives, causing defenders to progressively drain toward the fatigue cliff with no recovery mechanism outside of halftime (+30.0). By Q4, defensive starters were routinely below 40% energy — well into the cliff zone — while offensive players stayed fresh.

### 4. No Bye Week Recovery

Teams on a bye week received no benefit. Injuries ticked down normally but there was no accelerated healing. In a 12-week season where bye positioning is a coaching strategy, bye weeks should meaningfully help injured rosters recover.

---

## Goals

| Goal | Metric | Before | After |
|------|--------|--------|-------|
| Prevent kicker-less games | ZB benched as last kicker | Possible | Blocked |
| Eliminate bench bouncing | Players re-benched same drive they return | Possible | Blocked |
| Benched players off the field | Selection paths using `_unavailable_in_game` | 12 of 20 | 20 of 20 |
| Energy drain coverage | Play types with individual drain | 2 of 6 | 6 of 6 |
| Defense recovery parity | Defensive energy recovery between drives | 0.0 | +3.0/player |
| Bye week healing benefit | Injury recovery acceleration on bye | None | ~40% chance to shave 1 week |

---

## Changes

### 1. Zeroback Benching Protection

Added `_is_last_kicker(team, player, already_out)` helper. All three benching paths (blowout, performance, workload) now skip the player if they're the team's last available Zeroback.

**Why not protect all ZBs?** Teams with 2-3 Zerobacks should still be able to rest one. The protection only activates when benching would leave zero available kickers.

### 2. Bench-Rebench Race Condition Fix

`_process_bench_expirations()` now returns the set of player names just unbenched. This set is passed to `evaluate_coaching_substitutions(just_returned)` and merged into `already_out`, preventing those players from being immediately re-evaluated for benching.

### 3. Comprehensive Energy Drain

Added `drain_player_energy()` calls to every play type:

| Play Type | Players Now Drained | Drain Category |
|-----------|-------------------|----------------|
| **Kick pass completion** | Kicker, receiver, tackler | kick_pass (1.2), carrier (1.8), tackler (1.2) |
| **Kick pass incompletion** | Kicker, matched defender | kick_pass (1.2), tackler (1.2) |
| **Kick pass sack** | Kicker, sacker | kick_pass (1.2), tackler (1.2) |
| **Kick pass interception** | Kicker, interceptor | kick_pass (1.2), carrier (1.8) |
| **Trick play** | Carrier, tackler | carrier (1.8), tackler (1.2) |
| **Punt** | Punter | kick_pass (1.2) |
| **Punt return** | Returner | carrier (1.8) |
| **Punt return TD** | Returner | carrier (1.8) |
| **Fake punt** | Playmaker | carrier (1.8) |
| **Lateral chain tackler** | Tackler | tackler (1.2) |
| **Lateral interception** | Interceptor | carrier (1.8) |
| **Run assist tackle** | Assist tackler | tackler (1.2) |
| **KP assist tackle** | Assist tackler | tackler (1.2) |
| **OL blocks** | Blocking linemen | lineman (0.6) |

All drains are modified by the existing fatigue tier system (Elite 0.8x, Standard 1.0x, Low 1.5x), progressive quarter multiplier (Q1 0.6x through Q4 1.4x), and weather effects.

### 4. Defense Recovery Between Drives

`recover_energy_between_drives()` now recovers both sides:
- **Offense** (about to start a new drive): +5.0 energy per player (unchanged)
- **Defense** (just finished a shift): +3.0 energy per player (new)

The asymmetry is intentional — the offense is fresh and preparing; the defense just exerted themselves on the previous drive and the changeover is brief.

### 5. Benched Player Selection Leak Fixes

Replaced `_injured_names()` with `_unavailable_in_game()` in 4 remaining locations:
- `_credit_ol_blocks()` — OL block/pancake credits
- KP OL protection credits
- Kick pass hurry selection
- `_pick_returner()` — punt/kick return selection
- `_pick_coverage_tackler()` — ST coverage tackle selection

### 6. Fallback Player Selection Hardening

`_offense_all()` and `_defense_players()` now attempt an intermediate fallback (any available player) before the absolute last resort of `team.players[:N]`. This prevents benched players from being selected in degraded-roster scenarios.

### 7. Bye Week Recovery

New `resolve_week_bye(week, team_name)` method on `InjuryTracker`:

- **Day-to-day** injuries: Auto-cleared during bye
- **Within 1 week of return**: Auto-cleared (bye rest finishes recovery)
- **All other non-season-ending injuries**: 40% chance to shave 1 week off timeline
- **No setback risk**: Bye weeks are safe recovery — no chance of regression
- **Season-ending injuries**: Unaffected (structural damage doesn't heal in a week)

Called from `simulate_week()` after identifying teams not scheduled for any game that week.

---

## Files Changed

| File | Lines Changed | Summary |
|------|--------------|---------|
| `engine/game_engine.py` | +119 / -23 | Energy drain, sub fixes, defense recovery, selection leak fixes |
| `engine/injuries.py` | +40 | `resolve_week_bye()` method |
| `engine/season.py` | +14 | Bye team identification and recovery call |

---

## Gameplay Impact

**Fatigue now matters across all play types.** Boot Raid offenses (kick pass heavy) will see their Zerobacks and receivers fatigue at realistic rates. Chain Gang offenses already drained lateral participants — now their tacklers drain too, making lateral-heavy drives genuinely exhausting for both sides.

**Defense stays competitive in Q4.** The +3.0 between-drive recovery prevents the death spiral where defenders hit the fatigue cliff with no recovery path. Combined with the existing +30.0 halftime recovery, defenders now manage energy similar to offense rather than draining linearly to zero.

**Bye weeks are strategic.** A team entering its bye with 3 injured starters might get 1-2 back early. DTD players are guaranteed cleared. This makes bye week positioning meaningful for playoff contenders managing banged-up rosters.

**Substitutions work as designed.** Benched players are fully off the field. Kickers are protected. Workload rests don't create bounce loops. The coaching substitution system from PR #191 is now properly integrated across all player selection paths.
