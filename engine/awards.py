"""
Viperball End-of-Season Awards System

Selection methodology:
- Winners chosen using actual season performance stats (WPA, yards, TDs, etc.)
  with OVR-based attribute scoring as fallback when stats are unavailable
- Team performance context (win%, avg OPI) applied as a 0.88–1.10× multiplier
- Each named trophy has a stat-based scoring function tuned for its position group
- Freshman eligibility restricted to players whose year == "Freshman"

─────────────────────────────────────────────────────────────────────────────
INDIVIDUAL TROPHIES
─────────────────────────────────────────────────────────────────────────────

  Persephone Award                   – National Player of the Year (all positions eligible).
                              The sport's highest individual honour.  Any position can win.

  Best Zeroback             – Outstanding Zeroback.

  Best Viper                – Outstanding Viper.

  Best Lateral Specialist   – Outstanding lateral specialist.

  Minerva Award             – Best defensive player from a top-tier defense nationally.

  Best Kicker               – Outstanding kicker.

  Diamond Gloves            – Outstanding defensive backfield player (keeper/safety).
                              Awarded to the player with the lowest KPR (Keeper Rating),
                              an ERA-style stat measuring defensive impact per coverage snap.

  Venus Award                   – Offensive Player of the Year.
  Bellona Award                  – Defensive Player of the Year.

TEAM-LEVEL HONOURS
  Coach of the Year         – Best coaching performance relative to expectations.
  Most Improved Program     – Biggest win-total gain from previous season.

─────────────────────────────────────────────────────────────────────────────
COLLECTIVE TEAMS
─────────────────────────────────────────────────────────────────────────────

  All-CVL (1st, 2nd, 3rd Team)     – Nine position slots each (see _AA_SLOTS)
  All-CVL Honorable Mention         – Next ~18 players across the same slots
  All-Freshman Team                 – Best first-year players (Freshman only)
  All-Conference (1st & 2nd Team)   – Per conference, two full nine-slot teams

Position slots (all tiers):
    1 Zeroback · 2 Vipers · 3 Halfbacks/Wingbacks · 2 Linemen · 1 Safety/Keeper

Usage:
    from engine.awards import compute_season_awards
    honors = compute_season_awards(season, year, conferences, prev_season_wins)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from engine.season import Season
from engine.game_engine import Team, Player


# ──────────────────────────────────────────────
# DATACLASSES
# ──────────────────────────────────────────────

@dataclass
class AwardWinner:
    """A single named award or team-slot selection."""
    award_name: str
    player_name: str
    team_name: str
    position: str
    year_in_school: str   # Freshman / Sophomore / Junior / Senior / Graduate
    overall_rating: int
    reason: str
    season_stats: Optional[Dict] = None  # key stats for display

    def to_dict(self) -> dict:
        d = {
            "award_name": self.award_name,
            "player_name": self.player_name,
            "team_name": self.team_name,
            "position": self.position,
            "year_in_school": self.year_in_school,
            "overall_rating": self.overall_rating,
            "reason": self.reason,
        }
        if self.season_stats:
            d["season_stats"] = self.season_stats
        return d


@dataclass
class AllAmericanTeam:
    """
    One tier of All-CVL selections.

    team_level: "first" | "second" | "third" | "honorable_mention" | "freshman"
    """
    team_level: str
    year: int
    slots: List[AwardWinner] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "team_level": self.team_level,
            "year": self.year,
            "slots": [w.to_dict() for w in self.slots],
        }


@dataclass
class AllConferenceTeam:
    """
    All-Conference selections for one conference, one tier.

    team_level: "first" | "second"
    """
    conference_name: str
    team_level: str
    year: int
    slots: List[AwardWinner] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "conference_name": self.conference_name,
            "team_level": self.team_level,
            "year": self.year,
            "slots": [w.to_dict() for w in self.slots],
        }


@dataclass
class SeasonHonors:
    """
    Complete end-of-season honours package produced by compute_season_awards().
    Stored in Dynasty.honors_history[year] as a serialised dict.
    """
    year: int

    # Named individual trophies
    individual_awards: List[AwardWinner] = field(default_factory=list)

    # All-CVL tiers
    all_american_first: Optional[AllAmericanTeam] = None
    all_american_second: Optional[AllAmericanTeam] = None
    all_american_third: Optional[AllAmericanTeam] = None
    honorable_mention: Optional[AllAmericanTeam] = None
    all_freshman: Optional[AllAmericanTeam] = None

    # All-Conference: conf_name -> {"first": AllConferenceTeam, "second": AllConferenceTeam}
    all_conference_teams: Dict[str, Dict[str, AllConferenceTeam]] = field(default_factory=dict)

    # Team-level awards
    coach_of_year: str = ""
    coach_of_year_team: str = ""
    most_improved: str = ""

    # Conference-level individual awards: conf_name -> list of AwardWinner
    conference_awards: Dict[str, List[AwardWinner]] = field(default_factory=dict)

    # Media awards (postseason — AP, UPI, The Lateral, TSN)
    media_awards: List[Dict] = field(default_factory=list)

    # ── helpers ──
    def get_award(self, award_name: str) -> Optional[AwardWinner]:
        for a in self.individual_awards:
            if a.award_name == award_name:
                return a
        return None

    def all_winners(self) -> List[Tuple[AwardWinner, str]]:
        """Return all award winners with their level ('national'/'conference')."""
        results = []
        for a in self.individual_awards:
            results.append((a, "national"))
        for tier_name, tier_obj in [
            ("All-CVL First Team", self.all_american_first),
            ("All-CVL Second Team", self.all_american_second),
            ("All-CVL Third Team", self.all_american_third),
            ("All-CVL Honorable Mention", self.honorable_mention),
            ("All-Freshman Team", self.all_freshman),
        ]:
            if tier_obj:
                for slot in tier_obj.slots:
                    results.append((AwardWinner(
                        award_name=tier_name,
                        player_name=slot.player_name,
                        team_name=slot.team_name,
                        position=slot.position,
                        year_in_school=slot.year_in_school,
                        overall_rating=slot.overall_rating,
                        reason=slot.reason,
                    ), "national"))
        for conf_name, tiers in self.all_conference_teams.items():
            for tier_key, tier_obj in tiers.items():
                tier_label = f"All-{conf_name} {'First' if tier_key == 'first' else 'Second'} Team"
                for slot in tier_obj.slots:
                    results.append((AwardWinner(
                        award_name=tier_label,
                        player_name=slot.player_name,
                        team_name=slot.team_name,
                        position=slot.position,
                        year_in_school=slot.year_in_school,
                        overall_rating=slot.overall_rating,
                        reason=slot.reason,
                    ), "conference"))
        for conf_name, awards_list in self.conference_awards.items():
            for a in awards_list:
                results.append((a, "conference"))
        for ma in self.media_awards:
            results.append((AwardWinner(
                award_name=ma.get("award_name", ""),
                player_name=ma.get("player_name", ""),
                team_name=ma.get("team_name", ""),
                position=ma.get("position", ""),
                year_in_school=ma.get("year_in_school", ""),
                overall_rating=ma.get("overall_rating", 0),
                reason=ma.get("reason", ""),
                season_stats=ma.get("season_stats"),
            ), "media"))
        return results

    def to_dict(self) -> dict:
        ac = {}
        for conf, tiers in self.all_conference_teams.items():
            ac[conf] = {tier: obj.to_dict() for tier, obj in tiers.items()}
        ca = {}
        for conf, awards_list in self.conference_awards.items():
            ca[conf] = [a.to_dict() for a in awards_list]
        return {
            "year": self.year,
            "individual_awards": [a.to_dict() for a in self.individual_awards],
            "all_american_first":   self.all_american_first.to_dict()  if self.all_american_first  else None,
            "all_american_second":  self.all_american_second.to_dict() if self.all_american_second else None,
            "all_american_third":   self.all_american_third.to_dict()  if self.all_american_third  else None,
            "honorable_mention":    self.honorable_mention.to_dict()   if self.honorable_mention   else None,
            "all_freshman":         self.all_freshman.to_dict()         if self.all_freshman        else None,
            "all_conference_teams": ac,
            "conference_awards": ca,
            "coach_of_year": self.coach_of_year,
            "coach_of_year_team": self.coach_of_year_team,
            "most_improved": self.most_improved,
            "media_awards": self.media_awards,
        }


# ──────────────────────────────────────────────
# POSITION GROUP CLASSIFIER
# ──────────────────────────────────────────────

def _pos_group(position: str) -> str:
    pos = position.lower()
    if "zeroback" in pos or "zero" in pos:
        return "zeroback"
    if "viper" in pos:
        return "viper"
    if any(p in pos for p in ["halfback", "wingback", "shiftback", "flanker"]):
        return "back"
    if "lineman" in pos or "line" in pos or "wedge" in pos:
        return "lineman"
    if "keeper" in pos:
        return "keeper_def"
    if "safety" in pos:
        return "safety"
    if "kicker" in pos:
        return "kicker"
    return "other"


# ──────────────────────────────────────────────
# SEASON STAT AGGREGATION
# ──────────────────────────────────────────────

def _aggregate_player_season_stats(season) -> Dict[str, Dict[str, dict]]:
    """Aggregate individual player stats from completed games.

    Returns: {team_name: {player_name: {stat_dict}}}
    """
    agg: Dict[str, Dict[str, dict]] = {}

    for game in season.schedule:
        if not game.completed or not getattr(game, "full_result", None):
            continue
        fr = game.full_result
        ps = fr.get("player_stats", {})
        for side, team_name in [("home", game.home_team), ("away", game.away_team)]:
            if team_name not in agg:
                agg[team_name] = {}
            for p in ps.get(side, []):
                name = p.get("name", "")
                if not name:
                    continue
                if name not in agg[team_name]:
                    agg[team_name][name] = _init_player_stats(p)
                a = agg[team_name][name]
                _accumulate_player_stats(a, p)

    # Also check playoff games
    for game in getattr(season, 'playoff_bracket', []):
        if not getattr(game, 'completed', False) or not getattr(game, "full_result", None):
            continue
        fr = game.full_result
        ps = fr.get("player_stats", {})
        for side, team_name in [("home", game.home_team), ("away", game.away_team)]:
            if team_name not in agg:
                agg[team_name] = {}
            for p in ps.get(side, []):
                name = p.get("name", "")
                if not name:
                    continue
                if name not in agg[team_name]:
                    agg[team_name][name] = _init_player_stats(p)
                a = agg[team_name][name]
                _accumulate_player_stats(a, p)

    return agg


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
    "keeper_tackles", "coverage_snaps", "muffs",
    "points_allowed_in_coverage", "completions_allowed_in_coverage",
    "kick_return_yards", "punt_return_yards",
    "plays_involved",
]


def _init_player_stats(p: dict) -> dict:
    d = {s: 0 for s in _AGG_COUNTING_STATS}
    d.update({
        "games": 0, "wpa": 0.0,
        "tag": p.get("tag", ""),
        "position": p.get("position", ""),
    })
    return d


def _accumulate_player_stats(a: dict, p: dict):
    a["games"] += 1
    if not a["tag"]:
        a["tag"] = p.get("tag", "")
    if not a.get("position"):
        a["position"] = p.get("position", "")
    for stat in _AGG_COUNTING_STATS:
        a[stat] += p.get(stat, 0)
    a["wpa"] += p.get("wpa", 0.0)


def _stat_score_for_group(stats: dict, group: str, team_perf_mult: float = 1.0) -> float:
    """Score a player for All-League selection using season statistics.

    Pure stats — WPA is NOT included. WPA is used as a tiebreaker
    externally when two candidates score within 5% of each other.
    """
    games = max(1, stats.get("games", 1))
    if group in ("zeroback",):
        kp_yds = stats.get("kick_pass_yards", 0)
        kp_tds = stats.get("kick_pass_tds", 0)
        rush_yds = stats.get("rushing_yards", 0)
        tds = stats.get("tds", 0)
        raw = (kp_yds * 0.45 + rush_yds * 0.35
               + tds * 15 + kp_tds * 12) / games
    elif group == "viper":
        yds = stats.get("yards", 0)
        tds = stats.get("tds", 0)
        raw = (yds * 0.5 + tds * 20) / games
    elif group == "back":
        rush_yds = stats.get("rushing_yards", 0)
        carries = max(1, stats.get("rush_carries", 1))
        tds = stats.get("tds", 0)
        ypc = rush_yds / carries
        raw = (rush_yds * 0.4 + ypc * 8 + tds * 20) / games
    elif group == "lineman":
        tackles = stats.get("tackles", 0)
        sacks = stats.get("sacks", 0)
        tfl = stats.get("tfl", 0)
        raw = (tackles * 2 + sacks * 12 + tfl * 6) / games
    elif group == "keeper_def":
        # 50/50 blend of KPR (0-10, higher=better) and inverted ERA
        # (0-9.99, lower=better → invert to 0-10 higher=better)
        kpr = _compute_kpr(stats)
        era = _compute_keeper_era(stats)
        inv_era = max(0.0, 10.0 - era)
        raw = kpr * 0.5 + inv_era * 0.5  # already a rate, no /games
    elif group == "safety":
        tackles = stats.get("tackles", 0)
        sacks = stats.get("sacks", 0)
        tfl = stats.get("tfl", 0)
        raw = (tackles * 2.5 + sacks * 10 + tfl * 5) / games
    elif group == "kicker":
        kick_made = stats.get("kick_made", 0)
        kick_att = max(1, stats.get("kick_att", 1))
        pct = kick_made / kick_att
        raw = (kick_made * 8 + pct * 30) / games
    else:
        raw = stats.get("yards", 0) / games
    return round(raw * team_perf_mult, 2)


def _format_stat_line(stats: dict, group: str) -> str:
    """Build a concise stat line for display."""
    games = stats.get("games", 0)
    parts = [f"{games} GP"]

    if group in ("zeroback",):
        kp_comp = stats.get("kick_passes_completed", 0)
        kp_att = stats.get("kick_passes_thrown", 0)
        kp_yds = stats.get("kick_pass_yards", 0)
        kp_tds = stats.get("kick_pass_tds", 0)
        rush_yds = stats.get("rushing_yards", 0)
        tds = stats.get("tds", 0)
        parts.append(f"{kp_comp}/{kp_att} KP {kp_yds} yds {kp_tds} KP TD")
        parts.append(f"{rush_yds} rush yds, {tds} TD")
    elif group == "viper":
        yds = stats.get("yards", 0)
        tds = stats.get("tds", 0)
        parts.append(f"{yds} yds, {tds} TD")
    elif group == "back":
        rush_yds = stats.get("rushing_yards", 0)
        carries = stats.get("rush_carries", 0)
        tds = stats.get("tds", 0)
        ypc = round(rush_yds / max(1, carries), 1)
        parts.append(f"{rush_yds} yds, {carries} car, {ypc} YPC, {tds} TD")
    elif group == "keeper_def":
        k_tackles = stats.get("keeper_tackles", 0)
        bells = stats.get("keeper_bells", 0)
        deflections = stats.get("kick_deflections", 0)
        coverage = stats.get("coverage_snaps", 0)
        kpr = _compute_kpr(stats)
        era = _compute_keeper_era(stats)
        parts.append(f"{deflections} DEFL, {k_tackles} TKL, {bells} BLL, {coverage} COV | {kpr} KPR, {era:.2f} ERA")
    elif group in ("lineman", "safety"):
        tackles = stats.get("tackles", 0)
        sacks = stats.get("sacks", 0)
        tfl = stats.get("tfl", 0)
        parts.append(f"{tackles} TKL, {sacks} sacks, {tfl} TFL")
    elif group == "kicker":
        kick_made = stats.get("kick_made", 0)
        kick_att = stats.get("kick_att", 0)
        pct = round(100 * kick_made / max(1, kick_att), 1)
        parts.append(f"{kick_made}/{kick_att} kicks ({pct}%)")
    else:
        yds = stats.get("yards", 0)
        tds = stats.get("tds", 0)
        parts.append(f"{yds} yds, {tds} TD")

    wpa = stats.get("wpa", 0.0)
    if wpa:
        parts.append(f"{wpa:+.1f} WPA")

    return " | ".join(parts)


def _build_season_stats_dict(stats: dict, group: str) -> dict:
    """Build a dict of key stats for JSON serialization."""
    d = {"games": stats.get("games", 0)}
    if group in ("zeroback",):
        d["kick_passes_completed"] = stats.get("kick_passes_completed", 0)
        d["kick_passes_thrown"] = stats.get("kick_passes_thrown", 0)
        d["kick_pass_yards"] = stats.get("kick_pass_yards", 0)
        d["kick_pass_tds"] = stats.get("kick_pass_tds", 0)
        d["rushing_yards"] = stats.get("rushing_yards", 0)
        d["tds"] = stats.get("tds", 0)
    elif group == "viper":
        d["yards"] = stats.get("yards", 0)
        d["tds"] = stats.get("tds", 0)
    elif group == "back":
        d["rushing_yards"] = stats.get("rushing_yards", 0)
        d["rush_carries"] = stats.get("rush_carries", 0)
        d["tds"] = stats.get("tds", 0)
    elif group == "keeper_def":
        d["keeper_tackles"] = stats.get("keeper_tackles", 0)
        d["keeper_bells"] = stats.get("keeper_bells", 0)
        d["kick_deflections"] = stats.get("kick_deflections", 0)
        d["coverage_snaps"] = stats.get("coverage_snaps", 0)
        d["muffs"] = stats.get("muffs", 0)
        d["kpr"] = _compute_kpr(stats)
        d["keeper_era"] = _compute_keeper_era(stats)
    elif group in ("lineman", "safety"):
        d["tackles"] = stats.get("tackles", 0)
        d["sacks"] = stats.get("sacks", 0)
        d["tfl"] = stats.get("tfl", 0)
    elif group == "kicker":
        d["kick_made"] = stats.get("kick_made", 0)
        d["kick_att"] = stats.get("kick_att", 0)
    else:
        d["yards"] = stats.get("yards", 0)
        d["tds"] = stats.get("tds", 0)
    wpa = stats.get("wpa", 0.0)
    if wpa:
        d["wpa"] = round(wpa, 1)
    return d


# ──────────────────────────────────────────────
# SCORING FUNCTIONS (rating-based fallback)
# ──────────────────────────────────────────────

def _player_score(player: Player, team_perf_mult: float = 1.0) -> float:
    pos = player.position.lower()
    if "zeroback" in pos or "zero" in pos:
        raw = (player.speed * 0.9 + player.kicking * 1.2 + player.lateral_skill * 1.1
               + player.awareness * 1.2 + player.stamina * 0.8) / 5.2
    elif "viper" in pos:
        raw = (player.speed * 1.3 + player.lateral_skill * 1.4 + player.agility * 1.2
               + player.hands * 1.0 + player.stamina * 0.8) / 5.7
    elif any(p in pos for p in ["halfback", "wingback", "shiftback"]):
        raw = (player.speed * 1.2 + player.lateral_skill * 1.1 + player.agility * 1.1
               + player.power * 0.9 + player.stamina * 0.9) / 5.2
    elif "lineman" in pos or "line" in pos or "wedge" in pos:
        raw = (player.tackling * 1.6 + player.power * 1.5 + player.stamina * 1.2
               + player.awareness * 0.9) / 5.2
    elif "keeper" in pos:
        raw = (player.speed * 1.0 + player.tackling * 1.4 + player.hands * 1.2
               + player.awareness * 1.4 + player.stamina * 0.8) / 5.8
    elif "safety" in pos:
        raw = (player.speed * 1.1 + player.tackling * 1.3 + player.lateral_skill * 1.0
               + player.awareness * 1.3 + player.stamina * 0.9) / 5.6
    else:
        raw = float(player.overall)
    return round(raw * team_perf_mult, 2)


def _national_poy_score(player: Player, team_perf_mult: float = 1.0) -> float:
    """
    Persephone Award scorer — any position eligible.
    Uses overall plus a 'impact' bonus for offensive skill positions.
    """
    base = float(player.overall)
    pos = player.position.lower()
    # Offensive skill positions get a modest recognition boost to match real-world bias
    # but defenders with elite overall CAN win
    if any(p in pos for p in ["zeroback", "zero", "viper", "halfback", "wingback"]):
        base *= 1.04
    return round(base * team_perf_mult, 2)


def _compute_kpr(stats: dict) -> float:
    """Compute Keeper Rating (KPR) — a composite defensive analytics stat.

    Higher is better. Measures a keeper's value as captain of the
    defensive backfield: deflections (disrupting the aerial attack),
    tackles (last-line stops), bells (loose ball recoveries worth 0.5
    scoreboard points each), coverage involvement, minus mistakes (muffs).

    Scaled to roughly 0-10 range for a typical season.
    """
    games = max(1, stats.get("games", 1))
    deflections = stats.get("kick_deflections", 0)
    k_tackles = stats.get("keeper_tackles", 0)
    bells = stats.get("keeper_bells", 0)
    coverage = stats.get("coverage_snaps", 0)
    tackles = stats.get("tackles", 0)
    muffs = stats.get("muffs", 0)
    # Per-game composite weighted toward disruptive plays
    raw = (deflections * 10 + k_tackles * 5 + bells * 8
           + tackles * 2 + coverage * 0.3 - muffs * 6) / games
    # Scale to 0-10 range
    return round(min(10.0, max(0.0, raw / 0.8)), 1)


def _compute_keeper_era(stats: dict) -> float:
    """Compute Keeper ERA — an ERA-style rate stat. Lower is better.

    Like a pitcher's ERA tracks earned runs allowed per 9 innings,
    Keeper ERA tracks points scored against the keeper's coverage
    per 9 coverage snaps. Built from actual per-play attribution:
    the game engine tracks points_allowed_in_coverage and
    completions_allowed_in_coverage on each keeper/safety.

    ERA = (points_allowed_in_coverage / coverage_snaps) * 9

    Elite: < 2.50 | Good: 2.50-4.00 | Average: 4.00-5.50 | Poor: > 5.50
    """
    coverage = stats.get("coverage_snaps", 0)
    if coverage < 10:
        return 9.99  # insufficient sample
    pts_allowed = stats.get("points_allowed_in_coverage", 0)
    era = (pts_allowed / coverage) * 9.0
    return round(max(0.0, min(9.99, era)), 2)


def _kicker_score(player: Player, team_perf_mult: float = 1.0) -> float:
    raw = (player.kicking * 1.4 + player.kick_power * 1.2
           + player.kick_accuracy * 1.3 + player.awareness * 0.8) / 4.7
    return round(raw * team_perf_mult, 2)


def _lateral_score(player: Player, team_perf_mult: float = 1.0) -> float:
    raw = (player.lateral_skill * 1.5 + player.hands * 1.2
           + player.speed * 1.1 + player.agility * 1.1) / 4.9
    return round(raw * team_perf_mult, 2)


def _defensive_score(player: Player, team_perf_mult: float = 1.0) -> float:
    raw = (player.tackling * 1.5 + player.power * 1.1 + player.speed * 1.0
           + player.awareness * 1.3 + player.stamina * 1.0) / 5.9
    return round(raw * team_perf_mult, 2)


# ──────────────────────────────────────────────
# TEAM PERFORMANCE MULTIPLIER
# ──────────────────────────────────────────────

def _team_perf_mult(team_name: str, standings: dict) -> float:
    record = standings.get(team_name)
    if record is None:
        return 1.0
    # Aggressive curve: 2-win team ~0.65, 6-win ~0.95, 8-win ~1.05, 10-win ~1.15
    wp = record.win_percentage
    mult = 0.55 + wp * 0.55 + min(record.avg_opi / 100.0, 1.0) * 0.05
    return round(min(1.15, max(0.55, mult)), 3)


def _team_win_pct(team_name: str, standings: dict) -> float:
    """Return a team's win percentage from standings."""
    record = standings.get(team_name)
    if record is None:
        return 0.5
    return record.win_percentage


# Minimum team record thresholds
_MIN_WIN_PCT_MVP = 0.500           # Persephone Award, conference MVP
_MIN_WIN_PCT_POY = 0.600           # Player of the Year awards
_MIN_WIN_PCT_POSITIONAL = 0.500    # Best Zeroback, Best Viper, etc.


# ──────────────────────────────────────────────
# WPA TIEBREAKER
# ──────────────────────────────────────────────

_WPA_TIEBREAK_THRESHOLD = 0.05  # 5% — WPA breaks ties within this margin


def _wpa_tiebreak(
    candidate_score: float,
    candidate_wpa: float,
    best_score: float,
    best_wpa: float,
) -> bool:
    """Return True if the candidate should beat the current best.

    If candidate has a clearly higher stat score (>5% gap), it wins outright.
    If scores are within 5%, WPA breaks the tie.
    """
    if best_score <= 0:
        return True
    gap = (candidate_score - best_score) / max(1.0, abs(best_score))
    if gap > _WPA_TIEBREAK_THRESHOLD:
        # Candidate clearly better on stats alone
        return True
    if gap < -_WPA_TIEBREAK_THRESHOLD:
        # Current best clearly better on stats alone
        return False
    # Within 5% — WPA breaks the tie
    return candidate_wpa > best_wpa


def _passes_volume_gate(pstats: dict, group: str, standings: dict, team_name: str) -> bool:
    """Check that a player played enough games and had enough volume.

    Requires 80% of team games played AND position-specific minimum
    touch/attempt thresholds to prevent tiny-sample-size rate inflation.
    """
    games = pstats.get("games", 0)
    if games == 0:
        return False
    team_rec = standings.get(team_name)
    team_gp = team_rec.games_played if team_rec else 0
    if team_gp > 0 and games < team_gp * 0.8:
        return False
    # Minimum volume thresholds per position group
    if group == "back":
        if pstats.get("rush_carries", 0) < games * 2:
            return False
    elif group == "viper":
        if pstats.get("yards", 0) == 0 and pstats.get("tds", 0) == 0:
            return False
    elif group == "zeroback":
        if pstats.get("kick_passes_thrown", 0) < games * 2:
            return False
    return True


# ──────────────────────────────────────────────
# POSITION SLOT SELECTORS
# ──────────────────────────────────────────────

def _best_in_position(
    teams: Dict[str, Team],
    standings: dict,
    group_filter: str,
    score_fn,
    exclude: set,
    freshman_only: bool = False,
    player_stats_agg: Optional[Dict] = None,
    min_win_pct: float = 0.0,
) -> Optional[Tuple[Player, str]]:
    best_score = -1.0
    best_wpa = -999.0
    best_pair = None
    use_stats = bool(player_stats_agg)
    for team_name, team in teams.items():
        if min_win_pct > 0 and _team_win_pct(team_name, standings) < min_win_pct:
            continue
        mult = _team_perf_mult(team_name, standings)
        team_stats = player_stats_agg.get(team_name, {}) if use_stats else {}
        for player in team.players:
            uid = f"{team_name}::{player.name}"
            if uid in exclude:
                continue
            if group_filter == "kicker":
                # Kicker is role-based, not position-based — any player who kicks
                if use_stats and player.name in team_stats:
                    if team_stats[player.name].get("kick_att", 0) == 0:
                        continue
                elif player.kicking < 60:
                    continue
            elif _pos_group(player.position) != group_filter:
                continue
            if freshman_only and getattr(player, "year", "") != "Freshman":
                continue
            if use_stats and player.name in team_stats:
                pstats = team_stats[player.name]
                if not _passes_volume_gate(pstats, group_filter, standings, team_name):
                    continue
                score = _stat_score_for_group(pstats, group_filter, mult)
                wpa = pstats.get("wpa", 0.0)
            else:
                score = score_fn(player, mult)
                wpa = 0.0
            if _wpa_tiebreak(score, wpa, best_score, best_wpa):
                best_score = score
                best_wpa = wpa
                best_pair = (player, team_name)
    return best_pair


# Canonical All-CVL position slots (skill positions + kicker only)
_AA_SLOTS = [
    ("zeroback", "Zeroback",              _player_score),
    ("viper",    "Viper (1)",             _player_score),
    ("viper",    "Viper (2)",             _player_score),
    ("viper",    "Viper (3)",             _player_score),
    ("back",     "Halfback/Wingback (1)", _player_score),
    ("back",     "Halfback/Wingback (2)", _player_score),
    ("back",     "Halfback/Wingback (3)", _player_score),
    ("safety",   "Safety",                _player_score),
    ("keeper_def", "Keeper",             _player_score),
    ("kicker",   "Kicker",               _player_score),
]


def _select_slots(
    teams: Dict[str, Team],
    standings: dict,
    slot_spec: list,
    exclude: set,
    year: int,
    team_level: str,
    freshman_only: bool = False,
    player_stats_agg: Optional[Dict] = None,
) -> List[AwardWinner]:
    winners = []
    for group, label, score_fn in slot_spec:
        pair = _best_in_position(teams, standings, group, score_fn, exclude, freshman_only,
                                  player_stats_agg=player_stats_agg)
        if pair:
            player, team_name = pair
            uid = f"{team_name}::{player.name}"
            exclude.add(uid)
            # Build season stats for display
            pstats = None
            stat_line = ""
            stats_dict = None
            if player_stats_agg:
                pstats = player_stats_agg.get(team_name, {}).get(player.name)
            if pstats and pstats.get("games", 0) > 0:
                stat_line = _format_stat_line(pstats, group)
                stats_dict = _build_season_stats_dict(pstats, group)
            winners.append(AwardWinner(
                award_name=label,
                player_name=player.name,
                team_name=team_name,
                position=player.position,
                year_in_school=getattr(player, "year", ""),
                overall_rating=player.overall,
                reason=stat_line if stat_line else f"{team_level.replace('_', ' ').title()} All-CVL",
                season_stats=stats_dict,
            ))
    return winners


# ──────────────────────────────────────────────
# NAMED INDIVIDUAL TROPHIES
# ──────────────────────────────────────────────

def _stat_score_any_offense(stats: dict, team_perf_mult: float = 1.0) -> float:
    """Score any offensive player using season stats (for MVP / OPOY).
    Pure stats — WPA is used as tiebreaker externally."""
    games = max(1, stats.get("games", 1))
    yds = stats.get("yards", 0)
    tds = stats.get("tds", 0)
    kp_yds = stats.get("kick_pass_yards", 0)
    kp_tds = stats.get("kick_pass_tds", 0)
    fumbles = stats.get("fumbles", 0)
    raw = (yds * 0.4 + kp_yds * 0.35
           + tds * 18 + kp_tds * 14 - fumbles * 8) / games
    return round(raw * team_perf_mult, 2)


def _stat_score_zeroback(stats: dict, team_perf_mult: float = 1.0) -> float:
    """Score a Zeroback — kick passing + rushing.
    Pure stats — WPA is used as tiebreaker externally."""
    games = max(1, stats.get("games", 1))
    kp_yds = stats.get("kick_pass_yards", 0)
    kp_tds = stats.get("kick_pass_tds", 0)
    kp_comp = stats.get("kick_passes_completed", 0)
    kp_att = max(1, stats.get("kick_passes_thrown", 1))
    rush_yds = stats.get("rushing_yards", 0)
    tds = stats.get("tds", 0)
    fumbles = stats.get("fumbles", 0)
    kp_pct = kp_comp / kp_att
    raw = (kp_yds * 0.45 + rush_yds * 0.35
           + tds * 15 + kp_tds * 12 + kp_pct * 20 - fumbles * 8) / games
    return round(raw * team_perf_mult, 2)


def _stat_score_viper(stats: dict, team_perf_mult: float = 1.0) -> float:
    """Score a Viper — all-purpose yards, TDs.
    Pure stats — WPA is used as tiebreaker externally."""
    games = max(1, stats.get("games", 1))
    yds = stats.get("yards", 0)
    tds = stats.get("tds", 0)
    fumbles = stats.get("fumbles", 0)
    kr_yds = stats.get("kick_return_yards", 0)
    pr_yds = stats.get("punt_return_yards", 0)
    all_purpose = yds + kr_yds + pr_yds
    raw = (all_purpose * 0.5 + tds * 20 - fumbles * 8) / games
    return round(raw * team_perf_mult, 2)


def _stat_score_lateral(stats: dict, team_perf_mult: float = 1.0) -> float:
    """Score lateral specialist — volume, accuracy, lateral yards.
    Pure stats — WPA is used as tiebreaker externally."""
    games = max(1, stats.get("games", 1))
    lat_yds = stats.get("lateral_yards", 0)
    lat_thrown = stats.get("laterals_thrown", 0)
    lat_assists = stats.get("lateral_assists", 0)
    lat_pct = lat_assists / max(1, lat_thrown)
    yds = stats.get("yards", 0)
    raw = (lat_yds * 0.5 + lat_thrown * 3 + lat_pct * 30 + yds * 0.1) / games
    return round(raw * team_perf_mult, 2)


def _stat_score_kicker(stats: dict, team_perf_mult: float = 1.0) -> float:
    """Score kicker — accuracy, volume.
    Pure stats — WPA is used as tiebreaker externally."""
    games = max(1, stats.get("games", 1))
    kick_made = stats.get("kick_made", 0)
    kick_att = max(1, stats.get("kick_att", 1))
    pct = kick_made / kick_att
    raw = (kick_made * 8 + pct * 30) / games
    return round(raw * team_perf_mult, 2)


def _stat_score_defense(stats: dict, team_perf_mult: float = 1.0) -> float:
    """Score defensive player — tackles, sacks, TFLs, hurries.
    Pure stats — WPA is used as tiebreaker externally."""
    games = max(1, stats.get("games", 1))
    tackles = stats.get("tackles", 0)
    sacks = stats.get("sacks", 0)
    tfl = stats.get("tfl", 0)
    hurries = stats.get("hurries", 0)
    bells = stats.get("keeper_bells", 0)
    deflections = stats.get("kick_deflections", 0)
    raw = (tackles * 2 + sacks * 12 + tfl * 6 + hurries * 3
           + bells * 4 + deflections * 5) / games
    return round(raw * team_perf_mult, 2)


def _select_individual_awards(
    teams: Dict[str, Team],
    standings: dict,
    player_stats_agg: Optional[Dict] = None,
) -> List[AwardWinner]:

    awards: List[AwardWinner] = []
    seen: set = set()
    use_stats = bool(player_stats_agg)

    def _add(player, team_name, award_name, reason):
        seen.add(f"{team_name}::{player.name}")
        stat_line = ""
        stats_dict = None
        pstats = _get_stats(team_name, player.name)
        if pstats and pstats.get("games", 0) > 0:
            group = _pos_group(player.position)
            stat_line = _format_stat_line(pstats, group)
            stats_dict = _build_season_stats_dict(pstats, group)
        awards.append(AwardWinner(
            award_name=award_name,
            player_name=player.name,
            team_name=team_name,
            position=player.position,
            year_in_school=getattr(player, "year", ""),
            overall_rating=player.overall,
            reason=stat_line if stat_line else reason,
            season_stats=stats_dict,
        ))

    def _get_stats(team_name, player_name):
        if use_stats:
            team_stats = player_stats_agg.get(team_name, {})
            return team_stats.get(player_name)
        return None

    def _best(group, score_fn, exclude_set=None, min_win_pct=0.0):
        return _best_in_position(teams, standings, group, score_fn,
                                  exclude_set if exclude_set is not None else seen,
                                  player_stats_agg=player_stats_agg,
                                  min_win_pct=min_win_pct)

    def _scan_best(position_groups, stat_score_fn, min_win_pct=0.0):
        """Scan all players in given position groups using stat_score_fn.
        Applies WPA tiebreaker and minimum team record threshold.
        Returns (player, team_name) or None."""
        best = None
        best_score = -1.0
        best_wpa = -999.0
        for t_name, t in teams.items():
            if min_win_pct > 0 and _team_win_pct(t_name, standings) < min_win_pct:
                continue
            mult = _team_perf_mult(t_name, standings)
            for p in t.players:
                uid = f"{t_name}::{p.name}"
                if uid in seen:
                    continue
                if position_groups and _pos_group(p.position) not in position_groups:
                    continue
                pstats = _get_stats(t_name, p.name)
                group = _pos_group(p.position)
                if not pstats or not _passes_volume_gate(pstats, group, standings, t_name):
                    continue
                s = stat_score_fn(pstats, mult)
                wpa = pstats.get("wpa", 0.0)
                if _wpa_tiebreak(s, wpa, best_score, best_wpa):
                    best_score = s
                    best_wpa = wpa
                    best = (p, t_name)
        return best

    # ── Persephone Award (national POY — any position) ──────────────────
    # Minimum .500 team record required
    best_poy = None
    best_poy_score = -1.0
    best_poy_wpa = -999.0
    for t_name, t in teams.items():
        if _team_win_pct(t_name, standings) < _MIN_WIN_PCT_MVP:
            continue
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            if f"{t_name}::{p.name}" in seen:
                continue
            pstats = _get_stats(t_name, p.name)
            group = _pos_group(p.position)
            if not pstats or not _passes_volume_gate(pstats, group, standings, t_name):
                continue
            if group in ("lineman", "safety", "keeper_def"):
                s = _stat_score_defense(pstats, mult)
            else:
                s = _stat_score_any_offense(pstats, mult)
            wpa = pstats.get("wpa", 0.0)
            if _wpa_tiebreak(s, wpa, best_poy_score, best_poy_wpa):
                best_poy_score = s
                best_poy_wpa = wpa
                best_poy = (p, t_name)
    if best_poy:
        p, t = best_poy
        _add(p, t, "Persephone Award",
             f"Nation's outstanding collegiate viperball player ({t})")

    # ── Best Zeroback ─────────────────────────────
    # Minimum .500 team record required
    best_zb = _scan_best({"zeroback"}, _stat_score_zeroback, _MIN_WIN_PCT_POSITIONAL)
    if best_zb:
        _add(best_zb[0], best_zb[1], "Best Zeroback",
             f"Nation's outstanding Zeroback ({best_zb[1]})")

    # ── Best Viper ────────────────────────────────
    # Minimum .500 team record required
    best_vp = _scan_best({"viper"}, _stat_score_viper, _MIN_WIN_PCT_POSITIONAL)
    if not best_vp:
        # Fallback: find best viper without stat requirement
        best_vp = _best("viper", _player_score, min_win_pct=_MIN_WIN_PCT_POSITIONAL)
    if best_vp:
        _add(best_vp[0], best_vp[1], "Best Viper",
             f"Nation's outstanding Viper ({best_vp[1]})")

    # ── Best Lateral Specialist ─────────────────
    # Minimum .500 team record required
    best_lat = _scan_best({"zeroback", "viper", "back"}, _stat_score_lateral, _MIN_WIN_PCT_POSITIONAL)
    if best_lat:
        _add(best_lat[0], best_lat[1], "Best Lateral Specialist",
             f"Nation's outstanding lateral specialist ({best_lat[1]})")

    # ── Minerva Award (best defensive player from a top defense) ──────
    # Rank teams by defensive quality, take top quartile, find best player among them
    _minerva_eligible = set()
    _team_def_scores = {}
    for t_name in teams:
        rec = standings.get(t_name)
        if rec and rec.games_played > 0:
            # Defensive quality: low points against + high stop rate + turnovers forced
            ppg_against = rec.points_against / rec.games_played
            stop = getattr(rec, 'stop_rate', 0)
            to_forced = getattr(rec, 'avg_turnovers_forced', 0)
            # Lower ppg_against is better, so invert it; higher stop/TO is better
            _team_def_scores[t_name] = -ppg_against * 2 + stop * 0.5 + to_forced * 5
    if _team_def_scores:
        sorted_def = sorted(_team_def_scores, key=_team_def_scores.get, reverse=True)
        cutoff = max(1, len(sorted_def) // 4)  # top 25%
        _minerva_eligible = set(sorted_def[:cutoff])

    if _minerva_eligible:
        # Build a filtered teams dict with only top-defense teams
        minerva_teams = {t: teams[t] for t in _minerva_eligible if t in teams}
        best_minerva = None
        best_minerva_score = -1.0
        best_minerva_wpa = -999.0
        for t_name, t in minerva_teams.items():
            if _team_win_pct(t_name, standings) < _MIN_WIN_PCT_POSITIONAL:
                continue
            mult = _team_perf_mult(t_name, standings)
            for p in t.players:
                uid = f"{t_name}::{p.name}"
                if uid in seen:
                    continue
                group = _pos_group(p.position)
                if group not in ("lineman", "safety", "keeper_def"):
                    continue
                pstats = _get_stats(t_name, p.name)
                if not pstats or not _passes_volume_gate(pstats, group, standings, t_name):
                    continue
                s = _stat_score_defense(pstats, mult)
                wpa = pstats.get("wpa", 0.0)
                if _wpa_tiebreak(s, wpa, best_minerva_score, best_minerva_wpa):
                    best_minerva_score = s
                    best_minerva_wpa = wpa
                    best_minerva = (p, t_name)
        if best_minerva:
            _add(best_minerva[0], best_minerva[1], "Minerva Award",
                 f"Best defensive player from a top defense ({best_minerva[1]})")

    # ── Best Kicker (any position) ───────────────────
    # Minimum .500 team record required
    best_k = None
    best_k_score = -1.0
    best_k_wpa = -999.0
    for t_name, t in teams.items():
        if _team_win_pct(t_name, standings) < _MIN_WIN_PCT_POSITIONAL:
            continue
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            pstats = _get_stats(t_name, p.name)
            if not pstats or not _passes_volume_gate(pstats, "kicker", standings, t_name):
                continue
            if pstats.get("kick_att", 0) == 0:
                continue
            s = _stat_score_kicker(pstats, mult)
            wpa = pstats.get("wpa", 0.0)
            if _wpa_tiebreak(s, wpa, best_k_score, best_k_wpa):
                best_k_score = s
                best_k_wpa = wpa
                best_k = (p, t_name)
    if best_k:
        _add(best_k[0], best_k[1], "Best Kicker",
             f"Nation's outstanding kicker ({best_k[1]})")

    # ── Diamond Gloves (best defensive backfield player by KPR + ERA) ────
    # Keepers and safeties eligible. Highest KPR wins.
    # Minimum .500 team record required, must have coverage snaps
    best_dg = None
    best_dg_kpr = -1.0
    for t_name, t in teams.items():
        if _team_win_pct(t_name, standings) < _MIN_WIN_PCT_POSITIONAL:
            continue
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            group = _pos_group(p.position)
            if group not in ("keeper_def", "safety"):
                continue
            pstats = _get_stats(t_name, p.name)
            if not pstats or not _passes_volume_gate(pstats, group, standings, t_name):
                continue
            if pstats.get("coverage_snaps", 0) < 20:
                continue
            kpr = _compute_kpr(pstats)
            if kpr > best_dg_kpr:
                best_dg_kpr = kpr
                best_dg = (p, t_name, pstats)
    if best_dg:
        p, t, pstats = best_dg
        kpr = _compute_kpr(pstats)
        era = _compute_keeper_era(pstats)
        _add(p, t, "Diamond Gloves",
             f"Nation's outstanding defensive back — {kpr} KPR, {era:.2f} ERA ({t})")

    # ── Offensive Player of the Year ──────────────────────────────────────
    # Minimum .600 team record required
    off_groups = {"zeroback", "viper", "back"}
    best_off = None
    best_off_score = -1.0
    best_off_wpa = -999.0
    for t_name, t in teams.items():
        if _team_win_pct(t_name, standings) < _MIN_WIN_PCT_POY:
            continue
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            if _pos_group(p.position) not in off_groups:
                continue
            group = _pos_group(p.position)
            pstats = _get_stats(t_name, p.name)
            if not pstats or not _passes_volume_gate(pstats, group, standings, t_name):
                continue
            s = _stat_score_for_group(pstats, group, mult)
            wpa = pstats.get("wpa", 0.0)
            if _wpa_tiebreak(s, wpa, best_off_score, best_off_wpa):
                best_off_score = s
                best_off_wpa = wpa
                best_off = (p, t_name)
    if best_off:
        _add(best_off[0], best_off[1], "Venus Award",
             f"Offensive Player of the Year ({best_off[1]})")

    # ── Defensive Player of the Year ──────────────────────────────────────
    # Minimum .600 team record required
    def_groups = {"lineman", "safety", "keeper_def"}
    best_def = None
    best_def_score = -1.0
    best_def_wpa = -999.0
    for t_name, t in teams.items():
        if _team_win_pct(t_name, standings) < _MIN_WIN_PCT_POY:
            continue
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            group = _pos_group(p.position)
            if group not in def_groups:
                continue
            pstats = _get_stats(t_name, p.name)
            if not pstats or not _passes_volume_gate(pstats, group, standings, t_name):
                continue
            s = _stat_score_for_group(pstats, group, mult)
            wpa = pstats.get("wpa", 0.0)
            if _wpa_tiebreak(s, wpa, best_def_score, best_def_wpa):
                best_def_score = s
                best_def_wpa = wpa
                best_def = (p, t_name)
    if best_def:
        _add(best_def[0], best_def[1], "Bellona Award",
             f"Defensive Player of the Year ({best_def[1]})")

    return awards


# ──────────────────────────────────────────────
# ALL-CONFERENCE SELECTION (2 teams per conf)
# ──────────────────────────────────────────────

def _select_all_conference_both(
    conference_name: str,
    conf_teams: List[str],
    all_teams: Dict[str, Team],
    standings: dict,
    year: int,
    player_stats_agg: Optional[Dict] = None,
) -> Dict[str, AllConferenceTeam]:
    """Returns {"first": AllConferenceTeam, "second": AllConferenceTeam}."""
    conf_team_objs = {t: all_teams[t] for t in conf_teams if t in all_teams}
    seen: set = set()

    first_slots = _select_slots(conf_team_objs, standings, _AA_SLOTS, seen, year, "first_conference",
                                 player_stats_agg=player_stats_agg)
    second_slots = _select_slots(conf_team_objs, standings, _AA_SLOTS, seen, year, "second_conference",
                                  player_stats_agg=player_stats_agg)

    return {
        "first": AllConferenceTeam(
            conference_name=conference_name,
            team_level="first",
            year=year,
            slots=first_slots,
        ),
        "second": AllConferenceTeam(
            conference_name=conference_name,
            team_level="second",
            year=year,
            slots=second_slots,
        ),
    }


# ──────────────────────────────────────────────
# CONFERENCE INDIVIDUAL AWARDS
# ──────────────────────────────────────────────

def _select_conference_individual_awards(
    conference_name: str,
    conf_teams: List[str],
    all_teams: Dict[str, Team],
    standings: dict,
    prev_season_wins: Dict[str, int] = None,
    coaching_staffs: Optional[Dict] = None,
    player_stats_agg: Optional[Dict] = None,
    season: Optional["Season"] = None,
) -> List[AwardWinner]:
    """Select conference-level individual awards mirroring national trophies."""
    conf_team_objs = {t: all_teams[t] for t in conf_teams if t in all_teams}
    if not conf_team_objs:
        return []

    awards: List[AwardWinner] = []
    seen: set = set()
    use_stats = bool(player_stats_agg)

    def _add(player, team_name, award_name, reason):
        seen.add(f"{team_name}::{player.name}")
        stat_line = ""
        stats_dict = None
        pstats = _get_stats(team_name, player.name)
        if pstats and pstats.get("games", 0) > 0:
            group = _pos_group(player.position)
            stat_line = _format_stat_line(pstats, group)
            stats_dict = _build_season_stats_dict(pstats, group)
        awards.append(AwardWinner(
            award_name=award_name,
            player_name=player.name,
            team_name=team_name,
            position=player.position,
            year_in_school=getattr(player, "year", ""),
            overall_rating=player.overall,
            reason=stat_line if stat_line else reason,
            season_stats=stats_dict,
        ))

    def _get_stats(team_name, player_name):
        if use_stats:
            team_stats = player_stats_agg.get(team_name, {})
            return team_stats.get(player_name)
        return None

    # Conference MVP — minimum .500 record required
    best_poy = None
    best_poy_score = -1.0
    best_poy_wpa = -999.0
    for t_name, t in conf_team_objs.items():
        if _team_win_pct(t_name, standings) < _MIN_WIN_PCT_MVP:
            continue
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            if f"{t_name}::{p.name}" in seen:
                continue
            pstats = _get_stats(t_name, p.name)
            group = _pos_group(p.position)
            if not pstats or not _passes_volume_gate(pstats, group, standings, t_name):
                continue
            if group in ("lineman", "safety", "keeper_def"):
                s = _stat_score_defense(pstats, mult)
            else:
                s = _stat_score_any_offense(pstats, mult)
            wpa = pstats.get("wpa", 0.0)
            if _wpa_tiebreak(s, wpa, best_poy_score, best_poy_wpa):
                best_poy_score = s
                best_poy_wpa = wpa
                best_poy = (p, t_name)
    if best_poy:
        _add(best_poy[0], best_poy[1], f"{conference_name} MVP",
             f"{conference_name} Player of the Year ({best_poy[1]})")

    # Conference Offensive Player of the Year — no min record, team mult handles it
    off_groups = {"zeroback", "viper", "back"}
    best_off = None
    best_off_score = -1.0
    best_off_wpa = -999.0
    for t_name, t in conf_team_objs.items():
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            group = _pos_group(p.position)
            if group not in off_groups:
                continue
            pstats = _get_stats(t_name, p.name)
            if not pstats or not _passes_volume_gate(pstats, group, standings, t_name):
                continue
            s = _stat_score_for_group(pstats, group, mult)
            wpa = pstats.get("wpa", 0.0)
            if _wpa_tiebreak(s, wpa, best_off_score, best_off_wpa):
                best_off_score = s
                best_off_wpa = wpa
                best_off = (p, t_name)
    if best_off:
        _add(best_off[0], best_off[1], f"{conference_name} Offensive POY",
             f"{conference_name} Offensive Player of the Year ({best_off[1]})")

    # Conference Defensive Player of the Year — no min record, team mult handles it
    def_groups = {"lineman", "safety", "keeper_def"}
    best_def = None
    best_def_score = -1.0
    best_def_wpa = -999.0
    for t_name, t in conf_team_objs.items():
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            group = _pos_group(p.position)
            if group not in def_groups:
                continue
            pstats = _get_stats(t_name, p.name)
            if not pstats or not _passes_volume_gate(pstats, group, standings, t_name):
                continue
            s = _stat_score_for_group(pstats, group, mult)
            wpa = pstats.get("wpa", 0.0)
            if _wpa_tiebreak(s, wpa, best_def_score, best_def_wpa):
                best_def_score = s
                best_def_wpa = wpa
                best_def = (p, t_name)
    if best_def:
        _add(best_def[0], best_def[1], f"{conference_name} Defensive POY",
             f"{conference_name} Defensive Player of the Year ({best_def[1]})")

    # Conference Diamond Gloves — best keeper/safety by KPR (highest wins)
    best_conf_dg = None
    best_conf_dg_kpr = -1.0
    for t_name, t in conf_team_objs.items():
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            group = _pos_group(p.position)
            if group not in ("keeper_def", "safety"):
                continue
            pstats = _get_stats(t_name, p.name)
            if not pstats or not _passes_volume_gate(pstats, group, standings, t_name):
                continue
            if pstats.get("coverage_snaps", 0) < 20:
                continue
            kpr = _compute_kpr(pstats)
            if kpr > best_conf_dg_kpr:
                best_conf_dg_kpr = kpr
                best_conf_dg = (p, t_name, pstats)
    if best_conf_dg:
        p, t, pstats = best_conf_dg
        kpr = _compute_kpr(pstats)
        era = _compute_keeper_era(pstats)
        _add(p, t, f"{conference_name} Diamond Gloves",
             f"{conference_name} outstanding defensive back — {kpr} KPR, {era:.2f} ERA ({t})")

    # Conference Freshman of the Year — no min record
    best_fresh = None
    best_fresh_score = -1.0
    best_fresh_wpa = -999.0
    for t_name, t in conf_team_objs.items():
        mult = _team_perf_mult(t_name, standings)
        for p in t.players:
            uid = f"{t_name}::{p.name}"
            if uid in seen:
                continue
            if getattr(p, "year", "") != "Freshman":
                continue
            group = _pos_group(p.position)
            pstats = _get_stats(t_name, p.name)
            if not pstats or not _passes_volume_gate(pstats, group, standings, t_name):
                continue
            s = _stat_score_for_group(pstats, group, mult)
            wpa = pstats.get("wpa", 0.0)
            if _wpa_tiebreak(s, wpa, best_fresh_score, best_fresh_wpa):
                best_fresh_score = s
                best_fresh_wpa = wpa
                best_fresh = (p, t_name)
    if best_fresh:
        _add(best_fresh[0], best_fresh[1], f"{conference_name} Freshman of the Year",
             f"{conference_name} Top Freshman ({best_fresh[1]})")

    # Conference Coach of the Year — conference win%, improvement, H2H, conf title
    conf_standings = {t: standings[t] for t in conf_teams if t in standings}
    if conf_standings:
        # Determine conference champion
        conf_champ = ""
        if season and hasattr(season, 'get_conference_champions'):
            champs = season.get_conference_champions()
            conf_champ = champs.get(conference_name, "")
        # Build H2H record among top teams from schedule
        h2h_wins = {}  # team -> count of wins vs other conf teams
        if season:
            for g in season.schedule:
                if not g.completed or g.home_score == g.away_score:
                    continue
                if g.home_team in conf_standings and g.away_team in conf_standings:
                    winner = g.home_team if g.home_score > g.away_score else g.away_team
                    h2h_wins[winner] = h2h_wins.get(winner, 0) + 1
        coy_scores = {}
        for t_name, r in conf_standings.items():
            score = r.conf_win_percentage * 50  # primary: conf win%
            score += r.win_percentage * 10       # secondary: overall win%
            # Improvement bonus
            if prev_season_wins:
                prev_w = prev_season_wins.get(t_name, r.wins)
                gain = r.wins - prev_w
                score += max(0, gain) * 3
            # Conference champion bonus
            if t_name == conf_champ:
                score += 10
            # H2H tiebreaker (small weight)
            score += h2h_wins.get(t_name, 0) * 2
            coy_scores[t_name] = score
        coy_team = max(coy_scores, key=coy_scores.get)
        coy_display = _get_head_coach_name(coy_team, coaching_staffs)
        awards.append(AwardWinner(
            award_name=f"{conference_name} Coach of the Year",
            player_name=coy_display,
            team_name=coy_team,
            position="Coach",
            year_in_school="",
            overall_rating=0,
            reason=f"{conference_name} Coach of the Year",
        ))

    return awards


# ──────────────────────────────────────────────
# COACHING STAFF HELPERS
# ──────────────────────────────────────────────

def _get_head_coach_name(team_name: str, coaching_staffs: Optional[Dict] = None) -> str:
    """Look up the head coach name for a team. Returns 'Coach Name (School)' or just the school name."""
    if coaching_staffs:
        staff = coaching_staffs.get(team_name, {})
        hc = staff.get("head_coach")
        if hc:
            first = getattr(hc, "first_name", "") or ""
            last = getattr(hc, "last_name", "") or ""
            name = f"{first} {last}".strip()
            if name:
                return f"{name} ({team_name})"
    return team_name


# ──────────────────────────────────────────────
# TEAM-LEVEL AWARDS
# ──────────────────────────────────────────────

def _select_team_awards(
    standings: dict,
    prev_season_wins: Dict[str, int] = None,
    coaching_staffs: Optional[Dict] = None,
    season: Optional["Season"] = None,
) -> Tuple[str, str, str]:
    """Returns (coach_of_year_display, coy_team_name, most_improved_team)."""
    sorted_std = sorted(standings.values(), key=lambda r: r.win_percentage, reverse=True)

    # Coach of Year: weighted by results, improvement, and conference title
    # - Win% is the primary factor
    # - Big improvement bonus (team that dramatically exceeded prior year)
    # - Conference championship bonus
    conf_champs = set()
    if season and hasattr(season, 'get_conference_champions'):
        conf_champs = set(season.get_conference_champions().values())
    # H2H: count wins against teams with winning records
    h2h_quality_wins = {}
    if season:
        for g in season.schedule:
            if not g.completed or g.home_score == g.away_score:
                continue
            winner = g.home_team if g.home_score > g.away_score else g.away_team
            loser = g.away_team if winner == g.home_team else g.home_team
            loser_rec = standings.get(loser)
            if loser_rec and loser_rec.win_percentage >= 0.500:
                h2h_quality_wins[winner] = h2h_quality_wins.get(winner, 0) + 1
    coy_scores = {}
    for r in standings.values():
        score = r.win_percentage * 50  # primary: win percentage
        # Improvement bonus
        if prev_season_wins:
            prev_w = prev_season_wins.get(r.team_name, r.wins)
            gain = r.wins - prev_w
            score += max(0, gain) * 3  # each win above last year
        # Conference champion bonus
        if r.team_name in conf_champs:
            score += 10
        # H2H quality wins (minor tiebreaker)
        score += h2h_quality_wins.get(r.team_name, 0) * 2
        coy_scores[r.team_name] = score
    coy_team = max(coy_scores, key=coy_scores.get) if coy_scores else ""
    coy = _get_head_coach_name(coy_team, coaching_staffs) if coy_team else ""

    # Most Improved
    most_imp = ""
    if prev_season_wins:
        best_gain = -999
        for r in standings.values():
            prev = prev_season_wins.get(r.team_name, r.wins)
            gain = r.wins - prev
            if gain > best_gain:
                best_gain = gain
                most_imp = r.team_name
    else:
        most_imp = sorted_std[1].team_name if len(sorted_std) > 1 else (sorted_std[0].team_name if sorted_std else "")

    return coy, coy_team, most_imp


# ──────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────

def compute_season_awards(
    season: Season,
    year: int,
    conferences: Dict[str, List[str]] = None,
    prev_season_wins: Dict[str, int] = None,
) -> SeasonHonors:
    """
    Compute all end-of-season honours for a completed season.

    Args:
        season:            Completed Season with standings and teams
        year:              Season year
        conferences:       conf_name -> [team_names]; used for All-Conference
        prev_season_wins:  team_name -> wins last season; used for Most Improved

    Returns:
        SeasonHonors ready to store in Dynasty.honors_history[year]
    """
    standings = season.standings
    teams = season.teams
    honors = SeasonHonors(year=year)

    # ── Aggregate player season stats for stats-based All-League selection ──
    player_stats_agg = _aggregate_player_season_stats(season)

    # ── Named individual trophies ──────────────────────────────────────────
    honors.individual_awards = _select_individual_awards(teams, standings,
                                                          player_stats_agg=player_stats_agg)

    # ── All-CVL (1st, 2nd, 3rd, Honorable Mention) ────────────────────────
    aa_seen: set = set()

    first_slots = _select_slots(teams, standings, _AA_SLOTS, aa_seen, year, "first",
                                 player_stats_agg=player_stats_agg)
    honors.all_american_first = AllAmericanTeam(team_level="first", year=year, slots=first_slots)

    second_slots = _select_slots(teams, standings, _AA_SLOTS, aa_seen, year, "second",
                                  player_stats_agg=player_stats_agg)
    honors.all_american_second = AllAmericanTeam(team_level="second", year=year, slots=second_slots)

    third_slots = _select_slots(teams, standings, _AA_SLOTS, aa_seen, year, "third",
                                 player_stats_agg=player_stats_agg)
    honors.all_american_third = AllAmericanTeam(team_level="third", year=year, slots=third_slots)

    # Honorable Mention: two more players per slot = 18 total
    hm_slots_spec = _AA_SLOTS * 2   # run the same slot list twice
    hm_slots = _select_slots(teams, standings, hm_slots_spec, aa_seen, year, "honorable_mention",
                              player_stats_agg=player_stats_agg)
    honors.honorable_mention = AllAmericanTeam(team_level="honorable_mention", year=year, slots=hm_slots)

    # ── All-Freshman Team ─────────────────────────────────────────────────
    fresh_seen: set = set()
    fresh_slots = _select_slots(teams, standings, _AA_SLOTS, fresh_seen, year, "freshman",
                                freshman_only=True, player_stats_agg=player_stats_agg)
    honors.all_freshman = AllAmericanTeam(team_level="freshman", year=year, slots=fresh_slots)

    # ── All-Conference (1st & 2nd per conference) ─────────────────────────
    coaching_staffs = getattr(season, 'coaching_staffs', None) or {}
    if conferences:
        for conf_name, conf_teams in conferences.items():
            honors.all_conference_teams[conf_name] = _select_all_conference_both(
                conf_name, conf_teams, teams, standings, year,
                player_stats_agg=player_stats_agg,
            )
            honors.conference_awards[conf_name] = _select_conference_individual_awards(
                conf_name, conf_teams, teams, standings, prev_season_wins,
                coaching_staffs=coaching_staffs,
                player_stats_agg=player_stats_agg,
                season=season,
            )

    # ── Team-level awards ─────────────────────────────────────────────────
    coy, coy_team, most_imp = _select_team_awards(standings, prev_season_wins,
                                                    coaching_staffs=coaching_staffs,
                                                    season=season)
    honors.coach_of_year = coy
    honors.coach_of_year_team = coy_team
    honors.most_improved = most_imp

    return honors
