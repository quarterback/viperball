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

from engine import ViperballEngine, load_team_from_json, get_available_teams, get_available_styles, OFFENSE_STYLES, DEFENSE_STYLES
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
    "rouge_hunt": "Punt early, pin deep, force mistakes. Score via Pindowns, Bells, Safeties. Defense-first offense.",
    "chain_gang": "Maximum laterals, maximum chaos. Every play is a 4-5 lateral chain. Showtime Viperball.",
    "triple_threat": "Single-wing misdirection. Power Flankers take direct snaps. No one knows who has the ball.",
    "balanced": "No strong tendency — mixes run, chain, and kick based on game state. Jack of all trades.",
}

DEFENSE_TOOLTIPS = {
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

    home_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    away_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    for p in plays:
        q = p["quarter"]
        if q not in home_q:
            continue
        if p["result"] == "touchdown" or p["result"] == "punt_return_td":
            if p["possession"] == "home":
                home_q[q] += 9
            else:
                away_q[q] += 9
        elif p["result"] == "successful_kick":
            pts = 5 if p["play_type"] == "drop_kick" else 3
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
    lines.append(f"| Kick % | {hs.get('kick_percentage',0)}% | {as_.get('kick_percentage',0)}% |")
    lines.append(f"| Total Yards | {hs['total_yards']} | {as_['total_yards']} |")
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

    st.markdown(f"### {winner} {fmt_vb_score(w_score)} - {loser} {fmt_vb_score(l_score)}")

    weather = result.get("weather", "clear")
    seed = result.get("seed", "N/A")
    st.caption(f"Weather: {weather.title()} | Seed: {seed}")

    home_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    away_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    for p in plays:
        q = p.get("quarter", 0)
        if q not in home_q:
            continue
        if p["result"] in ("touchdown", "punt_return_td"):
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
        {"Stat": "Yards/Play", home_name: str(hs['yards_per_play']), away_name: str(as_['yards_per_play'])},
        {"Stat": "Total Plays", home_name: str(hs['total_plays']), away_name: str(as_['total_plays'])},
        {"Stat": "Fumbles Lost", home_name: str(hs['fumbles_lost']), away_name: str(as_['fumbles_lost'])},
        {"Stat": "Penalties", home_name: f"{hs.get('penalties',0)} for {hs.get('penalty_yards',0)} yds", away_name: f"{as_.get('penalties',0)} for {as_.get('penalty_yards',0)} yds"},
    ]
    st.dataframe(pd.DataFrame(stat_rows), hide_index=True, use_container_width=True)

    drives = result.get("drive_summary", [])
    if drives:
        with st.expander("Drive Summary", expanded=False):
            drive_rows = []
            for i, d in enumerate(drives):
                team_label = home_name if d['team'] == 'home' else away_name
                drive_rows.append({
                    "#": i + 1,
                    "Team": team_label,
                    "Qtr": f"Q{d['quarter']}",
                    "Start": f"{d['start_yard_line']}yd",
                    "Plays": d['plays'],
                    "Yards": d['yards'],
                    "Result": drive_result_label(d['result']),
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
    }
