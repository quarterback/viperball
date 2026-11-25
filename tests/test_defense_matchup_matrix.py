"""DEF-06 benchmark contract, attribution, coverage, and smoke tests."""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import pytest

from engine.game_engine import DEFENSE_STYLES, OFFENSE_STYLES
from scripts.defense_matchup_matrix import (
    FORMATIONS, ROOT, aggregate, choose_rosters, load_stable_fresh_rosters,
    main, observed_drive_points, paired_scheme_contrasts, parse_choices,
    sample_ci, selected_roster_fingerprint, stable_seed,
)




def test_fresh_roster_order_is_reproducible():
    # Production team-directory iteration currently uses unsorted glob().
    # DEF-06 must always choose the same actual rosters under one seed.
    random.seed(20261123)
    teams1 = load_stable_fresh_rosters(ROOT / "data" / "teams")
    attacker1, defenders1 = choose_rosters(teams1)
    random.seed(20261123)
    teams2 = load_stable_fresh_rosters(ROOT / "data" / "teams")
    attacker2, defenders2 = choose_rosters(teams2)
    assert attacker1.name == attacker2.name
    assert [defenders1[x].name for x in ("weak", "strong")] == [
        defenders2[x].name for x in ("weak", "strong")]
    assert [p.overall for p in attacker1.players] == [
        p.overall for p in attacker2.players]
    p1 = {"offense": attacker1.name, "weak": defenders1["weak"].name,
          "strong": defenders1["strong"].name}
    p2 = {"offense": attacker2.name, "weak": defenders2["weak"].name,
          "strong": defenders2["strong"].name}
    assert selected_roster_fingerprint(p1) == selected_roster_fingerprint(p2)


def test_stable_seed_ignores_defense_in_paired_context():
    assert stable_seed(20261123, "boot_raid", "spread", "weak", "home", "clear", 0) == (
        stable_seed(20261123, "boot_raid", "spread", "weak", "home", "clear", 0)
    )
    assert stable_seed(20261123, "boot_raid", "spread", "weak", "home", "clear", 0) != (
        stable_seed(20261123, "boot_raid", "spread", "strong", "home", "clear", 0)
    )


def test_all_160_matchups_and_40_formation_defense_cells_exist():
    from engine.game_engine import FORMATION_VS_DEFENSE, OFFENSE_VS_DEFENSE_MATCHUP
    assert len(OFFENSE_STYLES) == 16
    assert len(DEFENSE_STYLES) == 10  # DEF-12 added Keeper Hunt and Rotation
    assert set(OFFENSE_VS_DEFENSE_MATCHUP) == {
        (off, scheme) for off in OFFENSE_STYLES for scheme in DEFENSE_STYLES
    }
    assert set(FORMATION_VS_DEFENSE) == {
        (form, scheme) for form in FORMATIONS for scheme in DEFENSE_STYLES
    }


def test_drive_attribution_uses_scoreboard_differences_not_final_score():
    drives = [
        {"team": "home", "home_score_after": 9, "away_score_after": 0},
        {"team": "away", "home_score_after": 9, "away_score_after": 5},
        {"team": "home", "home_score_after": 9, "away_score_after": 14},
        {"team": "away", "home_score_after": 9.5, "away_score_after": 19},
    ]
    assert observed_drive_points(drives, "home") == [9.0, 0.0]
    assert observed_drive_points(drives, "away") == [5.0, 5.0]


def test_bootstrap_is_deterministic_and_reports_uncertainty():
    data = [1.0, 2.0, 4.0, 7.0, 8.0]
    ci = sample_ci(data, seed=39)
    assert ci == sample_ci(data, seed=39)
    assert ci[0] <= sum(data)/len(data) <= ci[1]
    assert sample_ci([1.0]) == (None, None)


def test_filters_reject_missing_unknown_and_duplicate_values():
    with pytest.raises(ValueError):
        parse_choices("", ("swarm",), "defenses")
    with pytest.raises(ValueError):
        parse_choices("swarm,swarm", ("swarm",), "defenses")
    with pytest.raises(ValueError):
        parse_choices("no-such-scheme", ("swarm",), "defenses")


def test_aggregates_keep_observations_distinct_and_weight_attempts():
    rows = []
    for defense, attempts, completions in [
        ("swarm", 10, 2), ("swarm", 1, 1),
        ("lockdown", 10, 1), ("lockdown", 1, 0),
    ]:
        rows.append({
            "offense": "boot_raid", "defense": defense, "formation": "spread",
            "defense_tier": "weak", "venue": "home", "weather": "clear",
            "rep": len(rows) // 2,
            "drives": 2, "attacking_drive_points": 5.0,
            "points_per_drive": 2.5, "offensive_points": 5.0,
            "run_plays": 4, "run_yards": 12, "kick_pass_attempts": attempts,
            "kick_pass_completions": completions, "sacks_allowed": 1,
            "explosive_30": 1, "turnovers": 0, "defensive_bells": 0,
            "stops": 1, "read_attempts": 1, "read_successes": 1,
            "punt_attempts": 0, "pindowns": 0, "defense_energy_end": 80.0,
        })
    summary = {(r["offense"], r["defense"]): r for r in aggregate(rows)}
    assert summary["boot_raid", "swarm"]["kick_pass_pct"] == pytest.approx(3/11, abs=.001)
    assert summary["boot_raid", "lockdown"]["kick_pass_pct"] == pytest.approx(1/11, abs=.001)
    contrasts = paired_scheme_contrasts(rows)
    assert any(r["defense"] == "lockdown" and r["metric"] == "points_per_drive"
               for r in contrasts)


def test_small_full_engine_smoke_generates_expected_files(tmp_path):
    out = tmp_path / "def06-smoke"
    main([
        "--offenses", "boot_raid", "--defenses", "swarm,lockdown",
        "--formations", "spread", "--tiers", "weak", "--venues", "home",
        "--weathers", "clear", "--reps", "1", "--seed", "20261123",
        "--out", str(out),
    ])
    metadata = json.loads((out / "metadata.json").read_text())
    assert metadata["games"] == 2
    assert metadata["defenses"] == ["swarm", "lockdown"]
    assert metadata["rosters"]["weak"]["defense"] < metadata["rosters"]["strong"]["defense"]
    with (out / "games.csv").open(newline="") as stream:
        games = list(csv.DictReader(stream))
    assert len(games) == 2
    assert {row["defense"] for row in games} == {"swarm", "lockdown"}
    assert all(float(row["read_attempts"]) > 0 for row in games)
    with (out / "matrix.csv").open(newline="") as stream:
        assert len(list(csv.DictReader(stream))) == 2
    assert (out / "family.csv").is_file()
    assert (out / "contrasts.csv").is_file()
    assert "boot_raid" in (out / "report.md").read_text()
