"""Ready made playbooks cover every package and resolve like saved ones."""

import json

from engine.custom_playbooks import (assign_computer_books, house_books,
                                     package_group, resolve_choices)


def test_every_package_is_in_a_ready_made_book():
    with open("data/playbooks/packages.json", encoding="utf-8") as f:
        catalog = {p["package_id"] for p in json.load(f)["packages"]}
    covered = {pid for book in house_books() for pid in book["packages"]}
    assert covered == catalog


def test_concept_books_lead_with_their_set():
    books = {b["id"]: b for b in house_books()}
    cape = books["house:offense:lateral_spread:cape:1"]
    assert "cape_cod_hook" in cape["packages"] and cape["preferred"] == "cape_cod_hook"
    trap = books["house:defense:swarm:cape:1"]
    assert "cape_cod_trap" in trap["packages"]
    assert package_group("pk_kicker_diamond") == "delta"


def test_ready_made_book_resolves_for_a_program():
    picked = resolve_choices({"offense": "house:offense:lateral_spread:cape:1"})
    assert picked["offense"]["school"] == "lateral_spread"


def test_computer_teams_spread_across_books():
    books = [b for b in house_books() if b["side"] == "offense" and b["school"] == "balanced"]
    teams = {f"T{i}": object() for i in range(12)}
    styles = {t: {"offense_style": "balanced"} for t in teams}
    import engine.custom_playbooks as cp
    orig = cp.catalog.packages_for_roster
    cp.catalog.packages_for_roster = lambda side, school, stats: [
        {"package_id": pid, "meets_personnel": True} for b in books for pid in b["packages"]]
    import engine.team_installation as ti
    orig_prof = ti.league_roster_profiles
    ti.league_roster_profiles = lambda teams: {}
    try:
        picked = assign_computer_books(books, teams, styles, set(), 7)
    finally:
        cp.catalog.packages_for_roster = orig
        ti.league_roster_profiles = orig_prof
    names = [p["offense"]["name"] for p in picked.values()]
    assert len(names) == 6 and len(set(names)) == 6


def test_cross_code_books_get_their_own_ready_made_books():
    books = {b["id"]: b for b in house_books()}
    ghost = books["house:offense:ghost:free:1"]
    assert ghost["group_label"] == "Free Motion" and ghost["preferred"].startswith("fm_")
    assert books["house:defense:lockdown:crossdefense:1"]["preferred"].startswith("dx_")
    assert package_group("rl_wall_return") == "relay"
