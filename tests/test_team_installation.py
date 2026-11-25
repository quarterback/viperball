"""CCH-04: team installation and career progression."""

import json
import os
import sys
from copy import deepcopy

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine import team_installation as ti  # noqa: E402
from engine.coaching import CoachCard  # noqa: E402
from engine.coach_tactics import OFFENSIVE_ARCHETYPES  # noqa: E402

STATS = {"avg_speed": 86, "avg_stamina": 86, "avg_weight": 186, "kicking_strength": 83,
         "lateral_proficiency": 86, "defensive_strength": 81}


def card(cid, role, tree=(), archetype=None):
    c = CoachCard(coach_id=cid, first_name="T", last_name=cid, age=45, gender="female",
                  role=role, classification="scheme_master", instincts=70, leadership=70,
                  composure=70, rotations=65, development=65, recruiting=65,
                  personality_sliders={"aggression": 60, "risk_tolerance": 60, "chaos_appetite": 50,
                                       "tempo_preference": 55, "stubbornness": 40, "player_trust": 60,
                                       "adaptability": 60})
    c.coaching_tree = [{"coach_id": t, "coach_name": t, "team_name": "X",
                        "year_start": 2020, "year_end": 2024} for t in tree]
    if archetype:
        from engine.coach_tactics import ensure_coach_tactical_profile
        p = ensure_coach_tactical_profile(c)
        tpl = OFFENSIVE_ARCHETYPES[archetype]
        p["identity"]["offense_interpretation"] = archetype
        p["offense"].update({k: dict(tpl[k]) for k in ("formation_bias", "family_bias", "kick_pass_bias")})
    return c


def staff(oc, hc=None, dc=None):
    return {"head_coach": hc or card("hc-1", "head_coach"), "oc": oc, "dc": dc or card("dc-1", "dc")}


def fresh(oc, **kw):
    recs = {}
    s = staff(oc, **kw)
    rec = ti.sync_installation(recs, "Team", s, "boot_raid", "lockdown", STATS, 2026)
    return recs, rec, s


def test_new_record_is_established_and_installs_fitting_packages():
    recs, rec, _ = fresh(card("oc-a", "oc", archetype="vertical_attack"))
    off = rec["offense"]
    assert off["familiarity"] == ti.ESTABLISHED_FAMILIARITY
    assert 1 <= len(off["packages"]) <= ti.PACKAGES_PER_COORDINATOR
    from engine import playbook_catalog as pc
    fit = {r["package_id"] for r in pc.packages_for_roster("offense", "boot_raid", STATS) if r["meets_personnel"]}
    assert all(p["package_id"] in fit for p in off["packages"])
    assert rec["defense"]["packages"]
    # Installed packages must have a supported trigger, including live events.
    live = ti.evaluable_situations()
    for side in ("offense", "defense"):
        for p in rec[side]["packages"]:
            assert set(pc.get_package(p["package_id"])["situation_tags"]) & live
    assert {"first_play_of_drive", "short_yardage", "after_takeaway",
            "after_score_restart", "tired_defense"} <= live


def test_sync_is_a_no_op_when_nothing_changed():
    recs, rec, s = fresh(card("oc-a", "oc", archetype="vertical_attack"))
    before = deepcopy(rec)
    ti.sync_installation(recs, "Team", s, "boot_raid", "lockdown", STATS, 2026)
    assert rec == before


def test_new_coordinator_starts_low_and_leaves_a_fading_trace():
    recs, rec, s = fresh(card("oc-a", "oc", archetype="run_to_kick"))
    s["oc"] = card("oc-b", "oc", archetype="vertical_attack")
    ti.sync_installation(recs, "Team", s, "boot_raid", "lockdown", STATS, 2027)
    off = rec["offense"]
    assert off["coach_id"] == "oc-b"
    assert off["familiarity"] == ti.NEW_COACH_FAMILIARITY
    assert off["vestigial"][0]["coach_id"] == "oc-a"
    assert off["vestigial"][0]["weight"] == round(ti.ESTABLISHED_FAMILIARITY * ti.VESTIGE_SHARE, 3)
    assert any(h["event"] == "offense_coordinator_change" for h in rec["history"])


def test_coaching_tree_and_signature_carry_over():
    recs, rec, s = fresh(card("oc-a", "oc", archetype="vertical_attack"))
    s["oc"] = card("oc-b", "oc", tree=["hc-1"], archetype="vertical_attack")
    ti.sync_installation(recs, "Team", s, "boot_raid", "lockdown", STATS, 2027)
    expect = min(ti.CARRYOVER_CAP, ti.NEW_COACH_FAMILIARITY + ti.LINEAGE_BONUS + ti.SAME_SIGNATURE_BONUS)
    assert rec["offense"]["familiarity"] == round(expect, 3)


def test_promotion_from_the_staff_keeps_most_familiarity():
    dc = card("dc-1", "dc")
    recs, rec, s = fresh(card("oc-a", "oc", archetype="vertical_attack"), dc=dc)
    promoted = card("dc-1", "oc", archetype="balanced")   # same coach, new role
    s["oc"] = promoted
    s["dc"] = card("dc-2", "dc")
    ti.sync_installation(recs, "Team", s, "boot_raid", "lockdown", STATS, 2027)
    assert rec["offense"]["familiarity"] >= ti.PROMOTION_FLOOR


def test_growth_and_decay_over_games_and_offseasons():
    recs, rec, s = fresh(card("oc-a", "oc", archetype="run_to_kick"))
    s["oc"] = card("oc-b", "oc", archetype="vertical_attack")
    ti.sync_installation(recs, "Team", s, "boot_raid", "lockdown", STATS, 2027)
    v0 = rec["offense"]["vestigial"][0]["weight"]
    for _ in range(10):
        ti.record_game(rec)
    assert rec["offense"]["familiarity"] == pytest.approx(ti.NEW_COACH_FAMILIARITY + 10 * ti.GAME_GROWTH, abs=1e-3)
    assert rec["offense"]["vestigial"][0]["weight"] < v0
    ti.advance_offseason(rec, 2028)
    assert rec["offense"]["seasons_together"] == 1
    for _ in range(3):
        ti.advance_offseason(rec)
    assert rec["offense"]["vestigial"] == []      # faded out
    assert rec["offense"]["familiarity"] == 1.0


def test_family_change_resets_book_familiarity_and_rechecks_packages():
    recs, rec, s = fresh(card("oc-a", "oc", archetype="run_to_kick"))
    ti.sync_installation(recs, "Team", s, "chain_gang", "lockdown", STATS, 2027)
    off = rec["offense"]
    assert off["family"] == "chain_gang" and off["family_familiarity"] == ti.NEW_FAMILY_FAMILIARITY
    from engine import playbook_catalog as pc
    ok = {p["package_id"] for p in pc.list_compatible_packages("offense", "chain_gang")}
    assert all(p["package_id"] in ok for p in off["packages"])


def _tactics(archetype="vertical_attack", coach_id="oc-a"):
    tpl = OFFENSIVE_ARCHETYPES[archetype]
    return {"coach_id": coach_id, "signature": archetype, "featured_position": tpl["featured_position"],
            "authority": 0.8, **{k: dict(tpl[k]) for k in ("formation_bias", "family_bias", "kick_pass_bias")}}


def test_familiarity_scales_the_signature_and_vestiges_add_back():
    recs, rec, s = fresh(card("oc-a", "oc", archetype="vertical_attack"))
    rec["offense"]["familiarity"] = 0.5
    rec["offense"]["family_familiarity"] = 1.0
    rec["offense"]["vestigial"] = [{"coach_id": "old", "signature": "run_to_kick", "weight": 0.4,
                                    "bias": {k: dict(OFFENSIVE_ARCHETYPES["run_to_kick"][k])
                                             for k in ("formation_bias", "family_bias", "kick_pass_bias")}}]
    t = ti.apply_installation_to_offense(_tactics(), rec)
    spread = 0.5 * OFFENSIVE_ARCHETYPES["vertical_attack"]["formation_bias"]["spread"] \
        + 0.4 * OFFENSIVE_ARCHETYPES["run_to_kick"]["formation_bias"]["spread"]
    assert t["formation_bias"]["spread"] == pytest.approx(spread, abs=1e-4)
    assert t["installation"]["execution_factor"] == 0.5


def test_full_installation_and_no_record_leave_tactics_unchanged():
    base = _tactics()
    assert ti.apply_installation_to_offense(base, None) is base
    recs, rec, _ = fresh(card("oc-a", "oc", archetype="vertical_attack"))
    rec["offense"].update(familiarity=1.0, family_familiarity=1.0, vestigial=[], packages=[])
    t = ti.apply_installation_to_offense(base, rec)
    for k in ("formation_bias", "family_bias", "kick_pass_bias"):
        assert t[k] == pytest.approx(base[k])
    stale = ti.apply_installation_to_offense(_tactics(coach_id="someone-else"), rec)
    assert "installation" not in stale


def test_packages_pull_only_in_their_situations():
    recs, rec, _ = fresh(card("oc-a", "oc", archetype="vertical_attack"))
    rec["offense"]["packages"] = [{"package_id": "gp_heavy_push", "familiarity": 1.0}]
    t = ti.apply_installation_to_offense(_tactics(), rec)
    usage = {}
    short = {"down": 3, "yards_to_go": 2, "field_position": 40, "quarter": 2, "time_remaining": 500, "score_diff": 0}
    long_ = dict(short, yards_to_go=15)
    on = ti.situational_bias(t, "family_bias", short, usage)
    off = ti.situational_bias(t, "family_bias", long_, usage)
    assert on["power"] == pytest.approx(off["power"] + ti.PACKAGE_PULL, abs=1e-6)
    assert usage["packages"] == {"gp_heavy_push": 1}


def test_situations_follow_the_catalog_rules():
    ctx = {"down": 5, "yards_to_go": 3, "field_position": 90, "quarter": 4, "time_remaining": 100, "score_diff": 4}
    live = ti.active_situations(ctx)
    assert {"short_yardage", "goal_line", "late_downs", "kick_range", "protect_lead", "two_minute"} <= live
    assert "chasing" not in live
    # Viperball needs 20 yards in six downs: 1st and 20 is normal, 3rd and 20 is long.
    assert "long_yardage" not in ti.active_situations(dict(ctx, down=1, yards_to_go=20))
    assert "long_yardage" in ti.active_situations(dict(ctx, down=3, yards_to_go=20))
    assert "early_down" in ti.active_situations(dict(ctx, down=1, yards_to_go=20))
    # Rules the engine cannot evaluate yet are never live.
    assert not live & {"tired_defense", "first_play_of_drive", "after_takeaway", "after_score_restart"}


def test_league_profiles_rank_against_the_team_files():
    import importlib.util
    root = os.path.join(os.path.dirname(__file__), "..")
    spec = importlib.util.spec_from_file_location("bm", os.path.join(root, "scripts", "benchmark_engine.py"))
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    teams, _, _ = bm.build_matchups(1, 2026)
    prof = ti.league_roster_profiles(teams)
    from engine import playbook_catalog as pc
    share = sum("team_speed" in pc.roster_tags(p) for p in prof.values()) / len(prof)
    assert 0.35 < share < 0.65


def test_old_records_migrate_and_bad_ones_are_rejected():
    rec = ti.ensure_installation({"team": "T", "offense": {"coach_id": "x"}}, "T")
    assert rec["offense"]["vestigial"] == [] and rec["defense"]["packages"] == []
    with pytest.raises(ValueError):
        ti.ensure_installation({"version": 99}, "T")
    with pytest.raises(ValueError):
        ti.ensure_installation(["not", "a", "record"], "T")
    assert ti.ensure_installation(None) is None


def test_defense_factor_for_cch03():
    assert ti.defense_execution_factor(None) == 1.0
    recs, rec, _ = fresh(card("oc-a", "oc"))
    rec["defense"]["familiarity"] = 0.5
    rec["defense"]["family_familiarity"] = 0.0
    assert ti.defense_execution_factor(rec) == 0.35


def test_dynasty_save_round_trip(tmp_path):
    from engine.dynasty import Dynasty, create_dynasty
    d = create_dynasty("Test Dynasty", "Coach", "Gonzaga", 2026)
    recs, rec, _ = fresh(card("oc-a", "oc", archetype="vertical_attack"))
    d._team_installations = recs
    path = tmp_path / "d.json"
    d.save(str(path))
    loaded = Dynasty.load(str(path))
    assert loaded._team_installations["Team"]["offense"]["coach_id"] == "oc-a"
    data = json.loads(path.read_text())
    data.pop("team_installations")
    path.write_text(json.dumps(data))
    assert Dynasty.load(str(path))._team_installations == {}


def test_engine_full_installation_matches_no_record_and_packages_show_up():
    from engine.game_engine import ViperballEngine, load_team_from_json
    import random
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    paths = sorted((root / "data" / "teams").glob("*.json"))
    random.seed(7)
    off = load_team_from_json(str(paths[0]), fresh=False)
    de = load_team_from_json(str(paths[1]), fresh=False)
    oc = card("oc-a", "oc", archetype="vertical_attack")
    st = {"head_coach": card("hc-1", "head_coach"), "oc": oc}

    def run(installation):
        a, b = deepcopy(off), deepcopy(de)
        a.installation = installation
        r = ViperballEngine(a, b, seed=11, home_coaching=deepcopy(st),
                            style_overrides={a.name: "boot_raid", b.name: "balanced"},
                            weather="clear", neutral_site=True).simulate_game()
        return r

    plain = run(None)
    recs = {}
    rec = ti.sync_installation(recs, off.name, st, "boot_raid", "balanced", STATS, 2026)
    rec["offense"].update(familiarity=1.0, family_familiarity=1.0, vestigial=[], packages=[])
    full = run(deepcopy(rec))
    assert [p["description"] for p in full["play_by_play"]] == [p["description"] for p in plain["play_by_play"]]
    rec["offense"]["packages"] = [{"package_id": "gp_heavy_push", "familiarity": 1.0},
                                  {"package_id": "ec_quick_kick_chain", "familiarity": 1.0}]
    pk = run(deepcopy(rec))
    used = pk["coach_tactics"]["home"]["selected"].get("packages", {})
    assert used and set(used) <= {"gp_heavy_push", "ec_quick_kick_chain"}
    from collections import Counter
    calls = [p["offensive_call"] for p in pk["play_by_play"]
             if (p.get("offensive_call") or {}).get("offense_side") == "home"]
    assert calls
    assert Counter(c["package_id"] for c in calls if c.get("package_id")) == Counter(used)
    selected = pk["coach_tactics"]["home"]["selected"]
    assert Counter(pid for c in calls for pid in c["eligible"]) == Counter(selected["packages_eligible"])
    for call in calls:
        if call.get("package_id"):
            assert call["package_id"] in call["eligible"]
            assert call["family_matched"] == call["matches"].get("family", False)
    assert pk["coach_tactics"]["home"]["installation"]["execution_factor"] == 1.0
