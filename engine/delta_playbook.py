"""Delta-specific modular playbook policy. No new scoring or possession rules.

Context is from the offense's possession, score_diff from the caller's side.
The read and defense assignments are coarse engine commitments, not coordinates.
"""
PP = frozenset(("pp_advantage_entry", "pp_umbrella", "pp_overload",
    "pp_double_threat", "pp_five_nine", "pp_compression", "pp_rapid_finish",
    "pp_second_shot"))
PKO = frozenset(("pko_escape", "pko_secure_twenty", "pko_territory_exit", "pko_counterpunch"))
PK = frozenset(("pk_compact_box", "pk_kicker_diamond", "pk_side_lock",
    "pk_rotating_shell", "pk_range_denial", "pk_goal_line_wall",
    "pk_late_down_surge", "pk_takeaway_trap"))
OFFENSE = PP | PKO
ALL = OFFENSE | PK


def possession_context(origin, pending_cost, spot, prior=None):
    """Latch once per possession, retaining the original start across quarters."""
    if origin is None and prior is not None:
        return dict(prior)
    cost = pending_cost if origin == "score_restart" else 0
    return {"delta_cost": cost, "delta_bucket": "power_play" if cost < 0 else
            "penalty_kill" if cost > 0 else "neutral", "delta_start": spot}


def retained_miss(play, snap_side, end_side, next_down, snap_down):
    """Only a resolved ordinary drop-kick miss that consumed a down."""
    return (play.play_type == "drop_kick" and play.result == "missed_kick"
            and snap_side == end_side and snap_down < 6
            and next_down == snap_down + 1 and not getattr(play, "penalty", None))


def weight(pid, c):
    if pid not in ALL:
        return 1.0
    if c.get("delta_bucket") != ("penalty_kill" if pid in PKO else "power_play"):
        return 0.0
    fp, d, y = c.get("field_position", 20), c.get("down", 1), c.get("yards_to_go", 20)
    q, tr, diff = c.get("quarter", 1), c.get("time_remaining", 600), c.get("score_diff", 0)
    kick = c.get("delta_drop_success", 0)
    lat = c.get("recent_lateral_rate", 0)
    peri = c.get("recent_perimeter_rate", 0)
    passes = c.get("recent_kick_rate", 0)
    urgent = q == 4 and tr <= 180 and diff < 0
    fits = {
        "pp_advantage_entry": fp < 50 and d <= 4,
        "pp_umbrella": 55 <= fp < 95 and d >= 3 and kick >= .40,
        "pp_overload": 20 <= fp < 85 and d <= 4,
        "pp_double_threat": 20 <= fp < 95 and d <= 5,
        "pp_five_nine": 50 <= fp < 95 and d >= 4,
        "pp_compression": fp >= 85,
        "pp_rapid_finish": urgent and d <= 6,
        "pp_second_shot": bool(c.get("delta_retained_miss")) and 2 <= d <= 6,
        "pko_escape": fp <= 10 and d <= 4,
        "pko_secure_twenty": 10 < fp <= 50 and d <= 5,
        "pko_territory_exit": d >= 5 and y >= 5 and diff >= 0,
        "pko_counterpunch": fp <= 35 and c.get("delta_defense_school") in ("blitz_pack", "keeper_hunt", "predator"),
        "pk_compact_box": fp >= 75,
        "pk_kicker_diamond": kick >= .40 and fp < 95,
        "pk_side_lock": max(lat, peri) >= .20,
        "pk_rotating_shell": passes >= .20 or peri >= .20,
        "pk_range_denial": kick < .55 and fp < 85,
        "pk_goal_line_wall": fp >= 95,
        "pk_late_down_surge": d >= 5,
        "pk_takeaway_trap": max(lat, passes) >= .25,
    }
    if not fits[pid]:
        return 0.0
    w = 1.0
    archetypes = set(c.get("clinic_archetypes", ()))
    if pid in ("pp_umbrella", "pp_five_nine", "pp_second_shot"):
        w *= 1.25 if archetypes & {"kicking_zb", "dual_threat_zb"} else .8
    if pid == "pp_overload":
        if c.get("clinic_skill_count", 6) < 3:
            return 0.0
        w *= 1.25 if "distributor_zb" in archetypes else .8
        if (c.get("offense_energy") or 100) < 70 or c.get("clinic_bonus_pending"):
            w *= .55
    if pid in ("pp_double_threat", "pp_compression") and archetypes & {"running_zb", "dual_threat_zb", "power_viper"}:
        w *= 1.25
    if pid == "pk_kicker_diamond" and q == 4 and tr <= 180 and 0 < diff <= 5:
        w *= 1.5
    if pid == "pk_goal_line_wall" and q == 4 and tr <= 180 and 5 < diff <= 9:
        w *= 1.5
    if pid == "pk_takeaway_trap" and q == 4 and diff > 9:
        w *= .6
    return w


# Visible-front adjustments, applied once through existing bounded family bias.
def read(pid, alignment):
    if pid not in OFFENSE:
        return None, {}
    if alignment == "stacked":
        if pid in ("pp_overload", "pp_umbrella", "pp_double_threat", "pp_compression"):
            return "outside_box", {"kick_pass": .10, "sweep_option": .10, "power": -.08}
        return "interior_closed", {"counter": .12, "dive_option": -.10}
    if alignment == "spread":
        return "interior_available", {"power": .12, "dive_option": .08, "lateral_spread": -.10}
    if alignment == "aggressive":
        return "pressure_outlet", {"draw": .12, "counter": .10, "kick_pass": -.08}
    return "base_read", {}


# Distinct commitments and concessions, resolved by the existing physical contests.
POSTURES = {
    "pk_compact_box": ("stacked", -.06, ["power", "dive_option", "kick_pass"]),
    "pk_kicker_diamond": ("aggressive", .08, ["kick_pass"]),
    "pk_side_lock": ("spread", -.04, ["sweep_option", "lateral_spread"]),
    "pk_rotating_shell": ("spread", -.08, ["kick_pass", "lateral_spread"]),
    "pk_range_denial": ("balanced", -.02, ["power", "dive_option", "speed_option"]),
    "pk_goal_line_wall": ("stacked", -.02, ["power", "dive_option", "kick_pass"]),
    "pk_late_down_surge": ("aggressive", .14, ["kick_pass", "power"]),
    "pk_takeaway_trap": ("spread", -.02, ["lateral_spread", "kick_pass"]),
}
RUN = {
    "pk_compact_box": {"power": -.32, "dive_option": -.30, "sweep_option": .24},
    "pk_kicker_diamond": {"power": .24, "draw": .22},
    "pk_side_lock": {"sweep_option": -.30, "lateral_spread": -.25, "power": .22},
    "pk_rotating_shell": {"lateral_spread": -.18, "power": .20, "dive_option": .18},
    "pk_range_denial": {"power": -.20, "dive_option": -.20, "speed_option": -.12, "sweep_option": .16},
    "pk_goal_line_wall": {"power": -.38, "dive_option": -.35, "sweep_option": .26},
    "pk_late_down_surge": {"power": -.16, "draw": .32, "counter": .30},
    "pk_takeaway_trap": {"lateral_spread": -.20, "power": .24},
}
KICK = {
    "pk_compact_box": {"quick_kick": -.10, "territory": .10},
    "pk_kicker_diamond": {"quick_kick": .08, "territory": -.10},
    "pk_side_lock": {"quick_kick": -.06, "bomb": .12},
    "pk_rotating_shell": {"territory": -.14, "bomb": -.18, "quick_kick": .08},
    "pk_range_denial": {"quick_kick": -.08, "bomb": .12},
    "pk_goal_line_wall": {"quick_kick": -.12, "territory": .10},
    "pk_late_down_surge": {"quick_kick": .12, "bomb": .14},
    "pk_takeaway_trap": {"kick_lateral": -.12, "bomb": .15},
}


def finish_shift(pid, familiarity, authority, c, kicker_archetype):
    """Signed adjustment to existing stalled-drive kick thresholds only."""
    if c.get("down") not in (4, 5) or not weight(pid, c):
        return 0.0
    if pid in ("pp_umbrella", "pp_five_nine", "pp_second_shot"):
        if kicker_archetype not in ("kicking_zb", "dual_threat_zb"):
            return 0.0
        direction = 2.0
    elif pid == "pp_compression":
        direction = -2.0
    else:
        return 0.0
    return direction * max(0.0, min(1.0, familiarity)) * max(0.0, min(1.0, authority))
