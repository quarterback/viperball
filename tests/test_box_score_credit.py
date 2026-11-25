"""Box score player credit reconciles with team totals for simulated games."""
import pytest

from engine import ViperballEngine, load_team_from_json

MATCHUPS = [("nyu", "wisconsin"), ("alabama", "air_force"), ("wisconsin", "alabama")]


@pytest.fixture(scope="module")
def games():
    results = []
    for i, (home, away) in enumerate(MATCHUPS):
        engine = ViperballEngine(load_team_from_json(f"data/teams/{home}.json"),
                                 load_team_from_json(f"data/teams/{away}.json"), seed=100 + i)
        results.append(engine.simulate_game())
    return results


def sides():
    return (("home", "away"), ("away", "home"))


def test_player_touchdowns_match_team_touchdowns(games):
    for g in games:
        for side, _ in sides():
            assert sum(p["tds"] for p in g["player_stats"][side]) == g["stats"][side]["touchdowns"]


def test_every_interception_and_pick_six_is_credited_to_a_defender(games):
    for g in games:
        for side, opp in sides():
            thrown = g["stats"][opp]
            players = g["player_stats"][side]
            assert sum(p["def_ints"] for p in players) == (
                thrown["kick_pass_interceptions"] + thrown["lateral_interceptions"])
            assert sum(p["int_return_tds"] for p in players) == thrown["int_return_tds"]


def test_timeouts_used_and_remaining_reconcile_per_half(games):
    for g in games:
        if any(p["quarter"] > 4 for p in g["play_by_play"]):
            continue
        logged = {s: sum(1 for t in g["timeout_log"] if t["team"] == s) for s in ("home", "away")}
        for side, _ in sides():
            st = g["stats"][side]
            assert st["timeouts_used"] == logged[side] == st["timeouts_1h"] + st["timeouts_2h"]
            assert st["timeouts_2h"] + st["timeouts_remaining"] == 4
            assert st["timeouts_remaining_period"] == "2H"


def test_lateral_percent_matches_lateral_efficiency(games):
    for g in games:
        for side, _ in sides():
            st = g["stats"][side]
            assert st["successful_laterals"] <= st["lateral_chains"]
            assert st["viperball_metrics"]["lateral_pct"] == st["lateral_efficiency"]


def test_defenders_receive_wpa(games):
    pure_defenders = [p for g in games for s in ("home", "away") for p in g["player_stats"][s]
                      if p["defensive_snaps"] > 0 and p["offensive_snaps"] == 0]
    assert any(p["wpa"] != 0 for p in pure_defenders)
