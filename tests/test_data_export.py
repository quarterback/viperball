"""The flat season data tables load as CSV and JSON, with CORS for notebooks."""
import csv
import io


def test_data_tables(tmp_path, monkeypatch):
    monkeypatch.setenv("VIPERBALL_DB_PATH", str(tmp_path / "data.db"))
    from fastapi.testclient import TestClient
    import api.main as api
    from stats_site.data_export import TABLES
    client = TestClient(api.app)
    sid = client.post("/sessions", json={}).json()["session_id"]
    client.post(f"/sessions/{sid}/season", json={}).raise_for_status()
    client.post(f"/sessions/{sid}/season/simulate-week", json={}).raise_for_status()
    base = f"/stats/data/college/{sid}"

    index = client.get(base + "/")
    assert index.status_code == 200
    assert index.headers["access-control-allow-origin"] == "*"
    assert [t["name"] for t in index.json()["tables"]] == list(TABLES)
    assert index.json()["tables"][0]["csv"].endswith(f"{base}/games.csv")

    for name in TABLES:
        js = client.get(f"{base}/{name}.json")
        assert js.status_code == 200, name
        rows = js.json()
        assert rows, name
        assert all(not isinstance(v, (dict, list)) for v in rows[0].values()), name
        cs = client.get(f"{base}/{name}.csv")
        assert cs.status_code == 200 and cs.headers["access-control-allow-origin"] == "*"
        parsed = list(csv.DictReader(io.StringIO(cs.text)))
        assert len(parsed) == len(rows), name

    games = client.get(base + "/games.json").json()
    team = games[0]["home"]
    tg = client.get(base + "/team_games.json", params={"team": team}).json()
    assert len(tg) == 1 and tg[0]["team"] == team and "total_yards" in tg[0]
    plays = client.get(base + "/plays.json", params={"team": team}).json()
    assert plays and all(p["offense"] == team for p in plays)
    assert client.get(base + "/nope.csv").status_code == 404
    assert client.get(base + "/games.xml").status_code == 404

    page = client.get("/stats/export")
    assert f"{base}/plays.csv" in page.text
