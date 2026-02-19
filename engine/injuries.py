"""
Viperball Injury & Availability System

Comprehensive model covering:
- On-field contact injuries (football-specific, during games)
- On-field non-contact injuries (muscle pulls, ligament tears)
- Practice/training injuries (between games)
- Off-field availability issues (academics, illness, personal — women's college context)
- In-game injury events (injuries that happen mid-game, triggering substitutions)
- Substitution logic (depth chart fallback when players are unavailable)

Tiers:
    day_to_day   – Available but diminished, or misses 0-1 games
    minor        – Out 1-2 weeks
    moderate     – Out 3-5 weeks
    major        – Out 6-8 weeks
    severe       – Season-ending

Usage:
    tracker = InjuryTracker()
    new_injuries = tracker.process_week(week, teams, standings)
    unavailable = tracker.get_unavailable_names(team_name, week)
    penalties = tracker.get_team_injury_penalties(team_name, week)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ──────────────────────────────────────────────────────────────
# INJURY TIERS
# ──────────────────────────────────────────────────────────────

INJURY_TIER_WEEKS = {
    "day_to_day": (0, 1),
    "minor":      (1, 2),
    "moderate":   (3, 5),
    "major":      (6, 8),
    "severe":     (99, 99),   # season-ending
}

INJURY_SEVERITY_PENALTY = {
    "day_to_day": 0.01,
    "minor":      0.03,
    "moderate":   0.07,
    "major":      0.10,
    "severe":     0.12,
}

# Stat reduction when a DTD player plays through it (multiplied against their attributes)
DTD_PERFORMANCE_REDUCTION = 0.90  # 10% reduction


# ──────────────────────────────────────────────────────────────
# INJURY CATALOG — On-field contact (football-specific)
# ──────────────────────────────────────────────────────────────

_ON_FIELD_CONTACT = {
    "day_to_day": [
        {"desc": "bruised shoulder", "body": "shoulder"},
        {"desc": "hand contusion", "body": "hand"},
        {"desc": "stinger", "body": "neck"},
        {"desc": "minor knee bruise", "body": "knee"},
        {"desc": "jammed finger", "body": "hand"},
        {"desc": "hip pointer", "body": "hip"},
        {"desc": "minor ankle tweak", "body": "ankle"},
    ],
    "minor": [
        {"desc": "sprained ankle", "body": "ankle"},
        {"desc": "bruised ribs", "body": "ribs"},
        {"desc": "mild concussion", "body": "head"},
        {"desc": "AC joint sprain", "body": "shoulder"},
        {"desc": "turf toe", "body": "foot"},
        {"desc": "bone bruise (knee)", "body": "knee"},
        {"desc": "calf contusion", "body": "calf"},
    ],
    "moderate": [
        {"desc": "MCL sprain (grade 2)", "body": "knee"},
        {"desc": "high ankle sprain", "body": "ankle"},
        {"desc": "shoulder separation", "body": "shoulder"},
        {"desc": "broken hand", "body": "hand"},
        {"desc": "fractured rib", "body": "ribs"},
        {"desc": "concussion (extended protocol)", "body": "head"},
        {"desc": "deep thigh contusion", "body": "thigh"},
    ],
    "major": [
        {"desc": "broken collarbone", "body": "collarbone"},
        {"desc": "torn meniscus (partial)", "body": "knee"},
        {"desc": "Lisfranc sprain", "body": "foot"},
        {"desc": "dislocated elbow", "body": "elbow"},
        {"desc": "broken wrist", "body": "wrist"},
        {"desc": "severe concussion (multi-week protocol)", "body": "head"},
    ],
    "severe": [
        {"desc": "ACL tear", "body": "knee"},
        {"desc": "Achilles rupture", "body": "achilles"},
        {"desc": "broken leg (tibia/fibula)", "body": "leg"},
        {"desc": "dislocated shoulder (labrum tear)", "body": "shoulder"},
        {"desc": "torn patellar tendon", "body": "knee"},
        {"desc": "spinal compression injury", "body": "spine"},
    ],
}


# ──────────────────────────────────────────────────────────────
# INJURY CATALOG — On-field non-contact
# ──────────────────────────────────────────────────────────────

_ON_FIELD_NONCONTACT = {
    "day_to_day": [
        {"desc": "minor hamstring tightness", "body": "hamstring"},
        {"desc": "quad tightness", "body": "quad"},
        {"desc": "cramping", "body": "general"},
        {"desc": "calf tightness", "body": "calf"},
    ],
    "minor": [
        {"desc": "strained hamstring", "body": "hamstring"},
        {"desc": "groin strain", "body": "groin"},
        {"desc": "hip flexor strain", "body": "hip"},
        {"desc": "calf strain", "body": "calf"},
        {"desc": "lower back spasm", "body": "back"},
    ],
    "moderate": [
        {"desc": "pulled hamstring (grade 2)", "body": "hamstring"},
        {"desc": "quad strain (grade 2)", "body": "quad"},
        {"desc": "abdominal strain", "body": "abdomen"},
        {"desc": "groin tear (partial)", "body": "groin"},
    ],
    "major": [
        {"desc": "stress fracture (shin)", "body": "shin"},
        {"desc": "stress fracture (foot)", "body": "foot"},
        {"desc": "herniated disc", "body": "back"},
    ],
    "severe": [
        {"desc": "ACL tear (non-contact)", "body": "knee"},
        {"desc": "Achilles tear (planting)", "body": "achilles"},
        {"desc": "complete hamstring avulsion", "body": "hamstring"},
    ],
}


# ──────────────────────────────────────────────────────────────
# INJURY CATALOG — Practice/training injuries (between games)
# ──────────────────────────────────────────────────────────────

_PRACTICE_INJURY = {
    "day_to_day": [
        {"desc": "tweaked knee in practice", "body": "knee"},
        {"desc": "rolled ankle in warmups", "body": "ankle"},
        {"desc": "sore shoulder from drills", "body": "shoulder"},
        {"desc": "minor back stiffness", "body": "back"},
        {"desc": "jammed thumb in drill", "body": "hand"},
    ],
    "minor": [
        {"desc": "ankle sprain (practice)", "body": "ankle"},
        {"desc": "hamstring pull (conditioning)", "body": "hamstring"},
        {"desc": "shoulder impingement", "body": "shoulder"},
        {"desc": "knee hyperextension (practice)", "body": "knee"},
    ],
    "moderate": [
        {"desc": "ligament sprain (practice collision)", "body": "knee"},
        {"desc": "broken finger (practice)", "body": "hand"},
        {"desc": "labrum aggravation", "body": "shoulder"},
    ],
    "major": [
        {"desc": "torn meniscus (practice)", "body": "knee"},
        {"desc": "broken foot (dropped weight)", "body": "foot"},
    ],
    "severe": [
        {"desc": "ACL tear (practice)", "body": "knee"},
        {"desc": "neck injury (practice collision)", "body": "neck"},
    ],
}


# ──────────────────────────────────────────────────────────────
# AVAILABILITY CATALOG — Off-field issues (women's college)
# ──────────────────────────────────────────────────────────────

_OFF_FIELD = {
    "day_to_day": [
        {"desc": "minor illness", "body": "n/a"},
        {"desc": "missed class — making up coursework", "body": "n/a"},
        {"desc": "stomach bug", "body": "n/a"},
        {"desc": "allergy flare-up", "body": "n/a"},
    ],
    "minor": [
        {"desc": "flu", "body": "n/a"},
        {"desc": "family emergency (brief)", "body": "n/a"},
        {"desc": "upper respiratory infection", "body": "n/a"},
        {"desc": "food poisoning", "body": "n/a"},
        {"desc": "COVID protocol", "body": "n/a"},
        {"desc": "migraine episodes", "body": "n/a"},
    ],
    "moderate": [
        {"desc": "academic probation — limited practice", "body": "n/a"},
        {"desc": "mononucleosis", "body": "n/a"},
        {"desc": "extended personal leave", "body": "n/a"},
        {"desc": "mental health break", "body": "n/a"},
        {"desc": "disciplinary suspension (1 game)", "body": "n/a"},
        {"desc": "iron deficiency — recovery program", "body": "n/a"},
    ],
    "major": [
        {"desc": "academic ineligibility (semester)", "body": "n/a"},
        {"desc": "extended family hardship", "body": "n/a"},
        {"desc": "stress-related medical leave", "body": "n/a"},
        {"desc": "study abroad commitment", "body": "n/a"},
    ],
    "severe": [
        {"desc": "entered transfer portal", "body": "n/a"},
        {"desc": "medical retirement (chronic condition)", "body": "n/a"},
        {"desc": "left program (personal reasons)", "body": "n/a"},
        {"desc": "academic dismissal", "body": "n/a"},
    ],
}


# ──────────────────────────────────────────────────────────────
# INJURY CATEGORY WEIGHTS — How often each category occurs
# ──────────────────────────────────────────────────────────────

# Weekly between-game roll: what kind of issue does a player develop?
WEEKLY_CATEGORY_WEIGHTS = {
    "on_field_contact":    0.30,   # Lingering from last game
    "on_field_noncontact": 0.20,   # Soft tissue from game exertion
    "practice":            0.30,   # Practice injuries
    "off_field":           0.20,   # Non-sport issues
}

_CATEGORY_CATALOG = {
    "on_field_contact":    _ON_FIELD_CONTACT,
    "on_field_noncontact": _ON_FIELD_NONCONTACT,
    "practice":            _PRACTICE_INJURY,
    "off_field":           _OFF_FIELD,
}

# In-game injury category weights (only physical categories apply mid-game)
IN_GAME_CATEGORY_WEIGHTS = {
    "on_field_contact":    0.65,
    "on_field_noncontact": 0.35,
}


# ──────────────────────────────────────────────────────────────
# TIER DISTRIBUTION
# ──────────────────────────────────────────────────────────────

# Weekly between-game tier probabilities
WEEKLY_TIER_WEIGHTS = {
    "day_to_day": 0.40,
    "minor":      0.30,
    "moderate":   0.18,
    "major":      0.08,
    "severe":     0.04,
}

# In-game tier probabilities (skew toward less severe — most in-game
# injuries are minor, the serious ones are rarer)
IN_GAME_TIER_WEIGHTS = {
    "day_to_day": 0.50,
    "minor":      0.28,
    "moderate":   0.14,
    "major":      0.05,
    "severe":     0.03,
}


# ──────────────────────────────────────────────────────────────
# POSITION INJURY RISK — Base weekly probability per position
# ──────────────────────────────────────────────────────────────

_BASE_INJURY_PROB = {
    "Viper":           0.032,   # High-touch, but agile players avoid worst hits
    "Zeroback":        0.030,   # Kicking specialists — leg/foot stress
    "Halfback":        0.038,   # Heavy contact, ball carriers
    "Wingback":        0.036,   # Speed players, soft tissue risk
    "Slotback":        0.033,   # Route runners, moderate contact
    "Keeper":          0.028,   # Last line of defense, less frequent contact
    "Offensive Line":  0.040,   # Trench warfare, most contact per play
    "Defensive Line":  0.038,   # Same
    "default":         0.032,
}

# In-game injury probability per play for involved players
# Scales by play type violence
IN_GAME_INJURY_RATE = {
    "run":         0.004,   # ~0.4% per play for ball carrier
    "lateral":     0.003,   # Slightly less — more evasive
    "kick_pass":   0.002,   # Kicker has low risk, receiver moderate
    "punt":        0.002,   # Returner risk
    "drop_kick":   0.002,
    "tackle":      0.003,   # Tackler risk
    "default":     0.002,
}

# Position groups that can substitute for each other
POSITION_FLEXIBILITY = {
    "Viper":          ["Viper", "Wingback", "Halfback"],
    "Zeroback":       ["Zeroback", "Slotback", "Halfback"],
    "Halfback":       ["Halfback", "Wingback", "Slotback"],
    "Wingback":       ["Wingback", "Halfback", "Slotback"],
    "Slotback":       ["Slotback", "Wingback", "Halfback"],
    "Keeper":         ["Keeper", "Defensive Line"],
    "Offensive Line": ["Offensive Line", "Defensive Line"],
    "Defensive Line": ["Defensive Line", "Offensive Line"],
}

# Stat penalty when playing out of position
OUT_OF_POSITION_PENALTY = 0.85  # 15% reduction in effective stats


# ──────────────────────────────────────────────────────────────
# INJURY DATACLASS
# ──────────────────────────────────────────────────────────────

@dataclass
class Injury:
    """A single player injury or availability issue."""
    player_name: str
    team_name: str
    position: str
    tier: str                   # "day_to_day" | "minor" | "moderate" | "major" | "severe"
    category: str               # "on_field_contact" | "on_field_noncontact" | "practice" | "off_field"
    description: str
    body_part: str              # "knee", "ankle", "n/a" for off-field, etc.
    week_injured: int
    weeks_out: int              # 0 for DTD who play through, 99 for season-ending
    week_return: int            # week player is available again; 9999 = season-ending
    in_game: bool = False       # True if this happened during a game

    @property
    def is_season_ending(self) -> bool:
        return self.weeks_out >= 99

    @property
    def is_day_to_day(self) -> bool:
        return self.tier == "day_to_day"

    @property
    def is_off_field(self) -> bool:
        return self.category == "off_field"

    @property
    def display(self) -> str:
        tag = ""
        if self.is_season_ending:
            tag = " [OUT FOR SEASON]"
        elif self.is_day_to_day:
            tag = " [DAY-TO-DAY]"
        else:
            tag = f" [OUT {self.weeks_out} wk(s)]"
        prefix = ""
        if self.in_game:
            prefix = "(in-game) "
        return f"{self.player_name} ({self.position}) — {prefix}{self.description}{tag}"

    @property
    def game_status(self) -> str:
        """Return game-day status label."""
        if self.is_season_ending:
            return "OUT"
        if self.tier == "major":
            return "OUT"
        if self.tier == "moderate":
            return "OUT"
        if self.tier == "minor":
            return "DOUBTFUL"
        if self.tier == "day_to_day":
            return "QUESTIONABLE"
        return "OUT"

    def to_dict(self) -> dict:
        return {
            "player_name": self.player_name,
            "team_name": self.team_name,
            "position": self.position,
            "tier": self.tier,
            "category": self.category,
            "description": self.description,
            "body_part": self.body_part,
            "week_injured": self.week_injured,
            "weeks_out": self.weeks_out,
            "week_return": self.week_return,
            "is_season_ending": self.is_season_ending,
            "in_game": self.in_game,
            "game_status": self.game_status,
        }


# ──────────────────────────────────────────────────────────────
# IN-GAME INJURY EVENT (returned to game engine)
# ──────────────────────────────────────────────────────────────

@dataclass
class InGameInjuryEvent:
    """Describes an injury that just occurred during a play."""
    player_name: str
    position: str
    description: str
    tier: str
    category: str
    is_season_ending: bool
    substitute_name: Optional[str] = None
    substitute_position: Optional[str] = None
    is_out_of_position: bool = False

    @property
    def narrative(self) -> str:
        severity = "OUT FOR SEASON" if self.is_season_ending else self.tier.replace("_", "-").upper()
        line = f"INJURY: {self.player_name} ({self.position}) — {self.description} [{severity}]"
        if self.substitute_name:
            oop = " (out of position)" if self.is_out_of_position else ""
            line += f" | SUB IN: {self.substitute_name} ({self.substitute_position}){oop}"
        return line


# ──────────────────────────────────────────────────────────────
# INJURY TRACKER
# ──────────────────────────────────────────────────────────────

@dataclass
class InjuryTracker:
    """
    Manages all injuries and availability across a season.

    active_injuries: team_name -> list of active Injury objects
    season_log: full history of every injury/issue this season
    """
    active_injuries: Dict[str, List[Injury]] = field(default_factory=dict)
    season_log: List[Injury] = field(default_factory=list)
    rng: random.Random = field(default_factory=random.Random)

    def seed(self, s: int):
        self.rng.seed(s)

    # ── Tier / Category rolling ──────────────────────────

    def _roll_tier(self, weights: Dict[str, float] = None) -> str:
        """Roll an injury tier using weighted probabilities."""
        w = weights or WEEKLY_TIER_WEIGHTS
        tiers = list(w.keys())
        probs = list(w.values())
        return self.rng.choices(tiers, weights=probs, k=1)[0]

    def _roll_category(self, weights: Dict[str, float] = None) -> str:
        """Roll which injury category (contact, non-contact, practice, off-field)."""
        w = weights or WEEKLY_CATEGORY_WEIGHTS
        cats = list(w.keys())
        probs = list(w.values())
        return self.rng.choices(cats, weights=probs, k=1)[0]

    def _pick_flavor(self, category: str, tier: str) -> Tuple[str, str]:
        """Pick a specific injury description and body part from the catalog."""
        catalog = _CATEGORY_CATALOG.get(category, _ON_FIELD_CONTACT)
        tier_entries = catalog.get(tier, catalog.get("minor", []))
        if not tier_entries:
            tier_entries = [{"desc": "undisclosed injury", "body": "undisclosed"}]
        entry = self.rng.choice(tier_entries)
        return entry["desc"], entry["body"]

    # ── Base probability ─────────────────────────────────

    def _base_prob_for_position(self, position: str) -> float:
        return _BASE_INJURY_PROB.get(position, _BASE_INJURY_PROB["default"])

    # ── Create an injury ─────────────────────────────────

    def _make_injury(self, player, team_name: str, week: int,
                     category: str = None, tier: str = None,
                     in_game: bool = False) -> Injury:
        if tier is None:
            tier_weights = IN_GAME_TIER_WEIGHTS if in_game else WEEKLY_TIER_WEIGHTS
            tier = self._roll_tier(tier_weights)
        if category is None:
            cat_weights = IN_GAME_CATEGORY_WEIGHTS if in_game else WEEKLY_CATEGORY_WEIGHTS
            category = self._roll_category(cat_weights)

        description, body_part = self._pick_flavor(category, tier)
        week_range = INJURY_TIER_WEEKS[tier]

        if tier == "severe":
            weeks_out = 99
            week_return = 9999
        elif tier == "day_to_day":
            # DTD: 50% chance they miss 0 games, 50% chance they miss 1
            weeks_out = self.rng.choice([0, 1])
            week_return = week + weeks_out
        else:
            weeks_out = self.rng.randint(week_range[0], week_range[1])
            week_return = week + weeks_out

        return Injury(
            player_name=player.name,
            team_name=team_name,
            position=player.position,
            tier=tier,
            category=category,
            description=description,
            body_part=body_part,
            week_injured=week,
            weeks_out=weeks_out,
            week_return=week_return,
            in_game=in_game,
        )

    # ── Weekly processing (between games) ────────────────

    def process_week(self, week: int, teams: Dict, standings: Dict = None) -> List[Injury]:
        """
        Roll for new injuries/availability issues at the start of a week.

        Probability modified by:
        - Player stamina (lower = higher risk)
        - Season fatigue (more games played = higher risk)
        - Position (linemen/backs at higher risk)

        Returns list of new injuries this week.
        """
        new_injuries: List[Injury] = []

        for team_name, team in teams.items():
            if team_name not in self.active_injuries:
                self.active_injuries[team_name] = []

            current_active = [
                inj for inj in self.active_injuries[team_name]
                if week < inj.week_return
            ]
            already_out = {inj.player_name for inj in current_active}

            games_played = 0
            if standings and team_name in standings:
                games_played = standings[team_name].games_played

            fatigue_mult = 1.0 + min(0.3, games_played * 0.02)

            for player in team.players:
                if player.name in already_out:
                    continue

                base_prob = self._base_prob_for_position(player.position)
                stamina_mod = max(0.5, (100 - player.stamina) / 100.0) * 0.5
                prob = base_prob * (1.0 + stamina_mod) * fatigue_mult

                if self.rng.random() < prob:
                    injury = self._make_injury(player, team_name, week)
                    self.active_injuries[team_name].append(injury)
                    self.season_log.append(injury)
                    new_injuries.append(injury)

        return new_injuries

    def resolve_week(self, week: int):
        """Remove players who have returned from injury."""
        for team_name in list(self.active_injuries.keys()):
            self.active_injuries[team_name] = [
                inj for inj in self.active_injuries[team_name]
                if inj.week_return > week
            ]

    # ── In-game injury roll ──────────────────────────────

    def roll_in_game_injury(self, player, team_name: str, week: int,
                            play_type: str = "default") -> Optional[Injury]:
        """
        Roll for an in-game injury on a specific player after a play.

        Returns an Injury if the player got hurt, None otherwise.
        Called by the game engine after contact plays.
        """
        rate = IN_GAME_INJURY_RATE.get(play_type, IN_GAME_INJURY_RATE["default"])

        # Fatigue increases in-game injury risk
        current_stamina = getattr(player, 'current_stamina', 100.0)
        if current_stamina < 50:
            rate *= 1.5
        elif current_stamina < 70:
            rate *= 1.2

        # Low base stamina attribute = more fragile
        base_stamina = getattr(player, 'stamina', 75)
        if base_stamina < 65:
            rate *= 1.3
        elif base_stamina > 85:
            rate *= 0.8

        if self.rng.random() < rate:
            injury = self._make_injury(player, team_name, week, in_game=True)
            self.active_injuries.setdefault(team_name, []).append(injury)
            self.season_log.append(injury)
            return injury

        return None

    # ── Query methods ────────────────────────────────────

    def get_active_injuries(self, team_name: str, week: int) -> List[Injury]:
        """Return currently active injuries for a team at a given week."""
        return [
            inj for inj in self.active_injuries.get(team_name, [])
            if week < inj.week_return
        ]

    def get_unavailable_names(self, team_name: str, week: int) -> Set[str]:
        """Return set of player names who cannot play this week.

        DTD players with weeks_out=0 are NOT included (they play through it).
        """
        names = set()
        for inj in self.get_active_injuries(team_name, week):
            if inj.weeks_out > 0:
                names.add(inj.player_name)
        return names

    def get_dtd_names(self, team_name: str, week: int) -> Set[str]:
        """Return set of player names who are day-to-day (playing through injury)."""
        names = set()
        for inj in self.get_active_injuries(team_name, week):
            if inj.is_day_to_day and inj.weeks_out == 0:
                names.add(inj.player_name)
        return names

    def get_team_injury_penalties(self, team_name: str, week: int) -> Dict[str, float]:
        """
        Return performance penalty modifiers for a team due to injuries.

        Returns dict with keys:
            "yards_penalty"   – multiplicative modifier (e.g. 0.95 = 5% reduction)
            "kick_penalty"    – modifier for kicking effectiveness
            "lateral_penalty" – modifier for lateral chain success
        """
        active = self.get_active_injuries(team_name, week)
        if not active:
            return {"yards_penalty": 1.0, "kick_penalty": 1.0, "lateral_penalty": 1.0}

        total_penalty = 0.0
        kick_penalty = 0.0
        lateral_penalty = 0.0

        for inj in active:
            sev = INJURY_SEVERITY_PENALTY[inj.tier]
            total_penalty += sev

            pos = inj.position.lower()
            if "zero" in pos or "safety" in pos:
                kick_penalty += sev * 0.6
            if "viper" in pos or "halfback" in pos or "wingback" in pos:
                lateral_penalty += sev * 0.5

        return {
            "yards_penalty": round(1.0 - total_penalty, 3),
            "kick_penalty": round(1.0 - kick_penalty, 3),
            "lateral_penalty": round(1.0 - lateral_penalty, 3),
        }

    # ── Reporting ────────────────────────────────────────

    def get_season_injury_report(self) -> Dict[str, List[dict]]:
        """Return all injuries by team for a season summary."""
        report: Dict[str, List[dict]] = {}
        for inj in self.season_log:
            report.setdefault(inj.team_name, []).append(inj.to_dict())
        return report

    def get_season_injury_counts(self) -> Dict[str, int]:
        """Return total injury count per team for the season."""
        counts: Dict[str, int] = {}
        for inj in self.season_log:
            counts[inj.team_name] = counts.get(inj.team_name, 0) + 1
        return counts

    def get_injury_report_by_category(self) -> Dict[str, Dict[str, int]]:
        """Return injury counts broken down by category for each team."""
        report: Dict[str, Dict[str, int]] = {}
        for inj in self.season_log:
            team_cats = report.setdefault(inj.team_name, {})
            team_cats[inj.category] = team_cats.get(inj.category, 0) + 1
        return report

    def display_injury_report(self, team_name: str, week: int):
        """Print a human-readable injury report for a team."""
        active = self.get_active_injuries(team_name, week)
        if not active:
            print(f"  {team_name}: No active injuries")
            return
        print(f"\n  {team_name} INJURY REPORT (Week {week})")
        print(f"  {'-' * 60}")
        for inj in sorted(active, key=lambda i: ("OUT" if i.tier != "day_to_day" else "DTD", i.player_name)):
            print(f"    [{inj.game_status:12s}] {inj.display}")


# ──────────────────────────────────────────────────────────────
# SUBSTITUTION SYSTEM
# ──────────────────────────────────────────────────────────────

def find_substitute(team_players: List, injured_player, unavailable_names: Set[str],
                    injured_in_game: Set[str] = None) -> Tuple[Optional[object], bool]:
    """
    Find the best available substitute for an injured player.

    Search order:
    1. Same position, best overall rating
    2. Flexible position (from POSITION_FLEXIBILITY), best overall
    3. Any available player

    Returns:
        (substitute_player, is_out_of_position)
        (None, False) if no substitute available
    """
    if injured_in_game is None:
        injured_in_game = set()

    excluded = unavailable_names | injured_in_game | {injured_player.name}
    available = [p for p in team_players if p.name not in excluded]

    if not available:
        return None, False

    pos = injured_player.position
    flex_chain = POSITION_FLEXIBILITY.get(pos, [pos])

    def _player_overall(p):
        return getattr(p, 'overall', (p.speed + p.stamina + p.kicking + p.lateral_skill + p.tackling) / 5)

    # 1. Same position
    same_pos = [p for p in available if p.position == pos]
    if same_pos:
        return max(same_pos, key=_player_overall), False

    # 2. Flexible positions
    for flex_pos in flex_chain[1:]:
        flex_candidates = [p for p in available if p.position == flex_pos]
        if flex_candidates:
            return max(flex_candidates, key=_player_overall), True

    # 3. Any available player (emergency — way out of position)
    return max(available, key=_player_overall), True


def filter_available_players(team_players: List, unavailable_names: Set[str],
                             dtd_names: Set[str] = None) -> List:
    """
    Return the list of players available for a game, filtering out
    injured/unavailable players. DTD players are included but with
    a flag set for reduced performance.

    This should be called before passing a team to the game engine.
    """
    dtd = dtd_names or set()
    available = []
    for p in team_players:
        if p.name in unavailable_names:
            continue
        if p.name in dtd:
            p._is_dtd = True
        available.append(p)
    return available
