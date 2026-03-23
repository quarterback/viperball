"""
WVL Commissioner Mode Engine
==============================

Run the entire WVL as league commissioner. No team ownership, no financials.
All 64 teams are AI-managed. Integrates FIV international play and tracks
player careers from college through retirement.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from engine.wvl_config import (
    ALL_CLUBS, CLUBS_BY_KEY, get_default_tier_assignments, ALL_WVL_TIERS,
)
from engine.wvl_dynasty import WVLTeamHistory
from engine.wvl_season import WVLMultiTierSeason
from engine.wvl_owner import AI_OWNER_PROFILES
from engine.player_career_tracker import PlayerCareerTracker
from engine.hall_of_fame import HallOfFame


@dataclass
class WVLCommissionerDynasty:
    """Commissioner mode: run the entire WVL world without owning a team."""

    dynasty_name: str
    current_year: int
    tier_assignments: Dict[str, int]
    team_histories: Dict[str, WVLTeamHistory] = field(default_factory=dict)
    ai_team_owners: Dict[str, str] = field(default_factory=dict)
    promotion_history: Dict[int, dict] = field(default_factory=dict)

    # Season results (not serialized - too large)
    last_season_standings: Dict[int, dict] = field(default_factory=dict)
    last_season_champions: Dict[int, str] = field(default_factory=dict)

    # FIV international
    fiv_history: List[dict] = field(default_factory=list)  # past World Cup results

    # League expansion
    custom_nations: List[dict] = field(default_factory=list)

    # Linked CVL dynasty for auto-import
    linked_cvl_dynasty: str = ""

    # Career tracking and Hall of Fame
    career_tracker: PlayerCareerTracker = field(default_factory=PlayerCareerTracker)
    hall_of_fame: HallOfFame = field(default_factory=HallOfFame)

    # Internal state (not serialized)
    _current_season: Optional[WVLMultiTierSeason] = field(default=None, repr=False)
    _team_rosters: Dict[str, list] = field(default_factory=dict, repr=False)

    # ═══════════════════════════════════════════════════════════════
    # SEASON MANAGEMENT
    # ═══════════════════════════════════════════════════════════════

    def start_season(self) -> WVLMultiTierSeason:
        """Create a new WVL season across all 4 tiers."""
        self._current_season = WVLMultiTierSeason(self.tier_assignments)

        # Inject prestige-based modifiers for all teams (no owner - all AI)
        for tier_season in self._current_season.tier_seasons.values():
            for team_key, team in tier_season.teams.items():
                club = CLUBS_BY_KEY.get(team_key)
                prestige = club.prestige if club else 50
                try:
                    team.investment_modifier = prestige * 0.03
                except Exception:
                    pass

        return self._current_season

    def sim_full_season(self, use_fast_sim: bool = True) -> Dict[int, dict]:
        """Simulate entire regular season + playoffs for all tiers."""
        if not self._current_season:
            self.start_season()
        return self._current_season.run_full_season(use_fast_sim=use_fast_sim)

    def advance_season(self, season: WVLMultiTierSeason):
        """Record completed season results into history."""
        year = self.current_year

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

            if tier_season.champion and tier_season.champion in self.team_histories:
                self.team_histories[tier_season.champion].championship_years.append(year)

        # Store champions
        self.last_season_champions = {}
        for tier_num, tier_season in season.tier_seasons.items():
            if tier_season.champion:
                self.last_season_champions[tier_num] = tier_season.champion

        # Store standings
        self.last_season_standings = season.get_all_standings()

        # Record career stats
        self._load_rosters_from_season(season)
        for tier_num, tier_season in season.tier_seasons.items():
            team_names = {k: t.name for k, t in tier_season.teams.items()}
            self.career_tracker.record_wvl_season(
                team_rosters=self._team_rosters,
                season_stats=tier_season.player_season_stats,
                tier_assignments=self.tier_assignments,
                year=year,
                team_names=team_names,
            )

    def _load_rosters_from_season(self, season: WVLMultiTierSeason):
        """Extract PlayerCard rosters from a live season."""
        from engine.player_card import player_to_card
        self._team_rosters = {}
        for tier_season in season.tier_seasons.values():
            for team_key, team in tier_season.teams.items():
                self._team_rosters[team_key] = [
                    player_to_card(p, team_key) for p in team.players
                ]

    # ═══════════════════════════════════════════════════════════════
    # OFFSEASON
    # ═══════════════════════════════════════════════════════════════

    def run_offseason(
        self,
        season: WVLMultiTierSeason,
        rng: Optional[random.Random] = None,
    ) -> dict:
        """Run the full offseason automatically.

        Returns summary dict of everything that happened.
        """
        from engine.wvl_free_agency import (
            process_retirements, generate_synthetic_fa_pool,
            run_free_agency, compute_fa_attractiveness,
        )
        from engine.development import apply_pro_development
        from engine.wvl_owner import generate_ai_investment
        from engine.wvl_config import CLUBS_BY_KEY

        if rng is None:
            rng = random.Random()

        year = self.current_year
        summary = {"year": year}

        self._load_rosters_from_season(season)

        # 1. Retirements
        retirements = process_retirements(self._team_rosters, rng)
        summary["retirements"] = retirements
        retired_names = [r["player_name"] for r in retirements]
        for name in retired_names:
            self.career_tracker.record_retirement(name, year)

        # 2. Hall of Fame evaluation
        new_inductees = self.hall_of_fame.process_retirements(
            retired_names, self.career_tracker, year,
        )
        summary["hall_of_fame_inductees"] = [e.to_dict() for e in new_inductees]

        # 3. Promotion/Relegation
        prom_rel = season.run_promotion_relegation(rng=rng)
        self.tier_assignments = prom_rel.new_tier_assignments
        self.promotion_history[year] = prom_rel.to_dict()
        summary["promotion_relegation"] = prom_rel.to_dict()

        for movement in prom_rel.movements:
            key = movement.team_key
            if key in self.team_histories:
                if movement.to_tier < movement.from_tier:
                    self.team_histories[key].promotion_years.append(year)
                else:
                    self.team_histories[key].relegation_years.append(year)

        # 4. CVL graduate import via bridge DB
        import_data = None
        try:
            from engine.db import load_graduating_pools, consume_graduating_pool
            pools = load_graduating_pools(user_id="default")
            if pools:
                bridge_players = []
                for pool in pools:
                    bridge_players.extend(pool.get("players", []))
                    consume_graduating_pool(
                        save_key=pool["save_key"], user_id="default",
                    )
                if bridge_players:
                    import_data = bridge_players
                    self.career_tracker.ingest_cvl_graduates(bridge_players, year)
                    summary["bridge_import"] = {
                        "pools_consumed": len(pools),
                        "players_imported": len(bridge_players),
                    }
        except Exception:
            pass

        # 5. Free agency
        from engine.wvl_free_agency import build_free_agent_pool_from_data
        if import_data:
            fa_pool = build_free_agent_pool_from_data(import_data)
        else:
            fa_pool = generate_synthetic_fa_pool(70, rng)

        team_attractiveness = {}
        team_budgets = {}
        for team_key in self.tier_assignments:
            tier = self.tier_assignments[team_key]
            club = CLUBS_BY_KEY.get(team_key)
            prestige = club.prestige if club else 50
            attractiveness = compute_fa_attractiveness(
                tier=tier, recent_wins=10, total_games=20,
                stadium_investment=0, brand_investment=0, prestige=prestige,
            )
            team_attractiveness[team_key] = attractiveness

            ai_profile_key = self.ai_team_owners.get(team_key, "balanced")
            ai_profile = AI_OWNER_PROFILES.get(ai_profile_key, AI_OWNER_PROFILES["balanced"])
            from engine.wvl_dynasty import _BROADCAST_REVENUE
            est_revenue = _BROADCAST_REVENUE.get(tier, 3.0) + float(tier) * 2.0
            team_budgets[team_key] = min(20.0, max(2.0, est_revenue * ai_profile["spending_ratio"] * 0.3))

        fa_result = run_free_agency(
            pool=fa_pool,
            team_rosters=self._team_rosters,
            team_attractiveness=team_attractiveness,
            team_budgets=team_budgets,
            owner_club_key="",  # no owner team
            rng=rng,
        )
        summary["free_agency"] = fa_result.to_dict()

        # 6. Player development
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

        # 7. Roster cuts
        for team_key, roster in self._team_rosters.items():
            if len(roster) > 36:
                roster.sort(key=lambda c: -c.overall)
                while len(roster) > 36:
                    roster.pop()

        # Advance year
        self.current_year += 1

        return summary

    # ═══════════════════════════════════════════════════════════════
    # FIV INTERNATIONAL
    # ═══════════════════════════════════════════════════════════════

    def run_fiv_cycle(self, host: Optional[str] = None, rng: Optional[random.Random] = None) -> dict:
        """Run a full FIV World Cup cycle using WVL players on national teams.

        Returns cycle results summary.
        """
        try:
            from engine.fiv import FIVCycle
        except ImportError:
            return {"error": "FIV module not available"}

        if rng is None:
            rng = random.Random(self.current_year)

        cycle = FIVCycle(host_nation=host)

        # Route WVL players to national teams
        self._route_wvl_players_to_fiv(cycle)

        # Run the full cycle
        cycle.sim_continental_all()
        cycle.sim_playoff()
        cycle.draw_world_cup()
        cycle.sim_world_cup_all()

        # Record results
        result = {
            "year": self.current_year,
            "champion": cycle.world_cup.champion if cycle.world_cup else None,
            "golden_boot": cycle.world_cup.golden_boot if cycle.world_cup else None,
            "mvp": cycle.world_cup.mvp if cycle.world_cup else None,
            "host": host,
        }
        self.fiv_history.append(result)

        return result

    def _route_wvl_players_to_fiv(self, cycle):
        """Assign WVL players to their national teams in the FIV cycle."""
        try:
            from engine.fiv import _resolve_fiv_code
        except ImportError:
            return

        for team_key, roster in self._team_rosters.items():
            for card in roster:
                nationality = getattr(card, 'nationality', '')
                if not nationality:
                    continue
                fiv_code = _resolve_fiv_code(nationality)
                if fiv_code and fiv_code in cycle.teams:
                    national_team = cycle.teams[fiv_code]
                    # Add player to national team if slot available and good enough
                    if len(national_team.players) < 36:
                        from engine.player_card import card_to_player
                        try:
                            player = card_to_player(card)
                            national_team.players.append(player)
                        except Exception:
                            pass

    # ═══════════════════════════════════════════════════════════════
    # COMMISSIONER TOOLS
    # ═══════════════════════════════════════════════════════════════

    def move_player(self, player_name: str, from_team: str, to_team: str) -> bool:
        """Move a player between teams. Returns True if successful."""
        from_roster = self._team_rosters.get(from_team, [])
        to_roster = self._team_rosters.get(to_team, [])

        player = None
        for i, card in enumerate(from_roster):
            if card.full_name == player_name:
                player = from_roster.pop(i)
                break

        if player is None:
            return False

        to_roster.append(player)
        self._team_rosters[to_team] = to_roster

        # Also update live season if mid-season
        if self._current_season:
            self._move_in_live_season(player_name, from_team, to_team)

        return True

    def _move_in_live_season(self, player_name: str, from_key: str, to_key: str):
        """Apply a player move to the live season's Team objects."""
        from_team = None
        to_team = None
        for ts in self._current_season.tier_seasons.values():
            if from_key in ts.teams:
                from_team = ts.teams[from_key]
            if to_key in ts.teams:
                to_team = ts.teams[to_key]

        if from_team and to_team:
            player = None
            for i, p in enumerate(from_team.players):
                if p.name == player_name:
                    player = from_team.players.pop(i)
                    break
            if player:
                to_team.players.append(player)

    def add_nation(self, code: str, name: str, confederation: str, tier: str = "developing"):
        """Add a custom nation to FIV for league expansion."""
        self.custom_nations.append({
            "code": code,
            "name": name,
            "confederation": confederation,
            "tier": tier,
            "added_year": self.current_year,
        })

    def nominate_hall_of_fame(self, player_name: str) -> Optional[dict]:
        """Manually nominate a player for Hall of Fame induction."""
        career = self.career_tracker.get_career(player_name)
        if career is None:
            return None
        entry = self.hall_of_fame.induct(career, self.current_year, "Commissioner selection")
        return entry.to_dict()

    def get_team_roster(self, team_key: str) -> List[dict]:
        """Get any team's roster as display-ready dicts."""
        roster = self._team_rosters.get(team_key, [])
        if not roster and self._current_season:
            self._load_rosters_from_season(self._current_season)
            roster = self._team_rosters.get(team_key, [])
        return [{
            "name": c.full_name,
            "position": c.position,
            "overall": c.overall,
            "age": getattr(c, 'age', None),
            "nationality": c.nationality,
            "archetype": c.archetype,
        } for c in roster]

    # ═══════════════════════════════════════════════════════════════
    # SERIALIZATION
    # ═══════════════════════════════════════════════════════════════

    def to_dict(self) -> dict:
        return {
            "dynasty_name": self.dynasty_name,
            "current_year": self.current_year,
            "tier_assignments": self.tier_assignments,
            "team_histories": {k: v.to_dict() for k, v in self.team_histories.items()},
            "ai_team_owners": self.ai_team_owners,
            "promotion_history": {str(k): v for k, v in self.promotion_history.items()},
            "last_season_champions": self.last_season_champions,
            "fiv_history": self.fiv_history,
            "custom_nations": self.custom_nations,
            "linked_cvl_dynasty": self.linked_cvl_dynasty,
            "career_tracker": self.career_tracker.to_dict(),
            "hall_of_fame": self.hall_of_fame.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WVLCommissionerDynasty":
        dynasty = cls(
            dynasty_name=d["dynasty_name"],
            current_year=d["current_year"],
            tier_assignments=d["tier_assignments"],
        )
        for k, v in d.get("team_histories", {}).items():
            dynasty.team_histories[k] = WVLTeamHistory.from_dict(v)
        dynasty.ai_team_owners = d.get("ai_team_owners", {})
        dynasty.promotion_history = {int(k): v for k, v in d.get("promotion_history", {}).items()}
        dynasty.last_season_champions = d.get("last_season_champions", {})
        dynasty.fiv_history = d.get("fiv_history", [])
        dynasty.custom_nations = d.get("custom_nations", [])
        dynasty.linked_cvl_dynasty = d.get("linked_cvl_dynasty", "")
        ct = d.get("career_tracker")
        if ct:
            dynasty.career_tracker = PlayerCareerTracker.from_dict(ct)
        hof = d.get("hall_of_fame")
        if hof:
            dynasty.hall_of_fame = HallOfFame.from_dict(hof)
        return dynasty


# ═══════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════

def create_commissioner_dynasty(
    dynasty_name: str,
    starting_year: int = 2026,
    linked_cvl_dynasty: str = "",
) -> WVLCommissionerDynasty:
    """Create a new commissioner dynasty with all 64 WVL teams."""
    tier_assignments = get_default_tier_assignments()

    team_histories = {}
    ai_owners = {}
    ai_profiles = list(AI_OWNER_PROFILES.keys())
    rng = random.Random(starting_year)

    for club in ALL_CLUBS:
        team_histories[club.key] = WVLTeamHistory(
            team_key=club.key,
            team_name=club.name,
        )
        ai_owners[club.key] = rng.choice(ai_profiles)

    return WVLCommissionerDynasty(
        dynasty_name=dynasty_name,
        current_year=starting_year,
        tier_assignments=tier_assignments,
        team_histories=team_histories,
        ai_team_owners=ai_owners,
        linked_cvl_dynasty=linked_cvl_dynasty,
    )
