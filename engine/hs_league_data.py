"""
High School League Data — Real schools organized by state, conference, and region.

Hierarchy: Conference → Division (State) → Region → National
California is its own region.
"""

# ──────────────────────────────────────────────
# REGIONS
# ──────────────────────────────────────────────

REGIONS = {
    "Northeast": ["MA", "CT", "NY", "NJ"],
    "Mid-Atlantic": ["PA", "MD", "VA"],
    "Southeast": ["GA", "FL", "NC", "TN"],
    "Great Lakes": ["OH", "IL", "MI", "MN"],
    "Plains": ["TX", "OK", "KS"],
    "Mountain": ["CO", "WY", "UT", "MT"],
    "Pacific Northwest": ["OR", "WA"],
    "California": ["CA"],
}

# Reverse lookup: state → region
STATE_TO_REGION = {}
for region, states in REGIONS.items():
    for st in states:
        STATE_TO_REGION[st] = region

# ──────────────────────────────────────────────
# STATES / DIVISIONS — each state has conferences with real schools
# ──────────────────────────────────────────────

STATES = {
    # ═══════════════ NORTHEAST ═══════════════
    "MA": {
        "name": "Massachusetts",
        "conferences": {
            "Bay State Conference": [
                "Boston Latin", "Brookline High", "Newton North", "Belmont High",
                "Lexington High", "Winchester High", "Wellesley High", "Needham High",
                "Natick High", "Andover High",
            ],
            "New England Prep": [
                "Phillips Academy", "Deerfield Academy", "Milton Academy",
                "Noble & Greenough", "Thayer Academy", "BB&N",
                "Middlesex School", "Concord Academy", "Dana Hall",
                "Northfield Mount Hermon",
            ],
            "Pioneer Valley": [
                "Groton School", "St. Mark's School", "Worcester Academy",
                "Tabor Academy", "Springfield Central", "Longmeadow High",
                "Amherst Regional", "Northampton High",
            ],
        },
    },
    "CT": {
        "name": "Connecticut",
        "conferences": {
            "Fairfield County League": [
                "Greenwich High", "Staples High", "New Canaan High",
                "Darien High", "Ridgefield High", "Weston High",
                "Wilton High", "Trumbull High",
            ],
            "Hartford Metro": [
                "Glastonbury High", "Hall High", "Conard High",
                "Simsbury High", "Avon High", "Farmington High",
                "Southington High", "Cheshire Academy",
            ],
            "CT Prep League": [
                "Choate Rosemary Hall", "Hotchkiss School", "Kent School",
                "Loomis Chaffee", "Westminster School", "Taft School",
                "Pomfret School", "Suffield Academy", "Miss Porter's School",
            ],
        },
    },
    "NY": {
        "name": "New York",
        "conferences": {
            "NYC Metro": [
                "Stuyvesant", "Bronx Science", "Brooklyn Tech",
                "Dalton School", "Horace Mann", "Trinity School",
                "Fieldston", "Poly Prep",
            ],
            "Westchester-Hudson": [
                "Riverdale Country", "Hackley School", "Rye High",
                "Mamaroneck High", "Scarsdale High", "Byram Hills",
                "Bronxville High", "Hastings High",
            ],
            "Upstate Elite": [
                "Emma Willard", "Albany Academy", "Nichols School",
                "Canisius High", "Aquinas Institute", "McQuaid Jesuit",
                "Pittsford Mendon", "Fairport High",
            ],
        },
    },
    "NJ": {
        "name": "New Jersey",
        "conferences": {
            "North Jersey Conference": [
                "Bergen Catholic", "Don Bosco Prep", "Delbarton School",
                "Seton Hall Prep", "St. Peter's Prep", "Montclair High",
                "Ridgewood High", "Westfield High",
            ],
            "Central Jersey League": [
                "Pingry School", "Lawrenceville School", "Hun School",
                "Blair Academy", "Peddie School", "Gill St. Bernard's",
                "Plainfield High School", "Phillipsburg High School",
            ],
            "Shore Conference": [
                "Red Bank Catholic", "Rumson-Fair Haven",
                "Bridgewater-Raritan", "Hunterdon Central",
                "Moorestown High", "Cherry Hill East",
                "Bernards High", "Ridge High",
            ],
        },
    },

    # ═══════════════ MID-ATLANTIC ═══════════════
    "PA": {
        "name": "Pennsylvania",
        "conferences": {
            "Philadelphia Metro": [
                "Central High", "Masterman", "Friends Select",
                "Penn Charter", "Germantown Academy", "Episcopal Academy",
                "Haverford School", "Agnes Irwin",
            ],
            "Main Line League": [
                "Baldwin School", "Shipley School", "Malvern Prep",
                "La Salle College High", "Harriton High",
                "Lower Merion High", "Radnor High", "Conestoga High",
            ],
            "Western PA": [
                "North Allegheny", "Mt. Lebanon", "Fox Chapel",
                "Shady Side Academy", "Winchester Thurston", "Ellis School",
                "Pine-Richland", "Seneca Valley",
            ],
        },
    },
    "MD": {
        "name": "Maryland",
        "conferences": {
            "Capital Beltway": [
                "Sidwell Friends", "National Cathedral", "Georgetown Day",
                "St. Albans", "Gonzaga", "Landon School",
                "Holton-Arms", "Bullis School",
            ],
            "Baltimore Metro": [
                "McDonogh School", "Gilman School", "Calvert Hall",
                "Loyola Blakefield", "Mt. St. Joseph", "John Carroll",
                "Archbishop Spalding", "Severn School",
            ],
        },
    },
    "VA": {
        "name": "Virginia",
        "conferences": {
            "NoVA Prep": [
                "Thomas Jefferson STEM", "Flint Hill", "Potomac School",
                "Foxcroft School", "Madeira School", "Episcopal High",
                "Woodberry Forest", "Collegiate School",
            ],
            "Northern Virginia": [
                "Langley High", "McLean High", "Oakton High",
                "Centreville High", "Lake Braddock", "Robinson Secondary",
                "South County High", "West Springfield High",
            ],
        },
    },

    # ═══════════════ SOUTHEAST ═══════════════
    "GA": {
        "name": "Georgia",
        "conferences": {
            "Metro Atlanta Prep": [
                "Marist School", "Lovett School", "Pace Academy",
                "Woodward Academy", "Westminster Schools", "Holy Innocents",
                "Greater Atlanta Christian", "Blessed Trinity",
            ],
            "Gwinnett-Cobb": [
                "North Gwinnett", "Mill Creek", "Buford High",
                "Collins Hill", "Brookwood", "Parkview",
                "Walton High", "Lassiter High",
            ],
        },
    },
    "FL": {
        "name": "Florida",
        "conferences": {
            "South Florida Gold": [
                "American Heritage", "St. Thomas Aquinas", "Chaminade-Madonna",
                "Cardinal Gibbons", "Pine Crest", "Ransom Everglades",
                "Gulliver Prep", "Palmer Trinity",
            ],
            "Central Florida": [
                "Trinity Prep", "Lake Highland Prep", "Montverde Academy",
                "Windermere Prep", "Berkeley Prep", "Plant High",
                "Bolles School", "Bishop Kenny",
            ],
        },
    },
    "NC": {
        "name": "North Carolina",
        "conferences": {
            "Charlotte Metro": [
                "Charlotte Country Day", "Providence Day", "Cannon School",
                "Charlotte Latin", "Charlotte Catholic", "Ardrey Kell",
                "Myers Park", "Hough High",
            ],
            "Triangle League": [
                "Ravenscroft", "Durham Academy", "Cary Academy",
                "Leesville Road", "Green Hope", "Panther Creek",
                "Holly Springs", "Apex Friendship",
            ],
        },
    },
    "TN": {
        "name": "Tennessee",
        "conferences": {
            "Nashville Prep": [
                "Montgomery Bell Academy", "Brentwood Academy",
                "Ensworth School", "Battle Ground Academy",
                "University School Nashville", "Webb School",
                "Ravenwood High", "Independence High",
            ],
            "Memphis-Chattanooga": [
                "Baylor School", "McCallie School", "GPS Chattanooga",
                "Catholic High Memphis", "Houston High",
                "Briarcrest Christian", "Collierville High", "St. George's",
            ],
        },
    },

    # ═══════════════ GREAT LAKES ═══════════════
    "OH": {
        "name": "Ohio",
        "conferences": {
            "Northeast Ohio": [
                "St. Ignatius", "St. Edward", "Archbishop Hoban",
                "Walsh Jesuit", "St. Vincent-St. Mary", "Gilmour Academy",
                "University School", "Western Reserve Academy",
            ],
            "Cincinnati-Columbus": [
                "St. Xavier", "Elder High", "Moeller",
                "La Salle", "Centerville", "Mason",
                "Dublin Jerome", "Upper Arlington",
            ],
        },
    },
    "IL": {
        "name": "Illinois",
        "conferences": {
            "Chicago Metro": [
                "Whitney Young", "Lane Tech", "Walter Payton",
                "Jones College Prep", "Northside Prep", "Latin School",
                "Loyola Academy", "New Trier",
            ],
            "Suburban West": [
                "Stevenson", "Lake Forest Academy", "Naperville Central",
                "Naperville North", "Hinsdale Central", "Downers Grove North",
                "Glenbard West", "Barrington",
            ],
        },
    },
    "MI": {
        "name": "Michigan",
        "conferences": {
            "Detroit Metro": [
                "Detroit Country Day", "Cranbrook Kingswood",
                "University Liggett", "Brother Rice",
                "De La Salle", "Catholic Central",
                "Marian High", "Mercy High",
            ],
            "Washtenaw-West": [
                "Ann Arbor Pioneer", "Ann Arbor Huron", "Brighton High",
                "Saline High", "Northville High", "Plymouth High",
                "Grand Rapids Christian", "East Grand Rapids",
            ],
        },
    },
    "MN": {
        "name": "Minnesota",
        "conferences": {
            "Metro Prep": [
                "Blake School", "Breck School", "St. Thomas Academy",
                "Benilde-St. Margaret's", "Minnehaha Academy",
                "Mounds Park Academy", "Edina High", "Wayzata High",
            ],
            "South Suburban": [
                "Eden Prairie", "Minnetonka", "Prior Lake", "Rosemount",
                "Lakeville North", "Lakeville South",
                "Woodbury High", "Eagan High",
            ],
        },
    },

    # ═══════════════ PLAINS ═══════════════
    "TX": {
        "name": "Texas",
        "conferences": {
            "DFW Metroplex": [
                "Highland Park", "St. Mark's", "Hockaday School",
                "Greenhill School", "Episcopal Dallas", "Parish Episcopal",
                "Jesuit Dallas", "Ursuline Academy",
            ],
            "Houston Metro": [
                "Kinkaid School", "St. John's Houston", "Episcopal Houston",
                "Strake Jesuit", "St. Agnes Academy", "St. Pius X",
                "Memorial High", "Bellaire High",
            ],
            "Texas Hill Country": [
                "Westlake High", "Lake Travis", "Vandegrift",
                "Cedar Park", "Dripping Springs", "Bowie High",
                "Anderson High", "McCallum High",
            ],
            "North Texas": [
                "Allen High", "Southlake Carroll", "Coppell",
                "Prosper", "Denton Guyer", "Trophy Club Byron Nelson",
                "Flower Mound", "Hebron High",
            ],
        },
    },
    "OK": {
        "name": "Oklahoma",
        "conferences": {
            "Tulsa Metro": [
                "Jenks High", "Union High", "Owasso High",
                "Broken Arrow", "Bixby High", "Bishop Kelley",
                "Holland Hall", "Casady School",
            ],
            "OKC Metro": [
                "Edmond Memorial", "Edmond North", "Edmond Santa Fe",
                "Norman North", "Deer Creek", "Mustang High",
                "Heritage Hall", "Stillwater High",
            ],
        },
    },
    "KS": {
        "name": "Kansas",
        "conferences": {
            "Johnson County": [
                "Blue Valley North", "Blue Valley", "Blue Valley West",
                "Blue Valley Northwest", "Shawnee Mission East",
                "St. Thomas Aquinas KS", "Bishop Miege", "Olathe North",
            ],
            "Central Kansas": [
                "Olathe West", "Lawrence Free State", "Manhattan High",
                "Wichita Collegiate", "Kapaun Mt. Carmel",
                "Derby High", "Maize High", "Washburn Rural",
            ],
        },
    },

    # ═══════════════ MOUNTAIN ═══════════════
    "CO": {
        "name": "Colorado",
        "conferences": {
            "South Metro": [
                "Cherry Creek", "Valor Christian", "Regis Jesuit",
                "Mullen High", "Arapahoe High", "ThunderRidge",
                "Legend High", "Mountain Vista",
            ],
            "Front Range": [
                "Grandview High", "Chatfield High", "Columbine High",
                "Smoky Hill", "Fairview High", "Monarch High",
                "Boulder High", "Niwot High",
            ],
            "Northern Colorado": [
                "Fossil Ridge", "Poudre High", "Rocky Mountain",
                "Fort Collins High", "Rampart High",
                "Cheyenne Mountain", "Air Academy", "Pine Creek",
            ],
        },
    },
    "WY": {
        "name": "Wyoming",
        "conferences": {
            "Cheyenne-Casper": [
                "Cheyenne Central", "Cheyenne East", "Cheyenne South",
                "Natrona County", "Kelly Walsh", "Laramie High",
                "Thunder Basin", "Campbell County",
            ],
            "Frontier League": [
                "Sheridan High", "Rock Springs", "Green River",
                "Star Valley", "Jackson Hole", "Cody High",
                "Powell High", "Riverton High", "Lander Valley",
            ],
        },
    },
    "UT": {
        "name": "Utah",
        "conferences": {
            "Salt Lake Metro": [
                "Brighton High", "East High SLC", "Highland High",
                "Olympus High", "Skyline High", "Bingham High",
                "Herriman High", "Riverton UT",
            ],
            "Utah Valley": [
                "Corner Canyon", "Lone Peak", "American Fork",
                "Pleasant Grove", "Westlake UT", "Timpview",
                "Provo High", "Mountain Ridge",
            ],
        },
    },
    "MT": {
        "name": "Montana",
        "conferences": {
            "Western Montana": [
                "Sentinel High", "Hellgate High", "Big Sky Missoula",
                "Capital High Helena", "Helena High", "Glacier High",
                "Flathead High", "Butte High",
            ],
            "Eastern Montana": [
                "Bozeman High", "Gallatin High", "Billings Senior",
                "Billings West", "Billings Skyview", "Great Falls High",
                "CMR Great Falls", "Belgrade High",
            ],
        },
    },

    # ═══════════════ PACIFIC NORTHWEST ═══════════════
    "OR": {
        "name": "Oregon",
        "conferences": {
            "Metro League": [
                "Jesuit Portland", "Central Catholic", "Sunset High",
                "Westview High", "Beaverton High", "Southridge High",
                "Catlin Gabel School", "Oregon Episcopal School",
            ],
            "Portland Interscholastic": [
                "Lincoln Portland", "Grant Portland", "Cleveland Portland",
                "Wilson Portland", "Franklin Portland", "Roosevelt Portland",
                "Jefferson Portland", "Madison Portland", "Benson Portland",
            ],
            "Three Rivers": [
                "Lake Oswego", "Lakeridge High", "West Linn",
                "Tualatin High", "Tigard High", "Sheldon High",
                "South Eugene", "North Medford",
            ],
        },
    },
    "WA": {
        "name": "Washington",
        "conferences": {
            "Seattle Metro": [
                "Lakeside School", "Roosevelt High", "Garfield High",
                "Ballard High", "O'Dea High", "Bishop Blanchet",
                "Eastside Catholic", "Bellevue High",
            ],
            "Eastside-Spokane": [
                "Issaquah High", "Skyline High WA", "Woodinville High",
                "Bothell High", "Gonzaga Prep", "Lewis & Clark",
                "Mead High", "University High Spokane",
            ],
        },
    },

    # ═══════════════ CALIFORNIA ═══════════════
    "CA": {
        "name": "California",
        "conferences": {
            "LA Prep": [
                "Harvard-Westlake", "Crossroads", "Windward",
                "Marlborough", "Archer School", "Polytechnic Pasadena",
                "Loyola High LA", "Brentwood School",
            ],
            "LA Private": [
                "Campbell Hall", "Sierra Canyon", "Oaks Christian",
                "Alemany High", "Chaminade Prep", "St. Francis Prep",
                "Crespi Carmelite", "Notre Dame Sherman Oaks",
            ],
            "NorCal Prep": [
                "Bellarmine", "Sacred Heart Prep", "Crystal Springs Uplands",
                "Menlo School", "Castilleja", "St. Ignatius SF",
                "Mitty Archbishop", "Presentation High",
            ],
            "East Bay-Valley": [
                "De La Salle CA", "Carondelet", "Monte Vista",
                "Amador Valley", "San Ramon Valley", "California High",
                "Dublin High", "Foothill Pleasanton",
            ],
            "Orange County": [
                "Mater Dei", "Servite", "JSerra Catholic",
                "Santa Margarita", "Tesoro High", "San Clemente",
                "Mission Viejo", "El Toro High",
            ],
            "San Diego": [
                "Torrey Pines", "Cathedral Catholic", "La Jolla Country Day",
                "Francis Parker", "Granite Hills", "Helix High",
                "Rancho Bernardo", "Poway High",
            ],
        },
    },
}

# ──────────────────────────────────────────────
# MASCOT POOL (assigned randomly to HS teams)
# ──────────────────────────────────────────────

HS_MASCOTS = [
    "Eagles", "Hawks", "Falcons", "Panthers", "Tigers", "Lions",
    "Bears", "Wolves", "Bulldogs", "Wildcats", "Mustangs", "Cougars",
    "Warriors", "Knights", "Spartans", "Trojans", "Vikings", "Pioneers",
    "Raiders", "Chargers", "Rams", "Hornets", "Jaguars", "Bobcats",
    "Owls", "Cardinals", "Blue Devils", "Crusaders", "Lancers",
    "Thunderbolts", "Coyotes", "Stallions", "Bison", "Grizzlies",
    "Huskies", "Braves", "Rebels", "Cavaliers", "Comets", "Stingers",
]

# ──────────────────────────────────────────────
# HS OFFENSE STYLES (simpler than college)
# ──────────────────────────────────────────────

HS_OFFENSE_STYLES = [
    "balanced", "ground_pound", "triple_option", "smashmouth", "tempo",
]

HS_DEFENSE_STYLES = [
    "swarm", "zone", "man_press", "blitz_heavy",
]

# ──────────────────────────────────────────────
# ROSTER TEMPLATE (24 players per HS team)
# ──────────────────────────────────────────────

HS_ROSTER_TEMPLATE = [
    "Offensive Line", "Offensive Line", "Offensive Line",
    "Offensive Line", "Offensive Line", "Offensive Line",
    "Defensive Line", "Defensive Line", "Defensive Line",
    "Defensive Line", "Defensive Line",
    "Halfback", "Halfback", "Halfback",
    "Wingback", "Wingback",
    "Slotback", "Slotback",
    "Zeroback", "Zeroback",
    "Viper", "Viper",
    "Keeper", "Keeper",
]

# Stat ranges by HS class year
HS_STAT_RANGES = {
    "Freshman":  (15, 30),
    "Sophomore": (22, 38),
    "Junior":    (28, 48),
    "Senior":    (33, 55),
}

HS_YEAR_ORDER = ["Freshman", "Sophomore", "Junior", "Senior"]
