"""CCH-03/04 integration: installed DC experience constrains her calls.

No new playbook engine is introduced: CCH-04 supplies familiarity, CCH-03
supplies the single defensive pre-snap decision and existing contests.
"""
from copy import deepcopy
from pathlib import Path

import pytest

from engine.coach_tactics import resolve_defensive_tactics
from engine.coaching import CoachCard
from engine.game_engine import V2_ENGINE_CONFIG, ViperballEngine, load_team_from_json
from engine.team_installation import new_installation, defense_execution_factor


def make_dc():
    return CoachCard(
        coach_id="dc-cch03-cch04", first_name="Dana", last_name="Martin",
        gender="female", age=46, role="dc", classification="scheme_master",
        instincts=75, leadership=70, composure=72, rotations=67,
        development=71, recruiting=63,
        personality_sliders={"aggression": 78, "risk_tolerance": 65,
                             "adaptability": 72, "stubbornness": 30,
                             "player_trust": 72},
    )


def team_pair():
    base = Path(__file__).resolve().parents[1] / "data" / "teams"
    names = sorted(base.glob("*.json"))
    return (load_team_from_json(str(names[0]), fresh=False),
            load_team_from_json(str(names[1]), fresh=False))


def game_with_dc(familiarity=None):
    home, away = team_pair()
    dc = make_dc()
    staff = {"dc": dc}
    if familiarity is not None:
        install = new_installation(
            away.name, staff, offense_family="balanced",
            defense_family="lockdown", year=2026,
        )
        install["defense"]["familiarity"] = familiarity
        install["defense"]["family_familiarity"] = 1.0
        away.installation = install
    game = ViperballEngine(
        deepcopy(home), deepcopy(away), seed=20261123,
        neutral_site=True, weather="clear", away_coaching=staff,
        style_overrides={home.name: "boot_raid",
                         away.name + "_defense": "lockdown"},
    ).simulate_game()
    return game, dc, getattr(away, "installation", None)


@pytest.mark.parametrize("familiarity", [0.30, 0.75, 1.00])
def test_dc_familiarity_scales_saved_signature_and_keeps_actual_calls(familiarity):
    game, dc, install = game_with_dc(familiarity)
    summary = game["defensive_coach_tactics"]["away"]
    old_authority = resolve_defensive_tactics({"dc": dc})["authority"]
    factor = defense_execution_factor(install)
    assert summary["dc_id"] == dc.coach_id
    assert summary["installation_execution_factor"] == pytest.approx(factor)
    assert summary["authority"] == pytest.approx(round(old_authority * factor, 3))
    assert summary["calls"] > 0
    assert sum(summary["alignments"].values()) == summary["calls"]
    assert summary["blitz_calls"] <= summary["calls"]
    assert any(p["defensive_call"] for p in game["play_by_play"])


def test_without_installation_old_cch03_behavior_is_unchanged():
    game, dc, _ = game_with_dc()
    summary = game["defensive_coach_tactics"]["away"]
    assert summary["authority"] == resolve_defensive_tactics({"dc": dc})["authority"]
    assert summary["installation_execution_factor"] == 1.0


def test_switch_disables_dc_installation_only_not_existing_defensive_calls(monkeypatch):
    monkeypatch.setitem(V2_ENGINE_CONFIG, "team_installation_enabled", False)
    game, dc, _ = game_with_dc(0.30)
    summary = game["defensive_coach_tactics"]["away"]
    assert summary["authority"] == resolve_defensive_tactics({"dc": dc})["authority"]
    assert summary["calls"] > 0
    assert summary["installation_execution_factor"] == 1.0


def test_defensive_signature_switch_is_independent(monkeypatch):
    monkeypatch.setitem(V2_ENGINE_CONFIG, "defensive_coach_tactics_enabled", False)
    game, _, _ = game_with_dc(0.30)
    assert game["defensive_coach_tactics"]["away"] == {}
    assert not any(p["defensive_call"] for p in game["play_by_play"])
