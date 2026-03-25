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
    ClubOwner, TeamPresident, InvestmentAllocation, ClubFinancials, ClubLoan,
    OWNER_ARCHETYPES, AI_OWNER_PROFILES, generate_president_pool, apply_investment_boosts,
    apply_infrastructure_effects,
    compute_financials, president_set_team_style,
    compute_investment_modifier, generate_ai_investment,
    assign_ai_owner_profile, starting_fanbase, compute_fanbase_update,
    compute_loan_payment, _BROADCAST_REVENUE, _TIER_STARTING_FANBASE,
)
from engine.wvl_free_agency import (
    FreeAgent, FreeAgencyResult, run_free_agency, process_retirements,
    apply_roster_cuts, generate_synthetic_fa_pool,
    build_free_agent_pool_from_import, build_free_agent_pool_from_data,
    compute_fa_attractiveness,
)
from engine.wvl_season import WVLMultiTierSeason
from engine.promotion_relegation import (
    PromotionRelegationResult, persist_tier_assignments,
)
from engine.development import apply_pro_development
from engine.player_card import PlayerCard, player_to_card
from engine.bourse import next_bourse_rate, revenue_modifier, build_rate_record, macro_shock


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
    investment_budget: float = 5.0  # Annual spend (millions) drawn from bankroll

    # Seeded FA pool — unique per dynasty, persisted across reloads
    dynasty_seed: int = 0  # set once in create_wvl_dynasty; seeds FA pool generation

    # Last completed season snapshot (plain dicts — survives serialization)
    last_season_standings: Dict[int, dict] = field(default_factory=dict)  # tier → standings
    last_season_schedule: Dict[int, list] = field(default_factory=dict)  # tier → list of week results
    last_season_champions: Dict[int, str] = field(default_factory=dict)  # tier → champion team_key
    last_season_owner_results: List[dict] = field(default_factory=list)  # [{week, opp, score, result}, ...]

    # Depth chart overrides: club_key → {position → [player_name, ...] in priority order}
    # First name in each list is the designated starter for that position.
    depth_chart: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)

    # ── Economic simulation state ────────────────────────────────
    # Fanbase: persistent metric driving ticket/sponsorship/merch revenue
    fanbase: float = 0.0

    # Infrastructure levels (0.0–10.0) per investment category
    # Grow from sustained annual spending; depreciate slightly without investment
    infrastructure: Dict[str, float] = field(default_factory=dict)

    # AI owner personality for every club (team_key → AI_OWNER_PROFILES key)
    ai_team_owners: Dict[str, str] = field(default_factory=dict)

    # Active loans: list of ClubLoan.to_dict() entries
    loans: List[dict] = field(default_factory=list)

    # Bourse exchange rate vs SDR basket (baseline 1.0).
    # Fluctuates each season via mean-reverting random walk.
    bourse_rate: float = 1.0
    # year → BourseRateRecord.to_dict()
    bourse_rate_history: Dict[int, dict] = field(default_factory=dict)

    # Season-level caches (not persisted)
    _current_season: Optional[WVLMultiTierSeason] = field(default=None, repr=False)
    _team_rosters: Dict[str, List[PlayerCard]] = field(default_factory=dict, repr=False)
    _fa_pool_dicts: List[dict] = field(default_factory=list, repr=False)  # persisted via to_dict/from_dict

    _INFRA_KEYS = ("training", "coaching", "stadium", "youth", "science", "marketing")

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
        # Ensure infrastructure always has all six keys (baseline 1.0)
        for key in self._INFRA_KEYS:
            if key not in self.infrastructure:
                self.infrastructure[key] = 1.0

    def _load_rosters_from_season(self, season: "WVLMultiTierSeason"):
        """Populate _team_rosters from the live season's Team objects."""
        self._team_rosters = {}
        for tier_season in season.tier_seasons.values():
            for team_key, team in tier_season.teams.items():
                players = getattr(team, "players", [])
                cards = []
                for player in players:
                    try:
                        card = player_to_card(player, team_key)
                        cards.append(card)
                    except Exception:
                        pass
                self._team_rosters[team_key] = cards

    def start_season(self) -> WVLMultiTierSeason:
        """Initialize a new season across all 4 tiers.

        Also injects per-team investment modifiers into Team objects so that
        investment allocation has a marginal in-season effect on dice rolls
        (via fast_sim._team_strength).
        """
        self._current_season = WVLMultiTierSeason(self.tier_assignments)
        self._inject_investment_modifiers(self._current_season)
        return self._current_season

    def inject_forced_starters(self, season: WVLMultiTierSeason):
        """Apply owner's depth-chart ordering to their team object before each sim.

        Sets team.forced_starters = {position: player_name} on the owner's team
        so assign_game_roles() in the game engine gives those players starter priority.
        """
        owner_dc = self.depth_chart.get(self.owner.club_key, {})
        if not owner_dc:
            return
        tier_num = self.tier_assignments.get(self.owner.club_key, 1)
        ts = season.tier_seasons.get(tier_num)
        if not ts:
            return
        owner_team = ts.teams.get(self.owner.club_key)
        if not owner_team:
            return
        forced = {pos: names[0] for pos, names in owner_dc.items() if names}
        try:
            owner_team.forced_starters = forced
        except Exception:
            pass

    def _inject_investment_modifiers(self, season: WVLMultiTierSeason):
        """Set investment_modifier attribute on each Team object before simming."""
        owner_modifier = compute_investment_modifier(self.investment, self.investment_budget)
        for tier_season in season.tier_seasons.values():
            for team_key, team in tier_season.teams.items():
                if team_key == self.owner.club_key:
                    modifier = owner_modifier
                else:
                    club = CLUBS_BY_KEY.get(team_key)
                    prestige = club.prestige if club else 50
                    modifier = prestige * 0.03  # ~1.5 for prestige-50, ~2.4 for prestige-80
                try:
                    team.investment_modifier = modifier
                except Exception:
                    pass

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

        # Full schedules per tier (for box score lookups)
        self.last_season_schedule = {}
        for tier_num, tier_season in season.tier_seasons.items():
            self.last_season_schedule[tier_num] = tier_season.get_schedule()

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
        import_data: Optional[list] = None,
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

        # Load player rosters from the live season before free agency/retirements
        self._load_rosters_from_season(season)

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

        # 2b. Apply owner strategy for AI teams before FA
        for team_key in self.tier_assignments:
            if team_key == self.owner.club_key:
                continue
            ai_profile_key = self.ai_team_owners.get(team_key, "balanced")

            class _OwnerProxy:
                pass
            op = _OwnerProxy()
            op.type = ai_profile_key

            class _TeamProxy:
                pass
            tp = _TeamProxy()
            bcast = _BROADCAST_REVENUE.get(self.tier_assignments.get(team_key, 4), 1.0)
            tp.revenue = bcast + float(self.tier_assignments.get(team_key, 4)) * 2.0
            owner_strategy(tp, op)

        # 3. Free Agency
        # Auto-consume CVL graduates from bridge DB if no explicit import
        if import_data is None and import_path is None:
            try:
                from engine.db import load_graduating_pools, consume_graduating_pool
                pools = load_graduating_pools(user_id="default")
                if pools:
                    # Merge all unconsumed pools into one import
                    bridge_players = []
                    for pool in pools:
                        bridge_players.extend(pool.get("players", []))
                        consume_graduating_pool(
                            save_key=pool["save_key"], user_id="default",
                        )
                    if bridge_players:
                        import_data = bridge_players
                        summary["bridge_import"] = {
                            "pools_consumed": len(pools),
                            "players_imported": len(bridge_players),
                        }
            except Exception:
                pass  # Bridge DB unavailable — fall through to synthetic

        if import_data:
            fa_pool = build_free_agent_pool_from_data(import_data)
        elif import_path:
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

            # AI team budgets: use AI owner profile spending_ratio × estimated revenue
            if team_key == self.owner.club_key:
                team_budgets[team_key] = max(3, min(15, int(prestige / 8)))
            else:
                ai_profile_key = self.ai_team_owners.get(team_key, "balanced")
                ai_profile = AI_OWNER_PROFILES.get(ai_profile_key, AI_OWNER_PROFILES["balanced"])
                est_revenue = _BROADCAST_REVENUE.get(tier, 3.0) + float(tier) * 2.0
                ai_budget = min(20.0, max(2.0, est_revenue * ai_profile["spending_ratio"] * 0.3))
                team_budgets[team_key] = ai_budget

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
        # Use self.investment_budget if caller passed the default
        effective_budget = investment_budget if investment_budget != 5.0 else self.investment_budget
        owner_roster = self._team_rosters.get(self.owner.club_key, [])
        boosts = apply_investment_boosts(
            roster=owner_roster,
            allocation=self.investment,
            investment_budget=effective_budget,
            owner_archetype=self.owner.archetype,
            rng=rng,
            infrastructure=self.infrastructure,
        )
        summary["investment_boosts"] = boosts

        # 4b. Apply AI investment boosts to all other teams
        for team_key, roster in self._team_rosters.items():
            if team_key == self.owner.club_key:
                continue
            club = CLUBS_BY_KEY.get(team_key)
            prestige = club.prestige if club else 50
            ai_alloc = generate_ai_investment(prestige, rng)
            ai_budget = float(team_budgets.get(team_key, 5.0))
            apply_investment_boosts(
                roster=roster,
                allocation=ai_alloc,
                investment_budget=ai_budget,
                owner_archetype="patient_builder",
                rng=rng,
            )

        # 4c. Accumulate infrastructure levels from this season's spending
        for key in self._INFRA_KEYS:
            fraction = getattr(self.investment, key, 0.0)
            budget_spent = effective_budget * fraction
            gain = min(0.5, budget_spent / 10.0)
            depreciation = 0.05
            current = self.infrastructure.get(key, 1.0)
            self.infrastructure[key] = max(1.0, min(10.0, current + gain - depreciation))

        # 4d. Apply infrastructure effects to owner's team attributes
        # Use a simple namespace so apply_infrastructure_effects can set attrs
        class _TeamProxy:
            pass
        team_proxy = _TeamProxy()
        apply_infrastructure_effects(team_proxy, self.infrastructure)
        summary["infrastructure_effects"] = {
            "dev_multiplier": team_proxy.dev_multiplier,
            "injury_modifier": team_proxy.injury_modifier,
            "fan_growth_multiplier": team_proxy.fan_growth_multiplier,
            "attendance_multiplier": team_proxy.attendance_multiplier,
        }

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

        # Roster cuts — collect released PlayerCard objects to add to FA pool
        cut_cards = []
        for team_key, roster in self._team_rosters.items():
            if len(roster) > 36:
                roster.sort(key=lambda c: -c.overall)
                while len(roster) > 36:
                    cut = roster.pop()
                    cut.pro_status = "free_agent"
                    cut_cards.append(cut)
        cuts = [{"player_name": c.full_name, "team_key": "auto", "overall": c.overall} for c in cut_cards]
        summary["roster_cuts"] = cuts
        # Add cut players to the persistent FA pool
        self._ensure_fa_pool()
        for card in cut_cards:
            salary = max(1, min(5, card.overall // 20))
            self._fa_pool_dicts.append({
                "card_dict": card.to_dict(),
                "asking_salary": salary,
                "source": "cut",
            })

        # 5b. Fanbase update — record before value, then compute new
        owner_pre_promo_tier = self.tier_assignments.get(self.owner.club_key, 2)
        is_promoted = any(
            m.team_key == self.owner.club_key and m.to_tier < m.from_tier
            for m in prom_rel.movements
        )
        is_relegated = any(
            m.team_key == self.owner.club_key and m.to_tier > m.from_tier
            for m in prom_rel.movements
        )

        # 6. Financials (for owner's team)
        owner_tier = self.tier_assignments.get(self.owner.club_key, 2)
        # Get owner's team record from season
        owner_wins, owner_losses = 0, 0
        playoff_result = "none"
        # Use the tier from before promotion/relegation for win records
        pre_tier = owner_pre_promo_tier
        tier_season = season.tier_seasons.get(pre_tier)
        if tier_season:
            for rec in tier_season.standings.values():
                if rec.team_key == self.owner.club_key:
                    owner_wins = rec.wins
                    owner_losses = rec.losses
                    break
            if tier_season.champion == self.owner.club_key:
                playoff_result = "champion"

        # Process loan payments before computing financials
        total_loan_payment = 0.0
        surviving_loans = []
        for loan_dict in self.loans:
            loan = ClubLoan.from_dict(loan_dict)
            self.owner.bankroll -= loan.annual_payment
            total_loan_payment += loan.annual_payment
            loan.years_remaining -= 1
            if loan.years_remaining > 0:
                surviving_loans.append(loan.to_dict())
        self.loans = surviving_loans

        # Advance Bourse exchange rate for this season (OU step + macro shock)
        old_bourse_rate = self.bourse_rate
        rate = next_bourse_rate(self.bourse_rate, rng=rng)
        rate = macro_shock(rate, rng)
        self.bourse_rate = rate
        bourse_record = build_rate_record(year, old_bourse_rate, self.bourse_rate)
        self.bourse_rate_history[year] = bourse_record.to_dict()
        summary["bourse_rate"] = bourse_record.to_dict()

        if self.president:
            financials = compute_financials(
                year=year,
                tier=pre_tier,
                wins=owner_wins,
                losses=owner_losses,
                playoff_result=playoff_result,
                roster=owner_roster,
                president=self.president,
                investment=self.investment,
                investment_budget=effective_budget,
                bankroll_start=self.owner.bankroll,
                fanbase=self.fanbase,
                loan_payments=total_loan_payment,
                infrastructure=self.infrastructure,
            )
            # Apply Bourse exchange rate modifier to revenue
            bourse_mod = revenue_modifier(self.bourse_rate)
            raw_revenue = financials.total_revenue
            adjusted_revenue = round(raw_revenue * bourse_mod, 2)
            revenue_delta = round(adjusted_revenue - raw_revenue, 2)
            # Recalculate net and bankroll with adjusted revenue
            adjusted_net = round(adjusted_revenue - financials.total_expenses, 2)
            adjusted_bankroll_end = round(financials.bankroll_start + adjusted_net, 2)
            self.owner.bankroll = adjusted_bankroll_end
            fin_dict = financials.to_dict()
            # Patch the dict to reflect exchange-rate-adjusted totals
            fin_dict["total_revenue"] = adjusted_revenue
            fin_dict["net_income"] = adjusted_net
            fin_dict["bankroll_end"] = adjusted_bankroll_end
            fin_dict["bourse_rate"] = self.bourse_rate
            fin_dict["bourse_revenue_delta"] = revenue_delta
            # Inject revenue/expense breakdowns for UI consumption
            fin_dict["revenue_breakdown"] = {
                "Ticket Sales":    financials.ticket_revenue,
                "Broadcasting":    financials.broadcast_revenue,
                "Sponsorship":     financials.sponsorship_revenue,
                "Merchandise":     financials.merchandise_revenue,
                "Prize Money":     financials.prize_money,
            }
            fin_dict["expense_breakdown"] = {
                "Roster Wages":         financials.roster_cost,
                "President":            financials.president_cost,
                "Operations":           financials.base_ops_cost,
                "Investment":           financials.investment_spend,
                "Loan Repayments":      financials.loan_payments,
                "Infra Maintenance":    financials.infra_maintenance,
            }
            self.financial_history[year] = fin_dict
            summary["financials"] = fin_dict

        # Fanbase update (after we know wins/losses and promotion/relegation)
        fanbase_before = int(self.fanbase)
        self.fanbase = compute_fanbase_update(
            fanbase=self.fanbase,
            wins=owner_wins,
            total_games=max(1, owner_wins + owner_losses),
            promoted=is_promoted,
            relegated=is_relegated,
            marketing_fraction=self.investment.marketing,
        )
        fanbase_after = int(self.fanbase)
        summary["fanbase_before"] = fanbase_before
        summary["fanbase_after"] = fanbase_after
        if "financials" in summary:
            summary["financials"]["fanbase_before"] = fanbase_before
            summary["financials"]["fanbase_after"] = fanbase_after

        # 6b. AI owner turnover — 3 % chance per AI team per season
        owner_changes = []
        for team_key in list(self.ai_team_owners.keys()):
            if team_key == self.owner.club_key:
                continue
            if rng.random() < 0.03:
                old_profile = self.ai_team_owners[team_key]
                new_profile = random_owner_profile(rng)
                self.ai_team_owners[team_key] = new_profile
                club = CLUBS_BY_KEY.get(team_key)
                club_name = club.name if club else team_key
                owner_changes.append({
                    "team": club_name,
                    "from": old_profile,
                    "to": new_profile,
                })
        if owner_changes:
            summary["owner_changes"] = owner_changes

        # 6c. Compute real AI club financials and store on summary
        ai_financials = []
        for team_key in self.tier_assignments:
            if team_key == self.owner.club_key:
                continue
            tier = self.tier_assignments.get(team_key, 4)
            club = CLUBS_BY_KEY.get(team_key)
            prestige = club.prestige if club else 50
            ai_profile_key = self.ai_team_owners.get(team_key, "balanced")
            ai_profile = AI_OWNER_PROFILES.get(ai_profile_key, AI_OWNER_PROFILES["balanced"])

            # Estimate AI team fanbase from tier and prestige
            base_fanbase = _TIER_STARTING_FANBASE.get(tier, 5_000)
            est_fanbase = int(base_fanbase * (0.5 + prestige / 100))

            # Revenue streams (simplified for AI)
            bcast = _BROADCAST_REVENUE.get(tier, 1.0)
            est_ticket = round(est_fanbase * 30 * 12 / 1_000_000, 2)
            est_sponsor = round((est_fanbase / 50_000) * {1: 3.0, 2: 2.0, 3: 1.0, 4: 0.5}.get(tier, 0.5), 2)
            est_merch = round(est_fanbase * 14 / 1_000_000, 2)
            total_revenue = round(bcast + est_ticket + est_sponsor + est_merch, 2)

            # Expenses
            est_payroll = round(total_revenue * ai_profile["spending_ratio"], 2)
            est_ops = 5.0
            total_expenses = round(est_payroll + est_ops, 2)

            net_income = round(total_revenue - total_expenses, 2)

            ai_financials.append({
                "team_key": team_key,
                "team": club.name if club else team_key,
                "tier": tier,
                "owner_type": ai_profile_key,
                "fanbase": est_fanbase,
                "revenue": total_revenue,
                "expenses": total_expenses,
                "payroll": est_payroll,
                "net_income": net_income,
                "bankroll": round(prestige * 0.5 + net_income * 2, 1),
            })
        summary["ai_financials"] = ai_financials

        # Update owner tracking
        self.owner.seasons_owned += 1
        if owner_wins < owner_losses:
            self.owner.consecutive_bad_seasons += 1
        else:
            self.owner.consecutive_bad_seasons = 0

        # Check forced sale (bankruptcy at bankroll < -15M)
        arch = OWNER_ARCHETYPES.get(self.owner.archetype, {})
        patience = arch.get("patience_threshold", 3)
        if self.owner.bankroll < -15.0 and is_relegated:
            summary["forced_sale"] = True
        elif self.owner.consecutive_bad_seasons >= patience and self.owner.bankroll < 10:
            summary["pressure_mounting"] = True

        # Advance year
        self.current_year += 1

        return summary

    # ═══════════════════════════════════════════════════════════════
    # ROSTER MANAGEMENT
    # ═══════════════════════════════════════════════════════════════

    def get_owner_roster(self) -> List[dict]:
        roster = self._team_rosters.get(self.owner.club_key, [])
        if not roster and self._current_season:
            self._load_rosters_from_season(self._current_season)
            roster = self._team_rosters.get(self.owner.club_key, [])
        result = []
        for card in roster:
            result.append({
                "name": card.full_name,
                "position": card.position,
                "age": card.age,
                "overall": card.overall,
                "speed": card.speed,
                "kicking": card.kicking,
                "lateral_skill": card.lateral_skill,
                "tackling": card.tackling,
                "stamina": card.stamina,
                "archetype": card.archetype,
                "development": card.development,
                "potential": card.potential,
                "contract_years": card.contract_years,
                "contract_salary": card.contract_salary,
                "number": card.number,
                "height": card.height,
                "weight": card.weight,
                "nationality": card.nationality,
            })
        return result

    def cut_player(self, player_name: str):
        roster = self._team_rosters.get(self.owner.club_key, [])
        if len(roster) <= 15:
            return False, "Cannot cut player: roster is at minimum size (15)."
        for i, card in enumerate(roster):
            if card.full_name == player_name:
                roster.pop(i)
                card.pro_status = "free_agent"
                salary = max(1, min(5, card.overall // 20))
                self._fa_pool_dicts.insert(0, {
                    "card_dict": card.to_dict(),
                    "asking_salary": salary,
                    "source": "cut",
                })
                return True, f"{player_name} has been released."
        return False, f"Player '{player_name}' not found on roster."

    def sign_free_agent(self, player_name: str, salary_tier: int):
        """Sign a free agent by name from the FA pool."""
        roster = self._team_rosters.get(self.owner.club_key, [])
        if len(roster) >= 40:
            return False, "Cannot sign player: roster is at maximum size (40)."
        self._ensure_fa_pool()
        entry = next(
            (e for e in self._fa_pool_dicts
             if PlayerCard.from_dict(e["card_dict"]).full_name == player_name),
            None,
        )
        if not entry:
            return False, f"{player_name} not found in free agency."
        card = PlayerCard.from_dict(entry["card_dict"])
        card.pro_team = self.owner.club_key
        card.pro_status = "active"
        card.contract_years = 3
        card.contract_salary = salary_tier
        self._team_rosters.setdefault(self.owner.club_key, []).append(card)
        self._fa_pool_dicts.remove(entry)
        return True, f"{card.full_name} signed for salary tier {salary_tier}."

    def get_owner_team_summary(self) -> dict:
        club = CLUBS_BY_KEY.get(self.owner.club_key)
        team_name = club.name if club else self.owner.club_key
        tier = self.tier_assignments.get(self.owner.club_key, 1)
        roster = self._team_rosters.get(self.owner.club_key, [])
        if not roster and self._current_season:
            self._load_rosters_from_season(self._current_season)
            roster = self._team_rosters.get(self.owner.club_key, [])

        wins, losses = 0, 0
        for r in self.last_season_owner_results:
            if r.get("result") == "W":
                wins += 1
            elif r.get("result") == "L":
                losses += 1
        record = f"{wins}-{losses}"

        overall_rating = 0
        average_age = 0
        position_counts: Dict[str, int] = {}
        if roster:
            overall_rating = round(sum(c.overall for c in roster) / len(roster), 1)
            ages = [c.age for c in roster if c.age is not None]
            average_age = round(sum(ages) / max(1, len(ages)), 1) if ages else 0
            for c in roster:
                position_counts[c.position] = position_counts.get(c.position, 0) + 1

        return {
            "team_name": team_name,
            "tier": tier,
            "record": record,
            "overall_rating": overall_rating,
            "average_age": average_age,
            "roster_size": len(roster),
            "position_counts": position_counts,
            "bankroll": self.owner.bankroll,
        }

    def take_loan(
        self,
        amount: float,
        interest_rate: float = 0.08,
        years: int = 5,
    ) -> ClubLoan:
        """Take a loan against future revenue. Adds amount to bankroll immediately."""
        annual_payment = compute_loan_payment(amount, interest_rate, years)
        loan = ClubLoan(
            amount=amount,
            interest_rate=interest_rate,
            annual_payment=annual_payment,
            years_remaining=years,
        )
        self.loans.append(loan.to_dict())
        self.owner.bankroll += amount
        return loan

    def _ensure_fa_pool(self):
        """Lazily generate the FA pool from dynasty_seed (unique per dynasty)."""
        if not self._fa_pool_dicts:
            seed = self.dynasty_seed if self.dynasty_seed else random.randint(1, 999_999)
            rng = random.Random(seed)
            fa_list = generate_synthetic_fa_pool(70, rng)
            self._fa_pool_dicts = [
                {
                    "card_dict": fa.player_card.to_dict(),
                    "asking_salary": fa.asking_salary,
                    "source": "synthetic",
                }
                for fa in fa_list
            ]

    def get_available_free_agents(self, count: int = 25) -> List[dict]:
        self._ensure_fa_pool()
        result = []
        for entry in self._fa_pool_dicts[:count]:
            try:
                card = PlayerCard.from_dict(entry["card_dict"])
                result.append({
                    "name": card.full_name,
                    "position": card.position,
                    "age": card.age,
                    "overall": card.overall,
                    "speed": card.speed,
                    "kicking": card.kicking,
                    "archetype": card.archetype,
                    "asking_salary": entry.get("asking_salary", 1),
                    "_idx": id(entry),
                })
            except Exception:
                pass
        return result

    # ═══════════════════════════════════════════════════════════════
    # SAVE / LOAD
    # ═══════════════════════════════════════════════════════════════

    def to_dict(self) -> dict:
        """Serialize dynasty to a plain dict (JSON-safe)."""
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
            "investment_budget": self.investment_budget,
            "dynasty_seed": self.dynasty_seed,
            "depth_chart": self.depth_chart,
            # Economic simulation state
            "fanbase": self.fanbase,
            "infrastructure": self.infrastructure,
            "ai_team_owners": self.ai_team_owners,
            "loans": self.loans,
            "bourse_rate": self.bourse_rate,
            "bourse_rate_history": {str(k): v for k, v in self.bourse_rate_history.items()},
        }
        if self.president:
            data["president"] = self.president.to_dict()
        if self.investment:
            data["investment"] = self.investment.to_dict()
        # Persist owner's roster so it survives page reloads (draft picks, edits)
        owner_roster = self._team_rosters.get(self.owner.club_key, [])
        if owner_roster:
            data["owner_roster"] = [c.to_dict() for c in owner_roster]
        # Persist FA pool (unique per dynasty, includes cut players)
        if self._fa_pool_dicts:
            data["fa_pool"] = list(self._fa_pool_dicts)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "WVLDynasty":
        """Reconstruct a WVLDynasty from a plain dict."""
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
        dynasty.investment_budget = float(data.get("investment_budget", 5.0))
        dynasty.dynasty_seed = int(data.get("dynasty_seed", 0))
        dynasty.depth_chart = data.get("depth_chart", {})

        # Economic simulation state
        dynasty.fanbase = float(data.get("fanbase", 0.0))
        raw_infra = data.get("infrastructure", {})
        dynasty.infrastructure = {str(k): float(v) for k, v in raw_infra.items()}
        # Fill any missing keys with baseline
        for key in dynasty._INFRA_KEYS:
            if key not in dynasty.infrastructure:
                dynasty.infrastructure[key] = 1.0
        dynasty.ai_team_owners = data.get("ai_team_owners", {})
        dynasty.loans = list(data.get("loans", []))
        dynasty.bourse_rate = float(data.get("bourse_rate", 1.0))
        dynasty.bourse_rate_history = {
            int(k): v for k, v in data.get("bourse_rate_history", {}).items()
        }

        # Restore FA pool (includes cut players; regenerated from seed if missing)
        dynasty._fa_pool_dicts = list(data.get("fa_pool", []))

        # Restore owner's persisted roster (from draft or edits)
        for card_dict in data.get("owner_roster", []):
            try:
                card = PlayerCard.from_dict(card_dict)
                dynasty._team_rosters.setdefault(owner.club_key, []).append(card)
            except Exception:
                pass

        return dynasty

    def save(self, filepath: str):
        """Save WVL dynasty to JSON."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "WVLDynasty":
        """Load WVL dynasty from JSON."""
        with open(filepath) as f:
            data = json.load(f)
        return cls.from_dict(data)


# ═══════════════════════════════════════════════════════════════
# OWNER BEHAVIOR / TURNOVER
# ═══════════════════════════════════════════════════════════════

def owner_strategy(team, owner):
    """Set team spending targets based on AI owner personality."""

    if owner.type == "aggressive":
        team.payroll_target = team.revenue * 0.80
        team.infra_focus = ["training"]

    elif owner.type == "balanced":
        team.payroll_target = team.revenue * 0.60
        team.infra_focus = ["training", "marketing"]

    elif owner.type == "frugal":
        team.payroll_target = team.revenue * 0.40
        team.infra_focus = []

    elif owner.type == "builder":
        team.payroll_target = team.revenue * 0.55
        team.infra_focus = ["youth", "scouting"]

    elif owner.type == "vanity":
        team.payroll_target = team.revenue * 0.90
        team.infra_focus = ["training"]


def random_owner_profile(rng):
    """Return a random AI owner profile key."""
    return rng.choice(["aggressive", "balanced", "frugal", "builder", "vanity"])


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

    rng = random.Random(random.randint(1, 999_999))

    dynasty = WVLDynasty(
        dynasty_name=dynasty_name,
        owner=owner,
        current_year=starting_year,
        dynasty_seed=rng.randint(1, 999_999),
    )

    # Initialize owner's fanbase from club prestige + tier
    club = CLUBS_BY_KEY.get(club_key)
    if club:
        tier = dynasty.tier_assignments.get(club_key, 4)
        dynasty.fanbase = float(starting_fanbase(tier, club.prestige))

    # Infrastructure baseline is already set to 1.0 in __post_init__

    # Assign AI owner profiles to all other clubs
    for c in ALL_CLUBS:
        if c.key != club_key:
            dynasty.ai_team_owners[c.key] = assign_ai_owner_profile(c.prestige, rng)

    return dynasty
