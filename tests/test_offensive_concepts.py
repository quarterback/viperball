import random

import pytest

from engine.game_engine import V2_ENGINE_CONFIG, PlayFamily, ViperballEngine, load_team_from_json
from engine.offensive_concepts import (
    BOUNDARY_SWITCH, CARRY_RELEASE, CORNER_CHASE, KICK_AND_FOLLOW, PROTECT_BONUS,
    sequence_call,
)
from engine.playbook_catalog import get_package
from tests.test_team_installation import STATS, card, staff


def installed_engine(package_id, seed=1):
    from engine.team_installation import sync_installation

    home = load_team_from_json("data/teams/alabama.json")
    away = load_team_from_json("data/teams/duke.json")
    coaches = staff(card("home-oc", "oc"))
    package = get_package(package_id)
    school = package["origin_family"]
    home.installation = sync_installation(
        {}, home.name, coaches, school, "swarm", STATS,
        books={"offense": {"packages": [package_id], "preferred": package_id}},
    )
    home.installation["offense"]["packages"][0]["familiarity"] = 1.0
    game = ViperballEngine(
        home, away, seed=seed,
        style_overrides={home.name: school, f"{away.name}_defense": "blitz_pack"},
        home_coaching=coaches, away_coaching=staff(card("away-oc", "oc")),
    )
    game.home_oc_tactics["authority"] = 1.0
    return game


def called(game, package_id):
    for play in game.simulate_game()["play_by_play"]:
        call = play.get("offensive_call") or {}
        if call.get("package_id") == package_id:
            yield play, call


def test_kick_and_follow_resolves_a_keep_and_one_support_lateral():
    snaps = list(called(installed_engine(KICK_AND_FOLLOW), KICK_AND_FOLLOW))
    assert any(call.get("read") == "keep" and play["laterals"] is None for play, call in snaps)
    given = [(play, call) for play, call in snaps if call.get("read") == "lateral"
             and (play.get("penalty") or {}).get("nullified") is not True]
    assert given
    assert all(play["laterals"] == 1 and call["support_runner"] in play["players"]
               for play, call in given)


@pytest.mark.parametrize("package_id,payoff", [(BOUNDARY_SWITCH, "switch"), (CARRY_RELEASE, "release")])
def test_sequence_releases_only_after_two_setups_and_pressure(package_id, payoff):
    setup = [{"lane": "right", "pressed": True}]
    assert sequence_call(package_id, setup)["phase"] == "setup"
    assert sequence_call(package_id, setup + [{"lane": "right", "pressed": False}])["phase"] == "setup"
    planned = sequence_call(package_id, setup * 2)
    assert planned["phase"] == payoff and planned["lane"] == "left"

    snaps = list(called(installed_engine(package_id), package_id))
    assert any(call.get("setup_response") == "pressed" for _, call in snaps)
    assert any(call["design"]["phase"] == payoff and call["family_matched"] for _, call in snaps)


def test_bonus_protection_excludes_the_bonus_drive():
    game = installed_engine(PROTECT_BONUS)
    game.state.possession = "home"
    game.state.field_position = 30
    game.state.down = 1
    game.state.yards_to_go = 20
    game._bonus_recipient = "home"
    game._bonus_drives_remaining = 1
    game._offensive_package_rng["home"] = random.Random(1)
    game._begin_offensive_plan()
    assert game._planned_choice("family") == "dive_option"
    game._is_bonus_drive = True
    game._begin_offensive_plan()
    assert game._active_offensive_plan is None


def test_corner_chase_dispatches_through_the_sixth_down_decision(monkeypatch):
    game = installed_engine(CORNER_CHASE)
    game.state.possession = "home"
    game.state.field_position = 52
    game.state.yards_to_go = 12
    game.state.time_remaining = 600
    game.state.down = 6
    game._offensive_package_rng["home"] = random.Random(1)
    monkeypatch.setattr(game, "_check_penalties", lambda *args, **kwargs: None)
    monkeypatch.setattr(game, "_drop_kick_success", lambda *args: 0.1)
    monkeypatch.setattr(game, "_place_kick_success", lambda *args: 0.1)
    monkeypatch.setattr(game, "calculate_block_probability", lambda **kwargs: 0)
    play = game.simulate_play()
    assert play.play_type == "punt"
    assert play.offensive_call["package_id"] == CORNER_CHASE
    assert play.offensive_call["family_matched"]
    assert play.special_teams_event["placement"] == "corner"
    assert play.special_teams_event["coverage_runner"]

    game.state.possession = "home"
    game.state.away_score = game.state.home_score + 1
    game.state.down = 6
    game.state.yards_to_go = 12
    game.state.field_position = 52
    assert game.select_kick_decision() is None


def test_delta_exit_preserves_the_selected_plan_on_a_sixth_down_punt(monkeypatch):
    game = installed_engine("pko_territory_exit")
    game.state.possession = "home"
    game.state.field_position = 52
    game.state.yards_to_go = 12
    game.state.down = 6
    game._delta_playbook_context = {"delta_bucket": "penalty_kill", "delta_cost": 19}
    game._offensive_package_rng["home"] = random.Random(1)
    monkeypatch.setattr(game, "_check_penalties", lambda *args, **kwargs: None)
    monkeypatch.setattr(game, "_drop_kick_success", lambda *args: 0.1)
    monkeypatch.setattr(game, "_place_kick_success", lambda *args: 0.1)
    play = game.simulate_play()
    assert play.play_type == "punt"
    assert play.offensive_call["package_id"] == "pko_territory_exit"
    assert play.offensive_call["delta_bucket"] == "penalty_kill"


def paired_engine(scheme, seed=14, tempo=80):
    from engine.custom_playbooks import validate_book
    from engine.team_installation import sync_installation

    home = load_team_from_json("data/teams/alabama.json")
    away = load_team_from_json("data/teams/duke.json")
    coaches = staff(card("home-oc", "oc"))
    coaches["oc"].personality_sliders["tempo_preference"] = tempo
    packages = [KICK_AND_FOLLOW, CARRY_RELEASE]
    book = validate_book({"version": 2, "name": "Split answers", "side": "offense", "school": "ghost",
                          "packages": packages, "preferred": CARRY_RELEASE,
                          "same_look_pairs": [{"formation": "split", "packages": packages}]})
    home.installation = sync_installation({}, home.name, coaches, "ghost", "swarm", STATS,
                                          books={"offense": book})
    for package in home.installation["offense"]["packages"]:
        package["familiarity"] = 1.0
    game = ViperballEngine(home, away, seed=seed, home_coaching=coaches,
                           away_coaching=staff(card("away-oc", "oc")),
                           style_overrides={home.name: "ghost", f"{away.name}_defense": scheme})
    game.home_oc_tactics["authority"] = 1.0
    return game


def test_paired_drive_changes_calls_against_observed_fronts(monkeypatch):
    def run(defense, enabled=True, tempo=80):
        random.seed(104)
        monkeypatch.setitem(V2_ENGINE_CONFIG, "paired_drive_plans_enabled", enabled)
        # This test is about pace after a probe. Keep the defense from also
        # learning the offense's side habit, which changes which probes gain.
        monkeypatch.setitem(V2_ENGINE_CONFIG, "side_learning_enabled", False)
        return paired_engine(defense, tempo=tempo).simulate_game()["play_by_play"]

    def calls(plays, status):
        return [(play, call, call["sequence"]) for play in plays
                if (call := play.get("offensive_call")) and call.get("offense_side") == "home"
                and (call.get("sequence") or {}).get("status") == status]

    crowded, spacious = run("fortress"), run("drift")
    counters = calls(crowded, "counter")
    assert len(counters) > len(calls(spacious, "counter")) > 0
    assert calls(spacious, "held_width")
    assert calls(crowded, "down_and_distance") and calls(crowded, "penalty")
    assert any(sequence["pace"]["choice"] == "quick" and sequence["pace"]["setup_seconds"] > 0
               for _, _, sequence in counters if sequence.get("pace"))
    for play, call, sequence in counters:
        assert call["play_caller_id"] == "home-oc"
        assert call["package_id"] == sequence["target"] and call["package_id"] in call["eligible"]
        assert play["formation"] == sequence["formation"] == "split"
        assert [call["choices"].get(key) for key in ("family", "kick_pass")] != list(sequence["action"])
        assert sequence["front"] in {"stacked", "aggressive"}
        assert play["possession_snap_index"] > sequence["snap"]
    assert not any((play.get("offensive_call") or {}).get("sequence")
                   for play in run("fortress", enabled=False))
    assert not any((sequence.get("pace") or {}).get("choice") == "quick"
                   for _, _, sequence in calls(run("fortress", tempo=25), "counter"))


def test_paired_action_filters_zero_weights_and_requires_ready_personnel():
    from engine.coach_drive import paired_options

    package = get_package("sa_vertical_shot")
    prior = ("kick_pass", "territory")
    assert paired_options(package, "kick_pass", {"territory": .4, "bomb": .2}, prior) == {"bomb": .2}
    assert paired_options(package, "kick_pass", {"territory": .4, "bomb": 0}, prior) == {}

    game = paired_engine("fortress")
    game.state.possession = "home"
    game.state.down = 2
    game._current_formation = "split"
    game._possession_snap_count = 2
    game._active_offensive_plan = get_package(KICK_AND_FOLLOW)
    game._drive_plan_trace = {"status": "counter", "formation": "split", "snap": 1,
                              "action": ("power", None), "gained": True}
    for player in game.home_team.players:
        if player.position == "Zeroback":
            player.game_energy = 20
    game._paired_pace(PlayFamily.KICK_PASS, "kick_lateral")
    assert game._drive_plan_trace["pace"] == {"choice": "normal", "reason": "personnel_readiness"}
