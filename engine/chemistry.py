"""Team chemistry — composition math + generation (Phase 1).

Computes a `TeamChemistryState` from a roster + head coach. Chemistry is
read pregame and modulates `game_rhythm` (see `game_engine._kickoff`).

Layers:
- Stable attributes (voice/glue/pull/reach/drama_baseline/fit) live on Player.
- Permanent flags (franchise/big_stage/baggage) shape composition math.
- Coach archetype (chemistry_archetype, derived from classification) mediates
  drag and provides modifiers to drift in Phase 2.

The four outputs (tone, fabric, drag, tilt) all live on a 0-100 scale.
None of them dominates `game_rhythm` on its own — see `apply_chemistry_to_rhythm`.
"""

from __future__ import annotations

import random as _random_module
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from engine.game_engine import Player, Team, TeamChemistryState
    from engine.coaching import CoachCard


# ──────────────────────────────────────────────────────────────────────
# Player chemistry attribute generation
# ──────────────────────────────────────────────────────────────────────

# Distribution targets:
#   - Most players land in 40-60 current values (the unspectacular middle).
#   - ~10% have one stable attribute with ceiling 80+ (rare voices, high glue).
#   - ~5% have drama_baseline ceiling 75+ (the volatile ones).

_STABLE_ATTRS = ("voice", "glue", "pull", "reach")
_DRAMA_HIGH_CEILING_RATE = 0.05
_RARE_HIGH_CEILING_RATE = 0.10


def _roll_range(rng: "_random_module.Random", *, allow_high: bool = False) -> Tuple[int, int]:
    """Roll an innate range on the 25-95 scale.

    Range width is typically 30-50 points, anchored anywhere in the band.
    `allow_high` flags this attribute as one of the player's "high ceiling"
    attributes — ceiling lifts to 80-95.
    """
    width = rng.randint(30, 50)
    if allow_high:
        ceiling = rng.randint(80, 95)
    else:
        ceiling = rng.randint(60, 78)
    floor = max(25, ceiling - width)
    return (floor, ceiling)


def _roll_drama_range(rng: "_random_module.Random", *, allow_volatile: bool = False) -> Tuple[int, int]:
    """Drama ranges skew low — most players just aren't dramatic.

    A volatile player gets ceiling 75+ (the locker-room problem cases).
    """
    if allow_volatile:
        ceiling = rng.randint(75, 95)
        floor = max(25, ceiling - rng.randint(30, 50))
    else:
        ceiling = rng.randint(40, 60)
        floor = max(25, ceiling - rng.randint(15, 30))
    return (floor, ceiling)


def generate_chemistry_attributes(
    player: "Player",
    rng: Optional["_random_module.Random"] = None,
) -> None:
    """Roll innate ranges + initial current values for chemistry attrs.

    Called once at player creation. Mutates `player` in place. Idempotent
    re-calls would re-roll; only call on freshly generated players.
    """
    rng = rng or _random_module.Random()

    # Roll which attributes get high ceilings (~10% chance per attribute).
    # This is per-attribute, so a player could rarely get two high-ceiling traits.
    for attr in _STABLE_ATTRS:
        allow_high = rng.random() < _RARE_HIGH_CEILING_RATE
        rng_lo, rng_hi = _roll_range(rng, allow_high=allow_high)
        setattr(player, f"{attr}_range", (rng_lo, rng_hi))
        # Initial current value: uniformly in range, but biased toward middle.
        midpoint = (rng_lo + rng_hi) / 2
        spread = (rng_hi - rng_lo) / 2
        current = int(rng.gauss(midpoint, spread * 0.4))
        current = max(rng_lo, min(rng_hi, current))
        setattr(player, attr, current)

    # Drama gets its own roll — most players are in the low band.
    is_volatile = rng.random() < _DRAMA_HIGH_CEILING_RATE
    drama_lo, drama_hi = _roll_drama_range(rng, allow_volatile=is_volatile)
    player.drama_baseline_range = (drama_lo, drama_hi)
    drama_mid = (drama_lo + drama_hi) / 2
    drama_spread = (drama_hi - drama_lo) / 2
    drama_current = int(rng.gauss(drama_mid, drama_spread * 0.4))
    player.drama_baseline = max(drama_lo, min(drama_hi, drama_current))

    # Fit defaults to the middle of a generated range; gets recomputed
    # game-by-game in Phase 3. Range exists for future scheme-fit logic.
    fit_lo, fit_hi = _roll_range(rng, allow_high=False)
    player.fit_range = (fit_lo, fit_hi)
    fit_mid = (fit_lo + fit_hi) / 2
    player.fit = int(fit_mid)

    # Permanent flags always start False on freshly generated players.
    # They are earned in Phase 2; veteran imports may seed them post-hoc.
    player.franchise = False
    player.big_stage = False
    player.baggage = False


# ──────────────────────────────────────────────────────────────────────
# Playing-time weights
# ──────────────────────────────────────────────────────────────────────

_STARTER_WEIGHT = 1.0
_ROTATION_WEIGHT = 0.4
# When game_role has not been assigned, treat the top-N by overall as starters.
# 22 ≈ offense + defense first units.
_DEFAULT_STARTER_COUNT = 22


def playing_time_weighted_roster(team: "Team") -> List[Tuple["Player", float]]:
    """Return [(player, weight)] where weight is a proxy for chemistry voice.

    Uses `game_role` if set (post-pregame role assignment), otherwise falls
    back to overall-based starter identification.
    """
    players = list(team.players)
    if not players:
        return []

    has_role = any(getattr(p, "game_role", "ROTATION") == "STARTER" for p in players)
    if has_role:
        return [
            (p, _STARTER_WEIGHT if p.game_role == "STARTER" else _ROTATION_WEIGHT)
            for p in players
        ]

    ranked = sorted(players, key=lambda p: p.overall, reverse=True)
    starter_set = set(id(p) for p in ranked[:_DEFAULT_STARTER_COUNT])
    return [
        (p, _STARTER_WEIGHT if id(p) in starter_set else _ROTATION_WEIGHT)
        for p in players
    ]


# ──────────────────────────────────────────────────────────────────────
# Composition curves
# ──────────────────────────────────────────────────────────────────────

# Voice saturation: yield as a function of "effective voices" (count of
# voice >= 70 players, weighted by playing time). big_stage flag halves
# a player's contribution to saturation since they've proven they can
# play in stacked rooms.
#
# Tuning: 1 voice strongest, 2 still strong, 3 flat, 4+ declining.
def _voice_saturation_yield(effective_voices: float, glue_total: float) -> float:
    """Map effective voices → tone (0-100).

    A roster with NO loud voice still gets baseline tone (HC compensates a bit).
    Glue shifts the saturation *point* outward — high-glue rosters tolerate
    more voices before friction sets in — but does NOT pull rising-regime
    voice counts down. (Otherwise high glue would penalize quiet rooms.)
    """
    # Yield in the "rising regime" (0-2 voices): unaffected by glue shift.
    if effective_voices <= 0:
        return 45.0  # baseline — quiet room
    if effective_voices <= 1:
        return 45.0 + 30.0 * effective_voices  # 45 → 75
    if effective_voices <= 2:
        return 75.0 + 10.0 * (effective_voices - 1)  # 75 → 85

    # Saturation regime: glue extends tolerance.
    # +1 voice of headroom for every ~350 glue-points above 700 (avg-ish for 22 starters).
    glue_shift = max(0.0, (glue_total - 700.0) / 350.0)
    n = max(2.0, effective_voices - glue_shift)
    if n <= 3:
        return 85.0 - 2.0 * (n - 2)        # gentle dip 85 → 83
    if n <= 5:
        return 83.0 - 12.0 * (n - 3)       # declining: 83 → 59
    return max(35.0, 59.0 - 6.0 * (n - 5))


def _voice_saturation_curve(weighted: List[Tuple["Player", float]]) -> float:
    """Tone score: piecewise voice saturation with glue + big_stage modifiers."""
    if not weighted:
        return 50.0
    effective_voices = 0.0
    glue_total = 0.0
    for p, w in weighted:
        glue_total += p.glue * w
        if p.voice >= 70:
            # big_stage players count as 0.5 voices for saturation purposes —
            # they've proven they can play in voice-stacked rooms without friction.
            voice_weight = 0.5 if p.big_stage else 1.0
            effective_voices += voice_weight * w
    return _voice_saturation_yield(effective_voices, glue_total)


def _fabric(weighted: List[Tuple["Player", float]]) -> float:
    """Fabric: weighted Σ(glue × pull/100), franchise pull-multiplier, normalized.

    A roster of high-glue, high-pull players with one franchise icon hits
    ~80. A roster of low-glue, low-pull no-flag players hits ~30-40.
    """
    if not weighted:
        return 50.0
    raw = 0.0
    weight_total = 0.0
    for p, w in weighted:
        pull = p.pull * (1.3 if p.franchise else 1.0)
        raw += (p.glue * pull / 100.0) * w
        weight_total += w
    if weight_total == 0:
        return 50.0
    avg = raw / weight_total
    # avg is glue × pull / 100 ≈ 25-95 range maps to roughly the same scale.
    return max(0.0, min(100.0, avg))


def _drag(
    weighted: List[Tuple["Player", float]], hc: "CoachCard", glue_total: float
) -> float:
    """Drag: roster drama load, archetype-modulated, message-suppressed.

    Per drama-prone player (drama_baseline >= 60, OR baggage flag):
      raw_load = drama_val × weight × (1 + pull/100)
      protection = 60 / mean_team_glue   (>1 → low-glue room, <1 → high-glue)
      load = raw_load × protection × archetype_mod × franchise_mod
    HC `message` reduces sum multiplicatively.

    Calibration target:
      - 1 high-drama (80) under players_coach (good HC, glue=70) → drag ~15-25
      - 4 high-drama (80) on the same roster → drag ~55-80 (structural)
    """
    if not weighted:
        return 0.0
    archetype = hc.chemistry_archetype if hc is not None else "tactician"
    weight_total = sum(w for _, w in weighted) or 1.0
    mean_glue = max(25.0, glue_total / weight_total)
    protection = 60.0 / mean_glue  # 60 = neutral team glue

    raw = 0.0
    for p, w in weighted:
        is_dramatic = p.drama_baseline >= 60 or p.baggage
        if not is_dramatic:
            continue
        # Use baseline (Phase 1); Phase 3 swaps in drama_current.
        drama_val = p.drama_baseline
        if p.baggage:
            # Baggage adds a permanent +20 to drama contribution.
            drama_val = drama_val + 20
        load = drama_val * w * (1.0 + p.pull / 100.0) * protection

        # Archetype modifier — depends on whether the player's talent
        # justifies the drama (high overall = "earned it"; low = mismatch).
        talent_justifies = p.overall >= 80
        if archetype == "players_coach":
            load *= 0.7
        elif archetype == "disciplinarian":
            load *= 0.6 if talent_justifies else 1.2
        elif archetype == "mentor":
            load *= 0.85
        # tactician: 1.0 (no change)

        if p.franchise:
            load *= 0.5

        raw += load

    # `message` suppression: high-message coach (75+) cuts ~12-22%.
    if hc is not None:
        message_factor = 1.0 - max(0.0, (hc.message - 50)) * 0.005
        raw *= message_factor

    # Normalize so 1 high-drama player produces ~20 drag, 4 produces ~75.
    # Per-player raw under players_coach + message=60 + glue=70 + drama=80
    # is ~68 (drama_val × 1.5 × 0.857 × 0.7 × 0.95). 4× = 272. / 3.5 = 78.
    return max(0.0, min(100.0, raw / 3.5))


def _tilt(
    weighted: List[Tuple["Player", float]],
    hc: "CoachCard",
    fabric: float,
    franchise_count: int,
) -> float:
    """Tilt risk: high pull × high drama presence, suppressed by fabric/HC/franchise."""
    if not weighted:
        return 0.0
    risk = 0.0
    for p, w in weighted:
        if p.pull >= 70 and p.drama_baseline >= 60:
            risk += (p.pull / 100.0) * (p.drama_baseline / 100.0) * w * 35.0
    risk -= (fabric - 50.0) * 0.6
    if hc is not None:
        risk -= max(0.0, hc.message - 50) * 0.3
    risk -= franchise_count * 5.0
    return max(0.0, min(100.0, risk))


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────


def compute_chemistry(team: "Team", hc: "CoachCard | None") -> "TeamChemistryState":
    """Pregame chemistry snapshot. Sets `team.chemistry` and returns it."""
    from engine.game_engine import TeamChemistryState  # avoid circular import

    weighted = playing_time_weighted_roster(team)
    if not weighted:
        state = TeamChemistryState()
        team.chemistry = state
        return state

    glue_total = sum(p.glue * w for p, w in weighted)
    franchise_count = sum(1 for p, _ in weighted if p.franchise)

    tone = _voice_saturation_curve(weighted)
    fabric = _fabric(weighted)
    drag = _drag(weighted, hc, glue_total)
    tilt = _tilt(weighted, hc, fabric, franchise_count)

    state = TeamChemistryState(
        tone=tone,
        fabric=fabric,
        drag=drag,
        tilt=tilt,
        franchise_count=franchise_count,
    )
    team.chemistry = state
    return state


def apply_chemistry_to_rhythm(rhythm: float, state: "TeamChemistryState") -> float:
    """Apply chemistry modifiers to `game_rhythm` (capped at the system's 0.65-1.35).

    Each component is a small lever — chemistry is a modifier in normal play,
    not a determinant. (Phase 4 lifts spine into a major lever for adversity.)
    """
    rhythm += (state.fabric - 50.0) * 0.001     # ±5% max
    rhythm += (state.tone - 50.0) * 0.0005      # ±2.5% max
    rhythm -= state.drag * 0.001                # 0 → -10% max
    return max(0.65, min(1.35, rhythm))
