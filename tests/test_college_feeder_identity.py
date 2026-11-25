"""The college recruiting board must represent real competition players."""
import json
import random
from dataclasses import asdict
from types import SimpleNamespace

from engine.college_feeder import (
    competition_index, pipeline_from_league, verify_pipeline,
    advance_college_feeder,
)
from engine.hs_league import HSLeague, generate_hs_team, hs_player_id, simulate_hs_season
from engine.hs_league_data import HS_YEAR_ORDER
from engine.roster_continuity import assign_opening_roster_ids


def miniature_league():
    league = HSLeague(year=2026)
    rng = random.Random(22)
    for state in ("OR", "WA"):
        for school in ("Central", "West"):
            team = generate_hs_team(school,state,"Metro",rng)
            for i,p in enumerate(team.players):
                p.player_id = hs_player_id(team.key,league.year-HS_YEAR_ORDER.index(p.year),i)
            league.teams[team.key] = team
    return league


def test_competition_and_recruiting_share_actual_players_and_ratings():
    league = miniature_league()
    pipeline = pipeline_from_league(league,12,["A","B"],{"A":40,"B":60})
    assert len(verify_pipeline(league,pipeline)) == 48
    index = competition_index(league)
    for rows in pipeline.classes.values():
        for prospect in rows:
            r = prospect.recruit
            team, p = index[r.recruit_id]
            assert r.true_overall == p.overall
            card = r.to_player_card("A")
            assert card.player_id == p.player_id
            assert card.overall == p.overall
            assert card.high_school == team.name


def test_actual_graduates_and_returning_prospects_are_not_regenerated(monkeypatch):
    league = miniature_league()
    pipeline = pipeline_from_league(league,12,["A","B"])
    old = competition_index(league)
    grads = {p.recruit.recruit_id:asdict(p.recruit) for p in pipeline.classes["12th"]}
    tracked_returning = verify_pipeline(league,pipeline)-set(grads)
    dynasty = SimpleNamespace(current_year=2027, retired_programs=[],
        team_histories={"A":None,"B":None}, team_prestige={"A":40,"B":60},
        _hs_league=league,_hs_pipeline=pipeline)
    # Avoid a postseason engine run in this small lifecycle unit test.
    monkeypatch.setattr("engine.college_feeder._isolated_sim",lambda l:l)
    result = advance_college_feeder(dynasty,2027,["A","B"],12)
    assert {r.recruit_id:asdict(r) for r in result} == grads
    new = competition_index(dynasty._hs_league)
    assert not (set(grads)&set(new))
    assert set(old)-set(new) == {pid for pid,(_,p) in old.items() if p.year=="Senior"}
    assert tracked_returning <= verify_pipeline(dynasty._hs_league,dynasty._hs_pipeline)
    assert all(old[pid][1] is not new[pid][1] for pid in set(old)&set(new))


def test_school_names_in_different_states_do_not_alias(monkeypatch):
    league = miniature_league()
    # The fast model exercises actual scheduling and bookkeeping; full
    # title-game path is covered by existing high-school page integration.
    from engine import hs_league
    monkeypatch.setattr(hs_league,"HS_ENGINE_ROUNDS",set())
    simulate_hs_season(league,random.Random(7))
    for g in league.schedule:
        assert g.home_key in league.teams and g.away_key in league.teams
        assert g.home_key != g.away_key
        assert g.winner_key in (g.home_key,g.away_key)
    for state,key in league.state_champion_keys.items():
        assert league.teams[key].state == state
    assert sum(t.wins for t in league.teams.values()) == len(league.schedule)
    assert sum(t.losses for t in league.teams.values()) == len(league.schedule)


def test_competition_and_pipeline_roundtrip():
    league = miniature_league()
    pipeline = pipeline_from_league(league,12,["A","B"])
    from engine.recruiting import HSRecruitingPipeline
    restored = HSLeague.from_save_state(json.loads(json.dumps(league.save_state())))
    restored_pipeline = HSRecruitingPipeline.from_save_state(json.loads(json.dumps(pipeline.save_state())))
    assert restored.save_state() == league.save_state()
    assert verify_pipeline(restored,restored_pipeline) == verify_pipeline(league,pipeline)


def test_fresh_college_id_collision_repair_never_rewrites_saved_players():
    teams = {name:SimpleNamespace(players=[SimpleNamespace(player_id="same")])
             for name in ("A","B","C")}
    assign_opening_roster_ids(teams,{"C":[{"player_id":"same"}]},2026)
    ids = [t.players[0].player_id for t in teams.values()]
    assert len(set(ids)) == 3
    assert teams["C"].players[0].player_id == "same"
    assert all(pid.startswith("CVL-OPEN-2026-") for pid in ids[:2])
