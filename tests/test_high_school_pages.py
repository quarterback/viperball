"""High school section of the stats site."""
import os
import random
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_high_school_pages_render():
    os.environ.setdefault("VIPERBALL_DB_PATH", os.path.join(tempfile.mkdtemp(), "hs.db"))
    random.seed(7)
    from fastapi.testclient import TestClient
    import api.main as api
    c = TestClient(api.app)
    sid = c.post("/sessions", json={}).json()["session_id"]
    c.post(f"/sessions/{sid}/dynasty", json={"coach_team": "Gonzaga", "dynasty_name": "HS"}).raise_for_status()

    home = c.get("/stats/")
    assert 'href="/stats/high-school/"' in home.text

    r = c.get("/stats/high-school/")
    assert r.status_code == 200
    assert "National champion" in r.text and "Top seniors" in r.text
    state = re.search(r'/stats/high-school/state/([A-Z]{2})"', r.text).group(1)
    team = re.search(r'/stats/high-school/team/([^"]+)"', r.text).group(1)

    s = c.get(f"/stats/high-school/state/{state}")
    assert s.status_code == 200 and "W-L" in s.text

    t = c.get(f"/stats/high-school/team/{team}")
    assert t.status_code == 200 and "Roster" in t.text and "Schedule" in t.text

    assert c.get("/stats/high-school/team/Nowhere_ZZ").status_code == 404
