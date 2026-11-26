from types import SimpleNamespace as NS
from engine.regional_polls import STATE_REGION, build_regional_polls


def test_regional_polls():
    states = {"A": "OR", "B": "WA", "C": "NY", "D": ""}
    standings = {n: NS(record_str="1-1", conference="Shared") for n in states}
    power = [("B", 60, 0), ("A", 59, 0), ("C", 50, 0), ("D", 40, 0)]
    game = NS(week=1, completed=True, is_fcs_game=False,
              home_team="A", away_team="B", home_score=30, away_score=20)
    prior = {"Pacific": [{"team_name": "B", "rank": 1}]}
    ranks = {n: i for i, (n, _, _) in enumerate(power, 1)}
    result = build_regional_polls(1, states, standings, [game], power, prior, ranks)
    assert result["Pacific"][0]["team_name"] == "A"
    assert result["Pacific"][0]["regional_record"] == "1-0"
    assert result["Pacific"][1]["rank_change"] == -1
    assert result["Pacific"][0]["regional_quality_wins"] == 1
    assert result["Mid-Atlantic"][0]["team_name"] == "C"
    assert all(r["team_name"] != "D" for rows in result.values() for r in rows)
    assert len(STATE_REGION) == 51
    earlier = build_regional_polls(0, states, standings, [game], power, {}, ranks)
    assert earlier["Pacific"][0]["regional_record"] == "0-0"
