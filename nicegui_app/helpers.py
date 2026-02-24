"""Helper functions for the NiceGUI Viperball app.

Pure-data formatting and CSV/text generation functions ported from
ui/helpers.py.  Streamlit-specific rendering (render_game_detail, caches)
is replaced by NiceGUI equivalents in the page modules.
"""

from __future__ import annotations

import io
import csv
import os
import json
from functools import lru_cache

from engine import load_team_from_json
from engine.game_engine import WEATHER_CONDITIONS

# ── Tooltip dictionaries (shared across pages) ──

OFFENSE_TOOLTIPS = {
    "ground_pound": "Grind 20 yards, punch it in. Heavy dive/power runs using all 6 downs. Old-school power football.",
    "lateral_spread": "Stretch the defense with 2-4 lateral chains. High-variance, big-play offense. Risky but devastating.",
    "boot_raid": "Air Raid with the foot. Get to the Launch Pad (opp 40-45), then fire snap kicks. Kick-heavy.",
    "ball_control": "Conservative, mistake-free football. Take the 3-point place kick when available. Win 24-21.",
    "ghost": "Pre-snap chaos. Viper misdirection, counters, and broken plays. Defense never knows who has the ball.",
    "rouge_hunt": "Punt early, pin deep, force mistakes. Score via Pindowns, Bells, Safeties. Defense-first offense.",
    "chain_gang": "Maximum laterals, maximum chaos. Every play is a 4-5 lateral chain. Showtime Viperball.",
    "triple_threat": "Single-wing misdirection. Power Flankers take direct snaps. No one knows who has the ball.",
    "balanced": "No strong tendency — mixes run, chain, and kick based on game state. Jack of all trades.",
}

DEFENSE_TOOLTIPS = {
    "swarm": "Zone rally defense — everyone flows to the ball. Elite vs laterals, but kick pass finds the seams between zones.",
    "blitz_pack": "Relentless pressure — extra rushers every snap. Forces TFLs and fumbles, but counters and draws exploit empty gaps.",
    "shadow": "Mirrors the Viper with a dedicated spy. Shuts down jet sweeps and ghost schemes, but power runs exploit the undermanned box.",
    "fortress": "Stacks the box with bodies. Dominates inside runs and short yardage, but kick pass and laterals stretch the vacated edges.",
    "predator": "Gambles for turnovers — jumps routes, forces fumbles. Creates takeaways constantly, but gives up explosives when the gamble fails.",
    "drift": "Soft zone — bend but don't break. Prevents explosives and big plays, but gives up 4-5 yards on every carry. Death by paper cuts.",
    "chaos": "Stunts, disguises, and line shifts every snap. Wrecks blocking assignments, but when the offense adjusts, it's wide open.",
    "lockdown": "Shutdown kick pass coverage — blankets receivers. Forces you to grind on the ground, but power runs bulldoze the light box.",
    "base_defense": "Solid fundamentals, no major weaknesses. Balanced approach to all play types.",
    "pressure_defense": "Aggressive blitzing and disruption. Forces fumbles but vulnerable to explosive lateral plays.",
    "contain_defense": "Gap discipline prevents big plays. Forces runs inside. Patient but can be methodically attacked.",
    "run_stop_defense": "Stacks the box to stuff the run. Elite vs ground game but weak against lateral chains and kicks.",
    "coverage_defense": "Anti-kick specialist. Prevents pindowns and covers punt returns. Slightly weaker vs dive plays.",
}


# ── Data directory ──

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
TEAMS_DIR = os.path.join(DATA_DIR, "teams")


@lru_cache(maxsize=256)
def load_team(key: str):
    return load_team_from_json(os.path.join(TEAMS_DIR, f"{key}.json"))


# ── Formatting ──

def format_time(seconds):
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


def fmt_vb_score(v):
    """Format Viperball score: whole numbers without .0, half-points as half."""
    if v is None:
        return "0"
    if isinstance(v, (int, float)):
        negative = v < 0
        av = abs(float(v))
        whole = int(av)
        frac = av - whole
        sign = "-" if negative else ""
        if abs(frac) < 0.01:
            return f"{sign}{whole}"
        elif abs(frac - 0.5) < 0.01:
            return f"{sign}{whole}\u00bd" if whole > 0 else f"{sign}\u00bd"
        else:
            return f"{v:g}"
    return str(v)


def safe_filename(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "")


def drive_result_label(result: str) -> str:
    labels = {
        "touchdown": "TD",
        "successful_kick": "SK/FG",
        "fumble": "STRIKE (+\u00bd)",
        "turnover_on_downs": "DOWNS",
        "punt": "PUNT",
        "missed_kick": "MISSED KICK",
        "stall": "END OF QUARTER",
        "pindown": "PINDOWN",
        "punt_return_td": "PUNT RET TD",
        "chaos_recovery": "CHAOS REC",
        "safety": "SAFETY",
        "blocked_punt": "BLOCKED PUNT",
        "muffed_punt": "MUFFED PUNT",
        "blocked_kick": "BLOCKED KICK",
        "lateral_intercepted": "LAT INT",
        "kick_pass_intercepted": "KP INT",
        "int_return_td": "PICK-SIX",
    }
    return labels.get(result, result.upper())


def drive_result_color(result: str) -> str:
    colors = {
        "touchdown": "#22c55e",
        "successful_kick": "#3b82f6",
        "fumble": "#ef4444",
        "turnover_on_downs": "#f59e0b",
        "punt": "#94a3b8",
        "missed_kick": "#f59e0b",
        "stall": "#64748b",
        "pindown": "#a855f7",
        "punt_return_td": "#22c55e",
        "chaos_recovery": "#f97316",
        "safety": "#dc2626",
        "blocked_punt": "#a855f7",
        "muffed_punt": "#ec4899",
        "blocked_kick": "#a855f7",
        "lateral_intercepted": "#ef4444",
        "kick_pass_intercepted": "#ef4444",
        "int_return_td": "#22c55e",
    }
    return colors.get(result, "#94a3b8")


# ── Quarter scoring breakdown ──

def compute_quarter_scores(plays: list) -> tuple[dict, dict]:
    """Compute per-quarter scoring from play-by-play data."""
    home_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    away_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    for p in plays:
        q = p.get("quarter", 0)
        if q not in home_q:
            continue
        if p["result"] in ("touchdown", "punt_return_td", "int_return_td"):
            if p["possession"] == "home":
                home_q[q] += 9
            else:
                away_q[q] += 9
        elif p["result"] == "successful_kick":
            pts = 5 if p.get("play_type") == "drop_kick" else 3
            if p["possession"] == "home":
                home_q[q] += pts
            else:
                away_q[q] += pts
        elif p["result"] == "pindown":
            if p["possession"] == "home":
                home_q[q] += 1
            else:
                away_q[q] += 1
        elif p["result"] == "safety":
            if p["possession"] == "home":
                away_q[q] += 2
            else:
                home_q[q] += 2
        elif p["result"] == "fumble":
            if p["possession"] == "home":
                away_q[q] += 0.5
            else:
                home_q[q] += 0.5
    return home_q, away_q


# ── CSV/Text generators (unchanged from Streamlit version) ──

def _player_stats_markdown(player_list, team_name):
    """Generate markdown tables for player stats from a team's player_stats list."""
    if not player_list:
        return []
    lines = []
    lines.append(f"### {team_name}")

    rushers = [p for p in player_list if p.get("touches", 0) > 0]
    if rushers:
        rushers.sort(key=lambda p: p.get("rushing_yards", 0), reverse=True)
        lines.append("")
        lines.append("**Rushing**")
        lines.append("| Player | Car | Yds | Lat | TDs | Fum |")
        lines.append("|--------|----:|----:|----:|----:|----:|")
        for p in rushers:
            tag = p.get("tag", "")
            name = p.get("name", "?")
            lines.append(f"| {tag} {name} | {p.get('touches',0)} | {p.get('rushing_yards',0)} | {p.get('lateral_yards',0)} | {p.get('rushing_tds',0)} | {p.get('fumbles',0)} |")

    receivers = [p for p in player_list if p.get("kick_pass_receptions", 0) > 0]
    if receivers:
        receivers.sort(key=lambda p: p.get("kick_pass_receptions", 0), reverse=True)
        lines.append("")
        lines.append("**Receiving (Kick Pass)**")
        lines.append("| Player | Rec | KP Yds |")
        lines.append("|--------|----:|-------:|")
        for p in receivers:
            tag = p.get("tag", "")
            name = p.get("name", "?")
            kp_yds = p.get("kick_pass_yards", 0)
            lines.append(f"| {tag} {name} | {p.get('kick_pass_receptions',0)} | {kp_yds} |")

    passers = [p for p in player_list if p.get("kick_passes_thrown", 0) > 0]
    if passers:
        passers.sort(key=lambda p: p.get("kick_passes_thrown", 0), reverse=True)
        lines.append("")
        lines.append("**Kick Passing**")
        lines.append("| Player | Att | Comp | Yds | TDs | INTs |")
        lines.append("|--------|----:|-----:|----:|----:|-----:|")
        for p in passers:
            tag = p.get("tag", "")
            name = p.get("name", "?")
            lines.append(f"| {tag} {name} | {p.get('kick_passes_thrown',0)} | {p.get('kick_passes_completed',0)} | {p.get('kick_pass_yards',0)} | {p.get('kick_pass_tds',0)} | {p.get('kick_pass_interceptions_thrown',0)} |")

    kickers = [p for p in player_list if p.get("kick_att", 0) > 0 or p.get("dk_att", 0) > 0]
    if kickers:
        lines.append("")
        lines.append("**Kicking**")
        lines.append("| Player | DK | PK | Punts |")
        lines.append("|--------|---:|---:|------:|")
        for p in kickers:
            tag = p.get("tag", "")
            name = p.get("name", "?")
            dk = f"{p.get('dk_made',0)}/{p.get('dk_att',0)}" if p.get('dk_att',0) else "-"
            pk = f"{p.get('pk_made',0)}/{p.get('pk_att',0)}" if p.get('pk_att',0) else "-"
            lines.append(f"| {tag} {name} | {dk} | {pk} | - |")

    defenders = [p for p in player_list if p.get("tackles", 0) > 0]
    if defenders:
        defenders.sort(key=lambda p: p.get("tackles", 0), reverse=True)
        lines.append("")
        lines.append("**Defense**")
        lines.append("| Player | Tkl | TFL | Sck | Hur | INTs |")
        lines.append("|--------|----:|----:|----:|----:|-----:|")
        for p in defenders[:8]:
            tag = p.get("tag", "")
            name = p.get("name", "?")
            lines.append(f"| {tag} {name} | {p.get('tackles',0)} | {p.get('tfl',0)} | {p.get('sacks',0)} | {p.get('hurries',0)} | {p.get('kick_pass_ints',0)} |")

    return lines


def generate_box_score_markdown(result):
    home = result["final_score"]["home"]
    away = result["final_score"]["away"]
    hs = result["stats"]["home"]
    as_ = result["stats"]["away"]
    plays = result["play_by_play"]
    home_q, away_q = compute_quarter_scores(plays)

    lines = []
    lines.append(f"# {home['team']} vs {away['team']}")
    lines.append(f"**Seed:** {result.get('seed', 'N/A')}")
    lines.append("")
    lines.append("## Score")
    lines.append("| Team | Q1 | Q2 | Q3 | Q4 | Final |")
    lines.append("|------|----|----|----|----|-------|")
    lines.append(f"| {home['team']} | {fmt_vb_score(home_q[1])} | {fmt_vb_score(home_q[2])} | {fmt_vb_score(home_q[3])} | {fmt_vb_score(home_q[4])} | **{fmt_vb_score(home['score'])}** |")
    lines.append(f"| {away['team']} | {fmt_vb_score(away_q[1])} | {fmt_vb_score(away_q[2])} | {fmt_vb_score(away_q[3])} | {fmt_vb_score(away_q[4])} | **{fmt_vb_score(away['score'])}** |")
    lines.append("")
    lines.append("## Team Stats")
    lines.append(f"| Stat | {home['team']} | {away['team']} |")
    lines.append(f"|------|{'---:|' * 2}")
    lines.append(f"| Total Yards | {hs['total_yards']} | {as_['total_yards']} |")
    lines.append(f"| Touchdowns | {hs['touchdowns']} | {as_['touchdowns']} |")
    lines.append(f"| Rushing Yards | {hs['rushing_yards']} | {as_['rushing_yards']} |")
    lines.append(f"| KP Comp/Att | {hs.get('kick_passes_completed',0)}/{hs.get('kick_passes_attempted',0)} | {as_.get('kick_passes_completed',0)}/{as_.get('kick_passes_attempted',0)} |")
    lines.append(f"| KP Yards | {hs.get('kick_pass_yards',0)} | {as_.get('kick_pass_yards',0)} |")
    lines.append(f"| Snap Kicks | {hs.get('drop_kicks_made',0)}/{hs.get('drop_kicks_attempted',0)} | {as_.get('drop_kicks_made',0)}/{as_.get('drop_kicks_attempted',0)} |")
    lines.append(f"| Field Goals | {hs.get('place_kicks_made',0)}/{hs.get('place_kicks_attempted',0)} | {as_.get('place_kicks_made',0)}/{as_.get('place_kicks_attempted',0)} |")
    lines.append(f"| Fumbles Lost | {hs['fumbles_lost']} | {as_['fumbles_lost']} |")
    lines.append(f"| KP Interceptions | {hs.get('kick_pass_interceptions', 0)} | {as_.get('kick_pass_interceptions', 0)} |")
    lines.append(f"| Lateral Chains | {hs.get('lateral_chains',0)} | {as_.get('lateral_chains',0)} |")
    lines.append(f"| Penalties | {hs.get('penalties',0)} for {hs.get('penalty_yards',0)} yds | {as_.get('penalties',0)} for {as_.get('penalty_yards',0)} yds |")

    ps = result.get("player_stats", {})
    home_players = ps.get("home", [])
    away_players = ps.get("away", [])
    if home_players or away_players:
        lines.append("")
        lines.append("## Player Performance")
        if home_players:
            lines.extend(_player_stats_markdown(home_players, home['team']))
        if away_players:
            lines.append("")
            lines.extend(_player_stats_markdown(away_players, away['team']))

    return "\n".join(lines)


def generate_forum_box_score(result):
    """Generate a plain-text box score suitable for forums."""
    home = result["final_score"]["home"]
    away = result["final_score"]["away"]
    hs = result["stats"]["home"]
    as_ = result["stats"]["away"]
    plays = result["play_by_play"]
    home_q, away_q = compute_quarter_scores(plays)

    winner = home['team'] if home['score'] > away['score'] else away['team']
    w_score = max(home['score'], away['score'])
    l_score = min(home['score'], away['score'])
    loser = away['team'] if winner == home['team'] else home['team']
    weather = result.get("weather", "clear").title()
    seed = result.get("seed", "N/A")

    lines = []
    lines.append("=" * 60)
    lines.append("COLLEGIATE VIPERBALL LEAGUE - OFFICIAL BOX SCORE")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  {winner} {fmt_vb_score(w_score)}, {loser} {fmt_vb_score(l_score)}")
    lines.append(f"  Weather: {weather} | Seed: {seed}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("SCORING BY QUARTER")
    lines.append("-" * 60)
    col_w = max(len(home['team']), len(away['team']), 4) + 2
    lines.append(f"  {'Team':<{col_w}}  Q1    Q2    Q3    Q4    Final")
    lines.append(f"  {'-'*col_w}  ----  ----  ----  ----  -----")
    lines.append(f"  {home['team']:<{col_w}}  {fmt_vb_score(home_q[1]):>4}  {fmt_vb_score(home_q[2]):>4}  {fmt_vb_score(home_q[3]):>4}  {fmt_vb_score(home_q[4]):>4}  {fmt_vb_score(home['score']):>5}")
    lines.append(f"  {away['team']:<{col_w}}  {fmt_vb_score(away_q[1]):>4}  {fmt_vb_score(away_q[2]):>4}  {fmt_vb_score(away_q[3]):>4}  {fmt_vb_score(away_q[4]):>4}  {fmt_vb_score(away['score']):>5}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("TEAM STATISTICS")
    lines.append("-" * 60)
    stat_w = max(len(home['team']), len(away['team']), 6) + 2

    def _stat_line(label, h_val, a_val):
        return f"  {label:<22} {str(h_val):>{stat_w}}  {str(a_val):>{stat_w}}"

    lines.append(f"  {'':22} {home['team']:>{stat_w}}  {away['team']:>{stat_w}}")
    lines.append(_stat_line("Total Yards", hs['total_yards'], as_['total_yards']))
    lines.append(_stat_line("Touchdowns (9pts)", f"{hs['touchdowns']} ({hs['touchdowns']*9}pts)", f"{as_['touchdowns']} ({as_['touchdowns']*9}pts)"))
    lines.append(_stat_line("Rushing Yards", hs.get('rushing_yards', 0), as_.get('rushing_yards', 0)))
    lines.append(_stat_line("KP Comp/Att", f"{hs.get('kick_passes_completed',0)}/{hs.get('kick_passes_attempted',0)}", f"{as_.get('kick_passes_completed',0)}/{as_.get('kick_passes_attempted',0)}"))
    lines.append(_stat_line("KP Yards", hs.get('kick_pass_yards', 0), as_.get('kick_pass_yards', 0)))
    lines.append(_stat_line("Snap Kicks", f"{hs.get('drop_kicks_made',0)}/{hs.get('drop_kicks_attempted',0)}", f"{as_.get('drop_kicks_made',0)}/{as_.get('drop_kicks_attempted',0)}"))
    lines.append(_stat_line("Field Goals", f"{hs.get('place_kicks_made',0)}/{hs.get('place_kicks_attempted',0)}", f"{as_.get('place_kicks_made',0)}/{as_.get('place_kicks_attempted',0)}"))
    lines.append(_stat_line("Fumbles Lost", hs['fumbles_lost'], as_['fumbles_lost']))
    lines.append(_stat_line("KP Interceptions", hs.get('kick_pass_interceptions', 0), as_.get('kick_pass_interceptions', 0)))
    lines.append(_stat_line("Lateral Chains", hs.get('lateral_chains', 0), as_.get('lateral_chains', 0)))
    lines.append(_stat_line("Penalties", f"{hs.get('penalties',0)} for {hs.get('penalty_yards',0)}yds", f"{as_.get('penalties',0)} for {as_.get('penalty_yards',0)}yds"))

    ps = result.get("player_stats", {})
    home_players = ps.get("home", [])
    away_players = ps.get("away", [])
    if home_players or away_players:
        lines.append("")
        lines.append("-" * 60)
        lines.append("INDIVIDUAL LEADERS")
        lines.append("-" * 60)
        for side_name, plist in [(home['team'], home_players), (away['team'], away_players)]:
            if not plist:
                continue
            lines.append(f"\n  {side_name}")
            lines.append(f"  {'-' * len(side_name)}")
            rushers = sorted([p for p in plist if p.get("touches", 0) > 0],
                             key=lambda x: x.get("rushing_yards", 0), reverse=True)
            if rushers:
                lines.append("  RUSHING:")
                for p in rushers[:5]:
                    lines.append(f"    {p.get('tag','')} {p.get('name','?')}: {p.get('touches',0)} car, {p.get('rushing_yards',0)} yds, {p.get('rushing_tds',0)} TDs")
            passers = [p for p in plist if p.get("kick_passes_thrown", 0) > 0]
            if passers:
                lines.append("  KICK PASSING:")
                for p in passers[:3]:
                    lines.append(f"    {p.get('tag','')} {p.get('name','?')}: {p.get('kick_passes_completed',0)}/{p.get('kick_passes_thrown',0)}, {p.get('kick_pass_yards',0)} yds, {p.get('kick_pass_tds',0)} TDs")
            receivers = sorted([p for p in plist if p.get("kick_pass_receptions", 0) > 0],
                               key=lambda x: x.get("kick_pass_receptions", 0), reverse=True)
            if receivers:
                lines.append("  RECEIVING:")
                for p in receivers[:5]:
                    lines.append(f"    {p.get('tag','')} {p.get('name','?')}: {p.get('kick_pass_receptions',0)} rec")
            defenders = sorted([p for p in plist if p.get("tackles", 0) > 0],
                               key=lambda x: x.get("tackles", 0), reverse=True)
            if defenders:
                lines.append("  DEFENSE:")
                for p in defenders[:5]:
                    lines.append(f"    {p.get('tag','')} {p.get('name','?')}: {p.get('tackles',0)} tkl, {p.get('tfl',0)} tfl, {p.get('sacks',0)} sck")

    lines.append("")
    lines.append("=" * 60)
    lines.append("CVL Official Box Score | 6-down, 20-yard system")
    lines.append("=" * 60)
    return "\n".join(lines)


def generate_play_log_csv(result):
    plays = result["play_by_play"]
    home_name = result["final_score"]["home"]["team"]
    away_name = result["final_score"]["away"]["team"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["play_number", "team", "quarter", "time", "down", "yards_to_go",
                     "field_position", "play_family", "play_type", "description",
                     "yards", "result", "fatigue", "laterals"])
    for p in plays:
        team_label = home_name if p["possession"] == "home" else away_name
        writer.writerow([
            p["play_number"], team_label, p["quarter"], format_time(p["time_remaining"]),
            p["down"], p.get("yards_to_go", ""), p["field_position"],
            p.get("play_family", ""), p.get("play_type", ""), p["description"],
            p["yards"], p["result"], p.get("fatigue", ""), p.get("laterals", 0)
        ])
    return output.getvalue()


def generate_drives_csv(result):
    drives = result.get("drive_summary", [])
    home_name = result["final_score"]["home"]["team"]
    away_name = result["final_score"]["away"]["team"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["drive_number", "team", "quarter", "start_yard_line", "plays", "yards", "result", "bonus_drive"])
    for i, d in enumerate(drives):
        team_label = home_name if d["team"] == "home" else away_name
        writer.writerow([i + 1, team_label, d["quarter"], d["start_yard_line"],
                         d["plays"], d["yards"], d["result"], d.get("bonus_drive", False)])
    return output.getvalue()


def generate_batch_summary_csv(results):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["game", "seed", "home_team", "away_team", "home_score", "away_score",
                     "home_yards", "away_yards", "home_tds", "away_tds",
                     "home_fumbles", "away_fumbles", "winner"])
    for i, r in enumerate(results):
        h = r["final_score"]["home"]
        a = r["final_score"]["away"]
        hs = r["stats"]["home"]
        as_ = r["stats"]["away"]
        winner = h["team"] if h["score"] > a["score"] else (a["team"] if a["score"] > h["score"] else "TIE")
        writer.writerow([
            i + 1, r.get("seed", ""), h["team"], a["team"],
            fmt_vb_score(h["score"]), fmt_vb_score(a["score"]),
            hs["total_yards"], as_["total_yards"],
            hs["touchdowns"], as_["touchdowns"],
            hs["fumbles_lost"], as_["fumbles_lost"],
            winner
        ])
    return output.getvalue()
