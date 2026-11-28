from types import SimpleNamespace
from engine.program_policy import roster_horizon, recruit_preference, portal_preference

def test_roster_horizon_excludes_graduates():
    h = roster_horizon([{"position":"Viper","year":"Graduate"},
                       {"position":"Viper","year":"Sophomore"}])
    assert h["Viper"] == {"continuing":1,"young":1,"gap":2}

def test_development_and_immediate_help_are_distinct():
    h = roster_horizon([])
    builder = {"development_horizon":1,"immediate_help":0}
    buyer = {"development_horizon":0,"immediate_help":1}
    raw = SimpleNamespace(position="Viper",true_potential=5,coachability=95)
    low = SimpleNamespace(position="Viper",true_potential=1,coachability=25)
    assert recruit_preference(raw,builder,h)>recruit_preference(low,builder,h)
    assert recruit_preference(raw,buyer,h)==recruit_preference(low,buyer,h)
    def entry(year):
        return SimpleNamespace(position="Viper",player_card=SimpleNamespace(year=year,potential=3,coachability=60))
    assert portal_preference(entry("Senior"),buyer,h,{}) > portal_preference(entry("Freshman"),buyer,h,{})
    assert portal_preference(entry("Freshman"),builder,h,{}) > portal_preference(entry("Senior"),builder,h,{})
    assert recruit_preference(raw,{},h)==1
    assert portal_preference(entry("Senior"),{},h,{})==0

def test_upward_learning_requires_attribution_and_is_bounded(monkeypatch):
    from engine import coach_learning as cl
    from engine.coaching import CoachCard
    from engine.coach_career import ensure
    from engine.coach_tactics import ensure_coach_tactical_profile
    def coach(cid,role):
        c=CoachCard(coach_id=cid,first_name="Test",last_name=cid,age=45,gender="female",
          role=role,classification="scheme_master",instincts=75,leadership=75,
          composure=75,rotations=70,development=75,recruiting=70,
          personality_sliders={"adaptability":100,"stubbornness":0})
        ensure(c)["history"]=[{"year":2026,"team":"A"}]
        return c
    hc,oc=coach("hc","head_coach"),coach("oc","oc")
    dc = coach("dc", "dc")
    h=ensure_coach_tactical_profile(hc)
    o=ensure_coach_tactical_profile(oc)
    h["offense"]["family_bias"]["kick_pass"]=-.1
    o["offense"]["family_bias"]["kick_pass"]=.1
    assert cl.learn_from_coordinator(hc,oc,"oc","A",2026,None) is None
    monkeypatch.setattr(cl, "observe", lambda season, team, card, role: {
        "games": 8, "high": 40, "low": 40, "contrast": 0.5 if role == "oc" else -0.5,
    })
    ev=cl.learn_from_coordinator(hc,oc,"oc","A",2026,object())
    assert ev and 0<ev["after"]<=cl.MENTOR_STEP
    assert h["offense"]["family_bias"]["kick_pass"]==-.1
    assert cl.learn_from_coordinator(hc,oc,"oc","A",2026,object()) is None
    h["defense"]["pressure_bias"] = -0.1
    ensure_coach_tactical_profile(dc)["defense"]["pressure_bias"] = 0.1
    defense = cl.learn_from_coordinator(hc, dc, "dc", "A", 2026, object())
    assert defense["key"] == "pressure" and 0 < defense["after"] <= cl.MENTOR_STEP
    assert h["learning"]["mentorship"]["kick_mix"] == ev["after"]
    assert cl.learn_from_coordinator(hc, dc, "dc", "A", 2026, object()) is None


def test_joint_objective_is_shared_and_clock_sensitive():
    from engine.program_policy import live_objective, objective_bias
    p={"objective":"territory_control","strength":.5,"hc_id":"h"}
    live=live_objective(p,4,2,300)
    assert objective_bias(live,"offense")["power"]>0
    assert objective_bias(live,"defense")["spread"]>0
    assert objective_bias(live,"st")["field_position_bias"]>0
    urgent=live_objective(p,-4,4,120)
    assert objective_bias(urgent,"offense")["kick_pass"]>0
    assert objective_bias(urgent,"defense")["aggressive"]>0
    assert objective_bias(urgent,"st")["return_aggression"]>0
    assert live_objective({},4,4,30)=={}


def test_curriculum_conserves_instruction_weight(monkeypatch):
    from engine.position_staff import instruction
    from engine import program_policy
    staff={"pos_zb":SimpleNamespace(development=75)}
    monkeypatch.setattr(program_policy,"curriculum",lambda *a:{})
    base=instruction(staff,"Zeroback")
    monkeypatch.setattr(program_policy,"curriculum",lambda *a:{"kicking":1.0})
    revised=instruction(staff,"Zeroback")
    assert base["focus"]==revised["focus"]
    assert abs(sum(base["weights"].values())-sum(revised["weights"].values()))<1e-9
    assert revised["weights"]["kicking"]>base["weights"]["kicking"]
