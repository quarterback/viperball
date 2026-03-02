"""
WVL Dynasty — Owner Mode Multi-Season Tracking
================================================

Completely separate from the college Dynasty class. Tracks the owner's
multi-season journey through the WVL pyramid.

Key differences from college dynasty:
- Owner mode (not coach mode)
- 4-tier pyramid with promotion/relegation
- Free agency instead of recruiting
- Age-based player development instead of year-based
- Financial tracking and bankroll management
"""

import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

from engine.wvl_config import (
    ALL_CLUBS, CLUBS_BY_KEY, get_default_tier_assignments,
)
from engine.wvl_owner import (
    ClubOwner, TeamPresident, InvestmentAllocation, ClubFinancials,
    OWNER_ARCHETYPES, generate_president_pool, apply_investment_boosts,
    compute_financials, president_set_team_style,
)
from engine.wvl_free_agency import (
    FreeAgent, FreeAgencyResult, run_free_agency, process_retirements,
    apply_roster_cuts, generate_synthetic_fa_pool, build_free_agent_pool_from_import,
    compute_fa_attractiveness,
)
from engine.wvl_season import WVLMultiTierSeason
from engine.promotion_relegation import (
    PromotionRelegationResult, persist_tier_assignments,
)
from engine.development import apply_pro_development
from engine.player_card import PlayerCard


DATA_DIR = Path(__file__).parent.parent / "data"


# ═══════════════════════════════════════════════════════════════
# TEAM HISTORY
# ═══════════════════════════════════════════════════════════════

@dataclass
class WVLTeamHistory:
    """Historical record for a single WVL club."""
    team_key: str
    team_name: str
    total_wins: int = 0
    total_losses: int = 0
    tier_history: List[int] = field(default_factory=list)  # tier per season
    championship_years: List[int] = field(default_factory=list)
    promotion_years: List[int] = field(default_factory=list)
    relegation_years: List[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WVLTeamHistory":
        return cls(**d)


# ═══════════════════════════════════════════════════════════════
# WVL DYNASTY
# ═══════════════════════════════════════════════════════════════

@dataclass
class WVLDynasty:
    """Complete WVL owner mode with multi-season tracking."""
    dynasty_name: str
    owner: ClubOwner
    current_year: int

    # Tier assignments (team_key → tier_number) — updated each offseason
    tier_assignments: Dict[str, int] = field(default_factory=dict)

    # Historical data
    team_histories: Dict[str, WVLTeamHistory] = field(default_factory=dict)
    financial_history: Dict[int, dict] = field(default_factory=dict)  # year → ClubFinancials dict
    promotion_history: Dict[int, dict] = field(default_factory=dict)  # year → PromotionRelegationResult dict
    president_history: List[Dict] = field(default_factory=list)

    # Current state
    president: Optional[TeamPresident] = None
    investment: InvestmentAllocation = field(default_factory=InvestmentAllocation)

    # Last completed season snapshot (plain dicts — survives serialization)
    last_season_standings: Dict[int, dict] = field(default_factory=dict)  # tier → standings
    last_season_schedule: Dict[int, list] = field(default_factory=dict)  # tier → list of week results
    last_season_champions: Dict[int, str] = field(default_factory=dict)  # tier → champion team_key
    last_season_owner_results: List[dict] = field(default_factory=list)  # [{week, opp, score, result}, ...]

    # Season-level caches (not persisted)
    _current_season: Optional[WVLMultiTierSeason] = field(default=None, repr=False)
    _team_rosters: Dict[str, List[PlayerCard]] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if not self.tier_assignments:
            self.tier_assignments = get_default_tier_assignments()
        # Initialize team histories
        for club in ALL_CLUBS:
            if club.key not in self.team_histories:
                self.team_histories[club.key] = WVLTeamHistory(
                    team_key=club.key,
                    team_name=club.name,
                )

    def start_season(self) -> WVLMultiTierSeason:
        """Initialize a new season across all 4 tiers."""
        self._current_season = WVLMultiTierSeason(self.tier_assignments)
        return self._current_season

    def snapshot_season(self, season: WVLMultiTierSeason):
        """Extract serializable season data into dynasty fields.

        Must be called BEFORE advance_season() so tier assignments still match.
        Stores standings, schedules, champions, and owner's game results
        as plain dicts that survive NiceGUI storage serialization.
        """
        # Standings with zone annotations
        self.last_season_standings = season.get_all_standings()
        # Strip non-serializable data — keep only plain dict values
        for tier_num, st in self.last_season_standings.items():
            ranked = st.get("ranked", [])
            # Ensure all values are JSON-safe primitives
            for team in ranked:
                for k, v in list(team.items()):
                    if not isinstance(v, (str, int, float, bool, type(None))):
                        team[k] = str(v)

        # Champions per tier
        self.last_season_champions = {}
        for tier_num, tier_season in season.tier_seasons.items():
            if tier_season.champion:
                self.last_season_champions[tier_num] = tier_season.champion

        # Owner's game-by-game results
        owner_tier = self.tier_assignments.get(self.owner.club_key, 1)
        tier_season = season.tier_seasons.get(owner_tier)
        self.last_season_owner_results = []
        if tier_season:
            schedule = tier_season.get_schedule()
            for week_data in schedule.get("weeks", []):
                week_num = week_data.get("week", 0)
                for game in week_data.get("games", []):
                    if not game.get("completed"):
                        continue
                    is_home = game.get("home_key") == self.owner.club_key
                    is_away = game.get("away_key") == self.owner.club_key
                    if not (is_home or is_away):
                        continue
                    hs = game.get("home_score", 0)
                    aws = game.get("away_score", 0)
                    if is_home:
                        opp_key = game.get("away_key", "")
                        opp_name = game.get("away_name", opp_key)
                        my_score, opp_score = hs, aws
                        loc = "H"
                    else:
                        opp_key = game.get("home_key", "")
                        opp_name = game.get("home_name", opp_key)
                        my_score, opp_score = aws, hs
                        loc = "A"
                    result = "W" if my_score > opp_score else "L" if my_score < opp_score else "D"
                    self.last_season_owner_results.append({
                        "week": week_num,
                        "opponent": opp_name,
                        "opponent_key": opp_key,
                        "location": loc,
                        "my_score": my_score,
                        "opp_score": opp_score,
                        "result": result,
                        "matchup_key": game.get("matchup_key", ""),
                    })

    def advance_season(
        self,
        season: WVLMultiTierSeason,
        rng: Optional[random.Random] = None,
    ):
        """Record a completed season's results into dynasty history."""
        if rng is None:
            rng = random.Random()

        year = self.current_year

        # Update team histories from standings
        for tier_num, tier_season in season.tier_seasons.items():
            standings = tier_season.get_standings()
            for div_teams in standings.get("divisions", {}).values():
                for team_data in div_teams:
                    key = team_data.get("team_key", "")
                    if key in self.team_histories:
                        hist = self.team_histories[key]
                        hist.total_wins += team_data.get("wins", 0)
                        hist.total_losses += team_data.get("losses", 0)
                        hist.tier_history.append(tier_num)

            # Record champions
            if tier_season.champion and tier_season.champion in self.team_histories:
                self.team_histories[tier_season.champion].championship_years.append(year)

    def run_offseason(
        self,
        season: WVLMultiTierSeason,
        investment_budget: float = 5.0,
        owner_targeted_fa_name: Optional[str] = None,
        import_path: Optional[str] = None,
        rng: Optional[random.Random] = None,
    ) -> Dict:
        """Run full offseason:
        1. Process retirements
        2. Run promotion/relegation
        3. Free agency (owner targeted FA + AI autonomous)
        4. Apply investment boosts
        5. Apply pro development (age-based)
        6. Compute financials

        Returns a summary dict of everything that happened.
        """
        if rng is None:
            rng = random.Random()

        year = self.current_year
        summary = {"year": year}

        # 1. Process retirements
        retirements = process_retirements(self._team_rosters, rng)
        summary["retirements"] = retirements

        # 2. Promotion/Relegation
        prom_rel = season.run_promotion_relegation(rng=rng)
        self.tier_assignments = prom_rel.new_tier_assignments
        self.promotion_history[year] = prom_rel.to_dict()
        summary["promotion_relegation"] = prom_rel.to_dict()

        # Record pro/rel in team histories
        for movement in prom_rel.movements:
            key = movement.team_key
            if key in self.team_histories:
                if movement.to_tier < movement.from_tier:
                    self.team_histories[key].promotion_years.append(year)
                else:
                    self.team_histories[key].relegation_years.append(year)

        # Persist tier assignments
        assignments_path = DATA_DIR / "wvl_tier_assignments.json"
        persist_tier_assignments(self.tier_assignments, str(assignments_path))

        # 3. Free Agency
        if import_path:
            fa_pool = build_free_agent_pool_from_import(import_path)
        else:
            fa_pool = generate_synthetic_fa_pool(70, rng)

        # Compute attractiveness for all teams
        team_attractiveness = {}
        team_budgets = {}
        for team_key in self.tier_assignments:
            tier = self.tier_assignments[team_key]
            hist = self.team_histories.get(team_key)
            recent_wins = 0
            total_games = 0
            if hist and hist.tier_history:
                recent_wins = hist.total_wins
                total_games = hist.total_wins + hist.total_losses

            club = CLUBS_BY_KEY.get(team_key)
            prestige = club.prestige if club else 50

            attractiveness = compute_fa_attractiveness(
                tier=tier,
                recent_wins=min(recent_wins, 20),
                total_games=max(1, min(total_games, 40)),
                stadium_investment=self.investment.stadium if team_key == self.owner.club_key else 0,
                brand_investment=self.investment.marketing if team_key == self.owner.club_key else 0,
                prestige=prestige,
            )
            team_attractiveness[team_key] = attractiveness
            team_budgets[team_key] = max(3, min(15, int(prestige / 8)))

        fa_result = run_free_agency(
            pool=fa_pool,
            team_rosters=self._team_rosters,
            team_attractiveness=team_attractiveness,
            team_budgets=team_budgets,
            owner_club_key=self.owner.club_key,
            owner_targeted_fa_name=owner_targeted_fa_name,
            rng=rng,
        )
        summary["free_agency"] = fa_result.to_dict()

        # 4. Apply investment boosts to owner's team
        owner_roster = self._team_rosters.get(self.owner.club_key, [])
        boosts = apply_investment_boosts(
            roster=owner_roster,
            allocation=self.investment,
            investment_budget=investment_budget,
            owner_archetype=self.owner.archetype,
            rng=rng,
        )
        summary["investment_boosts"] = boosts

        # 5. Pro development (age-based) for all teams
        dev_events = []
        for team_key, roster in self._team_rosters.items():
            for card in roster:
                event = apply_pro_development(card, rng)
                if event:
                    dev_events.append({
                        "team": team_key,
                        "player": event.player_name,
                        "type": event.event_type,
                        "description": event.description,
                    })
        summary["development"] = dev_events

        # Roster cuts
        cuts = apply_roster_cuts(self._team_rosters, limit=36)
        summary["roster_cuts"] = cuts

        # 6. Financials (for owner's team)
        owner_tier = self.tier_assignments.get(self.owner.club_key, 2)
        # Get owner's team record from season
        owner_wins, owner_losses = 0, 0
        playoff_result = "none"
        tier_season = season.tier_seasons.get(owner_tier)
        if tier_season:
            for rec in tier_season.standings.values():
                if rec.team_key == self.owner.club_key:
                    owner_wins = rec.wins
                    owner_losses = rec.losses
                    break
            if tier_season.champion == self.owner.club_key:
                playoff_result = "champion"

        if self.president:
            financials = compute_financials(
                year=year,
                tier=owner_tier,
                wins=owner_wins,
                losses=owner_losses,
                playoff_result=playoff_result,
                roster=owner_roster,
                president=self.president,
                investment=self.investment,
                investment_budget=investment_budget,
                bankroll_start=self.owner.bankroll,
            )
            self.owner.bankroll = financials.bankroll_end
            self.financial_history[year] = financials.to_dict()
            summary["financials"] = financials.to_dict()

        # Update owner tracking
        self.owner.seasons_owned += 1
        if owner_wins < owner_losses:
            self.owner.consecutive_bad_seasons += 1
        else:
            self.owner.consecutive_bad_seasons = 0

        # Check forced sale
        arch = OWNER_ARCHETYPES.get(self.owner.archetype, {})
        patience = arch.get("patience_threshold", 3)
        is_relegated = any(
            m.team_key == self.owner.club_key and m.to_tier > m.from_tier
            for m in prom_rel.movements
        )
        if self.owner.bankroll <= 0 and is_relegated:
            summary["forced_sale"] = True
        elif self.owner.consecutive_bad_seasons >= patience and self.owner.bankroll < 10:
            summary["pressure_mounting"] = True

        # Advance year
        self.current_year += 1

        return summary

    # ═══════════════════════════════════════════════════════════════
    # SAVE / LOAD
    # ═══════════════════════════════════════════════════════════════

    def save(self, filepath: str):
        """Save WVL dynasty to JSON."""
        data = {
            "type": "wvl_dynasty",
            "dynasty_name": self.dynasty_name,
            "current_year": self.current_year,
            "owner": self.owner.to_dict(),
            "tier_assignments": self.tier_assignments,
            "team_histories": {k: v.to_dict() for k, v in self.team_histories.items()},
            "financial_history": self.financial_history,
            "promotion_history": self.promotion_history,
            "president_history": self.president_history,
            "last_season_standings": {str(k): v for k, v in self.last_season_standings.items()},
            "last_season_schedule": {str(k): v for k, v in self.last_season_schedule.items()},
            "last_season_champions": {str(k): v for k, v in self.last_season_champions.items()},
            "last_season_owner_results": self.last_season_owner_results,
        }
        if self.president:
            data["president"] = self.president.to_dict()
        if self.investment:
            data["investment"] = self.investment.to_dict()

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "WVLDynasty":
        """Load WVL dynasty from JSON."""
        with open(filepath) as f:
            data = json.load(f)

        owner = ClubOwner.from_dict(data["owner"])

        dynasty = cls(
            dynasty_name=data["dynasty_name"],
            owner=owner,
            current_year=data["current_year"],
            tier_assignments=data.get("tier_assignments", {}),
        )

        # Restore team histories
        for key, hist_data in data.get("team_histories", {}).items():
            dynasty.team_histories[key] = WVLTeamHistory.from_dict(hist_data)

        dynasty.financial_history = {
            int(k): v for k, v in data.get("financial_history", {}).items()
        }
        dynasty.promotion_history = {
            int(k): v for k, v in data.get("promotion_history", {}).items()
        }
        dynasty.president_history = data.get("president_history", [])

        # Restore last season snapshot
        dynasty.last_season_standings = {
            int(k): v for k, v in data.get("last_season_standings", {}).items()
        }
        dynasty.last_season_schedule = {
            int(k): v for k, v in data.get("last_season_schedule", {}).items()
        }
        dynasty.last_season_champions = {
            int(k): v for k, v in data.get("last_season_champions", {}).items()
        }
        dynasty.last_season_owner_results = data.get("last_season_owner_results", [])

        if "president" in data:
            dynasty.president = TeamPresident.from_dict(data["president"])
        if "investment" in data:
            dynasty.investment = InvestmentAllocation.from_dict(data["investment"])

        return dynasty


# ═══════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════

def create_wvl_dynasty(
    dynasty_name: str,
    owner_name: str,
    owner_archetype: str,
    club_key: str,
    starting_year: int = 2026,
) -> WVLDynasty:
    """Create a new WVL dynasty.

    Args:
        dynasty_name: Name of this save
        owner_name: Human player's owner name
        owner_archetype: Key from OWNER_ARCHETYPES
        club_key: Which club to own (e.g., "vimpeli", "wrexham", "real_madrid")
        starting_year: First season year
    """
    arch = OWNER_ARCHETYPES.get(owner_archetype, OWNER_ARCHETYPES["patient_builder"])

    owner = ClubOwner(
        name=owner_name,
        archetype=owner_archetype,
        club_key=club_key,
        bankroll=float(arch["starting_bankroll"]),
    )

    dynasty = WVLDynasty(
        dynasty_name=dynasty_name,
        owner=owner,
        current_year=starting_year,
    )

    return dynasty
