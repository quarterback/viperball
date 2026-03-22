"""
EPA — Expected Points Added

Analytics engine for Viperball, modeled after real NFL analytics.

Key concepts:
  - EP (Expected Points): How many points a league-average offense would
    score from a given field position + down. Calibrated for 6-down,
    20-yards-to-gain, 9-point TD Viperball.
  - EPA (Expected Points Added): How much each play changes the offense's
    expected point output. Positive = moved closer to scoring, negative =
    lost ground or turned it over. A TD from midfield is a huge EPA
    because you scored 9 points when only ~2 were expected.
  - Success Rate: % of plays with positive EPA (moved the chains).
    Healthy offenses: 45-55%.
  - Explosiveness: Average EPA on successful plays only. Measures
    big-play ability independent of consistency.
"""

EP_TABLE = {
    1: 0.05,
    5: 0.15,
    10: 0.3,
    15: 0.5,
    20: 0.7,
    25: 0.9,
    30: 1.1,
    35: 1.4,
    40: 1.7,
    45: 2.0,
    50: 2.3,
    55: 2.7,
    60: 3.1,
    65: 3.6,
    70: 4.1,
    75: 4.7,
    80: 5.4,
    85: 6.2,
    90: 7.1,
    95: 8.1,
    99: 9.0,
}

DOWN_MULTIPLIER = {
    1: 1.00,
    2: 0.97,
    3: 0.93,
    4: 0.85,
    5: 0.72,
    6: 0.50,
}

POINTS = {
    "touchdown": 9,
    "snapkick": 5,
    "field_goal": 3,
    "safety": 2,
    "pindown": 1,
    "strike": 0.5,
}

_SORTED_KEYS = sorted(EP_TABLE.keys())


def calculate_ep(yardline: int, down: int) -> float:
    """Expected Points from a given field position and down."""
    down = max(1, min(6, down))
    yardline = max(1, min(99, yardline))

    if yardline <= _SORTED_KEYS[0]:
        base_ep = EP_TABLE[_SORTED_KEYS[0]]
    elif yardline >= _SORTED_KEYS[-1]:
        base_ep = EP_TABLE[_SORTED_KEYS[-1]]
    else:
        for i in range(len(_SORTED_KEYS) - 1):
            if _SORTED_KEYS[i] <= yardline <= _SORTED_KEYS[i + 1]:
                lo, hi = _SORTED_KEYS[i], _SORTED_KEYS[i + 1]
                ratio = (yardline - lo) / (hi - lo)
                base_ep = EP_TABLE[lo] + ratio * (EP_TABLE[hi] - EP_TABLE[lo])
                break
        else:
            base_ep = EP_TABLE[_SORTED_KEYS[-1]]

    return round(base_ep * DOWN_MULTIPLIER[down], 3)


def calculate_epa(play_data: dict) -> float:
    """Calculate the EP change (EPA) for a single play."""
    ep_before = play_data["ep_before"]
    result = play_data.get("result", "")

    if result in ("touchdown", "punt_return_td"):
        delta = POINTS["touchdown"] - ep_before
    elif result == "successful_kick":
        kick_type = play_data.get("play_type", "")
        pts = POINTS["snapkick"] if kick_type == "drop_kick" else POINTS["field_goal"]
        delta = pts - ep_before
    elif result == "safety":
        delta = POINTS["safety"] - ep_before
    elif result == "pindown":
        delta = POINTS["pindown"] - ep_before
    elif result == "fumble":
        delta = POINTS["strike"] - ep_before
    elif result in ("turnover_on_downs", "chaos_recovery"):
        delta = 0 - ep_before
    elif result == "punt":
        delta = 0 - ep_before
    else:
        ep_after = play_data.get("ep_after", 0)
        delta = ep_after - ep_before

    return round(delta, 3)


def calculate_drive_epa(plays: list) -> float:
    """Sum of per-play EP deltas for a drive."""
    return round(sum(p.get("epa", 0) for p in plays), 3)


def calculate_game_epa(all_plays: list, team: str) -> dict:
    """Aggregate EPA / success-rate / explosiveness for one team in a game.

    Returns dict with both legacy keys (total_vpa, etc.) and primary
    keys (wpa/epa, success_rate, explosiveness).
    """
    team_plays = [p for p in all_plays if p.get("possession") == team]
    if not team_plays:
        return {
            "wpa": 0.0,
            "wpa_per_play": 0.0,
            "offense_wpa": 0.0,
            "special_teams_wpa": 0.0,
            "success_rate": 0.0,
            "explosiveness": 0.0,
            "total_plays": 0,
            # Legacy aliases so old UI code doesn't crash during migration
            "total_vpa": 0.0,
            "vpa_per_play": 0.0,
            "offense_vpa": 0.0,
            "special_teams_vpa": 0.0,
            "total_epa": 0.0,
            "epa_per_play": 0.0,
            "offense_epa": 0.0,
            "special_teams_epa": 0.0,
            "chaos_epa": 0.0,
        }

    kick_types = ["punt", "drop_kick", "place_kick"]

    all_deltas = [p.get("epa", 0) for p in team_plays]
    total_wpa = sum(all_deltas)

    offense_plays = [p for p in team_plays if p.get("play_type") not in kick_types]
    special_plays = [p for p in team_plays if p.get("play_type") in kick_types]
    chaos_plays = [p for p in team_plays if p.get("chaos_event", False)]

    offense_wpa = sum(p.get("epa", 0) for p in offense_plays)
    special_teams_wpa = sum(p.get("epa", 0) for p in special_plays)
    chaos_wpa = sum(p.get("epa", 0) for p in chaos_plays)

    successful_plays = [v for v in all_deltas if v > 0]
    success_rate = len(successful_plays) / max(1, len(all_deltas))
    explosiveness = sum(successful_plays) / max(1, len(successful_plays)) if successful_plays else 0.0

    return {
        # Primary fan-facing keys
        "wpa": round(total_wpa, 2),
        "wpa_per_play": round(total_wpa / max(1, len(team_plays)), 3),
        "offense_wpa": round(offense_wpa, 2),
        "special_teams_wpa": round(special_teams_wpa, 2),
        "success_rate": round(success_rate * 100, 1),
        "explosiveness": round(explosiveness, 3),
        "total_plays": len(team_plays),
        # Legacy aliases (backward compat)
        "total_vpa": round(total_wpa, 2),
        "vpa_per_play": round(total_wpa / max(1, len(team_plays)), 3),
        "offense_vpa": round(offense_wpa, 2),
        "special_teams_vpa": round(special_teams_wpa, 2),
        "total_epa": round(total_wpa, 2),
        "epa_per_play": round(total_wpa / max(1, len(team_plays)), 3),
        "offense_epa": round(offense_wpa, 2),
        "special_teams_epa": round(special_teams_wpa, 2),
        "chaos_epa": round(chaos_wpa, 2),
    }
