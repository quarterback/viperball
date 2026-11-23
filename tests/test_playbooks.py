"""Coach playbooks: borrowed books, situational calls, and their effects."""

import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine import playbooks as pb  # noqa: E402
from engine.game_engine import (  # noqa: E402
    DEFENSE_PACKAGE_SITUATIONS,
    DEFENSE_STYLES,
    OFFENSE_STYLES,
    V2_ENGINE_CONFIG,
)


def test_borrowed_offense_takes_the_call_and_keeps_the_home_system():
    base, borrowed = OFFENSE_STYLES["east_coast"], OFFENSE_STYLES["ground_pound"]
    m = pb.merged_offense(base, borrowed)
    assert m["weights"] == borrowed["weights"]
    assert m["formation_weights"] == borrowed["formation_weights"]
    assert m["tempo"] == base["tempo"]
    assert m["fatigue_resistance"] == base["fatigue_resistance"]
    # East Coast's own situational modes do not leak into a Ground & Pound call.
    assert "weights_attack" not in m
    assert m["run_bonus"] == borrowed["run_bonus"] * pb.BORROWED_BONUS_SHARE


def test_borrowed_defense_plays_halfway_and_keeps_package_personnel():
    base, pkg = DEFENSE_STYLES["swarm"], DEFENSE_STYLES["fortress"]
    m = pb.merged_defense(base, pkg)
    assert m["personnel_weights"] == pkg["personnel_weights"]
    mid = base["read_success_rate"] + 0.5 * (pkg["read_success_rate"] - base["read_success_rate"])
    assert abs(m["read_success_rate"] - mid) < 1e-9
    dive = base["play_family_modifiers"]["dive_option"]
    dive += 0.5 * (pkg["play_family_modifiers"]["dive_option"] - dive)
    assert abs(m["play_family_modifiers"]["dive_option"] - dive) < 1e-9


def test_build_playbook_shares_follow_appetite():
    rng = random.Random(1)
    purist = pb.build_playbook("ground_pound", {}, 0.0, rng, OFFENSE_STYLES)
    magpie = pb.build_playbook("ground_pound", {}, 1.0, rng, OFFENSE_STYLES)
    assert len(purist) == 1 and len(magpie) == 3
    assert abs(sum(purist.values()) - 0.05) < 0.01
    assert abs(sum(magpie.values()) - 0.45) < 0.01
    for book in list(purist) + list(magpie):
        assert book not in ("ground_pound", "balanced")


def test_choose_call_favors_a_book_in_its_situation():
    random.seed(3)
    playbook = {"ground_pound": 0.15}
    flat = lambda b: 1.0
    short = sum(pb.choose_call("east_coast", playbook, {"short_yardage"}, pb.OFFENSE_BOOK_SITUATIONS, flat)
                == "ground_pound" for _ in range(4000))
    long_ = sum(pb.choose_call("east_coast", playbook, {"long_yardage"}, pb.OFFENSE_BOOK_SITUATIONS, flat)
                == "ground_pound" for _ in range(4000))
    assert short > 2.5 * long_
    assert pb.choose_call("east_coast", {}, {"short_yardage"}, pb.OFFENSE_BOOK_SITUATIONS, flat) == "east_coast"


def test_defense_situations_come_from_scheme_ratings():
    assert "short_yardage" in DEFENSE_PACKAGE_SITUATIONS["fortress"]
    assert "long_yardage" in DEFENSE_PACKAGE_SITUATIONS["drift"]
    assert "kick_range" in DEFENSE_PACKAGE_SITUATIONS["lockdown"]
    # Blitz Pack is rated weak in long yardage, so it is not called there.
    assert "long_yardage" not in DEFENSE_PACKAGE_SITUATIONS["blitz_pack"]
    assert DEFENSE_PACKAGE_SITUATIONS["shadow"] == ()


def _game(seed=11):
    import importlib.util
    root = os.path.join(os.path.dirname(__file__), "..")
    spec = importlib.util.spec_from_file_location("bm", os.path.join(root, "scripts", "benchmark_engine.py"))
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    from engine import ViperballEngine
    teams, styles, pairs = bm.build_matchups(2, seed)
    h, a = pairs[0]
    return ViperballEngine(teams[h], teams[a], seed=seed, style_overrides=bm.overrides(styles, h, a)).simulate_game()


def test_engine_tags_borrowed_calls_and_counts_them():
    r = _game()
    pbk = r["game_day"]["playbook"]
    borrowed = 0
    for side in ("home", "away"):
        calls = pbk[side]["offense_calls"]
        borrowed += sum(n for b, n in calls.items() if b != pbk[side]["offense_home"])
        for book in calls:
            assert book == pbk[side]["offense_home"] or book in pbk[side]["offense_playbook"]
    # A play's possession field is recorded after the play, so a borrowed
    # call that ends in a turnover lists the other team: compare totals.
    tagged = sum(1 for p in r["play_by_play"] if p.get("call_book"))
    assert borrowed == tagged and borrowed > 0


def test_playbooks_off_means_home_books_only():
    V2_ENGINE_CONFIG["playbooks_enabled"] = False
    try:
        r = _game()
    finally:
        V2_ENGINE_CONFIG["playbooks_enabled"] = True
    assert not any(p.get("call_book") or p.get("def_call") for p in r["play_by_play"])


def test_ai_assignment_repeats_for_a_seed():
    from engine.ai_coach import auto_assign_all_teams
    d = os.path.join(os.path.dirname(__file__), "..", "data", "teams")
    a = auto_assign_all_teams(d, seed=5)
    b = auto_assign_all_teams(d, seed=5)
    assert a == b
    assert all("offense_playbook" in cfg for cfg in a.values())
