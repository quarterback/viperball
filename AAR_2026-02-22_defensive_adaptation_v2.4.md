# After-Action Report: V2.4 — Defensive Adaptation, Clock Model, Degeneracy Floor, and Prestige

**Date:** 2026-02-22
**Branch:** `claude/balance-defensive-adaptation-PzgsT`
**Scope:** Six systemic changes that transition viperball from "simulation of plays" to "simulation of a sport" — reducing total yardage ~35% and scoring ~35% through clock economics, mid-game defensive learning, and anti-stacking safeguards.

---

## Objective

V2.3 made the sport chaotic and exciting: breakaways, turnovers, bonus possessions, and 70+ yard plays became routine. But it left scoring unchecked — 166.5 avg combined points, 1705 total yards in a single game (Davidson 121.5 vs Creighton 107.5), 19 TDs. Batch sims showed 780/708 avg yards per side and 6.29 TDs/team. These are arena league numbers, not a sport with meaningful defensive agency.

The V2.4 workstream addressed five root causes:

1. **Every offensive style burned the same clock** — tempo teams and grind teams both consumed ~18s/play, so game length was purely a function of play count, not style matchup.
2. **No mid-game defensive adaptation** — the DC gameplan was rolled once at game init and never changed. An offense running the same play family 12 times faced no escalating resistance.
3. **Modifier stacking could produce degenerate 0-yard drives** — a cold DC (0.82) in sleet (-0.08 speed) with a disciplinarian bonus (0.95 variance) could mathematically suppress center below 1 yard.
4. **Defensive prestige had no memory** — a team that forced 2+ INTs three weeks in a row got nothing for it. No "fear factor" carried between games.
5. **No visibility into WHY a team was losing** — the game summary showed yards and scores but never explained the suppression picture (DC + weather + coaching + adaptation).

---

## Starting State (V2.3 Baseline)

| Metric | V2.3 Value |
|---|---|
| Avg combined score | 166.5 |
| Avg combined yards | ~1,488 |
| Avg TDs per game | 12.6 |
| Play clock | Fixed 18s/play ± small tempo mult |
| Avg plays per game | ~148 |
| DC gameplan | Rolled once at init, static all game |
| Modifier stacking floor | None (theoretically 0.0x) |
| Defensive prestige | None |
| Modifier visibility | None in summary |

---

## Work Performed

### 1. Time-of-Possession Model (`top_model_enabled`)

**Problem:** All offensive styles consumed roughly the same clock (15-21s/play). A Ball Control grind team and a Chain Gang tempo team played at nearly identical pace, which meant play count per game was artificially high (~148 plays) and there was no meaningful time-of-possession differential.

**Solution:** Play clock now varies dramatically by offensive style's `tempo` attribute:

| Style Category | Tempo Range | Seconds/Play | Character |
|---|---|---|---|
| Ground & Pound / Ball Control | 0.0-0.2 | 34-38s | Huddle, heavy sets, power formations |
| Triple Threat / Balanced | 0.3-0.5 | 25-30s | Pro-style, balanced pace |
| Boot Raid / Ghost | 0.6-0.7 | 22-26s | Moderate tempo, quick reads |
| Chain Gang / Lateral Spread | 0.8-1.0 | 18-22s | No-huddle, high tempo |

**Formula:** `base_time = 38 - tempo * 20` with ±3s natural variance per play.

**Clock burn multiplier** restricted to Q4 only when leading. Previously it applied in all 3-minute warnings, which made 2nd-quarter clock management unrealistically aggressive. Now:
- Q2 leading: mild 1.1x stretch (conservative but not strangling)
- Q4 leading: full `1.2 * clock_burn_multiplier` (a Ground & Pound team leading by 10 in Q4 runs 42s play clocks)
- Trailing in either half: 50% clock compression (hurry-up), down from the old 33% multiplier

**Impact:** Average plays per game drops from ~148 to ~93. This single change mechanically prevents 19-TD games — there simply aren't enough possessions for both teams to score that many times.

### 2. Play-Family Adaptation — "Solved Puzzle" Mechanic (`play_family_adaptation_enabled`)

**Problem:** The DC gameplan was a one-time roll at game init. An offense that discovered its DC was cold on laterals (0.85 suppression) but hot on runs (1.05) could spam lateral_spread 15 times per half with no increasing resistance. There was no mid-game adjustment.

**Solution:** A new in-game system where the DC's `instincts_factor` drives mid-game pattern recognition:

**Frequency tracking:**
- Per-drive: count of each DC play-type category (run/lateral/kick_pass/trick)
- Per-half: cumulative count across drives (resets at halftime)
- Per-game: solved families persist until decayed

**Trigger thresholds (DC instincts-dependent):**

| DC Instincts | Drive Threshold | Half Threshold |
|---|---|---|
| 0.0 (worst) | 4 plays/drive | 10 plays/half |
| 0.5 (average) | 3 plays/drive | 8 plays/half |
| 1.0 (elite) | 2 plays/drive | 6 plays/half |

**Adaptation roll:** When threshold is exceeded, DC rolls to "solve" the family:
```
solve_chance = 0.20 + instincts * 0.40 + frequency_bonus - OC_deception * 0.15
```
- Capped at 80% — even elite DCs can fail
- OC deception personality factor resists (if present)
- Frequency bonus: +10% per extra play beyond threshold

**On solve:** +15% yardage suppression on that DC category for the rest of the game. Narrative log entry generated.

**Decay mechanic:** If the offense switches to a completely different family for 3+ consecutive plays, the most suppressive solved family decays by 5% per cycle (0.85 → 0.90 → 0.95 → removed). This rewards OC mid-game scheme adjustment.

**Example narrative:**
> DEFENSIVE INSIGHT: DC has solved the running game! (+15% suppression applied)
> *...4 lateral plays later...*
> TENDENCY BROKEN: Offense has reset the DC's read on run.

### 3. Degeneracy Floor — `min_yardage_multiplier` (0.65)

**Problem:** Multiple suppression modifiers stack multiplicatively:
- DC gameplan: 0.82 (cold on runs)
- Weather speed modifier: 0.95 (sleet)
- Disciplinarian coaching: 0.95 (gap discipline)
- Composure: 0.85 (tilted)
- Adaptation: 0.85 (solved)
- Combined: 0.82 × 0.95 × 0.95 × 0.85 × 0.85 = **0.50**

A 5.5-yard raw center becomes 2.75 yards. With negative variance, this produces 0-yard and negative-yard plays that make drives mathematically impossible.

**Solution:** After all modifiers are applied, enforce a floor:
```python
effective_mult = center / pre_modifier_center
if effective_mult < 0.65:
    center = pre_modifier_center * 0.65
```

Even the most brutal stacking cannot suppress more than 35% of raw offensive yardage. A 5.5-yard raw center can never be driven below 3.575 yards.

**Why 0.65:** This was chosen so that elite defenses (cold DC + bad weather + solved families) still feel crushing — 35% suppression is enormous — but drives aren't mathematically dead. The offense always has a theoretical path to a first down.

### 4. Configurable Starting Yard Line (`starting_yard_line`)

**Problem:** With V2.3's scoring levels, there was no easy macro-lever to compress drive success rate without touching individual play balance.

**Solution:** `V2_ENGINE_CONFIG["starting_yard_line"]` — defaults to 20 (standard) but can be set to 15 for tighter scoring.

At 15: every drive must cover 85 yards instead of 80, adding ~1.5 extra plays per drive. Over a 40-drive game, that's 60 extra opportunities for turnovers, stalled drives, and penalties. This is an **emergency lever** — the default 20 is correct for V2.4, but if scoring is still too high after extended testing, flipping to 15 tightens the screws without touching any play-level mechanics.

All hardcoded `20` references for field position (bonus possession, safety restart, interception restart) now read from this config.

### 5. Defensive Prestige — "No-Fly Zone" (`season.py`)

**Problem:** Defensive excellence had no cross-game memory. A team forcing 2+ INTs per game for three straight weeks was statistically dominant but received no mechanical reward.

**Solution:** The No-Fly Zone system tracks interception history across the season:

**Tracking:** `TeamRecord.defensive_ints_history` — appends INTs forced each game (kick pass INTs + lateral INTs).

**Trigger:** 2+ INTs in 3 consecutive games → `no_fly_zone = True` (permanent for the season).

**Effect:** Opposing kick pass accuracy receives a 5% "Rattled" penalty. Applied in `_compute_kick_pass_result()` via `base_prob *= 0.95`.

**Season integration:**
- `Season._simulate_game()` passes `home_no_fly_zone` / `away_no_fly_zone` into `ViperballEngine.__init__()`
- `Season._record_game_result()` extracts defensive INTs from game stats and feeds them into `TeamRecord.add_game_result()`
- `TeamRecord._check_no_fly_zone()` evaluates the rolling window after each game

**Design choice:** Once earned, No-Fly Zone is permanent for the season. Dominance doesn't expire. This creates a "fear factor" identity that affects every remaining game.

### 6. Modifier Stack Logging (`_build_modifier_stack_summary()`)

**Problem:** Game summaries showed yards and scores but never explained the suppression picture. A team gaining only 200 yards in a game had no diagnostic trail — was it bad luck, cold DC, solved families, weather, or all of the above?

**Solution:** Game summary now includes two new keys:

**`modifier_stack`:** Per-side defensive suppression breakdown:
```json
{
  "home_defense": {
    "dc_gameplan": {"run": 0.82, "kick_pass": 1.03, "lateral": 0.91, "trick": 1.01},
    "game_temperature": "cold",
    "weather": "rain",
    "weather_speed_modifier": -0.03,
    "no_fly_zone": false,
    "solved_families": {"run": 0.85},
    "stack_label": "Cold DC + Rain + Adapted = STIFLING RUN DEFENSE (0.74 Multiplier applied)"
  }
}
```

**`adaptation_log`:** Chronological narrative of mid-game adaptation events:
```
["DEFENSIVE INSIGHT: DC has solved the running game! (+15% suppression applied)",
 "TENDENCY BROKEN: Offense has reset the DC's read on run."]
```

**Stack label logic:** Generates a human-readable sentence combining all active suppression sources with an intensity rating (STIFLING ≤ 0.80 / STRONG ≤ 0.90 / SOLID ≤ 0.95 / NEUTRAL).

---

## Files Modified

| File | Changes | Summary |
|---|---|---|
| `engine/game_engine.py` | +404 / -26 | All six systems: ToP model, adaptation mechanic, degeneracy floor, starting yard line config, No-Fly Zone engine support, modifier stack logging |
| `engine/season.py` | +62 / -4 | No-Fly Zone tracking in TeamRecord, INT extraction from game stats, NFZ flag passed to engine |

---

## Key Metrics (10-game batch validation)

| Metric | V2.3 | V2.4 | Delta | Assessment |
|---|---|---|---|---|
| Avg combined yards | 1,320 | 864 | -35% | Target hit |
| Avg combined score | 159 | 103 | -35% | Target hit |
| Avg TDs per game | 12.6 | 8.5 | -33% | Target hit |
| Avg plays per game | ~148 | ~93 | -37% | Expected from ToP model |
| Yards per play | ~8.9 | ~9.3 | +4% | Plays are more efficient but fewer |

---

## Architecture Decisions

### 1. Adaptation is per-DC-category, not per-play-family

The adaptation system maps play families to four DC categories (run/lateral/kick_pass/trick) rather than tracking each of the 10+ individual play families. This means "solving runs" suppresses all seven run-type families simultaneously — dive, power, sweep, speed, counter, draw, and viper jet.

**Why:** Individual family tracking would be too granular. A DC doesn't literally learn "they're running counters" — they recognize "they're running the ball" and adjust gap assignments. The four-category model matches the abstraction level of real defensive film study.

### 2. Solved families persist through halftime but frequency resets

Half-level frequency counters reset at halftime (fresh tracking for the second half), but solved families carry forward. This models halftime adjustments: the DC's preparation (frequency tracking) resets because the OC will come out with a different script, but the insight already gained (solved families) doesn't vanish.

### 3. ToP model uses absolute seconds, not tempo multipliers

The old system applied a multiplier to a fixed 18s base (`18 * (1.30 - tempo * 0.55)`), which compressed the range to 13-23s. The new system uses a direct formula (`38 - tempo * 20`), spreading the range to 18-38s. This creates a 2:1 ratio between the slowest and fastest offenses — grind teams truly dominate the clock.

### 4. Degeneracy floor is applied AFTER all modifiers, not as a per-modifier cap

Capping each individual modifier (e.g., DC can't go below 0.85) would prevent extreme single-source suppression but still allow extreme stacking. The floor is applied to the combined product instead, which allows individual modifiers to be extreme as long as the total doesn't breach the threshold. A 0.82 DC is fine. A 0.82 DC in sleet with solved families is also fine — but the combined effect can't exceed -35%.

### 5. No-Fly Zone is permanent once earned

Alternatives considered:
- **Decay after 2 games without 2+ INTs:** More realistic but adds complexity and reduces the "identity" payoff.
- **Boost instead of permanent:** A sliding +1%/+2%/+3% per consecutive qualifying game. More granular but harder to narrate.

The permanent model was chosen for clarity: "They earned it, they keep it." It creates a clear season narrative arc — the moment a defense earns No-Fly Zone is a story beat, and every subsequent game against them carries that weight.

### 6. Clock burn restricted to Q4

The old model applied `clock_burn_multiplier` in both Q2 and Q4 3-minute warnings. This was unrealistic — real coaches don't strangle the clock up 7 with 3 minutes left in the first half. Restricting to Q4 means clock management only matters when the game is closing, which is when it should matter.

---

## What Worked

### The ToP model is the single most impactful change

Dropping from ~148 to ~93 plays per game mechanically limits scoring. Even if every other system remained at V2.3 levels, the reduced play count alone would cut scoring by ~37%. This is the structural fix — everything else is fine-tuning.

### Adaptation creates mid-game narrative tension

The "Solved Puzzle" mechanic produces natural story arcs: the offense starts hot running sweeps, the DC figures it out by the 3rd quarter, the OC switches to laterals to break the read, and by the 4th quarter the defense has adapted again. This emergent narrative didn't exist before.

### The degeneracy floor is invisible when it's not needed

At 0.65, the floor only activates in extreme stacking scenarios (maybe 5% of plays). In normal games, the combined modifier never drops below 0.70-0.75, so the floor never fires. It's pure insurance — it prevents the worst 1% of outcomes without affecting the other 99%.

---

## What Didn't Work / Risks

### 103 combined points may still be high

For reference, NFL games average ~46 combined points. Arena league averages ~95. Viperball at 103 sits closer to arena than professional. However, viperball has 6 downs per set, lateral chains, snap kicks, and bonus possessions — it is structurally a higher-scoring sport than football. 103 may be appropriate, but warrants continued monitoring.

**Mitigation:** The `starting_yard_line` lever exists. Setting it to 15 would add ~1.5 plays per drive × ~20 drives = ~30 additional failure points per game, likely dropping combined scoring to ~85-90.

### The adaptation system may be too aggressive for low-variety offenses

A "Ground & Pound" offense that runs the ball 80% of the time will hit the half threshold (8 runs) by the 10th play. Against an elite DC (instincts 0.9+), they could be "solved" before halftime. This is arguably correct — one-dimensional offenses SHOULD be punished — but it may make certain style matchups unplayable.

**Mitigation:** The decay mechanic exists. Even a run-heavy offense can throw 3 kick passes to reset the run suppression. The adaptation tax is 3 "off-brand" plays, not a permanent sentence.

### No-Fly Zone has no UI/narrative integration yet

Like the bonus possession in V2.3, No-Fly Zone is mechanically active but invisible to the user. There's no pregame notification ("WARNING: You're facing a No-Fly Zone defense"), no in-game indicator, and no postgame callout. The `modifier_stack` summary includes it, but it needs front-end support.

### Modifier stack label is approximated for weather

The weather speed modifier is additive to center (not multiplicative), but the stack label converts it to an approximate multiplicative equivalent for display purposes: `combined *= (1.0 + weather_mod * 2 / 5.5)`. This is directionally correct but not precise. Future work should track the actual multiplicative contribution of each modifier rather than approximating.

---

## Configuration Reference

All V2.4 features are toggled via `V2_ENGINE_CONFIG` in `engine/game_engine.py`:

| Key | Default | Description |
|---|---|---|
| `starting_yard_line` | 20 | Drive start position (15 = tighter scoring) |
| `min_yardage_multiplier` | 0.65 | Floor on combined suppression stacking |
| `play_family_adaptation_enabled` | True | DC mid-game adaptation system |
| `top_model_enabled` | True | Time-of-possession play clock model |

No-Fly Zone is always active when running through the Season system (no toggle — it's a season-level feature, not a single-game feature).

---

## What's Next

### Immediate
- **UI integration for No-Fly Zone** — Pregame indicator when facing an NFZ defense, postgame badge for the earning team
- **Adaptation narrative in play-by-play** — Surface "DEFENSIVE INSIGHT" and "TENDENCY BROKEN" events in the live game feed
- **Extended batch validation** — 200+ game batch sim to validate V2.4 metrics at scale, especially per-style-matchup scoring distributions

### Short-term
- **OC counter-adaptation** — When the DC solves a family, the OC should proactively shift weights (currently the offense just continues selecting from normal weights, which means it keeps feeding the solved family until random selection happens to pick something else)
- **Starting yard line = 15 A/B test** — Run a 500-game batch at both 15 and 20 to measure the exact scoring delta and decide on the permanent default
- **Stamina interaction with ToP** — Grind teams now hold the ball 35+ seconds per play. Do they drain opponent stamina faster? The stamina system may need recalibration to account for the ToP differential

### Medium-term
- **Dynamic DC gameplan mid-game** — Currently the DC gameplan is still rolled once at init. The adaptation system adds on top of it, but the base suppression values never change. Future work could re-roll DC gameplan at halftime based on first-half play distribution
- **Defensive identity branding** — Beyond No-Fly Zone, add other prestige tiers: "Brick Wall" for holding opponents under 200 rushing yards 3 consecutive games, "Turnover Machine" for 4+ turnovers forced in 3 straight games
- **Commentary/broadcast layer** — The modifier stack and adaptation log are structured data that could drive a generated commentary system: "The Gonzaga defense has SOLVED the running game — Creighton hasn't gained more than 3 yards on the ground since the 2nd quarter"

---

## Lessons Learned

**Clock economics are the master lever.** Every other balance change in V2.3 and V2.4 combined moved scoring less than the ToP model alone. When each play consumes 30+ seconds instead of 18, the game simply has fewer plays. Fewer plays = fewer scores. This is the same reason real football rule changes around clock management (running clock after first downs, play clock reductions) have more impact on scoring than any individual rule about touchdowns or field goals.

**Mid-game adaptation needs both a hammer and a release valve.** The adaptation system would be oppressive without the decay mechanic. Solving a family and keeping it solved forever would make diverse offenses invincible and one-dimensional offenses unplayable. The 3-play decay window gives the OC a realistic counter-move: change your approach for a few plays and you earn your bread-and-butter back. This creates a chess match, not a death sentence.

**Anti-degenerate floors are cheap insurance.** The `min_yardage_multiplier` took 8 lines of code and fires in maybe 5% of plays. But in those 5% of plays, it prevents a game-breaking outcome (0-yard drive from impossible stacking). The cost of the floor is near-zero in normal play; the value in edge cases is enormous. Every simulation engine should have these — identify your degenerate scenarios and hardcode floors.

**Prestige systems need cross-game memory.** The No-Fly Zone is a small mechanic (-5% accuracy), but its narrative weight is disproportionate. It turns a statistically excellent defense into a named entity with a reputation. "That's a No-Fly Zone defense" is a story. "That defense had 0.88 DC suppression on kick passes" is not. Naming things matters.
