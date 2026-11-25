"""PBK-05: offensive scripts are bounded pre-snap choices."""
import random
from copy import deepcopy

from engine import team_installation as ti
from engine.coach_tactics import apply_weight_bias
from engine.playbook_catalog import get_package


def package(pid, familiarity=1.0):
    return {**get_package(pid), "familiarity": familiarity}


def test_drive_scripts_require_both_catalog_conditions():
    for pid, required in [
        ("afl_kick_in_breakout", {"backed_up", "first_play_of_drive"}),
        ("afl_restart_go_to", {"after_score_restart", "first_play_of_drive"}),
        ("lax_fast_break", {"after_takeaway", "first_play_of_drive"}),
        ("league_last_tackle_kick", {"late_downs", "launch_pad"}),
    ]:
        p = package(pid)
        assert ti.offensive_package_eligible(p, required)
        assert all(not ti.offensive_package_eligible(p, {tag}) for tag in required)
    assert ti.offensive_package_eligible(package("sa_vertical_shot"), {"chasing"})
    assert ti.offensive_package_eligible(package("sa_vertical_shot"), {"long_yardage"})


def test_plan_selection_is_one_optional_package_and_deterministic():
    tactics = {"authority": 1.0, "packages": [
        package("gp_heavy_push"), package("gp_goal_line_jumbo")]}
    context = {"down": 3, "yards_to_go": 2, "field_position": 92}
    rng = random.Random(71)
    before = random.getstate()
    results = [ti.choose_offensive_package(tactics, context, rng) for _ in range(100)]
    assert random.getstate() == before
    assert all(set(eligible) == {"gp_heavy_push", "gp_goal_line_jumbo"}
               for _, eligible, _ in results)
    ids = [p["package_id"] if p else None for p, _, _ in results]
    assert set(ids) == {"gp_heavy_push", "gp_goal_line_jumbo", None}
    rng2 = random.Random(71)
    assert results == [ti.choose_offensive_package(tactics, context, rng2) for _ in range(100)]
    no_authority = {**tactics, "authority": 0}
    assert ti.choose_offensive_package(no_authority, context, rng)[0] is None


def test_single_plan_bias_does_not_revive_illegal_play_weights():
    p = package("gp_heavy_push", .5)
    tactics = {"family_bias": {"power": .02}, "formation_bias": {}}
    original = deepcopy(tactics)
    bias = ti.offensive_plan_bias(tactics, "family_bias", p)
    assert abs(bias["power"] - .08) < 1e-9
    assert ti.offensive_plan_bias(tactics, "formation_bias", p)["heavy"] == .06
    assert apply_weight_bias({"power": 0, "dive_option": 1}, bias)["power"] == 0
    assert tactics == original


def test_actual_choices_are_separate_from_package_selection():
    p = package("ec_quick_kick_chain")
    assert ti.offensive_plan_matches(p, {
        "formation":"split", "family":"kick_pass", "kick_pass":"quick_kick",
    }) == {"formation":True, "family":True, "kick_pass":True}
    assert ti.offensive_plan_matches(p, {
        "formation":"heavy", "family":"power",
    }) == {"formation":False, "family":False}
