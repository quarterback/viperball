import sys
import os
import random
import json
import io
import csv
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from engine import ViperballEngine, load_team_from_json, get_available_teams, get_available_styles, OFFENSE_STYLES, DEFENSE_STYLES, ST_SCHEMES
from engine.game_engine import WEATHER_CONDITIONS, POSITION_ARCHETYPES, get_archetype_info
from engine.season import load_teams_from_directory, create_season
from engine.dynasty import create_dynasty, Dynasty
from engine.viperball_metrics import calculate_viperball_metrics
from engine.conference_names import generate_conference_names
from engine.geography import get_geographic_conference_defaults
from engine.injuries import InjuryTracker
from engine.player_card import player_to_card
from engine.export import (
    export_season_standings_csv, export_season_game_log_csv,
    export_dynasty_standings_csv, export_dynasty_awards_csv,
    export_injury_history_csv, export_development_history_csv,
    export_all_american_csv, export_all_conference_csv,
)

OFFENSE_TOOLTIPS = {
    "ground_pound": "Grind 20 yards, punch it in. Heavy dive/power runs using all 6 downs. Old-school power football.",
    "lateral_spread": "Stretch the defense with 2-4 lateral chains. High-variance, big-play offense. Risky but devastating.",
    "boot_raid": "Air Raid with the foot. Get to the Launch Pad (opp 40-45), then fire snap kicks. Kick-heavy.",
    "ball_control": "Conservative, mistake-free football. Take the 3-point place kick when available. Win 24-21.",
    "ghost": "Pre-snap chaos. Viper misdirection, counters, and broken plays. Defense never knows who has the ball.",
    "stampede": "High-tempo speed run offense. Stretch the defense outside with sweeps, speed options, and counters. Gets stronger as the game goes on.",
    "chain_gang": "Maximum laterals, maximum chaos. Every play is a 4-5 lateral chain. Showtime Viperball.",
    "slick_n_slide": "Go-Go inspired 2-back attack. Zone reads + run-kick pass options. Adapts to any roster by reading the defense.",
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
    # Legacy (backward compatibility)
    "base_defense": "Solid fundamentals, no major weaknesses. Balanced approach to all play types.",
    "pressure_defense": "Aggressive blitzing and disruption. Forces fumbles but vulnerable to explosive lateral plays.",
    "contain_defense": "Gap discipline prevents big plays. Forces runs inside. Patient but can be methodically attacked.",
    "run_stop_defense": "Stacks the box to stuff the run. Elite vs ground game but weak against lateral chains and kicks.",
    "coverage_defense": "Anti-kick specialist. Prevents pindowns and covers punt returns. Slightly weaker vs dive plays.",
}


@st.cache_data
def load_team(key):
    return load_team_from_json(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams", f"{key}.json"))


def format_time(seconds):
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


def _compute_quarter_scores(plays):
    """Compute per-quarter scoring from play-by-play data.

    Uses running score embedded in each play (home_score / away_score) for
    exact totals via deltas. Falls back to result-based heuristics for legacy data.
    """
    home_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    away_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}

    if plays and "home_score" in plays[0]:
        prev_home = 0.0
        prev_away = 0.0
        for p in plays:
            q = p.get("quarter", 0)
            if q not in home_q:
                continue
            cur_home = p.get("home_score", prev_home)
            cur_away = p.get("away_score", prev_away)
            home_q[q] += cur_home - prev_home
            away_q[q] += cur_away - prev_away
            prev_home = cur_home
            prev_away = cur_away
        return home_q, away_q

    for p in plays:
        q = p.get("quarter", 0)
        if q not in home_q:
            continue
        if p["result"] in ("touchdown", "punt_return_td", "int_return_td", "missed_dk_return_td"):
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
                home_q[q] += 0.5
            else:
                away_q[q] += 0.5
    return home_q, away_q


def fmt_vb_score(v):
    """Format Viperball score: whole numbers without .0, half-points as ½."""
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
            return f"{sign}{whole}½" if whole > 0 else f"{sign}½"
        else:
            return f"{v:g}"
    return str(v)


def generate_box_score_markdown(result):
    home = result["final_score"]["home"]
    away = result["final_score"]["away"]
    hs = result["stats"]["home"]
    as_ = result["stats"]["away"]
    plays = result["play_by_play"]

    home_q, away_q = _compute_quarter_scores(plays)

    lines = []
    lines.append(f"# {home['team']} vs {away['team']}")
    lines.append(f"**Seed:** {result.get('seed', 'N/A')}")
    lines.append("")
    lines.append("## Score")
    lines.append(f"| Team | Q1 | Q2 | Q3 | Q4 | Final |")
    lines.append(f"|------|----|----|----|----|-------|")
    lines.append(f"| {home['team']} | {fmt_vb_score(home_q[1])} | {fmt_vb_score(home_q[2])} | {fmt_vb_score(home_q[3])} | {fmt_vb_score(home_q[4])} | **{fmt_vb_score(home['score'])}** |")
    lines.append(f"| {away['team']} | {fmt_vb_score(away_q[1])} | {fmt_vb_score(away_q[2])} | {fmt_vb_score(away_q[3])} | {fmt_vb_score(away_q[4])} | **{fmt_vb_score(away['score'])}** |")
    lines.append("")

    lines.append("## Team Stats")
    lines.append(f"| Stat | {home['team']} | {away['team']} |")
    lines.append(f"|------|{'---:|' * 2}")
    h_fr = hs.get('fumble_recoveries', 0)
    a_fr = as_.get('fumble_recoveries', 0)
    h_frp = hs.get('fumble_recovery_points', 0)
    a_frp = as_.get('fumble_recovery_points', 0)
    h_saf = hs.get('safeties_conceded', 0)
    a_saf = as_.get('safeties_conceded', 0)
    lines.append(f"| Touchdowns (9pts) | {hs['touchdowns']} ({hs['touchdowns']*9}pts) | {as_['touchdowns']} ({as_['touchdowns']*9}pts) |")
    lines.append(f"| Snap Kicks (5pts) | {hs['drop_kicks_made']}/{hs.get('drop_kicks_attempted',0)} ({hs['drop_kicks_made']*5}pts) | {as_['drop_kicks_made']}/{as_.get('drop_kicks_attempted',0)} ({as_['drop_kicks_made']*5}pts) |")
    lines.append(f"| Field Goals (3pts) | {hs['place_kicks_made']}/{hs.get('place_kicks_attempted',0)} ({hs['place_kicks_made']*3}pts) | {as_['place_kicks_made']}/{as_.get('place_kicks_attempted',0)} ({as_['place_kicks_made']*3}pts) |")
    lines.append(f"| Safeties (2pts) | {a_saf} ({a_saf*2}pts) | {h_saf} ({h_saf*2}pts) |")
    lines.append(f"| Pindowns (1pt) | {hs.get('pindowns',0)} ({hs.get('pindowns',0)}pts) | {as_.get('pindowns',0)} ({as_.get('pindowns',0)}pts) |")
    lines.append(f"| Strikes (½pt) | {h_fr} ({fmt_vb_score(h_frp)}pts) | {a_fr} ({fmt_vb_score(a_frp)}pts) |")
    lines.append(f"| Punt Return TDs | {hs.get('punt_return_tds',0)} | {as_.get('punt_return_tds',0)} |")
    lines.append(f"| Chaos Recoveries | {hs.get('chaos_recoveries',0)} | {as_.get('chaos_recoveries',0)} |")
    lines.append(f"| Punts | {hs.get('punts',0)} | {as_.get('punts',0)} |")
    lines.append(f"| Kick Passes (Comp/Att) | {hs.get('kick_passes_completed',0)}/{hs.get('kick_passes_attempted',0)} | {as_.get('kick_passes_completed',0)}/{as_.get('kick_passes_attempted',0)} |")
    lines.append(f"| Kick Pass Yards | {hs.get('kick_pass_yards',0)} | {as_.get('kick_pass_yards',0)} |")
    lines.append(f"| Kick Pass TDs | {hs.get('kick_pass_tds',0)} | {as_.get('kick_pass_tds',0)} |")
    lines.append(f"| Kick Pass INTs | {hs.get('kick_pass_interceptions',0)} | {as_.get('kick_pass_interceptions',0)} |")
    lines.append(f"| Kick % | {hs.get('kick_percentage',0)}% | {as_.get('kick_percentage',0)}% |")
    lines.append(f"| Total Yards | {hs['total_yards']} | {as_['total_yards']} |")
    h_delta = hs.get('delta_yards', 0)
    a_delta = as_.get('delta_yards', 0)
    if h_delta or a_delta:
        lines.append(f"| Delta Yards | {h_delta} | {a_delta} |")
        lines.append(f"| Adjusted Yards | {hs.get('adjusted_yards', hs['total_yards'])} | {as_.get('adjusted_yards', as_['total_yards'])} |")
    h_delta_dr = hs.get('delta_drives', 0)
    a_delta_dr = as_.get('delta_drives', 0)
    if h_delta_dr or a_delta_dr:
        h_kr = hs.get('kill_rate')
        a_kr = as_.get('kill_rate')
        lines.append(f"| Delta Drives | {h_delta_dr} | {a_delta_dr} |")
        lines.append(f"| Delta Scores | {hs.get('delta_scores',0)} | {as_.get('delta_scores',0)} |")
        if h_kr is not None or a_kr is not None:
            h_kr_str = f"{h_kr}%" if h_kr is not None else "—"
            a_kr_str = f"{a_kr}%" if a_kr is not None else "—"
            lines.append(f"| Kill Rate | {h_kr_str} | {a_kr_str} |")
    # Power Play / Penalty Kill / Mess Rate line
    h_dye = hs.get('dye', {})
    a_dye = as_.get('dye', {})
    h_pp = h_dye.get('power_play', {})
    a_pp = a_dye.get('power_play', {})
    h_pk = h_dye.get('penalty_kill', {})
    a_pk = a_dye.get('penalty_kill', {})
    if h_pp.get('count', 0) > 0 or a_pp.get('count', 0) > 0:
        h_pp_str = f"{h_pp.get('scores',0)}/{h_pp.get('count',0)} ({h_pp.get('score_rate',0)}%)" if h_pp.get('count', 0) > 0 else "—"
        a_pp_str = f"{a_pp.get('scores',0)}/{a_pp.get('count',0)} ({a_pp.get('score_rate',0)}%)" if a_pp.get('count', 0) > 0 else "—"
        h_pk_str = f"{h_pk.get('scores',0)}/{h_pk.get('count',0)} ({h_pk.get('score_rate',0)}%)" if h_pk.get('count', 0) > 0 else "—"
        a_pk_str = f"{a_pk.get('scores',0)}/{a_pk.get('count',0)} ({a_pk.get('score_rate',0)}%)" if a_pk.get('count', 0) > 0 else "—"
        h_mr = hs.get('mess_rate')
        a_mr = as_.get('mess_rate')
        h_mr_str = str(h_mr) if h_mr is not None else "—"
        a_mr_str = str(a_mr) if a_mr is not None else "—"
        lines.append(f"| Power Play | {h_pp_str} | {a_pp_str} |")
        lines.append(f"| Penalty Kill | {h_pk_str} | {a_pk_str} |")
        lines.append(f"| Mess Rate | {h_mr_str} | {a_mr_str} |")
    lines.append(f"| Rushing Yards | {hs.get('rushing_yards',0)} | {as_.get('rushing_yards',0)} |")
    lines.append(f"| Lateral Yards | {hs.get('lateral_yards',0)} | {as_.get('lateral_yards',0)} |")
    lines.append(f"| Yards/Play | {hs['yards_per_play']} | {as_['yards_per_play']} |")
    lines.append(f"| Total Plays | {hs['total_plays']} | {as_['total_plays']} |")
    lines.append(f"| Lateral Chains | {hs['lateral_chains']} ({hs['lateral_efficiency']}% eff) | {as_['lateral_chains']} ({as_['lateral_efficiency']}% eff) |")
    lines.append(f"| Fumbles Lost | {hs['fumbles_lost']} | {as_['fumbles_lost']} |")
    lines.append(f"| Turnovers on Downs | {hs['turnovers_on_downs']} | {as_['turnovers_on_downs']} |")
    lines.append(f"| Penalties | {hs.get('penalties',0)} for {hs.get('penalty_yards',0)} yds | {as_.get('penalties',0)} for {as_.get('penalty_yards',0)} yds |")
    lines.append(f"| Avg Fatigue | {hs['avg_fatigue']}% | {as_['avg_fatigue']}% |")
    lines.append("")

    h_dc = hs.get("down_conversions", {})
    a_dc = as_.get("down_conversions", {})
    lines.append("## Down Conversions")
    lines.append("| Down | " + home['team'] + " | " + away['team'] + " |")
    lines.append("|------|---:|---:|")
    for d in [4, 5, 6]:
        hd = h_dc.get(d, h_dc.get(str(d), {"converted": 0, "attempts": 0, "rate": 0}))
        ad = a_dc.get(d, a_dc.get(str(d), {"converted": 0, "attempts": 0, "rate": 0}))
        label = f"{'4th' if d == 4 else '5th' if d == 5 else '6th'}"
        lines.append(f"| {label} | {hd['converted']}/{hd['attempts']} ({hd['rate']}%) | {ad['converted']}/{ad['attempts']} ({ad['rate']}%) |")
    lines.append("")

    drives = result.get("drive_summary", [])
    if drives:
        lines.append("## Drive Summary")
        lines.append("| # | Team | Qtr | Start | Plays | Yards | Result |")
        lines.append("|---|------|-----|-------|-------|-------|--------|")
        for i, d in enumerate(drives):
            team_label = home['team'] if d['team'] == 'home' else away['team']
            lines.append(f"| {i+1} | {team_label} | Q{d['quarter']} | {d['start_yard_line']}yd | {d['plays']} | {d['yards']} | {drive_result_label(d['result'])} |")
        lines.append("")

    lines.append("## Play-by-Play")
    lines.append("| # | Team | Qtr | Time | Down | Pos | Family | Description | Yds | Result |")
    lines.append("|---|------|-----|------|------|-----|--------|-------------|-----|--------|")
    for p in plays:
        team_label = home['team'] if p['possession'] == 'home' else away['team']
        time_str = format_time(p['time_remaining'])
        lines.append(f"| {p['play_number']} | {team_label} | Q{p['quarter']} | {time_str} | {p['down']}&{p.get('yards_to_go','')} | {p['field_position']}yd | {p.get('play_family','')} | {p['description']} | {p['yards']} | {p['result']} |")

    return "\n".join(lines)


def generate_forum_box_score(result):
    """Generate a plain-text box score suitable for pasting into forums."""
    home = result["final_score"]["home"]
    away = result["final_score"]["away"]
    hs = result["stats"]["home"]
    as_ = result["stats"]["away"]
    plays = result["play_by_play"]

    home_q, away_q = _compute_quarter_scores(plays)

    winner = home['team'] if home['score'] > away['score'] else away['team']
    w_score = max(home['score'], away['score'])
    l_score = min(home['score'], away['score'])
    loser = away['team'] if winner == home['team'] else home['team']

    weather = result.get("weather", "clear").title()
    seed = result.get("seed", "N/A")

    lines = []
    lines.append("=" * 60)
    lines.append("COLLEGIATE VIPERBALL LEAGUE — OFFICIAL BOX SCORE")
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
    lines.append(f"  {'':22} {'-'*stat_w}  {'-'*stat_w}")
    lines.append(_stat_line("Touchdowns (9pts)", f"{hs['touchdowns']} ({hs['touchdowns']*9}pts)", f"{as_['touchdowns']} ({as_['touchdowns']*9}pts)"))
    lines.append(_stat_line("Snap Kicks (5pts)", f"{hs['drop_kicks_made']}/{hs.get('drop_kicks_attempted',0)}", f"{as_['drop_kicks_made']}/{as_.get('drop_kicks_attempted',0)}"))
    lines.append(_stat_line("Field Goals (3pts)", f"{hs['place_kicks_made']}/{hs.get('place_kicks_attempted',0)}", f"{as_['place_kicks_made']}/{as_.get('place_kicks_attempted',0)}"))
    lines.append(_stat_line("Pindowns (1pt)", hs.get('pindowns', 0), as_.get('pindowns', 0)))
    lines.append(_stat_line("Strikes (1/2pt)", hs.get('fumble_recoveries', 0), as_.get('fumble_recoveries', 0)))
    lines.append(_stat_line("Total Yards", hs['total_yards'], as_['total_yards']))
    lines.append(_stat_line("Rushing Yards", hs.get('rushing_yards', 0), as_.get('rushing_yards', 0)))
    lines.append(_stat_line("Lateral Yards", hs.get('lateral_yards', 0), as_.get('lateral_yards', 0)))
    lines.append(_stat_line("Kick Passes", f"{hs.get('kick_passes_completed',0)}/{hs.get('kick_passes_attempted',0)}", f"{as_.get('kick_passes_completed',0)}/{as_.get('kick_passes_attempted',0)}"))
    lines.append(_stat_line("Kick Pass Yards", hs.get('kick_pass_yards', 0), as_.get('kick_pass_yards', 0)))
    lines.append(_stat_line("KP TDs", hs.get('kick_pass_tds', 0), as_.get('kick_pass_tds', 0)))
    lines.append(_stat_line("Kick Pass INTs", hs.get('kick_pass_interceptions', 0), as_.get('kick_pass_interceptions', 0)))
    lines.append(_stat_line("Yards/Play", hs['yards_per_play'], as_['yards_per_play']))
    lines.append(_stat_line("Total Plays", hs['total_plays'], as_['total_plays']))
    lines.append(_stat_line("Lateral Chains", f"{hs['lateral_chains']} ({hs['lateral_efficiency']}%)", f"{as_['lateral_chains']} ({as_['lateral_efficiency']}%)"))
    lines.append(_stat_line("Fumbles Lost", hs['fumbles_lost'], as_['fumbles_lost']))
    lines.append(_stat_line("Turnovers on Downs", hs['turnovers_on_downs'], as_['turnovers_on_downs']))
    lines.append(_stat_line("Penalties", f"{hs.get('penalties',0)} / {hs.get('penalty_yards',0)}yds", f"{as_.get('penalties',0)} / {as_.get('penalty_yards',0)}yds"))
    lines.append("")

    ps = result.get("player_stats", {})
    for side_key, side_name in [("home", home['team']), ("away", away['team'])]:
        side_ps = ps.get(side_key, [])
        if not side_ps:
            continue

        lines.append("-" * 60)
        lines.append(f"INDIVIDUAL STATS — {side_name.upper()}")
        lines.append("-" * 60)

        rushers = [p for p in side_ps if p.get("rush_carries", 0) > 0]
        if rushers:
            lines.append("")
            lines.append("  Rushing & Laterals")
            lines.append(f"  {'Player':<28} CAR  YDS  RUSH  LAT   TD  FUM  L.Thr L.Rec")
            lines.append(f"  {'-'*28} ---  ---  ----  ---   --  ---  ----- -----")
            for p in rushers:
                name = f"{p['tag']} {p['name']}"
                if len(name) > 28:
                    name = name[:27] + "."
                lines.append(f"  {name:<28} {p.get('rush_carries',0):>3}  {p['yards']:>3}  {p.get('rushing_yards',0):>4}  {p.get('lateral_yards',0):>3}   {p['tds']:>2}  {p['fumbles']:>3}  {p.get('laterals_thrown',0):>5} {p.get('lateral_receptions',0):>5}")

        kickers = [p for p in side_ps if p.get("kick_att", 0) > 0]
        if kickers:
            lines.append("")
            lines.append("  Kicking")
            lines.append(f"  {'Player':<28} ATT  MADE  PCT")
            lines.append(f"  {'-'*28} ---  ----  ---")
            for p in kickers:
                name = f"{p['tag']} {p['name']}"
                if len(name) > 28:
                    name = name[:27] + "."
                pct = f"{(p['kick_made']/p['kick_att']*100):.0f}%" if p['kick_att'] > 0 else "—"
                lines.append(f"  {name:<28} {p['kick_att']:>3}  {p['kick_made']:>4}  {pct:>3}")

        kp_players = [p for p in side_ps if (p.get("kick_passes_thrown", 0) + p.get("kick_pass_receptions", 0) + p.get("kick_pass_ints", 0)) > 0]
        if kp_players:
            lines.append("")
            lines.append("  Kick Passing")
            lines.append(f"  {'Player':<28} ATT  COMP  YDS  TD  INT  REC  DINT")
            lines.append(f"  {'-'*28} ---  ----  ---  --  ---  ---  ----")
            for p in kp_players:
                name = f"{p['tag']} {p['name']}"
                if len(name) > 28:
                    name = name[:27] + "."
                lines.append(f"  {name:<28} {p.get('kick_passes_thrown',0):>3}  {p.get('kick_passes_completed',0):>4}  {p.get('kick_pass_yards',0):>3}  {p.get('kick_pass_tds',0):>2}  {p.get('kick_pass_interceptions_thrown',0):>3}  {p.get('kick_pass_receptions',0):>3}  {p.get('kick_pass_ints',0):>4}")

        st_players = [p for p in side_ps if (p.get("kick_returns", 0) + p.get("punt_returns", 0) + p.get("st_tackles", 0)) > 0]
        if st_players:
            lines.append("")
            lines.append("  Special Teams")
            lines.append(f"  {'Player':<28} KR  KRYds KRTD  PR  PRYds PRTD  Tkl")
            lines.append(f"  {'-'*28} --  ----- ----  --  ----- ----  ---")
            for p in st_players:
                name = f"{p['tag']} {p['name']}"
                if len(name) > 28:
                    name = name[:27] + "."
                lines.append(f"  {name:<28} {p.get('kick_returns',0):>2}  {p.get('kick_return_yards',0):>5} {p.get('kick_return_tds',0):>4}  {p.get('punt_returns',0):>2}  {p.get('punt_return_yards',0):>5} {p.get('punt_return_tds',0):>4}  {p.get('st_tackles',0):>3}")
        lines.append("")

    key_plays = []
    for p in plays:
        if p["result"] in ("touchdown", "punt_return_td", "int_return_td", "missed_dk_return_td"):
            key_plays.append(p)
        elif p.get("yards", 0) >= 20:
            key_plays.append(p)
        elif p.get("play_type") in ("drop_kick", "place_kick") and p["result"] == "successful_kick":
            key_plays.append(p)
        elif p.get("play_type") == "kick_pass" and p["result"] in ("touchdown", "gain", "first_down"):
            key_plays.append(p)

    if key_plays:
        lines.append("-" * 60)
        lines.append("KEY PLAYS")
        lines.append("-" * 60)
        for p in key_plays[:12]:
            q = p["quarter"]
            tr = p["time_remaining"]
            m, s = tr // 60, tr % 60
            side = "HOME" if p["possession"] == "home" else "AWAY"
            lines.append(f"  Q{q} {m:02d}:{s:02d} [{side}] {p['description']}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("CVL Official Box Score | 6-down, 20-yard system")
    lines.append("Scoring: TD 9 | SK 5 | FG 3 | Safety 2 | Pindown 1 | Strike 1/2")
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
    writer.writerow(["drive_number", "team", "quarter", "start_yard_line", "plays", "yards", "result"])
    for i, d in enumerate(drives):
        team_label = home_name if d["team"] == "home" else away_name
        writer.writerow([i + 1, team_label, d["quarter"], d["start_yard_line"],
                         d["plays"], d["yards"], d["result"]])
    return output.getvalue()


def generate_batch_summary_csv(results):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["game", "seed", "home_team", "away_team", "home_score", "away_score",
                     "home_yards", "away_yards", "home_tds", "away_tds",
                     "home_fumbles", "away_fumbles", "home_plays", "away_plays",
                     "home_kick_pct", "away_kick_pct", "home_pindowns", "away_pindowns",
                     "home_snap_kicks", "away_snap_kicks", "home_lat_eff", "away_lat_eff",
                     "total_drives", "winner"])
    for i, r in enumerate(results):
        h = r["final_score"]["home"]
        a = r["final_score"]["away"]
        hs = r["stats"]["home"]
        as_ = r["stats"]["away"]
        winner = h["team"] if h["score"] > a["score"] else (a["team"] if a["score"] > h["score"] else "TIE")
        writer.writerow([
            i + 1, r.get("seed", ""), h["team"], a["team"], fmt_vb_score(h["score"]), fmt_vb_score(a["score"]),
            hs["total_yards"], as_["total_yards"], hs["touchdowns"], as_["touchdowns"],
            hs["fumbles_lost"], as_["fumbles_lost"], hs["total_plays"], as_["total_plays"],
            hs.get("kick_percentage", 0), as_.get("kick_percentage", 0),
            hs.get("pindowns", 0), as_.get("pindowns", 0),
            hs.get("drop_kicks_made", 0), as_.get("drop_kicks_made", 0),
            hs.get("lateral_efficiency", 0), as_.get("lateral_efficiency", 0),
            len(r.get("drive_summary", [])), winner
        ])
    return output.getvalue()


def generate_batch_full_export(results):
    """Build a comprehensive JSON-serialisable dict of all batch aggregate stats.

    Includes every metric the debug-tools page computes so that the full
    analysis can be consumed by external tools without copy-pasting.
    """
    from collections import Counter, defaultdict

    n = len(results)
    home_name = results[0]["final_score"]["home"]["team"]
    away_name = results[0]["final_score"]["away"]["team"]

    home_scores = [r["final_score"]["home"]["score"] for r in results]
    away_scores = [r["final_score"]["away"]["score"] for r in results]
    home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
    away_wins = sum(1 for h, a in zip(home_scores, away_scores) if a > h)
    ties = n - home_wins - away_wins

    def _avg(vals):
        return round(sum(vals) / max(1, len(vals)), 4)

    def _side(key, side):
        return [r["stats"][side].get(key, 0) for r in results]

    # ── Per-game rows ──
    per_game = []
    for i, r in enumerate(results):
        h = r["final_score"]["home"]
        a = r["final_score"]["away"]
        hs = r["stats"]["home"]
        as_ = r["stats"]["away"]
        winner = h["team"] if h["score"] > a["score"] else (a["team"] if a["score"] > h["score"] else "TIE")
        per_game.append({
            "game": i + 1,
            "seed": r.get("seed", None),
            "home_score": h["score"],
            "away_score": a["score"],
            "winner": winner,
            "home_stats": hs,
            "away_stats": as_,
            "drive_summary": r.get("drive_summary", []),
        })

    # ── Core aggregates ──
    home_yards = _side("total_yards", "home")
    away_yards = _side("total_yards", "away")
    home_tds = _side("touchdowns", "home")
    away_tds = _side("touchdowns", "away")
    home_fumbles = _side("fumbles_lost", "home")
    away_fumbles = _side("fumbles_lost", "away")

    longest_plays = []
    for r in results:
        mx = max((p["yards"] for p in r["play_by_play"] if p["play_type"] not in ["punt"]), default=0)
        longest_plays.append(mx)

    # ── Kicking / special teams ──
    home_kick_pct = _side("kick_percentage", "home")
    away_kick_pct = _side("kick_percentage", "away")
    home_pindowns = _side("pindowns", "home")
    away_pindowns = _side("pindowns", "away")
    home_lat_eff = _side("lateral_efficiency", "home")
    away_lat_eff = _side("lateral_efficiency", "away")
    home_dk = _side("drop_kicks_made", "home")
    away_dk = _side("drop_kicks_made", "away")
    home_pk = _side("place_kicks_made", "home")
    away_pk = _side("place_kicks_made", "away")
    home_bells = _side("bells", "home")
    away_bells = _side("bells", "away")
    home_punts = _side("punts", "home")
    away_punts = _side("punts", "away")
    home_saf = _side("safeties_conceded", "home")
    away_saf = _side("safeties_conceded", "away")

    # ── Down conversions ──
    down_conv = {}
    for d in [4, 5, 6]:
        rates = []
        for r in results:
            for side in ["home", "away"]:
                dc = r["stats"][side].get("down_conversions", {})
                dd = dc.get(d, dc.get(str(d), {"rate": 0}))
                rates.append(dd["rate"])
        down_conv[f"{d}th"] = round(_avg(rates), 1)

    # ── WPA ──
    home_total_vpa = [
        r["stats"]["home"].get("epa", {}).get(
            "total_vpa", r["stats"]["home"].get("epa", {}).get("total_epa", 0)
        ) for r in results
    ]
    away_total_vpa = [
        r["stats"]["away"].get("epa", {}).get(
            "total_vpa", r["stats"]["away"].get("epa", {}).get("total_epa", 0)
        ) for r in results
    ]
    home_vpa_pp = [
        r["stats"]["home"].get("epa", {}).get(
            "vpa_per_play", r["stats"]["home"].get("epa", {}).get("epa_per_play", 0)
        ) for r in results
    ]
    away_vpa_pp = [
        r["stats"]["away"].get("epa", {}).get(
            "vpa_per_play", r["stats"]["away"].get("epa", {}).get("epa_per_play", 0)
        ) for r in results
    ]
    home_sr = [r["stats"]["home"].get("epa", {}).get("success_rate", 0) for r in results]
    away_sr = [r["stats"]["away"].get("epa", {}).get("success_rate", 0) for r in results]
    home_exp = [r["stats"]["home"].get("epa", {}).get("explosiveness", 0) for r in results]
    away_exp = [r["stats"]["away"].get("epa", {}).get("explosiveness", 0) for r in results]

    # ── DYE ──
    all_pen_ypd, all_bst_ypd, all_neu_ypd = [], [], []
    all_pen_sr, all_bst_sr, all_neu_sr = [], [], []
    total_opp_boost_scores = 0
    wins_despite_delta = 0
    total_bonus_scores = 0
    total_bonus_drives = 0

    for r in results:
        for side in ["home", "away"]:
            dye = r["stats"][side].get("dye", {})
            pen = dye.get("penalized", {})
            bst = dye.get("boosted", {})
            neu = dye.get("neutral", {})
            if pen.get("count", 0) > 0:
                all_pen_ypd.append(pen["yards_per_drive"])
                all_pen_sr.append(pen["score_rate"])
            if bst.get("count", 0) > 0:
                all_bst_ypd.append(bst["yards_per_drive"])
                all_bst_sr.append(bst["score_rate"])
            if neu.get("count", 0) > 0:
                all_neu_ypd.append(neu["yards_per_drive"])
                all_neu_sr.append(neu["score_rate"])
            total_bonus_scores += r["stats"][side].get("bonus_possession_scores", 0)
            total_bonus_drives += r["stats"][side].get("bonus_possessions", 0)

        w = "home" if r["final_score"]["home"]["score"] > r["final_score"]["away"]["score"] else "away"
        l = "away" if w == "home" else "home"
        if r["stats"][w].get("dye", {}).get("penalized", {}).get("count", 0) > 0:
            wins_despite_delta += 1
        total_opp_boost_scores += r["stats"][l].get("dye", {}).get("boosted", {}).get("scores", 0)

    avg_pen_ypd = round(_avg(all_pen_ypd), 1) if all_pen_ypd else 0
    avg_bst_ypd = round(_avg(all_bst_ypd), 1) if all_bst_ypd else 0
    avg_neu_ypd = round(_avg(all_neu_ypd), 1) if all_neu_ypd else 0
    avg_pen_sr = round(_avg(all_pen_sr), 1) if all_pen_sr else 0
    avg_bst_sr = round(_avg(all_bst_sr), 1) if all_bst_sr else 0
    avg_neu_sr = round(_avg(all_neu_sr), 1) if all_neu_sr else 0

    # ── Drive outcomes ──
    outcome_counts = {}
    total_drives = 0
    for r in results:
        for d in r.get("drive_summary", []):
            label = drive_result_label(d["result"])
            outcome_counts[label] = outcome_counts.get(label, 0) + 1
            total_drives += 1
    drive_distribution = {k: round(v / max(1, total_drives) * 100, 2) for k, v in outcome_counts.items()}

    # ── Turnovers ──
    home_tod = _side("turnovers_on_downs", "home")
    away_tod = _side("turnovers_on_downs", "away")

    # ── Defensive performance ──
    def _def_block(off_side, def_label):
        return {
            "avg_kp_ints_forced": round(_avg(_side("kick_pass_interceptions", off_side)), 2),
            "avg_lateral_ints_forced": round(_avg(_side("lateral_interceptions", off_side)), 2),
            "avg_fumbles_forced": round(_avg(_side("fumbles_lost", off_side)), 2),
            "avg_total_turnovers_forced": round(
                _avg([a + b + c for a, b, c in zip(
                    _side("kick_pass_interceptions", off_side),
                    _side("lateral_interceptions", off_side),
                    _side("fumbles_lost", off_side),
                )]), 2),
            "avg_yards_allowed": round(_avg(_side("total_yards", off_side)), 1),
            "avg_tds_allowed": round(_avg(_side("touchdowns", off_side)), 2),
        }

    # ── DC Gameplan / Modifier Stack ──
    play_types = ("run", "lateral", "kick_pass", "trick")
    dc_data = {}
    for side_key, label in [("home_defense", home_name), ("away_defense", away_name)]:
        dc_accum = {pt: [] for pt in play_types}
        temp_counts = defaultdict(int)
        solved_counts = defaultdict(int)
        nfz_count = 0

        for r in results:
            ms = r.get("modifier_stack", {}).get(side_key, {})
            if not ms:
                continue
            gp = ms.get("dc_gameplan", {})
            for pt in play_types:
                if pt in gp:
                    dc_accum[pt].append(gp[pt])
            temp_counts[ms.get("game_temperature", "neutral")] += 1
            for fam in ms.get("solved_families", {}):
                solved_counts[fam] += 1
            if ms.get("no_fly_zone", False):
                nfz_count += 1

        suppression = {}
        for pt in play_types:
            vals = dc_accum[pt]
            if vals:
                suppression[pt] = {"avg": round(_avg(vals), 3), "min": round(min(vals), 3), "max": round(max(vals), 3)}
        total_temps = sum(temp_counts.values())
        dc_data[label] = {
            "suppression": suppression,
            "game_temperature": {t: {"count": c, "pct": round(c / max(1, total_temps) * 100, 1)} for t, c in temp_counts.items()},
            "solved_families": dict(solved_counts),
            "no_fly_zone_games": nfz_count,
        }

    # ── Adaptation events ──
    all_adapt = []
    for r in results:
        all_adapt.extend(r.get("adaptation_log", []))
    adapt_counts = Counter(all_adapt)

    # ── Offensive performance ──
    off_data = {}
    for side, label in [("home", home_name), ("away", away_name)]:
        stats_list = [r["stats"][side] for r in results]
        rush_car = [s.get("rushing_carries", 0) for s in stats_list]
        rush_yds = [s.get("rushing_yards", 0) for s in stats_list]
        rush_tds = [s.get("rushing_touchdowns", 0) for s in stats_list]
        kp_att = [s.get("kick_passes_attempted", 0) for s in stats_list]
        kp_comp = [s.get("kick_passes_completed", 0) for s in stats_list]
        kp_yds = [s.get("kick_pass_yards", 0) for s in stats_list]
        kp_tds = [s.get("kick_pass_tds", 0) for s in stats_list]
        kp_ints = [s.get("kick_pass_interceptions", 0) for s in stats_list]
        lat_chains = [s.get("lateral_chains", 0) for s in stats_list]
        l_eff = [s.get("lateral_efficiency", 0) for s in stats_list]
        lat_yds = [s.get("lateral_yards", 0) for s in stats_list]
        dk_att = [s.get("drop_kicks_attempted", 0) for s in stats_list]
        dk_made = [s.get("drop_kicks_made", 0) for s in stats_list]
        pk_a = [s.get("place_kicks_attempted", 0) for s in stats_list]
        pk_m = [s.get("place_kicks_made", 0) for s in stats_list]
        t_yds = [s.get("total_yards", 0) for s in stats_list]
        t_plays = [s.get("total_plays", 0) for s in stats_list]
        o_tds = [s.get("touchdowns", 0) for s in stats_list]
        tricks = [s.get("play_family_breakdown", {}).get("trick_play", 0) for s in stats_list]

        fam_accum = {}
        for s in stats_list:
            for fam, count in s.get("play_family_breakdown", {}).items():
                fam_accum[fam] = fam_accum.get(fam, 0) + count
        total_fam = sum(fam_accum.values()) or 1

        off_data[label] = {
            "avg_total_yards": round(_avg(t_yds), 1),
            "avg_total_plays": round(_avg(t_plays), 1),
            "avg_yards_per_play": round(sum(t_yds) / max(1, sum(t_plays)), 2),
            "avg_touchdowns": round(_avg(o_tds), 2),
            "rushing": {
                "avg_carries": round(_avg(rush_car), 1),
                "avg_yards": round(_avg(rush_yds), 1),
                "ypc": round(sum(rush_yds) / max(1, sum(rush_car)), 2),
                "avg_tds": round(_avg(rush_tds), 2),
            },
            "kick_pass": {
                "avg_attempts": round(_avg(kp_att), 1),
                "avg_completions": round(_avg(kp_comp), 1),
                "completion_pct": round(sum(kp_comp) / max(1, sum(kp_att)) * 100, 1),
                "avg_yards": round(_avg(kp_yds), 1),
                "avg_tds": round(_avg(kp_tds), 2),
                "avg_interceptions": round(_avg(kp_ints), 2),
            },
            "laterals": {
                "avg_chains": round(_avg(lat_chains), 1),
                "avg_yards": round(_avg(lat_yds), 1),
                "avg_efficiency": round(_avg(l_eff), 1),
            },
            "snap_kicks": {
                "avg_attempts": round(_avg(dk_att), 1),
                "avg_made": round(_avg(dk_made), 1),
                "pct": round(sum(dk_made) / max(1, sum(dk_att)) * 100, 1),
            },
            "field_goals": {
                "avg_attempts": round(_avg(pk_a), 1),
                "avg_made": round(_avg(pk_m), 1),
                "pct": round(sum(pk_m) / max(1, sum(pk_a)) * 100, 1),
            },
            "avg_trick_plays": round(_avg(tricks), 1),
            "play_family_distribution": {
                fam: {"total": count, "avg_per_game": round(count / n, 1), "share_pct": round(count / total_fam * 100, 1)}
                for fam, count in sorted(fam_accum.items(), key=lambda x: -x[1])
            },
        }

    # ── Player impact ──
    player_data = {}
    for side, team_name in [("home", home_name), ("away", away_name)]:
        accum = defaultdict(lambda: {
            "tag": "", "vpa_sum": 0.0, "plays_sum": 0, "touches_sum": 0,
            "yards_sum": 0, "tds_sum": 0, "fumbles_sum": 0, "games": 0,
        })
        for r in results:
            for p in r.get("player_stats", {}).get(side, []):
                if p.get("plays_involved", 0) == 0:
                    continue
                rec = accum[p["name"]]
                rec["tag"] = p["tag"]
                rec["vpa_sum"] += p.get("vpa", 0)
                rec["plays_sum"] += p.get("plays_involved", 0)
                rec["touches_sum"] += p.get("touches", 0)
                rec["yards_sum"] += p.get("yards", 0)
                rec["tds_sum"] += p.get("tds", 0)
                rec["fumbles_sum"] += p.get("fumbles", 0)
                rec["games"] += 1

        players = []
        for name, rec in sorted(accum.items(), key=lambda kv: kv[1]["vpa_sum"] / max(1, kv[1]["games"]), reverse=True):
            g = rec["games"]
            players.append({
                "name": name,
                "position": rec["tag"],
                "games": g,
                "avg_wpa": round(rec["vpa_sum"] / max(1, g), 2),
                "avg_wpa_per_play": round(rec["vpa_sum"] / max(1, rec["plays_sum"]), 3),
                "avg_plays": round(rec["plays_sum"] / max(1, g), 1),
                "avg_touches": round(rec["touches_sum"] / max(1, g), 1),
                "avg_yards": round(rec["yards_sum"] / max(1, g), 1),
                "avg_tds": round(rec["tds_sum"] / max(1, g), 2),
                "avg_fumbles": round(rec["fumbles_sum"] / max(1, g), 2),
            })
        player_data[team_name] = players

    # ── Fatigue ──
    fatigue_by_play = defaultdict(lambda: defaultdict(list))
    for r in results:
        for p in r["play_by_play"]:
            if p.get("fatigue") is not None:
                team = home_name if p["possession"] == "home" else away_name
                fatigue_by_play[team][p["play_number"]].append(p["fatigue"])
    fatigue_curves = {}
    for team in [home_name, away_name]:
        curve = []
        for play_num in sorted(fatigue_by_play[team].keys()):
            vals = fatigue_by_play[team][play_num]
            curve.append({"play": play_num, "avg_fatigue": round(sum(vals) / len(vals), 1)})
        fatigue_curves[team] = curve

    export = {
        "metadata": {
            "num_simulations": n,
            "home_team": home_name,
            "away_team": away_name,
        },
        "record": {
            "home_wins": home_wins,
            "away_wins": away_wins,
            "ties": ties,
            "tie_pct": round(ties / n * 100, 1),
        },
        "score_averages": {
            "home_avg_score": round(_avg(home_scores), 2),
            "away_avg_score": round(_avg(away_scores), 2),
            "home_avg_yards": round(_avg(home_yards), 1),
            "away_avg_yards": round(_avg(away_yards), 1),
        },
        "scoring_breakdown": {
            "avg_tds_per_team": round((sum(home_tds) + sum(away_tds)) / (2 * n), 2),
            "avg_fumbles_per_team": round((sum(home_fumbles) + sum(away_fumbles)) / (2 * n), 2),
            "avg_longest_play": round(_avg(longest_plays), 1),
            "max_longest_play": max(longest_plays),
        },
        "kicking_special_teams": {
            "avg_kick_pct": round((sum(home_kick_pct) + sum(away_kick_pct)) / (2 * n), 1),
            "avg_pindowns_per_game": round((sum(home_pindowns) + sum(away_pindowns)) / n, 2),
            "avg_lateral_eff": round((sum(home_lat_eff) + sum(away_lat_eff)) / (2 * n), 1),
            "avg_snap_kicks_per_team": round((sum(home_dk) + sum(away_dk)) / (2 * n), 2),
            "avg_fgs_made_per_team": round((sum(home_pk) + sum(away_pk)) / (2 * n), 2),
            "avg_bells_per_team": round((sum(home_bells) + sum(away_bells)) / (2 * n), 2),
            "avg_punts_per_team": round((sum(home_punts) + sum(away_punts)) / (2 * n), 2),
            "avg_safeties_per_team": round((sum(home_saf) + sum(away_saf)) / (2 * n), 2),
        },
        "down_conversions": down_conv,
        "wpa": {
            "home_avg_total_wpa": round(_avg(home_total_vpa), 2),
            "away_avg_total_wpa": round(_avg(away_total_vpa), 2),
            "home_avg_wpa_per_play": round(_avg(home_vpa_pp), 3),
            "away_avg_wpa_per_play": round(_avg(away_vpa_pp), 3),
            "home_avg_success_rate": round(_avg(home_sr), 1),
            "away_avg_success_rate": round(_avg(away_sr), 1),
            "home_avg_explosiveness": round(_avg(home_exp), 3),
            "away_avg_explosiveness": round(_avg(away_exp), 3),
        },
        "dye": {
            "penalized_ypd": avg_pen_ypd,
            "boosted_ypd": avg_bst_ypd,
            "neutral_ypd": avg_neu_ypd,
            "dye_ratio": round(avg_pen_ypd / avg_neu_ypd, 2) if avg_neu_ypd > 0 else None,
            "penalized_score_pct": avg_pen_sr,
            "boosted_score_pct": avg_bst_sr,
            "neutral_score_pct": avg_neu_sr,
            "wins_despite_delta_penalty": wins_despite_delta,
            "opp_cheap_boost_scores_per_game": round(total_opp_boost_scores / n, 1),
            "bonus_possession_score_pct": round(total_bonus_scores / max(1, total_bonus_drives) * 100, 1),
            "bonus_scores_per_game": round(total_bonus_scores / n, 2),
        },
        "drive_outcome_distribution": drive_distribution,
        "total_drives": total_drives,
        "turnovers": {
            "home_avg_fumbles": round(_avg(home_fumbles), 2),
            "away_avg_fumbles": round(_avg(away_fumbles), 2),
            "home_avg_turnovers_on_downs": round(_avg(home_tod), 2),
            "away_avg_turnovers_on_downs": round(_avg(away_tod), 2),
            "home_total_turnovers_per_game": round((sum(home_fumbles) + sum(home_tod)) / n, 2),
            "away_total_turnovers_per_game": round((sum(away_fumbles) + sum(away_tod)) / n, 2),
        },
        "defensive_performance": {
            home_name: _def_block("away", home_name),
            away_name: _def_block("home", away_name),
        },
        "dc_gameplan": dc_data,
        "adaptation_events": {
            "total": len(all_adapt),
            "avg_per_game": round(len(all_adapt) / n, 1),
            "top_events": [{"event": ev, "count": ct, "per_game": round(ct / n, 2)} for ev, ct in adapt_counts.most_common(20)],
        },
        "offensive_performance": off_data,
        "player_impact": player_data,
        "fatigue_curves": fatigue_curves,
        "per_game": per_game,
    }
    return export


def safe_filename(name):
    return name.lower().replace(" ", "_").replace("'", "")


def drive_result_label(result):
    labels = {
        "touchdown": "TD",
        "successful_kick": "SK/FG",
        "fumble": "STRIKE (+½)",
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
    }
    return labels.get(result, result.upper())


def drive_result_color(result):
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
    }
    return colors.get(result, "#94a3b8")


def render_game_detail(result, key_prefix="gd"):
    """Render a full game detail view from a game result dict."""
    home = result["final_score"]["home"]
    away = result["final_score"]["away"]
    hs = result["stats"]["home"]
    as_ = result["stats"]["away"]
    plays = result["play_by_play"]
    home_name = home["team"]
    away_name = away["team"]

    winner = home_name if home["score"] > away["score"] else away_name
    w_score = max(home["score"], away["score"])
    l_score = min(home["score"], away["score"])
    loser = away_name if winner == home_name else home_name

    rivalry_tag = ""
    if result.get("is_rivalry_game"):
        rivalry_tag = " :crossed_swords: **RIVALRY**"
    st.markdown(f"### {winner} {fmt_vb_score(w_score)} - {loser} {fmt_vb_score(l_score)}{rivalry_tag}")

    weather = result.get("weather", "clear")
    seed = result.get("seed", "N/A")
    caption_parts = [f"Weather: {weather.title()}", f"Seed: {seed}"]
    st.caption(" | ".join(caption_parts))

    home_q, away_q = _compute_quarter_scores(plays)

    q_data = []
    q_data.append({"Team": home_name, "Q1": fmt_vb_score(home_q[1]), "Q2": fmt_vb_score(home_q[2]),
                    "Q3": fmt_vb_score(home_q[3]), "Q4": fmt_vb_score(home_q[4]),
                    "Final": fmt_vb_score(home["score"])})
    q_data.append({"Team": away_name, "Q1": fmt_vb_score(away_q[1]), "Q2": fmt_vb_score(away_q[2]),
                    "Q3": fmt_vb_score(away_q[3]), "Q4": fmt_vb_score(away_q[4]),
                    "Final": fmt_vb_score(away["score"])})
    st.dataframe(pd.DataFrame(q_data), hide_index=True, use_container_width=True)

    st.markdown("**Team Stats**")
    stat_rows = [
        {"Stat": "Touchdowns (9pts)", home_name: f"{hs['touchdowns']} ({hs['touchdowns']*9}pts)", away_name: f"{as_['touchdowns']} ({as_['touchdowns']*9}pts)"},
        {"Stat": "Snap Kicks (5pts)", home_name: f"{hs['drop_kicks_made']}/{hs.get('drop_kicks_attempted',0)}", away_name: f"{as_['drop_kicks_made']}/{as_.get('drop_kicks_attempted',0)}"},
        {"Stat": "Field Goals (3pts)", home_name: f"{hs['place_kicks_made']}/{hs.get('place_kicks_attempted',0)}", away_name: f"{as_['place_kicks_made']}/{as_.get('place_kicks_attempted',0)}"},
        {"Stat": "Pindowns (1pt)", home_name: str(hs.get('pindowns',0)), away_name: str(as_.get('pindowns',0))},
        {"Stat": "Strikes (1/2pt)", home_name: str(hs.get('fumble_recoveries',0)), away_name: str(as_.get('fumble_recoveries',0))},
        {"Stat": "Total Yards", home_name: str(hs['total_yards']), away_name: str(as_['total_yards'])},
        {"Stat": "Rushing Yards", home_name: str(hs.get('rushing_yards',0)), away_name: str(as_.get('rushing_yards',0))},
        {"Stat": "Lateral Yards", home_name: str(hs.get('lateral_yards',0)), away_name: str(as_.get('lateral_yards',0))},
        {"Stat": "KP (Comp/Att)", home_name: f"{hs.get('kick_passes_completed',0)}/{hs.get('kick_passes_attempted',0)}", away_name: f"{as_.get('kick_passes_completed',0)}/{as_.get('kick_passes_attempted',0)}"},
        {"Stat": "KP Yards", home_name: str(hs.get('kick_pass_yards',0)), away_name: str(as_.get('kick_pass_yards',0))},
        {"Stat": "KP TDs", home_name: str(hs.get('kick_pass_tds',0)), away_name: str(as_.get('kick_pass_tds',0))},
        {"Stat": "KP INTs", home_name: str(hs.get('kick_pass_interceptions',0)), away_name: str(as_.get('kick_pass_interceptions',0))},
        {"Stat": "Yards/Play", home_name: str(hs['yards_per_play']), away_name: str(as_['yards_per_play'])},
        {"Stat": "Total Plays", home_name: str(hs['total_plays']), away_name: str(as_['total_plays'])},
        {"Stat": "Fumbles Lost", home_name: str(hs['fumbles_lost']), away_name: str(as_['fumbles_lost'])},
        {"Stat": "Penalties", home_name: f"{hs.get('penalties',0)} for {hs.get('penalty_yards',0)} yds", away_name: f"{as_.get('penalties',0)} for {as_.get('penalty_yards',0)} yds"},
    ]
    h_delta_dr = hs.get('delta_drives', 0)
    a_delta_dr = as_.get('delta_drives', 0)
    if h_delta_dr or a_delta_dr:
        stat_rows.extend([
            {"Stat": "Delta Yards", home_name: str(hs.get('delta_yards', 0)), away_name: str(as_.get('delta_yards', 0))},
            {"Stat": "Adjusted Yards", home_name: str(hs.get('adjusted_yards', hs['total_yards'])), away_name: str(as_.get('adjusted_yards', as_['total_yards']))},
            {"Stat": "Delta Drives", home_name: str(h_delta_dr), away_name: str(a_delta_dr)},
            {"Stat": "Delta Scores", home_name: str(hs.get('delta_scores', 0)), away_name: str(as_.get('delta_scores', 0))},
        ])
        h_kr = hs.get('kill_rate')
        a_kr = as_.get('kill_rate')
        if h_kr is not None or a_kr is not None:
            stat_rows.append({"Stat": "Kill Rate", home_name: f"{h_kr}%" if h_kr is not None else "—", away_name: f"{a_kr}%" if a_kr is not None else "—"})
        # Power Play / Penalty Kill / Mess Rate
        h_dye2 = hs.get('dye', {})
        a_dye2 = as_.get('dye', {})
        h_pp2 = h_dye2.get('power_play', {})
        a_pp2 = a_dye2.get('power_play', {})
        h_pk2 = h_dye2.get('penalty_kill', {})
        a_pk2 = a_dye2.get('penalty_kill', {})
        def _fmt_pp_pk(bucket):
            if bucket.get("count", 0) == 0:
                return "—"
            return f"{bucket['scores']}/{bucket['count']} ({bucket['score_rate']}%)"
        if h_pp2.get('count', 0) > 0 or a_pp2.get('count', 0) > 0:
            stat_rows.append({"Stat": "Power Play", home_name: _fmt_pp_pk(h_pp2), away_name: _fmt_pp_pk(a_pp2)})
            stat_rows.append({"Stat": "Penalty Kill", home_name: _fmt_pp_pk(h_pk2), away_name: _fmt_pp_pk(a_pk2)})
            h_mr2 = hs.get('mess_rate')
            a_mr2 = as_.get('mess_rate')
            stat_rows.append({"Stat": "Mess Rate", home_name: str(h_mr2) if h_mr2 is not None else "—", away_name: str(a_mr2) if a_mr2 is not None else "—"})
    st.dataframe(pd.DataFrame(stat_rows), hide_index=True, use_container_width=True)

    ps = result.get("player_stats", {})
    home_ps = ps.get("home", [])
    away_ps = ps.get("away", [])

    if home_ps or away_ps:
        with st.expander("Individual Player Stats", expanded=True):
            for side_label, side_ps, side_name in [("Home", home_ps, home_name), ("Away", away_ps, away_name)]:
                if not side_ps:
                    continue
                st.markdown(f"**{side_name}**")

                rush_rows = [p for p in side_ps if p.get("rush_carries", 0) > 0]
                if rush_rows:
                    st.caption("Rushing & Laterals")
                    rush_df = []
                    for p in rush_rows:
                        rush_df.append({
                            "Player": f"{p['tag']} {p['name']}",
                            "Arch": p.get("archetype", ""),
                            "CAR": p.get("rush_carries", 0),
                            "Rush Yds": p.get("rushing_yards", 0),
                            "LAT": p.get("lateral_yards", 0),
                            "TD": p["tds"],
                            "FUM": p["fumbles"],
                            "L.Thr": p.get("laterals_thrown", 0),
                            "L.Rec": p.get("lateral_receptions", 0),
                            "L.Ast": p.get("lateral_assists", 0),
                            "L.TD": p.get("lateral_tds", 0),
                        })
                    st.dataframe(pd.DataFrame(rush_df), hide_index=True, use_container_width=True)

                kick_rows = [p for p in side_ps if p.get("kick_att", 0) > 0]
                if kick_rows:
                    st.caption("Kicking")
                    kick_df = []
                    for p in kick_rows:
                        kick_df.append({
                            "Player": f"{p['tag']} {p['name']}",
                            "ATT": p["kick_att"],
                            "MADE": p["kick_made"],
                            "PCT": f"{(p['kick_made']/p['kick_att']*100):.0f}%" if p["kick_att"] > 0 else "—",
                            "BLK": p.get("kick_deflections", 0),
                        })
                    st.dataframe(pd.DataFrame(kick_df), hide_index=True, use_container_width=True)

                kp_rows = [p for p in side_ps if (p.get("kick_passes_thrown", 0) + p.get("kick_pass_receptions", 0) + p.get("kick_pass_ints", 0)) > 0]
                if kp_rows:
                    st.caption("Kick Passing")
                    kp_df = []
                    for p in kp_rows:
                        kp_df.append({
                            "Player": f"{p['tag']} {p['name']}",
                            "KP Att": p.get("kick_passes_thrown", 0),
                            "KP Comp": p.get("kick_passes_completed", 0),
                            "KP Yds": p.get("kick_pass_yards", 0),
                            "KP TD": p.get("kick_pass_tds", 0),
                            "KP INT": p.get("kick_pass_interceptions_thrown", 0),
                            "KP Rec": p.get("kick_pass_receptions", 0),
                            "Def KP INT": p.get("kick_pass_ints", 0),
                        })
                    st.dataframe(pd.DataFrame(kp_df), hide_index=True, use_container_width=True)

                st_rows = [p for p in side_ps if (p.get("kick_returns", 0) + p.get("punt_returns", 0) + p.get("st_tackles", 0) + p.get("keeper_bells", 0) + p.get("coverage_snaps", 0)) > 0]
                if st_rows:
                    st.caption("Special Teams & Defense")
                    st_df = []
                    for p in st_rows:
                        st_df.append({
                            "Player": f"{p['tag']} {p['name']}",
                            "KR": p.get("kick_returns", 0),
                            "KR Yds": p.get("kick_return_yards", 0),
                            "KR TD": p.get("kick_return_tds", 0),
                            "PR": p.get("punt_returns", 0),
                            "PR Yds": p.get("punt_return_yards", 0),
                            "PR TD": p.get("punt_return_tds", 0),
                            "Muffs": p.get("muffs", 0),
                            "ST Tkl": p.get("st_tackles", 0),
                            "Bells": p.get("keeper_bells", 0),
                            "Cov": p.get("coverage_snaps", 0),
                        })
                    st.dataframe(pd.DataFrame(st_df), hide_index=True, use_container_width=True)
                st.divider()

    in_game_inj = result.get("in_game_injuries", [])
    if in_game_inj:
        with st.expander("In-Game Injuries & Substitutions", expanded=True):
            for ig in in_game_inj:
                severity = "OUT FOR SEASON" if ig.get("season_ending") else (ig.get("tier") or "").replace("_", "-").upper()
                cat_labels = {"on_field_contact": "Contact", "on_field_noncontact": "Non-Contact", "practice": "Practice", "off_field": "Off-Field"}
                cat = cat_labels.get(ig.get("category", ""), ig.get("category", ""))
                line = f"**{ig['player']}** ({ig['position']}) — {ig['description']} [{severity}] *({cat})*"
                if ig.get("substitute"):
                    oop = " *(out of position)*" if ig.get("out_of_position") else ""
                    line += f"  \n&emsp;-> {ig['substitute']} ({ig['sub_position']}) sub in{oop}"
                st.markdown(line)

    drives = result.get("drive_summary", [])
    if drives:
        with st.expander("Drive Summary", expanded=False):
            drive_rows = []
            for i, d in enumerate(drives):
                team_label = home_name if d['team'] == 'home' else away_name
                result_lbl = drive_result_label(d['result'])
                if d.get('delta_drive'):
                    result_lbl += " Δ"
                drive_rows.append({
                    "#": i + 1,
                    "Team": team_label,
                    "Qtr": f"Q{d['quarter']}",
                    "Start": f"{d['start_yard_line']}yd",
                    "Plays": d['plays'],
                    "Yards": d['yards'],
                    "Result": result_lbl,
                })
            st.dataframe(pd.DataFrame(drive_rows), hide_index=True, use_container_width=True)

    with st.expander("Play-by-Play", expanded=False):
        quarter_filter = st.multiselect("Filter by Quarter", [1, 2, 3, 4], default=[1, 2, 3, 4], key=f"{key_prefix}_qfilter")
        filtered_plays = [p for p in plays if p.get("quarter") in quarter_filter]
        play_rows = []
        for p in filtered_plays:
            team_label = home_name if p['possession'] == 'home' else away_name
            play_rows.append({
                "#": p['play_number'],
                "INJ": "!" if "INJURY:" in p.get('description', '') else "",
                "Team": team_label,
                "Qtr": f"Q{p['quarter']}",
                "Time": format_time(p['time_remaining']),
                "Down": f"{p['down']}&{p.get('yards_to_go','')}",
                "FP": f"{p['field_position']}yd",
                "Family": p.get('play_family', ''),
                "Description": p['description'],
                "Yds": p['yards'],
                "Result": p['result'],
            })
        st.dataframe(pd.DataFrame(play_rows), hide_index=True, use_container_width=True, height=400)

    with st.expander("Export Game Data", expanded=False):
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button("Download Play Log (CSV)", generate_play_log_csv(result),
                               file_name=f"{safe_filename(home_name)}_vs_{safe_filename(away_name)}_plays.csv",
                               mime="text/csv", key=f"{key_prefix}_dl_plays")
        with dl2:
            st.download_button("Download Drives (CSV)", generate_drives_csv(result),
                               file_name=f"{safe_filename(home_name)}_vs_{safe_filename(away_name)}_drives.csv",
                               mime="text/csv", key=f"{key_prefix}_dl_drives")

        st.divider()
        st.markdown("**Forum-Ready Box Score**")
        st.caption("Copy the text below and paste it into any forum or message board.")
        forum_text = generate_forum_box_score(result)
        st.text_area("Box Score (select all, copy)", forum_text, height=400, key=f"{key_prefix}_forum_box")
        st.download_button("Download Box Score (.txt)", forum_text,
                           file_name=f"{safe_filename(home_name)}_vs_{safe_filename(away_name)}_boxscore.txt",
                           mime="text/plain", key=f"{key_prefix}_dl_forum")


@st.cache_resource
def get_shared_data():
    teams = get_available_teams()
    styles = get_available_styles()
    return {
        "teams": teams,
        "styles": styles,
        "team_names": {t["key"]: t["name"] for t in teams},
        "style_keys": list(styles.keys()),
        "defense_style_keys": list(DEFENSE_STYLES.keys()),
        "defense_styles": DEFENSE_STYLES,
        "OFFENSE_TOOLTIPS": OFFENSE_TOOLTIPS,
        "DEFENSE_TOOLTIPS": DEFENSE_TOOLTIPS,
        "st_schemes": ST_SCHEMES,
        "st_scheme_keys": list(ST_SCHEMES.keys()),
    }
