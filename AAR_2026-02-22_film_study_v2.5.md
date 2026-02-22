# After-Action Report: V2.5 — Film Study Escalation, Halftime Re-Roll, Defensive Prestige Tiers, and Tuning

**Date:** 2026-02-22
**Branch:** `claude/balance-defensive-adaptation-PzgsT`
**Scope:** Five commits introducing an offensive escalation system that counterbalances V2.4's defensive adaptation, a halftime DC re-roll mechanic, two new defensive prestige tiers, debug tooling for the suppression stack, season UI overhaul, and base yards tuning from 5.5 → 3.8 → 4.2.

---

## Objective

V2.4 successfully crushed scoring from arena-league levels (~160 combined) down to ~103 combined. But it overshot. The Time-of-Possession model locked play count at ~97, the Solved Puzzle mechanic punished repetitive offenses, and the base 5.5x yards multiplier was now too generous relative to the reduced play budget. The result: games felt lopsided toward defense with no offensive comeback mechanic. An offense that fell behind in the adaptation race had no path back.

V2.5 addressed five problems:

1. **No offensive escalation** — Defenses adapted mid-game (Solved Puzzle), but offenses had no equivalent "film study" system. Stale offenses stayed stale.
2. **DC gameplan was static across halves** — Rolled once at game init, never updated. Even after the OC shifted strategy at halftime, the DC's base suppression values didn't respond.
3. **Only one defensive prestige tier** — No-Fly Zone rewarded interception excellence but ignored run defense dominance and turnover volume.
4. **No visibility into the suppression stack** — Debug tools showed scores and yards but not WHY drives stalled. The DC gameplan, adaptation state, and modifier stack were invisible.
5. **Season UI was rudimentary** — Conference setup used a slider instead of real conference assignments; schedule length was editable (should be fixed at 13).

---

## Starting State (V2.4 Baseline)

| Metric | V2.4 Value |
|---|---|
| Avg score/team | ~51.5 |
| Avg yards/team | ~432 |
| Avg TDs/team | ~4.25 |
| Plays/game | ~93 |
| DC gameplan | Rolled once at init, static all game |
| Offensive escalation | None |
| Defensive prestige tiers | 1 (No-Fly Zone only) |
| Debug suppression visibility | None |

---

## Work Performed

### 1. Debug Tools — DC Gameplan & Adaptation Display

**Commit:** `6c19025`

**Problem:** Game summaries showed outcomes but never explained the suppression picture. A team gaining 200 yards had no diagnostic trail — was it bad luck, cold DC, solved families, weather, or all stacking together?

**Solution:** Extended `debug_tools.py` (+287 lines) with three new panels:

- **DC Gameplan Inspector** — Shows both sides' per-category suppression values (run/lateral/kick_pass/trick), game temperature rating, and the combined modifier product.
- **Adaptation State Viewer** — Real-time display of solved families per side, with suppression magnitude and decay status.
- **Modifier Stack Breakdown** — Full multiplicative chain: DC base × weather × coaching × adaptation × composure = effective multiplier, with a severity label (STIFLING / STRONG / SOLID / NEUTRAL).

**Why first:** Every subsequent change in this segment needed validation against the suppression stack. Building the debug tooling first meant every later change could be diagnosed immediately.

### 2. Season UI Fixes, Clock Management, Halftime DC Re-Roll, Defensive Prestige Tiers

**Commit:** `1dba5ec`

#### 2a. Halftime DC Gameplan Re-Roll

**Problem:** The DC gameplan was rolled once at game init and never changed. The V2.4 Solved Puzzle mechanic added per-drive adaptation *on top of* the base gameplan, but the base values themselves were frozen. An OC who shifted strategy at halftime still faced the same underlying DC suppression profile.

**Solution:** `_reroll_dc_gameplan_at_halftime()` — At the start of Q3, each DC re-rolls their gameplan using the normal stochastic process, but biased by first-half offensive tendencies:

- If any play type exceeded 40% of first-half plays, the DC applies a suppression bias of up to -0.06 on that category.
- Bias scales linearly: `min(0.06, (pct - 0.40) * 0.15)` — a 60% run rate yields -0.03, an 80% rate yields the full -0.06.
- Game temperature is recalculated after bias adjustments.
- Minimum 8 first-half plays required for bias to activate (avoids small-sample noise).
- Adaptation log records the re-roll: `"HALFTIME ADJUSTMENT: HOME DC re-evaluated gameplan (temp: cold)"`

**Design choice:** The re-roll is stochastic, not deterministic. The DC doesn't simply "go cold on runs because you ran a lot" — they re-roll with a thumb on the scale. This preserves game-to-game variance while rewarding halftime adjustments narratively.

#### 2b. Defensive Prestige Tiers — Brick Wall & Turnover Machine

**Problem:** No-Fly Zone was the only cross-game defensive prestige. Run defense excellence and turnover volume had no seasonal memory.

**Solution:** Two new prestige tiers in `TeamRecord`:

| Tier | Trigger | Effect |
|---|---|---|
| **Brick Wall** | Hold opponents under 200 rushing yards in 3 consecutive games | -8% yardage center on opposing run-family plays |
| **Turnover Machine** | Force 4+ turnovers in 3 consecutive games | +3% fumble probability on all carriers, +2% INT chance on kick passes |

Both are permanent once earned (same design as No-Fly Zone). Tracking data flows through `Season._record_game_result()` → `TeamRecord.add_game_result()` → `_check_brick_wall()` / `_check_turnover_machine()`. Prestige flags are passed to the engine via kwargs alongside the existing No-Fly Zone flags.

#### 2c. Season UI Overhaul

- **Conference setup** replaced slider-based conference count with a real assignment UI. Teams load stock conferences from team files and display in expandable panels. Each team has a reassignment dropdown.
- **Schedule length** fixed at 13 regular season games (removed configurable slider).
- **Async season creation** — `_create_season()` converted to async to prevent UI blocking during large league initialization.

#### 2d. Clock Management Refinements

- Q2 leading clock burn reduced to 1.1x (was applying full burn, unrealistic for first half).
- Q4 trailing hurry-up increased to 50% compression (was 33%, too gentle for a team needing to score).

### 3. Base Yards Multiplier Reduction (5.5 → 3.8) + Lateral Cap + Micro-Jitter

**Commit:** `10c644e`

**Problem:** At the original 5.5x multiplier, even with V2.4's ToP model limiting plays to ~97, yards/team was still ~450 and scoring remained high. The per-play yardage was inflated — an even-matchup play generated 5.5 yards center, meaning most drives converted first downs easily despite 20-yard requirements.

**Solution:** Three simultaneous changes:

1. **Base yards multiplier: 5.5 → 3.8** — At power 1.0, center drops from 5.5 to 3.8 yards. This makes even-matchup drives require ~6 plays to convert a first down instead of ~4, creating more opportunities for defensive stands.

2. **Lateral efficiency halved** — Lateral success rate was ~84%, making laterals a near-automatic play. Reduced baseline to create real risk/reward on lateral attempts.

3. **Micro-jitter on all yard calculations** — Small random noise (±0.3 yards) added to every yard result to prevent deterministic patterns in repeated identical situations.

**30-game batch results at 3.8x:**

| Metric | Value |
|---|---|
| Score/team | 52.4 |
| TDs/team | 3.3 |
| Yards/team | 420 |
| Plays/game | 97 |
| 4th down conversion | 26.4% |
| First downs/game | 11.2 |

**Assessment:** Scoring was realistic but 4th down conversion (26.4%) was too low — drives were dying before reaching conversion opportunities. The 3.8x multiplier overcompensated.

### 4. Film Study Escalation — Offensive Comeback Mechanic

**Commit:** `a0d2736`

**Problem:** V2.4 gave defenses a mid-game learning curve (Solved Puzzle) but offenses had no equivalent. A team trailing in the adaptation race had no mechanism to improve as the game progressed. This created a structural asymmetry: defenses got smarter, offenses stayed static.

**Solution:** The Film Study Escalation system — a per-drive dice roll that gives offenses an increasing chance of yard bonuses as the game progresses. Four layered components:

#### Component 1: Quarter-Gated Dice Roll

Each drive, the offense rolls against a quarter-dependent trigger chance:

| Quarter | Trigger Chance |
|---|---|
| Q1 | 10% |
| Q2 | 25% |
| Q3 | 40% |
| Q4 | 55% |

If the roll fails, escalation = 1.0 (no bonus) for that drive. This means early-game drives are almost always at baseline, while late-game drives frequently trigger escalation.

#### Component 2: Ball Carrier Ability

When triggered, bonus magnitude scales with the best available carrier's talent:

```
carrier_talent = (best.speed + best.agility) / 2.0
carrier_bonus = max(0.0, (carrier_talent - 60) / 30.0) * 0.15
```

A 60/60 grinder gets +0% carrier bonus. A 90/90 elite gets the full +15%. This rewards teams that feature their best athletes on critical late-game drives.

#### Component 3: Play Diversity (Offensive Puzzle)

Counts distinct DC categories used this half. Diverse play-calling earns extra escalation:

| Categories Used | Diversity Bonus |
|---|---|
| 1-2 | +0% |
| 3 | +5% |
| 4 | +10% |

This creates a strategic tension with the Solved Puzzle mechanic: using many play families avoids getting solved AND earns diversity bonus, but spreading too thin means no family builds momentum.

#### Component 4: Drive Number Ramp

After drive 3, a gentle +1% per drive (capped at +8%) represents accumulated "film" — the OC has seen more defensive looks and can exploit them.

#### Combined Escalation

```python
escalation = 1.0 + carrier_bonus + diversity_bonus + drive_ramp
escalation = min(1.35, escalation)  # Hard cap at 35%
```

Applied multiplicatively to `center` in `_contest_run_yards()` and to the skill component in `_compute_kick_pass_result()`.

**Maximum theoretical escalation:** 1.0 + 0.15 (carrier) + 0.10 (diversity) + 0.08 (drive ramp) = 1.33x. The 1.35 cap is generous — in practice, very few drives hit all three components at maximum.

**Interaction with Solved Puzzle:** These systems are designed as opposing forces. The DC solves a family (−15% on that category), but the offense escalates (+up to 33% on all yards). A diverse offense that switches families to avoid being solved ALSO earns diversity bonus. The chess match rewards mid-game adaptation on both sides.

### 5. Base Yards Multiplier Bump (3.8 → 4.2)

**Commit:** `80816db`

**Problem:** At 3.8x, even with Film Study Escalation, 4th down conversion was stuck at ~26%. Drives were dying too frequently — the escalation system couldn't overcome the baseline yardage deficit on early-game drives where escalation rarely triggers.

**Solution:** Bumped to 4.2x — a compromise between the too-generous 5.5x and the too-tight 3.8x. At power 1.0, center = 4.2 yards. Over 6 downs with ~4.2 yards/play, an even-matchup drive averages 25.2 yards — enough to convert a 20-yard first down with some margin.

**30-game batch results at 4.2x:**

| Metric | Value |
|---|---|
| Score/team | 57.2 |
| TDs/team | 3.9 |
| Yards/team | 445 |
| Plays/game | 97 |
| 4th down conversion | 27.6% |
| First downs/game | 12.2 |
| Avg yards-to-go on 4th | 11.0 |
| Lateral efficiency | 84.0% |

---

## Files Modified

| File | Lines Changed | Summary |
|---|---|---|
| `engine/game_engine.py` | +276 / -10 | Film Study Escalation system, halftime DC re-roll, base yards multiplier (5.5→3.8→4.2), micro-jitter, lateral cap enforcement, Brick Wall / Turnover Machine engine support |
| `engine/season.py` | +85 / -6 | Brick Wall + Turnover Machine prestige tracking, rushing yards / turnovers data pipeline, prestige flags passed to engine |
| `nicegui_app/pages/debug_tools.py` | +287 / -2 | DC Gameplan Inspector, Adaptation State Viewer, Modifier Stack Breakdown panels |
| `nicegui_app/pages/season_simulator.py` | +87 / -18 | Conference assignment UI, fixed 13-game schedule, async season creation |

**Total:** +701 / -34 across 4 files.

---

## Key Metrics Across Tuning Iterations

| Metric | V2.3 (5.5x) | V2.4 (5.5x + ToP) | V2.5 (3.8x) | V2.5 (4.2x + Escalation) |
|---|---|---|---|---|
| Score/team | ~83 | ~51.5 | 52.4 | 57.2 |
| TDs/team | ~6.3 | ~4.25 | 3.3 | 3.9 |
| Yards/team | ~744 | ~432 | 420 | 445 |
| Plays/game | ~148 | ~93 | 97 | 97 |
| First downs/game | — | — | 11.2 | 12.2 |
| 4th down conv | — | — | 26.4% | 27.6% |

---

## Architecture Decisions

### 1. Escalation is per-drive, not per-play

Each drive rolls once for escalation. The result applies to every play in that drive. Alternative: per-play rolls. Rejected because per-play escalation would create wild yard variance within a single drive and make drive outcomes feel random. Per-drive gives the OC a consistent "this drive is clicking" or "this drive is flat" feel — more realistic to how real offensive rhythm works.

### 2. Escalation resets every drive (no accumulation)

Each drive rolls independently. A team that got 1.25x on drive 7 might get 1.0 on drive 8. The drive_ramp component provides gentle accumulation (+1%/drive), but the quarter dice roll and carrier talent are fresh each time. This prevents snowball scoring where a hot offense gets hotter indefinitely.

### 3. Halftime DC re-roll is biased, not deterministic

The DC doesn't simply "go cold on whatever you ran most." They re-roll with a stochastic process and a bias toward your tendencies. A team that ran 70% of the time MIGHT still face a hot-on-runs DC in the second half — it's less likely, but possible. This preserves variance and prevents halftime from being a guaranteed strategic reset.

### 4. The 40% threshold prevents small-sample bias

The DC only applies tendency bias when a play type exceeded 40% of first-half plays and there were 8+ total plays. Without these gates, a team that happened to run 3 laterals out of 5 total plays would trigger a 60% tendency bias on laterals — clearly noise, not signal.

### 5. Prestige tiers are all permanent once earned

Brick Wall and Turnover Machine follow No-Fly Zone's "once earned, permanent" design. This was a deliberate repeat of the V2.4 decision. The value of prestige is in identity: "That's a Brick Wall defense" is a season-long narrative, not a week-to-week fluctuation.

### 6. Play count is time-constrained, not drive-constrained

A critical discovery during tuning: plays/game barely changed between 3.8x and 4.2x (~97 both times). The Time-of-Possession model is the true constraint — 2400 seconds of game clock ÷ ~25s/play ≈ 96 plays. Changing the yards multiplier changes *what happens* in those plays (more/fewer first downs, longer/shorter drives) but not *how many* plays occur. This means the yards multiplier primarily controls drive efficiency and scoring rate, not game length.

---

## What Worked

### Film Study Escalation creates a natural game arc

Q1: Both sides are baseline. Offenses are scripted, defenses are fresh. Low scoring.
Q2: Escalation starts triggering on ~25% of drives. Some offensive rhythm emerges.
Q3: Halftime DC re-roll resets the defensive base. Escalation triggers 40% of drives. The game opens up.
Q4: 55% trigger rate + accumulated drive ramp + diversity bonus from varied first-three-quarter play-calling. Offenses are at their best — but so are DCs who've solved families.

This mirrors real football game flow: slow starts, halftime adjustments, and a wide-open fourth quarter.

### Halftime DC re-roll rewards adaptive OCs

An OC who ran 70% runs in the first half will face a DC biased against runs in the second. But an OC who diversified in the first half gives the DC no clear tendency to bias toward. The re-roll mechanically rewards balanced first-half play-calling, which is exactly how real halftime adjustments work — "they showed us a lot of looks, we can't just key on one thing."

### Debug tooling paid for itself immediately

Every tuning iteration (3.8x, 4.2x, escalation parameters) was validated through the debug panels. Without them, we'd be guessing why 4th down conversion was low. With them, we could see the exact modifier stack on each play and diagnose whether the issue was the base multiplier, DC suppression, escalation not triggering, or something else entirely.

---

## What Didn't Work / Risks

### 4th down conversion is still low (27.6% vs ~85% target)

The target is 85% — viperball has 6 downs precisely so that most drive sets convert. At 27.6%, the sport is playing more like 4-down football where punting is routine. The root cause: average yards-to-go on 4th down is 11.0, meaning the first 3 downs only gain ~9 yards total (~3 yards/play). With a 4.2x multiplier, the center is 4.2 at even power — but play shifts, DC suppression, and variance pull the realized average below center.

**Mitigation path:** This likely requires either a higher base multiplier (4.8-5.0) or a down-specific boost on 4th+ downs that anchors center closer to yards-to-go. The late-down urgency system already exists (`_contest_run_yards` lines 4997-5003) but may need retuning.

### Plays/game (~97) is well below target (140-220)

The ToP model locks play count at ~97 regardless of yards multiplier. Hitting the 140-220 target requires either faster play clocks (reducing the 38s base) or longer quarters (increasing from 600s). This is a structural constraint, not a tuning knob — the base yards multiplier cannot fix it.

### Scoring (~57/team) is below target (65-85)

A direct consequence of the low 4th down conversion and limited play count. More drives stall → more punts → fewer scoring opportunities. The escalation system helps in Q3-Q4 but can't overcome the structural deficit in Q1-Q2 where trigger rates are 10-25%.

### Brick Wall and Turnover Machine have no UI integration

Like No-Fly Zone before them, these prestige tiers are mechanically active but invisible to the user. No pregame indicator, no season standings badge, no narrative callout when earned.

### Lateral efficiency rebounded to 84%

The lateral cap reduction from commit `10c644e` was intended to halve lateral efficiency, but the 30-game batch at 4.2x shows 84% — essentially unchanged from baseline. The cap may not be binding, or the lateral success calculation may have other dominant factors that override the cap.

---

## Configuration Reference

All V2.5 features in `V2_ENGINE_CONFIG`:

| Key | Default | Description |
|---|---|---|
| `base_yards_multiplier` | 4.2 | Primary lever for per-play yardage (was 5.5 in V2.3, 3.8 briefly in V2.5) |

Film Study Escalation has no config toggle — it's always active when `V2_ENGINE_CONFIG` exists. Internal parameters:

| Parameter | Value | Description |
|---|---|---|
| Q1/Q2/Q3/Q4 trigger | 10%/25%/40%/55% | Quarter-gated dice roll |
| Carrier bonus range | 0.0–0.15 | Scales with (speed+agility)/2, baseline 60 |
| Diversity bonus | +0.05 per category above 2 | Rewards showing 3-4 DC categories per half |
| Drive ramp | +0.01/drive after drive 3 | Capped at +0.08 |
| Hard cap | 1.35 | Maximum combined escalation |

Halftime DC re-roll has no toggle — always active. Bias parameters:

| Parameter | Value | Description |
|---|---|---|
| Tendency threshold | 40% | Play type must exceed this for bias |
| Min plays for bias | 8 | Avoids small-sample noise |
| Max bias | -0.06 | Suppression shift at 80%+ tendency |
| Bias rate | 0.15 per % above threshold | Linear scaling |

Defensive prestige tiers are season-level features (no per-game toggle):

| Tier | Trigger | Effect |
|---|---|---|
| No-Fly Zone | 2+ INTs in 3 consecutive games | -5% kick pass accuracy |
| Brick Wall | <200 rush yards allowed in 3 consecutive games | -8% run yardage center |
| Turnover Machine | 4+ turnovers forced in 3 consecutive games | +3% fumble prob, +2% INT chance |

---

## What's Next

### Immediate
- **4th down conversion tuning** — The 27.6% rate is the most pressing gap. Options: raise multiplier to 4.8, strengthen late-down urgency anchor, or add a "must-have" conversion boost on 5th/6th down.
- **Play count investigation** — Determine whether the 140-220 target is achievable within the ToP model or whether play clock parameters need adjustment.
- **Lateral efficiency audit** — Investigate why the lateral cap isn't binding at the expected level.

### Short-term
- **Prestige UI integration** — Add badges to season standings, pregame indicators, and postgame narrative callouts for all three prestige tiers.
- **Escalation narrative** — Surface Film Study Escalation triggers in the play-by-play feed ("FILM STUDY: Offense has found a rhythm — OC featuring [player name]").
- **OC counter-adaptation** — When the DC solves a family, the OC should proactively shift play-calling weights instead of relying on random selection to eventually pick a different family.

### Medium-term
- **Dynamic play clock** — If 97 plays/game is too few, the ToP model's base (38s) may need reduction. A 30s base would yield ~120 plays/game, closer to the 140 target.
- **Escalation decay on turnovers** — A turnover should reset escalation to 1.0 for the next drive, modeling momentum loss after a fumble or INT.
- **Prestige matchup narratives** — When a Brick Wall defense faces a Ground & Pound offense, generate a pregame "clash of styles" narrative.

---

## Lessons Learned

**Offense and defense need symmetric mid-game learning.** V2.4's Solved Puzzle gave defenses a learning curve but left offenses static. The result felt punitive — good defense was rewarded, but good offense wasn't. Film Study Escalation restores symmetry: both sides get smarter as the game progresses, and the outcome depends on which side adapts faster. Asymmetric progression creates structural bias; symmetric progression creates strategic depth.

**The time model is the master constraint, not the yards model.** Changing the base yards multiplier from 3.8 to 4.2 barely moved plays/game (97 → 97). The ToP model's 2400-second budget divided by ~25s/play is the binding constraint. Tuning yards changes drive *quality* (conversion rate, scoring efficiency) but not game *quantity* (total plays). Any future attempt to hit 140+ plays/game must address clock parameters, not yardage.

**Tune in one direction, then correct.** Going from 5.5 → 3.8 was aggressive and immediately showed the floor was too tight. Going from 3.8 → 4.2 was a measured correction informed by batch data. The two-step process (overshoot then correct) was faster than trying to find the right value in a single step, because the overshoot revealed which metrics were most sensitive to the multiplier.

**Debug tooling before tuning, always.** Building the suppression stack panels before touching any balance parameters meant every subsequent change could be diagnosed in minutes instead of hours. The temptation to "just change the number and see what happens" is strong, but without visibility into the modifier stack, you're tuning blind.
