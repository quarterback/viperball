"""A long-serving head coach changes the program's system (casebook case 6)."""
import random
from types import SimpleNamespace

from engine import coach_reinvention as cr
from engine.coaching import CoachCareerStop


def _hc(adapt=90, stubborn=10, start=2020):
    return SimpleNamespace(coach_id="hc1", first_name="Ann", last_name="Lee",
                           personality_sliders={"adaptability": adapt, "stubbornness": stubborn},
                           career_history=[CoachCareerStop(year_start=start, year_end=None,
                                                           team_name="Us", role="head_coach")])


def _league(us_ppd):
    teams = {f"T{i}": 2.0 + i * 0.1 for i in range(20)}
    teams["Us"] = us_ppd
    histories = {t: SimpleNamespace(season_records={y: {"avg_ppd": v, "wins": 6, "losses": 6,
                                                        "points_against": 300} for y in (2024, 2025)})
                 for t, v in teams.items()}
    configs = {t: {"offense_style": "slick_n_slide" if i % 2 else "ironclad"}
               for i, t in enumerate(sorted(teams))}
    for i in range(10, 20):
        configs[f"T{i}"]["offense_style"] = "slick_n_slide"
    for i in range(0, 10):
        configs[f"T{i}"]["offense_style"] = "ironclad"
    configs["Us"] = {"offense_style": "ironclad"}
    return histories, {2025: configs, 2024: configs}


CATALOGS = {"offense": {"ironclad": {}, "slick_n_slide": {}}, "defense": {"swarm": {}}}


def _consider(hc, us_ppd=1.0, specialty="dc"):
    histories, configs = _league(us_ppd)
    import engine.coach_career as career
    orig = career.management
    career.management = lambda card: {"specialty": specialty}
    try:
        return cr.consider("Us", hc, {"offense_style": "ironclad"}, histories, configs, 2026,
                           CATALOGS, random.Random(1))
    finally:
        career.management = orig


def test_adaptable_long_serving_coach_switches_to_the_winning_school():
    change = _consider(_hc())
    assert change and change["side"] == "offense"
    assert change["from"] == "ironclad" and change["to"] == "slick_n_slide"
    assert change["tenure"] == 6


def test_no_change_for_a_new_coach_a_good_offense_or_a_stubborn_coach():
    assert _consider(_hc(start=2024)) is None
    assert _consider(_hc(), us_ppd=9.0) is None
    assert _consider(_hc(adapt=10, stubborn=95)) is None


def test_offensive_specialist_changes_the_defense_side_only():
    assert _consider(_hc(), specialty="oc") is None or _consider(_hc(), specialty="oc")["side"] == "defense"
