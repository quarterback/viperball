"""
FIV — Fédération Internationale de Viperball
==============================================

Women's international Viperball: continental championships, cross-confederation
playoff, and 32-team World Cup.  All games on the full ViperballEngine.

National team rosters pull from the CVL pipeline (USA/CAN) or are generated
per-nation with tier-appropriate attribute ranges.  Elo-style world rankings
persist across cycles.

Implements spec tasks T001–T007:
  T001  Data model
  T002  Roster generation (three-pathway: heritage, mercenary, homegrown)
  T003  Continental championship engine
  T004  Cross-confederation playoff
  T005  World Cup tournament
  T006  FIV World Rankings (Elo)
  T007  Persistence (SQLite via engine/db.py)
"""

from __future__ import annotations

import json
import logging
import math
import random
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engine.game_engine import (
    Player,
    Team,
    ViperballEngine,
    derive_halo,
)
from engine.weather import generate_game_weather

_log = logging.getLogger("viperball.fiv")

DATA_DIR = Path(__file__).parent.parent / "data"
_FIV_NATIONS_PATH = DATA_DIR / "fiv_nations.json"

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — loaded once from fiv_nations.json
# ═══════════════════════════════════════════════════════════════

_config_cache: Optional[dict] = None


def _load_config() -> dict:
    global _config_cache
    if _config_cache is None:
        with open(_FIV_NATIONS_PATH) as f:
            _config_cache = json.load(f)
    return _config_cache


# ═══════════════════════════════════════════════════════════════
# T001 — DATA MODEL
# ═══════════════════════════════════════════════════════════════

ROSTER_SIZE = 36

TIER_ATTRIBUTES = {
    "elite":       {"attr_lo": 70, "attr_hi": 95, "rating_lo": 85, "rating_hi": 95},
    "strong":      {"attr_lo": 60, "attr_hi": 88, "rating_lo": 72, "rating_hi": 84},
    "competitive": {"attr_lo": 50, "attr_hi": 80, "rating_lo": 58, "rating_hi": 71},
    "developing":  {"attr_lo": 40, "attr_hi": 72, "rating_lo": 40, "rating_hi": 57},
}

STARTING_ELO = {
    "elite": 1800,
    "strong": 1500,
    "competitive": 1200,
    "developing": 900,
}

POSITION_TEMPLATE = [
    "Viper", "Viper", "Viper",
    "Zeroback", "Zeroback", "Zeroback",
    "Halfback", "Halfback", "Halfback", "Halfback",
    "Wingback", "Wingback", "Wingback", "Wingback",
    "Slotback", "Slotback", "Slotback", "Slotback",
    "Keeper", "Keeper", "Keeper",
    "Offensive Line", "Offensive Line", "Offensive Line",
    "Offensive Line", "Offensive Line", "Offensive Line",
    "Offensive Line", "Offensive Line",
    "Defensive Line", "Defensive Line", "Defensive Line",
    "Defensive Line", "Defensive Line", "Defensive Line",
    "Defensive Line",
]

VARIANCE_ARCHETYPES = ["reliable", "explosive", "clutch"]

# ── CVL hometown_state → FIV nation code mapping ──
# The CVL name generator stores country codes in Player.hometown_state
# for international players.  This maps those codes to FIV nation codes.
# Some map 1:1 (JPN → JPN), others need translation (ZAF → RSA, PHL → PHI).
CVL_STATE_TO_FIV_CODE: Dict[str, str] = {
    # East Asian
    "JPN": "JPN", "KOR": "KOR", "TWN": "CHN",  # Taiwan → China team
    # Southeast Asian
    "THA": "THA", "VNM": "VEN",  # no Vietnam in FIV, skip — handled below
    "PHL": "PHI", "IDN": "INA", "SGP": "CHN", "MYS": "CHN",
    # African
    "NGA": "NGA", "GHA": "GHA", "SEN": "SEN", "CIV": "CIV",
    "GIN": "SEN", "MLI": "SEN", "TOG": "GHA",  # small → nearest FIV nation
    "KEN": "KEN", "UGA": "KEN", "TZA": "TAN",
    "ETH": "KEN", "RWA": "KEN",
    "ZAF": "RSA", "ZWE": "RSA", "ZMB": "RSA", "BWA": "RSA",
    # Caribbean
    "JAM": "JAM", "TTO": "TTO", "BRB": "JAM", "BAH": "JAM",
    "HAI": "HAI", "DOM": "DOM", "PRI": "USA",  # Puerto Rico → USA
    "GUY": "TTO", "SUR": "TTO",
    "LCA": "JAM", "DMA": "JAM", "SKN": "JAM", "GRN": "JAM", "BEL": "BEL",
    # Latin American
    "BRA": "BRA", "ARG": "ARG", "COL": "COL", "PER": "PER",
    "CHI": "CHI", "MEX": "MEX", "VEN": "VEN", "URU": "URU",
    "PAR": "PAR", "ECU": "ECU", "CRC": "CRC", "GTM": "GUA", "PAN": "PAN",
    # UK / European
    "ENG": "GBR", "SCO": "GBR", "WAL": "GBR", "NIR": "GBR",
    "FRA": "FRA", "GER": "GER", "ESP": "ESP", "NED": "NED",
    "BEL": "BEL", "POR": "POR", "ITA": "ITA",
    "SWE": "SWE", "NOR": "NOR", "DEN": "DEN",
    # Nordic
    "FIN": "FIN",
    # Australian / NZ
    "VIC": "AUS", "NSW": "AUS", "QLD": "AUS", "WA": "AUS", "SA": "AUS", "TAS": "AUS",
    # Canadian provinces → CAN
    "ON": "CAN", "BC": "CAN", "AB": "CAN", "QC": "CAN",
    "MB": "CAN", "SK": "CAN", "NS": "CAN", "NB": "CAN",
    "PE": "CAN", "NL": "CAN",
}

# Full country name → FIV code (backup mapping via hometown_country)
CVL_COUNTRY_TO_FIV_CODE: Dict[str, str] = {
    "United States": "USA", "USA": "USA", "Canada": "CAN",
    "Japan": "JPN", "South Korea": "KOR", "China": "CHN",
    "Thailand": "THA", "Philippines": "PHI", "Indonesia": "INA",
    "Australia": "AUS", "New Zealand": "NZL",
    "Nigeria": "NGA", "Ghana": "GHA", "Kenya": "KEN",
    "South Africa": "RSA", "Tanzania": "TAN", "Senegal": "SEN",
    "Côte d'Ivoire": "CIV", "Cameroon": "CMR",
    "Jamaica": "JAM", "Trinidad and Tobago": "TTO",
    "Haiti": "HAI", "Dominican Republic": "DOM",
    "Brazil": "BRA", "Argentina": "ARG", "Colombia": "COL",
    "Peru": "PER", "Chile": "CHI", "Mexico": "MEX",
    "Venezuela": "VEN", "Uruguay": "URU", "Paraguay": "PAR",
    "Ecuador": "ECU", "Costa Rica": "CRC", "Guatemala": "GUA", "Panama": "PAN",
    "England": "GBR", "Scotland": "GBR", "Wales": "GBR",
    "United Kingdom": "GBR", "Northern Ireland": "GBR",
    "France": "FRA", "Germany": "GER", "Spain": "ESP",
    "Netherlands": "NED", "Belgium": "BEL", "Portugal": "POR",
    "Italy": "ITA", "Ireland": "IRL",
    "Sweden": "SWE", "Norway": "NOR", "Denmark": "DEN", "Finland": "FIN",
    "Nordic": "SWE", "Europe": "GER",
    "Pacific Islands": "FIJ", "Fiji": "FIJ", "Samoa": "SAM",
    "Cuba": "CUB", "Papua New Guinea": "PNG",
    "Egypt": "EGY", "Morocco": "MAR", "Saudi Arabia": "KSA",
    "Iran": "IRN", "Israel": "ISR", "UAE": "UAE",
    "Russia": "RUS", "Turkey": "TUR", "India": "IND",
    "Mongolia": "MGL", "Kazakhstan": "KAZ", "Uzbekistan": "UZB",
    "Poland": "POL", "Czech Republic": "CZE", "Ukraine": "UKR",
    "Honduras": "HON",
}


def _resolve_fiv_code(player: "Player") -> Optional[str]:
    """Determine the FIV nation code a CVL player is eligible for.

    Uses hometown_state first (more specific), then hometown_country.
    Returns None if the player cannot be mapped to any FIV nation.
    """
    # Try hometown_state first (e.g. JPN, NGA, JAM, ENG)
    state = getattr(player, "hometown_state", "") or ""
    if state:
        code = CVL_STATE_TO_FIV_CODE.get(state)
        if code:
            return code

    # Fallback to hometown_country
    country = getattr(player, "hometown_country", "") or ""
    if country:
        code = CVL_COUNTRY_TO_FIV_CODE.get(country)
        if code:
            return code

    return None


@dataclass
class NationInfo:
    """Static metadata for a national team."""
    name: str
    code: str
    tier: str
    confederation: str
    name_pool: str


@dataclass
class NationalTeamPlayer:
    """A player on a national team roster with continuity fields."""
    player: Player
    nationalities: List[str] = field(default_factory=lambda: ["USA"])
    active_national_team: Optional[str] = None
    naturalized: bool = False
    eligibility_locked: bool = False
    cvl_source: Optional[str] = None
    age: int = 22
    caps: int = 0
    career_international_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        p = self.player
        return {
            "name": p.name,
            "player_id": p.player_id,
            "position": p.position,
            "overall": p.overall,
            "archetype": p.archetype,
            "variance_archetype": p.variance_archetype,
            "speed": p.speed,
            "stamina": p.stamina,
            "kicking": p.kicking,
            "lateral_skill": p.lateral_skill,
            "tackling": p.tackling,
            "agility": p.agility,
            "power": p.power,
            "awareness": p.awareness,
            "hands": p.hands,
            "kick_power": p.kick_power,
            "kick_accuracy": p.kick_accuracy,
            "height": p.height,
            "weight": p.weight,
            "nationalities": self.nationalities,
            "active_national_team": self.active_national_team,
            "naturalized": self.naturalized,
            "eligibility_locked": self.eligibility_locked,
            "cvl_source": self.cvl_source,
            "age": self.age,
            "caps": self.caps,
            "career_international_stats": self.career_international_stats,
        }


@dataclass
class NationalTeam:
    """A national team with roster and metadata."""
    nation: NationInfo
    roster: List[NationalTeamPlayer] = field(default_factory=list)
    rating: int = 50  # 0-99 national team rating
    coaching_staff: Optional[dict] = None

    @property
    def code(self) -> str:
        return self.nation.code

    @property
    def name(self) -> str:
        return self.nation.name

    @property
    def tier(self) -> str:
        return self.nation.tier

    def to_engine_team(self) -> Team:
        """Build a Team object for the game engine."""
        players = [ntp.player for ntp in self.roster]
        if not players:
            raise ValueError(f"No players on {self.name} roster")

        avg_speed = sum(p.speed for p in players) // len(players)
        avg_stamina = sum(p.stamina for p in players) // len(players)
        kicking = sum(p.kicking for p in players) // len(players)
        lateral = sum(p.lateral_skill for p in players) // len(players)
        defense = sum(p.tackling for p in players) // len(players)

        prestige = self.rating
        h_off, h_def = derive_halo(prestige)

        return Team(
            name=self.name,
            abbreviation=self.code,
            mascot=self.name,
            players=players,
            avg_speed=avg_speed,
            avg_stamina=avg_stamina,
            kicking_strength=kicking,
            lateral_proficiency=lateral,
            defensive_strength=defense,
            offense_style="balanced",
            defense_style="swarm",
            st_scheme="aces",
            prestige=prestige,
            halo_offense=h_off,
            halo_defense=h_def,
        )

    def to_dict(self) -> dict:
        return {
            "nation": {
                "name": self.nation.name,
                "code": self.nation.code,
                "tier": self.nation.tier,
                "confederation": self.nation.confederation,
                "name_pool": self.nation.name_pool,
            },
            "roster": [ntp.to_dict() for ntp in self.roster],
            "rating": self.rating,
        }


@dataclass
class MatchResult:
    """Result of a single international match."""
    match_id: str
    home_code: str
    away_code: str
    home_score: float
    away_score: float
    winner: str  # nation code or "draw"
    competition: str  # "continental", "playoff", "wc_group", "wc_knockout"
    stage: str  # "group_A", "quarterfinal", etc.
    game_result: Optional[dict] = None  # slimmed engine output

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "home_code": self.home_code,
            "away_code": self.away_code,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "winner": self.winner,
            "competition": self.competition,
            "stage": self.stage,
            "game_result": _slim_result(self.game_result) if self.game_result else None,
        }


def _slim_result(result: dict) -> dict:
    """Keep scores, stats, player_stats, drives, and play-by-play."""
    slim: dict = {}
    for key in ("final_score", "stats", "player_stats", "weather",
                "home_team_name", "away_team_name",
                "home_team_abbrev", "away_team_abbrev",
                "drive_summary", "play_by_play",
                "in_game_injuries"):
        if key in result:
            slim[key] = result[key]
    return slim


@dataclass
class GroupStandings:
    """Round-robin group standings for a set of teams."""
    group_name: str
    teams: List[str]  # nation codes
    results: List[MatchResult] = field(default_factory=list)
    table: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def init_table(self):
        for code in self.teams:
            self.table[code] = {
                "played": 0, "won": 0, "drawn": 0, "lost": 0,
                "points_for": 0, "points_against": 0, "point_diff": 0,
                "points": 0,  # 3 for win, 1 for draw
            }

    def record_result(self, result: MatchResult):
        self.results.append(result)
        h, a = result.home_code, result.away_code
        hs, as_ = int(result.home_score), int(result.away_score)
        for code in (h, a):
            if code not in self.table:
                continue
            self.table[code]["played"] += 1
        if h in self.table:
            self.table[h]["points_for"] += hs
            self.table[h]["points_against"] += as_
            self.table[h]["point_diff"] = self.table[h]["points_for"] - self.table[h]["points_against"]
        if a in self.table:
            self.table[a]["points_for"] += as_
            self.table[a]["points_against"] += hs
            self.table[a]["point_diff"] = self.table[a]["points_for"] - self.table[a]["points_against"]

        if hs > as_:
            if h in self.table:
                self.table[h]["won"] += 1
                self.table[h]["points"] += 3
            if a in self.table:
                self.table[a]["lost"] += 1
        elif as_ > hs:
            if a in self.table:
                self.table[a]["won"] += 1
                self.table[a]["points"] += 3
            if h in self.table:
                self.table[h]["lost"] += 1
        else:
            for code in (h, a):
                if code in self.table:
                    self.table[code]["drawn"] += 1
                    self.table[code]["points"] += 1

    def ranked_teams(self) -> List[str]:
        """Return team codes sorted by points, then point diff, then points for."""
        return sorted(
            self.teams,
            key=lambda c: (
                self.table.get(c, {}).get("points", 0),
                self.table.get(c, {}).get("point_diff", 0),
                self.table.get(c, {}).get("points_for", 0),
            ),
            reverse=True,
        )

    def to_dict(self) -> dict:
        return {
            "group_name": self.group_name,
            "teams": self.teams,
            "results": [r.to_dict() for r in self.results],
            "table": self.table,
            "ranked": self.ranked_teams(),
        }


@dataclass
class KnockoutBracket:
    """Single-elimination knockout bracket."""
    round_name: str
    matchups: List[Dict[str, Any]] = field(default_factory=list)
    completed: bool = False

    def to_dict(self) -> dict:
        return {
            "round_name": self.round_name,
            "matchups": self.matchups,
            "completed": self.completed,
        }


@dataclass
class ContinentalChampionship:
    """A confederation's championship tournament."""
    confederation: str
    conf_full_name: str
    nations: List[str]  # nation codes
    wc_spots: int
    groups: List[GroupStandings] = field(default_factory=list)
    knockout_rounds: List[KnockoutBracket] = field(default_factory=list)
    qualifiers: List[str] = field(default_factory=list)
    champion: Optional[str] = None
    all_results: List[MatchResult] = field(default_factory=list)
    phase: str = "not_started"  # not_started, groups, knockout, completed
    current_group_matchday: int = 0
    current_knockout_round: int = 0
    non_qualifiers: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "confederation": self.confederation,
            "conf_full_name": self.conf_full_name,
            "nations": self.nations,
            "wc_spots": self.wc_spots,
            "groups": [g.to_dict() for g in self.groups],
            "knockout_rounds": [k.to_dict() for k in self.knockout_rounds],
            "qualifiers": self.qualifiers,
            "champion": self.champion,
            "phase": self.phase,
            "current_group_matchday": self.current_group_matchday,
            "current_knockout_round": self.current_knockout_round,
            "non_qualifiers": self.non_qualifiers,
        }


@dataclass
class CrossConfederationPlayoff:
    """Playoff for 4 remaining World Cup spots."""
    teams: List[str] = field(default_factory=list)
    bracket: List[KnockoutBracket] = field(default_factory=list)
    qualifiers: List[str] = field(default_factory=list)
    phase: str = "not_started"
    all_results: List[MatchResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "teams": self.teams,
            "bracket": [k.to_dict() for k in self.bracket],
            "qualifiers": self.qualifiers,
            "phase": self.phase,
        }


@dataclass
class WorldCup:
    """32-team FIV World Cup."""
    host: str  # nation code
    teams: List[str] = field(default_factory=list)
    seed_pots: Dict[str, List[str]] = field(default_factory=dict)
    groups: List[GroupStandings] = field(default_factory=list)
    knockout_rounds: List[KnockoutBracket] = field(default_factory=list)
    champion: Optional[str] = None
    third_place: Optional[str] = None
    golden_boot: Optional[dict] = None
    mvp: Optional[dict] = None
    all_results: List[MatchResult] = field(default_factory=list)
    phase: str = "not_started"  # not_started, draw, groups, knockout, completed
    current_group_matchday: int = 0
    current_knockout_round: int = 0

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "teams": self.teams,
            "seed_pots": self.seed_pots,
            "groups": [g.to_dict() for g in self.groups],
            "knockout_rounds": [k.to_dict() for k in self.knockout_rounds],
            "champion": self.champion,
            "third_place": self.third_place,
            "golden_boot": self.golden_boot,
            "mvp": self.mvp,
            "phase": self.phase,
            "current_group_matchday": self.current_group_matchday,
            "current_knockout_round": self.current_knockout_round,
        }


@dataclass
class FIVRankings:
    """Elo-style world rankings for all member nations."""
    ratings: Dict[str, float] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def init_from_tiers(self, nations: Dict[str, NationInfo]):
        for code, info in nations.items():
            self.ratings[code] = float(STARTING_ELO.get(info.tier, 900))

    def expected_result(self, team_rating: float, opponent_rating: float) -> float:
        return 1.0 / (1.0 + 10.0 ** ((opponent_rating - team_rating) / 400.0))

    def update(self, team_code: str, opponent_code: str,
               actual: float, match_weight: float = 1.0):
        """Update ratings after a match.

        actual: 1.0 = win, 0.5 = draw/OT loss, 0.0 = loss
        """
        K = 8.0
        tr = self.ratings.get(team_code, 1200.0)
        opp_r = self.ratings.get(opponent_code, 1200.0)
        expected = self.expected_result(tr, opp_r)
        delta = K * (actual - expected) * match_weight
        self.ratings[team_code] = tr + delta
        self.ratings[opponent_code] = opp_r - delta

    def update_from_result(self, result: MatchResult, competition: str):
        """Update ratings from a match result with appropriate weight."""
        weight_map = {
            "continental_group": 1.0,
            "continental_knockout": 1.5,
            "playoff": 1.5,
            "wc_group": 2.0,
            "wc_knockout": 3.0,
            "wc_semifinal": 4.0,
            "wc_final": 4.0,
        }
        weight = weight_map.get(competition, 1.0)
        if result.winner == result.home_code:
            self.update(result.home_code, result.away_code, 1.0, weight)
        elif result.winner == result.away_code:
            self.update(result.away_code, result.home_code, 1.0, weight)
        else:
            self.update(result.home_code, result.away_code, 0.5, weight)

    def get_ranked_list(self) -> List[Tuple[int, str, float]]:
        """Return [(rank, code, rating), ...] sorted by rating descending."""
        sorted_codes = sorted(self.ratings.items(), key=lambda x: -x[1])
        return [(i + 1, code, rating) for i, (code, rating) in enumerate(sorted_codes)]

    def snapshot(self) -> dict:
        return dict(self.ratings)

    def to_dict(self) -> dict:
        return {
            "ratings": self.ratings,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FIVRankings":
        r = cls()
        r.ratings = {k: float(v) for k, v in data.get("ratings", {}).items()}
        r.history = data.get("history", [])
        return r


@dataclass
class FIVCycle:
    """One complete FIV cycle: continental → playoff → World Cup."""
    cycle_number: int = 1
    national_teams: Dict[str, NationalTeam] = field(default_factory=dict)
    confederations_data: Dict[str, ContinentalChampionship] = field(default_factory=dict)
    playoff: Optional[CrossConfederationPlayoff] = None
    world_cup: Optional[WorldCup] = None
    rankings: Optional[FIVRankings] = None
    rankings_before: Optional[dict] = None
    phase: str = "roster_generation"
    # phases: roster_generation, continental, playoff, wc_draw,
    #         wc_groups, wc_knockout, completed
    host_nation: Optional[str] = None
    cvl_season_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "cycle_number": self.cycle_number,
            "national_teams": {c: nt.to_dict() for c, nt in self.national_teams.items()},
            "confederations_data": {c: cc.to_dict() for c, cc in self.confederations_data.items()},
            "playoff": self.playoff.to_dict() if self.playoff else None,
            "world_cup": self.world_cup.to_dict() if self.world_cup else None,
            "rankings": self.rankings.to_dict() if self.rankings else None,
            "rankings_before": self.rankings_before,
            "phase": self.phase,
            "host_nation": self.host_nation,
            "cvl_season_id": self.cvl_season_id,
        }


# ═══════════════════════════════════════════════════════════════
# T002 — ROSTER GENERATION
# ═══════════════════════════════════════════════════════════════

def _load_all_nations() -> Dict[str, NationInfo]:
    """Load all nations from config file."""
    cfg = _load_config()
    nations: Dict[str, NationInfo] = {}
    for conf_id, conf_data in cfg["confederations"].items():
        for n in conf_data["nations"]:
            nations[n["code"]] = NationInfo(
                name=n["name"],
                code=n["code"],
                tier=n["tier"],
                confederation=conf_id,
                name_pool=n["name_pool"],
            )
    return nations


def _generate_player_for_nation(
    nation: NationInfo,
    position: str,
    rng: random.Random,
    number: int = 0,
) -> Player:
    """Generate a single player for a national team using tier-based attributes."""
    tier_data = TIER_ATTRIBUTES[nation.tier]
    lo, hi = tier_data["attr_lo"], tier_data["attr_hi"]

    def _attr() -> int:
        # Gaussian centered in tier range
        center = (lo + hi) / 2
        spread = (hi - lo) / 4
        return max(lo, min(hi, int(rng.gauss(center, spread))))

    try:
        from scripts.generate_names import generate_player_name
        name_data = generate_player_name(
            origin=nation.name_pool if nation.name_pool != "american" else None,
            gender="female",
        )
        full_name = name_data.get("full_name", f"Player {number}")
    except Exception:
        full_name = f"Player {number}"

    player_id = str(uuid.uuid4())[:8]

    speed = _attr()
    stamina = _attr()
    kicking = _attr()
    lateral_skill = _attr()
    tackling = _attr()
    agility = _attr()
    power = _attr()
    awareness = _attr()
    hands = _attr()
    kick_power = _attr()
    kick_accuracy = _attr()

    # Assign archetype based on stats
    try:
        from engine.game_engine import assign_archetype
        archetype = assign_archetype(position, speed, stamina, kicking, lateral_skill, tackling)
    except Exception:
        archetype = "none"

    variance = rng.choice(VARIANCE_ARCHETYPES)

    # Generate physical attributes based on position
    height_inches = rng.randint(63, 75)  # 5'3" to 6'3"
    height = f"{height_inches // 12}-{height_inches % 12}"
    weight = rng.randint(130, 210)

    return Player(
        number=number,
        name=full_name,
        position=position,
        speed=speed,
        stamina=stamina,
        kicking=kicking,
        lateral_skill=lateral_skill,
        tackling=tackling,
        agility=agility,
        power=power,
        awareness=awareness,
        hands=hands,
        kick_power=kick_power,
        kick_accuracy=kick_accuracy,
        player_id=player_id,
        nationality=nation.name,
        hometown_country=nation.code,
        archetype=archetype,
        variance_archetype=variance,
        height=height,
        weight=weight,
        year="Senior",
    )


def _generate_full_roster(
    nation: NationInfo,
    rng: random.Random,
) -> List[NationalTeamPlayer]:
    """Generate a full 36-player roster for a nation."""
    used_numbers: set = set()
    roster: List[NationalTeamPlayer] = []

    for i, position in enumerate(POSITION_TEMPLATE):
        num = i + 1
        while num in used_numbers:
            num = rng.randint(1, 99)
        used_numbers.add(num)

        player = _generate_player_for_nation(nation, position, rng, number=num)
        ntp = NationalTeamPlayer(
            player=player,
            nationalities=[nation.code],
            active_national_team=nation.code,
            naturalized=False,
            eligibility_locked=False,
            age=rng.randint(19, 30),
        )
        roster.append(ntp)

    return roster


def _compute_team_rating(roster: List[NationalTeamPlayer]) -> int:
    """Compute national team rating from roster (avg of top 20 overalls, scaled)."""
    if not roster:
        return 50
    overalls = sorted([ntp.player.overall for ntp in roster], reverse=True)
    top_20 = overalls[:min(20, len(overalls))]
    avg = sum(top_20) / len(top_20)
    # Scale from ~40-95 attribute range to 0-99 rating
    return max(0, min(99, int(avg)))


def generate_national_teams(
    cvl_players: Optional[List[Player]] = None,
    rng: Optional[random.Random] = None,
) -> Dict[str, NationalTeam]:
    """Generate all national teams.

    CVL pipeline: every CVL player is mapped to a FIV nation via
    ``_resolve_fiv_code`` (hometown_state → FIV code).  International CVL
    players (e.g. a Japanese-origin player at Gonzaga) are routed to their
    home nation's team.  USA/CAN fill entirely from CVL when available;
    other nations get CVL players mixed with generated depth.

    Args:
        cvl_players: Optional list of all CVL players from a completed season
        rng: Random instance for reproducibility
    """
    if rng is None:
        rng = random.Random()

    all_nations = _load_all_nations()
    cfg = _load_config()
    teams: Dict[str, NationalTeam] = {}

    # Track claimed players to prevent dual-selection
    claimed_player_ids: set = set()

    # --- Phase 1: Route ALL CVL players to their eligible nations ---
    # Build per-nation buckets of CVL players sorted by overall
    cvl_by_nation: Dict[str, List[Player]] = {}
    if cvl_players:
        for p in cvl_players:
            fiv_code = _resolve_fiv_code(p)
            if fiv_code and fiv_code in all_nations:
                cvl_by_nation.setdefault(fiv_code, []).append(p)
        # Sort each bucket by overall descending
        for code in cvl_by_nation:
            cvl_by_nation[code].sort(key=lambda p: -p.overall)

        _log.info(
            f"CVL pipeline: {len(cvl_players)} total players, "
            f"{sum(len(v) for v in cvl_by_nation.values())} mapped to "
            f"{len(cvl_by_nation)} nations"
        )

    # --- Phase 1b: Build rosters from CVL players + generated depth ---
    for code, nation_info in all_nations.items():
        cvl_pool = cvl_by_nation.get(code, [])
        cvl_roster: List[NationalTeamPlayer] = []

        for p in cvl_pool:
            if p.player_id in claimed_player_ids:
                continue
            if len(cvl_roster) >= ROSTER_SIZE:
                break
            ntp = NationalTeamPlayer(
                player=deepcopy(p),
                nationalities=[code],
                active_national_team=code,
                cvl_source=getattr(p, '_team_name', None),
                age=_year_to_age(p.year, rng),
            )
            cvl_roster.append(ntp)
            claimed_player_ids.add(p.player_id)

        # Fill remaining slots with generated players at tier level
        remaining = ROSTER_SIZE - len(cvl_roster)
        if remaining > 0:
            gen = _generate_full_roster(nation_info, rng)
            cvl_roster.extend(gen[:remaining])

        roster = cvl_roster[:ROSTER_SIZE]
        nt = NationalTeam(nation=nation_info, roster=roster)

        # Rating: if mostly CVL players, compute from roster; otherwise use tier
        if len(cvl_pool) >= ROSTER_SIZE // 2:
            nt.rating = _compute_team_rating(roster)
        else:
            tier_data = TIER_ATTRIBUTES[nation_info.tier]
            nt.rating = rng.randint(tier_data["rating_lo"], tier_data["rating_hi"])
            # Boost slightly if CVL players are present
            if cvl_pool:
                cvl_boost = min(5, len(cvl_pool))
                nt.rating = min(99, nt.rating + cvl_boost)

        teams[code] = nt

        if cvl_pool:
            _log.debug(
                f"{code}: {len([r for r in roster if r.cvl_source])} CVL, "
                f"{remaining} generated, rating={nt.rating}"
            )

    # --- Phase 3: Mercenary naturalization ---
    merc_cfg = cfg.get("mercenary_nations", {})
    unclaimed_pool: List[NationalTeamPlayer] = []
    # Build pool of unclaimed generated players for mercenary system
    for code, nt in teams.items():
        for ntp in nt.roster:
            if not ntp.eligibility_locked and len(ntp.nationalities) == 1:
                unclaimed_pool.append(ntp)

    for tier_name, tier_cfg in merc_cfg.items():
        max_nat = tier_cfg["max_naturalized"]
        min_ovr = tier_cfg["min_overall_threshold"]
        for nation_code in tier_cfg["nations"]:
            if nation_code not in teams:
                continue
            nt = teams[nation_code]
            # Count existing naturalized
            current_nat = sum(1 for ntp in nt.roster if ntp.naturalized)
            slots = max_nat - current_nat
            if slots <= 0:
                continue
            # Find eligible high-talent unclaimed players from other nations
            candidates = [
                ntp for ntp in unclaimed_pool
                if ntp.player.overall >= min_ovr
                and nation_code not in ntp.nationalities
                and not ntp.eligibility_locked
            ]
            rng.shuffle(candidates)
            added = 0
            for cand in candidates[:slots]:
                # "Naturalize" — add to this nation's roster
                merc_player = NationalTeamPlayer(
                    player=deepcopy(cand.player),
                    nationalities=cand.nationalities + [nation_code],
                    active_national_team=nation_code,
                    naturalized=True,
                    age=cand.age,
                )
                # Replace weakest player on roster
                if len(nt.roster) >= ROSTER_SIZE:
                    weakest_idx = min(
                        range(len(nt.roster)),
                        key=lambda i: nt.roster[i].player.overall,
                    )
                    if merc_player.player.overall > nt.roster[weakest_idx].player.overall:
                        nt.roster[weakest_idx] = merc_player
                        added += 1
                else:
                    nt.roster.append(merc_player)
                    added += 1
            if added > 0:
                _log.debug(f"Naturalized {added} players for {nation_code}")

    # --- Phase 4: Generate coaching staffs ---
    for code, nt in teams.items():
        try:
            from engine.coaching import generate_coaching_staff
            staff = generate_coaching_staff(
                team_name=nt.name,
                prestige=nt.rating,
            )
            nt.coaching_staff = {role: _coach_to_dict(card) for role, card in staff.items()}
        except Exception:
            nt.coaching_staff = None

    return teams


def _year_to_age(year: str, rng: random.Random) -> int:
    """Convert college year to approximate age."""
    base = {"Freshman": 18, "Sophomore": 19, "Junior": 20, "Senior": 21}
    return base.get(year, 20) + rng.randint(0, 1)


def _coach_to_dict(card) -> dict:
    """Convert a CoachCard to a simple dict."""
    return {
        "coach_id": card.coach_id,
        "first_name": card.first_name,
        "last_name": card.last_name,
        "role": card.role,
        "classification": card.classification,
        "overall": card.overall,
    }


# ═══════════════════════════════════════════════════════════════
# T003 — CONTINENTAL CHAMPIONSHIP ENGINE
# ═══════════════════════════════════════════════════════════════

def _play_match(
    home_team: NationalTeam,
    away_team: NationalTeam,
    competition: str,
    stage: str,
    rankings: Optional[FIVRankings] = None,
    rng: Optional[random.Random] = None,
) -> MatchResult:
    """Play a single international match using the full ViperballEngine."""
    home_engine = home_team.to_engine_team()
    away_engine = away_team.to_engine_team()

    # Generate weather
    weather_key = "clear"
    try:
        weather_data = generate_game_weather(season_month="June")
        weather_key = weather_data.get("condition", "clear")
    except Exception:
        pass

    seed = rng.randint(1, 999999) if rng else random.randint(1, 999999)

    engine = ViperballEngine(
        home_team=home_engine,
        away_team=away_engine,
        seed=seed,
        weather=weather_key,
        neutral_site=True,  # International matches are neutral site
        home_prestige=home_team.rating,
        away_prestige=away_team.rating,
        is_playoff=(competition in ("wc_knockout", "continental_knockout", "playoff")),
    )
    result = engine.simulate_game()

    home_score = result["final_score"]["home"]["score"]
    away_score = result["final_score"]["away"]["score"]

    if home_score > away_score:
        winner = home_team.code
    elif away_score > home_score:
        winner = away_team.code
    else:
        # Tiebreaker for knockout games: whoever has more TDs wins
        # If still tied, coin flip
        home_tds = result.get("stats", {}).get("home", {}).get("touchdowns", 0)
        away_tds = result.get("stats", {}).get("away", {}).get("touchdowns", 0)
        if competition in ("wc_knockout", "continental_knockout", "playoff", "wc_semifinal", "wc_final"):
            if home_tds > away_tds:
                winner = home_team.code
            elif away_tds > home_tds:
                winner = away_team.code
            else:
                # Coin flip for knockout ties
                winner = home_team.code if (rng or random).random() < 0.5 else away_team.code
            # Award extra point to winner for tie resolution
            if winner == home_team.code:
                home_score += 1
            else:
                away_score += 1
        else:
            winner = "draw"

    match_id = str(uuid.uuid4())[:12]

    # Update caps for all players
    for ntp in home_team.roster:
        ntp.caps += 1
        ntp.eligibility_locked = True
    for ntp in away_team.roster:
        ntp.caps += 1
        ntp.eligibility_locked = True

    # Update rankings
    if rankings:
        rankings.update_from_result(
            MatchResult(
                match_id=match_id,
                home_code=home_team.code,
                away_code=away_team.code,
                home_score=home_score,
                away_score=away_score,
                winner=winner,
                competition=competition,
                stage=stage,
            ),
            competition,
        )

    return MatchResult(
        match_id=match_id,
        home_code=home_team.code,
        away_code=away_team.code,
        home_score=home_score,
        away_score=away_score,
        winner=winner,
        competition=competition,
        stage=stage,
        game_result=result,
    )


def _create_groups(nation_codes: List[str], num_groups: int, rng: random.Random) -> List[GroupStandings]:
    """Divide nations into groups."""
    shuffled = list(nation_codes)
    rng.shuffle(shuffled)
    groups: List[GroupStandings] = []
    for i in range(num_groups):
        group_name = chr(65 + i)  # A, B, C, ...
        group_teams = shuffled[i::num_groups]
        g = GroupStandings(group_name=group_name, teams=group_teams)
        g.init_table()
        groups.append(g)
    return groups


def _group_matchdays(group: GroupStandings) -> List[Tuple[str, str]]:
    """Generate all round-robin matchups for a group."""
    teams = group.teams
    matchups = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            matchups.append((teams[i], teams[j]))
    return matchups


def create_continental_championship(
    confederation: str,
    national_teams: Dict[str, NationalTeam],
) -> ContinentalChampionship:
    """Initialize a continental championship for a given confederation."""
    cfg = _load_config()
    conf_cfg = cfg["confederations"][confederation]
    nation_codes = [n["code"] for n in conf_cfg["nations"]]

    # Determine group structure based on confederation size
    n = len(nation_codes)
    if n <= 10:
        num_groups = 2
    elif n <= 12:
        num_groups = 4  # groups of 3
    else:
        num_groups = 4  # groups of 3-4

    cc = ContinentalChampionship(
        confederation=confederation,
        conf_full_name=conf_cfg["full_name"],
        nations=nation_codes,
        wc_spots=conf_cfg["wc_spots"],
        phase="not_started",
    )
    return cc


def run_continental_championship(
    cc: ContinentalChampionship,
    national_teams: Dict[str, NationalTeam],
    rankings: FIVRankings,
    rng: Optional[random.Random] = None,
) -> ContinentalChampionship:
    """Run an entire continental championship to completion."""
    if rng is None:
        rng = random.Random()

    n = len(cc.nations)
    if n <= 10:
        num_groups = 2
    elif n <= 12:
        num_groups = 4
    else:
        num_groups = 4

    # --- Group stage ---
    cc.groups = _create_groups(cc.nations, num_groups, rng)
    cc.phase = "groups"

    for group in cc.groups:
        matchups = _group_matchdays(group)
        for home_code, away_code in matchups:
            if home_code not in national_teams or away_code not in national_teams:
                continue
            result = _play_match(
                national_teams[home_code],
                national_teams[away_code],
                competition="continental_group",
                stage=f"group_{group.group_name}",
                rankings=rankings,
                rng=rng,
            )
            group.record_result(result)
            cc.all_results.append(result)

    # --- Determine knockout qualifiers ---
    # Top 2 from each group advance
    knockout_teams: List[str] = []
    for group in cc.groups:
        ranked = group.ranked_teams()
        advance = min(2, len(ranked))
        knockout_teams.extend(ranked[:advance])

    # --- Knockout stage ---
    cc.phase = "knockout"
    round_num = 0

    while len(knockout_teams) > 1:
        round_names = {8: "Quarterfinals", 4: "Semifinals", 2: "Final"}
        round_name = round_names.get(len(knockout_teams), f"Round of {len(knockout_teams)}")

        bracket = KnockoutBracket(round_name=round_name)
        next_round: List[str] = []

        for i in range(0, len(knockout_teams), 2):
            if i + 1 >= len(knockout_teams):
                next_round.append(knockout_teams[i])
                bracket.matchups.append({
                    "home": knockout_teams[i], "away": "BYE",
                    "winner": knockout_teams[i], "result": None,
                })
                continue

            home_code = knockout_teams[i]
            away_code = knockout_teams[i + 1]

            result = _play_match(
                national_teams[home_code],
                national_teams[away_code],
                competition="continental_knockout",
                stage=round_name.lower().replace(" ", "_"),
                rankings=rankings,
                rng=rng,
            )
            cc.all_results.append(result)
            bracket.matchups.append({
                "home": home_code, "away": away_code,
                "winner": result.winner,
                "home_score": result.home_score,
                "away_score": result.away_score,
                "match_id": result.match_id,
                "result": result.to_dict(),
            })
            next_round.append(result.winner)

        bracket.completed = True
        cc.knockout_rounds.append(bracket)
        knockout_teams = next_round
        round_num += 1

    # --- Determine champion and qualifiers ---
    if knockout_teams:
        cc.champion = knockout_teams[0]

    # Qualifiers: ranked by tournament performance
    # Champion + runner-up + semifinalists + best group stage performers
    all_finishers: List[str] = []

    # Walk knockout rounds backwards to build finish order
    for kr in reversed(cc.knockout_rounds):
        for m in kr.matchups:
            if m.get("winner") and m["winner"] not in all_finishers:
                all_finishers.append(m["winner"])
            # Losers come after winners at each round
        for m in kr.matchups:
            loser = m["away"] if m.get("winner") == m["home"] else m["home"]
            if loser and loser != "BYE" and loser not in all_finishers:
                all_finishers.append(loser)

    # Add remaining teams from group stage
    for group in cc.groups:
        for code in group.ranked_teams():
            if code not in all_finishers:
                all_finishers.append(code)

    cc.qualifiers = all_finishers[:cc.wc_spots]
    cc.non_qualifiers = [c for c in all_finishers if c not in cc.qualifiers]
    cc.phase = "completed"

    _log.info(f"{cc.confederation.upper()} Championship complete. "
              f"Champion: {cc.champion}. Qualifiers: {cc.qualifiers}")

    return cc


# ═══════════════════════════════════════════════════════════════
# T004 — CROSS-CONFEDERATION PLAYOFF
# ═══════════════════════════════════════════════════════════════

def create_playoff(
    confederations: Dict[str, ContinentalChampionship],
) -> CrossConfederationPlayoff:
    """Create the cross-confederation playoff bracket.

    Takes the top non-qualifiers from each confederation to fill 8 spots.
    """
    playoff_teams: List[str] = []

    # Distribute slots: 2 from each of 4 larger confederations, 0 from smallest
    # Or simpler: take top 1-2 non-qualifiers from each confederation until we have 8
    for conf_id in ("cav", "ifav", "evv", "aav", "cmv"):
        cc = confederations.get(conf_id)
        if not cc or cc.phase != "completed":
            continue
        # Take top 2 non-qualifiers
        for code in cc.non_qualifiers[:2]:
            playoff_teams.append(code)
            if len(playoff_teams) >= 8:
                break
        if len(playoff_teams) >= 8:
            break

    return CrossConfederationPlayoff(teams=playoff_teams[:8])


def run_playoff(
    playoff: CrossConfederationPlayoff,
    national_teams: Dict[str, NationalTeam],
    rankings: FIVRankings,
    rng: Optional[random.Random] = None,
) -> CrossConfederationPlayoff:
    """Run the cross-confederation playoff. 8 teams → 4 qualifiers."""
    if rng is None:
        rng = random.Random()

    playoff.phase = "in_progress"
    current_teams = list(playoff.teams)

    # Quarterfinals
    if len(current_teams) >= 8:
        bracket = KnockoutBracket(round_name="Quarterfinals")
        next_round: List[str] = []
        for i in range(0, 8, 2):
            home_code = current_teams[i]
            away_code = current_teams[i + 1]
            result = _play_match(
                national_teams[home_code],
                national_teams[away_code],
                competition="playoff",
                stage="quarterfinal",
                rankings=rankings,
                rng=rng,
            )
            playoff.all_results.append(result)
            bracket.matchups.append({
                "home": home_code, "away": away_code,
                "winner": result.winner,
                "home_score": result.home_score,
                "away_score": result.away_score,
                "match_id": result.match_id,
                "result": result.to_dict(),
            })
            next_round.append(result.winner)
        bracket.completed = True
        playoff.bracket.append(bracket)
        current_teams = next_round

    # Semifinals → all 4 semifinalists qualify
    if len(current_teams) >= 4:
        bracket = KnockoutBracket(round_name="Semifinals")
        for i in range(0, 4, 2):
            home_code = current_teams[i]
            away_code = current_teams[i + 1]
            result = _play_match(
                national_teams[home_code],
                national_teams[away_code],
                competition="playoff",
                stage="semifinal",
                rankings=rankings,
                rng=rng,
            )
            playoff.all_results.append(result)
            bracket.matchups.append({
                "home": home_code, "away": away_code,
                "winner": result.winner,
                "home_score": result.home_score,
                "away_score": result.away_score,
                "match_id": result.match_id,
                "result": result.to_dict(),
            })
        bracket.completed = True
        playoff.bracket.append(bracket)

    # All 4 semifinalists qualify (winners and losers of semis)
    playoff.qualifiers = current_teams[:4]
    playoff.phase = "completed"

    _log.info(f"Playoff complete. Qualifiers: {playoff.qualifiers}")
    return playoff


# ═══════════════════════════════════════════════════════════════
# T005 — WORLD CUP TOURNAMENT
# ═══════════════════════════════════════════════════════════════

def create_world_cup(
    continental_qualifiers: Dict[str, List[str]],
    playoff_qualifiers: List[str],
    host: str,
    rankings: FIVRankings,
    rng: Optional[random.Random] = None,
) -> WorldCup:
    """Create a 32-team World Cup with seeded group draw."""
    if rng is None:
        rng = random.Random()

    # Collect all 32 teams
    all_qualified: List[str] = []
    host_included = False

    for conf_id, qualifiers in continental_qualifiers.items():
        for code in qualifiers:
            if code == host:
                host_included = True
            if code not in all_qualified:
                all_qualified.append(code)

    for code in playoff_qualifiers:
        if code not in all_qualified:
            all_qualified.append(code)

    # Ensure host is included
    if not host_included and host not in all_qualified:
        all_qualified.append(host)

    # Trim to 32 or pad if needed
    all_qualified = all_qualified[:32]

    # If we don't have 32 yet, pad with highest-ranked non-qualifiers
    if len(all_qualified) < 32:
        ranked = rankings.get_ranked_list()
        for _, code, _ in ranked:
            if code not in all_qualified:
                all_qualified.append(code)
            if len(all_qualified) >= 32:
                break

    wc = WorldCup(host=host, teams=all_qualified[:32])

    # --- Seed pots (by world ranking) ---
    team_ratings = [(code, rankings.ratings.get(code, 900)) for code in wc.teams]
    team_ratings.sort(key=lambda x: -x[1])

    # Host always in Pot 1
    sorted_codes = [code for code, _ in team_ratings]
    if host in sorted_codes:
        sorted_codes.remove(host)
        sorted_codes.insert(0, host)

    wc.seed_pots = {
        "Pot 1": sorted_codes[:8],
        "Pot 2": sorted_codes[8:16],
        "Pot 3": sorted_codes[16:24],
        "Pot 4": sorted_codes[24:32],
    }

    return wc


def draw_world_cup_groups(
    wc: WorldCup,
    national_teams: Dict[str, NationalTeam],
    rng: Optional[random.Random] = None,
) -> WorldCup:
    """Perform the World Cup group draw with confederation separation."""
    if rng is None:
        rng = random.Random()

    groups: List[List[str]] = [[] for _ in range(8)]

    # Get confederation for each team
    def _conf(code: str) -> str:
        nt = national_teams.get(code)
        return nt.nation.confederation if nt else ""

    # Draw from each pot
    for pot_name in ("Pot 1", "Pot 2", "Pot 3", "Pot 4"):
        pot = list(wc.seed_pots.get(pot_name, []))
        rng.shuffle(pot)

        for team_code in pot:
            team_conf = _conf(team_code)
            # Try to place in a group without same confederation
            placed = False
            for gi in range(8):
                if len(groups[gi]) >= 4:
                    continue
                group_confs = [_conf(c) for c in groups[gi]]
                # Allow max 2 from same confederation (spec: CAV/EVV may have 2)
                if group_confs.count(team_conf) >= 2:
                    continue
                groups[gi].append(team_code)
                placed = True
                break
            if not placed:
                # Fallback: place in first available group
                for gi in range(8):
                    if len(groups[gi]) < 4:
                        groups[gi].append(team_code)
                        break

    wc.groups = []
    for i, group_teams in enumerate(groups):
        group_name = chr(65 + i)
        g = GroupStandings(group_name=group_name, teams=group_teams)
        g.init_table()
        wc.groups.append(g)

    wc.phase = "draw"
    return wc


def run_world_cup_group_stage(
    wc: WorldCup,
    national_teams: Dict[str, NationalTeam],
    rankings: FIVRankings,
    rng: Optional[random.Random] = None,
) -> WorldCup:
    """Run the World Cup group stage (48 matches)."""
    if rng is None:
        rng = random.Random()

    wc.phase = "groups"

    for group in wc.groups:
        matchups = _group_matchdays(group)
        for home_code, away_code in matchups:
            if home_code not in national_teams or away_code not in national_teams:
                continue
            result = _play_match(
                national_teams[home_code],
                national_teams[away_code],
                competition="wc_group",
                stage=f"group_{group.group_name}",
                rankings=rankings,
                rng=rng,
            )
            group.record_result(result)
            wc.all_results.append(result)

    return wc


def run_world_cup_knockout(
    wc: WorldCup,
    national_teams: Dict[str, NationalTeam],
    rankings: FIVRankings,
    rng: Optional[random.Random] = None,
) -> WorldCup:
    """Run the World Cup knockout stage (R16 → QF → SF → 3rd place → Final)."""
    if rng is None:
        rng = random.Random()

    wc.phase = "knockout"

    # Get top 2 from each group → 16 teams
    r16_teams: List[str] = []
    group_winners: List[str] = []
    group_runners: List[str] = []

    for group in wc.groups:
        ranked = group.ranked_teams()
        if len(ranked) >= 2:
            group_winners.append(ranked[0])
            group_runners.append(ranked[1])
        elif ranked:
            group_winners.append(ranked[0])

    # R16 matchups: 1A vs 2B, 1B vs 2A, 1C vs 2D, 1D vs 2C, etc.
    r16_matchups: List[Tuple[str, str]] = []
    for i in range(min(len(group_winners), len(group_runners))):
        # Cross-group pairing
        opp_idx = (i + 1) % len(group_runners) if i % 2 == 0 else (i - 1) % len(group_runners)
        r16_matchups.append((group_winners[i], group_runners[opp_idx]))

    # Run knockout rounds
    current_teams: List[str] = []
    round_configs = [
        ("Round of 16", r16_matchups, "wc_knockout"),
    ]

    # R16
    bracket = KnockoutBracket(round_name="Round of 16")
    for home_code, away_code in r16_matchups:
        if home_code not in national_teams or away_code not in national_teams:
            continue
        result = _play_match(
            national_teams[home_code],
            national_teams[away_code],
            competition="wc_knockout",
            stage="round_of_16",
            rankings=rankings,
            rng=rng,
        )
        wc.all_results.append(result)
        bracket.matchups.append({
            "home": home_code, "away": away_code,
            "winner": result.winner,
            "home_score": result.home_score,
            "away_score": result.away_score,
            "match_id": result.match_id,
            "result": result.to_dict(),
        })
        current_teams.append(result.winner)
    bracket.completed = True
    wc.knockout_rounds.append(bracket)

    # QF, SF
    for round_name, comp_type in [("Quarterfinals", "wc_knockout"), ("Semifinals", "wc_semifinal")]:
        if len(current_teams) < 2:
            break
        bracket = KnockoutBracket(round_name=round_name)
        next_round: List[str] = []
        losers: List[str] = []
        for i in range(0, len(current_teams), 2):
            if i + 1 >= len(current_teams):
                next_round.append(current_teams[i])
                continue
            home_code = current_teams[i]
            away_code = current_teams[i + 1]
            result = _play_match(
                national_teams[home_code],
                national_teams[away_code],
                competition=comp_type,
                stage=round_name.lower().replace(" ", "_"),
                rankings=rankings,
                rng=rng,
            )
            wc.all_results.append(result)
            bracket.matchups.append({
                "home": home_code, "away": away_code,
                "winner": result.winner,
                "home_score": result.home_score,
                "away_score": result.away_score,
                "match_id": result.match_id,
                "result": result.to_dict(),
            })
            next_round.append(result.winner)
            loser = away_code if result.winner == home_code else home_code
            losers.append(loser)
        bracket.completed = True
        wc.knockout_rounds.append(bracket)
        sf_losers = losers if round_name == "Semifinals" else []
        current_teams = next_round

    # Third-place match
    if len(sf_losers) >= 2:
        bracket = KnockoutBracket(round_name="Third Place Match")
        result = _play_match(
            national_teams[sf_losers[0]],
            national_teams[sf_losers[1]],
            competition="wc_knockout",
            stage="third_place",
            rankings=rankings,
            rng=rng,
        )
        wc.all_results.append(result)
        bracket.matchups.append({
            "home": sf_losers[0], "away": sf_losers[1],
            "winner": result.winner,
            "home_score": result.home_score,
            "away_score": result.away_score,
            "match_id": result.match_id,
            "result": result.to_dict(),
        })
        bracket.completed = True
        wc.knockout_rounds.append(bracket)
        wc.third_place = result.winner

    # Final
    if len(current_teams) >= 2:
        bracket = KnockoutBracket(round_name="Final")
        result = _play_match(
            national_teams[current_teams[0]],
            national_teams[current_teams[1]],
            competition="wc_final",
            stage="final",
            rankings=rankings,
            rng=rng,
        )
        wc.all_results.append(result)
        bracket.matchups.append({
            "home": current_teams[0], "away": current_teams[1],
            "winner": result.winner,
            "home_score": result.home_score,
            "away_score": result.away_score,
            "match_id": result.match_id,
            "result": result.to_dict(),
        })
        bracket.completed = True
        wc.knockout_rounds.append(bracket)
        wc.champion = result.winner

    # Compute tournament awards
    wc.golden_boot = _compute_golden_boot(wc.all_results)
    wc.mvp = _compute_mvp(wc.all_results)

    wc.phase = "completed"
    _log.info(f"World Cup complete. Champion: {wc.champion}")
    return wc


def compute_tournament_stat_leaders(results: List[MatchResult]) -> dict:
    """Aggregate player stats across tournament matches and compute leaders.

    Returns a dict with categories: rushing, kick_passing, scoring,
    defensive, and kicking — each a sorted list of player stat dicts.
    """
    # Accumulate per-player stats across all matches
    accum: Dict[str, Dict[str, Any]] = {}

    for r in results:
        if not r.game_result or "player_stats" not in r.game_result:
            continue
        for side in ("home", "away"):
            ps = r.game_result["player_stats"].get(side, [])
            nation_code = r.home_code if side == "home" else r.away_code
            if not isinstance(ps, list):
                continue
            for stats in ps:
                pname = stats.get("name", "Unknown")
                key = f"{pname}|{nation_code}"
                if key not in accum:
                    accum[key] = {
                        "name": pname,
                        "nation": nation_code,
                        "position": stats.get("position", ""),
                        "games": 0,
                        # Rushing
                        "rush_carries": 0, "rushing_yards": 0, "rushing_tds": 0,
                        "long_rush": 0,
                        # Kick passing
                        "kick_passes_thrown": 0, "kick_passes_completed": 0,
                        "kick_pass_yards": 0, "kick_pass_tds": 0,
                        "kick_pass_interceptions_thrown": 0,
                        # Receiving
                        "kick_pass_receptions": 0,
                        # Laterals
                        "laterals_thrown": 0, "lateral_receptions": 0,
                        "lateral_yards": 0, "lateral_tds": 0, "lateral_assists": 0,
                        # Defense
                        "tackles": 0, "tfl": 0, "sacks": 0,
                        "hurries": 0, "kick_pass_ints": 0, "st_tackles": 0,
                        # Kicking
                        "drop_kicks_made": 0, "drop_kicks_attempted": 0,
                        "place_kicks_made": 0, "place_kicks_attempted": 0,
                        # Scoring
                        "total_tds": 0, "fumbles": 0,
                        # Advanced
                        "wpa": 0.0,
                    }
                a = accum[key]
                a["games"] += 1
                for stat_key in (
                    "rush_carries", "rushing_yards", "rushing_tds",
                    "kick_passes_thrown", "kick_passes_completed",
                    "kick_pass_yards", "kick_pass_tds",
                    "kick_pass_interceptions_thrown",
                    "kick_pass_receptions",
                    "laterals_thrown", "lateral_receptions",
                    "lateral_yards", "lateral_tds", "lateral_assists",
                    "tackles", "tfl", "sacks", "hurries",
                    "kick_pass_ints", "st_tackles",
                    "drop_kicks_made", "drop_kicks_attempted",
                    "place_kicks_made", "place_kicks_attempted",
                    "fumbles",
                ):
                    a[stat_key] += stats.get(stat_key, 0)
                a["wpa"] += stats.get("wpa", stats.get("vpa", 0))
                a["long_rush"] = max(a["long_rush"], stats.get("long_rush", 0))
                a["total_tds"] = (
                    a["rushing_tds"] + a["lateral_tds"] + a["kick_pass_tds"]
                )

    all_players = list(accum.values())

    # Build category leaders
    rushing = sorted(
        [p for p in all_players if p["rush_carries"] > 0],
        key=lambda x: x["rushing_yards"], reverse=True,
    )[:20]

    kick_passing = sorted(
        [p for p in all_players if p["kick_passes_thrown"] > 0],
        key=lambda x: x["kick_pass_yards"], reverse=True,
    )[:20]

    scoring = sorted(
        [p for p in all_players if p["total_tds"] > 0],
        key=lambda x: x["total_tds"], reverse=True,
    )[:20]

    defensive = sorted(
        [p for p in all_players if p["tackles"] > 0],
        key=lambda x: x["tackles"], reverse=True,
    )[:20]

    kicking = sorted(
        [p for p in all_players
         if p["drop_kicks_made"] + p["place_kicks_made"] > 0],
        key=lambda x: x["drop_kicks_made"] * 5 + x["place_kicks_made"] * 3,
        reverse=True,
    )[:20]

    return {
        "rushing": rushing,
        "kick_passing": kick_passing,
        "scoring": scoring,
        "defensive": defensive,
        "kicking": kicking,
    }


def _compute_golden_boot(results: List[MatchResult]) -> Optional[dict]:
    """Find the top scorer across all World Cup games."""
    player_tds: Dict[str, Dict[str, Any]] = {}
    for r in results:
        if not r.game_result or "player_stats" not in r.game_result:
            continue
        for side in ("home", "away"):
            ps = r.game_result["player_stats"].get(side, [])
            nation_code = r.home_code if side == "home" else r.away_code
            # player_stats is a list of player stat dicts
            if isinstance(ps, list):
                for stats in ps:
                    pname = stats.get("name", "Unknown")
                    tds = stats.get("rushing_tds", 0) + stats.get("lateral_tds", 0) + stats.get("kick_pass_tds", 0)
                    if tds > 0:
                        if pname not in player_tds:
                            player_tds[pname] = {"name": pname, "nation": nation_code, "tds": 0}
                        player_tds[pname]["tds"] += tds

    if not player_tds:
        return None

    top = max(player_tds.values(), key=lambda x: x["tds"])
    return top


def _compute_mvp(results: List[MatchResult]) -> Optional[dict]:
    """Find the MVP (highest cumulative WPA/VPA across tournament)."""
    player_vpa: Dict[str, Dict[str, Any]] = {}
    for r in results:
        if not r.game_result or "player_stats" not in r.game_result:
            continue
        for side in ("home", "away"):
            ps = r.game_result["player_stats"].get(side, [])
            nation_code = r.home_code if side == "home" else r.away_code
            if isinstance(ps, list):
                for stats in ps:
                    pname = stats.get("name", "Unknown")
                    vpa = stats.get("wpa", stats.get("vpa", 0))
                    if pname not in player_vpa:
                        player_vpa[pname] = {"name": pname, "nation": nation_code, "vpa": 0.0}
                    player_vpa[pname]["vpa"] += vpa

    if not player_vpa:
        return None

    top = max(player_vpa.values(), key=lambda x: x["vpa"])
    top["vpa"] = round(top["vpa"], 1)
    return top


# ═══════════════════════════════════════════════════════════════
# FULL CYCLE ORCHESTRATION
# ═══════════════════════════════════════════════════════════════

def create_fiv_cycle(
    cycle_number: int = 1,
    host_nation: Optional[str] = None,
    cvl_players: Optional[List[Player]] = None,
    existing_rankings: Optional[FIVRankings] = None,
    seed: Optional[int] = None,
) -> FIVCycle:
    """Create a new FIV cycle with rosters and initial state."""
    rng = random.Random(seed) if seed else random.Random()

    # Generate all national team rosters
    national_teams = generate_national_teams(cvl_players=cvl_players, rng=rng)

    # Initialize or carry over rankings
    rankings = existing_rankings or FIVRankings()
    if not rankings.ratings:
        all_nations = _load_all_nations()
        rankings.init_from_tiers(all_nations)

    # Pick host if not specified
    if host_nation is None:
        host_nation = rng.choice(list(national_teams.keys()))

    # Snapshot rankings before cycle
    rankings_before = rankings.snapshot()

    cycle = FIVCycle(
        cycle_number=cycle_number,
        national_teams=national_teams,
        rankings=rankings,
        rankings_before=rankings_before,
        host_nation=host_nation,
        phase="roster_generation",
    )

    # Initialize continental championships
    cfg = _load_config()
    for conf_id in cfg["confederations"]:
        cc = create_continental_championship(conf_id, national_teams)
        cycle.confederations_data[conf_id] = cc

    return cycle


def run_continental_phase(cycle: FIVCycle, rng: Optional[random.Random] = None) -> FIVCycle:
    """Run all 5 continental championships."""
    if rng is None:
        rng = random.Random()

    cycle.phase = "continental"

    for conf_id, cc in cycle.confederations_data.items():
        run_continental_championship(
            cc,
            cycle.national_teams,
            cycle.rankings,
            rng=rng,
        )

    return cycle


def run_playoff_phase(cycle: FIVCycle, rng: Optional[random.Random] = None) -> FIVCycle:
    """Run the cross-confederation playoff."""
    if rng is None:
        rng = random.Random()

    cycle.playoff = create_playoff(cycle.confederations_data)
    run_playoff(cycle.playoff, cycle.national_teams, cycle.rankings, rng=rng)
    cycle.phase = "playoff"
    return cycle


def run_world_cup_phase(cycle: FIVCycle, rng: Optional[random.Random] = None) -> FIVCycle:
    """Run the full World Cup: draw → groups → knockout."""
    if rng is None:
        rng = random.Random()

    # Gather all qualifiers
    continental_qualifiers: Dict[str, List[str]] = {}
    for conf_id, cc in cycle.confederations_data.items():
        continental_qualifiers[conf_id] = cc.qualifiers

    playoff_qualifiers = cycle.playoff.qualifiers if cycle.playoff else []

    # Create and draw World Cup
    wc = create_world_cup(
        continental_qualifiers, playoff_qualifiers,
        cycle.host_nation or "USA",
        cycle.rankings, rng=rng,
    )
    draw_world_cup_groups(wc, cycle.national_teams, rng=rng)
    cycle.world_cup = wc
    cycle.phase = "wc_draw"

    # Run group stage
    run_world_cup_group_stage(wc, cycle.national_teams, cycle.rankings, rng=rng)
    cycle.phase = "wc_groups"

    # Run knockout
    run_world_cup_knockout(wc, cycle.national_teams, cycle.rankings, rng=rng)
    cycle.phase = "completed"

    # Record rankings history
    if cycle.rankings:
        cycle.rankings.history.append({
            "cycle": cycle.cycle_number,
            "snapshot": cycle.rankings.snapshot(),
            "champion": wc.champion,
        })

    return cycle


def run_full_cycle(
    cycle_number: int = 1,
    host_nation: Optional[str] = None,
    cvl_players: Optional[List[Player]] = None,
    existing_rankings: Optional[FIVRankings] = None,
    seed: Optional[int] = None,
) -> FIVCycle:
    """Run an entire FIV cycle from roster generation through World Cup final."""
    rng = random.Random(seed) if seed else random.Random()

    cycle = create_fiv_cycle(
        cycle_number=cycle_number,
        host_nation=host_nation,
        cvl_players=cvl_players,
        existing_rankings=existing_rankings,
        seed=seed,
    )

    run_continental_phase(cycle, rng=rng)
    run_playoff_phase(cycle, rng=rng)
    run_world_cup_phase(cycle, rng=rng)

    return cycle


# ═══════════════════════════════════════════════════════════════
# T007 — PERSISTENCE
# ═══════════════════════════════════════════════════════════════

def save_fiv_cycle(cycle: FIVCycle, user_id: str = "default"):
    """Save the current FIV cycle to the database."""
    from engine.db import save_blob
    data = cycle.to_dict()
    save_blob("fiv", f"cycle_{cycle.cycle_number}", data,
              label=f"FIV Cycle {cycle.cycle_number}", user_id=user_id)
    # Also save as active cycle
    save_blob("fiv", "cycle_active", data,
              label="Active FIV Cycle", user_id=user_id)
    _log.info(f"Saved FIV cycle {cycle.cycle_number} for user={user_id}")


def save_fiv_rankings(rankings: FIVRankings, user_id: str = "default"):
    """Save FIV World Rankings to the database."""
    from engine.db import save_blob
    save_blob("fiv", "world_rankings", rankings.to_dict(),
              label="FIV World Rankings", user_id=user_id)


def load_fiv_rankings(user_id: str = "default") -> Optional[FIVRankings]:
    """Load FIV World Rankings from the database."""
    from engine.db import load_blob
    data = load_blob("fiv", "world_rankings", user_id=user_id)
    if data is None:
        return None
    return FIVRankings.from_dict(data)


def load_fiv_cycle(cycle_number: Optional[int] = None, user_id: str = "default") -> Optional[dict]:
    """Load a FIV cycle from the database. Returns raw dict."""
    from engine.db import load_blob
    key = f"cycle_{cycle_number}" if cycle_number else "cycle_active"
    return load_blob("fiv", key, user_id=user_id)


def list_fiv_cycles(user_id: str = "default") -> list:
    """List all saved FIV cycles."""
    from engine.db import list_saves
    return [s for s in list_saves("fiv", user_id=user_id)
            if s["save_key"].startswith("cycle_") and s["save_key"] != "cycle_active"]


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE: Get match result by ID
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# T010 — DRAFTYQUEENZ INTEGRATION
# ═══════════════════════════════════════════════════════════════

def generate_fiv_odds(
    home_code: str,
    away_code: str,
    national_teams: Dict[str, NationalTeam],
    competition: str = "continental_group",
) -> Optional[dict]:
    """Generate DraftyQueenz betting odds for an FIV match.

    Uses national team ratings as prestige input to the standard odds generator.
    World Cup knockout games get a 1.5x payout multiplier.
    """
    try:
        from engine.draftyqueenz import generate_game_odds
    except ImportError:
        return None

    home_nt = national_teams.get(home_code)
    away_nt = national_teams.get(away_code)
    if not home_nt or not away_nt:
        return None

    odds = generate_game_odds(
        home_team_name=home_nt.name,
        away_team_name=away_nt.name,
        home_prestige=home_nt.rating,
        away_prestige=away_nt.rating,
    )

    result = odds.to_dict()

    # Apply payout multiplier for high-stakes matches
    multipliers = {
        "continental_group": 1.0,
        "continental_knockout": 1.2,
        "playoff": 1.3,
        "wc_group": 1.5,
        "wc_knockout": 2.0,
        "wc_semifinal": 2.5,
        "wc_final": 3.0,
    }
    result["payout_multiplier"] = multipliers.get(competition, 1.0)
    result["competition"] = competition

    return result


def find_match_in_cycle(cycle_data: dict, match_id: str) -> Optional[dict]:
    """Find a specific match result by ID across all competitions in a cycle.

    Returns the full MatchResult dict (with game_result) when available.
    For knockout matchups, returns the embedded ``result`` dict which
    contains the full game data for box score rendering.
    """
    # Search continental championships
    for conf_id, cc_data in cycle_data.get("confederations_data", {}).items():
        for group in cc_data.get("groups", []):
            for result in group.get("results", []):
                if result.get("match_id") == match_id:
                    return result
        for kr in cc_data.get("knockout_rounds", []):
            for m in kr.get("matchups", []):
                if m.get("match_id") == match_id:
                    return m.get("result", m)

    # Search playoff
    playoff = cycle_data.get("playoff")
    if playoff:
        for kr in playoff.get("bracket", []):
            for m in kr.get("matchups", []):
                if m.get("match_id") == match_id:
                    return m.get("result", m)

    # Search World Cup
    wc = cycle_data.get("world_cup")
    if wc:
        for group in wc.get("groups", []):
            for result in group.get("results", []):
                if result.get("match_id") == match_id:
                    return result
        for kr in wc.get("knockout_rounds", []):
            for m in kr.get("matchups", []):
                if m.get("match_id") == match_id:
                    return m.get("result", m)

    return None
