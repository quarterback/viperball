# AAR: Coaching Integration — FIV International + Pro League Fast Sim

**Date:** 2026-02-28
**Feature:** Wire coaching effects into international and pro league game modes
**Files Changed:** `engine/fiv.py`, `engine/fast_sim.py`
**Companion:** `docs/AAR_lead_management_countermeasures.md` (V2.7 countermeasure system)

---

## Problem Statement

After the V2.7 lead management countermeasure system was implemented, coaching effects (gameday modifiers, DC gameplan, lead management profiles) only activated in **college games**. The simulation has three tiers of competition, and two of them were completely unaffected:

| Tier | Engine | Coaching Before |
|---|---|---|
| **College** (season.py / dynasty.py) | Full ViperballEngine | Full coaching staffs passed as kwargs |
| **FIV International** (fiv.py) | Full ViperballEngine | Coaching staffs **generated but never used** |
| **Pro Leagues** (pro_league.py) | fast_sim statistical model | No coaching at all |

The FIV gap was especially frustrating: Phase 4 of international team building calls `generate_coaching_staff()` to create full 4-person staffs (HC, OC, DC, STC) with personality sliders, classifications, and all attributes. Then `_play_match()` creates a ViperballEngine and simply... doesn't pass them in. The coaches exist. They're just sitting in a drawer.

The pro league gap was structural: `fast_sim_game()` is a statistical model (~1-5ms per game vs ~1-3s for the full engine) designed for spectator-mode simulation. It has no coaching parameters at all. No CoachCard objects, no personality sliders, no gameday modifiers. Every air_raid team and every ground_pound team ran through the same scoring formula with the same variance.

---

## Fix 1: FIV International — Wire Existing Staffs Through

### The Data Loss Bug

The root cause was `_coach_to_dict()` in fiv.py. When coaching staffs were generated in Phase 4, this function serialized each CoachCard to a dict — but only stored 6 fields:

```python
# BEFORE — lost nearly everything
def _coach_to_dict(card) -> dict:
    return {
        "coach_id": card.coach_id,
        "first_name": card.first_name,
        "last_name": card.last_name,
        "role": card.role,
        "classification": card.classification,
        "overall": card.overall,
    }
```

The full CoachCard has ~30 fields including `instincts`, `leadership`, `composure`, `rotations`, `personality_sliders` (9 sliders), `hidden_traits`, `hc_affinity`, `sub_archetype`, and more. The coaching system needs all of these to compute gameday modifiers and lead management profiles. With only 6 fields stored, even if you passed the staffs to the engine, `CoachCard.from_dict()` would reconstruct a coach with default-zero values for everything that matters.

### The Fix

CoachCard already has a `to_dict()` method (coaching.py:641) that serializes every field, and a matching `from_dict()` class method that reconstructs the full object. The fix was one line:

```python
# AFTER — full serialization
def _coach_to_dict(card) -> dict:
    return card.to_dict()
```

### Passing Staffs to the Engine

With full data now preserved, `_play_match()` reconstructs CoachCard objects and passes them to ViperballEngine — matching exactly the pattern used by college games in season.py:

```python
coaching_kwargs: Dict[str, Any] = {}
try:
    from engine.coaching import CoachCard
    if home_team.coaching_staff:
        coaching_kwargs["home_coaching"] = {
            role: CoachCard.from_dict(card_data)
            for role, card_data in home_team.coaching_staff.items()
        }
    if away_team.coaching_staff:
        coaching_kwargs["away_coaching"] = {
            role: CoachCard.from_dict(card_data)
            for role, card_data in away_team.coaching_staff.items()
        }
except Exception:
    pass  # Graceful fallback: engine runs without coaching

engine = ViperballEngine(
    ...,
    **coaching_kwargs,
)
```

The `try/except` ensures that if coaching reconstruction fails for any reason, the game still runs — just without coaching effects, same as before.

### What FIV Gets Now

Everything. The full coaching pipeline activates automatically when `ViperballEngine.__init__()` receives coaching staffs:

- **Gameday modifiers** from `compute_gameday_modifiers()` — composure tracking, leadership effects, rotation quality
- **DC gameplan** from `roll_dc_gameplan()` — per-game defensive effectiveness
- **Lead management profiles** — the full V2.7 countermeasure system (Avalanche, Thermostat, Vault, Counterpunch, Slow Drip)
- **Halo system** — star player magnetism
- **Composure tracking** — tilt mechanics under pressure

International matches now have coaching identity. A Brazilian national team with a Motivator HC (high aggression, high chaos) will play Avalanche football — keep scoring even when the Delta Yards penalty is crushing them. A German national team with a Disciplinarian HC (high composure, high rotations) will play Vault — grind the clock and trust the defense. This diversity emerges automatically from the coaching staffs that were already being generated but never used.

---

## Fix 2: Pro League Fast Sim — Coaching Flavor Without Named Coaches

Pro leagues are "spectator-only" — no management, no coaching hires, no roster moves. Teams don't have named CoachCard objects. Switching pro games to the full ViperballEngine would cost ~1000x in performance (5-17 minutes to simulate one week across all leagues vs ~4 seconds today). That's not viable.

Instead, the fast sim now derives coaching-like personality effects from what pro teams already have: **offense_style**, **defense_style**, and **prestige**.

### COACHING_FLAVOR Table

Maps offense style to a `(points_mult, variance_mult)` pair:

```python
COACHING_FLAVOR = {
    # Explosive / aggressive styles → higher ceiling, wilder swings
    "air_raid":       (1.08, 1.30),
    "lateral_chaos":  (1.06, 1.35),
    "tempo":          (1.07, 1.20),
    "power_spread":   (1.04, 1.10),
    # Grinding / conservative styles → lower scoring, tighter outcomes
    "ground_pound":   (0.93, 0.75),
    "smashmouth":     (0.91, 0.70),
    "triple_option":  (0.95, 0.80),
    # Balanced / methodical → close to neutral, slightly tighter
    "balanced":       (1.00, 0.90),
    "west_coast":     (1.03, 0.95),
}
```

An air_raid team's expected points get multiplied by 1.08 (8% scoring boost) with a 1.30 variance multiplier — they'll have higher highs and lower lows. A smashmouth team gets 0.91 (9% scoring reduction) with 0.70 variance — they grind out tight games. The gap between the most explosive and most conservative styles is 17 percentage points of base scoring (0.91 to 1.08), which is significant across a season.

### DEFENSE_COACHING_FLAVOR Table

Defense style shifts the team's scoring envelope:

```python
DEFENSE_COACHING_FLAVOR = {
    "swarm":         0.00,
    "bend_no_break": 0.03,
    "blitz_heavy":  -0.05,
    "zone":          0.02,
    "man_press":    -0.03,
}
```

The logic: a blitz-heavy defensive philosophy correlates with aggressive coaching overall, which pushes the offense harder too. The sign is inverted (`pts_mult -= def_shift`), so blitz_heavy (-0.05) adds +0.05 to the scoring multiplier. A team with `air_raid + blitz_heavy` gets a 1.13x base multiplier — the most explosive combination in the league.

### Prestige Amplification

Prestige doesn't just add a flat bonus. It amplifies the gap between styles:

```python
prestige_factor = (prestige - 50) / 200.0  # -0.25 to +0.25
pts_mult += prestige_factor * abs(pts_mult - 1.0) * 1.5
```

An elite (prestige 90) air_raid team: the 1.08 base gets pushed further above 1.0. A weak (prestige 25) smashmouth team: the 0.91 base gets pushed further below 1.0. High-prestige teams also get tighter variance (0.85x multiplier on variance), making them more consistent game-to-game. Low-prestige teams get wilder variance (1.20x), creating more upset potential.

### Final Range

After all factors, the coaching flavor multiplier is clamped to **0.80 - 1.20** — a 40-percentage-point spread. Combined with the existing variance model (0.50-1.50 base), weather, rivalry, and home field modifiers, this creates meaningful differentiation between pro teams based on their identity.

### Application Point

Applied immediately after `_expected_points()`, before weather/rivalry modifiers:

```python
home_expected = _expected_points(home_str, away_def, rng)
away_expected = _expected_points(away_str, home_def, rng)

# V2.7: Coaching flavor — style/prestige → scoring personality
home_expected *= _coaching_flavor(home_team, rng)
away_expected *= _coaching_flavor(away_team, rng)
```

Computation overhead: <1ms. No CoachCard objects, no personality slider lookups, no profile derivation. Just table lookups and arithmetic.

---

## Design Decisions

**Why full coaching for FIV but lightweight for pro?** Two reasons. First, FIV already runs the full ViperballEngine — the coaching system plugs in with zero performance cost. The staffs were already being generated. There was no reason not to pass them through. Second, pro leagues use fast_sim for performance. The full coaching pipeline (personality sliders, sensitivity ramps, countermeasure blending) requires play-by-play decisions that fast_sim doesn't make. The statistical model operates at the game-result level, not the play level.

**Why no named coaches for pro?** Pro leagues are explicitly "spectator-only: no management, no coaching hires, no roster moves." Adding named coaches would create expectations around coaching hires, firings, contract management, and portal — none of which exist for pro leagues. The coaching flavor approach gives pro teams scoring personality without creating features that don't exist yet.

**Why 0.80-1.20 instead of a narrower range?** With 200+ teams, narrow ranges make everyone feel the same. A 1.02-1.05 spread would be invisible in the noise of the existing 0.50-1.50 variance multiplier. The 0.80-1.20 range means that across a 16-game season, an air_raid team will score meaningfully more than a smashmouth team on average — and the season standings will reflect coaching philosophy, not just roster strength.

**Why include defense_style in the scoring multiplier?** Coaching philosophy is holistic. A team that runs blitz_heavy defense and air_raid offense has an aggressive, high-risk identity top to bottom. Treating offense and defense styles as independent would miss this correlation. The defense_style shift is small (max 0.05), but it distinguishes teams with coherent aggressive identities from teams with mixed philosophies.

---

## Three-Tier Coaching Summary

| Tier | Engine | Coaching System | Lead Management | Performance |
|---|---|---|---|---|
| **College** | Full ViperballEngine | Full CoachCard staffs, gameday modifiers, DC gameplan | Full V2.7 countermeasures (5 tendencies, continuous ramp) | ~1-3s/game |
| **FIV International** | Full ViperballEngine | Full CoachCard staffs (now wired through) | Full V2.7 countermeasures | ~1-3s/game |
| **Pro Leagues** | fast_sim statistical | Coaching flavor from team identity (no named coaches) | Not applicable (no play-by-play) | ~1-5ms/game |

College and FIV now have identical coaching depth. A World Cup match between two national teams will show the same coaching diversity as a college rivalry game — different lead management philosophies, different tempo decisions, different formation tendencies. Pro leagues get style-based scoring personality that makes air_raid teams feel different from smashmouth teams across a season, without sacrificing the performance that makes spectator-mode simulation instant.

---

## What This Enables

- **FIV World Cup narratives**: International matches now have coaching matchups. A Counterpunch coach vs a Vault coach in the World Cup semifinal creates a legible tactical storyline.
- **Pro league style identity**: An air_raid pro team will have higher-scoring, wilder games across a season. A smashmouth team will grind out 14-12 outcomes. Season stats will reflect coaching philosophy.
- **Full-stack coaching**: The coaching system now touches every game mode in the simulation. No team anywhere in the 200+ team ecosystem plays uncoached football.
- **Future extensibility**: If pro leagues ever add management features (coaching hires, etc.), the fast_sim function already accepts the patterns — the coaching flavor can be replaced or augmented with full CoachCard integration without changing the call site.
