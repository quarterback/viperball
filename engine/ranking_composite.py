"""Viperball Ranking Composite System.

Implements multiple independent ranking algorithms inspired by the Massey
Composite for college football.  Each method produces a 1-N ordering; the
composite ranking is the average rank across all methods.

Algorithms implemented:
    1. Elo Ratings       — Adaptive, margin-aware, game-by-game
    2. Colley Matrix     — Pure W/L, no margin, no preseason bias
    3. Massey Ratings    — Least-squares on (truncated) score differentials
    4. Bradley-Terry/MOV — Margin-of-victory with iterative pairwise model
    5. Strength of Record— Resume metric: how hard was it to get your record?
    6. Simple Rating Sys — avg_margin + avg(opponent SRS), iterative

References:
    - Kenneth Massey's Ranking Composite (masseyratings.com)
    - Colley Matrix (colleyratings.com)
    - CFQI v2 (College Football Quality Index)
    - Kislanko ISOV ratings
    - Wobus MOV / Bradley-Terry model
    - Sorensen's ranking methods overview
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
class TeamRanking:
    """A team's ranking from a single method."""
    team: str
    rank: int
    rating: float  # raw rating value from the method


@dataclass
class CompositeRanking:
    """A team's composite ranking across all methods."""
    team: str
    composite_rank: int
    mean_rank: float
    median_rank: float
    std_dev: float
    # Individual method ranks
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
) -> List[CompositeRanking]:
    """Run all ranking methods and produce a composite ranking.

    Args:
        games: All completed games in chronological order.
        initial_elos: Optional starting Elo ratings (e.g. from prior season).
        team_conferences: Optional team -> conference mapping.

    Returns:
        List of CompositeRanking objects sorted by composite rank.
    """
    if not games:
        return []

    conferences = team_conferences or {}

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

    # --- Run all ranking methods ---
    elos = calculate_elo(games, initial_elos)
    colley = calculate_colley(games)
    massey = calculate_massey(games)
    bt = calculate_bradley_terry(games)
    sor = calculate_sor(games, elos)
    srs = calculate_srs(games)

    # Convert to ranks
    elo_ranks = _rank_by_rating(elos, descending=True)
    colley_ranks = _rank_by_rating(colley, descending=True)
    massey_ranks = _rank_by_rating(massey, descending=True)
    bt_ranks = _rank_by_rating(bt, descending=True)
    sor_ranks = _rank_by_rating(sor, descending=True)
    srs_ranks = _rank_by_rating(srs, descending=True)

    # SOS (Elo-based)
    sos_data = calculate_sos(games, elos)

    # --- Build composite ---
    n_teams = len(all_teams)
    composites: List[CompositeRanking] = []

    for team in all_teams:
        ranks = [
            elo_ranks.get(team, n_teams),
            colley_ranks.get(team, n_teams),
            massey_ranks.get(team, n_teams),
            bt_ranks.get(team, n_teams),
            sor_ranks.get(team, n_teams),
            srs_ranks.get(team, n_teams),
        ]
        mean_r = sum(ranks) / len(ranks)
        sorted_ranks = sorted(ranks)
        median_r = (sorted_ranks[2] + sorted_ranks[3]) / 2.0  # median of 6
        variance = sum((r - mean_r) ** 2 for r in ranks) / len(ranks)
        std = math.sqrt(variance)

        sos_overall, sos_w, sos_l = sos_data.get(team, (_DEFAULT_ELO, 0, 0))
        w, l = records.get(team, (0, 0))

        composites.append(CompositeRanking(
            team=team,
            composite_rank=0,  # filled below
            mean_rank=round(mean_r, 2),
            median_rank=round(median_r, 1),
            std_dev=round(std, 2),
            elo_rank=elo_ranks.get(team, n_teams),
            elo_rating=round(elos.get(team, _DEFAULT_ELO), 1),
            colley_rank=colley_ranks.get(team, n_teams),
            colley_rating=round(colley.get(team, 0.5), 4),
            massey_rank=massey_ranks.get(team, n_teams),
            massey_rating=round(massey.get(team, 0), 2),
            bt_rank=bt_ranks.get(team, n_teams),
            bt_rating=round(bt.get(team, 1.0), 4),
            sor_rank=sor_ranks.get(team, n_teams),
            sor_rating=round(sor.get(team, 0.5), 4),
            srs_rank=srs_ranks.get(team, n_teams),
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
