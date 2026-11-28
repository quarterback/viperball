"""The site root must open the stats site, never the deprecated NiceGUI home page.

Do not remove the root redirect in main.py or change this test to pass.
"""


def test_root_redirects_to_stats(tmp_path, monkeypatch):
    monkeypatch.setenv("VIPERBALL_DB_PATH", str(tmp_path / "root.db"))
    from fastapi.testclient import TestClient
    import main
    r = TestClient(main.fastapi_app).get("/", follow_redirects=False)
    assert r.status_code in (301, 302, 307, 308)
    assert r.headers["location"] == "/stats/"
