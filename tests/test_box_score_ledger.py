"""BOX-01 critical invariants: score ownership, bonus counts and player-credit parity."""
import pytest

from engine.box_score_ledger import scoring_ledger
from engine.viperball_metrics import calculate_scoring_profile, calculate_to_margin


def game_plays(*events):
    home = away = 0.0
    plays = []
    for result, typ, snap, scorer, points in events:
        if scorer == "home":
            home += points
        else:
            away += points
        plays.append({
            "result": result, "play_type": typ,
            "possession": snap, "snap_possession": snap,
            "home_score": home, "away_score": away,
        })
    return plays


def test_return_td_and_bell_are_credited_to_defender_only_once():
    plays = game_plays(
        ("touchdown", "run", "home", "home", 9),
        ("int_return_td", "kick_pass", "home", "away", 9),
        ("fumble", "run", "home", "away", 0.5),
        ("successful_kick", "drop_kick", "away", "away", 5),
    )
    ledger = scoring_ledger(plays, {"home": 9, "away": 14.5})
    assert ledger["home"]["counts"]["rush_td"] == 1
    assert ledger["away"]["counts"]["return_td"] == 1
    assert ledger["away"]["points"]["bell"] == 0.5
    assert ledger["away"]["score_from_plays"] == 14.5
    assert ledger["away"]["score_consistent"]
    assert calculate_to_margin(plays, "home") == -2


def test_combined_defensive_return_and_recovery_bell():
    plays = game_plays(("blocked_kick", "drop_kick", "home", "away", 9.5))
    ledger = scoring_ledger(plays, {"home": 0, "away": 9.5})
    assert ledger["away"]["counts"]["return_td"] == 1
    assert ledger["away"]["counts"]["bell"] == 1
    assert ledger["away"]["points"]["return_td"] + ledger["away"]["points"]["bell"] == 9.5


def test_bonus_drive_is_an_annotation_not_a_new_score():
    plays = game_plays(("successful_kick", "drop_kick", "home", "home", 5))
    drives = [{"team": "home", "bonus_drive": True, "result": "successful_kick"}]
    profile = calculate_scoring_profile(
        plays, drives, "home", {"official_score": 5, "bonus_possession_scores": 1})
    assert profile["total_pts"] == 5
    assert profile["dk_pts"] == 5
    assert profile["bonus_scores"] == 1
    assert profile["bonus_pts"] == 0
    assert profile["dk_pct"] == 100


def test_safety_pindown_and_half_point_sum_to_final():
    plays = game_plays(
        ("safety", "run", "home", "away", 2),
        ("pindown", "punt", "away", "away", 1),
        ("fumble", "lateral_chain", "home", "away", 0.5),
    )
    profile = calculate_scoring_profile(plays, [], "away", {"official_score": 3.5})
    assert profile["safeties"] == profile["pindowns"] == profile["bells"] == 1
    assert profile["score_consistent"]
    assert profile["total_pts"] == 3.5


def test_unlogged_score_is_exposed_not_covered_with_estimated_bonus():
    plays = game_plays(("touchdown", "run", "home", "home", 9))
    profile = calculate_scoring_profile(plays, [], "home", {"official_score": 14})
    assert not profile["score_consistent"]
    assert profile["unrecorded_pts"] == 5
    assert profile["rush_tds"] == 1
    assert profile["total_pts"] == 14


def test_legacy_profile_does_not_double_count_bonus():
    plays = [{"possession": "home", "play_type": "drop_kick", "result": "successful_kick"}]
    profile = calculate_scoring_profile(
        plays, [{"team": "home", "bonus_drive": True, "result": "successful_kick"}], "home")
    assert profile["total_pts"] == 5
    assert profile["bonus_scores"] == 1
    assert profile["bonus_pts"] == 0


def test_turnover_margin_counts_lateral_and_kick_interceptions_once():
    plays = [
        {"possession": "home", "snap_possession": "away", "result": "int_return_td"},
        {"possession": "away", "snap_possession": "away", "result": "lateral_intercepted"},
        {"possession": "home", "snap_possession": "home", "result": "kick_pass_intercepted"},
        {"possession": "home", "snap_possession": "home", "result": "safety"},
    ]
    assert calculate_to_margin(plays, "home") == 1
    assert calculate_to_margin(plays, "away") == -1
