"""Unified Saves / Experiments API.

The SPA's front door. The engine already persists each mode in its own
`saves` rows (save_type = college / dynasty / pro_league / wvl_season /
wvl_commissioner / season_archive). This router presents all of them as one
flat, normalized list the React Saves Library consumes, plus rename / fork /
delete. Experiment-only metadata (tags, notes) lives in a sidecar blob so we
don't touch the engine's save shapes.

A save's stable id is "<save_type>::<save_key>".
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine import db as vdb

router = APIRouter(prefix="/api/saves", tags=["saves"])

# save_type → frontend mode label. Only these surface in the library.
_TYPE_TO_MODE = {
    "college": "college",
    "dynasty": "dynasty",
    "pro_league": "pro",
    "wvl_career_league": "wvl",
    "wvl_season": "wvl",
    "wvl_commissioner": "wvl",
    "season_archive": "fiv",  # archives are mostly completed college/FIV cycles
}
_META_TYPE = "save_meta"  # sidecar: tags + notes keyed by save id

SEP = "::"


def _split_id(save_id: str) -> tuple[str, str]:
    if SEP not in save_id:
        raise HTTPException(status_code=400, detail="bad save id")
    save_type, save_key = save_id.split(SEP, 1)
    return save_type, save_key


def _meta_for(save_id: str) -> dict:
    return vdb.load_blob(_META_TYPE, save_id) or {}


def _iso(epoch: float | None) -> str:
    if not epoch:
        return ""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


class SaveSummary(BaseModel):
    id: str
    name: str
    mode: str
    teams: str
    progress: str
    seed: Optional[int]
    tags: list[str]
    notes: str
    createdAt: str
    lastSimmedAt: str


def _to_summary(save_type: str, meta_row: dict) -> SaveSummary:
    save_key = meta_row["save_key"]
    save_id = f"{save_type}{SEP}{save_key}"
    extra = _meta_for(save_id)
    mode = _TYPE_TO_MODE.get(save_type, save_type)
    teams = extra.get("teams", "")
    progress = extra.get("progress", "")
    # Season archives carry their own type/champion/counts in a sidecar meta blob.
    if save_type == "season_archive":
        am = vdb.load_season_archive_meta(save_key) or {}
        mode = am.get("type", "college") if am.get("type") in ("college", "fiv") else "college"
        if not teams and am.get("team_count"):
            teams = f"{am['team_count']} teams"
        if not progress:
            champ = am.get("champion")
            gp, tg = am.get("games_played", 0), am.get("total_games", 0)
            progress = f"🏆 {champ}" if champ else (f"{gp}/{tg} games" if tg else "")
    return SaveSummary(
        id=save_id,
        name=meta_row.get("label") or save_key,
        mode=mode,
        teams=teams,
        progress=progress,
        seed=extra.get("seed"),
        tags=extra.get("tags", []),
        notes=extra.get("notes", ""),
        createdAt=_iso(meta_row.get("created_at")),
        lastSimmedAt=_iso(meta_row.get("updated_at")),
    )


@router.get("", response_model=list[SaveSummary])
def list_all_saves():
    """Every experiment across every mode, newest first."""
    out: list[SaveSummary] = []
    for save_type in _TYPE_TO_MODE:
        for row in vdb.list_saves(save_type=save_type):
            out.append(_to_summary(save_type, row))
    out.sort(key=lambda s: s.lastSimmedAt, reverse=True)
    return out


class PatchSave(BaseModel):
    name: Optional[str] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None


@router.patch("/{save_id:path}", response_model=SaveSummary)
def patch_save(save_id: str, patch: PatchSave):
    save_type, save_key = _split_id(save_id)
    rows = {r["save_key"]: r for r in vdb.list_saves(save_type=save_type)}
    if save_key not in rows:
        raise HTTPException(status_code=404, detail="save not found")

    if patch.name is not None:
        vdb.update_save_label(save_type, save_key, patch.name)

    if patch.tags is not None or patch.notes is not None:
        meta = _meta_for(save_id)
        if patch.tags is not None:
            meta["tags"] = patch.tags
        if patch.notes is not None:
            meta["notes"] = patch.notes
        vdb.save_blob(_META_TYPE, save_id, meta)

    # Re-read for fresh label/timestamp.
    rows = {r["save_key"]: r for r in vdb.list_saves(save_type=save_type)}
    return _to_summary(save_type, rows[save_key])


@router.post("/{save_id:path}/fork", response_model=SaveSummary)
def fork(save_id: str):
    save_type, save_key = _split_id(save_id)
    new_key = uuid.uuid4().hex
    if not vdb.fork_save(save_type, save_key, new_key):
        raise HTTPException(status_code=404, detail="save not found")
    # Carry tags/notes onto the fork too.
    src_meta = _meta_for(save_id)
    if src_meta:
        vdb.save_blob(_META_TYPE, f"{save_type}{SEP}{new_key}", src_meta)
    row = next(
        (r for r in vdb.list_saves(save_type=save_type) if r["save_key"] == new_key),
        None,
    )
    if row is None:
        raise HTTPException(status_code=500, detail="fork failed")
    return _to_summary(save_type, row)


@router.delete("/{save_id:path}", status_code=204)
def delete(save_id: str):
    save_type, save_key = _split_id(save_id)
    vdb.delete_blob(save_type, save_key)
    vdb.delete_blob(_META_TYPE, save_id)
    if save_type == "college":
        # Clear the league's box scores and archive summary too.
        vdb.delete_box_scores_for_session(save_key)
        try:
            vdb.delete_season_archive(save_key)
        except Exception:
            pass
    elif save_type == "season_archive":
        # Removes both the snapshot and its summary meta.
        try:
            vdb.delete_season_archive(save_key)
        except Exception:
            pass
        # Auto-saved college runs are keyed "college_<session_id>"; drop their box scores.
        if save_key.startswith("college_"):
            vdb.delete_box_scores_for_session(save_key[len("college_"):])
    return None
