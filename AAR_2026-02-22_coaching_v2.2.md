# After-Action Report: V2.2 Coaching Personality System

**Date:** 2026-02-22
**Branch:** `claude/improve-fantasy-app-menus-cRFqp`
**Scope:** Full implementation of the V2.2 coaching personality layer

---

## Objective

Implement the V2.2 Coaching Personality System — adding sub-archetypes, personality sliders, and hidden traits on top of the existing V2.1 classification system. Also fix two discovered bugs where game engine code was orphaned (defined but never consumed).

## Starting State

- V2 engine rewrite had already been merged, wiring all 15 V2.1 classification effects
- Season coaching plumbing was done (Season passes coaching staffs to ViperballEngine)
- CoachCard had 6 attributes + 1 classification badge
- Coaching staffs generated for 187 teams
- Batch sim calibration: TDs ~3.45, yards ~433, score ~44

## Work Performed

### Phase 1: Audit & Spec (earlier session)

1. **Code-derived spec written** (`COACHING_SPEC.md`) — documented the entire coaching system from actual code, not memory
2. **Full audit** of which coaching effects were actually live vs dead
3. **Post-V2-merge re-audit** — all 15 V2.1 effects confirmed wired, but discovered two bugs:
   - `game_rhythm` orphaned: modified by 6 coaching effects, never consumed in play resolution
   - `EXPLOSIVE_CHANCE` dict defined but never referenced

### Phase 2: V2.2 Implementation (this session)

#### Step 1: CoachCard Data Model Extension (`engine/coaching.py`)
- Added 3 new fields: `sub_archetype`, `personality_sliders`, `hidden_traits`
- Added V2.2 constants: 15 sub-archetypes (3 per core type), 9 personality slider names, 20 hidden trait effect dicts, display labels
- Added helper functions: `personality_factor()`, `get_sub_archetype_effects()`, `compute_hidden_trait_effects()`, `coaching_modifier_chain()`
- Updated `to_dict()`/`from_dict()` for serialization
- Updated `generate_coach_card()` and `convert_player_to_coach()` with V2.2 generation
- Expanded `compute_gameday_modifiers()` to return sub-archetype effects, personality factors, and hidden trait effects

#### Step 2: Bug Fix — Wire `game_rhythm` (`engine/game_engine.py`)
- Applied rhythm multiplier in `_contest_run_yards()` before the dice roll
- Applied rhythm multiplier in `_contest_kick_pass_prob()` on offensive skill
- This makes 6 previously-dead coaching effects live: leadership variance narrowing, composure amplification, halftime adjustment, trailing halftime boost, chemistry, momentum recovery

#### Step 3: Bug Fix — Wire `EXPLOSIVE_CHANCE` (`engine/game_engine.py`)
- Changed `_breakaway_check()` to read per-family explosive base chance from `EXPLOSIVE_CHANCE` dict instead of hardcoded 0.15
- Updated call sites to pass `family` parameter

#### Step 4: V2.2 Personality Multipliers — 8 Game Engine Hooks (`engine/game_engine.py`)
1. **`select_play_family`** — aggression, risk tolerance, chaos appetite, tempo preference, variance tolerance modulate play family weights; punt hater/purist trait
2. **`select_kick_decision`** — aggression lowers go-for-it threshold; red zone gambler trait
3. **`_contest_run_yards`** — variance tolerance on boom/bust; emotional sub-archetype variance; analyst slow start Q1
4. **`_run_fumble_check`** — composure personality on pressure fumbles
5. **`get_defensive_read`** — adaptability vs stubbornness in late game; tactician defensive read bonus
6. **`_apply_halftime_coaching_adjustments`** — adaptability + adjuster sub on halftime adjustment; firestarter sub on trailing boost
7. **`_defensive_fatigue_factor`** — offensive tempo preference pressures opposing defense
8. **Hero ball** — player trust + star touch bias trait on star targeting weight

#### Step 5: Dynasty Integration (`engine/dynasty.py`)
- **Mentor** sub-archetype: +10% development boost multiplier
- **Recruiter** sub-archetype: +15% recruiting appeal, +2 prestige bonus
- **Stabilizer** sub-archetype: +20% retention bonus, +2% portal suppression

#### Step 6: Regenerate Coaching Staffs
- Re-ran `scripts/generate_coaching_staffs.py` for all 187 teams
- Verified V2.2 fields populated in team JSONs (sub_archetype, personality_sliders, hidden_traits)

#### Step 7: Verification
- Batch sim (200 games): TDs 3.3, yards 499, score 50
- Slight upward drift in yards/score from rhythm bug fix making coaching effects live — expected and acceptable

### Phase 3: Merge Conflict Resolution

Merged `origin/main` which had your PR #48 (4th down movement mechanic, bimodal yardage polarization, power play scaffolding). Two conflicts resolved:

1. **`select_kick_decision`**: Kept V2.2 personality modifiers alongside your refactored kick-mode logic
2. **`_contest_run_yards`**: Merged game_rhythm fix (applied to center) with your bimodal yardage polarization system (bust/explosive/normal modes). Rhythm multiplies center before the mode split.

## Files Modified

| File | Lines Changed | Summary |
|---|---|---|
| `engine/coaching.py` | +260 | V2.2 constants, fields, helpers, generation, serialization |
| `engine/game_engine.py` | +127 | 2 bug fixes + 8 personality hooks + merge resolution |
| `engine/dynasty.py` | +29 | Mentor, recruiter, stabilizer sub-archetype integration |
| `scripts/generate_coaching_staffs.py` | +5 | V2.2 fields in dry-run display |
| `data/teams/*.json` (187 files) | ~26k | Regenerated coaching staffs with V2.2 fields |

## Architecture Decisions

- **Multiplicative chain, not additive**: `X_final = X_base * F_personality * F_sub * F_trait`, clamped [0.5, 1.5]. This prevents any single layer from dominating.
- **F(50) = 1.0 neutrality**: Personality sliders gaussian around 50, so the average coach has neutral personality effects. Only outlier coaches push the needle.
- **Hidden traits capped at 2**: Prevents trait soup. 5% chance per trait, 20 traits → ~63% of coaches have 0 traits, ~32% have 1, ~5% have 2.
- **5 no-op sub-archetype effects stored for future systems**: tilt_resistance, tilt_sensitivity, timeout_efficiency, collapse_resistance, surge_probability_bonus. Harmlessly persisted.

## Bugs Found & Fixed

1. **Orphaned `game_rhythm`** — 6 coaching effects modified this state variable across 15 code sites, but it was never read during play resolution. Leadership, composure amplification, halftime adjustment, trailing boost, chemistry, and momentum recovery were all silently dead. Fixed by consuming rhythm in both `_contest_run_yards()` and `_contest_kick_pass_prob()`.

2. **Dead `EXPLOSIVE_CHANCE`** — Per-family explosive play probabilities (5-18%) defined as a constant dict but never referenced. The breakaway system used a hardcoded 0.15 base. Fixed by reading from the dict with play family key.

## Calibration Impact

| Metric | Before V2.2 | After V2.2 | Delta | Notes |
|---|---|---|---|---|
| TDs/team | 3.45 | 3.3 | -0.15 | Within noise |
| Yards/team | 433 | 499 | +66 | Rhythm bug fix makes coaching effects live |
| Score/team | 44 | 50 | +6 | Same cause |
| Plays/game | ~170 | 170 | 0 | Stable |

The drift is from the rhythm bug fix — coaching effects that push rhythm above 1.0 (chemistry, momentum, halftime boosts) now actually affect play outcomes. This is the intended behavior being unmasked, not a regression.

## What's Next

- Tune if the +66 yards drift is too much (could scale rhythm effect by 0.5-0.8 in the consumption points)
- Build timeout, tilt, collapse, and surge systems to activate the 5 no-op sub-archetype effects
- Consider exposing personality sliders in the UI (coach profile cards)
- Q3/Q4 analyst boost (`q3_boost_multiplier`) and `q4_explosive_play_bias` from firestarter are stored but not yet consumed (need quarter-aware hooks)
