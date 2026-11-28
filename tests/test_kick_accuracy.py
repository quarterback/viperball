"""Snap kicks are three pointers; field goals follow college rates."""

from engine.game_engine import ViperballEngine


def _engine():
    e = ViperballEngine.__new__(ViperballEngine)
    e._kick_range_shift = lambda side=None: 0.0
    return e


def test_snap_kick_curve_drops_three_to_seven_points_per_five_yards():
    e = _engine()
    ref = e._kick_reference()
    rates = [e._drop_kick_success_base(d, ref) for d in range(15, 56, 5)]
    assert abs(rates[0] - 0.42) < 0.005
    steps = [a - b for a, b in zip(rates, rates[1:])]
    assert all(0.029 <= s <= 0.071 for s in steps), steps
    assert steps == sorted(steps)


def test_elite_kicker_still_hits_from_range():
    e = _engine()
    assert e._drop_kick_success_base(35, 95) > 0.40
    assert e._drop_kick_success_base(35, 95) > e._drop_kick_success_base(35, 80) + 0.15


def test_field_goal_follows_college_rates():
    e = _engine()
    ref = e._kick_reference()
    assert 0.84 <= e._place_kick_success_base(35, ref) <= 0.90
    assert 0.68 <= e._place_kick_success_base(45, ref) <= 0.76
    assert 0.45 <= e._place_kick_success_base(55, ref) <= 0.60
    assert e._place_kick_success_base(35, 95) > e._place_kick_success_base(35, ref)
