"""Regression coverage for schedule integrity without simulating games."""
from collections import Counter
import random

import pytest

from engine.season import Season


def make_season(n, sizes):
    names = [f"School {i:03d}" for i in range(n)]
    conferences = {}
    offset = 0
    for i, size in enumerate(sizes):
        conferences[f"Conference {i}"] = names[offset:offset + size]
        offset += size
    return Season(
        name="Schedule regression",
        teams=dict.fromkeys(names),
        conferences=conferences,
        team_conferences={t: c for c, ts in conferences.items() for t in ts},
    )


def assert_integrity(season, quota):
    counts = Counter()
    pairs = set()
    slots = set()
    for game in season.schedule:
        pair = tuple(sorted((game.home_team, game.away_team)))
        assert pair[0] != pair[1]
        assert pair not in pairs
        pairs.add(pair)
        for team in pair:
            assert (game.week, team) not in slots
            slots.add((game.week, team))
            counts[team] += 1
    assert all(counts[t] <= quota for t in season.teams)
    return counts


@pytest.mark.parametrize("seed", range(12))
def test_reduced_dynasty_quota(seed):
    random.seed(seed)
    season = make_season(16, [8, 8])
    season.generate_schedule(games_per_team=12)
    counts = assert_integrity(season, 12)
    assert all(counts[t] == 12 for t in season.teams)


@pytest.mark.parametrize("seed", range(8))
def test_unconferenced_quota(seed):
    random.seed(seed)
    season = make_season(16, [])
    season.generate_schedule(games_per_team=12)
    counts = assert_integrity(season, 12)
    assert all(counts[t] == 12 for t in season.teams)


def test_pinned_game_preserved():
    random.seed(20261124)
    season = make_season(16, [8, 8])
    home, away = "School 000", "School 008"
    season.generate_schedule(games_per_team=12, pinned_matchups=[(home, away)])
    counts = assert_integrity(season, 12)
    assert all(counts[t] == 12 for t in season.teams)
    assert any(g.home_team == home and g.away_team == away for g in season.schedule)


def test_odd_degree_shortfall_reported():
    random.seed(20261124)
    season = make_season(15, [])
    with pytest.warns(RuntimeWarning, match="Schedule shortfall"):
        season.generate_schedule(games_per_team=5)
    counts = assert_integrity(season, 5)
    assert sum(counts.values()) < 75
