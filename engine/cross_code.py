"""Cross code concepts: the rest of the master clinic's books and defenses.

docs/master_coaching_clinic_cross_code_2026-11-27.md lists five offensive
books and eight defensive answers. Cape Cod, the clinic phase 1 concepts and
the five cross code packages already built cover part of them. This module
holds the rest:

Free Motion   FM01 Switchback, FM02 Twin Trigger, FM03 False Lead,
              FM05 Anchor Release, FM06 Mirror Flood
Phase Attack  PH03 Pullback, PH05 Short Side Strike
Relay         RL01 Wall Return, RL02 Up Back Across, RL05 Safe Outlet
Crossfire     CF01 Slip Cross, CF02 Pivot Turn, CF03 Double Clear,
              CF04 Handoff Punish, CF05 Same Look Reverse
Defense       D01 Exchange, D02 Stagger, D03 Edge Anchor, D04 Slide and
              Replace, D05 Channel Press, D06 Transition Net, D07 Cross Rush,
              D08 Set Breaker

How an offensive call runs. The caller picks the package before the snap
(team_installation.choose_offensive_package). After the defense sets, the
engine builds a look from what the offense can see (the front, the split of
defenders across the field, a blitz the Zeroback may or may not recognize)
and, for the calls that read a post snap contest, the result of that contest
between the actual players (a cross the defense may or may not switch, a
defender who may or may not commit). design() turns the look into the call:
the play family, the side, and which players carry, kick or receive. The
existing resolvers then play it out with the players' own ratings.

Nothing here grants yards. A branch only decides who has the ball, where it
goes and which defender is out of position; the normal contests decide the
result.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional

# ── Offense ──
FM_SWITCHBACK = "fm_switchback"
FM_TWIN_TRIGGER = "fm_twin_trigger"
FM_FALSE_LEAD = "fm_false_lead"
FM_ANCHOR_RELEASE = "fm_anchor_release"
FM_MIRROR_FLOOD = "fm_mirror_flood"
PH_PULLBACK = "ph_pullback"
PH_SHORT_SIDE = "ph_short_side_strike"
RL_WALL_RETURN = "rl_wall_return"
RL_UP_BACK_ACROSS = "rl_up_back_across"
RL_SAFE_OUTLET = "rl_safe_outlet"
CF_SLIP_CROSS = "cf_slip_cross"
CF_PIVOT_TURN = "cf_pivot_turn"
CF_DOUBLE_CLEAR = "cf_double_clear"
CF_HANDOFF_PUNISH = "cf_handoff_punish"
CF_SAME_LOOK_REVERSE = "cf_same_look_reverse"

OFFENSE = {
    FM_SWITCHBACK, FM_TWIN_TRIGGER, FM_FALSE_LEAD, FM_ANCHOR_RELEASE, FM_MIRROR_FLOOD,
    PH_PULLBACK, PH_SHORT_SIDE,
    RL_WALL_RETURN, RL_UP_BACK_ACROSS, RL_SAFE_OUTLET,
    CF_SLIP_CROSS, CF_PIVOT_TURN, CF_DOUBLE_CLEAR, CF_HANDOFF_PUNISH, CF_SAME_LOOK_REVERSE,
}
# Calls whose two receivers cross after the snap. The defense switches or stays.
CROSSING = {FM_SWITCHBACK, CF_SLIP_CROSS}
# Calls that show one thing and run another. An exchange defense bites on them.
FAKES = {FM_FALSE_LEAD, CF_SAME_LOOK_REVERSE}
# Calls that remember what the defense did on an earlier snap.
REMEMBERS = {FM_MIRROR_FLOOD, CF_SAME_LOOK_REVERSE}

# ── Defense ──
D_EXCHANGE = "dx_exchange"
D_STAGGER = "dx_stagger"
D_EDGE_ANCHOR = "dx_edge_anchor"
D_SLIDE_REPLACE = "dx_slide_replace"
D_CHANNEL_PRESS = "dx_channel_press"
D_TRANSITION_NET = "dx_transition_net"
D_CROSS_RUSH = "dx_cross_rush"
D_SET_BREAKER = "dx_set_breaker"

DEFENSE = {D_EXCHANGE, D_STAGGER, D_EDGE_ANCHOR, D_SLIDE_REPLACE, D_CHANNEL_PRESS,
           D_TRANSITION_NET, D_CROSS_RUSH, D_SET_BREAKER}
# Transition Net is a standing assignment on live turnovers, never a snap call.
SNAP_CALLS = DEFENSE - {D_TRANSITION_NET}

# Book of each call, for the site and the logs.
BOOK = {
    **{pid: "free_motion" for pid in (FM_SWITCHBACK, FM_TWIN_TRIGGER, FM_FALSE_LEAD,
                                      FM_ANCHOR_RELEASE, FM_MIRROR_FLOOD)},
    PH_PULLBACK: "phase_attack", PH_SHORT_SIDE: "phase_attack",
    **{pid: "relay" for pid in (RL_WALL_RETURN, RL_UP_BACK_ACROSS, RL_SAFE_OUTLET)},
    **{pid: "crossfire" for pid in (CF_SLIP_CROSS, CF_PIVOT_TURN, CF_DOUBLE_CLEAR,
                                    CF_HANDOFF_PUNISH, CF_SAME_LOOK_REVERSE)},
    **{pid: "cross_defense" for pid in DEFENSE},
}

# Defensive package postures: (alignment, blitz shift, focus families).
# Set Breaker's alignment changes with its read (set_breaker_alignment).
POSTURES = {
    D_EXCHANGE: ("balanced", -0.02, ["kick_pass", "lateral_spread"]),
    D_STAGGER: ("spread", -0.04, ["kick_pass", "lateral_spread"]),
    D_EDGE_ANCHOR: ("balanced", -0.02, ["counter", "sweep_option", "speed_option"]),
    D_SLIDE_REPLACE: ("balanced", 0.0, ["speed_option", "sweep_option", "viper_jet"]),
    D_CHANNEL_PRESS: ("aggressive", 0.10, ["kick_pass"]),
    D_CROSS_RUSH: ("aggressive", 0.08, ["kick_pass"]),
    D_SET_BREAKER: ("balanced", 0.0, ["power", "dive_option", "kick_pass"]),
}
# Yards a package takes away (negative) or concedes (positive) by run family,
# blended in with package strength like every other package.
RUN = {
    # Two defenders talk across a cross; a quick run up the middle beats the talk.
    D_EXCHANGE: {"dive_option": .18, "power": .16},
    # Three depths cover the second runner and leave the box light.
    D_STAGGER: {"dive_option": .20, "power": .20, "draw": .18, "lateral_spread": -.10},
    # A box defender stays home on the weak edge; the inside wall is thinner.
    D_EDGE_ANCHOR: {"counter": -.25, "sweep_option": -.12, "speed_option": -.12,
                    "dive_option": .24, "power": .22},
    # Help defenders slide to the ball; their own lanes open behind them.
    D_SLIDE_REPLACE: {"counter": .10},
    # Pressure from outside in leaves the interior open (on top of the box
    # defender it moves out, which field width already counts).
    D_CHANNEL_PRESS: {"dive_option": .10, "draw": .14},
    # Two rushers trading lanes arrive late on a draw.
    D_CROSS_RUSH: {"draw": .30, "dive_option": .12},
}
KICK = {
    D_EXCHANGE: {"quick_kick": -.06, "kick_lateral": -.04},
    D_STAGGER: {"kick_lateral": -.10, "quick_kick": -.04, "bomb": -.04},
    D_EDGE_ANCHOR: {"territory": .05},
    # The far channel is thinner after a slide.
    D_SLIDE_REPLACE: {"territory": .06, "bomb": .08},
    # The near outlet is denied; the switch across the field is open.
    D_CHANNEL_PRESS: {"quick_kick": -.16, "kick_lateral": -.10, "territory": .10},
    D_CROSS_RUSH: {"quick_kick": .04},
}
PRESS = {D_CHANNEL_PRESS, D_CROSS_RUSH}
COVER = {D_EXCHANGE, D_STAGGER, D_EDGE_ANCHOR}

INSIDE = ("dive_option", "power", "draw")
EDGE = ("sweep_option", "speed_option", "viper_jet", "counter", "lateral_spread")


def other(side: str) -> str:
    return {"left": "right", "right": "left"}.get(side, side)


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _rating(p, attr, default=70.0):
    """A player's rating on the legacy scale (about 70 for an average
    player), which every formula here is centered on."""
    raw = getattr(p, attr, None)
    if raw is None:
        return default
    from .rating_scale import current_to_legacy
    return float(current_to_legacy(raw))


# ── Post snap contests between actual players ──

def perceive_blitz(blitz: bool, awareness: float, rng=random) -> bool:
    """Does the Zeroback see the pressure coming? He misses some and sees
    some that are not there."""
    if blitz:
        return rng.random() < _clamp(0.55 + (awareness - 70) / 150.0, 0.25, 0.90)
    return rng.random() < 0.08


def exchange(attackers: List, defenders: List, strength: float, rng=random) -> Dict:
    """Two receivers cross; the two defenders on them switch or stay.

    The defenders' awareness and their practice at the call (strength, from an
    installed Exchange) against the crossers' agility and awareness. A clean
    switch leaves both covered. A missed one leaves the defender who followed
    the wrong man trailing. Returns the result and who was involved.
    """
    if len(attackers) < 2 or not defenders:
        return {"switched": True, "trailing": None, "p": None}
    d_aw = sum(_rating(d, "awareness") for d in defenders) / len(defenders)
    a_t = sum((_rating(a, "agility") + _rating(a, "awareness")) / 2 for a in attackers) / len(attackers)
    p = 0.45 + (d_aw - 70) / 100.0 - (a_t - 70) / 150.0 + 0.35 * strength
    p = _clamp(p, 0.10, 0.92)
    switched = rng.random() < p
    # The defender on the second crosser is the one who has to pass his man
    # on; when the talk fails he trails.
    trailing = None if switched else defenders[0]
    return {"switched": switched, "trailing": trailing, "p": round(p, 3)}


def commits(alignment: str, defender, rng=random) -> bool:
    """Does the nearest defender jump the first carrier (wall return)?"""
    base = {"aggressive": 0.62, "stacked": 0.52, "balanced": 0.45, "spread": 0.32}.get(alignment, 0.45)
    if defender is not None:
        base -= (_rating(defender, "awareness") - 70) / 200.0
    return rng.random() < _clamp(base, 0.10, 0.85)


def edge_steps_to_zeroback(alignment: str, defender, zeroback, rng=random) -> bool:
    """On the pivot turn, does the edge defender step toward the Zeroback?
    A Zeroback who is a real running threat draws him more often."""
    base = {"aggressive": 0.62, "stacked": 0.55, "balanced": 0.50, "spread": 0.40}.get(alignment, 0.50)
    if zeroback is not None:
        base += (_rating(zeroback, "speed") - 70) / 150.0
    if defender is not None:
        base -= (_rating(defender, "awareness") - 70) / 220.0
    return rng.random() < _clamp(base, 0.15, 0.85)


def decoys_draw(decoys: List, defenders: List, rng=random) -> List:
    """Each decoy threatens his side; the defender there may follow him."""
    drawn = []
    for decoy, defender in zip(decoys, defenders):
        if defender is None:
            continue
        p = 0.45 + (_rating(decoy, "speed") - _rating(defender, "awareness")) / 120.0
        if rng.random() < _clamp(p, 0.10, 0.80):
            drawn.append(defender)
    return drawn


def bad_snap(recipient, rng=random) -> bool:
    """A snap to someone other than the Zeroback goes wrong more often."""
    p = 0.03 * (1 + (70 - _rating(recipient, "hands")) / 40.0)
    return rng.random() < _clamp(p, 0.01, 0.08)


def pass_off(rushers: List, blockers: List, rng=random) -> Dict:
    """Cross Rush: two rushers trade lanes at the snap. The two blockers in
    front of them pass them off cleanly or one rusher comes free."""
    if len(rushers) < 2 or len(blockers) < 2:
        return {"clean": True, "p": None, "rushers": rushers[:2]}
    r = sum((_rating(p, "agility") + _rating(p, "awareness")) / 2 for p in rushers[:2]) / 2
    b = sum(_rating(p, "awareness") for p in blockers[:2]) / 2
    p = _clamp(0.55 + (b - r) / 90.0, 0.15, 0.85)
    return {"clean": rng.random() < p, "p": round(p, 3), "rushers": rushers[:2]}


def help_tackle(helper, carrier, strength: float, rng=random) -> bool:
    """Slide and Replace: after the first defender is beaten, the help
    defender sliding over gets a chance to make the tackle."""
    if helper is None:
        return False
    h = (_rating(helper, "speed") + _rating(helper, "tackling")) / 2
    c = (_rating(carrier, "speed") + _rating(carrier, "agility")) / 2
    p = 0.20 + 0.35 * strength + (h - c) / 120.0
    return rng.random() < _clamp(p, 0.05, 0.70)


# ── Set Breaker: predict the next call from what the offense has shown ──

def predict_next(transitions: Dict, last_family: Optional[str]):
    """From the families this offense ran after the same family earlier in
    the game, the most common one and how sure the defense is.
    Returns (family, confidence, samples)."""
    if not last_family:
        return None, 0.0, 0
    seen = transitions.get(last_family) or {}
    n = sum(seen.values())
    if n < 3:
        return None, 0.0, n
    fam, k = max(sorted(seen.items()), key=lambda kv: kv[1])
    return fam, k / n, n


def set_breaker_alignment(predicted: Optional[str]) -> str:
    if predicted in INSIDE:
        return "stacked"
    if predicted in ("kick_pass", "lateral_spread"):
        return "spread"
    if predicted in EDGE:
        return "balanced"
    return "balanced"


def set_breaker_deltas(predicted: Optional[str]):
    """Commit to the predicted family; everything else gets a little more."""
    run, kick = {}, {}
    if not predicted:
        return run, kick
    for fam in INSIDE + EDGE:
        run[fam] = -.28 if fam == predicted else .08
    if predicted == "kick_pass":
        kick = {"quick_kick": -.12, "territory": -.10, "kick_lateral": -.10, "bomb": -.06}
    else:
        kick = {"quick_kick": .05, "territory": .05}
    return run, kick


# ── Channels: Edge Anchor and Channel Press move one real defender ──

def move_defender(channels: Dict, player_id: int, to: str, x_room: Dict) -> None:
    """Move one defender to another channel and recompute what each side
    is worth to the offense (the same formula field_width uses)."""
    from . import field_width as FW
    frm = channels["by_id"].get(player_id)
    if frm is None or frm == to:
        return
    channels["by_id"][player_id] = to
    channels["counts"][frm] -= 1
    channels["counts"][to] += 1
    for side in ("left", "right"):
        channels["value"][side] = round(
            x_room[side] + FW.NUMBERS_EFFECT * (channels["fair"][side] - channels["counts"][side]), 4)


def weak_side(counts: Dict, fair: Dict) -> str:
    """The side with fewer defenders than its share, ties to the left."""
    gap_l = counts.get("left", 0) - fair.get("left", 0)
    gap_r = counts.get("right", 0) - fair.get("right", 0)
    return "left" if gap_l <= gap_r else "right"


# ── Offensive designs ──

def design(pid: str, look: Dict) -> Dict:
    """The call for this snap from the look. A design with no family hands
    the snap back to the normal selector (the fallback the clinic asks for)."""
    fn = _DESIGNS.get(pid)
    if fn is None:
        return {"branch": "unknown"}
    out = fn(look)
    out.setdefault("book", BOOK.get(pid))
    return out


def _weak(look):
    return look.get("weak") or "left"


def _switchback(look):
    ex = look.get("exchange") or {}
    weak = _weak(look)
    if ex.get("switched", True):
        # Both crossers are covered: the Zeroback keeps up the weak seam if
        # he runs, otherwise the normal quick outlet.
        if look.get("z_runs"):
            return {"branch": "switched_keep", "family": "dive_option", "carrier": "Zeroback",
                    "cross": True}
        return {"branch": "switched_outlet", "family": "kick_pass", "kick_pass": "quick_kick",
                "cross": True}
    # A defender trails: the Slotback takes the lane he left. Behind the
    # line it is a pitch on an edge run; past it, a quick kick.
    if look.get("ytg", 20) < 15:
        return {"branch": "vacated_pitch", "family": "speed_option", "lane": weak,
                "carrier": "Slotback", "cross": True}
    return {"branch": "vacated_kick", "family": "kick_pass", "kick_pass": "quick_kick",
            "lane": weak, "target": ["Slotback"], "cross": True}


def _twin_trigger(look):
    if not look.get("h_ready"):
        return {"branch": "default_zeroback"}
    if look.get("bad_snap"):
        return {"branch": "bad_snap", "family": "dive_option", "carrier": "Halfback",
                "recipient": "Halfback", "bad_snap": True}
    weak = _weak(look)
    counts, fair = look.get("counts") or {}, look.get("fair") or {}
    # A loaded box gets the kick over it; otherwise the Halfback carries to
    # a weak side that is at least half a man short of its share.
    soft = (look.get("alignment") not in ("stacked", "aggressive")
            and counts.get(weak, 0) <= fair.get(weak, 0) - 0.5)
    if soft:
        return {"branch": "recipient_carry", "family": "sweep_option", "lane": weak,
                "carrier": "Halfback", "recipient": "Halfback"}
    return {"branch": "recipient_kick", "family": "kick_pass", "kick_pass": "quick_kick",
            "distributor": "Halfback", "recipient": "Halfback", "target_not": ["Halfback"]}


def _false_lead(look):
    decoy = look.get("wide") or "right"
    away = other(decoy)
    pressed = (look.get("pressed") or {}).get(decoy, False)
    over = pressed or look.get("alignment") == "aggressive" or look.get("blitz_seen")
    if over:
        return {"branch": "counter", "family": "counter", "lane": away, "decoy": "Viper",
                "decoy_side": decoy}
    return {"branch": "quick_seam", "family": "kick_pass", "kick_pass": "quick_kick",
            "lane": away, "target": ["Wingback"], "decoy": "Viper", "decoy_side": decoy}


def _anchor_release(look):
    if look.get("blitz_seen"):
        return {"branch": "release", "family": "lateral_spread", "lane": look.get("lateral_lane", _weak(look)),
                "chain": ["Zeroback", "Offensive Line"], "release_lineman": True}
    return {"branch": "protect", "family": "power"}


def _mirror_flood(look):
    memory = look.get("memory") or []
    flood = look.get("wide") or "right"
    if memory and memory[-1].get("pressed"):
        # Weak evidence only: one loaded side last time flips the flood once.
        flood = other(memory[-1].get("lane", flood))
    if (look.get("pressed") or {}).get(flood, False):
        return {"branch": "weak_isolation", "family": "sweep_option", "lane": other(flood),
                "carrier": "Halfback", "flood": flood}
    sub = "quick_kick" if look.get("ytg", 20) <= 8 else "territory"
    return {"branch": "flood", "family": "kick_pass", "kick_pass": sub, "lane": flood,
            "target": ["Viper", "Slotback", "Wingback"], "flood": flood}


def _pullback(look):
    if look.get("blitz_seen"):
        return {"branch": "secure", "family": "dive_option", "carrier": "Halfback"}
    if look.get("alignment") == "stacked" or (look.get("counts") or {}).get("box", 0) >= 5:
        return {"branch": "pullback", "family": "lateral_spread", "lane": look.get("lateral_lane", _weak(look)),
                "chain": ["Zeroback", "Halfback", "Slotback"]}
    return {"branch": "pullback_kick", "family": "kick_pass", "kick_pass": "quick_kick",
            "lane": _weak(look)}


def _short_side(look):
    if not look.get("at_hash"):
        return {"branch": "no_short_side"}
    short = look.get("short")
    counts, fair = look.get("counts") or {}, look.get("fair") or {}
    if short not in ("left", "right") or counts.get(short, 0) > fair.get(short, 0):
        return {"branch": "short_side_covered"}
    if look.get("ytg", 20) <= 10 and look.get("has_viper"):
        # A quick pitch to the Viper, played as an edge run with her carrying.
        return {"branch": "strike_pitch", "family": "speed_option", "lane": short,
                "carrier": "Viper"}
    return {"branch": "strike_sweep", "family": "sweep_option", "lane": short}


def _wall_return(look):
    weak = look.get("lateral_lane", _weak(look))
    if look.get("commit"):
        return {"branch": "return", "family": "lateral_spread", "lane": weak,
                "chain": ["Zeroback", "Halfback", "Zeroback"]}
    # No commit: the Halfback keeps the pitch and runs, which this engine
    # plays as an option pitch on an edge run.
    return {"branch": "keep", "family": "speed_option", "lane": weak, "carrier": "Halfback"}


def _up_back_across(look):
    return {"branch": "up", "family": "kick_pass", "kick_pass": "kick_lateral",
            "lane": look.get("wide"), "target": ["Wingback"],
            "support": ["Slotback", "Halfback"], "retain_under_tackle": True}


def _safe_outlet(look):
    pressure = look.get("blitz_seen") or look.get("alignment") == "aggressive"
    if not pressure:
        return {"branch": "no_pressure"}
    # Lower exposure wins: the Zeroback's kick against the outlet's hands.
    kick_risk = 0.04 * (1 + (70 - look.get("z_accuracy", 70)) / 50.0)
    lat_risk = 0.05 * (1 + (70 - look.get("outlet_hands", 70)) / 50.0)
    if look.get("pending_bonus"):
        lat_risk *= 0.9  # a lateral to a back behind keeps the ball in front of you
    if lat_risk < kick_risk:
        # A pitch to the back behind, played as an edge run with him carrying.
        return {"branch": "pitch_outlet", "family": "speed_option",
                "carrier": "Halfback", "lane": look.get("lateral_lane", _weak(look))}
    return {"branch": "kick_outlet", "family": "kick_pass", "kick_pass": "quick_kick",
            "target": ["Halfback", "Slotback"]}


def _slip_cross(look):
    ex = look.get("exchange") or {}
    if ex.get("switched", True):
        return {"branch": "switched_inside", "family": "dive_option", "cross": True}
    return {"branch": "slip", "family": "kick_pass", "kick_pass": "quick_kick",
            "lane": _weak(look), "target": ["Slotback"], "cross": True}


def _pivot_turn(look):
    lane = look.get("wide") or "right"
    if look.get("edge_to_z"):
        return {"branch": "pivot", "family": "speed_option", "lane": lane,
                "carrier": "Halfback", "pitch_from": "Zeroback"}
    return {"branch": "keep", "family": "speed_option", "lane": lane, "carrier": "Zeroback"}


def _double_clear(look):
    drawn = look.get("drawn") or []
    if drawn:
        return {"branch": "seam", "family": "viper_jet", "lane": look.get("seam") or _weak(look),
                "carrier": "Viper", "decoys": ["Wingback", "Slotback"]}
    return {"branch": "kick_to_viper", "family": "kick_pass", "kick_pass": "quick_kick",
            "target": ["Viper"], "decoys": ["Wingback", "Slotback"]}


def _handoff_punish(look):
    m = look.get("mismatch")
    if not m:
        return {"branch": "no_evidence"}
    return {"branch": "punish", "family": "kick_pass", "kick_pass": "quick_kick",
            "target": [m["attacker_position"]], "mark": m["defender"]}


def _same_look_reverse(look):
    memory = look.get("memory") or []
    if memory and memory[-1].get("branch") == "look":
        return {"branch": "reverse", "family": "counter", "lane": other(memory[-1]["lane"]),
                "look_id": "pivot_look"}
    lane = look.get("wide") or "right"
    return {"branch": "look", "family": "speed_option", "lane": lane, "look_id": "pivot_look"}


_DESIGNS = {
    FM_SWITCHBACK: _switchback,
    FM_TWIN_TRIGGER: _twin_trigger,
    FM_FALSE_LEAD: _false_lead,
    FM_ANCHOR_RELEASE: _anchor_release,
    FM_MIRROR_FLOOD: _mirror_flood,
    PH_PULLBACK: _pullback,
    PH_SHORT_SIDE: _short_side,
    RL_WALL_RETURN: _wall_return,
    RL_UP_BACK_ACROSS: _up_back_across,
    RL_SAFE_OUTLET: _safe_outlet,
    CF_SLIP_CROSS: _slip_cross,
    CF_PIVOT_TURN: _pivot_turn,
    CF_DOUBLE_CLEAR: _double_clear,
    CF_HANDOFF_PUNISH: _handoff_punish,
    CF_SAME_LOOK_REVERSE: _same_look_reverse,
}


def eligibility(package_id: str, tags, context: Dict) -> Optional[bool]:
    """Primary trigger for each snap call (defensive_commitments uses it).
    Returns True, False, or None when the package is not one of these."""
    if package_id not in SNAP_CALLS:
        return None
    tags = set(tags)
    down = context.get("down", 1)
    ytg = context.get("yards_to_go", 20)
    cross = context.get("recent_cross_rate", 0.0)
    second = context.get("recent_second_runner_rate", 0.0)
    cutback = context.get("recent_cutback_rate", 0.0)
    perimeter = context.get("recent_perimeter_rate", 0.0)
    explosive = context.get("recent_explosive_rate", 0.0)
    kick = context.get("recent_kick_rate", 0.0)
    if package_id == D_EXCHANGE:
        return cross >= .10
    if package_id == D_STAGGER:
        return second >= .15
    if package_id == D_EDGE_ANCHOR:
        return "early_down" in tags and cutback + .5 * perimeter >= .18
    if package_id == D_SLIDE_REPLACE:
        return explosive >= .10
    if package_id == D_CHANNEL_PRESS:
        return context.get("formation_seen") == "spread" and kick >= .35
    if package_id == D_CROSS_RUSH:
        return down >= 3 and kick >= .30 and ytg >= 8
    if package_id == D_SET_BREAKER:
        return down >= 3 and context.get("set_breaker_confidence", 0.0) >= .45
    return False


def secondary(package_id: str, tags, context: Dict) -> bool:
    tags = set(tags)
    if package_id == D_EXCHANGE:
        return context.get("recent_cross_rate", 0.0) >= .05
    if package_id == D_STAGGER:
        return context.get("recent_second_runner_rate", 0.0) >= .08 or "late_downs" in tags
    if package_id == D_EDGE_ANCHOR:
        return context.get("recent_cutback_rate", 0.0) >= .10
    if package_id == D_SLIDE_REPLACE:
        return context.get("recent_explosive_rate", 0.0) >= .05
    if package_id == D_CHANNEL_PRESS:
        return context.get("formation_seen") == "spread" and context.get("recent_kick_rate", 0.0) >= .25
    if package_id == D_CROSS_RUSH:
        return context.get("down", 1) >= 4
    if package_id == D_SET_BREAKER:
        return context.get("set_breaker_confidence", 0.0) >= .35
    return False


def _runner(p):
    return (_rating(p, "speed") + _rating(p, "agility")) / 2 * (0.5 + float(getattr(p, "game_energy", 100)) / 200)


def immediate_tackle(receiver, defender) -> bool:
    """Up Back Across: is the defender on the catch close enough that the
    receiver should hold on rather than lateral?"""
    if defender is None:
        return False
    close = (_rating(defender, "speed") + _rating(defender, "tackling")) / 2
    return close >= _runner(receiver) + 8


def lane_closed(runner, defender) -> bool:
    """Up Back Across: the second runner's lane is closing, so he moves it
    on level to the last man."""
    if defender is None or runner is None:
        return False
    return (_rating(defender, "speed") + _rating(defender, "tackling")) / 2 >= _runner(runner)
