import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st

from engine import get_available_teams, get_available_styles, DEFENSE_STYLES

from ui.helpers import OFFENSE_TOOLTIPS, DEFENSE_TOOLTIPS
from ui.page_modules.section_play import render_play_section
from ui.page_modules.section_league import render_league_section
from ui.page_modules.section_my_team import render_my_team_section
from ui.page_modules.section_export import render_export_section
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
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }

    section[data-testid="stSidebar"] {
        background-color: #0f172a;
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] p {
        color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] .stRadio > label {
        color: #94a3b8 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        color: #cbd5e1 !important;
        font-size: 0.95rem !important;
        text-transform: none;
        letter-spacing: normal;
        font-weight: 400;
        padding: 0.4rem 0.6rem;
        border-radius: 6px;
        transition: background-color 0.15s;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
        background-color: #1e293b;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-checked="true"],
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {
        background-color: #1e293b;
        color: #ffffff !important;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #334155;
    }
    .sidebar-brand {
        font-size: 1.4rem;
        font-weight: 800;
        color: #ffffff !important;
        letter-spacing: -0.02em;
        margin-bottom: 0;
        line-height: 1.2;
    }
    .sidebar-tagline {
        font-size: 0.75rem;
        color: #64748b !important;
        margin-top: 2px;
        margin-bottom: 1rem;
    }

    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 12px 16px;
        border-radius: 10px;
    }
    div[data-testid="stMetric"] label {
        color: #64748b !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 700 !important;
        font-size: 1.5rem !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: #64748b !important;
        font-size: 0.85rem !important;
    }

    .score-big {
        font-size: 2.8rem;
        font-weight: 800;
        text-align: center;
        line-height: 1;
        margin: 0;
        color: #0f172a;
    }
    .team-name {
        font-size: 1.05rem;
        font-weight: 600;
        text-align: center;
        color: #475569;
        margin-bottom: 2px;
    }

    .drive-td { color: #16a34a; font-weight: 700; }
    .drive-kick { color: #2563eb; font-weight: 700; }
    .drive-fumble { color: #dc2626; font-weight: 700; }
    .drive-downs { color: #d97706; font-weight: 700; }
    .drive-punt { color: #94a3b8; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 20px;
        font-weight: 500;
    }

    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }

    h2 {
        color: #0f172a !important;
        font-weight: 700 !important;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.3rem;
    }

    .streamlit-expanderHeader {
        font-weight: 600;
        color: #334155;
    }
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

def _mode_label():
    if "dynasty" in st.session_state:
        d = st.session_state["dynasty"]
        return f"Dynasty: {d.dynasty_name} ({d.current_year})"
    if "active_season" in st.session_state:
        return f"Season: {st.session_state['active_season'].name}"
    return "No Active Session"

with st.sidebar:
    st.markdown('<p class="sidebar-brand">Viperball Sandbox</p>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-tagline">Collegiate Viperball League Simulator</p>', unsafe_allow_html=True)
    st.divider()

    st.markdown(f"**{_mode_label()}**")

    if "dynasty" in st.session_state or "active_season" in st.session_state:
        if st.button("End Session", key="end_session_sidebar", use_container_width=True):
            for key in ["dynasty", "dynasty_teams", "last_dynasty_season",
                        "last_dynasty_injury_tracker", "active_season",
                        "season_human_teams_list", "season_phase",
                        "season_playoff_size", "season_bowl_count",
                        "dyn_season_phase", "dyn_playoff_size", "dyn_bowl_count"]:
                st.session_state.pop(key, None)
            st.rerun()

    st.divider()
    st.markdown("**Settings**")
    settings_page = st.radio(
        "Settings", ["Debug Tools", "Play Inspector"],
        index=None,
        label_visibility="collapsed",
        key="settings_page",
    )

    st.divider()
    st.caption("v0.9 Beta — CVL Engine")
    st.caption(f"{len(teams)} teams across 12 conferences")

if settings_page:
    if settings_page == "Debug Tools":
        render_debug_tools(shared)
    elif settings_page == "Play Inspector":
        render_play_inspector(shared)
else:
    main_tabs = st.tabs(["Play", "League", "My Team", "Export"])

    with main_tabs[0]:
        render_play_section(shared)

    with main_tabs[1]:
        render_league_section(shared)

    with main_tabs[2]:
        render_my_team_section(shared)

    with main_tabs[3]:
        render_export_section(shared)
