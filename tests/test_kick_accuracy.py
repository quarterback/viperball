"""Snap kicks are three pointers; field goals follow college rates."""

from engine.game_engine import ViperballEngine


def _engine():
    e = ViperballEngine.__new__(ViperballEngine)
    e._kick_range_shift = lambda side=None: 0.0
    return e


def test_snap_kick_curve_drops_three_to_seven_points_per_five_yards():
    e = _engine()
    ref = e._kick_reference()
    rates = [e._drop_kick_success_base(d, ref) for d in range(15, 51, 5)]
    assert abs(rates[0] - 0.42) < 0.01
    steps = [a - b for a, b in zip(rates, rates[1:])]
    assert all(0.03 <= s <= 0.075 for s in steps), steps
    assert steps == sorted(steps)


def test_elite_kicker_still_hits_from_range():
    e = _engine()
    assert e._drop_kick_success_base(35, 95) > 0.40
    assert e._drop_kick_success_base(35, 95) > e._drop_kick_success_base(35, 80) + 0.15


def test_field_goal_follows_college_rates_through_college_posts():
    e = _engine()
    ref = e._kick_reference()
    assert 0.84 <= e._place_kick_college(35, ref) <= 0.90
    assert 0.68 <= e._place_kick_college(45, ref) <= 0.76
    assert 0.45 <= e._place_kick_college(55, ref) <= 0.60


def test_gaelic_posts_make_kicks_easier_most_at_range():
    from engine.game_engine import V2_ENGINE_CONFIG as C
    e = _engine()
    ref = e._kick_reference()
    lift = {d: e._place_kick_success_base(d, ref) - e._place_kick_college(d, ref)
            for d in (25, 45, 55)}
    assert 0 < lift[25] < lift[45]
    assert 0.05 <= lift[55] <= 0.12
    C["gaelic_posts"] = False
    try:
        assert e._place_kick_success_base(45, ref) == e._place_kick_college(45, ref)
    finally:
        C["gaelic_posts"] = True
    assert e._place_kick_success_base(35, 95) > e._place_kick_success_base(35, ref)
