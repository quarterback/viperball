# Viperball Offense System — Schema Reference

> Source of truth: `engine/game_engine.py` lines 1381–1705 (`OFFENSE_STYLES`)
> Play selection logic: `engine/game_engine.py` `select_play_family()` (line 4604)
> AI coaching assignment: `engine/ai_coach.py` `assign_ai_scheme()`

---

## 1. The 9 Offense Styles

| Key | Label | Identity | Play DNA |
|---|---|---|---|
| `ground_pound` | Ground & Pound | Power football, grind 20 yards, punch it in | 70% run:lateral, 85% red zone run, lowest tempo (0.4) |
| `lateral_spread` | Lateral Spread | Stretch defense horizontally with 2–4 lateral chains | 30% laterals, explosive lateral bonus +20%, high risk (1.4) |
| `boot_raid` | Boot Raid | Air Raid with the foot — get to Launch Pad, fire snap kicks | 55% kick rate, snap kick aggression 1.5x, launch pad at opp 45 |
| `ball_control` | Ball Control | Conservative, mistake-free, take the points | Clock burn 1.3x, 75% run:lateral, lowest aggression |
| `ghost` | Ghost Formation | Viper chaos and pre-snap confusion | Misdirection 1.3x, 80% pre-snap motion, trick play heavy |
| `stampede` | Stampede | High-tempo speed run offense, exploit tired defenders | Tempo 0.85 (highest), fatigue exploit +10%, outside runs |
| `chain_gang` | Chain Gang | Maximum laterals, maximum chaos, showtime Viperball | 30% lateral weight, 4-chain preference, risk tolerance 0.90, lateral risk 1.6 |
| `slick_n_slide` | Slick 'n Slide | Go-Go inspired 2-back zone reads + run-kick pass options | RKPO rate 30%, lead back bonus +15%, option read +8% |
| `balanced` | Balanced | No strong tendency, adapts to situation | All bonuses at +5%, no strong tendency |

---

## 2. Offense Style Schema

Every style in `OFFENSE_STYLES` is a dict with these fields:

### Required Fields

| Field | Type | Range | Description |
|---|---|---|---|
| `label` | str | — | Human-readable name |
| `description` | str | — | One-line flavor text |
| `weights` | dict | — | Play family → probability (14 families, should sum to ~1.0) |
| `tempo` | float | 0.3–0.85 | Play-calling speed. Higher = faster clock, more fatigue on both sides |
| `lateral_risk` | float | 0.5–1.6 | Lateral fumble rate multiplier. >1.0 = riskier laterals |
| `kick_rate` | float | 0.15–0.55 | Fraction of plays involving kicking |
| `option_rate` | float | 0.25–0.60 | Frequency of option reads vs straight runs |
| `kick_mode_aggression` | float | 0.25–0.80 | 4th-down kick-mode usage tendency |

### Bonus Modifiers (0.0 = no effect)

| Field | Range | Description |
|---|---|---|
| `run_bonus` | 0.0–0.06 | Flat run yardage boost |
| `fatigue_resistance` | 0.0–0.08 | Stamina drain reduction |
| `kick_accuracy_bonus` | 0.0–0.08 | Kicker accuracy boost |
| `explosive_lateral_bonus` | 0.0–0.25 | Big lateral play modifier |
| `option_read_bonus` | 0.0–0.08 | Option read success rate boost |
| `broken_play_bonus` | 0.0–0.12 | Scramble/improvise success modifier |
| `pindown_bonus` | 0.0–0.10 | Final-drive positioning advantage |

### Situational Dials

| Field | Range | Description |
|---|---|---|
| `run_vs_lateral` | 0.15–0.75 | Ratio split — higher = more run-focused |
| `early_down_aggression` | 0.50–0.85 | Aggressiveness on 1st/2nd down |
| `red_zone_run_pct` | 0.55–0.85 | % of red-zone plays that are runs |

### Style-Specific Fields (optional, used by only some styles)

| Field | Used By | Description |
|---|---|---|
| `weights_attack` | Boot Raid | Alternate weight dict activated at the "Launch Pad" field position |
| `snap_kick_aggression` | Boot Raid, Ball Control, Balanced | Multiplier for snap kick selection in scoring zones |
| `launch_pad_threshold` | Boot Raid | Field position (yard line) that triggers attack mode |
| `lateral_success_bonus` | Lateral Spread, Chain Gang | Lateral completion rate boost |
| `tired_def_yardage_bonus` | Lateral Spread | Extra yards against fatigued defenders |
| `kick_pass_bonus` | Lateral Spread, Ghost, Chain Gang, Slick 'n Slide | Kick pass success boost |
| `viper_touch_rate` | Ghost | % of plays involving the Viper position |
| `pre_snap_motion` | Ghost | Pre-snap motion frequency |
| `misdirection_bonus` | Ghost | Multiplier on misdirection play success |
| `fatigue_exploit_bonus` | Stampede | Extra yards when defense is gassed |
| `chain_length_preference` | Chain Gang | Target number of laterals per chain |
| `risk_tolerance` | Chain Gang | Overall aggression threshold (0.0–1.0) |
| `clock_burn_multiplier` | Ball Control | Multiplier on time consumed per play |
| `rkpo_rate` | Slick 'n Slide | Run-kick-pass-option frequency |
| `lead_back_bonus` | Slick 'n Slide | Bonus for 2-back formations |

---

## 3. Play Families

The 14 play families are the atomic unit of offensive strategy. Each `weights` dict maps these keys to probabilities.

### Run Families

| Family | Play Type | Ball Carrier Positions | Key Archetypes |
|---|---|---|---|
| `dive_option` | RUN | HB, SB, ZB | power_flanker, reliable_flanker |
| `power` | RUN | HB, SB | power_flanker |
| `sweep_option` | RUN | HB, SB, WB | speed_flanker |
| `speed_option` | RUN | HB, WB, SB | speed_flanker, hybrid_viper |
| `counter` | RUN | HB, SB | power_flanker, hybrid_viper |
| `draw` | RUN | HB, SB | power_flanker |
| `viper_jet` | RUN | VP, WB, HB | hybrid_viper, speed_flanker |

### Other Families

| Family | Play Type | Description |
|---|---|---|
| `lateral_spread` | LATERAL_CHAIN | Multi-player lateral chains (2–5 laterals) |
| `kick_pass` | KICK_PASS | Kicker throws to a receiver downfield |
| `trick_play` | TRICK_PLAY | Flea flicker, reverses, trick formations |
| `snap_kick` | DROP_KICK | Drop kick (5 points) — the Viperball signature scoring play |
| `field_goal` | PLACE_KICK | Traditional place kick (3 points) |
| `punt` | PUNT | Territory kick with pindown/touchback potential |
| `kneel` | KNEEL | Victory formation |

### Run Play Config (`RUN_PLAY_CONFIG`)

Each run family has detailed yardage/fumble/personnel configuration:

```python
{
    'base_yards': (min, max),        # Base yardage range before modifiers
    'variance': float,               # Yardage variance multiplier
    'fumble_rate': float,            # Base fumble probability
    'primary_positions': [str, ...], # Eligible ball carrier positions
    'carrier_weights': [float, ...], # Selection weights for each position
    'archetype_bonus': {str: float}, # Archetype → yardage multiplier
    'action': str,                   # Animation/description label
}
```

---

## 4. Play Selection Pipeline

`select_play_family()` transforms the style's static `weights` dict into a dynamic, game-state-aware probability distribution:

1. **Start** with the style's base `weights`
2. **Range-gate kicking families** — suppress snap kicks/FGs that are beyond the kicker's realistic range
3. **Apply scoring gravity zones:**
   - FP >= 85 (deep red zone): boost runs 2.5x, suppress kicks
   - FP >= 75 (snap kick range): boost snap kicks 2.5x
   - FP >= 65 (FG range): boost FG and snap kick
4. **Apply down/yards-to-go modifiers:**
   - YTG <= 3: boost dives/power 2.2x, suppress laterals
   - YTG 4–10: boost kick pass 1.4x, sweeps 1.3x
   - YTG > 10: boost laterals 1.8x, suppress power 0.7x
5. **Apply lateral hard cap** (max ~8% of plays)
6. **Weighted random selection** from the adjusted weights

---

## 5. Offense vs Defense Matchup Matrix

`OFFENSE_VS_DEFENSE_MATCHUP` (line 1734) contains 72 `(offense, defense) → multiplier` entries.

- `< 1.0` = defense has advantage (reduces offensive output)
- `> 1.0` = offense has advantage (boosts offensive output)
- `1.0` = neutral

### Chain Gang Example (high-variance offense)

| vs Defense | Multiplier | Note |
|---|---|---|
| Swarm | 0.78 | Swarm elite vs laterals |
| Blitz Pack | 1.10 | Chain exploits vacated gaps |
| Shadow | 0.88 | Shadow tracks the chaos |
| Fortress | 1.20 | Fortress weakest vs lateral |
| Predator | 1.05 | Slight advantage |
| Drift | 0.90 | Drift contains laterals |
| Chaos | 0.98 | Nearly neutral — chaos vs chaos |
| Lockdown | 0.90 | Coverage shuts down kick pass component |

---

## 6. AI Coaching Assignment

`ai_coach.py` auto-assigns offense styles to teams based on:

### Philosophy → Candidate Offenses

```python
"kick_heavy":        ["boot_raid", "ball_control", "stampede"]
"lateral_heavy":     ["lateral_spread", "chain_gang", "ghost"]
"ground_and_pound":  ["ground_pound", "ball_control", "slick_n_slide"]
"hybrid":            ["balanced", "ghost", "slick_n_slide", "ground_pound"]
```

### Roster Stat Thresholds (add to candidates if met)

| Stat | Threshold | Unlocks |
|---|---|---|
| Kicking >= 77 | boot_raid |
| Speed >= 86 | stampede |
| Lateral >= 87 | lateral_spread |
| Lateral >= 85 | chain_gang |
| Speed >= 87 | ghost |
| Speed >= 83 | slick_n_slide |

### Coaching Influence

Scheme Master coaches with instincts >= 80 boost the top-weighted candidate by 30%. Instincts >= 60 boosts by 15%.

---

## 7. Mid-Game Adaptation

### DC Play Family Adaptation ("Solved Puzzle")

The defensive coordinator "solves" repetitive play-calling mid-game:
- **3+ times in a single drive** → adaptation roll
- **8+ times in a half** → adaptation roll
- Solve chance: `0.20 + (dc_instincts * 0.40) + frequency_bonus - (oc_deception * 0.15)`, capped at 80%
- Once solved: family gets 15% suppression (0.85x multiplier)
- Counter: if offense switches away for 3+ consecutive plays, suppression decays

### Halftime DC Re-Roll

The DC "watches film" at halftime and re-rolls their gameplan stochastically, biased toward the offense's heaviest first-half tendency (up to -0.06 suppression shift).

---

## 8. Where to Add New Offenses or Adaptations

The system is fully data-driven. To add a new offense:

1. **Add entry to `OFFENSE_STYLES`** in `engine/game_engine.py` with all required fields
2. **Add matchup entries** to `OFFENSE_VS_DEFENSE_MATCHUP` (one per defense style)
3. **Wire into `ai_coach.py`:**
   - Add to `PHILOSOPHY_TO_OFFENSE` mapping
   - Add roster stat threshold in `assign_ai_scheme()` if applicable
   - Add label to `get_scheme_label()`
4. **Optionally add style-specific logic** in `select_play_family()` for unique behaviors

To create offense **variants** (same family, different personality):
- Use style-specific bonus fields (the engine ignores unknown keys gracefully)
- Use `weights_attack` for field-position-triggered alternate play calling
- Adjust the situational dials (tempo, run_vs_lateral, red_zone_run_pct)
