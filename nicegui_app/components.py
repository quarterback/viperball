"""Reusable UI components for the NiceGUI Viperball app.

Provides metric cards, score displays, team selectors, data tables
with pagination, loading skeletons, and other shared widgets.
"""

from __future__ import annotations

import io
import csv
import json
import math
from typing import Optional

from nicegui import ui


# ═══════════════════════════════════════════════════════════════
# P5.js SKETCH EMBED
# ═══════════════════════════════════════════════════════════════

def p5_sketch(sketch_name: str, container_id: str, data: dict | None = None,
              width: str = "100%", height: str = "400px",
              extra_classes: str = "", extra_style: str = ""):
    """Embed a P5.js sketch canvas with optional data injection."""
    style = f"width: {width}; height: {height}; {extra_style}"
    ui.html(f'<div id="{container_id}" class="{extra_classes}" style="{style}"></div>')

    js_parts = []
    if data is not None:
        data_json = json.dumps(data)
        var_name = f"_vb{container_id.replace('-', '_')}Data"
        js_parts.append(f"window.{var_name} = {data_json};")

    js_parts.append(f"""
        var s = document.createElement('script');
        s.src = '/sketches/{sketch_name}.js';
        document.head.appendChild(s);
    """)
    ui.run_javascript("\n".join(js_parts))


# ═══════════════════════════════════════════════════════════════
# METRIC CARD
# ═══════════════════════════════════════════════════════════════

def metric_card(label: str, value, delta: str = "", icon: str = ""):
    """Render a KPI metric card with optional icon and delta."""
    with ui.card().classes("p-3 min-w-[100px] flex-1").style(
        "background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; "
        "box-shadow: 0 1px 3px rgba(0,0,0,0.04);"
    ):
        with ui.row().classes("items-center gap-2"):
            if icon:
                ui.icon(icon).classes("text-sm").style("color: #94a3b8;")
            ui.label(label).classes("text-[11px] font-semibold uppercase tracking-wider").style("color: #94a3b8;")
        ui.label(str(value)).classes("text-xl sm:text-2xl font-extrabold mt-0.5").style("color: #0f172a; line-height: 1.2;")
        if delta:
            ui.label(delta).classes("text-xs mt-0.5").style("color: #64748b;")


# ═══════════════════════════════════════════════════════════════
# SCORE DISPLAY
# ═══════════════════════════════════════════════════════════════

def score_display(team_name: str, score):
    """Render a big score display for game results."""
    with ui.column().classes("items-center"):
        ui.label(team_name).classes("text-base font-semibold").style("color: #475569;")
        ui.label(str(score)).classes("text-5xl font-extrabold").style("color: #0f172a; line-height: 1;")


# ═══════════════════════════════════════════════════════════════
# DATA TABLE WITH PAGINATION
# ═══════════════════════════════════════════════════════════════

def stat_table(rows: list[dict], columns: Optional[list[str]] = None,
               rows_per_page: int = 25, title: str = "", searchable: bool = False):
    """Render a paginated, sortable data table.

    - ``rows_per_page``: number of rows per page (0 = no pagination).
    - ``title``: optional title shown above the table.
    - ``searchable``: adds a search/filter input above the table.
    """
    if not rows:
        ui.label("No data available.").classes("text-sm text-slate-400 italic py-4")
        return

    if columns is None:
        columns = list(rows[0].keys())

    col_defs = []
    for col in columns:
        col_defs.append({
            "name": col,
            "label": col,
            "field": col,
            "align": "left",
            "sortable": True,
        })

    clean_rows = []
    for row in rows:
        clean_rows.append({k: str(v) if v is not None else "" for k, v in row.items()})

    with ui.element("div").classes("w-full"):
        # Title + row count header
        if title or len(clean_rows) > 10:
            with ui.row().classes("items-center justify-between mb-1 px-1"):
                if title:
                    ui.label(title).classes("text-sm font-semibold text-slate-600")
                else:
                    ui.element("span")
                ui.label(f"{len(clean_rows)} rows").classes("text-[11px] text-slate-400")

        with ui.element("div").classes("w-full overflow-x-auto").style(
            "border: 1px solid #e2e8f0; border-radius: 8px;"
        ):
            pagination_val = rows_per_page if rows_per_page > 0 else 0
            tbl = ui.table(
                columns=col_defs,
                rows=clean_rows,
                pagination=pagination_val if pagination_val else None,
            ).classes("w-full")
            tbl.props("dense flat bordered separator=cell")
            tbl.style("""
                .q-table th { background: #f8fafc; font-weight: 700; font-size: 11px;
                  text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; }
                .q-table td { font-size: 13px; }
                .q-table tbody tr:hover { background: #f1f5f9; }
            """)

            if searchable:
                tbl.props('filter=""')
                with tbl.add_slot("top-left"):
                    with ui.input(placeholder="Search...").props(
                        "dense outlined clearable"
                    ).classes("text-xs w-48").bind_value(tbl, "filter") as search_input:
                        with search_input.add_slot("prepend"):
                            ui.icon("search").classes("text-slate-400")

    return tbl


# ═══════════════════════════════════════════════════════════════
# LOADING SKELETONS
# ═══════════════════════════════════════════════════════════════

_SKELETON_STYLE = (
    "background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%); "
    "background-size: 200% 100%; "
    "animation: vb-shimmer 1.5s infinite; "
    "border-radius: 8px;"
)

_SKELETON_KEYFRAMES = """
<style>
@keyframes vb-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
</style>
"""

_skeleton_css_injected = False


def _ensure_skeleton_css():
    global _skeleton_css_injected
    if not _skeleton_css_injected:
        ui.add_head_html(_SKELETON_KEYFRAMES)
        _skeleton_css_injected = True


def loading_skeleton(height: str = "200px", width: str = "100%"):
    """Render a single shimmer loading placeholder."""
    _ensure_skeleton_css()
    ui.element("div").style(
        f"height: {height}; width: {width}; {_SKELETON_STYLE}"
    )


def loading_card_skeleton(count: int = 3):
    """Render skeleton placeholders resembling metric cards."""
    _ensure_skeleton_css()
    with ui.row().classes("w-full gap-3 flex-wrap"):
        for _ in range(count):
            with ui.element("div").classes("flex-1 min-w-[120px]").style(
                f"height: 80px; {_SKELETON_STYLE}"
            ):
                pass


def loading_table_skeleton(row_count: int = 8):
    """Render a skeleton that looks like a table loading."""
    _ensure_skeleton_css()
    with ui.element("div").classes("w-full").style(
        "border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;"
    ):
        # Header row
        ui.element("div").style(
            f"height: 36px; width: 100%; background: #f1f5f9; border-bottom: 1px solid #e2e8f0;"
        )
        # Data rows
        for i in range(row_count):
            ui.element("div").style(
                f"height: 32px; width: 100%; {_SKELETON_STYLE} "
                f"border-radius: 0; animation-delay: {i * 0.05}s; "
                f"border-bottom: 1px solid #f1f5f9;"
            )


def loading_page_skeleton():
    """Full page loading skeleton with cards + table placeholder."""
    _ensure_skeleton_css()
    with ui.column().classes("w-full gap-4"):
        # Title placeholder
        ui.element("div").style(f"height: 28px; width: 200px; {_SKELETON_STYLE}")
        # Metric cards
        loading_card_skeleton(4)
        # Table
        loading_table_skeleton(6)


# ═══════════════════════════════════════════════════════════════
# SECTION HEADER
# ═══════════════════════════════════════════════════════════════

def section_header(title: str, subtitle: str = "", icon: str = ""):
    """Render a consistent section header with optional icon and subtitle."""
    with ui.row().classes("items-center gap-2 mb-1"):
        if icon:
            ui.icon(icon).classes("text-2xl").style("color: #6366f1;")
        ui.label(title).classes("text-2xl font-extrabold").style("color: #0f172a;")
    if subtitle:
        ui.label(subtitle).classes("text-sm mb-4").style("color: #64748b;")


# ═══════════════════════════════════════════════════════════════
# EMPTY STATE
# ═══════════════════════════════════════════════════════════════

def empty_state(message: str, icon: str = "inbox", action_label: str = "", on_action=None):
    """Render a centered empty-state placeholder."""
    with ui.column().classes("w-full items-center py-12"):
        ui.icon(icon).classes("text-6xl").style("color: #cbd5e1;")
        ui.label(message).classes("text-base mt-3").style("color: #94a3b8;")
        if action_label and on_action:
            ui.button(action_label, on_click=on_action).props("no-caps color=indigo outline").classes("mt-4")


# ═══════════════════════════════════════════════════════════════
# DOWNLOAD BUTTON
# ═══════════════════════════════════════════════════════════════

def download_button(label: str, data, filename: str, mime: str = "text/csv"):
    """Render a download button."""
    if isinstance(data, str):
        data = data.encode("utf-8")

    async def _download():
        ui.download(data, filename)

    ui.button(label, on_click=_download, icon="download").props("no-caps outline").classes(
        "text-sm"
    )


# ═══════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

def _safe_notify(msg: str, **kwargs):
    try:
        ui.notify(msg, **kwargs)
    except RuntimeError:
        pass


def notify_success(msg: str):
    _safe_notify(msg, type="positive", position="top")


def notify_error(msg: str):
    _safe_notify(msg, type="negative", position="top")


def notify_warning(msg: str):
    _safe_notify(msg, type="warning", position="top")


def notify_info(msg: str):
    _safe_notify(msg, type="info", position="top")


# ═══════════════════════════════════════════════════════════════
# COACHING SNAPSHOT CARD
# ═══════════════════════════════════════════════════════════════

_ROLE_DISPLAY = {
    "head_coach": "HC",
    "oc": "OC",
    "dc": "DC",
    "stc": "STC",
}


def coaching_snapshot_card(snapshot: dict, team_name: str, bg_class: str = "bg-slate-50"):
    """Render a compact coaching staff snapshot card."""
    if not snapshot:
        return

    hc = snapshot.get("head_coach", {})
    hc_name = hc.get("name", "Unknown")
    hc_class = hc.get("classification", "")
    hc_stars = hc.get("star_rating", 0)
    hc_comp = hc.get("composure", "")
    hc_aff = hc.get("hc_affinity", "")
    star_str = "\u2605" * hc_stars + "\u2606" * (5 - hc_stars) if hc_stars else ""

    with ui.card().classes(f"w-full p-3 {bg_class}").style(
        "border-radius: 10px; border: 1px solid #e2e8f0;"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.label(team_name).classes("font-bold text-sm text-slate-700")
            if star_str:
                ui.label(star_str).classes("text-sm text-amber-500")
        with ui.row().classes("items-center gap-2 mt-0.5"):
            ui.label(f"HC {hc_name}").classes("text-xs text-slate-600")
            if hc_class:
                ui.badge(hc_class).props("outline").classes("text-xs")
            if hc_comp:
                ui.badge(hc_comp).props("outline color=grey").classes("text-xs")
            if hc_aff and hc_aff != "Balanced":
                ui.badge(hc_aff).props("outline color=blue-grey").classes("text-xs")

        coord_parts = []
        for role_key in ("oc", "dc", "stc"):
            card = snapshot.get(role_key, {})
            if card:
                role_label = _ROLE_DISPLAY.get(role_key, role_key.upper())
                name = card.get("name", "")
                cls = card.get("classification", "")
                tag = f"{role_label}: {name}"
                if cls:
                    tag += f" ({cls})"
                coord_parts.append(tag)
        if coord_parts:
            ui.label(" | ".join(coord_parts)).classes("text-xs text-gray-500 mt-0.5")

        attrs = []
        if hc.get("leadership"):
            attrs.append(f"LDR {hc['leadership']}")
        if hc.get("rotations"):
            attrs.append(f"ROT {hc['rotations']}")
        if hc.get("overall"):
            attrs.append(f"OVR {hc['overall']}")
        if attrs:
            ui.label(" | ".join(attrs)).classes("text-xs text-gray-400")


# ═══════════════════════════════════════════════════════════════
# LAZY TAB HELPER
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# PLAYER RATING BADGES
# ═══════════════════════════════════════════════════════════════

_RATING_DISPLAY_ATTRS = [
    ("SPD", "speed"), ("STA", "stamina"), ("KICK", "kicking"),
    ("LAT", "lateral_skill"), ("TKL", "tackling"), ("AGI", "agility"),
    ("PWR", "power"), ("AWR", "awareness"), ("HND", "hands"),
    ("KPW", "kick_power"), ("KAC", "kick_accuracy"),
]


def rating_badge_color(val: int) -> tuple[str, str, str]:
    """Return (bg, fg, border) color tuple for a rating value."""
    if val >= 85:
        return "#dcfce7", "#166534", "#86efac"
    elif val >= 75:
        return "#dbeafe", "#1e40af", "#93c5fd"
    elif val >= 65:
        return "#fef3c7", "#92400e", "#fcd34d"
    else:
        return "#f1f5f9", "#475569", "#cbd5e1"


def render_rating_badges(ratings: dict, attrs: list | None = None):
    """Render compact rating badges from a player dict.

    ``ratings`` should map keys like "speed", "stamina", etc. to int values.
    ``attrs`` is an optional list of (abbr, key) tuples; defaults to all standard attrs.
    """
    if attrs is None:
        attrs = _RATING_DISPLAY_ATTRS
    with ui.element("div").classes("flex flex-wrap gap-1"):
        for abbr, key in attrs:
            val = ratings.get(key, 0)
            bg, fg, bd = rating_badge_color(val)
            with ui.element("div").classes(
                "flex flex-col items-center px-1.5 py-0.5 rounded"
            ).style(f"background:{bg}; color:{fg}; border:1px solid {bd}; min-width:42px;"):
                ui.label(abbr).classes("text-[9px] font-bold leading-tight")
                ui.label(str(val)).classes("text-xs font-extrabold leading-tight")


def render_ovr_display(ovr: int):
    """Render the large OVR number with color coding."""
    ovr_color = "#16a34a" if ovr >= 85 else ("#d97706" if ovr >= 75 else "#64748b")
    ui.label("OVR").classes("text-[10px] font-bold text-slate-400 mb-0")
    ui.label(str(ovr)).classes("text-4xl font-extrabold mb-2").style(
        f"color:{ovr_color}; line-height:1;"
    )


def render_bio_line(label: str, value):
    """Render a labeled bio line (e.g. 'Position: QB')."""
    with ui.row().classes("gap-1 items-baseline"):
        ui.label(f"{label}:").classes("text-xs font-bold text-slate-500")
        ui.label(str(value)).classes("text-xs text-slate-800")


# ═══════════════════════════════════════════════════════════════
# LAZY TAB HELPER
# ═══════════════════════════════════════════════════════════════

class LazyTabManager:
    """Helper for lazy-loading tab panel content.

    Usage::

        lazy = LazyTabManager()

        async def on_tab_change(tab_key):
            if lazy.is_loaded(tab_key):
                return
            lazy.mark_loaded(tab_key)
            panel_containers[tab_key].clear()
            with panel_containers[tab_key]:
                await render_tab_content(tab_key)
    """

    def __init__(self):
        self._loaded: set[str] = set()

    def is_loaded(self, key: str) -> bool:
        return key in self._loaded

    def mark_loaded(self, key: str):
        self._loaded.add(key)

    def reset(self, key: str | None = None):
        if key:
            self._loaded.discard(key)
        else:
            self._loaded.clear()
