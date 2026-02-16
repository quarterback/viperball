"""
Season Simulation for Viperball Dynasty Mode

Handles:
- Schedule generation (round-robin, conference play)
- Season-long standings
- Playoff brackets
- Season metrics and statistics
- Championship resolution
"""

import json
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path

from engine.game_engine import ViperballEngine, Team, load_team_from_json
from engine.viperball_metrics import calculate_viperball_metrics


@dataclass
class TeamRecord:
    """Season record for a single team"""
    team_name: str
    wins: int = 0
    losses: int = 0
    points_for: float = 0.0
    points_against: float = 0.0

    # Season-long cumulative metrics
    total_opi: float = 0.0
    total_territory: float = 0.0
    total_pressure: float = 0.0
    total_chaos: float = 0.0
    total_kicking: float = 0.0
    total_drive_quality: float = 0.0
    total_turnover_impact: float = 0.0
    games_played: int = 0

    # Style configuration
    offense_style: str = "balanced"
    defense_style: str = "base_defense"

    def add_game_result(self, won: bool, points_for: float, points_against: float, metrics: Dict):
        """Add a game result to the season record"""
        if won:
            self.wins += 1
        else:
            self.losses += 1

        self.points_for += points_for
        self.points_against += points_against

        # Accumulate metrics
        self.total_opi += metrics.get('opi', 0.0)
        self.total_territory += metrics.get('territory_rating', 0.0)
        self.total_pressure += metrics.get('pressure_index', 0.0)
        self.total_chaos += metrics.get('chaos_factor', 0.0)
        self.total_kicking += metrics.get('kicking_efficiency', 0.0)
        self.total_drive_quality += metrics.get('drive_quality', 0.0)
        self.total_turnover_impact += metrics.get('turnover_impact', 0.0)
        self.games_played += 1

    @property
    def avg_opi(self) -> float:
        """Average OPI across all games"""
        return self.total_opi / self.games_played if self.games_played > 0 else 0.0

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
    def win_percentage(self) -> float:
        """Win percentage (0.0 to 1.0)"""
        total_games = self.wins + self.losses
        return self.wins / total_games if total_games > 0 else 0.0

    @property
    def point_differential(self) -> float:
        """Average point differential per game"""
        total_games = self.wins + self.losses
        return (self.points_for - self.points_against) / total_games if total_games > 0 else 0.0


@dataclass
class Game:
    """Single game in the season"""
    week: int
    home_team: str
    away_team: str
    home_score: Optional[float] = None
    away_score: Optional[float] = None
    completed: bool = False

    # Game metrics for both teams
    home_metrics: Optional[Dict] = None
    away_metrics: Optional[Dict] = None


@dataclass
class Season:
    """Complete season simulation"""
    name: str
    teams: Dict[str, Team]
    schedule: List[Game] = field(default_factory=list)
    standings: Dict[str, TeamRecord] = field(default_factory=dict)

    # Style configurations for each team
    style_configs: Dict[str, Dict[str, str]] = field(default_factory=dict)

    # Playoff results
    playoff_bracket: List[Game] = field(default_factory=list)
    champion: Optional[str] = None

    def __post_init__(self):
        """Initialize standings for all teams"""
        for team_name, team in self.teams.items():
            # Get style config if exists
            style_config = self.style_configs.get(team_name, {})
            offense_style = style_config.get('offense_style', 'balanced')
            defense_style = style_config.get('defense_style', 'base_defense')

            self.standings[team_name] = TeamRecord(
                team_name=team_name,
                offense_style=offense_style,
                defense_style=defense_style
            )

    def generate_round_robin_schedule(self):
        """Generate a round-robin schedule where each team plays each other once"""
        team_names = list(self.teams.keys())
        week = 1

        # Generate all unique matchups
        for i in range(len(team_names)):
            for j in range(i + 1, len(team_names)):
                home = team_names[i]
                away = team_names[j]

                # Randomly decide home/away
                if random.random() < 0.5:
                    home, away = away, home

                self.schedule.append(Game(
                    week=week,
                    home_team=home,
                    away_team=away
                ))
                week += 1

        # Shuffle schedule for variety
        random.shuffle(self.schedule)

        # Reassign weeks sequentially
        for i, game in enumerate(self.schedule):
            game.week = (i // (len(team_names) // 2)) + 1

    def simulate_game(self, game: Game, verbose: bool = False) -> Dict:
        """Simulate a single game and update standings"""
        home_team = self.teams[game.home_team]
        away_team = self.teams[game.away_team]

        # Get style overrides for both teams
        home_style_config = self.style_configs.get(game.home_team, {})
        away_style_config = self.style_configs.get(game.away_team, {})

        style_overrides = {
            home_team.name: home_style_config.get('offense_style', 'balanced'),
            f"{home_team.name}_defense": home_style_config.get('defense_style', 'base_defense'),
            away_team.name: away_style_config.get('offense_style', 'balanced'),
            f"{away_team.name}_defense": away_style_config.get('defense_style', 'base_defense'),
        }

        # Simulate the game
        engine = ViperballEngine(
            home_team,
            away_team,
            seed=random.randint(1, 1000000),
            style_overrides=style_overrides
        )
        result = engine.simulate_game()

        # Extract scores
        game.home_score = result['final_score']['home']['score']
        game.away_score = result['final_score']['away']['score']
        game.completed = True

        # Calculate metrics for both teams
        home_metrics = calculate_viperball_metrics(result, 'home')
        away_metrics = calculate_viperball_metrics(result, 'away')

        game.home_metrics = home_metrics
        game.away_metrics = away_metrics

        # Update standings
        home_won = game.home_score > game.away_score
        away_won = game.away_score > game.home_score

        self.standings[game.home_team].add_game_result(
            won=home_won,
            points_for=game.home_score,
            points_against=game.away_score,
            metrics=home_metrics
        )

        self.standings[game.away_team].add_game_result(
            won=away_won,
            points_for=game.away_score,
            points_against=game.home_score,
            metrics=away_metrics
        )

        if verbose:
            print(f"Week {game.week}: {game.away_team} @ {game.home_team}")
            print(f"  Final: {game.away_team} {game.away_score:.1f} - {game.home_team} {game.home_score:.1f}")
            print(f"  {game.home_team} OPI: {home_metrics['opi']:.1f}/100")
            print(f"  {game.away_team} OPI: {away_metrics['opi']:.1f}/100")

        return result

    def simulate_season(self, verbose: bool = False):
        """Simulate all regular season games"""
        for game in self.schedule:
            if not game.completed:
                self.simulate_game(game, verbose=verbose)

    def get_standings_sorted(self) -> List[TeamRecord]:
        """Get standings sorted by win percentage, then point differential"""
        return sorted(
            self.standings.values(),
            key=lambda r: (r.win_percentage, r.point_differential),
            reverse=True
        )

    def get_playoff_teams(self, num_teams: int = 4) -> List[TeamRecord]:
        """Get top N teams for playoffs"""
        sorted_standings = self.get_standings_sorted()
        return sorted_standings[:num_teams]

    def simulate_playoff(self, num_teams: int = 4, verbose: bool = False):
        """
        Simulate playoff bracket

        num_teams: 4 (semifinals + final) or 8 (quarterfinals + semifinals + final)
        """
        playoff_teams = self.get_playoff_teams(num_teams)

        if num_teams == 4:
            # Semifinals: #1 vs #4, #2 vs #3
            semi1 = Game(
                week=999,  # Playoff week
                home_team=playoff_teams[0].team_name,
                away_team=playoff_teams[3].team_name
            )
            semi2 = Game(
                week=999,
                home_team=playoff_teams[1].team_name,
                away_team=playoff_teams[2].team_name
            )

            self.playoff_bracket.append(semi1)
            self.playoff_bracket.append(semi2)

            if verbose:
                print("\n🏆 SEMIFINALS")
                print("=" * 70)

            self.simulate_game(semi1, verbose=verbose)
            self.simulate_game(semi2, verbose=verbose)

            # Championship
            semi1_winner = semi1.home_team if semi1.home_score > semi1.away_score else semi1.away_team
            semi2_winner = semi2.home_team if semi2.home_score > semi2.away_score else semi2.away_team

            championship = Game(
                week=1000,  # Championship week
                home_team=semi1_winner,
                away_team=semi2_winner
            )

            self.playoff_bracket.append(championship)

            if verbose:
                print("\n🏆 CHAMPIONSHIP")
                print("=" * 70)

            self.simulate_game(championship, verbose=verbose)

            self.champion = championship.home_team if championship.home_score > championship.away_score else championship.away_team

        elif num_teams == 8:
            # Quarterfinals: 1v8, 2v7, 3v6, 4v5
            quarters = []
            for i in range(4):
                game = Game(
                    week=998,
                    home_team=playoff_teams[i].team_name,
                    away_team=playoff_teams[7-i].team_name
                )
                quarters.append(game)
                self.playoff_bracket.append(game)

            if verbose:
                print("\n🏆 QUARTERFINALS")
                print("=" * 70)

            for game in quarters:
                self.simulate_game(game, verbose=verbose)

            # Semifinals
            semi1 = Game(
                week=999,
                home_team=quarters[0].home_team if quarters[0].home_score > quarters[0].away_score else quarters[0].away_team,
                away_team=quarters[3].home_team if quarters[3].home_score > quarters[3].away_score else quarters[3].away_team
            )
            semi2 = Game(
                week=999,
                home_team=quarters[1].home_team if quarters[1].home_score > quarters[1].away_score else quarters[1].away_team,
                away_team=quarters[2].home_team if quarters[2].home_score > quarters[2].away_score else quarters[2].away_team
            )

            self.playoff_bracket.append(semi1)
            self.playoff_bracket.append(semi2)

            if verbose:
                print("\n🏆 SEMIFINALS")
                print("=" * 70)

            self.simulate_game(semi1, verbose=verbose)
            self.simulate_game(semi2, verbose=verbose)

            # Championship
            championship = Game(
                week=1000,
                home_team=semi1.home_team if semi1.home_score > semi1.away_score else semi1.away_team,
                away_team=semi2.home_team if semi2.home_score > semi2.away_score else semi2.away_team
            )

            self.playoff_bracket.append(championship)

            if verbose:
                print("\n🏆 CHAMPIONSHIP")
                print("=" * 70)

            self.simulate_game(championship, verbose=verbose)

            self.champion = championship.home_team if championship.home_score > championship.away_score else championship.away_team


def load_teams_from_directory(directory: str) -> Dict[str, Team]:
    """Load all teams from a directory"""
    teams = {}
    team_dir = Path(directory)

    for team_file in team_dir.glob("*.json"):
        team = load_team_from_json(str(team_file))
        teams[team.name] = team

    return teams


def create_season(
    name: str,
    teams: Dict[str, Team],
    style_configs: Optional[Dict[str, Dict[str, str]]] = None
) -> Season:
    """
    Create a season with teams and optional style configurations

    Args:
        name: Season name (e.g., "2026 Season")
        teams: Dictionary of team_name -> Team
        style_configs: Optional dictionary of team_name -> {'offense_style': ..., 'defense_style': ...}

    Returns:
        Season object ready for simulation
    """
    return Season(
        name=name,
        teams=teams,
        style_configs=style_configs or {}
    )
