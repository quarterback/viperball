"""Career intent and role qualifications shared by the coaching market.

No yearly lottery for changing disciplines. Preferences are drawn once per
coach ID and stored in the existing career_development save payload.
"""
import hashlib
import random

CORE_ROLES = ("head_coach", "oc", "dc", "stc")
POSITION_ROLES = ("pos_zb", "pos_backs", "pos_ol", "pos_dl", "pos_coverage", "pos_kicks")
ALL_ROLES = CORE_ROLES + POSITION_ROLES
POSITION_LABELS = dict(zip(POSITION_ROLES, (
    "Zerobacks", "Backs & Vipers", "Offensive Line", "Defensive Line",
    "Keepers & Coverage", "Kicking & Returns")))
POSITION_DISCIPLINE = dict(zip(POSITION_ROLES, ("oc", "oc", "oc", "dc", "dc", "stc")))
POSITION_GROUP = {
    "Zeroback": "pos_zb", "Halfback": "pos_backs", "Wingback": "pos_backs",
    "Slotback": "pos_backs", "Shiftback": "pos_backs", "Viper": "pos_backs",
    "Offensive Line": "pos_ol", "Defensive Line": "pos_dl", "Keeper": "pos_coverage",
    "Line Anchor": "pos_dl", "Edge Defender": "pos_dl", "Spotback": "pos_coverage",
    "Cornerback": "pos_coverage", "Lastback": "pos_coverage",
}
TECHNICAL = {
    "pos_zb": ("awareness", "hands", "kicking", "kick_accuracy"),
    "pos_backs": ("awareness", "hands", "lateral_skill"),
    "pos_ol": ("awareness", "hands"),
    "pos_dl": ("awareness", "tackling"),
    "pos_coverage": ("awareness", "hands", "tackling"),
    "pos_kicks": ("kicking", "kick_accuracy", "hands"),
}


def stable_rng(key):
    return random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest()[:16], "big"))


def career_path(card, state):
    path = state.get("career_path")
    if path:
        return path
    rng = stable_rng("coach-path-v1:" + card.coach_id)
    origin = (getattr(card, "tactical_profile", {}) or {}).get("origin_role", card.role)
    primary = POSITION_DISCIPLINE.get(origin, origin)
    if primary == "head_coach":
        primary = {"offensive_mind": "oc", "defensive_mind": "dc",
                   "special_teams_guru": "stc"}.get(card.hc_affinity, "oc")
    roll = rng.random()
    secondary = None
    if primary == "stc":
        intent = "specialist" if roll < .65 else "coordinator" if roll < .90 else "head_coach"
        if intent == "coordinator":
            secondary = {"offensive_mind": "oc", "defensive_mind": "dc"}.get(card.hc_affinity)
            secondary = secondary or rng.choice(("oc", "dc"))
    else:
        intent = "specialist" if roll < .75 else "secondary" if roll < .95 else "generalist"
        if intent != "specialist":
            secondary = "dc" if primary == "oc" else "oc"
    # An assistant position coach can choose a teaching career or pursue
    # coordination. This is separate from the coordinator's crossover intent.
    advancement = "coordinator" if origin in POSITION_ROLES and rng.random() < .55 else "teaching"
    state["career_path"] = {
        "primary": primary, "secondary": secondary, "intent": intent,
        "position_advancement": advancement,
        "teaching_role": origin if origin in POSITION_ROLES else rng.choice(
            [r for r in POSITION_ROLES if POSITION_DISCIPLINE[r] == primary]),
        "cross_after": rng.randint(4, 7),
    }
    return state["career_path"]


def experience(card, role, state):
    years = state.get("role_years", {})
    # Existing opening coaches have career totals but no dated history.
    # Only credit this legacy experience to the original employed role.
    legacy = state.get("legacy_role_years", {})
    return years.get(role, 0) + legacy.get(role, 0)


def qualifies(card, role, state):
    if role == card.role:
        return True
    path = career_path(card, state)
    primary, secondary = path["primary"], path["secondary"]
    if role in POSITION_ROLES:
        return role == path["teaching_role"] or experience(card, role, state) > 0
    if role not in ("oc", "dc", "stc"):
        return False
    if experience(card, role, state) > 0:
        return True
    if card.role in POSITION_ROLES:
        teaching_years = experience(card, card.role, state)
        return (path["position_advancement"] == "coordinator" and
                teaching_years >= 3 and card.instincts >= 55 and
                role == POSITION_DISCIPLINE[card.role])
    if card.role == "head_coach":
        return role == primary
    if role == primary:
        return True
    # Cross-discipline eligibility is durable, earned, and rare in actual
    # hiring; a second specialty alone does not make a coach a good caller.
    if role == secondary:
        return (sum(experience(card, r, state) for r in ("oc", "dc", "stc"))
                >= path["cross_after"] and card.instincts >= 55)
    return path["intent"] == "generalist" and role == "stc" and card.instincts >= 65


def role_readiness(card, role, state):
    """Scale unfamiliar-role tactical authority, not general attributes."""
    if role not in ("oc", "dc", "stc"):
        return 1.0
    path = career_path(card, state)
    years = experience(card, role, state)
    origin = (getattr(card, "tactical_profile", {}) or {}).get("origin_role")
    if origin == role or (origin == "head_coach" and path["primary"] == role):
        return 1.0
    return min(1.0, .65 + .12 * years)


def position_role(position):
    return POSITION_GROUP.get(position)
