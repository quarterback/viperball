from copy import deepcopy
from types import SimpleNamespace
import random
from engine.coaching import CoachCard, advance_hc_meter, get_acceptable_roles, calculate_coach_salary
from engine.coach_career import (ensure, appoint, active_management, caller, call_authority,
    record_season, grow, position_boost, requires_calls, seeks_hc, pregame_probability)
from engine.coach_tactics import resolve_offensive_tactics
from engine.team_installation import new_installation

def card(cid,role="oc",wants=False,grade=60):
    return CoachCard(coach_id=cid,first_name="Test",last_name=cid,gender="female",age=40,
        role=role,classification="scheme_master",instincts=grade,leadership=grade,
        composure=grade,rotations=grade,development=grade,recruiting=grade,wants_hc=wants)

def test_first_promotion_and_dormant_management():
    c=card("promotion")
    assert active_management(c)=={}
    base=deepcopy(c.tactical_profile)
    c.tactical_profile["head_coach"]["delegation"]=.4
    appoint(c,"head_coach")
    m=deepcopy(active_management(c))
    assert m["retained_call"]=="oc"
    assistant=card("assistant")
    staff={"head_coach":c,"oc":assistant}
    assert caller(staff,"oc") is c
    assert resolve_offensive_tactics(staff)["coach_id"]==c.coach_id
    assert new_installation("A",staff,"balanced","swarm")["offense"]["coach_id"]==c.coach_id
    appoint(c,"oc")
    assert active_management(c)=={} and requires_calls(c,"oc")
    appoint(c,"head_coach")
    assert active_management(c)==m
    assert c.tactical_profile["identity"]==base["identity"]
    assert CoachCard.from_dict(c.to_dict()).to_dict()==c.to_dict()

def test_former_head_calls_and_develops_own_unit():
    hc=card("hc")
    hc.tactical_profile["head_coach"]["delegation"]=.4
    appoint(hc,"head_coach")
    vet=card("vet","oc")
    appoint(vet,"head_coach")
    ensure(vet)["role_years"]["head_coach"]=8
    appoint(vet,"oc")
    staff={"head_coach":hc,"oc":vet}
    assert caller(staff,"oc") is vet and call_authority(staff,"oc")==1
    assert position_boost(staff,"Zeroback") > position_boost({"oc":card("novice")},"Zeroback")
    assert position_boost(staff,"Keeper")==0

def test_readiness_does_not_create_ambition():
    c=card("lifelong")
    ensure(c)["ambition"]=.1
    for _ in range(30):
        advance_hc_meter(c,12,0,rng=random.Random(1))
    assert c.hc_meter==100 and not c.wants_hc
    assert not seeks_hc(c) and "head_coach" not in get_acceptable_roles(c)
    c.wants_hc=True
    assert seeks_hc(c)

def test_market_evidence_and_growth_are_separate():
    a=card("same")
    b=CoachCard.from_dict(deepcopy(a.to_dict()))
    low={"games":12,"above_expectation":-.2}
    high={"games":12,"above_expectation":.2}
    record_season(a,"oc",2026,"A",2,10,low)
    record_season(b,"oc",2026,"B",10,2,high,True)
    assert ensure(b)["reputation"]>ensure(a)["reputation"]
    assert calculate_coach_salary(b,random.Random(4))>calculate_coach_salary(a,random.Random(4))
    assert record_season(a,"oc",2026,"A",2,10,low) is None
    assert ensure(a)["role_years"]["oc"]==1
    before=a.overall
    for _ in range(5):
        grow(a,low)
    assert a.overall>=before
    assert ensure(a)["interest_rate"]==ensure(b)["interest_rate"]

def test_pregame_probability_is_complementary_neutral():
    a=SimpleNamespace(players=[SimpleNamespace(overall=60)]*22)
    b=SimpleNamespace(players=[SimpleNamespace(overall=40)]*22)
    assert pregame_probability(a,b,True)>.5
    assert abs(pregame_probability(a,b,True)+pregame_probability(b,a,True)-1)<1e-5
