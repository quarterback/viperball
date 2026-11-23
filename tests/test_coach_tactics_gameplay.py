"""CCH-02: real offensive choice integration, gates, coach authority, role ordering."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import random

import pytest

from engine.coach_tactics import (
    OFFENSIVE_ARCHETYPES, apply_weight_bias, apply_featured_position_bias,
    resolve_offensive_tactics,
)
from engine.coaching import CoachCard
from engine.game_engine import (
    V2_ENGINE_CONFIG, ViperballEngine, load_team_from_json, PlayFamily,
)


def make_coach(cid, role="oc"):
    return CoachCard(
        coach_id=cid, first_name="Sam", last_name=cid, gender="female", age=46,
        role=role, classification="scheme_master",
        instincts=75, leadership=68, composure=70, rotations=65,
        development=64, recruiting=61,
        personality_sliders={"aggression": 60, "risk_tolerance": 65,
                             "stubbornness": 25, "player_trust": 75,
                             "adaptability": 70},
    )


def coach_variant(name, cid):
    coach = make_coach(cid)
    archetype = OFFENSIVE_ARCHETYPES[name]
    coach.tactical_profile["identity"]["offense_interpretation"] = name
    coach.tactical_profile["offense"] = {
        "formation_bias": dict(archetype["formation_bias"]),
        "family_bias": dict(archetype["family_bias"]),
        "kick_pass_bias": dict(archetype["kick_pass_bias"]),
        "featured_position": archetype["featured_position"],
    }
    return coach


def test_weight_bias_preserves_zero_and_family_keys():
    source = {"kick_pass": 0.0, "power": 0.5, "sweep_option": 0.25}
    out = apply_weight_bias(source, {"kick_pass": .99, "power": .99,
                                     "sweep_option": -1, "trick_play": .99},
                            authority=1.0)
    assert source["power"] == 0.5
    assert out["kick_pass"] == 0.0  # never revive illegal zero
    assert out["power"] == pytest.approx(0.6)  # 20% max gain
    assert out["sweep_option"] == pytest.approx(0.2)  # 20% max reduction
    assert "trick_play" not in out


def test_coordinator_owns_prefs_hc_limits_authority():
    oc = coach_variant("vertical_attack", "vertical-001")
    hc = make_coach("head-001", role="head_coach")
    no_hc = resolve_offensive_tactics({"oc": oc})
    both = resolve_offensive_tactics({"head_coach": hc, "oc": oc})
    assert no_hc["authority"] == 1.0
    assert 0.4 <= both["authority"] < 1.0
    assert both["coach_id"] == "vertical-001"
    assert both["signature"] == "vertical_attack"
    assert both["kick_pass_bias"]["bomb"] > 0
    assert resolve_offensive_tactics({"head_coach": hc}) == {}
    assert resolve_offensive_tactics(None) == {}


def test_featured_position_respects_existing_candidate_pool():
    eligible = [SimpleNamespace(position="Halfback"), SimpleNamespace(position="Viper")]
    assert apply_featured_position_bias(eligible, [0.0, 4], "Viper") == [0.0, pytest.approx(4.72)]
    assert apply_featured_position_bias(eligible, [4, 4], "Keeper") == [4, 4]


def light_engine(tactics):
    engine = object.__new__(ViperballEngine)
    engine.state = SimpleNamespace(
        possession="home", quarter=1, time_remaining=540,
        field_position=50, yards_to_go=20, down=1,
    )
    engine.home_oc_tactics = tactics
    engine.away_oc_tactics = {}
    engine._coach_tactics_usage = {
        "home": {"formation": {}, "family": {}, "kick_pass": {},
                 "featured_rushes": 0, "featured_targets": 0},
        "away": {"formation": {}, "family": {}, "kick_pass": {},
                 "featured_rushes": 0, "featured_targets": 0},
    }
    engine.home_style = {
        "formation_weights": {"tight": .25, "split": .25, "spread": .25, "heavy": .25},
        "kick_pass_weights": {
            "quick_kick": 1, "territory": 1, "bomb": 1, "kick_lateral": 1,
        },
    }
    engine._get_score_diff = lambda: 0
    engine._lead_management_modifiers = lambda: {}
    engine._resolve_weight_mode = lambda: "base"
    engine._current_style_name = lambda: "balanced"
    engine._def_dc_gameplan = lambda: {}
    engine.weather = "clear"
    return engine


def test_formation_selection_uses_oc_bias_after_situational(monkeypatch):
    vertical = resolve_offensive_tactics({"oc": coach_variant("vertical_attack", "one")})
    control = resolve_offensive_tactics({"oc": coach_variant("territory_control", "two")})
    weights_seen = []

    def choose(keys, weights, k=1):
        weights_seen.append(dict(zip(keys, weights)))
        return [keys[0]]

    monkeypatch.setattr(random, "choices", choose)
    a, b = light_engine(vertical), light_engine(control)
    a.select_formation()
    b.select_formation()
    assert weights_seen[0]["spread"] > weights_seen[1]["spread"]
    assert a._coach_tactics_usage["home"]["formation"]["tight"] == 1


def test_kick_pass_subfamily_selection_uses_same_coach_profile(monkeypatch):
    vertical = resolve_offensive_tactics({"oc": coach_variant("vertical_attack", "one")})
    territory = resolve_offensive_tactics({"oc": coach_variant("territory_control", "two")})
    captures = []

    def choose(keys, weights, k=1):
        captures.append({key.value: weight for key, weight in zip(keys, weights)})
        return [keys[0]]

    monkeypatch.setattr(random, "choices", choose)
    a, b = light_engine(vertical), light_engine(territory)
    kicker = SimpleNamespace(kick_power=90)
    a._select_kick_pass_subfamily(kicker)
    b._select_kick_pass_subfamily(kicker)
    assert captures[0]["bomb"] > captures[1]["bomb"]
    assert captures[0]["quick_kick"] < captures[1]["quick_kick"]


def test_default_without_oc_keeps_neutral_selection(monkeypatch):
    engine = light_engine({})
    assert engine._current_oc_tactics() == {}
    before = deepcopy(engine.home_style["formation_weights"])
    engine.select_formation()
    assert engine.home_style["formation_weights"] == before
    assert engine._coach_tactics_summary("home") == {}


def test_full_game_uses_final_scheme_for_role_assignment(monkeypatch):
    import engine.game_engine as module
    paths = sorted((Path(__file__).resolve().parents[1] / "data" / "teams").glob("*.json"))
    home = load_team_from_json(str(paths[0]), fresh=False)
    away = load_team_from_json(str(paths[1]), fresh=False)
    calls = []
    original = module.assign_game_roles

    def spy(team, scheme):
        calls.append((team.name, scheme, team.offense_style))
        return original(team, scheme)

    monkeypatch.setattr(module, "assign_game_roles", spy)
    staff = {"oc": coach_variant("vertical_attack", "oc-role-order")}
    engine = ViperballEngine(
        home, away, seed=91, home_coaching=staff,
        style_overrides={home.name: "boot_raid", away.name: "ground_pound"},
    )
    assert (home.name, "boot_raid", "boot_raid") in calls
    assert (away.name, "ground_pound", "ground_pound") in calls
    assert engine.home_oc_tactics["coach_id"] == "oc-role-order"
    assert engine.away_oc_tactics == {}


def test_full_game_exposes_real_oc_selection_counts():
    paths = sorted((Path(__file__).resolve().parents[1] / "data" / "teams").glob("*.json"))
    home = load_team_from_json(str(paths[0]), fresh=False)
    away = load_team_from_json(str(paths[1]), fresh=False)
    staff = {"oc": coach_variant("vertical_attack", "oc-integration")}
    game = ViperballEngine(
        home, away, seed=20261123, home_coaching=staff,
        style_overrides={home.name: "boot_raid", away.name: "balanced"},
    ).simulate_game()
    home_tactics = game["coach_tactics"]["home"]
    assert home_tactics["oc_id"] == "oc-integration"
    assert home_tactics["signature"] == "vertical_attack"
    assert sum(home_tactics["selected"]["formation"].values()) > 0
    assert sum(home_tactics["selected"]["family"].values()) > 0
    assert game["coach_tactics"]["away"] == {}
    assert "formation" in game["play_by_play"][0]
    assert "kick_pass_subfamily" in game["play_by_play"][0]


def test_seeded_game_control_identical_for_coaches_with_same_attributes(monkeypatch):
    # A coach's identifier must not change outcomes when her tactical
    # signature is switched off. The game-seeded per-side coaching RNG
    # makes the modifier and halftime preparation draws repeatable.
    monkeypatch.setitem(V2_ENGINE_CONFIG, "coach_tactics_enabled", False)
    paths = sorted((Path(__file__).resolve().parents[1] / "data" / "teams").glob("*.json"))
    home = load_team_from_json(str(paths[0]), fresh=False)
    away = load_team_from_json(str(paths[1]), fresh=False)
    hc = make_coach("same-hc", role="head_coach")
    scores = []
    for cid in ("one", "two"):
        oc = make_coach(cid)
        result = ViperballEngine(
            home, away, seed=20261123,
            home_coaching={"head_coach": hc, "oc": oc},
            style_overrides={home.name: "boot_raid", away.name: "balanced"},
            neutral_site=True,
        ).simulate_game()
        scores.append((result["final_score"], result["stats"]["home"]["total_plays"]))
    assert scores[0] == scores[1]
