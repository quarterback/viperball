#!/usr/bin/env python3
"""Generate team JSON files for all international Viperball pro leagues.

Creates team rosters for:
- Eurasian League (EL): 10 teams, 2 divisions
- AfroLeague (AL): 12 teams, 2 divisions
- Pacific League (PL): 8 teams, 2 divisions
- LigaAmerica (LA): 10 teams, 2 divisions

Uses the same structure as NVL teams (generate_nvl_teams.py pattern).
Each league has culturally appropriate player names and attribute ranges
per the talent tier table in the pro leagues spec.
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_names import generate_player_name, load_name_pools
from scripts.generate_rosters import assign_archetype

# ── Roster template (same as NVL) ───────────────────────────────────
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

OFFENSE_STYLES = [
    "balanced", "smashmouth", "air_raid", "west_coast", "power_spread",
    "lateral_chaos", "triple_option", "ground_pound", "tempo",
]
DEFENSE_STYLES = [
    "base_defense", "blitz_heavy", "zone", "man_press", "swarm", "bend_no_break",
]
PHILOSOPHIES = ["aggressive", "hybrid", "conservative", "ground_heavy", "kick_heavy"]
TEMPOS = ["fast", "moderate", "slow", "variable"]


# ═══════════════════════════════════════════════════════════════════════
# EURASIAN LEAGUE (EL) — 10 teams, 2 divisions of 5
# ═══════════════════════════════════════════════════════════════════════
EL_TEAMS = {
    # Nordic Division
    "sto": {
        "city": "Stockholm", "name": "Serpents", "abbr": "STO",
        "state": "SWE", "country": "Sweden", "division": "Nordic",
        "franchise_rating": 78, "origins": ["nordic"],
    },
    "hel": {
        "city": "Helsinki", "name": "Frost", "abbr": "HEL",
        "state": "FIN", "country": "Finland", "division": "Nordic",
        "franchise_rating": 72, "origins": ["nordic"],
    },
    "cop": {
        "city": "Copenhagen", "name": "Vikings", "abbr": "COP",
        "state": "DEN", "country": "Denmark", "division": "Nordic",
        "franchise_rating": 75, "origins": ["nordic"],
    },
    "osl": {
        "city": "Oslo", "name": "Trolls", "abbr": "OSL",
        "state": "NOR", "country": "Norway", "division": "Nordic",
        "franchise_rating": 68, "origins": ["nordic"],
    },
    "ams": {
        "city": "Amsterdam", "name": "Windmills", "abbr": "AMS",
        "state": "NED", "country": "Netherlands", "division": "Nordic",
        "franchise_rating": 76, "origins": ["dutch", "nordic"],
    },
    # Continental Division
    "bru": {
        "city": "Brussels", "name": "Wolves", "abbr": "BRU",
        "state": "BEL", "country": "Belgium", "division": "Continental",
        "franchise_rating": 70, "origins": ["dutch", "french"],
    },
    "ber": {
        "city": "Berlin", "name": "Iron Eagles", "abbr": "BER",
        "state": "GER", "country": "Germany", "division": "Continental",
        "franchise_rating": 80, "origins": ["german", "nordic"],
    },
    "pra": {
        "city": "Prague", "name": "Golems", "abbr": "PRA",
        "state": "CZE", "country": "Czech Republic", "division": "Continental",
        "franchise_rating": 66, "origins": ["czech", "german"],
    },
    "war": {
        "city": "Warsaw", "name": "Hussars", "abbr": "WAR",
        "state": "POL", "country": "Poland", "division": "Continental",
        "franchise_rating": 64, "origins": ["polish", "german"],
    },
    "zur": {
        "city": "Zurich", "name": "Alpines", "abbr": "ZUR",
        "state": "CHE", "country": "Switzerland", "division": "Continental",
        "franchise_rating": 73, "origins": ["german", "french"],
    },
}

# ═══════════════════════════════════════════════════════════════════════
# AFROLEAGUE (AL) — 12 teams, 2 divisions of 6
# ═══════════════════════════════════════════════════════════════════════
AL_TEAMS = {
    # West Division
    "lag": {
        "city": "Lagos", "name": "Lions", "abbr": "LAG",
        "state": "NGA", "country": "Nigeria", "division": "West",
        "franchise_rating": 76, "origins": ["african", "caribbean"],
    },
    "acc": {
        "city": "Accra", "name": "Gold Stars", "abbr": "ACC",
        "state": "GHA", "country": "Ghana", "division": "West",
        "franchise_rating": 72, "origins": ["african", "caribbean"],
    },
    "dak": {
        "city": "Dakar", "name": "Teranga", "abbr": "DAK",
        "state": "SEN", "country": "Senegal", "division": "West",
        "franchise_rating": 70, "origins": ["african", "caribbean"],
    },
    "cas": {
        "city": "Casablanca", "name": "Atlas", "abbr": "CAS",
        "state": "MAR", "country": "Morocco", "division": "West",
        "franchise_rating": 68, "origins": ["arabic", "african"],
    },
    "abi": {
        "city": "Abidjan", "name": "Elephants", "abbr": "ABI",
        "state": "CIV", "country": "Côte d'Ivoire", "division": "West",
        "franchise_rating": 65, "origins": ["african", "caribbean"],
    },
    "abj": {
        "city": "Abuja", "name": "Eagles", "abbr": "ABJ",
        "state": "NGA", "country": "Nigeria", "division": "West",
        "franchise_rating": 60, "origins": ["african", "caribbean"],
    },
    # East Division
    "nai": {
        "city": "Nairobi", "name": "Harambee", "abbr": "NAI",
        "state": "KEN", "country": "Kenya", "division": "East",
        "franchise_rating": 74, "origins": ["african", "caribbean"],
    },
    "joh": {
        "city": "Johannesburg", "name": "Springboks", "abbr": "JOH",
        "state": "ZAF", "country": "South Africa", "division": "East",
        "franchise_rating": 78, "origins": ["african", "uk_european"],
    },
    "cai": {
        "city": "Cairo", "name": "Pharaohs", "abbr": "CAI",
        "state": "EGY", "country": "Egypt", "division": "East",
        "franchise_rating": 71, "origins": ["arabic", "african"],
    },
    "dar": {
        "city": "Dar es Salaam", "name": "Dhows", "abbr": "DAR",
        "state": "TZA", "country": "Tanzania", "division": "East",
        "franchise_rating": 63, "origins": ["african", "caribbean"],
    },
    "add": {
        "city": "Addis Ababa", "name": "Runners", "abbr": "ADD",
        "state": "ETH", "country": "Ethiopia", "division": "East",
        "franchise_rating": 66, "origins": ["african", "caribbean"],
    },
    "kam": {
        "city": "Kampala", "name": "Cranes", "abbr": "KAM",
        "state": "UGA", "country": "Uganda", "division": "East",
        "franchise_rating": 61, "origins": ["african", "caribbean"],
    },
}

# ═══════════════════════════════════════════════════════════════════════
# PACIFIC LEAGUE (PL) — 8 teams, 2 divisions of 4
# ═══════════════════════════════════════════════════════════════════════
PL_TEAMS = {
    # North Division
    "tai": {
        "city": "Taipei", "name": "Dragons", "abbr": "TAI",
        "state": "TWN", "country": "Taiwan", "division": "North",
        "franchise_rating": 73, "origins": ["east_asian"],
    },
    "man": {
        "city": "Manila", "name": "Typhoons", "abbr": "MAN",
        "state": "PHL", "country": "Philippines", "division": "North",
        "franchise_rating": 68, "origins": ["southeast_asian"],
    },
    "seo": {
        "city": "Seoul", "name": "Tigers", "abbr": "SEO",
        "state": "KOR", "country": "South Korea", "division": "North",
        "franchise_rating": 75, "origins": ["east_asian"],
    },
    "osa": {
        "city": "Osaka", "name": "Samurai", "abbr": "OSA",
        "state": "JPN", "country": "Japan", "division": "North",
        "franchise_rating": 71, "origins": ["east_asian"],
    },
    # South Division
    "jak": {
        "city": "Jakarta", "name": "Komodos", "abbr": "JAK",
        "state": "IDN", "country": "Indonesia", "division": "South",
        "franchise_rating": 66, "origins": ["southeast_asian"],
    },
    "ban": {
        "city": "Bangkok", "name": "Muay", "abbr": "BAN",
        "state": "THA", "country": "Thailand", "division": "South",
        "franchise_rating": 70, "origins": ["southeast_asian"],
    },
    "hcm": {
        "city": "Ho Chi Minh City", "name": "Phoenix", "abbr": "HCM",
        "state": "VNM", "country": "Vietnam", "division": "South",
        "franchise_rating": 64, "origins": ["southeast_asian"],
    },
    "sgp": {
        "city": "Singapore", "name": "Merlions", "abbr": "SGP",
        "state": "SGP", "country": "Singapore", "division": "South",
        "franchise_rating": 72, "origins": ["southeast_asian", "east_asian"],
    },
}

# ═══════════════════════════════════════════════════════════════════════
# LIGAAMERICA (LA) — 10 teams, 2 divisions of 5
# ═══════════════════════════════════════════════════════════════════════
LA_TEAMS = {
    # Norte Division
    "mex": {
        "city": "Mexico City", "name": "Aztecas", "abbr": "MEX",
        "state": "MEX", "country": "Mexico", "division": "Norte",
        "franchise_rating": 76, "origins": ["latin_american"],
    },
    "sao": {
        "city": "São Paulo", "name": "Jaguares", "abbr": "SAO",
        "state": "BRA", "country": "Brazil", "division": "Norte",
        "franchise_rating": 78, "origins": ["latin_american", "african"],
    },
    "bue": {
        "city": "Buenos Aires", "name": "Gauchos", "abbr": "BUE",
        "state": "ARG", "country": "Argentina", "division": "Norte",
        "franchise_rating": 74, "origins": ["latin_american", "italian"],
    },
    "bog": {
        "city": "Bogotá", "name": "Cóndores", "abbr": "BOG",
        "state": "COL", "country": "Colombia", "division": "Norte",
        "franchise_rating": 70, "origins": ["latin_american"],
    },
    "lim": {
        "city": "Lima", "name": "Incas", "abbr": "LIM",
        "state": "PER", "country": "Peru", "division": "Norte",
        "franchise_rating": 65, "origins": ["latin_american"],
    },
    # Caribe Division
    "sju": {
        "city": "San Juan", "name": "Huracanes", "abbr": "SJU",
        "state": "PRI", "country": "Puerto Rico", "division": "Caribe",
        "franchise_rating": 72, "origins": ["caribbean", "latin_american"],
    },
    "sdo": {
        "city": "Santo Domingo", "name": "Leones", "abbr": "SDO",
        "state": "DOM", "country": "Dominican Republic", "division": "Caribe",
        "franchise_rating": 69, "origins": ["caribbean", "latin_american"],
    },
    "hav": {
        "city": "Havana", "name": "Cocodrilos", "abbr": "HAV",
        "state": "CUB", "country": "Cuba", "division": "Caribe",
        "franchise_rating": 67, "origins": ["caribbean", "latin_american"],
    },
    "mvd": {
        "city": "Montevideo", "name": "Charrúas", "abbr": "MVD",
        "state": "URU", "country": "Uruguay", "division": "Caribe",
        "franchise_rating": 63, "origins": ["latin_american"],
    },
    "stg": {
        "city": "Santiago", "name": "Mineros", "abbr": "STG",
        "state": "CHI", "country": "Chile", "division": "Caribe",
        "franchise_rating": 71, "origins": ["latin_american", "spanish"],
    },
}

ALL_LEAGUES = {
    "el": ("Eurasian League", EL_TEAMS, (58, 85), (50, 80)),
    "al": ("AfroLeague", AL_TEAMS, (55, 82), (45, 78)),
    "pl": ("Pacific League", PL_TEAMS, (55, 80), (45, 75)),
    "la": ("LigaAmerica", LA_TEAMS, (55, 82), (45, 78)),
}


def _team_colors(key: str) -> list:
    """Assign team colors based on key."""
    colors = {
        # EL
        "sto": ["Blue", "Yellow"], "hel": ["White", "Blue"],
        "cop": ["Red", "White"], "osl": ["Blue", "Red"],
        "ams": ["Orange", "White"], "bru": ["Red", "Gold"],
        "ber": ["Black", "White"], "pra": ["Red", "Blue"],
        "war": ["White", "Red"], "zur": ["Red", "White"],
        # AL
        "lag": ["Green", "White"], "acc": ["Gold", "Black"],
        "dak": ["Green", "Yellow"], "cas": ["Red", "Green"],
        "abi": ["Orange", "Green"], "abj": ["Green", "Gold"],
        "nai": ["Red", "Black"], "joh": ["Green", "Gold"],
        "cai": ["Red", "White"], "dar": ["Blue", "Green"],
        "add": ["Green", "Gold"], "kam": ["Red", "Yellow"],
        # PL
        "tai": ["Red", "Blue"], "man": ["Blue", "Red"],
        "seo": ["White", "Red"], "osa": ["Purple", "Gold"],
        "jak": ["Red", "White"], "ban": ["Blue", "Gold"],
        "hcm": ["Red", "Yellow"], "sgp": ["Red", "White"],
        # LA
        "mex": ["Green", "Red"], "sao": ["Yellow", "Green"],
        "bue": ["Light Blue", "White"], "bog": ["Yellow", "Blue"],
        "lim": ["Red", "White"], "sju": ["Blue", "Red"],
        "sdo": ["Red", "Blue"], "hav": ["Blue", "White"],
        "mvd": ["Light Blue", "Gold"], "stg": ["Red", "Blue"],
    }
    return colors.get(key, ["Gray", "White"])


def gen_pro_stats(franchise_rating: int, attr_range: tuple, rng: random.Random) -> dict:
    """Generate pro-level player stats based on franchise rating and league attribute range."""
    lo, hi = attr_range
    base = lo + (franchise_rating - 45) * 0.4  # Scale base from franchise rating
    base = max(lo, min(hi - 5, base))
    stats = {}
    for key in STAT_KEYS:
        val = int(rng.gauss(base, 8))
        val = max(lo - 5, min(hi + 3, val))
        stats[key] = val
    return stats


def gen_pro_player(number: int, position: str, franchise_rating: int,
                   team_info: dict, attr_range: tuple, rng: random.Random,
                   used_names: set) -> dict:
    """Generate a single player for an international pro team."""
    # Pick a random origin from the team's origin pool
    origins = team_info.get("origins", ["african"])
    origin = rng.choice(origins)

    for _ in range(50):
        player_data = generate_player_name(origin=origin, region=origin, gender='male')
        if player_data["full_name"] not in used_names:
            break
    used_names.add(player_data["full_name"])

    stats = gen_pro_stats(franchise_rating, attr_range, rng)

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
        "hometown": player_data.get("hometown", {"city": "", "state": "", "country": "", "region": ""}),
        "high_school": player_data.get("high_school", ""),
        "nationality": player_data.get("nationality", ""),
        "archetype": archetype,
        "potential": rng.randint(2, 5),
        "development": rng.choice(["normal", "quick", "late_bloomer"]),
        "contract": {"years": rng.randint(1, 4), "salary": 0},
        "stats": stats,
    }


def generate_team(key: str, info: dict, attr_range: tuple) -> dict:
    """Generate a full team JSON for an international pro team."""
    rng = random.Random(hash(key) + 42)
    used_names = set()

    players = []
    jersey = 1
    for position, count in ROSTER_TEMPLATE:
        for _ in range(count):
            player = gen_pro_player(
                jersey, position, info["franchise_rating"],
                info, attr_range, rng, used_names
            )
            players.append(player)
            jersey += 1

    # Add hidden gems (boosted players)
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

    # Random style selection
    style = rng.choice(OFFENSE_STYLES)
    defense = rng.choice(DEFENSE_STYLES)
    philosophy = rng.choice(PHILOSOPHIES)
    tempo = rng.choice(TEMPOS)

    team_data = {
        "team_info": {
            "school_id": key,
            "school_name": f"{info['city']} {info['name']}",
            "abbreviation": info["abbr"],
            "mascot": info["name"],
            "conference": info["division"],
            "city": info["city"],
            "state": info["state"],
            "country": info.get("country", ""),
            "colors": _team_colors(key),
        },
        "identity": {
            "style": philosophy,
            "philosophy": philosophy,
            "tempo": tempo,
            "two_way_emphasis": "low",
        },
        "style": {
            "offense_style": style,
            "defense_style": defense,
            "st_scheme": "aces",
        },
        "prestige": info["franchise_rating"],
        "franchise_rating": info["franchise_rating"],
        "recruiting_pipeline": {
            "northeast": 0.05, "mid_atlantic": 0.05, "south": 0.05,
            "midwest": 0.05, "west_coast": 0.05, "texas_southwest": 0.05,
            "canadian_english": 0.03, "canadian_french": 0.02,
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


def generate_league(league_id: str):
    """Generate all teams for a single league."""
    league_name, teams_dict, attr_range, rating_range = ALL_LEAGUES[league_id]
    output_dir = Path(__file__).parent.parent / "data" / f"{league_id}_teams"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  {league_name} ({league_id.upper()}) — {len(teams_dict)} teams")
    print(f"  Attribute range: {attr_range}")
    print(f"{'='*60}")

    for key, info in teams_dict.items():
        team_data = generate_team(key, info, attr_range)
        filepath = output_dir / f"{key}.json"
        with open(filepath, "w") as f:
            json.dump(team_data, f, indent=2)
        print(f"  {key}: {info['city']} {info['name']} (FR: {info['franchise_rating']})")

    print(f"\nGenerated {len(teams_dict)} team files in {output_dir}")


def main():
    """Generate teams for all international leagues."""
    # Pre-load name pools to warm the cache
    load_name_pools(gender='male')

    if len(sys.argv) > 1:
        # Generate specific league(s)
        for league_id in sys.argv[1:]:
            if league_id in ALL_LEAGUES:
                generate_league(league_id)
            else:
                print(f"Unknown league: {league_id}. Valid: {list(ALL_LEAGUES.keys())}")
    else:
        # Generate all leagues
        for league_id in ALL_LEAGUES:
            generate_league(league_id)

    print("\nDone!")


if __name__ == "__main__":
    main()
