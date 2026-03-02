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
# DASHBOARD HELPERS
# ═══════════════════════════════════════════════════════════════

def _ordinal(n: int) -> str:
    """Return number with ordinal suffix: 1st, 2nd, 3rd, 4th..."""
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    s = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{s}"


def _render_zone_standings(ranked: list, owner_club_key: str):
    """Render a tier's standings table with pro/rel zone row coloring."""
    columns = [
        {"name": "pos", "label": "#", "field": "pos", "align": "center"},
        {"name": "team", "label": "Team", "field": "team", "align": "left"},
        {"name": "country", "label": "", "field": "country", "align": "left"},
        {"name": "record", "label": "W-L", "field": "record", "align": "center"},
        {"name": "pct", "label": "PCT", "field": "pct", "align": "center"},
        {"name": "pf", "label": "PF", "field": "pf", "align": "right"},
        {"name": "pa", "label": "PA", "field": "pa", "align": "right"},
        {"name": "diff", "label": "DIFF", "field": "diff", "align": "right"},
        {"name": "streak", "label": "STR", "field": "streak", "align": "center"},
        {"name": "l5", "label": "L5", "field": "l5", "align": "center"},
    ]
    rows = []
    for i, t in enumerate(ranked):
        key = t.get("team_key", "")
        club_info = CLUBS_BY_KEY.get(key)
        is_owner = key == owner_club_key
        zone = t.get("zone", "safe")
        diff_val = t.get("diff", 0)
        rows.append({
            "pos": t.get("position", i + 1),
            "team": t.get("team_name", key),
            "country": club_info.country if club_info else "",
            "record": f"{t.get('wins', 0)}-{t.get('losses', 0)}",
            "pct": f"{t.get('pct', 0):.3f}",
            "pf": t.get("pf", t.get("points_for", 0)),
            "pa": t.get("pa", t.get("points_against", 0)),
            "diff": f"{diff_val:+d}" if diff_val else "0",
            "streak": t.get("streak", "-"),
            "l5": t.get("last_5", "-"),
            "_zone": zone,
            "_owner": is_owner,
        })
    table = ui.table(columns=columns, rows=rows, row_key="pos").classes(
        "w-full"
    ).props("dense flat")
    # Zone coloring: green=promotion, red=relegation, amber=playoff, indigo=owner
    table.add_slot("body", r"""
        <q-tr :props="props" :style="{
            'background-color':
                props.row._owner && props.row._zone === 'promotion' ? '#dcfce7' :
                props.row._owner && props.row._zone === 'relegation' ? '#fee2e2' :
                props.row._owner && props.row._zone === 'playoff' ? '#fef3c7' :
                props.row._owner ? '#e0e7ff' :
                props.row._zone === 'promotion' ? '#f0fdf4' :
                props.row._zone === 'relegation' ? '#fef2f2' :
                props.row._zone === 'playoff' ? '#fffbeb' : '',
            'font-weight': props.row._owner ? '700' : '400'
        }">
            <q-td v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.value }}
            </q-td>
        </q-tr>
    """)
    # Zone legend
    with ui.row().classes("gap-4 mt-1 text-[10px] text-gray-400"):
        ui.html('<span style="background:#f0fdf4;padding:2px 6px;border-radius:3px;">Promotion</span>')
        ui.html('<span style="background:#fffbeb;padding:2px 6px;border-radius:3px;">Playoff</span>')
        ui.html('<span style="background:#fef2f2;padding:2px 6px;border-radius:3px;">Relegation</span>')


def _render_preseason_tier(dynasty, tier_num: int):
    """Pre-season view: team names, country, narrative tag — no prestige."""
    teams_in_tier = [
        k for k, t in dynasty.tier_assignments.items()
        if t == tier_num
    ]
    if not teams_in_tier:
        ui.label("No teams in this tier").classes("text-gray-400 italic")
        return
    columns = [
        {"name": "pos", "label": "#", "field": "pos", "align": "center"},
        {"name": "team", "label": "Team", "field": "team", "align": "left"},
        {"name": "country", "label": "Country", "field": "country", "align": "left"},
        {"name": "tag", "label": "", "field": "tag", "align": "left"},
    ]
    rows = []
    sorted_keys = sorted(
        teams_in_tier,
        key=lambda k: CLUBS_BY_KEY[k].prestige if CLUBS_BY_KEY.get(k) else 0,
        reverse=True,
    )
    for i, key in enumerate(sorted_keys):
        club_info = CLUBS_BY_KEY.get(key)
        if club_info:
            rows.append({
                "pos": i + 1,
                "team": club_info.name,
                "country": club_info.country,
                "tag": club_info.narrative_tag or "",
                "_owner": key == dynasty.owner.club_key,
            })
    table = ui.table(columns=columns, rows=rows, row_key="pos").classes(
        "w-full"
    ).props("dense flat")
    table.add_slot("body", r"""
        <q-tr :props="props" :style="{
            'background-color': props.row._owner ? '#e0e7ff' : '',
            'font-weight': props.row._owner ? '700' : '400'
        }">
            <q-td v-for="col in props.cols" :key="col.name" :props="props">
                {{ col.value }}
            </q-td>
        </q-tr>
    """)


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

def _render_dashboard(container):
    """Main dashboard — hero header, standings, then owner/president."""
    dynasty = _get_dynasty()
    if not dynasty:
        _render_setup(container)
        return

    with container:
        club = CLUBS_BY_KEY.get(dynasty.owner.club_key)
        club_name = club.name if club else dynasty.owner.club_key
        club_tier = dynasty.tier_assignments.get(dynasty.owner.club_key, 1)
        tier_config = TIER_BY_NUMBER.get(club_tier)
        tier_name = tier_config.tier_name if tier_config else f"Tier {club_tier}"

        # ── HERO HEADER ──────────────────────────────────────
        # Club name is the headline; tier badge and bankroll are
        # the two numbers you check every time you open this screen.
        with ui.column().classes("w-full items-center py-4"):
            ui.label(club_name).classes(
                "text-3xl sm:text-4xl font-extrabold text-center"
            ).style("color: #312e81;")
            with ui.row().classes("gap-4 mt-3 justify-center flex-wrap"):
                # Tier badge — big, gradient
                with ui.card().classes("px-6 py-3 text-center").style(
                    "background: linear-gradient(135deg, #4338ca, #6366f1);"
                    "border-radius: 12px; box-shadow: 0 4px 12px rgba(99,102,241,0.3);"
                ):
                    ui.label("TIER").classes(
                        "text-[10px] font-bold uppercase tracking-widest"
                    ).style("color: #c7d2fe;")
                    ui.label(str(club_tier)).classes(
                        "text-5xl font-black leading-none"
                    ).style("color: white;")
                    ui.label(tier_name).classes("text-[11px] mt-1").style("color: #c7d2fe;")
                # Bankroll — big, gradient
                with ui.card().classes("px-6 py-3 text-center").style(
                    "background: linear-gradient(135deg, #065f46, #059669);"
                    "border-radius: 12px; box-shadow: 0 4px 12px rgba(5,150,105,0.3);"
                ):
                    ui.label("BANKROLL").classes(
                        "text-[10px] font-bold uppercase tracking-widest"
                    ).style("color: #a7f3d0;")
                    ui.label(f"${dynasty.owner.bankroll:.1f}M").classes(
                        "text-5xl font-black leading-none"
                    ).style("color: white;")
                    ui.label(f"Year {dynasty.current_year}").classes(
                        "text-[11px] mt-1"
                    ).style("color: #a7f3d0;")

        # ── ACTIONS (right below hero so sim button is easy to reach) ─
        with ui.row().classes("w-full justify-center gap-4 mb-2"):
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
                        msg_parts.append(f"{m['team_name']} {direction} (T{m['from_tier']}->T{m['to_tier']})")
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

        # ── STANDINGS ─────────────────────────────────────────
        # Your tier expanded by default, others collapsed.
        ui.separator()

        season = getattr(dynasty, "_current_season", None)
        all_standings = {}
        if season:
            try:
                all_standings = season.get_all_standings() if season.tier_seasons else {}
            except Exception:
                pass

        for tier_num in [1, 2, 3, 4]:
            tc = TIER_BY_NUMBER.get(tier_num)
            if not tc:
                continue

            tier_standings = all_standings.get(tier_num, {})
            ranked = tier_standings.get("ranked", [])
            is_owner_tier = (tier_num == club_tier)

            # Build header with owner position indicator
            header_parts = [f"Tier {tier_num} -- {tc.tier_name}"]

            if is_owner_tier and ranked:
                for i, t in enumerate(ranked):
                    if t.get("team_key") == dynasty.owner.club_key:
                        header_parts.append(
                            f"Your club: {_ordinal(i + 1)} of {len(ranked)}"
                        )
                        break
            elif is_owner_tier and not ranked:
                header_parts.append("Your tier")

            tier_season = season.tier_seasons.get(tier_num) if season else None
            if tier_season and getattr(tier_season, "champion", None):
                champ_club = CLUBS_BY_KEY.get(tier_season.champion)
                champ_name = champ_club.name if champ_club else tier_season.champion
                header_parts.append(f"Champion: {champ_name}")

            header = " | ".join(header_parts)

            with ui.expansion(header, icon="table_chart", value=is_owner_tier).classes("w-full"):
                if ranked:
                    _render_zone_standings(ranked, dynasty.owner.club_key)
                else:
                    _render_preseason_tier(dynasty, tier_num)

        # ── OWNER & PRESIDENT (compact, at the bottom) ────────
        ui.separator().classes("mt-4")
        ui.label("Management").classes(
            "text-xs font-semibold text-gray-400 uppercase tracking-wide mt-2"
        )

        with ui.row().classes("w-full gap-3 flex-wrap"):
            # Owner — compact card, name + archetype + seasons
            with ui.card().classes("flex-1 min-w-[220px] p-3"):
                arch = OWNER_ARCHETYPES.get(dynasty.owner.archetype, {})
                with ui.row().classes("items-center gap-2"):
                    ui.icon("person", size="sm").classes("text-indigo-600")
                    ui.label(dynasty.owner.name).classes("font-semibold text-sm")
                    ui.badge(
                        arch.get("label", dynasty.owner.archetype), color="indigo"
                    ).props("outline dense")
                ui.label(
                    f"Seasons: {dynasty.owner.seasons_owned}"
                ).classes("text-xs text-gray-400 ml-6")

            # President — compact card, ratings hidden behind expansion
            with ui.card().classes("flex-1 min-w-[220px] p-3"):
                if dynasty.president:
                    parch = PRESIDENT_ARCHETYPES.get(dynasty.president.archetype, {})
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("badge", size="sm").classes("text-amber-600")
                        ui.label(dynasty.president.name).classes("font-semibold text-sm")
                        ui.badge(
                            parch.get("label", ""), color="amber"
                        ).props("outline dense")
                    ui.label(
                        f"Contract: {dynasty.president.contract_years}yr"
                    ).classes("text-xs text-gray-400 ml-6")
                    with ui.expansion("Ratings").classes("w-full mt-1"):
                        with ui.row().classes("gap-4 py-1"):
                            for lbl, val in [
                                ("ACU", dynasty.president.acumen),
                                ("BDG", dynasty.president.budget_mgmt),
                                ("EYE", dynasty.president.recruiting_eye),
                                ("HIR", dynasty.president.staff_hiring),
                            ]:
                                with ui.column().classes("items-center"):
                                    ui.label(str(val)).classes(
                                        "text-lg font-bold text-gray-800"
                                    )
                                    ui.label(lbl).classes(
                                        "text-[10px] text-gray-400 uppercase"
                                    )
                else:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("warning", size="sm").classes("text-red-500")
                        ui.label("No president hired").classes("text-red-500 text-sm")


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
