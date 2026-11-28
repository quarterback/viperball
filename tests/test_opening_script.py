"""Opening scripts (casebook case 3): ordered calls, held for urgent
situations, observed fronts and answers after the script."""
from engine.coach_script import best_answer, build_script, interrupt_reason, script_length


WEIGHTS = {"dive_option": .2, "sweep_option": .2, "kick_pass": .3, "viper_jet": .1, "draw": .1}


def test_length_is_stable_and_some_callers_do_not_script():
    lengths = {script_length(f"coach-{i}") for i in range(200)}
    assert 0 in lengths and max(lengths) <= 6
    assert script_length("coach-7") == script_length("coach-7")
    assert script_length(None) == 0


def test_script_is_ordered_and_only_uses_legal_families():
    coach = next(f"c{i}" for i in range(500) if script_length(f"c{i}") == 6)
    calls = build_script(coach, WEIGHTS, {"split": .6, "tight": .4})
    assert [c["probe"] for c in calls][:3] == ["inside_run", "perimeter_run", "quick_kick_pass"]
    assert all(WEIGHTS.get(c["family"], 0) > 0 for c in calls)
    assert all(c["formation"] == "split" for c in calls)
    no_jet = build_script(coach, {**WEIGHTS, "viper_jet": 0}, {"split": 1})
    assert "viper_motion" not in [c["probe"] for c in no_jet]


def test_urgent_situations_hold_the_script():
    assert interrupt_reason(1, 20, 1, 500, 0, False, 40) is None
    assert interrupt_reason(3, 1, 1, 500, 0, False, 40) == "short_yardage"
    assert interrupt_reason(1, 20, 1, 500, 0, False, 90) == "red_zone"
    assert interrupt_reason(5, 8, 1, 500, 0, False, 40) == "down_and_distance"
    assert interrupt_reason(1, 20, 1, 500, 0, True, 40) == "kick_mode"


def test_answers_need_a_real_gain():
    obs = [{"probe": "inside_run", "family": "dive_option", "front": "spread", "yards": 7},
           {"probe": "draw", "family": "draw", "front": "spread", "yards": 3},
           {"probe": "draw", "family": "draw", "front": "stacked", "yards": 2}]
    answers = best_answer(obs)
    assert answers == {"spread": {"probe": "inside_run", "family": "dive_option"}}
