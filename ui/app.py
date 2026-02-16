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
from engine.season import load_teams_from_directory, create_season
from engine.dynasty import create_dynasty, Dynasty
from engine.viperball_metrics import calculate_viperball_metrics

st.set_page_config(
    page_title="Viperball Sandbox",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { max-width: 100%; }
    .block-container { padding-top: 1rem; }
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        border: 1px solid #d1d5db;
        padding: 12px;
        border-radius: 8px;
    }
    div[data-testid="stMetric"] label {
        color: #6b7280 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #111827 !important;
        font-weight: 700 !important;
        font-size: 1.6rem !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: #6b7280 !important;
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="stMetric"] {
            background-color: #1e1e2e;
            border: 1px solid #444;
        }
        div[data-testid="stMetric"] label {
            color: #a0aec0 !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #ffffff !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
            color: #a0aec0 !important;
        }
    }
    .score-big {
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        line-height: 1;
        margin: 0;
        color: #111827;
    }
    .team-name {
        font-size: 1.1rem;
        font-weight: 600;
        text-align: center;
        color: #4b5563;
        margin-bottom: 4px;
    }
    .drive-td { color: #22c55e; font-weight: 700; }
    .drive-kick { color: #3b82f6; font-weight: 700; }
    .drive-fumble { color: #ef4444; font-weight: 700; }
    .drive-downs { color: #f59e0b; font-weight: 700; }
    .drive-punt { color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

teams = get_available_teams()
styles = get_available_styles()
team_names = {t["key"]: t["name"] for t in teams}
style_keys = list(styles.keys())
defense_style_keys = list(DEFENSE_STYLES.keys())
defense_styles = DEFENSE_STYLES

OFFENSE_TOOLTIPS = {
    "power_option": "Heavy inside runs with option reads. Low kick attempts, high TD rate. Best against soft defenses.",
    "lateral_spread": "Spreads the field with lateral chains. High-variance, explosive plays. Risky but devastating when it works.",
    "territorial": "Prioritizes snap kicks and field goals. Plays for field position and pindowns. Patient, grinding style.",
    "option_spread": "Speed-based option reads mixed with lateral chains. Exploits tired defenses. High tempo.",
    "balanced": "No strong tendency — mixes run, chain, and kick based on game state. Jack of all trades.",
}

DEFENSE_TOOLTIPS = {
    "base_defense": "Solid fundamentals, no major weaknesses. Balanced approach to all play types.",
    "pressure_defense": "Aggressive blitzing and disruption. Forces fumbles but vulnerable to explosive lateral plays.",
    "contain_defense": "Gap discipline prevents big plays. Forces runs inside. Patient but can be methodically attacked.",
    "run_stop_defense": "Stacks the box to stuff the run. Elite vs ground game but weak against lateral chains and kicks.",
    "coverage_defense": "Anti-kick specialist. Prevents pindowns and covers punt returns. Slightly weaker vs dive plays.",
}


def load_team(key):
    return load_team_from_json(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams", f"{key}.json"))


def format_time(seconds):
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


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
                home_q[q] += 2
            else:
                away_q[q] += 2
        elif p["result"] == "fumble":
            if p["possession"] == "home":
                home_q[q] += 0.5
            else:
                away_q[q] += 0.5

    def _fq(v):
        return f"{v:g}" if v == int(v) else f"{v:.1f}"

    lines = []
    lines.append(f"# {home['team']} vs {away['team']}")
    lines.append(f"**Seed:** {result.get('seed', 'N/A')}")
    lines.append("")
    lines.append("## Score")
    lines.append(f"| Team | Q1 | Q2 | Q3 | Q4 | Final |")
    lines.append(f"|------|----|----|----|----|-------|")
    lines.append(f"| {home['team']} | {_fq(home_q[1])} | {_fq(home_q[2])} | {_fq(home_q[3])} | {_fq(home_q[4])} | **{_fq(home['score'])}** |")
    lines.append(f"| {away['team']} | {_fq(away_q[1])} | {_fq(away_q[2])} | {_fq(away_q[3])} | {_fq(away_q[4])} | **{_fq(away['score'])}** |")
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
    lines.append(f"| Strikes (0.5pts) | {h_fr} ({h_frp:g}pts) | {a_fr} ({a_frp:g}pts) |")
    lines.append(f"| Punts | {hs.get('punts',0)} | {as_.get('punts',0)} |")
    lines.append(f"| Kick % | {hs.get('kick_percentage',0)}% | {as_.get('kick_percentage',0)}% |")
    lines.append(f"| Total Yards | {hs['total_yards']} | {as_['total_yards']} |")
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
            i + 1, r.get("seed", ""), h["team"], a["team"], h["score"], a["score"],
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
        "fumble": "STRIKE (+0.5)",
        "turnover_on_downs": "DOWNS",
        "punt": "PUNT",
        "missed_kick": "MISSED KICK",
        "stall": "END OF QUARTER",
        "pindown": "PINDOWN",
        "punt_return_td": "PUNT RET TD",
        "chaos_recovery": "CHAOS REC",
        "safety": "SAFETY",
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
    }
    return colors.get(result, "#94a3b8")


page = st.sidebar.radio("Navigation", ["Game Simulator", "Season Simulator", "Dynasty Mode", "Debug Tools", "Play Inspector"], index=0)


if page == "Game Simulator":
    st.title("Viperball Game Simulator")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Home Team")
        home_key = st.selectbox("Select Home Team", [t["key"] for t in teams],
                                format_func=lambda x: team_names[x], key="home")
        home_style = st.selectbox("Home Offense Style", style_keys,
                                  format_func=lambda x: styles[x]["label"],
                                  index=style_keys.index(next((t["default_style"] for t in teams if t["key"] == home_key), "balanced")),
                                  key="home_style")
        st.caption(OFFENSE_TOOLTIPS.get(home_style, styles[home_style]["description"]))
        home_def_style = st.selectbox("Home Defense Style", defense_style_keys,
                                       format_func=lambda x: defense_styles[x]["label"],
                                       key="home_def_style")
        st.caption(DEFENSE_TOOLTIPS.get(home_def_style, defense_styles[home_def_style]["description"]))

    with col2:
        st.subheader("Away Team")
        away_key = st.selectbox("Select Away Team", [t["key"] for t in teams],
                                format_func=lambda x: team_names[x],
                                index=min(1, len(teams) - 1), key="away")
        away_style = st.selectbox("Away Offense Style", style_keys,
                                  format_func=lambda x: styles[x]["label"],
                                  index=style_keys.index(next((t["default_style"] for t in teams if t["key"] == away_key), "balanced")),
                                  key="away_style")
        st.caption(OFFENSE_TOOLTIPS.get(away_style, styles[away_style]["description"]))
        away_def_style = st.selectbox("Away Defense Style", defense_style_keys,
                                       format_func=lambda x: defense_styles[x]["label"],
                                       key="away_def_style")
        st.caption(DEFENSE_TOOLTIPS.get(away_def_style, defense_styles[away_def_style]["description"]))

    col_seed, col_btn = st.columns([1, 2])
    with col_seed:
        seed = st.number_input("Seed (0 = random)", min_value=0, max_value=999999, value=0, key="seed")
    with col_btn:
        st.write("")
        st.write("")
        run_game = st.button("Simulate Game", type="primary", use_container_width=True)

    if run_game:
        actual_seed = seed if seed > 0 else random.randint(1, 999999)
        home_team = load_team(home_key)
        away_team = load_team(away_key)

        style_overrides = {}
        style_overrides[home_team.name] = home_style
        style_overrides[away_team.name] = away_style
        style_overrides[f"{home_team.name}_defense"] = home_def_style
        style_overrides[f"{away_team.name}_defense"] = away_def_style

        engine = ViperballEngine(home_team, away_team, seed=actual_seed, style_overrides=style_overrides)

        with st.spinner("Simulating game..."):
            result = engine.simulate_game()

        st.session_state["last_result"] = result
        st.session_state["last_seed"] = actual_seed

    if "last_result" in st.session_state:
        result = st.session_state["last_result"]
        actual_seed = st.session_state["last_seed"]

        home_name = result["final_score"]["home"]["team"]
        away_name = result["final_score"]["away"]["team"]
        home_score = result["final_score"]["home"]["score"]
        away_score = result["final_score"]["away"]["score"]
        hs = result["stats"]["home"]
        as_ = result["stats"]["away"]

        st.divider()

        def fmt_score(s):
            return f"{s:g}" if s == int(s) else f"{s:.1f}"

        sc1, sc2, sc3 = st.columns([2, 1, 2])
        with sc1:
            st.markdown(f'<p class="team-name">{home_name}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="score-big">{fmt_score(home_score)}</p>', unsafe_allow_html=True)
        with sc2:
            st.markdown("<p style='text-align:center; padding-top:10px; font-size:1.2rem; opacity:0.5;'>vs</p>", unsafe_allow_html=True)
            st.caption(f"Seed: {actual_seed}")
        with sc3:
            st.markdown(f'<p class="team-name">{away_name}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="score-big">{fmt_score(away_score)}</p>', unsafe_allow_html=True)

        margin = abs(home_score - away_score)
        margin_str = fmt_score(margin)
        if home_score > away_score:
            st.success(f"{home_name} wins by {margin_str}")
        elif away_score > home_score:
            st.success(f"{away_name} wins by {margin_str}")
        else:
            st.info("Game ended in a tie")

        # ====== EXPORT SECTION ======
        st.subheader("Export Game Data")
        home_safe = safe_filename(home_name)
        away_safe = safe_filename(away_name)
        game_tag = f"{home_safe}_vs_{away_safe}_s{actual_seed}"

        ex1, ex2, ex3, ex4 = st.columns(4)
        with ex1:
            md_content = generate_box_score_markdown(result)
            st.download_button(
                "Box Score (.md)",
                data=md_content,
                file_name=f"{game_tag}_box_score.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with ex2:
            csv_plays = generate_play_log_csv(result)
            st.download_button(
                "Play Log (.csv)",
                data=csv_plays,
                file_name=f"{game_tag}_plays.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with ex3:
            csv_drives = generate_drives_csv(result)
            st.download_button(
                "Drives (.csv)",
                data=csv_drives,
                file_name=f"{game_tag}_drives.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with ex4:
            json_str = json.dumps(result, indent=2, default=str)
            st.download_button(
                "Full JSON",
                data=json_str,
                file_name=f"{game_tag}_full.json",
                mime="application/json",
                use_container_width=True,
            )

        # ====== 1. REAL BOX SCORE ======
        st.subheader("Box Score")

        plays = result["play_by_play"]
        home_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        away_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        for p in plays:
            q = p["quarter"]
            if q not in home_q:
                continue
            if p["result"] in ("touchdown", "punt_return_td"):
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
                    home_q[q] += 2
                else:
                    away_q[q] += 2
            elif p["result"] == "fumble":
                if p["possession"] == "home":
                    home_q[q] += 0.5
                else:
                    away_q[q] += 0.5

        qtr_data = {
            "": [home_name, away_name],
            "Q1": [home_q[1], away_q[1]],
            "Q2": [home_q[2], away_q[2]],
            "Q3": [home_q[3], away_q[3]],
            "Q4": [home_q[4], away_q[4]],
            "Final": [home_score, away_score],
        }
        st.dataframe(pd.DataFrame(qtr_data), hide_index=True, use_container_width=True)

        st.markdown("**Scoring Breakdown**")
        h_frp = hs.get('fumble_recovery_points', 0)
        a_frp = as_.get('fumble_recovery_points', 0)
        h_fr = hs.get('fumble_recoveries', 0)
        a_fr = as_.get('fumble_recoveries', 0)
        h_saf = hs.get('safeties_conceded', 0)
        a_saf = as_.get('safeties_conceded', 0)
        scoring_data = {
            "": ["Touchdowns (9pts)", "Snap Kicks (5pts)", "Field Goals (3pts)",
                 "Safeties (2pts)", "Pindowns (1pt)", "Strikes (0.5pts)",
                 "Punts", "Kick %",
                 "Total Yards", "Yards/Play", "Total Plays",
                 "Lateral Chains", "Lateral Efficiency",
                 "Fumbles Lost", "Turnovers on Downs",
                 "Penalties", "Penalty Yards",
                 "Longest Play", "Avg Fatigue"],
            home_name: [
                f"{hs['touchdowns']} ({hs['touchdowns'] * 9}pts)",
                f"{hs['drop_kicks_made']}/{hs.get('drop_kicks_attempted',0)} ({hs['drop_kicks_made'] * 5}pts)",
                f"{hs['place_kicks_made']}/{hs.get('place_kicks_attempted',0)} ({hs['place_kicks_made'] * 3}pts)",
                f"{a_saf} ({a_saf * 2}pts)",
                f"{hs.get('pindowns',0)} ({hs.get('pindowns',0)}pts)",
                f"{h_fr} ({h_frp:g}pts)",
                str(hs.get("punts", 0)),
                f"{hs.get('kick_percentage', 0)}%",
                str(hs["total_yards"]), str(hs["yards_per_play"]), str(hs["total_plays"]),
                str(hs["lateral_chains"]), f'{hs["lateral_efficiency"]}%',
                str(hs["fumbles_lost"]), str(hs["turnovers_on_downs"]),
                str(hs.get("penalties", 0)),
                str(hs.get("penalty_yards", 0)),
                str(max((p["yards"] for p in plays if p["possession"] == "home"), default=0)),
                f'{hs["avg_fatigue"]}%',
            ],
            away_name: [
                f"{as_['touchdowns']} ({as_['touchdowns'] * 9}pts)",
                f"{as_['drop_kicks_made']}/{as_.get('drop_kicks_attempted',0)} ({as_['drop_kicks_made'] * 5}pts)",
                f"{as_['place_kicks_made']}/{as_.get('place_kicks_attempted',0)} ({as_['place_kicks_made'] * 3}pts)",
                f"{h_saf} ({h_saf * 2}pts)",
                f"{as_.get('pindowns',0)} ({as_.get('pindowns',0)}pts)",
                f"{a_fr} ({a_frp:g}pts)",
                str(as_.get("punts", 0)),
                f"{as_.get('kick_percentage', 0)}%",
                str(as_["total_yards"]), str(as_["yards_per_play"]), str(as_["total_plays"]),
                str(as_["lateral_chains"]), f'{as_["lateral_efficiency"]}%',
                str(as_["fumbles_lost"]), str(as_["turnovers_on_downs"]),
                str(as_.get("penalties", 0)),
                str(as_.get("penalty_yards", 0)),
                str(max((p["yards"] for p in plays if p["possession"] == "away"), default=0)),
                f'{as_["avg_fatigue"]}%',
            ],
        }
        st.dataframe(pd.DataFrame(scoring_data), hide_index=True, use_container_width=True)

        st.markdown("**Down Conversions**")
        h_dc = hs.get("down_conversions", {})
        a_dc = as_.get("down_conversions", {})
        for d in [4, 5, 6]:
            hd = h_dc.get(d, h_dc.get(str(d), {"attempts": 0, "converted": 0, "rate": 0}))
            ad = a_dc.get(d, a_dc.get(str(d), {"attempts": 0, "converted": 0, "rate": 0}))
            label = f"{'4th' if d == 4 else '5th' if d == 5 else '6th'} Down"
            dc1, dc2 = st.columns(2)
            dc1.metric(f"{home_name} {label}", f"{hd['converted']}/{hd['attempts']} ({hd['rate']}%)")
            dc2.metric(f"{away_name} {label}", f"{ad['converted']}/{ad['attempts']} ({ad['rate']}%)")

        # ====== VPA (Viperball Points Added) ======
        st.subheader("VPA — Viperball Points Added")
        st.caption("Measures play efficiency vs league-average expectation from same field position & down. Positive = above average.")
        h_vpa = hs.get("epa", {})
        a_vpa = as_.get("epa", {})

        v1, v2 = st.columns(2)
        v1.metric(f"{home_name} Total VPA", h_vpa.get("total_vpa", h_vpa.get("total_epa", 0)))
        v2.metric(f"{away_name} Total VPA", a_vpa.get("total_vpa", a_vpa.get("total_epa", 0)))

        v3, v4, v5, v6 = st.columns(4)
        v3.metric(f"{home_name} VPA/Play", h_vpa.get("vpa_per_play", h_vpa.get("epa_per_play", 0)))
        v4.metric(f"{away_name} VPA/Play", a_vpa.get("vpa_per_play", a_vpa.get("epa_per_play", 0)))
        v5.metric(f"{home_name} Success Rate", f"{h_vpa.get('success_rate', 0)}%")
        v6.metric(f"{away_name} Success Rate", f"{a_vpa.get('success_rate', 0)}%")

        v7, v8, v9, v10 = st.columns(4)
        v7.metric(f"{home_name} Explosiveness", h_vpa.get("explosiveness", 0))
        v8.metric(f"{away_name} Explosiveness", a_vpa.get("explosiveness", 0))
        v9.metric(f"{home_name} Off VPA", h_vpa.get("offense_vpa", h_vpa.get("offense_epa", 0)))
        v10.metric(f"{away_name} Off VPA", a_vpa.get("offense_vpa", a_vpa.get("offense_epa", 0)))

        vpa_plays = [p for p in plays if "epa" in p]
        if vpa_plays:
            home_vpa_plays = [p for p in vpa_plays if p["possession"] == "home"]
            away_vpa_plays = [p for p in vpa_plays if p["possession"] == "away"]

            fig_vpa = go.Figure()
            if home_vpa_plays:
                home_cum = []
                running = 0
                for p in home_vpa_plays:
                    running += p["epa"]
                    home_cum.append(round(running, 2))
                fig_vpa.add_trace(go.Scatter(
                    y=home_cum, mode="lines", name=home_name,
                    line=dict(color="#3b82f6", width=2)
                ))
            if away_vpa_plays:
                away_cum = []
                running = 0
                for p in away_vpa_plays:
                    running += p["epa"]
                    away_cum.append(round(running, 2))
                fig_vpa.add_trace(go.Scatter(
                    y=away_cum, mode="lines", name=away_name,
                    line=dict(color="#ef4444", width=2)
                ))
            fig_vpa.update_layout(
                title="Cumulative VPA Over Game",
                xaxis_title="Play #", yaxis_title="Cumulative VPA",
                height=350, template="plotly_white"
            )
            st.plotly_chart(fig_vpa, use_container_width=True)

        # ====== 2. PLAY FAMILY DISTRIBUTION ======
        st.subheader("Play Family Distribution")
        home_fam = hs.get("play_family_breakdown", {})
        away_fam = as_.get("play_family_breakdown", {})

        all_families = sorted(set(list(home_fam.keys()) + list(away_fam.keys())))
        home_total = sum(home_fam.values()) or 1
        away_total = sum(away_fam.values()) or 1

        fam_chart_data = []
        for f in all_families:
            fam_chart_data.append({"Family": f.replace("_", " ").title(), "Team": home_name,
                                   "Pct": round(home_fam.get(f, 0) / home_total * 100, 1)})
            fam_chart_data.append({"Family": f.replace("_", " ").title(), "Team": away_name,
                                   "Pct": round(away_fam.get(f, 0) / away_total * 100, 1)})

        fig = px.bar(pd.DataFrame(fam_chart_data), x="Family", y="Pct", color="Team",
                     barmode="group", title="Play Call Distribution (%)",
                     labels={"Pct": "Percentage", "Family": "Play Family"})
        fig.update_layout(yaxis_ticksuffix="%", height=350)
        st.plotly_chart(fig, use_container_width=True)

        # ====== 3. DRIVE OUTCOME PANEL ======
        st.subheader("Drive Summary")
        drives = result.get("drive_summary", [])
        if drives:
            drive_rows = []
            for i, d in enumerate(drives):
                team_label = home_name if d["team"] == "home" else away_name
                drive_rows.append({
                    "#": i + 1,
                    "Team": team_label,
                    "Qtr": f"Q{d['quarter']}",
                    "Start": f"{d['start_yard_line']}yd",
                    "Plays": d["plays"],
                    "Yards": d["yards"],
                    "Result": drive_result_label(d["result"]),
                })
            st.dataframe(pd.DataFrame(drive_rows), hide_index=True, use_container_width=True, height=350)

            drive_outcomes = {}
            for d in drives:
                r = drive_result_label(d["result"])
                drive_outcomes[r] = drive_outcomes.get(r, 0) + 1

            fig = px.bar(x=list(drive_outcomes.keys()), y=list(drive_outcomes.values()),
                         title="Drive Outcomes",
                         color=list(drive_outcomes.keys()),
                         color_discrete_map={
                             "TD": "#22c55e", "FG": "#3b82f6", "FUMBLE": "#ef4444",
                             "DOWNS": "#f59e0b", "PUNT": "#94a3b8", "MISSED FG": "#f59e0b",
                             "END OF QUARTER": "#64748b", "PINDOWN": "#a855f7",
                             "PUNT RET TD": "#22c55e", "CHAOS REC": "#f97316",
                         })
            fig.update_layout(showlegend=False, height=300, xaxis_title="Outcome", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

        # ====== 4. PLAY LOG WITH ROLE TAGS ======
        st.subheader("Play-by-Play")
        play_df = pd.DataFrame(plays)

        quarter_filter = st.selectbox("Filter by Quarter", ["All", "Q1", "Q2", "Q3", "Q4"])
        if quarter_filter != "All":
            q = int(quarter_filter[1])
            play_df = play_df[play_df["quarter"] == q]

        if not play_df.empty:
            display_df = play_df.copy()
            if "time_remaining" in display_df.columns:
                display_df["time"] = display_df["time_remaining"].apply(format_time)
            if "possession" in display_df.columns:
                display_df["team"] = display_df["possession"].apply(
                    lambda x: home_name if x == "home" else away_name)

            show_cols = ["play_number", "team", "time", "down", "field_position",
                         "play_family", "description", "yards", "result", "fatigue"]
            available = [c for c in show_cols if c in display_df.columns]
            st.dataframe(display_df[available], hide_index=True, use_container_width=True, height=400)

        # ====== 5. DEBUG PANEL ======
        with st.expander("Debug Panel"):
            st.markdown("**Fatigue Over Time**")
            home_fat = []
            away_fat = []
            for p in plays:
                if p.get("fatigue") is not None:
                    entry = {"play": p["play_number"], "fatigue": p["fatigue"]}
                    if p["possession"] == "home":
                        home_fat.append({**entry, "team": home_name})
                    else:
                        away_fat.append({**entry, "team": away_name})

            if home_fat or away_fat:
                fat_df = pd.DataFrame(home_fat + away_fat)
                fig = px.line(fat_df, x="play", y="fatigue", color="team",
                              title="Fatigue Curve")
                fig.update_yaxes(range=[30, 105])
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("**Turnover Triggers**")
            fumble_plays = [p for p in plays if p.get("fumble")]
            tod_plays = [p for p in plays if p["result"] == "turnover_on_downs"]
            tc1, tc2 = st.columns(2)
            tc1.metric("Fumbles", len(fumble_plays))
            tc2.metric("Turnovers on Downs", len(tod_plays))

            if fumble_plays:
                st.markdown("*Fumble locations:*")
                for fp in fumble_plays:
                    team_label = home_name if fp["possession"] == "home" else away_name
                    st.text(f"  Q{fp['quarter']} {format_time(fp['time_remaining'])} | {team_label} at {fp['field_position']}yd | {fp['description']}")

            st.markdown("**Explosive Plays (15+ yards)**")
            big_plays = [p for p in plays if p["yards"] >= 15 and p["play_type"] not in ["punt"]]
            if big_plays:
                for bp in big_plays:
                    team_label = home_name if bp["possession"] == "home" else away_name
                    st.text(f"  Q{bp['quarter']} | {team_label} | {bp['yards']}yds | {bp['description']}")
            else:
                st.text("  No explosive plays")

            st.markdown("**Kick Decision Summary**")
            kick_plays = [p for p in plays if p["play_type"] in ["drop_kick", "place_kick", "punt"]]
            kc1, kc2, kc3 = st.columns(3)
            punts = [p for p in kick_plays if p["play_type"] == "punt"]
            drops = [p for p in kick_plays if p["play_type"] == "drop_kick"]
            places = [p for p in kick_plays if p["play_type"] == "place_kick"]
            kc1.metric("Punts", len(punts))
            kc2.metric("Snap Kick Attempts", len(drops))
            kc3.metric("Field Goal Attempts", len(places))

            st.markdown("**Style Parameters**")
            sc1, sc2 = st.columns(2)
            h_style_key = result.get("home_style", "balanced")
            a_style_key = result.get("away_style", "balanced")
            h_style = OFFENSE_STYLES.get(h_style_key, OFFENSE_STYLES["balanced"])
            a_style = OFFENSE_STYLES.get(a_style_key, OFFENSE_STYLES["balanced"])
            with sc1:
                st.markdown(f"**{home_name}** ({h_style['label']})")
                st.text(f"  Tempo: {h_style['tempo']}")
                st.text(f"  Lateral Risk: {h_style['lateral_risk']}")
                st.text(f"  Kick Rate: {h_style['kick_rate']}")
                st.text(f"  Option Rate: {h_style['option_rate']}")
            with sc2:
                st.markdown(f"**{away_name}** ({a_style['label']})")
                st.text(f"  Tempo: {a_style['tempo']}")
                st.text(f"  Lateral Risk: {a_style['lateral_risk']}")
                st.text(f"  Kick Rate: {a_style['kick_rate']}")
                st.text(f"  Option Rate: {a_style['option_rate']}")

            st.markdown("**Viperball Metrics (0-100)**")
            try:
                home_metrics = calculate_viperball_metrics(result, "home")
                away_metrics = calculate_viperball_metrics(result, "away")
                mc1, mc2 = st.columns(2)
                metric_labels = {
                    "opi": "OPI (Overall)",
                    "territory_rating": "Territory Rating",
                    "pressure_index": "Pressure Index",
                    "chaos_factor": "Chaos Factor",
                    "kicking_efficiency": "Kicking Efficiency",
                    "drive_quality": "Drive Quality",
                    "turnover_impact": "Turnover Impact",
                }
                with mc1:
                    st.markdown(f"*{home_name}*")
                    for k, label in metric_labels.items():
                        v = home_metrics.get(k, 0)
                        display = f"{v:.1f}" if k != "drive_quality" else f"{v:.2f}/10"
                        st.text(f"  {label}: {display}")
                with mc2:
                    st.markdown(f"*{away_name}*")
                    for k, label in metric_labels.items():
                        v = away_metrics.get(k, 0)
                        display = f"{v:.1f}" if k != "drive_quality" else f"{v:.2f}/10"
                        st.text(f"  {label}: {display}")
            except Exception:
                st.caption("Metrics unavailable for this game result")

        with st.expander("Raw JSON"):
            st.json(result)


elif page == "Debug Tools":
    st.title("Debug Tools - Batch Simulation")

    col1, col2 = st.columns(2)
    with col1:
        home_key = st.selectbox("Home Team", [t["key"] for t in teams],
                                format_func=lambda x: team_names[x], key="dbg_home")
        home_style = st.selectbox("Home Style", style_keys,
                                  format_func=lambda x: styles[x]["label"], key="dbg_home_style")
    with col2:
        away_key = st.selectbox("Away Team", [t["key"] for t in teams],
                                format_func=lambda x: team_names[x],
                                index=min(1, len(teams) - 1), key="dbg_away")
        away_style = st.selectbox("Away Style", style_keys,
                                  format_func=lambda x: styles[x]["label"], key="dbg_away_style")

    col_n, col_seed = st.columns(2)
    with col_n:
        num_sims = st.slider("Number of Simulations", 5, 200, 50)
    with col_seed:
        base_seed = st.number_input("Base Seed (0 = random)", min_value=0, max_value=999999, value=42, key="dbg_seed")

    run_batch = st.button("Run Batch Simulation", type="primary", use_container_width=True)

    if run_batch:
        home_team_data = load_team(home_key)
        away_team_data = load_team(away_key)
        style_overrides = {home_team_data.name: home_style, away_team_data.name: away_style}

        results = []
        progress = st.progress(0)
        for i in range(num_sims):
            s = (base_seed + i) if base_seed > 0 else None
            home_t = load_team(home_key)
            away_t = load_team(away_key)
            engine = ViperballEngine(home_t, away_t, seed=s, style_overrides=style_overrides)
            r = engine.simulate_game()
            results.append(r)
            progress.progress((i + 1) / num_sims)
        progress.empty()

        st.session_state["batch_results"] = results

    if "batch_results" in st.session_state:
        results = st.session_state["batch_results"]
        n = len(results)

        home_name = results[0]["final_score"]["home"]["team"]
        away_name = results[0]["final_score"]["away"]["team"]

        home_scores = [r["final_score"]["home"]["score"] for r in results]
        away_scores = [r["final_score"]["away"]["score"] for r in results]
        home_wins = sum(1 for h, a in zip(home_scores, away_scores) if h > a)
        away_wins = sum(1 for h, a in zip(home_scores, away_scores) if a > h)
        ties = n - home_wins - away_wins

        st.divider()
        st.subheader(f"Results: {n} Simulations")

        home_safe = safe_filename(home_name)
        away_safe = safe_filename(away_name)
        batch_tag = f"batch_{home_safe}_vs_{away_safe}_{n}sims"

        bex1, bex2, bex3 = st.columns(3)
        with bex1:
            batch_csv = generate_batch_summary_csv(results)
            st.download_button(
                "Batch Summary (.csv)",
                data=batch_csv,
                file_name=f"{batch_tag}_summary.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with bex2:
            all_batch_json = json.dumps([{
                "game": i + 1,
                "final_score": r["final_score"],
                "stats": r["stats"],
                "drive_summary": r.get("drive_summary", []),
            } for i, r in enumerate(results)], indent=2, default=str)
            st.download_button(
                "All Games (.json)",
                data=all_batch_json,
                file_name=f"{batch_tag}_all.json",
                mime="application/json",
                use_container_width=True,
            )
        with bex3:
            full_batch_json = json.dumps(results, indent=2, default=str)
            st.download_button(
                "Full Data + Plays (.json)",
                data=full_batch_json,
                file_name=f"{batch_tag}_full.json",
                mime="application/json",
                use_container_width=True,
            )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"{home_name} Wins", home_wins)
        m2.metric(f"{away_name} Wins", away_wins)
        m3.metric("Ties", ties)
        m4.metric("Tie %", f"{round(ties / n * 100, 1)}%")

        st.subheader("Score Averages")
        avg1, avg2, avg3, avg4 = st.columns(4)
        avg1.metric(f"Avg {home_name}", round(sum(home_scores) / n, 1))
        avg2.metric(f"Avg {away_name}", round(sum(away_scores) / n, 1))

        home_yards = [r["stats"]["home"]["total_yards"] for r in results]
        away_yards = [r["stats"]["away"]["total_yards"] for r in results]
        avg3.metric(f"Avg {home_name} Yards", round(sum(home_yards) / n, 1))
        avg4.metric(f"Avg {away_name} Yards", round(sum(away_yards) / n, 1))

        st.subheader("Scoring Breakdown")
        avg5, avg6, avg7, avg8 = st.columns(4)
        home_tds = [r["stats"]["home"]["touchdowns"] for r in results]
        away_tds = [r["stats"]["away"]["touchdowns"] for r in results]
        avg5.metric("Avg TDs/game", round((sum(home_tds) + sum(away_tds)) / n, 2))
        home_fumbles = [r["stats"]["home"]["fumbles_lost"] for r in results]
        away_fumbles = [r["stats"]["away"]["fumbles_lost"] for r in results]
        avg6.metric("Avg Fumbles/game", round((sum(home_fumbles) + sum(away_fumbles)) / n, 2))

        longest_plays = []
        for r in results:
            max_play = max((p["yards"] for p in r["play_by_play"] if p["play_type"] not in ["punt"]), default=0)
            longest_plays.append(max_play)
        avg7.metric("Avg Longest Play", round(sum(longest_plays) / n, 1))
        avg8.metric("Max Longest Play", max(longest_plays))

        k1, k2, k3, k4 = st.columns(4)
        home_kick_pct = [r["stats"]["home"].get("kick_percentage", 0) for r in results]
        away_kick_pct = [r["stats"]["away"].get("kick_percentage", 0) for r in results]
        avg_kick_pct = round((sum(home_kick_pct) + sum(away_kick_pct)) / (2 * n), 1)
        k1.metric("Avg Kick %", f"{avg_kick_pct}%")

        home_pindowns = [r["stats"]["home"].get("pindowns", 0) for r in results]
        away_pindowns = [r["stats"]["away"].get("pindowns", 0) for r in results]
        k2.metric("Avg Pindowns/game", round((sum(home_pindowns) + sum(away_pindowns)) / n, 2))

        home_lat_eff = [r["stats"]["home"].get("lateral_efficiency", 0) for r in results]
        away_lat_eff = [r["stats"]["away"].get("lateral_efficiency", 0) for r in results]
        avg_lat_eff = round((sum(home_lat_eff) + sum(away_lat_eff)) / (2 * n), 1)
        k3.metric("Avg Lateral Eff", f"{avg_lat_eff}%")

        home_dk = [r["stats"]["home"].get("drop_kicks_made", 0) for r in results]
        away_dk = [r["stats"]["away"].get("drop_kicks_made", 0) for r in results]
        k4.metric("Avg Snap Kicks/game", round((sum(home_dk) + sum(away_dk)) / n, 2))

        st.markdown("**Avg Down Conversions**")
        dc_cols = st.columns(3)
        for idx, d in enumerate([3, 4, 5]):
            rates = []
            for r in results:
                for side in ["home", "away"]:
                    dc = r["stats"][side].get("down_conversions", {})
                    dd = dc.get(d, dc.get(str(d), {"rate": 0}))
                    rates.append(dd["rate"])
            avg_rate = round(sum(rates) / max(1, len(rates)), 1)
            label = f"{'4th' if d == 4 else '5th' if d == 5 else '6th'} Down Conv %"
            dc_cols[idx].metric(label, f"{avg_rate}%")

        st.markdown("**Avg VPA (Viperball Points Added)**")
        vpa_cols = st.columns(4)
        home_total_vpa = [r["stats"]["home"].get("epa", {}).get("total_vpa", r["stats"]["home"].get("epa", {}).get("total_epa", 0)) for r in results]
        away_total_vpa = [r["stats"]["away"].get("epa", {}).get("total_vpa", r["stats"]["away"].get("epa", {}).get("total_epa", 0)) for r in results]
        home_vpa_pp = [r["stats"]["home"].get("epa", {}).get("vpa_per_play", r["stats"]["home"].get("epa", {}).get("epa_per_play", 0)) for r in results]
        away_vpa_pp = [r["stats"]["away"].get("epa", {}).get("vpa_per_play", r["stats"]["away"].get("epa", {}).get("epa_per_play", 0)) for r in results]
        vpa_cols[0].metric(f"Avg {home_name} VPA", round(sum(home_total_vpa) / n, 2))
        vpa_cols[1].metric(f"Avg {away_name} VPA", round(sum(away_total_vpa) / n, 2))
        vpa_cols[2].metric(f"Avg {home_name} VPA/Play", round(sum(home_vpa_pp) / n, 3))
        vpa_cols[3].metric(f"Avg {away_name} VPA/Play", round(sum(away_vpa_pp) / n, 3))

        home_sr = [r["stats"]["home"].get("epa", {}).get("success_rate", 0) for r in results]
        away_sr = [r["stats"]["away"].get("epa", {}).get("success_rate", 0) for r in results]
        home_exp = [r["stats"]["home"].get("epa", {}).get("explosiveness", 0) for r in results]
        away_exp = [r["stats"]["away"].get("epa", {}).get("explosiveness", 0) for r in results]
        sr_cols = st.columns(4)
        sr_cols[0].metric(f"Avg {home_name} Success Rate", f"{round(sum(home_sr) / n, 1)}%")
        sr_cols[1].metric(f"Avg {away_name} Success Rate", f"{round(sum(away_sr) / n, 1)}%")
        sr_cols[2].metric(f"Avg {home_name} Explosiveness", round(sum(home_exp) / n, 3))
        sr_cols[3].metric(f"Avg {away_name} Explosiveness", round(sum(away_exp) / n, 3))

        st.subheader("Score Distribution")
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=home_scores, name=home_name, opacity=0.7))
        fig.add_trace(go.Histogram(x=away_scores, name=away_name, opacity=0.7))
        fig.update_layout(barmode="overlay", xaxis_title="Score", yaxis_title="Frequency", height=350)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Drive Outcomes (aggregate)")
        all_drives = []
        for r in results:
            for d in r.get("drive_summary", []):
                all_drives.append(d)
        if all_drives:
            outcome_counts = {}
            for d in all_drives:
                r_label = drive_result_label(d["result"])
                outcome_counts[r_label] = outcome_counts.get(r_label, 0) + 1
            total_drives = len(all_drives)
            fig = px.bar(
                x=list(outcome_counts.keys()),
                y=[round(v / total_drives * 100, 1) for v in outcome_counts.values()],
                title=f"Drive Outcome Distribution ({total_drives} drives across {n} games)",
                labels={"x": "Outcome", "y": "Percentage"},
                color=list(outcome_counts.keys()),
                color_discrete_map={
                    "TD": "#22c55e", "FG": "#3b82f6", "FUMBLE": "#ef4444",
                    "DOWNS": "#f59e0b", "PUNT": "#94a3b8", "MISSED FG": "#f59e0b",
                    "END OF QUARTER": "#64748b", "PINDOWN": "#a855f7",
                    "PUNT RET TD": "#22c55e", "CHAOS REC": "#f97316",
                })
            fig.update_layout(showlegend=False, height=350, yaxis_ticksuffix="%")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Fatigue Curves")
        home_fatigue = []
        away_fatigue = []
        for r in results:
            plays = r["play_by_play"]
            for p in plays:
                if p["possession"] == "home" and p.get("fatigue") is not None:
                    home_fatigue.append({"play": p["play_number"], "fatigue": p["fatigue"], "team": home_name})
                elif p["possession"] == "away" and p.get("fatigue") is not None:
                    away_fatigue.append({"play": p["play_number"], "fatigue": p["fatigue"], "team": away_name})

        if home_fatigue or away_fatigue:
            fat_df = pd.DataFrame(home_fatigue + away_fatigue)
            avg_fat = fat_df.groupby(["play", "team"])["fatigue"].mean().reset_index()
            fig = px.line(avg_fat, x="play", y="fatigue", color="team",
                          title="Average Fatigue Over Play Number")
            fig.update_yaxes(range=[30, 105])
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Turnover Rates")
        home_tod = [r["stats"]["home"]["turnovers_on_downs"] for r in results]
        away_tod = [r["stats"]["away"]["turnovers_on_downs"] for r in results]

        to_data = {
            "Metric": ["Avg Fumbles", "Avg Turnovers on Downs", "Total Turnovers/Game"],
            home_name: [
                round(sum(home_fumbles) / n, 2),
                round(sum(home_tod) / n, 2),
                round((sum(home_fumbles) + sum(home_tod)) / n, 2),
            ],
            away_name: [
                round(sum(away_fumbles) / n, 2),
                round(sum(away_tod) / n, 2),
                round((sum(away_fumbles) + sum(away_tod)) / n, 2),
            ],
        }
        st.dataframe(pd.DataFrame(to_data), hide_index=True, use_container_width=True)


elif page == "Play Inspector":
    st.title("Play Inspector - Single Play Runner")

    col1, col2 = st.columns(2)
    with col1:
        play_style = st.selectbox("Offense Style", style_keys,
                                  format_func=lambda x: styles[x]["label"], key="pi_style")
        st.caption(styles[play_style]["description"])

        style_info = OFFENSE_STYLES[play_style]
        st.write("**Style Parameters:**")
        st.write(f"- Tempo: {style_info['tempo']}")
        st.write(f"- Lateral Risk: {style_info['lateral_risk']}")
        st.write(f"- Kick Rate: {style_info['kick_rate']}")
        st.write(f"- Option Rate: {style_info['option_rate']}")

    with col2:
        field_pos = st.slider("Field Position (yards from own goal)", 1, 99, 40, key="pi_fp")
        down = st.selectbox("Down", [1, 2, 3, 4, 5, 6], key="pi_down")
        ytg = st.number_input("Yards to Go", min_value=1, max_value=99, value=20, key="pi_ytg")

    col_n, col_seed = st.columns(2)
    with col_n:
        num_plays = st.slider("Number of Plays to Run", 1, 500, 50, key="pi_num")
    with col_seed:
        pi_seed = st.number_input("Base Seed (0 = random)", min_value=0, max_value=999999, value=0, key="pi_seed")

    run_plays = st.button("Run Plays", type="primary", use_container_width=True)

    if run_plays:
        home_team = load_team(teams[0]["key"])
        away_team = load_team(teams[1]["key"] if len(teams) > 1 else teams[0]["key"])

        play_results = []
        for i in range(num_plays):
            s = (pi_seed + i) if pi_seed > 0 else None
            engine = ViperballEngine(home_team, away_team, seed=s)
            result = engine.simulate_single_play(
                style=play_style,
                field_position=field_pos,
                down=down,
                yards_to_go=ytg,
            )
            result["run_number"] = i + 1
            play_results.append(result)

        st.session_state["play_results"] = play_results

    if "play_results" in st.session_state:
        play_results = st.session_state["play_results"]
        n = len(play_results)

        st.divider()
        st.subheader(f"Results: {n} Plays")

        pi_output = io.StringIO()
        pi_writer = csv.writer(pi_output)
        pi_writer.writerow(["run", "play_family", "play_type", "yards", "result",
                            "description", "fatigue", "field_position"])
        for pr in play_results:
            pi_writer.writerow([
                pr.get("run_number", ""), pr.get("play_family", ""), pr.get("play_type", ""),
                pr["yards"], pr["result"], pr.get("description", ""),
                pr.get("fatigue", ""), pr.get("field_position", "")
            ])
        st.download_button(
            "Export Plays (.csv)",
            data=pi_output.getvalue(),
            file_name=f"play_inspector_{n}plays.csv",
            mime="text/csv",
        )

        yards_list = [p["yards"] for p in play_results]
        results_list = [p["result"] for p in play_results]
        families = [p.get("play_family", "unknown") for p in play_results]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Avg Yards", round(sum(yards_list) / n, 2))
        m2.metric("Max Yards", max(yards_list))
        m3.metric("Min Yards", min(yards_list))
        td_count = sum(1 for r in results_list if r == "touchdown")
        m4.metric("TD Rate", f"{round(td_count / n * 100, 1)}%")

        m5, m6, m7, m8 = st.columns(4)
        fd_count = sum(1 for r in results_list if r == "first_down")
        fumble_count = sum(1 for r in results_list if r == "fumble")
        m5.metric("First Down Rate", f"{round(fd_count / n * 100, 1)}%")
        m6.metric("Fumble Rate", f"{round(fumble_count / n * 100, 1)}%")
        gain_count = sum(1 for r in results_list if r == "gain")
        m7.metric("Gain (no FD)", f"{round(gain_count / n * 100, 1)}%")
        negative = sum(1 for y in yards_list if y < 0)
        m8.metric("Negative Plays", f"{round(negative / n * 100, 1)}%")

        st.subheader("Yards Distribution")
        fig = px.histogram(x=yards_list, nbins=30, title="Yards Gained Distribution")
        fig.update_xaxes(title="Yards")
        fig.update_yaxes(title="Frequency")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Result Breakdown")
        result_counts = {}
        for r in results_list:
            result_counts[r] = result_counts.get(r, 0) + 1
        fig = px.bar(x=list(result_counts.keys()), y=list(result_counts.values()),
                     title="Play Results")
        fig.update_xaxes(title="Result")
        fig.update_yaxes(title="Count")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Play Family Distribution")
        fam_counts = {}
        for f in families:
            fam_counts[f] = fam_counts.get(f, 0) + 1
        fig = px.pie(values=list(fam_counts.values()), names=list(fam_counts.keys()),
                     title="Play Families Selected")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Play-by-Play Detail")
        df = pd.DataFrame(play_results)
        display_cols = ["run_number", "play_family", "play_type", "yards", "result",
                        "description", "fatigue", "field_position"]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available], hide_index=True, use_container_width=True, height=400)


elif page == "Season Simulator":
    st.title("Season Simulator")
    st.caption("Simulate a full round-robin season with standings, metrics, and playoffs")

    teams_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")
    all_teams = load_teams_from_directory(teams_dir)
    all_team_names = sorted(all_teams.keys())

    st.subheader("Season Setup")
    season_name = st.text_input("Season Name", value="2026 CVL Season", key="season_name")

    selected_teams = st.multiselect("Select Teams", all_team_names, default=all_team_names, key="season_teams")

    if len(selected_teams) < 2:
        st.warning("Select at least 2 teams to run a season.")
    else:
        human_teams = st.multiselect(
            "Human-Controlled Teams (configure manually)", 
            selected_teams,
            default=[],
            max_selections=4,
            key="season_human_teams",
            help="Select teams you want to configure manually. All others get AI-assigned schemes."
        )
        
        ai_seed_col, reroll_col = st.columns([3, 1])
        with ai_seed_col:
            ai_seed = st.number_input("AI Coaching Seed (0 = random)", min_value=0, max_value=999999, value=0, key="season_ai_seed")
        with reroll_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Re-roll AI", key="reroll_ai_season"):
                st.session_state["season_ai_seed"] = random.randint(1, 999999)
                st.rerun()
        
        actual_seed = ai_seed if ai_seed > 0 else hash(season_name) % 999999
        
        from engine.ai_coach import auto_assign_all_teams, get_scheme_label, load_team_identity
        teams_dir_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")
        team_identities = load_team_identity(teams_dir_path)
        
        style_configs = {}
        
        if human_teams:
            st.subheader("Your Team Configuration")
            h_cols_per_row = min(len(human_teams), 3)
            h_chunks = [human_teams[i:i + h_cols_per_row] for i in range(0, len(human_teams), h_cols_per_row)]
            for chunk in h_chunks:
                cols = st.columns(len(chunk))
                for col, tname in zip(cols, chunk):
                    with col:
                        identity = team_identities.get(tname, {})
                        mascot = identity.get("mascot", "")
                        conf = identity.get("conference", "")
                        colors = identity.get("colors", [])
                        color_str = " / ".join(colors[:2]) if colors else ""
                        
                        st.markdown(f"**{tname}**")
                        if mascot or conf:
                            st.caption(f"{mascot} | {conf}" + (f" | {color_str}" if color_str else ""))
                        
                        off_style = st.selectbox("Offense", style_keys,
                                                  format_func=lambda x: styles[x]["label"],
                                                  key=f"season_off_{tname}")
                        def_style = st.selectbox("Defense", defense_style_keys,
                                                  format_func=lambda x: defense_styles[x]["label"],
                                                  key=f"season_def_{tname}")
                        style_configs[tname] = {"offense_style": off_style, "defense_style": def_style}
        
        ai_teams = [t for t in selected_teams if t not in human_teams]
        if ai_teams:
            ai_configs = auto_assign_all_teams(teams_dir_path, human_teams=human_teams, seed=actual_seed)
            
            with st.expander(f"AI Coach Assignments ({len(ai_teams)} teams)", expanded=False):
                ai_data = []
                for tname in sorted(ai_teams):
                    cfg = ai_configs.get(tname, {"offense_style": "balanced", "defense_style": "base_defense"})
                    style_configs[tname] = cfg
                    identity = team_identities.get(tname, {})
                    mascot = identity.get("mascot", "")
                    ai_data.append({
                        "Team": tname,
                        "Mascot": mascot,
                        "Offense": styles.get(cfg["offense_style"], {}).get("label", cfg["offense_style"]),
                        "Defense": defense_styles.get(cfg["defense_style"], {}).get("label", cfg["defense_style"]),
                        "Scheme": get_scheme_label(cfg["offense_style"], cfg["defense_style"]),
                    })
                st.dataframe(pd.DataFrame(ai_data), hide_index=True, use_container_width=True)
        
        for tname in selected_teams:
            if tname not in style_configs:
                style_configs[tname] = {"offense_style": "balanced", "defense_style": "base_defense"}

        sched_col1, sched_col2 = st.columns(2)
        with sched_col1:
            season_games = st.slider("Regular Season Games Per Team", min_value=8, max_value=12, value=10, key="season_games_per_team")
        with sched_col2:
            playoff_options = [p for p in [4, 8, 12, 16] if p <= len(selected_teams)]
            if not playoff_options:
                playoff_options = [len(selected_teams)]
            playoff_size = st.radio("Playoff Format", playoff_options, index=0, key="playoff_size", horizontal=True)

        from engine.season import get_recommended_bowl_count
        rec_bowls = get_recommended_bowl_count(len(selected_teams), playoff_size)
        bowl_count = st.slider("Number of Bowl Games", min_value=0, max_value=min(12, (len(selected_teams) - playoff_size) // 2), value=rec_bowls, key="season_bowl_count")

        run_season = st.button("Simulate Season", type="primary", use_container_width=True, key="run_season")

        if run_season:
            filtered_teams = {name: team for name, team in all_teams.items() if name in selected_teams}

            auto_conferences = {}
            for tname in selected_teams:
                identity = team_identities.get(tname, {})
                conf = identity.get("conference", "")
                if conf:
                    auto_conferences.setdefault(conf, []).append(tname)
            auto_conferences = {k: v for k, v in auto_conferences.items() if len(v) >= 2}

            season = create_season(season_name, filtered_teams, style_configs,
                                   conferences=auto_conferences if auto_conferences else None,
                                   games_per_team=season_games)

            with st.spinner(f"Simulating {len(season.schedule)} games..."):
                season.simulate_season(generate_polls=True)

            num_playoff = playoff_size
            if num_playoff > 0 and len(selected_teams) >= num_playoff:
                with st.spinner("Running playoffs..."):
                    season.simulate_playoff(num_teams=min(num_playoff, len(selected_teams)))

            if bowl_count > 0:
                with st.spinner("Running bowl games..."):
                    season.simulate_bowls(bowl_count=bowl_count, playoff_size=num_playoff)

            st.session_state["last_season"] = season

        if "last_season" in st.session_state:
            season = st.session_state["last_season"]

            st.divider()
            st.subheader("Standings")
            standings = season.get_standings_sorted()
            has_conferences = bool(season.conferences) and len(season.conferences) >= 1
            standings_data = []
            for i, record in enumerate(standings, 1):
                row = {
                    "Rank": i,
                    "Team": record.team_name,
                }
                if has_conferences:
                    row["Conf"] = record.conference
                    row["Conf W-L"] = f"{record.conf_wins}-{record.conf_losses}"
                row.update({
                    "W": record.wins,
                    "L": record.losses,
                    "Win%": f"{record.win_percentage:.3f}",
                    "PF": f"{record.points_for:.1f}",
                    "PA": f"{record.points_against:.1f}",
                    "Diff": f"{record.point_differential:+.1f}",
                    "OPI": f"{record.avg_opi:.1f}",
                    "Territory": f"{record.avg_territory:.1f}",
                    "Pressure": f"{record.avg_pressure:.1f}",
                    "Chaos": f"{record.avg_chaos:.1f}",
                    "Kicking": f"{record.avg_kicking:.1f}",
                })
                standings_data.append(row)
            st.dataframe(pd.DataFrame(standings_data), hide_index=True, use_container_width=True)

            if season.conferences and len(season.conferences) >= 1:
                st.subheader("Conference Standings")
                conf_tabs = st.tabs(sorted(season.conferences.keys()))
                for conf_tab, conf_name in zip(conf_tabs, sorted(season.conferences.keys())):
                    with conf_tab:
                        conf_standings = season.get_conference_standings(conf_name)
                        if conf_standings:
                            conf_data = []
                            for i, record in enumerate(conf_standings, 1):
                                conf_data.append({
                                    "Rank": i,
                                    "Team": record.team_name,
                                    "Conf": f"{record.conf_wins}-{record.conf_losses}",
                                    "Overall": f"{record.wins}-{record.losses}",
                                    "Win%": f"{record.win_percentage:.3f}",
                                    "PF": f"{record.points_for:.1f}",
                                    "PA": f"{record.points_against:.1f}",
                                    "OPI": f"{record.avg_opi:.1f}",
                                })
                            st.dataframe(pd.DataFrame(conf_data), hide_index=True, use_container_width=True)

            final_poll = season.get_latest_poll()
            if final_poll:
                st.subheader("Final Top 25 Rankings")
                poll_data = []
                for r in final_poll.rankings:
                    movement = ""
                    if r.prev_rank is not None:
                        diff = r.prev_rank - r.rank
                        if diff > 0:
                            movement = f"+{diff}"
                        elif diff < 0:
                            movement = str(diff)
                        else:
                            movement = "--"
                    else:
                        movement = "NEW"
                    poll_data.append({
                        "#": r.rank,
                        "Team": r.team_name,
                        "Record": r.record,
                        "Conf": r.conference,
                        "Score": f"{r.poll_score:.1f}",
                        "Move": movement,
                    })
                st.dataframe(pd.DataFrame(poll_data), hide_index=True, use_container_width=True)

            st.subheader("Season Metrics Radar")
            radar_teams = st.multiselect("Compare Teams", [r.team_name for r in standings],
                                          default=[standings[0].team_name, standings[-1].team_name] if len(standings) > 1 else [standings[0].team_name],
                                          key="radar_teams")
            if radar_teams:
                categories = ["OPI", "Territory", "Pressure", "Chaos", "Kicking", "Drive Quality", "Turnover Impact"]
                fig = go.Figure()
                for tname in radar_teams:
                    record = season.standings[tname]
                    values = [record.avg_opi, record.avg_territory, record.avg_pressure,
                              record.avg_chaos, record.avg_kicking, record.avg_drive_quality * 10,
                              record.avg_turnover_impact]
                    fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]],
                                                   fill='toself', name=tname))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                                  title="Team Metrics Comparison", height=500)
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("Scoring Distribution")
            score_data = []
            for game in season.schedule:
                if game.completed:
                    score_data.append({"Team": game.home_team, "Score": game.home_score or 0, "Location": "Home"})
                    score_data.append({"Team": game.away_team, "Score": game.away_score or 0, "Location": "Away"})
            if score_data:
                fig = px.box(pd.DataFrame(score_data), x="Team", y="Score", color="Team",
                             title="Score Distribution by Team")
                fig.update_layout(showlegend=False, height=400)
                st.plotly_chart(fig, use_container_width=True)

            if season.playoff_bracket:
                st.subheader("Playoff Bracket")

                def _render_round(label, week):
                    round_games = [g for g in season.playoff_bracket if g.week == week]
                    if round_games:
                        st.markdown(f"**{label}**")
                        for i, game in enumerate(round_games, 1):
                            hs = game.home_score or 0
                            aws = game.away_score or 0
                            winner = game.home_team if hs > aws else game.away_team
                            loser = game.away_team if hs > aws else game.home_team
                            w_score = max(hs, aws)
                            l_score = min(hs, aws)
                            st.markdown(f"Game {i}: **{winner}** {w_score:.1f} def. {loser} {l_score:.1f}")

                _render_round("First Round", 997)
                _render_round("Quarterfinals", 998)
                _render_round("Semifinals", 999)

                championship = [g for g in season.playoff_bracket if g.week == 1000]
                if championship:
                    game = championship[0]
                    hs = game.home_score or 0
                    aws = game.away_score or 0
                    winner = game.home_team if hs > aws else game.away_team
                    loser = game.away_team if hs > aws else game.home_team
                    w_score = max(hs, aws)
                    l_score = min(hs, aws)
                    st.success(f"**CHAMPION: {winner}** {w_score:.1f} def. {loser} {l_score:.1f}")

            if season.bowl_games:
                st.subheader("Bowl Games")
                from engine.season import BOWL_TIERS
                current_tier = 0
                for bowl in season.bowl_games:
                    if bowl.tier != current_tier:
                        current_tier = bowl.tier
                        tier_label = BOWL_TIERS.get(bowl.tier, "Standard")
                        st.markdown(f"**{tier_label} Bowls**")
                    g = bowl.game
                    hs = g.home_score or 0
                    aws = g.away_score or 0
                    winner = g.home_team if hs > aws else g.away_team
                    loser = g.away_team if hs > aws else g.home_team
                    w_score = max(hs, aws)
                    l_score = min(hs, aws)
                    w_rec = bowl.team_1_record if winner == g.home_team else bowl.team_2_record
                    l_rec = bowl.team_2_record if winner == g.home_team else bowl.team_1_record
                    st.markdown(f"**{bowl.name}**: **{winner}** ({w_rec}) {w_score:.1f} def. {loser} ({l_rec}) {l_score:.1f}")

            st.subheader("Full Schedule Results")
            schedule_data = []
            for game in season.schedule:
                if game.completed:
                    hs = game.home_score or 0
                    aws = game.away_score or 0
                    winner = game.home_team if hs > aws else game.away_team
                    schedule_data.append({
                        "Week": game.week,
                        "Home": game.home_team,
                        "Away": game.away_team,
                        "Home Score": f"{hs:.1f}",
                        "Away Score": f"{aws:.1f}",
                        "Winner": winner,
                    })
            if schedule_data:
                st.dataframe(pd.DataFrame(schedule_data), hide_index=True, use_container_width=True, height=400)

            st.subheader("Export Season Data")
            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                standings_csv = io.StringIO()
                writer = csv.writer(standings_csv)
                writer.writerow(["Rank", "Team", "W", "L", "Win%", "PF", "PA", "Diff", "OPI"])
                for i, r in enumerate(standings, 1):
                    writer.writerow([i, r.team_name, r.wins, r.losses, f"{r.win_percentage:.3f}",
                                     f"{r.points_for:.1f}", f"{r.points_against:.1f}",
                                     f"{r.point_differential:+.1f}", f"{r.avg_opi:.1f}"])
                st.download_button("Download Standings (CSV)", standings_csv.getvalue(),
                                   file_name="season_standings.csv", mime="text/csv")
            with exp_col2:
                schedule_csv = io.StringIO()
                writer = csv.writer(schedule_csv)
                writer.writerow(["Week", "Home", "Away", "Home Score", "Away Score", "Winner"])
                for game in season.schedule:
                    if game.completed:
                        hs = game.home_score or 0
                        aws = game.away_score or 0
                        winner = game.home_team if hs > aws else game.away_team
                        writer.writerow([game.week, game.home_team, game.away_team,
                                         f"{hs:.1f}", f"{aws:.1f}", winner])
                st.download_button("Download Schedule (CSV)", schedule_csv.getvalue(),
                                   file_name="season_schedule.csv", mime="text/csv")


elif page == "Dynasty Mode":
    st.title("Dynasty Mode")
    st.caption("Multi-season career mode with historical tracking, awards, and record books")

    if "dynasty" not in st.session_state:
        st.subheader("Create New Dynasty")

        dynasty_col1, dynasty_col2 = st.columns(2)
        with dynasty_col1:
            dynasty_name = st.text_input("Dynasty Name", value="My Viperball Dynasty", key="dyn_name")
            coach_name = st.text_input("Coach Name", value="Coach", key="coach_name")
        with dynasty_col2:
            coach_team = st.selectbox("Your Team", [t["name"] for t in teams], key="coach_team")
            start_year = st.number_input("Starting Year", min_value=2020, max_value=2050, value=2026, key="start_year")

        st.divider()
        st.subheader("Conference Setup")
        teams_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")
        setup_teams = load_teams_from_directory(teams_dir)
        all_team_names_sorted = sorted(setup_teams.keys())

        num_conferences = st.radio("Number of Conferences", [1, 2, 3, 4], index=1, horizontal=True, key="num_conf")

        default_conf_names = ["CVL East", "CVL West", "CVL North", "CVL South"]
        conf_assignments = {}
        conf_names_list = []

        if num_conferences == 1:
            conf_name_single = st.text_input("Conference Name", value="CVL", key="conf_name_0")
            conf_names_list = [conf_name_single]
            for tname in all_team_names_sorted:
                conf_assignments[tname] = conf_name_single
        else:
            conf_cols = st.columns(num_conferences)
            for ci in range(num_conferences):
                with conf_cols[ci]:
                    cname = st.text_input(f"Conference {ci+1}", value=default_conf_names[ci], key=f"conf_name_{ci}")
                    conf_names_list.append(cname)

            chunk_size = len(all_team_names_sorted) // num_conferences
            default_splits = {}
            for ci in range(num_conferences):
                start_idx = ci * chunk_size
                end_idx = start_idx + chunk_size if ci < num_conferences - 1 else len(all_team_names_sorted)
                for tname in all_team_names_sorted[start_idx:end_idx]:
                    default_splits[tname] = conf_names_list[ci]

            with st.expander("Assign Teams to Conferences", expanded=False):
                assign_cols_per_row = 4
                assign_chunks = [all_team_names_sorted[i:i+assign_cols_per_row]
                                 for i in range(0, len(all_team_names_sorted), assign_cols_per_row)]
                for achunk in assign_chunks:
                    acols = st.columns(len(achunk))
                    for acol, tname in zip(acols, achunk):
                        with acol:
                            default_idx = conf_names_list.index(default_splits.get(tname, conf_names_list[0]))
                            assigned = st.selectbox(tname[:20], conf_names_list, index=default_idx,
                                                     key=f"conf_assign_{tname}")
                            conf_assignments[tname] = assigned

        st.divider()
        load_col1, load_col2 = st.columns(2)
        with load_col1:
            create_btn = st.button("Create Dynasty", type="primary", use_container_width=True, key="create_dynasty")
        with load_col2:
            uploaded = st.file_uploader("Load Saved Dynasty", type=["json"], key="load_dynasty")

        if create_btn:
            dynasty = create_dynasty(dynasty_name, coach_name, coach_team, start_year)
            conf_team_lists = {}
            for tname, cname in conf_assignments.items():
                if cname not in conf_team_lists:
                    conf_team_lists[cname] = []
                conf_team_lists[cname].append(tname)
            for cname, cteams in conf_team_lists.items():
                dynasty.add_conference(cname, cteams)
            st.session_state["dynasty"] = dynasty
            st.session_state["dynasty_teams"] = setup_teams
            st.rerun()

        if uploaded:
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                    tmp.write(uploaded.read().decode())
                    tmp_path = tmp.name
                dynasty = Dynasty.load(tmp_path)
                all_teams_loaded = load_teams_from_directory(teams_dir)
                st.session_state["dynasty"] = dynasty
                st.session_state["dynasty_teams"] = all_teams_loaded
                os.unlink(tmp_path)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load dynasty: {e}")

    else:
        dynasty = st.session_state["dynasty"]
        all_dynasty_teams = st.session_state["dynasty_teams"]

        st.sidebar.divider()
        st.sidebar.markdown(f"**Dynasty:** {dynasty.dynasty_name}")
        st.sidebar.markdown(f"**Coach:** {dynasty.coach.name}")
        st.sidebar.markdown(f"**Team:** {dynasty.coach.team_name}")
        st.sidebar.markdown(f"**Year:** {dynasty.current_year}")
        st.sidebar.markdown(f"**Record:** {dynasty.coach.career_wins}-{dynasty.coach.career_losses}")
        st.sidebar.markdown(f"**Titles:** {dynasty.coach.championships}")

        if st.sidebar.button("End Dynasty", key="end_dynasty"):
            del st.session_state["dynasty"]
            del st.session_state["dynasty_teams"]
            if "last_dynasty_season" in st.session_state:
                del st.session_state["last_dynasty_season"]
            st.rerun()

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Simulate Season", "Standings & Polls", "Coach Dashboard", "Team History", "Record Book"])

        with tab1:
            st.subheader(f"Season {dynasty.current_year}")

            setup_col1, setup_col2 = st.columns(2)
            with setup_col1:
                total_teams = len(all_dynasty_teams)
                games_per_team = st.slider(
                    "Regular Season Games Per Team",
                    min_value=8, max_value=12, value=10,
                    key=f"dyn_games_{dynasty.current_year}"
                )
            with setup_col2:
                dyn_playoff_options = [p for p in [4, 8, 12, 16] if p <= total_teams]
                if not dyn_playoff_options:
                    dyn_playoff_options = [total_teams]
                playoff_format = st.radio("Playoff Format", dyn_playoff_options, index=0, horizontal=True,
                                          key=f"dyn_playoff_{dynasty.current_year}")

            from engine.season import get_recommended_bowl_count as dyn_rec_bowls
            dyn_rec = dyn_rec_bowls(total_teams, playoff_format)
            dyn_max_bowls = max(0, (total_teams - playoff_format) // 2)
            dyn_bowl_count = st.slider("Number of Bowl Games", min_value=0, max_value=min(12, dyn_max_bowls), value=min(dyn_rec, min(12, dyn_max_bowls)),
                                        key=f"dyn_bowls_{dynasty.current_year}")

            from engine.ai_coach import auto_assign_all_teams, get_scheme_label, load_team_identity
            teams_dir_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")
            team_identities = load_team_identity(teams_dir_path)
            
            st.markdown("**Your Team**")
            user_team = dynasty.coach.team_name
            user_identity = team_identities.get(user_team, {})
            user_mascot = user_identity.get("mascot", "")
            user_conf = user_identity.get("conference", "")
            user_colors = user_identity.get("colors", [])
            user_color_str = " / ".join(user_colors[:2]) if user_colors else ""
            
            if user_mascot or user_conf:
                st.caption(f"{user_mascot} | {user_conf}" + (f" | {user_color_str}" if user_color_str else ""))
            
            user_off_col, user_def_col = st.columns(2)
            with user_off_col:
                user_off = st.selectbox("Offense Style", style_keys, format_func=lambda x: styles[x]["label"],
                                         key=f"dyn_user_off_{dynasty.current_year}")
            with user_def_col:
                user_def = st.selectbox("Defense Style", defense_style_keys,
                                         format_func=lambda x: defense_styles[x]["label"],
                                         key=f"dyn_user_def_{dynasty.current_year}")
            
            ai_seed = hash(f"{dynasty.dynasty_name}_{dynasty.current_year}") % 999999
            ai_configs = auto_assign_all_teams(
                teams_dir_path,
                human_teams=[user_team],
                human_configs={user_team: {"offense_style": user_off, "defense_style": user_def}},
                seed=ai_seed,
            )
            
            dyn_style_configs = {}
            dyn_style_configs[user_team] = {"offense_style": user_off, "defense_style": user_def}
            for tname in all_dynasty_teams:
                if tname != user_team:
                    dyn_style_configs[tname] = ai_configs.get(tname, {"offense_style": "balanced", "defense_style": "base_defense"})
            
            ai_opponent_teams = sorted([t for t in all_dynasty_teams if t != user_team])
            with st.expander(f"AI Coach Assignments ({len(ai_opponent_teams)} teams)", expanded=False):
                ai_data = []
                for tname in ai_opponent_teams:
                    cfg = dyn_style_configs[tname]
                    identity = team_identities.get(tname, {})
                    mascot = identity.get("mascot", "")
                    ai_data.append({
                        "Team": tname,
                        "Mascot": mascot,
                        "Offense": styles.get(cfg["offense_style"], {}).get("label", cfg["offense_style"]),
                        "Defense": defense_styles.get(cfg["defense_style"], {}).get("label", cfg["defense_style"]),
                    })
                st.dataframe(pd.DataFrame(ai_data), hide_index=True, use_container_width=True)

            if st.button(f"Simulate {dynasty.current_year} Season", type="primary", use_container_width=True, key="sim_dynasty_season"):
                conf_dict = dynasty.get_conferences_dict()
                season = create_season(
                    f"{dynasty.current_year} CVL Season",
                    all_dynasty_teams,
                    dyn_style_configs,
                    conferences=conf_dict,
                    games_per_team=games_per_team
                )

                total_games = len(season.schedule)
                with st.spinner(f"Simulating {dynasty.current_year} season ({total_games} games, {games_per_team}/team)..."):
                    season.simulate_season(generate_polls=True)

                playoff_count = min(playoff_format, len(team_list))
                if playoff_count >= 4:
                    with st.spinner("Running playoffs..."):
                        season.simulate_playoff(num_teams=playoff_count)

                if dyn_bowl_count > 0:
                    with st.spinner("Running bowl games..."):
                        season.simulate_bowls(bowl_count=dyn_bowl_count, playoff_size=playoff_count)

                dynasty.advance_season(season)
                st.session_state["dynasty"] = dynasty
                st.session_state["last_dynasty_season"] = season
                st.rerun()

            if "last_dynasty_season" in st.session_state:
                season = st.session_state["last_dynasty_season"]
                prev_year = dynasty.current_year - 1

                st.divider()
                st.subheader(f"{prev_year} Season Results")

                if season.champion:
                    if season.champion == dynasty.coach.team_name:
                        st.balloons()
                        st.success(f"YOUR TEAM {season.champion} WON THE CHAMPIONSHIP!")
                    else:
                        st.info(f"Champion: {season.champion}")

                standings = season.get_standings_sorted()
                standings_data = []
                for i, record in enumerate(standings, 1):
                    is_user = record.team_name == dynasty.coach.team_name
                    standings_data.append({
                        "Rank": i,
                        "Team": f"{'>>> ' if is_user else ''}{record.team_name}",
                        "Conf": record.conference,
                        "W": record.wins,
                        "L": record.losses,
                        "Conf W-L": f"{record.conf_wins}-{record.conf_losses}",
                        "Win%": f"{record.win_percentage:.3f}",
                        "PF": f"{record.points_for:.1f}",
                        "PA": f"{record.points_against:.1f}",
                        "OPI": f"{record.avg_opi:.1f}",
                    })
                st.dataframe(pd.DataFrame(standings_data), hide_index=True, use_container_width=True, height=400)

                if season.bowl_games:
                    st.subheader("Bowl Games")
                    from engine.season import BOWL_TIERS as DYN_BOWL_TIERS
                    dyn_current_tier = 0
                    for bowl in season.bowl_games:
                        if bowl.tier != dyn_current_tier:
                            dyn_current_tier = bowl.tier
                            tier_label = DYN_BOWL_TIERS.get(bowl.tier, "Standard")
                            st.markdown(f"**{tier_label} Bowls**")
                        g = bowl.game
                        hs = g.home_score or 0
                        aws = g.away_score or 0
                        winner = g.home_team if hs > aws else g.away_team
                        loser = g.away_team if hs > aws else g.home_team
                        w_score = max(hs, aws)
                        l_score = min(hs, aws)
                        w_rec = bowl.team_1_record if winner == g.home_team else bowl.team_2_record
                        l_rec = bowl.team_2_record if winner == g.home_team else bowl.team_1_record
                        is_user_bowl = dynasty.coach.team_name in (g.home_team, g.away_team)
                        prefix = ">>> " if is_user_bowl else ""
                        st.markdown(f"{prefix}**{bowl.name}**: **{winner}** ({w_rec}) {w_score:.1f} def. {loser} ({l_rec}) {l_score:.1f}")

        with tab2:
            st.subheader("Standings & Weekly Poll")

            if "last_dynasty_season" in st.session_state:
                season = st.session_state["last_dynasty_season"]
                prev_year = dynasty.current_year - 1

                view_mode = st.radio("View", ["Conference Standings", "Weekly Poll"], horizontal=True, key="standings_view")

                if view_mode == "Conference Standings":
                    conf_names = list(season.conferences.keys())
                    if conf_names:
                        for conf_name in conf_names:
                            st.subheader(f"{conf_name}")
                            conf_standings = season.get_conference_standings(conf_name)
                            if conf_standings:
                                conf_data = []
                                for i, record in enumerate(conf_standings, 1):
                                    is_user = record.team_name == dynasty.coach.team_name
                                    conf_data.append({
                                        "Rank": i,
                                        "Team": f"{'>>> ' if is_user else ''}{record.team_name}",
                                        "Conf": f"{record.conf_wins}-{record.conf_losses}",
                                        "Overall": f"{record.wins}-{record.losses}",
                                        "Win%": f"{record.win_percentage:.3f}",
                                        "PF": f"{record.points_for:.1f}",
                                        "PA": f"{record.points_against:.1f}",
                                        "OPI": f"{record.avg_opi:.1f}",
                                        "Kicking": f"{record.avg_kicking:.1f}",
                                        "Chaos": f"{record.avg_chaos:.1f}",
                                    })
                                st.dataframe(pd.DataFrame(conf_data), hide_index=True, use_container_width=True)
                    else:
                        st.caption("No conferences configured")

                elif view_mode == "Weekly Poll":
                    if season.weekly_polls:
                        total_weeks = len(season.weekly_polls)
                        selected_week_idx = st.slider("Select Week", 1, total_weeks, total_weeks,
                                                       key="poll_week_slider")
                        poll = season.weekly_polls[selected_week_idx - 1]

                        st.subheader(f"CVL Top 25 Poll - Week {poll.week}")

                        poll_data = []
                        for r in poll.rankings:
                            change_str = ""
                            if r.rank_change is not None:
                                if r.rank_change > 0:
                                    change_str = f"+{r.rank_change}"
                                elif r.rank_change < 0:
                                    change_str = str(r.rank_change)
                                else:
                                    change_str = "-"
                            else:
                                change_str = "NEW"
                            is_user = r.team_name == dynasty.coach.team_name
                            poll_data.append({
                                "#": r.rank,
                                "Team": f"{'>>> ' if is_user else ''}{r.team_name}",
                                "Record": r.record,
                                "Conf": r.conference,
                                "Score": f"{r.poll_score:.1f}",
                                "Change": change_str,
                            })
                        st.dataframe(pd.DataFrame(poll_data), hide_index=True, use_container_width=True, height=600)

                        if total_weeks >= 2:
                            st.subheader("Poll Movement")
                            track_teams = st.multiselect("Track Teams",
                                                          [r.team_name for r in season.weekly_polls[-1].rankings[:10]],
                                                          default=[dynasty.coach.team_name] if dynasty.coach.team_name in
                                                                   [r.team_name for r in season.weekly_polls[-1].rankings[:25]] else [],
                                                          key="poll_track")
                            if track_teams:
                                movement_data = []
                                for poll in season.weekly_polls:
                                    for r in poll.rankings:
                                        if r.team_name in track_teams:
                                            movement_data.append({
                                                "Week": poll.week,
                                                "Team": r.team_name,
                                                "Rank": r.rank,
                                            })
                                if movement_data:
                                    fig = px.line(pd.DataFrame(movement_data), x="Week", y="Rank",
                                                  color="Team", title="Poll Ranking Over Season",
                                                  markers=True)
                                    fig.update_yaxes(autorange="reversed", title="Rank (#1 = top)")
                                    fig.update_layout(height=400)
                                    st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.caption("No polls generated yet. Simulate a season first.")
            else:
                st.caption("Simulate a season to see standings and polls.")

        with tab3:
            st.subheader("Coach Career Dashboard")
            coach = dynasty.coach

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Career Record", f"{coach.career_wins}-{coach.career_losses}")
            c2.metric("Win%", f"{coach.win_percentage * 100:.1f}%")
            c3.metric("Championships", str(coach.championships))
            c4.metric("Seasons", str(coach.years_experience))

            if coach.season_records:
                st.subheader("Season-by-Season")
                season_hist = []
                for year in sorted(coach.season_records.keys()):
                    rec = coach.season_records[year]
                    season_hist.append({
                        "Year": year,
                        "W-L": f"{rec['wins']}-{rec['losses']}",
                        "PF": f"{rec['points_for']:.1f}",
                        "PA": f"{rec['points_against']:.1f}",
                        "Playoff": "Yes" if rec.get("playoff") else "No",
                        "Champion": "Yes" if rec.get("champion") else "No",
                    })
                st.dataframe(pd.DataFrame(season_hist), hide_index=True, use_container_width=True)

                years = sorted(coach.season_records.keys())
                wins = [coach.season_records[y]["wins"] for y in years]
                fig = px.bar(x=years, y=wins, title="Wins Per Season", labels={"x": "Year", "y": "Wins"})
                st.plotly_chart(fig, use_container_width=True)

        with tab4:
            st.subheader("Team History")
            selected_history_team = st.selectbox("Select Team", sorted(dynasty.team_histories.keys()), key="history_team")

            if selected_history_team in dynasty.team_histories:
                hist = dynasty.team_histories[selected_history_team]

                h1, h2, h3, h4 = st.columns(4)
                h1.metric("All-Time Record", f"{hist.total_wins}-{hist.total_losses}")
                h2.metric("Win%", f"{hist.win_percentage * 100:.1f}%")
                h3.metric("Championships", str(hist.total_championships))
                h4.metric("Playoff Apps", str(hist.total_playoff_appearances))

                if hist.championship_years:
                    st.markdown(f"**Championship Years:** {', '.join(str(y) for y in hist.championship_years)}")

                if hist.season_records:
                    st.subheader("Season Records")
                    hist_data = []
                    for year in sorted(hist.season_records.keys()):
                        rec = hist.season_records[year]
                        hist_data.append({
                            "Year": year,
                            "W-L": f"{rec['wins']}-{rec['losses']}",
                            "PF": f"{rec['points_for']:.1f}",
                            "PA": f"{rec['points_against']:.1f}",
                            "OPI": f"{rec.get('avg_opi', 0):.1f}",
                            "Champion": "Yes" if rec.get("champion") else "No",
                        })
                    st.dataframe(pd.DataFrame(hist_data), hide_index=True, use_container_width=True)

        with tab5:
            st.subheader("Record Book")
            rb = dynasty.record_book

            st.markdown("**Single-Season Records**")
            rec_data = []
            if rb.most_wins_season.get("team"):
                rec_data.append({"Record": "Most Wins", "Team": rb.most_wins_season["team"],
                                 "Value": str(rb.most_wins_season["wins"]), "Year": str(rb.most_wins_season.get("year", ""))})
            if rb.most_points_season.get("team"):
                rec_data.append({"Record": "Most Points", "Team": rb.most_points_season["team"],
                                 "Value": f"{rb.most_points_season['points']:.1f}", "Year": str(rb.most_points_season.get("year", ""))})
            if rb.best_defense_season.get("team"):
                rec_data.append({"Record": "Best Defense (PPG)", "Team": rb.best_defense_season["team"],
                                 "Value": f"{rb.best_defense_season['ppg_allowed']:.1f}", "Year": str(rb.best_defense_season.get("year", ""))})
            if rb.highest_opi_season.get("team"):
                rec_data.append({"Record": "Highest OPI", "Team": rb.highest_opi_season["team"],
                                 "Value": f"{rb.highest_opi_season['opi']:.1f}", "Year": str(rb.highest_opi_season.get("year", ""))})
            if rb.most_chaos_season.get("team"):
                rec_data.append({"Record": "Most Chaos", "Team": rb.most_chaos_season["team"],
                                 "Value": f"{rb.most_chaos_season['chaos']:.1f}", "Year": str(rb.most_chaos_season.get("year", ""))})
            if rec_data:
                st.dataframe(pd.DataFrame(rec_data), hide_index=True, use_container_width=True)
            else:
                st.caption("No records yet - simulate some seasons!")

            st.markdown("**All-Time Records**")
            alltime_data = []
            if rb.most_championships.get("team"):
                alltime_data.append({"Record": "Most Championships", "Team/Coach": rb.most_championships["team"],
                                     "Value": str(rb.most_championships["championships"])})
            if rb.highest_win_percentage.get("team"):
                alltime_data.append({"Record": "Highest Win%", "Team/Coach": rb.highest_win_percentage["team"],
                                     "Value": f"{rb.highest_win_percentage['win_pct']:.3f}"})
            if rb.most_coaching_wins.get("coach"):
                alltime_data.append({"Record": "Most Coaching Wins", "Team/Coach": rb.most_coaching_wins["coach"],
                                     "Value": str(rb.most_coaching_wins["wins"])})
            if rb.most_coaching_championships.get("coach"):
                alltime_data.append({"Record": "Most Coaching Titles", "Team/Coach": rb.most_coaching_championships["coach"],
                                     "Value": str(rb.most_coaching_championships["championships"])})
            if alltime_data:
                st.dataframe(pd.DataFrame(alltime_data), hide_index=True, use_container_width=True)
            else:
                st.caption("Play more seasons to build records!")

            if dynasty.awards_history:
                st.markdown("**Awards History**")
                awards_data = []
                for year in sorted(dynasty.awards_history.keys()):
                    awards = dynasty.awards_history[year]
                    awards_data.append({
                        "Year": year,
                        "Champion": awards.champion,
                        "Best Record": awards.best_record,
                        "Top Scoring": awards.highest_scoring,
                        "Best Defense": awards.best_defense,
                        "Highest OPI": awards.highest_opi,
                    })
                st.dataframe(pd.DataFrame(awards_data), hide_index=True, use_container_width=True)

            st.divider()
            save_col1, save_col2 = st.columns(2)
            with save_col1:
                if st.button("Save Dynasty", use_container_width=True, key="save_dynasty"):
                    save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dynasty_save.json")
                    dynasty.save(save_path)
                    st.success(f"Dynasty saved!")
            with save_col2:
                save_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dynasty_save.json")
                if os.path.exists(save_path):
                    with open(save_path, 'r') as f:
                        st.download_button("Download Save File", f.read(),
                                           file_name=f"{dynasty.dynasty_name.replace(' ', '_')}.json",
                                           mime="application/json")
