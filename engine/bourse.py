"""
Bourse Exchange Rate Engine
============================

The Bourse (₯, U+20AF) is the currency of Viperball.  It floats against a
synthetic SDR-like basket of world currencies.  The rate fluctuates each
season via a mean-reverting random walk.

Rate semantics
--------------
  bourse_rate = Bourses per 1 SDR unit (baseline = 1.000)
  > 1.000  →  ₯ is STRONG  (international revenue up, foreign costs up)
  < 1.000  →  ₯ is WEAK    (international revenue down, foreign costs down)

Revenue modifier:  total_revenue  *= bourse_rate_modifier(rate)
Cost modifier:     foreign costs  *= 1 / bourse_rate_modifier(rate)

where bourse_rate_modifier collapses to a ±15 % multiplicative band.
"""

import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

# Flavour labels displayed in the UI
_STRENGTH_LABELS = [
    (1.12, "₯ very strong — international deals lucrative"),
    (1.06, "₯ strong — revenue up"),
    (0.95, "₯ stable"),
    (0.88, "₯ weak — revenue down"),
    (0.00, "₯ very weak — headwinds for clubs"),
]

# Historical rate record: one entry per season
@dataclass
class BourseRateRecord:
    year: int
    rate: float          # SDR-relative (baseline 1.0)
    delta_pct: float     # change from prior year in %
    label: str           # flavour string

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BourseRateRecord":
        return cls(**d)


def _rate_label(rate: float) -> str:
    for threshold, label in _STRENGTH_LABELS:
        if rate >= threshold:
            return label
    return _STRENGTH_LABELS[-1][1]


def next_bourse_rate(
    current_rate: float,
    rng: Optional[random.Random] = None,
    mean: float = 1.0,
    reversion_speed: float = 0.25,
    volatility: float = 0.10,
) -> float:
    """
    Advance the Bourse rate by one season via an Ornstein–Uhlenbeck step.

    Parameters
    ----------
    current_rate:     rate at end of last season
    rng:              seeded Random instance (uses module-level random if None)
    mean:             long-run equilibrium (1.0 = par with SDR basket)
    reversion_speed:  how quickly the rate reverts to mean (0–1)
    volatility:       per-season standard deviation before reversion

    Returns
    -------
    New rate, clamped to [0.60, 1.50].
    """
    if rng is None:
        rng = random.Random()
    shock = rng.gauss(0, volatility)
    new_rate = current_rate + reversion_speed * (mean - current_rate) + shock
    return round(max(0.60, min(1.50, new_rate)), 4)


def revenue_modifier(rate: float) -> float:
    """
    Map the exchange rate to a revenue multiplier in [0.85, 1.15].

    At par (rate=1.0) → modifier = 1.0.
    At rate=1.50 (very strong ₯) → modifier ≈ 1.15.
    At rate=0.60 (very weak ₯) → modifier ≈ 0.85.
    """
    # Linear interpolation between 0.85 and 1.15 over [0.60, 1.50]
    modifier = 0.85 + (rate - 0.60) / (1.50 - 0.60) * 0.30
    return round(max(0.85, min(1.15, modifier)), 4)


def cost_modifier(rate: float) -> float:
    """
    Foreign player costs move inversely to the revenue modifier.
    When ₯ is strong, international wages cost more domestically.
    """
    rev_mod = revenue_modifier(rate)
    # Partial inverse: costs move half as much as revenue
    return round(1.0 + (1.0 - rev_mod) * 0.5, 4)


def build_rate_record(year: int, old_rate: float, new_rate: float) -> BourseRateRecord:
    delta = (new_rate - old_rate) / old_rate * 100 if old_rate else 0.0
    return BourseRateRecord(
        year=year,
        rate=new_rate,
        delta_pct=round(delta, 2),
        label=_rate_label(new_rate),
    )
