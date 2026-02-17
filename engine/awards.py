"""
Viperball End-of-Season Awards System

Selection methodology:
- Winners chosen from player rosters using position-weighted attribute ratings
- Team performance context (win%, avg OPI) applied as a 0.88–1.10× multiplier
- Each named trophy has a separate scoring function tuned for its position group
- Freshman eligibility restricted to players whose year == "Freshman"

─────────────────────────────────────────────────────────────────────────────
INDIVIDUAL TROPHIES
─────────────────────────────────────────────────────────────────────────────

  CVL MVP                   – National Player of the Year (all positions eligible).
                              The sport's highest individual honour.  Any position can win.

  Best Zeroback             – Outstanding Zeroback.

  Best Viper                – Outstanding Viper.

  Best Lateral Specialist   – Outstanding lateral specialist.

  Best Defensive Player     – Outstanding defensive player (Lineman or Safety/Keeper).

  Best Kicker               – Outstanding kicker.

  Offensive Player of the Year  – Offensive standout not yet recognised above.
  Defensive Player of the Year  – Defensive standout not yet recognised above.

TEAM-LEVEL HONOURS
  Coach of the Year         – Best coaching performance relative to expectations.
  Most Improved Program     – Biggest win-total gain from previous season.

─────────────────────────────────────────────────────────────────────────────
COLLECTIVE TEAMS
─────────────────────────────────────────────────────────────────────────────

  All-CVL (1st, 2nd, 3rd Team)     – Nine position slots each (see _AA_SLOTS)
  All-CVL Honorable Mention         – Next ~18 players across the same slots
  All-Freshman Team                 – Best first-year players (Freshman only)
  All-Conference (1st & 2nd Team)   – Per conference, two full nine-slot teams

Position slots (all tiers):
    1 Zeroback · 2 Vipers · 3 Halfbacks/Wingbacks · 2 Linemen · 1 Safety/Keeper

Usage:
    from engine.awards import compute_season_awards
    honors = compute_season_awards(season, year, conferences, prev_season_wins)
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
    """A single named award or team-slot selection."""
    award_name: str
    player_name: str
    team_name: str
    position: str
    year_in_school: str   # Freshman / Sophomore / Junior / Senior / Graduate
    overall_rating: int
    reason: str

    def to_dict(self) -> dict:
        return {
            "award_name": self.award_name,
            "player_name": self.player_name,
            "team_name": self.team_name,
            "position": self.position,
            "year_in_school": self.year_in_school,
            "overall_rating": self.overall_rating,
            "reason": self.reason,
        }


@dataclass
class AllAmericanTeam:
    """
    One tier of All-CVL selections.

    team_level: "first" | "second" | "third" | "honorable_mention" | "freshman"
    """
    team_level: str
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
    """
    All-Conference selections for one conference, one tier.

    team_level: "first" | "second"
    """
    conference_name: str
    team_level: str
    year: int
    slots: List[AwardWinner] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "conference_name": self.conference_name,
            "team_level": self.team_level,
            "year": self.year,
            "slots": [w.to_dict() for w in self.slots],
        }


@dataclass
class SeasonHonors:
    """
    Complete end-of-season honours package produced by compute_season_awards().
    Stored in Dynasty.honors_history[year] as a serialised dict.
    """
    year: int

    # Named individual trophies
    individual_awards: List[AwardWinner] = field(default_factory=list)

    # All-CVL tiers
    all_american_first: Optional[AllAmericanTeam] = None
    all_american_second: Optional[AllAmericanTeam] = None
    all_american_third: Optional[AllAmericanTeam] = None
    honorable_mention: Optional[AllAmericanTeam] = None
    all_freshman: Optional[AllAmericanTeam] = None

    # All-Conference: conf_name -> {"first": AllConferenceTeam, "second": AllConferenceTeam}
    all_conference_teams: Dict[str, Dict[str, AllConferenceTeam]] = field(default_factory=dict)

    # Team-level awards
    coach_of_year: str = ""
    most_improved: str = ""

    # ── helpers ──
    def get_award(self, award_name: str) -> Optional[AwardWinner]:
        for a in self.individual_awards:
            if a.award_name == award_name:
                return a
        return None

    def to_dict(self) -> dict:
        ac = {}
        for conf, tiers in self.all_conference_teams.items():
            ac[conf] = {tier: obj.to_dict() for tier, obj in tiers.items()}
        return {
            "year": self.year,
            "individual_awards": [a.to_dict() for a in self.individual_awards],
            "all_american_first":   self.all_american_first.to_dict()  if self.all_american_first  else None,
            "all_american_second":  self.all_american_second.to_dict() if self.all_american_second else None,
            "all_american_third":   self.all_american_third.to_dict()  if self.all_american_third  else None,
            "honorable_mention":    self.honorable_mention.to_dict()   if self.honorable_mention   else None,
            "all_freshman":         self.all_freshman.to_dict()         if self.all_freshman        else None,
            "all_conference_teams": ac,
            "coach_of_year": self.coach_of_year,
            "most_improved": self.most_improved,
        }


# ──────────────────────────────────────────────
# POSITION GROUP CLASSIFIER
# ──────────────────────────────────────────────

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


# ──────────────────────────────────────────────
# SCORING FUNCTIONS
# ──────────────────────────────────────────────

def _player_score(player: Player, team_perf_mult: float = 1.0) -> float:
    pos = player.position.lower()
    if "zeroback" in pos or "zero" in pos:
        raw = (player.speed * 0.9 + player.kicking * 1.2 + player.lateral_skill * 1.1
               + player.awareness * 1.2 + player.stamina * 0.8) / 5.2
    elif "viper" in pos:
        raw = (player.speed * 1.3 + player.lateral_skill * 1.4 + player.agility * 1.2
               + player.hands * 1.0 + player.stamina * 0.8) / 5.7
    elif any(p in pos for p in ["halfback", "wingback", "shiftback"]):
        raw = (player.speed * 1.2 + player.lateral_skill * 1.1 + player.agility * 1.1
               + player.power * 0.9 + player.stamina * 0.9) / 5.2
    elif "lineman" in pos or "line" in pos or "wedge" in pos:
        raw = (player.tackling * 1.6 + player.power * 1.5 + player.stamina * 1.2
               + player.awareness * 0.9) / 5.2
    elif "safety" in pos or "keeper" in pos:
        raw = (player.speed * 1.1 + player.tackling * 1.3 + player.lateral_skill * 1.0
               + player.awareness * 1.3 + player.stamina * 0.9) / 5.6
    else:
        raw = float(player.overall)
    return round(raw * team_perf_mult, 2)


def _national_poy_score(player: Player, team_perf_mult: float = 1.0) -> float:
    """
    CVL MVP scorer — any position eligible.
    Uses overall plus a 'impact' bonus for offensive skill positions.
    """
    base = float(player.overall)
    pos = player.position.lower()
    # Offensive skill positions get a modest recognition boost to match real-world bias
    # but defenders with elite overall CAN win
    if any(p in pos for p in ["zeroback", "zero", "viper", "halfback", "wingback"]):
        base *= 1.04
    return round(base * team_perf_mult, 2)


def _kicker_score(player: Player, team_perf_mult: float = 1.0) -> float:
    raw = (player.kicking * 1.4 + player.kick_power * 1.2
           + player.kick_accuracy * 1.3 + player.awareness * 0.8) / 4.7
    return round(raw * team_perf_mult, 2)


def _lateral_score(player: Player, team_perf_mult: float = 1.0) -> float:
    raw = (player.lateral_skill * 1.5 + player.hands * 1.2
           + player.speed * 1.1 + player.agility * 1.1) / 4.9
    return round(raw * team_perf_mult, 2)


def _defensive_score(player: Player, team_perf_mult: float = 1.0) -> float:
    raw = (player.tackling * 1.5 + player.power * 1.1 + player.speed * 1.0
           + player.awareness * 1.3 + player.stamina * 1.0) / 5.9
    return round(raw * team_perf_mult, 2)


# ──────────────────────────────────────────────
# TEAM PERFORMANCE MULTIPLIER
# ──────────────────────────────────────────────

def _team_perf_mult(team_name: str, standings: dict) -> float:
    record = standings.get(team_name)
    if record is None:
        return 1.0
    mult = 0.88 + record.win_percentage * 0.15 + min(record.avg_opi / 100.0, 1.0) * 0.07
    return round(min(1.10, max(0.88, mult)), 3)


# ──────────────────────────────────────────────
# POSITION SLOT SELECTORS
# ──────────────────────────────────────────────

def _best_in_position(
    teams: Dict[str, Team],
    standings: dict,
    group_filter: str,
    score_fn,
    exclude: set,
    freshman_only: bool = False,
) -> Optional[Tuple[Player, str]]:
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
            if freshman_only and getattr(player, "year", "") != "Freshman":
                continue
            score = score_fn(player, mult)
            if score > best_score:
                best_score = score
                best_pair = (player, team_name)
    return best_pair


# Canonical All-CVL position slots
_AA_SLOTS = [
    ("zeroback", "Zeroback",              _player_score),
    ("viper",    "Viper (1)",             _player_score),
    ("viper",    "Viper (2)",             _player_score),
    ("back",     "Halfback/Wingback (1)", _player_score),
    ("back",     "Halfback/Wingback (2)", _player_score),
    ("back",     "Halfback/Wingback (3)", _player_score),
    ("lineman",  "Lineman (1)",           _player_score),
    ("lineman",  "Lineman (2)",           _player_score),
    ("safety",   "Safety/Keeper",         _player_score),
]


def _select_slots(
    teams: Dict[str, Team],
    standings: dict,
    slot_spec: list,
    exclude: set,
    year: int,
    team_level: str,
    freshman_only: bool = False,
) -> List[AwardWinner]:
    winners = []
    for group, label, score_fn in slot_spec:
        pair = _best_in_position(teams, standings, group, score_fn, exclude, freshman_only)
        if pair:
            player, team_name = pair
            uid = f"{team_name}::{player.name}"
            exclude.add(uid)
            winners.append(AwardWinner(
                award_name=label,
                player_name=player.name,
                team_name=team_name,
                position=player.position,
                year_in_school=getattr(player, "year", ""),
                overall_rating=player.overall,
                reason=f"{team_level.replace('_', ' ').title()} All-CVL",
            ))
    return winners


# ──────────────────────────────────────────────
# NAMED INDIVIDUAL TROPHIES
# ──────────────────────────────────────────────

def _select_individual_awards(
    teams: Dict[str, Team],
    standings: dict,
) -> List[AwardWinner]:

    awards: List[AwardWinner] = []
    seen: set = set()

    def _add(player, team_name, award_name, reason):
        seen.add(f"{team_name}::{player.name}")
        awards.append(AwardWinner(
            award_name=award_name,
            player_name=player.name,
            team_name=team_name,
            position=player.position,
            year_in_school=getattr(player, "year", ""),
            overall_rating=player.overall,
            reason=reason,
        ))

    def _best(group, score_fn, exclude_set=None):
        return _best_in_position(teams, standings, group, score_fn,
                                  exclude_set if exclude_set is not None else seen)

    # ── CVL MVP (national POY — any position) ──────────────────
    best_poy = None
    best_poy_score = -1.0
    for t_name, t in teams.items():
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            if f"{t_name}::{p.name}" in seen:
                continue
            s = _national_poy_score(p, mult)
            if s > best_poy_score:
                best_poy_score = s
                best_poy = (p, t_name)
    if best_poy:
        p, t = best_poy
        _add(p, t, "CVL MVP",
             f"Nation's outstanding collegiate viperball player ({t})")

    # ── Best Zeroback ─────────────────────────────
    pair = _best("zeroback", _player_score)
    if pair:
        _add(pair[0], pair[1], "Best Zeroback",
             f"Nation's outstanding Zeroback ({pair[1]})")

    # ── Best Viper ────────────────────────────────
    pair = _best("viper", _player_score)
    if pair:
        _add(pair[0], pair[1], "Best Viper",
             f"Nation's outstanding Viper ({pair[1]})")

    # ── Best Lateral Specialist ─────────────────
    best_lat = None
    best_lat_score = -1.0
    for t_name, t in teams.items():
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            if _pos_group(p.position) not in {"zeroback", "viper", "back"}:
                continue
            s = _lateral_score(p, mult)
            if s > best_lat_score:
                best_lat_score = s
                best_lat = (p, t_name)
    if best_lat:
        _add(best_lat[0], best_lat[1], "Best Lateral Specialist",
             f"Nation's outstanding lateral specialist ({best_lat[1]})")

    # ── Best Defensive Player (lineman or safety) ──────
    cand_l = _best("lineman", _defensive_score)
    cand_s = _best("safety", _defensive_score)
    if cand_l and cand_s:
        ml = _team_perf_mult(cand_l[1], standings)
        ms = _team_perf_mult(cand_s[1], standings)
        pair = cand_l if _defensive_score(cand_l[0], ml) >= _defensive_score(cand_s[0], ms) else cand_s
    else:
        pair = cand_l or cand_s
    if pair:
        _add(pair[0], pair[1], "Best Defensive Player",
             f"Nation's outstanding defensive player ({pair[1]})")

    # ── Best Kicker (any position) ───────────────────
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
        _add(best_k[0], best_k[1], "Best Kicker",
             f"Nation's outstanding kicker ({best_k[1]})")

    # ── Offensive Player of the Year ──────────────────────────────────────
    off_groups = {"zeroback", "viper", "back"}
    best_off = None
    best_off_score = -1.0
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
        _add(best_off[0], best_off[1], "Offensive Player of the Year",
             f"Dominant offensive force ({best_off[1]})")

    # ── Defensive Player of the Year ──────────────────────────────────────
    def_groups = {"lineman", "safety"}
    best_def = None
    best_def_score = -1.0
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
        _add(best_def[0], best_def[1], "Defensive Player of the Year",
             f"Dominant defensive force ({best_def[1]})")

    return awards


# ──────────────────────────────────────────────
# ALL-CONFERENCE SELECTION (2 teams per conf)
# ──────────────────────────────────────────────

def _select_all_conference_both(
    conference_name: str,
    conf_teams: List[str],
    all_teams: Dict[str, Team],
    standings: dict,
    year: int,
) -> Dict[str, AllConferenceTeam]:
    """Returns {"first": AllConferenceTeam, "second": AllConferenceTeam}."""
    conf_team_objs = {t: all_teams[t] for t in conf_teams if t in all_teams}
    seen: set = set()

    first_slots = _select_slots(conf_team_objs, standings, _AA_SLOTS, seen, year, "first_conference")
    second_slots = _select_slots(conf_team_objs, standings, _AA_SLOTS, seen, year, "second_conference")

    return {
        "first": AllConferenceTeam(
            conference_name=conference_name,
            team_level="first",
            year=year,
            slots=first_slots,
        ),
        "second": AllConferenceTeam(
            conference_name=conference_name,
            team_level="second",
            year=year,
            slots=second_slots,
        ),
    }


# ──────────────────────────────────────────────
# TEAM-LEVEL AWARDS
# ──────────────────────────────────────────────

def _select_team_awards(
    standings: dict,
    prev_season_wins: Dict[str, int] = None,
) -> Tuple[str, str]:
    """Returns (coach_of_year_team, most_improved_team)."""
    sorted_std = sorted(standings.values(), key=lambda r: r.win_percentage, reverse=True)

    # Coach of Year: best win% with a surprise factor component
    coy_scores = {
        r.team_name: r.win_percentage * 0.7 + r.avg_opi * 0.003
        for r in standings.values()
    }
    coy = max(coy_scores, key=coy_scores.get) if coy_scores else ""

    # Most Improved
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
        most_imp = sorted_std[1].team_name if len(sorted_std) > 1 else (sorted_std[0].team_name if sorted_std else "")

    return coy, most_imp


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
    Compute all end-of-season honours for a completed season.

    Args:
        season:            Completed Season with standings and teams
        year:              Season year
        conferences:       conf_name -> [team_names]; used for All-Conference
        prev_season_wins:  team_name -> wins last season; used for Most Improved

    Returns:
        SeasonHonors ready to store in Dynasty.honors_history[year]
    """
    standings = season.standings
    teams = season.teams
    honors = SeasonHonors(year=year)

    # ── Named individual trophies ──────────────────────────────────────────
    honors.individual_awards = _select_individual_awards(teams, standings)

    # ── All-CVL (1st, 2nd, 3rd, Honorable Mention) ────────────────────────
    aa_seen: set = set()

    first_slots = _select_slots(teams, standings, _AA_SLOTS, aa_seen, year, "first")
    honors.all_american_first = AllAmericanTeam(team_level="first", year=year, slots=first_slots)

    second_slots = _select_slots(teams, standings, _AA_SLOTS, aa_seen, year, "second")
    honors.all_american_second = AllAmericanTeam(team_level="second", year=year, slots=second_slots)

    third_slots = _select_slots(teams, standings, _AA_SLOTS, aa_seen, year, "third")
    honors.all_american_third = AllAmericanTeam(team_level="third", year=year, slots=third_slots)

    # Honorable Mention: two more players per slot = 18 total
    hm_slots_spec = _AA_SLOTS * 2   # run the same slot list twice
    hm_slots = _select_slots(teams, standings, hm_slots_spec, aa_seen, year, "honorable_mention")
    honors.honorable_mention = AllAmericanTeam(team_level="honorable_mention", year=year, slots=hm_slots)

    # ── All-Freshman Team ─────────────────────────────────────────────────
    fresh_seen: set = set()
    fresh_slots = _select_slots(teams, standings, _AA_SLOTS, fresh_seen, year, "freshman",
                                freshman_only=True)
    honors.all_freshman = AllAmericanTeam(team_level="freshman", year=year, slots=fresh_slots)

    # ── All-Conference (1st & 2nd per conference) ─────────────────────────
    if conferences:
        for conf_name, conf_teams in conferences.items():
            honors.all_conference_teams[conf_name] = _select_all_conference_both(
                conf_name, conf_teams, teams, standings, year
            )

    # ── Team-level awards ─────────────────────────────────────────────────
    coy, most_imp = _select_team_awards(standings, prev_season_wins)
    honors.coach_of_year = coy
    honors.most_improved = most_imp

    return honors
