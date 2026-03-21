import json
import random
import os

POSITIONS = [
    "Zeroback", "Viper", "Halfback", "Wingback", "Slotback",
    "Keeper", "Offensive Line", "Defensive Line"
]

POSITION_WEIGHTS = {
    "Zeroback": 3, "Viper": 3, "Halfback": 4, "Wingback": 4, "Slotback": 4,
    "Keeper": 3, "Offensive Line": 8, "Defensive Line": 7
}

ARCHETYPES_BY_POS = {
    "Zeroback": ["distributor_zb", "dual_threat_zb", "kicking_zb", "running_zb"],
    "Viper": ["receiving_viper", "power_viper", "hybrid_viper", "decoy_viper"],
    "Halfback": ["power_flanker", "speed_flanker", "elusive_flanker", "reliable_flanker"],
    "Wingback": ["speed_flanker", "reliable_flanker", "elusive_flanker", "power_flanker"],
    "Slotback": ["speed_flanker", "elusive_flanker", "reliable_flanker", "power_flanker"],
    "Keeper": ["tackle_keeper", "return_keeper", "sure_hands_keeper"],
    "Offensive Line": ["none"],
    "Defensive Line": ["none"],
}

YEARS = ["Freshman", "Sophomore", "Junior", "Senior"]
DEVELOPMENTS = ["normal", "quick", "slow", "late_bloomer"]
DEV_WEIGHTS = [50, 25, 15, 10]

FIRST_NAMES = [
    "Aaliyah", "Abigail", "Ada", "Adelaide", "Adriana", "Aisha", "Alejandra", "Alexandra",
    "Amara", "Amelia", "Ana", "Angela", "Aniya", "Anna", "Aria", "Ariana", "Aurora",
    "Ava", "Bailey", "Beatrice", "Bianca", "Blair", "Briana", "Brianna", "Bridget",
    "Brooke", "Callie", "Cameron", "Carmen", "Caroline", "Cassidy", "Catherine",
    "Celeste", "Charlotte", "Chloe", "Claire", "Clara", "Danielle", "Daphne", "Darcy",
    "Delaney", "Diana", "Elena", "Eliana", "Elise", "Elizabeth", "Ella", "Emily",
    "Emma", "Esmeralda", "Eva", "Evelyn", "Faith", "Fatima", "Fiona", "Gabriella",
    "Gemma", "Genesis", "Gianna", "Grace", "Hailey", "Hannah", "Harper", "Hayden",
    "Helena", "Imani", "Iris", "Isabel", "Isabella", "Ivy", "Jade", "Jasmine",
    "Jenna", "Jessica", "Jordan", "Josephine", "Julia", "Juliana", "Kai", "Kaia",
    "Kamila", "Kara", "Katherine", "Kayla", "Keiko", "Kendall", "Kennedy", "Kira",
    "Lana", "Laura", "Layla", "Leah", "Lena", "Lillian", "Lily", "Lina", "London",
    "Lucia", "Luna", "Lydia", "Mackenzie", "Maddison", "Madison", "Maeve", "Maia",
    "Malia", "Mara", "Mariana", "Marina", "Maya", "Megan", "Melody", "Mia",
    "Michelle", "Mikaela", "Mila", "Miranda", "Molly", "Monica", "Morgan", "Nadia",
    "Naomi", "Natalie", "Natasha", "Nia", "Nicole", "Nina", "Nora", "Olivia",
    "Paige", "Paloma", "Patricia", "Penelope", "Piper", "Quinn", "Rachel", "Reagan",
    "Rebecca", "Reese", "Riley", "Rosa", "Rosalie", "Ruby", "Sabrina", "Sage",
    "Samantha", "Sara", "Savannah", "Scarlett", "Selena", "Serena", "Sienna",
    "Sierra", "Sofia", "Sophia", "Stella", "Sydney", "Talia", "Tara", "Taylor",
    "Valentina", "Valeria", "Vanessa", "Victoria", "Violet", "Vivian", "Willow",
    "Yasmin", "Zara", "Zoey", "Zuri"
]

LAST_NAMES = [
    "Adams", "Ali", "Allen", "Anderson", "Baker", "Barnes", "Bell", "Bennett",
    "Black", "Brown", "Burns", "Campbell", "Carter", "Chang", "Chen", "Clark",
    "Cohen", "Cole", "Collins", "Cooper", "Cruz", "Daniels", "Davis", "Diaz",
    "Dixon", "Dunn", "Edwards", "Ellis", "Evans", "Fisher", "Flores", "Ford",
    "Foster", "Fox", "Freeman", "Garcia", "Gomez", "Gonzalez", "Graham", "Grant",
    "Green", "Griffin", "Gutierrez", "Hall", "Hamilton", "Hansen", "Harris",
    "Hart", "Hayes", "Henderson", "Hernandez", "Hill", "Howard", "Hughes",
    "Jackson", "James", "Jenkins", "Jensen", "Johnson", "Jones", "Jordan",
    "Kelly", "Kennedy", "Kim", "King", "Knight", "Kumar", "Larson", "Lee",
    "Lewis", "Li", "Lopez", "Martin", "Martinez", "Mason", "McCarthy", "Meyer",
    "Miller", "Mitchell", "Moore", "Morgan", "Morris", "Murphy", "Murray",
    "Nelson", "Nguyen", "O'Brien", "Olsen", "Ortiz", "Park", "Parker", "Patel",
    "Patterson", "Perez", "Perry", "Peterson", "Phillips", "Powell", "Price",
    "Quinn", "Ramirez", "Reed", "Reyes", "Reynolds", "Richardson", "Rivera",
    "Roberts", "Robinson", "Rodriguez", "Rogers", "Ross", "Russell", "Ryan",
    "Sanchez", "Sanders", "Santos", "Schmidt", "Scott", "Shah", "Shaw",
    "Silva", "Simmons", "Singh", "Smith", "Spencer", "Stewart", "Sullivan",
    "Taylor", "Thomas", "Thompson", "Torres", "Turner", "Walker", "Walsh",
    "Wang", "Ward", "Washington", "Watson", "Webb", "White", "Williams",
    "Wilson", "Wood", "Wright", "Wu", "Yang", "Young", "Zhang"
]

CITIES_BY_REGION = {
    "northeast": [
        ("Boston", "MA"), ("New York", "NY"), ("Philadelphia", "PA"), ("Hartford", "CT"),
        ("Providence", "RI"), ("Worcester", "MA"), ("Springfield", "MA"), ("Newark", "NJ"),
        ("Trenton", "NJ"), ("Albany", "NY"), ("Buffalo", "NY"), ("Rochester", "NY"),
        ("Pittsburgh", "PA"), ("Burlington", "VT"), ("Portland", "ME"),
    ],
    "mid_atlantic": [
        ("Baltimore", "MD"), ("Washington", "DC"), ("Richmond", "VA"), ("Norfolk", "VA"),
        ("Wilmington", "DE"), ("Harrisburg", "PA"), ("Annapolis", "MD"),
    ],
    "south": [
        ("Atlanta", "GA"), ("Charlotte", "NC"), ("Raleigh", "NC"), ("Nashville", "TN"),
        ("Charleston", "SC"), ("Savannah", "GA"), ("Jacksonville", "FL"), ("Tampa", "FL"),
        ("Miami", "FL"), ("Birmingham", "AL"), ("Memphis", "TN"), ("Louisville", "KY"),
    ],
    "midwest": [
        ("Chicago", "IL"), ("Detroit", "MI"), ("Columbus", "OH"), ("Indianapolis", "IN"),
        ("Milwaukee", "WI"), ("Minneapolis", "MN"), ("St. Louis", "MO"), ("Cleveland", "OH"),
        ("Cincinnati", "OH"), ("Kansas City", "MO"), ("Omaha", "NE"),
    ],
    "texas_southwest": [
        ("Houston", "TX"), ("Dallas", "TX"), ("San Antonio", "TX"), ("Austin", "TX"),
        ("Phoenix", "AZ"), ("Tucson", "AZ"), ("Albuquerque", "NM"), ("El Paso", "TX"),
        ("Denver", "CO"), ("Las Vegas", "NV"),
    ],
    "west_coast": [
        ("Los Angeles", "CA"), ("San Francisco", "CA"), ("San Diego", "CA"),
        ("Seattle", "WA"), ("Portland", "OR"), ("Sacramento", "CA"), ("Oakland", "CA"),
        ("Fresno", "CA"), ("Santa Cruz", "CA"), ("Irvine", "CA"),
    ],
    "canadian_french": [
        ("Montreal", "QC"), ("Quebec City", "QC"), ("Ottawa", "ON"),
    ],
    "canadian_english": [
        ("Toronto", "ON"), ("Vancouver", "BC"), ("Calgary", "AB"),
    ],
    "caribbean": [
        ("Kingston", "JAM"), ("Port of Spain", "TTO"), ("Nassau", "BHS"),
    ],
    "australian": [
        ("Sydney", "NSW"), ("Melbourne", "VIC"), ("Brisbane", "QLD"),
    ],
    "african": [
        ("Lagos", "NGA"), ("Accra", "GHA"), ("Nairobi", "KEN"),
    ],
    "european": [
        ("London", "ENG"), ("Paris", "FRA"), ("Berlin", "DEU"),
    ],
}

REGION_WEIGHTS = {
    "northeast": 0.30, "mid_atlantic": 0.10, "south": 0.15, "midwest": 0.15,
    "texas_southwest": 0.10, "west_coast": 0.10,
    "canadian_french": 0.02, "canadian_english": 0.03,
    "caribbean": 0.02, "australian": 0.01, "african": 0.01, "european": 0.01,
}

NATIONALITIES = {
    "northeast": "American", "mid_atlantic": "American", "south": "American",
    "midwest": "American", "texas_southwest": "American", "west_coast": "American",
    "canadian_french": "Canadian", "canadian_english": "Canadian",
    "caribbean": "Caribbean", "australian": "Australian",
    "african": "African", "european": "European",
}

COUNTRIES = {
    "northeast": "USA", "mid_atlantic": "USA", "south": "USA",
    "midwest": "USA", "texas_southwest": "USA", "west_coast": "USA",
    "canadian_french": "Canada", "canadian_english": "Canada",
    "caribbean": "Jamaica", "australian": "Australia",
    "african": "Nigeria", "european": "United Kingdom",
}

COACH_FIRST_NAMES = [
    "Amanda", "Andrea", "Angela", "Barbara", "Beth", "Carol", "Catherine",
    "Christine", "Cynthia", "Debra", "Diana", "Donna", "Elizabeth", "Emily",
    "Helen", "Jennifer", "Jessica", "Karen", "Katherine", "Kelly", "Kimberly",
    "Laura", "Linda", "Lisa", "Margaret", "Maria", "Martha", "Mary",
    "Michelle", "Nancy", "Patricia", "Rachel", "Rebecca", "Sandra", "Sarah",
    "Sharon", "Stephanie", "Susan", "Teresa", "Victoria",
    "Andrew", "Brian", "Charles", "Christopher", "Daniel", "David", "Edward",
    "Eric", "Frank", "George", "James", "Jason", "Jeffrey", "John", "Joseph",
    "Kevin", "Mark", "Matthew", "Michael", "Patrick", "Paul", "Peter",
    "Richard", "Robert", "Scott", "Steven", "Thomas", "Timothy", "Travis", "William"
]

COACH_LAST_NAMES = [
    "Anderson", "Baker", "Barnes", "Campbell", "Carter", "Chen", "Clark", "Collins",
    "Cooper", "Davis", "Edwards", "Evans", "Fisher", "Foster", "Garcia", "Graham",
    "Green", "Hall", "Harris", "Henderson", "Hill", "Howard", "Hughes", "Jackson",
    "Johnson", "Jones", "Kelly", "Kim", "King", "Lee", "Lewis", "Martin", "Martinez",
    "Miller", "Mitchell", "Moore", "Morgan", "Murphy", "Nelson", "O'Brien", "Parker",
    "Patterson", "Perez", "Phillips", "Powell", "Price", "Reed", "Reynolds",
    "Richardson", "Roberts", "Robinson", "Rogers", "Russell", "Ryan", "Sanders",
    "Scott", "Shaw", "Smith", "Spencer", "Stewart", "Sullivan", "Taylor", "Thomas",
    "Thompson", "Turner", "Walker", "Walsh", "Ward", "Watson", "White", "Williams",
    "Wilson", "Wright", "Young"
]

STYLES = ["aggressive", "balanced", "conservative"]
PHILOSOPHIES = ["ground_and_pound", "hybrid", "kick_heavy", "lateral_heavy"]
TEMPOS = ["fast", "slow", "variable"]

COACHING_STYLES = ["adaptive", "innovative", "disciplined", "aggressive"]
COACHING_PHILOSOPHIES = [
    "Balanced approach adapting to opponent",
    "Aggressive attacking philosophy",
    "Ground-based power running system",
    "Lateral-heavy spread offense",
    "Field position battle with strategic kicking",
    "Up-tempo chaos with creative schemes",
    "Disciplined defensive identity",
]
COACHING_BACKGROUNDS = [
    "Long-time coordinator stepping into head role",
    "Experienced coach hired from rival program",
    "Former player turned successful coach",
    "Rising star from assistant coaching ranks",
    "Defensive specialist building a program",
    "Offensive innovator with unique system",
    "Well-respected veteran with championship pedigree",
]

CONFERENCES_D3 = [
    "Independence Conference",
    "Founders League",
    "Liberty Athletic",
    "Heritage Conference",
    "Atlantic Collegiate",
    "Pioneer League",
    "Centennial Conference",
    "Empire Athletic",
]


def get_local_region(state):
    ne = ["MA", "CT", "RI", "NH", "VT", "ME", "NY", "NJ"]
    ma = ["PA", "MD", "DE", "DC", "VA", "WV"]
    south = ["GA", "NC", "SC", "FL", "TN", "AL", "KY", "LA", "MS", "AR"]
    mw = ["IL", "OH", "MI", "IN", "WI", "MN", "MO", "IA", "NE", "KS", "ND", "SD"]
    tx = ["TX", "AZ", "NM", "CO", "NV", "UT", "OK"]
    wc = ["CA", "WA", "OR", "HI"]
    if state in ne: return "northeast"
    if state in ma: return "mid_atlantic"
    if state in south: return "south"
    if state in mw: return "midwest"
    if state in tx: return "texas_southwest"
    if state in wc: return "west_coast"
    if state == "BC": return "canadian_english"
    return "northeast"


def make_pipeline(state):
    local = get_local_region(state)
    regions = list(REGION_WEIGHTS.keys())
    pipeline = {}
    remaining = 1.0
    local_weight = random.uniform(0.35, 0.55)
    pipeline[local] = round(local_weight, 2)
    remaining -= local_weight
    other_regions = [r for r in regions if r != local and r in ["northeast", "mid_atlantic", "south", "midwest", "texas_southwest", "west_coast"]]
    random.shuffle(other_regions)
    for r in other_regions[:4]:
        w = round(random.uniform(0.03, remaining * 0.4), 2)
        pipeline[r] = w
        remaining -= w
    intl = [r for r in regions if r not in pipeline]
    random.shuffle(intl)
    for r in intl[:2]:
        w = round(remaining / 2, 3)
        pipeline[r] = w
    return pipeline


def gen_player(num, used_names, local_region, team_tier):
    while True:
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        if name not in used_names:
            used_names.add(name)
            break

    pos_pool = []
    for p, w in POSITION_WEIGHTS.items():
        pos_pool.extend([p] * w)
    position = random.choice(pos_pool)

    archs = ARCHETYPES_BY_POS[position]
    archetype = random.choice(archs)

    year = random.choice(YEARS)

    regions = list(REGION_WEIGHTS.keys())
    weights = list(REGION_WEIGHTS.values())
    weights[regions.index(local_region)] += 0.25
    total = sum(weights)
    weights = [w / total for w in weights]
    region = random.choices(regions, weights=weights, k=1)[0]

    city_state = random.choice(CITIES_BY_REGION[region])
    country = COUNTRIES[region]
    nationality = NATIONALITIES[region]

    base = team_tier
    def stat(low_mod=0, high_mod=0):
        return max(50, min(100, base + random.randint(-15 + low_mod, 15 + high_mod)))

    is_lineman = "Line" in position or "Wedge" in position
    if is_lineman:
        height_inches = random.randint(70, 74)
        weight_lbs = random.randint(185, 210)
    elif "Back" in position and "Zero" not in position:
        height_inches = random.randint(66, 72)
        weight_lbs = random.randint(155, 185)
    else:
        height_inches = random.randint(66, 73)
        weight_lbs = random.randint(160, 195)

    h_ft = height_inches // 12
    h_in = height_inches % 12

    stats = {
        "speed": stat(-3 if is_lineman else 0, 5 if not is_lineman else 0),
        "stamina": stat(),
        "kicking": stat(-5 if is_lineman else 0, 5 if "Zero" in position else 0),
        "lateral_skill": stat(0, 5 if "Viper" in position or "Shift" in position else 0),
        "tackling": stat(5 if is_lineman else 0, 0),
        "agility": stat(-5 if is_lineman else 0, 5 if "Shift" in position else 0),
        "power": stat(5 if is_lineman else 0, 0),
        "awareness": stat(),
        "hands": stat(0, 5 if "Wing" in position else 0),
        "kick_power": stat(-5, 5 if "Zero" in position else 0),
        "kick_accuracy": stat(-5, 5 if "Zero" in position else 0),
    }

    potential = random.choices([1, 2, 3, 4, 5], weights=[5, 30, 40, 20, 5], k=1)[0]
    development = random.choices(DEVELOPMENTS, weights=DEV_WEIGHTS, k=1)[0]

    hs_name = f"{city_state[0]} {'High School' if random.random() < 0.6 else random.choice(['Academy', 'Prep', 'Central High', 'North High', 'South High', 'West High', 'East High'])}"

    return {
        "number": num,
        "name": name,
        "position": position,
        "height": f"{h_ft}-{h_in}",
        "weight": weight_lbs,
        "year": year,
        "hometown": {
            "city": city_state[0],
            "state": city_state[1],
            "country": country,
            "region": region,
        },
        "high_school": hs_name,
        "nationality": nationality,
        "archetype": archetype,
        "potential": potential,
        "development": development,
        "stats": stats,
    }


def gen_team(school):
    sid = school["id"]
    local_region = get_local_region(school["state"])
    tier = school.get("tier", 72)

    used_names = set()
    roster_size = random.randint(34, 38)
    numbers = random.sample(range(1, 100), roster_size)
    numbers.sort()
    players = [gen_player(n, used_names, local_region, tier) for n in numbers]

    speeds = [p["stats"]["speed"] for p in players]
    weights = [p["weight"] for p in players]
    staminas = [p["stats"]["stamina"] for p in players]

    coach_first = random.choice(COACH_FIRST_NAMES)
    coach_last = random.choice(COACH_LAST_NAMES)
    coach_gender = "female" if coach_first in [
        "Amanda", "Andrea", "Angela", "Barbara", "Beth", "Carol", "Catherine",
        "Christine", "Cynthia", "Debra", "Diana", "Donna", "Elizabeth", "Emily",
        "Helen", "Jennifer", "Jessica", "Karen", "Katherine", "Kelly", "Kimberly",
        "Laura", "Linda", "Lisa", "Margaret", "Maria", "Martha", "Mary",
        "Michelle", "Nancy", "Patricia", "Rachel", "Rebecca", "Sandra", "Sarah",
        "Sharon", "Stephanie", "Susan", "Teresa", "Victoria",
    ] else "male"

    team = {
        "team_info": {
            "school_id": sid,
            "school_name": school["name"],
            "abbreviation": school["abbrev"],
            "mascot": school["mascot"],
            "conference": school["conference"],
            "city": school["city"],
            "state": school["state"],
            "colors": school["colors"],
        },
        "identity": {
            "style": random.choice(STYLES),
            "philosophy": random.choice(PHILOSOPHIES),
            "tempo": random.choice(TEMPOS),
            "two_way_emphasis": random.choice(["high", "medium", "low"]),
        },
        "recruiting_pipeline": make_pipeline(school["state"]),
        "roster": {
            "size": roster_size,
            "players": players,
        },
        "team_stats": {
            "avg_speed": round(sum(speeds) / len(speeds)),
            "avg_weight": round(sum(weights) / len(weights)),
            "avg_stamina": round(sum(staminas) / len(staminas)),
            "kicking_strength": round(sum(p["stats"]["kicking"] for p in players) / len(players)),
            "lateral_proficiency": round(sum(p["stats"]["lateral_skill"] for p in players) / len(players)),
            "defensive_strength": round(sum(p["stats"]["tackling"] for p in players) / len(players)),
        },
        "coaching": {
            "head_coach": f"{coach_first} {coach_last}",
            "head_coach_gender": coach_gender,
            "philosophy": random.choice(COACHING_PHILOSOPHIES),
            "coaching_style": random.choice(COACHING_STYLES),
            "experience": f"{random.randint(2, 25)} years",
            "background": random.choice(COACHING_BACKGROUNDS),
        },
    }
    return team


NEW_SCHOOLS = [
    # ══════════════════════════════════════════════════════════════════
    # BIG TEN (12 new teams — renamed from Giant 14)
    # ══════════════════════════════════════════════════════════════════
    {"id": "illinois", "name": "University of Illinois", "abbrev": "ILL", "mascot": "Fighting Illini", "city": "Champaign", "state": "IL", "colors": ["Orange", "Blue"], "conference": "Big Ten", "tier": 85},
    {"id": "indiana", "name": "Indiana University", "abbrev": "IND", "mascot": "Hoosiers", "city": "Bloomington", "state": "IN", "colors": ["Crimson", "Cream"], "conference": "Big Ten", "tier": 83},
    {"id": "iowa", "name": "University of Iowa", "abbrev": "IOWA", "mascot": "Hawkeyes", "city": "Iowa City", "state": "IA", "colors": ["Black", "Gold"], "conference": "Big Ten", "tier": 86},
    {"id": "michigan", "name": "University of Michigan", "abbrev": "MICH", "mascot": "Wolverines", "city": "Ann Arbor", "state": "MI", "colors": ["Maize", "Blue"], "conference": "Big Ten", "tier": 93},
    {"id": "michigan_state", "name": "Michigan State University", "abbrev": "MSU", "mascot": "Spartans", "city": "East Lansing", "state": "MI", "colors": ["Green", "White"], "conference": "Big Ten", "tier": 87},
    {"id": "nebraska", "name": "University of Nebraska", "abbrev": "NEB", "mascot": "Cornhuskers", "city": "Lincoln", "state": "NE", "colors": ["Scarlet", "Cream"], "conference": "Big Ten", "tier": 88},
    {"id": "northwestern", "name": "Northwestern University", "abbrev": "NW", "mascot": "Wildcats", "city": "Evanston", "state": "IL", "colors": ["Purple", "White"], "conference": "Big Ten", "tier": 82},
    {"id": "notre_dame", "name": "University of Notre Dame", "abbrev": "ND", "mascot": "Fighting Irish", "city": "Notre Dame", "state": "IN", "colors": ["Navy", "Gold"], "conference": "Big Ten", "tier": 94},
    {"id": "ohio_state", "name": "Ohio State University", "abbrev": "OSU", "mascot": "Buckeyes", "city": "Columbus", "state": "OH", "colors": ["Scarlet", "Gray"], "conference": "Big Ten", "tier": 95},
    {"id": "purdue", "name": "Purdue University", "abbrev": "PUR", "mascot": "Boilermakers", "city": "West Lafayette", "state": "IN", "colors": ["Old Gold", "Black"], "conference": "Big Ten", "tier": 84},
    {"id": "wisconsin", "name": "University of Wisconsin", "abbrev": "WIS", "mascot": "Badgers", "city": "Madison", "state": "WI", "colors": ["Cardinal", "White"], "conference": "Big Ten", "tier": 88},
    # ══════════════════════════════════════════════════════════════════
    # ACC (15 new teams — renamed from Potomac Athletic)
    # ══════════════════════════════════════════════════════════════════
    {"id": "boston_college", "name": "Boston College", "abbrev": "BC", "mascot": "Eagles", "city": "Chestnut Hill", "state": "MA", "colors": ["Maroon", "Gold"], "conference": "ACC", "tier": 83},
    {"id": "clemson", "name": "Clemson University", "abbrev": "CLEM", "mascot": "Tigers", "city": "Clemson", "state": "SC", "colors": ["Orange", "Purple"], "conference": "ACC", "tier": 92},
    {"id": "duke", "name": "Duke University", "abbrev": "DUKE", "mascot": "Blue Devils", "city": "Durham", "state": "NC", "colors": ["Royal Blue", "White"], "conference": "ACC", "tier": 82},
    {"id": "florida_state", "name": "Florida State University", "abbrev": "FSU", "mascot": "Seminoles", "city": "Tallahassee", "state": "FL", "colors": ["Garnet", "Gold"], "conference": "ACC", "tier": 90},
    {"id": "georgia_tech", "name": "Georgia Tech", "abbrev": "GT", "mascot": "Yellow Jackets", "city": "Atlanta", "state": "GA", "colors": ["Old Gold", "White"], "conference": "ACC", "tier": 84},
    {"id": "louisville", "name": "University of Louisville", "abbrev": "LOU", "mascot": "Cardinals", "city": "Louisville", "state": "KY", "colors": ["Cardinal", "Black"], "conference": "ACC", "tier": 85},
    {"id": "maryland", "name": "University of Maryland", "abbrev": "UMD", "mascot": "Terrapins", "city": "College Park", "state": "MD", "colors": ["Red", "White", "Black", "Gold"], "conference": "ACC", "tier": 84},
    {"id": "miami", "name": "University of Miami", "abbrev": "MIA", "mascot": "Hurricanes", "city": "Coral Gables", "state": "FL", "colors": ["Orange", "Green", "White"], "conference": "ACC", "tier": 90},
    {"id": "nc_state", "name": "North Carolina State University", "abbrev": "NCST", "mascot": "Wolfpack", "city": "Raleigh", "state": "NC", "colors": ["Red", "White"], "conference": "ACC", "tier": 84},
    {"id": "north_carolina", "name": "University of North Carolina", "abbrev": "UNC", "mascot": "Tar Heels", "city": "Chapel Hill", "state": "NC", "colors": ["Carolina Blue", "White"], "conference": "ACC", "tier": 86},
    {"id": "pitt", "name": "University of Pittsburgh", "abbrev": "PITT", "mascot": "Panthers", "city": "Pittsburgh", "state": "PA", "colors": ["Royal Blue", "Gold"], "conference": "ACC", "tier": 83},
    {"id": "syracuse", "name": "Syracuse University", "abbrev": "SYR", "mascot": "Orange", "city": "Syracuse", "state": "NY", "colors": ["Orange", "Blue"], "conference": "ACC", "tier": 83},
    {"id": "virginia", "name": "University of Virginia", "abbrev": "UVA", "mascot": "Cavaliers", "city": "Charlottesville", "state": "VA", "colors": ["Orange", "Navy"], "conference": "ACC", "tier": 84},
    {"id": "virginia_tech", "name": "Virginia Tech", "abbrev": "VT", "mascot": "Hokies", "city": "Blacksburg", "state": "VA", "colors": ["Maroon", "Orange"], "conference": "ACC", "tier": 86},
    {"id": "wake_forest", "name": "Wake Forest University", "abbrev": "WAKE", "mascot": "Demon Deacons", "city": "Winston-Salem", "state": "NC", "colors": ["Old Gold", "Black"], "conference": "ACC", "tier": 80},
    # ══════════════════════════════════════════════════════════════════
    # SEC (16 new teams — renamed from Southern Sun)
    # ══════════════════════════════════════════════════════════════════
    {"id": "alabama", "name": "University of Alabama", "abbrev": "BAMA", "mascot": "Crimson Tide", "city": "Tuscaloosa", "state": "AL", "colors": ["Crimson", "White"], "conference": "SEC", "tier": 95},
    {"id": "arkansas", "name": "University of Arkansas", "abbrev": "ARK", "mascot": "Razorbacks", "city": "Fayetteville", "state": "AR", "colors": ["Cardinal", "White"], "conference": "SEC", "tier": 85},
    {"id": "auburn", "name": "Auburn University", "abbrev": "AUB", "mascot": "Tigers", "city": "Auburn", "state": "AL", "colors": ["Burnt Orange", "Navy"], "conference": "SEC", "tier": 89},
    {"id": "florida", "name": "University of Florida", "abbrev": "UF", "mascot": "Gators", "city": "Gainesville", "state": "FL", "colors": ["Orange", "Blue"], "conference": "SEC", "tier": 91},
    {"id": "georgia", "name": "University of Georgia", "abbrev": "UGA", "mascot": "Bulldogs", "city": "Athens", "state": "GA", "colors": ["Red", "Black"], "conference": "SEC", "tier": 94},
    {"id": "kentucky", "name": "University of Kentucky", "abbrev": "UK", "mascot": "Wildcats", "city": "Lexington", "state": "KY", "colors": ["Blue", "White"], "conference": "SEC", "tier": 83},
    {"id": "lsu", "name": "Louisiana State University", "abbrev": "LSU", "mascot": "Tigers", "city": "Baton Rouge", "state": "LA", "colors": ["Purple", "Gold"], "conference": "SEC", "tier": 92},
    {"id": "mississippi_state", "name": "Mississippi State University", "abbrev": "MSST", "mascot": "Bulldogs", "city": "Starkville", "state": "MS", "colors": ["Maroon", "White"], "conference": "SEC", "tier": 83},
    {"id": "missouri", "name": "University of Missouri", "abbrev": "MIZ", "mascot": "Tigers", "city": "Columbia", "state": "MO", "colors": ["Black", "Gold"], "conference": "SEC", "tier": 84},
    {"id": "oklahoma", "name": "University of Oklahoma", "abbrev": "OU", "mascot": "Sooners", "city": "Norman", "state": "OK", "colors": ["Crimson", "Cream"], "conference": "SEC", "tier": 93},
    {"id": "ole_miss", "name": "University of Mississippi", "abbrev": "MISS", "mascot": "Rebels", "city": "Oxford", "state": "MS", "colors": ["Red", "Blue"], "conference": "SEC", "tier": 85},
    {"id": "south_carolina", "name": "University of South Carolina", "abbrev": "SC", "mascot": "Gamecocks", "city": "Columbia", "state": "SC", "colors": ["Garnet", "Black"], "conference": "SEC", "tier": 84},
    {"id": "tennessee", "name": "University of Tennessee", "abbrev": "TENN", "mascot": "Volunteers", "city": "Knoxville", "state": "TN", "colors": ["Orange", "White"], "conference": "SEC", "tier": 90},
    {"id": "texas", "name": "University of Texas", "abbrev": "TEX", "mascot": "Longhorns", "city": "Austin", "state": "TX", "colors": ["Burnt Orange", "White"], "conference": "SEC", "tier": 94},
    {"id": "texas_am", "name": "Texas A&M University", "abbrev": "TAMU", "mascot": "Aggies", "city": "College Station", "state": "TX", "colors": ["Maroon", "White"], "conference": "SEC", "tier": 88},
    {"id": "vanderbilt", "name": "Vanderbilt University", "abbrev": "VAN", "mascot": "Commodores", "city": "Nashville", "state": "TN", "colors": ["Black", "Gold"], "conference": "SEC", "tier": 76},
    # ══════════════════════════════════════════════════════════════════
    # MOONSHINE LEAGUE / Big 12 (16 new teams — keeps Moonshine name)
    # ══════════════════════════════════════════════════════════════════
    {"id": "arizona", "name": "University of Arizona", "abbrev": "ARIZ", "mascot": "Wildcats", "city": "Tucson", "state": "AZ", "colors": ["Cardinal", "Navy"], "conference": "Moonshine League", "tier": 85},
    {"id": "arizona_state", "name": "Arizona State University", "abbrev": "ASU", "mascot": "Sun Devils", "city": "Tempe", "state": "AZ", "colors": ["Maroon", "Gold"], "conference": "Moonshine League", "tier": 86},
    {"id": "baylor", "name": "Baylor University", "abbrev": "BAY", "mascot": "Bears", "city": "Waco", "state": "TX", "colors": ["Green", "Gold"], "conference": "Moonshine League", "tier": 85},
    {"id": "byu", "name": "Brigham Young University", "abbrev": "BYU", "mascot": "Cougars", "city": "Provo", "state": "UT", "colors": ["Royal Blue", "White"], "conference": "Moonshine League", "tier": 84},
    {"id": "cincinnati", "name": "University of Cincinnati", "abbrev": "CIN", "mascot": "Bearcats", "city": "Cincinnati", "state": "OH", "colors": ["Red", "Black"], "conference": "Moonshine League", "tier": 83},
    {"id": "colorado", "name": "University of Colorado", "abbrev": "CU", "mascot": "Buffaloes", "city": "Boulder", "state": "CO", "colors": ["Silver", "Gold", "Black"], "conference": "Moonshine League", "tier": 84},
    {"id": "houston", "name": "University of Houston", "abbrev": "UH", "mascot": "Cougars", "city": "Houston", "state": "TX", "colors": ["Scarlet", "White"], "conference": "Moonshine League", "tier": 83},
    {"id": "iowa_state", "name": "Iowa State University", "abbrev": "ISU", "mascot": "Cyclones", "city": "Ames", "state": "IA", "colors": ["Cardinal", "Gold"], "conference": "Moonshine League", "tier": 84},
    {"id": "kansas", "name": "University of Kansas", "abbrev": "KU", "mascot": "Jayhawks", "city": "Lawrence", "state": "KS", "colors": ["Crimson", "Blue"], "conference": "Moonshine League", "tier": 82},
    {"id": "kansas_state", "name": "Kansas State University", "abbrev": "KST", "mascot": "Wildcats", "city": "Manhattan", "state": "KS", "colors": ["Purple", "White"], "conference": "Moonshine League", "tier": 85},
    {"id": "oklahoma_state", "name": "Oklahoma State University", "abbrev": "OKST", "mascot": "Cowboys", "city": "Stillwater", "state": "OK", "colors": ["Orange", "Black"], "conference": "Moonshine League", "tier": 85},
    {"id": "tcu", "name": "Texas Christian University", "abbrev": "TCU", "mascot": "Horned Frogs", "city": "Fort Worth", "state": "TX", "colors": ["Purple", "White"], "conference": "Moonshine League", "tier": 85},
    {"id": "texas_tech", "name": "Texas Tech University", "abbrev": "TTU", "mascot": "Red Raiders", "city": "Lubbock", "state": "TX", "colors": ["Scarlet", "Black"], "conference": "Moonshine League", "tier": 84},
    {"id": "ucf", "name": "University of Central Florida", "abbrev": "UCF", "mascot": "Knights", "city": "Orlando", "state": "FL", "colors": ["Black", "Gold"], "conference": "Moonshine League", "tier": 83},
    {"id": "utah", "name": "University of Utah", "abbrev": "UTAH", "mascot": "Utes", "city": "Salt Lake City", "state": "UT", "colors": ["Crimson", "White"], "conference": "Moonshine League", "tier": 85},
    {"id": "west_virginia", "name": "West Virginia University", "abbrev": "WVU", "mascot": "Mountaineers", "city": "Morgantown", "state": "WV", "colors": ["Old Gold", "Blue"], "conference": "Moonshine League", "tier": 84},
    # ══════════════════════════════════════════════════════════════════
    # PAC-12 (6 new teams — new 17th conference)
    # ══════════════════════════════════════════════════════════════════
    {"id": "cal", "name": "University of California, Berkeley", "abbrev": "CAL", "mascot": "Golden Bears", "city": "Berkeley", "state": "CA", "colors": ["Blue", "Gold"], "conference": "Pac-12", "tier": 84},
    {"id": "oregon", "name": "University of Oregon", "abbrev": "ORE", "mascot": "Ducks", "city": "Eugene", "state": "OR", "colors": ["Green", "Yellow"], "conference": "Pac-12", "tier": 91},
    {"id": "stanford", "name": "Stanford University", "abbrev": "STAN", "mascot": "Cardinal", "city": "Stanford", "state": "CA", "colors": ["Cardinal", "White"], "conference": "Pac-12", "tier": 86},
    {"id": "ucla", "name": "University of California, Los Angeles", "abbrev": "UCLA", "mascot": "Bruins", "city": "Los Angeles", "state": "CA", "colors": ["True Blue", "Gold"], "conference": "Pac-12", "tier": 88},
    {"id": "usc", "name": "University of Southern California", "abbrev": "USC", "mascot": "Trojans", "city": "Los Angeles", "state": "CA", "colors": ["Cardinal", "Gold"], "conference": "Pac-12", "tier": 93},
    {"id": "washington", "name": "University of Washington", "abbrev": "UW", "mascot": "Huskies", "city": "Seattle", "state": "WA", "colors": ["Purple", "Gold"], "conference": "Pac-12", "tier": 88},
    # ══════════════════════════════════════════════════════════════════
    # SERVICE ACADEMIES (3 new)
    # ══════════════════════════════════════════════════════════════════
    {"id": "army", "name": "Army", "abbrev": "ARMY", "mascot": "Black Knights", "city": "West Point", "state": "NY", "colors": ["Black", "Gold"], "conference": "Pioneer Athletic Association", "tier": 78},
    {"id": "navy", "name": "Navy", "abbrev": "NAVY", "mascot": "Midshipmen", "city": "Annapolis", "state": "MD", "colors": ["Navy", "Gold"], "conference": "Yankee Fourteen", "tier": 78},
    {"id": "merchant_marine", "name": "Merchant Marine", "abbrev": "USMM", "mascot": "Mariners", "city": "Kings Point", "state": "NY", "colors": ["Blue", "Gray"], "conference": "Yankee Fourteen", "tier": 72},
    # ══════════════════════════════════════════════════════════════════
    # IVY LEAGUE & NESCAC (6 new)
    # ══════════════════════════════════════════════════════════════════
    {"id": "harvard", "name": "Harvard University", "abbrev": "HARV", "mascot": "Crimson", "city": "Cambridge", "state": "MA", "colors": ["Crimson", "Black", "White"], "conference": "Collegiate Commonwealth", "tier": 82},
    {"id": "yale", "name": "Yale University", "abbrev": "YALE", "mascot": "Bulldogs", "city": "New Haven", "state": "CT", "colors": ["Yale Blue", "White"], "conference": "Yankee Fourteen", "tier": 80},
    {"id": "columbia", "name": "Columbia University", "abbrev": "CLMB", "mascot": "Lions", "city": "New York", "state": "NY", "colors": ["Columbia Blue", "White"], "conference": "Galactic League", "tier": 78},
    {"id": "princeton", "name": "Princeton University", "abbrev": "PRIN", "mascot": "Tigers", "city": "Princeton", "state": "NJ", "colors": ["Orange", "Black"], "conference": "Yankee Fourteen", "tier": 80},
    {"id": "penn", "name": "University of Pennsylvania", "abbrev": "PENN", "mascot": "Quakers", "city": "Philadelphia", "state": "PA", "colors": ["Red", "Blue"], "conference": "Collegiate Commonwealth", "tier": 79},
    {"id": "middlebury", "name": "Middlebury College", "abbrev": "MIDD", "mascot": "Panthers", "city": "Middlebury", "state": "VT", "colors": ["Blue", "White"], "conference": "Northern Shield", "tier": 76},
    # ══════════════════════════════════════════════════════════════════
    # OTHER (2 new)
    # ══════════════════════════════════════════════════════════════════
    {"id": "greenville", "name": "Greenville University", "abbrev": "GRNV", "mascot": "Panthers", "city": "Greenville", "state": "IL", "colors": ["Maroon", "White"], "conference": "Prairie Athletic Union", "tier": 58},
    {"id": "smu", "name": "Southern Methodist University", "abbrev": "SMU", "mascot": "Mustangs", "city": "Dallas", "state": "TX", "colors": ["Red", "Blue"], "conference": "Border Conference", "tier": 83},
]

if __name__ == "__main__":
    random.seed(42)
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")

    skipped = []
    created = []
    for school in NEW_SCHOOLS:
        path = os.path.join(out_dir, f"{school['id']}.json")
        if os.path.exists(path):
            skipped.append(school["id"])
            continue
        team = gen_team(school)
        with open(path, "w") as f:
            json.dump(team, f, indent=2)
        created.append(school["id"])

    print(f"Created {len(created)} teams: {', '.join(created)}")
    if skipped:
        print(f"Skipped {len(skipped)} (already exist): {', '.join(skipped)}")
    print(f"Total teams in directory: {len([f for f in os.listdir(out_dir) if f.endswith('.json')])}")
