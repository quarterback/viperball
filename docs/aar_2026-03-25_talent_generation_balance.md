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

| Archetype | Center (original → final) | Spread (original → final) | Base OVR range |
|---|---|---|---|
| doormat | 28 → 15 | 5 → 12 | ~15-27 |
| underdog | 50 → 20 | 6 → 12 | ~15-32 |
| punching_above | 65 → 35 | 6 → 12 | ~23-47 |
| regional_power | 78 → 44 | 5 → 12 | ~32-56 |
| national_power | 89 → 52 | 4 → 12 | ~40-64 |
| blue_blood | 95 → 64 | 3 → 12 | ~52-76 |

**Key design decisions:**
- **All centers dropped by ~30 points.** This is the philosophical shift: base stats represent raw, undeveloped talent. Players arrive as projects. In-game multipliers, coaching, and the development system are what transform a 64-center blue blood recruit into an All-American. Nobody walks onto a roster already elite.
- **All spreads unified to 12** (from 3-6). With a gaussian spread of 12, individual stats on the same player swing ±12 points from center (1 sigma) and ±24 points (2 sigma). A blue blood Viper might have 76 speed but 52 awareness — she has one elite tool to develop but needs coaching to round out her game.
- The uniform spread across tiers means the *center* is what differentiates programs, not the consistency. A blue blood (center 64) and a doormat (center 15) still produce totally different rosters. But within each tier, individual players are interesting and varied.
- Hidden gem boosts recalibrated proportionally for the new scale.
- **OVR floor lowered from 40 to 15** across player_card.py, recruiting.py, and development.py so the full range of talent is visible rather than being clamped into an artificial floor.

**Conference floors adjusted proportionally** to reflect the new center scale.

### Recruiting (`engine/recruiting.py`)

**Star tier stat ranges shifted down ~30 points:**

| Star tier | Before | After |
|---|---|---|
| 5-star | 83-98 | 49-63 |
| 4-star | 72-90 | 37-54 |
| 3-star | 58-78 | 25-45 |
| 2-star | 45-68 | 15-35 |
| 1-star | 35-58 | 15-25 |

A 5-star recruit now arrives at 49-63 — clearly the best available talent, but far from a finished product. In-game multipliers and development over 2-4 seasons are what transform them into stars. The journey IS the game.

### Transfer portal (`engine/transfer_portal.py`)

**Stat ranges shifted down by 30:**

| Player type | Before | After |
|---|---|---|
| Base (Soph/Jr) | 65-90 | 28-52 |
| Senior/Graduate | 70-93 | 32-56 |

**5-star potential reduced:** 10% → 6% of portal players. The portal is a depth tool, not a cheat code.

### OVR floor (`player_card.py`, `recruiting.py`, `development.py`)

**Floor lowered from 40 to 10.** With base stats this low, the old floor of 40 would have masked the entire bottom half of the talent spectrum. Lowering it to 10 makes the full range visible — a doormat freshman should *look* like a 15 OVR player, not be artificially propped up to 40.

## Expected Impact

- **No more 90+ OVR players at generation.** The best a blue blood player can roll at generation is ~76 OVR (center 64 + position offsets + lucky rolls, capped at 96 per stat, constrained by stat budget). Reaching 80+ requires development. Reaching 90+ requires seasons of it.
- **In-game multipliers become the star-making engine.** Base stats are the clay; coaching, scheme fit, and game reps are what sculpt it. A 5-star with 60 OVR who develops quick will *feel* like a rising star, not someone who arrived pre-made.
- **Players have actual profiles.** With spread 12 on a center of 64, a blue blood Viper might roll 76 speed and 52 awareness. She's fast but raw — exactly what a freshman should be.
- **"Elite" is earned, not generated.** The progression from 50s OVR to 80+ over a 4-year career is the core loop. Every star has a development story.
- **Games should be competitive, not shootouts.** With base stats in the 40s-60s, scoring is driven by scheme and multipliers rather than raw stat advantages.
- **Roster management becomes meaningful.** Teams have clear stars, solid contributors, and developmental players. Recruiting and portal decisions matter because you're filling actual skill gaps, not swapping one 95 for another.
- **Upsets become plausible.** A punching_above team with a couple hidden gems can now genuinely threaten a national power whose bottom starters might be in the mid-60s on key stats. The overlap in the tails creates drama.
- **Development matters.** A 5-star arriving at 82 OVR needs to grow into a 90+ player over 2-3 seasons. That progression arc is the story of a dynasty mode.

### Generation ceiling and stat budget (all three pipelines)

**Per-stat ceiling lowered from 99 to 96** across roster generation, recruiting, and transfer portal. A freshly generated player can never have a stat above 96. Reaching 97-99 requires earning it through the development system over multiple seasons — that's a meaningful progression arc.

**Stat budget system added to roster generation.** After rolling all 11 stats, total points are capped at `center * 11 + 44` (roughly 4 points of headroom per stat above the archetype center). If a player's total exceeds the budget, excess is trimmed from their highest stats first. This preserves the player's profile shape (their best stat stays their best) while preventing the "wall of 99s" problem. Example: a blue blood (center 87) has a budget of 1001 — avg stat ~91, allowing some stats to reach 96 as long as others stay lower.

## Risk Assessment

- **Possible over-correction:** If scoring drops too far, the centers can be nudged back up 2-3 points without touching the spreads. The spreads are the more important fix.
- **Conference floor interaction:** The floors were lowered but may need further tuning if weak-conference teams are too competitive with strong-conference teams. Monitor SEC/ACC bottom-tier team OVRs.
- **Existing saved rosters unaffected:** These changes only impact newly generated rosters. Existing dynasty saves will retain their current (inflated) talent until natural attrition cycles players out through graduation and portal departures.
