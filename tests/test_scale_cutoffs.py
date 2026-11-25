"""SCALE-01: fixed cutoffs written on the old 60 to 100 scale read current
ratings through their old scale equivalent."""
import glob
import os
from collections import Counter

from engine import game_engine as ge

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _players(limit=40):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "teams", "*.json")))[:limit]:
        out.extend(ge.load_team_from_json(f).players)
    return out


def test_position_archetypes_are_not_all_default():
    arch = Counter(ge.assign_archetype(p) for p in _players())
    specialists = sum(n for a, n in arch.items()
                      if a not in ("none", "reliable_flanker", "tackle_keeper",
                                   "hybrid_viper", "dual_threat_zb"))
    assert specialists / sum(arch.values()) > 0.05


def test_variance_archetypes_not_dominated_by_explosive():
    var = Counter(ge.assign_variance_archetype(p) for p in _players())
    assert var["explosive"] / sum(var.values()) < 0.5


def test_median_carrier_gets_no_fumble_penalty():
    # A median player (35) is 70 on the old scale: between the 60 and 85 cutoffs.
    assert 60 <= ge._old(35) < 85
