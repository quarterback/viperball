"""Punting: who punts well, the kinds of punts, and when a coach punts.

Punting skill
    Every player has a punting profile built from their kick ratings plus a
    personal knack that their kick ratings don't capture. Kicking is a skill
    every position uses in Viperball, so good punters turn up all over a
    roster, and a few players are natural punters well above their goal
    kicking. A profile has two parts: distance (how far and how high) and
    placement (where it lands and how it stops), and a style:
      aussie       the drop punt and the rugby roll out
      continental  the North American spiral
      both         a rare punter who does both well

Punt types
    spiral   distance and hang. Best from deep in your own end. From closer
             in it is aimed at the end zone for a pindown.
    drop     the end over end drop punt. Shorter, but placed: aimed to land
             inside the 10 and stop there with backspin. Hard to return.
    rugby    the roll out: the punter runs toward a sideline and kicks low
             and end over end so it bounces forward. Hard to block, hard to
             field, and the coverage arrives with it.
    quick    a surprise punt on 5th down with no returner back. Rolls far
             and is rarely returned.
    rouge    the last play of a half out of kick range: a spiral aimed at
             the end zone for a pindown.
    corner   the Corner Chase package (offensive_concepts.CORNER_CHASE).

When to punt
    A punt is a 6th down play. Coaches weigh it against going for it and
    against a kick, using what drives are worth from each spot in this
    engine (DRIVE_VALUE). Each head coach also has a punting philosophy from
    -1 (never punts, in the manner of Kevin Kelley at Pulaski Academy) to +1
    (field position first, in the manner of Jim Tressel at Ohio State), which
    adds to or takes from the punt's value. A punt before 6th down happens
    only as a quick kick in a few extreme spots (see quick_kick_spot).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from engine.stable_hash import stable_hash

# Points an offense scores on a drive that starts at each yard line, fitted
# from 400 engine games (November 28, 2026). Field position is cheaper here
# than in football because offenses score kicks from most of the field.
DRIVE_VALUE = {
    0: 2.21, 5: 2.47, 10: 2.72, 15: 2.76, 20: 2.96, 25: 3.06, 30: 3.15,
    35: 3.23, 40: 3.33, 45: 3.45, 50: 3.90, 55: 4.23, 60: 4.74, 65: 4.57,
    70: 4.63, 75: 5.03, 80: 5.10, 85: 6.89, 90: 7.21, 95: 7.93,
}


def drive_value(yard: float) -> float:
    yard = max(0.0, min(99.0, yard))
    lo = int(yard // 5) * 5
    hi = min(95, lo + 5)
    if hi == lo:
        return DRIVE_VALUE[lo]
    frac = (yard - lo) / 5.0
    return DRIVE_VALUE[lo] + frac * (DRIVE_VALUE[hi] - DRIVE_VALUE[lo])


def sixth_down_conversion(ytg: int) -> float:
    """How often a 6th down try gains the first down in this engine."""
    if ytg <= 1:
        return 0.47
    if ytg <= 3:
        return 0.33
    if ytg < 20:
        return 0.28
    return 0.10


# ── Punting skill ─────────────────────────────────────────────────────

@dataclass
class PuntProfile:
    distance: int
    placement: int
    rating: int
    style: str  # "aussie" | "continental" | "both"


def _unit(seed: int, salt: str) -> float:
    return (stable_hash(f"{seed}:{salt}") % 10000) / 10000.0


def _bell(seed: int, salt: str) -> float:
    """Roughly normal, mean 0, sd about 1, the same every run."""
    return (sum(_unit(seed, f"{salt}{i}") for i in range(4)) - 2.0) / 0.577


def punter_profile(player) -> PuntProfile:
    seed = stable_hash(f"{getattr(player, 'name', '')}|{getattr(player, 'player_id', '')}")
    power = getattr(player, "kick_power", 70)
    accuracy = getattr(player, "kick_accuracy", 70)
    kicking = getattr(player, "kicking", 70)
    knack = 6.5 * _bell(seed, "knack")
    # About one player in twelve is a natural punter.
    if _unit(seed, "natural") < 0.08:
        knack += 8.0
    distance = 0.55 * power + 0.30 * kicking + 0.15 * getattr(player, "power", 70) + knack + 4 * _bell(seed, "d")
    placement = 0.55 * accuracy + 0.25 * kicking + 0.20 * getattr(player, "awareness", 70) + knack + 4 * _bell(seed, "p")
    distance = int(max(25, min(99, round(distance))))
    placement = int(max(25, min(99, round(placement))))
    roll = _unit(seed, "style")
    style = "both" if roll < 0.10 and distance + placement >= 160 else ("aussie" if roll < 0.55 else "continental")
    return PuntProfile(distance, placement, int(round((distance + placement) / 2)), style)


def kick_scale(rating: float) -> float:
    """A rating on the scale the kick formulas use, as the engine's
    _kick_skill does: a 35 kicks like a 70, a 79 like a 92."""
    return max(40.0, min(100.0, 60.0 + (rating - 15.0) * 0.5))


def best_punter(players):
    """The best punter among these players, with their profile."""
    best, best_profile = None, None
    for p in players:
        prof = punter_profile(p)
        if best_profile is None or prof.rating > best_profile.rating:
            best, best_profile = p, prof
    return best, best_profile


# ── Punt types ────────────────────────────────────────────────────────

TYPE_LABELS = {"spiral": "spiral", "drop": "drop punt", "rugby": "rugby punt",
               "quick": "quick kick", "corner": "corner punt",
               "rouge": "punt for a pindown"}

# How each type changes the return, the muff chance and the block chance.
RETURN_MULT = {"spiral": 1.00, "drop": 0.45, "rugby": 0.40, "quick": 0.10, "corner": 0.80,
               "rouge": 1.00}
MUFF_MULT = {"spiral": 1.00, "drop": 0.85, "rugby": 1.60, "quick": 1.30, "corner": 1.00,
             "rouge": 1.00}
BLOCK_MULT = {"spiral": 1.00, "drop": 1.00, "rugby": 0.45, "quick": 0.60, "corner": 1.00,
              "rouge": 1.00}


def choose_type(fp: int, prof: PuntProfile, tailwind: float = 0.0, kick_rush: float = 1.0,
                rng=random) -> str:
    """The punt this punter calls from this spot.

    Deep in your own end the job is distance. Past midfield the job is to
    pin: an aussie punter drops it inside the 10; a continental punter
    boots it at the end zone for a pindown. A heavy kick rush or a wind in
    the punter's face brings out the low rugby punt.
    """
    aussie = prof.style in ("aussie", "both")
    continental = prof.style in ("continental", "both")
    if (kick_rush > 1.15 or tailwind <= -12) and aussie:
        return "rugby"
    if fp >= 55:
        return "drop" if aussie else "spiral"
    if not aussie:
        return "spiral"
    roll = rng.random()
    if fp >= 40:
        # Midfield: an aussie punter mixes the drop punt, the roll out and
        # the long torpedo spiral.
        return "drop" if roll < 0.40 else ("rugby" if roll < 0.75 else "spiral")
    if continental:
        return "spiral" if roll < 0.6 else "rugby"
    return "rugby" if roll < 0.55 else "spiral"


def sample_punt(fp: int, prof: PuntProfile, kind: str, weather_mod: float = 1.0,
                rng=random) -> dict:
    """How far the punt goes, in yards from the line of scrimmage.

    Returns {"distance": yards, "stopped": bool}. "stopped" means a drop
    punt that would have reached the end zone checked up short of it.
    """
    to_goal = 100 - fp
    dist_skill = (kick_scale(prof.distance) - 85.0) / 10.0
    place_skill = (kick_scale(prof.placement) - 85.0) / 10.0
    stopped = False
    if kind == "rouge":
        d = min(rng.gauss(to_goal + 6, 6), rng.gauss(62 + 9 * dist_skill, 6)) * weather_mod
    elif kind == "spiral":
        if fp >= 50:
            # Aimed at the end zone for the pindown.
            d = rng.gauss(to_goal + 4, 7 - 2 * place_skill)
        else:
            d = rng.gauss(60 + 8 * dist_skill, 9)
        d *= weather_mod
    elif kind == "drop":
        target = to_goal - 7          # land around the 7
        error = max(2.5, 7.0 - 3.0 * place_skill)
        d = min(rng.gauss(target, error), 46 + 6 * dist_skill)
        if d >= to_goal:
            # Backspin: a good drop punt checks up before the goal line.
            if rng.random() < 0.45 + 0.35 * max(0.0, place_skill):
                d = to_goal - rng.uniform(1, 4)
                stopped = True
        d *= max(0.85, weather_mod)
    elif kind == "rugby":
        carry = rng.gauss(38 + 5 * dist_skill, 6)
        roll = rng.uniform(0, 24)
        d = (carry + roll) * max(0.9, weather_mod)
    elif kind == "quick":
        d = rng.gauss(40 + 4 * dist_skill, 7) + rng.uniform(8, 22)
    else:
        d = rng.gauss(min(to_goal, 50 + 6 * dist_skill), 8) * weather_mod
    return {"distance": int(max(8, round(d))), "stopped": stopped}


def expected_opponent_spot(fp: int, prof: PuntProfile, kind: str) -> tuple:
    """Where the receiving team should start, from its own goal line, and
    the chance of a pindown, for a coach weighing the punt.

    Averages over the punt's spread so a coach sees the same odds the play
    will produce.
    """
    rng = random.Random(stable_hash(f"{fp}:{prof.distance}:{prof.placement}:{kind}"))
    base_return = {"spiral": 9.0, "drop": 4.0, "rugby": 3.5, "quick": 1.0, "corner": 5.0,
                   "rouge": 9.0}[kind]
    spots, pins = [], 0.0
    for _ in range(40):
        d = sample_punt(fp, prof, kind, 1.0, rng)["distance"]
        land = fp + d
        if land >= 100:
            pins += 0.12
            spots.append(20.0)
        else:
            spots.append(max(1.0, 100 - land + base_return))
    return sum(spots) / len(spots), pins / 40


# ── When to punt ──────────────────────────────────────────────────────

def philosophy(mods: Optional[dict], punt_aggression: float = 1.0,
               field_position_priority: float = 0.5) -> float:
    """A head coach's punting philosophy, -1 (never punts) to +1 (field
    position first). Most coaches sit a little above zero: they punt by the
    book, more often than the numbers alone would say."""
    mods = mods or {}
    traits = mods.get("hidden_trait_effects") or {}
    mult = traits.get("punt_weight_multiplier", 1.0)
    if mult <= 0.6:
        return -1.0          # Punt Hater
    if mult >= 1.4:
        return 1.0           # Field Position Purist
    value = 0.45
    late = (mods.get("personality_factors") or {}).get("late_down_aggression")
    if late is not None:
        # Personality factors run 0.75 to 1.25.
        value -= (late - 1.0) * 2.4
    if mods.get("hc_classification") == "special_teams_guru":
        value += 0.25
    value += (punt_aggression - 1.0) * 1.5 + (field_position_priority - 0.5)
    return max(-0.95, min(0.95, value))


def philosophy_for_coach(card) -> float:
    """The punting philosophy a head coach card brings to a game."""
    from engine.coaching import HIDDEN_TRAIT_EFFECTS
    traits = {}
    for trait in getattr(card, "hidden_traits", []) or []:
        for key, val in HIDDEN_TRAIT_EFFECTS.get(trait, {}).items():
            traits[key] = traits.get(key, 1.0) * val
    sliders = getattr(card, "personality_sliders", {}) or {}
    mods = {"hidden_trait_effects": traits,
            "hc_classification": getattr(card, "classification", "")}
    if "late_down_aggression" in sliders:
        mods["personality_factors"] = {
            "late_down_aggression": 1.0 + (sliders["late_down_aggression"] - 50) / 200.0}
    return philosophy(mods)


def philosophy_label(value: float) -> str:
    if value <= -0.95:
        return "Never punts"
    if value < 0.0:
        return "Rarely punts"
    if value < 0.6:
        return "Punts by the book"
    if value < 0.99:
        return "Leans on field position"
    return "Field position first"


def punt_bias(value: float) -> float:
    """Points the philosophy adds to a punt's value on 6th down."""
    return 1.6 * value


def quick_kick_spot(down: int, fp: int, ytg: int, quarter: int, time_left: int,
                    score_diff: int, tailwind: float, wind_turns: bool,
                    philosophy_value: float) -> Optional[str]:
    """The few spots where a punt before 6th down makes sense.

    Returns a reason or None.
      protect_lead   5th and long deep in your own end, leading late in the
                     game: flip the field before the defense sets a returner.
      wind           5th and long in your own half with a strong wind at your
                     back in the last 30 seconds of a quarter; the teams
                     change ends at the break and the wind turns against you.
    A coach who never punts never quick kicks.
    """
    if down != 5 or philosophy_value <= -0.95 or ytg < 10:
        return None
    if quarter == 4 and 60 <= time_left <= 300 and score_diff > 0 and fp <= 30:
        return "protect_lead"
    if wind_turns and tailwind >= 12 and fp <= 50 and time_left <= 30:
        return "wind"
    return None
