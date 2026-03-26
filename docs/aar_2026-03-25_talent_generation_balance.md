# After Action Review — Talent Generation Balance

**Date:** 2026-03-25
**Branch:** `claude/balance-talent-generation-mS413`

## Mission

Rebalance the talent generation system to eliminate the glut of 90+ OVR players that was causing unrealistic 100+ point games and compressing the competitive landscape.

## Incident / Starting State

The game engine was generating too many overpowered players across three independent pipelines — roster generation, recruiting, and the transfer portal. The cumulative effect was that top-tier teams fielded rosters where nearly every player was 90+, producing blowout scores that broke immersion.

Specific symptoms:
- **Blue blood rosters were wall-to-wall 93-99 OVR.** With `stat_center=95` and `stat_spread=3`, the gaussian roll produced stats in a razor-tight 92-98 band. After position offsets (+3-5 for Vipers/flankers) and viper boosts (+3), most skill players hit 99 on multiple attributes.
- **National power teams weren't far behind.** `stat_center=89` with `stat_spread=4` meant OVRs landing 85-93 baseline, and hidden gems (4-7 per team, +4-8 boost) pushed several players past 95.
- **Transfer portal seniors generated up to 93 OVR base** with +2-6 position boosts on top, routinely producing 95+ players from thin air. 10% of portal players rolled 5-star potential.
- **Recruit stat ranges were too generous.** 5-star recruits rolled 83-98, 4-star rolled 72-90 — the overlap with portal ranges meant the talent pipeline was flooded from every direction.
- **Stat spreads were universally too narrow (3-6).** This made every player on a team feel like a clone of every other player. A blue blood's worst player was only ~6 points worse than its best. No real depth chart drama.

The net effect: when two elite teams met, both had 11 starters averaging 95+ OVR, producing basketball-score shootouts. Lower-tier teams had no prayer, not because of a talent gap (which is fine) but because the gap was a cliff.

## Root Cause Analysis

### 1. Stat centers were calibrated for ceiling, not average

The archetype system was designed so that `stat_center` represented the *floor* of where a team's talent should land, not the center. Blue blood at 95 meant "everyone starts at 95 and the spread is just noise." This inverted the intent — the center should be the *average*, with the spread creating genuine variance above and below.

### 2. Gaussian spreads were too narrow to create roster texture

With `stat_spread=3` (blue blood) or `stat_spread=4` (national power), 95% of all stat rolls fell within ±6-8 points of center. On a 15-99 scale, that's effectively no variance. Every Viper on a blue blood team was a 94-99 speedster. There were no "average starters" or "weak links" — concepts that are fundamental to real sports roster construction. Critically, individual players had no *profile* — a player who was fast was also strong was also aware was also a good kicker. The tight spread meant every stat clustered together, producing generically "good" or "bad" players with no personality.

### 3. Three independent talent pipelines all skewed high

Roster generation, recruiting classes, and the transfer portal each independently generated players at the top of the scale. When a blue blood lost a 96 OVR senior, they replaced him with a 93 OVR portal senior and a 90 OVR 5-star recruit. There was no regression — only lateral movement at the ceiling.

### 4. Hidden gems compounded the problem at the top

National power teams got 4-7 hidden gems with +4-8 boosts. On a team already centered at 89, these gems pushed to 93-97 — indistinguishable from blue blood starters. The gem system was meant to create standout talent; instead, it just raised an already-high floor.

## Changes Made

### Roster generation (`scripts/generate_rosters.py`)

**Stat centers lowered for top three tiers:**

| Archetype | Center (before → after) | Spread (before → after) | Effective OVR range |
|---|---|---|---|
| doormat | 28 → 28 | 5 → 12 | ~15-42 |
| underdog | 50 → 50 | 6 → 12 | ~36-64 |
| punching_above | 65 → 65 | 6 → 12 | ~51-79 |
| regional_power | 78 → 74 | 5 → 12 | ~60-88 |
| national_power | 89 → 82 | 4 → 12 | ~68-96 |
| blue_blood | 95 → 87 | 3 → 12 | ~73-99 |

**Key design decisions:**
- Centers for lower tiers (doormat, underdog, punching_above) were left unchanged — these weren't the problem.
- **All spreads unified to 12** (from 3-6), roughly 3-4x the original values. This is the biggest single change. With a gaussian spread of 12, individual stats on the same player swing ±12 points from center (1 sigma) and ±24 points (2 sigma). A blue blood Viper might have 97 speed but 75 awareness — she's "elite" in the open field but a liability reading defenses. That's a real player, not a generic 95 OVR robot.
- The uniform spread across tiers means the *center* is what differentiates programs, not the consistency. A blue blood (center 87) and a doormat (center 28) still produce totally different rosters. But within each tier, individual players are interesting and varied.
- Hidden gem counts reduced for blue blood (5-8 → 4-6) and national power (4-7 → 3-5) since the wider spreads already create natural standouts.
- Hidden gem boost for blue blood increased slightly (1-4 → 3-6) since the lower center means gems need a bigger push to become All-Americans.

**Conference floors adjusted proportionally** to reflect the new center scale.

### Recruiting (`engine/recruiting.py`)

**Star tier stat ranges shifted down ~4-5 points:**

| Star tier | Before | After |
|---|---|---|
| 5-star | 83-98 | 79-93 |
| 4-star | 72-90 | 67-84 |
| 3-star | 58-78 | 55-75 |
| 2-star | 45-68 | 43-65 |
| 1-star | 35-58 | 33-55 |

A 5-star recruit now arrives as a 79-93 OVR player — elite and clearly special, but not an instant 95+ starter. They need development to reach All-American status, which makes the development system actually matter for top talent.

### Transfer portal (`engine/transfer_portal.py`)

**Stat ranges compressed and lowered:**

| Player type | Before | After |
|---|---|---|
| Base (Soph/Jr) | 65-90 | 58-82 |
| Senior/Graduate | 70-93 | 62-86 |

**5-star potential reduced:** 10% → 6% of portal players. The portal should be a source of solid depth and occasional gems, not an elite talent factory.

## Expected Impact

- **90+ OVR players become rare.** On a blue blood roster (best case), maybe 3-5 of 36 players will be 90+, not 30+. Even those players will have exploitable weaknesses in individual stats.
- **Players have actual profiles.** A Viper with 95 speed and 72 awareness plays completely differently from one with 80 speed and 92 awareness. The wide spread (±12 per stat) means every player is a unique combination of strengths and weaknesses, not a flat OVR number.
- **"Elite" becomes situational.** A player might be elite in one game where her speed dominates, then invisible the next week against a team with high tackling. This creates the kind of variance that makes games feel alive.
- **Games should be competitive, not shootouts.** With individual stats swinging 24+ points within a single roster, no team is uniformly dominant across all phases.
- **Roster management becomes meaningful.** Teams have clear stars, solid contributors, and developmental players. Recruiting and portal decisions matter because you're filling actual skill gaps, not swapping one 95 for another.
- **Upsets become plausible.** A punching_above team with a couple hidden gems can now genuinely threaten a national power whose bottom starters might be in the mid-60s on key stats. The overlap in the tails creates drama.
- **Development matters.** A 5-star arriving at 82 OVR needs to grow into a 90+ player over 2-3 seasons. That progression arc is the story of a dynasty mode.

## Risk Assessment

- **Possible over-correction:** If scoring drops too far, the centers can be nudged back up 2-3 points without touching the spreads. The spreads are the more important fix.
- **Conference floor interaction:** The floors were lowered but may need further tuning if weak-conference teams are too competitive with strong-conference teams. Monitor SEC/ACC bottom-tier team OVRs.
- **Existing saved rosters unaffected:** These changes only impact newly generated rosters. Existing dynasty saves will retain their current (inflated) talent until natural attrition cycles players out through graduation and portal departures.
