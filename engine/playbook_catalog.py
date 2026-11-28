"""
Viperball playbook catalog (PLAYBOOK track, PBK-01 / PBK-02 / PBK-04).

A read only catalog of the sport's scheme families and the packages that
can be installed from them. Data lives in data/playbooks/*.json; this
module loads it, checks every ID against the live engine, and answers
lookups. It never changes engine behavior: the COACH track's resolver
decides what gets installed and called (see the coach and playbook PRD on
docs PR #324).

Families are the engine's 16 offensive styles and 8 defensive schemes.
Family records combine the engine's own numbers (play types, formations,
kick pass mix, matchups, defensive ratings) with catalog notes.

A package starts in one family (origin_family) and lists the families
that can install it (compatible_families). That is how a coach running
one book uses plays from another: an East Coast team can install Ground &
Pound's Heavy Push for short yardage.

Public functions (the PRD's PLAYBOOK side of the shared contract):

    get_scheme_family(side, scheme_id) -> dict
    get_package(package_id) -> dict
    list_compatible_packages(side, scheme_id) -> list[dict]

Plus:

    validate_catalog(families, packages, vocabulary) -> list[str]
    roster_tags(team_stats) -> set[str]
    packages_for_roster(side, scheme_id, team_stats) -> list[dict]
    inventory_markdown() -> str

Run `python -m engine.playbook_catalog` to validate the catalog and print
the inventory.
"""

from __future__ import annotations

import copy
import json
import os
import re

from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Set

from .offensive_concepts import CORNER_CHASE

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "playbooks")

SIDES = ("offense", "defense")
_SLUG = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")
# Families with no identity of their own: they can install packages but
# are never a package's origin.
NO_ORIGIN = {"balanced"}
# Terminal kicks and kneels are gated by the game state. The validator
# permits Pindown Chase as a narrowly scoped punt plan.
_NOT_PACKAGE_FAMILIES = {"snap_kick", "field_goal", "punt", "kneel", "territory_kick"}

_REQUIRED_PACKAGE_FIELDS = (
    "version", "package_id", "side", "name", "origin_family", "compatible_families",
    "formation_tags", "play_family_tags", "kick_pass_tags", "personnel_tags",
    "situation_tags", "countered_by", "tradeoffs", "inspiration", "scenario",
    "benefits", "cost", "counter", "summary",
)
_TEXT_FIELDS = ("name", "inspiration", "scenario", "benefits", "cost", "counter", "summary")
_LIST_FIELDS = ("compatible_families", "formation_tags", "play_family_tags",
                "kick_pass_tags", "personnel_tags", "situation_tags",
                "countered_by", "tradeoffs")


class CatalogError(ValueError):
    """The catalog data failed validation."""


def _engine():
    from engine import game_engine as ge
    return ge


def _engine_ids() -> Dict[str, Set[str]]:
    ge = _engine()
    return {
        "offense": set(ge.OFFENSE_STYLES),
        "defense": set(ge.DEFENSE_STYLES),
        "play_families": {f.value for f in ge.PlayFamily} - _NOT_PACKAGE_FAMILIES,
        "kick_pass": {k.value for k in ge.KickPassSubFamily},
        "formations": set(getattr(ge, "DEFAULT_FORMATION_WEIGHTS", {"tight": 0, "split": 0, "spread": 0, "heavy": 0})),
    }


def _read(name: str) -> dict:
    with open(os.path.join(_DATA_DIR, name), encoding="utf-8") as fh:
        return json.load(fh)


# ── Validation ──

def validate_catalog(families: dict, packages: dict, vocabulary: dict) -> List[str]:
    """Every problem found, as plain sentences. Empty means valid."""
    errs: List[str] = []
    ids = _engine_ids()
    situations = set((vocabulary or {}).get("situations", {}))
    personnel = set((vocabulary or {}).get("personnel", {}))
    formations = set((vocabulary or {}).get("formations", []))

    if formations != ids["formations"]:
        errs.append(f"vocabulary formations {sorted(formations)} do not match the engine's {sorted(ids['formations'])}")
    for tag, rec in (vocabulary or {}).get("personnel", {}).items():
        if not isinstance(rec, dict) or "stat" not in rec or "min" not in rec:
            errs.append(f"personnel tag {tag} needs a stat and a min")

    for side in SIDES:
        fam = (families or {}).get(side, {})
        missing = ids[side] - set(fam)
        extra = set(fam) - ids[side]
        if missing:
            errs.append(f"{side} families missing from the catalog: {sorted(missing)}")
        if extra:
            errs.append(f"{side} families in the catalog but not the engine: {sorted(extra)}")
        for fid, rec in fam.items():
            if not isinstance(rec, dict):
                errs.append(f"{side} family {fid} is not a record")
                continue
            for t in rec.get("strong_in", []):
                if t not in situations:
                    errs.append(f"{side} family {fid}: unknown situation {t}")
            for t in rec.get("personnel", []):
                if t not in personnel:
                    errs.append(f"{side} family {fid}: unknown personnel tag {t}")
            if side == "offense" and fid in ids["offense"]:
                style = _engine().OFFENSE_STYLES[fid]
                for f in rec.get("signature_fields", []):
                    if f not in style:
                        errs.append(f"offense family {fid}: signature field {f} is not in its engine style")

    pk_list = (packages or {}).get("packages")
    if not isinstance(pk_list, list):
        return errs + ["packages.json needs a packages list"]
    seen: Set[str] = set()
    by_side = {s: set() for s in SIDES}
    for p in pk_list:
        if isinstance(p, dict) and p.get("side") in SIDES and isinstance(p.get("package_id"), str):
            by_side[p["side"]].add(p["package_id"])
    for i, p in enumerate(pk_list):
        where = f"package {i}"
        if not isinstance(p, dict):
            errs.append(f"{where} is not a record")
            continue
        pid = p.get("package_id")
        where = f"package {pid or i}"
        for f in _REQUIRED_PACKAGE_FIELDS:
            if f not in p:
                errs.append(f"{where}: missing {f}")
        if any(f not in p for f in ("side", "package_id")):
            continue
        if not isinstance(pid, str) or not _SLUG.match(pid):
            errs.append(f"{where}: package_id must be a lowercase slug")
        if pid in seen:
            errs.append(f"{where}: duplicate package_id")
        seen.add(pid)
        side = p["side"]
        if side not in SIDES:
            errs.append(f"{where}: side must be offense or defense")
            continue
        other = "defense" if side == "offense" else "offense"
        for f in _TEXT_FIELDS:
            if f in p and (not isinstance(p[f], str) or not p[f].strip()):
                errs.append(f"{where}: {f} must be non-empty text")
        for f in _LIST_FIELDS:
            if f in p and not isinstance(p[f], list):
                errs.append(f"{where}: {f} must be a list")
        if any(not isinstance(p.get(f, []), list) for f in _LIST_FIELDS):
            continue
        origin = p.get("origin_family")
        if origin not in ids[side]:
            errs.append(f"{where}: origin_family {origin} is not a {side} family")
        elif origin in NO_ORIGIN:
            errs.append(f"{where}: {origin} has no identity to borrow from")
        compat = p.get("compatible_families", [])
        if not compat:
            errs.append(f"{where}: no compatible families")
        for fid in compat:
            if fid not in ids[side]:
                errs.append(f"{where}: compatible family {fid} is not a {side} family")
        if origin in ids[side] and origin not in compat:
            errs.append(f"{where}: its origin family must be able to install it")
        for t in p.get("formation_tags", []):
            if t not in ids["formations"]:
                errs.append(f"{where}: unknown formation {t}")
        if side == "offense" and not p.get("formation_tags"):
            errs.append(f"{where}: an offensive package needs at least one formation")
        if not p.get("play_family_tags"):
            errs.append(f"{where}: needs at least one play family")
        for t in p.get("play_family_tags", []):
            if t not in ids["play_families"] and not (pid == CORNER_CHASE and side == "offense" and t == "punt"):
                errs.append(f"{where}: {t} is not an installable play family")
        for t in p.get("kick_pass_tags", []):
            if t not in ids["kick_pass"]:
                errs.append(f"{where}: unknown kick pass subfamily {t}")
        if side == "offense" and p.get("kick_pass_tags") and "kick_pass" not in p.get("play_family_tags", []):
            errs.append(f"{where}: kick pass tags need the kick_pass play family")
        if not p.get("situation_tags"):
            errs.append(f"{where}: needs at least one situation")
        for t in p.get("situation_tags", []):
            if t not in situations:
                errs.append(f"{where}: unknown situation {t}")
        for t in p.get("personnel_tags", []):
            if t not in personnel:
                errs.append(f"{where}: unknown personnel tag {t}")
        if not p.get("countered_by"):
            errs.append(f"{where}: needs a counter")
        for c in p.get("countered_by", []):
            if c not in ids[other] and c not in by_side[other]:
                errs.append(f"{where}: counter {c} is not a {other} family or package")
        if not p.get("tradeoffs"):
            errs.append(f"{where}: needs at least one tradeoff")
        for t in p.get("tradeoffs", []):
            if not isinstance(t, str) or not _SLUG.match(t):
                errs.append(f"{where}: tradeoff {t!r} must be a lowercase slug")
    return errs


# ── Loading ──

@lru_cache(maxsize=1)
def _catalog() -> dict:
    vocabulary = _read("vocabulary.json")
    families = _read("families.json")
    packages = _read("packages.json")
    errs = validate_catalog(families, packages, vocabulary)
    if errs:
        raise CatalogError("Playbook catalog is invalid:\n  " + "\n  ".join(errs))
    return {"vocabulary": vocabulary, "families": families,
            "packages": {p["package_id"]: p for p in packages["packages"]}}


def vocabulary() -> dict:
    return copy.deepcopy(_catalog()["vocabulary"])


def _defense_strong_in(d: dict) -> List[str]:
    """Where a defensive scheme's own ratings say it is strong."""
    sit = d.get("situational", {})
    tags = []
    if sit.get("short_yardage_modifier", 1.0) <= 0.85:
        tags.append("short_yardage")
    if sit.get("red_zone_read_boost", 0.0) >= 0.10 and sit.get("short_yardage_modifier", 1.0) <= 0.90:
        tags.append("goal_line")
    if sit.get("long_yardage_modifier", 1.0) <= 0.90:
        tags.append("long_yardage")
    if d.get("kick_suppression", 1.0) <= 0.85:
        tags.append("kick_range")
    if sit.get("leading_conserve", 0.0) >= 0.10 and d.get("explosive_suppression", 1.0) <= 0.78:
        tags.append("protect_lead")
    if d.get("explosive_suppression", 1.0) <= 0.60:
        tags.append("two_minute")
    if sit.get("trailing_aggression", 0.0) >= 0.10:
        tags.append("chasing")
    return tags


def _top(d: dict, n: int, skip: Iterable[str] = ()) -> List[dict]:
    items = [(k, v) for k, v in (d or {}).items() if k not in set(skip) and v > 0]
    items.sort(key=lambda x: -x[1])
    return [{"id": k, "weight": round(v, 3)} for k, v in items[:n]]


def get_scheme_family(side: str, scheme_id: str) -> dict:
    """One family record: catalog notes plus the engine's own numbers."""
    if side not in SIDES:
        raise KeyError(f"side must be offense or defense, not {side!r}")
    cat = _catalog()
    fam = cat["families"][side]
    if scheme_id not in fam:
        raise KeyError(f"no {side} family {scheme_id!r}")
    ge = _engine()
    rec = copy.deepcopy(fam[scheme_id])
    rec.update({"version": 1, "side": side, "scheme_id": scheme_id})
    matchup = getattr(ge, "OFFENSE_VS_DEFENSE_MATCHUP", {})
    if side == "offense":
        st = ge.OFFENSE_STYLES[scheme_id]
        rec["label"] = st.get("label", scheme_id)
        rec["description"] = st.get("description", "")
        rec["top_play_families"] = _top(st.get("weights", {}), 4, _NOT_PACKAGE_FAMILIES)
        rec["formation_mix"] = {k: round(v, 3) for k, v in st.get("formation_weights", {}).items()}
        rec["kick_pass_mix"] = {k: round(v, 3) for k, v in st.get("kick_pass_weights", {}).items()}
        vs = {d: matchup.get((scheme_id, d), 1.0) for d in ge.DEFENSE_STYLES}
        rec["best_against"] = [d for d, v in sorted(vs.items(), key=lambda x: -x[1])[:2] if v > 1.0]
        rec["worst_against"] = [d for d, v in sorted(vs.items(), key=lambda x: x[1])[:2] if v < 1.0]
    else:
        d = ge.DEFENSE_STYLES[scheme_id]
        rec["label"] = d.get("label", scheme_id)
        rec["description"] = d.get("description", "")
        rec["strong_in"] = _defense_strong_in(d)
        mods = d.get("play_family_modifiers", {})
        rec["stops_best"] = [k for k, _ in sorted(mods.items(), key=lambda x: x[1])[:3]]
        rec["weakest_against"] = [k for k, _ in sorted(mods.items(), key=lambda x: -x[1])[:2]]
        vs = {o: matchup.get((o, scheme_id), 1.0) for o in ge.OFFENSE_STYLES}
        rec["beats"] = [o for o, v in sorted(vs.items(), key=lambda x: x[1])[:2] if v < 1.0]
        rec["beaten_by"] = [o for o, v in sorted(vs.items(), key=lambda x: -x[1])[:2] if v > 1.0]
    rec["packages"] = [p["package_id"] for p in list_compatible_packages(side, scheme_id)]
    rec["origin_of"] = sorted(pid for pid, p in cat["packages"].items()
                              if p["side"] == side and p["origin_family"] == scheme_id)
    return rec


def get_package(package_id: str) -> dict:
    pk = _catalog()["packages"]
    if package_id not in pk:
        raise KeyError(f"no package {package_id!r}")
    return copy.deepcopy(pk[package_id])


def list_compatible_packages(side: str, scheme_id: str) -> List[dict]:
    """Packages a team running this family can install, sorted by ID.
    Includes packages borrowed from other families."""
    if side not in SIDES:
        raise KeyError(f"side must be offense or defense, not {side!r}")
    pk = _catalog()["packages"]
    return [copy.deepcopy(p) for pid, p in sorted(pk.items())
            if p["side"] == side and scheme_id in p["compatible_families"]]


def same_look_formations(first: dict, second: dict) -> List[str]:
    """Shared offensive formations with distinct advancement options."""
    if first["side"] != "offense" or second["side"] != "offense":
        return []
    first_families = set(first["play_family_tags"]) - _NOT_PACKAGE_FAMILIES
    second_families = set(second["play_family_tags"]) - _NOT_PACKAGE_FAMILIES
    first_actions = (first_families, set(first["kick_pass_tags"]))
    second_actions = (second_families, set(second["kick_pass_tags"]))
    if not first_families or not second_families or first_actions == second_actions:
        return []
    return sorted(set(first["formation_tags"]) & set(second["formation_tags"]))


# ── PBK-04: what a roster can run ──

def roster_tags(team_stats: Optional[dict]) -> Set[str]:
    """Personnel tags a team's team_stats block satisfies."""
    out = set()
    stats = team_stats or {}
    for tag, rule in _catalog()["vocabulary"]["personnel"].items():
        v = stats.get(rule["stat"])
        if isinstance(v, (int, float)) and v >= rule["min"]:
            out.add(tag)
    return out


def packages_for_roster(side: str, scheme_id: str, team_stats: Optional[dict]) -> List[dict]:
    """Every package this family can install, with whether this roster
    meets its personnel needs and what is missing. Selection and saving
    are the COACH track's job; this only reports."""
    have = roster_tags(team_stats)
    out = []
    for p in list_compatible_packages(side, scheme_id):
        missing = [t for t in p["personnel_tags"] if t not in have]
        out.append({
            "package_id": p["package_id"],
            "name": p["name"],
            "origin_family": p["origin_family"],
            "borrowed": p["origin_family"] != scheme_id,
            "situation_tags": p["situation_tags"],
            "meets_personnel": not missing,
            "missing_personnel": missing,
        })
    return out


# ── Inventory (PBK-01) ──

def inventory_markdown() -> str:
    ge = _engine()
    cat = _catalog()
    voc = cat["vocabulary"]
    sit = lambda tags: ", ".join(voc["situations"][t]["plain"] for t in tags) or "on matchups"
    lines = ["# Playbook catalog inventory", "",
             "Generated by `python -m engine.playbook_catalog` from the engine and `data/playbooks/`.", ""]
    lines += ["## Offensive families", "",
              "| Family | Strong in | Packages it can install | Packages that start here |",
              "|---|---|---|---|"]
    for fid in sorted(ge.OFFENSE_STYLES):
        f = get_scheme_family("offense", fid)
        lines.append(f"| {f['label']} | {sit(f.get('strong_in', []))} | {len(f['packages'])} | "
                     f"{', '.join(get_package(p)['name'] for p in f['origin_of']) or 'none'} |")
    lines += ["", "## Defensive families", "",
              "| Family | Strong in (from its ratings) | Packages it can install | Packages that start here |",
              "|---|---|---|---|"]
    for fid in sorted(ge.DEFENSE_STYLES):
        f = get_scheme_family("defense", fid)
        lines.append(f"| {f['label']} | {sit(f['strong_in'])} | {len(f['packages'])} | "
                     f"{', '.join(get_package(p)['name'] for p in f['origin_of']) or 'none'} |")
    for side in SIDES:
        lines += ["", f"## {side.title()} packages", "",
                  "| Package | From | Called | Needs | Countered by |", "|---|---|---|---|---|"]
        for pid, p in sorted(cat["packages"].items()):
            if p["side"] != side:
                continue
            origin = get_scheme_family(side, p["origin_family"])["label"]
            needs = ", ".join(voc["personnel"][t]["plain"] for t in p["personnel_tags"]) or "nothing special"
            other = "defense" if side == "offense" else "offense"
            def _name(c):
                if c in cat["packages"]:
                    return cat["packages"][c]["name"]
                return get_scheme_family(other, c)["label"]
            lines.append(f"| {p['name']} | {origin} | {sit(p['situation_tags'])} | {needs} | "
                         f"{', '.join(_name(c) for c in p['countered_by'])} |")
    lines += ["", f"Counts: {len(ge.OFFENSE_STYLES)} offensive families, {len(ge.DEFENSE_STYLES)} defensive "
              f"families, {len(voc['formations'])} formations, {len(_engine_ids()['kick_pass'])} kick pass "
              f"subfamilies, {sum(1 for p in cat['packages'].values() if p['side'] == 'offense')} offensive "
              f"and {sum(1 for p in cat['packages'].values() if p['side'] == 'defense')} defensive packages.", ""]
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    print(inventory_markdown())
