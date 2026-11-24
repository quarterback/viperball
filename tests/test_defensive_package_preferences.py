"""DEF-11: package selection reflects tactical interests, not package names."""
from copy import deepcopy
import random
from types import SimpleNamespace

import pytest

from engine import team_installation as ti
from engine.coach_tactics import PROFILE_VERSION
from engine.playbook_catalog import get_package


ROSTER = {"avg_speed": 90, "avg_stamina": 90, "avg_weight": 200,
          "kicking_strength": 90, "lateral_proficiency": 90,
          "defensive_strength": 90}


def coordinator(cid, focus, reads=(), pressure=0.0, support=0.0):
    return SimpleNamespace(coach_id=cid, tactical_profile={
        "version": PROFILE_VERSION, "coach_id": cid,
        "defense": {"coverage_focus": focus, "read_focus": list(reads),
                    "pressure_bias": pressure, "run_support_bias": support},
    })


def test_same_pressure_different_coverage_preferences():
    deep = coordinator("deep", "deep", ["kick_pass"])
    intermediate = coordinator("intermediate", "intermediate", ["kick_pass"])
    deep_score = ti._package_preference_score("defense", "shadow", deep)
    mid_score = ti._package_preference_score("defense", "shadow", intermediate)
    # Prevent and Robber address different coverage depths. Use the same
    # non-native family for both when testing the focus itself.
    deep_score = ti._package_preference_score("defense", "swarm", deep)
    mid_score = ti._package_preference_score("defense", "swarm", intermediate)
    assert deep_score("drift_prevent") > deep_score("shadow_robber")
    assert mid_score("shadow_robber") > mid_score("drift_prevent")


def test_same_native_pressure_packages_differ_by_focus():
    mid = coordinator("mid", "intermediate", ["kick_pass"], pressure=.11)
    edge = coordinator("edge", "perimeter", ["run", "kick_pass"], pressure=.11)
    for coach, first, second in [
        (mid, "afl_kick_in_press", "predator_exhaustion_press"),
        (edge, "predator_exhaustion_press", "afl_kick_in_press"),
    ]:
        score = ti._package_preference_score("defense", "predator", coach)
        assert score(first) > score(second)


def test_preference_components_bounded_and_native_advantage_preserved():
    pkg = get_package("shadow_robber")
    d = {"pressure_bias": -.1, "coverage_focus": "intermediate",
         "read_focus": ["kick_pass", "run", "lateral", "trick"]}
    native = ti._defensive_preference_components(pkg, "shadow", d)
    borrowed = ti._defensive_preference_components(pkg, "swarm", d)
    assert native["category"] == pytest.approx(.1)
    assert native["focus_match"] == pytest.approx(.08)
    assert native["read_match"] == pytest.approx(.025)
    assert sum(native.values()) - sum(borrowed.values()) == pytest.approx(.07)


def test_snapshot_matches_fresh_selection_and_preserves_rng():
    coach = coordinator("coach-a", "intermediate", ["kick_pass"], pressure=.11)
    unit = {"family": "predator", "packages": []}
    before = deepcopy(unit)
    rng_before = random.getstate()
    snap = ti.defensive_adoption_snapshot(unit, coach, ROSTER)
    assert unit == before
    assert random.getstate() == rng_before
    ranked = sorted((r["preference_rank"], pid)
                    for pid, r in snap["packages"].items()
                    if "preference_rank" in r)
    ti._choose_packages("defense", unit, coach, ROSTER, 2026)
    assert {p["package_id"] for p in unit["packages"]} == {
        pid for _, pid in ranked[:ti.PACKAGES_PER_COORDINATOR]}
    assert random.getstate() == rng_before
    for p in unit["packages"]:
        row = snap["packages"][p["package_id"]]
        assert row["personnel_ok"] and row["compatible"] and row["callable"]
        assert row["preference_score"] == pytest.approx(
            sum(row["preference_components"].values()), abs=1e-6)


def test_exact_ties_are_stable_and_do_not_override_score():
    candidates = ["fortress_goal_line_stand", "fortress_short_yardage_wall"]
    score = lambda pid: 0.1
    coach = coordinator("coach-a", "short")
    key = lambda pid: ti._package_rank_key("defense", coach, score, pid)
    assert sorted(candidates, key=key) == sorted(reversed(candidates), key=key)
    assert key(candidates[0]) == key(candidates[0])
    higher = lambda pid: .101 if pid == candidates[1] else .1
    assert sorted(candidates, key=lambda pid: ti._package_rank_key(
        "defense", coach, higher, pid))[0] == candidates[1]


def test_existing_knowledge_retained_and_unfit_removed():
    coach = coordinator("coach-a", "perimeter", ["run"])
    unit = {"family": "predator", "packages": [
        {"package_id": "afl_kick_in_press", "familiarity": .92,
         "installed_by": "coach-a", "installed_year": 2025}]}
    learned = deepcopy(unit["packages"][0])
    ti._choose_packages("defense", unit, coach, ROSTER, 2026)
    assert learned in unit["packages"]
    assert len(unit["packages"]) <= ti.MAX_PACKAGES
    low = dict(ROSTER, avg_speed=0, avg_stamina=0)
    ti._choose_packages("defense", unit, coach, low, 2026)
    assert not any(p["package_id"] == learned["package_id"]
                   for p in unit["packages"])
