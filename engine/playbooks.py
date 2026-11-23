"""
Coach playbooks.

Every team has a home book (its offense style and defense scheme) and
borrows packages from other books. Coaches call a borrowed package mostly
in the situation it was built for: Ground & Pound in short yardage, Boot
Raid on the Launch Pad, Lockdown when the other team is in kicking range.
They also lean on packages that beat this week's opponent.

A borrowed call takes that book's play design whole: its play families,
kick pass mix, formation mix and situational modes. The home book keeps
its system: tempo, conditioning and signature mechanics such as East
Coast's rhythm stay with the home book. Because a staff drills its home
book every day, a borrowed offensive call gets half of its book's
execution bonuses, and a borrowed defensive package plays halfway between
the home scheme and the borrowed one.

How much a staff borrows comes from its coordinator's adaptability and
stubbornness: a purist calls about 5% of plays from other books, a magpie
up to about 45%.
"""

from __future__ import annotations

import random
from typing import Dict, Iterable, Optional, Set

# ── Situations each book's packages were built for ──
OFFENSE_BOOK_SITUATIONS: Dict[str, tuple] = {
    "ground_pound": ("short_yardage", "goal_line"),
    "ironclad": ("short_yardage", "protect_lead"),
    "ball_control": ("protect_lead",),
    "boot_raid": ("launch_pad",),
    "six_shooter": ("launch_pad", "late_downs"),
    "shock_and_awe": ("chasing", "long_yardage"),
    "chain_gang": ("chasing",),
    "lateral_spread": ("chasing", "long_yardage"),
    "quick_strike": ("chasing", "two_minute"),
    "east_coast": ("long_yardage", "two_minute"),
    # Stampede wins by running at tired defenders, so its packages come out
    # when the defense on the field is worn down. (Measured: called on early
    # downs instead, borrowed Stampede and Slick 'n Slide plays lost about a
    # yard a play, because their tempo and read systems stay home.)
    "stampede": ("tired_defense",),
    # Ghost, Mismatch, Mousetrap and Slick 'n Slide are called on matchups.
    "slick_n_slide": (),
    "ghost": (),
    "mismatch": (),
    "mousetrap": (),
}

def defense_package_situations(defense_styles: Dict[str, dict]) -> Dict[str, tuple]:
    """Where each defensive scheme is built to be strong, read from the
    scheme's own ratings in DEFENSE_STYLES (its situational modifiers,
    kick suppression and explosive suppression), so coaches call a package
    where the scheme says it is strong. Schemes with no situational edge
    (Shadow) are called on matchups."""
    out = {}
    for name, d in defense_styles.items():
        sit = d.get("situational", {})
        tags = []
        if sit.get("short_yardage_modifier", 1.0) <= 0.85:
            tags.append("short_yardage")
        if sit.get("red_zone_read_boost", 0.0) >= 0.10 and sit.get("short_yardage_modifier", 1.0) <= 0.90:
            tags.append("goal_line")
        if sit.get("long_yardage_modifier", 1.0) <= 0.90:
            tags.append("long_yardage")
        if d.get("kick_suppression", 1.0) <= 0.85:
            tags.append("kick_range")
        if sit.get("leading_conserve", 0.0) >= 0.10 and d.get("explosive_suppression", 1.0) <= 0.78:
            tags.append("protect_lead")
        if d.get("explosive_suppression", 1.0) <= 0.60:
            tags.append("two_minute")
        if sit.get("trailing_aggression", 0.0) >= 0.10:
            tags.append("chasing")
        out[name] = tuple(tags)
    return out


# Books with no identity of their own are never borrowed.
NOT_BORROWED = {"balanced"}

IN_SITUATION = 2.5      # a package is called this much more in its situation
OUT_OF_SITUATION = 0.6
MATCHUP_GAIN = 3.0      # how hard coaches lean on a package that beats the opponent

# Offensive fields that describe what play gets called. A borrowed call
# takes these whole from the borrowed book.
_CALL_PREFIXES = ("weights", "kick_pass_weights", "formation_weights")
_CALL_FIELDS = {"run_vs_lateral", "early_down_aggression", "red_zone_run_pct",
                "option_rate", "lateral_risk"}
# Offensive execution bonuses: a borrowed call gets half of its book's.
_BONUS_FIELDS = {"run_bonus", "explosive_lateral_bonus", "option_read_bonus",
                 "broken_play_bonus", "kick_accuracy_bonus", "pindown_bonus"}
BORROWED_BONUS_SHARE = 0.5

# Defensive fields that describe the call (who covers, how many rush):
# taken whole. Effectiveness fields play halfway to the borrowed scheme.
_DEF_CALL_FIELDS = {"label", "description", "personnel_weights", "pressure_factor",
                    "gameplan_bias", "situational"}
BORROWED_DEFENSE_SHARE = 0.5


def _is_call_key(k: str) -> bool:
    return k.startswith(_CALL_PREFIXES) or k in _CALL_FIELDS


def merged_offense(base: dict, borrowed: dict) -> dict:
    """The style record for one borrowed call."""
    out = {k: v for k, v in base.items() if not _is_call_key(k) and k not in _BONUS_FIELDS}
    for k, v in borrowed.items():
        if _is_call_key(k):
            out[k] = v
    for k in _BONUS_FIELDS:
        out[k] = BORROWED_BONUS_SHARE * borrowed.get(k, 0.0)
    return out


def _halfway(a, b, share):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + share * (b - a)
    if isinstance(a, dict) and isinstance(b, dict):
        keys = set(a) | set(b)
        return {k: _halfway(a.get(k, b.get(k)), b.get(k, a.get(k)), share) for k in keys}
    return b


def merged_defense(base: dict, package: dict) -> dict:
    """The defense record for one borrowed package call."""
    out = {}
    for k in set(base) | set(package):
        if k in _DEF_CALL_FIELDS:
            out[k] = package.get(k, base.get(k))
        elif k in base and k in package:
            out[k] = _halfway(base[k], package[k], BORROWED_DEFENSE_SHARE)
        else:
            out[k] = package.get(k, base.get(k))
    return out


# ── Building a staff's playbook ──

def borrow_appetite(staff: Optional[dict], role: str, rng: random.Random) -> float:
    """0 (purist) to 1 (magpie), from the coordinator's adaptability and
    stubbornness, the head coach counting a third."""
    def sliders(card):
        s = getattr(card, "personality_sliders", None) or {}
        return s.get("adaptability"), s.get("stubbornness")

    vals = []
    if staff:
        for key, wt in ((role, 2.0), ("head_coach", 1.0)):
            card = staff.get(key)
            if card is None:
                continue
            a, s = sliders(card)
            if a is None or s is None:
                continue
            vals.append((0.5 + (a - s) / 160.0, wt))
    if vals:
        base = sum(v * w for v, w in vals) / sum(w for _, w in vals)
        base += rng.gauss(0, 0.08)
    else:
        base = rng.betavariate(2.0, 2.0)
    return max(0.0, min(1.0, base))


def build_playbook(home: str, fit: Dict[str, float], appetite: float,
                   rng: random.Random, all_books: Iterable[str]) -> Dict[str, float]:
    """Pick one to three borrowed books and the share of calls each gets.

    fit: how well each book suits the roster (books not listed get a small
    default), so a team mostly borrows what its players can run."""
    pool = [b for b in all_books if b != home and b not in NOT_BORROWED]
    if not pool:
        return {}
    weights = [max(0.05, fit.get(b, 0.35)) for b in pool]
    n = 1 + (appetite > 0.40) + (appetite > 0.75)
    chosen = []
    for _ in range(min(n, len(pool))):
        pick = rng.choices(range(len(pool)), weights=weights)[0]
        chosen.append(pool[pick])
        weights[pick] = 0.0
        if sum(weights) <= 0:
            break
    total = 0.05 + 0.40 * appetite
    raw = [max(0.05, fit.get(b, 0.35)) * rng.uniform(0.7, 1.3) for b in chosen]
    s = sum(raw)
    return {b: round(total * r / s, 3) for b, r in zip(chosen, raw)}


# ── Calling a play ──

def situation_tags(state, side: str) -> Set[str]:
    """Situations from the calling team's point of view. Field position and
    distance are always the offense's."""
    tags = set()
    diff = (state.home_score - state.away_score) if side == "home" else (state.away_score - state.home_score)
    q, tr = state.quarter, state.time_remaining
    fp, ytg, down = state.field_position, state.yards_to_go, state.down
    if ytg <= 4:
        tags.add("short_yardage")
    if ytg >= 12:
        tags.add("long_yardage")
    if fp >= 88:
        tags.add("goal_line")
    if 55 <= fp <= 85:
        tags.add("launch_pad")
    if fp >= 55 and down >= 4:
        tags.add("kick_range")
    if down >= 4:
        tags.add("late_downs")
    if down <= 2 and ytg >= 10:
        tags.add("early_down")
    if (q == 4 and diff >= 1) or (q >= 3 and diff >= 10):
        tags.add("protect_lead")
    if (q >= 3 and diff <= -10) or (q == 4 and tr <= 300 and diff < 0):
        tags.add("chasing")
    if q in (2, 4) and tr <= 120:
        tags.add("two_minute")
    return tags


def choose_call(home: str, playbook: Dict[str, float], tags: Set[str],
                situations: Dict[str, tuple], matchup) -> str:
    """Pick the book this play comes from. matchup(book) returns how well
    that book fares against this opponent (1.0 neutral, above favors the
    calling team)."""
    if not playbook:
        return home
    names = [home]
    weights = [max(0.05, 1.0 - sum(playbook.values()))]
    for book, share in playbook.items():
        sit = IN_SITUATION if set(situations.get(book, ())) & tags else OUT_OF_SITUATION
        m = max(0.6, min(1.6, 1.0 + (matchup(book) - 1.0) * MATCHUP_GAIN))
        names.append(book)
        weights.append(share * sit * m)
    return random.choices(names, weights=weights)[0]


def describe(playbook: Dict[str, float], labels: Dict[str, str]) -> str:
    if not playbook:
        return "home book only"
    parts = [f"{labels.get(b, b)} {round(s * 100)}%" for b, s in
             sorted(playbook.items(), key=lambda x: -x[1])]
    return "borrows " + ", ".join(parts)
