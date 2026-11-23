"""An odd program count retires Coast Guard (Merchant Marine if Coast Guard is yours)."""

import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _start(coach_team):
    os.environ.setdefault("VIPERBALL_DB_PATH", os.path.join(tempfile.mkdtemp(), "g.db"))
    random.seed(2026)
    from fastapi.testclient import TestClient
    import api.main as api
    c = TestClient(api.app)
    sid = c.post("/sessions", json={}).json()["session_id"]
    c.post(f"/sessions/{sid}/dynasty", json={"coach_team": coach_team, "dynasty_name": "T"}).raise_for_status()
    r = c.post(f"/sessions/{sid}/dynasty/start-season", json={})
    r.raise_for_status()
    return r.json(), api.sessions[sid]


def test_odd_count_retires_coast_guard():
    body, sess = _start("Gonzaga")
    assert body.get("auto_retired") == "Coast Guard"
    assert "Coast Guard" not in sess["season"].teams
    assert len(sess["season"].teams) % 2 == 0


def test_coast_guard_dynasty_retires_merchant_marine():
    body, sess = _start("Coast Guard")
    assert body.get("auto_retired") == "Merchant Marine"
    assert "Coast Guard" in sess["season"].teams
