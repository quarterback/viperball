"""Cross code books and defensive answers (engine/cross_code.py)."""
import random
from copy import deepcopy
from types import SimpleNamespace

import pytest

from engine import cross_code as XC
from engine.defensive_commitments import eligibility
from engine.playbook_catalog import get_package, get_scheme_family


def player(**ratings):
    # Current rating scale: about 33 is an average player.
    base = dict(speed=33, agility=33, awareness=33, hands=33, tackling=40, game_energy=100)
    base.update(ratings)
    return SimpleNamespace(**base)


def test_every_call_is_in_the_catalog_with_the_clinic_schools():
    books = {
        "free_motion": {"ghost", "mismatch", "stampede", "slick_n_slide", "lateral_spread"},
        "phase_attack": {"ground_control", "slick_n_slide", "lateral_spread", "mousetrap", "six_shooter"},
        "relay": {"east_coast", "lateral_spread", "mismatch", "balanced"},
        "crossfire": {"ghost", "mousetrap", "mismatch", "east_coast"},
    }
    for pid in XC.OFFENSE:
        pkg = get_package(pid)
        assert pkg["side"] == "offense"
        assert set(pkg["compatible_families"]) == books[XC.BOOK[pid]]
    schools = {
        XC.D_EXCHANGE: {"lockdown", "chaos", "shadow"}, XC.D_STAGGER: {"drift", "lockdown"},
        XC.D_EDGE_ANCHOR: {"swarm", "fortress"}, XC.D_SLIDE_REPLACE: {"shadow", "rotation"},
        XC.D_CHANNEL_PRESS: {"blitz_pack", "keeper_hunt"}, XC.D_TRANSITION_NET: {"rotation", "drift"},
        XC.D_CROSS_RUSH: {"blitz_pack", "chaos"}, XC.D_SET_BREAKER: {"fortress", "swarm", "chaos"},
    }
    for pid, fams in schools.items():
        pkg = get_package(pid)
        assert pkg["side"] == "defense" and set(pkg["compatible_families"]) == fams
    assert "fm_switchback" in get_scheme_family("offense", "ghost")["packages"]
    assert "dx_set_breaker" in get_scheme_family("defense", "swarm")["packages"]


def test_every_branch_family_is_one_the_package_lists():
    looks = []
    for switched in (True, False):
        for ytg in (4, 18):
            looks.append({"exchange": {"switched": switched}, "ytg": ytg, "z_runs": True})
            looks.append({"exchange": {"switched": switched}, "ytg": ytg, "z_runs": False})
    for align in ("stacked", "aggressive", "balanced", "spread"):
        for blitz in (True, False):
            looks.append({"alignment": align, "blitz_seen": blitz, "commit": blitz,
                          "edge_to_z": blitz, "drawn": ["x"] if blitz else [],
                          "pressed": {"left": blitz, "right": not blitz},
                          "counts": {"left": 1, "right": 3, "box": 5 if blitz else 3},
                          "fair": {"left": 2, "right": 2}, "weak": "left", "short": "left",
                          "wide": "right", "at_hash": True, "has_viper": blitz, "ytg": 8,
                          "h_ready": True, "bad_snap": False,
                          "mismatch": {"attacker_position": "Viper", "defender": "D"} if blitz else None,
                          "memory": [{"branch": "look", "lane": "left", "pressed": True}] if blitz else []})
    for pid in XC.OFFENSE:
        tags = set(get_package(pid)["play_family_tags"])
        for look in looks:
            out = XC.design(pid, dict(look))
            assert out["branch"]
            if out.get("family"):
                assert out["family"] in tags, (pid, out)
            if out.get("kick_pass"):
                assert out["kick_pass"] in get_package(pid)["kick_pass_tags"], (pid, out)


def test_switchback_reads_the_switch():
    clean = XC.design(XC.FM_SWITCHBACK, {"exchange": {"switched": True}, "z_runs": True, "weak": "left"})
    assert clean["branch"] == "switched_keep" and clean["carrier"] == "Zeroback"
    missed = XC.design(XC.FM_SWITCHBACK, {"exchange": {"switched": False}, "ytg": 8, "weak": "left"})
    assert missed == {"branch": "vacated_pitch", "family": "speed_option", "lane": "left",
                      "carrier": "Slotback", "cross": True, "book": "free_motion"}


def test_practiced_exchange_switches_more_often():
    attackers = [player(agility=40, awareness=40), player(agility=40, awareness=40)]
    defenders = [player(), player()]
    rng = random.Random(3)
    raw = sum(XC.exchange(attackers, defenders, 0.0, rng)["switched"] for _ in range(2000))
    drilled = sum(XC.exchange(attackers, defenders, 1.0, rng)["switched"] for _ in range(2000))
    assert drilled > raw + 400
    miss = next(r for r in (XC.exchange(attackers, defenders, 0.0, rng) for _ in range(50)) if not r["switched"])
    assert miss["trailing"] is defenders[0]


def test_remembering_calls_flip_after_a_loaded_side():
    first = XC.design(XC.FM_MIRROR_FLOOD, {"wide": "right", "pressed": {}, "memory": []})
    assert first["branch"] == "flood" and first["lane"] == "right"
    again = XC.design(XC.FM_MIRROR_FLOOD, {"wide": "right", "pressed": {},
                                           "memory": [{"lane": "right", "pressed": True}]})
    assert again["lane"] == "left"
    look = XC.design(XC.CF_SAME_LOOK_REVERSE, {"wide": "right", "memory": []})
    assert look["branch"] == "look"
    rev = XC.design(XC.CF_SAME_LOOK_REVERSE, {"memory": [{"branch": "look", "lane": "right"}]})
    assert rev == {"branch": "reverse", "family": "counter", "lane": "left",
                   "look_id": "pivot_look", "book": "crossfire"}


def test_calls_without_their_look_hand_the_snap_back():
    assert "family" not in XC.design(XC.PH_SHORT_SIDE, {"at_hash": False})
    assert "family" not in XC.design(XC.CF_HANDOFF_PUNISH, {"mismatch": None})
    assert "family" not in XC.design(XC.RL_SAFE_OUTLET, {"alignment": "balanced", "blitz_seen": False})
    assert "family" not in XC.design(XC.FM_TWIN_TRIGGER, {"h_ready": False})


def test_set_breaker_predicts_from_what_the_offense_has_run():
    assert XC.predict_next({"power": {"draw": 2}}, "power") == (None, 0.0, 2)
    fam, conf, n = XC.predict_next({"power": {"draw": 3, "power": 1}}, "power")
    assert (fam, conf, n) == ("draw", 0.75, 4)
    run, kick = XC.set_breaker_deltas("draw")
    assert run["draw"] < 0 < run["power"]
    assert XC.set_breaker_alignment("draw") == "stacked"


def test_defensive_triggers():
    quiet = {"recent_cross_rate": 0.0, "down": 1}
    busy = {"recent_cross_rate": 0.2, "down": 1}
    assert eligibility("dx_exchange", ["early_down"], quiet, []) == 0.0
    assert eligibility("dx_exchange", ["early_down"], busy, []) == 1.0
    assert eligibility("dx_transition_net", ["after_takeaway"], busy, []) == 0.0
    late = {"down": 4, "set_breaker_confidence": 0.6}
    assert eligibility("dx_set_breaker", ["late_downs"], late, []) == 1.0
    assert eligibility("dx_set_breaker", ["late_downs"], {"down": 1, "set_breaker_confidence": 0.4}, []) == .45


def test_move_defender_changes_what_each_side_is_worth():
    channels = {"by_id": {1: "box", 2: "left"}, "counts": {"left": 1, "box": 1, "right": 0},
                "fair": {"left": 1.0, "right": 1.0}, "value": {"left": 0.0, "right": 0.12}}
    XC.move_defender(channels, 1, "right", {"left": 0.0, "right": 0.0})
    assert channels["counts"] == {"left": 1, "box": 0, "right": 1}
    assert channels["value"]["right"] == 0.0


def _game(package, side, style, defense, seed=7, offense_package=None):
    from engine.game_engine import ViperballEngine, load_team_from_json
    from engine.team_installation import new_installation
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from benchmark_defensive_coaches import coach, dc_variant
    home = load_team_from_json("data/teams/alabama.json", fresh=True)
    away = load_team_from_json("data/teams/duke.json", fresh=True)
    staff = {"head_coach": coach("t-hc", "head_coach"), "oc": coach("t-oc", "oc")}
    opp = {"head_coach": coach("t-away-hc", "head_coach"), "dc": dc_variant("selective_pressure")}
    rec = new_installation(home.name, staff, style, "swarm", 2026)
    rec["offense"].update(familiarity=1.0, family_familiarity=1.0,
                          packages=[{"package_id": package if side == "offense" else offense_package,
                                     "familiarity": 1.0}] if side == "offense" or offense_package else [])
    home.installation = rec
    arec = new_installation(away.name, opp, "ghost", defense, 2026)
    arec["defense"].update(familiarity=1.0, family_familiarity=1.0,
                           packages=[{"package_id": package, "familiarity": 1.0}] if side == "defense" else [])
    away.installation = arec
    random.seed(seed)
    return ViperballEngine(home, away, seed=seed, neutral_site=True, weather="clear",
                           home_coaching=deepcopy(staff), away_coaching=deepcopy(opp),
                           style_overrides={home.name: style, away.name + "_defense": defense}).simulate_game()


@pytest.mark.parametrize("pid,style", [(XC.FM_SWITCHBACK, "ghost"), (XC.RL_WALL_RETURN, "east_coast"),
                                       (XC.RL_UP_BACK_ACROSS, "east_coast")])
def test_calls_run_in_a_full_game(pid, style):
    game = _game(pid, "offense", style, "rotation")
    branches = game["cross_code"]["home"]["offense"].get(pid, {})
    assert sum(branches.values()) > 5
    for play in game["play_by_play"]:
        call = play.get("offensive_call") or {}
        if call.get("package_id") != pid or not (call.get("design") or {}).get("family"):
            continue
        # The play that ran is the one the read designed, unless a foul or a
        # forced kick took the snap.
        if play["play_type"] in ("run", "kick_pass", "lateral_chain") and not play.get("penalty"):
            assert play["play_family"] == call["design"]["family"], (pid, call["cross"], play["play_family"])


def test_defensive_answers_act_in_a_full_game():
    # Against the call each answers, over a few games: a single game can
    # pass without the trigger the answer waits for.
    moved = acted = 0
    for seed in (7, 8, 9):
        anchor = _game(XC.D_EDGE_ANCHOR, "defense", "lateral_spread", "swarm", seed, "cape_cod_hook")
        moved += anchor["cross_code"]["away"]["defense"].get(XC.D_EDGE_ANCHOR, {}).get("moved_anchor", 0)
        rush = _game(XC.D_CROSS_RUSH, "defense", "east_coast", "blitz_pack", seed)
        done = rush["cross_code"]["away"]["defense"].get(XC.D_CROSS_RUSH, {})
        acted += done.get("passed_off", 0) + done.get("came_free", 0)
    assert moved > 0 and acted > 0


def test_every_cross_code_call_has_its_own_preview():
    from pathlib import Path
    js = Path("stats_site/static/playbook_cookbook.js").read_text()
    for pid in XC.OFFENSE | XC.DEFENSE:
        assert f"    {pid}: (" in js, pid
    # Calls with more than one branch let the viewer pick the branch.
    for pid in XC.OFFENSE - {XC.CF_HANDOFF_PUNISH}:
        assert f"    {pid}: [[" in js, pid
