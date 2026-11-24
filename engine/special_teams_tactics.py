"""ST-01: bounded, saved-coordinator choices layered over the five ST schemes.

The scheme remains the tactical baseline.  STC preferences only affect
legal choices and existing scoring/return/coverage contests.  No coordinator
means no change to legacy behavior.
"""
from __future__ import annotations

from .coach_tactics import ensure_coach_tactical_profile


def resolve_special_teams_tactics(staff):
    if not staff or staff.get("stc") is None:
        return {}
    stc = staff["stc"]
    profile = ensure_coach_tactical_profile(stc)
    hc = staff.get("head_coach")
    if hc is None:
        authority = 1.0
    else:
        leader = ensure_coach_tactical_profile(hc)
        delegation = float(leader.get("head_coach", {}).get("delegation", 0.5))
        authority = max(0.4, min(0.95, 0.4 + 0.6 * delegation))
    prefs = profile.get("special_teams", {})
    return {
        "coach_id": stc.coach_id,
        "authority": round(authority, 3),
        "field_position_bias": max(-0.5, min(0.5, float(prefs.get("field_position_bias", 0.0)))),
        "return_aggression": max(-0.5, min(0.5, float(prefs.get("return_aggression", 0.0)))),
    }


def bounded_choice(base, bias, authority, scale=0.30, floor=0.0, ceiling=1.0):
    """Proportional coordinator preference; scheme retains the main effect."""
    change = 1.0 + max(-0.5, min(0.5, bias)) * max(0.0, min(1.0, authority)) * scale
    return max(floor, min(ceiling, base * change))
