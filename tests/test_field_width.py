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
