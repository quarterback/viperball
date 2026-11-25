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


def test_retirement_and_management_preferences():
    from engine.coach_career import retirement_probability, retires, staffing_preference, continuity_carryover
    hc=card("leader")
    appoint(hc,"head_coach")
    m=active_management(hc)
    m["continuity"]=1.
    a=card("local"); a.team_name="A"
    b=card("outside"); b.team_name="B"
    b.tactical_profile=deepcopy(a.tactical_profile)
    b.tactical_profile["coach_id"]=b.coach_id
    assert staffing_preference(hc,a,"oc","A")>staffing_preference(hc,b,"oc","A")
    assert .3<continuity_carryover({"head_coach":hc},{"familiarity":.9},.3)<=.85
    assert retirement_probability(59)==0 and retirement_probability(80)==1
    hc.age=80
    assert retires(hc,2040)

def test_retired_coach_cannot_return_to_portal():
    from engine.coaching_portal import CoachingPortal,populate_coaching_portal,run_coaching_match
    c=card("retired","oc",True); c.age=80; c.hc_meter=100
    staff={"A":{"oc":c}}
    portal=CoachingPortal(year=2040)
    portal.add_vacancy("A","oc")
    populate_coaching_portal(portal,staff,{"A":(6,6)},{"A":50},retired_ids={c.coach_id},rng=random.Random(1))
    assert c.coach_id not in [e.coach_id for e in portal.entries]
    run_coaching_match(portal,staff,{"A":50},year=2040,rng=random.Random(1))
    assert staff["A"]["oc"].coach_id!=c.coach_id


def test_career_intent_is_stable_and_stc_is_viable():
    from engine.coach_roles import career_path
    counts = {"specialist":0, "coordinator":0, "head_coach":0}
    for i in range(2000):
        candidate = SimpleNamespace(coach_id="stc-population-"+str(i),role="stc",
                                    tactical_profile={},hc_affinity="balanced")
        state = {}
        first = career_path(candidate,state)
        counts[first["intent"]] += 1
        assert career_path(candidate,state) is first
    assert .60 < counts["specialist"]/2000 < .70
    assert .20 < counts["coordinator"]/2000 < .30
    assert .07 < counts["head_coach"]/2000 < .13
    stc = card("career-stc","stc",True,80)
    stc.hc_meter=100
    st=ensure(stc)
    st["career_path"].update(intent="specialist",secondary=None)
    st["role_years"]["stc"]=20
    assert not seeks_hc(stc)
    assert set(get_acceptable_roles(stc)) & {"oc","dc","head_coach"} == set()
    st["career_path"].update(intent="coordinator",secondary="dc",cross_after=5)
    assert "dc" in get_acceptable_roles(stc)
    assert "oc" not in get_acceptable_roles(stc)
    st["career_path"].update(intent="head_coach",secondary=None)
    assert seeks_hc(stc) and "head_coach" in get_acceptable_roles(stc)


def test_earned_oc_dc_crossover_preserves_identity_and_grows_readiness():
    c=card("crossover","oc",False,80)
    st=ensure(c)
    st["career_path"].update(intent="secondary",secondary="dc",cross_after=5)
    assert "dc" not in get_acceptable_roles(c)
    st["role_years"]["oc"]=5
    assert "dc" in get_acceptable_roles(c)
    profile=deepcopy(c.tactical_profile)
    appoint(c,"dc")
    assert call_authority({"dc":c},"dc")==.65
    assert c.tactical_profile==profile
    for y in range(2026,2029):
        record_season(c,"dc",y,"A",6,6,{"games":12,"above_expectation":0})
    assert call_authority({"dc":c},"dc")==1
    assert ensure(c)["role_years"]["oc"]==5
    assert CoachCard.from_dict(c.to_dict()).to_dict()==c.to_dict()


def test_position_teaching_career_and_market_promotion():
    from engine.coaching_portal import CoachingPortal, CoachingPortalEntry, run_coaching_match
    teacher=card("teacher","pos_dl",False,85)
    st=ensure(teacher)
    st["career_path"]["position_advancement"]="teaching"
    st["role_years"]["pos_dl"]=10
    assert "dc" not in get_acceptable_roles(teacher)
    st["career_path"]["position_advancement"]="coordinator"
    assert "dc" in get_acceptable_roles(teacher)
    assert "oc" not in get_acceptable_roles(teacher)
    portal=CoachingPortal(year=2027)
    portal.add_vacancy("B","dc")
    portal.add_entry(CoachingPortalEntry(teacher,"A","seeking_coordinator",2027,["dc"]))
    staffs={"A":{"pos_dl":teacher},"B":{}}
    run_coaching_match(portal,staffs,{"A":50,"B":65},year=2027,rng=random.Random(42))
    assert staffs["B"]["dc"].coach_id=="teacher"
    assert staffs["A"]["pos_dl"].coach_id!="teacher"
    assert portal.hires[0]["previous_role"]=="pos_dl"
    assert len({c.coach_id for s in staffs.values() for c in s.values()})==2


def test_position_staff_size_payroll_coverage_and_roundtrip():
    from engine.coach_roles import CORE_ROLES, POSITION_ROLES
    from engine.position_staff import ensure_position_staff, coverage, salary_cap
    staffs={t:{r:card(t+r,r,False,65) for r in CORE_ROLES} for t in ("A","B","C")}
    prestige={"A":20,"B":50,"C":90}
    assert len(ensure_position_staff(staffs,prestige,2026))==12
    assert [len(staffs[t]) for t in ("A","B","C")]==[6,8,10]
    assert ensure_position_staff(staffs,prestige,2026)==[]
    ids=[]
    for team,staff in staffs.items():
        assert set(coverage(staff))==set(POSITION_ROLES)
        assert all(v["coach_id"] for v in coverage(staff).values())
        for role,c in staff.items():
            ids.append(c.coach_id)
            if role in POSITION_ROLES:
                assert c.contract_salary<=salary_cap(prestige[team])
                assert c.role==role and c.team_name==team
                assert CoachCard.from_dict(c.to_dict()).to_dict()==c.to_dict()
    assert len(ids)==len(set(ids))
    assert coverage(staffs["A"])["pos_ol"]["coach_id"]==staffs["A"]["oc"].coach_id


def test_position_instruction_conserves_existing_growth_envelope():
    from engine.position_staff import instruction
    from engine.development import focus_position_ceiling
    staff={"pos_zb":card("zb","pos_zb",False,95),"pos_kicks":card("kicks","pos_kicks",False,95)}
    plan=instruction(staff,"Zeroback")
    base={a:2. for a in ("speed","awareness","hands","kicking","kick_accuracy")}
    ceiling={a:2.5 for a in base}
    revised=focus_position_ceiling(ceiling,base,plan)
    assert abs(sum(revised.values())-sum(ceiling.values()))<1e-9
    assert revised["speed"]<ceiling["speed"]
    assert revised["kick_accuracy"]>ceiling["kick_accuracy"]
    assert all(base[a]<=v<=ceiling[a]+.75 for a,v in revised.items())
    assert focus_position_ceiling(ceiling,base,{})==ceiling
    assert instruction({},"Zeroback")=={}


def test_position_coaches_change_recruiting_and_scouting_not_player_attributes():
    from engine.position_staff import recruiting_multiplier, scouting_error
    from engine.recruiting import auto_recruit_team
    teacher=card("scout","pos_zb",False,95)
    staff={"pos_zb":teacher}
    def prospect(name,technical):
        return SimpleNamespace(recruit_id=name,position="Zeroback",region="midwest",stars=3,
            true_overall=70,true_awareness=technical,true_hands=technical,true_kicking=technical,
            true_kick_accuracy=technical,committed_to=None,signed=False,offers=[])
    low=prospect("low",45);high=prospect("high",95)
    assert recruiting_multiplier(staff,high)==1.03
    assert recruiting_multiplier(staff,low)==.97
    assert recruiting_multiplier({},high)==1
    assert scouting_error(staff,"Zeroback")==1 and scouting_error(staff,"Halfback")==3
    class NoNoise:
        def uniform(self,lo,hi): return (lo+hi)/2
    board,nil=auto_recruit_team("A",[low,high],60,"midwest",scholarships=1,
                                rng=NoNoise(),position_staff=staff)
    assert board.offered[0]=="high" and "high" in nil
    assert high.true_overall==70 and high.true_kicking==95


def test_alumni_enter_only_after_delay_and_are_not_duplicated():
    from engine.coach_roles import stable_rng
    from engine.position_staff import alumni_candidates, available_alumni
    pid=next("grad-"+str(i) for i in range(10000)
             if stable_rng("alumni-coaching-v1:grad-"+str(i)).random()<.04)
    p=SimpleNamespace(player_id=pid,position="Keeper",year="Graduate",coachability=95,
                      first_name="Former",last_name="Player",full_name="Former Player")
    rows=alumni_candidates({"A":[p]},2027,{})
    assert len(rows)==1
    h={2027:{"alumni_candidates":rows}}
    year=rows[0]["ready_year"]
    assert 2030<=year<=2033
    assert alumni_candidates({"A":[p]},2028,h)==[]
    assert available_alumni(h,year-1,{})==[]
    entry=available_alumni(h,year,{})[0]
    assert entry.former_player_id==pid and entry.role=="pos_coverage" and entry.alma_mater=="A"
    assert available_alumni(h,year,{"A":{"pos_coverage":entry}})==[]
    h[year]={"portal_hires":[{"coach_id":entry.coach_id}]}
    assert available_alumni(h,year+1,{})==[]
