"""
Viperball Player Card System

Sports-reference style player profiles with:
- Full biographical data
- Complete attribute ratings (0-100 per attribute)
- Per-game and season stat tracking
- Career history across multiple seasons
- Computed overall rating

A PlayerCard is generated once when a player is created and updated as they
accumulate stats throughout a dynasty.  It serialises cleanly to/from JSON so
it can live inside a save file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ──────────────────────────────────────────────
# GAME-LEVEL LOG ENTRY
# ──────────────────────────────────────────────

@dataclass
class GameLog:
    """Stats from a single game, stored on the player's season record."""
    opponent: str
    week: int
    touches: int = 0
    rushing_yards: int = 0
    lateral_yards: int = 0
    total_yards: int = 0
    touchdowns: int = 0
    fumbles: int = 0
    laterals_thrown: int = 0
    kick_attempts: int = 0
    kick_makes: int = 0
    coverage_snaps: int = 0
    kick_deflections: int = 0
    keeper_tackles: int = 0
    keeper_bells: int = 0
    return_yards: int = 0

    def to_dict(self) -> dict:
        return {
            "opponent": self.opponent,
            "week": self.week,
            "touches": self.touches,
            "rushing_yards": self.rushing_yards,
            "lateral_yards": self.lateral_yards,
            "total_yards": self.total_yards,
            "touchdowns": self.touchdowns,
            "fumbles": self.fumbles,
            "laterals_thrown": self.laterals_thrown,
            "kick_attempts": self.kick_attempts,
            "kick_makes": self.kick_makes,
            "coverage_snaps": self.coverage_snaps,
            "kick_deflections": self.kick_deflections,
            "keeper_tackles": self.keeper_tackles,
            "keeper_bells": self.keeper_bells,
            "return_yards": self.return_yards,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GameLog":
        return cls(**{k: d.get(k, 0) if k not in ("opponent",) else d.get(k, "")
                      for k in cls.__dataclass_fields__})


# ──────────────────────────────────────────────
# SEASON STATS
# ──────────────────────────────────────────────

@dataclass
class SeasonStats:
    """Aggregated statistics for one season."""
    season_year: int
    team: str
    games_played: int = 0
    touches: int = 0
    rushing_yards: int = 0
    lateral_yards: int = 0
    total_yards: int = 0
    touchdowns: int = 0
    fumbles: int = 0
    laterals_thrown: int = 0
    kick_attempts: int = 0
    kick_makes: int = 0
    coverage_snaps: int = 0
    kick_deflections: int = 0
    keeper_tackles: int = 0
    keeper_bells: int = 0
    return_yards: int = 0
    game_log: List[GameLog] = field(default_factory=list)

    # ── computed properties ──
    @property
    def yards_per_touch(self) -> float:
        return round(self.total_yards / max(1, self.touches), 1)

    @property
    def kick_pct(self) -> float:
        return round(self.kick_makes / max(1, self.kick_attempts) * 100, 1)

    @property
    def points(self) -> float:
        """Approximate scoring contribution (6 per TD)."""
        return self.touchdowns * 6.0

    def add_game(self, log: GameLog) -> None:
        """Accumulate a game log entry into season totals."""
        self.game_log.append(log)
        self.games_played += 1
        self.touches += log.touches
        self.rushing_yards += log.rushing_yards
        self.lateral_yards += log.lateral_yards
        self.total_yards += log.total_yards
        self.touchdowns += log.touchdowns
        self.fumbles += log.fumbles
        self.laterals_thrown += log.laterals_thrown
        self.kick_attempts += log.kick_attempts
        self.kick_makes += log.kick_makes
        self.coverage_snaps += log.coverage_snaps
        self.kick_deflections += log.kick_deflections
        self.keeper_tackles += log.keeper_tackles
        self.keeper_bells += log.keeper_bells
        self.return_yards += log.return_yards

    def to_dict(self) -> dict:
        return {
            "season_year": self.season_year,
            "team": self.team,
            "games_played": self.games_played,
            "touches": self.touches,
            "rushing_yards": self.rushing_yards,
            "lateral_yards": self.lateral_yards,
            "total_yards": self.total_yards,
            "touchdowns": self.touchdowns,
            "fumbles": self.fumbles,
            "laterals_thrown": self.laterals_thrown,
            "kick_attempts": self.kick_attempts,
            "kick_makes": self.kick_makes,
            "coverage_snaps": self.coverage_snaps,
            "kick_deflections": self.kick_deflections,
            "keeper_tackles": self.keeper_tackles,
            "keeper_bells": self.keeper_bells,
            "return_yards": self.return_yards,
            "yards_per_touch": self.yards_per_touch,
            "kick_pct": self.kick_pct,
            "game_log": [g.to_dict() for g in self.game_log],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SeasonStats":
        logs = [GameLog.from_dict(g) for g in d.pop("game_log", [])]
        d.pop("yards_per_touch", None)
        d.pop("kick_pct", None)
        obj = cls(**{k: d.get(k, 0) if k not in ("team",) else d.get(k, "")
                     for k in cls.__dataclass_fields__ if k != "game_log"})
        obj.game_log = logs
        return obj


# ──────────────────────────────────────────────
# RATINGS BREAKDOWN
# ──────────────────────────────────────────────

# Position weights used when computing overall rating
_POSITION_WEIGHTS: Dict[str, Dict[str, float]] = {
    "Zeroback": {
        "speed": 1.2, "stamina": 1.0, "kicking": 1.3, "lateral_skill": 1.0,
        "tackling": 0.5, "agility": 1.0, "power": 0.6, "awareness": 1.4,
        "hands": 0.8, "kick_power": 1.2, "kick_accuracy": 1.2,
    },
    "Viper": {
        "speed": 1.4, "stamina": 1.0, "kicking": 0.6, "lateral_skill": 1.3,
        "tackling": 0.6, "agility": 1.3, "power": 0.7, "awareness": 1.0,
        "hands": 1.3, "kick_power": 0.4, "kick_accuracy": 0.4,
    },
    "Halfback": {
        "speed": 1.2, "stamina": 1.1, "kicking": 0.6, "lateral_skill": 1.2,
        "tackling": 0.7, "agility": 1.1, "power": 1.1, "awareness": 1.0,
        "hands": 1.0, "kick_power": 0.5, "kick_accuracy": 0.5,
    },
    "Wingback": {
        "speed": 1.3, "stamina": 1.0, "kicking": 0.6, "lateral_skill": 1.2,
        "tackling": 0.6, "agility": 1.2, "power": 0.8, "awareness": 0.9,
        "hands": 1.1, "kick_power": 0.4, "kick_accuracy": 0.4,
    },
    "Lineman": {
        "speed": 0.7, "stamina": 1.2, "kicking": 0.5, "lateral_skill": 0.8,
        "tackling": 1.6, "agility": 0.7, "power": 1.6, "awareness": 0.9,
        "hands": 0.6, "kick_power": 0.3, "kick_accuracy": 0.3,
    },
    "Safety": {
        "speed": 1.2, "stamina": 1.0, "kicking": 0.6, "lateral_skill": 1.0,
        "tackling": 1.3, "agility": 1.1, "power": 0.9, "awareness": 1.3,
        "hands": 0.9, "kick_power": 0.4, "kick_accuracy": 0.4,
    },
    "default": {
        "speed": 1.0, "stamina": 1.0, "kicking": 0.8, "lateral_skill": 1.0,
        "tackling": 1.0, "agility": 1.0, "power": 1.0, "awareness": 1.0,
        "hands": 1.0, "kick_power": 0.7, "kick_accuracy": 0.7,
    },
}


def _get_position_weights(position: str) -> Dict[str, float]:
    for key in _POSITION_WEIGHTS:
        if key.lower() in position.lower():
            return _POSITION_WEIGHTS[key]
    return _POSITION_WEIGHTS["default"]


# ──────────────────────────────────────────────
# PLAYER CARD
# ──────────────────────────────────────────────

@dataclass
class PlayerCard:
    """
    Sports-reference style player profile.

    Contains full biographical data, all attribute ratings, dynasty info,
    and a complete career stats history.  Lives inside a save file.
    """

    # ── Identity ──
    player_id: str
    first_name: str
    last_name: str
    number: int
    position: str
    archetype: str

    # ── Bio ──
    nationality: str
    hometown_city: str
    hometown_state: str
    hometown_country: str
    high_school: str
    height: str        # "5-10"
    weight: int
    year: str          # Freshman / Sophomore / Junior / Senior

    # ── Attribute ratings (0-100) ──
    speed: int
    stamina: int
    agility: int
    power: int
    awareness: int
    hands: int
    kicking: int
    kick_power: int
    kick_accuracy: int
    lateral_skill: int
    tackling: int

    # ── Dynasty / scouting ──
    potential: int     # 1-5 stars
    development: str   # normal / quick / slow / late_bloomer

    # ── Redshirt tracking ──
    redshirt: bool = False
    season_games_played: int = 0

    # ── Career history ──
    career_seasons: List[SeasonStats] = field(default_factory=list)
    current_team: str = ""

    # ── Computed ──
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        return f"{self.first_name[0]}. {self.last_name}"

    @property
    def overall(self) -> int:
        """Position-weighted overall rating (0-100)."""
        w = _get_position_weights(self.position)
        total_weight = sum(w.values())
        raw = (
            self.speed        * w["speed"]        +
            self.stamina      * w["stamina"]       +
            self.kicking      * w["kicking"]       +
            self.lateral_skill * w["lateral_skill"] +
            self.tackling     * w["tackling"]      +
            self.agility      * w["agility"]       +
            self.power        * w["power"]         +
            self.awareness    * w["awareness"]     +
            self.hands        * w["hands"]         +
            self.kick_power   * w["kick_power"]    +
            self.kick_accuracy * w["kick_accuracy"]
        ) / total_weight
        return min(99, max(40, int(raw)))

    @property
    def star_rating(self) -> str:
        return "★" * self.potential + "☆" * (5 - self.potential)

    # ── Career totals ──
    @property
    def career_games(self) -> int:
        return sum(s.games_played for s in self.career_seasons)

    @property
    def career_yards(self) -> int:
        return sum(s.total_yards for s in self.career_seasons)

    @property
    def career_touchdowns(self) -> int:
        return sum(s.touchdowns for s in self.career_seasons)

    @property
    def career_fumbles(self) -> int:
        return sum(s.fumbles for s in self.career_seasons)

    @property
    def career_kick_attempts(self) -> int:
        return sum(s.kick_attempts for s in self.career_seasons)

    @property
    def career_kick_makes(self) -> int:
        return sum(s.kick_makes for s in self.career_seasons)

    @property
    def career_kick_pct(self) -> float:
        return round(self.career_kick_makes / max(1, self.career_kick_attempts) * 100, 1)

    # ── Stat helpers ──
    def get_or_create_season(self, year: int, team: str) -> SeasonStats:
        """Return the SeasonStats for the given year, creating it if needed."""
        for s in self.career_seasons:
            if s.season_year == year and s.team == team:
                return s
        season = SeasonStats(season_year=year, team=team)
        self.career_seasons.append(season)
        return season

    def log_game(self, year: int, team: str, log: GameLog) -> None:
        """Add a game log entry to the correct season."""
        self.get_or_create_season(year, team).add_game(log)

    # ── Serialisation ──
    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "number": self.number,
            "position": self.position,
            "archetype": self.archetype,
            "nationality": self.nationality,
            "hometown": {
                "city": self.hometown_city,
                "state": self.hometown_state,
                "country": self.hometown_country,
            },
            "high_school": self.high_school,
            "height": self.height,
            "weight": self.weight,
            "year": self.year,
            "ratings": {
                "overall": self.overall,
                "speed": self.speed,
                "stamina": self.stamina,
                "agility": self.agility,
                "power": self.power,
                "awareness": self.awareness,
                "hands": self.hands,
                "kicking": self.kicking,
                "kick_power": self.kick_power,
                "kick_accuracy": self.kick_accuracy,
                "lateral_skill": self.lateral_skill,
                "tackling": self.tackling,
            },
            "potential": self.potential,
            "star_rating": self.star_rating,
            "development": self.development,
            "redshirt": self.redshirt,
            "season_games_played": self.season_games_played,
            "current_team": self.current_team,
            "career_totals": {
                "games": self.career_games,
                "yards": self.career_yards,
                "touchdowns": self.career_touchdowns,
                "fumbles": self.career_fumbles,
                "kick_attempts": self.career_kick_attempts,
                "kick_makes": self.career_kick_makes,
                "kick_pct": self.career_kick_pct,
            },
            "career_seasons": [s.to_dict() for s in self.career_seasons],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PlayerCard":
        hometown = d.get("hometown", {})
        ratings = d.get("ratings", {})
        seasons_raw = d.get("career_seasons", [])
        career = [SeasonStats.from_dict(s) for s in seasons_raw]
        return cls(
            player_id=d.get("player_id", ""),
            first_name=d.get("first_name", ""),
            last_name=d.get("last_name", ""),
            number=d.get("number", 0),
            position=d.get("position", ""),
            archetype=d.get("archetype", "none"),
            nationality=d.get("nationality", "American"),
            hometown_city=hometown.get("city", ""),
            hometown_state=hometown.get("state", ""),
            hometown_country=hometown.get("country", "USA"),
            high_school=d.get("high_school", ""),
            height=d.get("height", "5-10"),
            weight=d.get("weight", 170),
            year=d.get("year", "Sophomore"),
            speed=ratings.get("speed", 75),
            stamina=ratings.get("stamina", 75),
            agility=ratings.get("agility", 75),
            power=ratings.get("power", 75),
            awareness=ratings.get("awareness", 75),
            hands=ratings.get("hands", 75),
            kicking=ratings.get("kicking", 75),
            kick_power=ratings.get("kick_power", 75),
            kick_accuracy=ratings.get("kick_accuracy", 75),
            lateral_skill=ratings.get("lateral_skill", 75),
            tackling=ratings.get("tackling", 75),
            potential=d.get("potential", 3),
            development=d.get("development", "normal"),
            redshirt=d.get("redshirt", False),
            season_games_played=d.get("season_games_played", 0),
            career_seasons=career,
            current_team=d.get("current_team", ""),
        )

    def summary_line(self) -> str:
        """One-line description for a roster table."""
        return (
            f"#{self.number:>2} {self.full_name:<22} "
            f"{self.position:<15} {self.archetype:<18} "
            f"OVR {self.overall:>2} | "
            f"SPD {self.speed} STM {self.stamina} AGI {self.agility} "
            f"PWR {self.power} AWR {self.awareness} HND {self.hands} "
            f"KCK {self.kicking} TCK {self.tackling} | "
            f"{self.star_rating} pot | {self.nationality}"
        )


# ──────────────────────────────────────────────
# FACTORY: build a PlayerCard from a Player object
# ──────────────────────────────────────────────

def player_to_card(player, team_name: str = "") -> PlayerCard:
    """Convert a game_engine.Player to a PlayerCard for dynasty tracking."""
    parts = player.name.split()
    first = parts[0] if parts else player.name
    last = " ".join(parts[1:]) if len(parts) > 1 else player.name

    return PlayerCard(
        player_id=getattr(player, "player_id", ""),
        first_name=first,
        last_name=last,
        number=player.number,
        position=player.position,
        archetype=player.archetype,
        nationality=getattr(player, "nationality", "American"),
        hometown_city=getattr(player, "hometown_city", ""),
        hometown_state="",
        hometown_country=getattr(player, "hometown_country", "USA"),
        high_school=getattr(player, "high_school", ""),
        height=getattr(player, "height", "5-10"),
        weight=getattr(player, "weight", 170),
        year=getattr(player, "year", "Sophomore"),
        speed=player.speed,
        stamina=player.stamina,
        agility=getattr(player, "agility", 75),
        power=getattr(player, "power", 75),
        awareness=getattr(player, "awareness", 75),
        hands=getattr(player, "hands", 75),
        kicking=player.kicking,
        kick_power=getattr(player, "kick_power", 75),
        kick_accuracy=getattr(player, "kick_accuracy", 75),
        lateral_skill=player.lateral_skill,
        tackling=player.tackling,
        potential=getattr(player, "potential", 3),
        development=getattr(player, "development", "normal"),
        redshirt=getattr(player, "redshirt", False),
        season_games_played=getattr(player, "season_games_played", 0),
        current_team=team_name,
    )


def game_result_to_log(player, opponent: str, week: int) -> GameLog:
    """Snapshot a Player's in-game counters into a GameLog after a game."""
    return GameLog(
        opponent=opponent,
        week=week,
        touches=player.game_touches,
        rushing_yards=player.game_rushing_yards,
        lateral_yards=player.game_lateral_yards,
        total_yards=player.game_yards,
        touchdowns=player.game_tds,
        fumbles=player.game_fumbles,
        laterals_thrown=player.game_laterals_thrown,
        kick_attempts=player.game_kick_attempts,
        kick_makes=player.game_kick_makes,
        coverage_snaps=player.game_coverage_snaps,
        kick_deflections=player.game_kick_deflections,
        keeper_tackles=player.game_keeper_tackles,
        keeper_bells=player.game_keeper_bells,
        return_yards=player.game_keeper_return_yards,
    )
