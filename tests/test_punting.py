import random

import engine.game_engine as G
from engine import punting as PUNT
from engine.game_engine import ViperballEngine, load_team_from_json


class Kicker:
    def __init__(self, name, kick=60, power=50, awareness=50):
        self.name = name
        self.player_id = name
        self.kick_power = kick
        self.kick_accuracy = kick
        self.kicking = kick
        self.power = power
        self.awareness = awareness


def test_punting_profile_is_stable_and_spread_across_a_roster():
    a = PUNT.punter_profile(Kicker("Ava Marsh"))
    assert a == PUNT.punter_profile(Kicker("Ava Marsh"))
    ratings = [PUNT.punter_profile(Kicker(f"Player {i}")).rating for i in range(300)]
    assert max(ratings) - min(ratings) >= 25          # real gaps between players
    styles = {PUNT.punter_profile(Kicker(f"Player {i}")).style for i in range(300)}
    assert {"aussie", "continental"} <= styles


def test_each_style_calls_its_own_punts():
    aussie = PUNT.PuntProfile(70, 80, 75, "aussie")
    continental = PUNT.PuntProfile(80, 70, 75, "continental")
    rng = random.Random(1)
    assert PUNT.choose_type(60, aussie, rng=rng) == "drop"
    assert PUNT.choose_type(60, continental, rng=rng) == "spiral"
    assert PUNT.choose_type(20, continental, rng=rng) == "spiral"
    assert PUNT.choose_type(20, aussie, kick_rush=1.3, rng=rng) == "rugby"


def test_a_drop_punt_pins_deeper_and_returns_shorter_than_a_spiral():
    prof = PUNT.PuntProfile(70, 70, 70, "both")
    drop_spot, _ = PUNT.expected_opponent_spot(60, prof, "drop")
    spiral_spot, _ = PUNT.expected_opponent_spot(60, prof, "spiral")
    assert drop_spot < spiral_spot
    assert PUNT.RETURN_MULT["drop"] < PUNT.RETURN_MULT["spiral"]
    assert PUNT.BLOCK_MULT["rugby"] < PUNT.BLOCK_MULT["spiral"]


def test_coaching_traits_set_the_ends_of_the_philosophy():
    assert PUNT.philosophy({"hidden_trait_effects": {"punt_weight_multiplier": 0.5}}) == -1.0
    assert PUNT.philosophy({"hidden_trait_effects": {"punt_weight_multiplier": 1.5}}) == 1.0
    assert PUNT.philosophy_label(-1.0) == "Never punts"
    assert PUNT.philosophy_label(1.0) == "Field position first"
    assert -0.95 < PUNT.philosophy({}) < 0.95


def _punts(phil, games=6):
    orig = G.ViperballEngine._punt_philosophy
    G.ViperballEngine._punt_philosophy = lambda self: phil
    try:
        out = []
        for seed in range(games):
            home = load_team_from_json("data/teams/alabama.json")
            away = load_team_from_json("data/teams/duke.json")
            r = ViperballEngine(home, away, seed=40 + seed).simulate_game()
            out += [p for p in r["play_by_play"] if p["play_type"] == "punt"]
        return out
    finally:
        G.ViperballEngine._punt_philosophy = orig


def test_a_coach_who_never_punts_never_punts():
    assert _punts(-1.0) == []


def test_punts_come_on_sixth_down_or_as_quick_kicks():
    punts = _punts(1.0)
    assert punts
    for p in punts:
        st = p.get("special_teams_event") or {}
        if st.get("punt_type") == "rouge":
            continue                       # last play of a half
        if st.get("punt_type") == "quick":
            assert st.get("quick_kick") in ("protect_lead", "wind")
            continue
        assert p["down"] == 6 or p["result"] in ("pindown", "punt_return_td")


def test_quick_kicks_only_in_extreme_spots():
    assert PUNT.quick_kick_spot(5, 20, 14, 4, 200, 4, 0, False, 0.4) == "protect_lead"
    assert PUNT.quick_kick_spot(5, 40, 12, 1, 20, 0, 15, True, 0.4) == "wind"
    assert PUNT.quick_kick_spot(4, 20, 14, 4, 200, 4, 0, False, 0.4) is None
    assert PUNT.quick_kick_spot(5, 20, 14, 4, 200, 4, 0, False, -1.0) is None
    assert PUNT.quick_kick_spot(5, 20, 14, 2, 200, 4, 0, False, 0.4) is None
