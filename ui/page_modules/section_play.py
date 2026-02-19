import io
import csv
import json
import os
import random
import tempfile

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from engine.season import (
    load_teams_from_directory, get_recommended_bowl_count, BOWL_TIERS,
    get_non_conference_slots, get_available_non_conference_opponents,
    estimate_team_prestige_from_roster, is_buy_game, BUY_GAME_NIL_BONUS,
    MAX_CONFERENCE_GAMES,
)
from scripts.generate_rosters import PROGRAM_ARCHETYPES
from engine.conference_names import generate_conference_names
from engine.geography import get_geographic_conference_defaults
from engine.ai_coach import auto_assign_all_teams, get_scheme_label, load_team_identity
from engine.game_engine import WEATHER_CONDITIONS
from ui import api_client
from ui.page_modules.draftyqueenz_ui import (
    render_dq_bankroll_banner, render_dq_pre_sim, render_dq_post_sim,
    render_dq_history,
)
from ui.helpers import (
    load_team, format_time, fmt_vb_score,
    generate_box_score_markdown, generate_play_log_csv,
    generate_drives_csv, safe_filename, drive_result_label,
    render_game_detail, drive_result_color,
)


def _teams_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "teams")


def _get_active_session():
    mode = st.session_state.get("api_mode")
    session_id = st.session_state.get("api_session_id")
    if not session_id or not mode:
        return None
    return mode


def _ensure_session_id():
    if "api_session_id" not in st.session_state:
        resp = api_client.create_session()
        st.session_state["api_session_id"] = resp["session_id"]
    return st.session_state["api_session_id"]


# ── Non-conference scheduling UI helper ──

TIER_LABELS = {
    "elite": "Elite",
    "strong": "Strong",
    "mid": "Mid-Tier",
    "low": "Lower",
    "cupcake": "Cupcake",
}

TIER_HELP = {
    "elite": "Top programs — marquee matchups that boost your strength of schedule",
    "strong": "Solid programs — competitive non-conference games",
    "mid": "Average programs — reasonable opponents",
    "low": "Below-average programs — easier games",
    "cupcake": "Weakest programs — buy-game candidates that give NIL pool bonuses in dynasty",
}


def _render_non_conference_picker(
    user_teams: list,
    all_teams: dict,
    conferences: dict,
    games_per_team: int,
    team_prestige: dict = None,
    key_prefix: str = "nc",
    is_dynasty: bool = False,
):
    """Render a non-conference matchup picker for one or more user-controlled teams.

    Args:
        user_teams: List of team names the user controls.
        all_teams: Dict of team_name -> Team objects.
        conferences: Dict of conference_name -> [team_names].
        games_per_team: Total regular-season games per team.
        team_prestige: Optional prestige map (dynasty mode).
        key_prefix: Streamlit key prefix for unique widgets.
        is_dynasty: Whether this is dynasty mode (enables buy-game info).

    Returns:
        List of [home, away] pairs selected by the user.
    """
    if not user_teams:
        return []

    # Build team -> conference map
    team_conf_map = {}
    for conf_name, conf_teams in conferences.items():
        for t in conf_teams:
            team_conf_map[t] = conf_name

    st.divider()
    st.subheader("Non-Conference Schedule")
    st.caption(
        f"Conference games are capped at {MAX_CONFERENCE_GAMES} per team. "
        "Select your non-conference opponents below, then AI fills the rest when the season starts."
    )

    all_pinned = []

    for user_team in user_teams:
        my_conf = team_conf_map.get(user_team, "")
        my_conf_size = 0
        for conf_name, conf_teams in conferences.items():
            if user_team in conf_teams:
                my_conf_size = len(conf_teams)
                break

        nc_slots = get_non_conference_slots(games_per_team, my_conf_size)
        conf_games = min(my_conf_size - 1 if my_conf_size > 0 else 0, MAX_CONFERENCE_GAMES)

        if len(user_teams) > 1:
            st.markdown(f"**{user_team}**")

        info_col1, info_col2, info_col3 = st.columns(3)
        info_col1.metric("Conference Games", conf_games)
        info_col2.metric("Non-Conference Slots", nc_slots)
        info_col3.metric("Total Games", games_per_team)

        if nc_slots <= 0:
            st.info("No non-conference slots available with current settings.")
            continue

        # Get available opponents
        opponents = get_available_non_conference_opponents(
            team_name=user_team,
            all_teams=all_teams,
            conferences=conferences,
            team_conferences=team_conf_map,
            team_prestige=team_prestige,
        )

        if not opponents:
            st.info("No non-conference opponents available.")
            continue

        # Group by tier for display
        tier_groups = {}
        for opp in opponents:
            tier = opp["tier"]
            tier_groups.setdefault(tier, []).append(opp)

        # Show tier summary
        tier_summary = []
        for tier in ["elite", "strong", "mid", "low", "cupcake"]:
            if tier in tier_groups:
                tier_summary.append(f"{TIER_LABELS[tier]}: {len(tier_groups[tier])}")
        st.caption("Available opponents — " + " | ".join(tier_summary))

        # Initialize session state for this team's picks
        state_key = f"{key_prefix}_picks_{user_team}"
        if state_key not in st.session_state:
            st.session_state[state_key] = []

        current_picks = st.session_state[state_key]

        # Show current selections
        if current_picks:
            st.markdown("**Your Non-Conference Schedule:**")
            for i, pick in enumerate(current_picks):
                opp_data = next((o for o in opponents if o["name"] == pick), None)
                if opp_data:
                    tier_label = TIER_LABELS.get(opp_data["tier"], "")
                    buy_note = ""
                    if is_dynasty and team_prestige:
                        my_p = team_prestige.get(user_team, 50)
                        if is_buy_game(my_p, opp_data["prestige"]):
                            buy_note = f" — Buy Game (+${BUY_GAME_NIL_BONUS:,} NIL bonus)"
                    st.markdown(
                        f"  {i+1}. **{pick}** ({opp_data['conference']}) "
                        f"— {tier_label} (Prestige: {opp_data['prestige']}){buy_note}"
                    )

            if st.button("Clear All Selections", key=f"{key_prefix}_clear_{user_team}"):
                st.session_state[state_key] = []
                st.rerun()

        slots_remaining = nc_slots - len(current_picks)
        if slots_remaining > 0:
            st.markdown(f"**Select opponents** ({slots_remaining} slot{'s' if slots_remaining != 1 else ''} remaining)")

            # Tier filter
            tier_filter = st.selectbox(
                "Filter by tier",
                ["All Tiers"] + [TIER_LABELS[t] for t in ["elite", "strong", "mid", "low", "cupcake"] if t in tier_groups],
                key=f"{key_prefix}_tier_filter_{user_team}",
                help="Filter available opponents by program strength",
            )

            # Map filter back to tier key
            reverse_tier = {v: k for k, v in TIER_LABELS.items()}
            active_tier = reverse_tier.get(tier_filter, None) if tier_filter != "All Tiers" else None

            # Filter opponents
            filtered_opps = opponents
            if active_tier:
                filtered_opps = [o for o in opponents if o["tier"] == active_tier]
            # Exclude already picked
            filtered_opps = [o for o in filtered_opps if o["name"] not in current_picks]

            if filtered_opps:
                opp_options = [f"{o['name']} ({o['conference']}) — {TIER_LABELS[o['tier']]} (P:{o['prestige']})" for o in filtered_opps]
                selected_idx = st.selectbox(
                    "Choose opponent",
                    range(len(opp_options)),
                    format_func=lambda i: opp_options[i],
                    key=f"{key_prefix}_opp_select_{user_team}",
                )
                selected_opp = filtered_opps[selected_idx]

                # Show info about selected opponent
                if is_dynasty and team_prestige:
                    my_p = team_prestige.get(user_team, 50)
                    if is_buy_game(my_p, selected_opp["prestige"]):
                        st.info(
                            f"This is a **buy game** — playing at {selected_opp['name']} "
                            f"(prestige {selected_opp['prestige']}) earns your program "
                            f"+${BUY_GAME_NIL_BONUS:,} NIL pool bonus."
                        )

                add_col, home_col = st.columns(2)
                with home_col:
                    home_away = st.radio(
                        "Home/Away",
                        ["Home", "Away"],
                        horizontal=True,
                        key=f"{key_prefix}_ha_{user_team}",
                    )
                with add_col:
                    if st.button(
                        f"Add {selected_opp['name']}",
                        type="primary",
                        key=f"{key_prefix}_add_{user_team}",
                    ):
                        st.session_state[state_key].append(selected_opp["name"])
                        pair = [user_team, selected_opp["name"]] if home_away == "Home" else [selected_opp["name"], user_team]
                        # Store the home/away pairing in a separate state key
                        pairs_key = f"{key_prefix}_pairs_{user_team}"
                        if pairs_key not in st.session_state:
                            st.session_state[pairs_key] = []
                        st.session_state[pairs_key].append(pair)
                        st.rerun()
            else:
                st.caption("No more opponents available in this tier.")
        elif slots_remaining == 0:
            st.success(f"All {nc_slots} non-conference slots filled!")

        # Build final matchup list from stored pairs
        pairs_key = f"{key_prefix}_pairs_{user_team}"
        if pairs_key in st.session_state:
            all_pinned.extend(st.session_state[pairs_key])

    return all_pinned


CONFERENCE_TIERS = {
    "Giant 14": 85,
    "Big Pacific": 80,
    "Collegiate Commonwealth": 78,
    "Interstate Athletic Association": 75,
    "Southern Sun Conference": 73,
    "Yankee Fourteen": 70,
    "Potomac Athletic Conference": 67,
    "Metropolitan Athletic Union": 65,
    "Midwest States Interscholastic Association": 62,
    "Northern Shield": 58,
    "Pioneer Athletic Association": 55,
    "Outlands Coast Conference": 52,
    "Prairie Athletic Union": 50,
    "Border Conference": 48,
    "Moonshine League": 45,
    "National Collegiate League": 42,
}

PRESTIGE_LABELS = {
    (80, 100): "Elite",
    (65, 79): "Strong",
    (50, 64): "Mid-Tier",
    (35, 49): "Developing",
    (0, 34): "Rebuilding",
}


def _get_team_prestige(team: dict) -> int:
    import hashlib
    conf = team.get("conference", "Independent")
    base = CONFERENCE_TIERS.get(conf, 50)
    name_bytes = team.get("name", "").encode("utf-8")
    name_hash = int(hashlib.md5(name_bytes).hexdigest(), 16) % 21 - 10
    return max(10, min(99, base + name_hash))


def _get_prestige_label(prestige: int) -> str:
    for (lo, hi), label in PRESTIGE_LABELS.items():
        if lo <= prestige <= hi:
            return label
    return "Unknown"


def _format_team_option(team: dict, show_conference: bool = True) -> str:
    name = team.get("name", team.get("key", "Unknown"))
    prestige = _get_team_prestige(team)
    plabel = _get_prestige_label(prestige)
    if show_conference:
        conf = team.get("conference", "")
        return f"{name} ({conf}) — {plabel} [{prestige}]"
    return f"{name} — {plabel} [{prestige}]"


def _build_conference_team_map(teams):
    conf_map = {}
    for t in teams:
        conf = t.get("conference", "Independent")
        conf_map.setdefault(conf, []).append(t)
    for conf in conf_map:
        conf_map[conf].sort(key=lambda x: x["name"])
    return conf_map


def _render_team_picker_single(
    teams: list,
    label: str = "Your Team",
    key_prefix: str = "tp",
    default_team: str = None,
):
    conf_map = _build_conference_team_map(teams)
    conf_names = sorted(conf_map.keys())
    conf_options = ["All Conferences"] + conf_names

    filter_col, team_col = st.columns([1, 2])
    with filter_col:
        conf_filter = st.selectbox(
            "Filter by Conference",
            conf_options,
            key=f"{key_prefix}_conf_filter",
        )
    if conf_filter == "All Conferences":
        filtered_teams = sorted(teams, key=lambda t: t["name"])
    else:
        filtered_teams = conf_map.get(conf_filter, [])

    team_options = [t["name"] for t in filtered_teams]
    if not team_options:
        st.warning("No teams in this conference.")
        return teams[0]["name"] if teams else ""

    default_idx = 0
    if default_team and default_team in team_options:
        default_idx = team_options.index(default_team)

    with team_col:
        team_lookup = {t["name"]: t for t in filtered_teams}
        selected = st.selectbox(
            label,
            team_options,
            index=default_idx,
            format_func=lambda x: _format_team_option(team_lookup.get(x, {}), conf_filter == "All Conferences"),
            key=f"{key_prefix}_team_select",
        )
    return selected


def _render_team_picker_multi(
    teams: list,
    label: str = "Your Teams",
    key_prefix: str = "tp_multi",
    max_selections: int = 4,
    help_text: str = "",
):
    conf_map = _build_conference_team_map(teams)
    conf_names = sorted(conf_map.keys())

    st.caption(f"{len(teams)} teams across {len(conf_names)} conferences")

    browse_mode = st.radio(
        "Browse teams by",
        ["Conference", "All Teams (A-Z)"],
        horizontal=True,
        key=f"{key_prefix}_browse_mode",
    )

    picks_key = f"{key_prefix}_picks"
    if picks_key not in st.session_state:
        st.session_state[picks_key] = []
    current_picks = st.session_state[picks_key]

    if current_picks:
        conf_labels_map = {t["name"]: t.get("conference", "") for t in teams}
        pick_display = ", ".join([f"**{p}** ({conf_labels_map.get(p, '')})" for p in current_picks])
        st.markdown(f"Selected ({len(current_picks)}/{max_selections}): {pick_display}")
        if st.button("Clear All", key=f"{key_prefix}_clear"):
            st.session_state[picks_key] = []
            st.rerun()

    if len(current_picks) >= max_selections:
        st.info(f"Maximum {max_selections} teams selected.")
        return current_picks

    if browse_mode == "Conference":
        conf_filter = st.selectbox(
            "Select Conference",
            conf_names,
            key=f"{key_prefix}_conf_filter",
        )
        available = [t["name"] for t in conf_map.get(conf_filter, []) if t["name"] not in current_picks]
    else:
        available = sorted([t["name"] for t in teams if t["name"] not in current_picks])

    if available:
        add_col1, add_col2 = st.columns([3, 1])
        with add_col1:
            team_lookup = {t["name"]: t for t in teams}
            selected = st.selectbox(
                f"Add team ({len(available)} available)",
                available,
                format_func=lambda x: _format_team_option(team_lookup.get(x, {}), browse_mode != "Conference"),
                key=f"{key_prefix}_add_select",
            )
        with add_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Add", type="primary", key=f"{key_prefix}_add_btn", use_container_width=True):
                st.session_state[picks_key].append(selected)
                st.rerun()
    else:
        st.caption("No more teams available to add.")

    return current_picks


def _render_team_picker_quick(
    teams: list,
    label: str = "Select Team",
    key_prefix: str = "tp_quick",
    default_idx: int = 0,
):
    conf_map = _build_conference_team_map(teams)
    conf_names = sorted(conf_map.keys())
    conf_options = ["All Conferences"] + conf_names

    conf_filter = st.selectbox(
        "Conference",
        conf_options,
        key=f"{key_prefix}_conf_filter",
    )
    if conf_filter == "All Conferences":
        filtered_teams = sorted(teams, key=lambda t: t["name"])
    else:
        filtered_teams = conf_map.get(conf_filter, [])

    if not filtered_teams:
        st.warning("No teams in this conference.")
        return teams[default_idx]["key"] if teams else ""

    keys = [t["key"] for t in filtered_teams]
    team_by_key = {t["key"]: t for t in filtered_teams}

    sel_idx = min(default_idx, len(keys) - 1)
    selected_key = st.selectbox(
        label,
        keys,
        index=sel_idx,
        format_func=lambda k: _format_team_option(team_by_key.get(k, {}), conf_filter == "All Conferences"),
        key=f"{key_prefix}_team_select",
    )
    return selected_key


def _render_rivalry_picker(
    user_teams: list,
    all_teams: dict,
    conferences: dict,
    key_prefix: str = "rivalry",
):
    if not user_teams:
        return {}

    team_conf_map = {}
    for conf_name, conf_teams in conferences.items():
        for t in conf_teams:
            team_conf_map[t] = conf_name

    st.divider()
    st.subheader("Rivalries")
    st.caption(
        "Set a conference rival and a non-conference rival for each of your teams. "
        "Rivalry games are guaranteed every season, and both teams get intensity boosts during the matchup."
    )

    rivalries = {}
    for user_team in user_teams:
        my_conf = team_conf_map.get(user_team, "")
        conf_mates = sorted([
            t for t in (conferences.get(my_conf, []) if my_conf else [])
            if t != user_team
        ])
        non_conf_teams = sorted([
            t for t in all_teams.keys()
            if t != user_team and team_conf_map.get(t, "") != my_conf
        ])

        if len(user_teams) > 1:
            st.markdown(f"**{user_team}**")

        r_col1, r_col2 = st.columns(2)
        with r_col1:
            conf_rival_options = ["None (auto-assign)"] + conf_mates
            conf_rival_idx = st.selectbox(
                f"Conference Rival" if len(user_teams) == 1 else "Conference Rival",
                range(len(conf_rival_options)),
                format_func=lambda i, opts=conf_rival_options: opts[i],
                key=f"{key_prefix}_conf_{user_team}",
                help="Plays this team every year within your conference",
            )
            conf_rival = conf_rival_options[conf_rival_idx] if conf_rival_idx > 0 else None
        with r_col2:
            nc_rival_options = ["None (auto-assign)"] + non_conf_teams
            nc_rival_idx = st.selectbox(
                f"Non-Conference Rival" if len(user_teams) == 1 else "Non-Conf Rival",
                range(len(nc_rival_options)),
                format_func=lambda i, opts=nc_rival_options: opts[i],
                key=f"{key_prefix}_nc_{user_team}",
                help="Plays this team every year as a guaranteed non-conference game",
            )
            nc_rival = nc_rival_options[nc_rival_idx] if nc_rival_idx > 0 else None

        rivalries[user_team] = {
            "conference": conf_rival,
            "non_conference": nc_rival,
        }

    return rivalries


def render_play_section(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]
    OFFENSE_TOOLTIPS = shared["OFFENSE_TOOLTIPS"]
    DEFENSE_TOOLTIPS = shared["DEFENSE_TOOLTIPS"]

    mode = _get_active_session()

    if mode == "dynasty":
        _render_dynasty_play(shared)
    elif mode == "season":
        _render_season_play(shared)
    else:
        _render_mode_selection(shared)


def _render_mode_selection(shared):
    st.title("Play")
    st.caption("Start a new dynasty, season, or play a quick exhibition game")

    play_tabs = st.tabs(["New Dynasty", "New Season", "Quick Game"])

    with play_tabs[0]:
        _render_new_dynasty(shared)

    with play_tabs[1]:
        _render_new_season(shared)

    with play_tabs[2]:
        _render_quick_game(shared)


def _render_new_dynasty(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]

    st.subheader("Create New Dynasty")
    st.caption("Multi-season career mode with historical tracking, awards, and record books")

    dynasty_col1, dynasty_col2 = st.columns(2)
    with dynasty_col1:
        dynasty_name = st.text_input("Dynasty Name", value="My Viperball Dynasty", key="dyn_name")
    with dynasty_col2:
        coach_name = st.text_input("Coach Name", value="Coach", key="coach_name")

    st.markdown("**Choose Your Team**")
    coach_team = _render_team_picker_single(teams, label="Your Team", key_prefix="dyn_team")

    start_year = st.number_input("Starting Year", min_value=1906, max_value=2050, value=2026, key="start_year")

    st.divider()
    st.subheader("Program Archetype")
    st.caption("Choose your starting program level. This determines your roster talent and affects the challenge.")
    arch_keys = list(PROGRAM_ARCHETYPES.keys())
    arch_labels = [PROGRAM_ARCHETYPES[k]["label"] for k in arch_keys]
    arch_descs = [PROGRAM_ARCHETYPES[k]["description"] for k in arch_keys]
    default_arch_idx = arch_keys.index("regional_power")
    selected_arch_idx = st.radio(
        "Program Level",
        range(len(arch_keys)),
        index=default_arch_idx,
        format_func=lambda i: f"{arch_labels[i]}",
        key="dyn_program_archetype",
        horizontal=True,
    )
    st.caption(arch_descs[selected_arch_idx])
    dyn_archetype = arch_keys[selected_arch_idx]

    st.divider()
    st.subheader("Conference Setup")
    teams_dir = _teams_dir()
    setup_teams = load_teams_from_directory(teams_dir)
    all_team_names_sorted = sorted(setup_teams.keys())

    total_teams = len(all_team_names_sorted)
    max_conf = max(1, total_teams // 9)
    conf_options = list(range(1, min(max_conf + 1, 13)))
    default_idx = min(len(conf_options) - 1, max(0, total_teams // 12 - 1))
    num_conferences = st.select_slider(
        f"Number of Conferences ({total_teams} teams available)",
        options=conf_options,
        value=conf_options[default_idx],
        key="num_conf",
    )
    teams_per = total_teams // max(1, num_conferences)
    remainder = total_teams % max(1, num_conferences)
    size_note = f"~{teams_per} teams per conference" if remainder == 0 else f"~{teams_per}-{teams_per+1} teams per conference"
    st.caption(size_note)

    if "conf_name_seed" not in st.session_state:
        st.session_state["conf_name_seed"] = random.randint(0, 999999)

    if st.session_state.get("use_geo_names", True):
        geo_clusters = get_geographic_conference_defaults(teams_dir, all_team_names_sorted, num_conferences)
        generated_names = list(geo_clusters.keys())
        if len(generated_names) < num_conferences:
            generated_names.extend(generate_conference_names(count=num_conferences - len(generated_names), seed=st.session_state["conf_name_seed"]))
    else:
        generated_names = generate_conference_names(count=num_conferences, seed=st.session_state["conf_name_seed"])

    conf_assignments = {}
    conf_names_list = []

    name_col, btn_col = st.columns([5, 1])
    with btn_col:
        if st.button("🎲 New Names", key="regen_conf_names", use_container_width=True):
            st.session_state["conf_name_seed"] = random.randint(0, 999999)
            st.session_state["use_geo_names"] = False
            for ci2 in range(20):
                st.session_state.pop(f"conf_name_{ci2}", None)
            st.rerun()

    if num_conferences == 1:
        with name_col:
            conf_name_single = st.text_input("Conference Name", value=generated_names[0], key="conf_name_0")
        conf_names_list = [conf_name_single]
        for tname in all_team_names_sorted:
            conf_assignments[tname] = conf_name_single
    else:
        cols_per_row = min(num_conferences, 4)
        for row_start in range(0, num_conferences, cols_per_row):
            row_end = min(row_start + cols_per_row, num_conferences)
            conf_cols = st.columns(row_end - row_start)
            for ci_offset, ci in enumerate(range(row_start, row_end)):
                with conf_cols[ci_offset]:
                    cname = st.text_input(f"Conference {ci+1}", value=generated_names[ci], key=f"conf_name_{ci}")
                    conf_names_list.append(cname)

        geo_clusters = get_geographic_conference_defaults(teams_dir, all_team_names_sorted, num_conferences)
        geo_cluster_list = list(geo_clusters.values())
        default_splits = {}
        for ci in range(num_conferences):
            if ci < len(geo_cluster_list):
                for tname in geo_cluster_list[ci]:
                    default_splits[tname] = conf_names_list[ci]
        for tname in all_team_names_sorted:
            if tname not in default_splits:
                default_splits[tname] = conf_names_list[-1]

        with st.expander("Assign Teams to Conferences", expanded=False):
            assign_cols_per_row = 4
            assign_chunks = [all_team_names_sorted[i:i+assign_cols_per_row]
                             for i in range(0, len(all_team_names_sorted), assign_cols_per_row)]
            for achunk in assign_chunks:
                acols = st.columns(len(achunk))
                for acol, tname in zip(acols, achunk):
                    with acol:
                        didx = conf_names_list.index(default_splits.get(tname, conf_names_list[0]))
                        assigned = st.selectbox(tname[:20], conf_names_list, index=didx,
                                                 key=f"conf_assign_{tname}")
                        conf_assignments[tname] = assigned

    st.divider()
    st.subheader("League History")
    st.caption("Generate past seasons so your dynasty has an established history with champions, records, and rivalries.")
    history_col1, history_col2 = st.columns(2)
    with history_col1:
        history_years = st.slider("Years of History to Simulate", min_value=0, max_value=100, value=0, key="history_years",
                                   help="0 = start fresh with no history. Higher values take longer to generate.")
    with history_col2:
        history_games = st.slider("Games Per Team (History Seasons)", min_value=8, max_value=12, value=10, key="history_games")

    dyn_rivalries = {}
    if conf_assignments:
        dyn_conf_map = {}
        for tname, cname in conf_assignments.items():
            dyn_conf_map.setdefault(cname, []).append(tname)
        dyn_rivalries = _render_rivalry_picker(
            user_teams=[coach_team],
            all_teams=setup_teams,
            conferences=dyn_conf_map,
            key_prefix="dyn_rivalry",
        )

    st.divider()
    load_col1, load_col2 = st.columns(2)
    with load_col1:
        create_btn = st.button("Create Dynasty", type="primary", use_container_width=True, key="create_dynasty")
    with load_col2:
        uploaded = st.file_uploader("Load Saved Dynasty", type=["json"], key="load_dynasty")

    if create_btn:
        session_id = _ensure_session_id()
        with st.spinner("Creating dynasty..."):
            try:
                api_client.create_dynasty(
                    session_id,
                    dynasty_name=dynasty_name,
                    coach_name=coach_name,
                    coach_team=coach_team,
                    starting_year=start_year,
                    num_conferences=num_conferences,
                    history_years=history_years,
                    program_archetype=dyn_archetype,
                    rivalries=dyn_rivalries if dyn_rivalries else {},
                )
                st.session_state["api_mode"] = "dynasty"
                st.session_state["dyn_program_archetype_selected"] = dyn_archetype
                st.rerun()
            except api_client.APIError as e:
                st.error(f"Failed to create dynasty: {e.detail}")

    if uploaded:
        st.warning("Dynasty save file loading is not yet supported through the API. This feature is coming soon.")


def _render_new_season(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]

    st.subheader("New Season")
    st.caption(f"Simulate a full season with all {len(teams)} teams, standings, and playoffs")

    teams_dir = _teams_dir()
    all_teams = load_teams_from_directory(teams_dir)
    all_team_names = sorted(all_teams.keys())

    season_name = st.text_input("Season Name", value="2026 CVL Season", key="season_name")

    if len(all_team_names) < 2:
        st.warning("Not enough teams loaded to run a season.")
        return

    st.markdown("**Your Teams** (human-coached, up to 4)")
    human_teams = _render_team_picker_multi(
        teams,
        label="Your Teams",
        key_prefix="season_human",
        max_selections=4,
        help_text="Pick up to 4 teams to coach yourself. Everyone else is AI-controlled.",
    )

    if "season_ai_seed" not in st.session_state:
        st.session_state["season_ai_seed"] = 0

    def _reroll_season_ai():
        st.session_state["season_ai_seed"] = random.randint(1, 999999)

    ai_seed_col, reroll_col = st.columns([3, 1])
    with ai_seed_col:
        ai_seed = st.number_input("AI Coaching Seed (0 = random)", min_value=0, max_value=999999, key="season_ai_seed")
    with reroll_col:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("Re-roll AI", key="reroll_ai_season", on_click=_reroll_season_ai)

    actual_seed = ai_seed if ai_seed > 0 else hash(season_name) % 999999

    teams_dir_path = _teams_dir()
    team_identities = load_team_identity(teams_dir_path)

    style_configs = {}
    season_team_archetypes = {}

    if human_teams:
        st.subheader("Your Team Configuration")

        # Program archetype selection for each human team
        arch_keys = list(PROGRAM_ARCHETYPES.keys())
        arch_labels = [PROGRAM_ARCHETYPES[k]["label"] for k in arch_keys]
        default_arch_idx = arch_keys.index("regional_power")

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

                    sel_arch = st.selectbox(
                        "Program Level",
                        range(len(arch_keys)),
                        index=default_arch_idx,
                        format_func=lambda i: f"{arch_labels[i]} — {PROGRAM_ARCHETYPES[arch_keys[i]]['description'][:50]}...",
                        key=f"season_arch_{tname}",
                    )
                    season_team_archetypes[tname] = arch_keys[sel_arch]

                    off_style = st.selectbox("Offense", style_keys,
                                              format_func=lambda x: styles[x]["label"],
                                              key=f"season_off_{tname}")
                    def_style = st.selectbox("Defense", defense_style_keys,
                                              format_func=lambda x: defense_styles[x]["label"],
                                              key=f"season_def_{tname}")
                    style_configs[tname] = {"offense_style": off_style, "defense_style": def_style}

    ai_teams = [t for t in all_team_names if t not in human_teams]
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

    for tname in all_team_names:
        if tname not in style_configs:
            style_configs[tname] = {"offense_style": "balanced", "defense_style": "base_defense"}

    auto_conferences = {}
    for tname in all_team_names:
        identity = team_identities.get(tname, {})
        conf = identity.get("conference", "")
        if conf:
            auto_conferences.setdefault(conf, []).append(tname)
    auto_conferences = {k: v for k, v in auto_conferences.items() if len(v) >= 2}

    if auto_conferences:
        with st.expander("Conference Names", expanded=False):
            st.caption("Edit conference names or click the button to generate new ones.")

            if "season_conf_seed" not in st.session_state:
                st.session_state["season_conf_seed"] = None

            orig_conf_names = sorted(auto_conferences.keys())

            if st.session_state["season_conf_seed"] is not None:
                gen_names = generate_conference_names(
                    count=len(orig_conf_names),
                    seed=st.session_state["season_conf_seed"],
                )
            else:
                gen_names = list(orig_conf_names)

            regen_col, _ = st.columns([1, 5])
            with regen_col:
                if st.button("🎲 New Names", key="regen_season_conf"):
                    st.session_state["season_conf_seed"] = random.randint(0, 999999)
                    for ci2 in range(len(orig_conf_names)):
                        st.session_state.pop(f"season_conf_{ci2}", None)
                    st.rerun()

            conf_rename_map = {}
            conf_cols = st.columns(min(len(orig_conf_names), 4))
            for ci, old_name in enumerate(orig_conf_names):
                with conf_cols[ci % len(conf_cols)]:
                    new_name = st.text_input(
                        old_name, value=gen_names[ci], key=f"season_conf_{ci}"
                    )
                    conf_rename_map[old_name] = new_name

            renamed_conferences = {}
            for old_name, team_list in auto_conferences.items():
                new_name = conf_rename_map.get(old_name, old_name)
                renamed_conferences[new_name] = team_list
            auto_conferences = renamed_conferences

    sched_col1, sched_col2 = st.columns(2)
    with sched_col1:
        season_games = st.slider("Regular Season Games Per Team", min_value=8, max_value=12, value=10, key="season_games_per_team")
    with sched_col2:
        playoff_options = [p for p in [4, 8, 12, 16, 24, 32] if p <= len(all_team_names)]
        if not playoff_options:
            playoff_options = [len(all_team_names)]
        playoff_size = st.radio("Playoff Format", playoff_options, index=0, key="playoff_size", horizontal=True)

    rec_bowls = get_recommended_bowl_count(len(all_team_names), playoff_size)
    bowl_count = st.slider("Number of Bowl Games", min_value=0, max_value=min(12, (len(all_team_names) - playoff_size) // 2), value=rec_bowls, key="season_bowl_count")

    # Non-conference scheduling for human-controlled teams
    season_pinned = []
    if human_teams and auto_conferences:
        season_pinned = _render_non_conference_picker(
            user_teams=human_teams,
            all_teams=all_teams,
            conferences=auto_conferences,
            games_per_team=season_games,
            key_prefix="season_nc",
            is_dynasty=False,
        )

    season_rivalries = {}
    if human_teams and auto_conferences:
        season_rivalries = _render_rivalry_picker(
            user_teams=human_teams,
            all_teams=all_teams,
            conferences=auto_conferences,
            key_prefix="season_rivalry",
        )

    st.divider()
    start_season = st.button("Start Season", type="primary", use_container_width=True, key="run_season")

    if start_season:
        session_id = _ensure_session_id()
        with st.spinner("Creating season..."):
            try:
                api_client.create_season(
                    session_id,
                    name=season_name,
                    games_per_team=season_games,
                    playoff_size=playoff_size,
                    bowl_count=bowl_count,
                    human_teams=human_teams,
                    conferences=auto_conferences if auto_conferences else None,
                    style_configs=style_configs,
                    ai_seed=actual_seed,
                    pinned_matchups=season_pinned if season_pinned else None,
                    team_archetypes=season_team_archetypes if season_team_archetypes else None,
                    rivalries=season_rivalries if season_rivalries else {},
                )
                st.session_state["api_mode"] = "season"
                st.session_state["season_human_teams_list"] = human_teams
                st.rerun()
            except api_client.APIError as e:
                st.error(f"Failed to create season: {e.detail}")


def _render_offseason_flow(session_id, coach_team, current_year):
    try:
        off_status = api_client.get_offseason_status(session_id)
    except api_client.APIError as e:
        st.error(f"Could not load offseason data: {e.detail}")
        return

    off_phase = off_status.get("phase", "nil")

    phase_labels = {
        "nil": "1. NIL Budget Allocation",
        "portal": "2. Transfer Portal",
        "recruiting": "3. Recruiting",
        "ready": "4. Finalize Offseason",
    }
    current_label = phase_labels.get(off_phase, off_phase)

    st.subheader(f"Offseason — Year {current_year}")

    phase_order = ["nil", "portal", "recruiting", "ready"]
    current_idx = phase_order.index(off_phase) if off_phase in phase_order else 0
    progress = (current_idx + 1) / len(phase_order)
    st.progress(progress, text=f"Phase: {current_label}")

    if off_phase == "nil":
        _render_offseason_nil(session_id, off_status)
    elif off_phase == "portal":
        _render_offseason_portal(session_id, coach_team)
    elif off_phase == "recruiting":
        _render_offseason_recruiting(session_id, coach_team)
    elif off_phase == "ready":
        _render_offseason_finalize(session_id, current_year)


def _render_offseason_nil(session_id, off_status):
    st.markdown("### NIL Budget Allocation")
    st.caption("Allocate your NIL budget across recruiting, transfer portal, and player retention.")

    try:
        nil_data = api_client.get_offseason_nil(session_id)
    except api_client.APIError:
        st.warning("Could not load NIL data.")
        return

    budget = nil_data.get("annual_budget", 0)

    bm1, bm2, bm3 = st.columns(3)
    bm1.metric("Annual Budget", f"${budget:,.0f}")
    bm2.metric("Retention Risks", off_status.get("retention_risks_count", 0))
    bm3.metric("Portal Players", off_status.get("portal_count", 0))

    st.markdown("**Set Pool Allocations**")
    st.caption("Split your budget between recruiting new high school players, transfer portal acquisitions, and retaining current roster players.")

    default_recruit = int(budget * 0.50)
    default_portal = int(budget * 0.30)
    default_retain = budget - default_recruit - default_portal

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        recruit_pool = st.number_input(
            "Recruiting Pool ($)",
            min_value=0, max_value=budget, value=default_recruit,
            step=10000, key="nil_recruit_pool",
        )
    with rc2:
        portal_pool = st.number_input(
            "Portal Pool ($)",
            min_value=0, max_value=budget, value=default_portal,
            step=10000, key="nil_portal_pool",
        )
    with rc3:
        retain_pool = st.number_input(
            "Retention Pool ($)",
            min_value=0, max_value=budget, value=default_retain,
            step=10000, key="nil_retain_pool",
        )

    total_alloc = recruit_pool + portal_pool + retain_pool
    remaining = budget - total_alloc

    am1, am2 = st.columns(2)
    am1.metric("Total Allocated", f"${total_alloc:,.0f}")
    if remaining >= 0:
        am2.metric("Remaining", f"${remaining:,.0f}")
    else:
        am2.metric("Over Budget", f"${abs(remaining):,.0f}", delta=f"-${abs(remaining):,.0f}", delta_color="inverse")

    if total_alloc > budget:
        st.error(f"Total allocation (${total_alloc:,.0f}) exceeds budget (${budget:,.0f}). Reduce allocations.")
    else:
        if st.button("Confirm NIL Allocation & Continue to Portal", type="primary", use_container_width=True, key="nil_confirm"):
            with st.spinner("Allocating NIL budget..."):
                try:
                    api_client.offseason_nil_allocate(session_id, recruit_pool, portal_pool, retain_pool)
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Allocation failed: {e.detail}")


def _render_offseason_portal(session_id, coach_team):
    st.markdown("### Transfer Portal")
    st.caption("Browse available transfer players, make offers, and commit players to your roster.")

    pf1, pf2 = st.columns(2)
    with pf1:
        pos_filter = st.selectbox("Position Filter", ["All", "VP", "HB", "WB", "SB", "ZB", "LB", "CB", "LA", "LM"], key="portal_pos")
    with pf2:
        ovr_filter = st.number_input("Min Overall", min_value=0, max_value=99, value=0, key="portal_min_ovr")

    pos_param = pos_filter if pos_filter != "All" else None
    ovr_param = ovr_filter if ovr_filter > 0 else None

    try:
        portal_resp = api_client.get_offseason_portal(session_id, position=pos_param, min_overall=ovr_param)
        entries = portal_resp.get("entries", [])
        total = portal_resp.get("total_entries", 0)
        available = portal_resp.get("total_available", 0)
    except api_client.APIError as e:
        st.warning(f"Could not load portal: {e.detail}")
        return

    pm1, pm2 = st.columns(2)
    pm1.metric("Total Portal Entries", total)
    pm2.metric("Available", available)

    if entries:
        portal_data = []
        for i, e in enumerate(entries):
            portal_data.append({
                "idx": i,
                "Name": e.get("name", ""),
                "Position": e.get("position", ""),
                "OVR": e.get("overall", 0),
                "Year": e.get("year", ""),
                "From": e.get("origin_team", ""),
                "Reason": e.get("reason", "").replace("_", " ").title(),
                "Stars": e.get("potential", 0),
                "Offers": e.get("offers_count", 0),
            })

        st.dataframe(
            pd.DataFrame(portal_data).drop(columns=["idx"]),
            hide_index=True, use_container_width=True, height=350,
        )

        st.markdown("**Make an Offer / Commit**")
        player_options = [f"{e['Name']} ({e['Position']}, OVR {e['OVR']}) — from {e['From']}" for e in portal_data]
        selected_idx = st.selectbox("Select Player", range(len(player_options)), format_func=lambda i: player_options[i], key="portal_select")

        selected_entry = entries[selected_idx]
        global_idx = selected_entry.get("global_index", -1)

        if global_idx < 0:
            st.warning("Cannot interact with this player — index unavailable. Try refreshing.")
        else:
            oc1, oc2 = st.columns(2)
            with oc1:
                nil_offer = st.number_input("NIL Offer ($)", min_value=0, max_value=500000, value=25000, step=5000, key="portal_nil_offer")
                if st.button("Make Offer", use_container_width=True, key="portal_offer_btn"):
                    try:
                        api_client.offseason_portal_offer(session_id, entry_index=global_idx, nil_amount=nil_offer)
                        st.success(f"Offer sent to {selected_entry['name']}")
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Offer failed: {e.detail}")

            with oc2:
                st.caption("Instantly commit (bypasses decision sim)")
                if st.button("Commit Player", type="primary", use_container_width=True, key="portal_commit_btn"):
                    try:
                        api_client.offseason_portal_commit(session_id, entry_index=global_idx)
                        st.success(f"Committed {selected_entry['name']} to {coach_team}!")
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Commit failed: {e.detail}")
    else:
        st.info("No available portal players matching your filters.")

    st.divider()
    if st.button("Resolve Portal & Continue to Recruiting", type="primary", use_container_width=True, key="portal_resolve"):
        with st.spinner("Resolving transfer portal (AI teams making decisions)..."):
            try:
                result = api_client.offseason_portal_resolve(session_id)
                total_transfers = result.get("total_transfers", 0)
                human_transfers = result.get("human_transfers", [])
                st.success(f"Portal resolved! {total_transfers} total transfers completed.")
                if human_transfers:
                    st.markdown(f"**Your incoming transfers ({len(human_transfers)}):**")
                    for t in human_transfers:
                        st.markdown(f"- {t.get('name', '')} ({t.get('position', '')}, OVR {t.get('overall', 0)})")
                st.rerun()
            except api_client.APIError as e:
                st.error(f"Portal resolution failed: {e.detail}")



def _render_offseason_recruiting(session_id, coach_team):
    st.markdown("### Recruiting")
    st.caption("Scout, evaluate, and offer scholarships to high school recruits.")

    try:
        rec_resp = api_client.get_offseason_recruiting(session_id)
        recruits = rec_resp.get("recruits", [])
        total_pool = rec_resp.get("total_pool", 0)
        board = rec_resp.get("board", {})
    except api_client.APIError as e:
        st.warning(f"Could not load recruiting: {e.detail}")
        return

    bm1, bm2, bm3, bm4 = st.columns(4)
    bm1.metric("Recruit Pool", total_pool)
    bm2.metric("Available", len(recruits))
    if board:
        bm3.metric("Scholarships", board.get("scholarships_available", 0))
        bm4.metric("Scouting Pts", board.get("scouting_points", 0))

    rf1, rf2 = st.columns(2)
    with rf1:
        star_filter = st.selectbox("Min Stars", [0, 1, 2, 3, 4, 5], index=0, key="rec_star_filter")
    with rf2:
        pos_filter = st.selectbox("Position", ["All", "VP", "HB", "WB", "SB", "ZB", "LB", "CB", "LA", "LM"], key="rec_pos_filter")

    filtered = recruits
    if star_filter > 0:
        filtered = [r for r in filtered if r.get("stars", 0) >= star_filter]
    if pos_filter != "All":
        filtered = [r for r in filtered if r.get("position", "") == pos_filter]

    if filtered:
        rec_data = []
        for r in filtered[:50]:
            scouted = r.get("scouted", {})
            row = {
                "Name": r.get("name", ""),
                "Position": r.get("position", ""),
                "Stars": "+" * r.get("stars", 0),
                "Region": r.get("region", "").replace("_", " ").title(),
                "Hometown": r.get("hometown", ""),
                "HS": r.get("high_school", ""),
            }
            if scouted:
                row["SPD"] = scouted.get("speed", "?")
                row["AGI"] = scouted.get("agility", "?")
                row["PWR"] = scouted.get("power", "?")
                row["HND"] = scouted.get("hands", "?")
            if "true_overall" in r:
                row["OVR"] = r["true_overall"]
            if "potential" in r:
                row["Pot"] = r["potential"]
            elif "potential_range" in r:
                row["Pot"] = r["potential_range"]
            rec_data.append(row)

        st.dataframe(pd.DataFrame(rec_data), hide_index=True, use_container_width=True, height=400)

        st.markdown("**Scout / Offer a Recruit**")
        recruit_options = [f"{r.get('name', '')} ({r.get('position', '')}, {'+'*r.get('stars',0)})" for r in filtered[:50]]
        sel_rec_idx = st.selectbox("Select Recruit", range(len(recruit_options)), format_func=lambda i: recruit_options[i], key="rec_select")

        sel_recruit = filtered[sel_rec_idx]
        pool_idx = sel_recruit.get("pool_index", 0)

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            scout_level = st.selectbox("Scout Level", ["basic", "full"], key="rec_scout_level")
            if st.button("Scout", use_container_width=True, key="rec_scout_btn"):
                try:
                    result = api_client.offseason_recruiting_scout(session_id, recruit_index=pool_idx, level=scout_level)
                    pts_left = result.get("scouting_points_remaining", 0)
                    st.success(f"Scouted! ({pts_left} scouting pts remaining)")
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Scouting failed: {e.detail}")
        with sc2:
            if st.button("Offer Scholarship", type="primary", use_container_width=True, key="rec_offer_btn"):
                try:
                    result = api_client.offseason_recruiting_offer(session_id, recruit_index=pool_idx)
                    offers_made = result.get("offers_made", 0)
                    max_offers = result.get("max_offers", 0)
                    st.success(f"Offered! ({offers_made}/{max_offers} offers used)")
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Offer failed: {e.detail}")
        with sc3:
            pass

        if board and board.get("offered"):
            st.markdown("**Your Offer Board**")
            offer_data = []
            for offered_id in board.get("offered", []):
                for r in recruits:
                    if r.get("name", "") in offered_id or offered_id in r.get("name", ""):
                        offer_data.append({
                            "Name": r.get("name", ""),
                            "Position": r.get("position", ""),
                            "Stars": "+" * r.get("stars", 0),
                        })
                        break
            if offer_data:
                st.dataframe(pd.DataFrame(offer_data), hide_index=True, use_container_width=True)
    else:
        st.info("No recruits match your filters.")

    st.divider()
    if st.button("Run Signing Day & Continue", type="primary", use_container_width=True, key="rec_resolve"):
        with st.spinner("Simulating signing day (all teams making decisions)..."):
            try:
                result = api_client.offseason_recruiting_resolve(session_id)
                human_signed = result.get("human_signed", [])
                total_signed = result.get("total_signed", 0)
                st.success(f"Signing day complete! {total_signed} total recruits signed.")
                if human_signed:
                    st.markdown(f"**Your signing class ({len(human_signed)}):**")
                    for r in human_signed:
                        st.markdown(f"- {r.get('name', '')} ({r.get('position', '')}, {'+'*r.get('stars',0)})")
                st.rerun()
            except api_client.APIError as e:
                st.error(f"Signing day failed: {e.detail}")



def _render_offseason_finalize(session_id, current_year):
    st.markdown("### Offseason Complete")
    st.success("All offseason phases are done! Your roster has been updated with portal transfers and incoming recruits.")
    st.caption(f"Click below to finalize the offseason and prepare for the {current_year} season.")

    if st.button(f"Start {current_year} Season Setup", type="primary", use_container_width=True, key="off_complete"):
        with st.spinner("Finalizing offseason..."):
            try:
                api_client.offseason_complete(session_id)
                st.rerun()
            except api_client.APIError as e:
                st.error(f"Finalize failed: {e.detail}")


def _render_quick_game(shared):
    teams = shared["teams"]
    styles = shared["styles"]
    team_names = shared["team_names"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]
    OFFENSE_TOOLTIPS = shared["OFFENSE_TOOLTIPS"]
    DEFENSE_TOOLTIPS = shared["DEFENSE_TOOLTIPS"]

    st.subheader("Quick Game")
    st.caption("Play a single exhibition game between any two teams")

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Home Team**")
            home_key = _render_team_picker_quick(teams, label="Select Home Team", key_prefix="home", default_idx=0)
            hc1, hc2 = st.columns(2)
            with hc1:
                home_style = st.selectbox("Offense", style_keys,
                                          format_func=lambda x: styles[x]["label"],
                                          index=style_keys.index(next((t["default_style"] for t in teams if t["key"] == home_key), "balanced")),
                                          key="home_style")
            with hc2:
                home_def_style = st.selectbox("Defense", defense_style_keys,
                                               format_func=lambda x: defense_styles[x]["label"],
                                               key="home_def_style")
            st.caption(OFFENSE_TOOLTIPS.get(home_style, styles[home_style]["description"]))

        with col2:
            st.markdown("**Away Team**")
            away_key = _render_team_picker_quick(teams, label="Select Away Team", key_prefix="away", default_idx=min(1, len(teams) - 1))
            ac1, ac2 = st.columns(2)
            with ac1:
                away_style = st.selectbox("Offense", style_keys,
                                          format_func=lambda x: styles[x]["label"],
                                          index=style_keys.index(next((t["default_style"] for t in teams if t["key"] == away_key), "balanced")),
                                          key="away_style")
            with ac2:
                away_def_style = st.selectbox("Defense", defense_style_keys,
                                               format_func=lambda x: defense_styles[x]["label"],
                                               key="away_def_style")
            st.caption(OFFENSE_TOOLTIPS.get(away_style, styles[away_style]["description"]))

    weather_keys = list(WEATHER_CONDITIONS.keys())
    weather_labels = {k: v["label"] for k, v in WEATHER_CONDITIONS.items()}
    col_weather, col_seed, col_btn = st.columns([1, 1, 2])
    with col_weather:
        weather = st.selectbox("Weather", weather_keys, format_func=lambda x: f"{weather_labels[x]}", key="weather")
    with col_seed:
        seed = st.number_input("Seed (0 = random)", min_value=0, max_value=999999, value=0, key="seed")
    with col_btn:
        st.write("")
        st.write("")
        run_game = st.button("Simulate Game", type="primary", use_container_width=True)

    if run_game:
        actual_seed = seed if seed > 0 else random.randint(1, 999999)
        home_name = team_names[home_key]
        away_name = team_names[away_key]

        with st.spinner("Simulating game..."):
            try:
                result = api_client.simulate_quick_game(
                    home=home_key,
                    away=away_key,
                    home_offense=home_style,
                    home_defense=home_def_style,
                    away_offense=away_style,
                    away_defense=away_def_style,
                    weather=weather,
                    seed=actual_seed,
                )
                st.session_state["last_result"] = result
                st.session_state["last_seed"] = actual_seed
            except api_client.APIError as e:
                st.error(f"Simulation failed: {e.detail}")

    if "last_result" in st.session_state:
        result = st.session_state["last_result"]
        actual_seed = st.session_state["last_seed"]
        render_game_detail(result, key_prefix="qg")


def _render_dynasty_play(shared):
    styles = shared["styles"]
    style_keys = shared["style_keys"]
    defense_style_keys = shared["defense_style_keys"]
    defense_styles = shared["defense_styles"]

    session_id = st.session_state["api_session_id"]

    try:
        dynasty_status = api_client.get_dynasty_status(session_id)
    except api_client.APIError:
        st.error("Could not load dynasty data.")
        return

    coach = dynasty_status.get("coach", {})
    current_year = dynasty_status.get("current_year", 2026)
    dynasty_name = dynasty_status.get("dynasty_name", "Dynasty")
    coach_team = coach.get("team", "")
    coach_name_str = coach.get("name", "Coach")

    st.title(f"Play — {dynasty_name}")
    st.caption(f"Season {current_year} | Coach {coach_name_str} | {coach_team}")

    play_tabs = st.tabs(["Simulate Season", "Quick Game"])

    with play_tabs[0]:
        st.subheader(f"Season {current_year}")

        teams_dir = _teams_dir()
        all_teams = load_teams_from_directory(teams_dir)
        total_teams = len(all_teams)

        setup_col1, setup_col2 = st.columns(2)
        with setup_col1:
            games_per_team = st.slider(
                "Regular Season Games Per Team",
                min_value=8, max_value=12, value=10,
                key=f"dyn_games_{current_year}"
            )
        with setup_col2:
            dyn_playoff_options = [p for p in [4, 8, 12, 16, 24, 32] if p <= total_teams]
            if not dyn_playoff_options:
                dyn_playoff_options = [total_teams]
            playoff_format = st.radio("Playoff Format", dyn_playoff_options, index=0, horizontal=True,
                                      key=f"dyn_playoff_{current_year}")

        dyn_rec = get_recommended_bowl_count(total_teams, playoff_format)
        dyn_max_bowls = max(0, (total_teams - playoff_format) // 2)
        dyn_bowl_count = st.slider("Number of Bowl Games", min_value=0, max_value=min(12, dyn_max_bowls), value=min(dyn_rec, min(12, dyn_max_bowls)),
                                    key=f"dyn_bowls_{current_year}")

        teams_dir_path = _teams_dir()
        team_identities = load_team_identity(teams_dir_path)

        st.markdown("**Your Team**")
        user_team = coach_team
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
                                     key=f"dyn_user_off_{current_year}")
        with user_def_col:
            user_def = st.selectbox("Defense Style", defense_style_keys,
                                     format_func=lambda x: defense_styles[x]["label"],
                                     key=f"dyn_user_def_{current_year}")

        ai_seed = hash(f"{dynasty_name}_{current_year}") % 999999
        ai_configs = auto_assign_all_teams(
            teams_dir_path,
            human_teams=[user_team],
            human_configs={user_team: {"offense_style": user_off, "defense_style": user_def}},
            seed=ai_seed,
        )

        ai_opponent_teams = sorted([t for t in all_teams if t != user_team])
        with st.expander(f"AI Coach Assignments ({len(ai_opponent_teams)} teams)", expanded=False):
            ai_data = []
            for tname in ai_opponent_teams:
                cfg = ai_configs.get(tname, {"offense_style": "balanced", "defense_style": "base_defense"})
                identity = team_identities.get(tname, {})
                mascot = identity.get("mascot", "")
                ai_data.append({
                    "Team": tname,
                    "Mascot": mascot,
                    "Offense": styles.get(cfg["offense_style"], {}).get("label", cfg["offense_style"]),
                    "Defense": defense_styles.get(cfg["defense_style"], {}).get("label", cfg["defense_style"]),
                })
            st.dataframe(pd.DataFrame(ai_data), hide_index=True, use_container_width=True)

        phase = dynasty_status.get("phase", "setup")

        try:
            season_status = api_client.get_season_status(session_id)
            season_phase = season_status.get("phase", phase)
        except api_client.APIError:
            season_phase = phase

        if season_phase == "setup":
            # Non-conference scheduling for dynasty
            dyn_pinned = []
            try:
                nc_resp = api_client.get_dynasty_non_conference_opponents(
                    session_id, team=user_team, games_per_team=games_per_team,
                )
                dyn_conferences = {}
                # Rebuild conference dict from dynasty
                for opp in nc_resp.get("opponents", []):
                    conf = opp.get("conference", "")
                    if conf:
                        dyn_conferences.setdefault(conf, [])
                # Also add user team's conference
                user_dyn_conf = nc_resp.get("conference", "")
                if user_dyn_conf:
                    dyn_conferences.setdefault(user_dyn_conf, [])

                # Get full conference dict from dynasty status
                dyn_status_confs = dynasty_status.get("conferences", {})
                if dyn_status_confs:
                    dyn_conferences = dyn_status_confs
                else:
                    # Fallback: use team identities to build conference map
                    dyn_conferences = {}
                    for tname in all_teams:
                        ident = team_identities.get(tname, {})
                        c = ident.get("conference", "")
                        if c:
                            dyn_conferences.setdefault(c, []).append(tname)
                    dyn_conferences = {k: v for k, v in dyn_conferences.items() if len(v) >= 2}

                # Get dynasty prestige map
                dyn_prestige = {}
                for opp in nc_resp.get("opponents", []):
                    dyn_prestige[opp["name"]] = opp["prestige"]
                my_prestige = nc_resp.get("team_prestige", 50)
                dyn_prestige[user_team] = my_prestige

                if dyn_conferences:
                    dyn_pinned = _render_non_conference_picker(
                        user_teams=[user_team],
                        all_teams=all_teams,
                        conferences=dyn_conferences,
                        games_per_team=games_per_team,
                        team_prestige=dyn_prestige,
                        key_prefix=f"dyn_nc_{current_year}",
                        is_dynasty=True,
                    )
            except api_client.APIError:
                pass  # Non-conference picker unavailable; proceed without it

            st.divider()
            if st.button(f"Start {current_year} Season", type="primary", use_container_width=True, key="sim_dynasty_season"):
                with st.spinner("Starting season..."):
                    try:
                        api_client.dynasty_start_season(
                            session_id,
                            games_per_team=games_per_team,
                            playoff_size=playoff_format,
                            bowl_count=dyn_bowl_count,
                            offense_style=user_off,
                            defense_style=user_def,
                            ai_seed=ai_seed,
                            pinned_matchups=dyn_pinned if dyn_pinned else None,
                            program_archetype=st.session_state.get("dyn_program_archetype_selected"),
                        )
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Failed to start season: {e.detail}")

        elif season_phase in ("regular",):
            status = season_status
            total_weeks = status.get("total_weeks", 0)
            current_week = status.get("current_week", 0)
            next_week = status.get("next_week")
            games_played = status.get("games_played", 0)
            total_games = status.get("total_games", 0)

            if next_week is not None:
                sm1, sm2, sm3 = st.columns(3)
                sm1.metric("Current Week", f"Week {next_week} of {total_weeks}")
                sm2.metric("Games Played", f"{games_played} / {total_games}")
                progress_pct = games_played / total_games if total_games > 0 else 0
                sm3.metric("Progress", f"{progress_pct:.0%}")
                st.progress(progress_pct)

                render_dq_bankroll_banner(session_id)
                render_dq_pre_sim(session_id, next_week, key_prefix="dyn_")

                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button("Sim Next Week", type="primary", use_container_width=True, key="dyn_sim_next_week"):
                        with st.spinner(f"Simulating Week {next_week}..."):
                            try:
                                api_client.simulate_week(session_id, week=next_week)
                                try:
                                    api_client.dq_resolve_week(session_id, next_week)
                                except api_client.APIError:
                                    pass
                                st.rerun()
                            except api_client.APIError as e:
                                st.error(f"Simulation failed: {e.detail}")

                with btn_col2:
                    remaining = list(range(next_week + 1, total_weeks + 1))
                    if remaining:
                        target = st.selectbox("Sim through week...", remaining,
                                               format_func=lambda w: f"Week {w}",
                                               key="dyn_sim_to_week_select")
                        if st.button("Sim to Week", use_container_width=True, key="dyn_sim_to_week_btn"):
                            with st.spinner(f"Simulating through Week {target}..."):
                                try:
                                    api_client.simulate_through_week(session_id, target)
                                    st.rerun()
                                except api_client.APIError as e:
                                    st.error(f"Simulation failed: {e.detail}")

                with btn_col3:
                    if st.button("Sim Rest of Season", use_container_width=True, key="dyn_sim_rest"):
                        with st.spinner("Simulating remaining games..."):
                            try:
                                api_client.simulate_rest(session_id)
                                st.rerun()
                            except api_client.APIError as e:
                                st.error(f"Simulation failed: {e.detail}")

                if current_week > 0:
                    render_dq_post_sim(session_id, current_week, key_prefix="dyn_")

                    with st.expander("DraftyQueenz Season History", expanded=False):
                        render_dq_history(session_id, key_prefix="dyn_")

                    st.divider()
                    try:
                        standings_resp = api_client.get_standings(session_id)
                        standings = standings_resp.get("standings", [])
                        user_rec = next((r for r in standings if r["team_name"] == coach_team), None)
                        if user_rec:
                            ur_rank = next((i for i, r in enumerate(standings, 1) if r["team_name"] == coach_team), 0)
                            ur1, ur2, ur3 = st.columns(3)
                            ur1.metric("Your Record", f"{user_rec['wins']}-{user_rec['losses']}", f"#{ur_rank} overall")
                            ur2.metric("Points For", fmt_vb_score(user_rec['points_for']))
                            ur3.metric("Points Against", fmt_vb_score(user_rec['points_against']))
                    except api_client.APIError:
                        pass

                    st.divider()
                    st.subheader("Recent Results")
                    show_weeks = range(max(1, current_week - 2), current_week + 1)
                    for w in show_weeks:
                        _render_week_results_api(session_id, w)

            else:
                st.rerun()

        elif season_phase == "playoffs_pending":
            st.success("Regular season complete!")
            try:
                standings_resp = api_client.get_standings(session_id)
                standings = standings_resp.get("standings", [])
                user_rec = next((r for r in standings if r["team_name"] == coach_team), None)
                if user_rec:
                    ur_rank = next((i for i, r in enumerate(standings, 1) if r["team_name"] == coach_team), 0)
                    st.metric("Your Final Record", f"{user_rec['wins']}-{user_rec['losses']} (#{ur_rank})")
            except api_client.APIError:
                pass

            if playoff_format >= 4:
                st.subheader(f"Playoff ({playoff_format} teams)")
                if st.button("Run Playoffs", type="primary", use_container_width=True, key="dyn_run_playoffs"):
                    with st.spinner("Running playoffs..."):
                        try:
                            api_client.run_playoffs(session_id)
                            st.rerun()
                        except api_client.APIError as e:
                            st.error(f"Playoffs failed: {e.detail}")

        elif season_phase == "bowls_pending":
            try:
                bracket_resp = api_client.get_playoff_bracket(session_id)
                champion = bracket_resp.get("champion")
                if champion:
                    if champion == coach_team:
                        st.success(f"YOUR TEAM {champion} ARE THE NATIONAL CHAMPIONS!")
                    else:
                        st.info(f"National Champions: {champion}")
            except api_client.APIError:
                pass

            st.subheader(f"Bowl Games ({dyn_bowl_count} bowls)")
            if st.button("Run Bowl Games", type="primary", use_container_width=True, key="dyn_run_bowls"):
                with st.spinner("Running bowl games..."):
                    try:
                        api_client.run_bowls(session_id)
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Bowl games failed: {e.detail}")

        elif season_phase in ("complete", "finalize"):
            try:
                bracket_resp = api_client.get_playoff_bracket(session_id)
                champion = bracket_resp.get("champion")
                if champion:
                    if champion == coach_team:
                        st.balloons()
                        st.success(f"YOUR TEAM {champion} ARE THE NATIONAL CHAMPIONS!")
                    else:
                        st.info(f"National Champions: {champion}")
            except api_client.APIError:
                pass

            st.subheader(f"Begin Offseason for {current_year + 1}")
            st.caption("This will process development, graduation, and start the offseason — NIL allocation, transfer portal, and recruiting.")

            if st.button("Start Offseason", type="primary", use_container_width=True, key="dyn_advance"):
                with st.spinner("Processing offseason..."):
                    try:
                        api_client.dynasty_advance(session_id)
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Offseason start failed: {e.detail}")

        elif season_phase == "offseason":
            _render_offseason_flow(session_id, coach_team, current_year)

    with play_tabs[1]:
        _render_quick_game(shared)


def _render_week_results_api(session_id, week_num, label=None):
    try:
        resp = api_client.get_schedule(session_id, week=week_num, completed_only=True)
        week_games = resp.get("games", [])
    except api_client.APIError:
        return

    if not week_games:
        return
    header = label or f"Week {week_num} Results"
    with st.expander(header, expanded=True):
        for g in week_games:
            home_score = g.get("home_score") or 0
            away_score = g.get("away_score") or 0
            home_team = g.get("home_team", "")
            away_team = g.get("away_team", "")
            winner = home_team if home_score > away_score else away_team
            marker = "**" if winner == home_team else ""
            marker2 = "**" if winner == away_team else ""
            st.markdown(f"{marker}{home_team}{marker} {fmt_vb_score(home_score)} — {fmt_vb_score(away_score)} {marker2}{away_team}{marker2}")


def _render_season_portal(session_id, shared):
    st.title("Transfer Portal")
    st.caption("Browse available transfer players and add them to your roster before the season begins.")

    human_teams = st.session_state.get("season_human_teams_list", [])
    if not human_teams:
        st.info("No human-coached teams — skipping portal.")
        try:
            api_client.season_portal_skip(session_id)
            st.rerun()
        except api_client.APIError:
            pass
        return

    active_team = human_teams[0]
    if len(human_teams) > 1:
        active_team = st.selectbox("Manage Portal For", human_teams, key="portal_team_select")

    try:
        portal_resp = api_client.season_portal_get(session_id)
    except api_client.APIError:
        try:
            portal_resp = api_client.season_portal_generate(session_id, human_team=active_team)
        except api_client.APIError as e:
            st.error(f"Could not load portal: {e.detail}")
            return

    entries = portal_resp.get("entries", [])
    committed = portal_resp.get("committed", [])
    cap = portal_resp.get("transfer_cap", 0)
    remaining = portal_resp.get("transfers_remaining", 0)
    if remaining == -1:
        remaining = cap

    pm1, pm2, pm3 = st.columns(3)
    pm1.metric("Available Players", len(entries))
    pm2.metric("Transfer Cap", cap)
    pm3.metric("Slots Remaining", remaining)

    if committed:
        st.subheader("Your Incoming Transfers")
        committed_data = []
        for c in committed:
            committed_data.append({
                "Name": c.get("name", ""),
                "Position": c.get("position", ""),
                "OVR": c.get("overall", 0),
                "Year": c.get("year", ""),
                "From": c.get("origin_team", ""),
            })
        st.dataframe(pd.DataFrame(committed_data), hide_index=True, use_container_width=True)

    st.divider()

    pf1, pf2 = st.columns(2)
    with pf1:
        pos_filter = st.selectbox(
            "Position Filter",
            ["All", "VP", "HB", "WB", "SB", "ZB", "LB", "CB", "LA", "LM"],
            key="season_portal_pos",
        )
    with pf2:
        ovr_filter = st.number_input("Min Overall", min_value=0, max_value=99, value=0, key="season_portal_ovr")

    filtered = entries
    if pos_filter != "All":
        filtered = [e for e in filtered if e.get("position", "") == pos_filter]
    if ovr_filter > 0:
        filtered = [e for e in filtered if e.get("overall", 0) >= ovr_filter]

    if filtered:
        portal_data = []
        for e in filtered:
            reason_label = e.get("reason", "").replace("_", " ").title()
            portal_data.append({
                "Name": e.get("name", ""),
                "Position": e.get("position", ""),
                "OVR": e.get("overall", 0),
                "Year": e.get("year", ""),
                "From": e.get("origin_team", ""),
                "Reason": reason_label,
                "Stars": e.get("potential", 0),
            })

        st.dataframe(
            pd.DataFrame(portal_data),
            hide_index=True, use_container_width=True, height=350,
        )

        if remaining > 0:
            st.subheader("Commit a Player")
            player_options = [
                f"{e.get('name', '')} ({e.get('position', '')}, OVR {e.get('overall', 0)}) — from {e.get('origin_team', '')}"
                for e in filtered
            ]
            selected_idx = st.selectbox(
                "Select Player", range(len(player_options)),
                format_func=lambda i: player_options[i],
                key="season_portal_select",
            )

            selected_entry = filtered[selected_idx]
            global_idx = selected_entry.get("global_index", -1)

            if global_idx >= 0:
                if st.button(
                    f"Commit {selected_entry.get('name', '')} to {active_team}",
                    type="primary", use_container_width=True,
                    key="season_portal_commit_btn",
                ):
                    try:
                        result = api_client.season_portal_commit(
                            session_id, team_name=active_team,
                            entry_index=global_idx,
                        )
                        st.success(
                            f"Committed {result.get('player', {}).get('name', '')} to {active_team}! "
                            f"({result.get('transfers_remaining', 0)} slots remaining)"
                        )
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Commit failed: {e.detail}")
            else:
                st.warning("Cannot interact with this player — try refreshing.")
        else:
            st.info("You've used all your transfer slots.")
    else:
        st.info("No available portal players matching your filters.")

    st.divider()
    dc1, dc2 = st.columns(2)
    with dc1:
        if st.button("Done with Portal — Start Season", type="primary", use_container_width=True, key="portal_done_btn"):
            try:
                api_client.season_portal_skip(session_id)
                st.rerun()
            except api_client.APIError as e:
                st.error(f"Could not advance: {e.detail}")
    with dc2:
        if st.button("Skip Portal", use_container_width=True, key="portal_skip_btn"):
            try:
                api_client.season_portal_skip(session_id)
                st.rerun()
            except api_client.APIError as e:
                st.error(f"Could not skip: {e.detail}")


def _render_season_play(shared):
    session_id = st.session_state["api_session_id"]

    try:
        status = api_client.get_season_status(session_id)
    except api_client.APIError:
        st.error("Could not load season data.")
        return

    phase = status.get("phase", "regular")
    season_name = status.get("name", "Season")
    total_weeks = status.get("total_weeks", 0)
    current_week = status.get("current_week", 0)
    next_week = status.get("next_week")
    games_played = status.get("games_played", 0)
    total_games = status.get("total_games", 0)
    champion = status.get("champion")

    if phase == "portal":
        _render_season_portal(session_id, shared)
        return

    st.title(f"Play — {season_name}")

    if phase == "regular":
        if next_week is not None:
            sm1, sm2, sm3 = st.columns(3)
            sm1.metric("Current Week", f"Week {next_week} of {total_weeks}")
            sm2.metric("Games Played", f"{games_played} / {total_games}")
            progress_pct = games_played / total_games if total_games > 0 else 0
            sm3.metric("Progress", f"{progress_pct:.0%}")

            st.progress(progress_pct)

            render_dq_bankroll_banner(session_id)
            render_dq_pre_sim(session_id, next_week, key_prefix="ssn_")

            st.subheader("Advance Season")

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("Sim Next Week", type="primary", use_container_width=True, key="sim_next_week"):
                    with st.spinner(f"Simulating Week {next_week}..."):
                        try:
                            api_client.simulate_week(session_id, week=next_week)
                            try:
                                api_client.dq_resolve_week(session_id, next_week)
                            except api_client.APIError:
                                pass
                            st.rerun()
                        except api_client.APIError as e:
                            st.error(f"Simulation failed: {e.detail}")

            with btn_col2:
                remaining = list(range(next_week + 1, total_weeks + 1))
                if remaining:
                    target = st.selectbox("Sim through week...", remaining,
                                           format_func=lambda w: f"Week {w}",
                                           key="sim_to_week_select")
                    if st.button("Sim to Week", use_container_width=True, key="sim_to_week_btn"):
                        with st.spinner(f"Simulating through Week {target}..."):
                            try:
                                api_client.simulate_through_week(session_id, target)
                                st.rerun()
                            except api_client.APIError as e:
                                st.error(f"Simulation failed: {e.detail}")

            with btn_col3:
                if st.button("Sim Rest of Season", use_container_width=True, key="sim_rest_season"):
                    with st.spinner(f"Simulating remaining {total_games - games_played} games..."):
                        try:
                            api_client.simulate_rest(session_id)
                            st.rerun()
                        except api_client.APIError as e:
                            st.error(f"Simulation failed: {e.detail}")

            if current_week > 0:
                render_dq_post_sim(session_id, current_week, key_prefix="ssn_")

                with st.expander("DraftyQueenz Season History", expanded=False):
                    render_dq_history(session_id, key_prefix="ssn_")

                st.divider()
                try:
                    standings_resp = api_client.get_standings(session_id)
                    standings = standings_resp.get("standings", [])
                    top5 = standings[:5]
                    st.subheader("Current Standings (Top 5)")
                    for i, rec in enumerate(top5, 1):
                        st.markdown(f"{i}. **{rec['team_name']}** — {rec['wins']}-{rec['losses']} (PF: {fmt_vb_score(rec['points_for'])})")
                    st.caption("See full standings in the League tab.")
                except api_client.APIError:
                    pass

                st.divider()
                st.subheader("Recent Results")
                show_weeks = range(max(1, current_week - 2), current_week + 1)
                for w in show_weeks:
                    _render_week_results_api(session_id, w)
        else:
            st.rerun()

    elif phase == "playoffs_pending":
        st.success("Regular season complete!")
        try:
            standings_resp = api_client.get_standings(session_id)
            standings = standings_resp.get("standings", [])
            sm1, sm2, sm3 = st.columns(3)
            sm1.metric("Games Played", games_played)
            best = standings[0] if standings else None
            sm2.metric("#1 Team", best["team_name"] if best else "—")
            sm3.metric("Record", f"{best['wins']}-{best['losses']}" if best else "—")
        except api_client.APIError:
            pass

        playoff_size = st.session_state.get("season_playoff_size", 8)
        if playoff_size > 0:
            st.subheader(f"Playoff ({playoff_size} teams)")
            st.caption("Conference champions get auto-bids, remaining spots filled by Power Index.")
            if st.button("Run Playoffs", type="primary", use_container_width=True, key="run_playoffs_btn"):
                with st.spinner("Running playoffs..."):
                    try:
                        api_client.run_playoffs(session_id)
                        st.rerun()
                    except api_client.APIError as e:
                        st.error(f"Playoffs failed: {e.detail}")

    elif phase == "bowls_pending":
        if champion:
            st.success(f"**National Champions: {champion}**")
        bowl_count = st.session_state.get("season_bowl_count", 0)
        st.subheader(f"Bowl Games ({bowl_count} bowls)")
        if st.button("Run Bowl Games", type="primary", use_container_width=True, key="run_bowls_btn"):
            with st.spinner("Running bowl games..."):
                try:
                    api_client.run_bowls(session_id)
                    st.rerun()
                except api_client.APIError as e:
                    st.error(f"Bowl games failed: {e.detail}")

    elif phase == "complete":
        if champion:
            st.success(f"**National Champions: {champion}**")

        try:
            standings_resp = api_client.get_standings(session_id)
            standings = standings_resp.get("standings", [])
            schedule_resp = api_client.get_schedule(session_id, completed_only=True)
            all_games = schedule_resp.get("games", [])
            all_scores = []
            for g in all_games:
                all_scores.extend([g.get("home_score") or 0, g.get("away_score") or 0])
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Teams", len(standings))
            sm2.metric("Games Played", len(all_games))
            sm3.metric("Avg Score", f"{avg_score:.1f}")
            best = standings[0] if standings else None
            sm4.metric("Top Team", f"{best['team_name']}" if best else "—", f"{best['wins']}-{best['losses']}" if best else "")
        except api_client.APIError:
            pass

        st.divider()
        st.caption("Season is complete. Browse results in the League tab, or start a new session.")

    if st.button("End Season & Start New", key="end_season_btn"):
        try:
            api_client.delete_session(session_id)
        except api_client.APIError:
            pass
        for key in ["api_session_id", "api_mode", "season_human_teams_list",
                     "season_playoff_size", "season_bowl_count"]:
            st.session_state.pop(key, None)
        st.rerun()
