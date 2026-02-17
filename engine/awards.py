"""
Viperball End-of-Season Awards System

Selects individual award winners, All-American teams, and All-Conference teams
at the conclusion of each regular season.

Selection methodology:
- Winners are chosen from players across all team rosters using attribute
  ratings (since play-by-play per-player stats aren't aggregated in Season).
- Team performance context is applied as a multiplier: top teams see their
  stars recognized more; weak teams see their stars discounted slightly.
- Position eligibility, archetype type, and attribute weights are all
  Viperball-specific.

Individual Awards:
    "The Roper"            – Best Zeroback (nation's premier all-around threat)
    "The Viper Claw"       – Best Viper (best alignment-exempt threat)
    "The Iron Chain"       – Best lateral specialist
    "The Brickwall"        – Best defensive stopper (Lineman / Safety / Keeper)
    "The Kicker's Crown"   – Best kicker / field position threat
    "Offensive POY"        – Overall best offensive player
    "Defensive POY"        – Overall best defensive player
    "Coach of the Year"    – Best coaching performance relative to expectation
    "Chaos King"           – Team with most chaotic / entertaining season
    "Most Improved Team"   – Biggest win-total jump from last season

All-American Teams (1st and 2nd):
    1 Zeroback, 2 Vipers, 3 Halfbacks/Wingbacks, 2 Linemen, 1 Safety/Keeper

All-Conference Teams (1st team per conference):
    Same position slots as All-American

Usage:
    from engine.awards import compute_season_awards
    awards = compute_season_awards(season, dynasty, year)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from engine.season import Season
from engine.game_engine import Team, Player


# ──────────────────────────────────────────────
# DATACLASSES
# ──────────────────────────────────────────────

@dataclass
class AwardWinner:
    """A single individual award winner."""
    award_name: str
    player_name: str
    team_name: str
    position: str
    overall_rating: int
    reason: str   # brief narrative phrase for display

    def to_dict(self) -> dict:
        return {
            "award_name": self.award_name,
            "player_name": self.player_name,
            "team_name": self.team_name,
            "position": self.position,
            "overall_rating": self.overall_rating,
            "reason": self.reason,
        }


@dataclass
class AllAmericanTeam:
    """
    First or second-team All-American selections.
    team_level: "first" or "second"
    """
    team_level: str  # "first" | "second"
    year: int
    slots: List[AwardWinner] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "team_level": self.team_level,
            "year": self.year,
            "slots": [w.to_dict() for w in self.slots],
        }


@dataclass
class AllConferenceTeam:
    """First-team All-Conference selections for one conference."""
    conference_name: str
    year: int
    slots: List[AwardWinner] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "conference_name": self.conference_name,
            "year": self.year,
            "slots": [w.to_dict() for w in self.slots],
        }


@dataclass
class SeasonHonors:
    """
    Complete end-of-season honors package.
    Returned by compute_season_awards() and stored in Dynasty.
    """
    year: int

    # Individual awards
    individual_awards: List[AwardWinner] = field(default_factory=list)

    # Collective honors
    all_american_first: Optional[AllAmericanTeam] = None
    all_american_second: Optional[AllAmericanTeam] = None
    all_conference_teams: Dict[str, AllConferenceTeam] = field(default_factory=dict)

    # Team-level awards (winner name only for simplicity)
    coach_of_year: str = ""
    chaos_king: str = ""        # most entertaining team
    most_improved: str = ""     # biggest win jump

    def get_award(self, award_name: str) -> Optional[AwardWinner]:
        for a in self.individual_awards:
            if a.award_name == award_name:
                return a
        return None

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "individual_awards": [a.to_dict() for a in self.individual_awards],
            "all_american_first": self.all_american_first.to_dict() if self.all_american_first else None,
            "all_american_second": self.all_american_second.to_dict() if self.all_american_second else None,
            "all_conference_teams": {k: v.to_dict() for k, v in self.all_conference_teams.items()},
            "coach_of_year": self.coach_of_year,
            "chaos_king": self.chaos_king,
            "most_improved": self.most_improved,
        }


# ──────────────────────────────────────────────
# PLAYER SCORING HELPERS
# ──────────────────────────────────────────────

# Position group classifier
def _pos_group(position: str) -> str:
    pos = position.lower()
    if "zeroback" in pos or "zero" in pos:
        return "zeroback"
    if "viper" in pos:
        return "viper"
    if any(p in pos for p in ["halfback", "wingback", "shiftback", "flanker"]):
        return "back"
    if "lineman" in pos or "line" in pos or "wedge" in pos:
        return "lineman"
    if "safety" in pos or "keeper" in pos:
        return "safety"
    return "other"


def _player_score(player: Player, team_perf_mult: float = 1.0) -> float:
    """Base scoring function: position-weighted average * team context."""
    pos = player.position.lower()

    if "zeroback" in pos or "zero" in pos:
        raw = (player.speed * 0.9 + player.kicking * 1.2 + player.lateral_skill * 1.1
               + player.awareness * 1.2 + player.stamina * 0.8)
        raw /= 5.2
    elif "viper" in pos:
        raw = (player.speed * 1.3 + player.lateral_skill * 1.4 + player.agility * 1.2
               + player.hands * 1.0 + player.stamina * 0.8)
        raw /= 5.7
    elif any(p in pos for p in ["halfback", "wingback", "shiftback"]):
        raw = (player.speed * 1.2 + player.lateral_skill * 1.1 + player.agility * 1.1
               + player.power * 0.9 + player.stamina * 0.9)
        raw /= 5.2
    elif "lineman" in pos or "line" in pos or "wedge" in pos:
        raw = (player.tackling * 1.6 + player.power * 1.5 + player.stamina * 1.2
               + player.awareness * 0.9)
        raw /= 5.2
    elif "safety" in pos or "keeper" in pos:
        raw = (player.speed * 1.1 + player.tackling * 1.3 + player.lateral_skill * 1.0
               + player.awareness * 1.3 + player.stamina * 0.9)
        raw /= 5.6
    else:
        raw = player.overall

    return round(raw * team_perf_mult, 2)


def _kicker_score(player: Player, team_perf_mult: float = 1.0) -> float:
    raw = (player.kicking * 1.4 + player.kick_power * 1.2 + player.kick_accuracy * 1.3
           + player.awareness * 0.8)
    return round((raw / 4.7) * team_perf_mult, 2)


def _lateral_score(player: Player, team_perf_mult: float = 1.0) -> float:
    raw = (player.lateral_skill * 1.5 + player.hands * 1.2 + player.speed * 1.1
           + player.agility * 1.1)
    return round((raw / 4.9) * team_perf_mult, 2)


def _defensive_score(player: Player, team_perf_mult: float = 1.0) -> float:
    raw = (player.tackling * 1.5 + player.power * 1.1 + player.speed * 1.0
           + player.awareness * 1.3 + player.stamina * 1.0)
    return round((raw / 5.9) * team_perf_mult, 2)


# ──────────────────────────────────────────────
# TEAM PERFORMANCE MULTIPLIER
# ──────────────────────────────────────────────

def _team_perf_mult(team_name: str, standings: dict) -> float:
    """
    0.88 – 1.10 multiplier based on team win% and OPI.
    Top programs get a slight boost; bottom feeders get a slight discount.
    """
    record = standings.get(team_name)
    if record is None:
        return 1.0
    win_pct = record.win_percentage
    opi = record.avg_opi
    # Scale: 0.88 (0% wins, low OPI) to 1.10 (100% wins, top OPI)
    mult = 0.88 + win_pct * 0.15 + min(opi / 100.0, 1.0) * 0.07
    return round(min(1.10, max(0.88, mult)), 3)


# ──────────────────────────────────────────────
# POSITION SLOT SELECTOR
# ──────────────────────────────────────────────

def _best_in_position(
    teams: Dict[str, Team],
    standings: dict,
    group_filter: str,
    score_fn,
    exclude: set = None,
) -> Optional[Tuple[Player, str]]:
    """
    Find the best player in a position group, excluding already-selected players.

    Returns (player, team_name) or None.
    """
    if exclude is None:
        exclude = set()

    best_score = -1.0
    best_pair = None

    for team_name, team in teams.items():
        mult = _team_perf_mult(team_name, standings)
        for player in team.players:
            uid = f"{team_name}::{player.name}"
            if uid in exclude:
                continue
            if _pos_group(player.position) != group_filter:
                continue
            score = score_fn(player, mult)
            if score > best_score:
                best_score = score
                best_pair = (player, team_name)

    return best_pair


def _select_slots(
    teams: Dict[str, Team],
    standings: dict,
    slot_spec: List[Tuple[str, str, callable]],
    exclude: set = None,
    year: int = 0,
    team_level: str = "first",
) -> List[AwardWinner]:
    """
    Fill a list of (group_filter, award_label, score_fn) slots.

    Returns list of AwardWinner objects.
    """
    if exclude is None:
        exclude = set()
    winners = []
    for group, label, score_fn in slot_spec:
        pair = _best_in_position(teams, standings, group, score_fn, exclude)
        if pair:
            player, team_name = pair
            uid = f"{team_name}::{player.name}"
            exclude.add(uid)
            winners.append(AwardWinner(
                award_name=label,
                player_name=player.name,
                team_name=team_name,
                position=player.position,
                overall_rating=player.overall,
                reason=f"{team_level.title()} Team All-American",
            ))
    return winners


# Canonical All-American position slots
_AA_SLOTS = [
    ("zeroback", "Zeroback",         _player_score),
    ("viper",    "Viper (1)",        _player_score),
    ("viper",    "Viper (2)",        _player_score),
    ("back",     "Halfback/Wingback (1)", _player_score),
    ("back",     "Halfback/Wingback (2)", _player_score),
    ("back",     "Halfback/Wingback (3)", _player_score),
    ("lineman",  "Lineman (1)",      _player_score),
    ("lineman",  "Lineman (2)",      _player_score),
    ("safety",   "Safety/Keeper",    _player_score),
]


# ──────────────────────────────────────────────
# INDIVIDUAL AWARD HELPERS
# ──────────────────────────────────────────────

def _select_individual_awards(
    teams: Dict[str, Team],
    standings: dict,
) -> List[AwardWinner]:
    awards = []
    seen: set = set()

    def _best(group, score_fn, award_name, reason_template):
        pair = _best_in_position(teams, standings, group, score_fn, seen)
        if pair:
            player, team = pair
            seen.add(f"{team}::{player.name}")
            awards.append(AwardWinner(
                award_name=award_name,
                player_name=player.name,
                team_name=team,
                position=player.position,
                overall_rating=player.overall,
                reason=reason_template.format(team=team),
            ))

    # The Roper – best Zeroback
    _best("zeroback", _player_score,
          "The Roper Award",
          "Nation's premier all-around threat ({team})")

    # The Viper Claw – best Viper
    _best("viper", _player_score,
          "The Viper Claw Award",
          "Elite alignment-exempt weapon ({team})")

    # The Iron Chain – best lateral specialist (any position with high lateral_skill)
    _best("back", _lateral_score,
          "The Iron Chain Award",
          "Master of the lateral chain game ({team})")

    # The Brickwall – best defender (lineman or safety)
    # Check linemen first, then safeties, pick best
    best_line = _best_in_position(teams, standings, "lineman", _defensive_score, set(seen))
    best_saf = _best_in_position(teams, standings, "safety", _defensive_score, set(seen))
    if best_line and best_saf:
        mult_l = _team_perf_mult(best_line[1], standings)
        mult_s = _team_perf_mult(best_saf[1], standings)
        if _defensive_score(best_line[0], mult_l) >= _defensive_score(best_saf[0], mult_s):
            player, team = best_line
        else:
            player, team = best_saf
    elif best_line:
        player, team = best_line
    elif best_saf:
        player, team = best_saf
    else:
        player, team = None, None

    if player:
        seen.add(f"{team}::{player.name}")
        awards.append(AwardWinner(
            award_name="The Brickwall Award",
            player_name=player.name,
            team_name=team,
            position=player.position,
            overall_rating=player.overall,
            reason=f"Immovable defensive force ({team})",
        ))

    # The Kicker's Crown – best kicker (any position, highest kicker score)
    best_k = None
    best_k_score = -1.0
    for t_name, t in teams.items():
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            s = _kicker_score(p, mult)
            if s > best_k_score:
                best_k_score = s
                best_k = (p, t_name)
    if best_k:
        player, team = best_k
        seen.add(f"{team}::{player.name}")
        awards.append(AwardWinner(
            award_name="The Kicker's Crown",
            player_name=player.name,
            team_name=team,
            position=player.position,
            overall_rating=player.overall,
            reason=f"Best territorial and scoring kicker ({team})",
        ))

    # Offensive Player of the Year – best offensive player overall
    # (exclude already-awarded Brickwall/Kicker)
    best_off = None
    best_off_score = -1.0
    off_groups = {"zeroback", "viper", "back"}
    for t_name, t in teams.items():
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            if _pos_group(p.position) not in off_groups:
                continue
            s = _player_score(p, mult)
            if s > best_off_score:
                best_off_score = s
                best_off = (p, t_name)
    if best_off:
        player, team = best_off
        seen.add(f"{team}::{player.name}")
        awards.append(AwardWinner(
            award_name="Offensive Player of the Year",
            player_name=player.name,
            team_name=team,
            position=player.position,
            overall_rating=player.overall,
            reason=f"Most dominant offensive force ({team})",
        ))

    # Defensive Player of the Year – best defensive player overall
    best_def = None
    best_def_score = -1.0
    def_groups = {"lineman", "safety"}
    for t_name, t in teams.items():
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            if _pos_group(p.position) not in def_groups:
                continue
            s = _defensive_score(p, mult)
            if s > best_def_score:
                best_def_score = s
                best_def = (p, t_name)
    if best_def:
        player, team = best_def
        seen.add(f"{team}::{player.name}")
        awards.append(AwardWinner(
            award_name="Defensive Player of the Year",
            player_name=player.name,
            team_name=team,
            position=player.position,
            overall_rating=player.overall,
            reason=f"Most dominant defensive force ({team})",
        ))

    return awards


# ──────────────────────────────────────────────
# ALL-CONFERENCE SELECTION
# ──────────────────────────────────────────────

def _select_all_conference(
    conference_name: str,
    conf_teams: List[str],
    all_teams: Dict[str, Team],
    standings: dict,
    year: int,
) -> AllConferenceTeam:
    """Select 1st-team All-Conference for a single conference."""
    conf_team_objs = {t: all_teams[t] for t in conf_teams if t in all_teams}
    seen: set = set()
    slots = _select_slots(conf_team_objs, standings, _AA_SLOTS, seen, year, "conference")
    return AllConferenceTeam(
        conference_name=conference_name,
        year=year,
        slots=slots,
    )


# ──────────────────────────────────────────────
# TEAM-LEVEL AWARDS
# ──────────────────────────────────────────────

def _select_team_awards(
    standings: dict,
    prev_season_wins: Dict[str, int] = None,
) -> Tuple[str, str, str]:
    """
    Returns (coach_of_year_team, chaos_king_team, most_improved_team).
    """
    sorted_std = sorted(standings.values(), key=lambda r: r.win_percentage, reverse=True)

    # Coach of the Year: team that exceeded expectations the most.
    # Proxy: highest win% with high OPI relative to team avg kicking (lower-rated offense doing well).
    coy_scores = {}
    for r in standings.values():
        # Surprise factor: win% relative to kicking average (high wins with lower-rated D)
        coy_scores[r.team_name] = r.win_percentage * 0.7 + r.avg_opi * 0.003
    coy = max(coy_scores, key=coy_scores.get) if coy_scores else ""

    # Chaos King: team with highest avg_chaos
    chaos_k = max(standings.values(), key=lambda r: r.avg_chaos).team_name if standings else ""

    # Most Improved: biggest gain in wins vs last season
    most_imp = ""
    if prev_season_wins:
        best_gain = -999
        for r in standings.values():
            prev = prev_season_wins.get(r.team_name, r.wins)
            gain = r.wins - prev
            if gain > best_gain:
                best_gain = gain
                most_imp = r.team_name
    else:
        # Without prior season, just pick the team with most wins that didn't win championship
        if len(sorted_std) > 1:
            most_imp = sorted_std[1].team_name
        elif sorted_std:
            most_imp = sorted_std[0].team_name

    return coy, chaos_k, most_imp


# ──────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────

def compute_season_awards(
    season: Season,
    year: int,
    conferences: Dict[str, List[str]] = None,
    prev_season_wins: Dict[str, int] = None,
) -> SeasonHonors:
    """
    Compute all end-of-season honors for a completed regular season.

    Args:
        season:           Completed Season object with standings
        year:             The season year (for labeling)
        conferences:      dict of conf_name -> [team_names]; used for All-Conference
        prev_season_wins: dict of team_name -> wins from last season; used for Most Improved

    Returns:
        SeasonHonors object ready to store in Dynasty.honors_history
    """
    standings = season.standings
    teams = season.teams

    honors = SeasonHonors(year=year)

    # Individual awards
    honors.individual_awards = _select_individual_awards(teams, standings)

    # All-American (1st team)
    aa_seen: set = set()
    aa_first_slots = _select_slots(teams, standings, _AA_SLOTS, aa_seen, year, "first")
    honors.all_american_first = AllAmericanTeam(
        team_level="first", year=year, slots=aa_first_slots
    )

    # All-American (2nd team) – from remaining players, same slots
    aa_second_slots = _select_slots(teams, standings, _AA_SLOTS, aa_seen, year, "second")
    honors.all_american_second = AllAmericanTeam(
        team_level="second", year=year, slots=aa_second_slots
    )

    # All-Conference teams
    if conferences:
        for conf_name, conf_teams in conferences.items():
            honors.all_conference_teams[conf_name] = _select_all_conference(
                conf_name, conf_teams, teams, standings, year
            )

    # Team-level awards
    coy, chaos_k, most_imp = _select_team_awards(standings, prev_season_wins)
    honors.coach_of_year = coy
    honors.chaos_king = chaos_k
    honors.most_improved = most_imp

    return honors
