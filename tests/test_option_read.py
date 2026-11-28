"""Option calls are read live: the Zeroback sees which runner the read
defender takes and the branch decides who carries (casebook case 7)."""
import random

from engine.game_engine import PlayFamily, ViperballEngine, load_team_from_json
import glob


def _engine(seed=3):
    files = sorted(glob.glob("data/teams/*.json"))[:2]
    return ViperballEngine(load_team_from_json(files[0]), load_team_from_json(files[1]), seed=seed)


def test_full_game_records_option_reads():
    eng = _engine()
    result = eng.simulate_game()
    reads = [p["option_read"] for p in result["play_by_play"] if p.get("option_read")]
    for r in reads:
        assert r["branch"] in ("give", "keep", "pitch")
        assert r["defender_took"] in ("zeroback", "runner")
        assert isinstance(r["correct"], bool)
        if r["branch"] == "keep":
            assert r["carrier"] == r["zeroback"]


def test_branch_follows_the_read():
    eng = _engine()
    eng.simulate_game()  # sets up rosters and live state
    random.seed(0)
    seen = set()
    for _ in range(400):
        team = eng.get_offensive_team()
        pool = eng._offense_skill(team)
        info = eng._resolve_option_read(PlayFamily.DIVE_OPTION, pool, pool, [1.0] * len(pool))
        if not info:
            continue
        right = "give" if info["defender_took"] == "zeroback" else "keep"
        assert (info["branch"] == right) == info["correct"]
        seen.add(info["branch"])
    assert seen <= {"give", "keep"}
