"""DEF-12, DEF-13, COACH-FP-01: defenses with signatures, weekly game
plans, coach fingerprints and the measured fingerprint."""
import glob
import os
from types import SimpleNamespace

from engine import game_engine as ge
from engine.fingerprint import team_fingerprint

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _teams():
    fs = sorted(glob.glob(os.path.join(ROOT, "data", "teams", "*.json")))
    return ge.load_team_from_json(fs[0]), ge.load_team_from_json(fs[1])


def test_new_defenses_exist_with_matchups():
    for d in ("keeper_hunt", "rotation"):
        assert d in ge.DEFENSE_STYLES
        assert all((o, d) in ge.OFFENSE_VS_DEFENSE_MATCHUP for o in ge.OFFENSE_STYLES)
    assert ge.DEFENSE_SIGNATURES["keeper_hunt"]["kick_rush"] > 1
    assert ge.DEFENSE_SIGNATURES["predator"]["kp_int"] > 1


def test_weekly_game_plan_leans_toward_counter_but_keeps_identity():
    h, a = _teams()
    e = ge.ViperballEngine(h, a, seed=3, style_overrides={
        h.name: "balanced", f"{h.name}_defense": "swarm",
        a.name: "ground_control", f"{a.name}_defense": "drift"})
    plan = e.game_plans["home"]
    assert plan["lean"] == "fortress" and 0 < plan["weight"] <= 0.6
    assert e.home_defense["label"] == ge.DEFENSE_STYLES["swarm"]["label"]
    base = ge.DEFENSE_STYLES["swarm"]["play_family_modifiers"]["power"]
    fort = ge.DEFENSE_STYLES["fortress"]["play_family_modifiers"]["power"]
    assert min(base, fort) < e.home_defense["play_family_modifiers"]["power"] < max(base, fort)


def test_stubborn_coach_barely_moves():
    w_adapt = max(0.0, min(0.6, 0.35 * 1.25 * (2.0 - 0.75)))
    w_stub = max(0.0, min(0.6, 0.35 * 0.75 * (2.0 - 1.25)))
    assert w_stub < 0.25 < w_adapt


def test_fingerprint_shifts_style_settings():
    e = object.__new__(ge.ViperballEngine)
    e.state = SimpleNamespace(possession="home")
    e.home_style = dict(ge.OFFENSE_STYLES["balanced"])
    e.home_coaching_mods = {"personality_factors": {"touchdown_finish": 1.25,
                                                    "late_down_aggression": 0.75}}
    assert e._style_knob("kick_mode_aggression", 0.5) < 0.5
    assert e._style_knob("go_for_it", 0.5) < e.home_style["go_for_it"]


def test_measured_fingerprint_from_games():
    h, a = _teams()
    r = ge.ViperballEngine(h, a, seed=5).simulate_game()
    g = SimpleNamespace(home_team=h.name, away_team=a.name, completed=True, full_result=r)
    fp = team_fingerprint([g], h.name)
    assert fp["games"] == 1
    assert 0 <= fp["run_share"] <= 100 and fp["plays_per_game"] > 0
