"""Viperball Ranking Composite System.

Implements multiple independent ranking algorithms inspired by the Massey
Composite for college football.  Each method produces a 1-N ordering; the
composite ranking is the average rank across all methods.

Core Math (6):
    1. Elo Ratings       — Adaptive, margin-aware, game-by-game
    2. Colley Matrix     — Pure W/L, no margin, no preseason bias
    3. Massey Ratings    — Least-squares on (truncated) score differentials
    4. Bradley-Terry/MOV — Margin-of-victory with iterative pairwise model
    5. Strength of Record— Resume metric: how hard was it to get your record?
    6. Simple Rating Sys — avg_margin + avg(opponent SRS), iterative

Simple (4):
    7.  Win%                — raw winning percentage
    8.  Point Differential  — raw PPG minus PPG allowed
    9.  Pythagorean Expect. — expected W% from PF^exp/(PF^exp+PA^exp)
    10. SOS-adjusted Win%   — win% × (avg opponent Elo / 1500)

Elo Variants (2):
    11. Recency-weighted Elo — same as Elo but K×2 for second-half games
    12. Round Robin Win%     — expected W% vs every team (from Elo)

Resume (2):
    13. ISOV (Kislanko)  — iterative strength of victory
    14. Resume Index     — quality wins weighted, bad losses penalized

Efficiency (3):
    15. Offensive Efficiency  — PPD + conv% + explosive composite
    16. Defensive Efficiency  — stop rate + TOs forced + KILL% composite
    17. FPI-style EPA         — EPA per play, SOS-adjusted

Viperball-specific (3):
    18. Delta Yards Index     — PK efficiency + mess rate + penalty wins
    19. Comeback Success Rate — W% trailing at half + PP scoring rate
    20. Margin Compression    — log-compressed MOV (blowouts worth less)

Controversial/Opaque (3):
    21. Billingsley   — chain-based rating transfer
    22. Dokter Entropy— information entropy of margin distribution
    23. PageRank      — web-graph authority model on wins

Meta (2):
    24. CFQI (Team Coefficients) — SRS + conference-strength adjustment
    25. Game Control             — avg share of game time in the lead

Pass-through (1):
    26. CVL Official  — existing Power Index from season.py

References:
    - Kenneth Massey's Ranking Composite (masseyratings.com)
    - Colley Matrix (colleyratings.com)
    - CFQI v2 (College Football Quality Index)
    - Kislanko ISOV ratings
    - Wobus MOV / Bradley-Terry model
    - Sorensen's ranking methods overview
    - Billingsley (cfrc.com)
    - PageRank (Brin & Page, 1998)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GameResult:
    """A single completed game used for ranking calculations."""
    home_team: str
    away_team: str
    home_score: float
    away_score: float
    neutral_site: bool = False


@dataclass
class TeamSeasonStats:
    """Per-team season-level stats for efficiency/Viperball-specific rankings.

    These stats are accumulated by the Season class and passed into
    calculate_composite() for methods that need more than game results.
    """
    team: str
    # Offensive
    ppd: float = 0.0                # Points Per Drive
    conversion_pct: float = 0.0     # 3rd+ down conversion %
    explosive_plays: int = 0        # 15+ yard plays
    total_drives: int = 0
    # Defensive
    opp_ppd: float = 0.0            # Opponent Points Per Drive
    turnovers_forced: int = 0
    kill_pct: float = 0.0           # KILL% from DYE penalty kill scoring rate
    stops: int = 0                  # non-scoring opponent drives
    opp_drives: int = 0
    # DYE (Delta Yards Efficiency)
    pk_efficiency: float = 0.0      # penalty kill yards/drive vs baseline
    pp_efficiency: float = 0.0      # power play yards/drive vs baseline
    mess_rate: float = 0.0          # PP score% - PK score% (lower = better)
    wins_despite_penalty: int = 0
    # EPA
    total_epa: float = 0.0          # season EPA sum
    epa_per_play: float = 0.0
    # Comeback
    comeback_wins: int = 0          # wins when trailing at halftime
    games_trailing_at_half: int = 0
    pp_score_rate: float = 0.0      # power play scoring %
    # Game Control
    game_control_avg: float = 0.0   # avg fraction of game spent in the lead
    # Pass-through
    power_index: float = 0.0        # existing CVL Power Index from season.py


@dataclass
class TeamRanking:
    """A team's ranking from a single method."""
    team: str
    rank: int
    rating: float  # raw rating value from the method


# All method keys in canonical order
METHOD_KEYS = [
    "elo", "colley", "massey", "bt", "sor", "srs",          # Core Math
    "win_pct", "point_diff", "pythag", "sos_win_pct",       # Simple
    "elo_recent", "round_robin",                              # Elo Variants
    "isov", "resume",                                         # Resume
    "off_eff", "def_eff", "fpi",                             # Efficiency
    "dye_index", "comeback", "margin_comp",                   # Viperball
    "billingsley", "entropy", "pagerank",                     # Controversial
    "cfqi", "game_control",                                   # Meta
    "cvl_official",                                           # Pass-through
]


@dataclass
class CompositeRanking:
    """A team's composite ranking across all methods."""
    team: str
    composite_rank: int
    mean_rank: float
    median_rank: float
    std_dev: float
    # Generic method storage (all 26 methods)
    method_ranks: Dict[str, int] = field(default_factory=dict)
    method_ratings: Dict[str, float] = field(default_factory=dict)
    # Legacy individual fields (Core Math 6) for backward compat
    elo_rank: int = 0
    elo_rating: float = 0.0
    colley_rank: int = 0
    colley_rating: float = 0.0
    massey_rank: int = 0
    massey_rating: float = 0.0
    bt_rank: int = 0
    bt_rating: float = 0.0
    sor_rank: int = 0
    sor_rating: float = 0.0
    srs_rank: int = 0
    srs_rating: float = 0.0
    # Schedule strength
    sos: float = 0.0
    sos_w: float = 0.0  # avg Elo of teams beaten
    sos_l: float = 0.0  # avg Elo of teams lost to
    # Record
    wins: int = 0
    losses: int = 0
    conference: str = ""


# ---------------------------------------------------------------------------
# 1. Elo Ratings
# ---------------------------------------------------------------------------

_DEFAULT_ELO = 1500
_ELO_K_BASE = 30
_ELO_HFA = 50  # home field advantage in Elo points


def _elo_expected(elo_a: float, elo_b: float) -> float:
    """Win expectancy for team A vs team B."""
    return 1.0 / (1.0 + 10.0 ** (-(elo_a - elo_b) / 400.0))


def _elo_k_factor(mov: float, elo_diff: float) -> float:
    """Margin-of-victory adjusted K factor.

    Dampens blowout inflation against weak teams using the
    multiplier from FiveThirtyEight's NFL Elo:
        K * ln(1 + |MOV|) * (2.2 / (2.2 + 0.001 * |elo_diff|))
    """
    mov_mult = math.log(1.0 + abs(mov))
    dampener = 2.2 / (2.2 + 0.001 * abs(elo_diff))
    return _ELO_K_BASE * mov_mult * dampener


def calculate_elo(
    games: List[GameResult],
    initial_elos: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Calculate Elo ratings from a sequence of games.

    Args:
        games: Ordered list of completed games.
        initial_elos: Starting Elo for each team.  Teams not listed
            start at _DEFAULT_ELO.

    Returns:
        Dict mapping team name -> current Elo rating.
    """
    elos: Dict[str, float] = dict(initial_elos or {})

    for game in games:
        h, a = game.home_team, game.away_team
        elo_h = elos.setdefault(h, _DEFAULT_ELO)
        elo_a = elos.setdefault(a, _DEFAULT_ELO)

        # Adjust for home field (neutral sites get no bonus)
        hfa = 0 if game.neutral_site else _ELO_HFA
        exp_h = _elo_expected(elo_h + hfa, elo_a)

        # Actual result: 1 = home win, 0 = home loss, 0.5 = tie
        if game.home_score > game.away_score:
            actual_h = 1.0
        elif game.home_score < game.away_score:
            actual_h = 0.0
        else:
            actual_h = 0.5

        mov = game.home_score - game.away_score
        k = _elo_k_factor(mov, elo_h - elo_a)

        delta = k * (actual_h - exp_h)
        elos[h] = elo_h + delta
        elos[a] = elo_a - delta

    return elos


# ---------------------------------------------------------------------------
# 2. Colley Matrix
# ---------------------------------------------------------------------------

def calculate_colley(games: List[GameResult]) -> Dict[str, float]:
    """Colley Matrix rankings — pure W/L, no margin, no preseason bias.

    Solves C * r = b where:
        C[i][i] = 2 + total_games[i]
        C[i][j] = -games_between[i][j]  (i != j)
        b[i] = 1 + (wins[i] - losses[i]) / 2
    """
    # Build team index
    teams: List[str] = []
    team_idx: Dict[str, int] = {}
    for g in games:
        for t in (g.home_team, g.away_team):
            if t not in team_idx:
                team_idx[t] = len(teams)
                teams.append(t)
    n = len(teams)
    if n == 0:
        return {}

    # Build matrices (using lists for no-numpy fallback)
    # C matrix and b vector
    C = [[0.0] * n for _ in range(n)]
    wins = [0] * n
    losses = [0] * n
    games_between = [[0] * n for _ in range(n)]

    for g in games:
        hi, ai = team_idx[g.home_team], team_idx[g.away_team]
        games_between[hi][ai] += 1
        games_between[ai][hi] += 1
        if g.home_score > g.away_score:
            wins[hi] += 1
            losses[ai] += 1
        elif g.away_score > g.home_score:
            wins[ai] += 1
            losses[hi] += 1
        else:
            # Tie: half win, half loss for each
            wins[hi] += 0
            losses[hi] += 0
            wins[ai] += 0
            losses[ai] += 0

    # Fill Colley matrix
    for i in range(n):
        total_games_i = sum(games_between[i])
        C[i][i] = 2.0 + total_games_i
        for j in range(n):
            if i != j:
                C[i][j] = -games_between[i][j]

    b = [1.0 + (wins[i] - losses[i]) / 2.0 for i in range(n)]

    # Solve via Gauss-Seidel iteration (avoids numpy dependency)
    r = [1.0 / n] * n
    for _ in range(200):
        max_delta = 0.0
        for i in range(n):
            s = b[i]
            for j in range(n):
                if j != i:
                    s -= C[i][j] * r[j]
            new_r = s / C[i][i] if C[i][i] != 0 else r[i]
            max_delta = max(max_delta, abs(new_r - r[i]))
            r[i] = new_r
        if max_delta < 1e-10:
            break

    return {teams[i]: r[i] for i in range(n)}


# ---------------------------------------------------------------------------
# 3. Massey Ratings (least-squares on score differentials)
# ---------------------------------------------------------------------------

def calculate_massey(
    games: List[GameResult],
    max_margin: float = 21.0,
) -> Dict[str, float]:
    """Massey ratings via least-squares on truncated score differentials.

    For each game: r_home - r_away ≈ truncated(home_score - away_score)
    Solve the overdetermined system A*r = b via normal equations.
    """
    teams: List[str] = []
    team_idx: Dict[str, int] = {}
    for g in games:
        for t in (g.home_team, g.away_team):
            if t not in team_idx:
                team_idx[t] = len(teams)
                teams.append(t)
    n = len(teams)
    if n == 0:
        return {}

    # Build normal equations: (A^T A) r = A^T b
    # A^T A is an n×n matrix, A^T b is length-n vector
    ata = [[0.0] * n for _ in range(n)]
    atb = [0.0] * n

    for g in games:
        hi, ai = team_idx[g.home_team], team_idx[g.away_team]
        margin = g.home_score - g.away_score
        # Truncate margin
        margin = max(-max_margin, min(max_margin, margin))

        # A row is: +1 at hi, -1 at ai
        # A^T A contribution
        ata[hi][hi] += 1
        ata[ai][ai] += 1
        ata[hi][ai] -= 1
        ata[ai][hi] -= 1
        # A^T b contribution
        atb[hi] += margin
        atb[ai] -= margin

    # The system is singular (ratings are relative). Replace last equation
    # with constraint: sum(r) = 0
    for j in range(n):
        ata[n - 1][j] = 1.0
    atb[n - 1] = 0.0

    # Solve via Gauss-Seidel
    r = [0.0] * n
    for _ in range(300):
        max_delta = 0.0
        for i in range(n):
            s = atb[i]
            for j in range(n):
                if j != i:
                    s -= ata[i][j] * r[j]
            new_r = s / ata[i][i] if ata[i][i] != 0 else r[i]
            max_delta = max(max_delta, abs(new_r - r[i]))
            r[i] = new_r
        if max_delta < 1e-10:
            break

    return {teams[i]: r[i] for i in range(n)}


# ---------------------------------------------------------------------------
# 4. Bradley-Terry with Margin of Victory (Wobus-style)
# ---------------------------------------------------------------------------

_BT_INTERCEPT = 0.51025  # base win probability for winner
_BT_SLOPE = 0.028        # probability per point of margin (football-like)


def _bt_win_prob(margin: float) -> float:
    """Estimate probability that the winner wins again, given the margin.

    Based on Wobus's empirical study of margin-of-victory.
    """
    if margin > 0:
        p = _BT_INTERCEPT + _BT_SLOPE * margin
    elif margin < 0:
        p = 1.0 - (_BT_INTERCEPT + _BT_SLOPE * abs(margin))
    else:
        p = 0.5
    return max(0.01, min(0.99, p))


def calculate_bradley_terry(
    games: List[GameResult],
    max_iterations: int = 200,
) -> Dict[str, float]:
    """Bradley-Terry ratings with margin-of-victory weighting.

    Each game contributes a fractional win/loss based on the margin-derived
    probability, fed into the standard BT iterative algorithm.
    """
    teams: List[str] = []
    team_idx: Dict[str, int] = {}
    for g in games:
        for t in (g.home_team, g.away_team):
            if t not in team_idx:
                team_idx[t] = len(teams)
                teams.append(t)
    n = len(teams)
    if n == 0:
        return {}

    # Build fractional win matrix
    # frac_wins[i] = sum of win probabilities across all games for team i
    # matchups[i] = list of (opponent_idx, games_weight) pairs
    frac_wins = [0.0] * n
    matchups: List[List[Tuple[int, float]]] = [[] for _ in range(n)]

    for g in games:
        hi, ai = team_idx[g.home_team], team_idx[g.away_team]
        margin = g.home_score - g.away_score
        p_home = _bt_win_prob(margin)

        frac_wins[hi] += p_home
        frac_wins[ai] += 1.0 - p_home
        matchups[hi].append((ai, 1.0))
        matchups[ai].append((hi, 1.0))

    # Iterative BT: r[i] = frac_wins[i] / sum(weight / (r[i] + r[j]))
    r = [1.0] * n
    for _ in range(max_iterations):
        new_r = [0.0] * n
        for i in range(n):
            denom = 0.0
            for j, w in matchups[i]:
                denom += w / (r[i] + r[j])
            new_r[i] = frac_wins[i] / denom if denom > 0 else r[i]
        # Normalize so average = 1
        avg_r = sum(new_r) / n if n > 0 else 1.0
        if avg_r > 0:
            new_r = [x / avg_r for x in new_r]
        max_delta = max(abs(new_r[i] - r[i]) for i in range(n))
        r = new_r
        if max_delta < 1e-10:
            break

    return {teams[i]: r[i] for i in range(n)}


# ---------------------------------------------------------------------------
# 5. Strength of Record (SOR)
# ---------------------------------------------------------------------------

def calculate_sor(
    games: List[GameResult],
    elos: Dict[str, float],
    n_simulations: int = 1000,
) -> Dict[str, float]:
    """Strength of Record — probability a top-25 team gets this record or worse.

    For each team, simulate a top-25 caliber team (Elo ~1650) playing the
    same schedule.  Count what fraction of simulations produce the same
    record or worse.  Higher SOR = more impressive record.

    Uses current Elo ratings to estimate game-by-game win probabilities.
    """
    # Build schedule for each team
    team_schedules: Dict[str, List[Tuple[str, bool, bool]]] = {}
    # (opponent, is_home, neutral_site)
    team_records: Dict[str, Tuple[int, int]] = {}  # wins, losses

    for g in games:
        team_schedules.setdefault(g.home_team, []).append(
            (g.away_team, True, g.neutral_site)
        )
        team_schedules.setdefault(g.away_team, []).append(
            (g.home_team, False, g.neutral_site)
        )

        if g.home_score > g.away_score:
            w, l = team_records.get(g.home_team, (0, 0))
            team_records[g.home_team] = (w + 1, l)
            w, l = team_records.get(g.away_team, (0, 0))
            team_records[g.away_team] = (w, l + 1)
        elif g.away_score > g.home_score:
            w, l = team_records.get(g.away_team, (0, 0))
            team_records[g.away_team] = (w + 1, l)
            w, l = team_records.get(g.home_team, (0, 0))
            team_records[g.home_team] = (w, l + 1)
        else:
            # Tie: neither win nor loss for SOR purposes
            pass

    # Top-25 Elo: ~90th percentile of all Elo ratings
    if elos:
        sorted_elos = sorted(elos.values(), reverse=True)
        top25_elo = sorted_elos[min(24, len(sorted_elos) - 1)]
    else:
        top25_elo = 1650.0

    sor: Dict[str, float] = {}
    rng = random.Random(42)  # deterministic for reproducibility

    for team, schedule in team_schedules.items():
        actual_wins, actual_losses = team_records.get(team, (0, 0))
        actual_total = actual_wins + actual_losses
        if actual_total == 0:
            sor[team] = 0.5
            continue

        worse_or_equal = 0
        for _ in range(n_simulations):
            sim_wins = 0
            for opp, is_home, neutral in schedule:
                opp_elo = elos.get(opp, _DEFAULT_ELO)
                hfa = 0 if neutral else (_ELO_HFA if is_home else -_ELO_HFA)
                p_win = _elo_expected(top25_elo + hfa, opp_elo)
                if rng.random() < p_win:
                    sim_wins += 1
            if sim_wins <= actual_wins:
                worse_or_equal += 1

        sor[team] = worse_or_equal / n_simulations

    return sor


# ---------------------------------------------------------------------------
# 6. Simple Rating System (SRS)
# ---------------------------------------------------------------------------

def calculate_srs(
    games: List[GameResult],
    max_iterations: int = 200,
) -> Dict[str, float]:
    """Simple Rating System: SRS[i] = avg_margin[i] + avg(SRS[opponents]).

    Iterative until convergence.  Like pro-football-reference SRS.
    """
    teams: List[str] = []
    team_idx: Dict[str, int] = {}
    for g in games:
        for t in (g.home_team, g.away_team):
            if t not in team_idx:
                team_idx[t] = len(teams)
                teams.append(t)
    n = len(teams)
    if n == 0:
        return {}

    # Accumulate margins and opponents
    margin_sum = [0.0] * n
    game_count = [0] * n
    opponents: List[List[int]] = [[] for _ in range(n)]

    for g in games:
        hi, ai = team_idx[g.home_team], team_idx[g.away_team]
        margin = g.home_score - g.away_score
        margin_sum[hi] += margin
        margin_sum[ai] -= margin
        game_count[hi] += 1
        game_count[ai] += 1
        opponents[hi].append(ai)
        opponents[ai].append(hi)

    avg_margin = [
        margin_sum[i] / game_count[i] if game_count[i] > 0 else 0.0
        for i in range(n)
    ]

    # Iterate
    srs = [0.0] * n
    for _ in range(max_iterations):
        new_srs = [0.0] * n
        for i in range(n):
            if not opponents[i]:
                new_srs[i] = avg_margin[i]
                continue
            opp_avg = sum(srs[j] for j in opponents[i]) / len(opponents[i])
            new_srs[i] = avg_margin[i] + opp_avg
        # Normalize: center at 0
        mean_srs = sum(new_srs) / n if n > 0 else 0.0
        new_srs = [x - mean_srs for x in new_srs]
        max_delta = max(abs(new_srs[i] - srs[i]) for i in range(n))
        srs = new_srs
        if max_delta < 1e-10:
            break

    return {teams[i]: srs[i] for i in range(n)}


# ---------------------------------------------------------------------------
# 7. Win Percentage
# ---------------------------------------------------------------------------

def calculate_win_pct(games: List[GameResult]) -> Dict[str, float]:
    """Raw winning percentage. Ties count as half a win."""
    wins: Dict[str, float] = {}
    total: Dict[str, int] = {}
    for g in games:
        for t in (g.home_team, g.away_team):
            wins.setdefault(t, 0.0)
            total.setdefault(t, 0)
        total[g.home_team] += 1
        total[g.away_team] += 1
        if g.home_score > g.away_score:
            wins[g.home_team] += 1.0
        elif g.away_score > g.home_score:
            wins[g.away_team] += 1.0
        else:
            wins[g.home_team] += 0.5
            wins[g.away_team] += 0.5
    return {t: wins[t] / total[t] if total[t] > 0 else 0.0 for t in wins}


# ---------------------------------------------------------------------------
# 8. Point Differential
# ---------------------------------------------------------------------------

def calculate_point_diff(games: List[GameResult]) -> Dict[str, float]:
    """Raw points-per-game differential (PPG scored minus PPG allowed)."""
    pf: Dict[str, float] = {}
    pa: Dict[str, float] = {}
    gp: Dict[str, int] = {}
    for g in games:
        for t in (g.home_team, g.away_team):
            pf.setdefault(t, 0.0)
            pa.setdefault(t, 0.0)
            gp.setdefault(t, 0)
        pf[g.home_team] += g.home_score
        pa[g.home_team] += g.away_score
        pf[g.away_team] += g.away_score
        pa[g.away_team] += g.home_score
        gp[g.home_team] += 1
        gp[g.away_team] += 1
    return {
        t: (pf[t] - pa[t]) / gp[t] if gp[t] > 0 else 0.0
        for t in pf
    }


# ---------------------------------------------------------------------------
# 9. Pythagorean Expectation
# ---------------------------------------------------------------------------

_PYTHAG_EXP = 2.37  # Viperball: 9-pt TDs, ~27 PPG, similar to NFL scaling


def calculate_pythagorean(
    games: List[GameResult],
    exponent: float = _PYTHAG_EXP,
) -> Dict[str, float]:
    """Expected win% from PF^exp / (PF^exp + PA^exp)."""
    pf: Dict[str, float] = {}
    pa: Dict[str, float] = {}
    for g in games:
        for t in (g.home_team, g.away_team):
            pf.setdefault(t, 0.0)
            pa.setdefault(t, 0.0)
        pf[g.home_team] += g.home_score
        pa[g.home_team] += g.away_score
        pf[g.away_team] += g.away_score
        pa[g.away_team] += g.home_score
    result: Dict[str, float] = {}
    for t in pf:
        pf_exp = pf[t] ** exponent
        pa_exp = pa[t] ** exponent
        denom = pf_exp + pa_exp
        result[t] = pf_exp / denom if denom > 0 else 0.5
    return result


# ---------------------------------------------------------------------------
# 10. SOS-adjusted Win%
# ---------------------------------------------------------------------------

def calculate_sos_adjusted_win_pct(
    games: List[GameResult],
    elos: Dict[str, float],
) -> Dict[str, float]:
    """Win% multiplied by schedule strength (avg opponent Elo / 1500)."""
    win_pcts = calculate_win_pct(games)

    # Build avg opponent Elo per team
    opp_elo_sum: Dict[str, float] = {}
    opp_count: Dict[str, int] = {}
    for g in games:
        h, a = g.home_team, g.away_team
        opp_elo_sum.setdefault(h, 0.0)
        opp_elo_sum.setdefault(a, 0.0)
        opp_count.setdefault(h, 0)
        opp_count.setdefault(a, 0)
        opp_elo_sum[h] += elos.get(a, _DEFAULT_ELO)
        opp_elo_sum[a] += elos.get(h, _DEFAULT_ELO)
        opp_count[h] += 1
        opp_count[a] += 1

    return {
        t: win_pcts.get(t, 0.0) * (
            (opp_elo_sum[t] / opp_count[t] / _DEFAULT_ELO)
            if opp_count.get(t, 0) > 0 else 1.0
        )
        for t in win_pcts
    }


# ---------------------------------------------------------------------------
# 11. Recency-weighted Elo
# ---------------------------------------------------------------------------

def calculate_elo_recent(
    games: List[GameResult],
    initial_elos: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Elo ratings where second-half games have K×2.

    Captures late-season form — a team surging in November matters more
    than an early-season blowout.
    """
    elos: Dict[str, float] = dict(initial_elos or {})
    n_games = len(games)
    midpoint = n_games // 2

    for idx, game in enumerate(games):
        h, a = game.home_team, game.away_team
        elo_h = elos.setdefault(h, _DEFAULT_ELO)
        elo_a = elos.setdefault(a, _DEFAULT_ELO)

        hfa = 0 if game.neutral_site else _ELO_HFA
        exp_h = _elo_expected(elo_h + hfa, elo_a)

        if game.home_score > game.away_score:
            actual_h = 1.0
        elif game.home_score < game.away_score:
            actual_h = 0.0
        else:
            actual_h = 0.5

        mov = game.home_score - game.away_score
        k = _elo_k_factor(mov, elo_h - elo_a)

        # Double K for second-half games
        if idx >= midpoint:
            k *= 2.0

        delta = k * (actual_h - exp_h)
        elos[h] = elo_h + delta
        elos[a] = elo_a - delta

    return elos


# ---------------------------------------------------------------------------
# 12. Round Robin Win%
# ---------------------------------------------------------------------------

def calculate_round_robin(elos: Dict[str, float]) -> Dict[str, float]:
    """Expected win% if every team played every other team once.

    For each team, average the Elo expected score against all opponents.
    """
    teams = list(elos.keys())
    n = len(teams)
    if n < 2:
        return {t: 0.5 for t in teams}

    result: Dict[str, float] = {}
    for t in teams:
        total_exp = sum(
            _elo_expected(elos[t], elos[opp])
            for opp in teams if opp != t
        )
        result[t] = total_exp / (n - 1)
    return result


# ---------------------------------------------------------------------------
# 13. ISOV (Kislanko Iterative Strength of Victory)
# ---------------------------------------------------------------------------

def calculate_isov(
    games: List[GameResult],
    max_iterations: int = 200,
) -> Dict[str, float]:
    """ISOV: each team's rating = average rating of teams they beat.

    Iterative — beating highly-rated teams cascades upward.
    Teams with no wins get rating 0.
    """
    # Build victory lists
    victories: Dict[str, List[str]] = {}
    all_teams: set = set()
    for g in games:
        all_teams.add(g.home_team)
        all_teams.add(g.away_team)
        if g.home_score > g.away_score:
            victories.setdefault(g.home_team, []).append(g.away_team)
        elif g.away_score > g.home_score:
            victories.setdefault(g.away_team, []).append(g.home_team)

    # Initialize
    ratings = {t: 1.0 for t in all_teams}

    for _ in range(max_iterations):
        new_ratings: Dict[str, float] = {}
        for t in all_teams:
            beaten = victories.get(t, [])
            if beaten:
                new_ratings[t] = sum(ratings[b] for b in beaten) / len(beaten)
            else:
                new_ratings[t] = 0.0

        # Normalize so average = 1.0
        avg_r = sum(new_ratings.values()) / len(new_ratings) if new_ratings else 1.0
        if avg_r > 0:
            new_ratings = {t: r / avg_r for t, r in new_ratings.items()}

        max_delta = max(
            abs(new_ratings[t] - ratings[t]) for t in all_teams
        )
        ratings = new_ratings
        if max_delta < 1e-10:
            break

    return ratings


# ---------------------------------------------------------------------------
# 14. Resume Index
# ---------------------------------------------------------------------------

def calculate_resume(
    games: List[GameResult],
    elos: Dict[str, float],
) -> Dict[str, float]:
    """Resume Index — quality wins weighted by opponent Elo tier, bad losses penalized.

    Uses Elo ratings to determine opponent tiers (not poll rankings).
    """
    # Build Elo-based rankings (1 = best)
    elo_ranks = _rank_by_rating(elos, descending=True)

    scores: Dict[str, float] = {}
    all_teams: set = set()
    for g in games:
        all_teams.add(g.home_team)
        all_teams.add(g.away_team)
    for t in all_teams:
        scores[t] = 0.0

    for g in games:
        if g.home_score > g.away_score:
            winner, loser = g.home_team, g.away_team
        elif g.away_score > g.home_score:
            winner, loser = g.away_team, g.home_team
        else:
            continue  # ties: no resume impact

        loser_rank = elo_ranks.get(loser, len(all_teams))
        winner_rank = elo_ranks.get(winner, len(all_teams))

        # Quality win points
        if loser_rank <= 5:
            scores[winner] += 10.0
        elif loser_rank <= 10:
            scores[winner] += 7.0
        elif loser_rank <= 25:
            scores[winner] += 4.0
        elif loser_rank <= 50:
            scores[winner] += 2.0
        elif loser_rank <= 100:
            scores[winner] += 1.0

        # Bad loss penalties
        if winner_rank > 100:
            scores[loser] -= 5.0
        elif winner_rank > 50:
            scores[loser] -= 3.0
        elif winner_rank > 25:
            scores[loser] -= 2.0
        elif winner_rank <= 25:
            scores[loser] -= 0.5

    return scores


# ---------------------------------------------------------------------------
# 15. Offensive Efficiency (requires TeamSeasonStats)
# ---------------------------------------------------------------------------

def _normalize_values(values: Dict[str, float]) -> Dict[str, float]:
    """Normalize values to 0-100 scale across all teams."""
    if not values:
        return {}
    vals = list(values.values())
    lo, hi = min(vals), max(vals)
    span = hi - lo
    if span == 0:
        return {t: 50.0 for t in values}
    return {t: (v - lo) / span * 100.0 for t, v in values.items()}


def calculate_off_efficiency(
    team_stats: Dict[str, TeamSeasonStats],
) -> Dict[str, float]:
    """Offensive efficiency composite: PPD + conversion% + explosive plays.

    Weighted: 40% PPD, 30% conversion%, 30% explosive plays.
    Each component normalized 0-100 across the league.
    """
    ppd_norm = _normalize_values({t: s.ppd for t, s in team_stats.items()})
    conv_norm = _normalize_values({t: s.conversion_pct for t, s in team_stats.items()})
    expl_norm = _normalize_values(
        {t: float(s.explosive_plays) for t, s in team_stats.items()}
    )
    return {
        t: 0.4 * ppd_norm.get(t, 50) + 0.3 * conv_norm.get(t, 50) + 0.3 * expl_norm.get(t, 50)
        for t in team_stats
    }


# ---------------------------------------------------------------------------
# 16. Defensive Efficiency (requires TeamSeasonStats)
# ---------------------------------------------------------------------------

def calculate_def_efficiency(
    team_stats: Dict[str, TeamSeasonStats],
) -> Dict[str, float]:
    """Defensive efficiency composite: stop rate + TOs forced + KILL%.

    Weighted: 40% stop rate (inverted opp PPD), 30% turnovers forced, 30% KILL%.
    """
    # Invert opp_ppd so lower opponent PPD = higher score
    stop_norm = _normalize_values(
        {t: (1.0 / s.opp_ppd if s.opp_ppd > 0 else 0.0) for t, s in team_stats.items()}
    )
    to_norm = _normalize_values(
        {t: float(s.turnovers_forced) for t, s in team_stats.items()}
    )
    kill_norm = _normalize_values({t: s.kill_pct for t, s in team_stats.items()})
    return {
        t: 0.4 * stop_norm.get(t, 50) + 0.3 * to_norm.get(t, 50) + 0.3 * kill_norm.get(t, 50)
        for t in team_stats
    }


# ---------------------------------------------------------------------------
# 17. FPI-style EPA (requires TeamSeasonStats + Elo SOS)
# ---------------------------------------------------------------------------

def calculate_fpi(
    team_stats: Dict[str, TeamSeasonStats],
    sos_data: Dict[str, Tuple[float, float, float]],
) -> Dict[str, float]:
    """EPA per play adjusted for schedule strength.

    FPI = epa_per_play × (1 + 0.1 × (sos_elo - 1500) / 100)
    Teams efficient against tough schedules rank higher.
    """
    result: Dict[str, float] = {}
    for t, s in team_stats.items():
        sos_elo = sos_data.get(t, (_DEFAULT_ELO, 0, 0))[0]
        sos_adj = 1.0 + 0.1 * (sos_elo - _DEFAULT_ELO) / 100.0
        result[t] = s.epa_per_play * sos_adj
    return result


# ---------------------------------------------------------------------------
# 18. Delta Yards Index (requires TeamSeasonStats)
# ---------------------------------------------------------------------------

def calculate_dye_index(
    team_stats: Dict[str, TeamSeasonStats],
) -> Dict[str, float]:
    """Delta Yards Efficiency index — Viperball-specific.

    Composite of penalty kill efficiency, inverted mess rate, and
    wins despite delta penalty.  Measures how well teams handle
    the delta yards system.

    Weighted: 40% PK efficiency, 30% -mess_rate, 30% penalty wins.
    """
    pk_norm = _normalize_values({t: s.pk_efficiency for t, s in team_stats.items()})
    # Invert mess_rate: lower is better, so negate before normalizing
    mess_norm = _normalize_values({t: -s.mess_rate for t, s in team_stats.items()})
    wins_norm = _normalize_values(
        {t: float(s.wins_despite_penalty) for t, s in team_stats.items()}
    )
    return {
        t: 0.4 * pk_norm.get(t, 50) + 0.3 * mess_norm.get(t, 50) + 0.3 * wins_norm.get(t, 50)
        for t in team_stats
    }


# ---------------------------------------------------------------------------
# 19. Comeback Success Rate (requires TeamSeasonStats)
# ---------------------------------------------------------------------------

def calculate_comeback(
    team_stats: Dict[str, TeamSeasonStats],
) -> Dict[str, float]:
    """Comeback success rate — W% when trailing at half + PP scoring rate.

    Composite: 60% comeback win rate, 40% power play score rate.
    Teams that never trail get comeback_rate = 1.0 (benefit of dominance).
    """
    result: Dict[str, float] = {}
    for t, s in team_stats.items():
        if s.games_trailing_at_half > 0:
            comeback_rate = s.comeback_wins / s.games_trailing_at_half
        else:
            comeback_rate = 1.0  # never trailed = maximum resilience credit
        result[t] = 0.6 * comeback_rate + 0.4 * (s.pp_score_rate / 100.0 if s.pp_score_rate > 1 else s.pp_score_rate)
    return result


# ---------------------------------------------------------------------------
# 20. Margin Compression MOV
# ---------------------------------------------------------------------------

def calculate_margin_compression(games: List[GameResult]) -> Dict[str, float]:
    """Log-compressed margin of victory.

    For each game: sign(margin) × ln(1 + |margin|).
    Average across season.  Blowouts are worth less than close wins.
    Smoother than Massey's hard truncation.
    """
    compressed_sum: Dict[str, float] = {}
    game_count: Dict[str, int] = {}
    for g in games:
        for t in (g.home_team, g.away_team):
            compressed_sum.setdefault(t, 0.0)
            game_count.setdefault(t, 0)

        margin_h = g.home_score - g.away_score
        compressed_h = math.copysign(math.log(1.0 + abs(margin_h)), margin_h)

        compressed_sum[g.home_team] += compressed_h
        compressed_sum[g.away_team] -= compressed_h
        game_count[g.home_team] += 1
        game_count[g.away_team] += 1

    return {
        t: compressed_sum[t] / game_count[t] if game_count[t] > 0 else 0.0
        for t in compressed_sum
    }


# ---------------------------------------------------------------------------
# 21. Billingsley
# ---------------------------------------------------------------------------

_BILLINGSLEY_TRANSFER = 0.04   # fraction of loser's rating transferred
_BILLINGSLEY_MARGIN_K = 0.01   # per-point margin bonus


def calculate_billingsley(games: List[GameResult]) -> Dict[str, float]:
    """Billingsley chain-reaction ratings.

    Order-dependent: for each game chronologically, the winner inherits
    a fraction of the loser's rating scaled by margin.  Earlier games
    cascade more because they feed into later transfers.  Opaque by design.
    """
    ratings: Dict[str, float] = {}
    for g in games:
        ratings.setdefault(g.home_team, 1.0)
        ratings.setdefault(g.away_team, 1.0)

    for g in games:
        if g.home_score == g.away_score:
            continue  # ties: no transfer
        if g.home_score > g.away_score:
            winner, loser = g.home_team, g.away_team
        else:
            winner, loser = g.away_team, g.home_team

        margin = abs(g.home_score - g.away_score)
        margin_factor = 1.0 + _BILLINGSLEY_MARGIN_K * margin
        transfer = ratings[loser] * _BILLINGSLEY_TRANSFER * margin_factor

        ratings[winner] += transfer
        ratings[loser] -= transfer * 0.5  # losers lose less than winners gain

    # Normalize so average = 1.0
    n = len(ratings)
    if n > 0:
        avg_r = sum(ratings.values()) / n
        if avg_r > 0:
            ratings = {t: r / avg_r for t, r in ratings.items()}

    return ratings


# ---------------------------------------------------------------------------
# 22. Dokter Entropy
# ---------------------------------------------------------------------------

_ENTROPY_BIN_SIZE = 5  # bin margins in 5-point buckets


def calculate_entropy(games: List[GameResult]) -> Dict[str, float]:
    """Dokter Entropy — information entropy of margin distribution.

    Lower entropy = more consistent/predictable outcomes.
    Rating = win_pct × (1 / (1 + entropy)).
    Consistent winners rank highest; unpredictable teams are penalized.
    """
    margins: Dict[str, List[float]] = {}
    wins: Dict[str, float] = {}
    total: Dict[str, int] = {}
    for g in games:
        for t in (g.home_team, g.away_team):
            margins.setdefault(t, [])
            wins.setdefault(t, 0.0)
            total.setdefault(t, 0)
        margin_h = g.home_score - g.away_score
        margins[g.home_team].append(margin_h)
        margins[g.away_team].append(-margin_h)
        total[g.home_team] += 1
        total[g.away_team] += 1
        if g.home_score > g.away_score:
            wins[g.home_team] += 1.0
        elif g.away_score > g.home_score:
            wins[g.away_team] += 1.0
        else:
            wins[g.home_team] += 0.5
            wins[g.away_team] += 0.5

    result: Dict[str, float] = {}
    for t in margins:
        # Build histogram of binned margins
        bins: Dict[int, int] = {}
        for m in margins[t]:
            b = int(m // _ENTROPY_BIN_SIZE)
            bins[b] = bins.get(b, 0) + 1

        # Shannon entropy
        n = len(margins[t])
        if n == 0:
            result[t] = 0.0
            continue
        entropy = 0.0
        for count in bins.values():
            p = count / n
            if p > 0:
                entropy -= p * math.log2(p)

        win_pct = wins[t] / total[t] if total[t] > 0 else 0.0
        result[t] = win_pct / (1.0 + entropy)

    return result


# ---------------------------------------------------------------------------
# 23. PageRank
# ---------------------------------------------------------------------------

_PAGERANK_DAMPING = 0.85


def calculate_pagerank(
    games: List[GameResult],
    max_iterations: int = 200,
) -> Dict[str, float]:
    """PageRank on the win/loss graph.

    Directed graph: each win creates a link FROM the loser TO the winner.
    Teams beaten by many highly-ranked teams accumulate authority.
    Standard PageRank with damping factor 0.85.
    """
    all_teams: set = set()
    # outlinks[loser] = list of winners (teams they lost to)
    outlinks: Dict[str, List[str]] = {}
    for g in games:
        all_teams.add(g.home_team)
        all_teams.add(g.away_team)
        if g.home_score > g.away_score:
            outlinks.setdefault(g.away_team, []).append(g.home_team)
        elif g.away_score > g.home_score:
            outlinks.setdefault(g.home_team, []).append(g.away_team)

    teams = list(all_teams)
    n = len(teams)
    if n == 0:
        return {}

    # Initialize uniform
    pr = {t: 1.0 / n for t in teams}

    for _ in range(max_iterations):
        new_pr: Dict[str, float] = {}
        # Compute incoming PageRank for each team
        incoming: Dict[str, float] = {t: 0.0 for t in teams}
        for src in teams:
            links = outlinks.get(src, [])
            if links:
                share = pr[src] / len(links)
                for dst in links:
                    incoming[dst] += share
            # else: dangling node — distribute uniformly (handled by base)

        # Dangling mass: teams with no outlinks (never lost, or ties only)
        dangling_mass = sum(
            pr[t] for t in teams if not outlinks.get(t)
        )

        for t in teams:
            new_pr[t] = (
                (1.0 - _PAGERANK_DAMPING) / n
                + _PAGERANK_DAMPING * (incoming[t] + dangling_mass / n)
            )

        max_delta = max(abs(new_pr[t] - pr[t]) for t in teams)
        pr = new_pr
        if max_delta < 1e-10:
            break

    return pr


# ---------------------------------------------------------------------------
# 24. CFQI (Team Coefficients)
# ---------------------------------------------------------------------------

def calculate_cfqi(
    games: List[GameResult],
    team_conferences: Optional[Dict[str, str]] = None,
    max_iterations: int = 200,
) -> Dict[str, float]:
    """CFQI — SRS with margin capping and conference-strength adjustment.

    Like SRS but:
    (a) margin capped at ±21 (blowouts don't dominate)
    (b) conference bonus = 0.05 × conference non-conference win%
    """
    conferences = team_conferences or {}

    teams: List[str] = []
    team_idx: Dict[str, int] = {}
    for g in games:
        for t in (g.home_team, g.away_team):
            if t not in team_idx:
                team_idx[t] = len(teams)
                teams.append(t)
    n = len(teams)
    if n == 0:
        return {}

    # Accumulate capped margins and opponents
    margin_sum = [0.0] * n
    game_count = [0] * n
    opponents: List[List[int]] = [[] for _ in range(n)]

    for g in games:
        hi, ai = team_idx[g.home_team], team_idx[g.away_team]
        margin = g.home_score - g.away_score
        margin = max(-21.0, min(21.0, margin))  # cap
        margin_sum[hi] += margin
        margin_sum[ai] -= margin
        game_count[hi] += 1
        game_count[ai] += 1
        opponents[hi].append(ai)
        opponents[ai].append(hi)

    avg_margin = [
        margin_sum[i] / game_count[i] if game_count[i] > 0 else 0.0
        for i in range(n)
    ]

    # Conference strength bonus: non-conference W% of conference members
    conf_nc_win_pct: Dict[str, float] = {}
    if conferences:
        # Build conference non-conf records
        conf_nc_wins: Dict[str, int] = {}
        conf_nc_games: Dict[str, int] = {}
        for g in games:
            h_conf = conferences.get(g.home_team, "")
            a_conf = conferences.get(g.away_team, "")
            if h_conf and a_conf and h_conf == a_conf:
                continue  # conference game, skip
            if h_conf:
                conf_nc_games[h_conf] = conf_nc_games.get(h_conf, 0) + 1
                if g.home_score > g.away_score:
                    conf_nc_wins[h_conf] = conf_nc_wins.get(h_conf, 0) + 1
            if a_conf:
                conf_nc_games[a_conf] = conf_nc_games.get(a_conf, 0) + 1
                if g.away_score > g.home_score:
                    conf_nc_wins[a_conf] = conf_nc_wins.get(a_conf, 0) + 1
        for conf in conf_nc_games:
            total = conf_nc_games[conf]
            conf_nc_win_pct[conf] = conf_nc_wins.get(conf, 0) / total if total > 0 else 0.5

    conf_bonus = [0.0] * n
    for i, t in enumerate(teams):
        conf = conferences.get(t, "")
        if conf and conf in conf_nc_win_pct:
            conf_bonus[i] = 0.05 * conf_nc_win_pct[conf]

    # Iterate SRS-style
    srs = [0.0] * n
    for _ in range(max_iterations):
        new_srs = [0.0] * n
        for i in range(n):
            if not opponents[i]:
                new_srs[i] = avg_margin[i] + conf_bonus[i]
                continue
            opp_avg = sum(srs[j] for j in opponents[i]) / len(opponents[i])
            new_srs[i] = avg_margin[i] + opp_avg + conf_bonus[i]
        mean_srs = sum(new_srs) / n if n > 0 else 0.0
        new_srs = [x - mean_srs for x in new_srs]
        max_delta = max(abs(new_srs[i] - srs[i]) for i in range(n))
        srs = new_srs
        if max_delta < 1e-10:
            break

    return {teams[i]: srs[i] for i in range(n)}


# ---------------------------------------------------------------------------
# 25. Game Control (requires TeamSeasonStats)
# ---------------------------------------------------------------------------

def calculate_game_control(
    team_stats: Dict[str, TeamSeasonStats],
) -> Dict[str, float]:
    """Average fraction of game time spent in the lead.

    Pre-computed by the Season class and passed via TeamSeasonStats.
    """
    return {t: s.game_control_avg for t, s in team_stats.items()}


# ---------------------------------------------------------------------------
# 26. CVL Official (pass-through)
# ---------------------------------------------------------------------------

def calculate_cvl_official(
    team_stats: Dict[str, TeamSeasonStats],
) -> Dict[str, float]:
    """CVL Official Power Index — pass-through from season.py."""
    return {t: s.power_index for t, s in team_stats.items()}


# ---------------------------------------------------------------------------
# SOS (Elo-based, not RPI)
# ---------------------------------------------------------------------------

def calculate_sos(
    games: List[GameResult],
    elos: Dict[str, float],
) -> Dict[str, Tuple[float, float, float]]:
    """Rating-based Strength of Schedule.

    Returns dict of team -> (overall_sos, sos_wins, sos_losses) where:
        overall_sos = average Elo of all opponents
        sos_wins = average Elo of opponents beaten
        sos_losses = average Elo of opponents lost to

    This does NOT penalize conferences for playing each other because
    strength is measured by the opponent's own Elo rating, not their win%.
    """
    opp_elos: Dict[str, List[float]] = {}
    win_opp_elos: Dict[str, List[float]] = {}
    loss_opp_elos: Dict[str, List[float]] = {}

    for g in games:
        h, a = g.home_team, g.away_team
        h_elo = elos.get(h, _DEFAULT_ELO)
        a_elo = elos.get(a, _DEFAULT_ELO)

        opp_elos.setdefault(h, []).append(a_elo)
        opp_elos.setdefault(a, []).append(h_elo)

        if g.home_score > g.away_score:
            win_opp_elos.setdefault(h, []).append(a_elo)
            loss_opp_elos.setdefault(a, []).append(h_elo)
        elif g.away_score > g.home_score:
            win_opp_elos.setdefault(a, []).append(h_elo)
            loss_opp_elos.setdefault(h, []).append(a_elo)

    result: Dict[str, Tuple[float, float, float]] = {}
    for team in opp_elos:
        overall = sum(opp_elos[team]) / len(opp_elos[team]) if opp_elos[team] else _DEFAULT_ELO
        w_sos = sum(win_opp_elos.get(team, [])) / len(win_opp_elos[team]) if win_opp_elos.get(team) else 0.0
        l_sos = sum(loss_opp_elos.get(team, [])) / len(loss_opp_elos[team]) if loss_opp_elos.get(team) else 0.0
        result[team] = (overall, w_sos, l_sos)

    return result


# ---------------------------------------------------------------------------
# Composite Ranking
# ---------------------------------------------------------------------------

def _rank_by_rating(
    ratings: Dict[str, float],
    descending: bool = True,
) -> Dict[str, int]:
    """Convert ratings dict to rank dict (1 = best)."""
    sorted_teams = sorted(
        ratings.keys(),
        key=lambda t: ratings[t],
        reverse=descending,
    )
    return {t: rank + 1 for rank, t in enumerate(sorted_teams)}


def calculate_composite(
    games: List[GameResult],
    initial_elos: Optional[Dict[str, float]] = None,
    team_conferences: Optional[Dict[str, str]] = None,
    team_stats: Optional[Dict[str, TeamSeasonStats]] = None,
) -> List[CompositeRanking]:
    """Run all ranking methods and produce a composite ranking.

    Args:
        games: All completed games in chronological order.
        initial_elos: Optional starting Elo ratings (e.g. from prior season).
        team_conferences: Optional team -> conference mapping.
        team_stats: Optional per-team season stats for efficiency/Viperball
            methods (15-19, 25-26).  If not provided, those methods are
            excluded from the composite.

    Returns:
        List of CompositeRanking objects sorted by composite rank.
    """
    if not games:
        return []

    conferences = team_conferences or {}
    stats = team_stats or {}

    # Collect all teams
    all_teams: set = set()
    for g in games:
        all_teams.add(g.home_team)
        all_teams.add(g.away_team)

    # Build win/loss records
    records: Dict[str, Tuple[int, int]] = {t: (0, 0) for t in all_teams}
    for g in games:
        if g.home_score > g.away_score:
            w, l = records[g.home_team]
            records[g.home_team] = (w + 1, l)
            w, l = records[g.away_team]
            records[g.away_team] = (w, l + 1)
        elif g.away_score > g.home_score:
            w, l = records[g.away_team]
            records[g.away_team] = (w + 1, l)
            w, l = records[g.home_team]
            records[g.home_team] = (w, l + 1)

    n_teams = len(all_teams)

    # ── Core Math (1-6) ──────────────────────────────────────────────────
    elos = calculate_elo(games, initial_elos)
    colley = calculate_colley(games)
    massey = calculate_massey(games)
    bt = calculate_bradley_terry(games)
    sor = calculate_sor(games, elos)
    srs = calculate_srs(games)

    # ── Simple (7-10) ────────────────────────────────────────────────────
    win_pct = calculate_win_pct(games)
    point_diff = calculate_point_diff(games)
    pythag = calculate_pythagorean(games)
    sos_win_pct = calculate_sos_adjusted_win_pct(games, elos)

    # ── Elo Variants (11-12) ─────────────────────────────────────────────
    elo_recent = calculate_elo_recent(games, initial_elos)
    round_robin = calculate_round_robin(elos)

    # ── Resume (13-14) ───────────────────────────────────────────────────
    isov = calculate_isov(games)
    resume = calculate_resume(games, elos)

    # ── Controversial (21-23) ────────────────────────────────────────────
    billingsley = calculate_billingsley(games)
    entropy = calculate_entropy(games)
    pagerank = calculate_pagerank(games)

    # ── Margin Compression (20) ──────────────────────────────────────────
    margin_comp = calculate_margin_compression(games)

    # ── Meta (24) ────────────────────────────────────────────────────────
    cfqi = calculate_cfqi(games, team_conferences)

    # ── SOS (metadata, not a ranking method) ─────────────────────────────
    sos_data = calculate_sos(games, elos)

    # ── Build ratings dict: key -> {team: rating} ────────────────────────
    all_ratings: Dict[str, Dict[str, float]] = {
        "elo": elos,
        "colley": colley,
        "massey": massey,
        "bt": bt,
        "sor": sor,
        "srs": srs,
        "win_pct": win_pct,
        "point_diff": point_diff,
        "pythag": pythag,
        "sos_win_pct": sos_win_pct,
        "elo_recent": elo_recent,
        "round_robin": round_robin,
        "isov": isov,
        "resume": resume,
        "billingsley": billingsley,
        "entropy": entropy,
        "pagerank": pagerank,
        "margin_comp": margin_comp,
        "cfqi": cfqi,
    }

    # ── Season-stats methods (only if team_stats provided) ───────────────
    if stats:
        all_ratings["off_eff"] = calculate_off_efficiency(stats)
        all_ratings["def_eff"] = calculate_def_efficiency(stats)
        all_ratings["fpi"] = calculate_fpi(stats, sos_data)
        all_ratings["dye_index"] = calculate_dye_index(stats)
        all_ratings["comeback"] = calculate_comeback(stats)
        all_ratings["game_control"] = calculate_game_control(stats)
        all_ratings["cvl_official"] = calculate_cvl_official(stats)

    # ── Convert all ratings to ranks ─────────────────────────────────────
    all_ranks: Dict[str, Dict[str, int]] = {}
    for key, ratings in all_ratings.items():
        all_ranks[key] = _rank_by_rating(ratings, descending=True)

    active_keys = list(all_ratings.keys())

    # ── Build composite rankings ─────────────────────────────────────────
    composites: List[CompositeRanking] = []

    for team in all_teams:
        method_ranks: Dict[str, int] = {}
        method_ratings: Dict[str, float] = {}
        rank_list: List[int] = []

        for key in active_keys:
            r = all_ranks[key].get(team, n_teams)
            method_ranks[key] = r
            method_ratings[key] = round(all_ratings[key].get(team, 0.0), 4)
            rank_list.append(r)

        n_methods = len(rank_list)
        mean_r = sum(rank_list) / n_methods if n_methods > 0 else n_teams
        sorted_ranks = sorted(rank_list)
        if n_methods % 2 == 0:
            mid = n_methods // 2
            median_r = (sorted_ranks[mid - 1] + sorted_ranks[mid]) / 2.0
        else:
            median_r = float(sorted_ranks[n_methods // 2])
        variance = sum((r - mean_r) ** 2 for r in rank_list) / n_methods if n_methods > 0 else 0.0
        std = math.sqrt(variance)

        sos_overall, sos_w, sos_l = sos_data.get(team, (_DEFAULT_ELO, 0, 0))
        w, l = records.get(team, (0, 0))

        composites.append(CompositeRanking(
            team=team,
            composite_rank=0,  # filled below
            mean_rank=round(mean_r, 2),
            median_rank=round(median_r, 1),
            std_dev=round(std, 2),
            method_ranks=method_ranks,
            method_ratings=method_ratings,
            # Legacy fields (Core Math 6)
            elo_rank=method_ranks.get("elo", n_teams),
            elo_rating=round(elos.get(team, _DEFAULT_ELO), 1),
            colley_rank=method_ranks.get("colley", n_teams),
            colley_rating=round(colley.get(team, 0.5), 4),
            massey_rank=method_ranks.get("massey", n_teams),
            massey_rating=round(massey.get(team, 0), 2),
            bt_rank=method_ranks.get("bt", n_teams),
            bt_rating=round(bt.get(team, 1.0), 4),
            sor_rank=method_ranks.get("sor", n_teams),
            sor_rating=round(sor.get(team, 0.5), 4),
            srs_rank=method_ranks.get("srs", n_teams),
            srs_rating=round(srs.get(team, 0), 2),
            sos=round(sos_overall, 1),
            sos_w=round(sos_w, 1),
            sos_l=round(sos_l, 1),
            wins=w,
            losses=l,
            conference=conferences.get(team, ""),
        ))

    # Sort by mean rank (ascending = better)
    composites.sort(key=lambda c: c.mean_rank)
    for i, c in enumerate(composites):
        c.composite_rank = i + 1

    return composites
