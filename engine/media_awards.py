"""
Viperball Media Awards — Postseason Edition

Seven named awards from four media outlets, generated AFTER the postseason
(unlike the regular-season-only institutional awards in awards.py).

─────────────────────────────────────────────────────────────────────
MEDIA OUTLETS & AWARDS
─────────────────────────────────────────────────────────────────────

  Associated Press (AP)
    · AP National Viperball Player of the Year

  United Press International (UPI)
    · UPI National Player of the Year
    · UPI Defensive Player of the Year

  The Lateral Magazine
    · The Lateral National Freshman of the Year

  The Sporting News (TSN)
    · TSN National Player of the Year
    · TSN Defensive Player of the Year
    · TSN Comeback Player of the Year

─────────────────────────────────────────────────────────────────────
DESIGN PRINCIPLES
─────────────────────────────────────────────────────────────────────

  • None of these awards use WPA. They rely on raw stats, opponent
    quality, and narrative factors described per-award.
  • Divergence is the point — four outlets occasionally produce four
    different winners.  When they agree, the player was obviously best.
  • Games played floor: 60% of schedule (50% for Comeback).
  • Postseason performance is included for TSN awards.

Usage:
    from engine.media_awards import compute_media_awards
    media = compute_media_awards(season, year)
    # Returns list[dict], each with award_name, player_name, team_name, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from engine.season import Season


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _pos_group(position: str) -> str:
    pos = position.lower()
    if "zeroback" in pos or "zero" in pos:
        return "zeroback"
    if "viper" in pos:
        return "viper"
    if any(p in pos for p in ["halfback", "wingback", "shiftback", "flanker", "slotback"]):
        return "back"
    if "lineman" in pos or "line" in pos or "wedge" in pos:
        return "lineman"
    if "safety" in pos or "keeper" in pos:
        return "safety"
    return "other"


def _is_offensive(group: str) -> bool:
    return group in ("zeroback", "viper", "back")


def _is_defensive(group: str) -> bool:
    return group in ("lineman", "safety")


_AGG_COUNTING_STATS = [
    "touches", "yards", "rushing_yards", "rush_carries",
    "tds", "rushing_tds", "fumbles", "lateral_yards",
    "laterals_thrown", "lateral_assists",
    "kick_att", "kick_made",
    "kick_passes_thrown", "kick_passes_completed",
    "kick_pass_yards", "kick_pass_tds",
    "kick_pass_interceptions",
    "tackles", "tfl", "sacks", "hurries",
    "keeper_bells", "kick_deflections",
    "kick_return_yards", "punt_return_yards",
    "plays_involved",
]


def _init_player_stats(p: dict) -> dict:
    d = {s: 0 for s in _AGG_COUNTING_STATS}
    d.update({
        "games": 0,
        "tag": p.get("tag", ""),
        "position": p.get("position", ""),
        "year_in_school": "",
    })
    return d


def _accumulate(a: dict, p: dict):
    a["games"] += 1
    if not a["tag"]:
        a["tag"] = p.get("tag", "")
    if not a.get("position"):
        a["position"] = p.get("position", "")
    for stat in _AGG_COUNTING_STATS:
        a[stat] += p.get(stat, 0)


# ──────────────────────────────────────────────
# STAT AGGREGATION (regular + postseason split)
# ──────────────────────────────────────────────

def _aggregate_stats(season, include_postseason: bool = True):
    """Aggregate player stats.

    Returns:
      full_agg  — {team: {player: stats}} across all included games
      vs_winning — {team: {player: stats}} only from games against above-.500 teams
      postseason_agg — {team: {player: stats}} from playoff games only
    """
    standings = season.standings

    # Determine winning-record teams
    winning_teams = set()
    for team_name, rec in standings.items():
        total = rec.wins + rec.losses
        if total > 0 and rec.wins / total > 0.500:
            winning_teams.add(team_name)

    full_agg: Dict[str, Dict[str, dict]] = {}
    vs_winning: Dict[str, Dict[str, dict]] = {}
    postseason_agg: Dict[str, Dict[str, dict]] = {}

    def _process_game(game, target, opponent_filter=None):
        if not game.completed or not getattr(game, "full_result", None):
            return
        fr = game.full_result
        ps = fr.get("player_stats", {})
        for side, team_name in [("home", game.home_team), ("away", game.away_team)]:
            opp = game.away_team if side == "home" else game.home_team
            if opponent_filter and opp not in opponent_filter:
                continue
            if team_name not in target:
                target[team_name] = {}
            for p in ps.get(side, []):
                name = p.get("name", "")
                if not name:
                    continue
                if name not in target[team_name]:
                    target[team_name][name] = _init_player_stats(p)
                _accumulate(target[team_name][name], p)

    # Regular season
    for game in season.schedule:
        _process_game(game, full_agg)
        _process_game(game, vs_winning, opponent_filter=winning_teams)

    # Postseason
    if include_postseason:
        for game in getattr(season, 'playoff_bracket', []):
            _process_game(game, full_agg)
            _process_game(game, postseason_agg)
            _process_game(game, vs_winning, opponent_filter=winning_teams)

    return full_agg, vs_winning, postseason_agg


def _get_team_schedule_len(season, team_name: str) -> int:
    """Count completed regular season games for a team."""
    n = 0
    for g in season.schedule:
        if g.completed and team_name in (g.home_team, g.away_team):
            n += 1
    return n


def _team_made_playoffs(season, team_name: str) -> bool:
    for g in getattr(season, 'playoff_bracket', []):
        if team_name in (g.home_team, g.away_team):
            return True
    return False


def _team_is_conf_champ(season, team_name: str) -> bool:
    conf_champs = season.get_conference_champions() if hasattr(season, 'get_conference_champions') else {}
    return team_name in set(conf_champs.values())


def _team_win_pct(team_name: str, standings: dict) -> float:
    rec = standings.get(team_name)
    if rec is None:
        return 0.5
    total = rec.wins + rec.losses
    return rec.wins / total if total > 0 else 0.5


def _team_wins(team_name: str, standings: dict) -> int:
    rec = standings.get(team_name)
    return rec.wins if rec else 0


def _count_winning_opponents_faced(season, team_name: str, standings: dict) -> int:
    """Count how many opponents with winning records this team played."""
    winning_teams = set()
    for tn, rec in standings.items():
        total = rec.wins + rec.losses
        if total > 0 and rec.wins / total > 0.500:
            winning_teams.add(tn)
    count = 0
    for g in season.schedule:
        if not g.completed:
            continue
        if g.home_team == team_name and g.away_team in winning_teams:
            count += 1
        elif g.away_team == team_name and g.home_team in winning_teams:
            count += 1
    return count


# ──────────────────────────────────────────────
# AWARD-SPECIFIC SCORING FUNCTIONS
# ──────────────────────────────────────────────

def _ap_score(stats: dict, group: str, team_wp: float) -> float:
    """AP Player of the Year scoring.

    Biased toward Zerobacks/Vipers. Rewards raw production and winning.
    Team record weighted heavily.
    """
    games = max(1, stats.get("games", 1))

    if group == "zeroback":
        kp_yds = stats.get("kick_pass_yards", 0)
        kp_tds = stats.get("kick_pass_tds", 0)
        kp_comp = stats.get("kick_passes_completed", 0)
        kp_att = max(1, stats.get("kick_passes_thrown", 1))
        rush_yds = stats.get("rushing_yards", 0)
        tds = stats.get("tds", 0)
        kp_pct = kp_comp / kp_att
        raw = (kp_yds * 0.45 + rush_yds * 0.25 + tds * 20 + kp_tds * 15
               + kp_pct * 25) / games
        # Position bias: Zerobacks get AP love
        raw *= 1.10
    elif group == "viper":
        yds = stats.get("yards", 0)
        tds = stats.get("tds", 0)
        lat_yds = stats.get("lateral_yards", 0)
        kr_yds = stats.get("kick_return_yards", 0)
        pr_yds = stats.get("punt_return_yards", 0)
        raw = ((yds + kr_yds + pr_yds) * 0.35 + lat_yds * 0.2 + tds * 22) / games
        # Position bias: Vipers also get AP attention
        raw *= 1.05
    elif group == "back":
        rush_yds = stats.get("rushing_yards", 0)
        tds = stats.get("tds", 0)
        carries = max(1, stats.get("rush_carries", 1))
        ypc = rush_yds / carries
        raw = (rush_yds * 0.4 + ypc * 10 + tds * 22) / games
    else:
        # Defensive players rarely win AP, but possible
        tackles = stats.get("tackles", 0)
        sacks = stats.get("sacks", 0)
        tfl = stats.get("tfl", 0)
        raw = (tackles * 2.5 + sacks * 14 + tfl * 7) / games
        # AP depresses defensive candidates
        raw *= 0.80

    # Team record multiplier — AP weights winning very heavily
    # Sub-.500 requires historically exceptional numbers
    team_mult = 0.5 + team_wp * 0.6
    team_mult = min(1.15, max(0.50, team_mult))

    return round(raw * team_mult, 2)


def _upi_player_score(stats: dict, group: str, team_wp: float) -> float:
    """UPI Player of the Year scoring.

    More position-neutral. Lower team record threshold.
    Rewards conference-level dominance. Numbers-first.
    """
    games = max(1, stats.get("games", 1))

    if group == "zeroback":
        kp_yds = stats.get("kick_pass_yards", 0)
        kp_tds = stats.get("kick_pass_tds", 0)
        rush_yds = stats.get("rushing_yards", 0)
        tds = stats.get("tds", 0)
        raw = (kp_yds * 0.35 + rush_yds * 0.25 + tds * 18 + kp_tds * 14) / games
    elif group == "viper":
        yds = stats.get("yards", 0)
        tds = stats.get("tds", 0)
        lat_yds = stats.get("lateral_yards", 0)
        raw = (yds * 0.35 + lat_yds * 0.25 + tds * 20) / games
    elif group == "back":
        rush_yds = stats.get("rushing_yards", 0)
        tds = stats.get("tds", 0)
        carries = max(1, stats.get("rush_carries", 1))
        ypc = rush_yds / carries
        raw = (rush_yds * 0.4 + ypc * 8 + tds * 20) / games
    else:
        # UPI more willing to reward defensive players
        tackles = stats.get("tackles", 0)
        sacks = stats.get("sacks", 0)
        tfl = stats.get("tfl", 0)
        hurries = stats.get("hurries", 0)
        raw = (tackles * 2.5 + sacks * 13 + tfl * 7 + hurries * 3) / games
        # UPI only mildly depresses defensive candidates
        raw *= 0.92

    # Softer team record weight — 7-5 team can produce a winner
    team_mult = 0.65 + team_wp * 0.40
    team_mult = min(1.10, max(0.60, team_mult))

    return round(raw * team_mult, 2)


def _upi_defense_score(stats: dict, team_wp: float) -> float:
    """UPI Defensive Player of the Year — co-equal award, not consolation."""
    games = max(1, stats.get("games", 1))
    tackles = stats.get("tackles", 0)
    sacks = stats.get("sacks", 0)
    tfl = stats.get("tfl", 0)
    hurries = stats.get("hurries", 0)
    bells = stats.get("keeper_bells", 0)
    deflections = stats.get("kick_deflections", 0)
    raw = (tackles * 2.5 + sacks * 14 + tfl * 7 + hurries * 4
           + bells * 5 + deflections * 6) / games

    # UPI DPOY has minimal team record weight
    team_mult = 0.75 + team_wp * 0.30
    return round(raw * min(1.10, max(0.70, team_mult)), 2)


def _lateral_freshman_score(stats: dict, group: str, team_wp: float,
                            team_impact: float) -> float:
    """The Lateral National Freshman of the Year.

    Analytical, contrarian. Rewards freshmen who changed what was
    possible for their team over freshmen who produced on already-good teams.
    """
    games = max(1, stats.get("games", 1))

    if group == "zeroback":
        kp_yds = stats.get("kick_pass_yards", 0)
        tds = stats.get("tds", 0)
        raw = (kp_yds * 0.35 + tds * 18) / games
    elif group == "viper":
        yds = stats.get("yards", 0)
        tds = stats.get("tds", 0)
        raw = (yds * 0.35 + tds * 20) / games
    elif group == "back":
        rush_yds = stats.get("rushing_yards", 0)
        tds = stats.get("tds", 0)
        raw = (rush_yds * 0.4 + tds * 20) / games
    else:
        tackles = stats.get("tackles", 0)
        sacks = stats.get("sacks", 0)
        tfl = stats.get("tfl", 0)
        raw = (tackles * 2.5 + sacks * 14 + tfl * 7) / games

    # The Lateral weight: "did this player change what was possible?"
    # Penalize freshmen on teams that would have won anyway (high wp),
    # reward freshmen who stepped into big roles on middling teams
    # team_impact is touches / team_total_touches — how central was the freshman?
    narrative_mult = 1.0
    if team_wp > 0.75:
        # Great team — freshman was helpful but not transformative
        narrative_mult = 0.90
    elif team_wp < 0.45:
        # Bad team — freshman was there, team still lost
        narrative_mult = 0.85
    else:
        # Competitive team where freshman made the difference
        narrative_mult = 1.05 + team_impact * 0.3

    return round(raw * narrative_mult, 2)


def _tsn_player_score(stats: dict, group: str,
                      postseason_stats: Optional[dict],
                      made_playoffs: bool) -> float:
    """TSN Player of the Year.

    Drama and narrative. Postseason performance weighted 2x.
    Rewards the player whose season had the best story.
    """
    games = max(1, stats.get("games", 1))

    if group == "zeroback":
        kp_yds = stats.get("kick_pass_yards", 0)
        kp_tds = stats.get("kick_pass_tds", 0)
        rush_yds = stats.get("rushing_yards", 0)
        tds = stats.get("tds", 0)
        raw = (kp_yds * 0.35 + rush_yds * 0.25 + tds * 18 + kp_tds * 14) / games
    elif group == "viper":
        yds = stats.get("yards", 0)
        tds = stats.get("tds", 0)
        lat_yds = stats.get("lateral_yards", 0)
        raw = (yds * 0.35 + lat_yds * 0.2 + tds * 20) / games
    elif group == "back":
        rush_yds = stats.get("rushing_yards", 0)
        tds = stats.get("tds", 0)
        raw = (rush_yds * 0.4 + tds * 22) / games
    else:
        tackles = stats.get("tackles", 0)
        sacks = stats.get("sacks", 0)
        tfl = stats.get("tfl", 0)
        raw = (tackles * 2.5 + sacks * 13 + tfl * 7) / games
        raw *= 0.85  # TSN also biased toward offense for this award

    # Postseason bonus — 2x weight on postseason production
    if postseason_stats and postseason_stats.get("games", 0) > 0:
        ps_games = postseason_stats["games"]
        if group == "zeroback":
            ps_raw = (postseason_stats.get("kick_pass_yards", 0) * 0.35
                      + postseason_stats.get("tds", 0) * 18) / ps_games
        elif group == "viper":
            ps_raw = (postseason_stats.get("yards", 0) * 0.35
                      + postseason_stats.get("tds", 0) * 20) / ps_games
        elif group == "back":
            ps_raw = (postseason_stats.get("rushing_yards", 0) * 0.4
                      + postseason_stats.get("tds", 0) * 22) / ps_games
        else:
            ps_raw = (postseason_stats.get("tackles", 0) * 2.5
                      + postseason_stats.get("sacks", 0) * 13) / ps_games
        # Postseason counts 2x — blend with 2x weight
        total_games = games + ps_games
        raw = (raw * (games - ps_games) + ps_raw * 2 * ps_games) / total_games

    # No playoff = no TSN Player of the Year
    if not made_playoffs:
        raw *= 0.0  # TSN requires playoffs or conference championship

    return round(raw, 2)


def _tsn_defense_score(stats: dict, vs_winning_stats: Optional[dict],
                       postseason_stats: Optional[dict],
                       winning_opps_faced: int) -> float:
    """TSN Defensive Player of the Year.

    Most prestigious defensive media honor. Rewards dominance against
    good teams. Prefers pass rushers over volume tacklers.
    """
    games = max(1, stats.get("games", 1))
    tackles = stats.get("tackles", 0)
    sacks = stats.get("sacks", 0)
    tfl = stats.get("tfl", 0)
    hurries = stats.get("hurries", 0)
    bells = stats.get("keeper_bells", 0)

    # TSN biases toward impact defenders: sacks and TFL weighted heavily
    raw = (tackles * 1.5 + sacks * 16 + tfl * 8 + hurries * 4 + bells * 5) / games

    # Performance against winning teams bonus
    if vs_winning_stats and vs_winning_stats.get("games", 0) > 0:
        vw_games = vs_winning_stats["games"]
        vw_raw = (vs_winning_stats.get("tackles", 0) * 1.5
                  + vs_winning_stats.get("sacks", 0) * 16
                  + vs_winning_stats.get("tfl", 0) * 8
                  + vs_winning_stats.get("hurries", 0) * 4) / vw_games
        # Blend: weight vs-winning performance at 40%
        raw = raw * 0.6 + vw_raw * 0.4

    # Must have faced at least 6 winning opponents
    if winning_opps_faced < 6:
        raw *= 0.70

    # Postseason bonus
    if postseason_stats and postseason_stats.get("games", 0) > 0:
        ps_games = postseason_stats["games"]
        ps_raw = (postseason_stats.get("tackles", 0) * 1.5
                  + postseason_stats.get("sacks", 0) * 16
                  + postseason_stats.get("tfl", 0) * 8) / ps_games
        raw = raw * 0.8 + ps_raw * 0.2

    return round(raw, 2)


# ──────────────────────────────────────────────
# STAT LINE BUILDERS
# ──────────────────────────────────────────────

def _build_stat_line(stats: dict, group: str) -> str:
    parts = [f"{stats.get('games', 0)} GP"]
    if group == "zeroback":
        kp_comp = stats.get("kick_passes_completed", 0)
        kp_att = stats.get("kick_passes_thrown", 0)
        parts.append(f"{kp_comp}/{kp_att} KP")
        parts.append(f"{stats.get('kick_pass_yards', 0)} KP yds")
        parts.append(f"{stats.get('kick_pass_tds', 0)} KP TD")
        parts.append(f"{stats.get('tds', 0)} total TD")
    elif group == "viper":
        parts.append(f"{stats.get('yards', 0)} yds")
        parts.append(f"{stats.get('lateral_yards', 0)} lat yds")
        parts.append(f"{stats.get('tds', 0)} TD")
    elif group == "back":
        parts.append(f"{stats.get('rushing_yards', 0)} rush yds")
        parts.append(f"{stats.get('rush_carries', 0)} car")
        parts.append(f"{stats.get('tds', 0)} TD")
    else:
        parts.append(f"{stats.get('tackles', 0)} TKL")
        parts.append(f"{stats.get('sacks', 0)} sacks")
        parts.append(f"{stats.get('tfl', 0)} TFL")
    return " | ".join(parts)


def _build_stats_dict(stats: dict, group: str) -> dict:
    d = {"games": stats.get("games", 0)}
    if group == "zeroback":
        d["kick_passes_completed"] = stats.get("kick_passes_completed", 0)
        d["kick_passes_thrown"] = stats.get("kick_passes_thrown", 0)
        d["kick_pass_yards"] = stats.get("kick_pass_yards", 0)
        d["kick_pass_tds"] = stats.get("kick_pass_tds", 0)
        d["yards"] = stats.get("yards", 0)
        d["tds"] = stats.get("tds", 0)
    elif group == "viper":
        d["yards"] = stats.get("yards", 0)
        d["lateral_yards"] = stats.get("lateral_yards", 0)
        d["tds"] = stats.get("tds", 0)
    elif group == "back":
        d["rushing_yards"] = stats.get("rushing_yards", 0)
        d["rush_carries"] = stats.get("rush_carries", 0)
        d["tds"] = stats.get("tds", 0)
    else:
        d["tackles"] = stats.get("tackles", 0)
        d["sacks"] = stats.get("sacks", 0)
        d["tfl"] = stats.get("tfl", 0)
        d["hurries"] = stats.get("hurries", 0)
    return d


# ──────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────

def compute_media_awards(
    season: Season,
    year: int,
    conferences: Optional[Dict[str, list]] = None,
    prev_season_games: Optional[Dict[str, int]] = None,
) -> List[dict]:
    """Compute all 7 media awards after the postseason.

    Args:
        season: The completed season object with standings, schedule,
                playoff_bracket, and team rosters.
        year: The season year.
        conferences: {conf_name: [team_names]} for conference context.
        prev_season_games: {player_name: games_played_last_year} for
                           Comeback Player tracking (None if unavailable).

    Returns:
        List of award dicts, each with:
          award_name, outlet, player_name, team_name, position,
          year_in_school, overall_rating, reason, season_stats
    """
    standings = season.standings
    if not standings:
        return []

    teams = getattr(season, 'teams', {})
    if not teams:
        return []

    # Aggregate stats with regular+postseason and opponent-quality splits
    full_agg, vs_winning_agg, postseason_agg = _aggregate_stats(season, include_postseason=True)

    # Also need regular-season-only agg for games-played floor
    reg_agg, _, _ = _aggregate_stats(season, include_postseason=False)

    results: List[dict] = []
    seen: set = set()  # track winners to encourage divergence

    def _make_award(award_name: str, outlet: str, player, team_name: str,
                    stats: dict, group: str, reason: str = "") -> dict:
        return {
            "award_name": award_name,
            "outlet": outlet,
            "player_name": player.name,
            "team_name": team_name,
            "position": player.position,
            "year_in_school": getattr(player, "year", ""),
            "overall_rating": player.overall,
            "reason": reason if reason else _build_stat_line(stats, group),
            "season_stats": _build_stats_dict(stats, group),
        }

    # ── 1. AP National Viperball Player of the Year ──────────────
    # Winning record required. Biased toward ZB/Viper. Raw production.
    best_ap = None
    best_ap_score = -1.0
    for t_name, team in teams.items():
        wp = _team_win_pct(t_name, standings)
        if wp < 0.500:
            continue
        schedule_len = _get_team_schedule_len(season, t_name)
        for p in team.players:
            group = _pos_group(p.position)
            stats = full_agg.get(t_name, {}).get(p.name)
            if not stats or stats.get("games", 0) == 0:
                continue
            # 60% games played floor
            if stats["games"] < schedule_len * 0.60:
                continue
            # AP tiebreaker: conference play success (use team wp)
            s = _ap_score(stats, group, wp)
            # Bonus for opponents: production vs winning teams
            vw_stats = vs_winning_agg.get(t_name, {}).get(p.name)
            if vw_stats and vw_stats.get("games", 0) > 0:
                vw_games = vw_stats["games"]
                vw_yds = vw_stats.get("yards", 0) + vw_stats.get("kick_pass_yards", 0)
                vw_tds = vw_stats.get("tds", 0)
                s += (vw_yds * 0.05 + vw_tds * 3) / vw_games
            if s > best_ap_score:
                best_ap_score = s
                best_ap = (p, t_name, stats, group)

    if best_ap:
        p, t_name, stats, group = best_ap
        results.append(_make_award(
            "AP National Viperball Player of the Year", "Associated Press",
            p, t_name, stats, group))
        seen.add(f"{t_name}::{p.name}")

    # ── 2. UPI National Player of the Year ──────────────────────
    # More position-neutral. Lower team threshold. Numbers-first.
    best_upi = None
    best_upi_score = -1.0
    for t_name, team in teams.items():
        wp = _team_win_pct(t_name, standings)
        schedule_len = _get_team_schedule_len(season, t_name)
        for p in team.players:
            group = _pos_group(p.position)
            stats = full_agg.get(t_name, {}).get(p.name)
            if not stats or stats.get("games", 0) == 0:
                continue
            if stats["games"] < schedule_len * 0.60:
                continue
            s = _upi_player_score(stats, group, wp)
            # UPI tiebreaker: yards and TDs per game vs above-.500
            vw_stats = vs_winning_agg.get(t_name, {}).get(p.name)
            if vw_stats and vw_stats.get("games", 0) > 0:
                vw_games = vw_stats["games"]
                vw_ypg = (vw_stats.get("yards", 0) + vw_stats.get("kick_pass_yards", 0)) / vw_games
                vw_tpg = vw_stats.get("tds", 0) / vw_games
                s += vw_ypg * 0.03 + vw_tpg * 2
            # Slight divergence encouragement: if already won AP, small penalty
            if f"{t_name}::{p.name}" in seen:
                s *= 0.97
            if s > best_upi_score:
                best_upi_score = s
                best_upi = (p, t_name, stats, group)

    if best_upi:
        p, t_name, stats, group = best_upi
        results.append(_make_award(
            "UPI National Player of the Year", "United Press International",
            p, t_name, stats, group))
        seen.add(f"{t_name}::{p.name}")

    # ── 3. UPI Defensive Player of the Year ─────────────────────
    # Co-equal award. Numbers-first for defensive players.
    best_upi_def = None
    best_upi_def_score = -1.0
    for t_name, team in teams.items():
        wp = _team_win_pct(t_name, standings)
        schedule_len = _get_team_schedule_len(season, t_name)
        for p in team.players:
            group = _pos_group(p.position)
            if not _is_defensive(group):
                continue
            stats = full_agg.get(t_name, {}).get(p.name)
            if not stats or stats.get("games", 0) == 0:
                continue
            if stats["games"] < schedule_len * 0.60:
                continue
            s = _upi_defense_score(stats, wp)
            if s > best_upi_def_score:
                best_upi_def_score = s
                best_upi_def = (p, t_name, stats, group)

    if best_upi_def:
        p, t_name, stats, group = best_upi_def
        results.append(_make_award(
            "UPI Defensive Player of the Year", "United Press International",
            p, t_name, stats, group))
        seen.add(f"{t_name}::{p.name}")

    # ── 4. The Lateral National Freshman of the Year ────────────
    # Freshmen only. Analytical, contrarian. Narrative factor.
    best_freshman = None
    best_freshman_score = -1.0
    for t_name, team in teams.items():
        wp = _team_win_pct(t_name, standings)
        schedule_len = _get_team_schedule_len(season, t_name)
        # Calculate team total touches for impact ratio
        team_total_touches = 0
        for pn, ps in full_agg.get(t_name, {}).items():
            team_total_touches += ps.get("touches", 0)
        team_total_touches = max(1, team_total_touches)

        for p in team.players:
            year_str = getattr(p, "year", "")
            if year_str != "Freshman":
                continue
            group = _pos_group(p.position)
            stats = full_agg.get(t_name, {}).get(p.name)
            if not stats or stats.get("games", 0) == 0:
                continue
            # 8 games minimum
            if stats["games"] < 8:
                continue
            # Team impact: how central was this freshman?
            player_touches = stats.get("touches", 0)
            impact = player_touches / team_total_touches
            s = _lateral_freshman_score(stats, group, wp, impact)
            # Divergence: The Lateral avoids the "obvious" choice
            if f"{t_name}::{p.name}" in seen:
                s *= 0.92
            if s > best_freshman_score:
                best_freshman_score = s
                best_freshman = (p, t_name, stats, group)

    if best_freshman:
        p, t_name, stats, group = best_freshman
        results.append(_make_award(
            "The Lateral National Freshman of the Year", "The Lateral Magazine",
            p, t_name, stats, group))
        seen.add(f"{t_name}::{p.name}")

    # ── 5. TSN National Player of the Year ──────────────────────
    # Drama and narrative. Postseason weighted 2x.
    # Must have made playoffs or won conference.
    best_tsn = None
    best_tsn_score = -1.0
    for t_name, team in teams.items():
        wp = _team_win_pct(t_name, standings)
        if wp < 0.500:
            continue
        made_playoffs = _team_made_playoffs(season, t_name)
        is_conf_champ = _team_is_conf_champ(season, t_name)
        if not made_playoffs and not is_conf_champ:
            continue
        schedule_len = _get_team_schedule_len(season, t_name)
        for p in team.players:
            group = _pos_group(p.position)
            stats = full_agg.get(t_name, {}).get(p.name)
            if not stats or stats.get("games", 0) == 0:
                continue
            if stats["games"] < schedule_len * 0.60:
                continue
            ps_stats = postseason_agg.get(t_name, {}).get(p.name)
            s = _tsn_player_score(stats, group, ps_stats, made_playoffs)
            if s > best_tsn_score:
                best_tsn_score = s
                best_tsn = (p, t_name, stats, group)

    if best_tsn:
        p, t_name, stats, group = best_tsn
        results.append(_make_award(
            "TSN National Player of the Year", "The Sporting News",
            p, t_name, stats, group))
        seen.add(f"{t_name}::{p.name}")

    # ── 6. TSN Defensive Player of the Year ─────────────────────
    # Most prestigious defensive media honor. Dominance against good teams.
    # Prefers pass rushers over volume tacklers. Postseason included.
    best_tsn_def = None
    best_tsn_def_score = -1.0
    for t_name, team in teams.items():
        schedule_len = _get_team_schedule_len(season, t_name)
        winning_opps = _count_winning_opponents_faced(season, t_name, standings)
        for p in team.players:
            group = _pos_group(p.position)
            if not _is_defensive(group):
                continue
            stats = full_agg.get(t_name, {}).get(p.name)
            if not stats or stats.get("games", 0) == 0:
                continue
            if stats["games"] < schedule_len * 0.60:
                continue
            vw_stats = vs_winning_agg.get(t_name, {}).get(p.name)
            ps_stats = postseason_agg.get(t_name, {}).get(p.name)
            s = _tsn_defense_score(stats, vw_stats, ps_stats, winning_opps)
            if s > best_tsn_def_score:
                best_tsn_def_score = s
                best_tsn_def = (p, t_name, stats, group)

    if best_tsn_def:
        p, t_name, stats, group = best_tsn_def
        results.append(_make_award(
            "TSN Defensive Player of the Year", "The Sporting News",
            p, t_name, stats, group))
        seen.add(f"{t_name}::{p.name}")

    # ── 7. TSN Comeback Player of the Year ──────────────────────
    # Player who missed significant time last season and returned to produce.
    # Uses prev_season_games to detect gap years / low-games seasons.
    best_comeback = None
    best_comeback_score = -1.0
    if prev_season_games:
        for t_name, team in teams.items():
            schedule_len = _get_team_schedule_len(season, t_name)
            for p in team.players:
                year_str = getattr(p, "year", "")
                if year_str == "Freshman":
                    continue  # freshmen can't come back
                # Check if player had reduced games last year
                prev_games = prev_season_games.get(p.name, None)
                if prev_games is None:
                    continue  # no prior data
                # "Comeback" = played less than 40% of last year's schedule
                # or was completely absent (0 games)
                if prev_games > 5:
                    continue  # played a full-ish season, not a comeback

                group = _pos_group(p.position)
                stats = full_agg.get(t_name, {}).get(p.name)
                if not stats or stats.get("games", 0) == 0:
                    continue
                # 50% floor for comeback (more lenient)
                if stats["games"] < schedule_len * 0.50:
                    continue
                # Score based on raw production this season
                games = max(1, stats["games"])
                if _is_offensive(group):
                    yds = stats.get("yards", 0) + stats.get("kick_pass_yards", 0)
                    tds = stats.get("tds", 0)
                    raw = (yds * 0.35 + tds * 20) / games
                else:
                    tackles = stats.get("tackles", 0)
                    sacks = stats.get("sacks", 0)
                    raw = (tackles * 2.5 + sacks * 14) / games
                # Bonus for severity of absence: 0 games last year > 3 games
                absence_mult = 1.0 + (5 - prev_games) * 0.04
                raw *= absence_mult
                if raw > best_comeback_score:
                    best_comeback_score = raw
                    best_comeback = (p, t_name, stats, group)

    if best_comeback:
        p, t_name, stats, group = best_comeback
        results.append(_make_award(
            "TSN Comeback Player of the Year", "The Sporting News",
            p, t_name, stats, group,
            reason=f"Returned from limited action to produce at a high level"))

    return results
