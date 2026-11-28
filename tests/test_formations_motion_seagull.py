"""Rulebook v2.1: line minimum, backfield motion, the Viper jersey and the Seagull."""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.game_engine import PENALTY_CATALOG, ViperballEngine  # noqa: E402
from engine.presnap import LINE_MINIMUM, MAX_SEAGULLS, presnap_foul_scale  # noqa: E402

_spec = importlib.util.spec_from_file_location("bm", os.path.join(ROOT, "scripts", "benchmark_engine.py"))
bm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bm)

_TEAMS, _STYLES, _PAIRS = bm.build_matchups(4, 2026)


def _games(level="college"):
    out = []
    for i, (a, b) in enumerate(_PAIRS):
        eng = ViperballEngine(_TEAMS[a], _TEAMS[b], seed=300 + i,
                              style_overrides=bm.overrides(_STYLES, a, b),
                              officiating_level=level)
        out.append((eng, eng.simulate_game()))
    return out


GAMES = _games()


def test_retired_fouls_are_gone():
    names = {p["name"] for e in PENALTY_CATALOG.values() for p in e}
    for name in ("Illegal Viper Alignment", "Illegal Numbering",
                 "Illegal Formation (Numbering Exception)"):
        assert name not in names


def test_line_minimum_by_level():
    assert LINE_MINIMUM == {"high_school": 3, "college": 5, "pro": 5}
    a, b = _PAIRS[0]
    eng = ViperballEngine(_TEAMS[a], _TEAMS[b], seed=1, officiating_level="high_school")
    assert eng.line_minimum == 3
    assert GAMES[0][1]["line_minimum"] == 5


def test_seagulls_listed_and_off_the_lines():
    for eng, r in GAMES:
        for side, team in (("home", eng.home_team), ("away", eng.away_team)):
            rows = r["seagulls"][side]
            assert len(rows) <= MAX_SEAGULLS
            names = {row["name"] for row in rows}
            for row in rows:
                assert 2 <= len(row["groups"]) <= 3
                if "Viper" in row["groups"]:
                    assert row["position"] == "Viper"
            lines = eng._midfield_lines(team, set())
            assert not names & {p.name for l in lines for p in l}


def test_seagulls_play_and_report():
    snaps, reports, line_snaps = 0, 0, 0
    for _, r in GAMES:
        for side in ("home", "away"):
            for row in r["seagulls"][side]:
                snaps += sum(row["snaps"].values())
        reports += len(r["seagull_reports"])
        line_snaps += sum(bool((p.get("motion") or {}).get("seagull_line")) for p in r["play_by_play"])
        for rep in r["seagull_reports"]:
            row = next(x for x in r["seagulls"][rep["side"]] if x["name"] == rep["player"])
            assert "Viper" in row["groups"]
    assert snaps > 0 and reports > 0 and line_snaps > 0


def test_motion_is_recorded_and_varies():
    movers = []
    for _, r in GAMES:
        for p in r["play_by_play"]:
            m = p.get("motion")
            if m:
                movers.append(m["movers"])
                assert len(m["in_motion"]) == m["movers"]
                if m["seagull_slide"]:
                    assert m["seagull_line"]
    assert movers and max(movers) >= 2 and min(movers) == 0
    assert 0.3 < sum(movers) / len(movers) < 2.0


def test_foul_scale_follows_the_snap():
    assert presnap_foul_scale("Illegal Viper Substitution", {"movers": 0}) == 0.0
    assert presnap_foul_scale("Illegal Viper Substitution", {"jersey_report": True}) > 1.0
    assert presnap_foul_scale("Illegal Motion", {"movers": 3}) > presnap_foul_scale("Illegal Motion", {"movers": 0})
    assert presnap_foul_scale("False Start", {"seagull_slide": True}) > 1.0
    assert presnap_foul_scale("Offsides", {"movers": 4}) == 1.0


def test_viper_substitution_flags_need_a_seagull():
    for _, r in GAMES:
        for p in r["play_by_play"]:
            pen = p.get("penalty") or {}
            if pen.get("name") == "Illegal Viper Substitution" and pen.get("phase") == "pre_snap":
                m = p.get("motion") or {}
                assert m.get("seagull_viper") or m.get("seagull_line")
