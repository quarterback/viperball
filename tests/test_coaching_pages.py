"""Render actual college coaching pages and the career-history endpoint."""
import os
from urllib.parse import quote

def test_coaching_pages_and_career_history(tmp_path,monkeypatch):
    monkeypatch.setenv("VIPERBALL_DB_PATH",str(tmp_path/"coaching.db"))
    from fastapi.testclient import TestClient
    import api.main as api
    from engine.coach_career import active_management, ensure, record_season
    client=TestClient(api.app)
    sid=client.post("/sessions",json={}).json()["session_id"]
    base=f"/sessions/{sid}"
    client.post(base+"/dynasty",json={"coach_team":"Gonzaga","dynasty_name":"Career smoke"}).raise_for_status()
    client.post(base+"/dynasty/start-season",json={"ai_seed":20261126}).raise_for_status()
    sess=api.sessions[sid]
    season=sess["season"]
    dynasty=sess["dynasty"]
    staff=season.coaching_staffs["Gonzaga"]
    hc=staff["head_coach"]
    oc=staff["oc"]
    active_management(hc)["retained_call"]="oc"
    ensure(oc)["ever_head_coach"]=True
    ensure(oc)["role_years"]["head_coach"]=5
    record_season(oc,"oc",2025,"Previous Program",8,4,
        {"games":12,"expected":6.5,"actual":8,"above_expectation":.125})
    team_url=f"/stats/college/{sid}/team/{quote('Gonzaga')}"
    team=client.get(team_url)
    assert team.status_code==200
    assert "Coaching Staff" in team.text and "Reputation" in team.text and "Former HC" in team.text
    head=client.get(f"/stats/college/{sid}/coach/Gonzaga/head_coach")
    assert head.status_code==200 and "Program Leadership" in head.text and "Market reputation" in head.text
    assistant=client.get(f"/stats/college/{sid}/coach/Gonzaga/oc")
    assert assistant.status_code==200
    for value in ("Previous head coach","requires play-calling authority","Season-by-season Career Evidence","Previous Program","6.5"):
        assert value in assistant.text
    assert "Program Leadership" not in assistant.text
    assert client.get(f"/stats/college/{sid}/coach/Gonzaga/invalid").status_code==404
    hist=client.get(base+"/dynasty/coaching-history")
    assert hist.status_code==200
    assert hist.json()["current_staffs"]["Gonzaga"]["hc_name"]==dynasty._coaching_staffs["Gonzaga"]["head_coach"].full_name
