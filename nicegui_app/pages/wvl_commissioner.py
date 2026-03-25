"""
WVL Commissioner Mode — NiceGUI UI Page
=========================================

Unified simulation hub: WVL pro league + FIV international + career tracking.
No team ownership. All teams AI-managed. Commissioner observes and influences.
"""

from nicegui import ui, app
from typing import Optional
import logging

_log = logging.getLogger("viperball.commissioner")

from engine.wvl_config import ALL_CLUBS, CLUBS_BY_KEY, CLUBS_BY_TIER, TIER_BY_NUMBER
from engine.wvl_commissioner import (
    WVLCommissionerDynasty, create_commissioner_dynasty,
)
from engine.db import (
    save_commissioner_dynasty, load_commissioner_dynasty, delete_commissioner_dynasty,
    save_hall_of_fame_entry, load_hall_of_fame,
)

_COMMISH_KEY = "_wvl_commissioner"
_COMMISH_SEASON_KEY = "_wvl_commish_season"
_COMMISH_PHASE_KEY = "_wvl_commish_phase"

# In-memory cache
_commish_cache = {}


def _get_dynasty() -> Optional[WVLCommissionerDynasty]:
    if "current" in _commish_cache:
        return _commish_cache["current"]
    d = load_commissioner_dynasty()
    if d:
        _commish_cache["current"] = d
    return d


def _save_dynasty(d: WVLCommissionerDynasty):
    _commish_cache["current"] = d
    try:
        save_commissioner_dynasty(d)
    except Exception as e:
        _log.warning(f"Failed to save commissioner dynasty: {e}")


def _clear_dynasty():
    _commish_cache.pop("current", None)
    try:
        delete_commissioner_dynasty()
    except Exception:
        pass


def _get_phase() -> str:
    return app.storage.user.get(_COMMISH_PHASE_KEY, "setup")


def _set_phase(phase: str):
    app.storage.user[_COMMISH_PHASE_KEY] = phase


def _refresh():
    r = app.storage.user.get("_commish_refresh")
    if r:
        r()


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def render_commissioner_section():
    """Main entry point for Commissioner Mode."""
    dynasty = _get_dynasty()
    phase = _get_phase()

    @ui.refreshable
    def _main():
        d = _get_dynasty()
        p = _get_phase()

        if not d or p == "setup":
            _render_setup()
        else:
            _render_dashboard(d)

    app.storage.user["_commish_refresh"] = _main.refresh
    _main()


# ═══════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════

def _render_setup():
    with ui.element("div").classes("w-full max-w-2xl mx-auto"):
        with ui.element("div").classes("w-full").style(
            "background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%); "
            "padding: 32px; border-radius: 12px; margin-bottom: 24px;"
        ):
            ui.label("WVL Commissioner Mode").classes("text-3xl font-bold text-white")
            ui.label(
                "Run the entire Women's Viperball League. "
                "Simulate seasons, track careers, manage the Hall of Fame."
            ).classes("text-sm text-blue-200 mt-1")

        with ui.card().classes("w-full p-6"):
            name_input = ui.input("Dynasty Name", value="My Commissioner Save").classes("w-full")
            year_input = ui.number("Starting Year", value=2026, min=2020, max=2050).classes("w-full")

            ui.separator().classes("my-4")

            async def _create():
                name = name_input.value.strip() or "Commissioner"
                year = int(year_input.value or 2026)
                d = create_commissioner_dynasty(name, starting_year=year)
                _save_dynasty(d)
                _set_phase("dashboard")
                ui.notify(f"Commissioner dynasty '{name}' created!", type="positive")
                _refresh()

            ui.button("Create Commissioner Dynasty", icon="gavel", on_click=_create).classes(
                "bg-blue-600 text-white px-8 py-3 rounded-lg text-lg"
            )

        # Load existing
        existing = _get_dynasty()
        if existing:
            with ui.card().classes("w-full p-4 mt-4"):
                ui.label(f"Continue: {existing.dynasty_name} (Year {existing.current_year})").classes(
                    "text-sm font-semibold text-slate-700"
                )
                async def _resume():
                    _set_phase("dashboard")
                    _refresh()
                ui.button("Resume", icon="play_arrow", on_click=_resume).classes("bg-green-600 text-white")


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

def _render_dashboard(dynasty: WVLCommissionerDynasty):
    phase = _get_phase()

    # Header
    with ui.element("div").classes("w-full").style(
        "background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%); "
        "padding: 20px 24px; border-radius: 8px; margin-bottom: 16px;"
    ):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-0"):
                ui.label(dynasty.dynasty_name).classes("text-xl font-bold text-white")
                ui.label(f"Year {dynasty.current_year} — Commissioner Mode").classes("text-sm text-blue-200")
            with ui.row().classes("gap-2"):
                for tier_num in sorted(dynasty.last_season_champions.keys()):
                    champ_key = dynasty.last_season_champions[tier_num]
                    club = CLUBS_BY_KEY.get(champ_key)
                    tc = TIER_BY_NUMBER.get(tier_num)
                    tier_label = tc.tier_name if tc else f"T{tier_num}"
                    ui.chip(
                        f"{tier_label}: {club.name if club else champ_key}",
                        icon="emoji_events",
                    ).props("dense color=amber-8 text-color=white")

    # Tabs
    with ui.tabs().classes("w-full") as tabs:
        tab_wvl = ui.tab("WVL", icon="sports_football")
        tab_rosters = ui.tab("Rosters", icon="groups")
        tab_players = ui.tab("Players", icon="person_search")
        tab_hof = ui.tab("Hall of Fame", icon="museum")
        tab_history = ui.tab("History", icon="timeline")

    with ui.tab_panels(tabs, value=tab_wvl).classes("w-full"):
        with ui.tab_panel(tab_wvl):
            _render_wvl_tab(dynasty)
        with ui.tab_panel(tab_rosters):
            _render_rosters_tab(dynasty)
        with ui.tab_panel(tab_players):
            _render_players_tab(dynasty)
        with ui.tab_panel(tab_hof):
            _render_hof_tab(dynasty)
        with ui.tab_panel(tab_history):
            _render_history_tab(dynasty)


# ═══════════════════════════════════════════════════════════════
# WVL TAB — Simulate & Standings
# ═══════════════════════════════════════════════════════════════

def _render_wvl_tab(dynasty: WVLCommissionerDynasty):
    phase = _get_phase()

    with ui.row().classes("w-full gap-3 mb-4 flex-wrap"):
        # Sim controls
        if phase in ("dashboard", "pre_season"):
            async def _start_and_sim():
                d = _get_dynasty()
                if not d:
                    return
                ui.notify("Starting season...", type="info")
                season = d.start_season()
                _set_phase("in_season")
                _save_dynasty(d)
                # Store season reference
                _commish_cache["season"] = season
                _refresh()

            ui.button("Start Season", icon="play_arrow", on_click=_start_and_sim).classes(
                "bg-green-600 text-white"
            )

        elif phase == "in_season":
            season = _commish_cache.get("season")

            async def _sim_week():
                d = _get_dynasty()
                s = _commish_cache.get("season")
                if not d or not s:
                    return
                s.sim_week_all_tiers(use_fast_sim=True)

                all_done = all(
                    t.current_week >= t.total_weeks or t.phase != "regular_season"
                    for t in s.tier_seasons.values()
                )
                if all_done:
                    s.start_playoffs_all()
                    _set_phase("playoffs")

                _save_dynasty(d)
                _refresh()

            async def _sim_full():
                d = _get_dynasty()
                s = _commish_cache.get("season")
                if not d or not s:
                    return
                ui.notify("Simulating full season...", type="info")

                # Sim remaining regular season
                while s.phase == "regular_season" or any(
                    t.phase == "regular_season" and t.current_week < t.total_weeks
                    for t in s.tier_seasons.values()
                ):
                    s.sim_week_all_tiers(use_fast_sim=True)

                s.start_playoffs_all()
                safety = 0
                while s.phase != "season_complete" and safety < 20:
                    s.advance_playoffs_all()
                    safety += 1

                d.advance_season(s)
                _set_phase("season_complete")
                _save_dynasty(d)
                ui.notify("Season complete!", type="positive")
                _refresh()

            ui.button("Sim Week", icon="skip_next", on_click=_sim_week).classes("bg-green-600 text-white")
            ui.button("Sim Full Season", icon="fast_forward", on_click=_sim_full).classes("bg-blue-600 text-white")

            if season:
                for tn, ts in season.tier_seasons.items():
                    tc = TIER_BY_NUMBER.get(tn)
                    label = tc.tier_name if tc else f"Tier {tn}"
                    ui.chip(f"{label}: Week {ts.current_week}/{ts.total_weeks}").props("dense outline")

        elif phase == "playoffs":
            async def _advance_playoffs():
                d = _get_dynasty()
                s = _commish_cache.get("season")
                if not d or not s:
                    return
                s.advance_playoffs_all()
                if s.phase == "season_complete":
                    d.advance_season(s)
                    _set_phase("season_complete")
                    ui.notify("Season complete!", type="positive")
                _save_dynasty(d)
                _refresh()

            async def _sim_all_playoffs():
                d = _get_dynasty()
                s = _commish_cache.get("season")
                if not d or not s:
                    return
                safety = 0
                while s.phase != "season_complete" and safety < 20:
                    s.advance_playoffs_all()
                    safety += 1
                d.advance_season(s)
                _set_phase("season_complete")
                _save_dynasty(d)
                ui.notify("Playoffs complete!", type="positive")
                _refresh()

            ui.button("Advance Playoffs", icon="emoji_events", on_click=_advance_playoffs).classes("bg-amber-600 text-white")
            ui.button("Sim All Playoffs", icon="fast_forward", on_click=_sim_all_playoffs).classes("bg-purple-600 text-white")

        elif phase == "season_complete":
            async def _run_offseason():
                d = _get_dynasty()
                s = _commish_cache.get("season")
                if not d:
                    return
                ui.notify("Processing offseason...", type="info")
                import random as _rng
                offseason = d.run_offseason(s or d._current_season, rng=_rng.Random())
                _save_dynasty(d)

                # Persist HoF entries to DB
                for entry_dict in offseason.get("hall_of_fame_inductees", []):
                    try:
                        save_hall_of_fame_entry(
                            entry_dict, entry_dict.get("player_id", entry_dict["full_name"])
                        )
                    except Exception:
                        pass

                hof_count = len(offseason.get("hall_of_fame_inductees", []))
                ret_count = len(offseason.get("retirements", []))
                bridge = offseason.get("bridge_import")
                msg = f"Offseason done! {ret_count} retirements"
                if hof_count:
                    msg += f", {hof_count} HoF inductees"
                if bridge:
                    msg += f", {bridge['players_imported']} CVL imports"
                ui.notify(msg, type="positive", timeout=6000)
                _set_phase("dashboard")
                _refresh()

            ui.button("Process Offseason & Next Year", icon="autorenew", on_click=_run_offseason).classes(
                "bg-amber-600 text-white"
            )

            # Show champions
            with ui.card().classes("w-full p-4 mt-3 bg-amber-50"):
                ui.label("Season Champions").classes("text-lg font-bold text-amber-800")
                for tier_num in sorted(dynasty.last_season_champions.keys()):
                    champ_key = dynasty.last_season_champions[tier_num]
                    club = CLUBS_BY_KEY.get(champ_key)
                    tc = TIER_BY_NUMBER.get(tier_num)
                    tier_label = tc.tier_name if tc else f"Tier {tier_num}"
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("emoji_events", size="sm").classes("text-amber-500")
                        ui.label(f"{tier_label}: {club.name if club else champ_key}").classes("text-sm")

    # Reset button
    with ui.row().classes("w-full justify-end mt-4"):
        async def _reset():
            _clear_dynasty()
            _set_phase("setup")
            _commish_cache.clear()
            _refresh()

        ui.button("New Dynasty", icon="restart_alt", on_click=_reset).props("flat color=red-6 no-caps size=sm")


# ═══════════════════════════════════════════════════════════════
# ROSTERS TAB
# ═══════════════════════════════════════════════════════════════

def _render_rosters_tab(dynasty: WVLCommissionerDynasty):
    selected_team = {"key": None}

    with ui.row().classes("w-full gap-4"):
        # Team selector
        with ui.column().classes("w-64"):
            ui.label("Select Team").classes("text-sm font-semibold text-slate-600 mb-2")
            for tier_num in sorted(TIER_BY_NUMBER.keys()):
                tc = TIER_BY_NUMBER[tier_num]
                ui.label(tc.tier_name).classes("text-xs text-slate-400 uppercase mt-2")
                teams_in_tier = [
                    k for k, t in dynasty.tier_assignments.items() if t == tier_num
                ]
                for tk in sorted(teams_in_tier):
                    club = CLUBS_BY_KEY.get(tk)
                    name = club.name if club else tk

                    async def _select(team_key=tk):
                        selected_team["key"] = team_key
                        _roster_panel.refresh()

                    ui.button(name, on_click=_select).props("flat dense no-caps").classes("text-xs")

        # Roster display
        with ui.column().classes("flex-1"):
            @ui.refreshable
            def _roster_panel():
                tk = selected_team["key"]
                if not tk:
                    ui.label("Select a team to view roster").classes("text-slate-400 italic")
                    return

                club = CLUBS_BY_KEY.get(tk)
                team_name = club.name if club else tk
                tier = dynasty.tier_assignments.get(tk, 0)
                tc = TIER_BY_NUMBER.get(tier)

                ui.label(team_name).classes("text-xl font-bold text-slate-800")
                if tc:
                    ui.label(tc.tier_name).classes("text-xs text-slate-400")

                roster = dynasty.get_team_roster(tk)
                if not roster:
                    ui.label("No roster data available. Start a season first.").classes("text-sm text-slate-400")
                    return

                columns = [
                    {"name": "name", "label": "Name", "field": "name", "align": "left", "sortable": True},
                    {"name": "position", "label": "Pos", "field": "position", "align": "center"},
                    {"name": "overall", "label": "OVR", "field": "overall", "align": "center", "sortable": True},
                    {"name": "nationality", "label": "Nat", "field": "nationality", "align": "center"},
                    {"name": "archetype", "label": "Type", "field": "archetype", "align": "center"},
                ]
                rows = [{**p, "_idx": i} for i, p in enumerate(roster)]
                ui.table(columns=columns, rows=rows, row_key="_idx").classes("w-full").props(
                    "dense flat bordered"
                )

                # Hall of Fame alumni for this team
                hof_entries = dynasty.hall_of_fame.get_inductees()
                team_hof = [e for e in hof_entries if tk in [
                    s.get("team_key", "") for s in (
                        e.career_record.get("pro_seasons", [])
                        if isinstance(e.career_record, dict) else []
                    )
                ] or any(tk in t for t in (e.pro_teams or []))]
                if team_hof:
                    ui.separator().classes("my-3")
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("museum", size="sm").classes("text-amber-500")
                        ui.label("Hall of Fame Alumni").classes("text-sm font-semibold text-amber-700")
                    for hof_e in team_hof:
                        ui.label(
                            f"{hof_e.full_name} ({hof_e.position}) — "
                            f"OVR {hof_e.peak_overall}, inducted {hof_e.induction_year}"
                        ).classes("text-xs text-amber-600")

                # Move player controls
                ui.separator().classes("my-3")
                ui.label("Move Player").classes("text-sm font-semibold text-slate-600")
                with ui.row().classes("items-end gap-2"):
                    player_names = [p["name"] for p in roster]
                    all_teams = sorted([
                        (CLUBS_BY_KEY[k].name if k in CLUBS_BY_KEY else k, k)
                        for k in dynasty.tier_assignments if k != tk
                    ])
                    player_select = ui.select(
                        player_names, label="Player", value=player_names[0] if player_names else None
                    ).classes("w-48")
                    dest_select = ui.select(
                        {k: n for n, k in all_teams}, label="Destination"
                    ).classes("w-48")

                    async def _move():
                        d = _get_dynasty()
                        if not d:
                            return
                        pname = player_select.value
                        dest = dest_select.value
                        if not pname or not dest:
                            ui.notify("Select player and destination", type="warning")
                            return
                        ok = d.move_player(pname, tk, dest)
                        if ok:
                            _save_dynasty(d)
                            ui.notify(f"Moved {pname}!", type="positive")
                            _roster_panel.refresh()
                        else:
                            ui.notify("Move failed", type="negative")

                    ui.button("Move", icon="swap_horiz", on_click=_move).classes("bg-blue-600 text-white")

            _roster_panel()


# ═══════════════════════════════════════════════════════════════
# PLAYERS TAB — Career Search
# ═══════════════════════════════════════════════════════════════

def _render_players_tab(dynasty: WVLCommissionerDynasty):
    search_state = {"query": "", "results": []}

    with ui.row().classes("w-full items-end gap-3 mb-4"):
        search_input = ui.input("Search players...", placeholder="Player name").classes("w-64")

        async def _search():
            q = search_input.value.strip()
            results = dynasty.career_tracker.search_players(query=q, limit=30)
            search_state["results"] = results
            _results_panel.refresh()

        ui.button("Search", icon="search", on_click=_search).classes("bg-blue-600 text-white")

        async def _leaders():
            leaders = dynasty.career_tracker.get_all_time_leaders("seasons", limit=30)
            search_state["results"] = [e["record"] for e in leaders]
            _results_panel.refresh()

        ui.button("All-Time Leaders", icon="leaderboard", on_click=_leaders).props("flat no-caps")

    @ui.refreshable
    def _results_panel():
        results = search_state["results"]
        if not results:
            ui.label("Search for a player or view all-time leaders.").classes("text-slate-400 italic")
            return

        columns = [
            {"name": "name", "label": "Name", "field": "name", "align": "left"},
            {"name": "pos", "label": "Pos", "field": "pos", "align": "center"},
            {"name": "nat", "label": "Nationality", "field": "nat", "align": "center"},
            {"name": "status", "label": "Status", "field": "status", "align": "center"},
            {"name": "ovr", "label": "Peak OVR", "field": "ovr", "align": "center"},
            {"name": "seasons", "label": "Pro Seasons", "field": "seasons", "align": "center"},
            {"name": "college", "label": "College", "field": "college", "align": "left"},
            {"name": "teams", "label": "Pro Teams", "field": "teams", "align": "left"},
        ]
        rows = []
        for i, r in enumerate(results):
            rows.append({
                "name": r.full_name,
                "pos": r.position,
                "nat": r.nationality,
                "status": r.career_status,
                "ovr": r.peak_overall,
                "seasons": r.career_pro_seasons_count,
                "college": r.college_team or "-",
                "teams": ", ".join(r.pro_teams_summary[:2]) or "-",
                "_idx": i,
            })

        def _on_row_click(e):
            idx = e.args[1].get("_idx", 0)
            if idx < len(results):
                _show_career_card(results[idx], dynasty)

        table = ui.table(columns=columns, rows=rows, row_key="_idx").classes("w-full").props(
            "dense flat bordered"
        )
        table.on("rowClick", _on_row_click)
        ui.label("Click a row to view full career card.").classes("text-xs text-slate-400 mt-1")

    _results_panel()


def _show_career_card(record, dynasty):
    """Show a modal with the player's full career card."""
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-6"):
        ui.label(record.full_name).classes("text-2xl font-bold text-slate-800")
        with ui.row().classes("gap-4 text-sm text-slate-500"):
            ui.label(record.position)
            ui.label(f"OVR {record.peak_overall}")
            ui.label(record.nationality)
            ui.chip(record.career_status, color="green" if record.career_status == "active" else "slate").props("dense")

        # College
        if record.college_team:
            ui.separator().classes("my-2")
            ui.label("College").classes("text-sm font-semibold text-blue-700")
            ui.label(f"{record.college_team} ({record.college_conference})").classes("text-sm")

        # Pro career
        if record.pro_seasons:
            ui.separator().classes("my-2")
            ui.label("Pro Career").classes("text-sm font-semibold text-green-700")
            for team_str in record.pro_teams_summary:
                ui.label(f"  {team_str}").classes("text-sm")
            ui.label(
                f"{record.career_pro_seasons_count} seasons, "
                f"{record.career_pro_yards} yards, "
                f"{record.career_pro_tds} TDs"
            ).classes("text-xs text-slate-500")

        # International
        if record.international_caps > 0:
            ui.separator().classes("my-2")
            ui.label("International").classes("text-sm font-semibold text-purple-700")
            ui.label(f"{record.national_team} — {record.international_caps} caps").classes("text-sm")
            if record.world_cup_appearances:
                ui.label(f"{record.world_cup_appearances} World Cup appearances").classes("text-xs text-slate-500")

        # HoF nomination
        if record.career_status != "hall_of_fame":
            async def _nominate():
                d = _get_dynasty()
                if not d:
                    return
                entry = d.nominate_hall_of_fame(record.full_name)
                if entry:
                    save_hall_of_fame_entry(entry, entry.get("player_id", record.full_name))
                    _save_dynasty(d)
                    ui.notify(f"{record.full_name} inducted into Hall of Fame!", type="positive")
                    dialog.close()

            ui.button("Nominate for Hall of Fame", icon="museum", on_click=_nominate).classes(
                "bg-amber-600 text-white mt-3"
            ).props("no-caps")

        ui.button("Close", on_click=dialog.close).props("flat no-caps")

    dialog.open()


# ═══════════════════════════════════════════════════════════════
# HALL OF FAME TAB
# ═══════════════════════════════════════════════════════════════

def _render_hof_tab(dynasty: WVLCommissionerDynasty):
    with ui.element("div").classes("w-full").style(
        "background: linear-gradient(135deg, #92400e 0%, #d97706 100%); "
        "padding: 20px 24px; border-radius: 8px; margin-bottom: 16px;"
    ):
        ui.label("Hall of Fame").classes("text-2xl font-bold text-white")
        ui.label("Permanent player cards — these survive refreshes and resets.").classes("text-sm text-amber-100")

    entries = dynasty.hall_of_fame.get_inductees(sort_by="year")

    # Also load from DB (persistent across dynasties)
    db_entries = load_hall_of_fame()
    db_names = {e.get("full_name", "").lower() for e in db_entries}
    mem_names = {e.full_name.lower() for e in entries}
    # Merge DB entries not in memory
    extra_entries = [e for e in db_entries if e.get("full_name", "").lower() not in mem_names]

    if not entries and not extra_entries:
        ui.label("No inductees yet. Players are auto-evaluated at retirement, or you can nominate anyone from the Players tab.").classes(
            "text-sm text-slate-400 italic"
        )
        return

    # Display inductees
    with ui.element("div").classes("grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"):
        for entry in entries:
            _render_hof_card(entry.to_dict())
        for entry_dict in extra_entries:
            _render_hof_card(entry_dict)


def _render_hof_card(entry: dict):
    """Render a single Hall of Fame card."""
    with ui.card().classes("p-4").style(
        "border: 2px solid #d97706; border-radius: 8px;"
    ):
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.icon("emoji_events", size="md").classes("text-amber-500")
            with ui.column().classes("gap-0"):
                ui.label(entry.get("full_name", "?")).classes("text-lg font-bold text-slate-800")
                ui.label(f"{entry.get('position', '')} — {entry.get('nationality', '')}").classes("text-xs text-slate-400")

        with ui.row().classes("gap-3 text-sm"):
            ui.label(f"OVR {entry.get('peak_overall', 0)}").classes("font-semibold text-blue-600")
            ui.label(f"{entry.get('pro_seasons', 0)} seasons").classes("text-slate-500")
            if entry.get("international_caps", 0):
                ui.label(f"{entry['international_caps']} caps").classes("text-purple-500")

        if entry.get("college_team"):
            ui.label(f"College: {entry['college_team']}").classes("text-xs text-slate-400")

        pro_teams = entry.get("pro_teams", [])
        if pro_teams:
            ui.label(f"Pro: {', '.join(pro_teams[:3])}").classes("text-xs text-slate-400")

        ui.label(f"Inducted {entry.get('induction_year', '?')} — {entry.get('induction_reason', '')}").classes(
            "text-xs text-amber-600 mt-1 italic"
        )


# ═══════════════════════════════════════════════════════════════
# HISTORY TAB
# ═══════════════════════════════════════════════════════════════

def _render_history_tab(dynasty: WVLCommissionerDynasty):
    ui.label("League History").classes("text-xl font-bold text-slate-800 mb-3")

    # Champions by year
    if dynasty.last_season_champions:
        ui.label("Most Recent Champions").classes("text-sm font-semibold text-slate-600 mb-2")
        for tier_num in sorted(dynasty.last_season_champions.keys()):
            champ_key = dynasty.last_season_champions[tier_num]
            club = CLUBS_BY_KEY.get(champ_key)
            tc = TIER_BY_NUMBER.get(tier_num)
            tier_label = tc.tier_name if tc else f"Tier {tier_num}"
            with ui.row().classes("items-center gap-2"):
                ui.icon("emoji_events", size="sm").classes("text-amber-500")
                ui.label(f"{tier_label}: {club.name if club else champ_key}").classes("text-sm")

    # FIV history
    if dynasty.fiv_history:
        ui.separator().classes("my-3")
        ui.label("World Cup History").classes("text-sm font-semibold text-slate-600 mb-2")
        for wc in reversed(dynasty.fiv_history):
            ui.label(f"Year {wc.get('year', '?')}: {wc.get('champion', '?')}").classes("text-sm")

    # Promotion/relegation history
    if dynasty.promotion_history:
        ui.separator().classes("my-3")
        ui.label("Recent Promotion/Relegation").classes("text-sm font-semibold text-slate-600 mb-2")
        recent = sorted(dynasty.promotion_history.keys(), reverse=True)[:3]
        for year in recent:
            pr = dynasty.promotion_history[year]
            movements = pr.get("movements", [])
            if movements:
                ui.label(f"Year {year}:").classes("text-xs font-semibold text-slate-500")
                for m in movements:
                    club = CLUBS_BY_KEY.get(m.get("team_key", ""))
                    name = club.name if club else m.get("team_name", "?")
                    direction = "promoted" if m.get("to_tier", 0) < m.get("from_tier", 0) else "relegated"
                    ui.label(f"  {name}: T{m.get('from_tier')} → T{m.get('to_tier')} ({direction})").classes("text-xs")

    # Expansion nations
    if dynasty.custom_nations:
        ui.separator().classes("my-3")
        ui.label("League Expansion").classes("text-sm font-semibold text-slate-600 mb-2")
        for nation in dynasty.custom_nations:
            ui.label(
                f"{nation['name']} ({nation['code']}) — {nation['confederation']}, "
                f"added Year {nation.get('added_year', '?')}"
            ).classes("text-xs")

    # Team all-time records
    ui.separator().classes("my-3")
    ui.label("All-Time Championship Leaders").classes("text-sm font-semibold text-slate-600 mb-2")
    champ_counts = []
    for key, hist in dynasty.team_histories.items():
        if hist.championship_years:
            club = CLUBS_BY_KEY.get(key)
            champ_counts.append({
                "team": club.name if club else key,
                "titles": len(hist.championship_years),
                "years": ", ".join(str(y) for y in hist.championship_years),
            })
    champ_counts.sort(key=lambda x: -x["titles"])
    for entry in champ_counts[:10]:
        ui.label(f"{entry['team']}: {entry['titles']} titles ({entry['years']})").classes("text-xs")

    if not champ_counts:
        ui.label("No championships recorded yet.").classes("text-xs text-slate-400 italic")
