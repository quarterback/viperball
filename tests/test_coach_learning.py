from types import SimpleNamespace
from engine.coaching import CoachCard
from engine.coach_learning import adapt, observe, offense_bias, pressure_bias, LIMIT, STEP
from engine.coach_tactics import ensure_coach_tactical_profile

def card(role="oc"):
    return CoachCard(coach_id="learning-"+role,first_name="Test",last_name="Coach",
        gender="female",age=40,role=role,classification="scheme_master",
        personality_sliders={"adaptability":100,"stubbornness":0})

def season(c, n=6):
    plays=[]
    for _ in range(6):
        for family,yards in (("kick_pass",20),("power",0)):
            plays.append({"snap_possession":"home","play_family":family,"down":1,
                "yards_to_go":20,"field_position":40,"yards":yards,"result":"gain"})
    games=[SimpleNamespace(completed=True,home_team="A",away_team="B",full_result={
        "coach_tactics":{"home":{"oc_id":c.coach_id}},"play_by_play":plays}) for _ in range(n)]
    return SimpleNamespace(schedule=games,playoff_bracket=[])

def test_evidence_floor_and_idempotence():
    c=card()
    assert not adapt(c,"oc","A",2026,season(c,2))["sufficient"]
    assert adapt(c,"oc","A",2026,season(c)) is None
    p=ensure_coach_tactical_profile(c)
    identity=p["identity"].copy()
    e=adapt(c,"oc","A",2027,season(c))
    assert e["sufficient"] and 0 < e["after"] <= STEP
    assert p["identity"] == identity
    assert offense_bias(p)["kick_pass"] > p["offense"]["family_bias"].get("kick_pass",0)
    for y in range(2028,2040):
        adapt(c,"oc","A",y,season(c))
    assert abs(p["learning"]["kick_mix"]) <= LIMIT
    loaded=CoachCard.from_dict(c.to_dict())
    assert ensure_coach_tactical_profile(loaded) == p

def test_unattributed_games_do_not_teach():
    c=card()
    s=season(card("dc"))
    assert observe(s,"A",c,"oc")["games"] == 0
