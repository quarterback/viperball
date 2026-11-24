"""Calls, no calls and missed calls (engine/officiating.py)."""
import os
import random
import statistics

from engine.game_engine import PENALTY_CATALOG, RefereeCrew, ViperballEngine, load_team_from_json
from engine.officiating import _CLASS_BY_NAME, decide

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_every_catalog_foul_has_a_class():
    names = {p["name"] for entries in PENALTY_CATALOG.values() for p in entries}
    assert names <= set(_CLASS_BY_NAME)


def _rates(name, **kw):
    rng = random.Random(4)
    crew = RefereeCrew(name="Test Crew")
    crew.strictness = 1.0
    out = [decide(name, crew, rng=rng, **kw)[0] for _ in range(4000)]
    return {k: out.count(k) / len(out) for k in ("called", "no_call", "missed")}


def test_visible_fouls_are_called_more_than_holding():
    assert _rates("False Start")["called"] > 0.8
    holding = _rates("Holding")
    assert holding["called"] < 0.35 and holding["no_call"] > 0.5


def test_late_close_games_let_judgment_fouls_go():
    assert _rates("Holding", late_close=True)["called"] < _rates("Holding")["called"]
    assert abs(_rates("False Start", late_close=True)["called"] - _rates("False Start")["called"]) < 0.02


def test_games_have_flags_let_go_and_missed_calls():
    files = sorted(os.listdir(os.path.join(ROOT, "data", "teams")))
    flags, missed, phantom, lets = [], [], [], []
    for i in range(12):
        random.seed(900 + i)
        h = load_team_from_json(os.path.join(ROOT, "data", "teams", files[i * 7]))
        a = load_team_from_json(os.path.join(ROOT, "data", "teams", files[i * 7 + 3]))
        ref = ViperballEngine(h, a, seed=900 + i).simulate_game()["referee"]
        flags.append(ref["flags_thrown"])
        missed.append(ref["missed_calls"])
        phantom.append(ref["phantom_flags"])
        lets.append(ref["no_calls"])
        assert ref["infractions"] >= ref["flags_thrown"] - ref["phantom_flags"]
    assert 10 < statistics.mean(flags) < 24
    assert statistics.mean(lets) > 3
    assert statistics.mean(missed) > statistics.mean(phantom)


def test_college_crews_spread_wider_than_pro_crews():
    from engine.officiating import apply_level
    acc, strict = {}, {}
    for level in ("pro", "college", "high_school"):
        a, s = [], []
        for i, base in enumerate([0.91, 0.93, 0.945, 0.96, 0.98] * 20):
            crew = RefereeCrew(name=f"Crew {i}", accuracy=base)
            apply_level(crew, level)
            a.append(crew.accuracy)
            s.append(crew.strictness)
        acc[level], strict[level] = a, s
    assert statistics.mean(acc["pro"]) > statistics.mean(acc["college"]) > statistics.mean(acc["high_school"])
    assert statistics.pstdev(acc["pro"]) < statistics.pstdev(acc["college"]) < statistics.pstdev(acc["high_school"])
    assert statistics.pstdev(strict["pro"]) < statistics.pstdev(strict["college"])
