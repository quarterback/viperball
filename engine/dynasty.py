"""
Dynasty Mode for Viperball

Complete multi-season career mode with:
- Coach profile and career tracking
- Historical records (team, player, conference)
- Award history (who won what in each year)
- Conference management
- Record books (single-season, career, all-time)
- Hall of Fame
"""

import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict

from engine.season import Season, TeamRecord, Game


# ========================================
# PLAYER CAREER STATS
# ========================================

@dataclass
class PlayerCareerStats:
    """Career statistics for a single player"""
    player_name: str
    team_name: str
    position: str

    # Career totals
    games_played: int = 0
    total_points_scored: float = 0.0
    total_yards_gained: int = 0
    total_laterals: int = 0
    total_fumbles: int = 0
    total_touchdowns: int = 0

    # Season-by-season breakdown
    seasons: List[int] = field(default_factory=list)  # List of years played

    @property
    def points_per_game(self) -> float:
        return self.total_points_scored / max(1, self.games_played)

    @property
    def yards_per_game(self) -> float:
        return self.total_yards_gained / max(1, self.games_played)


# ========================================
# TEAM HISTORICAL RECORDS
# ========================================

@dataclass
class TeamHistory:
    """All-time history for a single team"""
    team_name: str

    # All-time record
    total_wins: int = 0
    total_losses: int = 0
    total_championships: int = 0
    total_playoff_appearances: int = 0

    # Points
    total_points_for: float = 0.0
    total_points_against: float = 0.0

    # Season-by-season records
    season_records: Dict[int, Dict] = field(default_factory=dict)  # year -> {wins, losses, points_for, etc.}

    # Best seasons
    best_season_wins: int = 0
    best_season_year: Optional[int] = None

    # Championships
    championship_years: List[int] = field(default_factory=list)

    @property
    def win_percentage(self) -> float:
        total_games = self.total_wins + self.total_losses
        return self.total_wins / total_games if total_games > 0 else 0.0

    @property
    def points_per_game(self) -> float:
        total_games = self.total_wins + self.total_losses
        return self.total_points_for / total_games if total_games > 0 else 0.0


# ========================================
# SEASON AWARDS
# ========================================

@dataclass
class SeasonAwards:
    """Awards for a single season"""
    year: int

    # Team awards
    champion: str
    best_record: str
    highest_scoring: str
    best_defense: str
    highest_opi: str
    most_chaos: str
    best_kicking: str

    # Individual awards (if we add player stats later)
    # mvp: Optional[str] = None
    # offensive_player: Optional[str] = None
    # defensive_player: Optional[str] = None


# ========================================
# CONFERENCE SYSTEM
# ========================================

@dataclass
class Conference:
    """A conference of teams"""
    name: str
    teams: List[str]  # List of team names

    # Conference history
    championship_history: Dict[int, str] = field(default_factory=dict)  # year -> champion


# ========================================
# COACH PROFILE
# ========================================

@dataclass
class Coach:
    """User's coach profile for dynasty mode"""
    name: str
    team_name: str  # Team they coach

    # Career stats
    career_wins: int = 0
    career_losses: int = 0
    championships: int = 0
    playoff_appearances: int = 0

    # Years coached
    years_coached: List[int] = field(default_factory=list)
    first_year: Optional[int] = None
    current_year: Optional[int] = None

    # Season-by-season record
    season_records: Dict[int, Dict] = field(default_factory=dict)  # year -> {wins, losses, champion, etc.}

    @property
    def win_percentage(self) -> float:
        total_games = self.career_wins + self.career_losses
        return self.career_wins / total_games if total_games > 0 else 0.0

    @property
    def years_experience(self) -> int:
        return len(self.years_coached)


# ========================================
# RECORD BOOK
# ========================================

@dataclass
class RecordBook:
    """Historical records across all seasons"""

    # Single-season team records
    most_wins_season: Dict = field(default_factory=lambda: {"team": None, "wins": 0, "year": None})
    most_points_season: Dict = field(default_factory=lambda: {"team": None, "points": 0.0, "year": None})
    best_defense_season: Dict = field(default_factory=lambda: {"team": None, "ppg_allowed": 999.9, "year": None})
    highest_opi_season: Dict = field(default_factory=lambda: {"team": None, "opi": 0.0, "year": None})
    most_chaos_season: Dict = field(default_factory=lambda: {"team": None, "chaos": 0.0, "year": None})

    # All-time team records
    most_championships: Dict = field(default_factory=lambda: {"team": None, "championships": 0})
    highest_win_percentage: Dict = field(default_factory=lambda: {"team": None, "win_pct": 0.0, "games": 0})

    # Coaching records
    most_coaching_wins: Dict = field(default_factory=lambda: {"coach": None, "wins": 0})
    most_coaching_championships: Dict = field(default_factory=lambda: {"coach": None, "championships": 0})


# ========================================
# DYNASTY MODE
# ========================================

@dataclass
class Dynasty:
    """Complete dynasty mode with multi-season tracking"""
    dynasty_name: str
    coach: Coach
    current_year: int

    # Teams and conferences
    conferences: Dict[str, Conference] = field(default_factory=dict)

    # Historical data
    team_histories: Dict[str, TeamHistory] = field(default_factory=dict)  # team_name -> TeamHistory
    player_stats: Dict[str, PlayerCareerStats] = field(default_factory=dict)  # player_name -> PlayerCareerStats

    # Season data
    seasons: Dict[int, Season] = field(default_factory=dict)  # year -> Season
    awards_history: Dict[int, SeasonAwards] = field(default_factory=dict)  # year -> SeasonAwards

    # Records
    record_book: RecordBook = field(default_factory=RecordBook)

    def add_conference(self, name: str, teams: List[str]):
        """Add a conference to the dynasty"""
        self.conferences[name] = Conference(name=name, teams=teams)

        for team_name in teams:
            if team_name not in self.team_histories:
                self.team_histories[team_name] = TeamHistory(team_name=team_name)

    def get_conferences_dict(self) -> Dict[str, List[str]]:
        """Get conferences as a simple dict for passing to Season"""
        return {name: conf.teams for name, conf in self.conferences.items()}

    def get_team_conference(self, team_name: str) -> str:
        """Get the conference a team belongs to"""
        for conf_name, conf in self.conferences.items():
            if team_name in conf.teams:
                return conf_name
        return ""

    def advance_season(self, season: Season):
        """
        Add a completed season to dynasty history

        Updates:
        - Team histories
        - Coach record
        - Awards
        - Record book
        """
        year = self.current_year
        self.seasons[year] = season

        # Update team histories
        for team_name, record in season.standings.items():
            history = self.team_histories[team_name]

            # Update all-time totals
            history.total_wins += record.wins
            history.total_losses += record.losses
            history.total_points_for += record.points_for
            history.total_points_against += record.points_against

            # Check if playoff team
            playoff_teams = [r.team_name for r in season.get_playoff_teams(num_teams=8)]
            if team_name in playoff_teams:
                history.total_playoff_appearances += 1

            # Check if champion
            if team_name == season.champion:
                history.total_championships += 1
                history.championship_years.append(year)

            # Store season record
            history.season_records[year] = {
                "wins": record.wins,
                "losses": record.losses,
                "points_for": record.points_for,
                "points_against": record.points_against,
                "avg_opi": record.avg_opi,
                "champion": (team_name == season.champion),
                "playoff": (team_name in playoff_teams),
            }

            # Check if best season ever for this team
            if record.wins > history.best_season_wins:
                history.best_season_wins = record.wins
                history.best_season_year = year

        # Update coach record (if coaching this season)
        if self.coach.team_name in season.standings:
            coach_record = season.standings[self.coach.team_name]
            self.coach.career_wins += coach_record.wins
            self.coach.career_losses += coach_record.losses
            self.coach.years_coached.append(year)

            if self.coach.first_year is None:
                self.coach.first_year = year
            self.coach.current_year = year

            # Check if champion
            if self.coach.team_name == season.champion:
                self.coach.championships += 1

            # Check if playoff
            playoff_teams = [r.team_name for r in season.get_playoff_teams(num_teams=8)]
            if self.coach.team_name in playoff_teams:
                self.coach.playoff_appearances += 1

            # Store coach season record
            self.coach.season_records[year] = {
                "wins": coach_record.wins,
                "losses": coach_record.losses,
                "points_for": coach_record.points_for,
                "points_against": coach_record.points_against,
                "champion": (self.coach.team_name == season.champion),
                "playoff": (self.coach.team_name in playoff_teams),
            }

        # Record awards
        standings = season.get_standings_sorted()
        highest_scoring = max(standings, key=lambda r: r.points_for / max(1, r.games_played))
        best_defense = min(standings, key=lambda r: r.points_against / max(1, r.games_played))
        highest_opi = max(standings, key=lambda r: r.avg_opi)
        most_chaos = max(standings, key=lambda r: r.avg_chaos)
        best_kicking = max(standings, key=lambda r: r.avg_kicking)

        self.awards_history[year] = SeasonAwards(
            year=year,
            champion=season.champion or "N/A",
            best_record=standings[0].team_name,
            highest_scoring=highest_scoring.team_name,
            best_defense=best_defense.team_name,
            highest_opi=highest_opi.team_name,
            most_chaos=most_chaos.team_name,
            best_kicking=best_kicking.team_name,
        )

        # Update record book
        self._update_record_book(year, season)

        # Advance year
        self.current_year += 1

    def _update_record_book(self, year: int, season: Season):
        """Update record book with new season results"""
        standings = season.get_standings_sorted()

        # Check single-season records
        for record in standings:
            # Most wins
            if record.wins > self.record_book.most_wins_season["wins"]:
                self.record_book.most_wins_season = {
                    "team": record.team_name,
                    "wins": record.wins,
                    "year": year,
                }

            # Most points
            if record.points_for > self.record_book.most_points_season["points"]:
                self.record_book.most_points_season = {
                    "team": record.team_name,
                    "points": record.points_for,
                    "year": year,
                }

            # Best defense (fewest PPG allowed)
            ppg_allowed = record.points_against / max(1, record.games_played)
            if ppg_allowed < self.record_book.best_defense_season["ppg_allowed"]:
                self.record_book.best_defense_season = {
                    "team": record.team_name,
                    "ppg_allowed": ppg_allowed,
                    "year": year,
                }

            # Highest OPI
            if record.avg_opi > self.record_book.highest_opi_season["opi"]:
                self.record_book.highest_opi_season = {
                    "team": record.team_name,
                    "opi": record.avg_opi,
                    "year": year,
                }

            # Most chaos
            if record.avg_chaos > self.record_book.most_chaos_season["chaos"]:
                self.record_book.most_chaos_season = {
                    "team": record.team_name,
                    "chaos": record.avg_chaos,
                    "year": year,
                }

        # Check all-time records
        for team_name, history in self.team_histories.items():
            # Most championships
            if history.total_championships > self.record_book.most_championships["championships"]:
                self.record_book.most_championships = {
                    "team": team_name,
                    "championships": history.total_championships,
                }

            # Highest win percentage (minimum 20 games)
            total_games = history.total_wins + history.total_losses
            if total_games >= 20:
                if history.win_percentage > self.record_book.highest_win_percentage["win_pct"]:
                    self.record_book.highest_win_percentage = {
                        "team": team_name,
                        "win_pct": history.win_percentage,
                        "games": total_games,
                    }

        # Coaching records
        if self.coach.career_wins > self.record_book.most_coaching_wins["wins"]:
            self.record_book.most_coaching_wins = {
                "coach": self.coach.name,
                "wins": self.coach.career_wins,
            }

        if self.coach.championships > self.record_book.most_coaching_championships["championships"]:
            self.record_book.most_coaching_championships = {
                "coach": self.coach.name,
                "championships": self.coach.championships,
            }

    def get_team_history(self, team_name: str) -> Optional[TeamHistory]:
        """Get historical record for a team"""
        return self.team_histories.get(team_name)

    def get_awards_for_year(self, year: int) -> Optional[SeasonAwards]:
        """Get awards for a specific year"""
        return self.awards_history.get(year)

    def get_conference_standings(self, conference_name: str, year: int) -> List[TeamRecord]:
        """Get standings for a specific conference in a specific year"""
        if year not in self.seasons:
            return []

        season = self.seasons[year]
        conference = self.conferences.get(conference_name)
        if not conference:
            return []

        # Filter standings to only teams in this conference
        conference_standings = [
            record for record in season.standings.values()
            if record.team_name in conference.teams
        ]

        # Sort by win%, then point differential
        return sorted(
            conference_standings,
            key=lambda r: (r.win_percentage, r.point_differential),
            reverse=True
        )

    def save(self, filepath: str):
        """Save dynasty to JSON file"""
        # Convert to dict (simplified - would need custom serialization for full support)
        data = {
            "dynasty_name": self.dynasty_name,
            "coach": asdict(self.coach),
            "current_year": self.current_year,
            "conferences": {name: asdict(conf) for name, conf in self.conferences.items()},
            "team_histories": {name: asdict(history) for name, history in self.team_histories.items()},
            "awards_history": {year: asdict(awards) for year, awards in self.awards_history.items()},
            "record_book": asdict(self.record_book),
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'Dynasty':
        """Load dynasty from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Reconstruct dynasty (simplified)
        dynasty = cls(
            dynasty_name=data["dynasty_name"],
            coach=Coach(**data["coach"]),
            current_year=data["current_year"],
        )

        # Reconstruct conferences
        for name, conf_data in data["conferences"].items():
            dynasty.conferences[name] = Conference(**conf_data)

        # Reconstruct team histories
        for name, history_data in data["team_histories"].items():
            dynasty.team_histories[name] = TeamHistory(**history_data)

        # Reconstruct awards
        for year, awards_data in data["awards_history"].items():
            dynasty.awards_history[int(year)] = SeasonAwards(**awards_data)

        # Reconstruct record book
        dynasty.record_book = RecordBook(**data["record_book"])

        return dynasty


def create_dynasty(
    dynasty_name: str,
    coach_name: str,
    coach_team: str,
    starting_year: int = 2026
) -> Dynasty:
    """
    Create a new dynasty

    Args:
        dynasty_name: Name of the dynasty (e.g., "My Viperball Dynasty")
        coach_name: Name of the coach (user)
        coach_team: Team the coach is managing
        starting_year: First year of the dynasty

    Returns:
        Dynasty object ready for season simulation
    """
    coach = Coach(name=coach_name, team_name=coach_team)

    return Dynasty(
        dynasty_name=dynasty_name,
        coach=coach,
        current_year=starting_year,
    )
