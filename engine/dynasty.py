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
import random
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict

from engine.season import Season, TeamRecord, Game, load_teams_from_directory, create_season
from engine.awards import SeasonHonors, compute_season_awards
from engine.injuries import InjuryTracker
from engine.development import apply_team_development, get_preseason_breakout_candidates, DevelopmentReport
from engine.ai_coach import auto_assign_all_teams
from engine.player_card import player_to_card


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

    # Individual & collective honors (SeasonHonors object serialised as dict)
    honors: Optional[dict] = None   # SeasonHonors.to_dict() stored here

    # Convenience accessors for individual awards
    def get_individual_award(self, award_name: str) -> Optional[dict]:
        if not self.honors:
            return None
        for a in self.honors.get("individual_awards", []):
            if a.get("award_name") == award_name:
                return a
        return None

    @property
    def coach_of_year(self) -> str:
        return self.honors.get("coach_of_year", "") if self.honors else ""

    @property
    def most_improved(self) -> str:
        return self.honors.get("most_improved", "") if self.honors else ""


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

    # Full honors (All-American, All-Conference, individual awards)
    honors_history: Dict[int, dict] = field(default_factory=dict)  # year -> SeasonHonors.to_dict()

    # Injury history per season
    injury_history: Dict[int, dict] = field(default_factory=dict)  # year -> InjuryTracker.get_season_injury_report()

    # Development history: year -> list of notable development event dicts
    development_history: Dict[int, List[dict]] = field(default_factory=dict)

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

    def _roster_maintenance(self, season: Season, rng: Optional[random.Random] = None):
        """Remove graduated players and recruit new freshmen for all teams.

        Called after development (which advances class years) so that
        players who just became 'Graduate' after their Senior year are removed,
        and new Freshman players are recruited to fill the roster back to 36.
        Uses ROSTER_TEMPLATE from game_engine for position distribution.
        """
        from engine.game_engine import Player
        from scripts.generate_names import generate_player_name, build_geo_pipeline
        from scripts.generate_rosters import generate_player_attributes, assign_archetype

        if rng is None:
            rng = random.Random()

        ROSTER_TARGET = 36
        ROSTER_TEMPLATE = [
            ("Viper/Back", True), ("Viper/Back", False),
            ("Zeroback/Back", False), ("Zeroback/Back", False),
            ("Halfback/Back", False), ("Halfback/Back", False),
            ("Halfback/Back", False), ("Halfback/Back", False),
            ("Wingback/End", False), ("Wingback/End", False),
            ("Wingback/End", False), ("Wingback/End", False),
            ("Shiftback/Back", False), ("Shiftback/Back", False),
            ("Lineman", False), ("Lineman", False), ("Lineman", False),
            ("Lineman", False), ("Lineman", False),
            ("Wedge/Line", False), ("Wedge/Line", False), ("Wedge/Line", False),
            ("Back/Safety", False), ("Back/Safety", False),
            ("Back/Safety", False), ("Back/Safety", False),
            ("Back/Corner", False), ("Back/Corner", False),
            ("Back/Corner", False), ("Back/Corner", False),
            ("Wing/End", False), ("Wing/End", False),
            ("Wing/End", False), ("Wing/End", False),
            ("Back/Safety", False), ("Back/Corner", False),
        ]

        import os
        teams_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")
        team_state_cache = {}
        try:
            for f in os.listdir(teams_dir):
                if f.endswith(".json"):
                    with open(os.path.join(teams_dir, f)) as fh:
                        td = json.load(fh)
                    tn = td.get("team_info", {}).get("school") or td.get("team_info", {}).get("school_name", "")
                    if tn:
                        team_state_cache[tn] = td.get("team_info", {}).get("state", "")
        except Exception:
            pass

        for team_name, team in season.teams.items():
            graduated = [p for p in team.players if getattr(p, 'year', '') == 'Graduate']
            remaining = [p for p in team.players if getattr(p, 'year', '') != 'Graduate']
            team.players = remaining

            slots_to_fill = max(0, ROSTER_TARGET - len(remaining))
            if slots_to_fill == 0:
                continue

            current_positions = {}
            for p in remaining:
                current_positions[p.position] = current_positions.get(p.position, 0) + 1

            template_counts = {}
            for pos, _ in ROSTER_TEMPLATE:
                template_counts[pos] = template_counts.get(pos, 0) + 1

            recruit_positions = []
            for pos, target in template_counts.items():
                current = current_positions.get(pos, 0)
                deficit = target - current
                for _ in range(max(0, deficit)):
                    if len(recruit_positions) < slots_to_fill:
                        recruit_positions.append(pos)

            while len(recruit_positions) < slots_to_fill:
                recruit_positions.append(rng.choice([p for p, _ in ROSTER_TEMPLATE]))

            used_numbers = {p.number for p in remaining}
            state_str = team_state_cache.get(team_name, "")
            pipeline = build_geo_pipeline(state_str) if state_str else None
            philosophy = getattr(team, 'philosophy', 'hybrid') if hasattr(team, 'philosophy') else 'hybrid'

            for pos in recruit_positions:
                number = None
                while number is None or number in used_numbers:
                    number = rng.randint(2, 99)
                used_numbers.add(number)

                is_viper = "Viper" in pos
                name_data = generate_player_name(
                    school_recruiting_pipeline=pipeline,
                    year="freshman",
                )
                attrs = generate_player_attributes(pos, philosophy, "freshman", is_viper)
                archetype = assign_archetype(
                    pos,
                    attrs["speed"], attrs["stamina"],
                    attrs["kicking"], attrs["lateral_skill"], attrs["tackling"],
                )
                hometown = name_data.get("hometown", {})

                team.players.append(Player(
                    number=number,
                    name=name_data["full_name"],
                    position=pos,
                    speed=attrs["speed"],
                    stamina=attrs["stamina"],
                    kicking=attrs["kicking"],
                    lateral_skill=attrs["lateral_skill"],
                    tackling=attrs["tackling"],
                    agility=attrs.get("agility", 75),
                    power=attrs.get("power", 75),
                    awareness=attrs.get("awareness", 75),
                    hands=attrs.get("hands", 75),
                    kick_power=attrs.get("kick_power", 75),
                    kick_accuracy=attrs.get("kick_accuracy", 75),
                    archetype=archetype,
                    player_id=name_data.get("player_id", ""),
                    nationality=name_data.get("nationality", "American"),
                    hometown_city=hometown.get("city", ""),
                    hometown_country=hometown.get("country", "USA"),
                    high_school=name_data.get("high_school", ""),
                    height=attrs.get("height", "5-10"),
                    weight=attrs.get("weight", 170),
                    year="Freshman",
                    potential=attrs.get("potential", 3),
                    development=attrs.get("development", "normal"),
                ))

    def advance_season(
        self,
        season: Season,
        injury_tracker: Optional["InjuryTracker"] = None,
        player_cards: Optional[Dict[str, list]] = None,
        rng: Optional[random.Random] = None,
    ):
        """
        Add a completed season to dynasty history.

        Updates:
        - Team histories
        - Coach record
        - Team + individual awards (SeasonAwards + SeasonHonors)
        - All-American / All-Conference teams
        - Injury history (if tracker provided)
        - Player development arcs (if player_cards provided)
        - Record book

        Args:
            season:          Completed Season object
            injury_tracker:  Optional InjuryTracker from this season
            player_cards:    Optional dict of team_name -> list[PlayerCard] for dev arcs
            rng:             Optional seeded Random for reproducibility
        """
        year = self.current_year
        self.seasons[year] = season

        # Determine previous season wins for Most Improved calculation
        prev_wins = {}
        if (year - 1) in self.seasons:
            for t, r in self.seasons[year - 1].standings.items():
                prev_wins[t] = r.wins

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

        # Team-level standings
        standings = season.get_standings_sorted()
        highest_scoring = max(standings, key=lambda r: r.points_for / max(1, r.games_played))
        best_defense = min(standings, key=lambda r: r.points_against / max(1, r.games_played))
        highest_opi = max(standings, key=lambda r: r.avg_opi)
        most_chaos = max(standings, key=lambda r: r.avg_chaos)
        best_kicking = max(standings, key=lambda r: r.avg_kicking)

        # Compute full honors (All-American, All-Conference, individual awards)
        conf_dict = self.get_conferences_dict() if self.conferences else None
        honors = compute_season_awards(
            season=season,
            year=year,
            conferences=conf_dict,
            prev_season_wins=prev_wins if prev_wins else None,
        )
        self.honors_history[year] = honors.to_dict()

        self.awards_history[year] = SeasonAwards(
            year=year,
            champion=season.champion or "N/A",
            best_record=standings[0].team_name,
            highest_scoring=highest_scoring.team_name,
            best_defense=best_defense.team_name,
            highest_opi=highest_opi.team_name,
            most_chaos=most_chaos.team_name,
            best_kicking=best_kicking.team_name,
            honors=honors.to_dict(),
        )

        # Store injury history for this season
        if injury_tracker is not None:
            self.injury_history[year] = injury_tracker.get_season_injury_report()

        # Apply player development (offseason)
        if player_cards is not None:
            dev_events = []
            dev_rng = rng or random.Random(year + 42)
            for team_name, cards in player_cards.items():
                report = apply_team_development(cards, rng=dev_rng)
                for ev in report.notable_events:
                    dev_events.append({
                        "team": team_name,
                        "player": ev.player_name,
                        "event_type": ev.event_type,
                        "description": ev.description,
                        "attr_changes": ev.attr_changes,
                    })
            self.development_history[year] = dev_events

        # Roster maintenance: graduate seniors, recruit freshmen
        self._roster_maintenance(season, rng=rng or random.Random(year + 99))

        # Update record book
        self._update_record_book(year, season)

        # Advance year
        self.current_year += 1

    def get_honors(self, year: int) -> Optional[dict]:
        """Return the full SeasonHonors dict for a given year."""
        return self.honors_history.get(year)

    def get_all_americans(self, year: int) -> Optional[dict]:
        """Return All-American teams dict for a given year."""
        h = self.honors_history.get(year)
        if not h:
            return None
        return {
            "first_team": h.get("all_american_first"),
            "second_team": h.get("all_american_second"),
        }

    def get_all_conference(self, year: int, conference_name: str) -> Optional[dict]:
        """Return All-Conference team dict for a given year and conference."""
        h = self.honors_history.get(year)
        if not h:
            return None
        return h.get("all_conference_teams", {}).get(conference_name)

    def get_individual_award(self, year: int, award_name: str) -> Optional[dict]:
        """Return a specific individual award winner dict for a given year."""
        h = self.honors_history.get(year)
        if not h:
            return None
        for a in h.get("individual_awards", []):
            if a.get("award_name") == award_name:
                return a
        return None

    def get_injury_report(self, year: int) -> Optional[dict]:
        """Return the injury report for a given year."""
        return self.injury_history.get(year)

    def get_development_events(self, year: int) -> List[dict]:
        """Return notable development events for a given offseason year."""
        return self.development_history.get(year, [])

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

    def simulate_history(
        self,
        num_years: int,
        teams_dir: str,
        games_per_team: int = 10,
        playoff_size: int = 8,
        progress_callback=None,
    ):
        """
        Simulate N years of league history before the coach's tenure begins.

        This creates a rich backstory: champions, records, team legacies, and
        an established record book that the player can browse before starting
        their own dynasty.

        The coach does NOT accumulate wins/losses during history simulation.
        History years run from (current_year - num_years) to (current_year - 1).

        Args:
            num_years:          How many seasons of history to generate (1-100)
            teams_dir:          Path to data/teams/ directory
            games_per_team:     Games per team each season (default 10)
            playoff_size:       Playoff field size (default 8)
            progress_callback:  Optional callable(year, total) for UI updates
        """
        all_teams = load_teams_from_directory(teams_dir, fresh=True)
        conf_dict = self.get_conferences_dict()

        original_year = self.current_year
        history_start = original_year - num_years

        saved_coach_wins = self.coach.career_wins
        saved_coach_losses = self.coach.career_losses
        saved_coach_years = list(self.coach.years_coached)
        saved_coach_championships = self.coach.championships
        saved_coach_playoff = self.coach.playoff_appearances
        saved_coach_records = dict(self.coach.season_records)
        saved_coach_first_year = self.coach.first_year
        saved_coach_current_year = self.coach.current_year

        for i, year in enumerate(range(history_start, original_year)):
            self.current_year = year

            seed = hash(f"history_{self.dynasty_name}_{year}") % 999999
            ai_configs = auto_assign_all_teams(teams_dir, human_teams=[], seed=seed)

            style_configs = {}
            for tname in all_teams:
                style_configs[tname] = ai_configs.get(
                    tname, {"offense_style": "balanced", "defense_style": "base_defense"}
                )

            season = create_season(
                f"{year} CVL Season",
                all_teams,
                style_configs,
                conferences=conf_dict,
                games_per_team=games_per_team,
            )
            season.simulate_season(generate_polls=True)

            effective_playoff = min(playoff_size, len(all_teams))
            if effective_playoff >= 4:
                season.simulate_playoff(num_teams=effective_playoff)

            injury_tracker = InjuryTracker()
            injury_tracker.seed(hash(f"history_{self.dynasty_name}_{year}_inj") % 999999)
            max_week = max((g.week for g in season.schedule if g.completed), default=0)
            for wk in range(1, max_week + 1):
                injury_tracker.process_week(wk, season.teams, season.standings)
                injury_tracker.resolve_week(wk)

            player_cards = {}
            for t_name, t_obj in season.teams.items():
                player_cards[t_name] = [player_to_card(p, t_name) for p in t_obj.players]

            self.advance_season(season, injury_tracker=injury_tracker, player_cards=player_cards)

            if progress_callback:
                progress_callback(i + 1, num_years)

        self.coach.career_wins = saved_coach_wins
        self.coach.career_losses = saved_coach_losses
        self.coach.years_coached = saved_coach_years
        self.coach.championships = saved_coach_championships
        self.coach.playoff_appearances = saved_coach_playoff
        self.coach.season_records = saved_coach_records
        self.coach.first_year = saved_coach_first_year
        self.coach.current_year = saved_coach_current_year

        for year in range(history_start, original_year):
            if year in self.seasons:
                del self.seasons[year]

        self.current_year = original_year

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
