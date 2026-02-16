"""
VPA — Viperball Points Added

Sabermetric efficiency system for Viperball. Measures how much value
each play produces relative to the expected outcome from that situation.

Key concepts:
  - EP (Expected Points): How many points a league-average offense would
    score from a given field position + down. Calibrated for 6-down,
    9-point TD Viperball.
  - VPA (Viperball Points Added): Points of value a play produced above
    or below expectation. Positive = good play, negative = bad play.
    Framed from the offense's perspective only — no double-counting
    of possession changes.
  - Success Rate: % of plays with VPA > 0 (offense improved its
    situation). Healthy offenses: 45-55%.
  - Explosiveness: Average VPA on successful plays only. Measures
    big-play ability.
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
    ep_before = play_data["ep_before"]
    result = play_data.get("result", "")

    if result in ("touchdown", "punt_return_td"):
        vpa = POINTS["touchdown"] - ep_before
    elif result == "successful_kick":
        kick_type = play_data.get("play_type", "")
        pts = POINTS["snapkick"] if kick_type == "drop_kick" else POINTS["field_goal"]
        vpa = pts - ep_before
    elif result == "safety":
        vpa = POINTS["safety"] - ep_before
    elif result == "pindown":
        vpa = POINTS["pindown"] - ep_before
    elif result == "fumble":
        vpa = POINTS["strike"] - ep_before
    elif result in ("turnover_on_downs", "chaos_recovery"):
        vpa = 0 - ep_before
    elif result == "punt":
        vpa = 0 - ep_before
    else:
        ep_after = play_data.get("ep_after", 0)
        vpa = ep_after - ep_before

    return round(vpa, 3)


def calculate_drive_epa(plays: list) -> float:
    return round(sum(p.get("epa", 0) for p in plays), 3)


def calculate_game_epa(all_plays: list, team: str) -> dict:
    team_plays = [p for p in all_plays if p.get("possession") == team]
    if not team_plays:
        return {
            "total_vpa": 0.0,
            "vpa_per_play": 0.0,
            "offense_vpa": 0.0,
            "special_teams_vpa": 0.0,
            "success_rate": 0.0,
            "explosiveness": 0.0,
            "total_plays": 0,
            "total_epa": 0.0,
            "epa_per_play": 0.0,
            "offense_epa": 0.0,
            "special_teams_epa": 0.0,
            "chaos_epa": 0.0,
        }

    kick_types = ["punt", "drop_kick", "place_kick"]

    all_vpa = [p.get("epa", 0) for p in team_plays]
    total_vpa = sum(all_vpa)

    offense_plays = [p for p in team_plays if p.get("play_type") not in kick_types]
    special_plays = [p for p in team_plays if p.get("play_type") in kick_types]
    chaos_plays = [p for p in team_plays if p.get("chaos_event", False)]

    offense_vpa = sum(p.get("epa", 0) for p in offense_plays)
    special_teams_vpa = sum(p.get("epa", 0) for p in special_plays)
    chaos_vpa = sum(p.get("epa", 0) for p in chaos_plays)

    successful_plays = [v for v in all_vpa if v > 0]
    success_rate = len(successful_plays) / max(1, len(all_vpa))
    explosiveness = sum(successful_plays) / max(1, len(successful_plays)) if successful_plays else 0.0

    return {
        "total_vpa": round(total_vpa, 2),
        "vpa_per_play": round(total_vpa / max(1, len(team_plays)), 3),
        "offense_vpa": round(offense_vpa, 2),
        "special_teams_vpa": round(special_teams_vpa, 2),
        "success_rate": round(success_rate * 100, 1),
        "explosiveness": round(explosiveness, 3),
        "total_plays": len(team_plays),
        "total_epa": round(total_vpa, 2),
        "epa_per_play": round(total_vpa / max(1, len(team_plays)), 3),
        "offense_epa": round(offense_vpa, 2),
        "special_teams_epa": round(special_teams_vpa, 2),
        "chaos_epa": round(chaos_vpa, 2),
    }
