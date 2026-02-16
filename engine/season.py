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
from engine.viperball_metrics import calculate_viperball_metrics


@dataclass
class TeamRecord:
    """Season record for a single team"""
    team_name: str
    wins: int = 0
    losses: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    conference: str = ""

    total_opi: float = 0.0
    total_territory: float = 0.0
    total_pressure: float = 0.0
    total_chaos: float = 0.0
    total_kicking: float = 0.0
    total_drive_quality: float = 0.0
    total_turnover_impact: float = 0.0
    games_played: int = 0

    conf_wins: int = 0
    conf_losses: int = 0

    offense_style: str = "balanced"
    defense_style: str = "base_defense"

    def add_game_result(self, won: bool, points_for: float, points_against: float,
                        metrics: Dict, is_conference_game: bool = False):
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


@dataclass
class PollRanking:
    """A single team's poll ranking for a given week"""
    rank: int
    team_name: str
    record: str
    conference: str
    poll_score: float
    prev_rank: Optional[int] = None

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

    home_metrics: Optional[Dict] = None
    away_metrics: Optional[Dict] = None


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

    weekly_polls: List[WeeklyPoll] = field(default_factory=list)

    playoff_bracket: List[Game] = field(default_factory=list)
    champion: Optional[str] = None

    def __post_init__(self):
        for team_name, team in self.teams.items():
            style_config = self.style_configs.get(team_name, {})
            offense_style = style_config.get('offense_style', 'balanced')
            defense_style = style_config.get('defense_style', 'base_defense')
            conf = self.team_conferences.get(team_name, "")

            self.standings[team_name] = TeamRecord(
                team_name=team_name,
                offense_style=offense_style,
                defense_style=defense_style,
                conference=conf
            )

    def generate_schedule(self, games_per_team: int = 0, conference_weight: float = 0.6):
        """
        Generate a season schedule with configurable game count.

        Args:
            games_per_team: Number of games each team plays. 0 = full round-robin.
            conference_weight: Proportion of games that should be conference games (0.0-1.0).
                             Only applies when conferences exist and games_per_team > 0.
        """
        team_names = list(self.teams.keys())
        num_teams = len(team_names)

        if games_per_team <= 0 or games_per_team >= num_teams - 1:
            self._generate_round_robin(team_names)
        else:
            self._generate_partial_schedule(team_names, games_per_team, conference_weight)

    def _generate_round_robin(self, team_names: List[str]):
        """Full round-robin: each team plays each other once"""
        games = []
        for i in range(len(team_names)):
            for j in range(i + 1, len(team_names)):
                home = team_names[i]
                away = team_names[j]
                if random.random() < 0.5:
                    home, away = away, home

                is_conf = (self.team_conferences.get(home, "") == self.team_conferences.get(away, "")
                           and self.team_conferences.get(home, "") != "")
                games.append(Game(week=0, home_team=home, away_team=away, is_conference_game=is_conf))

        random.shuffle(games)
        games_per_slot = max(1, len(team_names) // 2)
        for i, game in enumerate(games):
            game.week = (i // games_per_slot) + 1
        self.schedule = games

    def _generate_partial_schedule(self, team_names: List[str], games_per_team: int,
                                    conference_weight: float):
        """Generate a schedule: conference round-robin first, then non-conference fill.

        Conference games: full round-robin within conference. If conference is too
        large (more opponents than games_per_team), each team plays a random subset
        of conference opponents.

        Non-conference games: remaining slots filled with cross-conference matchups.
        """
        game_counts = {name: 0 for name in team_names}
        scheduled_pairs = set()
        games = []

        has_conferences = bool(self.conferences) and len(self.conferences) > 1

        def _add_game(home, away, is_conf):
            if random.random() < 0.5:
                home, away = away, home
            games.append(Game(week=0, home_team=home, away_team=away, is_conference_game=is_conf))
            scheduled_pairs.add(tuple(sorted([home, away])))
            game_counts[home] += 1
            game_counts[away] += 1

        if has_conferences:
            for conf_name, conf_teams in self.conferences.items():
                conf_team_list = [t for t in conf_teams if t in self.teams]
                if len(conf_team_list) < 2:
                    continue

                conf_size = len(conf_team_list) - 1

                if conf_size <= games_per_team:
                    for i in range(len(conf_team_list)):
                        for j in range(i + 1, len(conf_team_list)):
                            h, a = conf_team_list[i], conf_team_list[j]
                            pair = tuple(sorted([h, a]))
                            if pair not in scheduled_pairs:
                                _add_game(h, a, True)
                else:
                    max_conf_games = games_per_team - 2
                    for team in conf_team_list:
                        opponents = [t for t in conf_team_list if t != team]
                        random.shuffle(opponents)
                        for opp in opponents[:max_conf_games]:
                            pair = tuple(sorted([team, opp]))
                            if pair in scheduled_pairs:
                                continue
                            if game_counts[team] >= games_per_team or game_counts[opp] >= games_per_team:
                                continue
                            _add_game(team, opp, True)

            nonconf_matchups = []
            for i in range(len(team_names)):
                for j in range(i + 1, len(team_names)):
                    t1, t2 = team_names[i], team_names[j]
                    c1 = self.team_conferences.get(t1, "")
                    c2 = self.team_conferences.get(t2, "")
                    if c1 != c2 or c1 == "":
                        nonconf_matchups.append((t1, t2))
            random.shuffle(nonconf_matchups)

            for home, away in nonconf_matchups:
                if game_counts[home] >= games_per_team or game_counts[away] >= games_per_team:
                    continue
                pair = tuple(sorted([home, away]))
                if pair in scheduled_pairs:
                    continue
                _add_game(home, away, False)
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

        random.shuffle(games)
        games_per_slot = max(1, len(team_names) // 2)
        for i, game in enumerate(games):
            game.week = (i // games_per_slot) + 1
        self.schedule = games

    def generate_round_robin_schedule(self):
        """Legacy method - generates full round-robin"""
        self.generate_schedule(games_per_team=0)

    def simulate_game(self, game: Game, verbose: bool = False) -> Dict:
        """Simulate a single game and update standings"""
        home_team = self.teams[game.home_team]
        away_team = self.teams[game.away_team]

        home_style_config = self.style_configs.get(game.home_team, {})
        away_style_config = self.style_configs.get(game.away_team, {})

        style_overrides = {
            home_team.name: home_style_config.get('offense_style', 'balanced'),
            f"{home_team.name}_defense": home_style_config.get('defense_style', 'base_defense'),
            away_team.name: away_style_config.get('offense_style', 'balanced'),
            f"{away_team.name}_defense": away_style_config.get('defense_style', 'base_defense'),
        }

        engine = ViperballEngine(
            home_team,
            away_team,
            seed=random.randint(1, 1000000),
            style_overrides=style_overrides
        )
        result = engine.simulate_game()

        game.home_score = result['final_score']['home']['score']
        game.away_score = result['final_score']['away']['score']
        game.completed = True

        home_metrics = calculate_viperball_metrics(result, 'home')
        away_metrics = calculate_viperball_metrics(result, 'away')

        game.home_metrics = home_metrics
        game.away_metrics = away_metrics

        home_won = game.home_score > game.away_score
        away_won = game.away_score > game.home_score

        self.standings[game.home_team].add_game_result(
            won=home_won,
            points_for=game.home_score,
            points_against=game.away_score,
            metrics=home_metrics,
            is_conference_game=game.is_conference_game
        )

        self.standings[game.away_team].add_game_result(
            won=away_won,
            points_for=game.away_score,
            points_against=game.home_score,
            metrics=away_metrics,
            is_conference_game=game.is_conference_game
        )

        return result

    def simulate_season(self, verbose: bool = False, generate_polls: bool = True):
        """Simulate all regular season games, optionally generating weekly polls"""
        weeks = sorted(set(g.week for g in self.schedule if not g.completed))

        for week in weeks:
            week_games = [g for g in self.schedule if g.week == week and not g.completed]
            for game in week_games:
                self.simulate_game(game, verbose=verbose)

            if generate_polls:
                self._generate_weekly_poll(week)

    def _calculate_poll_score(self, record: TeamRecord) -> float:
        """Calculate poll ranking score for a team"""
        if record.games_played == 0:
            return 0.0

        win_score = record.win_percentage * 40

        opi_score = min(20, record.avg_opi * 0.2)

        ppg = record.points_for / max(1, record.games_played)
        ppg_against = record.points_against / max(1, record.games_played)
        diff = ppg - ppg_against
        diff_score = min(15, max(0, (diff + 20) * 0.375))

        sos = self._calculate_sos(record.team_name)
        sos_score = sos * 25

        return win_score + opi_score + diff_score + sos_score

    def _calculate_sos(self, team_name: str) -> float:
        """Calculate strength of schedule for a team based on opponent win percentages"""
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
        for opp in opponents:
            if opp in self.standings:
                opp_win_pcts.append(self.standings[opp].win_percentage)

        return sum(opp_win_pcts) / len(opp_win_pcts) if opp_win_pcts else 0.5

    def _generate_weekly_poll(self, week: int):
        """Generate rankings after a week of games"""
        prev_poll = self.weekly_polls[-1] if self.weekly_polls else None
        prev_ranks = {}
        if prev_poll:
            for r in prev_poll.rankings:
                prev_ranks[r.team_name] = r.rank

        team_scores = []
        for team_name, record in self.standings.items():
            if record.games_played > 0:
                score = self._calculate_poll_score(record)
                team_scores.append((team_name, record, score))

        team_scores.sort(key=lambda x: x[2], reverse=True)

        rankings = []
        for i, (team_name, record, score) in enumerate(team_scores[:25], 1):
            rankings.append(PollRanking(
                rank=i,
                team_name=team_name,
                record=f"{record.wins}-{record.losses}",
                conference=record.conference,
                poll_score=round(score, 2),
                prev_rank=prev_ranks.get(team_name)
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
        sorted_standings = self.get_standings_sorted()
        return sorted_standings[:num_teams]

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
    style_configs: Optional[Dict[str, Dict[str, str]]] = None,
    conferences: Optional[Dict[str, List[str]]] = None,
    games_per_team: int = 0
) -> Season:
    """
    Create a season with teams and optional style configurations

    Args:
        name: Season name
        teams: Dictionary of team_name -> Team
        style_configs: Optional dictionary of team_name -> {'offense_style': ..., 'defense_style': ...}
        conferences: Optional dictionary of conference_name -> [team_names]
        games_per_team: Games per team (0 = full round-robin)

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
    )

    season.generate_schedule(games_per_team=games_per_team)

    return season
