import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st

from engine import get_available_teams, get_available_styles, DEFENSE_STYLES

from ui.helpers import OFFENSE_TOOLTIPS, DEFENSE_TOOLTIPS
from ui.page_modules.game_simulator import render_game_simulator
from ui.page_modules.season_simulator import render_season_simulator
from ui.page_modules.dynasty_mode import render_dynasty_mode
from ui.page_modules.team_roster import render_team_roster
from ui.page_modules.debug_tools import render_debug_tools
from ui.page_modules.play_inspector import render_play_inspector

st.set_page_config(
    page_title="Viperball Sandbox",
    page_icon="\U0001f3c8",
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

shared = {
    "teams": teams,
    "styles": styles,
    "team_names": team_names,
    "style_keys": style_keys,
    "defense_style_keys": defense_style_keys,
    "defense_styles": defense_styles,
    "OFFENSE_TOOLTIPS": OFFENSE_TOOLTIPS,
    "DEFENSE_TOOLTIPS": DEFENSE_TOOLTIPS,
}

page = st.sidebar.radio("Navigation", [
    "Game Simulator", "Season Simulator", "Dynasty Mode",
    "Team Roster", "Debug Tools", "Play Inspector"
], index=0)

if page == "Game Simulator":
    render_game_simulator(shared)
elif page == "Season Simulator":
    render_season_simulator(shared)
elif page == "Dynasty Mode":
    render_dynasty_mode(shared)
elif page == "Team Roster":
    render_team_roster(shared)
elif page == "Debug Tools":
    render_debug_tools(shared)
elif page == "Play Inspector":
    render_play_inspector(shared)
