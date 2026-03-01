"""
Pro League Framework for Viperball
===================================

Parameterized professional league system. All leagues (NVL, EL, AL, PL, LA, CL)
use the same ProLeagueSeason class configured via ProLeagueConfig. Adding a new
league means creating a config and a team-data directory — no new code paths.

Spectator-only: no management, no coaching hires, no roster moves.
"""

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from engine.game_engine import load_team_from_json, Team
from engine.fast_sim import fast_sim_game
from engine.weather import generate_game_weather, describe_conditions


DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class ProLeagueConfig:
    league_id: str
    league_name: str
    teams_dir: str
    divisions: Dict[str, List[str]]
    games_per_season: int = 22
    playoff_teams: int = 12
    bye_count: int = 4
    calendar_start: str = "September"
    calendar_end: str = "February"
    attribute_range: Tuple[int, int] = (65, 95)
    franchise_rating_range: Tuple[int, int] = (60, 95)
    name_pool: str = "male_english"


NVL_CONFIG = ProLeagueConfig(
    league_id="nvl",
    league_name="National Viperball League",
    teams_dir="data/nvl_teams",
    divisions={
        "East": ["nj", "bos", "eri", "orl", "bal", "roc"],
        "North": ["tor", "qc", "van", "cal", "dul", "mtl"],
        "Central": ["nol", "mem", "chi", "ark", "oma", "bhm"],
        "West": ["aus", "boi", "la", "pdx", "spk", "abq"],
    },
    games_per_season=22,
    playoff_teams=12,
    bye_count=4,
    calendar_start="September",
    calendar_end="February",
    attribute_range=(65, 95),
    franchise_rating_range=(60, 95),
    name_pool="male_english",
)


EL_CONFIG = ProLeagueConfig(
    league_id="el",
    league_name="Eurasian League",
    teams_dir="data/el_teams",
    divisions={
        "Nordic": ["sto", "hel", "cop", "osl", "ams"],
        "Continental": ["bru", "ber", "pra", "war", "zur"],
    },
    games_per_season=18,
    playoff_teams=4,
    bye_count=0,
    calendar_start="March",
    calendar_end="July",
    attribute_range=(58, 85),
    franchise_rating_range=(50, 80),
    name_pool="male_european",
)


AL_CONFIG = ProLeagueConfig(
    league_id="al",
    league_name="AfroLeague",
    teams_dir="data/al_teams",
    divisions={
        "West": ["lag", "acc", "dak", "cas", "abi", "abj"],
        "East": ["nai", "joh", "cai", "dar", "add", "kam"],
    },
    games_per_season=20,
    playoff_teams=4,
    bye_count=0,
    calendar_start="April",
    calendar_end="August",
    attribute_range=(55, 82),
    franchise_rating_range=(45, 78),
    name_pool="male_african",
)


PL_CONFIG = ProLeagueConfig(
    league_id="pl",
    league_name="Pacific League",
    teams_dir="data/pl_teams",
    divisions={
        "North": ["tai", "man", "seo", "osa"],
        "South": ["jak", "ban", "hcm", "sgp"],
    },
    games_per_season=14,
    playoff_teams=4,
    bye_count=0,
    calendar_start="January",
    calendar_end="May",
    attribute_range=(55, 80),
    franchise_rating_range=(45, 75),
    name_pool="male_asian",
)


LA_CONFIG = ProLeagueConfig(
    league_id="la_league",
    league_name="LigaAmerica",
    teams_dir="data/la_teams",
    divisions={
        "Norte": ["mex", "sao", "bue", "bog", "lim"],
        "Caribe": ["sju", "sdo", "hav", "mvd", "stg"],
    },
    games_per_season=18,
    playoff_teams=4,
    bye_count=0,
    calendar_start="June",
    calendar_end="October",
    attribute_range=(55, 82),
    franchise_rating_range=(45, 78),
    name_pool="male_latin",
)


ALL_LEAGUE_CONFIGS = {
    "nvl": NVL_CONFIG,
    "el": EL_CONFIG,
    "al": AL_CONFIG,
    "pl": PL_CONFIG,
    "la_league": LA_CONFIG,
}


# ═══════════════════════════════════════════════════════════════
# CHAMPIONS LEAGUE — completed-season archive & factory
# ═══════════════════════════════════════════════════════════════

_completed_league_snapshots: Dict[str, dict] = {}


def archive_season(season: 'ProLeagueSeason') -> dict:
    """Archive a completed league season for Champions League qualification.

    Stores the champion + the best-record non-champion team. The champion
    always qualifies regardless of regular-season record (they won the
    playoff tournament). The second qualifier is the best record team
    that isn't the champion.
    """
    if not season.champion:
        return {}

    league_id = season.config.league_id
    standings = season.get_standings()

    # Flatten all teams sorted by record
    all_teams = []
    for div_teams in standings["divisions"].values():
        all_teams.extend(div_teams)
    all_teams.sort(key=lambda t: (-t["wins"], t["losses"]))

    champ_key = season.champion
    top_teams = []
    seen = set()

    # Champion always qualifies first
    for t in all_teams:
        if t["team_key"] == champ_key:
            top_teams.append({
                "team_key": t["team_key"],
                "team_name": t["team_name"],
                "wins": t["wins"],
                "losses": t["losses"],
                "is_champion": True,
            })
            seen.add(t["team_key"])
            break

    # Best record non-champion qualifies second
    for t in all_teams:
        if t["team_key"] not in seen:
            top_teams.append({
                "team_key": t["team_key"],
                "team_name": t["team_name"],
                "wins": t["wins"],
                "losses": t["losses"],
                "is_champion": False,
            })
            seen.add(t["team_key"])
            break

    snapshot = {
        "league_id": league_id,
        "league_name": season.config.league_name,
        "champion": season.champion,
        "champion_name": season.teams[season.champion].name if season.champion in season.teams else season.champion,
        "teams_dir": season.config.teams_dir,
        "top_teams": top_teams,
    }
    _completed_league_snapshots[league_id] = snapshot
    return snapshot


def get_completed_leagues() -> Dict[str, dict]:
    """Return the archive of completed league seasons."""
    return dict(_completed_league_snapshots)


def create_champions_league() -> 'ProLeagueSeason':
    """Create a Champions League season from all archived league snapshots.

    Loads top 2 teams from each completed league, prefixes their keys to
    avoid collisions, and builds a round-robin + playoff tournament.
    """
    archives = get_completed_leagues()
    if len(archives) < 2:
        raise ValueError(f"Need at least 2 completed leagues, have {len(archives)}")

    # Load qualifying teams from their original JSON files
    cl_teams: Dict[str, Team] = {}
    cl_keys: List[str] = []
    for league_id, snap in archives.items():
        teams_dir = snap["teams_dir"]
        for t in snap["top_teams"]:
            orig_key = t["team_key"]
            cl_key = f"{league_id}_{orig_key}"
            filepath = DATA_DIR.parent / teams_dir / f"{orig_key}.json"
            if filepath.exists():
                team = load_team_from_json(str(filepath))
                cl_teams[cl_key] = team
                cl_keys.append(cl_key)

    n = len(cl_keys)
    if n < 4:
        raise ValueError(f"Need at least 4 qualifying teams, have {n}")

    # Scale playoff structure to field size
    if n <= 4:
        playoff_teams, bye_count = 4, 0
    elif n <= 6:
        playoff_teams, bye_count = 4, 0
    elif n <= 8:
        playoff_teams, bye_count = 8, 2
    else:
        playoff_teams, bye_count = 8, 2

    config = ProLeagueConfig(
        league_id="cl",
        league_name="Champions League",
        teams_dir="",
        divisions={"Champions League": cl_keys},
        games_per_season=n - 1,  # round-robin: each team plays every other once
        playoff_teams=playoff_teams,
        bye_count=bye_count,
        calendar_start="November",
        calendar_end="December",
        attribute_range=(55, 95),
        franchise_rating_range=(45, 95),
    )

    # Build the season without calling __init__ (we inject teams directly)
    season = ProLeagueSeason.__new__(ProLeagueSeason)
    season.config = config
    season.teams = cl_teams
    season.standings = {}
    season.schedule = []
    season.results = {}
    season.player_season_stats = {}
    season.current_week = 0
    season.total_weeks = 0
    season.phase = "regular_season"
    season.playoff_bracket = []
    season.playoff_round = 0
    season.champion = None

    season._init_standings()
    season._generate_schedule()
    return season


@dataclass
class ProTeamRecord:
    team_key: str
    team_name: str
    division: str
    wins: int = 0
    losses: int = 0
    points_for: int = 0
    points_against: int = 0
    div_wins: int = 0
    div_losses: int = 0
    streak: int = 0
    streak_type: str = ""
    last_5: List[str] = field(default_factory=list)

    @property
    def pct(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0

    @property
    def point_diff(self) -> int:
        return self.points_for - self.points_against

    def record_result(self, won: bool, pf: int, pa: int, is_div: bool):
        if won:
            self.wins += 1
            if self.streak_type == "W":
                self.streak += 1
            else:
                self.streak = 1
                self.streak_type = "W"
            self.last_5.append("W")
        else:
            self.losses += 1
            if self.streak_type == "L":
                self.streak += 1
            else:
                self.streak = 1
                self.streak_type = "L"
            self.last_5.append("L")
        self.last_5 = self.last_5[-5:]
        self.points_for += pf
        self.points_against += pa
        if is_div:
            if won:
                self.div_wins += 1
            else:
                self.div_losses += 1


@dataclass
class Matchup:
    home_key: str
    away_key: str
    week: int
    matchup_key: str = ""

    def __post_init__(self):
        if not self.matchup_key:
            self.matchup_key = f"{self.away_key}_at_{self.home_key}"


class ProLeagueSeason:

    def __init__(self, config: ProLeagueConfig):
        self.config = config
        self.teams: Dict[str, Team] = {}
        self.standings: Dict[str, ProTeamRecord] = {}
        self.schedule: List[List[Matchup]] = []
        self.results: Dict[int, Dict[str, dict]] = {}
        self.player_season_stats: Dict[str, Dict[str, dict]] = {}
        self.current_week: int = 0
        self.total_weeks: int = 0
        self.phase: str = "regular_season"
        self.playoff_bracket: List[dict] = []
        self.playoff_round: int = 0
        self.champion: Optional[str] = None

        self._load_teams()
        self._init_standings()
        self._generate_schedule()

    def _load_teams(self):
        teams_path = DATA_DIR.parent / self.config.teams_dir
        for div_name, team_keys in self.config.divisions.items():
            for key in team_keys:
                filepath = teams_path / f"{key}.json"
                if filepath.exists():
                    team = load_team_from_json(str(filepath))
                    self.teams[key] = team

    def _init_standings(self):
        for div_name, team_keys in self.config.divisions.items():
            for key in team_keys:
                if key in self.teams:
                    self.standings[key] = ProTeamRecord(
                        team_key=key,
                        team_name=self.teams[key].name,
                        division=div_name,
                    )

    def _get_division_for_key(self, key: str) -> str:
        for div_name, keys in self.config.divisions.items():
            if key in keys:
                return div_name
        return ""

    def _same_division(self, a: str, b: str) -> bool:
        return self._get_division_for_key(a) == self._get_division_for_key(b)

    def _generate_schedule(self):
        all_keys = list(self.teams.keys())
        num_teams = len(all_keys)
        rng = random.Random(42)
        target = self.config.games_per_season

        div_games: List[Tuple[str, str]] = []
        for div_name, keys in self.config.divisions.items():
            for i, a in enumerate(keys):
                for b in keys[i + 1:]:
                    div_games.append((a, b))
                    div_games.append((b, a))

        cross_div_pool: List[Tuple[str, str]] = []
        div_list = list(self.config.divisions.values())
        for i, div_a in enumerate(div_list):
            for div_b in div_list[i + 1:]:
                for a in div_a:
                    for b in div_b:
                        cross_div_pool.append((a, b))
                        cross_div_pool.append((b, a))
        rng.shuffle(cross_div_pool)

        games_per_team: Dict[str, int] = {k: 0 for k in all_keys}
        scheduled: List[Tuple[str, str]] = []

        for home, away in div_games:
            if games_per_team[home] < target and games_per_team[away] < target:
                scheduled.append((home, away))
                games_per_team[home] += 1
                games_per_team[away] += 1

        for home, away in cross_div_pool:
            if games_per_team[home] < target and games_per_team[away] < target:
                scheduled.append((home, away))
                games_per_team[home] += 1
                games_per_team[away] += 1

        rng.shuffle(scheduled)

        max_per_week = num_teams // 2
        target_weeks = target + 2
        matchups_by_week: List[List[Matchup]] = [[] for _ in range(target_weeks)]
        team_week_used: Dict[str, set] = {k: set() for k in all_keys}

        for home, away in scheduled:
            placed = False
            for w in range(target_weeks):
                if (w not in team_week_used[home] and
                    w not in team_week_used[away] and
                    len(matchups_by_week[w]) < max_per_week):
                    matchups_by_week[w].append(Matchup(home_key=home, away_key=away, week=w + 1))
                    team_week_used[home].add(w)
                    team_week_used[away].add(w)
                    placed = True
                    break
            if not placed:
                for w in range(target_weeks):
                    if (w not in team_week_used[home] and w not in team_week_used[away]):
                        matchups_by_week[w].append(Matchup(home_key=home, away_key=away, week=w + 1))
                        team_week_used[home].add(w)
                        team_week_used[away].add(w)
                        placed = True
                        break
                if not placed:
                    matchups_by_week.append([Matchup(home_key=home, away_key=away, week=len(matchups_by_week) + 1)])
                    team_week_used[home].add(len(matchups_by_week) - 1)
                    team_week_used[away].add(len(matchups_by_week) - 1)

        matchups_by_week = [w for w in matchups_by_week if w]
        for i, week in enumerate(matchups_by_week):
            for m in week:
                m.week = i + 1

        self.schedule = matchups_by_week
        self.total_weeks = len(matchups_by_week)

    def sim_week(self) -> dict:
        if self.phase != "regular_season":
            return {"error": "Season is not in regular season phase"}
        if self.current_week >= self.total_weeks:
            return {"error": "All regular season weeks completed"}

        week_idx = self.current_week
        week_matchups = self.schedule[week_idx]
        week_results = []

        for matchup in week_matchups:
            home = self.teams.get(matchup.home_key)
            away = self.teams.get(matchup.away_key)
            if not home or not away:
                continue

            weather_key = generate_game_weather()
            weather_label = weather_key.replace("_", " ").title() if weather_key else "Clear"
            weather_desc = weather_label

            result = fast_sim_game(
                home_team=home,
                away_team=away,
                weather=weather_key,
                weather_label=weather_label,
                weather_description=weather_desc,
            )

            home_score = result["final_score"]["home"]["score"]
            away_score = result["final_score"]["away"]["score"]
            is_div = self._same_division(matchup.home_key, matchup.away_key)

            self.standings[matchup.home_key].record_result(
                won=home_score > away_score, pf=int(home_score), pa=int(away_score), is_div=is_div
            )
            self.standings[matchup.away_key].record_result(
                won=away_score > home_score, pf=int(away_score), pa=int(home_score), is_div=is_div
            )

            self._accumulate_player_stats(matchup.home_key, result, "home")
            self._accumulate_player_stats(matchup.away_key, result, "away")

            game_summary = {
                "matchup_key": matchup.matchup_key,
                "home_key": matchup.home_key,
                "away_key": matchup.away_key,
                "home_name": home.name,
                "away_name": away.name,
                "home_score": home_score,
                "away_score": away_score,
                "weather": weather_label,
                "result": result,
            }
            week_results.append(game_summary)

        self.results[self.current_week + 1] = {
            g["matchup_key"]: g for g in week_results
        }
        self.current_week += 1

        return {
            "week": self.current_week,
            "games": [{
                "matchup_key": g["matchup_key"],
                "home_key": g["home_key"],
                "away_key": g["away_key"],
                "home_name": g["home_name"],
                "away_name": g["away_name"],
                "home_score": g["home_score"],
                "away_score": g["away_score"],
                "weather": g["weather"],
            } for g in week_results],
        }

    def sim_all(self) -> dict:
        results = []
        while self.current_week < self.total_weeks:
            week_result = self.sim_week()
            results.append(week_result)
        return {"weeks_simulated": len(results), "results": results}

    def get_standings(self) -> dict:
        divisions = {}
        for div_name in self.config.divisions:
            div_teams = [
                rec for rec in self.standings.values()
                if rec.division == div_name
            ]
            div_teams.sort(key=lambda r: (-r.wins, -r.pct, -r.point_diff))
            divisions[div_name] = [{
                "team_key": r.team_key,
                "team_name": r.team_name,
                "wins": r.wins,
                "losses": r.losses,
                "pct": round(r.pct, 3),
                "pf": r.points_for,
                "pa": r.points_against,
                "diff": r.point_diff,
                "div_record": f"{r.div_wins}-{r.div_losses}",
                "streak": f"{r.streak_type}{r.streak}" if r.streak_type else "-",
                "last_5": "".join(r.last_5[-5:]),
            } for r in div_teams]
        return {
            "league": self.config.league_name,
            "week": self.current_week,
            "total_weeks": self.total_weeks,
            "divisions": divisions,
        }

    def get_box_score(self, week: int, matchup_key: str) -> Optional[dict]:
        week_data = self.results.get(week, {})
        game = week_data.get(matchup_key)
        if not game:
            return None
        result = game["result"]

        stats_data = result.get("stats", {})
        player_stats_data = result.get("player_stats", {})

        # Inject fast_sim metrics as viperball_metrics so templates can find them
        fsm = result.get("_fast_sim_metrics", {})
        for side in ("home", "away"):
            side_stats = stats_data.get(side)
            if side_stats and side in fsm and "viperball_metrics" not in side_stats:
                side_stats["viperball_metrics"] = fsm[side]

        box = {
            "league": self.config.league_name,
            "week": week,
            "home_key": game["home_key"],
            "away_key": game["away_key"],
            "home_name": game["home_name"],
            "away_name": game["away_name"],
            "home_score": game["home_score"],
            "away_score": game["away_score"],
            "weather": game["weather"],
            # Nested structure (used by stats site templates)
            "stats": stats_data,
            "player_stats": player_stats_data,
            # Flat keys (used by NiceGUI box score dialog)
            "home_stats": stats_data.get("home", {}),
            "away_stats": stats_data.get("away", {}),
            "home_player_stats": player_stats_data.get("home", []),
            "away_player_stats": player_stats_data.get("away", []),
            "drive_summary": result.get("drive_summary", []),
            "play_by_play": result.get("play_by_play", []),
            "modifier_stack": result.get("modifier_stack", {}),
            "home_scoring": result["final_score"]["home"].get("stats", {}),
            "away_scoring": result["final_score"]["away"].get("stats", {}),
        }
        # Include top-level result keys for game context
        for key in ("weather_label", "weather_description", "home_style",
                     "away_style", "home_defense_style", "away_defense_style",
                     "home_st_scheme", "away_st_scheme"):
            if key in result:
                box[key] = result[key]
        return box

    def get_schedule(self) -> dict:
        weeks = []
        for i, week_matchups in enumerate(self.schedule):
            week_num = i + 1
            games = []
            for m in week_matchups:
                game_info = {
                    "matchup_key": m.matchup_key,
                    "home_key": m.home_key,
                    "away_key": m.away_key,
                    "home_name": self.teams[m.home_key].name if m.home_key in self.teams else m.home_key,
                    "away_name": self.teams[m.away_key].name if m.away_key in self.teams else m.away_key,
                    "completed": week_num <= self.current_week,
                }
                if week_num <= self.current_week:
                    result = self.results.get(week_num, {}).get(m.matchup_key)
                    if result:
                        game_info["home_score"] = result["home_score"]
                        game_info["away_score"] = result["away_score"]
                games.append(game_info)
            weeks.append({"week": week_num, "games": games})
        return {"weeks": weeks, "current_week": self.current_week}

    def _accumulate_player_stats(self, team_key: str, result: dict, side: str):
        if team_key not in self.player_season_stats:
            self.player_season_stats[team_key] = {}
        player_stats = result.get("player_stats", {}).get(side, [])
        for ps in player_stats:
            name = ps.get("name", "Unknown")
            pid = f"{team_key}_{name}"
            if pid not in self.player_season_stats[team_key]:
                self.player_season_stats[team_key][pid] = {
                    "name": name,
                    "team_key": team_key,
                    "position": ps.get("position", ""),
                    "games": 0,
                    "rushing_yards": 0,
                    "rushing_carries": 0,
                    "touchdowns": 0,
                    "kick_pass_yards": 0,
                    "kick_pass_completions": 0,
                    "kick_pass_attempts": 0,
                    "lateral_yards": 0,
                    "laterals": 0,
                    "fumbles": 0,
                    "tackles": 0,
                    "dk_made": 0,
                    "dk_attempted": 0,
                    "total_yards": 0,
                }
            acc = self.player_season_stats[team_key][pid]
            acc["games"] += 1
            # rushing_yards: fast_sim="rushing_yards", full engine="game_rushing_yards"/"yards"
            acc["rushing_yards"] += ps.get("rushing_yards", ps.get("game_rushing_yards", ps.get("yards", 0)))
            # carries: rush_carries + lateral_receptions (any ball touch on a run is a carry)
            rush_car = ps.get("rush_carries", ps.get("carries", ps.get("game_carries", 0)))
            lat_rec = ps.get("lateral_receptions", 0)
            acc["rushing_carries"] += rush_car + lat_rec
            # touchdowns: fast_sim="tds", full engine="touchdowns"/"game_touchdowns"
            acc["touchdowns"] += ps.get("tds", ps.get("touchdowns", ps.get("game_touchdowns", 0)))
            # kick pass yards: both use "kick_pass_yards"
            acc["kick_pass_yards"] += ps.get("kick_pass_yards", ps.get("game_kick_pass_yards", 0))
            # kick pass completions: fast_sim="kick_passes_completed", full engine="kick_pass_completions"
            acc["kick_pass_completions"] += ps.get("kick_passes_completed", ps.get("kick_pass_completions", ps.get("game_kick_pass_completions", 0)))
            # kick pass attempts: fast_sim="kick_passes_thrown", full engine="kick_pass_attempts"
            acc["kick_pass_attempts"] += ps.get("kick_passes_thrown", ps.get("kick_pass_attempts", ps.get("game_kick_pass_attempts", 0)))
            # lateral yards: both use "lateral_yards"
            acc["lateral_yards"] += ps.get("lateral_yards", ps.get("game_lateral_yards", 0))
            # laterals: fast_sim uses "laterals_thrown"+"lateral_receptions", full engine uses "laterals"/"lateral_chains"
            fast_lat = ps.get("laterals_thrown", 0) + ps.get("lateral_receptions", 0)
            acc["laterals"] += fast_lat if fast_lat else ps.get("laterals", ps.get("lateral_chains", 0))
            acc["fumbles"] += ps.get("fumbles", ps.get("game_fumbles", 0))
            acc["tackles"] += ps.get("tackles", ps.get("game_tackles", 0))
            acc["dk_made"] += ps.get("dk_made", ps.get("game_dk_made", 0))
            acc["dk_attempted"] += ps.get("dk_att", ps.get("dk_attempted", ps.get("game_dk_attempted", 0)))
            acc["total_yards"] = acc["rushing_yards"] + acc["kick_pass_yards"] + acc["lateral_yards"]

    def get_stat_leaders(self, category: str = "all") -> dict:
        all_players = []
        for team_key, players in self.player_season_stats.items():
            team_name = self.teams[team_key].name if team_key in self.teams else team_key
            for pid, stats in players.items():
                entry = {**stats, "team_name": team_name}
                all_players.append(entry)

        leaders = {}

        rushing = sorted(all_players, key=lambda p: -p["rushing_yards"])[:20]
        leaders["rushing"] = [{
            "name": p["name"], "team": p["team_name"], "team_key": p["team_key"],
            "position": p["position"],
            "value": p["rushing_yards"],
            "yards": p["rushing_yards"], "carries": p["rushing_carries"],
            "ypc": round(p["rushing_yards"] / max(1, p["rushing_carries"]), 1),
            "games": p["games"],
        } for p in rushing if p["rushing_yards"] > 0]

        kick_pass = sorted(all_players, key=lambda p: -p["kick_pass_yards"])[:20]
        leaders["kick_pass"] = [{
            "name": p["name"], "team": p["team_name"], "team_key": p["team_key"],
            "position": p["position"],
            "value": p["kick_pass_yards"],
            "yards": p["kick_pass_yards"], "completions": p["kick_pass_completions"],
            "attempts": p["kick_pass_attempts"],
            "pct": round(p["kick_pass_completions"] / max(1, p["kick_pass_attempts"]) * 100, 1),
            "games": p["games"],
        } for p in kick_pass if p["kick_pass_yards"] > 0]

        scoring = sorted(all_players, key=lambda p: -p["touchdowns"])[:20]
        leaders["scoring"] = [{
            "name": p["name"], "team": p["team_name"], "team_key": p["team_key"],
            "position": p["position"],
            "value": p["touchdowns"],
            "touchdowns": p["touchdowns"], "dk_made": p["dk_made"],
            "total_yards": p["total_yards"], "games": p["games"],
        } for p in scoring if p["touchdowns"] > 0]

        total = sorted(all_players, key=lambda p: -p["total_yards"])[:20]
        leaders["total_yards"] = [{
            "name": p["name"], "team": p["team_name"], "team_key": p["team_key"],
            "position": p["position"],
            "value": p["total_yards"],
            "total_yards": p["total_yards"], "rushing": p["rushing_yards"],
            "kick_pass": p["kick_pass_yards"], "games": p["games"],
        } for p in total if p["total_yards"] > 0]

        return leaders

    def get_team_detail(self, team_key: str) -> Optional[dict]:
        if team_key not in self.teams:
            return None
        team = self.teams[team_key]
        record = self.standings.get(team_key)

        roster = []
        for p in team.players:
            roster.append({
                "number": p.number,
                "name": p.name,
                "position": p.position,
                "speed": p.speed,
                "stamina": p.stamina,
                "kicking": p.kicking,
                "lateral_skill": p.lateral_skill,
                "tackling": p.tackling,
                "agility": p.agility,
                "power": p.power,
                "awareness": p.awareness,
                "hands": p.hands,
                "overall": p.overall,
                "archetype": p.archetype,
            })

        season_stats = list(self.player_season_stats.get(team_key, {}).values())

        team_schedule = []
        for i, week_matchups in enumerate(self.schedule):
            week_num = i + 1
            for m in week_matchups:
                if m.home_key == team_key or m.away_key == team_key:
                    game_info = {
                        "week": week_num,
                        "matchup_key": m.matchup_key,
                        "opponent_key": m.away_key if m.home_key == team_key else m.home_key,
                        "opponent_name": (self.teams[m.away_key].name if m.home_key == team_key
                                          else self.teams[m.home_key].name)
                                         if (m.away_key in self.teams and m.home_key in self.teams) else "???",
                        "home": m.home_key == team_key,
                        "completed": week_num <= self.current_week,
                    }
                    if week_num <= self.current_week:
                        res = self.results.get(week_num, {}).get(m.matchup_key)
                        if res:
                            if m.home_key == team_key:
                                game_info["score"] = f"{int(res['home_score'])}-{int(res['away_score'])}"
                                game_info["won"] = res["home_score"] > res["away_score"]
                            else:
                                game_info["score"] = f"{int(res['away_score'])}-{int(res['home_score'])}"
                                game_info["won"] = res["away_score"] > res["home_score"]
                    team_schedule.append(game_info)

        rec_dict = {
            "wins": record.wins, "losses": record.losses,
            "points_for": record.points_for, "points_against": record.points_against,
            "pct": record.pct,
        } if record else {"wins": 0, "losses": 0, "points_for": 0, "points_against": 0, "pct": 0.0}

        return {
            "team_key": team_key,
            "team_name": team.name,
            "mascot": team.mascot,
            "abbreviation": team.abbreviation,
            "division": self._get_division_for_key(team_key),
            "record": rec_dict,
            "offense_style": team.offense_style,
            "defense_style": team.defense_style,
            "prestige": team.prestige,
            "roster": roster,
            "season_stats": season_stats,
            "schedule": team_schedule,
        }

    def get_player_card(self, team_key: str, player_name: str) -> Optional[dict]:
        if team_key not in self.teams:
            return None
        team = self.teams[team_key]
        player = None
        for p in team.players:
            if p.name == player_name:
                player = p
                break
        if not player:
            return None

        record = self.standings.get(team_key)
        division = self._get_division_for_key(team_key)

        bio = {
            "name": player.name,
            "number": player.number,
            "position": player.position,
            "team_key": team_key,
            "team_name": team.name,
            "division": division,
            "team_record": f"{record.wins}-{record.losses}" if record else "0-0",
            "archetype": player.archetype,
            "height": player.height,
            "weight": player.weight,
            "hometown_city": player.hometown_city,
            "hometown_state": player.hometown_state,
            "nationality": player.nationality,
            "variance_archetype": player.variance_archetype,
        }

        ratings = {
            "overall": player.overall,
            "speed": player.speed,
            "stamina": player.stamina,
            "kicking": player.kicking,
            "lateral_skill": player.lateral_skill,
            "tackling": player.tackling,
            "agility": player.agility,
            "power": player.power,
            "awareness": player.awareness,
            "hands": player.hands,
            "kick_power": player.kick_power,
            "kick_accuracy": player.kick_accuracy,
        }

        pid = f"{team_key}_{player_name}"
        season_stats = {}
        team_stats = self.player_season_stats.get(team_key, {})
        if pid in team_stats:
            season_stats = dict(team_stats[pid])

        return {
            "bio": bio,
            "ratings": ratings,
            "season_stats": season_stats,
        }

    def start_playoffs(self) -> dict:
        if self.phase != "regular_season":
            return {"error": "Playoffs already started or season not complete"}
        if self.current_week < self.total_weeks:
            return {"error": f"Regular season not complete ({self.current_week}/{self.total_weeks} weeks)"}

        self.phase = "playoffs"
        self.playoff_round = 0

        num_divs = len(self.config.divisions)
        per_div = max(1, self.config.playoff_teams // num_divs)

        seeds = []
        for div_name in self.config.divisions:
            div_teams = [
                rec for rec in self.standings.values()
                if rec.division == div_name
            ]
            div_teams.sort(key=lambda r: (-r.wins, -r.pct, -r.point_diff))
            top_n = div_teams[:per_div]
            for i, rec in enumerate(top_n):
                seeds.append({
                    "team_key": rec.team_key,
                    "team_name": rec.team_name,
                    "division": div_name,
                    "seed": i + 1,
                    "wins": rec.wins,
                    "losses": rec.losses,
                    "div_seed": i + 1,
                })

        seeds.sort(key=lambda s: (-s["wins"], s["seed"]))
        for i, s in enumerate(seeds):
            s["overall_seed"] = i + 1

        top_seeds = [s for s in seeds if s["div_seed"] == 1]
        rest = [s for s in seeds if s["div_seed"] != 1]
        rest.sort(key=lambda s: (-s["wins"], s["seed"]))

        bye_teams = top_seeds[:self.config.bye_count]
        # Non-bye teams play in the first round
        non_bye_seeds = [s for s in top_seeds if s not in bye_teams]
        wc_teams = non_bye_seeds + rest
        wc_teams.sort(key=lambda s: -s["wins"])

        league_abbr = self.config.league_id.upper()
        if self.config.playoff_teams <= 4:
            first_round_name = "Semifinal"
        else:
            first_round_name = "Wild Card"

        round1 = []
        for i in range(0, len(wc_teams) - 1, 2):
            round1.append({
                "home": wc_teams[i],
                "away": wc_teams[i + 1] if i + 1 < len(wc_teams) else None,
                "result": None,
                "round": first_round_name,
            })

        self.playoff_bracket = [{
            "round_name": first_round_name,
            "matchups": round1,
            "bye_teams": bye_teams,
            "completed": False,
        }]

        return self.get_playoff_bracket()

    def advance_playoffs(self) -> dict:
        if self.phase != "playoffs":
            return {"error": "Not in playoff phase"}
        if self.champion:
            return {"error": "Season complete", "champion": self.champion}

        current_round = self.playoff_bracket[-1]
        if current_round["completed"]:
            pass

        if not current_round["completed"]:
            for matchup in current_round["matchups"]:
                if matchup["result"] is None and matchup["away"] is not None:
                    home_team = self.teams.get(matchup["home"]["team_key"])
                    away_team = self.teams.get(matchup["away"]["team_key"])
                    if home_team and away_team:
                        result = fast_sim_game(home_team, away_team, neutral_site=True)
                        h_score = result["final_score"]["home"]["score"]
                        a_score = result["final_score"]["away"]["score"]
                        winner_key = matchup["home"]["team_key"] if h_score > a_score else matchup["away"]["team_key"]
                        matchup["result"] = {
                            "home_score": h_score,
                            "away_score": a_score,
                            "winner": winner_key,
                            "winner_name": self.teams[winner_key].name,
                            "full_result": result,
                        }
            current_round["completed"] = True

        winners = []
        for m in current_round["matchups"]:
            if m["result"]:
                winner_key = m["result"]["winner"]
                winner_rec = self.standings.get(winner_key)
                winners.append({
                    "team_key": winner_key,
                    "team_name": self.teams[winner_key].name,
                    "division": self._get_division_for_key(winner_key),
                    "seed": 0,
                    "wins": winner_rec.wins if winner_rec else 0,
                    "losses": winner_rec.losses if winner_rec else 0,
                    "div_seed": 0,
                })
            elif m["away"] is None:
                winners.append(m["home"])

        bye_teams = current_round.get("bye_teams", [])
        advancing = bye_teams + winners

        if len(advancing) <= 1:
            if advancing:
                self.champion = advancing[0]["team_key"]
            return self.get_playoff_bracket()

        advancing.sort(key=lambda t: (-t.get("wins", 0), t.get("seed", 99)))

        league_abbr = self.config.league_id.upper()
        if self.config.playoff_teams <= 4:
            round_names = ["Semifinal", f"{league_abbr} Championship"]
        else:
            round_names = ["Wild Card", "Divisional", "Conference Championship", f"{league_abbr} Championship"]
        next_round_idx = len(self.playoff_bracket)
        round_name = round_names[next_round_idx] if next_round_idx < len(round_names) else f"Round {next_round_idx + 1}"

        next_matchups = []
        for i in range(0, len(advancing) - 1, 2):
            next_matchups.append({
                "home": advancing[i],
                "away": advancing[i + 1] if i + 1 < len(advancing) else None,
                "result": None,
                "round": round_name,
            })

        self.playoff_bracket.append({
            "round_name": round_name,
            "matchups": next_matchups,
            "bye_teams": [],
            "completed": False,
        })

        return self.get_playoff_bracket()

    def get_playoff_bracket(self) -> dict:
        bracket = []
        for round_data in self.playoff_bracket:
            matchups = []
            for m in round_data["matchups"]:
                entry = {
                    "home": {"team_key": m["home"]["team_key"], "team_name": m["home"]["team_name"]},
                    "away": {"team_key": m["away"]["team_key"], "team_name": m["away"]["team_name"]} if m["away"] else None,
                    "round": m["round"],
                }
                if m["result"]:
                    entry["home_score"] = m["result"]["home_score"]
                    entry["away_score"] = m["result"]["away_score"]
                    entry["winner"] = m["result"]["winner"]
                    entry["winner_name"] = m["result"]["winner_name"]
                matchups.append(entry)
            bracket.append({
                "round_name": round_data["round_name"],
                "matchups": matchups,
                "bye_teams": [{"team_key": t["team_key"], "team_name": t["team_name"]}
                              for t in round_data.get("bye_teams", [])],
                "completed": round_data["completed"],
            })
        return {
            "phase": self.phase,
            "champion": self.champion,
            "champion_name": self.teams[self.champion].name if self.champion else None,
            "rounds": bracket,
        }

    def get_status(self) -> dict:
        return {
            "league": self.config.league_name,
            "league_id": self.config.league_id,
            "phase": self.phase,
            "current_week": self.current_week,
            "total_weeks": self.total_weeks,
            "champion": self.champion,
            "champion_name": self.teams[self.champion].name if self.champion else None,
            "team_count": len(self.teams),
        }

    def export_snapshot(self) -> dict:
        standings_data = {}
        for key, rec in self.standings.items():
            standings_data[key] = {
                "wins": rec.wins, "losses": rec.losses,
                "pf": rec.points_for, "pa": rec.points_against,
            }
        return {
            "league": self.config.league_id,
            "champion": self.champion,
            "final_standings": standings_data,
            "stat_leaders": self.get_stat_leaders(),
        }

    def get_upcoming_matchups(self) -> list:
        if self.current_week >= self.total_weeks:
            return []
        return self.schedule[self.current_week]

    def get_team_prestige_map(self) -> Dict[str, int]:
        return {key: team.prestige for key, team in self.teams.items()}

    def get_team_record(self, key: str) -> Optional[Tuple[int, int]]:
        rec = self.standings.get(key)
        if rec:
            return (rec.wins, rec.losses)
        return None

    def build_dq_game_results(self, week: int) -> Dict[str, dict]:
        week_data = self.results.get(week, {})
        game_results = {}
        for mk, game in week_data.items():
            result = game["result"]
            key = f"{game['home_name']} vs {game['away_name']}"
            game_results[key] = result
        return game_results
