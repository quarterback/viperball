"""Halftime caller changes and between-series suggestions (casebook case 10)."""
import random
from types import SimpleNamespace

from engine.coach_handoff import accepts, struggling, suggestion


def test_struggling_offense():
    assert struggling(10, 25)
    assert struggling(12, 14)
    assert not struggling(30, 32)
    assert not struggling(20, 10)


def test_suggestion_needs_a_family_that_stands_out():
    plays = [("power", 2), ("power", 3), ("power", 1), ("sweep_option", 9),
             ("sweep_option", 8), ("sweep_option", 10), ("kick_pass", 0), ("kick_pass", 4)]
    idea = suggestion(plays)
    assert idea["family"] == "sweep_option"
    assert suggestion([("power", 3)] * 4 + [("sweep_option", 3)] * 4) is None
    assert suggestion([("sweep_option", 20), ("power", 1), ("power", 1), ("power", 2)]) is None


def test_adaptable_callers_take_more_suggestions():
    open_mind = SimpleNamespace(personality_sliders={"adaptability": 90, "stubbornness": 10})
    stubborn = SimpleNamespace(personality_sliders={"adaptability": 10, "stubbornness": 90})
    rng = random.Random(1)
    a = sum(accepts(open_mind, rng) for _ in range(500))
    b = sum(accepts(stubborn, rng) for _ in range(500))
    assert a > b * 2
