"""Observational longitudinal study of the actual college dynasty.

This module only records state. The existing benchmark drives every game,
recruiting transition, portal, and database reload. No synthetic outcomes,
forced coach moves, or gameplay tuning. Reports are checkpointed annually.
"""
from collections import Counter, defaultdict
from pathlib import Path
import json
import statistics
import subprocess

ATTRS=("instincts","leadership","composure","rotations","development","recruiting")
PLAYER_ATTRS=("speed","stamina","agility","power","awareness","hands","kicking",
              "kick_power","kick_accuracy","lateral_skill","tackling")

def stats(values):
    v=sorted(values)
    if not v:
        return {"n":0}
    def q(p):
        return round(v[round(p*(len(v)-1))],3)
    return {"n":len(v),"mean":round(statistics.mean(v),3),"min":v[0],
            "p10":q(.1),"median":q(.5),"p90":q(.9),"max":v[-1]}

def ratio(a,b):
    return round(a/b,5) if b else None

def write(path,data):
    path=Path(path)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data,sort_keys=True,indent=2))
    tmp.replace(path)

def coaches(dyn,active):
    rows={}
    for team in sorted(active):
        for role,c in sorted(dyn._coaching_staffs[team].items()):
            st=c.career_development
            rows[c.coach_id]={"team":team,"role":role,"age":c.age,"overall":c.overall,
                "attributes":{a:getattr(c,a) for a in ATTRS},"classification":c.classification,
                "tier":st.get("tier"),"interest_rate":st.get("interest_rate"),
                "ambition":st.get("ambition"),"wants_hc":c.wants_hc,
                "readiness":c.hc_meter,"reputation":st.get("reputation"),
                "ever_head_coach":st.get("ever_head_coach",False),
                "role_years":dict(st.get("role_years",{})),
                "career_wins":c.career_wins,"career_losses":c.career_losses,
                "salary":c.contract_salary,"management":dict(st.get("management",{}))}
    return rows

def roster_rows(teams):
    from engine.player_card import player_to_card
    result={}
    for name,t in sorted(teams.items()):
        for p in t.players:
            c=player_to_card(p,name)
            result[p.player_id]={"team":name,"position":p.position,"class":p.year,
                "overall":c.overall,"attributes":{a:getattr(c,a) for a in PLAYER_ATTRS}}
    return result

def roster_summary(rows):
    classes=defaultdict(list)
    positions=defaultdict(list)
    for p in rows.values():
        classes[p["class"]].append(p["overall"])
        positions[p["position"]].append(p["overall"])
    return {"overall":stats([p["overall"] for p in rows.values()]),
            "classes":{k:stats(v) for k,v in classes.items()},
            "positions":{k:stats(v) for k,v in positions.items()}}

def expectations(season):
    """Pregame proxy calibration, not causal attribution to coaches."""
    bins=defaultdict(lambda:{"n":0,"predicted_sum":0.,"actual_sum":0.,"brier_sum":0.})
    missing=0
    for g in season.schedule:
        p=(g.full_result or {}).get("coach_expectation_home")
        if p is None or g.home_score is None or g.away_score is None:
            missing+=1
            continue
        y=.5 if g.home_score==g.away_score else float(g.home_score>g.away_score)
        if not 0<=p<=1:
            raise RuntimeError("Pregame expectation outside probability bounds")
        bucket=bins[str(min(9,int(p*10)))]
        bucket["n"]+=1
        bucket["predicted_sum"]+=p
        bucket["actual_sum"]+=y
        bucket["brier_sum"]+=(p-y)**2
    return {"bins":dict(bins),"missing":missing}

def career_summary(rows):
    groups=defaultdict(list)
    for row in rows.values():
        groups[str(row["tier"])].append(row)
    return {"active":len(rows),"age":stats([r["age"] for r in rows.values()]),
        "ability":stats([r["overall"] for r in rows.values()]),
        "reputation":stats([r["reputation"] for r in rows.values() if r["reputation"] is not None]),
        "readiness":stats([r["readiness"] for r in rows.values() if r["role"]!="head_coach"]),
        "role_counts":dict(Counter(r["role"] for r in rows.values())),
        "tier_counts":dict(Counter(str(r["tier"]) for r in rows.values())),
        "age_75_plus":sum(r["age"]>=75 for r in rows.values()),
        "former_hc_assistants":sum(r["ever_head_coach"] and r["role"]!="head_coach" for r in rows.values()),
        "ready_nonaspiring_assistants":sum(r["role"]!="head_coach" and r["readiness"]>=75 and not r["wants_hc"] and (r["ambition"] or 0)<.65 for r in rows.values()),
        "by_tier":{k:{"ability":stats([r["overall"] for r in v]),
                      "age":stats([r["age"] for r in v])} for k,v in groups.items()}}

class Study:
    def __init__(self,out,seed,years):
        self.out=Path(out)/"longitudinal"
        self.out.mkdir(parents=True,exist_ok=True)
        try:
            commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
        except (OSError,subprocess.CalledProcessError):
            commit=None
        self.summary={"schema":1,"seed":seed,"commit":commit,"requested_seasons":years,
            "complete":False,"years":[],"transitions":[]}
        self.first_coaches={}
        self.latest_coaches={}
        self.program_paths=defaultdict(list)
        self.coach_paths=defaultdict(list)
        self.flush()

    def flush(self):
        write(self.out/"summary.json",self.summary)

    def opening(self,year,dyn,season):
        active=set(season.teams)
        self.open_coaches=coaches(dyn,active)
        self.open_players=roster_rows(season.teams)
        self.open_prestige={t:dyn.team_prestige.get(t,50) for t in sorted(active)}
        self.opening_by_team=defaultdict(list)
        for row in self.open_players.values():
            self.opening_by_team[row["team"]].append(row["overall"])
        for cid,row in self.open_coaches.items():
            self.first_coaches.setdefault(cid,row)
            self.latest_coaches[cid]=row
            self.coach_paths[cid].append({"year":year,"phase":"opening",**row})
        write(self.out/f"{year}-opening.json",{"coaches":self.open_coaches,
            "players":self.open_players,"prestige":self.open_prestige})

    def season_end(self,year,dyn,season,item):
        from engine.coach_career import season_evidence
        programs={}
        call_counts=Counter()
        for g in list(season.schedule)+list(season.playoff_bracket):
            fr=g.full_result or {}
            for key in ("coach_tactics","defensive_coach_tactics"):
                for side in ("home","away"):
                    data=fr.get(key,{}).get(side,{})
                    if not data:
                        continue
                    actual=data.get("play_caller_id")
                    employed=data.get("employed_oc_id" if key=="coach_tactics" else "employed_dc_id")
                    if actual and employed:
                        call_counts[key+":caller_games"]+=1
                        call_counts[key+":different_from_employed"]+=int(actual!=employed)
        for name,t in sorted(season.teams.items()):
            rec=season.standings[name]
            values=self.opening_by_team[name]
            row={"year":year,"opening_prestige":self.open_prestige[name],
                "closing_prestige":dyn.team_prestige.get(name,50),
                "wins":rec.wins,"losses":rec.losses,"champion":season.champion==name,
                "opening_roster":stats(values),"opening_top22":stats(sorted(values,reverse=True)[:22]),
                "staff":{role:c.coach_id for role,c in dyn._coaching_staffs[name].items()},
                "expectation":season_evidence(season,name)}
            programs[name]=row
            self.program_paths[name].append(row)
        record={"year":year,"regular_games":item["regular_games"],"playoff_games":item["playoff_games"],
            "champion":season.champion,"opening_coaching":career_summary(self.open_coaches),
            "opening_roster":roster_summary(self.open_players),"programs":programs,
            "expectation_calibration":expectations(season),"calling_authority":dict(call_counts)}
        self.summary["years"].append(record)
        self.milestones()
        self.flush()
        write(self.out/f"{year}-programs.json",programs)
        print("LONGITUDINAL_YEAR",year,json.dumps({"coaching":record["opening_coaching"],
            "roster":record["opening_roster"],"calling_authority":dict(call_counts)},sort_keys=True),flush=True)

    def developed(self,year,player_cards):
        # The API's completed offseason development, before transfers/signings.
        groups=defaultdict(list)
        for team,cards in player_cards.items():
            for card in cards:
                old=self.open_players.get(card.player_id)
                if not old:
                    continue
                row={"player_id":card.player_id,"team":team,"position":card.position,
                    "previous_class":old["class"],"next_class":card.year,
                    "overall_delta":card.overall-old["overall"],
                    "attribute_deltas":{a:getattr(card,a)-old["attributes"][a] for a in PLAYER_ATTRS}}
                groups[team].append(row)
        self.development={"groups":dict(groups),"observed":sum(len(v) for v in groups.values())}
        write(self.out/f"{year}-development.json",self.development)

    def transition(self,year,dyn,active,trans):
        closing=coaches(dyn,active)
        history=dyn.coaching_history[year+1]
        hires=history.get("portal_hires",[])
        moves=Counter()
        for hire in hires:
            origin=hire.get("previous_role")
            target=hire.get("role")
            moves[(origin or "unrecorded")+"->"+str(target)]+=1
        for cid,row in closing.items():
            self.first_coaches.setdefault(cid,row)
            self.latest_coaches[cid]=row
            self.coach_paths[cid].append({"year":year+1,"phase":"post_offseason",**row})
        departed=set(self.open_coaches)-set(closing)
        new=set(closing)-set(self.open_coaches)
        groups=defaultdict(list)
        for entries in self.development["groups"].values():
            for p in entries:
                groups[p["position"]].append(p["overall_delta"])
        record={"from_year":year,"to_year":year+1,"database_roundtrip":trans["database_roundtrip"],
            "retained":len(set(self.open_coaches)&set(closing)),"departed":len(departed),"new":len(new),
            "role_moves":dict(moves),"hire_reasons":dict(Counter(h.get("reason","unknown") for h in hires)),
            "coaching":career_summary(closing),"college_cohort":trans["college_cohort"],
            "development_by_position":{k:stats(v) for k,v in groups.items()}}
        self.summary["transitions"].append(record)
        write(self.out/f"{year}-transition.json",{"closing_coaches":closing,
            "departed":sorted(departed),"new":sorted(new),"hires":hires,
            "career_evidence":history.get("career_development",[]),
            "attribute_changes":history.get("development",[]),"summary":record})
        self.milestones()
        self.flush()
        print("LONGITUDINAL_TRANSITION",year,json.dumps(record,sort_keys=True),flush=True)

    def milestones(self):
        years=self.summary["years"]
        if not years:
            return
        n=len(years)
        # Report observed identity changes, with exposure rather than treating
        # coaches who disappear from the active staff pool as confirmed retired.
        trajectories=[]
        for cid,first in self.first_coaches.items():
            latest=self.latest_coaches[cid]
            path=self.coach_paths[cid]
            trajectories.append({"coach_id":cid,"tier":first["tier"],
                "first_role":first["role"],"last_role":latest["role"],
                "first_team":first["team"],"last_team":latest["team"],
                "overall_change":latest["overall"]-first["overall"],
                "observed_seasons":len({r["year"] for r in path if r["phase"]=="opening"}),
                "observed_first_promotion":any(r["role"]=="head_coach" for r in path) and first["role"]!="head_coach",
                "initial_ever_hc":first["ever_head_coach"],"latest_age":latest["age"]})
        write(self.out/"coach_trajectories.json",{"trajectories":trajectories,"paths":dict(self.coach_paths)})
        write(self.out/"program_trajectories.json",dict(self.program_paths))
        self.summary["observed_coaches"]=len(trajectories)
        self.summary["ability_change_by_tier"]={str(t):stats([r["overall_change"] for r in trajectories
            if r["tier"]==t and r["observed_seasons"]>=5]) for t in (1,2,3)}
        self.summary["first_observed_promotions"]=sum(r["observed_first_promotion"] and not r["initial_ever_hc"] for r in trajectories)
        self.summary["games"]=sum(y["regular_games"]+y["playoff_games"] for y in years)
        if n in (5,10,20,30) and (not self.summary["transitions"] or self.summary["transitions"][-1]["to_year"]<=years[-1]["year"]):
            self.summary.setdefault("milestones",{})[str(n)]={"year":years[-1]["year"],"games":self.summary["games"],
                "coaching":years[-1]["opening_coaching"],"roster":years[-1]["opening_roster"],
                "champion":years[-1]["champion"],"completed_offseasons":len(self.summary["transitions"])}

    def finish(self):
        self.summary["complete"]=True
        self.flush()
