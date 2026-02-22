import sys
import os
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

_api_server_lock = threading.Lock()
_api_server_started = False


def _port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _ensure_api_server():
    """Start the FastAPI backend in a background thread if it isn't already running.

    On Streamlit Cloud (or any single-process host) there is no external
    process manager to launch the API server, so we spin it up here.
    Guarded by a module-level lock + flag to prevent duplicate threads.
    Only starts an embedded server when the API URL points to localhost.
    Non-blocking: starts the server thread and returns immediately so
    Streamlit's health check endpoint can respond in time.
    """
    global _api_server_started

    from ui.api_client import API_BASE as _client_base
    api_base = _client_base
    if "127.0.0.1" not in api_base and "localhost" not in api_base:
        return

    # Parse the port from the API client's base URL so they always match
    try:
        _port = int(api_base.rsplit(":", 1)[1].split("/")[0])
    except (ValueError, IndexError):
        _port = 8080

    if _port_in_use(_port):
        return

    with _api_server_lock:
        if _api_server_started:
            return
        _api_server_started = True

    import uvicorn
    from api.main import app as fastapi_app

    def _run():
        uvicorn.run(fastapi_app, host="127.0.0.1", port=_port, log_level="warning")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    time.sleep(3)


_ensure_api_server()

import streamlit as st

from ui import api_client
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
    .block-container { padding-top: 2.5rem; padding-bottom: 2rem; }

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
        gap: 8px;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0;
    }
    .stTabs [data-baseweb="tab-list"] button[data-baseweb="tab"] {
        padding: 10px 24px;
        font-weight: 600;
        font-size: 1rem;
        color: #64748b;
        border-bottom: 3px solid transparent;
        margin-bottom: -2px;
    }
    .stTabs [data-baseweb="tab-list"] button[data-baseweb="tab"][aria-selected="true"] {
        color: #0f172a;
        border-bottom-color: #dc2626;
        font-weight: 700;
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

try:
    teams_resp = api_client.get_teams()
    teams = teams_resp.get("teams", [])
except api_client.APIError:
    teams = []

try:
    styles_resp = api_client.get_styles()
    styles = styles_resp.get("offense_styles", {})
    defense_styles = styles_resp.get("defense_styles", {})
    st_schemes = styles_resp.get("st_schemes", {})
except api_client.APIError:
    styles = {}
    defense_styles = {}
    st_schemes = {}

team_names = {t["key"]: t["name"] for t in teams}
style_keys = list(styles.keys())
defense_style_keys = list(defense_styles.keys())
st_scheme_keys = list(st_schemes.keys())

shared = {
    "teams": teams,
    "styles": styles,
    "team_names": team_names,
    "style_keys": style_keys,
    "defense_style_keys": defense_style_keys,
    "defense_styles": defense_styles,
    "st_schemes": st_schemes,
    "st_scheme_keys": st_scheme_keys,
    "OFFENSE_TOOLTIPS": OFFENSE_TOOLTIPS,
    "DEFENSE_TOOLTIPS": DEFENSE_TOOLTIPS,
}

def _mode_label():
    mode = st.session_state.get("api_mode")
    session_id = st.session_state.get("api_session_id")
    if not session_id or not mode:
        return "No Active Session"
    if mode == "dynasty":
        try:
            dyn_status = api_client.get_dynasty_status(session_id)
            dynasty_name = dyn_status.get("dynasty_name", "Dynasty")
            current_year = dyn_status.get("current_year", "")
            return f"Dynasty: {dynasty_name} ({current_year})"
        except api_client.APIError:
            return "Dynasty (loading...)"
    if mode == "season":
        try:
            status = api_client.get_season_status(session_id)
            return f"Season: {status.get('name', 'Season')}"
        except api_client.APIError:
            return "Season (loading...)"
    return "No Active Session"

with st.sidebar:
    st.markdown('<p class="sidebar-brand">Viperball Sandbox</p>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-tagline">Collegiate Viperball League Simulator</p>', unsafe_allow_html=True)
    st.divider()

    st.markdown(f"**{_mode_label()}**")

    if st.session_state.get("api_session_id") and st.session_state.get("api_mode"):
        if st.button("End Session", key="end_session_sidebar", use_container_width=True):
            session_id = st.session_state.get("api_session_id")
            if session_id:
                try:
                    api_client.delete_session(session_id)
                except api_client.APIError:
                    pass
            for key in ["api_session_id", "api_mode", "season_human_teams_list",
                        "season_playoff_size", "season_bowl_count",
                        "dynasty", "dynasty_teams", "last_dynasty_season",
                        "last_dynasty_injury_tracker", "active_season",
                        "season_phase", "dyn_season_phase", "dyn_playoff_size", "dyn_bowl_count"]:
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
