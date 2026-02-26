#!/usr/bin/env python3
"""Generate 24 NVL team JSON files with male player rosters."""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_names import generate_player_name, load_name_pools
from scripts.generate_rosters import generate_player_attributes, assign_archetype

NVL_TEAMS = {
    "nj": {
        "city": "New Jersey", "name": "Netsnakes", "abbr": "NJS",
        "state": "NJ", "country": "USA", "division": "NVL East",
        "franchise_rating": 88, "style": "lateral_chaos", "defense": "blitz_heavy",
        "philosophy": "aggressive", "tempo": "fast",
    },
    "bos": {
        "city": "Boston", "name": "Beacons", "abbr": "BOS",
        "state": "MA", "country": "USA", "division": "NVL East",
        "franchise_rating": 82, "style": "west_coast", "defense": "zone",
        "philosophy": "hybrid", "tempo": "moderate",
    },
    "eri": {
        "city": "Erie", "name": "Ironheads", "abbr": "ERI",
        "state": "PA", "country": "USA", "division": "NVL East",
        "franchise_rating": 71, "style": "smashmouth", "defense": "man_press",
        "philosophy": "ground_heavy", "tempo": "slow",
    },
    "orl": {
        "city": "Orlando", "name": "Orbits", "abbr": "ORL",
        "state": "FL", "country": "USA", "division": "NVL East",
        "franchise_rating": 79, "style": "air_raid", "defense": "zone",
        "philosophy": "kick_heavy", "tempo": "fast",
    },
    "bal": {
        "city": "Baltimore", "name": "Bells", "abbr": "BAL",
        "state": "MD", "country": "USA", "division": "NVL East",
        "franchise_rating": 75, "style": "ground_pound", "defense": "swarm",
        "philosophy": "hybrid", "tempo": "moderate",
    },
    "roc": {
        "city": "Rochester", "name": "Rapids", "abbr": "ROC",
        "state": "NY", "country": "USA", "division": "NVL East",
        "franchise_rating": 68, "style": "tempo", "defense": "bend_no_break",
        "philosophy": "aggressive", "tempo": "fast",
    },
    "tor": {
        "city": "Toronto", "name": "Talons", "abbr": "TOR",
        "state": "ON", "country": "Canada", "division": "NVL North",
        "franchise_rating": 91, "style": "power_spread", "defense": "swarm",
        "philosophy": "hybrid", "tempo": "moderate",
    },
    "qc": {
        "city": "Quebec City", "name": "Voyageurs", "abbr": "QCV",
        "state": "QC", "country": "Canada", "division": "NVL North",
        "franchise_rating": 72, "style": "triple_option", "defense": "zone",
        "philosophy": "ground_heavy", "tempo": "slow",
    },
    "van": {
        "city": "Vancouver", "name": "Vanguards", "abbr": "VAN",
        "state": "BC", "country": "Canada", "division": "NVL North",
        "franchise_rating": 80, "style": "balanced", "defense": "bend_no_break",
        "philosophy": "hybrid", "tempo": "variable",
    },
    "cal": {
        "city": "Calgary", "name": "Coldfront", "abbr": "CGY",
        "state": "AB", "country": "Canada", "division": "NVL North",
        "franchise_rating": 74, "style": "ground_pound", "defense": "man_press",
        "philosophy": "ground_heavy", "tempo": "slow",
    },
    "dul": {
        "city": "Duluth", "name": "Drifts", "abbr": "DUL",
        "state": "MN", "country": "USA", "division": "NVL North",
        "franchise_rating": 65, "style": "smashmouth", "defense": "swarm",
        "philosophy": "conservative", "tempo": "slow",
    },
    "mtl": {
        "city": "Montreal", "name": "Monarchs", "abbr": "MTL",
        "state": "QC", "country": "Canada", "division": "NVL North",
        "franchise_rating": 85, "style": "air_raid", "defense": "blitz_heavy",
        "philosophy": "kick_heavy", "tempo": "fast",
    },
    "nol": {
        "city": "New Orleans", "name": "Nightcreepers", "abbr": "NOL",
        "state": "LA", "country": "USA", "division": "NVL Central",
        "franchise_rating": 93, "style": "lateral_chaos", "defense": "blitz_heavy",
        "philosophy": "aggressive", "tempo": "fast",
    },
    "mem": {
        "city": "Memphis", "name": "Mudcats", "abbr": "MEM",
        "state": "TN", "country": "USA", "division": "NVL Central",
        "franchise_rating": 77, "style": "ground_pound", "defense": "swarm",
        "philosophy": "hybrid", "tempo": "moderate",
    },
    "chi": {
        "city": "Chicago", "name": "Chains", "abbr": "CHI",
        "state": "IL", "country": "USA", "division": "NVL Central",
        "franchise_rating": 86, "style": "power_spread", "defense": "man_press",
        "philosophy": "hybrid", "tempo": "moderate",
    },
    "ark": {
        "city": "Arkansas", "name": "Arks", "abbr": "ARK",
        "state": "AR", "country": "USA", "division": "NVL Central",
        "franchise_rating": 67, "style": "triple_option", "defense": "bend_no_break",
        "philosophy": "conservative", "tempo": "slow",
    },
    "oma": {
        "city": "Omaha", "name": "Outlaws", "abbr": "OMA",
        "state": "NE", "country": "USA", "division": "NVL Central",
        "franchise_rating": 70, "style": "balanced", "defense": "zone",
        "philosophy": "hybrid", "tempo": "variable",
    },
    "bhm": {
        "city": "Birmingham", "name": "Blitz", "abbr": "BHM",
        "state": "AL", "country": "USA", "division": "NVL Central",
        "franchise_rating": 73, "style": "tempo", "defense": "blitz_heavy",
        "philosophy": "aggressive", "tempo": "fast",
    },
    "aus": {
        "city": "Austin", "name": "Aviators", "abbr": "AUS",
        "state": "TX", "country": "USA", "division": "NVL West",
        "franchise_rating": 84, "style": "air_raid", "defense": "zone",
        "philosophy": "kick_heavy", "tempo": "fast",
    },
    "boi": {
        "city": "Boise", "name": "Burners", "abbr": "BOI",
        "state": "ID", "country": "USA", "division": "NVL West",
        "franchise_rating": 69, "style": "tempo", "defense": "swarm",
        "philosophy": "aggressive", "tempo": "fast",
    },
    "la": {
        "city": "Los Angeles", "name": "Linx", "abbr": "LAX",
        "state": "CA", "country": "USA", "division": "NVL West",
        "franchise_rating": 90, "style": "west_coast", "defense": "man_press",
        "philosophy": "hybrid", "tempo": "moderate",
    },
    "pdx": {
        "city": "Portland", "name": "Prowlers", "abbr": "PDX",
        "state": "OR", "country": "USA", "division": "NVL West",
        "franchise_rating": 76, "style": "lateral_chaos", "defense": "bend_no_break",
        "philosophy": "aggressive", "tempo": "fast",
    },
    "spk": {
        "city": "Spokane", "name": "Spikes", "abbr": "SPK",
        "state": "WA", "country": "USA", "division": "NVL West",
        "franchise_rating": 66, "style": "smashmouth", "defense": "swarm",
        "philosophy": "conservative", "tempo": "slow",
    },
    "abq": {
        "city": "Albuquerque", "name": "Aftershocks", "abbr": "ABQ",
        "state": "NM", "country": "USA", "division": "NVL West",
        "franchise_rating": 78, "style": "triple_option", "defense": "blitz_heavy",
        "philosophy": "hybrid", "tempo": "moderate",
    },
}

ROSTER_TEMPLATE = [
    ("Viper", 3),
    ("Zeroback", 3),
    ("Halfback", 4),
    ("Wingback", 4),
    ("Slotback", 4),
    ("Keeper", 3),
    ("Offensive Line", 8),
    ("Defensive Line", 7),
]

STAT_KEYS = [
    "speed", "stamina", "kicking", "lateral_skill", "tackling",
    "agility", "power", "awareness", "hands", "kick_power", "kick_accuracy",
]

YEAR_LABELS = ["Rookie", "2nd Year", "3rd Year", "Veteran", "Veteran", "Veteran"]


def gen_pro_stats(franchise_rating: int, rng: random.Random) -> dict:
    base = 60 + (franchise_rating - 60) * 0.4
    stats = {}
    for key in STAT_KEYS:
        val = int(rng.gauss(base, 8))
        val = max(55, min(97, val))
        stats[key] = val
    return stats


def gen_pro_player(number: int, position: str, franchise_rating: int,
                   team_info: dict, rng: random.Random, used_names: set) -> dict:
    for _ in range(50):
        player_data = generate_player_name(gender='male')
        if player_data["full_name"] not in used_names:
            break
    used_names.add(player_data["full_name"])

    stats = gen_pro_stats(franchise_rating, rng)

    if position in ("Viper", "Zeroback", "Halfback", "Wingback", "Slotback"):
        archetype = assign_archetype(
            position, stats["speed"], stats["stamina"],
            stats["kicking"], stats["lateral_skill"], stats["tackling"]
        )
    else:
        archetype = "none"

    year_idx = rng.choices(range(6), weights=[15, 20, 20, 20, 15, 10])[0]
    year = YEAR_LABELS[year_idx]

    return {
        "number": number,
        "name": player_data["full_name"],
        "position": position,
        "height": player_data.get("height", "6-0"),
        "weight": rng.randint(175, 240) if position not in ("Offensive Line", "Defensive Line") else rng.randint(225, 290),
        "year": year,
        "hometown": player_data.get("hometown", {"city": "", "state": "", "country": "USA", "region": ""}),
        "high_school": player_data.get("high_school", ""),
        "nationality": player_data.get("nationality", "American"),
        "archetype": archetype,
        "potential": rng.randint(2, 5),
        "development": rng.choice(["normal", "quick", "late_bloomer"]),
        "contract": {"years": rng.randint(1, 4), "salary": 0},
        "stats": stats,
    }


def generate_nvl_team(key: str, info: dict) -> dict:
    rng = random.Random(hash(key) + 42)
    used_names = set()

    players = []
    jersey = 1
    for position, count in ROSTER_TEMPLATE:
        for _ in range(count):
            player = gen_pro_player(jersey, position, info["franchise_rating"],
                                    info, rng, used_names)
            players.append(player)
            jersey += 1

    hidden_gem_count = rng.randint(2, 5)
    skill_indices = [i for i, p in enumerate(players) if p["position"] not in ("Offensive Line", "Defensive Line")]
    gems = rng.sample(skill_indices, min(hidden_gem_count, len(skill_indices)))
    for idx in gems:
        boost = rng.randint(8, 18)
        for stat in rng.sample(STAT_KEYS, rng.randint(3, 6)):
            players[idx]["stats"][stat] = min(99, players[idx]["stats"][stat] + boost)

    avg_speed = sum(p["stats"]["speed"] for p in players) // len(players)
    avg_stamina = sum(p["stats"]["stamina"] for p in players) // len(players)
    avg_kicking = sum(p["stats"]["kicking"] for p in players) // len(players)
    avg_lateral = sum(p["stats"]["lateral_skill"] for p in players) // len(players)
    avg_tackling = sum(p["stats"]["tackling"] for p in players) // len(players)

    team_data = {
        "team_info": {
            "school_id": key,
            "school_name": f"{info['city']} {info['name']}",
            "abbreviation": info["abbr"],
            "mascot": info["name"],
            "conference": info["division"],
            "city": info["city"],
            "state": info["state"],
            "country": info.get("country", "USA"),
            "colors": _team_colors(key),
        },
        "identity": {
            "style": info.get("philosophy", "hybrid"),
            "philosophy": info.get("philosophy", "hybrid"),
            "tempo": info.get("tempo", "moderate"),
            "two_way_emphasis": "low",
        },
        "style": {
            "offense_style": info["style"],
            "defense_style": info["defense"],
            "st_scheme": "aces",
        },
        "prestige": info["franchise_rating"],
        "franchise_rating": info["franchise_rating"],
        "recruiting_pipeline": {
            "northeast": 0.18, "mid_atlantic": 0.12, "south": 0.18,
            "midwest": 0.16, "west_coast": 0.16, "texas_southwest": 0.14,
            "canadian_english": 0.03, "canadian_french": 0.03,
        },
        "team_stats": {
            "avg_speed": avg_speed,
            "avg_stamina": avg_stamina,
            "kicking_strength": avg_kicking,
            "lateral_proficiency": avg_lateral,
            "defensive_strength": avg_tackling,
        },
        "roster": {
            "size": len(players),
            "players": players,
        },
    }

    return team_data


def _team_colors(key: str) -> list:
    colors = {
        "nj": ["Green", "Black"], "bos": ["Navy", "Gold"],
        "eri": ["Steel Gray", "Crimson"], "orl": ["Purple", "Silver"],
        "bal": ["Orange", "Black"], "roc": ["Blue", "White"],
        "tor": ["Red", "White"], "qc": ["Blue", "Gold"],
        "van": ["Teal", "Silver"], "cal": ["Ice Blue", "White"],
        "dul": ["Slate", "Copper"], "mtl": ["Royal Blue", "Crimson"],
        "nol": ["Black", "Gold"], "mem": ["Brown", "Teal"],
        "chi": ["Navy", "Orange"], "ark": ["Cardinal", "White"],
        "oma": ["Black", "Red"], "bhm": ["Red", "Silver"],
        "aus": ["Sky Blue", "White"], "boi": ["Orange", "Blue"],
        "la": ["Purple", "Gold"], "pdx": ["Forest Green", "Cream"],
        "spk": ["Maroon", "Gray"], "abq": ["Turquoise", "Sand"],
    }
    return colors.get(key, ["Gray", "White"])


def main():
    output_dir = Path(__file__).parent.parent / "data" / "nvl_teams"
    output_dir.mkdir(parents=True, exist_ok=True)

    for key, info in NVL_TEAMS.items():
        team_data = generate_nvl_team(key, info)
        filepath = output_dir / f"{key}.json"
        with open(filepath, "w") as f:
            json.dump(team_data, f, indent=2)
        print(f"  {key}: {info['city']} {info['name']} ({info['franchise_rating']})")

    print(f"\nGenerated {len(NVL_TEAMS)} NVL team files in {output_dir}")


if __name__ == "__main__":
    main()
