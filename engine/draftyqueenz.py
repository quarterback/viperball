"""
DraftyQueenz — Viperball's integrated prediction & weekly fantasy system.

Two modes that run side-by-side during a season:

  1. **Predictions** — Pick winners, spreads, over/unders, and Viperball
     metric props before each week's games.  Correct picks pay out DQ$.

  2. **Weekly Fantasy** — Draft a salary-capped roster of real players each
     week.  Player game stats map to fantasy points; top scores earn DQ$.

DQ$ is the universal currency.  It can be spent on *Booster Donations* that
feed back into the dynasty program (recruiting boost, development boost,
NIL top-up, retention bonus).

Works in both single-season and dynasty mode.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

STARTING_BANKROLL = 10_000
FANTASY_ENTRY_FEE = 500
MIN_BET = 100
MAX_BET = 2_000
MIN_DONATION = 1_000

# Fantasy roster slots  (position tag → how many)
ROSTER_SLOTS = {
    "VP": 1,     # Viper — premier playmaker
    "BALL": 2,   # Ball carrier — HB, ZB, WB, or SB
    "KP": 1,     # Keeper — defense / special teams
    "FLEX": 1,   # Any skill position
}
ROSTER_SIZE = sum(ROSTER_SLOTS.values())  # 5 starters
SALARY_CAP = 50_000

BALL_CARRIER_TAGS = {"HB", "ZB", "WB", "SB"}
FLEX_ELIGIBLE = {"VP", "HB", "ZB", "WB", "SB", "KP"}

# AI fantasy manager archetypes
AI_MANAGER_STYLES = ["stars_and_scrubs", "balanced", "contrarian", "chalk"]
AI_MANAGER_COUNT = 7  # compete against 7 AI managers each week

# Donation boost types and their dynasty effects
DONATION_TYPES = {
    "recruiting": {
        "label": "Recruiting Boost",
        "description": "Improve pipeline quality for next recruiting cycle",
        "per_1k": 0.5,   # +0.5 recruiting points per 1,000 DQ$
        "cap": 10.0,
    },
    "development": {
        "label": "Player Development",
        "description": "Extra coaching resources for offseason development",
        "per_1k": 0.3,
        "cap": 6.0,
    },
    "nil_topup": {
        "label": "NIL Top-Up",
        "description": "Inject extra NIL budget for portal/retention",
        "per_1k": 5_000,  # $5k real NIL per 1k DQ$
        "cap": 100_000,
    },
    "retention": {
        "label": "Retention Bonus",
        "description": "Reduce transfer portal attrition risk",
        "per_1k": 1.0,    # +1% retention modifier per 1k DQ$
        "cap": 15.0,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# FANTASY SCORING
# ═══════════════════════════════════════════════════════════════════════

SCORING_RULES = {
    # Offense
    "yards":              (1.0, 15),    # 1 pt per 15 yards
    "rushing_yards":      (0.5, 15),    # 0.5 bonus per 15 rushing yards (stacks with yards)
    "lateral_yards":      (1.0, 12),    # 1 pt per 12 lateral yards (premium)
    "tds":                9.0,
    "lateral_tds":        3.0,          # bonus on top of td points
    "laterals_thrown":    1.0,
    "lateral_receptions": 0.5,
    "lateral_assists":    0.75,
    "fumbles":           -3.0,
    # Kicking
    "kick_made":          4.0,
    "kick_att_miss":     -1.0,          # derived: att - made
    # Keeper / special teams
    "keeper_bells":       4.0,
    "kick_deflections":   3.0,
    "keeper_tackles":     2.0,
    "st_tackles":         1.5,
    "kick_return_yards":  (1.0, 20),
    "punt_return_yards":  (1.0, 15),
    "kick_return_tds":    9.0,
    "punt_return_tds":    9.0,
    "muffs":             -2.0,
}


def score_player(player_stats: Dict) -> float:
    """Calculate fantasy points for one player from their game stat dict.

    ``player_stats`` uses the same keys produced by
    ``ViperballEngine.generate_game_summary()`` → ``player_stats``.
    """
    pts = 0.0

    for stat_key, rule in SCORING_RULES.items():
        if stat_key == "kick_att_miss":
            # Derived: misses = attempts − makes
            misses = player_stats.get("kick_att", 0) - player_stats.get("kick_made", 0)
            pts += max(0, misses) * rule
            continue

        val = player_stats.get(stat_key, 0)
        if val == 0:
            continue

        if isinstance(rule, tuple):
            per_point, divisor = rule
            pts += (val / divisor) * per_point
        else:
            pts += val * rule

    return round(pts, 2)


# ═══════════════════════════════════════════════════════════════════════
# SALARY / PLAYER POOL
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class FantasyPlayer:
    """A player available in the weekly fantasy pool."""
    tag: str           # e.g. "VP1"
    name: str
    team_name: str
    position_tag: str  # VP, HB, ZB, WB, SB, KP
    overall: int
    salary: int
    projected_pts: float = 0.0
    actual_pts: float = 0.0


def _position_tag_from_full(tag: str) -> str:
    """Extract position letters from a player tag like 'VP1' → 'VP'."""
    return "".join(c for c in tag if c.isalpha())


def _salary_for_player(overall: int, position_tag: str) -> int:
    """Compute weekly salary from overall rating and position.

    VP commands a premium; KP gets a discount.  Values range ~4k–15k so
    that a 50k cap forces real trade-offs.
    """
    base = 3_000 + int((overall / 100) * 10_000)
    multiplier = {
        "VP": 1.25,
        "HB": 1.05,
        "ZB": 1.10,
        "WB": 1.00,
        "SB": 0.95,
        "KP": 0.85,
    }.get(position_tag, 1.0)
    return int(base * multiplier / 500) * 500  # round to nearest 500


def build_player_pool(teams: Dict, week_schedule: list) -> List[FantasyPlayer]:
    """Build the weekly fantasy player pool from teams playing this week.

    Only includes players from teams that have a game scheduled this week.
    ``teams`` maps team name → Team object.
    ``week_schedule`` is a list of Game objects for this week.
    """
    playing_teams = set()
    for game in week_schedule:
        playing_teams.add(game.home_team)
        playing_teams.add(game.away_team)

    pool: List[FantasyPlayer] = []
    for tname in sorted(playing_teams):
        team = teams.get(tname)
        if team is None:
            continue
        for p in team.players:
            from engine.game_engine import player_tag, POSITION_TAGS
            ptag = player_tag(p)
            pos_tag = _position_tag_from_full(ptag)
            if pos_tag not in FLEX_ELIGIBLE:
                continue  # skip OL/DL — they don't accumulate individual stats
            salary = _salary_for_player(p.overall, pos_tag)
            pool.append(FantasyPlayer(
                tag=ptag,
                name=p.name,
                team_name=tname,
                position_tag=pos_tag,
                overall=p.overall,
                salary=salary,
            ))
    return sorted(pool, key=lambda fp: fp.salary, reverse=True)


def project_player_points(fp: FantasyPlayer, team_prestige: int) -> float:
    """Rough pre-game projection for AI roster building.

    Higher overall + higher prestige team = higher projection.
    """
    base = (fp.overall / 100) * 12  # max ~12 pts baseline
    prestige_bonus = (team_prestige / 100) * 3
    position_bonus = {"VP": 2.0, "HB": 1.0, "ZB": 1.5, "WB": 0.5, "SB": 0.5, "KP": 1.0}.get(fp.position_tag, 0)
    noise = random.gauss(0, 1.5)
    return max(0, round(base + prestige_bonus + position_bonus + noise, 2))


# ═══════════════════════════════════════════════════════════════════════
# ROSTER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class FantasyRoster:
    """A weekly fantasy lineup."""
    manager_name: str
    entries: Dict[str, FantasyPlayer] = field(default_factory=dict)
    # slot keys: "VP", "BALL1", "BALL2", "KP", "FLEX"

    @property
    def total_salary(self) -> int:
        return sum(fp.salary for fp in self.entries.values())

    @property
    def total_points(self) -> float:
        return sum(fp.actual_pts for fp in self.entries.values())

    @property
    def is_valid(self) -> bool:
        if len(self.entries) != ROSTER_SIZE:
            return False
        if self.total_salary > SALARY_CAP:
            return False
        return True

    def slot_keys(self) -> List[str]:
        return ["VP", "BALL1", "BALL2", "KP", "FLEX"]

    def set_slot(self, slot: str, player: FantasyPlayer) -> str:
        """Assign a player to a slot.  Returns error message or empty string."""
        valid_slots = self.slot_keys()
        if slot not in valid_slots:
            return f"Invalid slot '{slot}'. Valid: {valid_slots}"

        # Position eligibility
        if slot == "VP" and player.position_tag != "VP":
            return f"{player.name} ({player.position_tag}) cannot fill the VP slot."
        if slot.startswith("BALL") and player.position_tag not in BALL_CARRIER_TAGS:
            return f"{player.name} ({player.position_tag}) cannot fill a BALL slot."
        if slot == "KP" and player.position_tag != "KP":
            return f"{player.name} ({player.position_tag}) cannot fill the KP slot."
        if slot == "FLEX" and player.position_tag not in FLEX_ELIGIBLE:
            return f"{player.name} ({player.position_tag}) is not flex-eligible."

        # Duplicate check
        for s, existing in self.entries.items():
            if s != slot and existing.tag == player.tag and existing.team_name == player.team_name:
                return f"{player.name} is already in slot {s}."

        self.entries[slot] = player

        if self.total_salary > SALARY_CAP:
            del self.entries[slot]
            return f"Adding {player.name} (${player.salary:,}) would exceed the ${SALARY_CAP:,} salary cap."

        return ""

    def clear_slot(self, slot: str):
        self.entries.pop(slot, None)

    def to_dict(self) -> Dict:
        return {
            "manager": self.manager_name,
            "entries": {
                slot: {
                    "tag": fp.tag,
                    "name": fp.name,
                    "team": fp.team_name,
                    "position": fp.position_tag,
                    "salary": fp.salary,
                    "points": fp.actual_pts,
                }
                for slot, fp in self.entries.items()
            },
            "total_salary": self.total_salary,
            "total_points": self.total_points,
        }


def build_ai_roster(
    style: str,
    pool: List[FantasyPlayer],
    team_prestige: Dict[str, int],
    rng: Optional[random.Random] = None,
) -> FantasyRoster:
    """Build an AI manager's roster using a given strategy style."""
    rng = rng or random.Random()
    roster = FantasyRoster(manager_name=f"AI-{style.title()}")

    # Give each player a projected score for sorting
    scored = []
    for fp in pool:
        proj = project_player_points(fp, team_prestige.get(fp.team_name, 50))
        scored.append((fp, proj))

    if style == "stars_and_scrubs":
        scored.sort(key=lambda x: x[1], reverse=True)
    elif style == "contrarian":
        scored.sort(key=lambda x: x[1])  # pick lower-projected first
    elif style == "chalk":
        scored.sort(key=lambda x: x[0].overall, reverse=True)
    else:  # balanced
        rng.shuffle(scored)

    # Greedy fill by slot order
    used_tags = set()
    for slot in roster.slot_keys():
        for fp, proj in scored:
            key = (fp.tag, fp.team_name)
            if key in used_tags:
                continue
            err = roster.set_slot(slot, fp)
            if not err:
                used_tags.add(key)
                break

    return roster


# ═══════════════════════════════════════════════════════════════════════
# PREDICTIONS / ODDS
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class GameOdds:
    """Pre-game odds for a single matchup."""
    home_team: str
    away_team: str
    home_win_prob: float       # 0.0–1.0
    spread: float              # negative = home favored
    over_under: float          # total points line
    home_moneyline: int        # American odds
    away_moneyline: int
    chaos_ou: float            # Chaos Factor over/under

    def to_dict(self) -> Dict:
        return {
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_win_prob": round(self.home_win_prob, 3),
            "spread": self.spread,
            "over_under": self.over_under,
            "home_moneyline": self.home_moneyline,
            "away_moneyline": self.away_moneyline,
            "chaos_ou": self.chaos_ou,
        }


def _prob_to_american(prob: float) -> int:
    """Convert implied probability to American-style moneyline."""
    prob = max(0.05, min(0.95, prob))
    if prob >= 0.5:
        return int(-100 * prob / (1 - prob))
    else:
        return int(100 * (1 - prob) / prob)


def generate_game_odds(
    home_team_name: str,
    away_team_name: str,
    home_prestige: int,
    away_prestige: int,
    home_record: Optional[Tuple[int, int]] = None,
    away_record: Optional[Tuple[int, int]] = None,
    rng: Optional[random.Random] = None,
) -> GameOdds:
    """Generate betting odds for a matchup.

    Uses prestige gap + home-field advantage + season record to estimate
    win probability, then derives spread, total, and moneyline.
    """
    rng = rng or random.Random()

    # Base win probability from prestige gap
    gap = home_prestige - away_prestige
    home_advantage = 3.0  # ~3 prestige points of home-field edge
    adjusted_gap = gap + home_advantage

    # Sigmoid to get probability (steepness tuned so ±30 prestige ≈ 85/15)
    home_prob = 1.0 / (1.0 + math.exp(-adjusted_gap / 12.0))

    # Adjust for in-season record if available
    if home_record and away_record:
        hw, hl = home_record
        aw, al = away_record
        home_wp = hw / max(1, hw + hl)
        away_wp = aw / max(1, aw + al)
        record_edge = (home_wp - away_wp) * 0.15
        home_prob = max(0.05, min(0.95, home_prob + record_edge))

    # Spread: positive = away favored, negative = home favored
    # Roughly 1 point of spread per 2% probability edge
    spread = round(-(home_prob - 0.5) * 50, 1)

    # Over/under: base ~30 points, adjusted by combined prestige
    avg_prestige = (home_prestige + away_prestige) / 2
    base_total = 26 + (avg_prestige / 100) * 12
    total = round(base_total + rng.gauss(0, 1.5), 1)

    # Chaos factor over/under (higher prestige gap = more chaos potential)
    chaos_base = 40 + abs(gap) * 0.3 + rng.gauss(0, 3)
    chaos_ou = round(max(20, min(80, chaos_base)), 1)

    return GameOdds(
        home_team=home_team_name,
        away_team=away_team_name,
        home_win_prob=home_prob,
        spread=spread,
        over_under=total,
        home_moneyline=_prob_to_american(home_prob),
        away_moneyline=_prob_to_american(1 - home_prob),
        chaos_ou=chaos_ou,
    )


# ── Pick types ──

@dataclass
class Pick:
    """A single prediction bet."""
    pick_type: str         # "winner", "spread", "over_under", "chaos"
    game_home: str
    game_away: str
    selection: str         # team name, "over", "under"
    amount: int            # DQ$ wagered
    odds_snapshot: Dict    # copy of GameOdds.to_dict() at time of pick
    payout: float = 0.0    # filled after resolution
    result: str = ""       # "win", "loss", "push"

    def to_dict(self) -> Dict:
        return {
            "pick_type": self.pick_type,
            "matchup": f"{self.game_away} @ {self.game_home}",
            "selection": self.selection,
            "amount": self.amount,
            "payout": self.payout,
            "result": self.result,
        }


def resolve_pick(pick: Pick, game_result: Dict) -> Pick:
    """Resolve a pick against a completed game result.

    ``game_result`` is the dict returned by ``ViperballEngine.generate_game_summary()``.
    """
    home_score = game_result["final_score"]["home"]["score"]
    away_score = game_result["final_score"]["away"]["score"]
    home_team = game_result["final_score"]["home"]["team"]
    away_team = game_result["final_score"]["away"]["team"]
    margin = home_score - away_score

    if pick.pick_type == "winner":
        if pick.selection == home_team:
            won = home_score > away_score
        else:
            won = away_score > home_score
        # Payout uses moneyline odds
        if won:
            ml = pick.odds_snapshot.get("home_moneyline", -110)
            if pick.selection == away_team:
                ml = pick.odds_snapshot.get("away_moneyline", 110)
            if ml < 0:
                profit = pick.amount * (100 / abs(ml))
            else:
                profit = pick.amount * (ml / 100)
            pick.payout = round(pick.amount + profit)
            pick.result = "win"
        else:
            pick.payout = 0
            pick.result = "loss"

    elif pick.pick_type == "spread":
        spread = pick.odds_snapshot.get("spread", 0)
        # Pick is always from home perspective: "home" covers or "away" covers
        if pick.selection == home_team:
            adjusted = margin + spread  # home must win by more than spread
            if adjusted > 0:
                pick.result = "win"
            elif adjusted == 0:
                pick.result = "push"
            else:
                pick.result = "loss"
        else:
            adjusted = -margin - spread
            if adjusted > 0:
                pick.result = "win"
            elif adjusted == 0:
                pick.result = "push"
            else:
                pick.result = "loss"
        # Spread pays even money (-110 style → ~0.91 profit)
        if pick.result == "win":
            pick.payout = round(pick.amount + pick.amount * 0.91)
        elif pick.result == "push":
            pick.payout = pick.amount
        else:
            pick.payout = 0

    elif pick.pick_type == "over_under":
        total = home_score + away_score
        line = pick.odds_snapshot.get("over_under", 30)
        if pick.selection == "over":
            if total > line:
                pick.result = "win"
            elif total == line:
                pick.result = "push"
            else:
                pick.result = "loss"
        else:  # under
            if total < line:
                pick.result = "win"
            elif total == line:
                pick.result = "push"
            else:
                pick.result = "loss"
        if pick.result == "win":
            pick.payout = round(pick.amount + pick.amount * 0.91)
        elif pick.result == "push":
            pick.payout = pick.amount
        else:
            pick.payout = 0

    elif pick.pick_type == "chaos":
        chaos_val = game_result.get("stats", {}).get("home", {}).get(
            "viperball_metrics", {}
        ).get("chaos_factor", 50)
        line = pick.odds_snapshot.get("chaos_ou", 40)
        if pick.selection == "over":
            won = chaos_val > line
        else:
            won = chaos_val < line
        if won:
            pick.payout = round(pick.amount + pick.amount * 1.5)  # prop pays 1.5:1
            pick.result = "win"
        else:
            pick.payout = 0
            pick.result = "loss"

    return pick


# ═══════════════════════════════════════════════════════════════════════
# DQ$ BANKROLL
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Bankroll:
    """Tracks a manager's DQ$ balance and transaction history."""
    balance: int = STARTING_BANKROLL
    history: List[Dict] = field(default_factory=list)

    def deposit(self, amount: int, reason: str = ""):
        self.balance += amount
        self.history.append({"type": "deposit", "amount": amount, "reason": reason,
                             "balance": self.balance})

    def withdraw(self, amount: int, reason: str = "") -> bool:
        """Attempt to withdraw.  Returns False if insufficient funds."""
        if amount > self.balance:
            return False
        self.balance -= amount
        self.history.append({"type": "withdraw", "amount": amount, "reason": reason,
                             "balance": self.balance})
        return True

    def to_dict(self) -> Dict:
        return {"balance": self.balance, "history": self.history[-20:]}  # last 20 txns


# ═══════════════════════════════════════════════════════════════════════
# DONATION / BOOSTER SYSTEM
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class BoosterDonation:
    """Record of a DQ$ donation to a program."""
    donation_type: str   # key in DONATION_TYPES
    amount: int          # DQ$ spent
    boost_value: float   # computed effect value
    week: int = 0

    def to_dict(self) -> Dict:
        info = DONATION_TYPES.get(self.donation_type, {})
        return {
            "type": self.donation_type,
            "label": info.get("label", self.donation_type),
            "amount": self.amount,
            "boost_value": self.boost_value,
            "week": self.week,
        }


def calculate_donation_boost(donation_type: str, dq_amount: int) -> float:
    """Calculate the boost value for a donation of ``dq_amount`` DQ$.

    Returns the raw boost value (capped per DONATION_TYPES).
    """
    info = DONATION_TYPES.get(donation_type)
    if info is None:
        return 0.0
    raw = (dq_amount / 1_000) * info["per_1k"]
    return min(raw, info["cap"])


def make_donation(
    bankroll: Bankroll,
    donation_type: str,
    amount: int,
    week: int = 0,
) -> Optional[BoosterDonation]:
    """Attempt to make a booster donation.

    Returns the BoosterDonation on success, or None if insufficient funds
    or invalid type.
    """
    if donation_type not in DONATION_TYPES:
        return None
    if amount < MIN_DONATION:
        return None
    if not bankroll.withdraw(amount, reason=f"Donation: {donation_type}"):
        return None

    boost = calculate_donation_boost(donation_type, amount)
    return BoosterDonation(
        donation_type=donation_type,
        amount=amount,
        boost_value=boost,
        week=week,
    )


# ═══════════════════════════════════════════════════════════════════════
# WEEKLY CONTEST (ties predictions + fantasy together for one week)
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class WeeklyContest:
    """Encapsulates one week of DraftyQueenz activity."""
    week: int
    odds: List[GameOdds] = field(default_factory=list)
    picks: List[Pick] = field(default_factory=list)
    player_pool: List[FantasyPlayer] = field(default_factory=list)
    user_roster: Optional[FantasyRoster] = None
    ai_rosters: List[FantasyRoster] = field(default_factory=list)
    resolved: bool = False

    # Earnings summary (filled after resolution)
    prediction_earnings: int = 0
    fantasy_earnings: int = 0

    def generate_odds(
        self,
        week_games: list,
        team_prestige: Dict[str, int],
        standings: Optional[Dict] = None,
        rng: Optional[random.Random] = None,
    ):
        """Generate odds for all games in the week."""
        rng = rng or random.Random()
        self.odds = []
        for game in week_games:
            hp = team_prestige.get(game.home_team, 50)
            ap = team_prestige.get(game.away_team, 50)
            hr = ar = None
            if standings:
                hs = standings.get(game.home_team)
                as_ = standings.get(game.away_team)
                if hs:
                    hr = (hs.wins, hs.losses)
                if as_:
                    ar = (as_.wins, as_.losses)
            self.odds.append(generate_game_odds(
                game.home_team, game.away_team, hp, ap, hr, ar, rng
            ))

    def build_pool(self, teams: Dict, week_games: list, team_prestige: Dict[str, int]):
        """Build the fantasy player pool for this week."""
        self.player_pool = build_player_pool(teams, week_games)
        for fp in self.player_pool:
            fp.projected_pts = project_player_points(
                fp, team_prestige.get(fp.team_name, 50)
            )

    def generate_ai_rosters(self, team_prestige: Dict[str, int]):
        """Create AI manager rosters for this week's contest."""
        self.ai_rosters = []
        for i, style in enumerate(AI_MANAGER_STYLES):
            r = build_ai_roster(
                style, self.player_pool, team_prestige,
                rng=random.Random(self.week * 1000 + i)
            )
            self.ai_rosters.append(r)
        # Fill remaining with balanced
        while len(self.ai_rosters) < AI_MANAGER_COUNT:
            r = build_ai_roster(
                "balanced", self.player_pool, team_prestige,
                rng=random.Random(self.week * 1000 + len(self.ai_rosters) + 100)
            )
            r.manager_name = f"AI-Balanced-{len(self.ai_rosters)}"
            self.ai_rosters.append(r)

    def make_pick(self, bankroll: Bankroll, pick_type: str, game_idx: int,
                  selection: str, amount: int) -> Tuple[Optional[Pick], str]:
        """Place a prediction bet.  Returns (Pick, error_message)."""
        if amount < MIN_BET:
            return None, f"Minimum bet is {MIN_BET} DQ$."
        if amount > MAX_BET:
            return None, f"Maximum bet is {MAX_BET} DQ$."
        if game_idx < 0 or game_idx >= len(self.odds):
            return None, "Invalid game index."
        if pick_type not in ("winner", "spread", "over_under", "chaos"):
            return None, f"Invalid pick type '{pick_type}'."

        if not bankroll.withdraw(amount, reason=f"Bet: {pick_type}"):
            return None, "Insufficient DQ$ balance."

        odds = self.odds[game_idx]
        pick = Pick(
            pick_type=pick_type,
            game_home=odds.home_team,
            game_away=odds.away_team,
            selection=selection,
            amount=amount,
            odds_snapshot=odds.to_dict(),
        )
        self.picks.append(pick)
        return pick, ""

    def resolve_week(self, game_results: Dict[str, Dict], bankroll: Bankroll):
        """Resolve all picks and fantasy scores after games are played.

        ``game_results`` maps "home_team vs away_team" → game summary dict.
        """
        if self.resolved:
            return

        # ── Resolve predictions ──
        total_prediction_payout = 0
        for pick in self.picks:
            key = f"{pick.game_home} vs {pick.game_away}"
            result = game_results.get(key)
            if result is None:
                # Try reverse
                key = f"{pick.game_away} vs {pick.game_home}"
                result = game_results.get(key)
            if result:
                resolve_pick(pick, result)
                total_prediction_payout += pick.payout

        if total_prediction_payout > 0:
            bankroll.deposit(total_prediction_payout, reason=f"Week {self.week} prediction payouts")
        self.prediction_earnings = total_prediction_payout

        # ── Score fantasy rosters ──
        # Build a lookup: (tag, team_name) → actual_pts from game results
        actual_scores: Dict[Tuple[str, str], float] = {}
        for key, result in game_results.items():
            for side in ("home", "away"):
                team_name = result["final_score"][side]["team"]
                for ps in result.get("player_stats", {}).get(side, []):
                    score = score_player(ps)
                    actual_scores[(ps["tag"], team_name)] = score

        # Apply scores to all rosters
        all_rosters = list(self.ai_rosters)
        if self.user_roster:
            all_rosters.append(self.user_roster)

        for roster in all_rosters:
            for slot, fp in roster.entries.items():
                pts = actual_scores.get((fp.tag, fp.team_name), 0.0)
                fp.actual_pts = pts

        # ── Fantasy payout ──
        if self.user_roster and self.user_roster.is_valid:
            user_pts = self.user_roster.total_points
            ai_scores = sorted([r.total_points for r in self.ai_rosters], reverse=True)
            # Payout tiers: beat all = 3x entry, top 3 = 2x, top 5 = 1.5x, else = 0
            rank = sum(1 for s in ai_scores if s > user_pts) + 1
            if rank == 1:
                payout = FANTASY_ENTRY_FEE * 3
            elif rank <= 3:
                payout = FANTASY_ENTRY_FEE * 2
            elif rank <= 5:
                payout = int(FANTASY_ENTRY_FEE * 1.5)
            else:
                payout = 0

            if payout > 0:
                bankroll.deposit(payout, reason=f"Week {self.week} fantasy finish (#{rank})")
            self.fantasy_earnings = payout

        self.resolved = True

    def to_dict(self) -> Dict:
        return {
            "week": self.week,
            "odds": [o.to_dict() for o in self.odds],
            "picks": [p.to_dict() for p in self.picks],
            "user_roster": self.user_roster.to_dict() if self.user_roster else None,
            "ai_rosters": [r.to_dict() for r in self.ai_rosters],
            "prediction_earnings": self.prediction_earnings,
            "fantasy_earnings": self.fantasy_earnings,
            "resolved": self.resolved,
        }


# ═══════════════════════════════════════════════════════════════════════
# SEASON-LONG TRACKER (the "DraftyQueenz Manager")
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class DraftyQueenzManager:
    """Season-long DraftyQueenz state.

    Owns the bankroll, weekly contests, donations, and leaderboard.
    Designed to be persisted alongside dynasty save data.
    """
    manager_name: str = "Coach"
    bankroll: Bankroll = field(default_factory=Bankroll)
    weekly_contests: Dict[int, WeeklyContest] = field(default_factory=dict)
    donations: List[BoosterDonation] = field(default_factory=list)
    season_year: int = 1

    # Cumulative stats
    total_picks_made: int = 0
    total_picks_won: int = 0
    total_fantasy_entries: int = 0
    total_fantasy_top3: int = 0
    peak_bankroll: int = STARTING_BANKROLL

    def start_week(
        self,
        week: int,
        week_games: list,
        teams: Dict,
        team_prestige: Dict[str, int],
        standings: Optional[Dict] = None,
    ) -> WeeklyContest:
        """Initialize a new weekly contest.  Returns the WeeklyContest."""
        contest = WeeklyContest(week=week)
        contest.generate_odds(week_games, team_prestige, standings)
        contest.build_pool(teams, week_games, team_prestige)
        contest.generate_ai_rosters(team_prestige)
        self.weekly_contests[week] = contest
        return contest

    def enter_fantasy(self, week: int) -> Tuple[bool, str]:
        """Pay the entry fee for this week's fantasy contest."""
        contest = self.weekly_contests.get(week)
        if contest is None:
            return False, "No contest for this week."
        if contest.user_roster is not None:
            return False, "Already entered this week."
        if not self.bankroll.withdraw(FANTASY_ENTRY_FEE, reason=f"Week {week} fantasy entry"):
            return False, f"Need {FANTASY_ENTRY_FEE} DQ$ to enter. Balance: {self.bankroll.balance}."
        contest.user_roster = FantasyRoster(manager_name=self.manager_name)
        self.total_fantasy_entries += 1
        return True, ""

    def resolve_week(self, week: int, game_results: Dict[str, Dict]):
        """Resolve predictions and fantasy for a completed week."""
        contest = self.weekly_contests.get(week)
        if contest is None:
            return
        contest.resolve_week(game_results, self.bankroll)

        # Update cumulative stats
        for pick in contest.picks:
            self.total_picks_made += 1
            if pick.result == "win":
                self.total_picks_won += 1

        if contest.user_roster:
            ai_scores = sorted([r.total_points for r in contest.ai_rosters], reverse=True)
            rank = sum(1 for s in ai_scores if s > contest.user_roster.total_points) + 1
            if rank <= 3:
                self.total_fantasy_top3 += 1

        self.peak_bankroll = max(self.peak_bankroll, self.bankroll.balance)

    def donate(self, donation_type: str, amount: int, week: int = 0) -> Tuple[Optional[BoosterDonation], str]:
        """Make a booster donation.  Returns (donation, error_msg)."""
        if donation_type not in DONATION_TYPES:
            types = ", ".join(DONATION_TYPES.keys())
            return None, f"Invalid type. Choose from: {types}"
        if amount < MIN_DONATION:
            return None, f"Minimum donation is {MIN_DONATION} DQ$."
        donation = make_donation(self.bankroll, donation_type, amount, week)
        if donation is None:
            return None, f"Insufficient DQ$ (need {amount}, have {self.bankroll.balance})."
        self.donations.append(donation)
        return donation, ""

    def get_active_boosts(self) -> Dict[str, float]:
        """Sum all donation boosts by type for the current season."""
        boosts: Dict[str, float] = {}
        for d in self.donations:
            cap = DONATION_TYPES.get(d.donation_type, {}).get("cap", 999)
            current = boosts.get(d.donation_type, 0.0)
            boosts[d.donation_type] = min(current + d.boost_value, cap)
        return boosts

    # ── Leaderboard / reporting ──

    @property
    def pick_accuracy(self) -> float:
        if self.total_picks_made == 0:
            return 0.0
        return round(self.total_picks_won / self.total_picks_made * 100, 1)

    @property
    def fantasy_top3_rate(self) -> float:
        if self.total_fantasy_entries == 0:
            return 0.0
        return round(self.total_fantasy_top3 / self.total_fantasy_entries * 100, 1)

    @property
    def total_earned(self) -> int:
        return sum(c.prediction_earnings + c.fantasy_earnings
                   for c in self.weekly_contests.values())

    @property
    def total_wagered(self) -> int:
        return sum(p.amount for c in self.weekly_contests.values() for p in c.picks)

    @property
    def total_donated(self) -> int:
        return sum(d.amount for d in self.donations)

    @property
    def roi(self) -> float:
        if self.total_wagered == 0:
            return 0.0
        return round((self.total_earned - self.total_wagered) / self.total_wagered * 100, 1)

    def season_summary(self) -> Dict:
        """Full season DraftyQueenz report."""
        weekly_data = []
        for week_num in sorted(self.weekly_contests.keys()):
            c = self.weekly_contests[week_num]
            weekly_data.append({
                "week": week_num,
                "picks_made": len(c.picks),
                "picks_won": sum(1 for p in c.picks if p.result == "win"),
                "prediction_earnings": c.prediction_earnings,
                "fantasy_entered": c.user_roster is not None,
                "fantasy_points": c.user_roster.total_points if c.user_roster else 0,
                "fantasy_earnings": c.fantasy_earnings,
            })

        return {
            "manager": self.manager_name,
            "season": self.season_year,
            "bankroll": self.bankroll.balance,
            "peak_bankroll": self.peak_bankroll,
            "total_earned": self.total_earned,
            "total_wagered": self.total_wagered,
            "total_donated": self.total_donated,
            "roi": self.roi,
            "pick_accuracy": self.pick_accuracy,
            "fantasy_top3_rate": self.fantasy_top3_rate,
            "active_boosts": self.get_active_boosts(),
            "weeks": weekly_data,
            "donations": [d.to_dict() for d in self.donations],
        }

    def to_dict(self) -> Dict:
        """Serialize for save/load."""
        return {
            "manager_name": self.manager_name,
            "bankroll": self.bankroll.to_dict(),
            "season_year": self.season_year,
            "total_picks_made": self.total_picks_made,
            "total_picks_won": self.total_picks_won,
            "total_fantasy_entries": self.total_fantasy_entries,
            "total_fantasy_top3": self.total_fantasy_top3,
            "peak_bankroll": self.peak_bankroll,
            "donations": [d.to_dict() for d in self.donations],
            "weekly_contests": {
                str(w): c.to_dict() for w, c in self.weekly_contests.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "DraftyQueenzManager":
        """Restore from saved data (bankroll + cumulative stats).

        Weekly contest detail is not fully round-tripped — only the summary
        stats survive a save/load cycle, which keeps save files small.
        """
        mgr = cls(
            manager_name=data.get("manager_name", "Coach"),
            season_year=data.get("season_year", 1),
        )
        br = data.get("bankroll", {})
        mgr.bankroll.balance = br.get("balance", STARTING_BANKROLL)
        mgr.bankroll.history = br.get("history", [])
        mgr.total_picks_made = data.get("total_picks_made", 0)
        mgr.total_picks_won = data.get("total_picks_won", 0)
        mgr.total_fantasy_entries = data.get("total_fantasy_entries", 0)
        mgr.total_fantasy_top3 = data.get("total_fantasy_top3", 0)
        mgr.peak_bankroll = data.get("peak_bankroll", STARTING_BANKROLL)

        for dd in data.get("donations", []):
            mgr.donations.append(BoosterDonation(
                donation_type=dd.get("type", ""),
                amount=dd.get("amount", 0),
                boost_value=dd.get("boost_value", 0),
                week=dd.get("week", 0),
            ))
        return mgr


# ═══════════════════════════════════════════════════════════════════════
# CONVENIENCE: format helpers for UI / display
# ═══════════════════════════════════════════════════════════════════════

def format_moneyline(ml: int) -> str:
    """Format American moneyline for display."""
    return f"+{ml}" if ml > 0 else str(ml)


def format_odds_line(odds: GameOdds) -> str:
    """One-line summary of a game's odds."""
    return (
        f"{odds.away_team} ({format_moneyline(odds.away_moneyline)}) "
        f"@ {odds.home_team} ({format_moneyline(odds.home_moneyline)}) | "
        f"Spread: {odds.spread:+.1f} | O/U: {odds.over_under:.1f} | "
        f"Chaos O/U: {odds.chaos_ou:.1f}"
    )


def format_roster_display(roster: FantasyRoster) -> List[str]:
    """Return a list of display lines for a roster."""
    lines = [f"{'Slot':<6} {'Player':<22} {'Team':<18} {'Pos':<4} {'Salary':>8} {'Pts':>6}"]
    lines.append("─" * 68)
    for slot in roster.slot_keys():
        fp = roster.entries.get(slot)
        if fp:
            lines.append(
                f"{slot:<6} {fp.name:<22} {fp.team_name:<18} {fp.position_tag:<4} "
                f"${fp.salary:>7,} {fp.actual_pts:>6.1f}"
            )
        else:
            lines.append(f"{slot:<6} {'(empty)':<22}")
    lines.append("─" * 68)
    lines.append(f"{'Total':<6} {'':<22} {'':<18} {'':<4} ${roster.total_salary:>7,} {roster.total_points:>6.1f}")
    cap_remaining = SALARY_CAP - roster.total_salary
    lines.append(f"Cap remaining: ${cap_remaining:,}")
    return lines


def format_leaderboard(manager: DraftyQueenzManager) -> List[str]:
    """Season leaderboard display."""
    lines = [
        f"╔══════════════════════════════════════════════════╗",
        f"║         DraftyQueenz Season {manager.season_year} Report          ║",
        f"╠══════════════════════════════════════════════════╣",
        f"║  Manager: {manager.manager_name:<38} ║",
        f"║  Balance: {manager.bankroll.balance:>10,} DQ$                    ║",
        f"║  Peak:    {manager.peak_bankroll:>10,} DQ$                    ║",
        f"╠══════════════════════════════════════════════════╣",
        f"║  PREDICTIONS                                     ║",
        f"║    Picks: {manager.total_picks_made:<5}  Won: {manager.total_picks_won:<5}  "
        f"Acc: {manager.pick_accuracy:>5.1f}%    ║",
        f"║    Wagered: {manager.total_wagered:>8,}  Earned: {manager.total_earned:>8,}    ║",
        f"║    ROI: {manager.roi:>+6.1f}%                                ║",
        f"╠══════════════════════════════════════════════════╣",
        f"║  FANTASY                                         ║",
        f"║    Entries: {manager.total_fantasy_entries:<4}  Top-3: {manager.total_fantasy_top3:<4}  "
        f"Rate: {manager.fantasy_top3_rate:>5.1f}%  ║",
        f"╠══════════════════════════════════════════════════╣",
        f"║  BOOSTER DONATIONS                               ║",
        f"║    Total donated: {manager.total_donated:>8,} DQ$                ║",
    ]
    boosts = manager.get_active_boosts()
    for btype, val in boosts.items():
        label = DONATION_TYPES[btype]["label"]
        lines.append(f"║    {label:<20} +{val:<8.1f}              ║")
    if not boosts:
        lines.append(f"║    (none yet)                                    ║")
    lines.append(f"╚══════════════════════════════════════════════════╝")
    return lines
