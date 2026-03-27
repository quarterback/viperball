"""
Player Career Tracker
======================

Tracks every player from college recruit through pro career, international play,
and retirement. Provides unified career views across CVL, WVL, and FIV.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PlayerCareerRecord:
    """Full career record for a single player across all competitions."""

    player_id: str
    full_name: str
    position: str
    nationality: str
    hometown: str = ""

    # College phase (populated from CVL bridge data)
    college_team: str = ""
    college_conference: str = ""
    college_prestige: int = 0
    college_seasons: List[dict] = field(default_factory=list)
    # [{year, team, games, yards, tds, awards...}]

    # Pro phase (populated from WVL season stats)
    pro_entry_year: Optional[int] = None
    pro_seasons: List[dict] = field(default_factory=list)
    # [{year, team_key, team_name, tier, games, yards, tds, awards...}]

    # International phase (populated from FIV cycle data)
    national_team: str = ""  # FIV nation code
    international_caps: int = 0
    international_seasons: List[dict] = field(default_factory=list)
    # [{year, competition, games, yards, tds...}]
    world_cup_appearances: int = 0

    # Status
    career_status: str = "active"  # "college" | "active" | "retired" | "hall_of_fame"
    retirement_year: Optional[int] = None

    # Snapshot of ratings at peak/retirement for display
    peak_overall: int = 0
    peak_ratings: Dict[str, int] = field(default_factory=dict)

    # Awards
    career_awards: List[str] = field(default_factory=list)

    @property
    def pro_teams_summary(self) -> List[str]:
        """e.g., ['Real Madrid (2026-2028)', 'Arsenal (2029-present)']"""
        if not self.pro_seasons:
            return []
        teams = []
        current_team = None
        start_year = None
        end_year = None
        for s in self.pro_seasons:
            t = s.get("team_name", "Unknown")
            y = s.get("year", 0)
            if t != current_team:
                if current_team:
                    teams.append((current_team, start_year, end_year))
                current_team = t
                start_year = y
            end_year = y
        if current_team:
            teams.append((current_team, start_year, end_year))
        result = []
        for t, sy, ey in teams:
            if self.career_status == "active" and t == teams[-1][0]:
                result.append(f"{t} ({sy}-present)")
            else:
                result.append(f"{t} ({sy}-{ey})")
        return result

    @property
    def career_pro_games(self) -> int:
        return sum(s.get("games", 0) for s in self.pro_seasons)

    @property
    def career_pro_yards(self) -> int:
        return sum(s.get("yards", 0) for s in self.pro_seasons)

    @property
    def career_pro_tds(self) -> int:
        return sum(s.get("tds", 0) for s in self.pro_seasons)

    @property
    def career_pro_seasons_count(self) -> int:
        return len(self.pro_seasons)

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "full_name": self.full_name,
            "position": self.position,
            "nationality": self.nationality,
            "hometown": self.hometown,
            "college_team": self.college_team,
            "college_conference": self.college_conference,
            "college_prestige": self.college_prestige,
            "college_seasons": self.college_seasons,
            "pro_entry_year": self.pro_entry_year,
            "pro_seasons": self.pro_seasons,
            "national_team": self.national_team,
            "international_caps": self.international_caps,
            "international_seasons": self.international_seasons,
            "world_cup_appearances": self.world_cup_appearances,
            "career_status": self.career_status,
            "retirement_year": self.retirement_year,
            "peak_overall": self.peak_overall,
            "peak_ratings": self.peak_ratings,
            "career_awards": self.career_awards,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PlayerCareerRecord":
        return cls(
            player_id=d.get("player_id", ""),
            full_name=d.get("full_name", ""),
            position=d.get("position", ""),
            nationality=d.get("nationality", ""),
            hometown=d.get("hometown", ""),
            college_team=d.get("college_team", ""),
            college_conference=d.get("college_conference", ""),
            college_prestige=d.get("college_prestige", 0),
            college_seasons=d.get("college_seasons") or [],
            pro_entry_year=d.get("pro_entry_year"),
            pro_seasons=d.get("pro_seasons") or [],
            national_team=d.get("national_team") or "",
            international_caps=d.get("international_caps") or 0,
            international_seasons=d.get("international_seasons") or [],
            world_cup_appearances=d.get("world_cup_appearances", 0),
            career_status=d.get("career_status", "active"),
            retirement_year=d.get("retirement_year"),
            peak_overall=d.get("peak_overall", 0),
            peak_ratings=d.get("peak_ratings", {}),
            career_awards=d.get("career_awards", []),
        )


class PlayerCareerTracker:
    """Tracks careers for all players across CVL, WVL, and FIV."""

    def __init__(self):
        self.careers: Dict[str, PlayerCareerRecord] = {}

    def _key(self, name: str) -> str:
        """Normalize player name for lookup."""
        return name.strip().lower()

    def get_or_create(self, full_name: str, **kwargs) -> PlayerCareerRecord:
        key = self._key(full_name)
        if key not in self.careers:
            self.careers[key] = PlayerCareerRecord(
                player_id=kwargs.get("player_id", ""),
                full_name=full_name,
                position=kwargs.get("position", ""),
                nationality=kwargs.get("nationality", ""),
                hometown=kwargs.get("hometown", ""),
            )
        return self.careers[key]

    def ingest_cvl_graduates(self, graduate_pool: list, year: int):
        """Import CVL graduates from the bridge DB export into career records."""
        for grad in graduate_pool:
            name = f"{grad.get('first_name', '')} {grad.get('last_name', '')}".strip()
            if not name:
                name = grad.get("full_name", grad.get("name", "Unknown"))

            record = self.get_or_create(
                name,
                player_id=grad.get("player_id", ""),
                position=grad.get("position", ""),
                nationality=grad.get("nationality", ""),
                hometown=grad.get("hometown", ""),
            )
            record.college_team = grad.get("graduating_from", "")
            record.college_conference = grad.get("conference", "")
            record.college_prestige = grad.get("college_prestige", 0)
            record.pro_entry_year = year

            # Import college career seasons if available
            for cs in grad.get("career_seasons", []):
                record.college_seasons.append(cs)

            # Update peak ratings from college graduation
            ratings = grad.get("ratings", {})
            ovr = ratings.get("overall", grad.get("overall", 0))
            if ovr > record.peak_overall:
                record.peak_overall = ovr
                record.peak_ratings = {
                    k: v for k, v in ratings.items()
                    if k != "overall" and isinstance(v, (int, float))
                }

    def record_wvl_season(
        self,
        team_rosters: Dict[str, list],
        season_stats: Dict[str, Dict[str, dict]],
        tier_assignments: Dict[str, int],
        year: int,
        team_names: Optional[Dict[str, str]] = None,
    ):
        """Record one WVL season's stats for all players in all rosters.

        Args:
            team_rosters: team_key -> list of PlayerCard objects
            season_stats: from ProLeagueSeason.player_season_stats
                          team_key -> {composite_key: {stat_name: value}}
                          where composite_key is f"{team_key}_{player_name}"
            tier_assignments: team_key -> tier number
            year: season year
            team_names: optional team_key -> display name mapping
        """
        names = team_names or {}
        for team_key, cards in team_rosters.items():
            tier = tier_assignments.get(team_key, 0)
            team_name = names.get(team_key, team_key)
            team_stats = season_stats.get(team_key, {})

            # Build a name-based lookup from the composite-keyed stats dict.
            # Keys in player_season_stats are f"{team_key}_{player_name}".
            stats_by_name: Dict[str, dict] = {}
            for composite_key, pdata in team_stats.items():
                pname = pdata.get("name", "")
                if pname:
                    stats_by_name[pname] = pdata
                else:
                    # Fallback: strip team_key prefix to get name
                    prefix = f"{team_key}_"
                    if composite_key.startswith(prefix):
                        stats_by_name[composite_key[len(prefix):]] = pdata

            for card in cards:
                name = card.full_name if hasattr(card, 'full_name') else str(card)
                record = self.get_or_create(
                    name,
                    player_id=getattr(card, 'player_id', ''),
                    position=getattr(card, 'position', ''),
                    nationality=getattr(card, 'nationality', ''),
                )

                # Match stats by player name (the actual key format)
                pstats = stats_by_name.get(name, {})

                ovr = getattr(card, 'overall', 0)
                if ovr > record.peak_overall:
                    record.peak_overall = ovr

                season_entry = {
                    "year": year,
                    "team_key": team_key,
                    "team_name": team_name,
                    "tier": tier,
                    "games": pstats.get("games", 0),
                    "yards": pstats.get("total_yards", 0),
                    "rushing_yards": pstats.get("rushing_yards", 0),
                    "kick_pass_yards": pstats.get("kick_pass_yards", 0),
                    "tds": pstats.get("touchdowns", 0),
                    "tackles": pstats.get("tackles", 0),
                    "overall": ovr,
                }
                record.pro_seasons.append(season_entry)
                if record.career_status == "college":
                    record.career_status = "active"
                if record.pro_entry_year is None:
                    record.pro_entry_year = year

    def record_fiv_cycle(self, player_stats: Dict[str, dict], year: int):
        """Record international stats from an FIV cycle.

        Args:
            player_stats: player_name -> {nation, caps, games, yards, tds, competition...}
            year: cycle year
        """
        for pname, stats in player_stats.items():
            record = self.get_or_create(pname)
            record.national_team = stats.get("nation", record.national_team)
            record.international_caps += stats.get("caps", stats.get("games", 0))

            season_entry = {
                "year": year,
                "nation": stats.get("nation", ""),
                "competition": stats.get("competition", "FIV"),
                "games": stats.get("games", 0),
                "yards": stats.get("yards", 0),
                "tds": stats.get("tds", 0),
            }
            record.international_seasons.append(season_entry)

            if stats.get("world_cup", False):
                record.world_cup_appearances += 1

    def record_retirement(self, player_name: str, year: int):
        """Mark a player as retired."""
        key = self._key(player_name)
        if key in self.careers:
            self.careers[key].career_status = "retired"
            self.careers[key].retirement_year = year

    def get_career(self, player_name: str) -> Optional[PlayerCareerRecord]:
        return self.careers.get(self._key(player_name))

    def search_players(
        self,
        query: str = "",
        position: str = "",
        status: str = "",
        nationality: str = "",
        limit: int = 50,
    ) -> List[PlayerCareerRecord]:
        """Search players with optional filters."""
        results = []
        q = query.lower()
        for record in self.careers.values():
            if q and q not in record.full_name.lower():
                continue
            if position and record.position != position:
                continue
            if status and record.career_status != status:
                continue
            if nationality and record.nationality != nationality:
                continue
            results.append(record)
        results.sort(key=lambda r: -r.peak_overall)
        return results[:limit]

    def get_all_time_leaders(self, stat: str = "yards", limit: int = 20) -> List[dict]:
        """Get career stat leaders."""
        entries = []
        for record in self.careers.values():
            if not record.pro_seasons:
                continue
            if stat == "yards":
                val = record.career_pro_yards
            elif stat == "tds":
                val = record.career_pro_tds
            elif stat == "games":
                val = record.career_pro_games
            elif stat == "seasons":
                val = record.career_pro_seasons_count
            elif stat == "caps":
                val = record.international_caps
            else:
                val = 0
            entries.append({"record": record, "value": val})
        entries.sort(key=lambda e: -e["value"])
        return entries[:limit]

    def to_dict(self) -> dict:
        return {
            "careers": {k: v.to_dict() for k, v in self.careers.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PlayerCareerTracker":
        tracker = cls()
        for key, rec_data in d.get("careers", {}).items():
            tracker.careers[key] = PlayerCareerRecord.from_dict(rec_data)
        return tracker
