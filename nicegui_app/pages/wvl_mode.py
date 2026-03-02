"""
WVL Owner Mode — NiceGUI UI Page
==================================

Owner mode interface for the Women's Viperball League.
The human acts as a club owner with 4 levers:
1. Owner archetype (chosen at setup)
2. President hire/fire
3. One targeted free agent per offseason
4. Investment allocation

Everything else is autonomous simulation.
"""

from nicegui import ui, app
from typing import Optional

from engine.wvl_config import (
    ALL_CLUBS, CLUBS_BY_KEY, CLUBS_BY_TIER, ALL_WVL_TIERS,
    TIER_BY_NUMBER, RIVALRIES,
)
from engine.wvl_owner import (
    OWNER_ARCHETYPES, PRESIDENT_ARCHETYPES,
    generate_president_pool, InvestmentAllocation,
)
from engine.wvl_dynasty import create_wvl_dynasty, WVLDynasty


# ═══════════════════════════════════════════════════════════════
# STATE KEYS (stored in app.storage.user)
# ═══════════════════════════════════════════════════════════════

_WVL_DYNASTY_KEY = "wvl_dynasty"
_WVL_PHASE_KEY = "wvl_phase"  # "setup" | "pre_season" | "in_season" | "offseason"


def _get_dynasty() -> Optional[WVLDynasty]:
    return app.storage.user.get(_WVL_DYNASTY_KEY)


def _set_dynasty(dynasty: Optional[WVLDynasty]):
    app.storage.user[_WVL_DYNASTY_KEY] = dynasty


def _get_phase() -> str:
    return app.storage.user.get(_WVL_PHASE_KEY, "setup")


def _set_phase(phase: str):
    app.storage.user[_WVL_PHASE_KEY] = phase


def _register_wvl_season(dynasty, season):
    """Register completed WVL season in shared state for the stats site."""
    try:
        from api.main import wvl_sessions
        session_id = f"wvl_{dynasty.dynasty_name}_{dynasty.current_year - 1}"
        session_id = session_id.lower().replace(" ", "_").replace("'", "")
        wvl_sessions[session_id] = {
            "season": season,
            "dynasty": dynasty,
            "dynasty_name": dynasty.dynasty_name,
            "year": dynasty.current_year - 1,
            "club_key": dynasty.owner.club_key,
        }
    except Exception:
        pass  # Stats site not available


# ═══════════════════════════════════════════════════════════════
# SETUP PAGE
# ═══════════════════════════════════════════════════════════════

def _render_setup(container):
    """Render the WVL setup flow — pick owner archetype, club, and president."""

    with container:
        ui.label("Women's Viperball League").classes("text-2xl font-bold text-indigo-700")
        ui.label("Galactic Premiership — Owner Mode").classes("text-lg text-gray-500 mb-4")

        ui.separator()

        # Step 1: Owner details
        ui.label("Step 1: Create Your Owner").classes("text-lg font-semibold mt-4")

        name_input = ui.input("Owner Name", value="").classes("w-64")

        ui.label("Owner Archetype:").classes("font-medium mt-2")
        archetype_select = ui.select(
            options={k: f"{v['label']} — {v['description']}" for k, v in OWNER_ARCHETYPES.items()},
            value="patient_builder",
        ).classes("w-full")

        # Step 2: Pick a club
        ui.label("Step 2: Pick Your Club").classes("text-lg font-semibold mt-6")
        ui.label("Choose from any tier — even Tier 4 for the ultimate challenge.").classes("text-sm text-gray-400")

        club_options = {}
        for tier_num in [1, 2, 3, 4]:
            tier_config = TIER_BY_NUMBER[tier_num]
            for club in CLUBS_BY_TIER[tier_num]:
                tag = f" [{club.narrative_tag}]" if club.narrative_tag else ""
                club_options[club.key] = f"T{tier_num}: {club.name} ({club.country}){tag}"

        club_select = ui.select(
            options=club_options,
            value="vimpeli",
        ).classes("w-full")

        # Step 3: Start
        ui.separator().classes("mt-4")

        async def _start():
            owner_name = name_input.value.strip() or "The Owner"
            archetype = archetype_select.value
            club_key = club_select.value

            dynasty = create_wvl_dynasty(
                dynasty_name=f"{owner_name}'s WVL",
                owner_name=owner_name,
                owner_archetype=archetype,
                club_key=club_key,
            )

            # Generate initial president pool
            import random
            pool = generate_president_pool(5, random.Random())
            dynasty.president = pool[0]  # Auto-assign first president for now

            _set_dynasty(dynasty)
            _set_phase("pre_season")
            ui.notify(f"Dynasty created! You own {CLUBS_BY_KEY[club_key].name}.", type="positive")
            container.clear()
            _render_dashboard(container)

        ui.button("Start Dynasty", on_click=_start).classes(
            "mt-4 bg-indigo-600 text-white px-6 py-2 rounded-lg"
        )


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

def _render_dashboard(container):
    """Main dashboard showing all 4 tiers, owner info, and actions."""
    dynasty = _get_dynasty()
    if not dynasty:
        _render_setup(container)
        return

    with container:
        club = CLUBS_BY_KEY.get(dynasty.owner.club_key)
        club_name = club.name if club else dynasty.owner.club_key
        club_tier = dynasty.tier_assignments.get(dynasty.owner.club_key, 1)

        # Header
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(f"WVL — Year {dynasty.current_year}").classes("text-2xl font-bold text-indigo-700")
            with ui.row().classes("gap-4 items-center"):
                ui.label(f"{club_name}").classes("text-lg font-semibold")
                ui.badge(f"Tier {club_tier}", color="indigo")
                ui.label(f"${dynasty.owner.bankroll:.1f}M").classes("text-green-600 font-mono")

        ui.separator()

        # Owner & President info
        with ui.row().classes("w-full gap-6"):
            with ui.card().classes("flex-1"):
                ui.label("Owner").classes("font-semibold text-gray-500 text-sm")
                arch = OWNER_ARCHETYPES.get(dynasty.owner.archetype, {})
                ui.label(f"{dynasty.owner.name}").classes("text-lg")
                ui.label(f"{arch.get('label', dynasty.owner.archetype)}").classes("text-sm text-gray-400")
                ui.label(f"Seasons: {dynasty.owner.seasons_owned} | Bankroll: ${dynasty.owner.bankroll:.1f}M")

            with ui.card().classes("flex-1"):
                ui.label("President").classes("font-semibold text-gray-500 text-sm")
                if dynasty.president:
                    parch = PRESIDENT_ARCHETYPES.get(dynasty.president.archetype, {})
                    ui.label(f"{dynasty.president.name}").classes("text-lg")
                    ui.label(f"{parch.get('label', '')} — Contract: {dynasty.president.contract_years}yr").classes("text-sm text-gray-400")
                    ui.label(
                        f"Acumen: {dynasty.president.acumen} | Budget: {dynasty.president.budget_mgmt} | "
                        f"Eye: {dynasty.president.recruiting_eye} | Hiring: {dynasty.president.staff_hiring}"
                    ).classes("text-xs text-gray-400 font-mono")
                else:
                    ui.label("No president hired!").classes("text-red-500")

        ui.separator()

        # 4-Tier Standings
        ui.label("League Standings").classes("text-lg font-semibold mt-4")

        for tier_num in [1, 2, 3, 4]:
            tier_config = TIER_BY_NUMBER.get(tier_num)
            if not tier_config:
                continue

            with ui.expansion(f"Tier {tier_num} — {tier_config.tier_name}", icon="table_chart").classes("w-full"):
                teams_in_tier = [
                    k for k, t in dynasty.tier_assignments.items()
                    if t == tier_num
                ]
                if teams_in_tier:
                    with ui.column().classes("w-full gap-1"):
                        for key in sorted(teams_in_tier, key=lambda k: CLUBS_BY_KEY.get(k, None).prestige if CLUBS_BY_KEY.get(k) else 0, reverse=True):
                            club_info = CLUBS_BY_KEY.get(key)
                            if club_info:
                                is_owner = key == dynasty.owner.club_key
                                style = "font-bold text-indigo-600" if is_owner else "text-gray-700"
                                tag = f" [{club_info.narrative_tag}]" if club_info.narrative_tag else ""
                                ui.label(
                                    f"{'> ' if is_owner else '  '}{club_info.name} ({club_info.country}) "
                                    f"— Prestige: {club_info.prestige}{tag}"
                                ).classes(f"text-sm font-mono {style}")
                else:
                    ui.label("No teams in this tier").classes("text-gray-400 italic")

        ui.separator()

        # Actions
        with ui.row().classes("gap-4 mt-4"):
            async def _sim_season():
                import random
                rng = random.Random()

                season = dynasty.start_season()
                if not season.tier_seasons:
                    ui.notify("No team files found. Run scripts/generate_wvl_teams.py first.", type="warning")
                    return

                ui.notify("Simulating full season...", type="info")
                season.run_full_season()

                dynasty.advance_season(season, rng)
                offseason = dynasty.run_offseason(season, investment_budget=5.0, rng=rng)

                _set_dynasty(dynasty)

                # Register season in shared state for stats site
                _register_wvl_season(dynasty, season)

                ui.notify(
                    f"Season {dynasty.current_year - 1} complete! "
                    f"Bankroll: ${dynasty.owner.bankroll:.1f}M",
                    type="positive",
                )

                # Show pro/rel results
                prom_rel = offseason.get("promotion_relegation", {})
                movements = prom_rel.get("movements", [])
                if movements:
                    msg_parts = []
                    for m in movements:
                        direction = "promoted" if m["to_tier"] < m["from_tier"] else "relegated"
                        msg_parts.append(f"{m['team_name']} {direction} (T{m['from_tier']}→T{m['to_tier']})")
                    ui.notify("Pro/Rel: " + "; ".join(msg_parts[:5]), type="info")

                container.clear()
                _render_dashboard(container)

            ui.button("Sim Season", on_click=_sim_season).classes(
                "bg-green-600 text-white px-6 py-2 rounded-lg"
            )

            async def _reset():
                _set_dynasty(None)
                _set_phase("setup")
                container.clear()
                _render_setup(container)

            ui.button("New Dynasty", on_click=_reset).classes(
                "bg-red-600 text-white px-4 py-2 rounded-lg"
            )


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

async def render_wvl_section(state, shared):
    """Main entry point for the WVL nav section."""
    container = ui.column().classes("w-full max-w-5xl mx-auto p-4")

    dynasty = _get_dynasty()
    if dynasty:
        _render_dashboard(container)
    else:
        _render_setup(container)
