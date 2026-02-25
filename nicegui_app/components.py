"""Reusable UI components for the NiceGUI Viperball app.

Provides metric cards, score displays, team selectors, and data tables
that replace Streamlit-specific widgets.
"""

from __future__ import annotations

import io
import csv
import json
from typing import Optional

from nicegui import ui


def metric_card(label: str, value, delta: str = ""):
    """Render a KPI metric card (replaces st.metric)."""
    with ui.card().classes("p-3 min-w-[100px] flex-1").style(
        "background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;"
    ):
        ui.label(label).classes("text-xs font-semibold uppercase tracking-wide").style("color: #64748b;")
        ui.label(str(value)).classes("text-xl sm:text-2xl font-bold").style("color: #0f172a;")
        if delta:
            ui.label(delta).classes("text-sm").style("color: #64748b;")


def score_display(team_name: str, score):
    """Render a big score display for game results."""
    with ui.column().classes("items-center"):
        ui.label(team_name).classes("text-base font-semibold").style("color: #475569;")
        ui.label(str(score)).classes("text-5xl font-extrabold").style("color: #0f172a; line-height: 1;")


def stat_table(rows: list[dict], columns: Optional[list[str]] = None):
    """Render a data table from a list of dicts (replaces st.dataframe).

    Uses NiceGUI's ui.table with auto-generated column definitions.
    """
    if not rows:
        ui.label("No data available.").classes("text-sm text-gray-400 italic")
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

    with ui.element("div").classes("w-full overflow-x-auto"):
        ui.table(columns=col_defs, rows=clean_rows).classes("w-full").props("dense flat")


def download_button(label: str, data, filename: str, mime: str = "text/csv"):
    """Render a download button (replaces st.download_button)."""
    if isinstance(data, str):
        data = data.encode("utf-8")

    async def _download():
        ui.download(data, filename)

    ui.button(label, on_click=_download, icon="download").classes("w-full")


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


_ROLE_DISPLAY = {
    "head_coach": "HC",
    "oc": "OC",
    "dc": "DC",
    "stc": "STC",
}


def coaching_snapshot_card(snapshot: dict, team_name: str, bg_class: str = "bg-slate-50"):
    """Render a compact coaching staff snapshot card.

    ``snapshot`` is the dict produced by ViperballEngine._coaching_snapshot(),
    containing per-role dicts with name, classification, composure, etc.
    """
    if not snapshot:
        return

    hc = snapshot.get("head_coach", {})
    hc_name = hc.get("name", "Unknown")
    hc_class = hc.get("classification", "")
    hc_stars = hc.get("star_rating", 0)
    hc_comp = hc.get("composure", "")
    hc_aff = hc.get("hc_affinity", "")
    star_str = "\u2605" * hc_stars + "\u2606" * (5 - hc_stars) if hc_stars else ""

    with ui.card().classes(f"w-full p-2 {bg_class} rounded"):
        # HC headline
        with ui.row().classes("items-center gap-2"):
            ui.label(team_name).classes("font-bold text-sm text-slate-700")
            if star_str:
                ui.label(star_str).classes("text-sm text-amber-500")
        with ui.row().classes("items-center gap-2"):
            ui.label(f"HC {hc_name}").classes("text-xs text-slate-600")
            if hc_class:
                ui.badge(hc_class).props("outline").classes("text-xs")
            if hc_comp:
                ui.badge(hc_comp).props("outline color=grey").classes("text-xs")
            if hc_aff and hc_aff != "Balanced":
                ui.badge(hc_aff).props("outline color=blue-grey").classes("text-xs")

        # Coordinator row
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
            ui.label(" | ".join(coord_parts)).classes("text-xs text-gray-500")

        # Key attributes row
        attrs = []
        if hc.get("leadership"):
            attrs.append(f"LDR {hc['leadership']}")
        if hc.get("rotations"):
            attrs.append(f"ROT {hc['rotations']}")
        if hc.get("overall"):
            attrs.append(f"OVR {hc['overall']}")
        if attrs:
            ui.label(" | ".join(attrs)).classes("text-xs text-gray-400")
