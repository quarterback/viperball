"""Inputs to the existing call selectors for a paired concept."""

POLICY_VERSION = 1
FOLLOWUP_WINDOW = 4
FOCUS_FRONTS = {"stacked", "aggressive"}


def interrupt_reason(down, yards_to_go, quarter, seconds, score_diff, kick_mode):
    if kick_mode:
        return "kick_mode"
    if down >= 5 or (down == 4 and yards_to_go >= 10):
        return "down_and_distance"
    if quarter in (2, 4) and seconds <= 180 and score_diff != 0:
        return "clock_priority"
    return None


def pair_for(pairs, package_id):
    for pair in pairs:
        if package_id in pair["packages"]:
            other = next(pid for pid in pair["packages"] if pid != package_id)
            return pair["formation"], other
    return None


def paired_options(package, category, weights, previous):
    """Filter the selector's positive weights to distinct catalog actions."""
    tag = "play_family_tags" if category == "family" else "kick_pass_tags"
    choices = set(package[tag])
    if previous:
        family, subtype = previous
        if category == "family":
            another_subtype = set(package["kick_pass_tags"]) - {subtype}
            if family != "kick_pass" or not another_subtype:
                choices.discard(family)
        elif family == "kick_pass":
            choices.discard(subtype)
    return {kind: weight for kind, weight in weights.items() if weight > 0 and kind in choices}
