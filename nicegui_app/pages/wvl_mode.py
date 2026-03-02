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
_WVL_SEASON_KEY = "wvl_last_season"  # stores last completed WVLMultiTierSeason (not persisted to disk)


def _get_dynasty() -> Optional[WVLDynasty]:
    raw = app.storage.user.get(_WVL_DYNASTY_KEY)
    if raw is None:
        return None
    if isinstance(raw, WVLDynasty):
        return raw
    try:
        return WVLDynasty.from_dict(raw)
    except Exception:
        return None


def _set_dynasty(dynasty: Optional[WVLDynasty]):
    app.storage.user[_WVL_DYNASTY_KEY] = dynasty.to_dict() if dynasty is not None else None


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
    """Main dashboard — hero header, standings, results, then management."""
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

        # Pull persisted standings (plain dicts — survive serialization)
        all_standings = getattr(dynasty, "last_season_standings", {}) or {}
        owner_results = getattr(dynasty, "last_season_owner_results", []) or []
        champions = getattr(dynasty, "last_season_champions", {}) or {}

        # Compute owner's position and form from persisted data
        owner_position = None
        owner_tier_total = None
        owner_record = None
        owner_zone = "safe"
        owner_form = ""
        # Look in the tier the owner was in when the season was played
        # (before pro/rel changed assignments). Check all tiers.
        for t_num, st in all_standings.items():
            for i, t in enumerate(st.get("ranked", [])):
                if t.get("team_key") == dynasty.owner.club_key:
                    owner_position = i + 1
                    owner_tier_total = len(st.get("ranked", []))
                    owner_record = f"{t.get('wins', 0)}-{t.get('losses', 0)}"
                    owner_zone = t.get("zone", "safe")
                    owner_form = t.get("last_5", "")
                    break
            if owner_position:
                break
        # Also compute form from game results if standings don't have it
        if not owner_form and owner_results:
            owner_form = "".join(r.get("result", "?") for r in owner_results[-5:])

        # Tier-specific colors
        _TIER_COLORS = {
            1: ("#b8860b", "#ffd700", "#fffacd"),  # gold
            2: ("#6b7280", "#9ca3af", "#f3f4f6"),  # silver
            3: ("#92400e", "#d97706", "#fef3c7"),  # bronze
            4: ("#334155", "#64748b", "#f1f5f9"),  # slate
        }
        tier_dark, tier_mid, tier_light = _TIER_COLORS.get(club_tier, _TIER_COLORS[4])

        # Bankroll health
        bankroll = dynasty.owner.bankroll
        if bankroll >= 50:
            bank_color, bank_bg = "#065f46", "linear-gradient(135deg, #065f46, #059669)"
        elif bankroll >= 20:
            bank_color, bank_bg = "#92400e", "linear-gradient(135deg, #92400e, #d97706)"
        else:
            bank_color, bank_bg = "#991b1b", "linear-gradient(135deg, #991b1b, #dc2626)"

        # ── HERO HEADER ──────────────────────────────────────
        with ui.column().classes("w-full items-center py-4"):
            ui.label(club_name).classes(
                "text-3xl sm:text-4xl font-extrabold text-center"
            ).style("color: #312e81;")

            # Position + record line
            if owner_position and owner_record:
                pos_text = f"{_ordinal(owner_position)} of {owner_tier_total} | {owner_record}"
                zone_color = {
                    "promotion": "#16a34a", "playoff": "#d97706",
                    "relegation": "#dc2626",
                }.get(owner_zone, "#475569")
                ui.label(pos_text).classes(
                    "text-lg font-bold mt-1"
                ).style(f"color: {zone_color};")

            # Form dots (last 5 results)
            if owner_form:
                with ui.row().classes("gap-1 mt-1 justify-center"):
                    for ch in owner_form[-5:]:
                        color = {"W": "#16a34a", "L": "#dc2626", "D": "#d97706"}.get(ch, "#9ca3af")
                        ui.html(
                            f'<span style="display:inline-block;width:22px;height:22px;'
                            f'border-radius:50%;background:{color};color:white;'
                            f'font-size:11px;font-weight:700;line-height:22px;'
                            f'text-align:center;">{ch}</span>'
                        )

            with ui.row().classes("gap-4 mt-3 justify-center flex-wrap"):
                # Tier badge — tier-specific color
                with ui.card().classes("px-6 py-3 text-center").style(
                    f"background: linear-gradient(135deg, {tier_dark}, {tier_mid});"
                    f"border-radius: 12px; box-shadow: 0 4px 12px {tier_mid}44;"
                ):
                    ui.label("TIER").classes(
                        "text-[10px] font-bold uppercase tracking-widest"
                    ).style(f"color: {tier_light};")
                    ui.label(str(club_tier)).classes(
                        "text-5xl font-black leading-none"
                    ).style("color: white;")
                    ui.label(tier_name).classes("text-[11px] mt-1").style(f"color: {tier_light};")
                # Bankroll — health-colored
                with ui.card().classes("px-6 py-3 text-center").style(
                    f"background: {bank_bg};"
                    f"border-radius: 12px; box-shadow: 0 4px 12px {bank_color}44;"
                ):
                    ui.label("BANKROLL").classes(
                        "text-[10px] font-bold uppercase tracking-widest"
                    ).style("color: rgba(255,255,255,0.7);")
                    ui.label(f"${bankroll:.1f}M").classes(
                        "text-5xl font-black leading-none"
                    ).style("color: white;")
                    ui.label(f"Year {dynasty.current_year}").classes(
                        "text-[11px] mt-1"
                    ).style("color: rgba(255,255,255,0.7);")

        # ── ACTIONS ───────────────────────────────────────────
        # CVL graduates import (optional)
        cached_graduates = app.storage.user.get("cvl_graduates")
        cached_year = app.storage.user.get("cvl_graduates_year", "")
        _import_state = {"data": cached_graduates}  # None = use synthetic players

        with ui.expansion(
            "CVL Graduates" + (
                f" — {len(cached_graduates)} players ready (Year {cached_year})"
                if cached_graduates else " (optional)"
            ),
            icon="school",
            value=bool(cached_graduates),
        ).classes("w-full mb-2"):
            if cached_graduates:
                with ui.row().classes("items-center gap-3 mb-2"):
                    ui.icon("check_circle").classes("text-green-600")
                    ui.label(
                        f"{len(cached_graduates)} graduates from CVL Year {cached_year} "
                        "are loaded and will be used in free agency."
                    ).classes("text-sm text-green-700 font-semibold")
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Clear (use synthetic players instead)",
                        icon="close",
                        on_click=lambda: (
                            app.storage.user.pop("cvl_graduates", None),
                            app.storage.user.pop("cvl_graduates_year", None),
                            _import_state.update({"data": None}),
                            ui.notify("Cleared — will use synthetic free agents.", type="info"),
                        ),
                    ).props("flat dense no-caps size=sm color=red-6")
            else:
                ui.label(
                    "No CVL graduates loaded. Run a CVL dynasty season, then use "
                    "Export → Dynasty Data → Export Graduates for WVL. "
                    "Or paste a file path below."
                ).classes("text-xs text-gray-500 mb-1")

            ui.label("Or load from file path:").classes("text-xs text-gray-400 mt-1")
            cvl_import_input = ui.input(
                "Path to CVL graduating class JSON",
                placeholder="/path/to/graduates.json",
            ).classes("w-full font-mono text-sm")

        # Engine toggle (persisted in a local mutable for this render scope)
        _engine_opts = {"use_fast_sim": True}
        with ui.row().classes("items-center gap-3 mb-1"):
            ui.label("Simulation engine:").classes("text-xs text-gray-500")
            engine_toggle = ui.toggle(
                {True: "Fast sim", False: "Full engine"},
                value=True,
                on_change=lambda e: _engine_opts.update({"use_fast_sim": e.value}),
            ).props("dense no-caps")
            ui.tooltip(
                "Fast sim: instant bulk season (recommended). "
                "Full engine: rich play-by-play box scores but ~100× slower — "
                "expect several minutes for a full season."
            )

        with ui.row().classes("w-full justify-center gap-4 mb-2"):
            async def _sim_season():
                import random
                rng = random.Random()

                season = dynasty.start_season()
                if not season.tier_seasons:
                    ui.notify("No team files found. Run scripts/generate_wvl_teams.py first.", type="warning")
                    return

                use_fast = _engine_opts["use_fast_sim"]
                label = "fast sim" if use_fast else "full engine"
                ui.notify(f"Simulating full season ({label})...", type="info")
                season.run_full_season(use_fast_sim=use_fast)

                # Snapshot season data BEFORE advance (tier assignments still match)
                dynasty.snapshot_season(season)

                dynasty.advance_season(season, rng)

                # Pass CVL graduates: prefer in-memory cache, fall back to file path
                import_data = _import_state.get("data")
                import_path = cvl_import_input.value.strip() or None
                offseason = dynasty.run_offseason(
                    season,
                    investment_budget=5.0,
                    import_data=import_data,
                    import_path=import_path if not import_data else None,
                    rng=rng,
                )

                _set_dynasty(dynasty)

                # Store season for box score lookups this session
                app.storage.user[_WVL_SEASON_KEY] = season

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
                app.storage.user.pop(_WVL_SEASON_KEY, None)
                container.clear()
                _render_setup(container)

            ui.button("New Dynasty", on_click=_reset).classes(
                "bg-red-600 text-white px-4 py-2 rounded-lg"
            )

        # ── STANDINGS ─────────────────────────────────────────
        # Read from persisted snapshot (plain dicts — survives serialization)
        ui.separator()

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

            champ_key = champions.get(tier_num)
            if champ_key:
                champ_club = CLUBS_BY_KEY.get(champ_key)
                champ_name = champ_club.name if champ_club else champ_key
                header_parts.append(f"Champion: {champ_name}")

            header = " | ".join(header_parts)

            with ui.expansion(header, icon="table_chart", value=is_owner_tier).classes("w-full"):
                if ranked:
                    _render_zone_standings(ranked, dynasty.owner.club_key)
                else:
                    _render_preseason_tier(dynasty, tier_num)

        # ── YOUR SEASON RESULTS ───────────────────────────────
        if owner_results:
            ui.separator().classes("mt-2")
            with ui.expansion(
                f"Your Season Results ({len(owner_results)} games)",
                icon="sports_football",
                value=False,
            ).classes("w-full"):
                columns = [
                    {"name": "wk", "label": "Wk", "field": "wk", "align": "center"},
                    {"name": "result", "label": "", "field": "result", "align": "center"},
                    {"name": "score", "label": "Score", "field": "score", "align": "center"},
                    {"name": "loc", "label": "", "field": "loc", "align": "center"},
                    {"name": "opponent", "label": "Opponent", "field": "opponent", "align": "left"},
                ]
                rows = []
                for g in owner_results:
                    rows.append({
                        "wk": g.get("week", ""),
                        "result": g.get("result", ""),
                        "score": f"{g.get('my_score', 0)}-{g.get('opp_score', 0)}",
                        "loc": g.get("location", ""),
                        "opponent": g.get("opponent", ""),
                        "_result": g.get("result", ""),
                    })
                tbl = ui.table(columns=columns, rows=rows, row_key="wk").classes(
                    "w-full"
                ).props("dense flat")
                tbl.add_slot("body", r"""
                    <q-tr :props="props" :style="{
                        'background-color':
                            props.row._result === 'W' ? '#f0fdf4' :
                            props.row._result === 'L' ? '#fef2f2' : ''
                    }">
                        <q-td v-for="col in props.cols" :key="col.name" :props="props"
                              :style="col.name === 'result' ? {
                                  'color': props.row._result === 'W' ? '#16a34a' :
                                           props.row._result === 'L' ? '#dc2626' : '#d97706',
                                  'font-weight': '700'
                              } : {}">
                            {{ col.value }}
                        </q-td>
                    </q-tr>
                """)

        # ── SCHEDULE & BOX SCORES ─────────────────────────────
        last_season = app.storage.user.get(_WVL_SEASON_KEY)
        if last_season is not None:
            owner_tier = dynasty.tier_assignments.get(dynasty.owner.club_key, 1)
            # owner_tier is the NEW tier after pro/rel; find schedule in the tier they played in
            # Check stored schedule keys (recorded before pro/rel)
            schedule_tier = None
            for t_num, sched in (getattr(dynasty, "last_season_schedule", {}) or {}).items():
                for wk in sched.get("weeks", []):
                    for g in wk.get("games", []):
                        if (g.get("home_key") == dynasty.owner.club_key or
                                g.get("away_key") == dynasty.owner.club_key):
                            schedule_tier = t_num
                            break
                    if schedule_tier is not None:
                        break
                if schedule_tier is not None:
                    break
            if schedule_tier is None:
                schedule_tier = owner_tier

            schedule_data = last_season.get_schedule(schedule_tier)
            weeks = schedule_data.get("weeks", [])
            if weeks:
                ui.separator().classes("mt-2")

                def _show_box(tier_num, wk, mk):
                    from nicegui_app.pages.pro_leagues import _show_box_score_dialog
                    box = last_season.get_box_score(tier_num, wk, mk)
                    if box:
                        _show_box_score_dialog(box)
                    else:
                        ui.notify("Box score not available.", type="warning")

                with ui.expansion(
                    f"Schedule & Box Scores (Tier {schedule_tier})",
                    icon="sports_football",
                    value=False,
                ).classes("w-full"):
                    week_options = {w["week"]: f"Week {w['week']}" for w in weeks}
                    selected_sched_week = {"val": weeks[-1]["week"] if weeks else 1}
                    sched_container = ui.column().classes("w-full")

                    def _fill_sched_week():
                        sched_container.clear()
                        wk = selected_sched_week["val"]
                        week_data = next((w for w in weeks if w["week"] == wk), None)
                        if not week_data:
                            return
                        with sched_container:
                            for game in week_data["games"]:
                                with ui.card().classes("p-3 mb-2 w-full").style("border: 1px solid #e2e8f0;"):
                                    is_owner = (
                                        game.get("home_key") == dynasty.owner.club_key or
                                        game.get("away_key") == dynasty.owner.club_key
                                    )
                                    card_style = "border-left: 3px solid #6366f1;" if is_owner else ""
                                    if game.get("completed"):
                                        h_score = int(game.get("home_score", 0))
                                        a_score = int(game.get("away_score", 0))
                                        h_bold = "font-bold" if h_score > a_score else ""
                                        a_bold = "font-bold" if a_score > h_score else ""
                                        with ui.row().classes("items-center gap-3 flex-wrap"):
                                            ui.label(game["away_name"]).classes(f"text-sm {a_bold} min-w-[160px]")
                                            ui.label(str(a_score)).classes(f"text-lg {a_bold} w-8 text-center")
                                            ui.label("@").classes("text-xs text-slate-400")
                                            ui.label(str(h_score)).classes(f"text-lg {h_bold} w-8 text-center")
                                            ui.label(game["home_name"]).classes(f"text-sm {h_bold}")
                                            mk = game.get("matchup_key", "")
                                            if mk:
                                                ui.button(
                                                    "Box Score",
                                                    icon="assessment",
                                                    on_click=lambda mk=mk, wk=wk, t=schedule_tier: _show_box(t, wk, mk),
                                                ).props("flat dense no-caps size=sm color=indigo")
                                    else:
                                        with ui.row().classes("items-center gap-3"):
                                            ui.label(game["away_name"]).classes("text-sm min-w-[160px]")
                                            ui.label("@").classes("text-xs text-slate-400")
                                            ui.label(game["home_name"]).classes("text-sm")
                                            ui.label("Upcoming").classes("text-xs text-slate-400 italic")

                    def _on_sched_week_change(e):
                        selected_sched_week["val"] = e.value
                        _fill_sched_week()

                    ui.select(
                        options=week_options,
                        value=selected_sched_week["val"],
                        label="Select Week",
                        on_change=_on_sched_week_change,
                    ).classes("w-40 mb-3")

                    _fill_sched_week()

        # ── STATS LEADERS ─────────────────────────────────────
        if last_season is not None and last_season.tier_seasons:
            leaders = last_season.get_all_stat_leaders()
            if any(leaders.values()):
                ui.separator().classes("mt-2")
                with ui.expansion("Season Stats — All Players", icon="leaderboard", value=False).classes("w-full"):
                    from nicegui_app.pages.pro_leagues import _show_player_card as _show_pc

                    def _wvl_stat_table(data: list, col_spec: list):
                        """Sortable full-roster table with clickable player names."""
                        if not data:
                            ui.label("No data yet.").classes("text-sm text-slate-400")
                            return
                        columns = [
                            {"name": k, "label": lbl, "field": k, "sortable": True,
                             "align": "left" if k in ("name", "team") else "center"}
                            for k, lbl in col_spec
                        ]
                        rows = [
                            {**{k: p.get(k, "") for k, _ in col_spec},
                             "team_key": p["team_key"], "tier_num": p["tier_num"],
                             "_idx": i}
                            for i, p in enumerate(data)
                        ]
                        tbl = (
                            ui.table(columns=columns, rows=rows, row_key="_idx")
                            .classes("w-full")
                            .props("dense flat bordered virtual-scroll")
                            .style("max-height: 420px;")
                        )
                        tbl.add_slot("body-cell-name", '''
                            <q-td :props="props">
                                <a class="text-indigo-600 font-semibold cursor-pointer hover:underline"
                                   @click="$parent.$emit('player_click', props.row)">
                                    {{ props.row.name }}
                                </a>
                            </q-td>
                        ''')
                        def _on_player_click(e, _tbl=tbl):
                            tier_num = e.args.get("tier_num", 0)
                            team_key = e.args.get("team_key", "")
                            name = e.args.get("name", "")
                            ts = last_season.tier_seasons.get(tier_num)
                            if not ts:
                                ui.notify("Player data not available.", type="warning")
                                return
                            # Look up college career history from dynasty rosters
                            career = None
                            for card in dynasty._team_rosters.get(team_key, []):
                                if card.full_name == name:
                                    career = [s.to_dict() for s in card.career_seasons]
                                    break
                            _show_pc(ts, team_key, name, career_seasons=career)

                        tbl.on("player_click", _on_player_click)

                    with ui.tabs().classes("w-full") as stat_tabs:
                        tab_rush  = ui.tab("Rushing")
                        tab_kp    = ui.tab("Kick-Pass")
                        tab_score = ui.tab("Scoring")
                        tab_def   = ui.tab("Defense")
                        tab_total = ui.tab("Total Yards")

                    with ui.tab_panels(stat_tabs, value=tab_rush).classes("w-full"):
                        with ui.tab_panel(tab_rush):
                            _wvl_stat_table(leaders.get("rushing", []), [
                                ("name", "Player"), ("team", "Team"), ("tier", "Tier"),
                                ("yards", "Rush Yds"), ("carries", "Car"), ("ypc", "YPC"),
                                ("games", "GP"),
                            ])
                        with ui.tab_panel(tab_kp):
                            _wvl_stat_table(leaders.get("kick_pass", []), [
                                ("name", "Player"), ("team", "Team"), ("tier", "Tier"),
                                ("yards", "KP Yds"), ("completions", "Comp"),
                                ("attempts", "Att"), ("pct", "Pct%"), ("games", "GP"),
                            ])
                        with ui.tab_panel(tab_score):
                            _wvl_stat_table(leaders.get("scoring", []), [
                                ("name", "Player"), ("team", "Team"), ("tier", "Tier"),
                                ("touchdowns", "TD"), ("dk_made", "DK"), ("games", "GP"),
                            ])
                        with ui.tab_panel(tab_def):
                            _wvl_stat_table(leaders.get("tackles", []), [
                                ("name", "Player"), ("team", "Team"), ("tier", "Tier"),
                                ("tackles", "TKL"), ("fumbles", "FUM"), ("games", "GP"),
                            ])
                        with ui.tab_panel(tab_total):
                            _wvl_stat_table(leaders.get("total_yards", []), [
                                ("name", "Player"), ("team", "Team"), ("tier", "Tier"),
                                ("total_yards", "Total"), ("rushing", "Rush"),
                                ("kick_pass", "KP"), ("games", "GP"),
                            ])

        # ── MANAGEMENT (compact, bottom) ──────────────────────
        ui.separator().classes("mt-4")
        with ui.expansion("Management", icon="business_center").classes("w-full"):
            with ui.row().classes("w-full gap-3 flex-wrap"):
                # Owner
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

                # President
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
