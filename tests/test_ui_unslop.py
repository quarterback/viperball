"""UI polish regression: preserve intentional animation and real template features."""
from pathlib import Path
import random
import shutil
from urllib.parse import quote
import json

ROOT = Path(__file__).resolve().parents[1]

def test_templates_compile():
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(ROOT / "stats_site" / "templates"))
    for name in env.list_templates(extensions=["html"]):
        env.parse(env.loader.get_source(env, name)[0])

def test_animated_background_and_transition_wiring():
    app = (ROOT / "nicegui_app" / "app.py").read_text()
    for name in ("ambient_bg", "page_transition", "nav_glow"):
        assert (ROOT / "nicegui_app" / "sketches" / (name + ".js")).is_file()
        assert "_vbLoadSketch('/sketches/" + name + ".js');" in app
        assert 'id="vb-' + name.replace("_", "-") + '"' in app
    assert "p5.min.js" in app
    assert "if (window.vbTransition) window.vbTransition();" in app
    assert "ui.timer(0.3, lambda: ui.run_javascript(_P5_INIT_JS), once=True)" in app

def test_polished_pages_render(tmp_path, monkeypatch):
    monkeypatch.setenv("VIPERBALL_DB_PATH", str(tmp_path / "ui.db"))
    from fastapi.testclient import TestClient
    import api.main as api
    # Keep the real engine and actual school files, but a small league.
    source=sorted((ROOT / "data" / "teams").glob("*.json"))
    selected=[source[round(i*(len(source)-1)/15)] for i in range(16)]
    league=tmp_path/"teams"; league.mkdir()
    names=[]
    for path in selected:
        shutil.copy(path,league/path.name)
        info=json.loads(path.read_text())["team_info"]
        names.append(info.get("school") or info["school_name"])
    monkeypatch.setattr(api,"TEAMS_DIR",str(league))
    random.seed(20261125)
    client=TestClient(api.app)
    sid=client.post("/sessions",json={}).json()["session_id"]
    base=f"/sessions/{sid}"
    client.post(base+"/season",json={"name":"UI verification season","ai_seed":20261125,
        "human_teams":[names[0]],"games_per_team":12,"playoff_size":4,"bowl_count":0,
        "conferences":{"East":names[:8],"West":names[8:]}}).raise_for_status()
    result=client.post(base+"/season/simulate-week",json={})
    result.raise_for_status()
    week=result.json()["week"]
    prefix=f"/stats/college/{sid}"
    pages={"/stats/":"home-leagues",prefix+"/":"UI verification season",
        prefix+"/team/"+quote(names[0],safe=""):"Coaching Staff",
        prefix+"/game/"+str(week)+"/0":"pbp-row",
        prefix+"/luck":"Actual wins minus expected wins",
        "/stats/my-team/":"Offseason Actions"}
    for url, expected in pages.items():
        response=client.get(url)
        assert response.status_code==200, (url,response.status_code,response.text[:400])
        assert expected in response.text, (url,expected)
    # A real game keeps the event semantics in the template instead of
    # dark-only inline fills; not dependent on a particular scoring outcome.
    template=(ROOT/"stats_site/templates/college/game.html").read_text()
    assert "game-event-score" in template and "game-event-turnover" in template
    assert "background:#1a1a00" not in template
