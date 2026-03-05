"""
WVL Multi-Tier Season Orchestrator
====================================

Wraps ProLeagueSeason to manage 4 tiers simultaneously.
Each tier runs its own independent season using the existing pro league engine.
After all seasons complete, runs promotion/relegation.
"""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from engine.pro_league import ProLeagueConfig, ProLeagueSeason, ProTeamRecord
from engine.injuries import InjuryTracker
from engine.game_engine import load_team_from_json
from engine.wvl_config import (
    ALL_WVL_TIERS, TIER_BY_NUMBER, WVLTierConfig, CLUBS_BY_KEY,
    is_rivalry_match,
)
from engine.promotion_relegation import (
    compute_tier_movements, PromotionRelegationResult,
)


DATA_DIR = Path(__file__).parent.parent / "data"


def _tier_to_pro_config(tier: WVLTierConfig, tier_assignments: Dict[str, int]) -> ProLeagueConfig:
    """Convert a WVLTierConfig + current tier assignments into a ProLeagueConfig.

    Teams are assigned to the tier based on current tier_assignments (which may
    differ from starting positions due to promotion/relegation).
    """
    # Find all teams currently assigned to this tier
    current_teams = [
        key for key, t in tier_assignments.items()
        if t == tier.tier_number
    ]

    # Split into 2 divisions (roughly equal)
    mid = len(current_teams) // 2
    div_a = current_teams[:mid]
    div_b = current_teams[mid:]

    return ProLeagueConfig(
        league_id=f"wvl_tier{tier.tier_number}",
        league_name=tier.tier_name,
        teams_dir=tier.teams_dir,
        divisions={
            f"{tier.tier_name} A": div_a,
            f"{tier.tier_name} B": div_b,
        },
        games_per_season=tier.games_per_season,
        playoff_teams=min(8, len(current_teams) // 2),
        bye_count=0,
        calendar_start="March",
        calendar_end="November",
        attribute_range=tier.attribute_range,
        franchise_rating_range=tier.franchise_rating_range,
        name_pool="female",
    )


class WVLMultiTierSeason:
    """Manages a full WVL season across all 4 tiers."""

    def __init__(self, tier_assignments: Dict[str, int]):
        """Initialize all 4 tier seasons.

        Args:
            tier_assignments: team_key → tier_number mapping
        """
        self.tier_assignments = dict(tier_assignments)
        self.tier_seasons: Dict[int, ProLeagueSeason] = {}
        self.phase = "pre_season"
        self.current_week = 0
        self.promotion_result: Optional[PromotionRelegationResult] = None

        # Pre-scan ALL tier directories so promoted/relegated teams are found
        # regardless of which tier directory they originally lived in.
        all_wvl_teams = {}
        for tc in ALL_WVL_TIERS:
            td = DATA_DIR.parent / tc.teams_dir
            if td.exists():
                for f in sorted(td.glob("*.json")):
                    key = f.stem
                    if key not in all_wvl_teams:
                        try:
                            all_wvl_teams[key] = load_team_from_json(str(f))
                        except Exception:
                            pass

        for tier_config in ALL_WVL_TIERS:
            config = _tier_to_pro_config(tier_config, self.tier_assignments)
            try:
                # Use __new__ + manual injection (same pattern as create_champions_league)
                # so team loading searches across all tier dirs, not just this tier's dir.
                season = ProLeagueSeason.__new__(ProLeagueSeason)
                season.config = config
                season.teams = {}
                season.standings = {}
                season.schedule = []
                season.results = {}
                season.player_season_stats = {}
                season.current_week = 0
                season.total_weeks = 0
                season.phase = "regular_season"
                season.playoff_bracket = []
                season.playoff_round = 0
                season.champion = None

                for div_keys in config.divisions.values():
                    for key in div_keys:
                        if key in all_wvl_teams:
                            season.teams[key] = all_wvl_teams[key]

                if not season.teams:
                    continue

                season._init_standings()
                season._generate_schedule()
                # Attach an injury tracker for this tier
                tracker = InjuryTracker()
                tracker.seed(random.randint(1, 999_999))
                season.injury_tracker = tracker
                self.tier_seasons[tier_config.tier_number] = season
            except Exception:
                pass

        if self.tier_seasons:
            self.phase = "regular_season"

    def sim_week_all_tiers(self, use_fast_sim: bool = True) -> Dict[int, dict]:
        """Simulate one week across all tiers. Returns tier_num → week results."""
        results = {}
        for tier_num, season in self.tier_seasons.items():
            if season.phase == "regular_season" and season.current_week < season.total_weeks:
                week_result = season.sim_week(use_fast_sim=use_fast_sim)
                results[tier_num] = week_result

                # Annotate rivalry matches
                for game in week_result.get("games", []):
                    home = game.get("home_key", "")
                    away = game.get("away_key", "")
                    rivalry = is_rivalry_match(home, away)
                    if rivalry:
                        game["rivalry"] = rivalry

        # Check if all regular seasons are done
        all_done = all(
            s.current_week >= s.total_weeks or s.phase != "regular_season"
            for s in self.tier_seasons.values()
        )
        if all_done:
            self.phase = "playoffs_pending"

        return results

    def sim_all(self, use_fast_sim: bool = True) -> Dict[int, dict]:
        """Simulate entire regular season for all tiers."""
        all_results = {}
        for tier_num, season in self.tier_seasons.items():
            tier_results = []
            while season.phase == "regular_season" and season.current_week < season.total_weeks:
                tier_results.append(season.sim_week(use_fast_sim=use_fast_sim))
            all_results[tier_num] = {"weeks": tier_results}

        self.phase = "playoffs_pending"
        return all_results

    def start_playoffs_all(self):
        """Start playoffs for all tiers."""
        for season in self.tier_seasons.values():
            if season.phase != "playoffs":
                season.start_playoffs()
        self.phase = "playoffs"

    def advance_playoffs_all(self) -> Dict[int, dict]:
        """Advance one round of playoffs across all tiers."""
        results = {}
        for tier_num, season in self.tier_seasons.items():
            if season.phase == "playoffs":
                result = season.advance_playoffs()
                results[tier_num] = result
                if season.champion:
                    results[tier_num]["champion"] = season.champion

        # Check if all playoffs are done
        all_done = all(
            s.champion is not None
            for s in self.tier_seasons.values()
        )
        if all_done:
            self.phase = "season_complete"

        return results

    def run_full_season(self, use_fast_sim: bool = True) -> Dict[int, dict]:
        """Sim entire season (regular + playoffs) for all tiers."""
        self.sim_all(use_fast_sim=use_fast_sim)
        self.start_playoffs_all()

        playoff_results = {}
        while self.phase == "playoffs":
            round_results = self.advance_playoffs_all()
            for tier_num, result in round_results.items():
                playoff_results[tier_num] = result

        return playoff_results

    def get_all_stat_leaders(self) -> Dict[str, List[dict]]:
        """Aggregate all player stats across all 4 tiers.

        Returns category → full sorted list of every player with > 0 in that
        stat (no cap).  Same field names as ProLeagueSeason.get_stat_leaders()
        plus tier_num/tier so the UI can route player-card lookups correctly.
        """
        all_players: List[dict] = []
        for tier_num, season in self.tier_seasons.items():
            for team_key, players in season.player_season_stats.items():
                team_name = season.teams[team_key].name if team_key in season.teams else team_key
                for pid, p in players.items():
                    all_players.append({**p, "team_name": team_name, "tier_num": tier_num})

        rushing   = sorted(all_players, key=lambda p: -p["rushing_yards"])
        kick_pass = sorted(all_players, key=lambda p: -p["kick_pass_yards"])
        scoring   = sorted(all_players, key=lambda p: -p["touchdowns"])
        tackles   = sorted(all_players, key=lambda p: -p["tackles"])
        total     = sorted(all_players, key=lambda p: -p["total_yards"])

        def _tier(p):
            return f"T{p['tier_num']}"

        return {
            "rushing": [{
                "name": p["name"], "team": p["team_name"], "team_key": p["team_key"],
                "tier": _tier(p), "tier_num": p["tier_num"], "position": p["position"],
                "yards": p["rushing_yards"], "carries": p["rushing_carries"],
                "ypc": round(p["rushing_yards"] / max(1, p["rushing_carries"]), 1),
                "games": p["games"],
            } for p in rushing if p["rushing_yards"] > 0],

            "kick_pass": [{
                "name": p["name"], "team": p["team_name"], "team_key": p["team_key"],
                "tier": _tier(p), "tier_num": p["tier_num"], "position": p["position"],
                "yards": p["kick_pass_yards"], "completions": p["kick_pass_completions"],
                "attempts": p["kick_pass_attempts"],
                "pct": round(p["kick_pass_completions"] / max(1, p["kick_pass_attempts"]) * 100, 1),
                "games": p["games"],
            } for p in kick_pass if p["kick_pass_yards"] > 0],

            "scoring": [{
                "name": p["name"], "team": p["team_name"], "team_key": p["team_key"],
                "tier": _tier(p), "tier_num": p["tier_num"], "position": p["position"],
                "touchdowns": p["touchdowns"], "dk_made": p["dk_made"],
                "total_yards": p["total_yards"], "games": p["games"],
            } for p in scoring if p["touchdowns"] > 0],

            "tackles": [{
                "name": p["name"], "team": p["team_name"], "team_key": p["team_key"],
                "tier": _tier(p), "tier_num": p["tier_num"], "position": p["position"],
                "tackles": p["tackles"], "fumbles": p["fumbles"], "games": p["games"],
            } for p in tackles if p["tackles"] > 0],

            "total_yards": [{
                "name": p["name"], "team": p["team_name"], "team_key": p["team_key"],
                "tier": _tier(p), "tier_num": p["tier_num"], "position": p["position"],
                "total_yards": p["total_yards"], "rushing": p["rushing_yards"],
                "kick_pass": p["kick_pass_yards"], "games": p["games"],
            } for p in total if p["total_yards"] > 0],
        }

    def get_all_standings(self) -> Dict[int, dict]:
        """Get standings for all tiers with pro/rel zone annotations."""
        all_standings = {}
        for tier_num, season in self.tier_seasons.items():
            standings = season.get_standings()
            tier_config = TIER_BY_NUMBER.get(tier_num)

            # Annotate pro/rel zones
            if tier_config and "divisions" in standings:
                # Flatten all teams for zone marking
                all_teams = []
                for div_teams in standings["divisions"].values():
                    all_teams.extend(div_teams)
                all_teams.sort(key=lambda t: (-t.get("wins", 0), -(t.get("pf", 0) - t.get("pa", 0))))

                for i, team in enumerate(all_teams):
                    pos = i + 1
                    team["position"] = pos
                    team["zone"] = "safe"

                    # Promotion zone (for tiers 2-4)
                    if tier_num > 1:
                        parent_config = TIER_BY_NUMBER.get(tier_num - 1)
                        if parent_config and pos <= parent_config.promote_from_below_count:
                            team["zone"] = "promotion"
                        elif parent_config and parent_config.playoff_enabled and pos == parent_config.playoff_lower_seed_pos:
                            team["zone"] = "playoff"

                    # Relegation zone (for tiers 1-3)
                    if tier_config.relegate_count > 0:
                        total_teams = len(all_teams)
                        if pos > total_teams - tier_config.relegate_count:
                            team["zone"] = "relegation"
                        elif tier_config.playoff_enabled and pos == tier_config.playoff_higher_seed_pos:
                            team["zone"] = "playoff"

                standings["ranked"] = all_teams

            all_standings[tier_num] = standings
        return all_standings

    def get_tier_standings_for_prom_rel(self) -> Dict[int, List[dict]]:
        """Get standings in the format needed by compute_tier_movements()."""
        result = {}
        for tier_num, season in self.tier_seasons.items():
            standings = season.get_standings()
            all_teams = []
            for div_teams in standings.get("divisions", {}).values():
                all_teams.extend(div_teams)
            all_teams.sort(key=lambda t: (-t.get("wins", 0), -(t.get("pf", 0) - t.get("pa", 0))))
            result[tier_num] = all_teams
        return result

    def get_box_score(self, tier_num: int, week: int, matchup_key: str) -> Optional[dict]:
        """Get box score data for a specific game in a tier."""
        season = self.tier_seasons.get(tier_num)
        if not season:
            return None
        return season.get_box_score(week, matchup_key)

    def get_schedule(self, tier_num: int) -> dict:
        """Get the full schedule for a specific tier."""
        season = self.tier_seasons.get(tier_num)
        if not season:
            return {"weeks": []}
        return season.get_schedule()

    def run_promotion_relegation(
        self,
        rng: Optional[random.Random] = None,
    ) -> PromotionRelegationResult:
        """Run promotion/relegation after all seasons are complete."""
        if self.phase != "season_complete":
            # Force complete if needed
            if self.phase == "playoffs_pending":
                self.start_playoffs_all()
            while self.phase == "playoffs":
                self.advance_playoffs_all()

        tier_standings = self.get_tier_standings_for_prom_rel()

        # Collect all loaded teams for playoff sim
        all_teams = {}
        for season in self.tier_seasons.values():
            all_teams.update(season.teams)

        result = compute_tier_movements(
            tier_standings=tier_standings,
            tier_assignments=self.tier_assignments,
            teams=all_teams,
            rng=rng,
        )

        self.promotion_result = result
        self.tier_assignments = result.new_tier_assignments
        return result
