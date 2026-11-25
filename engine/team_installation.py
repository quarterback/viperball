"""Team installation and career progression (CCH-04).

Layer 3 of the coach and playbook plan: what a team has actually learned.

A coordinator's signature (CCH-01) is hers and moves with her. A team's
installation is the program's: how well the roster knows the current
coordinator's system, what is left of the previous coordinator's habits,
how well it knows its base book, and which catalog packages (PBK-02) it
has installed. It changes with hires, scheme changes, games and offseasons,
and it is saved with the dynasty.

Game effect, offense (decisions only, inside CCH-02's bounds):

  * The OC's formation, play family and kick pass biases are scaled by
    familiarity, so a new OC's tendencies show partly in year one.
  * The previous OC's biases linger as a fading trace (vestigial plays).
  * Installed packages pull formation, play family and kick pass choices
    toward the package's tags, only in the package's own situations, and
    only as much as the team knows the package.

All of it goes through coach_tactics.apply_weight_bias, which clamps each
shift to plus or minus 20%, keeps zero weights at zero, and scales by the
head coach's delegation. Nothing here adds yardage or turnovers.

Defense: the installation records DC familiarity, base scheme familiarity
and defensive packages, and exposes defense_execution_factor() for CCH-03.
It does not change defensive calls itself.

Records are plain JSON dictionaries (version 1). Missing or old records are
migrated deterministically; nothing here draws from a random stream.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional

INSTALLATION_VERSION = 1

# Starting points
ESTABLISHED_FAMILIARITY = 0.75   # staff already in place when tracking starts
NEW_COACH_FAMILIARITY = 0.30     # a brand new coordinator, no shared roots
LINEAGE_BONUS = 0.25             # new OC worked under this HC, or shares a mentor with her predecessor
SAME_SIGNATURE_BONUS = 0.20      # new OC interprets the book the same way as her predecessor
PROMOTION_FLOOR = 0.70           # promoted from this staff
CARRYOVER_CAP = 0.85
NEW_FAMILY_FAMILIARITY = 0.35    # the program switched base books

# Growth and decay
GAME_GROWTH = 0.02
SEASON_GROWTH = 0.20
PACKAGE_START = 0.30
PACKAGE_GAME_GROWTH = 0.03
PACKAGE_SEASON_GROWTH = 0.25
VESTIGE_SHARE = 0.60             # how much of the old OC's habit survives the hire
VESTIGE_GAME_DECAY = 0.97
VESTIGE_SEASON_DECAY = 0.40
VESTIGE_FLOOR = 0.05

# Package limits and pull
PACKAGES_PER_COORDINATOR = 2
MAX_PACKAGES = 4
PACKAGE_PULL = 0.12

_BIAS_KEYS = ("formation_bias", "family_bias", "kick_pass_bias")
_PACKAGE_TAGS = {"formation_bias": "formation_tags",
                 "family_bias": "play_family_tags",
                 "kick_pass_bias": "kick_pass_tags"}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def _coach_id(card: Any) -> str:
    return str(getattr(card, "coach_id", "") or "") if card is not None else ""


def _profile(card: Any) -> Dict[str, Any]:
    if card is None:
        return {}
    from engine.coach_tactics import ensure_coach_tactical_profile
    try:
        return ensure_coach_tactical_profile(card)
    except ValueError:
        return {}


def _signature(card: Any, side: str) -> str:
    ident = _profile(card).get("identity", {})
    return ident.get("offense_interpretation" if side == "offense" else "defense_interpretation", "")


def _offense_bias(card: Any) -> Dict[str, Dict[str, float]]:
    off = _profile(card).get("offense", {})
    return {k: dict(off.get(k, {})) for k in _BIAS_KEYS}


def _mentors(card: Any) -> set:
    return {e.get("coach_id") for e in (getattr(card, "coaching_tree", None) or []) if e.get("coach_id")}


# ── Roster profile for package personnel checks ──

_MIDFIELD = ("Viper", "Halfback", "Wingback", "Slotback", "Zeroback")
_FILE_STATS_CACHE: Dict[str, List[float]] = {}


def _top_mean(vals, n):
    vals = sorted((v for v in vals if v is not None), reverse=True)[:n]
    return sum(vals) / len(vals) if vals else 0.0


def roster_measures(team: Any) -> Dict[str, float]:
    """Raw roster measures behind each team_stats field, from the players
    who matter for it, on the engine's 60 to 100 scale."""
    from engine.game_engine import scale_rating as sr
    players = list(getattr(team, "players", []) or [])
    if not players:
        return {}
    return {
        "avg_speed": _top_mean([sr(getattr(p, "speed", 0)) for p in players], 22),
        "avg_stamina": _top_mean([sr(getattr(p, "stamina", 0)) for p in players], 22),
        "avg_weight": _top_mean([getattr(p, "weight", None) for p in players], len(players)),
        "kicking_strength": _top_mean([sr(getattr(p, "kicking", 0)) for p in players], 1),
        "lateral_proficiency": _top_mean([sr(getattr(p, "lateral_skill", 0)) for p in players
                                          if p.position in _MIDFIELD], 10),
        "defensive_strength": _top_mean([sr(getattr(p, "tackling", 0)) for p in players
                                         if p.position in ("Defensive Line", "Keeper")], 7),
    }


def _file_stat_spread() -> Dict[str, List[float]]:
    """The team_stats values in data/teams, sorted per field. The playbook
    catalog's personnel thresholds are written against these."""
    if not _FILE_STATS_CACHE:
        import glob
        import json
        import os
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "teams")
        for f in sorted(glob.glob(os.path.join(root, "*.json"))):
            try:
                ts = json.load(open(f, encoding="utf-8")).get("team_stats", {})
            except (OSError, ValueError):
                continue
            for k, v in ts.items():
                if isinstance(v, (int, float)):
                    _FILE_STATS_CACHE.setdefault(k, []).append(float(v))
        for v in _FILE_STATS_CACHE.values():
            v.sort()
    return _FILE_STATS_CACHE


def league_roster_profiles(teams: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """team_stats style profiles for every team in a league.

    Fresh rosters and the team files sit on different scales, so each
    measure is ranked within the league and mapped to the same rank in the
    team files' spread: a team in the top half for speed gets what a top
    half team has in the files. The catalog's thresholds then mean the same
    thing for both."""
    measures = {name: roster_measures(t) for name, t in (teams or {}).items()}
    measures = {n: m for n, m in measures.items() if m}
    spread = _file_stat_spread()
    out: Dict[str, Dict[str, float]] = {n: {} for n in measures}
    for stat in ("avg_speed", "avg_stamina", "avg_weight", "kicking_strength",
                 "lateral_proficiency", "defensive_strength"):
        ranked = sorted(measures, key=lambda n: (measures[n].get(stat, 0.0), n))
        ref = spread.get(stat)
        for rank, name in enumerate(ranked):
            if ref and len(ranked) > 1:
                pct = rank / (len(ranked) - 1)
                out[name][stat] = ref[min(len(ref) - 1, int(round(pct * (len(ref) - 1))))]
            else:
                out[name][stat] = round(measures[name].get(stat, 0.0), 1)
    return out


# ── Records ──

def _new_unit(side: str, family: str, card: Any, familiarity: float, year: Optional[int]) -> Dict[str, Any]:
    unit = {
        "family": family,
        "family_familiarity": round(familiarity, 3),
        "coach_id": _coach_id(card),
        "signature": _signature(card, side),
        "familiarity": round(familiarity, 3),
        "since_year": year,
        "seasons_together": 0,
        "games_together": 0,
        "vestigial": [],
        "packages": [],
    }
    if side == "offense":
        unit["bias"] = _offense_bias(card)
    return unit


def new_installation(team_name: str, staff: Optional[dict], offense_family: str,
                     defense_family: str, year: Optional[int] = None) -> Dict[str, Any]:
    """A program whose current staff is already in place: well installed."""
    staff = staff or {}
    return {
        "version": INSTALLATION_VERSION,
        "team": team_name,
        "offense": _new_unit("offense", offense_family, staff.get("oc"), ESTABLISHED_FAMILIARITY, year),
        "defense": _new_unit("defense", defense_family, staff.get("dc"), ESTABLISHED_FAMILIARITY, year),
        "staff_ids": sorted(_coach_id(c) for c in staff.values() if _coach_id(c)),
        "history": [{"year": year, "event": "tracking_started"}],
    }


def ensure_installation(record: Optional[dict], team_name: str = "") -> Optional[Dict[str, Any]]:
    """Fill missing fields in an old or partial record; never invents data."""
    if not record:
        return None
    if not isinstance(record, dict):
        raise ValueError("A team installation must be an object")
    if record.get("version", INSTALLATION_VERSION) != INSTALLATION_VERSION:
        raise ValueError("Unsupported team installation version")
    record.setdefault("version", INSTALLATION_VERSION)
    record.setdefault("team", team_name)
    record.setdefault("staff_ids", [])
    record.setdefault("history", [])
    for side in ("offense", "defense"):
        u = record.setdefault(side, {})
        u.setdefault("family", "")
        u.setdefault("family_familiarity", ESTABLISHED_FAMILIARITY)
        u.setdefault("coach_id", "")
        u.setdefault("signature", "")
        u.setdefault("familiarity", ESTABLISHED_FAMILIARITY)
        u.setdefault("since_year", None)
        u.setdefault("seasons_together", 0)
        u.setdefault("games_together", 0)
        u.setdefault("vestigial", [])
        u.setdefault("packages", [])
        if side == "offense":
            u.setdefault("bias", {k: {} for k in _BIAS_KEYS})
    return record


def _carryover(side: str, unit: dict, new_card: Any, staff: dict, previous_staff_ids: Iterable[str]) -> float:
    """Starting familiarity for a new coordinator."""
    new_id = _coach_id(new_card)
    if not new_id:
        return 0.0
    if new_id in set(previous_staff_ids):
        return max(PROMOTION_FLOOR, unit.get("familiarity", 0.0))
    fam = NEW_COACH_FAMILIARITY
    hc_id = _coach_id(staff.get("head_coach"))
    mentors = _mentors(new_card)
    old_mentors = set(unit.get("mentors", []))
    if (hc_id and hc_id in mentors) or (mentors & old_mentors) or (unit.get("coach_id") in mentors):
        fam += LINEAGE_BONUS
    if unit.get("signature") and _signature(new_card, side) == unit.get("signature"):
        fam += SAME_SIGNATURE_BONUS
    return min(CARRYOVER_CAP, fam)


# Installation preferences, not execution modifiers. Existing pressure,
# run support and native-book preference remain; focus and read affinity
# distinguish packages with different tactical jobs.
_DEFENSE_PACKAGE_FOCUS = {
    "fortress_goal_line_stand": ("short", None),
    "fortress_short_yardage_wall": ("short", None),
    "lockdown_kick_range_shell": ("deep", "intermediate"),
    "lockdown_long_yardage_bracket": ("deep", "intermediate"),
    "drift_prevent": ("deep", None),
    "blitz_short_yardage_pressure": ("short", "opportunistic"),
    "rugby_rush_line": ("perimeter", "short"),
    "afl_kick_in_press": ("intermediate", "opportunistic"),
    "lax_ride": ("opportunistic", "perimeter"),
    "swarm_containment": ("perimeter", None),
    "shadow_robber": ("intermediate", "opportunistic"),
    "chaos_lateral_trap": ("opportunistic", "perimeter"),
    "predator_exhaustion_press": ("perimeter", "intermediate"),
}


def _defensive_preference_components(pkg: dict, family: str, defense: dict) -> dict:
    """Explain an install preference using the coach's saved tactical interests."""
    from engine.defensive_commitments import PRESS_PACKAGES, COVER_PACKAGES, WALL_PACKAGES
    pid = pkg["package_id"]
    pressure = float(defense.get("pressure_bias", 0.0))
    support = float(defense.get("run_support_bias", 0.0))
    category = (pressure if pid in PRESS_PACKAGES else -pressure if pid in COVER_PACKAGES
                else support if pid in WALL_PACKAGES else 0.0)
    focus = defense.get("coverage_focus")
    primary, adjacent = _DEFENSE_PACKAGE_FOCUS.get(pid, (None, None))
    focus_match = .08 if focus and focus == primary else .04 if focus and focus == adjacent else 0.0
    families = set(pkg.get("play_family_tags", ()))
    targets = set()
    if families & {"power", "dive_option", "counter", "draw", "sweep_option", "speed_option", "viper_jet"}:
        targets.add("run")
    if "lateral_spread" in families or "kick_lateral" in pkg.get("kick_pass_tags", ()):
        targets.add("lateral")
    if "kick_pass" in families:
        targets.add("kick_pass")
    reads = set(defense.get("read_focus") or ())
    read_match = .025 * len(targets & reads) / len(targets) if targets else 0.0
    return {"category": category, "focus_match": focus_match,
            "read_match": read_match, "native_book": .07 if pkg["origin_family"] == family else 0.0}


def _package_preference_score(side: str, family: str, card: Any):
    """Use the same preference calculation for selection and diagnostics."""
    from engine import playbook_catalog as pc
    bias = _offense_bias(card) if side == "offense" else {}
    defense = _profile(card).get("defense", {}) if side == "defense" else {}

    def score(pid):
        pkg = pc.get_package(pid)
        if side == "defense":
            return sum(_defensive_preference_components(pkg, family, defense).values())
        s = 0.0
        for key, tag_field in _PACKAGE_TAGS.items():
            s += sum(bias.get(key, {}).get(t, 0.0) for t in pkg.get(tag_field, []))
        if pkg["origin_family"] == family:
            s += 0.01
        return s

    return score


def _package_rank_key(side: str, card: Any, score, pid: str):
    """Stable coach-specific ordering only when preference scores tie."""
    if side == "defense" and _coach_id(card):
        from engine.stable_hash import stable_hash
        return (-round(score(pid), 9),
                stable_hash(f"def11:{_coach_id(card)}:{pid}"), pid)
    return (-score(pid), pid)


def _choose_packages(side: str, unit: dict, card: Any, team_stats: dict,
                     year: Optional[int]) -> None:
    """Keep what still fits this book and roster; let a new coordinator add
    the catalog packages that match her preferences."""
    from engine import playbook_catalog as pc
    family = unit.get("family", "")
    try:
        fits = {r["package_id"]: r for r in pc.packages_for_roster(side, family, team_stats)
                if r["meets_personnel"]}
    except KeyError:
        fits = {}
    # Only packages the engine can actually call: at least one of their
    # situations must be one the engine can evaluate today.
    callable_now = evaluable_situations()
    fits = {pid: r for pid, r in fits.items() if set(r["situation_tags"]) & callable_now}
    kept = [p for p in unit.get("packages", []) if p.get("package_id") in fits]
    have = {p["package_id"] for p in kept}
    coach_id = _coach_id(card)
    already_by_coach = sum(1 for p in kept if p.get("installed_by") == coach_id)
    if coach_id and already_by_coach < PACKAGES_PER_COORDINATOR:
        score = _package_preference_score(side, family, card)

        ranked = sorted((pid for pid in fits if pid not in have), key=lambda pid: _package_rank_key(side, card, score, pid))
        if side == "offense":
            ranked = [pid for pid in ranked if score(pid) > 0] or ranked
        for pid in ranked[:PACKAGES_PER_COORDINATOR - already_by_coach]:
            kept.append({"package_id": pid, "familiarity": PACKAGE_START,
                         "installed_by": coach_id, "installed_year": year})
    kept.sort(key=lambda p: (-p.get("familiarity", 0.0), p["package_id"]))
    unit["packages"] = kept[:MAX_PACKAGES]


def defensive_adoption_snapshot(unit: dict, card: Any, team_stats: dict) -> dict:
    """Explain package adoption without changing the saved unit or call weights.

    This is a snapshot, not a reconstruction of a past installation decision.
    Scores are the current ranking inputs; retained familiarity and available
    slots can explain why a higher-scoring package is not installed.
    """
    from engine import playbook_catalog as pc
    from engine.game_engine import DEFENSE_STYLES
    family = unit.get("family", "")
    installed = {p["package_id"]: p for p in unit.get("packages", [])}
    all_ids = sorted({p["package_id"] for scheme in DEFENSE_STYLES
                      for p in pc.list_compatible_packages("defense", scheme)})
    fits = {p["package_id"]: p for p in pc.packages_for_roster(
        "defense", family, team_stats)}
    score = _package_preference_score("defense", family, card)
    callable_now = evaluable_situations()
    defense = _profile(card).get("defense", {})
    rows = {}
    for pid in all_ids:
        fit = fits.get(pid)
        compatible = fit is not None
        personnel_ok = bool(fit and fit["meets_personnel"])
        callable_tag = bool(fit and set(fit["situation_tags"]) & callable_now)
        record = installed.get(pid)
        rows[pid] = {
            "compatible": compatible,
            "personnel_ok": personnel_ok,
            "missing_personnel": fit["missing_personnel"] if fit else [],
            "callable": callable_tag,
            "preference_score": round(score(pid), 6) if compatible else None,
            "preference_components": _defensive_preference_components(
                pc.get_package(pid), family, defense) if compatible else None,
            "installed": record is not None,
            "familiarity": record.get("familiarity") if record else None,
            "installed_by_current_dc": bool(record and
                record.get("installed_by") == _coach_id(card)),
        }
    eligible = sorted((pid for pid, row in rows.items()
                       if row["personnel_ok"] and row["callable"]),
                      key=lambda pid: _package_rank_key("defense", card, score, pid))
    for rank, pid in enumerate(eligible, 1):
        rows[pid]["preference_rank"] = rank
    return {
        "family": family,
        "coach_id": _coach_id(card),
        "coverage_focus": defense.get("coverage_focus"),
        "read_focus": list(defense.get("read_focus") or ()),
        "installed_count": len(installed),
        "current_dc_installed_count": sum(
            p.get("installed_by") == _coach_id(card) for p in installed.values()),
        "packages": rows,
    }


def sync_installation(installations: Dict[str, dict], team_name: str, staff: Optional[dict],
                      offense_family: str, defense_family: str,
                      team_stats: Optional[Dict[str, float]] = None,
                      year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Bring a team's record in line with its current staff and books.

    Called before each game. Does nothing when nothing changed; handles
    hires, promotions and scheme changes when they did. Returns the record
    (stored in `installations`), or None when the team has no staff."""
    if not staff:
        return None
    rec = ensure_installation(installations.get(team_name), team_name)
    # Reassess eligibility when the actual roster crosses a personnel threshold.
    # Keep learned packages that still fit; do not reset the coordinator.
    from engine.playbook_catalog import roster_tags
    current_fit = sorted(roster_tags(team_stats)) if team_stats else None
    team_stats = team_stats or {}
    if rec is None:
        rec = new_installation(team_name, staff, offense_family, defense_family, year)
        for side, key in (("offense", "oc"), ("defense", "dc")):
            rec[side]["mentors"] = sorted(_mentors(staff.get(key)))
            _choose_packages(side, rec[side], staff.get(key), team_stats, year)
        rec["roster_fit_tags"] = current_fit
        installations[team_name] = rec
        return rec

    fit_changed = current_fit is not None and current_fit != rec.get("roster_fit_tags")
    prev_ids = list(rec.get("staff_ids", []))
    for side, key, family in (("offense", "oc", offense_family), ("defense", "dc", defense_family)):
        unit = rec[side]
        card = staff.get(key)
        changed = False
        if family and unit.get("family") != family:
            rec["history"].append({"year": year, "event": f"{side}_family_change",
                                   "from": unit.get("family"), "to": family})
            unit["family"] = family
            unit["family_familiarity"] = NEW_FAMILY_FAMILIARITY
            changed = True
        new_id = _coach_id(card)
        if new_id != unit.get("coach_id"):
            start = _carryover(side, unit, card, staff, prev_ids)
            if side == "offense" and unit.get("coach_id"):
                weight = round(unit.get("familiarity", 0.0) * VESTIGE_SHARE, 3)
                if weight >= VESTIGE_FLOOR:
                    unit["vestigial"] = [{"coach_id": unit["coach_id"], "signature": unit.get("signature", ""),
                                          "weight": weight, "bias": deepcopy(unit.get("bias", {}))}] + [
                        v for v in unit.get("vestigial", []) if v.get("coach_id") != new_id][:1]
            rec["history"].append({"year": year, "event": f"{side}_coordinator_change",
                                   "from": unit.get("coach_id"), "to": new_id,
                                   "start_familiarity": round(start, 3)})
            unit.update({"coach_id": new_id, "signature": _signature(card, side),
                         "familiarity": round(start, 3), "since_year": year,
                         "seasons_together": 0, "games_together": 0,
                         "mentors": sorted(_mentors(card))})
            if side == "offense":
                unit["bias"] = _offense_bias(card)
                unit["vestigial"] = [v for v in unit.get("vestigial", []) if v.get("coach_id") != new_id]
            changed = True
        if changed or fit_changed or not unit.get("packages"):
            _choose_packages(side, unit, card, team_stats, year)
    if current_fit is not None:
        rec["roster_fit_tags"] = current_fit
    rec["staff_ids"] = sorted(_coach_id(c) for c in staff.values() if _coach_id(c))
    return rec


def record_game(rec: Optional[dict]) -> None:
    """In season learning: one more game with this staff."""
    if not rec:
        return
    for side in ("offense", "defense"):
        u = rec[side]
        u["games_together"] = u.get("games_together", 0) + 1
        u["familiarity"] = round(_clamp(u.get("familiarity", 0.0) + GAME_GROWTH), 3)
        u["family_familiarity"] = round(_clamp(u.get("family_familiarity", 0.0) + GAME_GROWTH), 3)
        for p in u.get("packages", []):
            p["familiarity"] = round(_clamp(p.get("familiarity", 0.0) + PACKAGE_GAME_GROWTH), 3)
        vest = []
        for v in u.get("vestigial", []):
            v["weight"] = round(v.get("weight", 0.0) * VESTIGE_GAME_DECAY, 3)
            if v["weight"] >= VESTIGE_FLOOR:
                vest.append(v)
        u["vestigial"] = vest


def advance_offseason(rec: Optional[dict], year: Optional[int] = None) -> None:
    """A season together: familiarity grows, old habits fade."""
    if not rec:
        return
    for side in ("offense", "defense"):
        u = rec[side]
        if u.get("coach_id"):
            u["seasons_together"] = u.get("seasons_together", 0) + 1
            u["familiarity"] = round(_clamp(u.get("familiarity", 0.0) + SEASON_GROWTH), 3)
        u["family_familiarity"] = round(_clamp(u.get("family_familiarity", 0.0) + SEASON_GROWTH), 3)
        u["games_together"] = 0
        for p in u.get("packages", []):
            p["familiarity"] = round(_clamp(p.get("familiarity", 0.0) + PACKAGE_SEASON_GROWTH), 3)
        vest = []
        for v in u.get("vestigial", []):
            v["weight"] = round(v.get("weight", 0.0) * VESTIGE_SEASON_DECAY, 3)
            if v["weight"] >= VESTIGE_FLOOR:
                vest.append(v)
        u["vestigial"] = vest
    rec.setdefault("history", []).append({"year": year, "event": "offseason"})
    rec["history"] = rec["history"][-40:]


# ── Game effect ──

def execution_factor(unit: dict) -> float:
    """How much of the coordinator's system the team executes: familiarity
    with her, discounted a little while it is still learning its base book."""
    return round(_clamp(unit.get("familiarity", 0.0)) * (0.7 + 0.3 * _clamp(unit.get("family_familiarity", 0.0))), 3)


def defense_execution_factor(rec: Optional[dict]) -> float:
    """For CCH-03: scale a DC's signature by the defense's installation.
    1.0 when there is no record (unchanged behavior)."""
    if not rec:
        return 1.0
    return execution_factor(rec["defense"])


def apply_installation_to_offense(tactics: Dict[str, Any], rec: Optional[dict]) -> Dict[str, Any]:
    """Blend an OC's resolved tactics (CCH-02) with what the team has
    installed. No tactics or no record leaves tactics unchanged."""
    if not tactics or not rec:
        return tactics
    unit = rec.get("offense", {})
    if unit.get("coach_id") and unit.get("coach_id") != tactics.get("coach_id"):
        return tactics   # stale record; sync_installation runs before games
    from engine import playbook_catalog as pc
    factor = execution_factor(unit)
    out = dict(tactics)
    for key in _BIAS_KEYS:
        blended: Dict[str, float] = {}
        for k, v in (tactics.get(key) or {}).items():
            blended[k] = v * factor
        for vest in unit.get("vestigial", []):
            for k, v in (vest.get("bias", {}).get(key) or {}).items():
                blended[k] = blended.get(k, 0.0) + v * vest.get("weight", 0.0)
        out[key] = {k: round(v, 4) for k, v in blended.items()}
    packages = []
    for p in unit.get("packages", []):
        try:
            pkg = pc.get_package(p["package_id"])
        except KeyError:
            continue
        packages.append({"package_id": pkg["package_id"], "name": pkg["name"],
                         "familiarity": p.get("familiarity", 0.0),
                         "situation_tags": pkg["situation_tags"],
                         "formation_tags": pkg["formation_tags"],
                         "play_family_tags": pkg["play_family_tags"],
                         "kick_pass_tags": pkg["kick_pass_tags"]})
    out["packages"] = packages
    out["installation"] = {
        "familiarity": unit.get("familiarity"),
        "family": unit.get("family"),
        "family_familiarity": unit.get("family_familiarity"),
        "execution_factor": factor,
        "vestigial": [{"coach_id": v.get("coach_id"), "signature": v.get("signature"),
                       "weight": v.get("weight")} for v in unit.get("vestigial", [])],
        "packages": [{"package_id": p["package_id"], "familiarity": p["familiarity"]} for p in packages],
    }
    return out


_EVALUABLE_RULE_KEYS = {"yards_per_down_min", "yards_to_go_max", "yards_to_go_min",
                        "field_position_min", "field_position_max", "down_min", "down_max",
                        "lead_min_q4", "lead_min_second_half", "deficit_min_second_half",
                        "deficit_min_last_300s", "quarters", "time_remaining_max",
                        "drive_play_index", "drive_start", "defense_energy_max"}


def evaluable_situations() -> set:
    """Catalog situations the engine can evaluate from live context."""
    from engine import playbook_catalog as pc
    return {tag for tag, spec in pc.vocabulary()["situations"].items()
            if spec.get("rule") and not set(spec["rule"]) - _EVALUABLE_RULE_KEYS}


def active_situations(context: Dict[str, Any]) -> set:
    """Catalog situations true right now; missing event inputs never match."""
    from engine import playbook_catalog as pc
    out = set()
    down = context.get("down", 1)
    ytg = context.get("yards_to_go", 10)
    fp = context.get("field_position", 25)
    q = context.get("quarter", 1)
    tr = context.get("time_remaining", 900)
    diff = context.get("score_diff", 0)
    for tag, spec in pc.vocabulary()["situations"].items():
        rule = spec.get("rule", {})
        ok = True
        if not rule or set(rule) - _EVALUABLE_RULE_KEYS:
            continue
        if "yards_per_down_min" in rule and ytg / max(1, 7 - down) < rule["yards_per_down_min"]:
            ok = False
        if "yards_to_go_max" in rule and ytg > rule["yards_to_go_max"]:
            ok = False
        if "yards_to_go_min" in rule and ytg < rule["yards_to_go_min"]:
            ok = False
        if "field_position_min" in rule and fp < rule["field_position_min"]:
            ok = False
        if "field_position_max" in rule and fp > rule["field_position_max"]:
            ok = False
        if "down_min" in rule and down < rule["down_min"]:
            ok = False
        if "down_max" in rule and down > rule["down_max"]:
            ok = False
        if "quarters" in rule and (q not in rule["quarters"] or tr > rule.get("time_remaining_max", 900)):
            ok = False
        if "lead_min_q4" in rule:
            ok = ok and ((q == 4 and diff >= rule["lead_min_q4"]) or
                         (q >= 3 and diff >= rule.get("lead_min_second_half", 99)))
        if "deficit_min_second_half" in rule:
            ok = ok and ((q >= 3 and -diff >= rule["deficit_min_second_half"]) or
                         (q == 4 and tr <= 300 and -diff >= rule.get("deficit_min_last_300s", 1)))
        if "drive_play_index" in rule and context.get("drive_play_index") != rule["drive_play_index"]:
            ok = False
        if "drive_start" in rule and context.get("drive_start") not in rule["drive_start"]:
            ok = False
        if "defense_energy_max" in rule:
            energy = context.get("defense_energy")
            if energy is None or energy >= rule["defense_energy_max"]:
                ok = False
        if ok:
            out.add(tag)
    return out


# These scripts have compound situations in their catalog descriptions.
# Other multi-tag packages deliberately allow alternative triggers.
_OFFENSE_ALL_SITUATIONS = {
    "afl_kick_in_breakout", "afl_restart_go_to", "lax_fast_break",
    "league_last_tackle_kick",
}


def offensive_package_eligible(pkg: dict, live: set) -> bool:
    tags = set(pkg.get("situation_tags", ()))
    if not tags:
        return False
    if pkg["package_id"] in _OFFENSE_ALL_SITUATIONS:
        return tags <= live
    return bool(tags & live)


def choose_offensive_package(tactics: dict, context: dict, rng):
    """One optional practiced plan per snap; base playbook is always available.

    No global RNG draws, no post-snap information, no changes to legal
    play weights. Formation, family and subtype share the same plan.
    """
    live = active_situations(context)
    candidates = []
    for pkg in sorted(tactics.get("packages") or [], key=lambda p: p["package_id"]):
        familiarity = _clamp(pkg.get("familiarity", 0.0))
        if familiarity > 0 and offensive_package_eligible(pkg, live):
            candidates.append((pkg, familiarity))
    eligible = [pkg["package_id"] for pkg, _ in candidates]
    if not candidates:
        return None, eligible, sorted(live)
    authority = _clamp(tactics.get("authority", 1.0))
    if rng.random() >= .90 * authority * max(f for _, f in candidates):
        return None, eligible, sorted(live)
    picked = rng.choices([p for p, _ in candidates],
                         weights=[f for _, f in candidates], k=1)[0]
    return picked, eligible, sorted(live)


def offensive_plan_bias(tactics: dict, key: str, package: Optional[dict]) -> dict:
    base = dict(tactics.get(key) or {})
    if package:
        pull = PACKAGE_PULL * _clamp(package.get("familiarity", 0.0))
        for tag in package.get(_PACKAGE_TAGS[key], ()):
            base[tag] = base.get(tag, 0.0) + pull
    return base


def offensive_plan_matches(package: dict, choices: dict) -> dict:
    """Report observed choices, not a claim that a package caused them."""
    result = {}
    for choice, field in (("formation", "formation_tags"),
                          ("family", "play_family_tags"),
                          ("kick_pass", "kick_pass_tags")):
        tags = package.get(field) or []
        if choice in choices and tags:
            result[choice] = choices[choice] in tags
    return result


def situational_bias(tactics: Dict[str, Any], key: str, context: Dict[str, Any],
                     usage: Optional[dict] = None) -> Dict[str, float]:
    """The OC's (installation scaled) bias for one category plus the pull
    of every installed package whose situation is live. Counts package
    activations in `usage` when given (once per play, on family calls)."""
    base = dict(tactics.get(key) or {})
    pkgs = tactics.get("packages") or []
    if not pkgs:
        return base
    live = active_situations(context)
    tag_field = _PACKAGE_TAGS[key]
    for p in pkgs:
        if not offensive_package_eligible(p, live):
            continue
        pull = PACKAGE_PULL * _clamp(p.get("familiarity", 0.0))
        for t in p.get(tag_field, []):
            base[t] = base.get(t, 0.0) + pull
        if usage is not None and key == "family_bias":
            bucket = usage.setdefault("packages", {})
            bucket[p["package_id"]] = bucket.get(p["package_id"], 0) + 1
    return base


def summarize(rec: Optional[dict]) -> Dict[str, Any]:
    """For API and team pages."""
    if not rec:
        return {}
    from engine import playbook_catalog as pc

    def pkg_name(pid):
        try:
            return pc.get_package(pid)["name"]
        except KeyError:
            return pid

    out = {"team": rec.get("team")}
    for side in ("offense", "defense"):
        u = rec[side]
        out[side] = {
            "family": u.get("family"),
            "family_familiarity": u.get("family_familiarity"),
            "coach_id": u.get("coach_id"),
            "signature": u.get("signature"),
            "familiarity": u.get("familiarity"),
            "execution_factor": execution_factor(u),
            "seasons_together": u.get("seasons_together"),
            "vestigial": [{"signature": v.get("signature"), "weight": v.get("weight")}
                          for v in u.get("vestigial", [])],
            "packages": [{"package_id": p["package_id"], "name": pkg_name(p["package_id"]),
                          "familiarity": p.get("familiarity")} for p in u.get("packages", [])],
        }
    out["recent_changes"] = [h for h in rec.get("history", []) if h.get("event") != "offseason"][-6:]
    return out
