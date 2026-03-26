# After Action Review — Talent Generation Balance

**Date:** 2026-03-25
**Branch:** `claude/balance-talent-generation-mS413`

## Mission

Rebalance the talent generation system to eliminate the glut of 90+ OVR players that was causing unrealistic 100+ point games and compressing the competitive landscape.

## Incident / Starting State

The game engine was generating too many overpowered players across three independent pipelines — roster generation, recruiting, and the transfer portal. The cumulative effect was that top-tier teams fielded rosters where nearly every player was 90+, producing blowout scores that broke immersion.

Specific symptoms:
- **Blue blood rosters were wall-to-wall 93-99 OVR.** With `stat_center=95` and `stat_spread=3`, the gaussian roll produced stats in a razor-tight 92-98 band. After position offsets (+3-5 for Vipers/flankers) and viper boosts (+3), most skill players hit 99 on multiple attributes. Players had no profile — fast was also strong was also aware was also a good kicker.
- **National power teams weren't far behind.** `stat_center=89` with `stat_spread=4` meant OVRs landing 85-93 baseline, and hidden gems (4-7 per team, +4-8 boost) pushed several players past 95.
- **Transfer portal seniors generated up to 93 OVR base** with +2-6 position boosts on top, routinely producing 95+ players from thin air. 10% of portal players rolled 5-star potential.
- **Recruit stat ranges were too generous.** 5-star recruits rolled 83-98, 4-star rolled 72-90 — the overlap with portal ranges meant the talent pipeline was flooded from every direction.
- **Stat spreads were universally too narrow (3-6).** This made every player on a team feel like a clone of every other player. A blue blood's worst player was only ~6 points worse than its best. No real depth chart drama.
- **Per-stat ceiling clamped at 99 with no stat budget.** Even with moderate centers, the gaussian pile-up effect at the 99 ceiling meant that any player with an effective center above ~85 would stack multiple stats at 99. There was no mechanism preventing a player from being elite at everything — no tradeoffs, no weaknesses.

The net effect: when two elite teams met, both had 11 starters averaging 95+ OVR, producing basketball-score shootouts. Lower-tier teams had no prayer, not because of a talent gap (which is fine) but because the gap was a cliff.

## Root Cause Analysis

### 1. Stat centers were calibrated for ceiling, not for raw talent

The archetype system treated `stat_center` as the *floor* of where a team's talent should land. Blue blood at 95 meant "everyone starts at 95 and the spread is just noise." But base stats should represent *raw, undeveloped potential* — the clay that coaching, development, and in-game multipliers shape into finished players. By setting centers near the ceiling, the generation system was doing the development system's job for it, leaving no room for player growth.

### 2. Gaussian spreads were too narrow to create roster texture

With `stat_spread=3` (blue blood) or `stat_spread=4` (national power), 95% of all stat rolls fell within ±6-8 points of center. On a 10-99 scale, that's no variance. Every Viper on a blue blood team was a 94-99 speedster. The tight spread meant every stat clustered together, producing generically "good" or "bad" players with no personality. No fast-but-dumb Vipers, no slow-but-savvy Keepers — just flat numbers.

### 3. Three independent talent pipelines all skewed high

Roster generation, recruiting classes, and the transfer portal each independently generated players at the top of the scale. When a blue blood lost a 96 OVR senior, they replaced her with a 93 OVR portal senior and a 90 OVR 5-star recruit. There was no regression — only lateral movement at the ceiling. The development system was irrelevant because players arrived already developed.

### 4. No ceiling or budget constraints

The per-stat ceiling of 99 combined with no total-stat budget meant that a lucky sequence of gaussian rolls could produce a player with 99 in 10 of 11 stats. The ceiling pile-up effect was especially brutal: with an effective center of 90+ (after position offsets), roughly 20% of rolls would exceed 99 and clamp there, producing a wall of maxed stats.

### 5. Hidden gems compounded the problem at the top

National power teams got 4-7 hidden gems with +4-8 boosts. On a team already centered at 89, these gems pushed to 93-97 — indistinguishable from blue blood starters. The gem system was meant to create standout talent; instead, it just raised an already-high floor.

## Changes Made

### 1. Stat centers dropped ~30 points across all tiers (`scripts/generate_rosters.py`)

This is the philosophical core of the fix. Base stats now represent raw, undeveloped talent. In-game multipliers, coaching, and the development system are what create stars.

| Archetype | Center (before → after) | Spread (before → after) | Base OVR range |
|---|---|---|---|
| doormat | 28 → 15 | 5 → 12 | ~10-27 |
| underdog | 50 → 20 | 6 → 12 | ~10-32 |
| punching_above | 65 → 35 | 6 → 12 | ~23-47 |
| regional_power | 78 → 44 | 5 → 12 | ~32-56 |
| national_power | 89 → 52 | 4 → 12 | ~40-64 |
| blue_blood | 95 → 64 | 3 → 12 | ~52-76 |

### 2. Spreads unified to 12 across all tiers

With a gaussian spread of 12, individual stats on the same player swing ±12 points from center (1σ) and ±24 points (2σ). A blue blood Viper might roll 76 speed but 52 awareness — she's fast but raw, exactly what a freshman should be. The uniform spread means the *center* differentiates programs, not the consistency.

### 3. Per-stat generation ceiling lowered to 96

No freshly generated player can have any individual stat above 96. Reaching 97-99 requires earning it through the development system over multiple seasons. This eliminates the gaussian pile-up at 99 and creates a meaningful progression arc: generation → development → elite.

### 4. Stat budget system added

After rolling all 11 stats, total points are capped at `center × 11 + 44` (~4 points headroom per stat). Excess is trimmed from the highest stats first, preserving the player's profile shape while preventing uniform excellence. A blue blood (center 64) has a budget of 748 — avg ~68 per stat, allowing a few stats to reach the mid-70s as long as others stay lower.

### 5. Recruiting stat ranges shifted down 30 (`engine/recruiting.py`)

| Star tier | Before | After |
|---|---|---|
| 5-star | 83-98 | 49-63 |
| 4-star | 72-90 | 37-54 |
| 3-star | 58-78 | 25-45 |
| 2-star | 45-68 | 15-35 |
| 1-star | 35-58 | 15-25 |

A 5-star recruit arrives at 49-63 — clearly the best available talent, but far from a finished product. Development over 2-4 seasons is what transforms them into stars.

### 6. Transfer portal ranges shifted down 30 (`engine/transfer_portal.py`)

| Player type | Before | After |
|---|---|---|
| Base (Soph/Jr) | 65-90 | 28-52 |
| Senior/Graduate | 70-93 | 32-56 |

5-star potential reduced from 10% → 6%. The portal is a depth tool, not a cheat code. Position boost caps lowered from 99 to 96.

### 7. OVR floor lowered from 40 to 10

Changed across `player_card.py`, `recruiting.py`, and `development.py`. The old floor of 40 masked the bottom half of the talent spectrum. With base stats now in the 15-64 range, the full spectrum needs to be visible. A doormat freshman should look like a 15 OVR player, not be artificially propped up to 40.

### 8. Conference floors adjusted proportionally

| Conference | Before | After |
|---|---|---|
| SEC | 60 | 25 |
| Big Ten | 55 | 20 |
| ACC | 69 | 32 |
| Big East | 53 | 18 |
| Yankee Conference | 65 | 28 |
| Pac-12/16 | 65 | 28 |

### 9. Hidden gem boosts recalibrated

Boosts scaled down proportionally to the new centers so gems create standouts relative to their tier without generating instant stars.

## How This Helps

### The scoring problem

The original complaint: teams scoring 100+ points because both rosters were stacked with 90+ OVR players. When every skill position player has 95+ speed, 95+ lateral skill, and 95+ hands, every play has a high probability of breaking for a big gain. Defenses can't stop what they can't match.

With base stats in the 40s-60s, raw talent alone doesn't dominate. A blue blood's best Viper might have 76 speed — fast for a freshman, but not fast enough to blow past every defender on every play. Scoring becomes a function of scheme, coaching, multipliers, and player development rather than raw stat stacking. The engine's play outcome calculations will produce more contested plays, more stops, more realistic scoring.

### The "all 99s" problem

Previously, a blue blood senior Halfback could generate with 10 of 11 stats at 99. This happened because: high center (95) + tight spread (3) + position offsets (+3-5) + hidden gem boost = everything clamped at 99. Three independent fixes prevent this now:

1. **Center at 64** — a blue blood Halfback's effective center for speed is 64+3 = 67. Even with a lucky +2σ roll, that's 91, not 99.
2. **Generation ceiling at 96** — even if a roll somehow reaches 99, it gets clamped at 96.
3. **Stat budget** — total stat points capped at center×11+44. A player who rolls high on speed pays for it with lower awareness or power.

The result: a newly generated player will have a *profile* — good at some things, average or weak at others — not a flat wall of maxed stats.

### The talent pipeline loop

Before: blue blood loses 96 OVR senior → recruits 90 OVR 5-star → grabs 93 OVR portal senior → net effect: zero regression, permanent ceiling.

After: blue blood loses developed 82 OVR senior → recruits 55 OVR 5-star → grabs 45 OVR portal junior → must develop both over 2-3 seasons to replace lost production. This is roster management. Graduation hurts. Recruiting matters. The portal is a supplement, not a replacement pipeline.

### In-game multipliers become meaningful

With base stats in the 50s-60s even on elite teams, the gap between a well-coached team and a poorly-coached team is driven by multipliers, scheme fit, and game planning — not by who has more 99-rated players. A punching_above team (center 35) with strong multipliers from a great coaching hire can compete with a national_power (center 52) that has better raw talent but worse scheme. This is where upsets come from.

### Development creates stories

A 5-star recruit arriving at 55 OVR who develops to 85 OVR over four years IS the dynasty mode experience. Each season she improves, earns awards, becomes the face of the program. Under the old system she arrived at 93 OVR and had nowhere to go — no arc, no story, no attachment.

## Risk Assessment

- **Possible over-correction on scoring:** If games become too low-scoring, centers can be nudged up 3-5 points without touching the spread/ceiling/budget infrastructure. The 30-point drop is aggressive but the in-game multiplier system is designed to compensate.
- **Multiplier dependency:** This change assumes the in-game multiplier system is robust enough to differentiate teams that start with similar raw stats. If multipliers are too flat, all teams will feel the same in gameplay. Monitor whether scheme/coaching differences produce enough separation in game outcomes.
- **Conference floor interaction:** Floors were lowered proportionally but may need tuning. If SEC doormats (floor 25) are too competitive with Big East powers, the floors need widening.
- **Existing saved rosters unaffected:** These changes only impact newly generated rosters. Existing dynasty saves will retain their current (inflated) talent until natural attrition cycles players out through graduation and portal departures.
- **UI/display consideration:** Player cards will now show stats in the 30s-70s range instead of the 80s-90s. This is correct — it reflects raw talent — but may initially feel "wrong" to players accustomed to seeing high numbers. The numbers are lower because they mean something different now: potential, not finished product.
