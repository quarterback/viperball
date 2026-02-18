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

@dataclass
class TransferPortal:
    """
    The transfer portal for a single offseason or one-off season.

    Contains all portal entries and manages offers / resolutions.
    """
    year: int
    entries: List[PortalEntry] = field(default_factory=list)
    resolved: bool = False

    # Tracking
    transfers_completed: List[dict] = field(default_factory=list)

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

    def instant_commit(self, team_name: str, entry: PortalEntry) -> bool:
        """
        For one-off season mode: immediately commit a player (no decision sim).
        """
        if entry.committed_to is not None or entry.withdrawn:
            return False
        entry.committed_to = team_name
        entry.offers = [team_name]
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

    for team_name, roster in team_rosters.items():
        wins, losses = team_records.get(team_name, (5, 5))
        for card in roster:
            reason = _should_enter_portal(card, wins, losses, rng)
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

def generate_quick_portal(
    team_names: List[str],
    year: int = 2027,
    size: int = 40,
    rng: Optional[random.Random] = None,
) -> TransferPortal:
    """
    Generate a pre-populated transfer portal for one-off season mode.

    Creates synthetic portal players (not drawn from actual rosters)
    so users can pick up reinforcements before a standalone season.

    Args:
        team_names: Available team names (used as origin teams).
        year:       Portal year.
        size:       Number of portal entries.
        rng:        Seeded Random.

    Returns:
        A TransferPortal with entries ready for instant_commit().
    """
    if rng is None:
        rng = random.Random(year + 99)

    portal = TransferPortal(year=year)

    # Position pool mirroring recruit generation
    positions_pool = [
        "Zeroback/Back", "Halfback/Back", "Wingback/End", "Shiftback/Back",
        "Viper/Back", "Lineman", "Back/Safety", "Back/Corner",
        "Wedge/Line", "Wing/End",
    ]

    _SIMPLE_FIRST = [
        "Aaliyah", "Bella", "Carmen", "Dakota", "Elena", "Faith", "Grace",
        "Harper", "Ivy", "Jordan", "Kai", "Luna", "Maya", "Nadia", "Olivia",
        "Quinn", "Riley", "Sage", "Taylor", "Victoria", "Willow", "Zoe",
        "Avery", "Blake", "Cora", "Drew", "Eva", "Finley", "Hailey",
    ]
    _SIMPLE_LAST = [
        "Adams", "Brown", "Clark", "Davis", "Evans", "Fisher", "Garcia",
        "Harris", "Jackson", "King", "Lee", "Martin", "Nelson", "Owen",
        "Parker", "Quinn", "Rivera", "Smith", "Turner", "Vasquez", "Williams",
        "Young", "Chen", "Diaz", "Ford", "Green", "Hill", "James", "Kelly",
    ]

    for i in range(size):
        pos = rng.choice(positions_pool)
        first = rng.choice(_SIMPLE_FIRST)
        last = rng.choice(_SIMPLE_LAST)

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

        if "Viper" in pos or "Back" in pos:
            speed = min(99, speed + rng.randint(2, 5))
            lateral_skill = min(99, lateral_skill + rng.randint(1, 4))
        elif "Lineman" in pos or "Wedge" in pos:
            tackling = min(99, tackling + rng.randint(3, 6))
            power = min(99, power + rng.randint(3, 6))
            speed = max(55, speed - rng.randint(2, 4))

        # Height / weight
        if "Lineman" in pos or "Wedge" in pos:
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

        card = PlayerCard(
            player_id=f"PORTAL-{year}-{i:04d}",
            first_name=first,
            last_name=last,
            number=0,
            position=pos,
            archetype="none",
            nationality="American",
            hometown_city="",
            hometown_state="",
            hometown_country="USA",
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

        origin = rng.choice(team_names) if team_names else "Unknown"
        reason = rng.choice(TRANSFER_REASONS)

        entry = PortalEntry(
            player_card=card,
            origin_team=origin,
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
        needs:         List of position keywords (e.g. ["Viper", "Lineman"]).
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
