import random

from engine import field_width as FW
from engine.game_engine import Penalty, Play, ViperballEngine, load_team_from_json


class Defender:
    def __init__(self, speed):
        self.speed = speed


def lineup(linemen=5, midfield=4, keepers=2):
    return ([(Defender(60), "Defensive Line") for _ in range(linemen)]
            + [(Defender(80 - i), "Midfield") for i in range(midfield)]
            + [(Defender(75), "Keeper") for _ in range(keepers)])


def test_snaps_are_spotted_between_the_hashes():
    assert FW.snap_spot(2) == FW.LEFT_HASH
    assert FW.snap_spot(FW.FIELD_WIDTH) == FW.RIGHT_HASH
    assert FW.snap_spot(FW.MIDDLE) == FW.MIDDLE
    assert FW.side_label(FW.LEFT_HASH, "left") == "boundary"
    assert FW.side_label(FW.LEFT_HASH, "right") == "field"
    assert FW.side_label(FW.MIDDLE, "left") == "middle"


def test_every_defender_gets_one_channel():
    players = lineup()
    for alignment in ("balanced", "stacked", "spread", "aggressive"):
        ch = FW.assign_channels(players, FW.LEFT_HASH, alignment, 1.0, random.Random(1))
        assert len(ch["by_id"]) == len(players)
        assert sum(ch["counts"].values()) == len(players)


def test_a_sharp_coordinator_leaves_the_offense_little_on_either_side():
    players = lineup()
    sharp = FW.assign_channels(players, FW.LEFT_HASH, "balanced", 1.0, random.Random(1))
    # From the left hash a sharp split puts more players on the wide side.
    assert sharp["counts"]["right"] > sharp["counts"]["left"]
    best = max(sharp["value"].values())
    rng = random.Random(4)
    worst = max(max(FW.assign_channels(players, FW.LEFT_HASH, "balanced", 0.0, rng)["value"].values())
                for _ in range(200))
    assert worst > best


def test_offense_reads_the_split_and_a_planned_lane_wins():
    channels = {"value": {"left": 0.15, "right": -0.15}, "counts": {}, "fair": {}}
    rng = random.Random(2)
    picks = [FW.choose_side(channels, 1.0, rng, x=FW.MIDDLE) for _ in range(500)]
    assert picks.count("left") > 350
    assert FW.choose_side(channels, 1.0, rng, planned="right") == "right"


def test_a_wiped_out_play_keeps_the_snap_spot():
    play = Play(1, 1, 600, "home", 40, 1, 20, "run", "sweep_option", [], 12, "gain", "")
    play.penalty = Penalty(name="Holding", yards=10, on_team="home", player="", nullified=True)
    x, out = FW.end_spot(FW.LEFT_HASH, {"side": "left"}, play, random.Random(1))
    assert x == FW.LEFT_HASH and not out


def test_games_track_the_ball_across_the_field():
    home = load_team_from_json("data/teams/alabama.json")
    away = load_team_from_json("data/teams/duke.json")
    result = ViperballEngine(home, away, seed=11).simulate_game()
    assert result["field_width"]["unset_plays"] == 0
    live = [p for p in result["play_by_play"]
            if p["play_type"] in ("run", "kick_pass", "lateral_chain") and p.get("width")]
    assert live
    for p in live:
        w = p["width"]
        assert FW.LEFT_HASH <= w["snap_x"] <= FW.RIGHT_HASH
        assert 0 <= w["end_x"] <= FW.FIELD_WIDTH
        assert w["side"] in ("left", "right", "middle")
    assert {p["width"]["hash"] for p in live} >= {"left_hash", "right_hash"}


def test_stats_site_shows_field_width(tmp_path, monkeypatch):
    monkeypatch.setenv("VIPERBALL_DB_PATH", str(tmp_path / "data.db"))
    from urllib.parse import quote
    from fastapi.testclient import TestClient
    import api.main as api
    client = TestClient(api.app)
    sid = client.post("/sessions", json={}).json()["session_id"]
    client.post(f"/sessions/{sid}/season", json={}).raise_for_status()
    client.post(f"/sessions/{sid}/season/simulate-week", json={}).raise_for_status()
    base = f"/stats/data/college/{sid}"
    games = client.get(base + "/games.json").json()
    plays = client.get(base + "/plays.json", params={"team": games[0]["home"]}).json()
    assert any(p["side_label"] in ("field", "boundary") for p in plays)
    assert all(p["hash"] in ("left_hash", "middle", "right_hash", None) for p in plays)

    game = client.get(f"/stats/college/{sid}/game/{games[0]['week']}/0")
    assert game.status_code == 200
    assert "Field width" in game.text and "Wide side" in game.text and "Left hash" in game.text
    team = client.get(f"/stats/college/{sid}/team/{quote(games[0]['home'])}")
    assert team.status_code == 200
    assert "Defense, by where opponents attacked" in team.text


def test_kicks_from_a_hash_see_a_narrower_target():
    assert FW.kick_angle_factor(FW.MIDDLE, 20) == 1.0
    assert FW.kick_angle_factor(FW.LEFT_HASH, 20) < FW.kick_angle_factor(FW.LEFT_HASH, 45) < 1.0
    home = load_team_from_json("data/teams/alabama.json")
    away = load_team_from_json("data/teams/duke.json")
    eng = ViperballEngine(home, away, seed=1)
    eng.state.ball_x = FW.MIDDLE
    middle = eng._place_kick_success(25, 80)
    eng.state.ball_x = FW.LEFT_HASH
    assert eng._place_kick_success(25, 80) < middle


def test_the_sideline_closes_off_returns():
    near = FW.return_plan(4.0, 1.0)
    open_field = FW.return_plan(FW.MIDDLE, 1.0)
    assert near["mod"] < open_field["mod"]
    assert near["dir"] == 1  # runs back toward the open field
    assert FW.return_plan(FW.MIDDLE, 1.3)["mod"] < open_field["mod"]
    end = FW.return_end(4.0, near, 20, random.Random(1))
    assert 4.0 < end <= FW.FIELD_WIDTH


def test_a_defense_that_has_seen_the_offense_shifts_a_player():
    players = lineup()
    rng = random.Random(5)
    base = FW.assign_channels(players, FW.LEFT_HASH, "balanced", 1.0, random.Random(5))
    shifted = FW.assign_channels(players, FW.LEFT_HASH, "balanced", 1.0, rng, lean=1.0)
    assert shifted["lean"] == 1
    assert shifted["counts"]["right"] == base["counts"]["right"] + 1
    toward_short = FW.assign_channels(players, FW.LEFT_HASH, "balanced", 1.0, random.Random(5), lean=-1.0)
    assert toward_short["counts"]["left"] == base["counts"]["left"] + 1
