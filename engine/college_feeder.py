"""Shared high school competition and college recruiting lifecycle."""
from copy import deepcopy
import random
import threading

from engine.hs_league import (
    create_hs_league, simulate_hs_season, advance_hs_league,
    hs_player_to_recruit,
)
from engine.recruiting import (
    HSRecruitingPipeline, HSProspect, _apply_scouting_noise,
    _rank_hs_class, seed_recruiting_interest,
)
from engine.talent import STAT_KEYS

GRADE = {"Freshman": "9th", "Sophomore": "10th", "Junior": "11th", "Senior": "12th"}


def competition_index(league):
    index = {}
    for team in league.teams.values():
        for player in team.players:
            if not player.player_id or player.player_id in index:
                raise ValueError("Missing or duplicate high school player identity")
            index[player.player_id] = (team, player)
    return index


def verify_pipeline(league, pipeline):
    if pipeline.source_league_year != league.year:
        raise ValueError("Recruiting and competition years differ")
    index = competition_index(league)
    seen = set()
    for grade, rows in pipeline.classes.items():
        for prospect in rows:
            r = prospect.recruit
            if r.recruit_id in seen or r.recruit_id not in index:
                raise ValueError("Recruiting prospect identity missing or duplicated")
            seen.add(r.recruit_id)
            team, p = index[r.recruit_id]
            if grade != GRADE[p.year] or prospect.grade != grade:
                raise ValueError("Recruiting prospect grade differs from competition")
            if (r.full_name, r.position, r.high_school, r.hometown) != (p.name, p.position, team.school_name, p.hometown):
                raise ValueError("Recruiting prospect biography differs from competition")
            if r.true_overall != p.overall or any(getattr(r, "true_"+attr) != getattr(p, attr) for attr in STAT_KEYS):
                raise ValueError("Recruiting prospect ratings differ from competition")
            if (r.true_work_rate, r.true_potential, r.true_development) != (p.work_rate, p.potential, p.development):
                raise ValueError("Recruiting prospect development metadata differs from competition")
    return seen


def pipeline_from_league(league, size_per_class, team_names, prestige=None, previous=None):
    """The recruiting board is a bounded view of actual competition players.

    Carry the tracked cohort forward without redrawing its membership. A
    fresh cohort is sampled without selecting on actual ability; no talent
    inflation from duplicating or developing an independent population.
    """
    index = competition_index(league)
    old = {p.recruit.recruit_id: p for rows in previous.classes.values() for p in rows} if previous else {}
    classes = {}
    for year_name, grade in GRADE.items():
        players = [(pid, t, p) for pid,(t,p) in index.items() if p.year == year_name]
        continuing = [(pid,t,p) for pid,t,p in players if pid in old]
        newcomers = [(pid,t,p) for pid,t,p in players if pid not in old]
        rng = random.Random(f"hs-recruit-view:{league.year}:{grade}")
        rng.shuffle(newcomers)
        selected = continuing + newcomers[:max(0, size_per_class-len(continuing))]
        rows, new_rows = [], []
        for pid, team, player in selected:
            recruit = hs_player_to_recruit(player, team)
            if pid in old:
                prospect = deepcopy(old[pid])
                # Preserve scouting, academic and recruiting history; copy
                # only authoritative physical ratings and competition stars.
                previous_recruit = prospect.recruit
                for attr in STAT_KEYS:
                    setattr(previous_recruit,"true_"+attr,getattr(recruit,"true_"+attr))
                for attr in ("true_work_rate","true_potential","true_development","stars"):
                    setattr(previous_recruit,attr,getattr(recruit,attr))
                prospect.grade = grade
                prospect.scouted_stars = _apply_scouting_noise(previous_recruit.stars,grade,rng)
                # New observations must not silently retain stale ratings.
                previous_recruit.scouted_attrs = {}
                previous_recruit.scout_level = "none"
            else:
                prospect = HSProspect(recruit=recruit, grade=grade,
                    scouted_stars=_apply_scouting_noise(recruit.stars,grade,rng))
                new_rows.append(prospect)
            rows.append(prospect)
        if team_names and new_rows:
            seed_recruiting_interest(new_rows, team_names, team_prestige=prestige, rng=rng)
        _rank_hs_class(rows)
        classes[grade] = rows
    pipeline = HSRecruitingPipeline(classes=classes, source_league_year=league.year,
                                    next_graduation_year=league.year+5)
    verify_pipeline(league,pipeline)
    return pipeline


def _isolated_sim(league):
    # Full-engine postseason games seed Python's global random stream.
    # Never let a scouting-page visit change the college schedule or RNG.
    state = random.getstate()
    try:
        return simulate_hs_season(league, rng=random.Random(f"hs-games:{league.year}"))
    finally:
        random.setstate(state)


def _backstory_sim(league):
    """The high school season before a dynasty starts. It happened before the
    player arrived, so every round runs on the quick model; live seasons
    (advance_college_feeder) keep full engine title games. The quick model
    draws only from its own seeded stream, never Python's global one, so this
    is safe to run on a background thread."""
    return simulate_hs_season(league, rng=random.Random(f"hs-games:{league.year}"),
                              engine_rounds=set())


# One feeder build at a time. Dynasty creation builds the feeder on a
# background thread; a page or offseason step that needs it first waits for
# that build instead of starting a second copy.
_FEEDER_LOCK = threading.RLock()
_BUILDS = {}   # id(dynasty) -> background build thread


def build_college_feeder_in_background(dynasty, year, team_names, on_done=None):
    """Build the high school league and recruiting board after the dynasty
    creation response goes out. on_done(dynasty) runs afterward (the API
    saves the dynasty again there)."""
    key = id(dynasty)

    def work():
        try:
            with _FEEDER_LOCK:
                _ensure_college_feeder(dynasty, year, team_names)
            if on_done:
                on_done(dynasty)
        except Exception:
            pass  # Non-critical: built again on first use or first offseason
        finally:
            _BUILDS.pop(key, None)

    t = threading.Thread(target=work, name="college-feeder", daemon=True)
    _BUILDS[key] = t   # registered before it starts, so no reader can miss it
    t.start()
    return t


def wait_for_feeder(dynasty):
    """Block until a background feeder build for this dynasty finishes."""
    t = _BUILDS.get(id(dynasty))
    if t is not None and t is not threading.current_thread():
        t.join()


def ensure_college_feeder(dynasty, year=None, team_names=None, size_per_class=None):
    wait_for_feeder(dynasty)
    with _FEEDER_LOCK:
        return _ensure_college_feeder(dynasty, year, team_names, size_per_class)


def _ensure_college_feeder(dynasty, year=None, team_names=None, size_per_class=None):
    year = dynasty.current_year if year is None else year
    retired = set(getattr(dynasty,"retired_programs",[]) or [])
    names = [t for t in (team_names if team_names is not None else dynasty.team_histories) if t not in retired]
    size = size_per_class or max(300,len(names)*12)
    league = dynasty._hs_league
    pipeline = dynasty._hs_pipeline
    if league is None:
        # Legacy saves have no durable competition roster. Do not match
        # unrelated synthetic prospects by name; start a new feeder cohort.
        league = _backstory_sim(create_hs_league(year,rng=random.Random(year)))
        pipeline = None
    if league.year != year:
        raise ValueError(f"High school feeder year {league.year} does not match {year}")
    if pipeline is None or pipeline.source_league_year != year:
        pipeline = pipeline_from_league(league,size,names,dynasty.team_prestige)
    else:
        verify_pipeline(league,pipeline)
    dynasty._hs_league, dynasty._hs_pipeline = league,pipeline
    return pipeline


def advance_college_feeder(dynasty, year, team_names=None, size_per_class=None, *, include_reserve=False):
    """Graduate exactly the tracked seniors, advance the competition once."""
    wait_for_feeder(dynasty)
    with _FEEDER_LOCK:
        return _advance_college_feeder(dynasty, year, team_names, size_per_class,
                                       include_reserve=include_reserve)


def _advance_college_feeder(dynasty, year, team_names=None, size_per_class=None, *, include_reserve=False):
    retired = set(getattr(dynasty,"retired_programs",[]) or [])
    names = [t for t in (team_names if team_names is not None else dynasty.team_histories) if t not in retired]
    size = size_per_class or max(300,len(names)*12)
    old = ensure_college_feeder(dynasty,year-1,names,size)
    graduates = [deepcopy(p.recruit) for p in old.classes["12th"]]
    tracked = {r.recruit_id for r in graduates}
    reserve = [hs_player_to_recruit(p,t) for t in dynasty._hs_league.teams.values()
               for p in t.seniors if p.player_id not in tracked] if include_reserve else []
    league = _isolated_sim(advance_hs_league(dynasty._hs_league,year,
                                            rng=random.Random(f"hs-development:{year}")))
    new = pipeline_from_league(league,size,names,dynasty.team_prestige,previous=old)
    if {r.recruit_id for r in graduates} & set(competition_index(league)):
        raise ValueError("High school graduate remained in active competition")
    dynasty._hs_league, dynasty._hs_pipeline = league,new
    return (graduates,reserve) if include_reserve else graduates
