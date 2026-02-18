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

    def generate_schedule(self, games_per_team: int = 0, conference_weight: float = 0.6, non_conf_weeks: int = 3):
        """
        Generate a season schedule with configurable game count.

        Args:
            games_per_team: Number of games each team plays. 0 = full round-robin.
            conference_weight: Proportion of games that should be conference games (0.0-1.0).
                             Only applies when conferences exist and games_per_team > 0.
            non_conf_weeks: Number of early weeks reserved for non-conference games (1-4).
        """
        team_names = list(self.teams.keys())
        num_teams = len(team_names)

        if games_per_team <= 0 or games_per_team >= num_teams - 1:
            self._generate_round_robin(team_names)
        else:
            self._generate_partial_schedule(team_names, games_per_team, conference_weight)

        self._assign_weeks_by_type(non_conf_weeks)

    def _assign_weeks_by_type(self, non_conf_weeks: int = 3):
        """Assign week numbers: non-conference games fill early weeks, conference games fill later weeks."""
        if not self.schedule:
            return

        non_conf = [g for g in self.schedule if not g.is_conference_game]
        conf = [g for g in self.schedule if g.is_conference_game]
        random.shuffle(non_conf)
        random.shuffle(conf)

        team_names = list(self.teams.keys())
        games_per_slot = max(1, len(team_names) // 2)

        max_early_games = non_conf_weeks * games_per_slot
        early_non_conf = non_conf[:max_early_games]
        overflow_non_conf = non_conf[max_early_games:]

        ordered = early_non_conf + conf + overflow_non_conf

        for i, game in enumerate(ordered):
            game.week = (i // games_per_slot) + 1
        self.schedule = ordered

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

        # Geo-aware weather: use home team's state if available
        home_state = self.team_states.get(game.home_team)
        total_weeks = max((g.week for g in self.schedule), default=18)
        season_weather = generate_game_weather(
            state=home_state,
            week=game.week,
            total_weeks=total_weeks,
        )

        engine = ViperballEngine(
            home_team,
            away_team,
            seed=random.randint(1, 1000000),
            style_overrides=style_overrides,
            weather=season_weather
        )
        result = engine.simulate_game()

        for p in home_team.players:
            p.season_games_played = getattr(p, 'season_games_played', 0) + 1
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

    def simulate_week(self, week: Optional[int] = None, verbose: bool = False,
                      generate_polls: bool = True) -> List[Game]:
        """Simulate a single week of games. Returns list of games played.

        Args:
            week: Specific week number to simulate. If None, simulates the next
                  unplayed week.
            generate_polls: Whether to generate a poll after this week.
            verbose: Enable verbose output.

        Returns:
            List of Game objects that were simulated this week, or empty list
            if no games remain.
        """
        if week is None:
            week = self.get_next_unplayed_week()
            if week is None:
                return []

        week_games = [g for g in self.schedule if g.week == week and not g.completed]
        for game in week_games:
            self.simulate_game(game, verbose=verbose)

        if generate_polls and week_games:
            self._generate_weekly_poll(week)

        return week_games

    def simulate_through_week(self, target_week: int, verbose: bool = False,
                              generate_polls: bool = True) -> List[Game]:
        """Simulate all unplayed weeks up to and including target_week.

        Returns all games simulated across those weeks.
        """
        all_games = []
        while True:
            next_week = self.get_next_unplayed_week()
            if next_week is None or next_week > target_week:
                break
            games = self.simulate_week(next_week, verbose=verbose,
                                       generate_polls=generate_polls)
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

    def simulate_season(self, verbose: bool = False, generate_polls: bool = True):
        """Simulate all remaining regular season games, optionally generating weekly polls"""
        while True:
            games = self.simulate_week(verbose=verbose, generate_polls=generate_polls)
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


def load_teams_from_directory(directory: str, fresh: bool = False) -> Dict[str, Team]:
    """Load all teams from a directory.

    Args:
        directory: Path to team JSON directory.
        fresh: If True, generate brand-new rosters for every team (new season/dynasty).
               If False, load stored rosters from JSON files (saved game).
    """
    teams = {}
    team_dir = Path(directory)

    for team_file in team_dir.glob("*.json"):
        team = load_team_from_json(str(team_file), fresh=fresh)
        teams[team.name] = team

    return teams


def load_teams_with_states(directory: str, fresh: bool = False) -> tuple:
    """
    Load all teams from a directory and also return a state map for weather.

    Args:
        directory: Path to team JSON directory.
        fresh: If True, generate brand-new rosters for every team.

    Returns:
        (teams_dict, team_states_dict) where team_states maps team_name -> state
    """
    import json as _json
    teams = {}
    team_states = {}
    team_dir = Path(directory)

    for team_file in team_dir.glob("*.json"):
        with open(team_file) as f:
            raw = _json.load(f)
        state = raw.get("team_info", {}).get("state", "")
        team = load_team_from_json(str(team_file), fresh=fresh)
        teams[team.name] = team
        if state:
            team_states[team.name] = state

    return teams, team_states


def create_season(
    name: str,
    teams: Dict[str, Team],
    style_configs: Optional[Dict[str, Dict[str, str]]] = None,
    conferences: Optional[Dict[str, List[str]]] = None,
    games_per_team: int = 0,
    team_states: Optional[Dict[str, str]] = None,
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
    )

    season.generate_schedule(games_per_team=games_per_team)

    return season
