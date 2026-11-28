"""Rulebook v2.1: line minimum, backfield motion, the Viper jersey and the Seagull."""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.game_engine import PENALTY_CATALOG, ViperballEngine  # noqa: E402
from engine.position_fit import adaptability, fit, fits, natural_fit  # noqa: E402
from engine.presnap import LINE_MINIMUM, MAX_SEAGULLS, presnap_foul_scale  # noqa: E402

_spec = importlib.util.spec_from_file_location("bm", os.path.join(ROOT, "scripts", "benchmark_engine.py"))
bm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bm)

_TEAMS, _STYLES, _PAIRS = bm.build_matchups(4, 2026)


def _staff(**sliders):
    import random
    from engine.coaching import generate_coaching_staff
    staff = generate_coaching_staff(team_name="Test", prestige=60, year=2026, rng=random.Random(7))
    for card in staff.values():
        card.personality_sliders = dict(card.personality_sliders or {}, **sliders)
    return staff


KEEN = _staff(adaptability=95, chaos_appetite=90, risk_tolerance=90, stubbornness=5)
RELUCTANT = _staff(adaptability=5, chaos_appetite=10, risk_tolerance=10, stubbornness=95)


def _games(level="college"):
    out = []
    for i, (a, b) in enumerate(_PAIRS):
        eng = ViperballEngine(_TEAMS[a], _TEAMS[b], seed=300 + i,
                              style_overrides=bm.overrides(_STYLES, a, b),
                              officiating_level=level, home_coaching=KEEN, away_coaching=KEEN)
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
                assert row["tag"].startswith("SG")
                assert any(g in ("Viper", "flanker", "Keeper", "defensive back") for g in row["groups"])
                p = next(x for x in team.players if x.name == row["name"])
                for g in row["groups"][1:]:
                    assert natural_fit(p, g)
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


def test_seagulls_are_a_college_rule():
    for level in ("high_school", "pro"):
        a, b = _PAIRS[0]
        r = ViperballEngine(_TEAMS[a], _TEAMS[b], seed=11, officiating_level=level).simulate_game()
        assert r["seagulls"] == {"home": [], "away": []}
        assert not r["seagull_reports"]


def test_high_school_short_line():
    a, b = _PAIRS[1]
    short, lowest = 0, 99
    for seed in (21, 22):
        r = ViperballEngine(_TEAMS[a], _TEAMS[b], seed=seed, officiating_level="high_school",
                            style_overrides={a: "chain_gang", b: "lateral_spread"}).simulate_game()
        for p in r["play_by_play"]:
            m = p.get("motion") or {}
            if m.get("on_line"):
                lowest = min(lowest, m["on_line"])
            if m.get("short_line"):
                short += 1
                assert m["on_line"] == 5 - len(m["short_line"])
    assert short > 0 and lowest == 3
    for _, r in GAMES:
        assert all(not (p.get("motion") or {}).get("short_line") for p in r["play_by_play"])


def test_two_seagulls_on_the_line_only_one_moves():
    seen = 0
    for _, r in GAMES:
        for p in r["play_by_play"]:
            m = p.get("motion") or {}
            both = m.get("seagull_line_all") or []
            if len(both) > 1:
                seen += 1
                assert m["seagull_line"] in both
    assert seen > 0


def test_position_fit_uses_ratings_and_size():
    a, _ = _PAIRS[0]
    players = _TEAMS[a].players
    lineman = next(p for p in players if p.position == "Offensive Line")
    keeper = next(p for p in players if p.position == "Keeper")
    assert natural_fit(lineman, "Offensive Line") and natural_fit(keeper, "Keeper")
    heavy = max(players, key=lambda p: p.weight)
    if heavy.weight > 192 and heavy.position not in ("Viper", "Halfback", "Wingback", "Slotback", "Keeper"):
        assert not natural_fit(heavy, "flanker")
    table = fits(keeper)
    assert set(table) >= {"Viper", "flanker", "Offensive Line", "Defensive Line", "Keeper", "defensive back"}
    assert 0 <= adaptability(keeper) <= 100
    assert fit(keeper, "flanker") <= table["flanker"]["fit"] + 1e-9


def test_seagulls_are_optional_by_coach():
    from engine.presnap import seagull_policy
    keen, reluctant, neutral = seagull_policy(KEEN), seagull_policy(RELUCTANT), seagull_policy(None)
    assert keen["max_listed"] == 2 and reluctant["max_listed"] == 0 and neutral["max_listed"] == 1
    assert keen["line_scale"] > neutral["line_scale"] > reluctant["line_scale"]
    assert keen["min_ratio"] < reluctant["min_ratio"]
    a, b = _PAIRS[0]
    r = ViperballEngine(_TEAMS[a], _TEAMS[b], seed=5, home_coaching=RELUCTANT,
                        away_coaching=KEEN).simulate_game()
    assert r["seagulls"]["home"] == []
    assert r["seagull_policy"]["home"]["max_listed"] == 0
    assert len(r["seagulls"]["away"]) <= 2
