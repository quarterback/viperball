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
    with ui.card().classes("p-3 min-w-[120px]").style(
        "background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;"
    ):
        ui.label(label).classes("text-xs font-semibold uppercase tracking-wide").style("color: #64748b;")
        ui.label(str(value)).classes("text-2xl font-bold").style("color: #0f172a;")
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
