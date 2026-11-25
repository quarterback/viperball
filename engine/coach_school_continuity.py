"""Plan the next season's school once, before recruiting.

The installed school belongs to the program; the coach retains a separate
tactical signature. Change a school only at an actual HC transition and
only on the incoming HC's specialist side. Human decisions remain manual.
"""
from .coach_career import management
from .coach_tactics import ensure_coach_tactical_profile
from .coach_recruiting_fit import OFFENSE_SCHOOLS, DEFENSE_SCHOOLS


# Ordered alternatives are existing engine scheme IDs, not new playbooks.
OFFENSE_TARGETS = {
    "run_to_kick": ("ground_control", "ground_pound"),
    "territory_control": ("ball_control", "boot_raid"),
    "vertical_attack": ("shock_and_awe", "quick_strike"),
    "spread_motion": ("slick_n_slide", "lateral_spread"),
}
DEFENSE_TARGETS = {
    "run_wall": ("trench_wall", "fortress"),
    "deep_coverage": ("sky_cover", "lockdown", "drift"),
    "selective_pressure": ("blitz_pack",),
    "pursuit_zone": ("edge_net", "shadow"),
    "turnover_hunt": ("bounty_defense", "chaos", "predator"),
}


def plan_schools(previous, staffs, previous_hc_ids, human_team,
                 offense_catalog, defense_catalog):
    """Return independent configs for continuing CPU programs."""
    plans = {}
    for team, staff in sorted(staffs.items()):
        if team == human_team or not previous.get(team):
            continue
        config = dict(previous[team])
        hc = staff.get("head_coach")
        prior_id = previous_hc_ids.get(team)
        if hc is not None and prior_id and hc.coach_id != prior_id:
            # A known in-house successor or shared mentor keeps the existing
            # school; their individual tactical signature still travels.
            mentors = {row.get("coach_id") for row in hc.coaching_tree}
            if prior_id not in mentors:
                specialty = management(hc).get("specialty")
                identity = ensure_coach_tactical_profile(hc)["identity"]
                if specialty == "oc":
                    key, signature, schools, targets, catalog = (
                        "offense_style", identity.get("offense_interpretation"),
                        OFFENSE_SCHOOLS, OFFENSE_TARGETS, offense_catalog)
                elif specialty == "dc":
                    key, signature, schools, targets, catalog = (
                        "defense_style", identity.get("defense_interpretation"),
                        DEFENSE_SCHOOLS, DEFENSE_TARGETS, defense_catalog)
                else:
                    key = None
                if key and schools.get(config.get(key)) != signature:
                    choice = next((s for s in targets.get(signature, ()) if s in catalog), None)
                    if choice:
                        config[key] = choice
        # A retired/renamed engine key must not override the new-season
        # fallback configuration. Do not pass invalid playbook families.
        if config.get("offense_style") not in offense_catalog:
            config.pop("offense_style", None)
        if config.get("defense_style") not in defense_catalog:
            config.pop("defense_style", None)
        plans[team] = config
    return plans


def planned_schools(dynasty, year):
    """Existing coaching history is serialized by both save paths."""
    return (dynasty.coaching_history.get(year, {}) or {}).get("planned_schools", {})
