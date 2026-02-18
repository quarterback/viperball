"""
Viperball Injury System

Tracks player injuries across a season:
- Three tiers: Minor (1-2 weeks), Moderate (3-4 weeks), Severe (season-ending)
- Injury probability driven by stamina, position, and weekly game load
- Team-level performance penalty applied when key players are out
- Integrated into Dynasty.advance_season() for cross-season tracking

Usage:
    tracker = InjuryTracker()
    new_injuries = tracker.process_week(week_number, teams_dict, season_standings)
    penalties = tracker.get_team_injury_penalties("MIT")
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# INJURY TIERS
# ──────────────────────────────────────────────

INJURY_TIER_WEEKS = {
    "minor":    (1, 2),
    "moderate": (3, 4),
    "severe":   (99, 99),   # out for season
}

# How much of the team's effective OVR drops per injured player by tier
INJURY_SEVERITY_PENALTY = {
    "minor":    0.03,
    "moderate": 0.07,
    "severe":   0.12,
}

# Injury descriptions by body region
_INJURY_FLAVORS = {
    "minor": [
        "sprained ankle", "bruised ribs", "strained hamstring",
        "minor shoulder sprain", "finger jam",
    ],
    "moderate": [
        "pulled hamstring", "MCL sprain", "shoulder separation",
        "deep thigh bruise", "groin strain",
    ],
    "severe": [
        "ACL tear", "broken leg", "dislocated shoulder (season-ending)",
        "fractured collarbone", "severe knee injury",
    ],
}

# Base weekly injury probability per player by position group
_BASE_INJURY_PROB = {
    "Offensive Line":  0.040,
    "Defensive Line":  0.038,
    "Zeroback": 0.030,
    "Halfback": 0.035,
    "Wingback": 0.035,
    "Slotback": 0.033,
    "Viper":    0.028,
    "Keeper":   0.025,
    "default":  0.032,
}


# ──────────────────────────────────────────────
# INJURY DATACLASS
# ──────────────────────────────────────────────

@dataclass
class Injury:
    """A single player injury."""
    player_name: str
    team_name: str
    position: str
    tier: str                   # "minor" | "moderate" | "severe"
    description: str
    week_injured: int
    weeks_out: int              # 99 = season-ending
    week_return: int            # week player is available again; 9999 = season-ending

    @property
    def is_season_ending(self) -> bool:
        return self.weeks_out >= 99

    @property
    def display(self) -> str:
        if self.is_season_ending:
            return f"{self.player_name} ({self.position}) — {self.description} [OUT FOR SEASON]"
        return f"{self.player_name} ({self.position}) — {self.description} [{self.weeks_out} wk(s)]"

    def to_dict(self) -> dict:
        return {
            "player_name": self.player_name,
            "team_name": self.team_name,
            "position": self.position,
            "tier": self.tier,
            "description": self.description,
            "week_injured": self.week_injured,
            "weeks_out": self.weeks_out,
            "week_return": self.week_return,
            "is_season_ending": self.is_season_ending,
        }


# ──────────────────────────────────────────────
# INJURY TRACKER
# ──────────────────────────────────────────────

@dataclass
class InjuryTracker:
    """
    Manages all injuries across a season.

    active_injuries: team_name -> list of active Injury objects
    season_log: full history of every injury this season
    """
    active_injuries: Dict[str, List[Injury]] = field(default_factory=dict)
    season_log: List[Injury] = field(default_factory=list)
    rng: random.Random = field(default_factory=random.Random)

    def seed(self, s: int):
        self.rng.seed(s)

    def _base_prob_for_position(self, position: str) -> float:
        if position in _BASE_INJURY_PROB:
            return _BASE_INJURY_PROB[position]
        return _BASE_INJURY_PROB["default"]

    def _roll_tier(self) -> str:
        """Roll an injury tier: 60% minor, 28% moderate, 12% severe."""
        r = self.rng.random()
        if r < 0.60:
            return "minor"
        elif r < 0.88:
            return "moderate"
        else:
            return "severe"

    def _make_injury(self, player, team_name: str, week: int) -> Injury:
        tier = self._roll_tier()
        description = self.rng.choice(_INJURY_FLAVORS[tier])
        week_range = INJURY_TIER_WEEKS[tier]
        if tier == "severe":
            weeks_out = 99
            week_return = 9999
        else:
            weeks_out = self.rng.randint(week_range[0], week_range[1])
            week_return = week + weeks_out

        return Injury(
            player_name=player.name,
            team_name=team_name,
            position=player.position,
            tier=tier,
            description=description,
            week_injured=week,
            weeks_out=weeks_out,
            week_return=week_return,
        )

    def process_week(self, week: int, teams: Dict, standings: Dict = None) -> List[Injury]:
        """
        Roll for new injuries at the start of a week.

        Each player has a small chance of getting injured, modified by:
        - Their stamina attribute (lower stamina = higher injury risk)
        - A small boost if the team has played many games (fatigue accumulation)

        Returns a list of newly injured players.
        """
        new_injuries: List[Injury] = []

        for team_name, team in teams.items():
            if team_name not in self.active_injuries:
                self.active_injuries[team_name] = []

            # Count already-active injuries to avoid piling on
            current_active = [
                inj for inj in self.active_injuries[team_name]
                if week < inj.week_return
            ]
            already_out = {inj.player_name for inj in current_active}

            games_played = 0
            if standings and team_name in standings:
                games_played = standings[team_name].games_played

            # Fatigue multiplier: ramps up slightly over the season
            fatigue_mult = 1.0 + min(0.3, games_played * 0.02)

            for player in team.players:
                if player.name in already_out:
                    continue

                base_prob = self._base_prob_for_position(player.position)

                # Lower stamina increases injury risk
                stamina_mod = max(0.5, (100 - player.stamina) / 100.0) * 0.5
                prob = base_prob * (1.0 + stamina_mod) * fatigue_mult

                # Cap at a sane weekly maximum
                prob = min(prob, 0.10)

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

    def get_active_injuries(self, team_name: str, week: int) -> List[Injury]:
        """Return currently active injuries for a team at a given week."""
        return [
            inj for inj in self.active_injuries.get(team_name, [])
            if week < inj.week_return
        ]

    def get_team_injury_penalties(self, team_name: str, week: int) -> Dict[str, float]:
        """
        Return performance penalty modifiers for a team due to injuries.

        Returns dict with keys:
            "yards_penalty"   – multiplicative reduction in yards gained (e.g. 0.95 = 5% reduction)
            "kick_penalty"    – multiplicative reduction in kicking effectiveness
            "lateral_penalty" – multiplicative reduction in lateral chain success
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

        # Cap penalties to avoid absurd situations
        yards_mult = max(0.65, 1.0 - min(0.35, total_penalty))
        kick_mult = max(0.70, 1.0 - min(0.30, kick_penalty))
        lat_mult = max(0.70, 1.0 - min(0.30, lateral_penalty))

        return {
            "yards_penalty": round(yards_mult, 3),
            "kick_penalty": round(kick_mult, 3),
            "lateral_penalty": round(lat_mult, 3),
        }

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

    def display_injury_report(self, team_name: str, week: int):
        """Print a human-readable injury report for a team."""
        active = self.get_active_injuries(team_name, week)
        if not active:
            print(f"  {team_name}: No active injuries")
            return
        print(f"\n  {team_name} INJURY REPORT (Week {week})")
        print(f"  {'-' * 50}")
        for inj in active:
            status = "OUT FOR SEASON" if inj.is_season_ending else f"OUT {inj.weeks_out} wk(s), RTN wk {inj.week_return}"
            print(f"    {inj.player_name} ({inj.position}) — {inj.description} [{status}]")
