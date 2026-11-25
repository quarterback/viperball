from pathlib import Path
from types import SimpleNamespace
from engine.game_engine import ViperballEngine, load_team_from_json, player_label

def engine():
    paths=sorted((Path(__file__).resolve().parents[1]/"data"/"teams").glob("*.json"))
    return ViperballEngine(load_team_from_json(str(paths[0])),load_team_from_json(str(paths[1])),
                           seed=20261125,neutral_site=True,weather="clear")

def test_coach_rotation_preference_is_bounded():
    e=engine()
    e._home_coaching_staff={"head_coach":SimpleNamespace(rotations=95),"oc":SimpleNamespace(rotations=95)}
    assert e._rotation_preference(e.home_team,"offense")==1
    e._home_coaching_staff={"head_coach":SimpleNamespace(rotations=25),"oc":SimpleNamespace(rotations=25)}
    assert e._rotation_preference(e.home_team,"offense")==-1

def test_full_game_snap_and_rush_ledgers():
    e=engine()
    result=e.simulate_game()
    counts={"home":{"offense":0,"defense":0},"away":{"offense":0,"defense":0}}
    for p in result["play_by_play"]:
        snap=p.get("snap_lineup")
        if not snap:
            continue
        side=snap["offense_side"]
        other="away" if side=="home" else "home"
        for k,owner in (("offense",side),("defense",other)):
            assert 0 < len(snap[k]) <= 11
            assert len(snap[k])==len(set(snap[k]))
            counts[owner][k]+=len(snap[k])
        rush=p.get("rush_event")
        if rush:
            assert set(rush["defenders_on_field"]) == set(snap["defense"])
            assert not set(rush["rushers"]) & set(rush["coverage_players"])
    for side in ("home","away"):
        rows=result["game_day"]["energy"][side]
        assert counts[side]["offense"]==sum(p["offensive_snaps"] for p in rows)
        assert counts[side]["defense"]==sum(p["defensive_snaps"] for p in rows)
        assert all(p["snaps"]==p["offensive_snaps"]+p["defensive_snaps"] for p in rows)

def test_defensive_pool_uses_current_xi_and_legacy_override():
    e=engine()
    team=e.away_team
    unavailable=e._unavailable_in_game(team)
    on=e._on_field(team,unavailable,"defense")
    assert {player_label(p) for p in e._get_defenders_by_group(team)["all"]}=={player_label(p) for p in on}
    assert len(on)==11
