"""RULE-01: the rulebooks say what the engine does.

RULES.md is the full rulebook and README.md is the rules record. Both are checked
against the engine here, so a rule change in either place fails a test until the
other is updated.
"""
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from engine.box_score_ledger import scoring_ledger  # noqa: E402
from engine.game_engine import (  # noqa: E402
    PENALTY_CATALOG, V2_ENGINE_CONFIG, GameState, ViperballEngine, load_team_from_json,
)
import build_rules_penalty_table  # noqa: E402


def _read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


RULES = _read("RULES.md")
README = _read("README.md")


def test_rules_penalty_table_is_the_engine_catalog():
    table = build_rules_penalty_table.build_table()
    assert table in RULES, "run python scripts/build_rules_penalty_table.py"


def test_readme_penalty_rows_match_catalog():
    by_name = {}
    for entries in PENALTY_CATALOG.values():
        for p in entries:
            by_name.setdefault(p["name"], []).append(p)
    section = README[README.index("## Penalties"):README.index("## Officials")]
    rows = re.findall(r"^\| ([^|]+?) \| (\d+) \| (\w+) \| ([^|]*?) ?\|$", section, re.M)
    assert len(rows) >= 8
    for name, yards, on, notes in rows:
        assert name in by_name, name
        options = by_name[name]
        assert any(p["yards"] == int(yards) and p["on"] == on.lower() for p in options), name
        if "Automatic first down" in notes:
            assert any(p.get("auto_first") for p in options), name
        if "Loss of down" in notes:
            assert any(p.get("loss_of_down") for p in options), name
    loss = sorted({p["name"] for e in PENALTY_CATALOG.values() for p in e if p.get("loss_of_down")})
    for name in loss:
        assert name in section, name


def test_rule_numbers_match_engine():
    state = GameState()
    assert state.down == 1 and state.yards_to_go == 20
    assert state.time_remaining == 600
    assert state.home_timeouts == state.away_timeouts == 4
    assert state.home_challenges == state.away_challenges == 3
    assert V2_ENGINE_CONFIG["play_clock_limit"] == 40
    assert V2_ENGINE_CONFIG.get("starting_yard_line", 20) == 20
    assert V2_ENGINE_CONFIG["place_kick_max_distance"] == 71
    assert V2_ENGINE_CONFIG.get("delta_restarts_enabled", True) is True
    for text in (RULES, README):
        assert "six downs to gain 20 yards" in text.lower() or "6-down, 20-yard" in text
        assert "four 10 minute quarters" in text.lower() or "four 10-minute quarters" in text.lower()
        assert "40 seconds" in text
        assert "8-minute periods" in text or "8 minutes" in text
        assert "4 timeouts per half" in text or "4 per half" in text
        assert "3 challenges per game" in text


SCORE_VALUES = {"rush_td": 9, "lateral_td": 9, "kp_td": 9, "return_td": 9,
                "dk": 5, "pk": 3, "safety": 2, "pindown": 1, "bell": 0.5}


def test_scoring_table_values_in_both_books():
    for text in (RULES, README):
        for label, pts in (("Touchdown", "9"), ("Snap Kick", "5"), ("Snap kick", "5"),
                           ("Field Goal", "3"), ("Field goal", "3"), ("Safety", "2"),
                           ("Pindown", "1"), ("Bell", "0.5")):
            if re.search(r"^\| \**" + label, text, re.M):
                assert re.search(r"^\| \**" + label + r"[^|]*\** \| \**" + re.escape(pts) + r"\**",
                                 text, re.M), (label, pts)


def test_games_follow_downs_and_scoring_rules():
    files = sorted(os.listdir(os.path.join(ROOT, "data", "teams")))
    pairs = [(files[0], files[1]), (files[40], files[90]), (files[120], files[170])]
    for i, (h, a) in enumerate(pairs):
        random.seed(500 + i)
        home = load_team_from_json(os.path.join(ROOT, "data", "teams", h))
        away = load_team_from_json(os.path.join(ROOT, "data", "teams", a))
        game = ViperballEngine(home, away, seed=500 + i).simulate_game()
        plays = game["play_by_play"]
        assert all(1 <= p["down"] <= 6 for p in plays if p.get("down") is not None)
        # A new set is 1st and 20; more than 20 only after an offensive foul.
        for prev, p in zip(plays, plays[1:]):
            if p.get("down") == 1 and (p.get("yards_to_go") or 0) > 20:
                assert prev.get("result") == "penalty", p.get("description")
        final = {s: game["final_score"][s]["score"] for s in ("home", "away")}
        ledger = scoring_ledger(plays, final)
        assert ledger is not None
        for side in ("home", "away"):
            row = ledger[side]
            assert row["points"]["other"] == 0, (h, a, side)
            for method, value in SCORE_VALUES.items():
                assert row["points"][method] == row["counts"][method] * value, method
