# Coaching Staff System — Technical Spec

> Source of truth: `engine/coaching.py`, diffs in `engine/game_engine.py`, `engine/dynasty.py`, `engine/recruiting.py`, `engine/ai_coach.py`. All facts below are drawn from code, not design intent.

---

## 1. Data Model

### 1.1 CoachCard (`engine/coaching.py:174`)

Each coach is a `@dataclass` with:

| Field | Type | Notes |
|---|---|---|
| `coach_id` | str | `"coach_{first}_{last}_{3-digit rand}"` |
| `first_name`, `last_name` | str | |
| `gender` | str | `"male"` / `"female"` / `"neutral"` |
| `age` | int | HC: 40-65, coordinators: 32-58 |
| `role` | str | `"head_coach"` / `"oc"` / `"dc"` / `"stc"` |
| `classification` | str | One of 5 values (see §2) |
| **instincts** | int 25-95 | **HIDDEN — not shown to the player** |
| **leadership** | int 25-95 | |
| **composure** | int 25-95 | Non-linear (see §3.3) |
| **rotations** | int 25-95 | |
| **development** | int 25-95 | |
| **recruiting** | int 25-95 | |
| `contract_salary` | int | Annual salary in dollars |
| `contract_years_remaining` | int | |
| `contract_buyout` | int | `salary * years * 0.5` |
| `year_signed` | int | |
| `team_name` | str | Empty string = free agent |
| `career_wins`, `career_losses` | int | Cumulative |
| `championships` | int | |
| `seasons_coached` | int | |
| `career_history` | List[CoachCareerStop] | |
| `is_former_player` | bool | |
| `former_player_id` | Optional[str] | Links back to PlayerCard |
| `philosophy`, `coaching_style`, `personality`, `background` | str | Flavor text |

#### Computed Properties

| Property | Formula |
|---|---|
| `visible_score` | `leadership*0.20 + composure*0.10 + rotations*0.15 + development*0.25 + recruiting*0.30` — **excludes instincts** |
| `overall` | `instincts*0.20 + leadership*0.20 + composure*0.10 + rotations*0.15 + development*0.15 + recruiting*0.20` — **includes instincts** |
| `star_rating` | 1-5 stars from overall: ≥85=5, ≥75=4, ≥65=3, ≥55=2, else 1 |
| `win_percentage` | `career_wins / (career_wins + career_losses)` |
| `composure_label` | ≤40="Fiery", ≤65="Balanced", >65="Ice" |

### 1.2 CoachContract (`engine/coaching.py:145`)

| Field | Type |
|---|---|
| `coach_id` | str |
| `role` | str |
| `team_name` | str |
| `annual_salary` | int |
| `years_total` | int |
| `years_remaining` | int |
| `buyout` | int |
| `year_signed` | int |

### 1.3 CoachCareerStop (`engine/coaching.py:118`)

One stint at a school: `year_start`, `year_end`, `team_name`, `role`, `wins`, `losses`, `championships`.

### 1.4 CoachingSalaryPool (`engine/coaching.py:377`)

| Field/Property | Description |
|---|---|
| `team_name` | str |
| `annual_budget` | int — generated per-team per-year |
| `contracts` | List[CoachContract] |
| `committed` | Sum of all `annual_salary` in contracts |
| `available` | `max(0, annual_budget - committed)` |
| `can_afford(salary)` | `available >= salary` |
| `add_contract(contract)` | Returns False if can't afford |
| `release_contract(coach_id)` | Returns buyout cost |

---

## 2. Classifications

Five classifications, each with a **primary attribute** that gets a +5-12 generation bonus:

| Classification | Label | Primary Attr | Effect Range Keys |
|---|---|---|---|
| `scheme_master` | Scheme Master | instincts | `scheme_amplification` (0.05-0.12), `gameplan_adaptation_bonus` (0.02-0.06) |
| `gameday_manager` | Gameday Manager | composure | `fourth_down_accuracy` (0.05-0.15), `halftime_adjustment_bonus` (0.03-0.08), `situational_amplification` (0.04-0.10) |
| `motivator` | Motivator | leadership | `trailing_halftime_boost` (1.05-1.12), `momentum_recovery_plays` (1-3), `composure_amplification` (1.10-1.20) |
| `players_coach` | Players' Coach | development | `retention_bonus` (0.10-0.25), `chemistry_bonus_per_game` (0.003-0.006), `recruiting_appeal_prestige` (3-8) |
| `disciplinarian` | Disciplinarian | rotations | `fumble_reduction` (0.85-0.95), `muff_reduction` (0.80-0.90), `variance_compression` (0.90-0.95), `gap_discipline_bonus` (0.02-0.06) |

Effect magnitudes are computed by `get_classification_effects()` (line 1321): the primary attribute is normalized to 0-1 within the 25-95 range, then linearly interpolated between the `(lo, hi)` for each effect key.

---

## 3. Attribute Details

### 3.1 Generation (`_generate_attributes`, line 535)

- Base range scales with prestige: `base_lo = 30 + prestige*0.20`, `base_hi = 65 + prestige*0.25`
- HC gets +3 to both bounds
- Each attr is `randint(base_lo, base_hi)`, clamped to 25-95
- Primary attribute for classification gets an additional `randint(5, 12)` bonus

### 3.2 Instincts (HIDDEN)

- Never shown numerically to the player
- **Excluded from `visible_score`**, which drives salary calculation (`calculate_coach_salary`, line 587)
- **Included in `overall`**, which is used for internal AI evaluation and sorting
- This means a Scheme Master with high instincts and low visible attrs can be cheap to hire but highly effective

### 3.3 Composure (Non-linear)

- ≤40 = "Fiery" — benefits when trailing at halftime
- 41-65 = "Balanced"
- ≥66 = "Ice" — benefits under pressure
- Neither extreme is strictly better; the engine uses `composure_value` (raw int) which different systems interpret differently

---

## 4. Salary System

### 4.1 Coach Salary (`calculate_coach_salary`, line 587)

```
base = visible_score * 2500 + 20_000
if seasons_coached >= 3:
    base *= (0.8 + win_percentage * 0.4)
base += championships * 25_000
if role == "head_coach":
    base *= 1.25
return base * uniform(0.92, 1.08)
```

### 4.2 Team Coaching Budget (`generate_coaching_budget`, line 452)

| Market | Range |
|---|---|
| small | $150k - $300k |
| medium | $250k - $500k |
| large | $400k - $750k |
| mega | $600k - $1.2M |

Then: `base * prestige_multiplier * (1 + win_bonus + championship_bonus) * noise(0.90, 1.10)`

Where `prestige_multiplier = 0.5 + (prestige / 100)`, win bonus = `(wins - 5) * $10k` if wins > 5, championship bonus = $150k.

---

## 5. Gameday Integration (engine/game_engine.py)

### 5.1 Entry Point

`ViperballEngine.__init__` accepts optional `home_coaching` and `away_coaching` (Dict[str, CoachCard]). If provided, calls `compute_gameday_modifiers()` to produce a modifier dict stored as `self.home_coaching_mods` / `self.away_coaching_mods`. If not provided, both default to `{}` — all coaching lookups return 0 via `.get()` defaults, making this fully backwards-compatible.

### 5.2 `compute_gameday_modifiers` (coaching.py:1403)

Blends HC and coordinator attributes (HC weight 0.4, coordinator 0.6 by default). Returns:

| Key | Source | Range |
|---|---|---|
| `instincts_factor` | `_blend("instincts")` normalized 0-1 | 0.0 - 1.0 |
| `leadership_factor` | `_blend("leadership")` normalized 0-1 | 0.0 - 1.0 |
| `composure_value` | HC composure raw | 25-95 |
| `fatigue_resistance_mod` | `(rotations_blended - 50) / 1000` | -0.025 to +0.045 |
| `classification_effects` | From `get_classification_effects(hc)` | Dict of effect values |
| `hc_classification` | HC's classification string | One of 5 values |

Blend rule: for `instincts`, `leadership`, `rotations` the relevant coordinator is DC. For `development`, `recruiting` it's OC. Composure is HC-only. Rotations uses HC weight 0.3 (coordinator weighted heavier).

### 5.3 Five Hooks in the Engine

**Hook 1: Defensive Read Rate** (`get_defensive_read`, game_engine.py, around line 3102)
```python
coaching_read_boost = instincts_factor * 0.06  # max +0.06 at 95 instincts
total_read_rate = base_read_rate + gameplan_bias + situational_boost + personnel_boost + coaching_read_boost
```
- Effect: +0% to +6% added to defensive read success rate (capped at 0.65)

**Hook 2: Leadership → Game Rhythm** (game_engine.py, around line 1904)
```python
home_game_rhythm = 1.0 + (home_game_rhythm - 1.0) * (1.0 - home_lead * 0.3)
```
- `home_game_rhythm` is a per-game random draw from `gauss(1.0, 0.15)` clamped to 0.65-1.35
- Leadership factor (0-1) * 0.3 = up to 30% compression toward 1.0
- Effect: prevents bad-rhythm games; a 95-leadership staff reduces rhythm deviation by ~30%

**Hook 3: Scheme Master → Play Family Modifier** (game_engine.py, around line 3213)
```python
if def_mods.get("hc_classification") == "scheme_master":
    amp = cls_effects.get("scheme_amplification", 0.0)
    pfm = 1.0 + (pfm - 1.0) * (1.0 + amp)
```
- Amplifies the defensive scheme's play-family modifier deviations from 1.0
- At max (instincts 95): `pfm` deviations get 12% stronger

**Hook 4: Disciplinarian → Fumble Reduction** (`_run_fumble_check`, game_engine.py, around line 3352)
```python
if off_mods.get("hc_classification") == "disciplinarian":
    base_fumble *= cls_fx.get("fumble_reduction", 1.0)
```
- Multiplies `base_fumble` by 0.85-0.95 (at max rotations)
- Also applies variance compression to play-family modifiers (offensive side)

**Hook 5: Rotations → Fatigue Resistance** (`_defensive_fatigue_factor`, game_engine.py, around line 3279)
```python
fatigue_resistance += def_mods.get("fatigue_resistance_mod", 0.0)
```
- Adds -0.025 to +0.045 to the scheme's existing `fatigue_resistance`
- This modifies how quickly the defense tires during long drives

### 5.4 Possession-Aware Access

Two helper methods determine which team's mods to use:
- `_coaching_mods()` — returns mods for the team **currently on offense**
- `_def_coaching_mods()` — returns mods for the team **currently on defense**

---

## 6. Development Integration (engine/dynasty.py:618)

In `Dynasty.advance_season()`, when computing `team_dev_boost`:

```python
if hasattr(self, '_coaching_staffs') and team_name in self._coaching_staffs:
    from engine.coaching import compute_dev_boost
    team_dev_boost += compute_dev_boost(self._coaching_staffs[team_name])
```

`compute_dev_boost` (coaching.py:1352): maps HC's `development` attribute (25-95) to a 0-8 scale:
```python
(dev_rating - 25) / (95 - 25) * 8.0
```

This is additive with existing DraftyQueenz dev_boost. A 95-development HC gives +8.0 (same max as DraftyQueenz).

---

## 7. Recruiting Integration (engine/recruiting.py)

### 7.1 Coaching Score in Recruit Decisions

`_compute_team_score` (line 732) now accepts `coaching_score: float = 0.0`:

```python
coach_score = coaching_score * 100.0  # normalize 0-1 → 0-100
prefers_coaching = getattr(recruit, "prefers_coaching", 0.15)

score = (
    recruit.prefers_prestige * prestige_score
    + recruit.prefers_geography * geo_score
    + recruit.prefers_nil * nil_score
    + prefers_coaching * coach_score
    + noise
)
```

- `coaching_score` comes from `compute_recruiting_bonus()` = `hc.recruiting / 95`
- `prefers_coaching` defaults to 0.15 via `getattr` (Recruit dataclass doesn't have this field yet — it's a soft extension point)
- The existing `prefers_prestige` (0.5), `prefers_geography` (0.3), `prefers_nil` (0.2) were NOT re-normalized. The coaching weight is additive, which means total weights now sum to ~1.15 instead of 1.0.

### 7.2 Data Flow

`Dynasty.run_offseason` → builds `team_coaching_scores` dict from `compute_recruiting_bonus()` per team → passes through `run_full_recruiting_cycle` → `simulate_recruit_decisions` → `_compute_team_score` per recruit-per-team.

---

## 8. AI Coach Integration (engine/ai_coach.py)

### 8.1 Scheme Assignment (`assign_ai_scheme`, line 38)

New optional param: `coaching_staff: Optional[Dict]`.

If the HC has `classification == "scheme_master"`:
- instincts ≥ 80 → `_coach_scheme_bias = 0.3`
- instincts ≥ 60 → `_coach_scheme_bias = 0.15`

Applied by boosting the max-weighted offense candidate: `weights[max_idx] *= (1.0 + _coach_scheme_bias)`.

### 8.2 Defensive Play-Calling (`choose_defensive_call`, line 305)

New optional param: `instincts: int = 50`.

If instincts > 50, aggression drifts toward 0.55 (the "optimal midpoint"):
```python
instincts_pull = (instincts - 50) / 900.0  # max ~0.05
aggression += (0.55 - aggression) * instincts_pull
```

### 8.3 `auto_assign_all_teams` (line 162)

New optional param: `coaching_staffs: Optional[Dict[str, Dict]]`. Passes each team's staff through to `assign_ai_scheme`.

---

## 9. Dynasty Integration (engine/dynasty.py)

### 9.1 New Fields on Dynasty

| Field | Type | Notes |
|---|---|---|
| `_coaching_staffs` | `Dict[str, dict]` | `team_name -> {role -> CoachCard}`. Transient (`repr=False`). **Not serialized.** |
| `coaching_history` | `Dict[int, dict]` | `year -> {"changes": ..., "marketplace_summary": ...}` |

### 9.2 Offseason Flow (run_offseason, step 1b)

Inserted between prestige update (step 1) and NIL build (step 2):

1. **Lazy init**: If `_coaching_staffs` is empty, generate staffs for all teams using `generate_coaching_staff(prestige=team_prestige)`.
2. **Build salary pools**: One `auto_coaching_pool()` per team, influenced by prestige, prev wins, championship.
3. **Generate marketplace**: 40 free agents via `CoachMarketplace.generate_free_agents()`.
4. **CPU evaluation loop** (skips human team):
   - `evaluate_coaching_staff()` returns a list of roles to fire
   - **HC firing criteria**: win% < 0.35 and ≥3 seasons → always fired; win% < 0.50 and ≥5 seasons → 30% chance
   - **OC firing criteria**: `development < 40` and losing record → 25% chance
   - **DC firing criteria**: `rotations < 40` and losing record → 25% chance
   - **STC firing criteria**: win% < 0.25 → 10% chance
   - Fired roles filled via `ai_fill_vacancies()`: top 10 marketplace candidates sorted by overall, first affordable one is hired. If nobody affordable, a cheap fill-in is generated (prestige 30, 1-year deal).
5. **Career stat updates**: All coaches (including human team) get `seasons_coached += 1`, `career_wins += team_wins`, `career_losses += team_losses`, `age += 1`, `contract_years_remaining -= 1`.
6. **History**: `coaching_history[year]` stores changes dict and marketplace summary.

---

## 10. Coach Marketplace (engine/coaching.py:867)

### 10.1 Structure

| Field | Type |
|---|---|
| `year` | int |
| `available_coaches` | List[CoachCard] — free agents |
| `poaching_targets` | List[CoachCard] — employed but available |
| `retired_players` | List[CoachCard] — former-player coaches |

### 10.2 Key Methods

**`hire_coach(team_name, coach_id, role, salary, years, year)`**: Searches `available_coaches` and `retired_players`. Removes from list, sets contract fields on card, returns `CoachContract` or `None`.

**`poach_coach(hiring_team, coach_id, new_role, offer_salary, offer_years, year)`**: Searches `poaching_targets`. Accept probability:
```
base = 0.30
+ 0.20 if salary raise ≥ 30%
+ 0.25 if promoted to HC
+ 0.10 if longer contract
cap at 0.90
```
Returns contract on accept, `None` on reject or not found.

**`add_poaching_targets(coaching_staffs)`**: Scans all teams' coordinators/STC (not HC). If overall ≥ 70 and contract ≤ 1 year remaining → 40% chance of being added as poaching target.

---

## 11. Player-to-Coach Conversion (engine/coaching.py:1245)

`convert_player_to_coach(player_card, team_name, role, year, years_after_graduation)`:

### 11.1 Attribute Derivation (`derive_coach_attributes_from_player`, line 1157)

| Coach Attr | Formula |
|---|---|
| instincts | `(awareness + lateral_skill) / 2 + rand(-5, 5)` |
| leadership | `(awareness + power) / 2 + games_bonus + rand(-3, 3)` |
| composure | `rand(35, 80) + rand(-5, 5)` — no playing correlate |
| rotations | `(stamina + awareness) / 2 + rand(-5, 5)` |
| development | `50 + (potential - 1) * 3 + rand(-5, 5)` |
| recruiting | `(hands + awareness) / 2 + rand(-3, 5)` |

Where `games_bonus = min(5, career_games // 10)`.

### 11.2 Classification Derivation (`derive_classification_from_player`, line 1206)

Weighted random. Base weight 1.0 for all. Bonuses:
- awareness ≥ 80 → scheme_master +2.0, gameday_manager +1.5
- tackling ≥ 80 → disciplinarian +2.5
- potential ≥ 4 → players_coach +2.0
- lateral_skill ≥ 85 → motivator +1.5

### 11.3 Contract

- Salary = `calculate_coach_salary() * 0.70` (30% discount for unproven)
- Years = 1 (prove-it deal)
- Buyout = 0
- Age = 22 + `years_after_graduation`

---

## 12. Team JSON Schema

All 187 team JSONs now contain a `coaching_staff` key:

```json
{
  "coaching_staff": {
    "head_coach": { /* full CoachCard.to_dict() */ },
    "oc": { ... },
    "dc": { ... },
    "stc": { ... }
  }
}
```

Generated by `scripts/generate_coaching_staffs.py` (seed 2026). The script reads each team JSON, estimates prestige from `team_stats`, generates a staff, and preserves the existing HC name from the `coaching.head_coach` field if present.

---

## 13. What Is NOT Wired

The following values are **computed** by `get_classification_effects()` and exist in the `CLASSIFICATION_EFFECTS` constant, but are **not consumed** by any game engine or dynasty code:

| Effect Key | Classification | Status |
|---|---|---|
| `gameplan_adaptation_bonus` | scheme_master | Computed, not consumed |
| `fourth_down_accuracy` | gameday_manager | Computed, not consumed |
| `halftime_adjustment_bonus` | gameday_manager | Computed, not consumed |
| `situational_amplification` | gameday_manager | Computed, not consumed |
| `trailing_halftime_boost` | motivator | Computed, not consumed |
| `momentum_recovery_plays` | motivator | Computed, not consumed |
| `composure_amplification` | motivator | Computed, not consumed |
| `retention_bonus` | players_coach | Computed, not consumed |
| `chemistry_bonus_per_game` | players_coach | Computed, not consumed |
| `recruiting_appeal_prestige` | players_coach | Computed, not consumed |
| `muff_reduction` | disciplinarian | Computed, not consumed |
| `gap_discipline_bonus` | disciplinarian | Computed, not consumed |

Additionally:
- `compute_scouting_error()` (coaching.py:1386) — exists but never called
- `CoachMarketplace.poach_coach()` — exists but `run_offseason()` never calls it (CPU teams only use `hire_coach` via `ai_fill_vacancies`)
- `CoachMarketplace.add_poaching_targets()` — exists but never called from dynasty
- `Dynasty._coaching_staffs` — **not serialized** in `Dynasty.to_dict()`/`from_dict()`. Lost on save/load.
- `Recruit.prefers_coaching` — accessed via `getattr` with default 0.15, but the field doesn't exist on the `Recruit` dataclass. Works via duck typing but won't appear in Recruit serialization.
- `coaching_history` — stored on Dynasty dataclass but no code reads it back or displays it

---

## 14. Backwards Compatibility

All new parameters are optional with safe defaults:
- `ViperballEngine(home_coaching=None, away_coaching=None)` — no coaching effects applied
- `assign_ai_scheme(coaching_staff=None)` — no scheme bias
- `choose_defensive_call(instincts=50)` — no aggression pull (50 is threshold)
- `auto_assign_all_teams(coaching_staffs=None)` — no coaching influence
- `run_full_recruiting_cycle(team_coaching_scores=None)` — no coaching in recruit decisions
- `simulate_recruit_decisions(team_coaching_scores=None)` — same
- `_compute_team_score(coaching_score=0.0)` — no coaching component added

No existing function signatures were broken. All existing callers continue to work without modification.
