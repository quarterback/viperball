import random
from types import SimpleNamespace

from engine.delta_playbook import ALL, OFFENSE, PK, PP, PKO, POSTURES, RUN, KICK
from engine.delta_playbook import possession_context, weight, retained_miss, finish_shift
from engine.playbook_catalog import get_package
from engine.team_installation import active_situations, choose_offensive_package
from engine.defensive_commitments import eligibility


def ctx(**kw):
    return dict({"delta_bucket":"power_play", "field_position":65, "down":4,
                 "yards_to_go":12, "delta_drop_success":.75, "quarter":4,
                 "time_remaining":120, "score_diff":-4, "recent_kick_rate":.4,
                 "recent_perimeter_rate":.3, "recent_lateral_rate":.3}, **kw)


def test_all_twenty_catalogued():
    assert len(ALL) == 20 and len(OFFENSE) == 12 and len(PK) == 8
    assert set(POSTURES) == set(RUN) == set(KICK) == PK
    for pid in ALL:
        p = get_package(pid)
        assert p["side"] == ("defense" if pid in PK else "offense")
        assert weight(pid, ctx(delta_bucket="neutral")) == 0


def test_possession_latch():
    p = possession_context("score_restart", -15, 35)
    assert p["delta_bucket"] == "power_play"
    assert possession_context(None, 0, 70, p) == p
    assert possession_context("turnover", -15, 35, p)["delta_bucket"] == "neutral"
    assert possession_context("bonus_possession", -15, 20, p)["delta_bucket"] == "neutral"
    assert possession_context("score_restart", 19, 1, p)["delta_bucket"] == "penalty_kill"


def test_every_module_has_callable_state():
    special = {
        "pp_advantage_entry": ctx(field_position=30, down=1),
        "pp_compression": ctx(field_position=90),
        "pp_second_shot": ctx(delta_retained_miss=True),
        "pko_escape": ctx(delta_bucket="penalty_kill",field_position=5, down=1,score_diff=15),
        "pko_secure_twenty": ctx(delta_bucket="penalty_kill",field_position=15,score_diff=5),
        "pko_territory_exit": ctx(delta_bucket="penalty_kill",down=6,score_diff=5),
        "pko_counterpunch": ctx(delta_bucket="penalty_kill",field_position=5,delta_defense_school="blitz_pack"),
        "pk_compact_box": ctx(field_position=80),
        "pk_range_denial": ctx(field_position=40,delta_drop_success=.2),
        "pk_goal_line_wall": ctx(field_position=97),
        "pk_late_down_surge": ctx(down=6),
    }
    for pid in ALL:
        c = special.get(pid, ctx())
        assert weight(pid,c) > 0, pid
        p = dict(get_package(pid),familiarity=1)
        live = active_situations(c)
        if pid in OFFENSE:
            picked, eligible, _ = choose_offensive_package({"packages":[p],"authority":1},c,random.Random(1))
            assert pid in eligible and picked["package_id"] == pid
        else:
            assert eligibility(pid,live,c,p["situation_tags"]) > 0


def test_second_shot_and_finish():
    p = SimpleNamespace(play_type="drop_kick",result="missed_kick",penalty=None)
    assert retained_miss(p,"home","home",6,5)
    assert not retained_miss(p,"home","away",1,5)
    assert not retained_miss(p,"home","home",1,6)
    assert weight("pp_second_shot",ctx()) == 0
    assert finish_shift("pp_five_nine",1,1,ctx(),"kicking_zb") == 2
    assert finish_shift("pp_five_nine",1,1,ctx(),"running_zb") == 0
    assert finish_shift("pp_five_nine",1,1,ctx(delta_bucket="neutral"),"kicking_zb") == 0


def test_defensive_score_and_scout_response():
    assert weight("pk_kicker_diamond",ctx(score_diff=4)) > weight("pk_kicker_diamond",ctx(score_diff=12))
    assert weight("pk_side_lock",ctx(recent_lateral_rate=0,recent_perimeter_rate=0)) == 0
    assert weight("pk_takeaway_trap",ctx(recent_kick_rate=0,recent_lateral_rate=0)) == 0
    assert RUN["pk_kicker_diamond"]["power"] > 0
    assert RUN["pk_goal_line_wall"]["power"] < 0
