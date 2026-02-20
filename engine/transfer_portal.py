"""
Viperball Transfer Portal

Handles player transfers between teams.  Players enter the portal after a
season when certain conditions are met (graduating seniors leave, unhappy
players transfer, etc.).  Other teams can browse the portal and make offers.

Works in both modes:
- **Dynasty mode**: Full cycle — portal opens after the season, teams make
  offers, players decide.  Integrates with the NIL system and recruiting.
- **One-off season mode**: Simplified — user picks from a pre-populated
  portal to bolster their roster before a single season starts.

Usage (dynasty):
    from engine.transfer_portal import (
        TransferPortal, populate_portal, PortalEntry,
    )

    portal = TransferPortal(year=2027)
    populate_portal(portal, all_rosters, standings, rng=rng)
    portal.make_offer("Gonzaga", portal.entries[0])
    results = portal.resolve_all(team_prestige, nil_offers, rng)

Usage (one-off season):
    portal = generate_quick_portal(team_names, size=40, rng=rng)
    picked = portal.entries[:5]  # user picks 5 players
"""

from __future__ import annotations

import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from engine.player_card import PlayerCard


# ──────────────────────────────────────────────
# TRANSFER REASONS
# ──────────────────────────────────────────────

TRANSFER_REASONS = [
    "seeking_playing_time",
    "coaching_change",
    "closer_to_home",
    "nil_opportunity",
    "fresh_start",
    "program_direction",
    "graduate_transfer",
]


# ──────────────────────────────────────────────
# PORTAL ENTRY
# ──────────────────────────────────────────────

@dataclass
class PortalEntry:
    """A single player in the transfer portal."""

    player_card: PlayerCard
    origin_team: str
    reason: str
    year_entered: int

    # Portal state
    offers: List[str] = field(default_factory=list)        # team names
    nil_offers: Dict[str, float] = field(default_factory=dict)  # team -> amount
    committed_to: Optional[str] = None
    withdrawn: bool = False

    # Preferences (affect decision)
    prefers_prestige: float = 0.4
    prefers_nil: float = 0.35
    prefers_geography: float = 0.25

    @property
    def player_name(self) -> str:
        return self.player_card.full_name

    @property
    def position(self) -> str:
        return self.player_card.position

    @property
    def overall(self) -> int:
        return self.player_card.overall

    @property
    def stars(self) -> int:
        return self.player_card.potential

    def get_summary(self) -> dict:
        """Public-facing summary for the portal browser."""
        return {
            "name": self.player_name,
            "position": self.position,
            "overall": self.overall,
            "year": self.player_card.year,
            "origin_team": self.origin_team,
            "reason": self.reason,
            "potential": self.player_card.potential,
            "offers_count": len(self.offers),
            "committed_to": self.committed_to,
        }

    def to_dict(self) -> dict:
        return {
            "player": self.player_card.to_dict(),
            "origin_team": self.origin_team,
            "reason": self.reason,
            "year_entered": self.year_entered,
            "offers": list(self.offers),
            "committed_to": self.committed_to,
            "withdrawn": self.withdrawn,
        }


# ──────────────────────────────────────────────
# TRANSFER PORTAL
# ──────────────────────────────────────────────

# ── Prestige → transfer cap mapping ──
# Higher prestige programs can land more portal players.
# This is used in one-off season mode where there's no multi-team
# competition — the cap IS the balancing mechanism.
_PORTAL_CAP_TABLE: List[Tuple[int, int]] = [
    # (min_prestige, max_transfers)
    (90, 7),   # blue-blood: up to 7
    (75, 6),   # strong program
    (60, 5),   # solid program
    (45, 4),   # average
    (30, 3),   # below average
    (0,  2),   # bottom tier: still get 2
]


def portal_cap_for_prestige(prestige: int) -> int:
    """Return the max portal transfers a team can make given its prestige."""
    for min_pres, cap in _PORTAL_CAP_TABLE:
        if prestige >= min_pres:
            return cap
    return 2


@dataclass
class TransferPortal:
    """
    The transfer portal for a single offseason or one-off season.

    Contains all portal entries and manages offers / resolutions.

    In one-off season mode, ``transfer_cap`` limits how many players a team
    can grab via ``instant_commit()``.  Set to 0 for unlimited (dynasty mode
    handles limits through scholarship counts instead).
    """
    year: int
    entries: List[PortalEntry] = field(default_factory=list)
    resolved: bool = False

    # Per-team transfer cap (one-off season mode).  0 = unlimited.
    transfer_cap: int = 0

    # Tracking
    transfers_completed: List[dict] = field(default_factory=list)
    _team_commit_counts: Dict[str, int] = field(default_factory=dict)

    def add_entry(self, entry: PortalEntry) -> None:
        self.entries.append(entry)

    def get_available(self) -> List[PortalEntry]:
        """Get entries that haven't committed or been withdrawn."""
        return [e for e in self.entries if e.committed_to is None and not e.withdrawn]

    def get_by_position(self, position_keyword: str) -> List[PortalEntry]:
        """Filter portal by position keyword (e.g. 'Viper', 'Lineman')."""
        return [
            e for e in self.get_available()
            if position_keyword.lower() in e.position.lower()
        ]

    def get_by_overall(self, min_ovr: int = 0) -> List[PortalEntry]:
        """Filter portal by minimum overall rating."""
        return [e for e in self.get_available() if e.overall >= min_ovr]

    def make_offer(self, team_name: str, entry: PortalEntry, nil_amount: float = 0.0) -> bool:
        """
        Make an offer to a portal player.

        Returns True if offer was made.
        """
        if entry.committed_to is not None or entry.withdrawn:
            return False
        if team_name == entry.origin_team:
            return False  # can't re-recruit from same school via portal
        if team_name in entry.offers:
            return False  # already offered

        entry.offers.append(team_name)
        if nil_amount > 0:
            entry.nil_offers[team_name] = nil_amount
        return True

    def withdraw_offer(self, team_name: str, entry: PortalEntry) -> bool:
        if team_name not in entry.offers:
            return False
        entry.offers.remove(team_name)
        entry.nil_offers.pop(team_name, None)
        return True

    def transfers_remaining(self, team_name: str) -> int:
        """How many more portal transfers this team can make.  -1 = unlimited."""
        if self.transfer_cap <= 0:
            return -1
        used = self._team_commit_counts.get(team_name, 0)
        return max(0, self.transfer_cap - used)

    def instant_commit(self, team_name: str, entry: PortalEntry) -> bool:
        """
        For one-off season mode: immediately commit a player (no decision sim).

        Respects ``transfer_cap`` — returns False if the team has hit its limit.
        """
        if entry.committed_to is not None or entry.withdrawn:
            return False

        # Enforce cap (0 = unlimited)
        if self.transfer_cap > 0:
            used = self._team_commit_counts.get(team_name, 0)
            if used >= self.transfer_cap:
                return False

        entry.committed_to = team_name
        entry.offers = [team_name]
        self._team_commit_counts[team_name] = self._team_commit_counts.get(team_name, 0) + 1
        self.transfers_completed.append({
            "player": entry.player_name,
            "from": entry.origin_team,
            "to": team_name,
            "overall": entry.overall,
            "position": entry.position,
        })
        return True

    def resolve_all(
        self,
        team_prestige: Dict[str, int],
        team_regions: Dict[str, str],
        rng: Optional[random.Random] = None,
    ) -> Dict[str, List[PortalEntry]]:
        """
        Resolve all portal entries (dynasty mode).

        Each player with offers picks the best team based on prestige,
        NIL, and geography.

        Returns dict of team_name -> list of PortalEntry that committed.
        """
        if rng is None:
            rng = random.Random()

        result: Dict[str, List[PortalEntry]] = {}

        # Sort by overall (best players decide first)
        sorted_entries = sorted(self.get_available(), key=lambda e: -e.overall)

        for entry in sorted_entries:
            if not entry.offers:
                continue

            best_score = -1.0
            best_team = None

            # Find max NIL for normalisation
            max_nil = max(entry.nil_offers.values()) if entry.nil_offers else 1.0

            for team_name in entry.offers:
                prestige = team_prestige.get(team_name, 50)
                prestige_score = prestige

                # Geography
                team_region = team_regions.get(team_name, "midwest")
                # Use player's hometown state/country for geo matching
                pc = entry.player_card
                if pc.hometown_state and team_region in _REGION_FROM_STATE.get(pc.hometown_state, []):
                    geo_score = 90.0
                else:
                    geo_score = 40.0

                # NIL
                nil_amt = entry.nil_offers.get(team_name, 0.0)
                nil_score = (nil_amt / max(1.0, max_nil)) * 100.0

                noise = rng.uniform(-6, 6)
                score = (
                    entry.prefers_prestige * prestige_score
                    + entry.prefers_geography * geo_score
                    + entry.prefers_nil * nil_score
                    + noise
                )
                if score > best_score:
                    best_score = score
                    best_team = team_name

            if best_team:
                entry.committed_to = best_team
                result.setdefault(best_team, []).append(entry)
                self.transfers_completed.append({
                    "player": entry.player_name,
                    "from": entry.origin_team,
                    "to": best_team,
                    "overall": entry.overall,
                    "position": entry.position,
                })

        self.resolved = True
        return result

    def get_class_summary(self) -> List[dict]:
        """Summary of all transfers that happened."""
        return list(self.transfers_completed)

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "entries": [e.to_dict() for e in self.entries],
            "transfers_completed": self.transfers_completed,
            "resolved": self.resolved,
        }


# State -> region mapping (simplified)
_REGION_FROM_STATE: Dict[str, List[str]] = {
    "MA": ["northeast"], "CT": ["northeast"], "ME": ["northeast"],
    "VT": ["northeast"], "NH": ["northeast"], "RI": ["northeast"],
    "NY": ["northeast", "mid_atlantic"], "NJ": ["mid_atlantic"],
    "PA": ["mid_atlantic"], "MD": ["mid_atlantic"], "DE": ["mid_atlantic"],
    "VA": ["mid_atlantic", "south"], "DC": ["mid_atlantic"],
    "NC": ["south"], "SC": ["south"], "GA": ["south"], "FL": ["south"],
    "TN": ["south"], "AL": ["south"], "MS": ["south"], "LA": ["south"],
    "AR": ["south"],
    "OH": ["midwest"], "MI": ["midwest"], "IN": ["midwest"],
    "IL": ["midwest"], "WI": ["midwest"], "MN": ["midwest"],
    "IA": ["midwest"], "MO": ["midwest"], "KS": ["midwest"],
    "NE": ["midwest"], "ND": ["midwest"], "SD": ["midwest"],
    "CA": ["west_coast"], "WA": ["west_coast"], "OR": ["west_coast"],
    "NV": ["west_coast"], "HI": ["west_coast"], "AK": ["west_coast"],
    "TX": ["texas_southwest"], "AZ": ["texas_southwest"],
    "NM": ["texas_southwest"], "OK": ["texas_southwest"],
    "CO": ["west_coast", "midwest"],
    "UT": ["west_coast"], "ID": ["west_coast"], "MT": ["midwest"],
    "WY": ["midwest"],
}


# ──────────────────────────────────────────────
# PORTAL POPULATION (DYNASTY MODE)
# ──────────────────────────────────────────────

def _should_enter_portal(
    card: PlayerCard,
    team_record_wins: int,
    team_record_losses: int,
    rng: random.Random,
    retention_bonus: float = 0.0,
) -> Optional[str]:
    """
    Determine if a player enters the transfer portal.

    Returns the reason string, or None if they stay.
    """
    # Graduates always leave
    if card.year == "Graduate":
        if rng.random() < 0.60:
            return "graduate_transfer"
        return None  # some graduates stay for a 5th+ year

    # Seniors very rarely transfer
    if card.year == "Senior":
        if rng.random() < 0.05:
            return "nil_opportunity"
        return None

    # Losing record increases portal entries
    loss_rate = team_record_losses / max(1, team_record_wins + team_record_losses)

    base_chance = 0.08  # ~8% base transfer rate
    if loss_rate > 0.6:
        base_chance += 0.10   # bad team: more players leave
    elif loss_rate > 0.4:
        base_chance += 0.04

    # Low potential players less likely to transfer (nowhere to go)
    if card.potential <= 2:
        base_chance *= 0.5

    # High potential underperformers more likely
    if card.potential >= 4 and card.overall < 70:
        base_chance += 0.06

    if retention_bonus > 0:
        base_chance *= max(0.3, 1.0 - retention_bonus)

    if rng.random() < base_chance:
        reasons = [
            ("seeking_playing_time", 0.30),
            ("nil_opportunity", 0.25),
            ("program_direction", 0.20),
            ("closer_to_home", 0.15),
            ("fresh_start", 0.10),
        ]
        r_names, r_weights = zip(*reasons)
        return rng.choices(r_names, weights=r_weights, k=1)[0]

    return None


def populate_portal(
    portal: TransferPortal,
    team_rosters: Dict[str, List[PlayerCard]],
    team_records: Dict[str, Tuple[int, int]],
    rng: Optional[random.Random] = None,
    coaching_retention: Optional[Dict[str, float]] = None,
) -> List[PortalEntry]:
    """
    Populate the transfer portal from existing team rosters.

    Args:
        portal:       TransferPortal to populate.
        team_rosters: team_name -> list of PlayerCard.
        team_records: team_name -> (wins, losses).
        rng:          Seeded Random.

    Returns:
        List of new PortalEntry objects added to the portal.
    """
    if rng is None:
        rng = random.Random()

    new_entries: List[PortalEntry] = []

    if coaching_retention is None:
        coaching_retention = {}

    for team_name, roster in team_rosters.items():
        wins, losses = team_records.get(team_name, (5, 5))
        ret_bonus = coaching_retention.get(team_name, 0.0)
        for card in roster:
            reason = _should_enter_portal(card, wins, losses, rng, retention_bonus=ret_bonus)
            if reason is not None:
                pres = rng.uniform(0.25, 0.55)
                nil_pref = rng.uniform(0.15, 0.45)
                geo = max(0.0, 1.0 - pres - nil_pref)

                entry = PortalEntry(
                    player_card=card,
                    origin_team=team_name,
                    reason=reason,
                    year_entered=portal.year,
                    prefers_prestige=pres,
                    prefers_nil=nil_pref,
                    prefers_geography=geo,
                )
                portal.add_entry(entry)
                new_entries.append(entry)

    return new_entries


# ──────────────────────────────────────────────
# QUICK PORTAL (ONE-OFF SEASON MODE)
# ──────────────────────────────────────────────

def estimate_prestige_from_roster(roster: list) -> int:
    """
    Estimate a team's prestige from its current roster.

    Works without dynasty history — useful for one-off season mode.
    Uses average overall + average potential across the roster to produce
    a 0-100 prestige score.

    Args:
        roster: List of objects with `overall` (int) and `potential` (int)
                attributes — PlayerCard, Player dicts, etc.  Also accepts
                dicts with "stats" and "potential" keys (raw team JSON format).

    Returns:
        Prestige rating 0-100.
    """
    if not roster:
        return 50

    overalls = []
    potentials = []
    for p in roster:
        if isinstance(p, dict):
            # Raw team JSON player dict
            stats = p.get("stats", {})
            avg_stat = sum(stats.values()) / max(1, len(stats)) if stats else 70
            overalls.append(avg_stat)
            potentials.append(p.get("potential", 3))
        else:
            # PlayerCard or Player object
            overalls.append(getattr(p, "overall", 70))
            potentials.append(getattr(p, "potential", 3))

    avg_ovr = sum(overalls) / len(overalls)
    avg_pot = sum(potentials) / len(potentials)

    # Scale: OVR maps roughly linearly to prestige across the full 0-100 range.
    # Potential gives a small bonus (3.0 avg → 0, 5.0 avg → +10)
    ovr_score = avg_ovr * 0.9
    pot_bonus = max(0, (avg_pot - 3.0)) * 5.0

    return max(10, min(99, int(ovr_score + pot_bonus)))


# ── Portal origin data (schools NOT in the game, with regional hometowns) ──

# These are all real schools that are NOT in the 102-team CVL.
# Spread across D1 football programs, FCS, D2, NAIA, and international clubs.
_DOMESTIC_ORIGINS = [
    {
        "schools": [
            "Ohio State", "Alabama", "Michigan", "LSU", "Georgia",
            "Oklahoma", "USC", "Texas", "Oregon", "Florida State",
            "Notre Dame", "Penn State", "Clemson", "Auburn", "Wisconsin",
        ],
        "hometowns": [
            {"city": "Columbus", "state": "OH", "country": "USA"},
            {"city": "Tuscaloosa", "state": "AL", "country": "USA"},
            {"city": "Ann Arbor", "state": "MI", "country": "USA"},
            {"city": "Baton Rouge", "state": "LA", "country": "USA"},
            {"city": "Athens", "state": "GA", "country": "USA"},
            {"city": "Norman", "state": "OK", "country": "USA"},
            {"city": "Eugene", "state": "OR", "country": "USA"},
        ],
        "first_names": [
            "Aaliyah", "Avery", "Bailey", "Blake", "Brianna", "Callie",
            "Cameron", "Casey", "Chelsea", "Cora", "Dakota", "Delaney",
            "Destiny", "Drew", "Elena", "Ella", "Emily", "Emma", "Eva",
            "Faith", "Grace", "Hailey", "Hannah", "Harper", "Hayden",
            "Isabella", "Jade", "Jamie", "Jasmine", "Jordan", "Julia",
            "Kayla", "Kendall", "Kennedy", "Leah", "Lily", "Logan",
            "Mackenzie", "Madison", "Mia", "Morgan", "Natalie", "Olivia",
            "Paige", "Peyton", "Quinn", "Reagan", "Reese", "Riley",
            "Sage", "Samantha", "Savannah", "Sierra", "Skylar", "Sloane",
            "Sydney", "Tatum", "Taylor", "Tessa", "Trinity", "Victoria",
        ],
        "last_names": [
            "Adams", "Allen", "Anderson", "Baker", "Barnes", "Bell",
            "Bennett", "Brooks", "Brown", "Bryant", "Butler", "Campbell",
            "Carter", "Clark", "Cole", "Collins", "Cook", "Cooper",
            "Cruz", "Davis", "Dixon", "Edwards", "Evans", "Fisher",
            "Flores", "Ford", "Foster", "Garcia", "Gibson", "Gonzalez",
            "Green", "Griffin", "Hall", "Hamilton", "Harris", "Hayes",
            "Henderson", "Hernandez", "Hill", "Howard", "Hughes",
            "Jackson", "James", "Jenkins", "Johnson", "Jones", "Jordan",
            "Kelly", "Kennedy", "King", "Lee", "Lewis", "Long", "Lopez",
            "Martin", "Martinez", "Miller", "Mitchell", "Moore", "Morgan",
            "Murphy", "Nelson", "Nguyen", "Owens", "Parker", "Patterson",
            "Perez", "Perry", "Phillips", "Powell", "Price", "Reed",
            "Richardson", "Rivera", "Roberts", "Robinson", "Rodriguez",
            "Rogers", "Russell", "Sanders", "Scott", "Smith", "Spencer",
            "Stewart", "Sullivan", "Taylor", "Thomas", "Thompson",
            "Torres", "Turner", "Walker", "Wallace", "Washington",
            "Watson", "White", "Williams", "Wilson", "Wright", "Young",
        ],
        "nationality": "American",
    },
    {
        # Smaller programs / FCS / D2 schools
        "schools": [
            "Montana", "North Dakota State", "James Madison", "Sam Houston State",
            "Villanova (FCS)", "Delaware", "Maine", "New Hampshire",
            "Towson", "William & Mary", "Richmond", "Youngstown State",
            "Central Michigan", "Eastern Michigan", "Bowling Green",
            "Akron", "Ball State", "Kent State", "Toledo",
            "Texas State", "Louisiana-Monroe", "Arkansas State",
            "Appalachian State", "Coastal Carolina", "Marshall",
        ],
        "hometowns": [
            {"city": "Missoula", "state": "MT", "country": "USA"},
            {"city": "Fargo", "state": "ND", "country": "USA"},
            {"city": "Harrisonburg", "state": "VA", "country": "USA"},
            {"city": "Huntsville", "state": "TX", "country": "USA"},
            {"city": "Newark", "state": "DE", "country": "USA"},
            {"city": "Orono", "state": "ME", "country": "USA"},
            {"city": "Morgantown", "state": "WV", "country": "USA"},
            {"city": "San Marcos", "state": "TX", "country": "USA"},
            {"city": "Boone", "state": "NC", "country": "USA"},
            {"city": "Conway", "state": "SC", "country": "USA"},
            {"city": "Bowling Green", "state": "OH", "country": "USA"},
            {"city": "Ypsilanti", "state": "MI", "country": "USA"},
        ],
        "first_names": [
            "Abby", "Alex", "Angel", "Aria", "Ariana", "Autumn",
            "Bella", "Brielle", "Brooklyn", "Carmen", "Charlie",
            "Claire", "Dani", "Diana", "Eliana", "Emery", "Evelyn",
            "Finley", "Gabriella", "Gianna", "Haven", "Ivy", "Jenna",
            "Kaia", "Kira", "Layla", "Lila", "Luna", "Maeve", "Malia",
            "Maya", "Nadia", "Nicole", "Nora", "Piper", "Raven",
            "Remi", "Rowan", "Sara", "Sienna", "Sofia", "Valentina",
            "Vivian", "Willow", "Zara", "Zoe",
        ],
        "last_names": [
            "Abbott", "Barker", "Blair", "Booth", "Burns", "Carpenter",
            "Carroll", "Chambers", "Chapman", "Curtis", "Dawson",
            "Drake", "Dunn", "Elliott", "Farmer", "Fields", "Garrett",
            "Gibbs", "Graves", "Harmon", "Hicks", "Holland", "Horton",
            "Hubbard", "Ingram", "Jennings", "Kemp", "Knox", "Lambert",
            "Lawson", "Mack", "Maloney", "Marsh", "Maxwell", "Meadows",
            "Mercer", "Miles", "Monroe", "Nash", "Norris", "Pace",
            "Pratt", "Ramsey", "Reeves", "Rowe", "Shepherd", "Snow",
            "Sparks", "Stokes", "Sutton", "Tate", "Valentine", "Vance",
            "Vaughn", "Wade", "Walters", "Warner", "Watts", "Whitaker",
        ],
        "nationality": "American",
    },
]

_INTL_ORIGINS = [
    {
        # Australian
        "schools": [
            "Sydney Uni Viperball Club", "Melbourne Chargers",
            "Brisbane Thunderbolts", "Perth Razorbacks",
            "Adelaide Vipers", "Canberra Capitals",
        ],
        "hometowns": [
            {"city": "Sydney", "state": "NSW", "country": "Australia"},
            {"city": "Melbourne", "state": "VIC", "country": "Australia"},
            {"city": "Brisbane", "state": "QLD", "country": "Australia"},
            {"city": "Perth", "state": "WA", "country": "Australia"},
            {"city": "Adelaide", "state": "SA", "country": "Australia"},
            {"city": "Gold Coast", "state": "QLD", "country": "Australia"},
        ],
        "first_names": [
            "Amelia", "Charlotte", "Chloe", "Grace", "Harper", "Isla",
            "Ivy", "Lily", "Mia", "Olivia", "Ruby", "Sophie", "Willow",
            "Billie", "Frankie", "Georgie", "Hayley", "Talia", "Zara",
        ],
        "last_names": [
            "Anderson", "Brown", "Campbell", "Clarke", "Collins",
            "Davidson", "Evans", "Ferguson", "Gibson", "Harris",
            "Henderson", "Hughes", "Johnston", "Kelly", "Kennedy",
            "McDonald", "Mitchell", "Morrison", "Murray", "O'Brien",
            "O'Connor", "Reid", "Robinson", "Stewart", "Taylor",
            "Thompson", "Turner", "Wallace", "Watson", "Wilson",
        ],
        "nationality": "Australian",
    },
    {
        # UK / European
        "schools": [
            "London Blitz", "Manchester Titans", "Edinburgh Wolves",
            "Birmingham Bulls", "Dublin Rebels", "Paris Vipers FC",
            "Berlin Adler", "Amsterdam Crusaders",
        ],
        "hometowns": [
            {"city": "London", "state": "", "country": "England"},
            {"city": "Manchester", "state": "", "country": "England"},
            {"city": "Birmingham", "state": "", "country": "England"},
            {"city": "Edinburgh", "state": "", "country": "Scotland"},
            {"city": "Dublin", "state": "", "country": "Ireland"},
            {"city": "Paris", "state": "", "country": "France"},
            {"city": "Berlin", "state": "", "country": "Germany"},
            {"city": "Amsterdam", "state": "", "country": "Netherlands"},
        ],
        "first_names": [
            "Amelia", "Charlotte", "Eleanor", "Freya", "Georgia",
            "Holly", "Imogen", "Jessica", "Katie", "Lucy", "Maisie",
            "Poppy", "Rosie", "Saoirse", "Niamh", "Ciara", "Aoife",
            "Eloise", "Léa", "Lena", "Maja", "Nele",
        ],
        "last_names": [
            "Armstrong", "Bailey", "Barrett", "Brennan", "Byrne",
            "Connolly", "Davies", "Doyle", "Fitzgerald", "Fletcher",
            "Gallagher", "Graham", "Hall", "Hart", "Hayes", "Kelly",
            "Lynch", "Murphy", "Nolan", "O'Brien", "O'Neill", "Quinn",
            "Ryan", "Shaw", "Sullivan", "Walsh", "Weber", "Müller",
            "Dubois", "Van der Berg",
        ],
        "nationality": "British",
    },
    {
        # Canadian
        "schools": [
            "Toronto Varsity Blues", "UBC Thunderbirds",
            "Laval Rouge et Or", "McGill Redbirds",
            "Calgary Dinos", "Western Mustangs",
            "Queen's Gaels", "McMaster Marauders",
        ],
        "hometowns": [
            {"city": "Toronto", "state": "ON", "country": "Canada"},
            {"city": "Vancouver", "state": "BC", "country": "Canada"},
            {"city": "Montreal", "state": "QC", "country": "Canada"},
            {"city": "Calgary", "state": "AB", "country": "Canada"},
            {"city": "Ottawa", "state": "ON", "country": "Canada"},
            {"city": "Edmonton", "state": "AB", "country": "Canada"},
            {"city": "Winnipeg", "state": "MB", "country": "Canada"},
        ],
        "first_names": [
            "Avery", "Brooklyn", "Charlotte", "Emma", "Harper", "Isla",
            "Jade", "Mackenzie", "Maeve", "Olivia", "Paige", "Quinn",
            "Riley", "Sofia", "Taylor", "Victoria", "Zoé", "Camille",
            "Émilie", "Laurence",
        ],
        "last_names": [
            "Anderson", "Blackwell", "Campbell", "Caron", "Chen",
            "Gagnon", "Gill", "Kim", "Lam", "Martin", "McDonald",
            "Nguyen", "Patel", "Roy", "Singh", "Smith", "Thompson",
            "Tremblay", "Wilson", "Wong",
        ],
        "nationality": "Canadian",
    },
    {
        # New Zealand / Pacific Islands
        "schools": [
            "Auckland Uni Viperball", "Canterbury Lancers",
            "Wellington Hurricanes VB", "Otago Highlanders VB",
            "Fiji Viperball Academy", "Samoa Manu VB",
        ],
        "hometowns": [
            {"city": "Auckland", "state": "", "country": "New Zealand"},
            {"city": "Wellington", "state": "", "country": "New Zealand"},
            {"city": "Christchurch", "state": "", "country": "New Zealand"},
            {"city": "Suva", "state": "", "country": "Fiji"},
            {"city": "Apia", "state": "", "country": "Samoa"},
        ],
        "first_names": [
            "Aroha", "Atawhai", "Grace", "Jade", "Manaia", "Mia",
            "Ngaire", "Olivia", "Ruby", "Tia", "Waimarie",
            "Leilani", "Moana", "Sina", "Teuila",
        ],
        "last_names": [
            "Barrett", "Brown", "Clarke", "Edwards", "Harris",
            "Jackson", "King", "Mitchell", "Morgan", "Nikora",
            "Perenara", "Savea", "Smith", "Tui", "Williams",
            "Tuilagi", "Matavesi", "Tuipulotu",
        ],
        "nationality": "New Zealander",
    },
    {
        # Latin American / Caribbean
        "schools": [
            "UNAM Pumas VB", "Tec de Monterrey", "São Paulo Vipers",
            "Buenos Aires Jaguars", "Jamaica Viperball Academy",
            "Trinidad & Tobago National VB",
        ],
        "hometowns": [
            {"city": "Mexico City", "state": "", "country": "Mexico"},
            {"city": "Guadalajara", "state": "", "country": "Mexico"},
            {"city": "Monterrey", "state": "", "country": "Mexico"},
            {"city": "São Paulo", "state": "", "country": "Brazil"},
            {"city": "Buenos Aires", "state": "", "country": "Argentina"},
            {"city": "Kingston", "state": "", "country": "Jamaica"},
            {"city": "Port of Spain", "state": "", "country": "Trinidad"},
        ],
        "first_names": [
            "Ana", "Camila", "Carolina", "Daniela", "Elena", "Gabriela",
            "Isabella", "Lucía", "María", "Sofía", "Valentina",
            "Yamileth", "Bianca", "Fernanda",
        ],
        "last_names": [
            "Alvarez", "Castillo", "Cruz", "Diaz", "Fernandez", "García",
            "Gonzalez", "Hernandez", "Lopez", "Martinez", "Morales",
            "Pérez", "Ramirez", "Rivera", "Rodriguez", "Santos",
            "Silva", "Torres", "Vargas", "Williams",
        ],
        "nationality": "Mexican",
    },
    {
        # African
        "schools": [
            "Lagos Viperball Academy", "Nairobi Cheetahs VB",
            "Accra Thunderbolts", "Cape Town Stormers VB",
            "Johannesburg Lions VB", "Dakar Athletics VB",
        ],
        "hometowns": [
            {"city": "Lagos", "state": "", "country": "Nigeria"},
            {"city": "Nairobi", "state": "", "country": "Kenya"},
            {"city": "Accra", "state": "", "country": "Ghana"},
            {"city": "Cape Town", "state": "", "country": "South Africa"},
            {"city": "Johannesburg", "state": "", "country": "South Africa"},
            {"city": "Dakar", "state": "", "country": "Senegal"},
        ],
        "first_names": [
            "Adaeze", "Amara", "Chidinma", "Ebele", "Fatima", "Ife",
            "Kemi", "Nia", "Nkechi", "Oluchi", "Wanjiru", "Amina",
            "Thandiwe", "Naledi", "Aisha",
        ],
        "last_names": [
            "Abara", "Adeyemi", "Afolabi", "Boateng", "Diallo",
            "Ibrahim", "Kamara", "Mensah", "Ndlovu", "Okafor",
            "Okonkwo", "Owusu", "Sow", "Traore", "Wanjiku",
        ],
        "nationality": "Nigerian",
    },
]


def _pick_portal_origin(is_international: bool, rng: random.Random) -> dict:
    """Pick a pool of origin data for a portal player."""
    if is_international:
        return rng.choice(_INTL_ORIGINS)
    return rng.choice(_DOMESTIC_ORIGINS)


def generate_quick_portal(
    team_names: List[str],
    year: int = 2027,
    size: int = 40,
    prestige: int = 0,
    rng: Optional[random.Random] = None,
) -> TransferPortal:
    """
    Generate a pre-populated transfer portal for one-off season mode.

    Creates synthetic portal players (not drawn from actual rosters)
    so users can pick up reinforcements before a standalone season.

    The portal enforces a prestige-based transfer cap — higher prestige
    programs can pick more players.  If prestige is 0 (unknown), defaults
    to a cap of 4.

    Args:
        team_names: Available team names (used as origin teams).
        year:       Portal year.
        size:       Number of portal entries.
        prestige:   Team prestige 0-100 (determines transfer cap).
        rng:        Seeded Random.

    Returns:
        A TransferPortal with entries ready for instant_commit().
    """
    if rng is None:
        rng = random.Random(year + 99)

    cap = portal_cap_for_prestige(prestige) if prestige > 0 else 4
    portal = TransferPortal(year=year, transfer_cap=cap)

    # Position pool mirroring recruit generation
    positions_pool = [
        "Zeroback", "Halfback", "Wingback", "Slotback",
        "Viper", "Keeper", "Offensive Line", "Defensive Line",
    ]

    for i in range(size):
        pos = rng.choice(positions_pool)

        # ~25% international, ~75% domestic
        is_intl = rng.random() < 0.25
        origin_data = _pick_portal_origin(is_intl, rng)

        first = rng.choice(origin_data["first_names"])
        last = rng.choice(origin_data["last_names"])

        # Portal players are Sophomores to Graduates (not Freshmen)
        year_class = rng.choices(
            ["Sophomore", "Junior", "Senior", "Graduate"],
            weights=[0.30, 0.35, 0.25, 0.10],
            k=1,
        )[0]

        # Stat range: portal players are decent (they had college experience)
        lo, hi = 65, 90
        if year_class in ("Senior", "Graduate"):
            lo, hi = 70, 93

        def _stat():
            return rng.randint(lo, hi)

        # Position adjustments
        speed = _stat()
        stamina = _stat()
        agility = _stat()
        power = _stat()
        awareness = _stat()
        hands = _stat()
        kicking = _stat()
        kick_power = _stat()
        kick_accuracy = _stat()
        lateral_skill = _stat()
        tackling = _stat()

        if pos in ("Viper", "Halfback", "Wingback", "Slotback", "Zeroback"):
            speed = min(99, speed + rng.randint(2, 5))
            lateral_skill = min(99, lateral_skill + rng.randint(1, 4))
        elif pos in ("Offensive Line", "Defensive Line"):
            tackling = min(99, tackling + rng.randint(3, 6))
            power = min(99, power + rng.randint(3, 6))
            speed = max(55, speed - rng.randint(2, 4))

        # Height / weight
        if pos in ("Offensive Line", "Defensive Line"):
            ht_in = rng.randint(69, 75)
            wt = rng.randint(185, 215)
        else:
            ht_in = rng.randint(66, 73)
            wt = rng.randint(155, 195)
        height = f"{ht_in // 12}-{ht_in % 12}"

        potential = rng.choices([2, 3, 4, 5, 1], weights=[30, 35, 20, 10, 5], k=1)[0]
        dev = rng.choices(
            ["normal", "quick", "slow", "late_bloomer"],
            weights=[55, 20, 15, 10], k=1,
        )[0]

        hometown = rng.choice(origin_data["hometowns"])
        ht_city = hometown["city"]
        ht_state = hometown.get("state", "")
        ht_country = hometown.get("country", "USA")

        card = PlayerCard(
            player_id=f"PORTAL-{year}-{i:04d}",
            first_name=first,
            last_name=last,
            number=0,
            position=pos,
            archetype="none",
            nationality=origin_data["nationality"],
            hometown_city=ht_city,
            hometown_state=ht_state,
            hometown_country=ht_country,
            high_school="",
            height=height,
            weight=wt,
            year=year_class,
            speed=speed,
            stamina=stamina,
            agility=agility,
            power=power,
            awareness=awareness,
            hands=hands,
            kicking=kicking,
            kick_power=kick_power,
            kick_accuracy=kick_accuracy,
            lateral_skill=lateral_skill,
            tackling=tackling,
            potential=potential,
            development=dev,
            current_team="",
        )

        # Origin school: always a school NOT in the game
        origin_school = rng.choice(origin_data["schools"])
        reason = rng.choice(TRANSFER_REASONS)

        entry = PortalEntry(
            player_card=card,
            origin_team=origin_school,
            reason=reason,
            year_entered=year,
        )
        portal.add_entry(entry)

    # Sort by overall descending
    portal.entries.sort(key=lambda e: -e.overall)
    return portal


# ──────────────────────────────────────────────
# AI PORTAL RECRUITING (CPU teams in dynasty)
# ──────────────────────────────────────────────

def auto_portal_offers(
    portal: TransferPortal,
    team_name: str,
    team_prestige: int,
    needs: List[str],
    nil_budget: float = 200_000.0,
    max_targets: int = 5,
    rng: Optional[random.Random] = None,
) -> Dict[str, float]:
    """
    Auto-make portal offers for a CPU team.

    Args:
        portal:        The transfer portal.
        team_name:     Team making offers.
        team_prestige: 0-100 prestige rating.
        needs:         List of position keywords (e.g. ["Viper", "Offensive Line"]).
        nil_budget:    NIL dollars available for portal players.
        max_targets:   Maximum number of offers.
        rng:           Seeded Random.

    Returns:
        Dict of player_name -> NIL offer amount.
    """
    if rng is None:
        rng = random.Random()

    available = portal.get_available()
    nil_offers: Dict[str, float] = {}

    # Score players by fit
    scored: List[Tuple[float, PortalEntry]] = []
    for entry in available:
        if entry.origin_team == team_name:
            continue

        # Need match bonus
        need_bonus = 0.0
        for need in needs:
            if need.lower() in entry.position.lower():
                need_bonus = 20.0
                break

        # Prestige-appropriate targeting
        ovr_match = 0.0
        if team_prestige >= 70 and entry.overall >= 80:
            ovr_match = 15.0
        elif team_prestige >= 50 and entry.overall >= 70:
            ovr_match = 10.0
        elif team_prestige < 50 and entry.overall < 80:
            ovr_match = 8.0

        score = entry.overall + need_bonus + ovr_match + rng.uniform(-5, 5)
        scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)

    for i, (score, entry) in enumerate(scored[:max_targets]):
        share = nil_budget * (0.35 if i == 0 else 0.15 / max(1, i))
        portal.make_offer(team_name, entry, nil_amount=share)
        nil_offers[entry.player_name] = share

    return nil_offers
