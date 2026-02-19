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
FANTASY_ENTRY_FEE = 2_500   # costs real money to enter — high risk
MIN_BET = 250
MAX_BET = 25_000             # you can bet your whole bankroll on one game
MIN_DONATION = 10_000        # serious money to move the needle

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
AI_MANAGER_COUNT = 9  # compete against 9 AI managers each week

# ── Booster tiers (cumulative career donations) ──
BOOSTER_TIERS = [
    (0,        "Sideline Pass",     "You're just a fan with a dream."),
    (25_000,   "Bronze Booster",    "The program knows your name."),
    (100_000,  "Silver Booster",    "You've got a parking spot near the stadium."),
    (250_000,  "Gold Booster",      "The AD takes your calls."),
    (500_000,  "Platinum Booster",  "The coach asks your opinion on recruits."),
    (1_000_000, "Diamond Booster",  "They're naming a facility after you."),
]

# ── Donation boost types and their dynasty effects ──
# These are EXPENSIVE — it takes multiple winning seasons to max out.
# The per_10k rate means you need serious DQ$ to move the needle.
DONATION_TYPES = {
    "recruiting": {
        "label": "Recruiting Boost",
        "description": "Improve pipeline quality for next recruiting cycle",
        "per_10k": 1.0,      # +1.0 recruiting points per 10,000 DQ$
        "cap": 15.0,         # need 150k DQ$ to max
    },
    "development": {
        "label": "Player Development",
        "description": "Extra coaching resources for offseason development",
        "per_10k": 0.5,      # +0.5 dev points per 10k
        "cap": 8.0,          # need 160k DQ$ to max
    },
    "nil_topup": {
        "label": "NIL Top-Up",
        "description": "Inject extra NIL budget for portal/retention",
        "per_10k": 10_000,   # $10k real NIL per 10k DQ$
        "cap": 500_000,      # need 500k DQ$ to max — multi-season project
    },
    "retention": {
        "label": "Retention Bonus",
        "description": "Reduce transfer portal attrition risk",
        "per_10k": 1.5,      # +1.5% retention modifier per 10k
        "cap": 20.0,         # need ~133k DQ$ to max
    },
    "facilities": {
        "label": "Facilities Upgrade",
        "description": "Better facilities boost prestige and recruiting appeal",
        "per_10k": 0.8,      # +0.8 prestige points per 10k
        "cap": 12.0,         # need 150k DQ$ to max
    },
}

# ── Fantasy payout structure (purse tiers) ──
# Entry = 2,500 DQ$.  Big purses mean high variance.
FANTASY_PAYOUTS = {
    1: 8,    # 1st place: 8x entry = 20,000 DQ$
    2: 5,    # 2nd: 5x = 12,500 DQ$
    3: 3,    # 3rd: 3x = 7,500 DQ$
    4: 2,    # 4th: 2x = 5,000 DQ$
    5: 1,    # 5th: break even = 2,500 DQ$
}
# 6th–10th = lose your entry fee


# ═══════════════════════════════════════════════════════════════════════
# FANTASY SCORING
# ═══════════════════════════════════════════════════════════════════════

SCORING_RULES = {
    # ── Offense ──
    "yards":              (1.0, 10),    # 1 pt per 10 yards
    "rushing_yards":      (0.5, 10),    # 0.5 bonus per 10 rushing yards (stacks)
    "lateral_yards":      (1.0, 8),     # 1 pt per 8 lateral yards (premium — Viperball's signature)
    "tds":                9.0,          # matches in-game TD value
    "lateral_tds":        4.0,          # bonus on top of td — the highlight play
    "laterals_thrown":    1.5,          # playmaking — like an assist
    "lateral_receptions": 1.0,
    "lateral_assists":    1.0,
    "fumbles":           -4.0,         # costly — just like in-game

    # ── Kick Passing (forward kicks to teammates — Viperball's wildcard weapon) ──
    "kick_passes_completed": 3.0,     # hard to complete — reward execution
    "kick_pass_yards":    (1.0, 8),   # premium rate like laterals
    "kick_pass_tds":      9.0,        # matches TD value
    "kick_pass_int":     -5.0,        # derived: kick_pass_interceptions_thrown; costlier than fumble
    "kick_pass_receptions": 2.0,      # catching a kicked ball is impressive
    "kick_pass_def_int":  6.0,        # derived: kick_pass_ints; big defensive play

    # ── Kicking (split stats: pk = place kick/FG 3pts, dk = drop kick/snap kick 5pts) ──
    "pk_made":            4.0,          # field goal made — reliable 3-pointer
    "dk_made":            8.0,          # drop kick made — the big 5-pointer, hard to hit
    "pk_miss":           -1.5,          # derived: pk_att - pk_made
    "dk_miss":           -3.0,          # derived: dk_att - dk_made; high risk, high penalty

    # ── Keeper / Special Teams ──
    "keeper_bells":       5.0,          # signature defensive play
    "kick_deflections":   4.0,
    "keeper_tackles":     3.0,
    "st_tackles":         2.0,
    "kick_return_yards":  (1.0, 15),
    "punt_return_yards":  (1.0, 12),
    "kick_return_tds":    9.0,
    "punt_return_tds":    9.0,
    "muffs":             -3.0,         # costly turnover
}


def score_player(player_stats: Dict) -> float:
    """Calculate fantasy points for one player from their game stat dict.

    ``player_stats`` uses the same keys produced by
    ``ViperballEngine.generate_game_summary()`` → ``player_stats``.
    """
    pts = 0.0

    for stat_key, rule in SCORING_RULES.items():
        # Derived miss stats (att − made)
        if stat_key == "pk_miss":
            misses = player_stats.get("pk_att", 0) - player_stats.get("pk_made", 0)
            pts += max(0, misses) * rule
            continue
        if stat_key == "dk_miss":
            misses = player_stats.get("dk_att", 0) - player_stats.get("dk_made", 0)
            pts += max(0, misses) * rule
            continue
        if stat_key == "kick_pass_int":
            val = player_stats.get("kick_pass_interceptions_thrown", 0)
            if val > 0:
                pts += val * rule
            continue
        if stat_key == "kick_pass_def_int":
            val = player_stats.get("kick_pass_ints", 0)
            if val > 0:
                pts += val * rule
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


def _salary_for_player(overall: int, position_tag: str,
                       games_played: int = 0, depth_rank: int = 1,
                       seed: int = 0) -> int:
    """Compute weekly salary from overall rating, position, usage, and depth.

    Bench warmers and low-usage players are cheap (~500-2000).
    Starters with high overalls command premiums.
    Returns granular, non-rounded amounts for realistic arbitrage.
    """
    import hashlib
    usage_factor = min(1.0, games_played / 12.0) if games_played > 0 else 0.05
    depth_factor = {1: 1.0, 2: 0.65, 3: 0.40}.get(depth_rank, max(0.15, 0.50 - depth_rank * 0.08))

    base = 400 + int((overall / 100) * 10_000 * usage_factor * depth_factor)

    pos_mult = {
        "VP": 1.28,
        "HB": 1.07,
        "ZB": 1.12,
        "WB": 1.00,
        "SB": 0.88,
        "KP": 0.78,
    }.get(position_tag, 1.0)

    raw = int(base * pos_mult)

    h = int(hashlib.md5(f"{seed}-{overall}-{position_tag}-{depth_rank}".encode()).hexdigest()[:8], 16)
    micro_var = 0.93 + (h % 1500) / 10000.0
    salary = max(487, int(raw * micro_var))

    return salary


def compute_depth_chart(players: list) -> Dict[str, list]:
    """Compute depth chart for a team's players, grouped by position.

    Returns dict of position -> list of (player, depth_rank) sorted by overall desc.
    """
    from engine.game_engine import player_tag
    pos_groups: Dict[str, list] = {}
    for p in players:
        pos = getattr(p, "position", "Unknown")
        pos_groups.setdefault(pos, []).append(p)

    depth_chart: Dict[str, list] = {}
    for pos, group in pos_groups.items():
        sorted_group = sorted(group, key=lambda x: getattr(x, "overall", 0), reverse=True)
        depth_chart[pos] = [(p, rank + 1) for rank, p in enumerate(sorted_group)]

    return depth_chart


def get_player_depth_rank(player, team_players: list) -> int:
    """Get a player's depth rank within their position group."""
    pos = getattr(player, "position", "Unknown")
    same_pos = [p for p in team_players if getattr(p, "position", "") == pos]
    same_pos.sort(key=lambda x: getattr(x, "overall", 0), reverse=True)
    for i, p in enumerate(same_pos, 1):
        if getattr(p, "name", "") == getattr(player, "name", ""):
            return i
    return len(same_pos)


def build_player_pool(teams: Dict, week_schedule: list, week_seed: int = 0) -> List[FantasyPlayer]:
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
        team_players = team.players
        for p in team_players:
            from engine.game_engine import player_tag, POSITION_TAGS
            ptag = player_tag(p)
            pos_tag = _position_tag_from_full(ptag)
            if pos_tag not in FLEX_ELIGIBLE:
                continue
            depth_rank = get_player_depth_rank(p, team_players)
            games = getattr(p, "season_games_played", 0)
            salary = _salary_for_player(
                p.overall, pos_tag,
                games_played=games,
                depth_rank=depth_rank,
                seed=week_seed + hash(p.name) % 10000,
            )
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
    kick_pass_ou: float = 14.5 # Kick Pass attempts over/under

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
            "kick_pass_ou": self.kick_pass_ou,
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

    # Kick pass over/under (total KP attempts both teams combined)
    # Base ~15 attempts, adjusted by combined prestige (better teams kick pass more)
    kp_base = 12 + (avg_prestige / 100) * 8 + rng.gauss(0, 2)
    kick_pass_ou = round(max(6.5, min(30.5, kp_base)) * 2) / 2  # round to nearest 0.5

    return GameOdds(
        home_team=home_team_name,
        away_team=away_team_name,
        home_win_prob=home_prob,
        spread=spread,
        over_under=total,
        home_moneyline=_prob_to_american(home_prob),
        away_moneyline=_prob_to_american(1 - home_prob),
        chaos_ou=chaos_ou,
        kick_pass_ou=kick_pass_ou,
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
            pick.payout = round(pick.amount + pick.amount * 3.0)  # prop pays 3:1 — hard to hit
            pick.result = "win"
        else:
            pick.payout = 0
            pick.result = "loss"

    elif pick.pick_type == "kick_pass":
        home_kp = game_result.get("stats", {}).get("home", {}).get("kick_passes_attempted", 0)
        away_kp = game_result.get("stats", {}).get("away", {}).get("kick_passes_attempted", 0)
        total_kp = home_kp + away_kp
        line = pick.odds_snapshot.get("kick_pass_ou", 14.5)
        if pick.selection == "over":
            if total_kp > line:
                pick.result = "win"
            elif total_kp == line:
                pick.result = "push"
            else:
                pick.result = "loss"
        else:
            if total_kp < line:
                pick.result = "win"
            elif total_kp == line:
                pick.result = "push"
            else:
                pick.result = "loss"
        if pick.result == "win":
            pick.payout = round(pick.amount + pick.amount * 2.0)  # kick pass prop pays 2:1
        elif pick.result == "push":
            pick.payout = pick.amount
        else:
            pick.payout = 0

    return pick


# ── Parlays: chain picks for multiplied payouts ──

PARLAY_MULTIPLIERS = {
    2: 2.6,    # 2-leg parlay
    3: 6.0,    # 3-leg
    4: 11.0,   # 4-leg
    5: 20.0,   # 5-leg — lose your shirt or buy a building
    6: 40.0,   # 6-leg — degenerate territory
}
MAX_PARLAY_LEGS = 6


@dataclass
class Parlay:
    """A multi-game parlay bet.  All legs must hit to win."""
    legs: List[Pick] = field(default_factory=list)
    amount: int = 0
    multiplier: float = 1.0
    payout: float = 0.0
    result: str = ""  # "win", "loss", "pending"

    def to_dict(self) -> Dict:
        return {
            "legs": [p.to_dict() for p in self.legs],
            "amount": self.amount,
            "multiplier": self.multiplier,
            "payout": self.payout,
            "result": self.result,
            "potential_payout": round(self.amount * self.multiplier),
        }


def resolve_parlay(parlay: Parlay, game_results: Dict[str, Dict]) -> Parlay:
    """Resolve all legs of a parlay.  ALL must win for payout."""
    for pick in parlay.legs:
        key = f"{pick.game_home} vs {pick.game_away}"
        result = game_results.get(key)
        if result is None:
            key = f"{pick.game_away} vs {pick.game_home}"
            result = game_results.get(key)
        if result:
            # Resolve individually but ignore individual payout — parlay pays as unit
            resolve_pick(pick, result)

    all_won = all(p.result == "win" for p in parlay.legs)
    any_push = any(p.result == "push" for p in parlay.legs)

    if all_won:
        parlay.payout = round(parlay.amount * parlay.multiplier)
        parlay.result = "win"
    elif any_push and all(p.result in ("win", "push") for p in parlay.legs):
        # Push reduces parlay to next-lower multiplier
        active_legs = sum(1 for p in parlay.legs if p.result == "win")
        reduced_mult = PARLAY_MULTIPLIERS.get(active_legs, 1.0) if active_legs >= 2 else 1.0
        parlay.payout = round(parlay.amount * reduced_mult)
        parlay.result = "win" if active_legs >= 2 else "push"
    else:
        parlay.payout = 0
        parlay.result = "loss"

    return parlay


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
    target_team: str = ""

    def to_dict(self) -> Dict:
        info = DONATION_TYPES.get(self.donation_type, {})
        return {
            "type": self.donation_type,
            "label": info.get("label", self.donation_type),
            "amount": self.amount,
            "boost_value": self.boost_value,
            "week": self.week,
            "target_team": self.target_team,
        }


def calculate_donation_boost(donation_type: str, dq_amount: int) -> float:
    """Calculate the boost value for a donation of ``dq_amount`` DQ$.

    Returns the raw boost value (capped per DONATION_TYPES).
    """
    info = DONATION_TYPES.get(donation_type)
    if info is None:
        return 0.0
    raw = (dq_amount / 10_000) * info["per_10k"]
    return min(raw, info["cap"])


def get_booster_tier(total_donated: int) -> Tuple[str, str]:
    """Return (tier_name, description) based on cumulative career donations."""
    tier_name, desc = BOOSTER_TIERS[0][1], BOOSTER_TIERS[0][2]
    for threshold, name, description in BOOSTER_TIERS:
        if total_donated >= threshold:
            tier_name, desc = name, description
    return tier_name, desc


def get_next_booster_tier(total_donated: int) -> Optional[Tuple[int, str]]:
    """Return (amount_needed, tier_name) for the next tier, or None if maxed."""
    for threshold, name, _ in BOOSTER_TIERS:
        if total_donated < threshold:
            return (threshold - total_donated, name)
    return None


def make_donation(
    bankroll: Bankroll,
    donation_type: str,
    amount: int,
    week: int = 0,
    target_team: str = "",
) -> Optional[BoosterDonation]:
    """Attempt to make a booster donation to a specific team program.

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
        target_team=target_team,
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
    parlays: List[Parlay] = field(default_factory=list)
    player_pool: List[FantasyPlayer] = field(default_factory=list)
    user_roster: Optional[FantasyRoster] = None
    ai_rosters: List[FantasyRoster] = field(default_factory=list)
    resolved: bool = False

    # Earnings summary (filled after resolution)
    prediction_earnings: int = 0
    fantasy_earnings: int = 0
    jackpot_bonus: int = 0

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

    def build_pool(self, teams: Dict, week_games: list, team_prestige: Dict[str, int],
                   week_seed: int = 0):
        """Build the fantasy player pool for this week."""
        self.player_pool = build_player_pool(teams, week_games, week_seed=week_seed)
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
        if pick_type not in ("winner", "spread", "over_under", "chaos", "kick_pass"):
            return None, f"Invalid pick type '{pick_type}'."

        for existing in self.picks:
            if existing.pick_type == pick_type and existing.game_home == self.odds[game_idx].home_team and existing.game_away == self.odds[game_idx].away_team:
                return None, f"You already placed a {pick_type} bet on this game."

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

    def make_parlay(self, bankroll: Bankroll, legs: List[Tuple[str, int, str]],
                    amount: int) -> Tuple[Optional[Parlay], str]:
        """Place a parlay bet.

        ``legs`` is a list of (pick_type, game_idx, selection) tuples.
        Returns (Parlay, error_message).
        """
        if len(legs) < 2:
            return None, "Parlay requires at least 2 legs."
        if len(legs) > MAX_PARLAY_LEGS:
            return None, f"Maximum {MAX_PARLAY_LEGS} legs per parlay."
        if amount < MIN_BET:
            return None, f"Minimum bet is {MIN_BET} DQ$."
        if amount > MAX_BET:
            return None, f"Maximum bet is {MAX_BET:,} DQ$."

        multiplier = PARLAY_MULTIPLIERS.get(len(legs))
        if multiplier is None:
            return None, f"No multiplier for {len(legs)}-leg parlay."

        if not bankroll.withdraw(amount, reason=f"Parlay ({len(legs)} legs)"):
            return None, "Insufficient DQ$ balance."

        parlay_picks = []
        for pick_type, game_idx, selection in legs:
            if game_idx < 0 or game_idx >= len(self.odds):
                bankroll.deposit(amount, reason="Parlay refund — invalid game")
                return None, f"Invalid game index {game_idx}."
            odds = self.odds[game_idx]
            parlay_picks.append(Pick(
                pick_type=pick_type,
                game_home=odds.home_team,
                game_away=odds.away_team,
                selection=selection,
                amount=0,  # individual legs don't have separate amounts
                odds_snapshot=odds.to_dict(),
            ))

        parlay = Parlay(legs=parlay_picks, amount=amount, multiplier=multiplier)
        self.parlays.append(parlay)
        return parlay, ""

    def resolve_week(self, game_results: Dict[str, Dict], bankroll: Bankroll):
        """Resolve all picks and fantasy scores after games are played.

        ``game_results`` maps "home_team vs away_team" → game summary dict.
        """
        if self.resolved:
            return

        # ── Resolve straight picks ──
        total_prediction_payout = 0
        for pick in self.picks:
            key = f"{pick.game_home} vs {pick.game_away}"
            result = game_results.get(key)
            if result is None:
                key = f"{pick.game_away} vs {pick.game_home}"
                result = game_results.get(key)
            if result:
                resolve_pick(pick, result)
                total_prediction_payout += pick.payout

        # ── Resolve parlays ──
        for parlay in self.parlays:
            resolve_parlay(parlay, game_results)
            total_prediction_payout += parlay.payout

        if total_prediction_payout > 0:
            bankroll.deposit(total_prediction_payout, reason=f"Week {self.week} prediction payouts")
        self.prediction_earnings = total_prediction_payout

        # ── Score fantasy rosters ──
        actual_scores: Dict[Tuple[str, str], float] = {}
        for key, result in game_results.items():
            for side in ("home", "away"):
                team_name = result["final_score"][side]["team"]
                for ps in result.get("player_stats", {}).get(side, []):
                    score = score_player(ps)
                    actual_scores[(ps["tag"], team_name)] = score

        all_rosters = list(self.ai_rosters)
        if self.user_roster:
            all_rosters.append(self.user_roster)

        for roster in all_rosters:
            for slot, fp in roster.entries.items():
                pts = actual_scores.get((fp.tag, fp.team_name), 0.0)
                fp.actual_pts = pts

        # ── Fantasy payout (big purses) ──
        if self.user_roster and self.user_roster.is_valid:
            user_pts = self.user_roster.total_points
            ai_scores = sorted([r.total_points for r in self.ai_rosters], reverse=True)
            rank = sum(1 for s in ai_scores if s > user_pts) + 1
            mult = FANTASY_PAYOUTS.get(rank, 0)
            payout = FANTASY_ENTRY_FEE * mult  # 1st = 20k, 2nd = 12.5k, etc.

            if payout > 0:
                bankroll.deposit(payout, reason=f"Week {self.week} fantasy #{rank} (×{mult})")
            self.fantasy_earnings = payout

            # ── Jackpot bonus: perfect week ──
            # Finish 1st in fantasy AND win all straight picks → jackpot
            picks_won = sum(1 for p in self.picks if p.result == "win")
            picks_total = len(self.picks)
            if rank == 1 and picks_total >= 3 and picks_won == picks_total:
                jackpot = FANTASY_ENTRY_FEE * 5  # 12,500 DQ$ bonus
                bankroll.deposit(jackpot, reason=f"Week {self.week} JACKPOT — perfect week!")
                self.jackpot_bonus = jackpot

        self.resolved = True

    def to_dict(self) -> Dict:
        return {
            "week": self.week,
            "odds": [o.to_dict() for o in self.odds],
            "picks": [p.to_dict() for p in self.picks],
            "parlays": [p.to_dict() for p in self.parlays],
            "user_roster": self.user_roster.to_dict() if self.user_roster else None,
            "ai_rosters": [r.to_dict() for r in self.ai_rosters],
            "prediction_earnings": self.prediction_earnings,
            "fantasy_earnings": self.fantasy_earnings,
            "jackpot_bonus": self.jackpot_bonus,
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

    # Cumulative stats (career-spanning in dynasty mode)
    total_picks_made: int = 0
    total_picks_won: int = 0
    total_parlays_made: int = 0
    total_parlays_won: int = 0
    total_fantasy_entries: int = 0
    total_fantasy_top3: int = 0
    total_jackpots: int = 0
    career_donated: int = 0         # lifetime total across all seasons
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

        for parlay in contest.parlays:
            self.total_parlays_made += 1
            if parlay.result == "win":
                self.total_parlays_won += 1

        if contest.user_roster:
            ai_scores = sorted([r.total_points for r in contest.ai_rosters], reverse=True)
            rank = sum(1 for s in ai_scores if s > contest.user_roster.total_points) + 1
            if rank <= 3:
                self.total_fantasy_top3 += 1

        if contest.jackpot_bonus > 0:
            self.total_jackpots += 1

        self.peak_bankroll = max(self.peak_bankroll, self.bankroll.balance)

    def donate(self, donation_type: str, amount: int, week: int = 0,
               target_team: str = "") -> Tuple[Optional[BoosterDonation], str]:
        """Make a booster donation to a specific program.  Returns (donation, error_msg)."""
        if donation_type not in DONATION_TYPES:
            types = ", ".join(DONATION_TYPES.keys())
            return None, f"Invalid type. Choose from: {types}"
        if amount < MIN_DONATION:
            return None, f"Minimum donation is {MIN_DONATION} DQ$."
        if not target_team:
            return None, "Must specify a target team for the donation."
        donation = make_donation(self.bankroll, donation_type, amount, week, target_team=target_team)
        if donation is None:
            return None, f"Insufficient DQ$ (need {amount}, have {self.bankroll.balance})."
        self.donations.append(donation)
        self.career_donated += amount
        return donation, ""

    def get_active_boosts(self, team_name: str = "") -> Dict[str, float]:
        """Sum all donation boosts by type for the current season.

        If team_name is provided, only include donations targeting that team.
        If empty, returns all boosts across all teams (legacy behavior).
        """
        boosts: Dict[str, float] = {}
        for d in self.donations:
            if team_name and d.target_team != team_name:
                continue
            cap = DONATION_TYPES.get(d.donation_type, {}).get("cap", 999)
            current = boosts.get(d.donation_type, 0.0)
            boosts[d.donation_type] = min(current + d.boost_value, cap)
        return boosts

    def get_all_team_boosts(self) -> Dict[str, Dict[str, float]]:
        """Return active boosts grouped by team name."""
        teams: Dict[str, Dict[str, float]] = {}
        for d in self.donations:
            if not d.target_team:
                continue
            if d.target_team not in teams:
                teams[d.target_team] = {}
            cap = DONATION_TYPES.get(d.donation_type, {}).get("cap", 999)
            current = teams[d.target_team].get(d.donation_type, 0.0)
            teams[d.target_team][d.donation_type] = min(current + d.boost_value, cap)
        return teams

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
        return sum(c.prediction_earnings + c.fantasy_earnings + c.jackpot_bonus
                   for c in self.weekly_contests.values())

    @property
    def total_wagered(self) -> int:
        straight = sum(p.amount for c in self.weekly_contests.values() for p in c.picks)
        parlays = sum(p.amount for c in self.weekly_contests.values() for p in c.parlays)
        entries = self.total_fantasy_entries * FANTASY_ENTRY_FEE
        return straight + parlays + entries

    @property
    def booster_tier(self) -> Tuple[str, str]:
        return get_booster_tier(self.career_donated)

    @property
    def next_tier(self) -> Optional[Tuple[int, str]]:
        return get_next_booster_tier(self.career_donated)

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

        tier_name, tier_desc = self.booster_tier
        next_info = self.next_tier
        return {
            "manager": self.manager_name,
            "season": self.season_year,
            "bankroll": self.bankroll.balance,
            "peak_bankroll": self.peak_bankroll,
            "total_earned": self.total_earned,
            "total_wagered": self.total_wagered,
            "total_donated": self.total_donated,
            "career_donated": self.career_donated,
            "roi": self.roi,
            "pick_accuracy": self.pick_accuracy,
            "parlays_made": self.total_parlays_made,
            "parlays_won": self.total_parlays_won,
            "jackpots": self.total_jackpots,
            "fantasy_top3_rate": self.fantasy_top3_rate,
            "booster_tier": tier_name,
            "booster_tier_description": tier_desc,
            "next_tier": {"amount_needed": next_info[0], "name": next_info[1]} if next_info else None,
            "active_boosts": self.get_active_boosts(),
            "team_boosts": self.get_all_team_boosts(),
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
            "total_parlays_made": self.total_parlays_made,
            "total_parlays_won": self.total_parlays_won,
            "total_fantasy_entries": self.total_fantasy_entries,
            "total_fantasy_top3": self.total_fantasy_top3,
            "total_jackpots": self.total_jackpots,
            "career_donated": self.career_donated,
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
        mgr.total_parlays_made = data.get("total_parlays_made", 0)
        mgr.total_parlays_won = data.get("total_parlays_won", 0)
        mgr.total_fantasy_entries = data.get("total_fantasy_entries", 0)
        mgr.total_fantasy_top3 = data.get("total_fantasy_top3", 0)
        mgr.total_jackpots = data.get("total_jackpots", 0)
        mgr.career_donated = data.get("career_donated", 0)
        mgr.peak_bankroll = data.get("peak_bankroll", STARTING_BANKROLL)

        for dd in data.get("donations", []):
            mgr.donations.append(BoosterDonation(
                donation_type=dd.get("type", ""),
                amount=dd.get("amount", 0),
                boost_value=dd.get("boost_value", 0),
                week=dd.get("week", 0),
                target_team=dd.get("target_team", ""),
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
        f"Chaos O/U: {odds.chaos_ou:.1f} | KP O/U: {odds.kick_pass_ou:.1f}"
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
    tier_name, tier_desc = manager.booster_tier
    next_info = manager.next_tier

    w = 56  # inner width
    lines = [
        f"╔{'═' * w}╗",
        f"║{'DraftyQueenz Season ' + str(manager.season_year) + ' Report':^{w}}║",
        f"╠{'═' * w}╣",
        f"║  Manager: {manager.manager_name:<{w - 12}}║",
        f"║  Tier:    {tier_name:<{w - 12}}║",
        f"║           {tier_desc:<{w - 12}}║",
        f"║  Balance: {manager.bankroll.balance:>10,} DQ${'':<{w - 18}}║",
        f"║  Peak:    {manager.peak_bankroll:>10,} DQ${'':<{w - 18}}║",
        f"╠{'═' * w}╣",
        f"║{'PREDICTIONS':^{w}}║",
        f"║  Straight — {manager.total_picks_made} picks, "
        f"{manager.total_picks_won} won ({manager.pick_accuracy:.1f}%)"
        f"{'':<{max(1, w - 42)}}║",
        f"║  Parlays  — {manager.total_parlays_made} made, "
        f"{manager.total_parlays_won} hit"
        f"{'':<{max(1, w - 32)}}║",
        f"║  Wagered: {manager.total_wagered:>10,}  "
        f"Earned: {manager.total_earned:>10,}{'':<{max(1, w - 38)}}║",
        f"║  ROI: {manager.roi:>+7.1f}%{'':<{w - 14}}║",
    ]

    if manager.total_jackpots > 0:
        lines.append(f"║  JACKPOTS: {manager.total_jackpots}{'':<{w - 13}}║")

    lines += [
        f"╠{'═' * w}╣",
        f"║{'FANTASY':^{w}}║",
        f"║  Entries: {manager.total_fantasy_entries:<5} "
        f"Top-3: {manager.total_fantasy_top3:<5} "
        f"Rate: {manager.fantasy_top3_rate:>5.1f}%{'':<{max(1, w - 42)}}║",
        f"║  Entry fee: {FANTASY_ENTRY_FEE:,} DQ$   "
        f"1st place purse: {FANTASY_ENTRY_FEE * FANTASY_PAYOUTS[1]:,} DQ${'':<{max(1, w - 48)}}║",
        f"╠{'═' * w}╣",
        f"║{'BOOSTER DONATIONS':^{w}}║",
        f"║  This season: {manager.total_donated:>8,} DQ$"
        f"   Career: {manager.career_donated:>10,} DQ${'':<{max(1, w - 44)}}║",
    ]

    if next_info:
        lines.append(
            f"║  Next tier: {next_info[1]} "
            f"({next_info[0]:,} DQ$ to go){'':<{max(1, w - 35 - len(next_info[1]) - len(f'{next_info[0]:,}'))}}║"
        )

    boosts = manager.get_active_boosts()
    for btype, val in boosts.items():
        label = DONATION_TYPES[btype]["label"]
        cap = DONATION_TYPES[btype]["cap"]
        pct = min(100, val / cap * 100)
        bar_len = 10
        filled = int(pct / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(f"║  {label:<20} +{val:<6.1f} [{bar}] {pct:>3.0f}%{'':<{max(1, w - 48)}}║")
    if not boosts:
        lines.append(f"║  (no donations yet){'':<{w - 20}}║")

    lines.append(f"╚{'═' * w}╝")
    return lines
