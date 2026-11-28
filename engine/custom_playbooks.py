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


HOUSE_PREFIX = "house:"
CROSS_CODE = ("gaelic_kick_and_follow", "afl_boundary_switch", "rugby_carry_release",
              "ball_protect_bonus", "cfl_corner_chase")
GROUP_ORDER = ("base", "cape", "cross", "clinic", "delta")


def package_group(package_id):
    """The set a package belongs to, as the Playbooks page groups them."""
    if package_id.startswith("cape_cod_"):
        return "cape"
    if package_id in CROSS_CODE:
        return "cross"
    if package_id.startswith("clinic_"):
        return "clinic"
    if package_id.split("_")[0] in ("pp", "pko", "pk"):
        return "delta"
    return "base"


def _group_label(group, side):
    return {"base": "Base", "cape": "Cape Cod", "cross": "Cross code concepts",
            "clinic": "Clinic concepts",
            "delta": "Delta penalty kill" if side == "defense" else "Delta power play"}[group]


def _house_books_for(side, school, group):
    """One book per four packages of a set, so every package is in a book.
    Concept books lead with their set and fill with the school's base
    packages."""
    family = catalog.get_scheme_family(side, school)
    ids = family["packages"]

    def native_first(pids):
        return sorted(pids, key=lambda pid: (catalog.get_package(pid)["origin_family"] != school, pid))

    members = native_first([pid for pid in ids if package_group(pid) == group])
    base = native_first([pid for pid in ids if package_group(pid) == "base"])
    label = family.get("label", school)
    out = []
    for n, start in enumerate(range(0, len(members), MAX_PACKAGES), 1):
        lead = members[start:start + MAX_PACKAGES]
        packages = (lead + [pid for pid in base if pid not in lead])[:MAX_PACKAGES]
        title = _group_label(group, side) + (f" {n}" if n > 1 else "")
        book = validate_book({
            "version": VERSION, "side": side, "school": school, "packages": packages,
            "name": f"{label} {title.lower()}" if group == "base" else f"{label} with {title}",
            "preferred": None if group == "base" else lead[0],
        })
        book.update(id=f"{HOUSE_PREFIX}{side}:{school}:{group}:{n}", house=True,
                    school_label=label, group_label=title)
        out.append(book)
    return out


_HOUSE = None


def house_books():
    """Ready made books: for every base school, its base book and one book for
    each concept set it carries (Cape Cod, cross code, clinic, Delta). Each
    concept book leads with that set and fills the rest with the school's
    own base packages."""
    global _HOUSE
    if _HOUSE is None:
        from .game_engine import DEFENSE_STYLES, OFFENSE_STYLES
        out = []
        for side, styles in (("offense", OFFENSE_STYLES), ("defense", DEFENSE_STYLES)):
            for school in styles:
                for group in GROUP_ORDER:
                    out.extend(_house_books_for(side, school, group))
        _HOUSE = out
    return [dict(book) for book in _HOUSE]


def choice_books():
    """Every book a program can pick: the ready made ones, then saved ones."""
    return house_books() + list_books()


def get_book(key):
    from .db import load_blob

    if key.startswith(HOUSE_PREFIX):
        for book in house_books():
            if book["id"] == key:
                return validate_book(book)
        raise ValueError("That playbook could not be found.")

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
    """Copy the ready made books and the current library without IDs."""
    return [{key: value for key, value in book.items()
             if key not in ("id", "house", "school_label", "group_label")}
            for book in choice_books()]


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
        # Spread the books: each team takes a fitting book used least so far,
        # so every book in the school gets a program before any repeats.
        used = defaultdict(int)
        for team, fitting in candidates[: (len(candidates) + 1) // 2]:
            least = min(used[book["name"]] for book in fitting)
            book = rng.choice([b for b in fitting if used[b["name"]] == least])
            used[book["name"]] += 1
            picked.setdefault(team, {})[side] = book
    return picked
