"""Field width: where the ball sits across the field and who covers each side.

The engine tracks the yard line on its own. This module adds the other axis.

Coordinates are yards across the field from the offense's left sideline:
0 is the left sideline, FIELD_WIDTH is the right sideline. When possession
changes the spot is mirrored, so the numbers always read from the side
that has the ball.

Each snap is spotted between the hashes. A ball downed outside a hash is
spotted on that hash, per the rules. From the left hash the left side of
the field is the short side (boundary) and the right side is the wide side
(field side).

The defense splits into three channels at the snap: left, box and right.
Three linemen hold the box, the two end linemen each hold an edge, and the
midfielders and keepers are split between the two sides by the defensive
coordinator. A good coordinator matches the split to the room on each side.
A weaker one leaves a side short. The offense reads the split and picks a
side. Room helps the offense, extra defenders hurt it, and the two can
cancel when the defense shades correctly.
"""

from __future__ import annotations

import random
from typing import Dict, Iterable, List, Optional, Tuple

FIELD_WIDTH = 160 / 3          # 53 1/3 yards
HASH_FROM_SIDELINE = 20.0      # NCAA hash spacing
LEFT_HASH = HASH_FROM_SIDELINE
RIGHT_HASH = FIELD_WIDTH - HASH_FROM_SIDELINE
MIDDLE = FIELD_WIDTH / 2

# Effect sizes. Kept modest: this changes where plays go and who makes
# the tackle more than it changes how many yards the league gains.
ROOM_EFFECT = 0.30             # yards multiplier swing per half field of room
NUMBERS_EFFECT = 0.12          # per defender above or below a fair share
SIDE_WEIGHT_IN_CHANNEL = 2.0   # tackler pick weight for a defender in the attacked channel
SIDE_WEIGHT_BOX = 1.0          # inside defenders pursue
SIDE_WEIGHT_FAR = 0.45         # backside defenders rarely make the play

EDGE_FAMILIES = ("sweep_option", "speed_option", "viper_jet")
INSIDE_FAMILIES = ("dive_option", "power", "draw")


def snap_spot(x: float) -> float:
    """Where the next snap is spotted: between the hashes."""
    return max(LEFT_HASH, min(RIGHT_HASH, x))


def mirror(x: float) -> float:
    return FIELD_WIDTH - x


def room(x: float, side: str) -> float:
    if side == "left":
        return x
    if side == "right":
        return FIELD_WIDTH - x
    return MIDDLE


def side_label(x: float, side: str) -> str:
    """Field side, boundary or middle, for a play attacking `side` from `x`."""
    if side not in ("left", "right"):
        return "middle"
    other = "right" if side == "left" else "left"
    gap = room(x, side) - room(x, other)
    if abs(gap) < 1.0:
        return "middle"
    return "field" if gap > 0 else "boundary"


def hash_label(x: float) -> str:
    x = snap_spot(x)
    if x <= LEFT_HASH + 0.5:
        return "left_hash"
    if x >= RIGHT_HASH - 0.5:
        return "right_hash"
    return "middle"


def room_mod(x: float, side: str) -> float:
    return (room(x, side) - MIDDLE) / MIDDLE * ROOM_EFFECT


# ── Defense ───────────────────────────────────────────────────────────

def _box_size(alignment: str, linemen: int) -> int:
    base = max(0, linemen - 2)
    if alignment == "stacked":
        return base + 1
    if alignment == "aggressive":
        return base + 1
    if alignment == "spread":
        return max(0, base - 1)
    return base


def assign_channels(lineup: Iterable[Tuple[object, str]], x: float, alignment: str,
                    dc_quality: float, rng=random) -> Dict:
    """Place each defender in a channel for this snap.

    lineup: (player, role) pairs for the defense on the field.
    dc_quality: 0 to 1, the defensive coordinator's read.
    Returns {"by_id": {id(player): channel}, "counts": {...}, "perimeter": n,
             "fair": {"left": f, "right": f}}.
    """
    lineup = list(lineup)
    linemen = [p for p, role in lineup if role == "Defensive Line"]
    others = [p for p, role in lineup if role != "Defensive Line"]
    box_n = min(len(linemen) + len(others), _box_size(alignment, len(linemen)))
    by_id: Dict[int, str] = {}

    # Inside linemen take the box; the two outside linemen set the edges.
    inside = linemen[1:-1] if len(linemen) > 2 else []
    ends = [linemen[0], linemen[-1]] if len(linemen) >= 2 else linemen[:]
    perimeter = list(others)
    box: List[object] = list(inside)
    while len(box) > box_n and box:
        perimeter.append(box.pop())
    while len(box) < box_n and perimeter:
        # A stacked or pressing front brings a midfielder down into the box.
        box.append(perimeter.pop())
    for p in box:
        by_id[id(p)] = "box"

    # Fair share of the perimeter is the share of room on each side.
    n = len(perimeter) + len(ends)
    share_left = room(x, "left") / FIELD_WIDTH
    fair = {"left": n * share_left, "right": n * (1 - share_left)}
    ends_left = 1 if len(ends) >= 1 else 0
    ends_right = len(ends) - ends_left

    def values(k_left: int) -> Tuple[float, float]:
        left = ends_left + k_left
        right = ends_right + (len(perimeter) - k_left)
        vl = room_mod(x, "left") + NUMBERS_EFFECT * (fair["left"] - left)
        vr = room_mod(x, "right") + NUMBERS_EFFECT * (fair["right"] - right)
        return vl, vr

    # The best split leaves the offense the least to gain on either side.
    options = range(len(perimeter) + 1)
    best = min(options, key=lambda k: (max(values(k)), abs(k - len(perimeter) * share_left)))
    # A weaker read misses by a player one way or the other.
    miss = max(0.0, 1.0 - dc_quality) * 0.55
    if perimeter and rng.random() < miss:
        best = max(0, min(len(perimeter), best + rng.choice((-1, 1))))

    # Fastest perimeter defenders go to the wide side.
    perimeter.sort(key=lambda p: -getattr(p, "speed", 70))
    wide = "right" if room(x, "right") >= room(x, "left") else "left"
    k_wide = (len(perimeter) - best) if wide == "right" else best
    for i, p in enumerate(perimeter):
        by_id[id(p)] = wide if i < k_wide else ("left" if wide == "right" else "right")
    if ends:
        by_id[id(ends[0])] = "left"
        if len(ends) > 1:
            by_id[id(ends[1])] = "right"

    counts = {"left": 0, "box": 0, "right": 0}
    for ch in by_id.values():
        counts[ch] += 1
    vl, vr = values(best)
    return {"by_id": by_id, "counts": counts, "fair": fair,
            "value": {"left": round(vl, 4), "right": round(vr, 4)}}


def side_value(channels: Dict, side: str) -> float:
    if side not in ("left", "right"):
        return 0.0
    return channels["value"][side]


def choose_side(channels: Dict, oc_quality: float, rng=random, planned: Optional[str] = None,
                counter: bool = False, x: Optional[float] = None) -> str:
    """Offense picks a side.

    A planned lane wins. Otherwise coaches lean to the wide side, where a
    play has room to break, and away from a side the defense loaded. The
    better the coordinator's read, the more the defense's split decides it.
    A counter or reverse goes back to the side the defense left lighter.
    """
    if planned in ("left", "right"):
        return planned
    vl, vr = channels["value"]["left"], channels["value"]["right"]
    read = 0.4 + 0.6 * max(0.0, min(1.0, oc_quality))
    lean = max(-1.0, min(1.0, (vl - vr) / 0.05)) * read
    if counter:
        p_left = 0.5 + 0.40 * lean
    else:
        wide = 0.0
        if x is not None and abs(room(x, "left") - room(x, "right")) >= 1.0:
            wide = 0.14 if room(x, "left") > room(x, "right") else -0.14
        p_left = 0.5 + 0.30 * lean + wide
    p_left = max(0.05, min(0.95, p_left))
    return "left" if rng.random() < p_left else "right"


def pressed(channels: Dict, side: str) -> bool:
    """The defense put more than its fair share on this side."""
    if side not in ("left", "right"):
        return False
    return channels["counts"][side] > channels["fair"][side] + 0.5


# ── Where the play ends ───────────────────────────────────────────────

SCORE_RESULTS = ("touchdown", "successful_kick", "safety", "pindown", "punt_return_td",
                 "int_return_td", "missed_dk_return_td")


def end_spot(x0: float, ctx: Optional[Dict], play, rng=random) -> Tuple[float, bool]:
    """Where the ball ended, across the field, from the snapping offense's view.

    Returns (x, out_of_bounds). The caller mirrors the spot when possession
    changed and resets it on restarts.
    """
    ptype = getattr(play, "play_type", "") or ""
    family = getattr(play, "play_family", "") or ""
    result = getattr(play, "result", "") or ""
    yards = getattr(play, "yards_gained", 0) or 0
    pen = getattr(play, "penalty", None)
    if ptype in ("penalty", "kneel") or (pen is not None and getattr(pen, "nullified", False)):
        return x0, False
    side = (ctx or {}).get("side", "middle")
    sign = -1 if side == "left" else 1 if side == "right" else 0
    space = room(x0, side) if sign else MIDDLE

    if ptype == "fake_punt":
        return _land(x0 + rng.uniform(-10, 10), ctx, play, rng)
    if ptype == "punt" or family == "punt":
        st = getattr(play, "special_teams_event", None) or {}
        if st.get("placement") == "corner":
            return (rng.uniform(3, 9) if rng.random() < 0.5 else FIELD_WIDTH - rng.uniform(3, 9)), False
        return rng.uniform(12, FIELD_WIDTH - 12), False
    if ptype in ("drop_kick", "place_kick"):
        return rng.uniform(15, FIELD_WIDTH - 15), False
    if ptype == "kick_pass":
        if result in ("kick_pass_incomplete", "incomplete"):
            return x0, False
        sub = getattr(play, "kick_pass_subfamily", "") or ""
        lo, hi = {"quick_kick": (3, 11), "kick_lateral": (4, 13), "territory": (5, 16),
                  "bomb": (4, 18)}.get(sub, (4, 12))
        x = x0 + sign * rng.uniform(lo, hi) + rng.uniform(-3, 3)
        if sign == 0:
            x = x0 + rng.uniform(-8, 8)
        if result in ("kick_pass_intercepted", "lateral_intercepted", "int_return_td"):
            return max(1.0, min(FIELD_WIDTH - 1, x)), False
        # Run after catch keeps going away from the middle a little.
        x += sign * rng.uniform(0, 4)
        return _land(x, ctx, play, rng)
    if ptype == "lateral_chain" or family == "lateral_spread":
        laterals = getattr(play, "laterals", 0) or 2
        travel = (ctx or {}).get("lateral_travel") or laterals * rng.uniform(4, 7)
        x = x0 + (sign or rng.choice((-1, 1))) * travel
        return _land(x, ctx, play, rng)
    if family in EDGE_FAMILIES:
        travel = rng.uniform(7, 14) + max(0, yards) * 0.35
        return _land(x0 + sign * travel, ctx, play, rng)
    if family == "counter":
        travel = rng.uniform(4, 10) + max(0, yards) * 0.25
        return _land(x0 + sign * travel, ctx, play, rng)
    if family == "trick_play":
        travel = rng.uniform(3, 15)
        return _land(x0 + (sign or rng.choice((-1, 1))) * travel, ctx, play, rng)
    # Inside runs and anything else: a few yards either way, more on long runs.
    drift = rng.uniform(-3, 3) + (sign * max(0, yards) * 0.2 if sign else rng.uniform(-1, 1) * max(0, yards) * 0.2)
    return _land(x0 + drift, ctx, play, rng)


def _land(x: float, ctx, play, rng) -> Tuple[float, bool]:
    """Clamp to the field. A carrier who reaches the sideline is often
    pushed out, which matters for the clock late in a half."""
    result = getattr(play, "result", "") or ""
    if getattr(play, "fumble", False) or result in SCORE_RESULTS:
        return max(1.0, min(FIELD_WIDTH - 1, x)), False
    if x <= 1.0 or x >= FIELD_WIDTH - 1.0:
        out = rng.random() < 0.60
        return (0.0 if x <= 1.0 else FIELD_WIDTH), out
    return x, False
