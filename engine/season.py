"""
Season Simulation for Viperball Dynasty Mode

Handles:
- Schedule generation (round-robin, conference play, configurable game count)
- Season-long standings
- Weekly poll/rankings
- Playoff brackets
- Season metrics and statistics
- Championship resolution
"""

import json
import random
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path

from engine.game_engine import ViperballEngine, Team, load_team_from_json
from engine.weather import generate_game_weather, describe_conditions
from engine.viperball_metrics import calculate_viperball_metrics
from engine.fast_sim import fast_sim_game


FCS_PREFIXES = [
    "North", "South", "East", "West", "Central", "Upper", "Lower",
    "Greater", "New", "Old", "Fort", "Lake", "Mount", "River",
    "Saint", "Grand", "Little", "Big", "Prairie", "Desert",
]
FCS_ROOTS = [
    "Valley", "Ridge", "Creek", "Springs", "Falls", "Plains",
    "Bluff", "Hollow", "Crossing", "Harbor", "Haven", "Grove",
    "Meadow", "Summit", "Pines", "Oaks", "Willows", "Brook",
    "Field", "Dale", "Glen", "Hill", "Landing", "Bend",
]
FCS_SUFFIXES = [
    "State", "A&M", "Tech", "College", "University", "Institute",
    "Polytechnic", "Seminary", "Academy",
]
FCS_MASCOTS = [
    "Wolves", "Hawks", "Bears", "Wildcats", "Panthers", "Eagles",
    "Stallions", "Coyotes", "Owls", "Foxes", "Ravens", "Jaguars",
    "Rams", "Falcons", "Bobcats", "Bison", "Hornets", "Badgers",
    "Cougars", "Mustangs", "Lynx", "Otters", "Scorpions", "Herons",
]

_fcs_used_names: set = set()


def generate_fcs_team_name() -> Tuple[str, str]:
    """Generate a unique fictional FCS/lower-division school name and mascot."""
    for _ in range(200):
        style = random.choice(["prefix_root", "root_suffix", "prefix_root_suffix"])
        if style == "prefix_root":
            name = f"{random.choice(FCS_PREFIXES)} {random.choice(FCS_ROOTS)}"
        elif style == "root_suffix":
            name = f"{random.choice(FCS_ROOTS)} {random.choice(FCS_SUFFIXES)}"
        else:
            name = f"{random.choice(FCS_PREFIXES)} {random.choice(FCS_ROOTS)} {random.choice(FCS_SUFFIXES)}"
        if name not in _fcs_used_names:
            _fcs_used_names.add(name)
            mascot = random.choice(FCS_MASCOTS)
            return name, mascot
    num = random.randint(100, 999)
    name = f"Division II School #{num}"
    return name, "Generals"


def generate_fcs_team(name: str, mascot: str) -> Team:
    """Generate a weak FCS/lower-division Team object for schedule-fill games.

    These are throwaway teams with low ratings — the CVL team should win
    comfortably, just like real FBS vs FCS matchups.
    """
    from engine.game_engine import Player, derive_halo

    positions = [
        ("Viper", True), ("Viper", False), ("Viper", False),
        ("Zeroback", False), ("Zeroback", False), ("Zeroback", False),
        ("Halfback", False), ("Halfback", False), ("Halfback", False), ("Halfback", False),
        ("Wingback", False), ("Wingback", False), ("Wingback", False), ("Wingback", False),
        ("Slotback", False), ("Slotback", False), ("Slotback", False), ("Slotback", False),
        ("Keeper", False), ("Keeper", False), ("Keeper", False),
        ("Offensive Line", False), ("Offensive Line", False), ("Offensive Line", False),
        ("Offensive Line", False), ("Offensive Line", False), ("Offensive Line", False),
        ("Offensive Line", False), ("Offensive Line", False),
        ("Defensive Line", False), ("Defensive Line", False), ("Defensive Line", False),
        ("Defensive Line", False), ("Defensive Line", False), ("Defensive Line", False),
        ("Defensive Line", False),
    ]

    first_names = [
        "Anna", "Beth", "Clara", "Diana", "Elena", "Fiona", "Grace", "Holly",
        "Iris", "Julia", "Kate", "Lily", "Maya", "Nina", "Olivia", "Paige",
        "Quinn", "Rosa", "Sara", "Tina", "Uma", "Val", "Wendy", "Xena",
        "Yara", "Zoe", "Amber", "Brooke", "Celia", "Dawn", "Eve", "Faith",
        "Gwen", "Hope", "Ivy",
    ]
    last_names = [
        "Smith", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor",
        "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Garcia",
        "Clark", "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "King",
        "Wright", "Lopez", "Hill", "Scott", "Green", "Adams", "Baker",
        "Nelson", "Carter", "Mitchell", "Perez", "Roberts",
    ]

    is_upset_team = random.randint(1, 100) == 1
    if is_upset_team:
        stat_low, stat_high = 45, 70
    else:
        stat_low, stat_high = 10, 30

    players = []
    used_nums: set = set()
    for i, (pos, is_viper) in enumerate(positions):
        num = 1 if is_viper and i == 0 else None
        while num is None or num in used_nums:
            num = random.randint(2, 99)
        used_nums.add(num)

        base = random.randint(stat_low, stat_high)
        p_name = f"{random.choice(first_names)} {random.choice(last_names)}"
        year = random.choice(["Freshman", "Sophomore", "Junior", "Senior"])

        players.append(Player(
            number=num,
            name=p_name,
            position=pos,
            speed=base + random.randint(-5, 10),
            stamina=base + random.randint(-5, 10),
            kicking=base + random.randint(-10, 5),
            lateral_skill=base + random.randint(-5, 5),
            tackling=base + random.randint(-5, 10),
            agility=base + random.randint(-5, 5),
            power=base + random.randint(-5, 5),
            awareness=base + random.randint(-5, 5),
            hands=base + random.randint(-5, 5),
            kick_power=base + random.randint(-10, 5),
            kick_accuracy=base + random.randint(-10, 5),
            archetype="",
            year=year,
        ))

    abbrev = "".join(w[0] for w in name.split()[:3]).upper()
    avg_speed = sum(p.speed for p in players) // len(players)
    avg_stamina = sum(p.stamina for p in players) // len(players)
    kicking = sum(p.kicking for p in players) // len(players)
    lateral = sum(p.lateral_skill for p in players) // len(players)
    defense = sum(p.tackling for p in players) // len(players)

    prestige = random.randint(30, 55) if is_upset_team else random.randint(5, 15)

    team = Team(
        name=name,
        abbreviation=abbrev,
        mascot=mascot,
        players=players,
        avg_speed=avg_speed,
        avg_stamina=avg_stamina,
        kicking_strength=kicking,
        lateral_proficiency=lateral,
        defensive_strength=defense,
        offense_style="balanced",
        defense_style="base_defense",
        st_scheme="aces",
        prestige=prestige,
    )
    h_off, h_def = derive_halo(prestige)
    team.halo_offense = h_off
    team.halo_defense = h_def
    return team


@dataclass
class TeamRecord:
    """Season record for a single team"""
    team_name: str
    wins: int = 0
    losses: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    conference: str = ""

    # Fan-friendly analytics accumulators
    total_team_rating: float = 0.0   # Team Rating (0-100, like SP+/Madden)
    total_ppd: float = 0.0           # Points Per Drive
    total_conversion_pct: float = 0.0  # 3rd+ down conversion %
    total_lateral_pct: float = 0.0   # Lateral chain completion %
    total_explosive: float = 0.0     # Explosive plays (15+ yards)
    total_to_margin: float = 0.0     # Turnover margin
    total_avg_start: float = 0.0     # Avg starting field position
    games_played: int = 0

    # Defensive impact season accumulators
    total_bonus_possessions: int = 0
    total_bonus_scores: int = 0
    total_turnovers_forced_all: int = 0  # all TOs (fumbles + TOD + INTs)
    total_defensive_stops: int = 0
    total_opponent_drives: int = 0

    # Legacy accumulators (kept for backward compat with saved data)
    total_opi: float = 0.0
    total_territory: float = 0.0
    total_pressure: float = 0.0
    total_chaos: float = 0.0
    total_kicking: float = 0.0
    total_drive_quality: float = 0.0
    total_turnover_impact: float = 0.0

    conf_wins: int = 0
    conf_losses: int = 0

    offense_style: str = "balanced"
    defense_style: str = "swarm"

    # V2.4: Defensive prestige tracking
    # Tracks INTs forced per game (rolling window) for No-Fly Zone status
    defensive_ints_history: list = field(default_factory=list)
    no_fly_zone: bool = False  # True if team earned "No-Fly Zone" status

    # V2.5: Additional defensive prestige tiers
    # Brick Wall: hold opponents under 200 rushing yards 3 consecutive games
    rushing_yards_allowed_history: list = field(default_factory=list)
    brick_wall: bool = False

    # Turnover Machine: force 4+ turnovers in 3 consecutive games
    turnovers_forced_history: list = field(default_factory=list)
    turnover_machine: bool = False

    # DYE (Delta Yards Efficiency) season accumulators
    dye_penalized_drives: int = 0
    dye_penalized_yards: int = 0
    dye_penalized_scores: int = 0
    dye_boosted_drives: int = 0
    dye_boosted_yards: int = 0
    dye_boosted_scores: int = 0
    dye_neutral_drives: int = 0
    dye_neutral_yards: int = 0
    dye_neutral_scores: int = 0
    dye_total_delta_yards: int = 0
    dye_opponent_boosted_scores: int = 0
    dye_wins_despite_penalty: int = 0
    bonus_poss_total: int = 0
    bonus_poss_scores: int = 0
    bonus_poss_yards: int = 0
    opponent_bonus_poss_scores: int = 0

    def add_game_result(self, won: bool, points_for: float, points_against: float,
                        metrics: Dict, is_conference_game: bool = False,
                        defensive_ints: int = 0,
                        rushing_yards_allowed: int = 0,
                        turnovers_forced: int = 0,
                        dye_data: Optional[Dict] = None,
                        opponent_dye_data: Optional[Dict] = None,
                        bonus_data: Optional[Dict] = None,
                        opponent_bonus_data: Optional[Dict] = None):
        if won:
            self.wins += 1
            if is_conference_game:
                self.conf_wins += 1
        else:
            self.losses += 1
            if is_conference_game:
                self.conf_losses += 1

        self.points_for += points_for
        self.points_against += points_against

        # Accumulate fan-friendly metrics
        self.total_team_rating += metrics.get('team_rating', metrics.get('opi', 0.0))
        self.total_ppd += metrics.get('ppd', metrics.get('drive_quality', 0.0))
        self.total_conversion_pct += metrics.get('conversion_pct', metrics.get('pressure_index', 0.0))
        self.total_lateral_pct += metrics.get('lateral_pct', 0.0)
        self.total_explosive += metrics.get('explosive_plays', 0.0)
        self.total_to_margin += metrics.get('to_margin', 0.0)
        self.total_avg_start += metrics.get('avg_start', 25.0)

        # Defensive impact accumulators
        def_impact = metrics.get('defensive_impact', {})
        self.total_bonus_possessions += def_impact.get('bonus_possessions', 0)
        self.total_bonus_scores += def_impact.get('bonus_scores', 0)
        self.total_turnovers_forced_all += def_impact.get('turnovers_forced', 0)
        self.total_defensive_stops += def_impact.get('defensive_stops', 0)
        self.total_opponent_drives += def_impact.get('opponent_drives', 0)

        # Legacy accumulators (for backward compat)
        self.total_opi += metrics.get('team_rating', metrics.get('opi', 0.0))
        self.total_territory += metrics.get('territory_rating', 0.0)
        self.total_pressure += metrics.get('pressure_index', 0.0)
        self.total_chaos += metrics.get('chaos_factor', 0.0)
        self.total_kicking += metrics.get('kicking_efficiency', 0.0)
        self.total_drive_quality += metrics.get('drive_quality', 0.0)
        self.total_turnover_impact += metrics.get('turnover_impact', 0.0)
        self.games_played += 1

        # V2.4: Defensive prestige — track INTs forced and check for No-Fly Zone
        if defensive_ints > 0 or self.defensive_ints_history:
            self.defensive_ints_history.append(defensive_ints)
            self._check_no_fly_zone()

        # V2.5: Track additional defensive prestige tiers
        self.rushing_yards_allowed_history.append(rushing_yards_allowed)
        self._check_brick_wall()
        self.turnovers_forced_history.append(turnovers_forced)
        self._check_turnover_machine()

        if dye_data:
            pen = dye_data.get("penalty_kill", {})
            bst = dye_data.get("power_play", {})
            neu = dye_data.get("neutral", {})
            self.dye_penalized_drives += pen.get("count", 0)
            self.dye_penalized_yards += pen.get("total_yards", 0)
            self.dye_penalized_scores += pen.get("scores", 0)
            self.dye_boosted_drives += bst.get("count", 0)
            self.dye_boosted_yards += bst.get("total_yards", 0)
            self.dye_boosted_scores += bst.get("scores", 0)
            self.dye_neutral_drives += neu.get("count", 0)
            self.dye_neutral_yards += neu.get("total_yards", 0)
            self.dye_neutral_scores += neu.get("scores", 0)

        if opponent_dye_data:
            opp_bst = opponent_dye_data.get("power_play", {})
            self.dye_opponent_boosted_scores += opp_bst.get("scores", 0)

        if dye_data and won:
            pen = dye_data.get("penalty_kill", {})
            if pen.get("count", 0) > 0:
                self.dye_wins_despite_penalty += 1

        self.dye_total_delta_yards += metrics.get("delta_yards_raw", 0)

        if bonus_data:
            self.bonus_poss_total += bonus_data.get("count", 0)
            self.bonus_poss_scores += bonus_data.get("scores", 0)
            self.bonus_poss_yards += bonus_data.get("yards", 0)
        if opponent_bonus_data:
            self.opponent_bonus_poss_scores += opponent_bonus_data.get("scores", 0)

    # ── Fan-friendly metric averages ──

    @property
    def avg_team_rating(self) -> float:
        return self.total_team_rating / self.games_played if self.games_played > 0 else 0.0

    @property
    def avg_ppd(self) -> float:
        return self.total_ppd / self.games_played if self.games_played > 0 else 0.0

    @property
    def avg_conversion_pct(self) -> float:
        return self.total_conversion_pct / self.games_played if self.games_played > 0 else 0.0

    @property
    def avg_lateral_pct(self) -> float:
        return self.total_lateral_pct / self.games_played if self.games_played > 0 else 0.0

    @property
    def avg_explosive(self) -> float:
        return self.total_explosive / self.games_played if self.games_played > 0 else 0.0

    @property
    def avg_to_margin(self) -> float:
        return self.total_to_margin / self.games_played if self.games_played > 0 else 0.0

    @property
    def avg_start_position(self) -> float:
        return self.total_avg_start / self.games_played if self.games_played > 0 else 25.0

    # ── Defensive impact season averages ──

    @property
    def avg_bonus_possessions(self) -> float:
        return self.total_bonus_possessions / self.games_played if self.games_played > 0 else 0.0

    @property
    def bonus_conv_rate(self) -> float:
        return round(self.total_bonus_scores / max(1, self.total_bonus_possessions) * 100, 1) if self.total_bonus_possessions else 0.0

    @property
    def avg_turnovers_forced(self) -> float:
        return self.total_turnovers_forced_all / self.games_played if self.games_played > 0 else 0.0

    @property
    def stop_rate(self) -> float:
        return round(self.total_defensive_stops / max(1, self.total_opponent_drives) * 100, 1) if self.total_opponent_drives else 0.0

    # ── Legacy property aliases (backward compat) ──

    @property
    def avg_opi(self) -> float:
        return self.avg_team_rating

    @property
    def avg_territory(self) -> float:
        return self.total_territory / self.games_played if self.games_played > 0 else 0.0

    @property
    def avg_pressure(self) -> float:
        return self.total_pressure / self.games_played if self.games_played > 0 else 0.0

    @property
    def avg_chaos(self) -> float:
        return self.total_chaos / self.games_played if self.games_played > 0 else 0.0

    @property
    def avg_kicking(self) -> float:
        return self.total_kicking / self.games_played if self.games_played > 0 else 0.0

    @property
    def avg_drive_quality(self) -> float:
        return self.total_drive_quality / self.games_played if self.games_played > 0 else 0.0

    @property
    def avg_turnover_impact(self) -> float:
        return self.total_turnover_impact / self.games_played if self.games_played > 0 else 0.0

    @property
    def dye_season_summary(self) -> Dict:
        pen_ypd = round(self.dye_penalized_yards / max(1, self.dye_penalized_drives), 1) if self.dye_penalized_drives else 0.0
        bst_ypd = round(self.dye_boosted_yards / max(1, self.dye_boosted_drives), 1) if self.dye_boosted_drives else 0.0
        neu_ypd = round(self.dye_neutral_yards / max(1, self.dye_neutral_drives), 1) if self.dye_neutral_drives else 0.0
        pen_score_rate = round(self.dye_penalized_scores / max(1, self.dye_penalized_drives) * 100, 1) if self.dye_penalized_drives else 0.0
        bst_score_rate = round(self.dye_boosted_scores / max(1, self.dye_boosted_drives) * 100, 1) if self.dye_boosted_drives else 0.0
        neu_score_rate = round(self.dye_neutral_scores / max(1, self.dye_neutral_drives) * 100, 1) if self.dye_neutral_drives else 0.0

        baseline = neu_ypd if neu_ypd > 0 else pen_ypd
        dye_pen = round(pen_ypd / baseline, 2) if baseline > 0 and self.dye_penalized_drives > 0 else None
        dye_bst = round(bst_ypd / baseline, 2) if baseline > 0 and self.dye_boosted_drives > 0 else None

        net_impact = 0
        if neu_ypd > 0:
            net_impact += (pen_ypd - neu_ypd) * self.dye_penalized_drives
            net_impact += (bst_ypd - neu_ypd) * self.dye_boosted_drives
        net_impact = round(net_impact, 0)

        # Season Mess Rate: PP% - Kill Rate
        if self.dye_boosted_drives > 0 and self.dye_penalized_drives > 0:
            season_mess_rate = round(bst_score_rate - pen_score_rate, 1)
        else:
            season_mess_rate = None

        return {
            "penalty_kill": {"drives": self.dye_penalized_drives, "yards": self.dye_penalized_yards,
                             "scores": self.dye_penalized_scores, "ypd": pen_ypd, "score_rate": pen_score_rate},
            "power_play": {"drives": self.dye_boosted_drives, "yards": self.dye_boosted_yards,
                           "scores": self.dye_boosted_scores, "ypd": bst_ypd, "score_rate": bst_score_rate},
            "neutral": {"drives": self.dye_neutral_drives, "yards": self.dye_neutral_yards,
                        "scores": self.dye_neutral_scores, "ypd": neu_ypd, "score_rate": neu_score_rate},
            "pk_efficiency": dye_pen,
            "pp_efficiency": dye_bst,
            "mess_rate": season_mess_rate,
            "net_yard_impact": net_impact,
            "total_delta_yards": self.dye_total_delta_yards,
            "opponent_power_play_scores": self.dye_opponent_boosted_scores,
            "wins_despite_penalty": self.dye_wins_despite_penalty,
            "bonus_poss": {"total": self.bonus_poss_total, "scores": self.bonus_poss_scores, "yards": self.bonus_poss_yards},
            "opponent_bonus_scores": self.opponent_bonus_poss_scores,
        }

    @property
    def win_percentage(self) -> float:
        total_games = self.wins + self.losses
        return self.wins / total_games if total_games > 0 else 0.0

    @property
    def conf_win_percentage(self) -> float:
        total = self.conf_wins + self.conf_losses
        return self.conf_wins / total if total > 0 else 0.0

    @property
    def point_differential(self) -> float:
        total_games = self.wins + self.losses
        return (self.points_for - self.points_against) / total_games if total_games > 0 else 0.0

    def _check_no_fly_zone(self):
        """V2.4: Check if team has earned No-Fly Zone defensive prestige.

        If a team records 2+ interceptions in 3 consecutive games, they earn
        the "No-Fly Zone" status for the rest of the season.

        Effect: Opposing Zerobacks get a "Rattled" modifier (-5% accuracy)
        when attempting deep kick passes against this defense.

        Once earned, No-Fly Zone is permanent for the season — dominance
        doesn't expire.
        """
        if self.no_fly_zone:
            return  # Already earned, permanent

        history = self.defensive_ints_history
        if len(history) < 3:
            return

        # Check the last 3 games
        last_three = history[-3:]
        if all(ints >= 2 for ints in last_three):
            self.no_fly_zone = True

    def _check_brick_wall(self):
        """V2.5: Check if team has earned Brick Wall defensive prestige.

        If a team holds opponents under 200 rushing yards in 3 consecutive
        games, they earn "Brick Wall" status for the rest of the season.

        Effect: Opposing run plays get -8% yardage center (applied in engine
        as a multiplicative modifier on run-family plays).
        """
        if self.brick_wall:
            return

        history = self.rushing_yards_allowed_history
        if len(history) < 3:
            return

        last_three = history[-3:]
        if all(yards < 200 for yards in last_three):
            self.brick_wall = True

    def _check_turnover_machine(self):
        """V2.5: Check if team has earned Turnover Machine defensive prestige.

        If a team forces 4+ turnovers in 3 consecutive games, they earn
        "Turnover Machine" status for the rest of the season.

        Effect: +3% fumble probability on all opposing ball carriers and
        +2% interception chance on kick passes.
        """
        if self.turnover_machine:
            return

        history = self.turnovers_forced_history
        if len(history) < 3:
            return

        last_three = history[-3:]
        if all(to >= 4 for to in last_three):
            self.turnover_machine = True


@dataclass
class PollRanking:
    """A single team's poll ranking for a given week"""
    rank: int
    team_name: str
    record: str
    conference: str
    poll_score: float
    prev_rank: Optional[int] = None
    power_index: float = 0.0
    quality_wins: int = 0
    sos_rank: int = 0
    bid_type: str = ""

    @property
    def rank_change(self) -> Optional[int]:
        if self.prev_rank is None:
            return None
        return self.prev_rank - self.rank


@dataclass
class WeeklyPoll:
    """Complete poll for a single week"""
    week: int
    rankings: List[PollRanking] = field(default_factory=list)


@dataclass
class Game:
    """Single game in the season"""
    week: int
    home_team: str
    away_team: str
    home_score: Optional[float] = None
    away_score: Optional[float] = None
    completed: bool = False
    is_conference_game: bool = False
    is_rivalry_game: bool = False
    is_fcs_game: bool = False

    home_metrics: Optional[Dict] = None
    away_metrics: Optional[Dict] = None
    full_result: Optional[Dict] = None


BOWL_WORD_BANKS = {
    "concepts": [
        "Horizon", "Keystone", "Summit", "Meridian", "Pioneer", "Union",
        "Heritage", "Legacy", "Vanguard", "Frontier", "Catalyst", "Apex",
        "Commonwealth", "Founders", "Iron", "Copper", "Granite", "Harbor",
        "Prairie", "Lakes", "River", "Delta", "Corridor", "Heartland",
    ],
    "places": [
        "Great Lakes", "Rust Belt", "Yankee", "Prairie", "Crossroads",
        "Motor City", "Steel City", "River Valley", "Lakefront", "Capital",
        "Heartland", "Coastal", "Inland", "Metro", "Tri-State", "Border",
        "Plains", "Peninsula",
    ],
    "descriptors_premier": ["Classic", "Crown", "Showcase", "Championship"],
    "descriptors_major": ["Challenge", "Cup", "Series", "Trophy"],
    "descriptors_standard": ["Invitational", "Shield", "Clash"],
    "objects": [
        "Lantern", "Anchor", "Rail", "Forge", "Mill", "Beacon", "Bridge",
        "Line", "Yard", "Depot", "Gridiron", "Banner", "Torch", "Spire",
    ],
}


def generate_bowl_names(count: int, tiers: Optional[List[int]] = None) -> List[str]:
    """Generate unique random bowl names using word banks, with tier-appropriate descriptors."""
    banks = BOWL_WORD_BANKS
    used = set()
    names = []

    for i in range(count):
        tier = tiers[i] if tiers and i < len(tiers) else 3
        if tier == 1:
            descriptors = banks["descriptors_premier"]
        elif tier == 2:
            descriptors = banks["descriptors_major"]
        else:
            descriptors = banks["descriptors_standard"]

        if tier <= 2:
            patterns = ["region_desc", "concept_desc"]
        else:
            patterns = ["region_desc", "concept_object", "place", "concept"]

        for _ in range(50):
            pattern = random.choice(patterns)
            if pattern == "region_desc":
                name = f"{random.choice(banks['places'])} {random.choice(descriptors)}"
            elif pattern == "concept_desc":
                name = f"{random.choice(banks['concepts'])} {random.choice(descriptors)}"
            elif pattern == "concept_object":
                name = f"{random.choice(banks['concepts'])} {random.choice(banks['objects'])} Bowl"
            elif pattern == "place":
                name = f"{random.choice(banks['places'])} Bowl"
            else:
                name = f"{random.choice(banks['concepts'])} Bowl"

            if name not in used:
                used.add(name)
                names.append(name)
                break
        else:
            names.append(f"Bowl Game {i + 1}")

    return names


BOWL_TIERS = {1: "Premier", 2: "Major", 3: "Standard"}


def get_recommended_bowl_count(league_size: int, playoff_size: int) -> int:
    if league_size <= 15:
        return 0
    remaining = league_size - playoff_size
    if remaining < 4:
        return 0
    table = {
        (24, 4): 4, (24, 8): 2, (24, 12): 1, (24, 16): 0,
        (40, 4): 6, (40, 8): 4, (40, 12): 3, (40, 16): 2,
        (60, 4): 8, (60, 8): 6, (60, 12): 5, (60, 16): 4,
        (80, 4): 10, (80, 8): 8, (80, 12): 6, (80, 16): 5,
        (100, 4): 12, (100, 8): 10, (100, 12): 8, (100, 16): 6,
    }
    best = 2
    for (sz, ps), bc in sorted(table.items()):
        if league_size <= sz and playoff_size <= ps:
            best = bc
            break
    return min(best, remaining // 2)


MAX_CONFERENCE_GAMES = 8  # hard cap on conference games per team per season


def get_non_conference_slots(
    games_per_team: int,
    conference_size: int,
) -> int:
    """Calculate how many non-conference game slots a team has.

    Conference games are capped at MAX_CONFERENCE_GAMES (9). If the conference
    round-robin is smaller than that cap, conference games = conf_size - 1.
    All remaining game slots are non-conference.

    Args:
        games_per_team: Total regular-season games each team plays.
        conference_size: Number of teams in the team's conference (including itself).

    Returns:
        Number of non-conference game slots available.
    """
    if games_per_team <= 0:
        return 0
    conf_opponents = conference_size - 1
    conf_games = min(conf_opponents, MAX_CONFERENCE_GAMES)
    return max(0, games_per_team - conf_games)


# Prestige tier thresholds for non-conference matchup display
PRESTIGE_TIERS = {
    "elite": 80,      # 80-99: top-tier programs
    "strong": 60,      # 60-79: solid programs
    "mid": 40,         # 40-59: mid-tier
    "low": 20,         # 20-39: lower programs
    "cupcake": 0,       # 0-19: cupcake / buy-game territory
}


def classify_prestige_tier(prestige: int) -> str:
    """Return a label for the prestige tier."""
    if prestige >= PRESTIGE_TIERS["elite"]:
        return "elite"
    elif prestige >= PRESTIGE_TIERS["strong"]:
        return "strong"
    elif prestige >= PRESTIGE_TIERS["mid"]:
        return "mid"
    elif prestige >= PRESTIGE_TIERS["low"]:
        return "low"
    return "cupcake"


def prestige_from_archetype(archetype_key: str) -> int:
    """Return a representative prestige value for a program archetype.

    Uses the midpoint of the archetype's prestige_range.
    """
    try:
        from scripts.generate_rosters import PROGRAM_ARCHETYPES
        arch = PROGRAM_ARCHETYPES.get(archetype_key)
        if arch:
            lo, hi = arch["prestige_range"]
            return (lo + hi) // 2
    except ImportError:
        pass
    return 50


def estimate_team_prestige_from_roster(team: "Team") -> int:
    """Estimate a rough prestige score from average player overall.

    Used in single-season mode where no dynasty history exists.
    Maps average team overall (full 10-100 range) to a 10-99 prestige scale.
    """
    if not team.players:
        return 50
    avg_ovr = sum(p.overall for p in team.players) / len(team.players)
    prestige = int(avg_ovr * 0.9 + 5)
    return max(10, min(99, prestige))


STATE_TO_REGION = {
    "CT": "Northeast", "DE": "Northeast", "MA": "Northeast", "MD": "Northeast",
    "ME": "Northeast", "NH": "Northeast", "NJ": "Northeast", "NY": "Northeast",
    "PA": "Northeast", "RI": "Northeast", "VT": "Northeast", "DC": "Northeast",
    "AL": "Southeast", "AR": "Southeast", "FL": "Southeast", "GA": "Southeast",
    "KY": "Southeast", "LA": "Southeast", "MS": "Southeast", "NC": "Southeast",
    "SC": "Southeast", "TN": "Southeast", "VA": "Southeast", "WV": "Southeast",
    "IA": "Midwest", "IL": "Midwest", "IN": "Midwest", "KS": "Midwest",
    "MI": "Midwest", "MN": "Midwest", "MO": "Midwest", "NE": "Midwest",
    "ND": "Midwest", "OH": "Midwest", "OK": "Midwest", "SD": "Midwest", "WI": "Midwest",
    "AZ": "West", "CA": "West", "CO": "West", "HI": "West", "ID": "West",
    "MT": "West", "NM": "West", "NV": "West", "OR": "West", "UT": "West",
    "WA": "West", "WY": "West",
    "TX": "Texas",
    "AK": "West",
    "AB": "Canada", "BC": "Canada", "MB": "Canada", "ON": "Canada",
    "QC": "Canada", "SK": "Canada", "NS": "Canada", "NB": "Canada",
    "PE": "Canada", "NL": "Canada",
}


def get_available_non_conference_opponents(
    team_name: str,
    all_teams: Dict[str, "Team"],
    conferences: Dict[str, List[str]],
    team_conferences: Dict[str, str],
    team_prestige: Optional[Dict[str, int]] = None,
    team_states: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """Get a list of available non-conference opponents for a team.

    Returns a list of dicts with keys: name, conference, prestige, tier, overall, state, region.
    Sorted by prestige descending (best opponents first).
    """
    my_conf = team_conferences.get(team_name, "")
    opponents = []
    for opp_name, opp_team in all_teams.items():
        if opp_name == team_name:
            continue
        opp_conf = team_conferences.get(opp_name, "")
        if opp_conf and opp_conf == my_conf:
            continue  # Same conference — skip
        if team_prestige and opp_name in team_prestige:
            prestige = team_prestige[opp_name]
        else:
            prestige = estimate_team_prestige_from_roster(opp_team)
        opp_state = (team_states or {}).get(opp_name, "")
        opp_region = STATE_TO_REGION.get(opp_state, "Other")
        opponents.append({
            "name": opp_name,
            "conference": opp_conf,
            "prestige": prestige,
            "tier": classify_prestige_tier(prestige),
            "overall": round(sum(p.overall for p in opp_team.players) / max(1, len(opp_team.players))),
            "state": opp_state,
            "region": opp_region,
        })
    opponents.sort(key=lambda x: x["prestige"], reverse=True)
    return opponents


# NIL bonus for buy games (low-prestige team plays at a high-prestige team)
BUY_GAME_NIL_BONUS = 50_000  # flat NIL pool bonus for playing a buy game


def is_buy_game(team_prestige: int, opponent_prestige: int) -> bool:
    """A buy game is when a lower-tier team plays a much higher-prestige team."""
    return (opponent_prestige - team_prestige) >= 25


@dataclass
class BowlGame:
    name: str
    tier: int
    game: Game
    team_1_seed: int = 0
    team_2_seed: int = 0
    team_1_record: str = ""
    team_2_record: str = ""


@dataclass
class Season:
    """Complete season simulation"""
    name: str
    teams: Dict[str, Team]
    schedule: List[Game] = field(default_factory=list)
    standings: Dict[str, TeamRecord] = field(default_factory=dict)

    style_configs: Dict[str, Dict[str, str]] = field(default_factory=dict)

    conferences: Dict[str, List[str]] = field(default_factory=dict)
    team_conferences: Dict[str, str] = field(default_factory=dict)

    # Optional: map team name -> US state for geo-aware weather generation
    team_states: Dict[str, str] = field(default_factory=dict)

    weekly_polls: List[WeeklyPoll] = field(default_factory=list)

    playoff_bracket: List[Game] = field(default_factory=list)
    champion: Optional[str] = None
    bowl_games: List[BowlGame] = field(default_factory=list)

    rivalries: Dict[str, Dict[str, Optional[str]]] = field(default_factory=dict)

    # Coaching staffs: team_name -> { role -> CoachCard }
    coaching_staffs: Dict[str, dict] = field(default_factory=dict)

    # FCS/lower-division teams generated for schedule fill (name -> mascot)
    fcs_teams: Dict[str, str] = field(default_factory=dict)

    # Injury tracker — when set, injuries affect game simulation
    injury_tracker: Optional[object] = None

    # Human-controlled teams — fast-sim skips these games
    human_teams: List[str] = field(default_factory=list)

    def __post_init__(self):
        for team_name, team in self.teams.items():
            style_config = self.style_configs.get(team_name, {})
            offense_style = style_config.get('offense_style', 'balanced')
            defense_style = style_config.get('defense_style', 'swarm')
            conf = self.team_conferences.get(team_name, "")

            self.standings[team_name] = TeamRecord(
                team_name=team_name,
                offense_style=offense_style,
                defense_style=defense_style,
                conference=conf
            )

    def generate_schedule(
        self,
        games_per_team: int = 0,
        conference_weight: float = 0.6,
        non_conf_weeks: int = 3,
        pinned_matchups: Optional[List[Tuple[str, str]]] = None,
        dynasty_year: Optional[int] = None,
    ):
        """
        Generate a season schedule with configurable game count.

        Args:
            games_per_team: Number of games each team plays. 0 = full round-robin.
            conference_weight: Proportion of games that should be conference games (0.0-1.0).
                             Only applies when conferences exist and games_per_team > 0.
            non_conf_weeks: Number of early weeks reserved for non-conference games (1-4).
            pinned_matchups: Optional list of (home, away) tuples for user-selected
                           non-conference games. These are guaranteed to appear in the schedule.
            dynasty_year: If set, home/away for recurring matchups flips deterministically
                         each year so opponents alternate venues.
        """
        team_names = list(self.teams.keys())
        num_teams = len(team_names)

        if games_per_team <= 0 or games_per_team >= num_teams - 1:
            self._generate_round_robin(team_names, dynasty_year=dynasty_year)
        else:
            self._generate_partial_schedule(
                team_names, games_per_team, conference_weight,
                pinned_matchups=pinned_matchups or [],
                dynasty_year=dynasty_year,
            )

        self._assign_weeks_by_type(non_conf_weeks)
        self._mark_rivalry_games()

    @staticmethod
    def _round_robin_rounds(team_list: List[str]) -> List[List[Tuple[str, str]]]:
        """Generate complete round-robin rounds using the circle method.

        Returns a list of rounds, where each round is a list of (team_a, team_b)
        pairs.  Every team plays exactly once per round (with a bye round for
        odd-sized conferences).
        """
        teams = list(team_list)
        n = len(teams)
        if n < 2:
            return []
        use_bye = n % 2 == 1
        if use_bye:
            teams.append("__BYE__")
            n += 1

        fixed = teams[0]
        rotating = teams[1:]
        rounds = []
        for r in range(n - 1):
            round_pairs = []
            current = [fixed] + rotating
            for i in range(n // 2):
                t1, t2 = current[i], current[n - 1 - i]
                if t1 != "__BYE__" and t2 != "__BYE__":
                    round_pairs.append(tuple(sorted([t1, t2])))
            rounds.append(round_pairs)
            rotating = [rotating[-1]] + rotating[:-1]
        return rounds

    @staticmethod
    def _balanced_conference_pairs(
        team_list: List[str],
        target_per_team: int,
        already_scheduled: set,
        existing_conf_counts: dict,
    ) -> List[Tuple[str, str]]:
        """Build a balanced set of conference pairs using the round-dropping method.

        Algorithm (works for any conference size N, target K):
          1. Generate a full round-robin (circle method, ghost team for odd N).
             This produces N-1 (even) or N (odd) rounds.
          2. If K >= opponents, use full round-robin.
          3. Otherwise, keep exactly K rounds and drop the rest.
             Dropping full rounds guarantees every team loses exactly one
             opponent per dropped round, preserving perfect balance.
          4. For odd N, one team has a bye each round. Keeping K rounds means
             each team plays in K or K-1 of them (depending on whether their
             bye round was kept). A greedy patch fills any 1-game shortfalls.
        """
        needed = {}
        for t in team_list:
            already = existing_conf_counts.get(t, 0)
            needed[t] = max(0, target_per_team - already)

        if max(needed.values(), default=0) == 0:
            return []

        n = len(team_list)
        if n - 1 <= target_per_team:
            result = []
            for i in range(n):
                for j in range(i + 1, n):
                    pair = tuple(sorted([team_list[i], team_list[j]]))
                    if pair not in already_scheduled:
                        result.append(pair)
            return result

        rounds = Season._round_robin_rounds(team_list)
        rounds_to_keep = max(needed.values())

        best_selected: List[Tuple[str, str]] = []
        best_deficit = n * target_per_team

        for _attempt in range(10):
            random.shuffle(rounds)
            kept_rounds = rounds[:rounds_to_keep]

            selected: List[Tuple[str, str]] = []
            selected_set: set = set()
            counts = {t: 0 for t in team_list}

            for rnd in kept_rounds:
                for pair in rnd:
                    if pair in already_scheduled:
                        continue
                    h, a = pair
                    selected.append(pair)
                    selected_set.add(pair)
                    counts[h] += 1
                    counts[a] += 1

            deficit = sum(max(0, needed[t] - counts[t]) for t in team_list)
            if deficit == 0:
                return selected

            short_teams = [t for t in team_list if counts[t] < needed[t]]
            patch_pairs = []
            for i in range(len(short_teams)):
                for j in range(i + 1, len(short_teams)):
                    pair = tuple(sorted([short_teams[i], short_teams[j]]))
                    if pair not in already_scheduled and pair not in selected_set:
                        patch_pairs.append(pair)
            random.shuffle(patch_pairs)
            for pair in patch_pairs:
                h, a = pair
                if counts[h] < needed[h] and counts[a] < needed[a]:
                    selected.append(pair)
                    selected_set.add(pair)
                    counts[h] += 1
                    counts[a] += 1

            deficit = sum(max(0, needed[t] - counts[t]) for t in team_list)
            if deficit == 0:
                return selected
            if deficit < best_deficit:
                best_deficit = deficit
                best_selected = list(selected)

        return best_selected

    def _mark_rivalry_games(self):
        """Mark games involving rivalry pairs with is_rivalry_game flag."""
        rivalry_pairs = set()
        for team, rivals in self.rivalries.items():
            conf_rival = rivals.get("conference")
            nc_rival = rivals.get("non_conference")
            if conf_rival:
                rivalry_pairs.add(tuple(sorted([team, conf_rival])))
            if nc_rival:
                rivalry_pairs.add(tuple(sorted([team, nc_rival])))
        for game in self.schedule:
            pair = tuple(sorted([game.home_team, game.away_team]))
            if pair in rivalry_pairs:
                game.is_rivalry_game = True

    def _assign_weeks_by_type(self, non_conf_weeks: int = 3):
        """Assign week numbers with natural bye weeks, like real college football.

        Non-conference games fill early weeks (1..non_conf_weeks), conference
        games fill later weeks.  Each game goes into the earliest eligible week
        where neither team already has a game.  The schedule stretches as many
        weeks as needed — teams naturally get byes when they aren't scheduled
        in a given week, just like Army-Navy being the only game in its week.
        """
        if not self.schedule:
            return

        non_conf = [g for g in self.schedule if not g.is_conference_game]
        conf = [g for g in self.schedule if g.is_conference_game]
        random.shuffle(non_conf)
        random.shuffle(conf)

        week_teams: dict[int, set] = {}

        def _assign(game, min_week):
            week = min_week
            while True:
                if week not in week_teams:
                    week_teams[week] = set()
                slot = week_teams[week]
                if game.home_team not in slot and game.away_team not in slot:
                    game.week = week
                    slot.add(game.home_team)
                    slot.add(game.away_team)
                    return
                week += 1

        for game in non_conf:
            _assign(game, 1)

        conf_start = non_conf_weeks + 1
        for game in conf:
            _assign(game, conf_start)

        self.schedule = sorted(non_conf + conf, key=lambda g: g.week)

    def _generate_round_robin(self, team_names: List[str], dynasty_year: Optional[int] = None):
        """Full round-robin: each team plays each other once"""
        games = []
        for i in range(len(team_names)):
            for j in range(i + 1, len(team_names)):
                home = team_names[i]
                away = team_names[j]
                if dynasty_year is not None:
                    # Deterministic flip: same pair alternates home/away each year
                    pair_key = tuple(sorted([home, away]))
                    if (hash(pair_key) + dynasty_year) % 2 == 1:
                        home, away = away, home
                elif random.random() < 0.5:
                    home, away = away, home

                is_conf = (self.team_conferences.get(home, "") == self.team_conferences.get(away, "")
                           and self.team_conferences.get(home, "") != "")
                games.append(Game(week=0, home_team=home, away_team=away, is_conference_game=is_conf))

        self.schedule = games

    def _generate_partial_schedule(
        self,
        team_names: List[str],
        games_per_team: int,
        conference_weight: float,
        pinned_matchups: Optional[List[Tuple[str, str]]] = None,
        dynasty_year: Optional[int] = None,
    ):
        """Generate a schedule: conference round-robin first, then non-conference fill.

        Conference games are capped at MAX_CONFERENCE_GAMES (9) per team. If the
        conference round-robin is smaller than that, each team plays all conference
        opponents. All remaining game slots are non-conference.

        Pinned matchups (user-selected non-conference games) are added first and
        guaranteed to appear in the schedule. AI teams' remaining non-conference
        slots are auto-filled.
        """
        game_counts = {name: 0 for name in team_names}
        conf_game_counts = {name: 0 for name in team_names}
        scheduled_pairs = set()
        games = []

        has_conferences = bool(self.conferences) and len(self.conferences) > 1

        def _add_game(home, away, is_conf, preserve_home_away=False):
            if not preserve_home_away:
                if dynasty_year is not None:
                    # Deterministic flip: same pair alternates home/away each year
                    pair_key = tuple(sorted([home, away]))
                    if (hash(pair_key) + dynasty_year) % 2 == 1:
                        home, away = away, home
                elif random.random() < 0.5:
                    home, away = away, home
            games.append(Game(week=0, home_team=home, away_team=away, is_conference_game=is_conf))
            scheduled_pairs.add(tuple(sorted([home, away])))
            game_counts[home] += 1
            game_counts[away] += 1
            if is_conf:
                conf_game_counts[home] += 1
                conf_game_counts[away] += 1

        # ── Step 1: Add pinned non-conference matchups (user selections) ──
        for home, away in (pinned_matchups or []):
            if home not in self.teams or away not in self.teams:
                continue
            pair = tuple(sorted([home, away]))
            if pair in scheduled_pairs:
                continue
            if game_counts[home] >= games_per_team or game_counts[away] >= games_per_team:
                continue
            _add_game(home, away, False, preserve_home_away=True)

        # ── Step 1b: Add rivalry matchups ──
        for team, rivals in self.rivalries.items():
            if team not in self.teams:
                continue
            conf_rival = rivals.get("conference")
            if conf_rival and conf_rival in self.teams:
                pair = tuple(sorted([team, conf_rival]))
                if pair not in scheduled_pairs:
                    if game_counts[team] < games_per_team and game_counts[conf_rival] < games_per_team:
                        _add_game(team, conf_rival, True)
            nc_rival = rivals.get("non_conference")
            if nc_rival and nc_rival in self.teams:
                pair = tuple(sorted([team, nc_rival]))
                if pair not in scheduled_pairs:
                    if game_counts[team] < games_per_team and game_counts[nc_rival] < games_per_team:
                        _add_game(team, nc_rival, False)

        # ── Step 2: Conference games (capped at MAX_CONFERENCE_GAMES per team) ──
        if has_conferences:
            for conf_name, conf_teams_list in self.conferences.items():
                conf_team_list = [t for t in conf_teams_list if t in self.teams]
                if len(conf_team_list) < 2:
                    continue

                conf_opponents = len(conf_team_list) - 1
                max_conf = min(conf_opponents, MAX_CONFERENCE_GAMES)

                available_pairs = []
                for i in range(len(conf_team_list)):
                    for j in range(i + 1, len(conf_team_list)):
                        pair = tuple(sorted([conf_team_list[i], conf_team_list[j]]))
                        if pair not in scheduled_pairs:
                            available_pairs.append(pair)

                if conf_opponents <= MAX_CONFERENCE_GAMES:
                    for h, a in available_pairs:
                        if game_counts[h] < games_per_team and game_counts[a] < games_per_team:
                            _add_game(h, a, True)
                else:
                    selected = self._balanced_conference_pairs(
                        conf_team_list, max_conf, scheduled_pairs, conf_game_counts,
                    )
                    for h, a in selected:
                        if game_counts[h] < games_per_team and game_counts[a] < games_per_team:
                            _add_game(h, a, True)

            # ── Step 3: Fill remaining non-conference slots (AI auto-fill) ──
            nonconf_matchups = []
            for i in range(len(team_names)):
                for j in range(i + 1, len(team_names)):
                    t1, t2 = team_names[i], team_names[j]
                    c1 = self.team_conferences.get(t1, "")
                    c2 = self.team_conferences.get(t2, "")
                    if c1 != c2 or c1 == "":
                        nonconf_matchups.append((t1, t2))
            random.shuffle(nonconf_matchups)

            for _pass in range(3):
                nonconf_matchups.sort(
                    key=lambda p: (games_per_team - game_counts[p[0]]) + (games_per_team - game_counts[p[1]]),
                    reverse=True,
                )
                for home, away in nonconf_matchups:
                    if game_counts[home] >= games_per_team or game_counts[away] >= games_per_team:
                        continue
                    pair = tuple(sorted([home, away]))
                    if pair in scheduled_pairs:
                        continue
                    _add_game(home, away, False)

            for _fill_pass in range(3):
                short_teams = [t for t in team_names if game_counts[t] < games_per_team]
                if not short_teams:
                    break

                all_remaining = []
                for st in short_teams:
                    st_conf = self.team_conferences.get(st, "")
                    for ot in team_names:
                        if ot == st:
                            continue
                        ot_conf = self.team_conferences.get(ot, "")
                        if st_conf and ot_conf and st_conf == ot_conf:
                            continue
                        pair = tuple(sorted([st, ot]))
                        if pair not in scheduled_pairs:
                            all_remaining.append(pair)
                random.shuffle(all_remaining)
                all_remaining.sort(
                    key=lambda p: (games_per_team - game_counts.get(p[0], 0))
                                + (games_per_team - game_counts.get(p[1], 0)),
                    reverse=True,
                )
                for pair in all_remaining:
                    h, a = pair
                    if game_counts[h] >= games_per_team and game_counts[a] >= games_per_team:
                        continue
                    _add_game(h, a, False)

            short_teams = [t for t in team_names if game_counts[t] < games_per_team]
            for st in short_teams:
                while game_counts[st] < games_per_team:
                    fcs_name, fcs_mascot = generate_fcs_team_name()
                    game = Game(week=0, home_team=st, away_team=fcs_name,
                                is_conference_game=False, is_fcs_game=True)
                    games.append(game)
                    scheduled_pairs.add(tuple(sorted([st, fcs_name])))
                    game_counts[st] += 1
                    self.fcs_teams[fcs_name] = fcs_mascot
        else:
            single_conf = len(self.conferences) == 1
            all_matchups = []
            for i in range(len(team_names)):
                for j in range(i + 1, len(team_names)):
                    all_matchups.append((team_names[i], team_names[j]))
            random.shuffle(all_matchups)

            for home, away in all_matchups:
                if game_counts[home] >= games_per_team or game_counts[away] >= games_per_team:
                    continue
                pair = tuple(sorted([home, away]))
                if pair in scheduled_pairs:
                    continue
                is_conf = single_conf or (
                    self.team_conferences.get(home, "") == self.team_conferences.get(away, "")
                    and self.team_conferences.get(home, "") != ""
                )
                _add_game(home, away, is_conf)

        self.schedule = games

    def generate_round_robin_schedule(self):
        """Legacy method - generates full round-robin"""
        self.generate_schedule(games_per_team=0)

    def _is_human_game(self, game: Game) -> bool:
        """Check if either team in this game is human-controlled."""
        if not self.human_teams:
            return False
        return game.home_team in self.human_teams or game.away_team in self.human_teams

    def simulate_game(self, game: Game, verbose: bool = False,
                      dq_team_boosts: Optional[Dict[str, Dict[str, float]]] = None,
                      use_fast_sim: bool = False) -> Dict:
        """Simulate a single game and update standings.

        Args:
            game: The Game to simulate.
            verbose: Enable verbose output (full engine only).
            dq_team_boosts: DraftyQueenz team boosts.
            use_fast_sim: If True, use fast statistical model for CPU-vs-CPU
                          games. Human-team games always use the full engine.
        """
        fcs_side = None
        if game.is_fcs_game:
            if game.home_team in self.fcs_teams:
                fcs_side = "home"
                mascot = self.fcs_teams[game.home_team]
                fcs_team_obj = generate_fcs_team(game.home_team, mascot)
                home_team = fcs_team_obj
                away_team = self.teams[game.away_team]
            else:
                fcs_side = "away"
                mascot = self.fcs_teams[game.away_team]
                fcs_team_obj = generate_fcs_team(game.away_team, mascot)
                home_team = self.teams[game.home_team]
                away_team = fcs_team_obj
        else:
            home_team = self.teams[game.home_team]
            away_team = self.teams[game.away_team]

        # Geo-aware weather: use home team's state if available
        home_state = self.team_states.get(game.home_team)
        total_weeks = max((g.week for g in self.schedule), default=18)
        season_weather = generate_game_weather(
            state=home_state,
            week=game.week,
            total_weeks=total_weeks,
        )

        is_neutral = game.week >= 900

        # ── Fast-Sim Path ──
        # CPU-vs-CPU games use lightweight statistical model.
        # Human-team games always get full play-by-play engine.
        should_fast_sim = use_fast_sim and not self._is_human_game(game)

        if should_fast_sim:
            weather_code = season_weather if isinstance(season_weather, str) else "clear"
            weather_label = weather_code.replace("_", " ").title()

            result = fast_sim_game(
                home_team, away_team,
                seed=random.randint(1, 1000000),
                weather=weather_code,
                weather_label=weather_label,
                weather_description=f"{weather_label} conditions",
                is_rivalry=game.is_rivalry_game,
                neutral_site=is_neutral,
            )
            result["is_rivalry_game"] = game.is_rivalry_game

            if fcs_side != "home":
                for p in home_team.players:
                    p.season_games_played = getattr(p, 'season_games_played', 0) + 1
            if fcs_side != "away":
                for p in away_team.players:
                    p.season_games_played = getattr(p, 'season_games_played', 0) + 1

            game.home_score = result['final_score']['home']['score']
            game.away_score = result['final_score']['away']['score']
            game.completed = True

            home_metrics = result.get("_fast_sim_metrics", {}).get("home", {})
            away_metrics = result.get("_fast_sim_metrics", {}).get("away", {})

            game.home_metrics = home_metrics
            game.away_metrics = away_metrics
            game.full_result = result

            self._update_standings(game, result, home_metrics, away_metrics, fcs_side)
            return result

        # ── Full Engine Path ──
        home_style_config = self.style_configs.get(game.home_team, {})
        away_style_config = self.style_configs.get(game.away_team, {})

        style_overrides = {
            home_team.name: home_style_config.get('offense_style', 'balanced'),
            f"{home_team.name}_defense": home_style_config.get('defense_style', 'swarm'),
            f"{home_team.name}_st": home_style_config.get('st_scheme', 'aces'),
            away_team.name: away_style_config.get('offense_style', 'balanced'),
            f"{away_team.name}_defense": away_style_config.get('defense_style', 'swarm'),
            f"{away_team.name}_st": away_style_config.get('st_scheme', 'aces'),
        }

        injury_kwargs = {}
        if self.injury_tracker is not None:
            fcs_teams_set = set(getattr(self, 'fcs_teams', {}).keys())
            home_is_fcs = game.home_team in fcs_teams_set
            away_is_fcs = game.away_team in fcs_teams_set
            injury_kwargs["injury_tracker"] = self.injury_tracker
            injury_kwargs["game_week"] = game.week
            injury_kwargs["unavailable_home"] = (
                [] if home_is_fcs else
                self.injury_tracker.get_unavailable_names(game.home_team, game.week))
            injury_kwargs["unavailable_away"] = (
                [] if away_is_fcs else
                self.injury_tracker.get_unavailable_names(game.away_team, game.week))
            injury_kwargs["dtd_home"] = (
                [] if home_is_fcs else
                self.injury_tracker.get_dtd_names(game.home_team, game.week))
            injury_kwargs["dtd_away"] = (
                [] if away_is_fcs else
                self.injury_tracker.get_dtd_names(game.away_team, game.week))

        dq_kwargs = {}
        if dq_team_boosts:
            dq_kwargs["home_dq_boosts"] = dq_team_boosts.get(game.home_team, {})
            dq_kwargs["away_dq_boosts"] = dq_team_boosts.get(game.away_team, {})

        coaching_kwargs = {}
        if self.coaching_staffs:
            home_staff = self.coaching_staffs.get(game.home_team)
            away_staff = self.coaching_staffs.get(game.away_team)
            if home_staff:
                coaching_kwargs["home_coaching"] = home_staff
            if away_staff:
                coaching_kwargs["away_coaching"] = away_staff
            if "game_week" not in injury_kwargs:
                coaching_kwargs["game_week"] = game.week

        nfz_kwargs = {}
        home_record = self.standings.get(game.home_team)
        away_record = self.standings.get(game.away_team)
        if home_record and home_record.no_fly_zone:
            nfz_kwargs["home_no_fly_zone"] = True
        if away_record and away_record.no_fly_zone:
            nfz_kwargs["away_no_fly_zone"] = True
        if home_record and home_record.brick_wall:
            nfz_kwargs["home_brick_wall"] = True
        if away_record and away_record.brick_wall:
            nfz_kwargs["away_brick_wall"] = True
        if home_record and home_record.turnover_machine:
            nfz_kwargs["home_turnover_machine"] = True
        if away_record and away_record.turnover_machine:
            nfz_kwargs["away_turnover_machine"] = True

        engine = ViperballEngine(
            home_team,
            away_team,
            seed=random.randint(1, 1000000),
            style_overrides=style_overrides,
            weather=season_weather,
            is_rivalry=game.is_rivalry_game,
            neutral_site=is_neutral,
            **injury_kwargs,
            **dq_kwargs,
            **coaching_kwargs,
            **nfz_kwargs,
        )
        result = engine.simulate_game()
        result["is_rivalry_game"] = game.is_rivalry_game

        if fcs_side != "home":
            for p in home_team.players:
                p.season_games_played = getattr(p, 'season_games_played', 0) + 1
        if fcs_side != "away":
            for p in away_team.players:
                p.season_games_played = getattr(p, 'season_games_played', 0) + 1

        game.home_score = result['final_score']['home']['score']
        game.away_score = result['final_score']['away']['score']
        game.completed = True

        home_metrics = calculate_viperball_metrics(result, 'home')
        away_metrics = calculate_viperball_metrics(result, 'away')

        game.home_metrics = home_metrics
        game.away_metrics = away_metrics
        game.full_result = result

        self._update_standings(game, result, home_metrics, away_metrics, fcs_side)
        return result

    def _update_standings(self, game: Game, result: Dict,
                          home_metrics: Dict, away_metrics: Dict,
                          fcs_side: Optional[str]):
        """Update standings for both teams after a game."""
        home_won = game.home_score > game.away_score
        away_won = game.away_score > game.home_score

        away_stats = result.get("final_score", {}).get("away", {}).get("stats", {})
        home_stats = result.get("final_score", {}).get("home", {}).get("stats", {})
        home_def_ints = (away_stats.get("kick_pass_interceptions", 0)
                         + away_stats.get("lateral_interceptions", 0))
        away_def_ints = (home_stats.get("kick_pass_interceptions", 0)
                         + home_stats.get("lateral_interceptions", 0))

        home_def_rush_allowed = away_stats.get("rushing_yards", 0)
        away_def_rush_allowed = home_stats.get("rushing_yards", 0)
        home_def_turnovers = (home_def_ints
                              + away_stats.get("fumbles_lost", 0)
                              + away_stats.get("turnovers_on_downs", 0))
        away_def_turnovers = (away_def_ints
                              + home_stats.get("fumbles_lost", 0)
                              + home_stats.get("turnovers_on_downs", 0))

        game_stats = result.get("stats", {})
        home_game_stats = game_stats.get("home", {})
        away_game_stats = game_stats.get("away", {})
        home_dye = home_game_stats.get("dye")
        away_dye = away_game_stats.get("dye")
        home_bonus = {"count": home_game_stats.get("bonus_possessions", 0),
                      "scores": home_game_stats.get("bonus_possession_scores", 0),
                      "yards": home_game_stats.get("bonus_possession_yards", 0)}
        away_bonus = {"count": away_game_stats.get("bonus_possessions", 0),
                      "scores": away_game_stats.get("bonus_possession_scores", 0),
                      "yards": away_game_stats.get("bonus_possession_yards", 0)}

        home_metrics["delta_yards_raw"] = home_game_stats.get("delta_yards", 0)
        away_metrics["delta_yards_raw"] = away_game_stats.get("delta_yards", 0)

        if fcs_side != "home" and game.home_team in self.standings:
            self.standings[game.home_team].add_game_result(
                won=home_won,
                points_for=game.home_score,
                points_against=game.away_score,
                metrics=home_metrics,
                is_conference_game=game.is_conference_game,
                defensive_ints=home_def_ints,
                rushing_yards_allowed=home_def_rush_allowed,
                turnovers_forced=home_def_turnovers,
                dye_data=home_dye,
                opponent_dye_data=away_dye,
                bonus_data=home_bonus,
                opponent_bonus_data=away_bonus,
            )

        if fcs_side != "away" and game.away_team in self.standings:
            self.standings[game.away_team].add_game_result(
                won=away_won,
                points_for=game.away_score,
                points_against=game.home_score,
                metrics=away_metrics,
                is_conference_game=game.is_conference_game,
                defensive_ints=away_def_ints,
                rushing_yards_allowed=away_def_rush_allowed,
                turnovers_forced=away_def_turnovers,
                dye_data=away_dye,
                opponent_dye_data=home_dye,
                bonus_data=away_bonus,
                opponent_bonus_data=home_bonus,
            )

    def simulate_week(self, week: Optional[int] = None, verbose: bool = False,
                      generate_polls: bool = True, rng=None,
                      dq_team_boosts: Optional[Dict[str, Dict[str, float]]] = None,
                      use_fast_sim: bool = False) -> List[Game]:
        """Simulate a single week of games. Returns list of games played.

        Args:
            week: Specific week number to simulate. If None, simulates the next
                  unplayed week.
            generate_polls: Whether to generate a poll after this week.
            verbose: Enable verbose output.
            dq_team_boosts: Optional dict of team_name -> boost_type -> boost_amount.
            use_fast_sim: If True, use fast statistical model for CPU-vs-CPU
                          games. Human-team games always use the full engine.

        Returns:
            List of Game objects that were simulated this week, or empty list
            if no games remain.
        """
        if week is None:
            week = self.get_next_unplayed_week()
            if week is None:
                return []

        if self.injury_tracker is not None:
            self.injury_tracker.resolve_week(week)
            self.injury_tracker.process_week(week, self.teams, self.standings)

        week_games = [g for g in self.schedule if g.week == week and not g.completed]
        for game in week_games:
            self.simulate_game(game, verbose=verbose, dq_team_boosts=dq_team_boosts,
                               use_fast_sim=use_fast_sim)

        if generate_polls and week_games:
            self._generate_weekly_poll(week)

        return week_games

    def simulate_through_week(self, target_week: int, verbose: bool = False,
                              generate_polls: bool = True,
                              use_fast_sim: bool = False) -> List[Game]:
        """Simulate all unplayed weeks up to and including target_week.

        Returns all games simulated across those weeks.
        """
        all_games = []
        while True:
            next_week = self.get_next_unplayed_week()
            if next_week is None or next_week > target_week:
                break
            games = self.simulate_week(next_week, verbose=verbose,
                                       generate_polls=generate_polls,
                                       use_fast_sim=use_fast_sim)
            all_games.extend(games)
        return all_games

    def get_next_unplayed_week(self) -> Optional[int]:
        """Return the earliest week number with unplayed games, or None if all done."""
        unplayed_weeks = sorted(set(g.week for g in self.schedule if not g.completed))
        return unplayed_weeks[0] if unplayed_weeks else None

    def get_last_completed_week(self) -> int:
        """Return the highest week number that has been fully completed, or 0."""
        completed_weeks = set()
        all_weeks = set()
        for g in self.schedule:
            all_weeks.add(g.week)
            if g.completed:
                completed_weeks.add(g.week)

        last = 0
        for w in sorted(all_weeks):
            week_games = [g for g in self.schedule if g.week == w]
            if all(g.completed for g in week_games):
                last = w
            else:
                break
        return last

    def is_regular_season_complete(self) -> bool:
        """Return True if all scheduled regular-season games have been played."""
        return all(g.completed for g in self.schedule)

    def simulate_season(self, verbose: bool = False, generate_polls: bool = True,
                        use_fast_sim: bool = False):
        """Simulate all remaining regular season games, optionally generating weekly polls.

        Args:
            use_fast_sim: If True, CPU-vs-CPU games use fast statistical model.
                          Human-team games always use the full engine.
        """
        while True:
            games = self.simulate_week(verbose=verbose, generate_polls=generate_polls,
                                        use_fast_sim=use_fast_sim)
            if not games:
                break

    def _calculate_sos(self, team_name: str) -> float:
        """Calculate strength of schedule based on opponent win pcts and opponent-opponent win pcts"""
        opponents = set()
        for game in self.schedule:
            if game.completed:
                if game.home_team == team_name:
                    opponents.add(game.away_team)
                elif game.away_team == team_name:
                    opponents.add(game.home_team)

        if not opponents:
            return 0.5

        opp_win_pcts = []
        opp_opp_win_pcts = []
        for opp in opponents:
            if opp in self.standings:
                opp_wp = self.standings[opp].win_percentage
                opp_win_pcts.append(opp_wp)
                opp_opps = set()
                for g in self.schedule:
                    if g.completed:
                        if g.home_team == opp and g.away_team != team_name:
                            opp_opps.add(g.away_team)
                        elif g.away_team == opp and g.home_team != team_name:
                            opp_opps.add(g.home_team)
                for oo in opp_opps:
                    if oo in self.standings:
                        opp_opp_win_pcts.append(self.standings[oo].win_percentage)

        direct = sum(opp_win_pcts) / len(opp_win_pcts) if opp_win_pcts else 0.5
        indirect = sum(opp_opp_win_pcts) / len(opp_opp_win_pcts) if opp_opp_win_pcts else 0.5
        return direct * 0.667 + indirect * 0.333

    def _get_current_rankings(self) -> Dict[str, int]:
        """Get current team rankings from latest poll, or by win pct if no poll exists"""
        if self.weekly_polls:
            return {r.team_name: r.rank for r in self.weekly_polls[-1].rankings}
        ranked = sorted(
            [(n, r) for n, r in self.standings.items() if r.games_played > 0],
            key=lambda x: (x[1].win_percentage, x[1].point_differential),
            reverse=True
        )
        return {name: i + 1 for i, (name, _) in enumerate(ranked)}

    def _count_quality_wins(self, team_name: str, rankings: Dict[str, int]) -> int:
        """Count wins against teams ranked in top 25"""
        quality = 0
        for game in self.schedule:
            if not game.completed:
                continue
            if game.home_team == team_name and (game.home_score or 0) > (game.away_score or 0):
                opp = game.away_team
            elif game.away_team == team_name and (game.away_score or 0) > (game.home_score or 0):
                opp = game.home_team
            else:
                continue
            if opp in rankings and rankings[opp] <= 25:
                quality += 1
        return quality

    def _quality_win_score(self, team_name: str, rankings: Dict[str, int]) -> float:
        """Score for wins against ranked teams, weighted higher for beating higher-ranked opponents"""
        score = 0.0
        for game in self.schedule:
            if not game.completed:
                continue
            if game.home_team == team_name and (game.home_score or 0) > (game.away_score or 0):
                opp = game.away_team
            elif game.away_team == team_name and (game.away_score or 0) > (game.home_score or 0):
                opp = game.home_team
            else:
                continue
            if opp in rankings and rankings[opp] <= 25:
                rank = rankings[opp]
                if rank <= 5:
                    score += 5.0
                elif rank <= 10:
                    score += 3.5
                elif rank <= 15:
                    score += 2.5
                elif rank <= 20:
                    score += 1.5
                else:
                    score += 1.0
        return score

    def _loss_quality_score(self, team_name: str, rankings: Dict[str, int]) -> float:
        """Losses to top-10 teams penalized less; losses to unranked teams penalized more"""
        penalty = 0.0
        for game in self.schedule:
            if not game.completed:
                continue
            if game.home_team == team_name and (game.home_score or 0) < (game.away_score or 0):
                opp = game.away_team
            elif game.away_team == team_name and (game.away_score or 0) < (game.home_score or 0):
                opp = game.home_team
            else:
                continue
            if opp in rankings:
                rank = rankings[opp]
                if rank <= 5:
                    penalty += 0.5
                elif rank <= 10:
                    penalty += 1.0
                elif rank <= 25:
                    penalty += 2.0
                else:
                    penalty += 3.0
            else:
                penalty += 3.5
        return penalty

    def _non_conference_record(self, team_name: str) -> Tuple[int, int]:
        """Get non-conference wins and losses"""
        nc_wins = 0
        nc_losses = 0
        for game in self.schedule:
            if not game.completed or game.is_conference_game:
                continue
            if game.home_team == team_name:
                if (game.home_score or 0) > (game.away_score or 0):
                    nc_wins += 1
                else:
                    nc_losses += 1
            elif game.away_team == team_name:
                if (game.away_score or 0) > (game.home_score or 0):
                    nc_wins += 1
                else:
                    nc_losses += 1
        return nc_wins, nc_losses

    def _conference_strength(self, conference: str) -> float:
        """Calculate conference strength based on non-conference performance of all members"""
        conf_teams = self.conferences.get(conference, [])
        if not conf_teams:
            return 0.5
        total_nc_wins = 0
        total_nc_games = 0
        for team in conf_teams:
            nc_w, nc_l = self._non_conference_record(team)
            total_nc_wins += nc_w
            total_nc_games += nc_w + nc_l
        return total_nc_wins / total_nc_games if total_nc_games > 0 else 0.5

    def calculate_power_index(self, team_name: str) -> float:
        """Calculate comprehensive Power Index for a team.

        Components (100-point scale):
        - Win percentage:       30 pts
        - Strength of schedule: 20 pts
        - Quality wins:         20 pts (weighted by opponent rank)
        - Loss quality:        -penalty (bad losses hurt more)
        - Non-conf record:      10 pts
        - Conference strength:  10 pts
        - Point differential:   10 pts
        """
        record = self.standings.get(team_name)
        if not record or record.games_played == 0:
            return 0.0

        rankings = self._get_current_rankings()

        win_component = record.win_percentage * 30.0

        sos = self._calculate_sos(team_name)
        sos_component = sos * 20.0

        qw_score = self._quality_win_score(team_name, rankings)
        qw_component = min(20.0, qw_score * 4.0)

        loss_penalty = self._loss_quality_score(team_name, rankings)

        nc_w, nc_l = self._non_conference_record(team_name)
        nc_total = nc_w + nc_l
        nc_component = (nc_w / nc_total * 10.0) if nc_total > 0 else 5.0

        conf = self.team_conferences.get(team_name, "")
        conf_str = self._conference_strength(conf) if conf else 0.5
        conf_component = conf_str * 10.0

        ppg = record.points_for / max(1, record.games_played)
        ppg_against = record.points_against / max(1, record.games_played)
        diff = ppg - ppg_against
        diff_component = min(10.0, max(0.0, (diff + 20) * 0.25))

        power = (win_component + sos_component + qw_component + nc_component +
                 conf_component + diff_component - loss_penalty)
        return max(0.0, round(power, 2))

    def get_all_power_rankings(self) -> List[Tuple[str, float, int]]:
        """Get all teams sorted by power index. Returns [(team_name, power_index, quality_wins)]"""
        rankings = self._get_current_rankings()
        results = []
        for team_name, record in self.standings.items():
            if record.games_played > 0:
                pi = self.calculate_power_index(team_name)
                qw = self._count_quality_wins(team_name, rankings)
                results.append((team_name, pi, qw))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def get_conference_champions(self) -> Dict[str, str]:
        """Determine conference champion for each conference (best conf record, then overall)"""
        champions = {}
        for conf_name in self.conferences:
            conf_standings = self.get_conference_standings(conf_name)
            if conf_standings:
                champions[conf_name] = conf_standings[0].team_name
        return champions

    def _calculate_poll_score(self, record: TeamRecord) -> float:
        """Calculate poll ranking score using Power Index"""
        if record.games_played == 0:
            return 0.0
        return self.calculate_power_index(record.team_name)

    def _generate_weekly_poll(self, week: int):
        """Generate rankings after a week using Power Index"""
        prev_poll = self.weekly_polls[-1] if self.weekly_polls else None
        prev_ranks = {}
        if prev_poll:
            for r in prev_poll.rankings:
                prev_ranks[r.team_name] = r.rank

        power_rankings = self.get_all_power_rankings()
        current_rankings = self._get_current_rankings()

        sos_list = []
        for team_name, record in self.standings.items():
            if record.games_played > 0:
                sos_list.append((team_name, self._calculate_sos(team_name)))
        sos_list.sort(key=lambda x: x[1], reverse=True)
        sos_rank_map = {name: i + 1 for i, (name, _) in enumerate(sos_list)}

        rankings = []
        for i, (team_name, pi, qw) in enumerate(power_rankings[:25], 1):
            record = self.standings[team_name]
            rankings.append(PollRanking(
                rank=i,
                team_name=team_name,
                record=f"{record.wins}-{record.losses}",
                conference=record.conference,
                poll_score=round(pi, 2),
                prev_rank=prev_ranks.get(team_name),
                power_index=round(pi, 2),
                quality_wins=qw,
                sos_rank=sos_rank_map.get(team_name, 0),
            ))

        self.weekly_polls.append(WeeklyPoll(week=week, rankings=rankings))

    def get_standings_sorted(self) -> List[TeamRecord]:
        """Get standings sorted by win percentage, then point differential"""
        return sorted(
            self.standings.values(),
            key=lambda r: (r.win_percentage, r.point_differential),
            reverse=True
        )

    def get_conference_standings(self, conference_name: str) -> List[TeamRecord]:
        """Get standings filtered to a specific conference, sorted by conf record then overall"""
        conf_teams = self.conferences.get(conference_name, [])
        conf_records = [
            self.standings[t] for t in conf_teams
            if t in self.standings
        ]
        return sorted(
            conf_records,
            key=lambda r: (r.conf_win_percentage, r.win_percentage, r.point_differential),
            reverse=True
        )

    def get_playoff_teams(self, num_teams: int = 4) -> List[TeamRecord]:
        """Select playoff teams: conference champions get auto-bids, remaining spots filled by power index.

        Each conference champion gets an automatic bid. Remaining spots go to the
        highest-rated teams by power index (at-large bids). Teams are then seeded
        by power index regardless of bid type.
        """
        champions = self.get_conference_champions()
        num_conferences = len(champions)

        auto_bid_teams = set(champions.values())
        self._playoff_bid_types = {}

        if num_conferences > 0 and num_teams >= num_conferences:
            for conf, champ in champions.items():
                self._playoff_bid_types[champ] = "auto"

            at_large_spots = num_teams - len(auto_bid_teams)

            power_ranked = self.get_all_power_rankings()
            at_large = []
            for team_name, pi, qw in power_ranked:
                if team_name not in auto_bid_teams:
                    at_large.append(team_name)
                    self._playoff_bid_types[team_name] = "at-large"
                    if len(at_large) >= at_large_spots:
                        break

            all_playoff_names = list(auto_bid_teams) + at_large

            pi_map = {name: pi for name, pi, _ in power_ranked}
            all_playoff_names.sort(key=lambda n: pi_map.get(n, 0), reverse=True)

            return [self.standings[n] for n in all_playoff_names if n in self.standings]
        else:
            power_ranked = self.get_all_power_rankings()
            result = []
            for team_name, pi, qw in power_ranked[:num_teams]:
                self._playoff_bid_types[team_name] = "at-large"
                result.append(self.standings[team_name])
            return result

    def get_playoff_bid_type(self, team_name: str) -> str:
        """Get whether a team earned an 'auto' or 'at-large' bid"""
        return getattr(self, '_playoff_bid_types', {}).get(team_name, "")

    def get_latest_poll(self) -> Optional[WeeklyPoll]:
        return self.weekly_polls[-1] if self.weekly_polls else None

    def get_total_weeks(self) -> int:
        if not self.schedule:
            return 0
        return max(g.week for g in self.schedule)

    def _get_winner(self, game: Game) -> str:
        return game.home_team if (game.home_score or 0) > (game.away_score or 0) else game.away_team

    def _play_round(self, matchups: list, week: int, verbose: bool = False) -> list:
        games = []
        for home, away in matchups:
            game = Game(week=week, home_team=home, away_team=away)
            self.playoff_bracket.append(game)
            games.append(game)
        for game in games:
            self.simulate_game(game, verbose=verbose)
        return games

    def simulate_playoff(self, num_teams: int = 4, verbose: bool = False):
        playoff_teams = self.get_playoff_teams(num_teams)
        seeds = [t.team_name for t in playoff_teams]

        if num_teams == 4:
            semis = self._play_round(
                [(seeds[0], seeds[3]), (seeds[1], seeds[2])], week=999, verbose=verbose
            )
            final_matchup = [(self._get_winner(semis[0]), self._get_winner(semis[1]))]
            finals = self._play_round(final_matchup, week=1000, verbose=verbose)
            self.champion = self._get_winner(finals[0])

        elif num_teams == 8:
            quarters = self._play_round(
                [(seeds[i], seeds[7 - i]) for i in range(4)], week=998, verbose=verbose
            )
            qw = [self._get_winner(g) for g in quarters]
            semis = self._play_round(
                [(qw[0], qw[3]), (qw[1], qw[2])], week=999, verbose=verbose
            )
            finals = self._play_round(
                [(self._get_winner(semis[0]), self._get_winner(semis[1]))], week=1000, verbose=verbose
            )
            self.champion = self._get_winner(finals[0])

        elif num_teams == 12:
            byes = seeds[:4]
            first_round = self._play_round(
                [(seeds[4 + i], seeds[11 - i]) for i in range(4)], week=997, verbose=verbose
            )
            frw = [self._get_winner(g) for g in first_round]
            quarter_matchups = [
                (byes[0], frw[3]),
                (byes[1], frw[2]),
                (byes[2], frw[1]),
                (byes[3], frw[0]),
            ]
            quarters = self._play_round(quarter_matchups, week=998, verbose=verbose)
            qw = [self._get_winner(g) for g in quarters]
            semis = self._play_round(
                [(qw[0], qw[3]), (qw[1], qw[2])], week=999, verbose=verbose
            )
            finals = self._play_round(
                [(self._get_winner(semis[0]), self._get_winner(semis[1]))], week=1000, verbose=verbose
            )
            self.champion = self._get_winner(finals[0])

        elif num_teams == 16:
            first_round = self._play_round(
                [(seeds[i], seeds[15 - i]) for i in range(8)], week=997, verbose=verbose
            )
            frw = [self._get_winner(g) for g in first_round]
            quarters = self._play_round(
                [(frw[i], frw[7 - i]) for i in range(4)], week=998, verbose=verbose
            )
            qw = [self._get_winner(g) for g in quarters]
            semis = self._play_round(
                [(qw[0], qw[3]), (qw[1], qw[2])], week=999, verbose=verbose
            )
            finals = self._play_round(
                [(self._get_winner(semis[0]), self._get_winner(semis[1]))], week=1000, verbose=verbose
            )
            self.champion = self._get_winner(finals[0])

        elif num_teams == 24:
            byes = seeds[:8]
            first_round = self._play_round(
                [(seeds[8 + i], seeds[23 - i]) for i in range(8)], week=996, verbose=verbose
            )
            frw = [self._get_winner(g) for g in first_round]
            second_matchups = [
                (byes[0], frw[7]),
                (byes[1], frw[6]),
                (byes[2], frw[5]),
                (byes[3], frw[4]),
                (byes[4], frw[3]),
                (byes[5], frw[2]),
                (byes[6], frw[1]),
                (byes[7], frw[0]),
            ]
            second_round = self._play_round(second_matchups, week=997, verbose=verbose)
            srw = [self._get_winner(g) for g in second_round]
            quarters = self._play_round(
                [(srw[i], srw[7 - i]) for i in range(4)], week=998, verbose=verbose
            )
            qw = [self._get_winner(g) for g in quarters]
            semis = self._play_round(
                [(qw[0], qw[3]), (qw[1], qw[2])], week=999, verbose=verbose
            )
            finals = self._play_round(
                [(self._get_winner(semis[0]), self._get_winner(semis[1]))], week=1000, verbose=verbose
            )
            self.champion = self._get_winner(finals[0])

        elif num_teams == 32:
            first_round = self._play_round(
                [(seeds[i], seeds[31 - i]) for i in range(16)], week=996, verbose=verbose
            )
            frw = [self._get_winner(g) for g in first_round]
            second_round = self._play_round(
                [(frw[i], frw[15 - i]) for i in range(8)], week=997, verbose=verbose
            )
            srw = [self._get_winner(g) for g in second_round]
            quarters = self._play_round(
                [(srw[i], srw[7 - i]) for i in range(4)], week=998, verbose=verbose
            )
            qw = [self._get_winner(g) for g in quarters]
            semis = self._play_round(
                [(qw[0], qw[3]), (qw[1], qw[2])], week=999, verbose=verbose
            )
            finals = self._play_round(
                [(self._get_winner(semis[0]), self._get_winner(semis[1]))], week=1000, verbose=verbose
            )
            self.champion = self._get_winner(finals[0])

    def simulate_bowls(self, bowl_count: int = 0, playoff_size: int = 4,
                       bowl_names: Optional[List[str]] = None, verbose: bool = False):
        """Simulate bowl games for non-playoff teams.

        Args:
            bowl_count: Number of bowls (0 = auto-recommend based on league/playoff size)
            playoff_size: Number of teams in playoff (to exclude from bowls)
            bowl_names: Custom bowl names (optional, uses defaults if not provided)
            verbose: Whether to log verbose output
        """
        standings = self.get_standings_sorted()
        league_size = len(standings)

        if bowl_count <= 0:
            bowl_count = get_recommended_bowl_count(league_size, playoff_size)
        if bowl_count == 0:
            return

        playoff_team_names = {t.team_name for t in standings[:playoff_size]}

        non_playoff = [t for t in standings if t.team_name not in playoff_team_names]

        total_games = max((t.wins + t.losses) for t in standings) if standings else 0
        threshold = total_games / 2 if total_games > 0 else 0

        eligible = [t for t in non_playoff if t.wins >= threshold]
        sub_500 = [t for t in non_playoff if t.wins < threshold]

        teams_needed = bowl_count * 2
        pool = list(eligible)
        if len(pool) < teams_needed:
            for t in sub_500:
                if len(pool) >= teams_needed:
                    break
                pool.append(t)

        if len(pool) < 2:
            return
        bowl_count = min(bowl_count, len(pool) // 2)

        tier_list = [1 if i < 2 else (2 if i < 4 else 3) for i in range(bowl_count)]
        if bowl_names:
            names = list(bowl_names)
            while len(names) < bowl_count:
                names.append(f"Bowl Game {len(names) + 1}")
        else:
            names = generate_bowl_names(bowl_count, tier_list)

        max_win_diff = 3
        used = set()
        matchups = []

        for i in range(bowl_count):
            best_pair = None
            best_diff = 999

            for a_idx in range(len(pool)):
                if a_idx in used:
                    continue
                for b_idx in range(a_idx + 1, len(pool)):
                    if b_idx in used:
                        continue
                    a, b = pool[a_idx], pool[b_idx]
                    win_diff = abs(a.wins - b.wins)
                    same_conf = (a.conference == b.conference and a.conference != "")
                    penalty = 2 if same_conf else 0
                    score = win_diff + penalty
                    if score < best_diff:
                        best_diff = score
                        best_pair = (a_idx, b_idx)

            if best_pair is None:
                break

            ai, bi = best_pair
            used.add(ai)
            used.add(bi)
            matchups.append((pool[ai], pool[bi]))

        for i, (team_a, team_b) in enumerate(matchups):
            tier = 1 if i < 2 else (2 if i < 4 else 3)
            game = Game(
                week=1001 + i,
                home_team=team_a.team_name,
                away_team=team_b.team_name,
            )
            self.simulate_game(game, verbose=verbose)

            a_seed = next((idx + 1 for idx, t in enumerate(standings) if t.team_name == team_a.team_name), 0)
            b_seed = next((idx + 1 for idx, t in enumerate(standings) if t.team_name == team_b.team_name), 0)

            bowl = BowlGame(
                name=names[i],
                tier=tier,
                game=game,
                team_1_seed=a_seed,
                team_2_seed=b_seed,
                team_1_record=f"{team_a.wins}-{team_a.losses}",
                team_2_record=f"{team_b.wins}-{team_b.losses}",
            )
            self.bowl_games.append(bowl)


def _pick_ai_archetype() -> str:
    """Pick a random archetype for an AI team from a weighted distribution.

    Creates a realistic league where most teams are mid-tier with a few
    elite programs and a handful of weak ones.
    """
    from scripts.generate_rosters import AI_ARCHETYPE_WEIGHTS
    keys = list(AI_ARCHETYPE_WEIGHTS.keys())
    weights = [AI_ARCHETYPE_WEIGHTS[k] for k in keys]
    return random.choices(keys, weights=weights)[0]


def load_teams_from_directory(
    directory: str,
    fresh: bool = False,
    team_archetypes: Optional[Dict[str, str]] = None,
) -> Dict[str, Team]:
    """Load all teams from a directory.

    Args:
        directory: Path to team JSON directory.
        fresh: If True, generate brand-new rosters for every team (new season/dynasty).
               If False, load stored rosters from JSON files (saved game).
        team_archetypes: Optional dict of team_name -> program archetype key.
                        Only used when fresh=True. Teams not in the dict get
                        a random archetype from a weighted distribution.
    """
    teams = {}
    team_dir = Path(directory)
    archetypes = team_archetypes or {}

    for team_file in team_dir.glob("*.json"):
        # We need the team name to look up archetype, but load_team_from_json
        # extracts it internally. Do a quick peek at the JSON for the name.
        import json as _json
        with open(team_file) as f:
            raw = _json.load(f)
        team_name = raw.get("team_info", {}).get("school") or raw.get("team_info", {}).get("school_name", "")
        arch = archetypes.get(team_name)
        if arch is None and fresh:
            arch = _pick_ai_archetype()
        team = load_team_from_json(str(team_file), fresh=fresh, program_archetype=arch)
        teams[team.name] = team

    return teams


def load_teams_with_states(
    directory: str,
    fresh: bool = False,
    team_archetypes: Optional[Dict[str, str]] = None,
) -> tuple:
    """
    Load all teams from a directory and also return a state map for weather.

    Args:
        directory: Path to team JSON directory.
        fresh: If True, generate brand-new rosters for every team.
        team_archetypes: Optional dict of team_name -> program archetype key.
                        Teams not in the dict get a random archetype when fresh.

    Returns:
        (teams_dict, team_states_dict) where team_states maps team_name -> state
    """
    import json as _json
    teams = {}
    team_states = {}
    team_dir = Path(directory)
    archetypes = team_archetypes or {}

    for team_file in team_dir.glob("*.json"):
        with open(team_file) as f:
            raw = _json.load(f)
        state = raw.get("team_info", {}).get("state", "")
        team_name = raw.get("team_info", {}).get("school") or raw.get("team_info", {}).get("school_name", "")
        arch = archetypes.get(team_name)
        if arch is None and fresh:
            arch = _pick_ai_archetype()
        team = load_team_from_json(str(team_file), fresh=fresh, program_archetype=arch)
        teams[team.name] = team
        if state:
            team_states[team.name] = state

    return teams, team_states


def load_coaching_staffs_from_directory(directory: str) -> Dict[str, dict]:
    """Load coaching staffs from team JSON files.

    Returns dict of team_name -> { role -> CoachCard }.
    """
    import json as _json
    from engine.coaching import CoachCard
    staffs = {}
    team_dir = Path(directory)
    for team_file in team_dir.glob("*.json"):
        with open(team_file) as f:
            raw = _json.load(f)
        team_name = raw.get("team_info", {}).get("school") or raw.get("team_info", {}).get("school_name", "")
        cs = raw.get("coaching_staff")
        if cs and team_name:
            staff = {}
            for role, card_data in cs.items():
                if isinstance(card_data, dict) and "coach_id" in card_data:
                    staff[role] = CoachCard.from_dict(card_data)
            if staff:
                staffs[team_name] = staff
    return staffs


def create_season(
    name: str,
    teams: Dict[str, Team],
    style_configs: Optional[Dict[str, Dict[str, str]]] = None,
    conferences: Optional[Dict[str, List[str]]] = None,
    games_per_team: int = 0,
    team_states: Optional[Dict[str, str]] = None,
    pinned_matchups: Optional[List[Tuple[str, str]]] = None,
    rivalries: Optional[Dict[str, Dict[str, Optional[str]]]] = None,
    coaching_staffs: Optional[Dict[str, dict]] = None,
    dynasty_year: Optional[int] = None,
) -> Season:
    """
    Create a season with teams and optional style configurations

    Args:
        name: Season name
        teams: Dictionary of team_name -> Team
        style_configs: Optional dictionary of team_name -> {'offense_style': ..., 'defense_style': ...}
        conferences: Optional dictionary of conference_name -> [team_names]
        games_per_team: Games per team (0 = full round-robin)
        team_states: Optional dict of team_name -> US state abbreviation for geo-aware weather
        pinned_matchups: Optional list of (home, away) tuples for user-selected
                        non-conference games that are locked into the schedule.
        dynasty_year: If set, home/away flips deterministically each year for dynasty mode.

    Returns:
        Season object ready for simulation
    """
    conf_map = conferences or {}
    team_conf_map = {}
    for conf_name, conf_teams in conf_map.items():
        for t in conf_teams:
            team_conf_map[t] = conf_name

    season = Season(
        name=name,
        teams=teams,
        style_configs=style_configs or {},
        conferences=conf_map,
        team_conferences=team_conf_map,
        team_states=team_states or {},
        coaching_staffs=coaching_staffs or {},
    )

    season.rivalries = rivalries or {}

    season.generate_schedule(
        games_per_team=games_per_team,
        pinned_matchups=pinned_matchups,
        dynasty_year=dynasty_year,
    )

    return season


STATE_NEIGHBORS: Dict[str, List[str]] = {
    "AL": ["FL","GA","MS","TN"],
    "AK": [],
    "AZ": ["CA","CO","NM","NV","UT"],
    "AR": ["LA","MO","MS","OK","TN","TX"],
    "CA": ["AZ","NV","OR"],
    "CO": ["AZ","KS","NE","NM","OK","UT","WY"],
    "CT": ["MA","NY","RI"],
    "DE": ["MD","NJ","PA"],
    "FL": ["AL","GA"],
    "GA": ["AL","FL","NC","SC","TN"],
    "HI": [],
    "ID": ["MT","NV","OR","UT","WA","WY"],
    "IL": ["IN","IA","KY","MO","WI"],
    "IN": ["IL","KY","MI","OH"],
    "IA": ["IL","MN","MO","NE","SD","WI"],
    "KS": ["CO","MO","NE","OK"],
    "KY": ["IL","IN","MO","OH","TN","VA","WV"],
    "LA": ["AR","MS","TX"],
    "ME": ["NH"],
    "MD": ["DE","PA","VA","WV","DC"],
    "MA": ["CT","NH","NY","RI","VT"],
    "MI": ["IN","OH","WI"],
    "MN": ["IA","ND","SD","WI"],
    "MS": ["AL","AR","LA","TN"],
    "MO": ["AR","IL","IA","KS","KY","NE","OK","TN"],
    "MT": ["ID","ND","SD","WY"],
    "NE": ["CO","IA","KS","MO","SD","WY"],
    "NV": ["AZ","CA","ID","OR","UT"],
    "NH": ["MA","ME","VT"],
    "NJ": ["DE","NY","PA"],
    "NM": ["AZ","CO","OK","TX","UT"],
    "NY": ["CT","MA","NJ","PA","VT"],
    "NC": ["GA","SC","TN","VA"],
    "ND": ["MN","MT","SD"],
    "OH": ["IN","KY","MI","PA","WV"],
    "OK": ["AR","CO","KS","MO","NM","TX"],
    "OR": ["CA","ID","NV","WA"],
    "PA": ["DE","MD","NJ","NY","OH","WV"],
    "RI": ["CT","MA"],
    "SC": ["GA","NC"],
    "SD": ["IA","MN","MT","ND","NE","WY"],
    "TN": ["AL","AR","GA","KY","MO","MS","NC","VA"],
    "TX": ["AR","LA","NM","OK"],
    "UT": ["AZ","CO","ID","NM","NV","WY"],
    "VT": ["MA","NH","NY"],
    "VA": ["KY","MD","NC","TN","WV","DC"],
    "WA": ["ID","OR"],
    "WV": ["KY","MD","OH","PA","VA"],
    "WI": ["IA","IL","MI","MN"],
    "WY": ["CO","ID","MT","NE","SD","UT"],
    "DC": ["MD","VA"],
    "BC": ["AB","WA"],
    "AB": ["BC","SK"],
    "SK": ["AB","MB"],
    "MB": ["SK","ON"],
    "ON": ["MB","QC","NY"],
    "QC": ["ON","NB","VT","ME","NH","NY"],
    "NB": ["QC","NS","ME"],
    "NS": ["NB"],
}


def _state_distance(s1: str, s2: str) -> int:
    if s1 == s2:
        return 0
    if s2 in STATE_NEIGHBORS.get(s1, []):
        return 1
    visited = {s1}
    frontier = [s1]
    depth = 0
    while frontier and depth < 8:
        depth += 1
        next_frontier = []
        for st in frontier:
            for nb in STATE_NEIGHBORS.get(st, []):
                if nb == s2:
                    return depth
                if nb not in visited:
                    visited.add(nb)
                    next_frontier.append(nb)
        frontier = next_frontier
    return 99


def auto_assign_rivalries(
    conferences: Dict[str, List[str]],
    team_states: Dict[str, str],
    human_team: Optional[str] = None,
    existing_rivalries: Optional[Dict[str, Dict[str, Optional[str]]]] = None,
) -> Dict[str, Dict[str, Optional[str]]]:
    """Auto-assign conference and non-conference rivals for AI teams.

    Uses state-based geographic proximity. Human team rivalries are preserved
    from existing_rivalries (not overwritten).

    Returns dict of team_name -> {"conference": rival_or_None, "non_conference": rival_or_None}
    """
    rivalries: Dict[str, Dict[str, Optional[str]]] = {}
    if existing_rivalries:
        for t, r in existing_rivalries.items():
            rivalries[t] = dict(r)

    team_conf: Dict[str, str] = {}
    for conf_name, members in conferences.items():
        for t in members:
            team_conf[t] = conf_name

    all_teams = list(team_conf.keys())
    claimed_conf: Dict[str, set] = {}
    claimed_nc: Dict[str, set] = {}
    for conf_name in conferences:
        claimed_conf[conf_name] = set()
    for t in all_teams:
        claimed_nc.setdefault(t, set())

    for t, r in rivalries.items():
        conf = team_conf.get(t, "")
        cr = r.get("conference")
        nr = r.get("non_conference")
        if cr and conf:
            claimed_conf.setdefault(conf, set()).add(cr)
            claimed_conf.setdefault(conf, set()).add(t)
        if nr:
            claimed_nc.setdefault(t, set()).add(nr)
            claimed_nc.setdefault(nr, set()).add(t)

    for team in all_teams:
        if team == human_team:
            continue
        if team in rivalries and rivalries[team].get("conference"):
            continue

        conf = team_conf.get(team, "")
        if not conf:
            continue
        conf_members = [t for t in conferences.get(conf, []) if t != team]
        if not conf_members:
            continue

        team_state = team_states.get(team, "")
        best_rival = None
        best_dist = 999
        for candidate in conf_members:
            if candidate == human_team:
                continue
            if candidate in claimed_conf.get(conf, set()):
                continue
            cand_state = team_states.get(candidate, "")
            if team_state and cand_state:
                dist = _state_distance(team_state, cand_state)
            else:
                dist = 50
            if dist < best_dist:
                best_dist = dist
                best_rival = candidate

        if best_rival:
            rivalries.setdefault(team, {"conference": None, "non_conference": None})
            rivalries[team]["conference"] = best_rival
            claimed_conf.setdefault(conf, set()).add(team)
            claimed_conf[conf].add(best_rival)
            rivalries.setdefault(best_rival, {"conference": None, "non_conference": None})
            if not rivalries[best_rival].get("conference"):
                rivalries[best_rival]["conference"] = team

    for team in all_teams:
        if team == human_team:
            continue
        if team in rivalries and rivalries[team].get("non_conference"):
            continue

        conf = team_conf.get(team, "")
        team_state = team_states.get(team, "")
        non_conf_teams = [t for t in all_teams if team_conf.get(t, "") != conf and t != team]
        if not non_conf_teams:
            continue

        best_rival = None
        best_dist = 999
        for candidate in non_conf_teams:
            if candidate == human_team:
                continue
            if candidate in claimed_nc.get(team, set()):
                continue
            if candidate in rivalries and rivalries[candidate].get("non_conference"):
                continue
            cand_state = team_states.get(candidate, "")
            if team_state and cand_state:
                dist = _state_distance(team_state, cand_state)
            else:
                dist = 50
            if dist < best_dist:
                best_dist = dist
                best_rival = candidate

        if best_rival:
            rivalries.setdefault(team, {"conference": None, "non_conference": None})
            rivalries[team]["non_conference"] = best_rival
            claimed_nc.setdefault(team, set()).add(best_rival)
            claimed_nc.setdefault(best_rival, set()).add(team)
            rivalries.setdefault(best_rival, {"conference": None, "non_conference": None})
            if not rivalries[best_rival].get("non_conference"):
                rivalries[best_rival]["non_conference"] = team

    return rivalries


# ── Fast History Simulation ──────────────────────────────────────────
# Generates lightweight season results (standings + champion) using
# team-rating-based win probability instead of full game simulation.
# ~1000x faster than running the game engine for every game.

def _team_avg_overall(team: Team) -> float:
    """Average player overall rating for a team."""
    if not team.players:
        return 60.0
    return sum(p.overall for p in team.players) / len(team.players)


def fast_sim_season(
    teams: Dict[str, Team],
    conferences: Dict[str, List[str]],
    games_per_team: int,
    rng: random.Random,
    playoff_size: int = 8,
) -> dict:
    """Simulate an entire season using rating-based outcomes (no game engine).

    Returns dict with keys: champion, runner_up, final_four, standings (list of dicts).
    """
    ratings = {name: _team_avg_overall(t) for name, t in teams.items()}
    team_names = list(teams.keys())

    records: Dict[str, dict] = {
        name: {"wins": 0, "losses": 0, "pf": 0.0, "pa": 0.0,
               "conf_wins": 0, "conf_losses": 0}
        for name in team_names
    }

    team_conf = {}
    for conf, members in conferences.items():
        for m in members:
            team_conf[m] = conf

    schedule = _fast_build_schedule(team_names, conferences, games_per_team, rng)

    for home, away, is_conf in schedule:
        winner, h_score, a_score = _fast_sim_game(home, away, ratings, rng)
        records[home]["pf"] += h_score
        records[home]["pa"] += a_score
        records[away]["pf"] += a_score
        records[away]["pa"] += h_score
        if winner == home:
            records[home]["wins"] += 1
            records[away]["losses"] += 1
            if is_conf:
                records[home]["conf_wins"] += 1
                records[away]["conf_losses"] += 1
        else:
            records[away]["wins"] += 1
            records[home]["losses"] += 1
            if is_conf:
                records[away]["conf_wins"] += 1
                records[home]["conf_losses"] += 1

    conf_champs = {}
    for conf, members in conferences.items():
        valid = [m for m in members if m in records]
        if valid:
            valid.sort(key=lambda n: (
                records[n]["conf_wins"],
                records[n]["wins"],
                records[n]["pf"] - records[n]["pa"],
            ), reverse=True)
            conf_champs[conf] = valid[0]

    ranked = sorted(
        team_names,
        key=lambda n: (records[n]["wins"], records[n]["pf"] - records[n]["pa"]),
        reverse=True,
    )

    playoff_pool = set(conf_champs.values())
    for name in ranked:
        if len(playoff_pool) >= playoff_size:
            break
        playoff_pool.add(name)
    playoff_list = sorted(playoff_pool, key=lambda n: ranked.index(n))[:playoff_size]

    champion, runner_up, final_four = _fast_sim_bracket(playoff_list, ratings, rng)

    return {
        "champion": champion,
        "runner_up": runner_up,
        "final_four": final_four,
        "_records": records,
        "_playoff_teams": set(playoff_list),
    }


def _fast_build_schedule(
    team_names: list,
    conferences: Dict[str, List[str]],
    games_per_team: int,
    rng: random.Random,
) -> List[tuple]:
    """Build a simplified schedule: (home, away, is_conference_game).

    Uses round-robin within conferences (capped) + random non-conf fill.
    Much faster than the full scheduler — no balancing needed for history.
    """
    games = []
    team_game_counts: Dict[str, int] = {n: 0 for n in team_names}
    team_conf = {}
    for conf, members in conferences.items():
        for m in members:
            team_conf[m] = conf

    conf_games_target = min(8, games_per_team)

    for conf, members in conferences.items():
        members = [m for m in members if m in team_game_counts]
        if len(members) < 2:
            continue
        pairs = []
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                pairs.append((members[i], members[j]))
        rng.shuffle(pairs)
        for a, b in pairs:
            if team_game_counts[a] >= conf_games_target:
                continue
            if team_game_counts[b] >= conf_games_target:
                continue
            home, away = (a, b) if rng.random() < 0.5 else (b, a)
            games.append((home, away, True))
            team_game_counts[a] += 1
            team_game_counts[b] += 1

    need_games = [n for n in team_names if team_game_counts[n] < games_per_team]
    rng.shuffle(need_games)
    attempts = 0
    max_attempts = len(team_names) * games_per_team
    while need_games and attempts < max_attempts:
        attempts += 1
        rng.shuffle(need_games)
        paired = set()
        for i in range(0, len(need_games) - 1, 2):
            a, b = need_games[i], need_games[i + 1]
            if a in paired or b in paired:
                continue
            home, away = (a, b) if rng.random() < 0.5 else (b, a)
            games.append((home, away, False))
            team_game_counts[a] += 1
            team_game_counts[b] += 1
            paired.add(a)
            paired.add(b)
        need_games = [n for n in team_names if team_game_counts[n] < games_per_team]

    return games


def _fast_sim_game(
    home: str, away: str,
    ratings: Dict[str, float],
    rng: random.Random,
) -> tuple:
    """Determine winner and approximate scores from team ratings.

    Returns (winner_name, home_score, away_score).
    """
    h_rat = ratings.get(home, 65.0)
    a_rat = ratings.get(away, 65.0)

    diff = h_rat - a_rat + rng.gauss(0, 8)
    home_advantage = 2.5
    diff += home_advantage

    base_score = 28 + rng.gauss(0, 8)
    h_score = max(0, base_score + diff * 0.6 + rng.gauss(0, 5))
    a_score = max(0, base_score - diff * 0.6 + rng.gauss(0, 5))

    h_score = round(h_score)
    a_score = round(a_score)
    if h_score == a_score:
        if diff >= 0:
            h_score += rng.choice([2, 3, 5])
        else:
            a_score += rng.choice([2, 3, 5])

    winner = home if h_score > a_score else away
    return winner, h_score, a_score


def _fast_sim_bracket(
    teams: list,
    ratings: Dict[str, float],
    rng: random.Random,
) -> tuple:
    """Single-elimination bracket simulation.

    Returns (champion, runner_up, final_four) tuple.
    final_four is ordered: [champion, runner_up, semi1_loser, semi2_loser].
    """
    if not teams:
        return "N/A", "N/A", []
    if len(teams) == 1:
        return teams[0], "N/A", [teams[0]]
    bracket = list(teams)
    semifinalists = []
    runner_up = "N/A"
    while len(bracket) > 1:
        next_round = []
        losers = []
        # Capture the Final Four: the 4 teams entering the semifinal round
        if len(bracket) == 4:
            semifinalists = list(bracket)
        for i in range(0, len(bracket) - 1, 2):
            winner, _, _ = _fast_sim_game(bracket[i], bracket[i + 1], ratings, rng)
            loser = bracket[i + 1] if winner == bracket[i] else bracket[i]
            next_round.append(winner)
            losers.append(loser)
        if len(bracket) % 2 == 1:
            next_round.append(bracket[-1])
        bracket = next_round
        # The last loser when bracket reaches the final is the runner-up
        if len(bracket) == 1:
            runner_up = losers[-1] if losers else "N/A"
    champion = bracket[0]
    # Build final_four list ordered: champion, runner_up, then the two semi losers
    if semifinalists:
        semi_losers = [t for t in semifinalists if t != champion and t != runner_up]
        final_four = [champion, runner_up] + semi_losers
    else:
        # Bracket had fewer than 4 teams
        final_four = [champion, runner_up]
    return champion, runner_up, final_four


def fast_generate_history(
    teams: Dict[str, Team],
    conferences: Dict[str, List[str]],
    num_years: int,
    games_per_team: int = 12,
    playoff_size: int = 8,
    base_seed: int = 42,
) -> list:
    """Generate num_years of fast-simulated history.

    Returns list of dicts: [{year, champion, runner_up, final_four}, ...]
    """
    rng = random.Random(base_seed)
    results = []
    for y in range(num_years):
        year = 2026 - num_years + y
        year_result = fast_sim_season(
            teams, conferences, games_per_team, rng, playoff_size,
        )
        year_result["year"] = year
        results.append(year_result)
    return results
