"""PBK-01/02/04: the playbook catalog matches the engine and stays valid."""

import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine import playbook_catalog as pc  # noqa: E402
from engine.game_engine import DEFENSE_STYLES, OFFENSE_STYLES  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "playbooks")


def _raw():
    load = lambda n: json.load(open(os.path.join(DATA, n), encoding="utf-8"))
    return load("families.json"), load("packages.json"), load("vocabulary.json")


def test_catalog_is_valid():
    assert pc.validate_catalog(*_raw()) == []


def test_every_engine_family_has_a_record():
    for fid in OFFENSE_STYLES:
        rec = pc.get_scheme_family("offense", fid)
        assert rec["label"] == OFFENSE_STYLES[fid]["label"]
        assert rec["formation_mix"]
    for fid in DEFENSE_STYLES:
        assert pc.get_scheme_family("defense", fid)["label"] == DEFENSE_STYLES[fid]["label"]


def test_defense_strengths_come_from_scheme_ratings():
    assert "short_yardage" in pc.get_scheme_family("defense", "fortress")["strong_in"]
    assert "kick_range" in pc.get_scheme_family("defense", "lockdown")["strong_in"]
    # Blitz Pack's own rating says it is weak in long yardage (1.20).
    assert "long_yardage" not in pc.get_scheme_family("defense", "blitz_pack")["strong_in"]


def test_packages_cross_books():
    """At least one package per side is installable by a family other than its origin."""
    for side in pc.SIDES:
        fams = OFFENSE_STYLES if side == "offense" else DEFENSE_STYLES
        borrowed = [p for f in fams for p in pc.list_compatible_packages(side, f) if p["origin_family"] != f]
        assert borrowed
    east_coast = {p["package_id"] for p in pc.list_compatible_packages("offense", "east_coast")}
    assert "gp_heavy_push" in east_coast


def test_every_package_has_scenario_personnel_benefit_counter_and_cost():
    for side in pc.SIDES:
        fams = OFFENSE_STYLES if side == "offense" else DEFENSE_STYLES
        for f in fams:
            for p in pc.list_compatible_packages(side, f):
                for k in ("scenario", "benefits", "cost", "counter"):
                    assert p[k].strip()
                assert p["situation_tags"] and p["countered_by"] and p["tradeoffs"]


def test_lookups_return_copies():
    a = pc.get_package("gp_heavy_push")
    a["situation_tags"].append("chasing")
    assert "chasing" not in pc.get_package("gp_heavy_push")["situation_tags"]
    f = pc.get_scheme_family("offense", "boot_raid")
    f["strong_in"].clear()
    assert pc.get_scheme_family("offense", "boot_raid")["strong_in"]


def test_unknown_ids_raise():
    with pytest.raises(KeyError):
        pc.get_package("no_such_package")
    with pytest.raises(KeyError):
        pc.get_scheme_family("offense", "air_raid")
    with pytest.raises(KeyError):
        pc.list_compatible_packages("special_teams", "aces")


@pytest.mark.parametrize("breakage, expect", [
    (lambda f, p, v: p["packages"][0].update(origin_family="air_raid"), "origin_family"),
    (lambda f, p, v: p["packages"][0]["play_family_tags"].append("forward_pass"), "installable play family"),
    (lambda f, p, v: p["packages"][0]["situation_tags"].append("midfield"), "unknown situation"),
    (lambda f, p, v: p["packages"][0].update(countered_by=["nobody"]), "counter"),
    (lambda f, p, v: p["packages"][0].pop("cost"), "missing cost"),
    (lambda f, p, v: p["packages"].append(copy.deepcopy(p["packages"][0])), "duplicate"),
    (lambda f, p, v: f["offense"].pop("boot_raid"), "missing from the catalog"),
    (lambda f, p, v: f["offense"]["boot_raid"]["signature_fields"].append("warp_drive"), "signature field"),
    (lambda f, p, v: p["packages"][0]["compatible_families"].remove(p["packages"][0]["origin_family"]), "origin family must"),
    (lambda f, p, v: p["packages"][0].update(origin_family="balanced", compatible_families=["balanced"]), "no identity"),
])
def test_malformed_catalog_is_rejected(breakage, expect):
    f, p, v = _raw()
    breakage(f, p, v)
    errs = pc.validate_catalog(f, p, v)
    assert any(expect in e for e in errs), errs


def test_roster_check_reports_what_is_missing():
    slow = {"avg_speed": 70, "kicking_strength": 70, "avg_weight": 180}
    fast = {"avg_speed": 90, "kicking_strength": 85, "avg_weight": 190, "avg_stamina": 88}
    assert pc.roster_tags(slow) == set()
    assert {"team_speed", "elite_speed", "strong_kicker", "elite_kicker", "physical_roster", "deep_conditioning"} <= pc.roster_tags(fast)
    rows = {r["package_id"]: r for r in pc.packages_for_roster("offense", "east_coast", slow)}
    assert rows["gp_heavy_push"]["borrowed"] and rows["gp_heavy_push"]["missing_personnel"] == ["physical_roster"]
    assert rows["ec_two_minute"]["meets_personnel"] and not rows["ec_two_minute"]["borrowed"]


def test_real_team_files_get_a_package_list():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "teams")
    names = sorted(n for n in os.listdir(path) if n.endswith(".json"))[:10]
    for n in names:
        stats = json.load(open(os.path.join(path, n), encoding="utf-8")).get("team_stats", {})
        rows = pc.packages_for_roster("offense", "balanced", stats)
        assert rows and all(isinstance(r["meets_personnel"], bool) for r in rows)


def test_inventory_renders():
    md = pc.inventory_markdown()
    assert "Heavy Push" in md and "16 offensive families" in md
