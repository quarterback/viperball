#!/usr/bin/env python3
"""
WVL Team Generator
==================

Generates 64 team JSON files for the Women's Viperball League across 4 tiers.
Follows the same format as existing NVL team files in data/nvl_teams/.

Usage:
    python scripts/generate_wvl_teams.py
"""

import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.wvl_config import (
    ALL_CLUBS, CLUBS_BY_TIER, COUNTRY_STYLE_TENDENCIES, WVLClub,
)

# ── Roster configuration ──
ROSTER_SIZE = 36
ROSTER_TEMPLATE = [
    ("Viper", True), ("Viper", False), ("Viper", False),
    ("Zeroback", False), ("Zeroback", False), ("Zeroback", False),
    ("Halfback", False), ("Halfback", False),
    ("Halfback", False), ("Halfback", False),
    ("Wingback", False), ("Wingback", False),
    ("Wingback", False), ("Wingback", False),
    ("Slotback", False), ("Slotback", False),
    ("Slotback", False), ("Slotback", False),
    ("Keeper", False), ("Keeper", False), ("Keeper", False),
    ("Offensive Line", False), ("Offensive Line", False),
    ("Offensive Line", False), ("Offensive Line", False),
    ("Offensive Line", False), ("Offensive Line", False),
    ("Offensive Line", False), ("Offensive Line", False),
    ("Defensive Line", False), ("Defensive Line", False),
    ("Defensive Line", False), ("Defensive Line", False),
    ("Defensive Line", False), ("Defensive Line", False),
    ("Defensive Line", False),
]

# ── Position archetypes (same as game engine) ──
POSITION_ARCHETYPES = {
    "Viper": ["hybrid_viper", "scrambler", "pocket_passer", "dual_threat"],
    "Zeroback": ["power_back", "speed_back", "receiving_back", "bruiser"],
    "Halfback": ["speed_back", "power_back", "all_purpose", "elusive"],
    "Wingback": ["burner", "possession", "deep_threat", "slot_specialist"],
    "Slotback": ["slot_specialist", "possession", "burner", "hybrid"],
    "Keeper": ["run_stopper", "coverage", "enforcer", "ball_hawk"],
    "Offensive Line": ["mauler", "technician", "road_grader", "balanced"],
    "Defensive Line": ["edge_rusher", "run_stuffer", "interior_disruptor", "hybrid"],
}

# ── Country name pools for pro players ──
# Female first names by country/region
FIRST_NAMES = {
    "Spain": ["Lucía", "María", "Carmen", "Ana", "Isabel", "Elena", "Sofía", "Paula",
              "Pilar", "Rosa", "Marta", "Laura", "Irene", "Alba", "Nuria", "Silvia",
              "Raquel", "Cristina", "Andrea", "Julia"],
    "England": ["Emma", "Olivia", "Charlotte", "Amelia", "Isla", "Sophie", "Grace",
                "Ruby", "Lily", "Jessica", "Mia", "Holly", "Eleanor", "Lucy", "Chloe",
                "Hannah", "Freya", "Alice", "Daisy", "Poppy"],
    "Italy": ["Giulia", "Francesca", "Chiara", "Sara", "Valentina", "Alessia", "Martina",
              "Elisa", "Giorgia", "Federica", "Ilaria", "Elena", "Claudia", "Silvia",
              "Arianna", "Beatrice", "Camilla", "Aurora", "Serena", "Viola"],
    "Germany": ["Anna", "Lena", "Julia", "Lea", "Laura", "Lisa", "Marie", "Sarah",
                "Katharina", "Hannah", "Jana", "Sophia", "Nina", "Johanna", "Clara",
                "Luisa", "Emma", "Mia", "Frieda", "Greta"],
    "France": ["Camille", "Manon", "Léa", "Inès", "Chloé", "Emma", "Sarah", "Jade",
               "Louise", "Léna", "Marie", "Julie", "Alice", "Clara", "Margot", "Zoé",
               "Lola", "Océane", "Romane", "Pauline"],
    "Portugal": ["Maria", "Ana", "Joana", "Inês", "Beatriz", "Sofia", "Rita", "Mariana",
                 "Carolina", "Leonor", "Catarina", "Teresa", "Sara", "Diana", "Marta",
                 "Raquel", "Filipa", "Helena", "Clara", "Isabel"],
    "Netherlands": ["Emma", "Sanne", "Lotte", "Fleur", "Sophie", "Julia", "Lieke",
                    "Daphne", "Iris", "Eva", "Noa", "Anouk", "Roos", "Fenna", "Maud",
                    "Britt", "Lisa", "Anne", "Kim", "Yara"],
    "Scotland": ["Eilidh", "Isla", "Freya", "Skye", "Iona", "Ailsa", "Morag", "Fiona",
                 "Kirsty", "Mhairi", "Catriona", "Heather", "Shona", "Gillian", "Aileen",
                 "Emma", "Sophie", "Olivia", "Grace", "Lucy"],
    "Wales": ["Cerys", "Seren", "Ffion", "Gwen", "Nia", "Megan", "Catrin", "Rhiannon",
              "Elin", "Bethan", "Lowri", "Carys", "Siân", "Angharad", "Efa",
              "Manon", "Eleri", "Alys", "Non", "Mali"],
    "Turkey": ["Elif", "Zeynep", "Defne", "Ecrin", "Nehir", "Yağmur", "Azra", "Asya",
               "Eylül", "Lara", "Derin", "Sude", "Nisa", "Ada", "Berra",
               "Melis", "İrem", "Ceren", "Deniz", "Selin"],
    "Greece": ["Eleni", "Maria", "Sophia", "Katerina", "Anna", "Christina", "Dimitra",
               "Eirini", "Georgia", "Vasiliki", "Ioanna", "Paraskevi", "Athena",
               "Nikoletta", "Ourania", "Theodora", "Chrysa", "Stavroula", "Fotini", "Despina"],
    "Finland": ["Aino", "Emma", "Sofia", "Ella", "Emilia", "Helmi", "Siiri", "Venla",
                "Eevi", "Iida", "Saara", "Anni", "Lilja", "Minja", "Viivi",
                "Nea", "Ronja", "Pihla", "Ilona", "Noora"],
    "Norway": ["Nora", "Emma", "Ella", "Maja", "Olivia", "Sofie", "Ingrid", "Sigrid",
               "Astrid", "Thea", "Ida", "Emilie", "Leah", "Sara", "Amalie",
               "Frida", "Solveig", "Maren", "Tuva", "Hedda"],
    "USA": ["Sophia", "Emma", "Olivia", "Ava", "Isabella", "Mia", "Charlotte", "Amelia",
            "Harper", "Evelyn", "Abigail", "Emily", "Madison", "Luna", "Chloe",
            "Layla", "Ella", "Avery", "Scarlett", "Aria"],
}

LAST_NAMES = {
    "Spain": ["García", "Rodríguez", "Martínez", "López", "Hernández", "González",
              "Pérez", "Sánchez", "Ramírez", "Torres", "Díaz", "Moreno", "Muñoz",
              "Álvarez", "Romero", "Navarro", "Domínguez", "Gutiérrez", "Ortega", "Rubio"],
    "England": ["Smith", "Jones", "Taylor", "Brown", "Williams", "Wilson", "Johnson",
                "Davies", "Robinson", "Wright", "Thompson", "Evans", "Walker", "White",
                "Roberts", "Green", "Hall", "Clarke", "Lewis", "Young"],
    "Italy": ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo",
              "Ricci", "Marino", "Greco", "Bruno", "Gallo", "Conti", "Costa",
              "Mancini", "Barbieri", "Fontana", "Santoro", "Mariani", "Rinaldi"],
    "Germany": ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner",
                "Becker", "Schulz", "Hoffmann", "Schäfer", "Koch", "Bauer", "Richter",
                "Klein", "Wolf", "Schröder", "Neumann", "Schwarz", "Braun"],
    "France": ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit",
               "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel",
               "Garcia", "David", "Bertrand", "Roux", "Vincent", "Fournier"],
    "Portugal": ["Silva", "Santos", "Ferreira", "Pereira", "Oliveira", "Costa", "Rodrigues",
                 "Martins", "Sousa", "Fernandes", "Gonçalves", "Gomes", "Lopes", "Marques",
                 "Almeida", "Ribeiro", "Pinto", "Carvalho", "Teixeira", "Moreira"],
    "Netherlands": ["de Jong", "Jansen", "de Vries", "van den Berg", "Bakker", "Janssen",
                    "Visser", "Smit", "Meijer", "de Boer", "Mulder", "de Groot",
                    "Bos", "Vos", "Peters", "Hendriks", "van Dijk", "Dekker", "Brouwer", "Kok"],
    "Scotland": ["Campbell", "Stewart", "Robertson", "Thomson", "MacDonald", "Fraser",
                 "Murray", "Anderson", "MacKenzie", "Ross", "Graham", "Hamilton",
                 "Reid", "Douglas", "Scott", "Crawford", "Burns", "Sinclair", "Kerr", "Wallace"],
    "Wales": ["Jones", "Williams", "Davies", "Thomas", "Evans", "Roberts", "Lewis",
              "Morgan", "Hughes", "Edwards", "Griffiths", "Owen", "Price", "Phillips",
              "Morris", "Jenkins", "James", "Powell", "Rees", "Lloyd"],
    "Turkey": ["Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Yıldırım",
               "Öztürk", "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan",
               "Çetin", "Kara", "Koç", "Kurt", "Özkan", "Polat"],
    "Greece": ["Papadopoulos", "Pappas", "Nikolaou", "Georgiou", "Dimitriou",
               "Konstantinou", "Ioannou", "Christodoulou", "Vasileiou", "Alexiou",
               "Theodorou", "Angelou", "Stavrou", "Michailidis", "Petrou",
               "Oikonomou", "Panagiotou", "Koutsou", "Makris", "Vlachos"],
    "Finland": ["Korhonen", "Virtanen", "Mäkinen", "Nieminen", "Mäkelä", "Hämäläinen",
                "Laine", "Heikkinen", "Koskinen", "Järvinen", "Lehtonen", "Lehtinen",
                "Saarinen", "Salminen", "Heinonen", "Niemi", "Heikkilä", "Kinnunen",
                "Salonen", "Tuominen"],
    "Norway": ["Hansen", "Johansen", "Olsen", "Larsen", "Andersen", "Pedersen",
               "Nilsen", "Kristiansen", "Jensen", "Karlsen", "Eriksen", "Johnsen",
               "Pettersen", "Haugen", "Berg", "Halvorsen", "Solberg", "Henriksen",
               "Bakken", "Moen"],
    "USA": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
            "Davis", "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Moore",
            "Jackson", "Martin", "Lee", "Thompson", "Harris", "Clark"],
}


def generate_player_name(country: str, rng: random.Random) -> dict:
    """Generate a female player name appropriate for the club's country."""
    firsts = FIRST_NAMES.get(country, FIRST_NAMES["England"])
    lasts = LAST_NAMES.get(country, LAST_NAMES["England"])
    first = rng.choice(firsts)
    last = rng.choice(lasts)
    return {
        "first_name": first,
        "last_name": last,
        "full_name": f"{first} {last}",
    }


def generate_player_stats(
    position: str,
    tier: int,
    club_prestige: int,
    rng: random.Random,
) -> dict:
    """Generate attribute stats for a pro player, scaled by tier and prestige."""
    # Base ranges by tier
    tier_ranges = {
        1: (70, 97),
        2: (62, 90),
        3: (55, 85),
        4: (48, 78),
    }
    lo, hi = tier_ranges.get(tier, (55, 85))

    # Prestige nudge: high prestige clubs get slightly better players
    prestige_bonus = (club_prestige - 60) / 40.0 * 5  # -2.5 to +5

    stats = {}
    for attr in ["speed", "stamina", "kicking", "lateral_skill", "tackling",
                 "agility", "power", "awareness", "hands", "kick_power", "kick_accuracy"]:
        base = rng.randint(lo, hi)
        base = int(base + prestige_bonus + rng.gauss(0, 3))
        stats[attr] = max(40, min(99, base))

    return stats


def generate_player(
    position: str,
    is_captain: bool,
    club: WVLClub,
    used_numbers: set,
    rng: random.Random,
) -> dict:
    """Generate a single pro player for a WVL team."""
    number = None
    while number is None or number in used_numbers:
        number = rng.randint(2, 99)
    used_numbers.add(number)

    name_data = generate_player_name(club.country, rng)
    stats = generate_player_stats(position, club.tier, club.prestige, rng)
    archetype = rng.choice(POSITION_ARCHETYPES.get(position, ["balanced"]))

    # Pro players are veterans (aged 22-33)
    age = rng.randint(22, 33)
    if age <= 24:
        year_label = "Young Pro"
    elif age <= 29:
        year_label = "Veteran"
    else:
        year_label = "Senior Pro"

    # Contract
    contract_years = rng.randint(1, 4)
    salary_tier = max(1, min(5, (stats["speed"] + stats["awareness"]) // 40))

    # Height/weight
    height_inches = rng.randint(62, 76)
    h_feet = height_inches // 12
    h_inches = height_inches % 12
    weight = rng.randint(140, 220)

    return {
        "number": number,
        "name": name_data["full_name"],
        "position": position,
        "height": f"{h_feet}-{h_inches}",
        "weight": weight,
        "year": year_label,
        "age": age,
        "hometown": {
            "city": club.city,
            "state": club.country[:3].upper(),
            "country": club.country,
            "region": club.country.lower(),
        },
        "high_school": "",
        "nationality": club.country,
        "archetype": archetype,
        "potential": rng.choices([1, 2, 3, 4, 5], weights=[5, 15, 40, 30, 10])[0],
        "development": rng.choice(["normal", "normal", "quick", "slow", "late_bloomer"]),
        "contract": {
            "years": contract_years,
            "salary": salary_tier,
        },
        "stats": stats,
    }


def generate_team_json(club: WVLClub, rng: random.Random) -> dict:
    """Generate a complete team JSON file for a WVL club."""
    country_styles = COUNTRY_STYLE_TENDENCIES.get(club.country, COUNTRY_STYLE_TENDENCIES["England"])

    offense_style = rng.choice(country_styles["offense_styles"])
    defense_style = rng.choice(country_styles["defense_styles"])
    st_scheme = rng.choice(country_styles["st_schemes"])

    # Generate roster
    used_numbers = set()
    players = []
    for pos, is_captain in ROSTER_TEMPLATE:
        player = generate_player(pos, is_captain, club, used_numbers, rng)
        players.append(player)

    # Compute team averages
    avg_speed = sum(p["stats"]["speed"] for p in players) // len(players)
    avg_stamina = sum(p["stats"]["stamina"] for p in players) // len(players)
    avg_kicking = sum(p["stats"]["kicking"] for p in players) // len(players)
    avg_lateral = sum(p["stats"]["lateral_skill"] for p in players) // len(players)
    avg_tackling = sum(p["stats"]["tackling"] for p in players) // len(players)

    team_data = {
        "team_info": {
            "school_id": club.key,
            "school_name": club.name,
            "abbreviation": club.key[:3].upper(),
            "mascot": club.name.split()[-1],
            "conference": f"WVL Tier {club.tier}",
            "city": club.city,
            "state": club.country[:3].upper(),
            "country": club.country,
            "colors": _get_club_colors(club.key),
        },
        "identity": {
            "style": "hybrid",
            "philosophy": "hybrid",
            "tempo": rng.choice(["slow", "moderate", "fast"]),
            "two_way_emphasis": rng.choice(["low", "medium", "high"]),
        },
        "style": {
            "offense_style": offense_style,
            "defense_style": defense_style,
            "st_scheme": st_scheme,
        },
        "prestige": club.prestige,
        "franchise_rating": club.prestige,
        "wvl_metadata": {
            "tier": club.tier,
            "country": club.country,
            "city": club.city,
            "narrative_tag": club.narrative_tag,
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


def _get_club_colors(key: str) -> list:
    """Return team colors based on club key."""
    COLORS = {
        "real_madrid": ["White", "Gold"],
        "fc_barcelona": ["Blue", "Red"],
        "man_united": ["Red", "White"],
        "liverpool": ["Red", "White"],
        "bayern_munich": ["Red", "White"],
        "juventus": ["Black", "White"],
        "ac_milan": ["Red", "Black"],
        "psg": ["Blue", "Red"],
        "arsenal": ["Red", "White"],
        "chelsea": ["Blue", "White"],
        "inter_milan": ["Blue", "Black"],
        "atletico_madrid": ["Red", "White"],
        "dortmund": ["Yellow", "Black"],
        "man_city": ["Sky Blue", "White"],
        "tottenham": ["White", "Navy"],
        "lyon": ["White", "Blue"],
        "wrexham": ["Red", "White"],
        "newcastle": ["Black", "White"],
        "as_roma": ["Crimson", "Gold"],
        "napoli": ["Sky Blue", "White"],
        "sevilla": ["White", "Red"],
        "ajax": ["White", "Red"],
        "benfica": ["Red", "White"],
        "porto": ["Blue", "White"],
        "celtic": ["Green", "White"],
        "rangers": ["Blue", "White"],
        "marseille": ["White", "Sky Blue"],
        "monaco": ["Red", "White"],
        "leverkusen": ["Red", "Black"],
        "rb_leipzig": ["White", "Red"],
        "villarreal": ["Yellow", "Blue"],
        "real_sociedad": ["Blue", "White"],
        "lazio": ["Sky Blue", "White"],
        "fiorentina": ["Purple", "White"],
        "sporting_cp": ["Green", "White"],
        "psv": ["Red", "White"],
        "feyenoord": ["Red", "White"],
        "portland": ["Green", "Gold"],
        "west_ham": ["Claret", "Sky Blue"],
        "aston_villa": ["Claret", "Sky Blue"],
        "everton": ["Blue", "White"],
        "leeds": ["White", "Blue"],
        "nott_forest": ["Red", "White"],
        "brighton": ["Blue", "White"],
        "swansea": ["White", "Black"],
        "hearts": ["Maroon", "White"],
        "real_betis": ["Green", "White"],
        "athletic_bilbao": ["Red", "White"],
        "deportivo": ["Blue", "White"],
        "valencia": ["White", "Black"],
        "atalanta": ["Blue", "Black"],
        "sassuolo": ["Green", "Black"],
        "hoffenheim": ["Blue", "White"],
        "frankfurt": ["Black", "Red"],
        "lapua": ["Blue", "Yellow"],
        "vimpeli": ["Red", "Blue"],
        "bodo_glimt": ["Yellow", "Black"],
        "lille": ["Red", "Blue"],
        "nice": ["Red", "Black"],
        "galatasaray": ["Red", "Yellow"],
        "fenerbahce": ["Yellow", "Blue"],
        "olympiacos": ["Red", "White"],
        "braga": ["Red", "White"],
        "torino": ["Maroon", "White"],
    }
    return COLORS.get(key, ["White", "Black"])


def main():
    rng = random.Random(42)
    base_dir = Path(__file__).parent.parent / "data" / "wvl_teams"

    for tier_num in range(1, 5):
        tier_dir = base_dir / f"tier{tier_num}"
        tier_dir.mkdir(parents=True, exist_ok=True)

        clubs = CLUBS_BY_TIER[tier_num]
        for club in clubs:
            team_data = generate_team_json(club, rng)
            filepath = tier_dir / f"{club.key}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(team_data, f, indent=2, ensure_ascii=False)
            print(f"  Generated: {filepath.relative_to(base_dir.parent.parent)}")

    # Write tier assignments
    assignments = {c.key: c.tier for c in ALL_CLUBS}
    assignments_path = base_dir.parent / "wvl_tier_assignments.json"
    with open(assignments_path, "w") as f:
        json.dump(assignments, f, indent=2)
    print(f"\n  Tier assignments: {assignments_path.relative_to(base_dir.parent.parent)}")

    print(f"\nGenerated {len(ALL_CLUBS)} WVL teams across 4 tiers.")


if __name__ == "__main__":
    main()
