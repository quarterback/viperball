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
    ma = ["PA", "MD", "DE", "DC", "VA"]
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
    {"id": "nyu", "name": "New York University", "abbrev": "NYU", "mascot": "Violets", "city": "New York", "state": "NY", "colors": ["Purple", "White"], "conference": "Empire Athletic", "tier": 75},
    {"id": "emory", "name": "Emory University", "abbrev": "EMRY", "mascot": "Eagles", "city": "Atlanta", "state": "GA", "colors": ["Blue", "Gold"], "conference": "Heritage Conference", "tier": 74},
    {"id": "brandeis", "name": "Brandeis University", "abbrev": "BRND", "mascot": "Judges", "city": "Waltham", "state": "MA", "colors": ["Blue", "White"], "conference": "Founders League", "tier": 73},
    {"id": "vassar", "name": "Vassar College", "abbrev": "VSSR", "mascot": "Brewers", "city": "Poughkeepsie", "state": "NY", "colors": ["Burgundy", "Grey"], "conference": "Founders League", "tier": 71},
    {"id": "swarthmore", "name": "Swarthmore College", "abbrev": "SWAT", "mascot": "Garnet", "city": "Swarthmore", "state": "PA", "colors": ["Garnet", "White"], "conference": "Centennial Conference", "tier": 73},
    {"id": "haverford", "name": "Haverford College", "abbrev": "HAVR", "mascot": "Fords", "city": "Haverford", "state": "PA", "colors": ["Scarlet", "Black"], "conference": "Centennial Conference", "tier": 71},
    {"id": "babson", "name": "Babson College", "abbrev": "BABS", "mascot": "Beavers", "city": "Wellesley", "state": "MA", "colors": ["Green", "White"], "conference": "Founders League", "tier": 70},
    {"id": "claremont_mckenna", "name": "Claremont McKenna College", "abbrev": "CMC", "mascot": "Stags", "city": "Claremont", "state": "CA", "colors": ["Cardinal", "Gold"], "conference": "Pioneer League", "tier": 72},
    {"id": "hunter", "name": "Hunter College", "abbrev": "HUNT", "mascot": "Hawks", "city": "New York", "state": "NY", "colors": ["Purple", "Gold"], "conference": "Empire Athletic", "tier": 68},
    {"id": "baruch", "name": "Baruch College", "abbrev": "BARC", "mascot": "Bearcats", "city": "New York", "state": "NY", "colors": ["Blue", "White", "Black"], "conference": "Empire Athletic", "tier": 67},
    {"id": "john_jay", "name": "John Jay College", "abbrev": "JJAY", "mascot": "Bloodhounds", "city": "New York", "state": "NY", "colors": ["Blue", "Gold"], "conference": "Empire Athletic", "tier": 66},
    {"id": "suffolk", "name": "Suffolk University", "abbrev": "SFLK", "mascot": "Rams", "city": "Boston", "state": "MA", "colors": ["Blue", "Gold"], "conference": "Atlantic Collegiate", "tier": 67},
    {"id": "umass_boston", "name": "UMass Boston", "abbrev": "UMB", "mascot": "Beacons", "city": "Boston", "state": "MA", "colors": ["Blue", "White"], "conference": "Atlantic Collegiate", "tier": 68},
    {"id": "uc_santa_cruz", "name": "UC Santa Cruz", "abbrev": "UCSC", "mascot": "Banana Slugs", "city": "Santa Cruz", "state": "CA", "colors": ["Blue", "Gold"], "conference": "Pioneer League", "tier": 69},
    {"id": "ut_dallas", "name": "UT Dallas", "abbrev": "UTD", "mascot": "Comets", "city": "Richardson", "state": "TX", "colors": ["Orange", "Green", "White"], "conference": "Independence Conference", "tier": 70},
    {"id": "uchicago", "name": "University of Chicago", "abbrev": "UCHI", "mascot": "Maroons", "city": "Chicago", "state": "IL", "colors": ["Maroon", "White"], "conference": "Heritage Conference", "tier": 76},
    {"id": "uc_santa_barbara", "name": "UC Santa Barbara", "abbrev": "UCSB", "mascot": "Gauchos", "city": "Santa Barbara", "state": "CA", "colors": ["Blue", "Gold"], "conference": "Pioneer League", "tier": 74},
    {"id": "whittier", "name": "Whittier College", "abbrev": "WHIT", "mascot": "Poets", "city": "Whittier", "state": "CA", "colors": ["Purple", "Gold"], "conference": "Pioneer League", "tier": 68},
    {"id": "occidental", "name": "Occidental College", "abbrev": "OXY", "mascot": "Tigers", "city": "Los Angeles", "state": "CA", "colors": ["Orange", "Black"], "conference": "Pioneer League", "tier": 70},
    {"id": "smith", "name": "Smith College", "abbrev": "SMTH", "mascot": "Pioneers", "city": "Northampton", "state": "MA", "colors": ["Blue", "Yellow"], "conference": "Founders League", "tier": 72},
    {"id": "wellesley", "name": "Wellesley College", "abbrev": "WELL", "mascot": "Blue", "city": "Wellesley", "state": "MA", "colors": ["Blue", "White"], "conference": "Founders League", "tier": 73},
    {"id": "bryn_mawr", "name": "Bryn Mawr College", "abbrev": "BRYN", "mascot": "Owls", "city": "Bryn Mawr", "state": "PA", "colors": ["Yellow", "White"], "conference": "Centennial Conference", "tier": 71},
    {"id": "meredith", "name": "Meredith College", "abbrev": "MERD", "mascot": "Avenging Angels", "city": "Raleigh", "state": "NC", "colors": ["Maroon", "Black", "White"], "conference": "Liberty Athletic", "tier": 67},
    {"id": "mount_holyoke", "name": "Mount Holyoke College", "abbrev": "MHC", "mascot": "Lyons", "city": "South Hadley", "state": "MA", "colors": ["Blue", "White"], "conference": "Founders League", "tier": 71},
    {"id": "academy_of_art", "name": "Academy of Art University", "abbrev": "AAU", "mascot": "Urban Knights", "city": "San Francisco", "state": "CA", "colors": ["Red", "Black"], "conference": "Pioneer League", "tier": 66},
    {"id": "point_loma", "name": "Point Loma Nazarene University", "abbrev": "PLNU", "mascot": "Sea Lions", "city": "San Diego", "state": "CA", "colors": ["Green", "Gold"], "conference": "Pioneer League", "tier": 69},
    {"id": "biola", "name": "Biola University", "abbrev": "BIOL", "mascot": "Eagles", "city": "La Mirada", "state": "CA", "colors": ["Red", "White"], "conference": "Pioneer League", "tier": 70},
    {"id": "ubc", "name": "University of British Columbia", "abbrev": "UBC", "mascot": "Thunderbirds", "city": "Vancouver", "state": "BC", "colors": ["Blue", "Gold"], "conference": "Independence Conference", "tier": 75},
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
