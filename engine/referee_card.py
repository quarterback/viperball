"""
Referee Card System for Viperball

Sports-reference style referee profiles with game logs and career
tracking.  Refs are treated like players — they have a card, a game
log, season stats, and a career history.  Their hidden attributes
(accuracy, home favor, consistency) drive blown-call rates but are
never shown to the user.

Usage:
    from engine.referee_card import RefereeCard, RefereeGameLog, RefereePool

    pool = RefereePool(seed=42)
    pool.generate(360)     # 360 refs for a 205-team league

    # Assign a crew to a game
    crew = pool.assign_crew(rng, is_playoff=True)

    # After game, record the result
    pool.record_game(crew_names, game_log_data)

    # Look up a ref's profile
    card = pool.get_card("Marcus Bell")
"""

from __future__ import annotations

import random
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ──────────────────────────────────────────────────────────────
# REFEREE GAME LOG — single game stats for one referee
# ──────────────────────────────────────────────────────────────

@dataclass
class RefereeGameLog:
    """One game's stats for a referee."""
    week: int
    year: int = 0
    home_team: str = ""
    away_team: str = ""
    home_score: float = 0.0
    away_score: float = 0.0
    # Penalty stats
    penalties_called: int = 0
    penalty_yards: int = 0
    penalties_on_home: int = 0
    penalties_on_away: int = 0
    # Blown call stats
    blown_calls: int = 0
    phantom_flags: int = 0
    swallowed_whistles: int = 0
    spot_errors: int = 0
    # Challenge stats
    challenges_attempted: int = 0
    challenges_overturned: int = 0
    # Game context
    is_playoff: bool = False
    is_overtime: bool = False

    def to_dict(self) -> dict:
        return {
            "week": self.week,
            "year": self.year,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "penalties_called": self.penalties_called,
            "penalty_yards": self.penalty_yards,
            "penalties_on_home": self.penalties_on_home,
            "penalties_on_away": self.penalties_on_away,
            "blown_calls": self.blown_calls,
            "phantom_flags": self.phantom_flags,
            "swallowed_whistles": self.swallowed_whistles,
            "spot_errors": self.spot_errors,
            "challenges_attempted": self.challenges_attempted,
            "challenges_overturned": self.challenges_overturned,
            "is_playoff": self.is_playoff,
            "is_overtime": self.is_overtime,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RefereeGameLog":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ──────────────────────────────────────────────────────────────
# REFEREE SEASON STATS — aggregated across a season
# ──────────────────────────────────────────────────────────────

@dataclass
class RefereeSeasonStats:
    """Aggregated season stats for a referee."""
    year: int = 0
    games_officiated: int = 0
    total_penalties: int = 0
    total_penalty_yards: int = 0
    total_blown_calls: int = 0
    total_phantom_flags: int = 0
    total_swallowed_whistles: int = 0
    total_spot_errors: int = 0
    total_challenges: int = 0
    total_overturned: int = 0
    playoff_games: int = 0
    overtime_games: int = 0
    # Home/away penalty balance
    penalties_on_home: int = 0
    penalties_on_away: int = 0

    @property
    def penalties_per_game(self) -> float:
        return round(self.total_penalties / max(1, self.games_officiated), 1)

    @property
    def blown_calls_per_game(self) -> float:
        return round(self.total_blown_calls / max(1, self.games_officiated), 2)

    @property
    def challenge_overturn_pct(self) -> float:
        if self.total_challenges == 0:
            return 0.0
        return round(self.total_overturned / self.total_challenges * 100, 1)

    @property
    def home_penalty_pct(self) -> float:
        total = self.penalties_on_home + self.penalties_on_away
        if total == 0:
            return 50.0
        return round(self.penalties_on_home / total * 100, 1)

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "games_officiated": self.games_officiated,
            "total_penalties": self.total_penalties,
            "total_penalty_yards": self.total_penalty_yards,
            "penalties_per_game": self.penalties_per_game,
            "total_blown_calls": self.total_blown_calls,
            "blown_calls_per_game": self.blown_calls_per_game,
            "total_phantom_flags": self.total_phantom_flags,
            "total_swallowed_whistles": self.total_swallowed_whistles,
            "total_spot_errors": self.total_spot_errors,
            "total_challenges": self.total_challenges,
            "total_overturned": self.total_overturned,
            "challenge_overturn_pct": self.challenge_overturn_pct,
            "home_penalty_pct": self.home_penalty_pct,
            "playoff_games": self.playoff_games,
            "overtime_games": self.overtime_games,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RefereeSeasonStats":
        fields = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in fields})


# ──────────────────────────────────────────────────────────────
# REFEREE CARD — the full profile
# ──────────────────────────────────────────────────────────────

@dataclass
class RefereeCard:
    """
    Sports-reference style referee profile.

    Hidden attributes drive blown-call rates but are never exposed
    to the user.  The user sees the name, game log, and season stats.
    """

    # ── Identity ──
    referee_id: str
    first_name: str
    last_name: str

    # ── Hidden attributes (not shown in UI) ──
    accuracy: float = 0.95       # 0.905-0.98
    home_favor: float = 0.0      # -0.5 to +0.5
    consistency: float = 0.94    # 0.87-0.97

    # ── Visible profile ──
    years_experience: int = 0
    conference: str = ""         # Assigned conference (future)

    # ── Career tracking ──
    career_seasons: List[RefereeSeasonStats] = field(default_factory=list)
    game_log: List[RefereeGameLog] = field(default_factory=list)

    # ── Computed ──
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        return f"{self.first_name[0]}. {self.last_name}"

    @property
    def career_games(self) -> int:
        return sum(s.games_officiated for s in self.career_seasons)

    @property
    def career_blown_calls(self) -> int:
        return sum(s.total_blown_calls for s in self.career_seasons)

    @property
    def career_penalties_per_game(self) -> float:
        total_pen = sum(s.total_penalties for s in self.career_seasons)
        total_games = max(1, self.career_games)
        return round(total_pen / total_games, 1)

    @property
    def career_blown_calls_per_game(self) -> float:
        return round(self.career_blown_calls / max(1, self.career_games), 2)

    @property
    def career_playoff_games(self) -> int:
        return sum(s.playoff_games for s in self.career_seasons)

    @property
    def tier_label(self) -> str:
        """Human-readable quality tier based on accuracy (hidden from user)."""
        if self.accuracy >= 0.97:
            return "Elite"
        elif self.accuracy >= 0.95:
            return "Good"
        elif self.accuracy >= 0.93:
            return "Solid"
        elif self.accuracy >= 0.92:
            return "Average"
        else:
            return "Below Average"

    def add_game(self, game_log: RefereeGameLog, year: int = 0):
        """Record a game and update the current season stats."""
        game_log.year = year
        self.game_log.append(game_log)

        # Find or create current season stats
        current_season = None
        for s in self.career_seasons:
            if s.year == year:
                current_season = s
                break
        if current_season is None:
            current_season = RefereeSeasonStats(year=year)
            self.career_seasons.append(current_season)

        current_season.games_officiated += 1
        current_season.total_penalties += game_log.penalties_called
        current_season.total_penalty_yards += game_log.penalty_yards
        current_season.penalties_on_home += game_log.penalties_on_home
        current_season.penalties_on_away += game_log.penalties_on_away
        current_season.total_blown_calls += game_log.blown_calls
        current_season.total_phantom_flags += game_log.phantom_flags
        current_season.total_swallowed_whistles += game_log.swallowed_whistles
        current_season.total_spot_errors += game_log.spot_errors
        current_season.total_challenges += game_log.challenges_attempted
        current_season.total_overturned += game_log.challenges_overturned
        if game_log.is_playoff:
            current_season.playoff_games += 1
        if game_log.is_overtime:
            current_season.overtime_games += 1

    def to_dict(self) -> dict:
        return {
            "referee_id": self.referee_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "years_experience": self.years_experience,
            "conference": self.conference,
            "career_games": self.career_games,
            "career_penalties_per_game": self.career_penalties_per_game,
            "career_blown_calls": self.career_blown_calls,
            "career_blown_calls_per_game": self.career_blown_calls_per_game,
            "career_playoff_games": self.career_playoff_games,
            "career_seasons": [s.to_dict() for s in self.career_seasons],
            "game_log": [g.to_dict() for g in self.game_log],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RefereeCard":
        seasons = [RefereeSeasonStats.from_dict(s) for s in d.get("career_seasons", [])]
        games = [RefereeGameLog.from_dict(g) for g in d.get("game_log", [])]
        return cls(
            referee_id=d["referee_id"],
            first_name=d["first_name"],
            last_name=d["last_name"],
            accuracy=d.get("accuracy", 0.95),
            home_favor=d.get("home_favor", 0.0),
            consistency=d.get("consistency", 0.94),
            years_experience=d.get("years_experience", 0),
            conference=d.get("conference", ""),
            career_seasons=seasons,
            game_log=games,
        )


# ──────────────────────────────────────────────────────────────
# REFEREE POOL — manages all referees for a league
# ──────────────────────────────────────────────────────────────

# Accuracy/consistency tiers for assigning hidden attributes
_REF_TIERS = [
    # (weight, accuracy_lo, accuracy_hi, consistency_lo, consistency_hi)
    (0.10, 0.97, 0.98, 0.95, 0.97),   # elite
    (0.33, 0.95, 0.97, 0.93, 0.96),   # good
    (0.33, 0.93, 0.95, 0.91, 0.94),   # solid
    (0.17, 0.92, 0.93, 0.89, 0.92),   # average
    (0.07, 0.905, 0.92, 0.87, 0.90),  # below-average
]


class RefereePool:
    """Manages the full pool of referee cards for a league.

    Generates named refs with hidden attributes, groups them into
    3-person crews, tracks game logs, and provides lookup by name.
    """

    def __init__(self, seed: int = 12345):
        self.seed = seed
        self.cards: Dict[str, RefereeCard] = {}  # name -> card
        self._crews: List[List[str]] = []  # cached crew groupings

    def generate(self, count: int = 360):
        """Generate the referee pool using the name generator."""
        rng = random.Random(self.seed)

        try:
            from scripts.generate_names import generate_player_name
            use_generator = True
        except (ImportError, FileNotFoundError):
            use_generator = False

        # Build tier cumulative weights
        tier_cumulative = []
        cumsum = 0.0
        for weight, *_ in _REF_TIERS:
            cumsum += weight
            tier_cumulative.append(cumsum)

        used_names: set = set()
        for i in range(count):
            # Generate unique name
            if use_generator:
                for _attempt in range(10):
                    gender = rng.choice(["female", "male"])
                    name_data = generate_player_name(gender=gender)
                    full_name = name_data["full_name"]
                    if full_name not in used_names:
                        used_names.add(full_name)
                        break
                first_name = name_data["first_name"]
                last_name = name_data["last_name"]
            else:
                first_name = f"Ref"
                last_name = f"#{i + 1}"
                full_name = f"{first_name} {last_name}"

            # Assign tier
            roll = rng.random()
            tier_idx = 0
            for j, boundary in enumerate(tier_cumulative):
                if roll <= boundary:
                    tier_idx = j
                    break

            _, acc_lo, acc_hi, con_lo, con_hi = _REF_TIERS[tier_idx]
            accuracy = rng.uniform(acc_lo, acc_hi)
            consistency = rng.uniform(con_lo, con_hi)
            favor_spread = 0.04 + (1.0 - accuracy) * 0.8
            home_favor = max(-0.5, min(0.5, rng.gauss(0.03, favor_spread)))

            ref_id = f"ref_{first_name.lower().replace(' ', '_')}_{last_name.lower().replace(' ', '_')}_{rng.randint(1000, 9999)}"
            years_exp = rng.randint(1, 20)

            card = RefereeCard(
                referee_id=ref_id,
                first_name=first_name,
                last_name=last_name,
                accuracy=round(accuracy, 4),
                home_favor=round(home_favor, 3),
                consistency=round(consistency, 4),
                years_experience=years_exp,
            )
            self.cards[full_name] = card

        self._build_crews(rng)

    def _build_crews(self, rng: random.Random):
        """Group refs into 3-person crews."""
        names = list(self.cards.keys())
        rng.shuffle(names)
        self._crews = []
        for i in range(0, len(names) - 2, 3):
            trio = names[i:i + 3]
            # Sort by accuracy — head ref is the best
            trio.sort(key=lambda n: self.cards[n].accuracy, reverse=True)
            self._crews.append(trio)

    def assign_crew(self, rng: random.Random, is_playoff: bool = False) -> List[str]:
        """Pick a crew for a game. Playoff games get top-tier crews."""
        if not self._crews:
            return []

        if is_playoff:
            # Sort crews by average accuracy, pick from top third
            sorted_crews = sorted(
                self._crews,
                key=lambda c: sum(self.cards[n].accuracy for n in c) / len(c),
                reverse=True,
            )
            top = sorted_crews[:max(1, len(sorted_crews) // 3)]
            return rng.choice(top)
        else:
            return rng.choice(self._crews)

    def get_crew_accuracy(self, crew_names: List[str]) -> float:
        """Average accuracy of a crew."""
        accs = [self.cards[n].accuracy for n in crew_names if n in self.cards]
        return sum(accs) / max(1, len(accs))

    def get_crew_home_favor(self, crew_names: List[str]) -> float:
        """Average home favor of a crew."""
        favs = [self.cards[n].home_favor for n in crew_names if n in self.cards]
        return sum(favs) / max(1, len(favs))

    def get_crew_consistency(self, crew_names: List[str]) -> float:
        """Average consistency of a crew."""
        cons = [self.cards[n].consistency for n in crew_names if n in self.cards]
        return sum(cons) / max(1, len(cons))

    def record_game(self, crew_names: List[str], game_data: dict, year: int = 0):
        """Record a game result for all crew members."""
        ref_data = game_data.get("referee", {})
        blown_call_log = ref_data.get("blown_call_log", [])

        # Count blown call types
        phantom = sum(1 for bc in blown_call_log if bc.get("type") == "phantom_flag")
        swallowed = sum(1 for bc in blown_call_log if bc.get("type") == "swallowed_whistle")
        spot = sum(1 for bc in blown_call_log if bc.get("type") == "spot_error")

        # Count penalties from play-by-play
        plays = game_data.get("play_by_play", [])
        pen_count = 0
        pen_yards = 0
        pen_home = 0
        pen_away = 0
        for p in plays:
            pen = p.get("penalty")
            if pen and not pen.get("declined", False):
                pen_count += 1
                pen_yards += pen.get("yards", 0)
                if pen.get("on_team") == "home":
                    pen_home += 1
                else:
                    pen_away += 1

        final = game_data.get("final_score", {})
        home_score = final.get("home", {}).get("score", 0)
        away_score = final.get("away", {}).get("score", 0)
        home_team = final.get("home", {}).get("team", "")
        away_team = final.get("away", {}).get("team", "")

        # Determine if overtime occurred
        is_ot = any(p.get("quarter", 0) > 4 for p in plays)

        game_log = RefereeGameLog(
            week=game_data.get("week", 0),
            year=year,
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            penalties_called=pen_count,
            penalty_yards=pen_yards,
            penalties_on_home=pen_home,
            penalties_on_away=pen_away,
            blown_calls=ref_data.get("blown_calls", 0),
            phantom_flags=phantom,
            swallowed_whistles=swallowed,
            spot_errors=spot,
            challenges_attempted=ref_data.get("challenged_calls", 0),
            challenges_overturned=ref_data.get("overturned_calls", 0),
            is_playoff=game_data.get("week", 0) >= 900,
            is_overtime=is_ot,
        )

        for name in crew_names:
            card = self.cards.get(name)
            if card:
                card.add_game(game_log, year=year)

    def get_card(self, name: str) -> Optional[RefereeCard]:
        """Look up a referee by full name."""
        return self.cards.get(name)

    def get_all_cards(self) -> List[RefereeCard]:
        """All referee cards sorted by career games descending."""
        return sorted(self.cards.values(), key=lambda c: c.career_games, reverse=True)

    def to_dict(self) -> dict:
        """Serialize the entire pool for save files."""
        return {
            "seed": self.seed,
            "cards": {name: card.to_dict() for name, card in self.cards.items()},
            "crews": self._crews,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RefereePool":
        """Deserialize from a save file."""
        pool = cls(seed=d.get("seed", 12345))
        for name, card_data in d.get("cards", {}).items():
            pool.cards[name] = RefereeCard.from_dict(card_data)
        pool._crews = d.get("crews", [])
        return pool
