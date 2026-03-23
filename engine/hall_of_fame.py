"""
Hall of Fame
=============

Persistent player museum. Hall of Fame entries are stored as individual SQLite
blobs and survive page refreshes, server restarts, and dynasty resets.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from engine.player_career_tracker import PlayerCareerRecord


@dataclass
class HallOfFameEntry:
    """A single Hall of Fame inductee with frozen career snapshot."""

    player_id: str
    full_name: str
    position: str
    nationality: str
    induction_year: int
    induction_reason: str  # "Auto: 8+ pro seasons" or "Commissioner selection"

    # Frozen career snapshot at time of induction
    career_record: dict = field(default_factory=dict)  # PlayerCareerRecord.to_dict()

    # Portrait data — ratings at retirement/peak
    peak_overall: int = 0
    peak_ratings: Dict[str, int] = field(default_factory=dict)

    # Career highlights
    pro_seasons: int = 0
    pro_yards: int = 0
    pro_tds: int = 0
    international_caps: int = 0
    world_cup_appearances: int = 0
    college_team: str = ""
    pro_teams: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "full_name": self.full_name,
            "position": self.position,
            "nationality": self.nationality,
            "induction_year": self.induction_year,
            "induction_reason": self.induction_reason,
            "career_record": self.career_record,
            "peak_overall": self.peak_overall,
            "peak_ratings": self.peak_ratings,
            "pro_seasons": self.pro_seasons,
            "pro_yards": self.pro_yards,
            "pro_tds": self.pro_tds,
            "international_caps": self.international_caps,
            "world_cup_appearances": self.world_cup_appearances,
            "college_team": self.college_team,
            "pro_teams": self.pro_teams,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HallOfFameEntry":
        return cls(
            player_id=d.get("player_id", ""),
            full_name=d.get("full_name", ""),
            position=d.get("position", ""),
            nationality=d.get("nationality", ""),
            induction_year=d.get("induction_year", 0),
            induction_reason=d.get("induction_reason", ""),
            career_record=d.get("career_record", {}),
            peak_overall=d.get("peak_overall", 0),
            peak_ratings=d.get("peak_ratings", {}),
            pro_seasons=d.get("pro_seasons", 0),
            pro_yards=d.get("pro_yards", 0),
            pro_tds=d.get("pro_tds", 0),
            international_caps=d.get("international_caps", 0),
            world_cup_appearances=d.get("world_cup_appearances", 0),
            college_team=d.get("college_team", ""),
            pro_teams=d.get("pro_teams", []),
        )


# ═══════════════════════════════════════════════════════════════
# AUTO-INDUCTION CRITERIA
# ═══════════════════════════════════════════════════════════════

_HOF_CRITERIA = [
    ("8+ pro seasons", lambda r: r.career_pro_seasons_count >= 8),
    ("5000+ career yards", lambda r: r.career_pro_yards >= 5000),
    ("50+ career TDs", lambda r: r.career_pro_tds >= 50),
    ("3+ career awards", lambda r: len(r.career_awards) >= 3),
    ("10+ international caps", lambda r: r.international_caps >= 10),
    ("World Cup appearance", lambda r: r.world_cup_appearances >= 1),
    ("90+ peak overall", lambda r: r.peak_overall >= 90),
]


class HallOfFame:
    """Manages Hall of Fame inductions and lookups.

    Entries are stored via engine/db.py save_blob for persistence.
    """

    def __init__(self):
        self.entries: Dict[str, HallOfFameEntry] = {}  # keyed by full_name.lower()

    def auto_evaluate(self, career: PlayerCareerRecord) -> Optional[str]:
        """Check if a retired player qualifies for auto-induction.

        Returns the reason string if they qualify, None otherwise.
        """
        if career.career_status not in ("retired",):
            return None
        key = career.full_name.strip().lower()
        if key in self.entries:
            return None  # already inducted

        reasons = []
        for label, check in _HOF_CRITERIA:
            try:
                if check(career):
                    reasons.append(label)
            except Exception:
                pass

        # Need at least 2 criteria met for auto-induction
        if len(reasons) >= 2:
            return f"Auto: {', '.join(reasons[:3])}"
        return None

    def induct(
        self,
        career: PlayerCareerRecord,
        year: int,
        reason: str = "Commissioner selection",
    ) -> HallOfFameEntry:
        """Add a player to the Hall of Fame."""
        entry = HallOfFameEntry(
            player_id=career.player_id,
            full_name=career.full_name,
            position=career.position,
            nationality=career.nationality,
            induction_year=year,
            induction_reason=reason,
            career_record=career.to_dict(),
            peak_overall=career.peak_overall,
            peak_ratings=career.peak_ratings,
            pro_seasons=career.career_pro_seasons_count,
            pro_yards=career.career_pro_yards,
            pro_tds=career.career_pro_tds,
            international_caps=career.international_caps,
            world_cup_appearances=career.world_cup_appearances,
            college_team=career.college_team,
            pro_teams=career.pro_teams_summary,
        )
        key = career.full_name.strip().lower()
        self.entries[key] = entry
        career.career_status = "hall_of_fame"
        return entry

    def process_retirements(
        self,
        retired_names: List[str],
        tracker: "PlayerCareerTracker",
        year: int,
    ) -> List[HallOfFameEntry]:
        """Evaluate all newly retired players for auto-induction.

        Returns list of new inductees.
        """
        from engine.player_career_tracker import PlayerCareerTracker

        new_inductees = []
        for name in retired_names:
            career = tracker.get_career(name)
            if career is None:
                continue
            reason = self.auto_evaluate(career)
            if reason:
                entry = self.induct(career, year, reason)
                new_inductees.append(entry)
        return new_inductees

    def get_entry(self, player_name: str) -> Optional[HallOfFameEntry]:
        return self.entries.get(player_name.strip().lower())

    def get_inductees(self, sort_by: str = "year") -> List[HallOfFameEntry]:
        entries = list(self.entries.values())
        if sort_by == "year":
            entries.sort(key=lambda e: -e.induction_year)
        elif sort_by == "overall":
            entries.sort(key=lambda e: -e.peak_overall)
        elif sort_by == "yards":
            entries.sort(key=lambda e: -e.pro_yards)
        return entries

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in self.entries.items()}

    @classmethod
    def from_dict(cls, d: dict) -> "HallOfFame":
        hof = cls()
        for key, entry_data in d.items():
            hof.entries[key] = HallOfFameEntry.from_dict(entry_data)
        return hof
