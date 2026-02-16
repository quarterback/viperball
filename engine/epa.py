import random

EP_BY_YARDLINE = {
    1: 0.1, 10: 0.3,
    20: 0.6,
    30: 0.9,
    40: 1.3,
    50: 1.8,
    60: 2.4,
    70: 3.2,
    80: 4.0,
    90: 5.0,
    99: 6.5
}

DOWN_MULTIPLIER = {
    1: 1.00,
    2: 0.92,
    3: 0.78,
    4: 0.60,
    5: 0.35
}

POINTS = {
    "touchdown": 9,
    "snapkick": 5,
    "field_goal": 3,
    "safety": 2,
    "pindown": 1,
    "strike": 0.5
}

_SORTED_KEYS = sorted(EP_BY_YARDLINE.keys())


def calculate_ep(yardline, down):
    down = max(1, min(5, down))
    yardline = max(1, min(99, yardline))
    for i in range(len(_SORTED_KEYS) - 1):
        if _SORTED_KEYS[i] <= yardline <= _SORTED_KEYS[i + 1]:
            low_y, high_y = _SORTED_KEYS[i], _SORTED_KEYS[i + 1]
            low_ep, high_ep = EP_BY_YARDLINE[low_y], EP_BY_YARDLINE[high_y]
            ratio = (yardline - low_y) / (high_y - low_y)
            base_ep = low_ep + ratio * (high_ep - low_ep)
            return round(base_ep * DOWN_MULTIPLIER[down], 3)
    return round(EP_BY_YARDLINE[99] * DOWN_MULTIPLIER[down], 3)


def calculate_epa(play_data):
    ep_before = play_data["ep_before"]
    result = play_data.get("result", "")
    laterals = play_data.get("laterals", 0)
    is_chaos = play_data.get("chaos_event", False)

    if result == "touchdown" or result == "punt_return_td":
        epa = POINTS["touchdown"] - ep_before
    elif result == "successful_kick":
        kick_type = play_data.get("play_type", "")
        if kick_type == "drop_kick":
            epa = POINTS["snapkick"] - ep_before
        else:
            epa = POINTS["field_goal"] - ep_before
    elif result == "safety":
        epa = POINTS["safety"] - ep_before
    elif result == "pindown":
        opp_yard = 100 - 20
        ep_opponent = -calculate_ep(opp_yard, 1)
        epa = POINTS["pindown"] + ep_opponent - ep_before
    elif result == "fumble":
        opp_yard = 100 - play_data.get("field_position_after", 50)
        ep_opponent = -calculate_ep(opp_yard, 1)
        epa = POINTS["strike"] + ep_opponent - ep_before
    elif result in ("turnover_on_downs", "chaos_recovery"):
        opp_yard = 100 - play_data.get("field_position_after", 50)
        ep_after = -calculate_ep(opp_yard, 1)
        epa = ep_after - ep_before
    elif result == "punt":
        opp_yard = 100 - play_data.get("field_position_after", 50)
        ep_after = -calculate_ep(opp_yard, 1)
        epa = ep_after - ep_before
    else:
        ep_after = play_data.get("ep_after", 0)
        epa = ep_after - ep_before

    if laterals > 1:
        lateral_penalty = 0.03 * (laterals - 1)
        epa -= lateral_penalty

    if is_chaos:
        epa += random.uniform(0.1, 0.4)

    return round(epa, 3)


def calculate_drive_epa(plays):
    return round(sum(p.get("epa", 0) for p in plays), 3)


def calculate_game_epa(all_plays, team):
    team_plays = [p for p in all_plays if p.get("possession") == team]

    total_epa = sum(p.get("epa", 0) for p in team_plays)

    run_types = ["run", "lateral_chain"]
    kick_types = ["punt", "drop_kick", "place_kick"]

    offense_plays = [p for p in team_plays if p.get("play_type") not in kick_types]
    special_plays = [p for p in team_plays if p.get("play_type") in kick_types]
    chaos_plays = [p for p in team_plays if p.get("chaos_event", False)]

    offense_epa = sum(p.get("epa", 0) for p in offense_plays)
    special_teams_epa = sum(p.get("epa", 0) for p in special_plays)
    chaos_epa = sum(p.get("epa", 0) for p in chaos_plays)

    return {
        "total_epa": round(total_epa, 2),
        "offense_epa": round(offense_epa, 2),
        "special_teams_epa": round(special_teams_epa, 2),
        "chaos_epa": round(chaos_epa, 2),
        "epa_per_play": round(total_epa / max(1, len(team_plays)), 3),
        "total_plays": len(team_plays),
    }
