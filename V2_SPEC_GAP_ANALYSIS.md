# V2 Engine Spec — Gap Analysis

**Spec:** VIPERBALL V2 Engine Architecture Specification (Feb 2026)
**Codebase audit date:** 2026-02-21
**Audited files:** `engine/game_engine.py`, `engine/coaching.py`, `engine/ai_coach.py`, `engine/season.py`, `engine/nil_system.py`, `engine/dynasty.py`, `viperball_v2/player.py`

---

## Summary Scorecard

| Spec Section | Status | Notes |
|---|---|---|
| **2. Halo Model** | NOT IMPLEMENTED | No team-level halo, no prestige-to-engine integration |
| **3.1 Archetypes (R/E/C)** | NOT IMPLEMENTED | Has 20+ position archetypes instead of 3 variance archetypes |
| **3.2 Four Talent Types** | Partial | Has the 4 core stats + 6 extended; not restricted to 4 |
| **3.3 Power Ratio** | NOT IMPLEMENTED | Uses additive sigmoid, not multiplicative power ratio |
| **3.4 Star Override** | NOT IMPLEMENTED | No star designation or performance floor |
| **3.5 Fatigue Tiers** | Partial | Has per-player fatigue, but not tiered by rating |
| **3.6 Hero Ball + Keying** | NOT IMPLEMENTED | Neither system exists |
| **4. Composure** | NOT IMPLEMENTED | No dynamic per-game composure system |
| **5. Decision Matrix** | Partial | Has aggression system, but not prestige-driven |
| **6. Prestige Decay** | Partial | Offseason-only recalculation, no per-game adjustments |
| **7. Narrative Gen** | NOT IMPLEMENTED | No YAR, no headlines, no composure graph |
| **9. Data Contracts** | Divergent | Most spec fields don't exist |

---

## Detailed Findings

### Section 2: Halo Model — NOT IMPLEMENTED

**Spec requires:** A Team Halo derived from Prestige that provides baseline play resolution for 90% of plays, with individual player ratings only consulted for Star-designated players at Critical Contest Points.

**What exists:** The engine resolves every play at the individual player level. `_contest_run_yards()` (`game_engine.py:3515`) always reads carrier and tackler attributes directly. Team averages (`avg_speed`, `avg_stamina`, etc.) exist on the `Team` class (`game_engine.py:671`) but are only used for breakaway checks and carrier selection, not as a halo replacement for individual resolution.

**Missing:**
- No `halo_offense` / `halo_defense` derived from prestige
- No prestige-to-halo derivation table (spec section 2.2)
- No conditional "use halo vs. use player rating" branching
- No "90% team-level / 10% individual" resolution split
- Prestige exists in `season.py` and `nil_system.py` but is never passed into the game engine

---

### Section 3: Individual Talent System — PARTIALLY IMPLEMENTED (divergent)

#### 3.1 Player Archetypes — DIVERGENT

**Spec requires:** Three archetypes (Reliable, Explosive, Clutch) controlling variance:
- Reliable: clamp roll to `rating ± 10`
- Explosive: full 0-100 roll range, no floor
- Clutch: standard variance + `+15%` boost when Composure < 80 or Q4 within 1 possession

**What exists:** ~20 position-based archetypes (`game_engine.py:314-507`): `kicking_zb`, `running_zb`, `speed_flanker`, `reliable_flanker`, etc. These modify outcomes via multipliers (fumble rate, yards per touch) but do not implement the spec's variance-clamping model.

The spec's design constraint (Star Override only for Reliable/Clutch, Explosive keeps full variance) has no implementation.

#### 3.2 Four Talent Types — PARTIAL

**Spec requires:** Exactly 4 talent ratings: Speed, Kicking, Lateral, Tackling.

**What exists:** `Player` class (`game_engine.py:553`) has the 4 core stats plus 6 extended attributes (`agility`, `power`, `awareness`, `hands`, `kick_power`, `kick_accuracy`). All 10 are used in contest resolution.

#### 3.3 Power Ratio Contest — NOT IMPLEMENTED

**Spec requires:** `success_chance = (carrier_rating / tackler_rating) ** 2`

**What exists:** Additive sigmoid resolution (`game_engine.py:3540-3580`):
```python
delta = off_skill - def_skill  # additive, not ratio
center = 5.0 + 2.5 * (2.0 / (1.0 + math.exp(-delta / 12.0)) - 1.0)
```

#### 3.4 Star Override — NOT IMPLEMENTED

No `star_designated` field. No pregame star selection. No performance floor (`max(roll, player_rating - 10)`).

#### 3.5 Fatigue Tiers — PARTIAL

**Spec requires:** Three tiers: Elite (0.8x drain, 0.5 stat loss/point), Standard (1.0x, 1.0), Low (1.5x, 1.5).

**What exists:** Per-player fatigue (`game_engine.py:6042-6083`) with progressive drain by quarter and a cliff model. Drain is role-based and quarter-based, not talent-tiered. No Elite/Standard/Low classification.

#### 3.6 Hero Ball + Defensive Keying — NOT IMPLEMENTED

No `hero_ball_target`, no `consecutive_star_touches` tracking, no force-feeding logic, no keying counter-mechanic.

---

### Section 4: Composure System — NOT IMPLEMENTED

**Spec requires:** Per-team Composure (60-140 range), modified by pregame context and in-game events:
- Pregame: rivalry +15% variance, playoff +25%, trap game -15/+15
- In-game: turnover -8, TD +6/-4, failed conversion -10, etc.
- Tilt at < 70: Awareness -15%, Fumble Risk 1.2x, panic AI
- 5-point hysteresis for tilt exit (recover above 75)
- Underdog Surge: fatigue -15% for underdog leading in Q4

**What exists:**
- `composure` is a coaching staff attribute (`coaching.py:197`), not a per-game team variable
- `game_rhythm` (`game_engine.py:1916-1919`) is a pregame random Gaussian that doesn't shift during the game
- Rivalry applies flat stat boosts (`_apply_rivalry_boost`), not variance amplification
- No tilt, no hysteresis, no underdog surge, no composure timeline

---

### Section 5: Prestige Decision Matrix — PARTIAL (different design)

**Spec requires:** `aggression = base_aggression * energy_mod * delta_mod * composure_mod` with three outputs (HUNT_TD, SNAP_KICK, FIELD_GOAL). Prestige bravado tiers with Conference Culture differentiation.

**What exists:** `ai_coach.py` has an aggression system using 5 coaching templates with `base_aggression` values. Considers score delta and critical downs. Does NOT incorporate:
- Team prestige as base
- Composure modifier
- Three-output decision model
- Prestige bravado tiers (90+/70-89/<70)
- Conference culture differentiation
- Desperation override (< 2:00, delta > 9)

---

### Section 6: Prestige Decay — PARTIAL (different mechanism)

**Spec requires:** Per-game asymmetric prestige adjustment. Fast decay on losses, slow rebuild on wins. Streak modifiers. Season-end 20% regression toward mean.

**What exists:** `compute_team_prestige()` (`nil_system.py:463`) recalculates prestige once per offseason from cumulative historical record. No per-game adjustment, no asymmetric decay, no streak modifiers, no season-end regression.

---

### Section 7: Narrative Generation — NOT IMPLEMENTED

**Spec requires:** YAR (Yards Above Replacement), Headline Generator with composure-driven templates, Composure Graph UI.

**What exists:** Detailed box scores and EPA/OPI metrics, but no YAR, no headline templates, no composure timeline data.

---

### Section 9: Data Contracts — DIVERGENT

| Spec Field | Exists? | Location |
|---|---|---|
| `Player.archetype` (R/E/C enum) | No | Has position-based archetype string |
| `Player.star_designated` | No | — |
| `Player.speed/kicking/lateral/tackling` | Yes | `game_engine.py:560-564` |
| `Player.energy` | Yes (as `game_energy`) | `game_engine.py:643` |
| `Player.fatigue_tier` | No | — |
| `TeamGameState.composure` | No | — |
| `TeamGameState.is_tilted` | No | — |
| `TeamGameState.hero_ball_target` | No | — |
| `TeamGameState.consecutive_star_touches` | No | — |
| `TeamGameState.momentum_delta` | No | — |
| `TeamGameState.stars` | No | — |
| `GameContext.is_trap_game` | No | — |
| `GameContext.is_playoff` | Partial | Not passed to engine |
| `PostGameLog.composure_timeline` | No | — |
| `PostGameLog.yar_report` | No | — |
| `PostGameLog.tilt_triggered` | No | — |

---

## Architectural Observations

1. **The engine is V1.5, not V2.** It has rich player-level simulation, position archetypes, coaching AI, weather, and EPA metrics — but has not adopted the V2 layered architecture.

2. **Prestige is disconnected from the game engine.** Prestige affects recruiting, NIL, and matchup display but has zero effect on play resolution or in-game coaching decisions.

3. **The current archetype system is complementary, not conflicting.** The spec's R/E/C variance model could layer on top of the existing position archetypes without replacing them.

4. **Contest resolution is fundamentally different.** Additive sigmoid (current) vs. multiplicative power ratio (spec) is the deepest architectural change required.

5. **Composure is the largest missing subsystem.** Without it, upsets are random rather than narratively driven. The engine has `game_rhythm` as a rough static proxy.

---

## Recommended Implementation Sequence (per spec Section 8)

The spec prescribes a 10-phase build order. Based on what already exists:

1. **Phase 1 (Power Ratio):** Replace `_contest_run_yards` sigmoid with power-ratio formula
2. **Phase 2 (Fatigue Tiers):** Add Elite/Standard/Low classification to `drain_player_energy`
3. **Phase 3 (Archetypes):** Layer R/E/C variance model onto existing position archetypes
4. **Phase 4 (Star Override):** Add `star_designated` + performance floor
5. **Phase 5 (Halo + Star):** Wire prestige into engine; add halo resolution path
6. **Phase 6 (Hero Ball + Keying):** Both systems, shipped together
7. **Phase 7 (Composure):** Full dynamic composure system with tilt/surge
8. **Phase 8 (Decision Matrix):** Refactor `ai_coach.py` to be prestige-driven
9. **Phase 9 (Prestige Decay):** Per-game adjustments + season regression
10. **Phase 10 (Narrative):** YAR, headlines, composure graph
