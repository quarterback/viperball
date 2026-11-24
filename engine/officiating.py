"""What the officials call: fouls, no calls and missed calls.

The penalty catalog says how often each foul happens on the field.  Officials
do not flag all of them, and real games show three outcomes for a foul:

- Called: a flag.
- No call: the official sees it and lets it go because it did not affect the
  play.  The NFL's officiating chief described holding away from the point of
  attack this way: no one wants a flag on every play.  Graders treat these as
  correct.
- Missed call: a foul that mattered and was not flagged.  In the NBA's Last
  Two Minute reports, incorrect non-calls far outnumber incorrect calls, and
  the NFL has put its graded misses at about 4 to 5 per game.

Fouls also differ in how visible they are.  A false start is in front of
every official; holding inside a pile is seen by one.  So each class of foul
has its own share that matter, its own chance a material foul is seen, and
its own chance an immaterial one is flagged anyway.

Crews differ (the NFL's loosest and strictest crews threw 13 and 20 flags a
game in the same season), and officials lean toward not deciding a close game
late (omission bias, the "let them play" whistle).
"""
from __future__ import annotations

import random
from typing import Dict, Tuple

# class: (share of infractions that affect the play,
#         chance a material foul is flagged,
#         chance an immaterial foul is flagged anyway)
FOUL_CLASSES: Dict[str, Tuple[float, float, float]] = {
    # Pre snap and procedure: in plain view of the whole crew.
    "procedural": (0.95, 0.92, 0.40),
    # Holding and illegal blocks: happen often, mostly away from the ball.
    "blocking": (0.30, 0.70, 0.06),
    # Coverage contact on laterals and kick passes: judgment calls.
    "coverage": (0.55, 0.68, 0.12),
    # Player safety: officials are told to err toward the flag.
    "safety": (0.85, 0.80, 0.45),
    # Ball rules: forward laterals, illegal kicks, touches.
    "ball": (0.90, 0.85, 0.35),
    # After the play: most of it is managed with a word, not a flag.
    "conduct": (0.30, 0.80, 0.08),
}

_CLASS_BY_NAME = {}
for _cls, _names in {
    "procedural": (
        "False Start", "Offsides", "Encroachment", "Delay of Game", "Delay of Game (Defense)",
        "Illegal Formation", "Illegal Formation (Numbering Exception)", "Illegal Defensive Formation",
        "Too Many Men on Field", "Illegal Substitution", "Illegal Viper Alignment",
        "Illegal Viper Substitution", "Missing Viper Jersey", "Illegal Motion", "Illegal Shift",
        "Illegal Snap", "Illegal Numbering", "Disconcerting Signals", "Player Out of Bounds at Snap",
        "Illegal Kickpass Formation", "Illegal Lateral Formation", "Illegal Free Kick Formation",
        "Offside on Kick", "Illegal Participation",
    ),
    "blocking": (
        "Holding", "Illegal Block", "Illegal Block in Back", "Illegal Use of Hands", "Clipping",
        "Chop Block", "Blindside Block", "Blocking Below the Waist", "Tripping", "Illegal Screen",
        "Leverage", "Assisting the Runner", "Interlocked Interference", "Wedge Formation",
        "Illegal Wedge Formation", "Shielding the Kickpass",
    ),
    "coverage": (
        "Defensive Holding", "Lateral Interference", "Contact Before Lateral Arrives",
        "Illegal Contact", "Illegal Viper Contact", "Contact on Kickpass Receiver",
        "Kickpass Interference", "Offensive Kickpass Interference", "Kick Catch Interference",
        "Fair Catch Interference",
    ),
    "safety": (
        "Facemask", "Horse Collar", "Roughing the Zeroback", "Roughing the Kicker",
        "Roughing the Kickpasser", "Targeting", "Helmet-to-Helmet Contact",
        "Hit on Defenseless Kickpass Receiver", "Excessive Contact on Lateral Receiver",
        "Unnecessary Roughness", "Personal Foul", "Striking", "Hurdling", "Lowering the Helmet",
        "Hands to the Face", "Illegal Contact Against Snapper", "Late Hit", "Late Hit Out of Bounds",
        "Piling On", "Fouling Out of Play", "Running Into Kicker",
    ),
    "ball": (
        "Illegal Forward Lateral", "Double Forward Lateral", "Illegal Lateral Beyond Scrimmage",
        "Illegal Double Kickpass", "Kickpass Out of Bounds", "Illegal Kick", "Illegal Bat",
        "Illegal Touch", "Illegal Kickpass Touch", "Concealing the Ball", "Illegal Viper Handoff",
        "Free Kick Out of Bounds", "Player Out of Bounds During Kick",
    ),
    "conduct": (
        "Taunting", "Unsportsmanlike Conduct", "Excessive Celebration", "Sideline Interference",
        "Bench Area Violation", "Persons Illegally on Field", "Player Not Returning Ball",
        "Removal of Helmet", "Continued Play Without Helmet", "Spiking the Ball",
        "Provoking Ill Will", "Obscene Language", "Throwing Punch", "Fighting",
        "Kicker Simulating Being Roughed",
    ),
}.items():
    for _n in _names:
        _CLASS_BY_NAME[_n] = _cls

# Judgment classes get the late game "let them play" lean; plain view ones do not.
JUDGMENT_CLASSES = ("blocking", "coverage", "conduct")
LATE_CLOSE_CALL_FACTOR = 0.85
PLAYOFF_CALL_FACTOR = 0.95


def foul_class(name: str) -> str:
    return _CLASS_BY_NAME.get(name, "blocking")


def crew_strictness(crew) -> float:
    """How tight a crew calls the game.  Stored on the crew once per game;
    spread about +-20%, matching the gap between the NFL's loosest and
    strictest crews (13 and 20 flags a game)."""
    s = getattr(crew, "strictness", None)
    if s is None:
        seed = sum(ord(c) for c in getattr(crew, "name", "")) or 1
        s = max(0.75, min(1.25, random.Random(seed).gauss(1.0, 0.12)))
        try:
            crew.strictness = s
        except Exception:
            pass
    return s


def decide(name: str, crew, late_close: bool = False, playoff: bool = False,
           against_home: bool = False, rng=random) -> Tuple[str, bool]:
    """Return (outcome, material) for a foul that happened.

    outcome is "called", "no_call" (immaterial, let go) or "missed" (material,
    not flagged).
    """
    cls = foul_class(name)
    material_share, see_material, call_immaterial = FOUL_CLASSES[cls]
    material = rng.random() < material_share
    strict = crew_strictness(crew)
    factor = strict
    if cls in JUDGMENT_CLASSES:
        if late_close:
            factor *= LATE_CLOSE_CALL_FACTOR
        if playoff:
            factor *= PLAYOFF_CALL_FACTOR
    # A home leaning crew misses a few more home fouls on close calls.
    lean = getattr(crew, "home_favor", 0.0) or 0.0
    if cls in JUDGMENT_CLASSES:
        factor *= (1.0 - 0.15 * lean) if against_home else (1.0 + 0.15 * lean)
    if material:
        accuracy = getattr(crew, "accuracy", 0.95) or 0.95
        p = see_material * factor * (0.6 + 0.4 * accuracy / 0.95)
        return ("called" if rng.random() < min(0.99, p) else "missed"), True
    p = call_immaterial * factor
    return ("called" if rng.random() < min(0.95, p) else "no_call"), False
