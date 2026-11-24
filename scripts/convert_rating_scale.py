"""Move every stored team file onto the current rating scale (PRO-01).

College (data/teams): the stored rosters were made before the November 2026
talent ladder.  Each player's ratings are re-rolled with the current roster
generator (same position, class, program archetype and philosophy), so a
stored roster looks like a fresh one.  Names, numbers and everything else stay.
Team stats take the new spread but keep each program's old league rank.

Pro, WVL and FIV club files: ratings and team stats are converted with
engine.rating_scale.legacy_to_current, which keeps every gap between players
and between tiers.

Files get "rating_scale": "current" and are skipped on a second run.

    python scripts/convert_rating_scale.py
"""
import json
import os
import random
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.rating_scale import CURRENT, RATING_ATTRS, TEAM_STAT_ATTRS, legacy_to_current  # noqa: E402
from scripts.generate_rosters import (  # noqa: E402
    DEFAULT_ARCHETYPE, PROGRAM_ARCHETYPES, assign_program_archetype, generate_player_attributes,
)

PRO_DIRS = ["nvl_teams", "al_teams", "el_teams", "la_teams", "pl_teams",
            "wvl_teams/tier1", "wvl_teams/tier2", "wvl_teams/tier3", "wvl_teams/tier4"]


def _team_stats(players):
    n = max(1, len(players))
    avg = lambda k: sum(p["stats"][k] for p in players) // n
    return {"avg_speed": avg("speed"), "avg_stamina": avg("stamina"),
            "kicking_strength": avg("kicking"), "lateral_proficiency": avg("lateral_skill"),
            "defensive_strength": avg("tackling")}


def convert_college(path: Path) -> bool:
    data = json.loads(path.read_text())
    if data.get("rating_scale") == CURRENT:
        return False
    school_id = data.get("team_info", {}).get("school_id", path.stem)
    archetype = data.get("program_archetype") or assign_program_archetype(school_id)
    if archetype not in PROGRAM_ARCHETYPES:
        archetype = DEFAULT_ARCHETYPE
    philosophy = data.get("identity", {}).get("philosophy", "hybrid")
    random.seed(zlib.crc32(school_id.encode()))
    players = data["roster"]["players"]
    for p in players:
        attrs = generate_player_attributes(
            p["position"], philosophy, str(p.get("year", "junior")).lower(),
            is_viper=p["position"] == "Viper", program_archetype=archetype)
        p["stats"] = {a: attrs[a] for a in RATING_ATTRS}
        p["stats"]["work_rate"] = attrs["work_rate"]
    data["_old_team_stats"] = dict(data.get("team_stats", {}))
    data["team_stats"] = {**data.get("team_stats", {}), **_team_stats(players)}
    data["rating_scale"] = CURRENT
    path.write_text(json.dumps(data, indent=2) + "\n")
    return True


def rank_college_team_stats(paths):
    """Give each program the team stat at its old league rank, taken from the
    new spread.  AI scheme assignment (engine/ai_coach.py) and playbook
    personnel tags read these numbers, so programs keep their identities."""
    files = []
    for path in paths:
        data = json.loads(path.read_text())
        if "_old_team_stats" in data:
            files.append((path, data))
    for attr in TEAM_STAT_ATTRS:
        rows = [(d["_old_team_stats"].get(attr), d["team_stats"].get(attr), p, d) for p, d in files]
        rows = [r for r in rows if isinstance(r[0], (int, float)) and isinstance(r[1], (int, float))]
        new_sorted = sorted(r[1] for r in rows)
        for i, (_, _, _, d) in enumerate(sorted(rows, key=lambda r: (r[0], r[2].stem))):
            d["team_stats"][attr] = new_sorted[i]
    for path, data in files:
        del data["_old_team_stats"]
        path.write_text(json.dumps(data, indent=2) + "\n")


def convert_pro(path: Path) -> bool:
    data = json.loads(path.read_text())
    if data.get("rating_scale") == CURRENT:
        return False
    for p in data["roster"]["players"]:
        for a in RATING_ATTRS:
            if isinstance(p["stats"].get(a), (int, float)):
                p["stats"][a] = legacy_to_current(p["stats"][a])
    for a in TEAM_STAT_ATTRS:
        if isinstance(data.get("team_stats", {}).get(a), (int, float)):
            data["team_stats"][a] = legacy_to_current(data["team_stats"][a])
    data["rating_scale"] = CURRENT
    path.write_text(json.dumps(data, indent=2) + "\n")
    return True


def main():
    done = 0
    college = []
    for path in sorted((ROOT / "data" / "teams").glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        if "roster" in data:
            done += convert_college(path)
            college.append(path)
    rank_college_team_stats(college)
    for d in PRO_DIRS:
        for path in sorted((ROOT / "data" / d).glob("*.json")):
            done += convert_pro(path)
    print(f"converted {done} files")


if __name__ == "__main__":
    main()
