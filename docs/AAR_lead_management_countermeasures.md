# AAR: Lead Management Countermeasures (V2.7)

**Date:** 2026-02-28
**Feature:** Lead management philosophy layer for coaching AI
**Files Changed:** `engine/coaching.py`, `engine/game_engine.py`, `engine/ai_coach.py`

---

## Problem Statement

The Delta Yards system (`start_position = max(1, 20 - point_differential)`) creates a structural tension between scoring and field position. Leading teams start drives further back, making every point a calculated trade-off. But the coaching AI treated this as a single-strategy problem: run more when leading, hurry when trailing, burn clock in the last 3 minutes. Every coach in a 200+ team league responded identically to the same score differential.

A Chain Gang coach up by 15 played identically to a Ball Control coach up by 15. A Motivator trailing by 10 panicked the same as a Disciplinarian trailing by 10. The Delta Yards mechanic created the *opportunity* for coaching diversity, but the AI didn't express it.

## Solution: Five Countermeasure Tendencies

Each head coach now gets a **lead management profile** — a normalized blend of five countermeasure tendencies derived entirely from existing attributes (personality sliders, classification, offensive style). No new coach attributes were added.

### The Five Tendencies

| Tendency | Leading Behavior | Trailing Behavior |
|---|---|---|
| **Avalanche** | Keep scoring aggressively, accept Delta penalty | Stay aggressive, bombs away, don't change identity |
| **Thermostat** | Modulate offense to maintain lead within target band | Measured increase in aggression, chip away |
| **Vault** | Possess ball, grind clock, deny opponent touches | Trust defense, grind back methodically, won't gamble |
| **Counterpunch** | Accept opponent scores to reset Delta Yards, then re-attack | Energized by deficits, offensive boost |
| **Slow Drip** | Score with FGs/snap kicks only, avoid TDs | Chip away with field goals, won't swing for fences |

### Derivation from Existing Attributes

Each tendency is a weighted sum of personality sliders:

- **Avalanche**: aggression(0.30) + risk_tolerance(0.25) + chaos_appetite(0.20) + variance_tolerance(0.15) + tempo_preference(0.10)
- **Thermostat**: composure_tendency(0.30) + adaptability(0.30) + inv_stubbornness(0.25) + inv_chaos(0.15)
- **Vault**: inv_risk(0.25) + rotations(0.30) + inv_chaos(0.20) + inv_variance(0.15) + inv_tempo(0.10)
- **Counterpunch**: player_trust(0.30) + variance_tolerance(0.25) + risk_tolerance(0.20) + chaos_appetite(0.15) + adaptability(0.10)
- **Slow Drip**: instincts(0.30) + inv_aggression(0.25) + composure(0.20) + adaptability(0.15) + inv_variance(0.10)

Classification and offensive style add bias bonuses (e.g., Motivators get +15% Avalanche/Counterpunch, Disciplinarians get +20% Vault, Boot Raid gets +25% Slow Drip). After bonuses, tendencies are normalized to sum to 1.0.

### Continuous Sensitivity Ramp (Not Binary)

No hard activation threshold. Each coach has a **sensitivity curve** derived from their reactivity score:

```
reactivity = agg(0.30) + chaos(0.25) + inv_stubborn(0.25) + inv_composure(0.20)
sensitivity_offset = max(1.0, 12.0 - reactivity * 0.11)    # 1-12
sensitivity_range  = max(6.0, 15.0 - reactivity * 0.09)    # 6-15
ramp = clamp(0, 1, (|score_diff| - offset) / range)
```

Most reactive coach in the league: starts adjusting at 1-point differentials, fully engaged by 7. Most stoic coach: barely notices until 11+ points, not fully engaged until 25+. Every coach in between lands at a unique point on this curve.

## Integration Points

The lead management profile modifies **five decision systems** in the game engine:

### 1. Play Family Weights (`select_play_family`)
After INT awareness block, before style-situational mods. Each tendency adjusts run/kick_pass/lateral/trick/snap_kick/field_goal weights multiplicatively. Slow Drip TD suppression: when leading in the red zone, shifts weight from scoring plays to kicks.

### 2. Tempo / Time-of-Possession
After `base_time` calculation, before 3-minute warning. Vault coaches slow down (divide base_time by 0.8), Avalanche/Counterpunch speed up (divide by 1.1+). This creates measurable time-of-possession differences between coaching styles.

### 3. Formation Selection (`select_formation`)
After weather adjustments, before normalization. Vault coaches shift toward Heavy/Tight formations. Avalanche coaches can shift toward Spread.

### 4. Kick Mode Entry (`_fourth_down_decision`)
After INT awareness kick bias. Slow Drip coaches get +0.25 kick_mode_aggression_shift (strongly prefer kick mode). Vault coaches get some shift too through the Thermostat component.

### 5. Defensive Yard Suppression (Counterpunch only)
When the defensive team's coach has strong Counterpunch tendency (>0.20) and is leading by 14+, defensive suppression is weakened (up to +15% yards allowed). This models the Counterpunch philosophy of deliberately allowing opponent scores to reset the Delta Yards penalty.

Also integrated into `ai_coach.py:choose_defensive_call()` via new `lead_management` parameter — reduces `aggression` by up to 0.30 for Counterpunch coaches leading big.

## Verified Profile Diversity

Test profiles for five extreme coaching archetypes:

```
Avalanche (Motivator, Chain Gang):
  avalanche: 0.361, counterpunch: 0.308, thermostat: 0.149
  Sensitivity: offset=3.1, range=7.7

Vault (Disciplinarian, Ground & Pound):
  vault: 0.421, slow_drip: 0.256, thermostat: 0.189
  Sensitivity: offset=10.3, range=13.6

Thermostat (Gameday Manager, Balanced):
  thermostat: 0.353, slow_drip: 0.198, vault: 0.169
  Sensitivity: offset=7.0, range=10.9

Slow Drip (Scheme Master, Boot Raid):
  slow_drip: 0.385, thermostat: 0.231, vault: 0.194
  Sensitivity: offset=8.6, range=12.2

Counterpunch (Players Coach, Lateral Spread):
  counterpunch: 0.312, avalanche: 0.268, thermostat: 0.202
  Sensitivity: offset=4.5, range=8.9
```

No tendency is ever zero. Every coach has minority tendencies that soften edges. The sensitivity range spans 3.1 to 10.3 for the offset alone — massive diversity across 200+ teams.

## Design Decisions

**Why bidirectional (leading AND trailing)?** A Vault coach trailing by 14 still trusts the defense and grinds. That's a *coaching identity*, not a deficiency. A Counterpunch coach trailing by 7 is energized — they prefer this game state. Making the system unidirectional (lead-only) would miss half the personality expression.

**Why continuous ramp instead of threshold?** Binary thresholds create cliffs in behavior. A coach who "activates" at 7 points would play identically at 6 vs 0, then jump at 7. The continuous ramp means every score change slightly adjusts behavior — the aggressive coaches feel every point.

**Why no new attributes?** The personality slider space (9 sliders x 0-100) already has enough dimensionality. Adding a "lead management tendency" slider would create redundancy with aggression/risk_tolerance/composure. Deriving the profile keeps the coaching card clean and produces emergent diversity from existing attributes.

**Why layer on top instead of replace?** The existing lead-aware logic (INT awareness, 3-min warning, style-situational) serves important baseline functions. The countermeasure system adds a coaching-personality envelope *around* those decisions. A Vault coach still benefits from INT awareness when leading — they just *also* shift toward run-heavy play calling.

## What This Enables

- **Pre-game narratives**: "Coach Stone's Vault defense meets Coach Blitz's Avalanche offense — a classic grind-vs-explosion matchup"
- **Coaching identity**: Every coaching staff in a 200+ team league has a visible, named lead management philosophy
- **Strategic depth**: The Thermostat band, Counterpunch defensie permissiveness, and Slow Drip TD suppression create genuine tactical decisions that play out differently in every game
- **College vs Pro diversity**: With wide sensitivity ranges, college coaches with extreme sliders play dramatically different football than balanced pro coaches
