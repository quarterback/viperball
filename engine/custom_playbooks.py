"""Validate and store user assembled books made from the live catalog."""

import hashlib
import json
from itertools import combinations
from uuid import uuid4

from . import playbook_catalog as catalog
from .team_installation import MAX_PACKAGES

SAVE_TYPE = "playbook"
SIDES = ("offense", "defense")
LEGACY_VERSION = 1
VERSION = 2


def same_look_options(packages):
    """Use the catalog's shared looks in both the editor and validator."""
    return [
        {"formation": formation, "packages": [first, second]}
        for first, second in combinations(sorted(packages), 2)
        for formation in catalog.same_look_formations(packages[first], packages[second])
    ]


def validate_book(data):
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] not in (LEGACY_VERSION, VERSION):
        raise ValueError("Expected a version 1 or version 2 playbook.")
    version = data["version"]
    title = data.get("name")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 80:
        raise ValueError("Enter a playbook name of 1 to 80 characters.")
    side, school = data.get("side"), data.get("school")
    if side not in SIDES or not isinstance(school, str):
        raise ValueError("Choose an offense or defense and a base school.")
    try:
        allowed = set(catalog.get_scheme_family(side, school)["packages"])
    except KeyError as exc:
        raise ValueError("Unknown base school for this side.") from exc
    packages = data.get("packages")
    if (not isinstance(packages, list) or not 1 <= len(packages) <= MAX_PACKAGES
            or any(not isinstance(pid, str) for pid in packages)):
        raise ValueError(f"Choose 1 to {MAX_PACKAGES} packages.")
    if len(set(packages)) != len(packages) or not set(packages) <= allowed:
        raise ValueError("Choose distinct packages compatible with the base school.")
    preferred = data.get("preferred")
    if preferred is not None and preferred not in packages:
        raise ValueError("Choose a preferred package from this book.")
    book = {"version": version, "name": title.strip(), "side": side, "school": school,
            "packages": list(packages), "preferred": preferred}
    if version == LEGACY_VERSION:
        return book

    book["packages"] = sorted(packages)
    focus = data.get("practice_focus")
    if focus is not None and focus not in packages:
        raise ValueError("Choose a practice focus from this book.")
    pairs = data.get("same_look_pairs", [])
    options = same_look_options({pid: catalog.get_package(pid) for pid in packages})
    if not isinstance(pairs, list) or len(pairs) > len(options):
        raise ValueError("Choose distinct same look pairs from this book.")
    selected = []
    for pair in pairs:
        if not isinstance(pair, dict) or not isinstance(pair.get("packages"), list):
            raise ValueError("Each same look pair needs a formation and two packages.")
        members = pair["packages"]
        if len(members) != 2 or any(not isinstance(pid, str) for pid in members):
            raise ValueError("Each same look pair needs two distinct packages.")
        option = {"formation": pair.get("formation"), "packages": sorted(members)}
        if option not in options or option in selected:
            raise ValueError("Pair two distinct offensive packages that share a formation and offer different actions.")
        selected.append(option)
    book.update(practice_focus=focus, same_look_pairs=[pair for pair in options if pair in selected])
    canonical = json.dumps(book, sort_keys=True, separators=(",", ":"))
    book["revision"] = hashlib.sha256(canonical.encode()).hexdigest()
    return book


def get_book(key):
    from .db import load_blob

    data = load_blob(SAVE_TYPE, key)
    if data is None:
        raise ValueError("That playbook could not be found.")
    return validate_book(data)


def save_book(data, key=None):
    from .db import save_blob

    book = validate_book(data)
    if key:
        get_book(key)
    else:
        key = uuid4().hex
    save_blob(SAVE_TYPE, key, book, label=book["name"])
    return key


def list_books():
    from .db import list_saves

    books = []
    for row in list_saves(SAVE_TYPE):
        key = row["save_key"]
        try:
            books.append({"id": key, **get_book(key)})
        except ValueError:
            # A retired catalog entry can make an older book unusable.
            continue
    return books


def resolve_choices(choices):
    """Snapshot library choices so edits do not affect an existing save."""
    picked = {}
    for side, key in choices.items():
        if not key:
            continue
        book = get_book(key)
        if side != book["side"]:
            raise ValueError(f"{book['name']} is a {book['side']} playbook.")
        picked[side] = book
    return picked


def apply_schools(style_configs, assignments):
    for team, books in assignments.items():
        styles = style_configs.setdefault(team, {})
        for side, book in books.items():
            styles[f"{side}_style"] = book["school"]


def library_snapshot():
    """Copy the current library without local database IDs."""
    return [{key: value for key, value in book.items() if key != "id"} for book in list_books()]


def assign_computer_books(books, teams, styles, excluded, seed):
    """Give one fitting book to roughly half of the eligible teams in each school."""
    from collections import defaultdict
    from random import Random

    from .team_installation import league_roster_profiles

    pool = defaultdict(list)
    for book in books:
        pool[book["side"], book["school"]].append(book)
    if not pool:
        return {}

    profiles = league_roster_profiles(teams)
    rng = Random(f"cookbook:{seed}")
    picked = {}
    for (side, school), options in sorted(pool.items()):
        options = sorted(options, key=lambda book: (
            book["name"], book["packages"], book.get("preferred") or "",
            book.get("revision") or "",
        ))
        candidates = []
        for team in sorted(teams.keys() - excluded):
            if styles.get(team, {}).get(f"{side}_style") != school:
                continue
            ready = {package["package_id"] for package in catalog.packages_for_roster(
                side, school, profiles.get(team, {}),
            ) if package["meets_personnel"]}
            fitting = [book for book in options if ready.intersection(book["packages"])]
            if fitting:
                candidates.append((team, fitting))
        rng.shuffle(candidates)
        for team, fitting in candidates[: (len(candidates) + 1) // 2]:
            picked.setdefault(team, {})[side] = rng.choice(fitting)
    return picked
