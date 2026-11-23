"""CCH-03: DC identity drives actual pre-snap choices and focused reads.

Tests avoid invented scoring targets. The full engine remains authoritative.
"""
from pathlib import Path
from types import SimpleNamespace
import random

import pytest

from engine.coaching import CoachCard
from engine.coach_tactics import (
    DEFENSIVE_ARCHETYPES, defensive_alignment_weights,
    defensive_blitz_probability, defensive_read_allocation,
    resolve_defensive_tactics,
)
from engine.game_engine import (
    DEFENSE_STYLES, PlayFamily, V2_ENGINE_CONFIG, ViperballEngine,
    load_team_from_json,
)


def coach(cid, role="dc", signature="selective_pressure"):
    c = CoachCard(
        coach_id=cid, first_name="Jordan", last_name="Smith",
        age=48, gender="female", role=role,
        classification="scheme_master", instincts=70, leadership=65,
        composure=72, rotations=65, development=68, recruiting=65,
        personality_sliders={"adaptability": 72, "stubbornness": 30,
                             "aggression": 70, "player_trust": 70},
    )
    if role == "dc":
        model = DEFENSIVE_ARCHETYPES[signature]
        c.tactical_profile["identity"]["defense_interpretation"] = signature
        c.tactical_profile["defense"] = {
            "pressure_bias": model["pressure_bias"],
            "run_support_bias": model["run_support_bias"],
            "coverage_focus": model["coverage_focus"],
            "read_focus": list(model["read_focus"]),
        }
    return c


def test_saved_dc_signature_survives_school_and_role_moves():
    c = coach("dc-17", signature="deep_coverage")
    before = c.to_dict()["tactical_profile"]
    c.team_name = "New College"
    c.role = "head_coach"
    assert CoachCard.from_dict(c.to_dict()).tactical_profile == before


def test_resolver_preserves_hc_control_and_missing_dc_is_neutral():
    dc = coach("dc-pressure")
    head = coach("hc", role="head_coach")
    alone = resolve_defensive_tactics({"dc": dc})
    constrained = resolve_defensive_tactics({"head_coach": head, "dc": dc})
    assert alone["authority"] == 1.0
    assert 0.4 <= constrained["authority"] < 1.0
    assert constrained["coach_id"] == dc.coach_id
    assert constrained["read_focus"] == ("kick_pass", "trick")
    assert resolve_defensive_tactics({"head_coach": head}) == {}
    assert resolve_defensive_tactics(None) == {}


def test_coaches_make_distinct_alignments_with_same_lockdown_scheme():
    pressure = resolve_defensive_tactics({"dc": coach("p")})
    wall = resolve_defensive_tactics({"dc": coach("w", signature="run_wall")})
    p = defensive_alignment_weights("spread", pressure,
                                     formation="split", yards_to_go=20)
    w = defensive_alignment_weights("spread", wall,
                                     formation="split", yards_to_go=20)
    assert p["aggressive"] > w["aggressive"]
    assert w["stacked"] > p["stacked"]
    assert p["spread"] > 0.70  # scheme look remains dominant
    assert w["spread"] > 0.70


def test_blitz_pressure_has_defensive_coverage_tradeoff():
    pressure = resolve_defensive_tactics({"dc": coach("p")})
    wall = resolve_defensive_tactics({"dc": coach("w", signature="run_wall")})
    a = defensive_blitz_probability(.10, pressure, "aggressive")
    b = defensive_blitz_probability(.10, wall, "spread")
    assert a > b
    assert defensive_blitz_probability(.45, pressure, "aggressive") <= .65
    assert defensive_blitz_probability(.08, wall, "spread") >= .02


def test_read_focus_reallocates_not_generally_increases_every_family():
    pressure = resolve_defensive_tactics({"dc": coach("p")})
    wall = resolve_defensive_tactics({"dc": coach("w", signature="run_wall")})
    assert defensive_read_allocation(pressure, "kick_pass") > 0
    assert defensive_read_allocation(pressure, "run") < 0
    assert defensive_read_allocation(wall, "run") > 0
    assert defensive_read_allocation(wall, "kick_pass") < 0
    assert defensive_read_allocation(pressure, "not-a-family") == 0


def minimal_engine(tactics):
    e = object.__new__(ViperballEngine)
    e.state = SimpleNamespace(possession="home", down=1, yards_to_go=20,
                              field_position=50, quarter=1)
    e.home_team = SimpleNamespace(defense_style="swarm", offense_style="balanced")
    e.away_team = SimpleNamespace(defense_style="lockdown", offense_style="balanced")
    e.home_defense = DEFENSE_STYLES["swarm"]
    e.away_defense = DEFENSE_STYLES["lockdown"]
    e.home_dc_tactics = {}
    e.away_dc_tactics = tactics
    e._away_dc_tactics_rng = random.Random(17)
    e._home_dc_tactics_rng = random.Random(19)
    e._dc_tactics_usage = {
        side: {"calls": 0, "alignments": {}, "blitz_calls": 0,
               "read_attempts": {}, "read_successes": {}}
        for side in ("home", "away")
    }
    e._active_defensive_call = None
    return e


def test_single_pre_snap_call_uses_known_formation_and_counts_defender():
    tactics = resolve_defensive_tactics({"dc": coach("p")})
    engine = minimal_engine(tactics)
    engine._begin_defensive_call("spread")
    call = engine._active_dc_call()
    assert call["defending_side"] == "away"
    assert call["alignment"] in ("balanced", "aggressive", "spread", "stacked")
    assert isinstance(call["blitz"], bool)
    assert engine._dc_tactics_usage["away"]["calls"] == 1
    assert sum(engine._dc_tactics_usage["away"]["alignments"].values()) == 1
    assert engine._dc_tactics_usage["home"]["calls"] == 0
    engine.state.possession = "away"
    assert engine._active_dc_call() == {}  # no stale snap after turnover


def test_without_dc_keeps_prior_alignment_and_does_not_roll():
    e = minimal_engine({})
    assert e._begin_defensive_call("spread") is None
    assert e._active_dc_call() == {}
    assert e._determine_defense_alignment() == "spread"
    assert e._dc_tactics_usage["away"]["calls"] == 0


def test_posture_controls_actual_run_alignment():
    e = minimal_engine(resolve_defensive_tactics({"dc": coach("p")}))
    e._begin_defensive_call("spread")
    assert e._determine_defense_alignment() == e._active_dc_call()["alignment"]


def test_read_focus_adjusts_canonical_read_and_preserves_existing_counter(monkeypatch):
    e = minimal_engine(resolve_defensive_tactics({"dc": coach("p")}))
    e._begin_defensive_call("spread")
    e._def_coaching_mods = lambda: {"instincts_factor": .5}
    e._get_defense_situational_boost = lambda d: 0.0
    e._get_defense_personnel_boost = lambda d: 0.0
    e._defense_read_counts = {
        "home": {"attempts": 0, "reads": 0},
        "away": {"attempts": 0, "reads": 0},
    }
    # Same draw lies between a focused vs a neglected read chance.
    monkeypatch.setattr(random, "random", lambda: .42)
    e.away_defense = dict(DEFENSE_STYLES["lockdown"],
                          read_success_rate=.42, gameplan_bias={})
    assert e.get_defensive_read(PlayFamily.KICK_PASS)
    assert not e.get_defensive_read(PlayFamily.POWER)
    assert e._defense_read_counts["away"]["attempts"] == 2
    assert e._dc_tactics_usage["away"]["read_attempts"] == {"kick_pass": 1, "run": 1}
    assert e._dc_tactics_usage["away"]["read_successes"] == {"kick_pass": 1, "run": 0}


def real_teams():
    paths = sorted((Path(__file__).resolve().parents[1] / "data" / "teams").glob("*.json"))
    return (load_team_from_json(str(paths[0]), fresh=False),
            load_team_from_json(str(paths[1]), fresh=False))


def test_full_engine_dc_calls_are_defender_attributed_and_visible():
    home, away = real_teams()
    dc = coach("defense-pressure")
    game = ViperballEngine(
        home, away, seed=20261123, neutral_site=True,
        away_coaching={"dc": dc},
        style_overrides={home.name: "boot_raid",
                         away.name + "_defense": "lockdown"},
    ).simulate_game()
    record = game["defensive_coach_tactics"]["away"]
    assert record["dc_id"] == dc.coach_id
    assert record["signature"] == "selective_pressure"
    assert record["calls"] > 0
    assert sum(record["alignments"].values()) == record["calls"]
    assert 0 <= record["blitz_calls"] <= record["calls"]
    assert game["defensive_coach_tactics"]["home"] == {}
    snaps = [p["defensive_call"] for p in game["play_by_play"]
             if p["defensive_call"] is not None]
    assert snaps and all(x["defending_side"] == "away" for x in snaps)
    assert any(v > 0 for v in record["read_attempts"].values())


def test_switch_off_restores_identical_seeded_game_for_two_dc_profiles(monkeypatch):
    monkeypatch.setitem(V2_ENGINE_CONFIG, "defensive_coach_tactics_enabled", False)
    home, away = real_teams()
    scores = []
    for style in ("selective_pressure", "run_wall"):
        game = ViperballEngine(
            home, away, seed=20261123, neutral_site=True,
            away_coaching={"dc": coach("same-" + style, signature=style)},
            style_overrides={home.name: "boot_raid",
                             away.name + "_defense": "lockdown"},
        ).simulate_game()
        assert game["defensive_coach_tactics"]["away"] == {}
        assert all(p["defensive_call"] is None for p in game["play_by_play"])
        scores.append((game["final_score"], game["stats"]["home"]["total_plays"]))
    assert scores[0] == scores[1]
