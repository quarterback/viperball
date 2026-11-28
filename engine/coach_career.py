"""CCH-09: persistent role experience, development and market reputation."""
import hashlib
import math
import random

from .coach_roles import (ALL_ROLES as ROLES, POSITION_ROLES, POSITION_DISCIPLINE,
                          career_path, experience, role_readiness)
ATTRS=("instincts","leadership","composure","rotations","development","recruiting")
FOCUS={"head_coach":(1,1.25,1.15,.95,.95,1.25),"oc":(1.2,.75,1,1.05,1.25,.85),
       "dc":(1.2,.85,1,1.2,1.15,.75),"stc":(1.05,.75,1.15,1.25,1.15,.75)}
def clip(x,lo=0.,hi=1.):
    return max(lo,min(hi,x))

def slider(card,key):
    return clip(float((getattr(card,"personality_sliders",{}) or {}).get(key,50))/100)

def ensure(card):
    state=getattr(card,"career_development",None)
    if state:
        for role in ROLES:
            state.setdefault("role_years", {}).setdefault(role, 0)
        if "legacy_role_years" not in state:
            origin = (getattr(card, "tactical_profile", {}) or {}).get("origin_role", card.role)
            state["legacy_role_years"] = {origin: max(0, card.seasons_coached - sum(state["role_years"].values()))}
        career_path(card, state)
        return state
    rng=random.Random(int.from_bytes(hashlib.sha256(("coach-career-v1:"+card.coach_id).encode()).digest()[:16],"big"))
    roll=rng.random()
    tier=1 if roll<.75 else 2 if roll<.95 else 3
    years={r:0 for r in ROLES}
    for stop in getattr(card,"career_history",[]) or []:
        if stop.role in years and stop.year_end is not None and stop.year_end>=stop.year_start and stop.wins+stop.losses>0:
            years[stop.role]+=stop.year_end-stop.year_start+1
    wp=getattr(card,"win_percentage",0.)
    n=getattr(card,"seasons_coached",0)
    prior=50+(wp-.5)*35*min(1,n/6)+min(8,getattr(card,"championships",0)*2)
    state={"version":1,"tier":tier,"interest_rate":round(rng.uniform(*{1:(.35,1.),2:(1.,1.8),3:(1.8,2.8)}[tier]),4),
           "role_years":years,"reputation":round(clip(prior,0,100),3),
           "ambition":round(clip((.55 if getattr(card,"wants_hc",False) else .45 if getattr(card,"role","")=="head_coach" else .12)+.30*slider(card,"aggression")+.15*rng.random()),3),
           "ever_head_coach":getattr(card,"role","")=="head_coach" or years["head_coach"]>0,
           "fractional_growth":{},"history":[]}
    card.career_development=state
    state["legacy_role_years"] = {card.role: max(0, n-sum(years.values()))}
    career_path(card, state)
    return state

def management(card):
    state=ensure(card)
    if not state.get("management"):
        from engine.coach_tactics import ensure_coach_tactical_profile
        tactics=ensure_coach_tactical_profile(card)
        origin=tactics.get("origin_role")
        specialty=origin if origin in ("oc","dc","stc") else {"offensive_mind":"oc","defensive_mind":"dc","special_teams_guru":"stc"}.get(getattr(card,"hc_affinity","balanced"))
        if origin in POSITION_ROLES or (origin in ("oc","dc","stc") and card.role in ("oc","dc","stc") and card.role != origin):
            # A promoted former position coach or crossover specialist retains
            # their proven calling discipline, not their earliest assignment.
            candidates = [r for r in ("oc","dc","stc") if experience(card,r,state)>0]
            specialty = card.role if card.role in candidates else max(candidates,key=lambda r:experience(card,r,state),default=POSITION_DISCIPLINE.get(origin))
        delegation=float(tactics.get("head_coach",{}).get("delegation",.6))
        state["management"]={"specialty":specialty,"retained_call":specialty if specialty and delegation<.62 else None,
            "delegation":delegation,"development":round(clip((card.development-25)/70),3),
            "recruiting":round(clip((card.recruiting-25)/70),3),
            "continuity":round((slider(card,"stubbornness")+slider(card,"player_trust"))/2,3),
            "game_management":round(clip((card.composure+card.instincts-50)/140),3),
            "staff_management":round(clip((card.leadership-25)/70),3)}
    return state["management"]

def appoint(card,role):
    state=ensure(card)
    if role=="head_coach":
        state["ever_head_coach"]=True
        management(card)
    card.role=role
    state["requires_calls"]=role!="head_coach" and state["ever_head_coach"]
    return card

def active_management(card):
    if card is None or getattr(card,"role","")!="head_coach":
        return {}
    return management(card)

def requires_calls(card,role):
    return role in ("oc","dc","stc") and bool(ensure(card).get("ever_head_coach"))

def caller(staff,role):
    staff=staff or {}
    coord=staff.get(role)
    hc=staff.get("head_coach")
    if hc is None:
        return coord
    m=active_management(hc)
    if m.get("retained_call")==role and not (coord and requires_calls(coord,role)):
        return hc
    return coord

def call_authority(staff,role):
    staff=staff or {}
    c=caller(staff,role)
    hc=staff.get("head_coach")
    if c is None:
        return 1.
    readiness = role_readiness(c, role, ensure(c))
    if hc is None or c is hc or requires_calls(c,role):
        return readiness
    return readiness * clip(.4+.6*active_management(hc).get("delegation",.5),.4,.95)

def aptitude(card):
    return .35*card.leadership+.30*card.instincts+.20*card.composure+.15*card.recruiting

def seeks_hc(card):
    state=ensure(card)
    if state["ever_head_coach"]:
        return True
    if card.role in POSITION_ROLES:
        return False
    path = career_path(card,state)
    if path["primary"] == "stc":
        return path["intent"] == "head_coach" and card.hc_meter >= 45
    return bool(getattr(card,"wants_hc",False) or state["ambition"]>=.65) and getattr(card,"hc_meter",0)>=45

def reputation(card):
    return ensure(card)["reputation"]

def veteran_premium(card):
    return min(1.,ensure(card)["role_years"].get("head_coach",0)/8.)

def pregame_probability(home,away,neutral=False):
    def quality(team):
        vals=sorted((float(p.overall) for p in team.players),reverse=True)[:22]
        return sum(vals)/max(1,len(vals))
    z=clip((quality(home)-quality(away))/12+(0 if neutral else .12),-4,4)
    return round(1/(1+math.exp(-z)),5)

def season_evidence(season,team):
    games=0; expected=0.; actual=0.
    if season is not None:
        for game in season.schedule:
            if not game.completed or team not in (game.home_team,game.away_team):
                continue
            prob=(game.full_result or {}).get("coach_expectation_home")
            if prob is None or game.home_score is None or game.away_score is None:
                continue
            home=team==game.home_team
            expected+=prob if home else 1-prob
            actual+=.5 if game.home_score==game.away_score else float((game.home_score>game.away_score)==home)
            games+=1
    return {"games":games,"expected":round(expected,3),"actual":actual,
            "above_expectation":round((actual-expected)/games,4) if games else None}

def record_season(card,role,year,team,wins,losses,evidence,playoff=False,conference=False,champion=False,prestige=50):
    st=ensure(card)
    if st.get("last_year",-1)>=year:
        return None
    st["role_years"][role]=st["role_years"].get(role,0)+1
    if role=="head_coach":
        st["ever_head_coach"]=True
        management(card)
    wp=wins/max(1,wins+losses)
    residual=evidence.get("above_expectation")
    if residual is None or evidence.get("games",0)<6:
        residual=0.
    target=clip(50+40*(wp-.5)+35*residual+5*int(playoff)+5*int(conference)+8*int(champion)+.08*(prestige-50),0,100)
    before=st["reputation"]
    st["reputation"]=round(clip(.78*before+.22*target,0,100),3)
    st["last_year"]=year
    event={"year":year,"team":team,"role":role,"coach_id":card.coach_id,"wins":wins,"losses":losses,
           "evidence":evidence,"reputation_before":before,"reputation_after":st["reputation"]}
    st["history"].append(event)
    return event

def grow(card,evidence=None,mentor=None):
    st=ensure(card)
    rate=st["interest_rate"]
    context=1+min(.15,max(0.,(evidence or {}).get("above_expectation") or 0.)*.3)
    if card.role in POSITION_ROLES and mentor is not None:
        context *= 1 + .05 * clip((mentor.development-50)/45) * slider(card,"adaptability")
    age_factor=1. if card.age<55 else .75 if card.age<60 else .5 if card.age<65 else .25
    result={}
    for attr,focus in zip(ATTRS,FOCUS.get(card.role,(.85,.85,1,1.05,1.35,1.20) if card.role in POSITION_ROLES else FOCUS["oc"])):
        old=getattr(card,attr)
        gap=max(0,95-old)
        annual_cap=clip(.65+gap*.06,.65,4.5)*(1 if st["tier"]==1 else 1.2 if st["tier"]==2 else 1.45)
        gain=min(annual_cap,gap*.025*rate*focus*context*age_factor)
        acc=st["fractional_growth"].get(attr,0.)+gain
        step=int(acc)
        st["fractional_growth"][attr]=round(acc-step,6)
        decline=1 if card.age>=65 and attr in ("instincts","rotations") else 0
        new=int(clip(old+step-decline,25,95))
        setattr(card,attr,new)
        if new!=old:
            result[attr]=new-old
    if card.role=="head_coach":
        m=management(card)
        for key,target in (("development",clip((card.development-25)/70)),("recruiting",clip((card.recruiting-25)/70)),("staff_management",clip((card.leadership-25)/70)),("game_management",clip((card.composure+card.instincts-50)/140))):
            m[key]=round(.85*m[key]+.15*target,4)
    return result

def position_boost(staff,position):
    staff=staff or {}
    from .coach_roles import position_role
    role=POSITION_DISCIPLINE.get(position_role(position),"oc")
    card=staff.get(role)
    if card is None:
        return 0.
    return min(1.5,max(0.,(card.development-50)/45)*.75+.75*veteran_premium(card))

def retirement_probability(age):
    """Candidate age curve; retirement is distinct from dismissal."""
    if age<60:
        return 0.
    if age>=80:
        return 1.
    return min(.65,.025*(age-59))

def retires(card,year):
    # Stable per coach and year; does not perturb hiring or game randomness.
    payload=f"coach-retirement-v1:{card.coach_id}:{year}".encode()
    u=int.from_bytes(hashlib.sha256(payload).digest()[:8],"big")/2**64
    return u<retirement_probability(card.age)

def staffing_preference(hc,candidate,role,team):
    """Modest ranking adjustment, not a game-day performance bonus."""
    m=active_management(hc)
    if not m or role=="head_coach":
        return 0.
    from engine.coach_tactics import ensure_coach_tactical_profile
    leadership=m.get("staff_management",.5)
    continuity=m.get("continuity",.5)
    # Reward existing knowledge of this program or shared tactical lineage.
    familiar=(candidate.team_name==team or any(
        getattr(stop,"team_name",None)==team for stop in candidate.career_history))
    mentor=any(x.get("coach_id")==hc.coach_id for x in candidate.coaching_tree)
    fit=0.
    if role in ("oc","dc"):
        k="offense_interpretation" if role=="oc" else "defense_interpretation"
        fit=float(ensure_coach_tactical_profile(hc)["identity"].get(k)==
                  ensure_coach_tactical_profile(candidate)["identity"].get(k))
    # Strong developers/recruiters seek complementary staff when their own
    # profile is weaker; the existing rank still dominates.
    teaching=(candidate.development-60)/35
    recruiting=(candidate.recruiting-60)/35
    complementary=(1-m.get("development",.5))*teaching+(1-m.get("recruiting",.5))*recruiting
    # An adaptive leader can hire an outside specialist rather than another
    # version of herself. Match role expertise and actual career experience.
    from .program_policy import program_policy
    innovation = program_policy({"head_coach":hc}).get("staff_innovation",0.)
    specialist = 0.
    if role in ("oc","dc") and not fit:
        specialist = innovation * min(1., experience(candidate,role,ensure(candidate))/5.) * 2
    return clip(continuity*(2*int(familiar)+1.5*int(mentor)+fit)+
                leadership*2*complementary+specialist,-3,5)

def continuity_carryover(staff,unit,familiarity):
    """Preserve a limited amount of practiced knowledge on succession."""
    hc=(staff or {}).get("head_coach")
    m=active_management(hc)
    if not m:
        return familiarity
    # A continuity-oriented leader preserves more of an existing installation;
    # does not manufacture familiarity for a newly invented system.
    retained=max(0.,unit.get("familiarity",0.)-familiarity)
    return clip(familiarity+retained*.20*m.get("continuity",.5),0,.85)
