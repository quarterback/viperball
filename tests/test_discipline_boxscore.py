"""Rendering contract for PEN-04 discipline presentation."""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from engine.box_score import BoxScoreGenerator

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return {
        "final_score": {"away": {"team": "Away U", "score": 30}, "home": {"team": "Home U", "score": 40}},
        "stats": {
            "away": {"penalties": 2, "penalty_yards": 20, "penalties_declined": 1,
                     "unsportsmanlike_fouls": 2, "ejections": 1,
                     "penalties_by_type": {"Holding": 1, "Taunting": 1}},
            "home": {"penalties": 1, "penalty_yards": 5, "penalties_declined": 0,
                     "unsportsmanlike_fouls": 0, "ejections": 0,
                     "penalties_by_type": {"False Start": 1}},
        },
        "ejections": [{"quarter": 5, "time_remaining": 65, "side": "away",
                       "tag": "ZB12", "player": "Alex & Lee", "foul": "Taunting",
                       "reason": "Second unsportsmanlike foul", "declined": True,
                       "substitute": "ZB14 Sam Jones"}],
        "player_discipline": {"away": [{"tag": "ZB12", "player": "Alex & Lee",
                                        "flags": 2, "accepted": 1,
                                        "unsportsmanlike": 2, "ejected": True}], "home": []},
    }


def html(result):
    env = Environment(loader=FileSystemLoader(ROOT / "stats_site" / "templates"),
                      autoescape=select_autoescape(["html"]))
    return env.get_template("_game_discipline.html").render(
        fr=result, game={"away_team": "Away U", "home_team": "Home U"},
        session_id="test", oneoff=True)


def markdown(result):
    return "\n".join(BoxScoreGenerator(result)._discipline_lines("Away U", "Home U"))


def test_ejection_rendered_from_summary_not_play_description():
    result = fixture()
    for output in (html(result), markdown(result)):
        assert "OT1 1:05" in output or "OT1 01:05" in output
        for expected in ("ZB12", "Second unsportsmanlike foul", "Declined", "ZB14 Sam Jones",
                         "Holding", "False Start", "Player disciplinary record"):
            assert expected in output
    assert "Alex &amp; Lee" in html(result)


def test_no_ejections_distinguished_from_legacy_missing_data():
    result = fixture()
    result["ejections"] = []
    result["player_discipline"] = {"away": [], "home": []}
    for stats in result["stats"].values():
        stats["ejections"] = 0
    for output in (html(result), markdown(result)):
        assert "No ejections." in output
    del result["ejections"]
    del result["player_discipline"]
    for output in (html(result), markdown(result)):
        assert "records are unavailable" in output
        assert "No ejections." not in output
        assert "Accepted penalties" in output
