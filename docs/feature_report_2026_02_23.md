# Feature Report — February 23, 2026

## Summary

Four areas of the Viperball engine were updated today: kick pass stat tracking (critical bug fix), blocked drop kicks (new mechanic), the Diving Wing archetype (new flanker specialization), and safety/pindown rate tuning.

---

## 1. Kick Pass Stat Tracking Fix

### What Changed

Fixed a three-part bug where player-level kick pass stats (yards, attempts) diverged from team-level stats derived from Play objects.

### Bug Details

**TD Yards Double-Counting**: When a breakaway check inflated a kick pass completion into a touchdown, the kicker's `game_kick_pass_yards` received yards BOTH before the TD determination (the inflated breakaway value) and after (the TD adjustment). This caused player stats to overcount by 60-70+ yards per game on TD-heavy games.

**INT Possession Attribution**: Kick pass interceptions called `change_possession()` before creating the Play object. The Play's `possession` field then reflected the intercepting team instead of the throwing team, causing attempts to be counted against the wrong team in team-level aggregation.

**Fumble Possession Attribution**: Same pattern as the INT bug — defensive fumble recoveries and fumble-into-turnover-on-downs plays also called `change_possession()` before the Play was created, misattributing the play.

### Fix

- Moved player yard tracking (`game_kick_pass_yards`, `game_yards`) to a single assignment AFTER the TD/gain/first-down determination, using the final `yards_gained` value.
- Saved `self.state.possession` into a local variable before any `change_possession()` call in all five affected return paths (INT, INT-return-TD, fumble-defense-recovery, fumble-offense-TOD, incomplete-TOD).

### Verification

| Metric | Before | After |
|---|---|---|
| Attempts match (player vs play objects) | ~90% | **100%** (40/40 team-sides) |
| Yards exact match | ~60% | **85%** (34/40) |
| Unaccounted discrepancies | Multiple | **0** |

The 15% of team-sides with remaining small yard differences are entirely from the penalty system replacing `play.yards_gained` after player stats are recorded — a separate, pre-existing issue.

### Design Principle Established

**"Save possession before mutating state."** Any play that can change possession must capture `self.state.possession` into a local variable before calling `change_possession()`, then use the saved value in the Play object's `possession` field.

---

## 2. Blocked Drop Kicks

### What Changed

Drop kicks (snap kicks) can now be blocked. Previously, all snap kicks were exempt from the block check — only non-snap-kick drop kicks (a path that was never actually called) could be blocked. Since snap kicks and drop kicks are the same play in Viperball, this exemption was removed.

### Mechanic

- **Base block rate**: 2.5% (`BASE_BLOCK_DK = 0.025`)
- Modulated by offensive style, defensive style, and weather
- Capped at 6% maximum
- **Block outcomes**:
  - 70% → Defense recovers the loose ball (turnover)
    - 15% of recoveries → Returned for a touchdown (+9)
    - 85% of recoveries → Defense takes over at the block spot
  - 30% → Kicking team recovers (dead ball, wasted down)

### Blocker Selection

If the defense has a Diving Wing flanker (see below), that player is the blocker. Otherwise, the fastest defensive player gets the block.

### Test Results (20-game batch)

- 160 total DK attempts
- 4 blocked (2.5% rate)
- Breakdown: 1 block TD, 1 defense recovery, 2 dead balls

---

## 3. Diving Wing Archetype

### What Changed

New flanker archetype: **Diving Wing (DW)**. A kick-block specialist who times the kicker's release and dives at the ball — analogous to a cover corner in football.

### Assignment Criteria

Flankers (Halfback, Wingback, Slotback) who meet all three thresholds:
- Tackling ≥ 82
- Speed ≥ 88
- Kicking ≥ 60 (understanding of kicking mechanics helps timing)

### Archetype Properties

| Property | Value | Context |
|---|---|---|
| `dk_block_bonus` | +0.008 | Adds ~0.8% to drop kick block probability |
| `yards_per_touch_modifier` | 0.80 | Below-average ball carrier |
| `fumble_modifier` | 0.90 | Slightly secure hands |
| `td_rate_modifier` | 0.75 | Not a scoring threat |
| `touches_target` | (3, 6) | Low offensive usage |

### Design Intent

The DW is not a separate position — it's a flanker whose athletic profile makes them a natural kick-block threat on the defensive side of the ball. Any defender can block a kick at the 2.5% base rate; a DW just makes it slightly more likely (~3.3% with DW present). Across 187 teams, approximately 189 players meet the DW criteria (~1 per team on average), showing up naturally when rosters are generated in season/dynasty mode.

---

## 4. Safety & Pindown Rate Tuning

### What Changed

Both safeties and pindowns were occurring too frequently. Rates were tuned to match the user's target feel.

### Safeties

**Target**: ~2-3% per team per game

| Field Position | Old Rate | New Rate |
|---|---|---|
| ≤ 2 yards | 10% | 1.8% |
| ≤ 5 yards | 6% | 0.8% |
| ≤ 8 yards | 3% | 0.3% |
| ≤ 10 yards | 3% | — (removed) |
| ≤ 12 yards | — | — (removed) |
| ≤ 15 yards | 1.5% | — (removed) |

Safety checks now only trigger inside the 8-yard line. Measured rate: **~1.7% per team per game** (down from 10%).

### Pindowns

**Target**: ~1.5% per team per game (user chose to leave at current level)

The return chance formula was adjusted from `return_speed / 200` to `return_speed / 90` with a floor of 75% (up from no floor). This means most receiving teams can return the ball out of the end zone, but fast-kicking teams with rouge_hunt offense and the pindown_bonus still create meaningful pindown pressure.

Measured rate: **~5-7% per team per game** (down from 12.5%). The user accepted this rate as fitting the aggressive kicking identity of Viperball's 6-down system.

---

## Files Modified

| File | Changes |
|---|---|
| `engine/game_engine.py` | All four features — stat tracking fix, blocked DK mechanic, DW archetype, safety/pindown tuning |

## AARs Created

| Document | Covers |
|---|---|
| `docs/AAR_kick_pass_stat_tracking.md` | Detailed technical breakdown of the KP stat fix |
