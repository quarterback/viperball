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
game in the same season), college crews differ more than pro ones (LEVELS),
and officials lean toward not deciding a close game late (omission bias, the
"let them play" whistle).
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
        "Illegal Formation", "Illegal Defensive Formation",
        "Too Many Men on Field", "Illegal Substitution",
        "Illegal Viper Substitution", "Missing Viper Jersey", "Illegal Motion", "Illegal Shift",
        "Illegal Snap", "Disconcerting Signals", "Player Out of Bounds at Snap",
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


# Officiating by level.  Pro crews are full time officials, graded on every
# play, drawn from a small pool: tight around a high standard (the NFL's
# loosest and strictest crews threw 13 and 20 flags a game).  College has many
# more crews of uneven training and review, so crews sit further apart in
# accuracy, strictness and home lean; high school further still.
#   acc_mean: average crew accuracy
#   acc_spread: how far crew accuracy spreads, relative to the referee pool
#   strict_sd: spread of how tightly crews call a game
#   favor_spread: spread of home lean, relative to the referee pool
LEVELS = {
    "pro": {"acc_mean": 0.965, "acc_spread": 0.5, "strict_sd": 0.09, "favor_spread": 0.5},
    "college": {"acc_mean": 0.94, "acc_spread": 1.5, "strict_sd": 0.18, "favor_spread": 1.5},
    "high_school": {"acc_mean": 0.91, "acc_spread": 2.0, "strict_sd": 0.25, "favor_spread": 2.0},
}
POOL_MEAN_ACCURACY = 0.945


def apply_level(crew, level: str = "college") -> None:
    """Set a game crew's accuracy, home lean, error rates and strictness for
    its level.  Safe to call twice."""
    if crew is None or getattr(crew, "_level_applied", None):
        return
    cfg = LEVELS.get(level, LEVELS["college"])
    acc = getattr(crew, "accuracy", POOL_MEAN_ACCURACY) or POOL_MEAN_ACCURACY
    acc = cfg["acc_mean"] + (acc - POOL_MEAN_ACCURACY) * cfg["acc_spread"]
    acc = max(0.80, min(0.995, acc))
    crew.accuracy = round(acc, 4)
    crew.home_favor = max(-0.5, min(0.5, (getattr(crew, "home_favor", 0.0) or 0.0) * cfg["favor_spread"]))
    inaccuracy = 1.0 - acc
    crew.phantom_flag_rate = round(0.0005 + inaccuracy * 0.01, 5)
    crew.spot_error_rate = round(0.001 + inaccuracy * 0.015, 5)
    import zlib
    seed = zlib.crc32(f"{getattr(crew, 'name', '')}|{level}".encode())
    sd = cfg["strict_sd"]
    crew.strictness = max(1 - 2.5 * sd, min(1 + 2.5 * sd, random.Random(seed).gauss(1.0, sd)))
    crew.level = level
    crew._level_applied = level


def crew_strictness(crew) -> float:
    """How tight a crew calls the game (set by apply_level)."""
    s = getattr(crew, "strictness", None)
    if s is None:
        apply_level(crew, getattr(crew, "level", "college"))
        s = getattr(crew, "strictness", 1.0)
    return s


def decide(name: str, crew, late_close: bool = False, playoff: bool = False,
           against_home: bool = False, rng=random) -> Tuple[str, bool]:
    """Return (outcome, material) for a foul that happened.

    outcome is "called", "no_call" (immaterial, let go) or "missed" (material,
    not flagged).
    """
    from engine.discipline import IMMEDIATE_EJECTION
    if name in IMMEDIATE_EJECTION:
        # Serious misconduct is always material; an unseen foul is a miss,
        # never a discretionary no-call. No late-game omission discount.
        accuracy = getattr(crew, "accuracy", 0.95) or 0.95
        return ("called" if rng.random() < min(0.99, accuracy) else "missed"), True
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
        # A less accurate crew sees fewer of the fouls that matter.
        p = see_material * factor * (accuracy / 0.95) ** 3
        return ("called" if rng.random() < min(0.99, p) else "missed"), True
    p = call_immaterial * factor
    return ("called" if rng.random() < min(0.95, p) else "no_call"), False
