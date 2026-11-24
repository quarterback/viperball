"""ROST-01: players made after the opening rosters keep the league's shape."""
import random
import statistics

from engine.development import apply_offseason_development
from engine.hs_league import _generate_hs_player
from engine.recruiting import generate_recruit_class, generate_single_recruit
from engine.talent import roll_stats, stars_for_level


def _deciles(values):
    return statistics.quantiles(values, n=10)


def test_recruit_class_has_stars_and_projects():
    cls = generate_recruit_class(2027, size=1200, rng=random.Random(11))
    ovr = [r.to_player_card("X").overall for r in cls]
    d = _deciles(ovr)
    # Opening roster freshmen run about 13 at the 10th percentile and 58 at the 90th.
    assert d[0] < 20 and d[-1] > 50
    assert 28 < statistics.mean(ovr) < 38
    shares = {s: sum(r.stars == s for r in cls) / len(cls) for s in range(1, 6)}
    assert 0.015 < shares[5] < 0.05 and 0.08 < shares[4] < 0.18
    assert all(r.true_work_rate > 0 for r in cls)
    assert all(r.to_player_card("X").work_rate == r.true_work_rate for r in cls[:20])


def test_requested_stars_match_level():
    rng = random.Random(3)
    for stars in (1, 3, 5):
        recruits = [generate_single_recruit(f"R{stars}{i}", stars=stars, rng=rng) for i in range(30)]
        assert all(r.stars == stars for r in recruits)
    fives = statistics.mean(r.true_overall for r in recruits)
    ones = statistics.mean(generate_single_recruit(f"Q{i}", stars=1, rng=rng).true_overall
                           for i in range(30))
    assert fives > ones + 25


def test_linemen_are_not_floored_at_old_scale_speed():
    rng = random.Random(5)
    speeds = [roll_stats(30, "Offensive Line", rng)["speed"] for _ in range(300)]
    assert statistics.mean(speeds) < 32
    assert stars_for_level(80) == 5 and stars_for_level(12) == 1


def test_hs_seniors_match_college_freshmen():
    rng = random.Random(8)
    seniors = [_generate_hs_player("Halfback", "Senior", "OH", "Central High", rng) for _ in range(400)]
    freshmen = [_generate_hs_player("Halfback", "Freshman", "OH", "Central High", rng) for _ in range(400)]
    assert statistics.mean(p.overall for p in seniors) > statistics.mean(p.overall for p in freshmen) + 4
    assert all(p.level for p in seniors)


def test_college_development_matches_class_gaps():
    rng = random.Random(9)
    cards = [generate_single_recruit(f"D{i}", rng=rng).to_player_card("X") for i in range(400)]
    start = statistics.mean(c.overall for c in cards)
    for _ in range(3):
        for c in cards:
            apply_offseason_development(c, rng=rng)
    # Opening rosters gain about 4.4 overall from freshman to senior.
    assert 3.0 < statistics.mean(c.overall for c in cards) - start < 6.0
