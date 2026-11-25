#!/usr/bin/env python3
"""Audit owner-mode WVL season/offseason continuity on the merged engine.

Run in a fresh process. Uses real clubs and schedules, isolated database
and a temporary destination for the tier-assignment export.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import random
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def identities(cards):
    return sorted((c.player_id, c.full_name, c.position) for c in cards)


def live_rosters(season):
    return {key: team.players for tier in season.tier_seasons.values()
            for key, team in tier.teams.items()}


def live_identities(season):
    return {key: sorted((p.player_id, p.name, p.position) for p in players)
            for key, players in live_rosters(season).items()}


def run(seed, seasons, out):
    out.mkdir(parents=True, exist_ok=True)
    report = {"seed": seed, "seasons": [], "transitions": [], "complete": False}

    def checkpoint():
        (out / "wvl_continuity.json").write_text(
            json.dumps(report, indent=2, sort_keys=True))

    with tempfile.TemporaryDirectory(prefix="wvl-continuity-") as tmp:
        os.environ["VIPERBALL_DB_PATH"] = str(Path(tmp) / "audit.sqlite3")
        from engine import wvl_dynasty as wd
        # The only redirected filesystem output is the owner's global tier
        # assignment export. Team-file loading remains in wvl_season.
        wd.DATA_DIR = Path(tmp)
        random.seed(seed)
        dynasty = wd.create_wvl_dynasty(
            "Continuity audit", "Audit owner", "patient_builder",
            "wrexham", starting_year=2026)
        clubs = set(dynasty.tier_assignments)
        expected_sizes = Counter(dynasty.tier_assignments.values())
        expected = None
        for i in range(seasons):
            year = dynasty.current_year
            season = dynasty.start_season()
            actual = live_identities(season)
            if set(actual) != clubs:
                raise RuntimeError("Active WVL club membership changed")
            if expected is not None and actual != expected:
                bad = [k for k in sorted(clubs) if actual[k] != expected[k]]
                report["roster_start_mismatches"] = bad
                checkpoint()
                raise RuntimeError(f"Offseason rosters not restored: {bad}")
            owners = Counter(pid for rows in actual.values() for pid, _, _ in rows if pid)
            duplicates = [pid for pid, n in owners.items() if n > 1]
            if duplicates:
                report["duplicate_ids"] = duplicates
                checkpoint()
                raise RuntimeError("Duplicate WVL player identities")
            season.run_full_season()
            tier_results = {}
            for number, tier in season.tier_seasons.items():
                scheduled = sum(len(w) for w in tier.schedule)
                results = [g for w in tier.results.values() for g in w.values()]
                if len(results) != scheduled or not tier.champion:
                    raise RuntimeError(f"Incomplete tier {number}")
                if any(not (g.get("result") or {}).get("play_by_play") for g in results):
                    raise RuntimeError(f"Non-full-engine game in tier {number}")
                tier_results[number] = {"regular_games": scheduled,
                                        "champion": tier.champion,
                                        "clubs": len(tier.teams)}
            report["seasons"].append({"year": year, "tiers": tier_results})
            checkpoint()
            if i + 1 == seasons:
                break
            dynasty.snapshot_season(season)
            dynasty.advance_season(season, rng=random.Random(seed + year))
            summary = dynasty.run_offseason(season, rng=random.Random(seed + year + 1))
            if dynasty.current_year != year + 1:
                raise RuntimeError("Offseason did not advance the year")
            if set(dynasty.tier_assignments) != clubs or Counter(dynasty.tier_assignments.values()) != expected_sizes:
                raise RuntimeError("Promotion/relegation changed tier capacity or club membership")
            expected = {k: identities(v) for k, v in dynasty._team_rosters.items()}
            if set(expected) != clubs:
                raise RuntimeError("Finalized offseason omitted clubs")
            report["transitions"].append({"year": year,
                "roster_sizes": {k: len(v) for k, v in expected.items()},
                "retirements": len(summary.get("retirements", [])),
                "promotion": summary.get("promotion_relegation"),
                "bankroll": dynasty.owner.bankroll})
            checkpoint()
            path = Path(tmp) / "dynasty.json"
            dynasty.save(str(path))
            dynasty = wd.WVLDynasty.load(str(path))
            restored = {k: identities(v) for k, v in dynasty._team_rosters.items()}
            if restored != expected:
                report["roster_save_missing_clubs"] = sorted(set(expected) - set(restored))
                report["roster_save_mismatches"] = sorted(k for k in expected if restored.get(k) != expected[k])
                checkpoint()
                raise RuntimeError("WVL dynasty save lost finalized rosters")
        report["complete"] = True
        checkpoint()
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=20261124)
    p.add_argument("--seasons", type=int, default=3)
    p.add_argument("--out", type=Path, default=Path("reports/wvl-continuity"))
    args = p.parse_args()
    if args.seasons < 2:
        p.error("At least two seasons required")
    run(args.seed, args.seasons, args.out)
