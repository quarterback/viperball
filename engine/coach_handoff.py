"""Mid-game caller changes and between-series suggestions (casebook case 10).

Two things a head coach and offensive coordinator do during a game:

1. At halftime, a struggling offense can change who calls the plays. A head
   coach who delegated can take the offense over if she is ready to call it
   and does not like to delegate. A head coach who kept the calls can hand
   them to the coordinator. An offensive coordinator who has been a head
   coach elsewhere keeps her calls, as she does before the game.
2. Between series, the coach who is not calling the offense looks at this
   game's plays and suggests the play family that has worked best. The
   caller takes the suggestion or not depending on how adaptable and how
   stubborn she is. A taken suggestion becomes the first call of the next
   drive.

Both use only what the staff can see: the score, the plays already run and
the coaches' own cards. No ratings or yards change.
"""
import random

POLICY_VERSION = 1

# A half that ends with the team this far behind, or with this few points
# while behind, counts as a struggling offense.
STRUGGLING_DEFICIT = 9
STRUGGLING_POINTS = 15


def _slider(card, name, default=0.5):
    from .coach_tactics import _slider as slider
    try:
        return slider(card, name)
    except Exception:
        return default


def struggling(own_points, opp_points):
    deficit = opp_points - own_points
    return deficit >= STRUGGLING_DEFICIT or (deficit > 0 and own_points < STRUGGLING_POINTS)


def halftime_change(staff, own_points, opp_points, rng):
    """Who calls the offense in the second half, if it changes.

    Returns {"from": card, "to": card, "direction": ..., "reason": ...} or None.
    """
    from .coach_career import active_management, caller, ensure, requires_calls
    from .coach_roles import role_readiness

    staff = staff or {}
    hc, oc = staff.get("head_coach"), staff.get("oc")
    if hc is None or oc is None or not struggling(own_points, opp_points):
        return None
    current = caller(staff, "oc")
    delegation = float(active_management(hc).get("delegation", .6))
    if current is oc:
        if requires_calls(oc, "oc"):
            return None
        readiness = role_readiness(hc, "oc", ensure(hc))
        if readiness < .85:
            return None
        chance = max(0.0, min(.8, (0.80 - delegation) * 2.0))
        if rng.random() < chance:
            return {"from": oc, "to": hc, "direction": "head_coach_takes_over",
                    "reason": "struggling_offense"}
        return None
    if current is hc:
        chance = max(0.0, min(.6, (delegation - 0.30) * 1.5))
        if rng.random() < chance:
            return {"from": hc, "to": oc, "direction": "head_coach_hands_off",
                    "reason": "struggling_offense"}
    return None


def tactics_for(staff, card):
    """Offensive tactics as if this card were the caller."""
    from .coach_career import active_management, ensure, requires_calls
    from .coach_learning import offense_bias
    from .coach_roles import role_readiness
    from .coach_tactics import ensure_coach_tactical_profile

    hc = (staff or {}).get("head_coach")
    profile = ensure_coach_tactical_profile(card)
    readiness = role_readiness(card, "oc", ensure(card))
    if hc is None or card is hc or requires_calls(card, "oc"):
        authority = readiness
    else:
        delegation = float(active_management(hc).get("delegation", .5))
        authority = readiness * max(.4, min(.95, .4 + .6 * delegation))
    return {
        "coach_id": card.coach_id,
        "signature": profile.get("identity", {}).get("offense_interpretation", ""),
        "featured_position": profile.get("offense", {}).get("featured_position", ""),
        "authority": round(authority, 3),
        "tempo_preference": _slider(card, "tempo_preference"),
        "formation_bias": dict(profile.get("offense", {}).get("formation_bias", {})),
        "family_bias": offense_bias(profile),
        "kick_pass_bias": dict(profile.get("offense", {}).get("kick_pass_bias", {})),
    }


def suggestion(plays, min_plays=3, edge=1.5):
    """The play family that has gained the most this game, if it stands out.

    `plays` is a list of (family, yards) for this offense's run and kick pass
    snaps so far.
    """
    by_family = {}
    for family, yards in plays:
        by_family.setdefault(family, []).append(yards)
    if not by_family:
        return None
    overall = sum(y for ys in by_family.values() for y in ys) / sum(len(ys) for ys in by_family.values())
    best = None
    for family, ys in by_family.items():
        if len(ys) < min_plays:
            continue
        mean = sum(ys) / len(ys)
        if mean >= overall + edge and (best is None or mean > best[1]):
            best = (family, mean)
    if best is None:
        return None
    return {"family": best[0], "family_mean": round(best[1], 2), "overall_mean": round(overall, 2)}


def accepts(caller_card, rng):
    """Whether the caller takes a suggestion from her staff."""
    adapt = _slider(caller_card, "adaptability")
    stubborn = _slider(caller_card, "stubbornness")
    return rng.random() < max(.10, min(.85, .30 + .50 * adapt - .30 * stubborn))
