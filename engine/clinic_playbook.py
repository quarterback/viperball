"""Cross-code clinic concepts: selection policy, not a second game resolver.

Only installed catalog packages opt in. Read progression describes available
coarse engine actions; no claim of spatial tracking or physical route simulation.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Concept:
    id: str
    name: str
    code_origin: Tuple[str, ...]
    family: str
    formation: Tuple[str, ...]
    personnel_focus: Tuple[str, ...]
    primary_action: str
    lateral_count_target: int
    risk_tier: str
    read_progression: Tuple[str, ...]
    downs: Tuple[int, ...]
    distances: Tuple[str, ...]
    field_zones: Tuple[str, ...]
    score_diff: str
    fatigue_sensitivity: str
    defensive_counters: Tuple[str, ...]


CONCEPTS = {c.id: c for c in (
    Concept("clinic_anchor_crease", "Anchor Crease", ("gridiron", "rugby"),
            "power_anchor", ("tight", "heavy"), ("running_zb", "dual_threat_zb", "power_viper"),
            "run", 0, "low", ("test interior", "prefer power or dive", "fallback to base call"),
            (1, 2, 5, 6), ("short", "medium"), ("own_deep", "midfield", "kick_range", "red_zone"),
            "protect", "low", ("fortress",)),
    Concept("clinic_pod_two", "Pod Two", ("rugby", "gridiron"),
            "lateral_chain", ("split", "spread"), ("distributor_zb", "dual_threat_zb", "receiving_viper", "hybrid_viper"),
            "lateral_chain", 2, "medium", ("test support", "two-transfer target", "retain base resolver"),
            (1, 2, 3, 4), ("medium", "long"), ("midfield", "kick_range"),
            "neutral", "high", ("swarm", "chaos")),
    Concept("clinic_edge_three", "Edge Three", ("rugby", "soccer"),
            "lateral_chain", ("spread",), ("distributor_zb", "receiving_viper", "hybrid_viper"),
            "lateral_chain", 3, "high", ("test perimeter", "three-transfer target", "retain base resolver"),
            (3, 4, 5), ("medium", "long"), ("midfield", "kick_range"),
            "neutral", "high", ("swarm", "chaos")),
    Concept("clinic_last_wave", "Last Wave", ("rugby", "soccer"),
            "desperation_chain", ("spread",), ("distributor_zb", "dual_threat_zb", "hybrid_viper"),
            "lateral_chain", 4, "extreme", ("check urgency", "four-transfer target", "retain base resolver"),
            (4, 5, 6), ("long",), ("midfield", "kick_range"),
            "chasing", "high", ("swarm", "chaos", "drift")),
    Concept("clinic_corridor_switch", "Corridor Switch", ("afl", "soccer"),
            "kick_pass", ("split", "spread"), ("kicking_zb", "dual_threat_zb", "receiving_viper", "decoy_viper"),
            "kick_pass", 0, "medium", ("recognize interior concentration", "prefer territory kick pass", "fallback to base call"),
            (1, 2, 3, 4), ("medium", "long"), ("own_deep", "midfield", "kick_range"),
            "neutral", "medium", ("lockdown", "drift")),
    Concept("clinic_third_runner", "Third Runner", ("soccer", "afl", "rugby"),
            "kick_pass", ("split", "spread"), ("distributor_zb", "receiving_viper", "hybrid_viper"),
            "kick_pass", 1, "high", ("prefer kick-lateral subtype", "existing catch/lateral contest", "fallback to base call"),
            (2, 3, 4), ("medium", "long"), ("midfield", "kick_range"),
            "neutral", "high", ("lockdown", "swarm")),
    Concept("clinic_launch_option", "Launch Option", ("gridiron", "afl"),
            "snap_kick_option", ("tight", "split"), ("kicking_zb", "dual_threat_zb", "decoy_viper"),
            "kick_pass", 0, "low", ("advance toward range", "leave scoring kick to existing finish policy"),
            (3, 4, 5, 6), ("short", "medium", "long"), ("midfield", "kick_range"),
            "neutral", "low", ("keeper_hunt", "blitz_pack")),
)}


def distance_bucket(yards):
    return "short" if yards <= 4 else "medium" if yards <= 10 else "long"


def field_zone(fp):
    return "own_deep" if fp <= 10 else "red_zone" if fp >= 85 else "kick_range" if fp >= 55 else "midfield"


def concept_weight(package_id, context):
    """Relative package preference; zeros exclude only clinic calls.
    Uses observable scheme/scout context, not the opponent's hidden next call.
    Unknown context is neutral. Coefficients are initial calibration hypotheses.
    """
    c = CONCEPTS.get(package_id)
    if not c:
        return 1.0
    down = context.get("down", 1)
    yards = context.get("yards_to_go", 20)
    diff = context.get("score_diff", 0)
    quarter = context.get("quarter", 1)
    urgent = diff < 0 and (quarter >= 3 and (diff <= -10 or context.get("time_remaining", 600) <= 180))
    if c.score_diff == "chasing" and not urgent:
        return 0.0
    if down not in c.downs or field_zone(context.get("field_position", 20)) not in c.field_zones:
        return 0.0
    weight = 1.0 if distance_bucket(yards) in c.distances else .55
    archetypes = context.get("clinic_archetypes", ())
    if archetypes:
        weight *= 1.0 + .15 * sum(a in c.personnel_focus for a in archetypes)
    pace = yards / max(1, 7 - down)
    if c.primary_action == "lateral_chain":
        if context.get("clinic_skill_count", 6) < 2:
            return 0.0
        if yards <= 4 or (quarter == 4 and diff > 0):
            weight *= .35
        if pace >= 5 and urgent:
            weight *= 1.25
        own = context.get("offense_energy")
        opp = context.get("defense_energy")
        if own is not None and own < 70:
            weight *= .55
        if opp is not None and opp < 75:
            weight *= 1.3
        if context.get("clinic_bonus_pending"):
            weight *= .55
    if c.primary_action == "kick_pass" and c.fatigue_sensitivity == "high":
        own = context.get("offense_energy")
        if own is not None and own < 70:
            weight *= .70
    if c.family == "power_anchor" and (yards <= 4 or (quarter == 4 and diff > 0)):
        weight *= 1.4
    defense = str(context.get("clinic_defense_school", "")).lower()
    if defense in c.defensive_counters:
        weight *= .65
    if c.primary_action == "kick_pass" and defense == "fortress":
        weight *= 1.25
    return min(2.0, weight)


def lateral_length(package, available):
    """Return desired number of transfer attempts, or None for legacy play.
    A target requires one more participant than transfers; never fabricate one.
    """
    c = CONCEPTS.get((package or {}).get("package_id"))
    if not c or c.primary_action != "lateral_chain" or available < 2:
        return None
    return min(c.lateral_count_target, available - 1)


def snap_kick_threshold_shift(tactics, context, kicker_archetype):
    """Bounded preference at existing fourth/fifth-down stalled-drive gates.

    Only a practiced Launch Option with a suitable actual kicker can move
    the threshold. Never changes kick success probability or legal range.
    """
    if kicker_archetype not in ("kicking_zb", "dual_threat_zb"):
        return 0.0
    if context.get("down") not in (4, 5):
        return 0.0
    for p in tactics.get("packages", ()):
        if p.get("package_id") == "clinic_launch_option":
            familiarity = max(0.0, min(1.0, p.get("familiarity", 0.0)))
            authority = max(0.0, min(1.0, tactics.get("authority", 1.0)))
            preference = concept_weight(p["package_id"], context)
            return min(2.0, familiarity * authority * preference)
    return 0.0


def clinic_read(package, alignment):
    """Bounded alternatives based on the publicly visible pre-snap front.

    The existing family selector applies its usual authority and legal gates.
    No claim of post-snap spatial reads; no access to hidden defensive focus.
    """
    c = CONCEPTS.get((package or {}).get("package_id"))
    if not c or alignment not in ("stacked", "spread", "aggressive", "balanced"):
        return None, {}
    if c.family == "power_anchor" and alignment == "stacked":
        return "inside_closed", {"power": -.12, "dive_option": -.12, "counter": .12, "draw": .08}
    if c.primary_action == "lateral_chain" and alignment == "spread":
        return "edge_contained", {"lateral_spread": -.12, "power": .08, "dive_option": .08}
    if c.primary_action == "lateral_chain" and alignment == "stacked":
        return "edge_available", {"lateral_spread": .10, "sweep_option": .08}
    if c.primary_action == "kick_pass" and alignment == "aggressive":
        return "pressure_outlet", {"kick_pass": -.08, "draw": .12, "counter": .08}
    if c.primary_action == "kick_pass" and alignment == "stacked":
        return "space_outside_box", {"kick_pass": .10, "sweep_option": .06}
    return "base_read", {}


def compound_fumble_probability(transfers, two_transfer_risk=.12):
    """Aggregate probability of at least one failed transfer.

    Calibrate the per-transfer hazard to the legacy two-transfer risk.
    Existing player/ball-handling/style modifiers and recovery rules still apply.
    This is not a spatial or sequential fumble resolver.
    """
    if transfers < 1:
        return 0.0
    risk = max(0.0, min(1.0, two_transfer_risk))
    return 1.0 - (1.0 - risk) ** (transfers / 2.0)
