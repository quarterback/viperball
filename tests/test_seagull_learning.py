"""Coaches learn from how Seagulls did (coach_learning.adapt_seagull)."""
import random
from types import SimpleNamespace

from engine.coach_learning import (SEAGULL_LIMIT, SEAGULL_STEP, adapt_seagull,
                                   observe_seagulls, seagull_learned)
from engine.coach_tactics import ensure_coach_tactical_profile
from engine.coaching import CoachCard, generate_coaching_staff
from engine.presnap import seagull_preference


def _card(role, adapt=100, stub=0, coach_id=None):
    return CoachCard(coach_id=coach_id or "sg-" + role, first_name="Test", last_name="Coach",
                     gender="female", age=45, role=role, classification="scheme_master",
                     instincts=70, leadership=70, composure=70, rotations=60, development=65,
                     recruiting=65, personality_sliders={"adaptability": adapt, "stubbornness": stub})


def _plays(side, offense_sg_gain, defense_sg_gain, opp_sg_gain=0):
    """One game: our offense with and without a Seagull, their offense against
    our defensive Seagull and against none, and their own Seagull."""
    other = "away" if side == "home" else "home"
    rows = []
    base = {"down": 1, "yards_to_go": 20, "field_position": 40, "result": "gain"}
    for _ in range(5):
        rows.append({**base, "snap_possession": side, "yards": 2 + offense_sg_gain,
                     "motion": {"seagull_line": "X"}})
        rows.append({**base, "snap_possession": side, "yards": 2, "motion": {"movers": 0}})
        rows.append({**base, "snap_possession": other, "yards": 4 + defense_sg_gain,
                     "motion": {"defense_seagull": {"name": "Y", "role": "defensive_back"}}})
        rows.append({**base, "snap_possession": other, "yards": 4, "motion": {"movers": 0}})
        rows.append({**base, "snap_possession": other, "yards": 4 + opp_sg_gain,
                     "motion": {"seagull_viper": "Z"}})
    return rows


def _season(oc, dc, n=8, **gains):
    games = []
    for _ in range(n):
        games.append(SimpleNamespace(completed=True, home_team="A", away_team="B", full_result={
            "coach_tactics": {"home": {"oc_id": oc.coach_id}},
            "defensive_coach_tactics": {"home": {"dc_id": dc.coach_id}},
            "play_by_play": _plays("home", **gains)}))
    return SimpleNamespace(schedule=games, playoff_bracket=[])


def test_seagulls_that_work_raise_preference_bounded():
    oc, dc, hc = _card("oc"), _card("dc"), _card("head_coach")
    season = _season(oc, dc, offense_sg_gain=10, defense_sg_gain=-3)
    before = {r: seagull_preference({r: c}, r) for r, c in (("oc", oc), ("dc", dc), ("head_coach", hc))}
    for role, card in (("oc", oc), ("dc", dc), ("head_coach", hc)):
        e = adapt_seagull(card, role, "A", 2026, season)
        assert e["sufficient"] and 0 < e["after"] <= SEAGULL_STEP
        assert adapt_seagull(card, role, "A", 2026, season) is None  # once a year
    assert seagull_preference({"oc": oc}, "oc") > before["oc"]
    assert seagull_preference({"dc": dc}, "dc") > before["dc"]
    for year in range(2027, 2040):
        adapt_seagull(oc, "oc", "A", year, season)
    assert seagull_learned(ensure_coach_tactical_profile(oc), "oc") <= SEAGULL_LIMIT
    loaded = CoachCard.from_dict(oc.to_dict())
    assert seagull_learned(ensure_coach_tactical_profile(loaded), "oc") == seagull_learned(oc.tactical_profile, "oc")


def test_seagulls_that_fail_lower_preference():
    oc, dc = _card("oc"), _card("dc")
    season = _season(oc, dc, offense_sg_gain=-2, defense_sg_gain=6)
    assert adapt_seagull(oc, "oc", "A", 2026, season)["after"] < 0
    assert adapt_seagull(dc, "dc", "A", 2026, season)["after"] < 0


def test_stubborn_coach_barely_moves_and_unattributed_games_do_not_teach():
    oc, dc = _card("oc", adapt=10, stub=95), _card("dc")
    season = _season(oc, dc, offense_sg_gain=10, defense_sg_gain=0)
    assert abs(adapt_seagull(oc, "oc", "A", 2026, season)["after"]) < 0.002
    stranger = _card("oc", coach_id="someone-else")
    assert adapt_seagull(stranger, "oc", "A", 2026, season) is None


def test_copy_what_beats_you():
    """A staff with no Seagulls learns from opponents' Seagulls that hurt it."""
    oc, dc, hc = _card("oc"), _card("dc"), _card("head_coach")
    games = []
    base = {"down": 1, "yards_to_go": 20, "field_position": 40, "result": "gain"}
    for _ in range(8):
        rows = []
        for _ in range(6):
            rows.append({**base, "snap_possession": "away", "yards": 12, "motion": {"seagull_line": "Z"}})
            rows.append({**base, "snap_possession": "away", "yards": 3, "motion": {"movers": 0}})
        games.append(SimpleNamespace(completed=True, home_team="A", away_team="B", full_result={
            "coach_tactics": {"home": {"oc_id": oc.coach_id}},
            "defensive_coach_tactics": {"home": {"dc_id": dc.coach_id}}, "play_by_play": rows}))
    season = SimpleNamespace(schedule=games, playoff_bracket=[])
    data, _ = observe_seagulls(season, "A")
    assert data["own_offense"]["games"] == 0 and data["opp_offense"]["contrast"] > 0
    assert adapt_seagull(hc, "head_coach", "A", 2026, season)["after"] > 0
    assert adapt_seagull(dc, "dc", "A", 2026, season)["after"] > 0


def test_real_games_produce_evidence():
    import importlib.util, os
    from engine.game_engine import ViperballEngine
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("bm", os.path.join(root, "scripts", "benchmark_engine.py"))
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    teams, styles, pairs = bm.build_matchups(8, 2026)
    staff = generate_coaching_staff(team_name="A", prestige=60, year=2026, rng=random.Random(3))
    for c in staff.values():
        c.personality_sliders = dict(c.personality_sliders or {}, adaptability=95,
                                     chaos_appetite=90, risk_tolerance=90, stubbornness=5)
    games = []
    home = pairs[0][0]
    for i, (_, away) in enumerate(pairs):
        if away == home:
            continue
        r = ViperballEngine(teams[home], teams[away], seed=40 + i, home_coaching=staff).simulate_game()
        games.append(SimpleNamespace(completed=True, home_team=home, away_team=away, full_result=r))
    season = SimpleNamespace(schedule=games, playoff_bracket=[])
    data, _ = observe_seagulls(season, home)
    assert data["own_offense"]["with"] > 0 and data["own_defense"]["with"] > 0
    event = adapt_seagull(staff["head_coach"], "head_coach", home, 2026, season)
    assert event is not None and abs(event["after"]) <= SEAGULL_STEP
