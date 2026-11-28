"""Position fit: how well a player can play each position group.

Every group asks for its own mix of skills. A player's fit in a group is the
weighted average of the ratings that group uses, so a fast, sure handed
Keeper can rate well at flanker and a strong Halfback can rate well on the
defensive line. Fit is not a new rating; it comes from the ratings a player
already has.

Two more pieces sit on top of it:

* Natural fit. Each group has minimums on the two skills it cannot do
  without, and the line groups need size while the open field groups
  cannot carry too much of it. A player who meets them is a natural fit and
  can be listed there.
  A coach can still put anyone anywhere; natural fit only says who is likely
  to hold up.
* Adaptability. Agile, aware players with an even spread of skills pick up a
  new job faster. Adaptability softens the cost of playing outside one's own
  group. It is derived from the ratings, never stored.

The engine uses fit for coach decisions: who to list as a Seagull and who to
send on in another group. The play itself is still decided by the player's
actual ratings in each contest.
"""

import statistics

CORE = ("speed", "stamina", "kicking", "lateral_skill", "tackling", "agility",
        "power", "awareness", "hands", "kick_power", "kick_accuracy")

GROUPS = ("Zeroback", "Viper", "flanker", "Offensive Line", "Defensive Line",
          "Keeper", "defensive back")

# The skills each group uses and how much.
PROFILES = {
    "Zeroback": {"kick_accuracy": 0.20, "awareness": 0.20, "kick_power": 0.15,
                 "kicking": 0.15, "lateral_skill": 0.15, "speed": 0.15},
    "Viper": {"speed": 0.25, "agility": 0.20, "hands": 0.20, "awareness": 0.20,
              "lateral_skill": 0.15},
    "flanker": {"speed": 0.25, "agility": 0.20, "hands": 0.15, "lateral_skill": 0.15,
                "awareness": 0.15, "power": 0.10},
    "Offensive Line": {"power": 0.45, "awareness": 0.25, "agility": 0.15, "stamina": 0.15},
    "Defensive Line": {"power": 0.30, "tackling": 0.30, "speed": 0.20, "agility": 0.20},
    "Keeper": {"speed": 0.25, "tackling": 0.25, "awareness": 0.25, "hands": 0.15,
               "agility": 0.10},
    "defensive back": {"tackling": 0.35, "speed": 0.25, "awareness": 0.20, "agility": 0.20},
}

# The bare minimums on the two skills a group cannot do without, set near the
# league average for players who play the group now.
MINIMUMS = {
    "Zeroback": {"kick_accuracy": 36, "awareness": 36},
    "Viper": {"speed": 36, "hands": 35},
    "flanker": {"speed": 35, "agility": 35},
    "Offensive Line": {"power": 38, "awareness": 32},
    "Defensive Line": {"power": 38, "tackling": 36},
    "Keeper": {"speed": 35, "awareness": 35},
    "defensive back": {"tackling": 34, "speed": 35},
}

# Size. Linemen play at 185 to 215 pounds and everyone else at 160 to 200,
# so the line groups need weight and the open field groups cannot carry too
# much of it.
MIN_WEIGHT = {"Offensive Line": 188, "Defensive Line": 188}
MAX_WEIGHT = {"Viper": 190, "flanker": 190, "Keeper": 192, "defensive back": 192}

OWN_GROUP = {"Zeroback": "Zeroback", "Viper": "Viper", "Halfback": "flanker",
             "Wingback": "flanker", "Slotback": "flanker",
             "Offensive Line": "Offensive Line", "Defensive Line": "Defensive Line",
             "Keeper": "Keeper"}


def own_group(player) -> str:
    return OWN_GROUP.get(player.position, "flanker")


def group_score(player, group: str) -> float:
    """Weighted average of the ratings the group uses, 0 to 100."""
    profile = PROFILES[group]
    return sum(getattr(player, attr, 35) * w for attr, w in profile.items())


def adaptability(player) -> float:
    """0 to 100. Agility and awareness, plus an even spread of skills."""
    values = [getattr(player, a, 35) for a in CORE]
    spread = statistics.pstdev(values) if len(values) > 1 else 0.0
    evenness = max(0.0, 100.0 - 2.5 * spread)
    return round(0.35 * getattr(player, "agility", 35)
                 + 0.35 * getattr(player, "awareness", 35)
                 + 0.30 * evenness, 1)


def natural_fit(player, group: str) -> bool:
    if group == own_group(player):
        return True
    weight = getattr(player, "weight", 175) or 175
    if weight < MIN_WEIGHT.get(group, 0) or weight > MAX_WEIGHT.get(group, 999):
        return False
    return all(getattr(player, a, 0) >= m for a, m in MINIMUMS[group].items())


def fit(player, group: str) -> float:
    """How well she plays the group, as a coach would judge it. Outside her
    own group she gives up 8%, less the more adaptable she is."""
    score = group_score(player, group)
    if group == own_group(player) or (group == "defensive back"
                                       and player.position in ("Viper", "Halfback", "Wingback", "Slotback")):
        return round(score, 1)
    return round(score * (0.92 + 0.08 * adaptability(player) / 100.0), 1)


def fits(player) -> dict:
    """Fit in every group, with natural fit marked."""
    return {g: {"fit": fit(player, g), "natural": natural_fit(player, g)} for g in GROUPS}
