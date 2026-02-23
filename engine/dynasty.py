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

from engine.season import Season, TeamRecord, Game, load_teams_from_directory, create_season, is_buy_game, BUY_GAME_NIL_BONUS
from engine.awards import SeasonHonors, compute_season_awards
from engine.injuries import InjuryTracker
from engine.development import apply_team_development, apply_redshirt_decisions, get_preseason_breakout_candidates, DevelopmentReport
from engine.ai_coach import auto_assign_all_teams
from engine.player_card import PlayerCard, player_to_card
from engine.recruiting import (
    generate_recruit_class,
    RecruitingBoard,
    Recruit,
    run_full_recruiting_cycle,
    auto_recruit_team,
    simulate_recruit_decisions,
)
from engine.transfer_portal import (
    TransferPortal,
    PortalEntry,
    populate_portal,
    auto_portal_offers,
)
from engine.nil_system import (
    NILProgram,
    NILDeal,
    auto_nil_program,
    generate_nil_budget,
    compute_team_prestige,
    estimate_market_tier,
    assess_retention_risks,
    RetentionRisk,
)


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

    # Recruiting history: year -> recruiting cycle results (class rankings, signed recruits)
    recruiting_history: Dict[int, dict] = field(default_factory=dict)

    # Transfer portal history: year -> portal summary (transfers completed)
    portal_history: Dict[int, dict] = field(default_factory=dict)

    # NIL history: year -> NIL program summary per team
    nil_history: Dict[int, dict] = field(default_factory=dict)

    # Team prestige ratings (updated each offseason)
    team_prestige: Dict[str, int] = field(default_factory=dict)

    rivalries: Dict[str, Dict[str, Optional[str]]] = field(default_factory=dict)
    rivalry_ledger: Dict[str, Dict] = field(default_factory=dict)

    # Team NIL programs for current year (not serialised, rebuilt each offseason)
    _nil_programs: Dict[str, NILProgram] = field(default_factory=dict, repr=False)

    # Coaching staff per team: team_name -> { role -> CoachCard }
    _coaching_staffs: Dict[str, dict] = field(default_factory=dict, repr=False)
    coaching_history: Dict[int, dict] = field(default_factory=dict)

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
            ("Viper", True), ("Viper", False), ("Viper", False),
            ("Zeroback", False), ("Zeroback", False), ("Zeroback", False),
            ("Halfback", False), ("Halfback", False),
            ("Halfback", False), ("Halfback", False),
            ("Wingback", False), ("Wingback", False),
            ("Wingback", False), ("Wingback", False),
            ("Slotback", False), ("Slotback", False),
            ("Slotback", False), ("Slotback", False),
            ("Keeper", False), ("Keeper", False), ("Keeper", False),
            ("Offensive Line", False), ("Offensive Line", False),
            ("Offensive Line", False), ("Offensive Line", False),
            ("Offensive Line", False), ("Offensive Line", False),
            ("Offensive Line", False), ("Offensive Line", False),
            ("Defensive Line", False), ("Defensive Line", False),
            ("Defensive Line", False), ("Defensive Line", False),
            ("Defensive Line", False), ("Defensive Line", False),
            ("Defensive Line", False),
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
        dq_team_boosts: Optional[Dict[str, Dict[str, float]]] = None,
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

            # Conference champion check
            conf_champs = season.get_conference_champions() if self.conferences else {}
            is_conf_champ = team_name in set(conf_champs.values())

            # Store season record
            history.season_records[year] = {
                "wins": record.wins,
                "losses": record.losses,
                "points_for": record.points_for,
                "points_against": record.points_against,
                "avg_opi": record.avg_opi,
                "champion": (team_name == season.champion),
                "playoff": (team_name in playoff_teams),
                "conference_champion": is_conf_champ,
            }

            # Check if best season ever for this team
            if record.wins > history.best_season_wins:
                history.best_season_wins = record.wins
                history.best_season_year = year

        # ── Update coaching staff postseason stats & coaching trees ──
        if hasattr(self, '_coaching_staffs') and self._coaching_staffs:
            # Conference champions
            conf_champions = season.get_conference_champions() if self.conferences else {}
            conf_champ_teams = set(conf_champions.values())

            # Playoff bracket: determine which teams won playoff games
            # and who reached the championship game
            playoff_teams_set = set()
            try:
                playoff_records = season.get_playoff_teams(num_teams=8)
                playoff_teams_set = {r.team_name for r in playoff_records}
            except Exception:
                pass

            # Count playoff wins per team from the bracket
            playoff_wins_by_team: Dict[str, int] = {}
            championship_game_teams: set = set()
            for game in season.playoff_bracket:
                if not game.completed:
                    continue
                winner = None
                loser = None
                if game.home_score is not None and game.away_score is not None:
                    if game.home_score > game.away_score:
                        winner = game.home_team
                        loser = game.away_team
                    elif game.away_score > game.home_score:
                        winner = game.away_team
                        loser = game.home_team
                if winner:
                    playoff_wins_by_team[winner] = playoff_wins_by_team.get(winner, 0) + 1
                # Week 1000 = championship game
                if getattr(game, 'week', 0) == 1000:
                    championship_game_teams.add(game.home_team)
                    championship_game_teams.add(game.away_team)

            for team_name, staff in self._coaching_staffs.items():
                hc = staff.get("head_coach")
                if hc is None:
                    continue

                # Conference title
                if team_name in conf_champ_teams:
                    hc.conference_titles += 1
                # Playoff appearance
                if team_name in playoff_teams_set:
                    hc.playoff_appearances += 1
                # Playoff wins
                pw = playoff_wins_by_team.get(team_name, 0)
                hc.playoff_wins += pw
                # Championship game appearance
                if team_name in championship_game_teams:
                    hc.championship_appearances += 1

                # Update coaching tree for all assistant coaches
                for role, card in staff.items():
                    if role == "head_coach":
                        continue
                    # Check if this HC is already the last entry in the tree
                    tree = card.coaching_tree
                    if tree and tree[-1].get("coach_id") == hc.coach_id:
                        # Same HC — extend year_end
                        tree[-1]["year_end"] = year
                    else:
                        # New HC for this assistant
                        tree.append({
                            "coach_name": hc.full_name,
                            "coach_id": hc.coach_id,
                            "team_name": team_name,
                            "year_start": year,
                            "year_end": year,
                        })

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

        if player_cards is not None:
            self._record_awards_to_cards(honors, player_cards, year)
            self._populate_career_seasons(season, player_cards, year)

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

        # Apply redshirt decisions + player development (offseason)
        if player_cards is not None:
            dev_events = []
            redshirt_events = []
            dev_rng = rng or random.Random(year + 42)

            season_injured = {}
            if injury_tracker is not None:
                for inj in injury_tracker.season_log:
                    if inj.is_season_ending:
                        team_inj = season_injured.setdefault(inj.team_name, [])
                        team_inj.append(inj.player_name)

            human_teams = set()
            if self.coach and self.coach.team_name:
                human_teams.add(self.coach.team_name)

            for team_name, cards in player_cards.items():
                for card in cards:
                    team = season.teams.get(team_name)
                    if team:
                        player_match = next(
                            (p for p in team.players if p.name == card.full_name), None
                        )
                        if player_match:
                            card.season_games_played = getattr(player_match, 'season_games_played', 99)
                        else:
                            card.season_games_played = 99

                team_injured = season_injured.get(team_name, [])
                is_human = team_name in human_teams
                rs_names = apply_redshirt_decisions(
                    cards,
                    injured_players=team_injured,
                    is_human=is_human,
                    rng=dev_rng,
                )
                for name in rs_names:
                    redshirt_events.append({"team": team_name, "player": name})

                team_dev_boost = 0.0
                if dq_team_boosts and team_name in dq_team_boosts:
                    team_dev_boost = dq_team_boosts[team_name].get("development", 0.0)
                # Coaching: HC development attribute adds to dev_boost
                if hasattr(self, '_coaching_staffs') and team_name in self._coaching_staffs:
                    from engine.coaching import compute_dev_boost, get_sub_archetype_effects
                    team_dev_boost += compute_dev_boost(self._coaching_staffs[team_name])
                    # V2.2: Mentor sub-archetype boosts development
                    hc = self._coaching_staffs[team_name].get("head_coach")
                    if hc:
                        sub_fx = get_sub_archetype_effects(hc)
                        team_dev_boost *= sub_fx.get("development_bonus_multiplier", 1.0)
                report = apply_team_development(cards, rng=dev_rng, dev_boost=team_dev_boost)
                for ev in report.notable_events:
                    dev_events.append({
                        "team": team_name,
                        "player": ev.player_name,
                        "event_type": ev.event_type,
                        "description": ev.description,
                        "attr_changes": ev.attr_changes,
                    })

                for card in cards:
                    if hasattr(card, '_redshirt_this_season'):
                        del card._redshirt_this_season

            for team_name, cards in player_cards.items():
                team = season.teams.get(team_name)
                if team:
                    card_map = {c.full_name: c for c in cards}
                    for player in team.players:
                        card = card_map.get(player.name)
                        if card:
                            player.year = card.year
                            player.redshirt = card.redshirt
                            player.redshirt_used = card.redshirt_used
                            player.season_games_played = 0
                            card.season_games_played = 0
                            player.career_awards = list(card.career_awards)
                            existing_seasons = getattr(player, "career_seasons", [])
                            new_seasons = [s.to_dict() for s in card.career_seasons]
                            existing_years = {s.get("season_year") for s in existing_seasons}
                            for ns in new_seasons:
                                if ns.get("season_year") not in existing_years:
                                    existing_seasons.append(ns)
                            player.career_seasons = existing_seasons
                            if hasattr(card, '_was_redshirted'):
                                del card._was_redshirted

            self.development_history[year] = dev_events
            if redshirt_events:
                self.development_history[f"{year}_redshirts"] = redshirt_events

        # Roster maintenance: graduate seniors, recruit freshmen
        self._roster_maintenance(season, rng=rng or random.Random(year + 99))

        self._update_rivalry_ledger(season)

        # Update record book
        self._update_record_book(year, season)

        # Advance year
        self.current_year += 1

    def run_offseason(
        self,
        season: Season,
        player_cards: Dict[str, list],
        human_board: Optional[RecruitingBoard] = None,
        human_nil_offers: Optional[Dict[str, float]] = None,
        human_portal_picks: Optional[List[str]] = None,
        pool_size: int = 300,
        rng: Optional[random.Random] = None,
    ) -> dict:
        """
        Run the full offseason cycle: prestige → NIL → portal → recruiting.

        This method should be called AFTER advance_season() to handle the
        between-seasons roster movement.  For the human team, the caller
        can provide pre-selected board/offers/portal picks (from the UI).
        If not provided, the human team is auto-managed like CPU teams.

        Args:
            season:             The just-completed Season object.
            player_cards:       Dict of team_name -> list[PlayerCard].
            human_board:        Optional pre-built RecruitingBoard for the human team.
            human_nil_offers:   Optional dict of recruit_id -> NIL amount for human team.
            human_portal_picks: Optional list of PortalEntry player_names the human picked.
            pool_size:          National recruit class size.
            rng:                Seeded Random for reproducibility.

        Returns:
            Dict with keys: "recruiting", "portal", "nil", "retention_risks",
            "graduating", "prestige".
        """
        if rng is None:
            rng = random.Random(self.current_year + 7)

        year = self.current_year  # already advanced by advance_season
        prev_year = year - 1
        result: dict = {}

        # ── 1. Update team prestige ──
        for team_name, history in self.team_histories.items():
            recent_wins = 5
            if prev_year in history.season_records:
                recent_wins = history.season_records[prev_year].get("wins", 5)
            self.team_prestige[team_name] = compute_team_prestige(
                all_time_wins=history.total_wins,
                all_time_losses=history.total_losses,
                championships=history.total_championships,
                recent_wins=recent_wins,
            )
        result["prestige"] = dict(self.team_prestige)

        # ── 1b. Coaching staff management (V2.4 Coaching Portal) ──
        from engine.coaching import (
            CoachCard, CoachMarketplace, CoachingSalaryPool,
            auto_coaching_pool, generate_coaching_staff,
            evaluate_coaching_staff, ai_fill_vacancies,
            calculate_coach_salary,
        )
        from engine.coaching_portal import (
            CoachingPortal as CPortal,
            populate_coaching_portal,
            run_coaching_match,
        )

        # Initialise coaching staffs if not present
        all_team_names = list(self.team_histories.keys())
        if not self._coaching_staffs:
            for team_name in self.team_histories:
                prestige = self.team_prestige.get(team_name, 50)
                self._coaching_staffs[team_name] = generate_coaching_staff(
                    team_name=team_name, prestige=prestige, year=year, rng=rng,
                    all_team_names=all_team_names,
                )

        # CPU teams evaluate and potentially fire coaches
        human_team = self.coach.team_name
        coaching_changes: Dict[str, list] = {}
        fired_roles: Dict[str, List[str]] = {}

        for team_name, staff in list(self._coaching_staffs.items()):
            if team_name == human_team:
                continue  # Human decides their own coaching
            sr = self.team_histories[team_name].season_records.get(prev_year, {})
            tw = sr.get("wins", 5)
            tl = sr.get("losses", 5)
            fire_list = evaluate_coaching_staff(staff, tw, tl, rng=rng)
            if fire_list:
                coaching_changes[team_name] = fire_list
                fired_roles[team_name] = fire_list
            # Tick contract years and update career stats for ALL coaches
            for role, card in staff.items():
                if team_name in fired_roles and role in fired_roles[team_name]:
                    continue  # fired coaches don't get updated
                card.contract_years_remaining = max(0, card.contract_years_remaining - 1)
                card.seasons_coached += 1
                card.career_wins += tw
                card.career_losses += tl
                card.age += 1

        # Update human team coaches too (career stats, age)
        if human_team in self._coaching_staffs:
            sr = self.team_histories.get(human_team, TeamHistory(team_name=human_team))
            hw = sr.season_records.get(prev_year, {}).get("wins", 5)
            hl = sr.season_records.get(prev_year, {}).get("losses", 5)
            for role, card in self._coaching_staffs[human_team].items():
                card.contract_years_remaining = max(0, card.contract_years_remaining - 1)
                card.seasons_coached += 1
                card.career_wins += hw
                card.career_losses += hl
                card.age += 1

        # ── 1c. HC meter advancement + coach attribute development ──
        from engine.coaching import advance_hc_meter, apply_coach_development
        _OFFENSE_POS = {"Zeroback", "Halfback", "Wingback", "Slotback", "Viper", "Offensive Line"}
        _DEFENSE_POS = {"Defensive Line", "Keeper"}

        for team_name, staff in self._coaching_staffs.items():
            sr = self.team_histories[team_name].season_records.get(prev_year, {})
            tw = sr.get("wins", 5)
            tl = sr.get("losses", 5)
            made_playoff = sr.get("playoff", False)
            won_conf = sr.get("conference_champion", False)

            hc_card = staff.get("head_coach")

            # Compute best player overall in each area from player_cards
            best_in_area: Dict[str, int] = {"oc": 0, "dc": 0, "stc": 0}
            team_cards = player_cards.get(team_name, [])
            for pc in team_cards:
                pos = getattr(pc, "position", "")
                ovr = getattr(pc, "overall", 60)
                if pos in _OFFENSE_POS:
                    best_in_area["oc"] = max(best_in_area["oc"], ovr)
                if pos in _DEFENSE_POS:
                    best_in_area["dc"] = max(best_in_area["dc"], ovr)
                # ST: kicking-related positions (Keeper) + top kicker
                kicking = getattr(pc, "kicking", 0)
                if kicking > 0:
                    best_in_area["stc"] = max(best_in_area["stc"], ovr)

            for role, card in staff.items():
                # Advance HC meter for assistants
                if role != "head_coach":
                    area_key = role if role in best_in_area else "oc"
                    advance_hc_meter(
                        card, tw, tl,
                        hc_card=hc_card,
                        best_player_ovr_in_area=best_in_area.get(area_key, 0),
                        made_playoff=made_playoff,
                        won_conference=won_conf,
                        rng=rng,
                    )

                # All coaches develop their attributes each offseason
                apply_coach_development(card, tw, tl, rng=rng)

        # Build team records for portal population
        team_records_for_portal: Dict[str, tuple] = {}
        for team_name in self.team_histories:
            sr = self.team_histories[team_name].season_records.get(prev_year, {})
            team_records_for_portal[team_name] = (
                sr.get("wins", 5), sr.get("losses", 5)
            )

        # Run the coaching portal (NRMP-style matching)
        coaching_portal = CPortal(year=year)
        populate_coaching_portal(
            coaching_portal,
            self._coaching_staffs,
            team_records_for_portal,
            self.team_prestige,
            fired_roles=fired_roles,
            human_team=human_team,
            rng=rng,
        )

        conf_dict = self.get_conferences_dict() if self.conferences else None
        portal_changes = run_coaching_match(
            coaching_portal,
            self._coaching_staffs,
            self.team_prestige,
            team_rosters=player_cards,
            conferences=conf_dict,
            year=year,
            rng=rng,
        )

        self.coaching_history[year] = {
            "changes": coaching_changes,
            "portal_summary": coaching_portal.get_summary(),
            "portal_hires": coaching_portal.hires,
        }
        result["coaching"] = self.coaching_history[year]

        # ── 2. Build NIL programs ──
        self._nil_programs = {}
        nil_summary = {}
        for team_name in self.team_histories:
            prestige = self.team_prestige.get(team_name, 50)
            # Determine market from conference data (simplified)
            state = ""
            for conf in self.conferences.values():
                if team_name in conf.teams:
                    break
            market = estimate_market_tier(state) if state else "medium"

            prev_wins = 5
            champ = False
            if prev_year in self.awards_history:
                awards = self.awards_history[prev_year]
                if team_name == awards.champion:
                    champ = True
            sr = self.team_histories[team_name].season_records.get(prev_year, {})
            prev_wins = sr.get("wins", 5)

            program = auto_nil_program(
                team_name=team_name,
                prestige=prestige,
                market=market,
                previous_wins=prev_wins,
                championship=champ,
                rng=rng,
            )
            self._nil_programs[team_name] = program
            nil_summary[team_name] = program.get_deal_summary()

        # ── 2b. Buy-game NIL bonuses ──
        # Teams that played buy games (visited a much higher-prestige team)
        # get a flat NIL pool bonus.
        buy_game_bonuses = {}
        for game in season.schedule:
            if game.is_conference_game or not game.completed:
                continue
            home_p = self.team_prestige.get(game.home_team, 50)
            away_p = self.team_prestige.get(game.away_team, 50)
            # Away team traveled to play higher-prestige home team
            if is_buy_game(away_p, home_p):
                buy_game_bonuses[game.away_team] = buy_game_bonuses.get(game.away_team, 0) + BUY_GAME_NIL_BONUS
            # Home team played a much higher-prestige away team (less common)
            if is_buy_game(home_p, away_p):
                buy_game_bonuses[game.home_team] = buy_game_bonuses.get(game.home_team, 0) + BUY_GAME_NIL_BONUS

        for team_name, bonus in buy_game_bonuses.items():
            if team_name in self._nil_programs:
                prog = self._nil_programs[team_name]
                prog.annual_budget += bonus
                prog.recruiting_pool += bonus * 0.5
                prog.portal_pool += bonus * 0.3
                prog.retention_pool += bonus * 0.2
        result["buy_game_bonuses"] = buy_game_bonuses

        self.nil_history[prev_year] = nil_summary
        result["nil"] = nil_summary

        # ── 3. Retention risks (for human team) ──
        human_team = self.coach.team_name
        retention_risks: List[RetentionRisk] = []
        if human_team in player_cards:
            ht_prestige = self.team_prestige.get(human_team, 50)
            sr = self.team_histories.get(human_team, TeamHistory(team_name=human_team))
            hw = sr.season_records.get(prev_year, {}).get("wins", 5)
            retention_risks = assess_retention_risks(
                roster=player_cards[human_team],
                team_prestige=ht_prestige,
                team_wins=hw,
                rng=rng,
            )
        result["retention_risks"] = [r.to_dict() for r in retention_risks]

        # ── 4. Graduating players ──
        graduating: Dict[str, List[str]] = {}
        for team_name, cards in player_cards.items():
            grads = [c.full_name for c in cards if c.year == "Graduate"]
            if grads:
                graduating[team_name] = grads
        result["graduating"] = graduating

        # ── 5. Transfer portal ──
        team_records: Dict[str, tuple] = {}
        for team_name in player_cards:
            sr = self.team_histories.get(team_name, TeamHistory(team_name=team_name))
            rec = sr.season_records.get(prev_year, {"wins": 5, "losses": 5})
            team_records[team_name] = (rec.get("wins", 5), rec.get("losses", 5))

        coaching_retention = {}
        for tn, staff in self._coaching_staffs.items():
            hc = staff.get("head_coach")
            if hc and hasattr(hc, 'classification') and hc.classification == "players_coach":
                from engine.coaching import get_classification_effects, get_sub_archetype_effects
                fx = get_classification_effects(hc)
                retention = fx.get("retention_bonus", 0.0)
                # V2.2: Stabilizer sub-archetype amplifies retention
                sub_fx = get_sub_archetype_effects(hc)
                retention *= sub_fx.get("retention_bonus_multiplier", 1.0)
                retention += sub_fx.get("portal_suppression_bonus", 0.0)
                coaching_retention[tn] = retention

        portal = TransferPortal(year=year)
        populate_portal(portal, player_cards, team_records, rng=rng,
                       coaching_retention=coaching_retention)

        # CPU teams make portal offers
        team_regions = self._estimate_team_regions()
        for team_name in self.team_histories:
            if team_name == human_team:
                continue
            prestige = self.team_prestige.get(team_name, 50)
            nil_prog = self._nil_programs.get(team_name)
            portal_budget = nil_prog.portal_pool if nil_prog else 150_000
            auto_portal_offers(
                portal=portal,
                team_name=team_name,
                team_prestige=prestige,
                needs=["Viper", "Halfback", "Offensive Line"],
                nil_budget=portal_budget,
                max_targets=4,
                rng=rng,
            )

        # Human portal picks (instant commit)
        if human_portal_picks:
            for pname in human_portal_picks:
                for entry in portal.get_available():
                    if entry.player_name == pname:
                        portal.instant_commit(human_team, entry)
                        break

        # Resolve remaining portal entries
        portal_result = portal.resolve_all(
            team_prestige=self.team_prestige,
            team_regions=team_regions,
            rng=rng,
        )
        self.portal_history[prev_year] = {
            "transfers": portal.get_class_summary(),
            "total_entries": len(portal.entries),
        }
        result["portal"] = self.portal_history[prev_year]

        # ── 6. Recruiting ──
        scholarships: Dict[str, int] = {}
        nil_budgets: Dict[str, float] = {}
        for team_name in self.team_histories:
            # Rough scholarship count: roster target (36) minus current players
            # minus portal additions plus graduating players
            portal_adds = len(portal_result.get(team_name, []))
            grads = len(graduating.get(team_name, []))
            portal_losses = sum(
                1 for e in portal.entries
                if e.origin_team == team_name and e.committed_to and e.committed_to != team_name
            )
            open_spots = max(3, min(12, grads + portal_losses - portal_adds))
            scholarships[team_name] = open_spots

            nil_prog = self._nil_programs.get(team_name)
            nil_budgets[team_name] = nil_prog.recruiting_pool if nil_prog else 300_000

        # Build coaching recruiting scores from staff
        team_coaching_scores: Dict[str, float] = {}
        if self._coaching_staffs:
            from engine.coaching import compute_recruiting_bonus, get_sub_archetype_effects
            for tn, staff in self._coaching_staffs.items():
                score = compute_recruiting_bonus(staff)
                # V2.2: Recruiter sub-archetype boosts appeal
                hc = staff.get("head_coach")
                if hc:
                    sub_fx = get_sub_archetype_effects(hc)
                    score = min(1.0, score * sub_fx.get("recruiting_appeal_multiplier", 1.0))
                team_coaching_scores[tn] = score

        coaching_prestige_bonus = {}
        for tn, staff in self._coaching_staffs.items():
            hc = staff.get("head_coach")
            if hc and hasattr(hc, 'classification') and hc.classification == "players_coach":
                from engine.coaching import get_classification_effects
                fx = get_classification_effects(hc)
                bonus = int(fx.get("recruiting_appeal_prestige", 0))
                # V2.2: Recruiter sub-archetype prestige bonus
                sub_fx = get_sub_archetype_effects(hc)
                bonus += int(sub_fx.get("prestige_bonus", 0))
                if bonus > 0:
                    coaching_prestige_bonus[tn] = bonus

        recruit_result = run_full_recruiting_cycle(
            year=year,
            team_names=list(self.team_histories.keys()),
            human_team=human_team,
            human_board=human_board,
            human_nil_offers=human_nil_offers,
            team_prestige=self.team_prestige,
            team_regions=team_regions,
            scholarships_per_team=scholarships,
            nil_budgets=nil_budgets,
            pool_size=pool_size,
            rng=rng,
            team_coaching_scores=team_coaching_scores,
            coaching_prestige_bonus=coaching_prestige_bonus,
        )

        self.recruiting_history[year] = {
            "class_rankings": recruit_result["class_rankings"],
            "signed_count": {t: len(r) for t, r in recruit_result["signed"].items()},
            "pool_size": pool_size,
        }
        result["recruiting"] = self.recruiting_history[year]

        return result

    def _estimate_team_regions(self) -> Dict[str, str]:
        """Estimate each team's geographic region from conference data."""
        # Simplified: map conference name to a region
        conf_region_map = {
            "Yankee Conference": "northeast",
            "Metro Atlantic": "mid_atlantic",
            "Great Lakes Union": "midwest",
            "Colonial Athletic": "south",
            "Gateway League": "midwest",
            "Sun Country": "texas_southwest",
            "Skyline Conference": "west_coast",
            "Pacific Rim": "west_coast",
        }
        result = {}
        for conf_name, conf in self.conferences.items():
            region = conf_region_map.get(conf_name, "midwest")
            for team in conf.teams:
                result[team] = region
        return result

    def get_recruiting_history(self, year: int) -> Optional[dict]:
        """Return recruiting class results for a given year."""
        return self.recruiting_history.get(year)

    def get_portal_history(self, year: int) -> Optional[dict]:
        """Return transfer portal results for a given year."""
        return self.portal_history.get(year)

    def get_nil_history(self, year: int) -> Optional[dict]:
        """Return NIL program summaries for a given year."""
        return self.nil_history.get(year)

    def get_team_prestige(self, team_name: str) -> int:
        """Return current prestige rating for a team."""
        return self.team_prestige.get(team_name, 50)

    def _record_awards_to_cards(
        self,
        honors: "SeasonHonors",
        player_cards: Dict[str, list],
        year: int,
    ) -> None:
        card_lookup: Dict[str, "PlayerCard"] = {}
        for team_name, cards in player_cards.items():
            for card in cards:
                key = f"{card.full_name}|{team_name}"
                card_lookup[key] = card

        for winner, level in honors.all_winners():
            key = f"{winner.player_name}|{winner.team_name}"
            card = card_lookup.get(key)
            if card is not None:
                card.career_awards.append({
                    "year": year,
                    "award": winner.award_name,
                    "level": level,
                    "team": winner.team_name,
                    "position": winner.position,
                })

    def _populate_career_seasons(
        self,
        season,
        player_cards: Dict[str, list],
        year: int,
    ) -> None:
        """Build season stats from completed games and log to PlayerCards."""
        from engine.player_card import SeasonStats

        card_lookup: Dict[str, "PlayerCard"] = {}
        for team_name, cards in player_cards.items():
            for card in cards:
                key = f"{card.full_name}|{team_name}"
                card_lookup[key] = card

        player_agg: Dict[str, Dict] = {}

        for game in season.schedule:
            if not game.completed or not getattr(game, "full_result", None):
                continue
            fr = game.full_result
            ps = fr.get("player_stats", {})
            for side, team_name in [("home", game.home_team), ("away", game.away_team)]:
                for p in ps.get(side, []):
                    agg_key = f"{p['name']}|{team_name}"
                    if agg_key not in player_agg:
                        player_agg[agg_key] = {
                            "team": team_name,
                            "games_played": 0,
                            "touches": 0,
                            "rushing_yards": 0,
                            "lateral_yards": 0,
                            "total_yards": 0,
                            "touchdowns": 0,
                            "fumbles": 0,
                            "laterals_thrown": 0,
                            "kick_attempts": 0,
                            "kick_makes": 0,
                            "pk_attempts": 0,
                            "pk_makes": 0,
                            "dk_attempts": 0,
                            "dk_makes": 0,
                            "tackles": 0,
                            "tfl": 0,
                            "sacks": 0,
                            "hurries": 0,
                            "return_yards": 0,
                            "st_tackles": 0,
                        }
                    a = player_agg[agg_key]
                    a["games_played"] += 1
                    a["touches"] += p.get("touches", 0)
                    a["rushing_yards"] += p.get("rushing_yards", 0)
                    a["lateral_yards"] += p.get("lateral_yards", 0)
                    a["total_yards"] += p.get("yards", 0)
                    a["touchdowns"] += p.get("tds", 0)
                    a["fumbles"] += p.get("fumbles", 0)
                    a["laterals_thrown"] += p.get("laterals_thrown", 0)
                    a["kick_attempts"] += p.get("kick_att", 0)
                    a["kick_makes"] += p.get("kick_made", 0)
                    a["pk_attempts"] += p.get("pk_att", 0)
                    a["pk_makes"] += p.get("pk_made", 0)
                    a["dk_attempts"] += p.get("dk_att", 0)
                    a["dk_makes"] += p.get("dk_made", 0)
                    a["tackles"] += p.get("tackles", 0)
                    a["tfl"] += p.get("tfl", 0)
                    a["sacks"] += p.get("sacks", 0)
                    a["hurries"] += p.get("hurries", 0)
                    a["return_yards"] += p.get("kick_return_yards", 0) + p.get("punt_return_yards", 0)
                    a["st_tackles"] += p.get("st_tackles", 0)

        for agg_key, stats in player_agg.items():
            card = card_lookup.get(agg_key)
            if card is not None and stats["games_played"] > 0:
                ss = SeasonStats(
                    season_year=year,
                    team=stats["team"],
                    games_played=stats["games_played"],
                    touches=stats["touches"],
                    rushing_yards=stats["rushing_yards"],
                    lateral_yards=stats["lateral_yards"],
                    total_yards=stats["total_yards"],
                    touchdowns=stats["touchdowns"],
                    fumbles=stats["fumbles"],
                    laterals_thrown=stats["laterals_thrown"],
                    kick_attempts=stats["kick_attempts"],
                    kick_makes=stats["kick_makes"],
                    pk_attempts=stats["pk_attempts"],
                    pk_makes=stats["pk_makes"],
                    dk_attempts=stats["dk_attempts"],
                    dk_makes=stats["dk_makes"],
                    tackles=stats["tackles"],
                    tfl=stats["tfl"],
                    sacks=stats["sacks"],
                    hurries=stats["hurries"],
                    return_yards=stats["return_yards"],
                    st_tackles=stats["st_tackles"],
                )
                card.career_seasons.append(ss)

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

    def _update_rivalry_ledger(self, season: Season):
        """Update head-to-head rivalry records from completed season games."""
        rivalry_pairs = set()
        for team, rivals in self.rivalries.items():
            conf_rival = rivals.get("conference")
            nc_rival = rivals.get("non_conference")
            if conf_rival:
                rivalry_pairs.add(tuple(sorted([team, conf_rival])))
            if nc_rival:
                rivalry_pairs.add(tuple(sorted([team, nc_rival])))

        for game in season.schedule:
            if not game.completed:
                continue
            pair = tuple(sorted([game.home_team, game.away_team]))
            if pair not in rivalry_pairs:
                continue

            ledger_key = f"{pair[0]}|{pair[1]}"
            if ledger_key not in self.rivalry_ledger:
                self.rivalry_ledger[ledger_key] = {
                    "team_a": pair[0],
                    "team_b": pair[1],
                    "wins": {pair[0]: 0, pair[1]: 0},
                    "seasons_played": [],
                    "current_streak": {"team": None, "count": 0},
                    "last_result": None,
                }

            entry = self.rivalry_ledger[ledger_key]
            year = self.current_year
            if year not in entry["seasons_played"]:
                entry["seasons_played"].append(year)

            if game.home_score is not None and game.away_score is not None:
                if game.home_score > game.away_score:
                    winner = game.home_team
                elif game.away_score > game.home_score:
                    winner = game.away_team
                else:
                    winner = None

                if winner:
                    entry["wins"][winner] = entry["wins"].get(winner, 0) + 1
                    if entry["current_streak"]["team"] == winner:
                        entry["current_streak"]["count"] += 1
                    else:
                        entry["current_streak"] = {"team": winner, "count": 1}

                entry["last_result"] = {
                    "winner": winner,
                    "home": game.home_team,
                    "away": game.away_team,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                    "year": year,
                }

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
                    tname, {"offense_style": "balanced", "defense_style": "swarm"}
                )

            season = create_season(
                f"{year} CVL Season",
                all_teams,
                style_configs,
                conferences=conf_dict,
                games_per_team=games_per_team,
                dynasty_year=year,
            )
            injury_tracker = InjuryTracker()
            injury_tracker.seed(hash(f"history_{self.dynasty_name}_{year}_inj") % 999999)
            season.injury_tracker = injury_tracker

            season.simulate_season(generate_polls=True)

            effective_playoff = min(playoff_size, len(all_teams))
            if effective_playoff >= 4:
                season.simulate_playoff(num_teams=effective_playoff)

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
        from engine.coaching import CoachCard
        data = {
            "dynasty_name": self.dynasty_name,
            "coach": asdict(self.coach),
            "current_year": self.current_year,
            "conferences": {name: asdict(conf) for name, conf in self.conferences.items()},
            "team_histories": {name: asdict(history) for name, history in self.team_histories.items()},
            "awards_history": {year: asdict(awards) for year, awards in self.awards_history.items()},
            "record_book": asdict(self.record_book),
            "coaching_staffs": {
                team_name: {
                    role: (card.to_dict() if isinstance(card, CoachCard) else card)
                    for role, card in staff.items()
                }
                for team_name, staff in self._coaching_staffs.items()
            } if self._coaching_staffs else {},
            "coaching_history": {str(k): v for k, v in self.coaching_history.items()},
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

        # Reconstruct coaching staffs
        if "coaching_staffs" in data and data["coaching_staffs"]:
            from engine.coaching import CoachCard
            for team_name, staff_data in data["coaching_staffs"].items():
                dynasty._coaching_staffs[team_name] = {
                    role: CoachCard.from_dict(card_data)
                    for role, card_data in staff_data.items()
                }

        # Reconstruct coaching history
        if "coaching_history" in data:
            dynasty.coaching_history = {int(k): v for k, v in data["coaching_history"].items()}

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
