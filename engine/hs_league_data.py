"""
High School League Data — Real schools organized by state, conference, and region.

Hierarchy: Conference → Division (State) → Region → National
California is its own region.
"""

# ──────────────────────────────────────────────
# REGIONS
# ──────────────────────────────────────────────

REGIONS = {
    "New England": ["MA", "CT", "NH", "VT", "ME", "RI"],
    "Tri-State": ["NY", "NJ", "DE"],
    "Mid-Atlantic": ["PA", "MD", "VA", "DC", "WV"],
    "Southeast": ["GA", "FL", "NC", "SC", "TN", "AL", "MS"],
    "Gulf Coast": ["LA", "AR"],
    "Great Lakes": ["OH", "IL", "MI", "MN", "IN", "WI"],
    "Plains": ["TX", "OK", "KS", "MO", "NE", "IA"],
    "Mountain": ["CO", "WY", "UT", "MT", "ID", "NM", "AZ", "NV", "ND", "SD"],
    "Pacific Northwest": ["OR", "WA"],
    "California": ["CA"],
    "Pacific": ["HI", "AK"],
    "Appalachia": ["KY"],
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
    # ═══════════════ NEW ENGLAND ═══════════════
    "MA": {
        "name": "Massachusetts",
        "conferences": {
            "Bay State Conference": [
                "Boston Latin", "Brookline High", "Newton North", "Belmont High",
                "Lexington High", "Winchester High", "Wellesley High", "Needham High",
                "Natick High", "Andover High", "Braintree High", "Framingham High",
                "Milton High", "Walpole High",
            ],
            "New England Prep": [
                "Phillips Academy", "Deerfield Academy", "Milton Academy",
                "Noble & Greenough", "Thayer Academy", "BB&N",
                "Middlesex School", "Concord Academy", "Dana Hall",
                "Northfield Mount Hermon", "Rivers School", "Tabor Academy",
            ],
            "Pioneer Valley": [
                "Groton School", "St. Mark's School", "Worcester Academy",
                "Springfield Central", "Longmeadow High",
                "Amherst Regional", "Northampton High", "Westfield High MA",
                "Chicopee Comp", "Ludlow High",
            ],
            "South Coast": [
                "New Bedford High", "Dartmouth High", "Durfee High",
                "Bridgewater-Raynham", "BC High", "Xaverian Brothers",
                "Archbishop Williams", "Cardinal Spellman",
            ],
            "Merrimack Valley": [
                "Central Catholic MA", "Lowell High", "Haverhill High",
                "Methuen High", "Lawrence High", "North Andover High",
                "Chelmsford High", "Billerica Memorial",
            ],
        },
    },
    "CT": {
        "name": "Connecticut",
        "conferences": {
            "Fairfield County League": [
                "Greenwich High", "Staples High", "New Canaan High",
                "Darien High", "Ridgefield High", "Weston High",
                "Wilton High", "Trumbull High", "Fairfield Prep",
                "Fairfield Ludlowe", "Norwalk High", "Brien McMahon",
            ],
            "Hartford Metro": [
                "Glastonbury High", "Hall High", "Conard High",
                "Simsbury High", "Avon High", "Farmington High",
                "Southington High", "Cheshire Academy", "Cheshire High",
                "Newington High", "Bristol Central",
            ],
            "CT Prep League": [
                "Choate Rosemary Hall", "Hotchkiss School", "Kent School",
                "Loomis Chaffee", "Westminster School", "Taft School",
                "Pomfret School", "Suffield Academy", "Miss Porter's School",
            ],
            "Shoreline Conference": [
                "Guilford High", "Hand High", "Shelton High",
                "East Haven High", "Hamden Hall", "Sacred Heart Academy CT",
                "Notre Dame West Haven", "West Haven High",
            ],
        },
    },
    "NH": {
        "name": "New Hampshire",
        "conferences": {
            "Division I": [
                "Exeter High", "Phillips Exeter", "Pinkerton Academy",
                "Bedford High", "Londonderry High", "Goffstown High",
                "Salem High NH", "Nashua South", "Nashua North",
                "Concord High NH", "Dover High", "Winnacunnet High",
            ],
            "Division II": [
                "St. Paul's School NH", "Proctor Academy", "Kimball Union",
                "Holderness School", "New Hampton School", "Brewster Academy",
                "Tilton School", "Lebanon High", "Hanover High NH",
            ],
        },
    },
    "VT": {
        "name": "Vermont",
        "conferences": {
            "Metro Conference": [
                "Rice Memorial", "Burlington High", "South Burlington High",
                "Essex High", "Colchester High", "Mount Mansfield Union",
                "Champlain Valley Union", "St. Johnsbury Academy",
            ],
        },
    },
    "ME": {
        "name": "Maine",
        "conferences": {
            "Southern Maine": [
                "Portland High ME", "Deering High", "Scarborough High",
                "Thornton Academy", "Bonny Eagle", "Gorham High",
                "Windham High ME", "Cheverus High", "South Portland High",
            ],
            "Central Maine": [
                "Bangor High", "Brewer High", "Edward Little",
                "Lewiston High", "Oxford Hills", "Hampden Academy",
                "John Bapst", "Maine Central Institute",
            ],
        },
    },
    "RI": {
        "name": "Rhode Island",
        "conferences": {
            "Interscholastic League": [
                "La Salle Academy RI", "Bishop Hendricken", "St. Raphael",
                "Barrington High", "East Greenwich High", "Cranston West",
                "North Kingstown High", "South Kingstown High",
                "Moses Brown", "Wheeler School", "Providence Country Day",
            ],
        },
    },

    # ═══════════════ TRI-STATE ═══════════════
    "NY": {
        "name": "New York",
        "conferences": {
            "NYC Metro": [
                "Stuyvesant", "Bronx Science", "Brooklyn Tech",
                "Dalton School", "Horace Mann", "Trinity School",
                "Fieldston", "Poly Prep", "Regis High", "Xavier High NY",
                "Fordham Prep", "Mount St. Michael",
            ],
            "NYC Public": [
                "Erasmus Hall", "Lincoln HS Brooklyn", "Boys & Girls High",
                "Thomas Jefferson HS", "Murry Bergtraum", "Cardozo High",
                "Francis Lewis", "Tottenville High",
            ],
            "Westchester-Hudson": [
                "Riverdale Country", "Hackley School", "Rye High",
                "Mamaroneck High", "Scarsdale High", "Byram Hills",
                "Bronxville High", "Hastings High", "Iona Prep",
                "Stepinac High", "Kennedy Catholic", "Ossining High",
            ],
            "Long Island": [
                "Chaminade High", "St. Anthony's", "Holy Trinity LI",
                "Kellenberg Memorial", "Garden City High", "Manhasset High",
                "Massapequa High", "Syosset High", "Uniondale High",
                "Freeport High", "Baldwin Senior High",
            ],
            "Upstate Elite": [
                "Emma Willard", "Albany Academy", "Nichols School",
                "Canisius High", "Aquinas Institute", "McQuaid Jesuit",
                "Pittsford Mendon", "Fairport High", "Victor High",
                "Rush-Henrietta", "Cicero-North Syracuse",
            ],
            "Capital Region": [
                "Shaker High", "Shenendehowa", "Saratoga Springs",
                "Niskayuna High", "Bethlehem Central", "Colonie Central",
                "LaSalle Institute", "CBA Albany",
            ],
        },
    },
    "NJ": {
        "name": "New Jersey",
        "conferences": {
            "North Jersey Conference": [
                "Bergen Catholic", "Don Bosco Prep", "Delbarton School",
                "Seton Hall Prep", "St. Peter's Prep", "Montclair High",
                "Ridgewood High", "Westfield High", "Paramus Catholic",
                "DePaul Catholic", "Wayne Hills", "Ramapo High",
            ],
            "Central Jersey League": [
                "Pingry School", "Lawrenceville School", "Hun School",
                "Blair Academy", "Peddie School", "Gill St. Bernard's",
                "Plainfield High", "Phillipsburg High",
                "Watchung Hills", "Hillsborough High",
            ],
            "Shore Conference": [
                "Red Bank Catholic", "Rumson-Fair Haven",
                "Bridgewater-Raritan", "Hunterdon Central",
                "Moorestown High", "Cherry Hill East",
                "Bernards High", "Ridge High", "Wall Township",
                "Manalapan High", "Freehold Township",
            ],
            "South Jersey": [
                "Camden Catholic", "Williamstown High", "St. Augustine Prep",
                "Holy Spirit NJ", "Vineland High", "Millville High",
                "Egg Harbor Township", "Absegami High",
            ],
            "Hudson County": [
                "St. Peter's Prep JC", "Marist High", "Hoboken High",
                "Memorial West NY", "North Bergen High", "Union City High",
                "Bayonne High", "Kearny High",
            ],
        },
    },
    "DE": {
        "name": "Delaware",
        "conferences": {
            "Blue Hen Conference": [
                "Salesianum School", "St. Mark's DE", "Archmere Academy",
                "Tower Hill School", "Wilmington Friends", "Tatnall School",
                "Concord High DE", "Middletown High DE", "Smyrna High",
                "Caesar Rodney", "Dover High DE", "Cape Henlopen",
            ],
        },
    },

    # ═══════════════ MID-ATLANTIC ═══════════════
    "PA": {
        "name": "Pennsylvania",
        "conferences": {
            "Philadelphia Catholic": [
                "St. Joseph's Prep", "Roman Catholic", "Archbishop Wood",
                "Archbishop Ryan", "La Salle College High", "Father Judge",
                "Cardinal O'Hara", "Bonner-Prendergast", "Neumann-Goretti",
                "West Catholic Prep",
            ],
            "Philadelphia Public": [
                "Central High Philly", "Masterman", "Imhotep Charter",
                "Martin Luther King HS", "Constitution High",
                "Northeast High Philly", "Frankford High", "Overbrook High",
            ],
            "Main Line League": [
                "Baldwin School", "Shipley School", "Malvern Prep",
                "Episcopal Academy", "Haverford School", "Agnes Irwin",
                "Penn Charter", "Germantown Academy",
                "Harriton High", "Lower Merion High", "Radnor High",
                "Conestoga High", "Garnet Valley", "Strath Haven",
            ],
            "Western PA": [
                "North Allegheny", "Mt. Lebanon", "Fox Chapel",
                "Shady Side Academy", "Winchester Thurston", "Ellis School",
                "Pine-Richland", "Seneca Valley", "Central Catholic Pittsburgh",
                "Gateway High", "Woodland Hills", "Penn Hills",
            ],
            "Central PA": [
                "State College High", "Harrisburg High", "Central Dauphin",
                "Cumberland Valley", "Carlisle High", "Mifflin County",
                "Williamsport Area", "Bishop McDevitt PA",
            ],
            "Lehigh Valley": [
                "Liberty High Bethlehem", "Freedom High", "Emmaus High",
                "Parkland High", "Northampton High PA", "Allen High",
                "Easton Area", "Nazareth Area",
            ],
        },
    },
    "MD": {
        "name": "Maryland",
        "conferences": {
            "Capital Beltway": [
                "Sidwell Friends", "National Cathedral", "Georgetown Day",
                "St. Albans", "Gonzaga DC", "Landon School",
                "Holton-Arms", "Bullis School", "Good Counsel",
                "DeMatha Catholic", "Bishop McNamara", "Archbishop Carroll DC",
            ],
            "Baltimore Metro": [
                "McDonogh School", "Gilman School", "Calvert Hall",
                "Loyola Blakefield", "Mt. St. Joseph", "John Carroll MD",
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

    # ═══════════════ MID-ATLANTIC (cont.) ═══════════════
    "DC": {
        "name": "District of Columbia",
        "conferences": {
            "DCIAA": [
                "Dunbar High DC", "Wilson High DC", "Coolidge High",
                "Ballou High", "Anacostia High", "Eastern High DC",
                "Roosevelt High DC", "H.D. Woodson",
            ],
            "DC Metro Private": [
                "Maret School", "Sidwell Friends DC", "St. John's DC",
                "Gonzaga College High", "Georgetown Prep",
                "Potomac School DC", "Flint Hill DC",
            ],
        },
    },
    "WV": {
        "name": "West Virginia",
        "conferences": {
            "Mountain State": [
                "Huntington High", "Spring Valley WV", "Cabell Midland",
                "George Washington WV", "South Charleston",
                "Morgantown High", "University High WV", "Bridgeport High WV",
                "Wheeling Park", "Wheeling Central Catholic",
                "Parkersburg High", "Parkersburg South",
            ],
        },
    },

    # ═══════════════ SOUTHEAST ═══════════════
    "GA": {
        "name": "Georgia",
        "conferences": {
            "Metro Atlanta Prep": [
                "Marist School GA", "Lovett School", "Pace Academy",
                "Woodward Academy", "Westminster Schools", "Holy Innocents",
                "Greater Atlanta Christian", "Blessed Trinity",
                "Wesleyan School", "Mount Pisgah Christian",
            ],
            "Gwinnett-Cobb": [
                "North Gwinnett", "Mill Creek", "Buford High",
                "Collins Hill", "Brookwood", "Parkview",
                "Walton High", "Lassiter High", "McEachern",
                "Grayson High", "Norcross High", "Peachtree Ridge",
            ],
            "South Metro": [
                "Creekside High GA", "Newnan High", "Starr's Mill",
                "McIntosh High", "Whitewater High", "Fayette County",
                "Carrollton High", "LaGrange High",
            ],
            "Coastal Georgia": [
                "Savannah Country Day", "Savannah Christian",
                "Benedictine Military", "St. Andrew's Savannah",
                "Brunswick High", "Glynn Academy", "Richmond Hill",
                "Effingham County", "Statesboro High",
            ],
            "Augusta-Macon": [
                "Augusta Christian", "Westside Augusta", "Evans High GA",
                "Lakeside Augusta", "Stratford Academy",
                "First Presbyterian Day", "Houston County",
                "Warner Robins High", "Northside Warner Robins",
            ],
        },
    },
    "FL": {
        "name": "Florida",
        "conferences": {
            "South Florida Gold": [
                "American Heritage", "St. Thomas Aquinas", "Chaminade-Madonna",
                "Cardinal Gibbons FL", "Pine Crest", "Ransom Everglades",
                "Gulliver Prep", "Palmer Trinity", "University School NSU",
                "Dillard High", "Stranahan High",
            ],
            "Miami-Dade": [
                "Belen Jesuit", "Columbus High FL", "Coral Gables High",
                "Miami Norland", "Carol City", "Northwestern Miami",
                "Booker T. Washington FL", "Killian High",
                "South Dade High", "Monsignor Pace",
            ],
            "Central Florida": [
                "Trinity Prep", "Lake Highland Prep", "Montverde Academy",
                "Windermere Prep", "Berkeley Prep", "Plant High",
                "Bolles School", "Bishop Kenny", "Bartram Trail",
                "Nease High", "Creekside FL", "Fletcher High",
            ],
            "Palm Beach": [
                "Oxbridge Academy", "King's Academy", "Benjamin School",
                "Palm Beach Gardens High", "Dwyer High",
                "Jupiter High", "Seminole Ridge", "Wellington High FL",
            ],
            "Tampa Bay": [
                "Jesuit Tampa", "Tampa Catholic", "Steinbrenner High",
                "Newsome High", "Gaither High", "Wharton High",
                "Robinson High", "Sickles High",
            ],
            "Panhandle": [
                "Booker T. Washington Pensacola", "Pine Forest FL",
                "Pace High FL", "Niceville High", "Fort Walton Beach",
                "Crestview High", "Choctawhatchee High", "Navarre High",
            ],
        },
    },
    "NC": {
        "name": "North Carolina",
        "conferences": {
            "Charlotte Metro": [
                "Charlotte Country Day", "Providence Day", "Cannon School",
                "Charlotte Latin", "Charlotte Catholic", "Ardrey Kell",
                "Myers Park", "Hough High", "Mallard Creek",
                "Vance High", "Olympic High", "Butler High NC",
            ],
            "Triangle League": [
                "Ravenscroft", "Durham Academy", "Cary Academy",
                "Leesville Road", "Green Hope", "Panther Creek",
                "Holly Springs", "Apex Friendship", "Millbrook High",
                "Sanderson High", "Broughton High",
            ],
            "Piedmont Triad": [
                "Grimsley High", "Page High", "Ragsdale High",
                "Northwest Guilford", "Northern Guilford",
                "Dudley High", "Smith High", "Southeast Guilford",
                "Reagan High NC", "West Forsyth",
            ],
            "Eastern NC": [
                "New Hanover High", "Hoggard High", "Laney High",
                "Jacksonville High NC", "South Central", "Northside Pinetown",
                "Rose High", "Havelock High",
            ],
        },
    },
    "SC": {
        "name": "South Carolina",
        "conferences": {
            "Lowcountry": [
                "Porter-Gaud", "Ashley Hall", "Bishop England",
                "Academic Magnet", "James Island Charter",
                "Wando High", "Lucy Beckham", "Cane Bay",
                "Summerville High", "Goose Creek High",
            ],
            "Midlands": [
                "Hammond School", "Heathwood Hall", "Ben Lippen",
                "Cardinal Newman SC", "Dreher High", "A.C. Flora",
                "Spring Valley SC", "Richland Northeast",
                "Dutch Fork", "River Bluff",
            ],
            "Upstate": [
                "Christ Church Episcopal", "Greenville High",
                "Mauldin High", "J.L. Mann", "Byrnes High",
                "Spartanburg High", "Dorman High", "Boiling Springs SC",
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
                "Brentwood High", "Franklin High TN",
            ],
            "Memphis": [
                "Catholic High Memphis", "Houston High TN",
                "Briarcrest Christian", "Collierville High", "St. George's",
                "Germantown High", "White Station",
                "East High Memphis", "Central High Memphis",
                "Whitehaven High", "MUS Memphis",
            ],
            "Chattanooga-Knoxville": [
                "Baylor School", "McCallie School", "GPS Chattanooga",
                "Webb School Knoxville", "Catholic High Knoxville",
                "Farragut High", "Bearden High", "Maryville High",
                "Science Hill", "Dobyns-Bennett",
            ],
        },
    },
    "AL": {
        "name": "Alabama",
        "conferences": {
            "Birmingham Metro": [
                "Mountain Brook", "Vestavia Hills", "Hoover High AL",
                "Spain Park", "Oak Mountain", "Thompson High",
                "Briarwood Christian", "John Carroll Catholic AL",
                "Indian Springs School", "Altamont School",
            ],
            "Gulf Coast AL": [
                "McGill-Toolen", "UMS-Wright", "St. Paul's Episcopal Mobile",
                "Murphy High", "Theodore High", "Baker High",
                "Fairhope High", "Spanish Fort", "Daphne High",
                "Saraland High",
            ],
            "Black Belt-Tuscaloosa": [
                "Tuscaloosa County", "Central Tuscaloosa", "Hillcrest Tuscaloosa",
                "American Christian Academy", "Northridge High AL",
                "Auburn High", "Opelika High", "Lee-Scott Academy",
            ],
            "North Alabama": [
                "Huntsville High", "Grissom High", "Bob Jones High",
                "James Clemens", "Sparkman High",
                "Randolph School", "Westminster Christian AL",
                "Decatur High", "Hartselle High",
            ],
        },
    },
    "MS": {
        "name": "Mississippi",
        "conferences": {
            "Jackson Metro": [
                "Jackson Prep", "Jackson Academy", "Madison-Ridgeland Academy",
                "MRA", "Hartfield Academy", "Parklane Academy",
                "Murrah High", "Jim Hill High",
                "Ridgeland High", "Clinton High MS",
            ],
            "Gulf Coast MS": [
                "Biloxi High", "D'Iberville High", "Ocean Springs",
                "Gulfport High", "Long Beach High MS",
                "Pass Christian", "Moss Point", "Pascagoula High",
            ],
            "Delta-North": [
                "Greenville High MS", "Washington School",
                "Pillow Academy", "Cleveland Central",
                "Tupelo High", "Oxford High MS", "Starkville High",
                "Columbus High MS", "West Point High MS",
            ],
        },
    },

    # ═══════════════ GULF COAST ═══════════════
    "LA": {
        "name": "Louisiana",
        "conferences": {
            "Greater New Orleans": [
                "Jesuit New Orleans", "Brother Martin", "Holy Cross LA",
                "Archbishop Rummel", "John Curtis Christian",
                "St. Augustine LA", "De La Salle LA", "Newman School NOLA",
                "Isidore Newman", "Country Day NOLA",
                "Lusher Charter", "Benjamin Franklin",
            ],
            "Baton Rouge": [
                "Catholic High BR", "University Lab", "Baton Rouge Magnet",
                "Episcopal BR", "Parkview Baptist", "Dunham School",
                "Zachary High", "Central Baton Rouge",
                "Scotlandville Magnet", "McKinley High BR",
            ],
            "Acadiana-North": [
                "Lafayette High", "Acadiana High", "Teurlings Catholic",
                "St. Thomas More LA", "Comeaux High",
                "Byrd High", "Captain Shreve", "Evangel Christian",
                "Woodlawn High LA", "Airline High",
            ],
        },
    },
    "AR": {
        "name": "Arkansas",
        "conferences": {
            "Central Arkansas": [
                "Pulaski Academy", "Catholic High LR", "Little Rock Central",
                "Little Rock Christian", "Bryant High AR",
                "Benton High AR", "Conway High", "Cabot High",
                "Maumelle High", "North Little Rock",
            ],
            "Northwest Arkansas": [
                "Bentonville High", "Bentonville West", "Fayetteville High",
                "Har-Ber High", "Rogers Heritage", "Rogers High",
                "Springdale High", "Springdale Har-Ber",
            ],
        },
    },

    # ═══════════════ GREAT LAKES ═══════════════
    "OH": {
        "name": "Ohio",
        "conferences": {
            "Northeast Ohio": [
                "St. Ignatius Cleveland", "St. Edward Cleveland",
                "Archbishop Hoban", "Walsh Jesuit", "St. Vincent-St. Mary",
                "Gilmour Academy", "University School OH",
                "Western Reserve Academy", "Shaker Heights",
                "Solon High", "Strongsville High",
            ],
            "Cincinnati": [
                "St. Xavier Cincinnati", "Elder High", "Moeller",
                "La Salle Cincinnati", "Lakota West", "Mason",
                "Centerville", "Colerain", "Sycamore High OH",
                "Anderson High OH", "Turpin High",
            ],
            "Columbus": [
                "Dublin Jerome", "Upper Arlington", "Olentangy Liberty",
                "Olentangy Orange", "Hilliard Davidson",
                "Gahanna Lincoln", "Pickerington Central",
                "New Albany OH", "Westerville Central",
            ],
            "Dayton-Toledo": [
                "Centerville OH", "Springboro High", "Alter High",
                "Chaminade Julienne", "Wayne High OH",
                "St. John's Jesuit Toledo", "Central Catholic Toledo",
                "Anthony Wayne", "Perrysburg High", "Whitmer High",
            ],
        },
    },
    "IL": {
        "name": "Illinois",
        "conferences": {
            "Chicago Catholic": [
                "Mount Carmel IL", "De La Salle Chicago",
                "Brother Rice IL", "St. Rita", "Marist IL",
                "St. Laurence", "Leo High", "Fenwick High",
            ],
            "Chicago Public": [
                "Whitney Young", "Lane Tech", "Walter Payton",
                "Jones College Prep", "Northside Prep", "Latin School",
                "Simeon Career Academy", "Morgan Park",
                "King College Prep", "Kenwood Academy",
            ],
            "North Shore": [
                "Loyola Academy IL", "New Trier", "Evanston Township",
                "Maine South", "Glenbrook South", "Glenbrook North",
                "Lake Forest High", "Lake Forest Academy",
                "Highland Park IL", "Deerfield High",
            ],
            "Suburban West": [
                "Stevenson IL", "Naperville Central",
                "Naperville North", "Hinsdale Central", "Downers Grove North",
                "Glenbard West", "Barrington", "Fremd High",
                "Palatine High", "Schaumburg High",
            ],
            "Central-Southern IL": [
                "Springfield High IL", "Sacred Heart-Griffin",
                "Normal Community", "University High IL",
                "Champaign Central", "Centennial Champaign",
                "Peoria Notre Dame", "Richwoods Peoria",
            ],
        },
    },
    "MI": {
        "name": "Michigan",
        "conferences": {
            "Detroit Catholic": [
                "Brother Rice MI", "Catholic Central MI",
                "De La Salle Collegiate", "U of D Jesuit",
                "Orchard Lake St. Mary's", "Shrine Catholic",
                "Notre Dame Prep MI", "Marian High MI",
            ],
            "Detroit Metro": [
                "Detroit Country Day", "Cranbrook Kingswood",
                "University Liggett", "Detroit King",
                "Cass Tech", "Renaissance High", "Detroit Cass Tech",
                "West Bloomfield", "Clarkston High",
            ],
            "Washtenaw-West": [
                "Ann Arbor Pioneer", "Ann Arbor Huron", "Brighton High",
                "Saline High", "Northville High", "Plymouth High",
                "Novi High", "Canton High",
            ],
            "West Michigan": [
                "Grand Rapids Christian", "East Grand Rapids",
                "Catholic Central GR", "Forest Hills Central",
                "Rockford High", "West Ottawa", "Holland Christian",
                "Muskegon High", "Mona Shores",
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
                "Woodbury High", "Eagan High", "Eastview High",
                "Burnsville High", "Apple Valley High",
            ],
            "North Metro": [
                "Totino-Grace", "Blaine High", "Andover MN",
                "Rogers High MN", "Maple Grove", "Osseo High",
                "Champlin Park", "Elk River",
            ],
        },
    },
    "IN": {
        "name": "Indiana",
        "conferences": {
            "Indianapolis Metro": [
                "Cathedral High IN", "Brebeuf Jesuit", "Park Tudor",
                "Heritage Christian IN", "Lawrence Central",
                "Warren Central", "North Central IN", "Carmel High",
                "Center Grove", "Brownsburg High",
            ],
            "Northern Indiana": [
                "Marian High South Bend", "Penn High", "Saint Joseph South Bend",
                "Concord High IN", "Elkhart High", "Warsaw Community",
                "Carroll Fort Wayne", "Homestead High", "Snider High",
                "Bishop Dwenger", "Leo High IN",
            ],
            "Southern Indiana": [
                "Floyd Central", "New Albany IN", "Jeffersonville High",
                "Castle High", "North High Evansville",
                "Memorial Evansville", "Reitz High", "Mater Dei IN",
                "Bloomington South", "Bloomington North",
            ],
        },
    },
    "WI": {
        "name": "Wisconsin",
        "conferences": {
            "Milwaukee Metro": [
                "Marquette University High", "Brookfield Academy",
                "University School Milwaukee", "Rufus King",
                "Brookfield Central", "Brookfield East",
                "Menomonee Falls", "Germantown WI",
                "Waukesha West", "Pewaukee High",
            ],
            "Madison-Fox Valley": [
                "Madison Memorial", "Madison West", "Sun Prairie",
                "Verona Area", "Middleton High WI", "Oregon WI",
                "Appleton North", "Appleton East",
                "Kimberly High", "Neenah High",
            ],
        },
    },

    # ═══════════════ PLAINS ═══════════════
    "TX": {
        "name": "Texas",
        "conferences": {
            "DFW Private": [
                "Highland Park TX", "St. Mark's Texas", "Hockaday School",
                "Greenhill School", "Episcopal Dallas", "Parish Episcopal",
                "Jesuit Dallas", "Ursuline Academy TX",
            ],
            "DFW Public": [
                "Allen High TX", "Southlake Carroll", "Coppell",
                "Prosper High", "Denton Guyer", "Trophy Club Byron Nelson",
                "Flower Mound", "Hebron High", "Plano West",
                "Plano East", "DeSoto High", "Duncanville High",
                "Cedar Hill TX", "Mansfield High", "South Grand Prairie",
            ],
            "Houston Private": [
                "Kinkaid School", "St. John's Houston", "Episcopal Houston",
                "Strake Jesuit", "St. Agnes Academy", "St. Pius X Houston",
                "Second Baptist", "St. Thomas Houston",
            ],
            "Houston Public": [
                "Memorial High TX", "Bellaire High TX", "Lamar High Houston",
                "Westside High", "Katy High", "Cinco Ranch",
                "Tompkins High", "The Woodlands", "College Park TX",
                "Atascocita High", "Kingwood High", "North Shore TX",
                "Dickinson High TX", "Shadow Creek",
            ],
            "Texas Hill Country": [
                "Westlake High TX", "Lake Travis", "Vandegrift",
                "Cedar Park", "Dripping Springs", "Bowie High TX",
                "Anderson High TX", "McCallum High",
            ],
            "San Antonio": [
                "Alamo Heights", "Central Catholic SA", "Antonian Prep",
                "TMI Episcopal", "Johnson High SA", "Reagan High SA",
                "Churchill High", "Brandeis High",
                "Steele High", "Judson High", "Clemens High",
            ],
            "West Texas": [
                "Midland High", "Midland Lee", "Odessa Permian",
                "Odessa High", "Abilene High", "Lubbock Coronado",
                "Lubbock Monterey", "Amarillo High", "Tascosa High",
            ],
            "Rio Grande Valley": [
                "Edinburg Vela", "Edinburg North", "McAllen High",
                "PSJA North", "San Benito High", "Harlingen High",
                "Brownsville Hanna", "Los Fresnos",
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
                "Booker T. Washington Tulsa", "East Central Tulsa",
            ],
            "OKC Metro": [
                "Edmond Memorial", "Edmond North", "Edmond Santa Fe",
                "Norman North", "Deer Creek OK", "Mustang High OK",
                "Heritage Hall", "Stillwater High",
                "Moore High", "Westmoore", "Norman High",
                "Putnam City", "Yukon High",
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
                "Mill Valley KS", "De Soto KS",
            ],
            "Central Kansas": [
                "Olathe West", "Lawrence Free State", "Manhattan High",
                "Wichita Collegiate", "Kapaun Mt. Carmel",
                "Derby High", "Maize High", "Washburn Rural",
                "Wichita Heights", "Wichita East",
            ],
        },
    },
    "MO": {
        "name": "Missouri",
        "conferences": {
            "St. Louis Metro": [
                "De Smet Jesuit", "CBC St. Louis", "SLUH",
                "Chaminade MO", "John Burroughs", "MICDS",
                "Priory School", "Vianney High",
                "Kirkwood High", "Ladue Horton Watkins",
                "Clayton High", "Webster Groves",
            ],
            "Kansas City": [
                "Rockhurst High", "Pembroke Hill", "Barstow School",
                "Blue Valley Stilwell", "Lee's Summit North",
                "Lee's Summit West", "Liberty High MO", "Park Hill",
                "Staley High", "Blue Springs South",
            ],
            "Central Missouri": [
                "Hickman High", "Rock Bridge", "Helias Catholic",
                "Jefferson City High", "Capital City", "Camdenton High",
                "Rolla High", "Waynesville High",
            ],
        },
    },
    "NE": {
        "name": "Nebraska",
        "conferences": {
            "Omaha Metro": [
                "Creighton Prep", "Omaha Westside", "Millard North",
                "Millard South", "Millard West", "Elkhorn South",
                "Papillion-LaVista South", "Bellevue West",
                "Omaha Burke", "Omaha Central",
            ],
            "Lincoln-Greater NE": [
                "Lincoln Southeast", "Lincoln Southwest", "Lincoln East",
                "Lincoln Pius X", "Norfolk High", "Grand Island High",
                "Kearney High", "North Platte High",
            ],
        },
    },
    "IA": {
        "name": "Iowa",
        "conferences": {
            "Des Moines Metro": [
                "Dowling Catholic", "Valley High IA", "Roosevelt IA",
                "West Des Moines Valley", "Waukee High", "Waukee Northwest",
                "Ankeny High", "Ankeny Centennial",
                "Southeast Polk", "Johnston High",
            ],
            "Eastern Iowa": [
                "Iowa City High", "Iowa City West", "Cedar Rapids Kennedy",
                "Cedar Rapids Washington", "Cedar Rapids Prairie",
                "Xavier Cedar Rapids", "Dubuque Senior", "Hempstead Dubuque",
            ],
        },
    },

    # ═══════════════ APPALACHIA ═══════════════
    "KY": {
        "name": "Kentucky",
        "conferences": {
            "Louisville Metro": [
                "Trinity Louisville", "St. Xavier Louisville",
                "Male High", "DuPont Manual", "Ballard High KY",
                "Eastern High KY", "Christian Academy Louisville",
                "Collegiate School KY", "Kentucky Country Day",
                "Sacred Heart Academy KY",
            ],
            "Lexington-Central": [
                "Lexington Catholic", "Sayre School", "Paul Laurence Dunbar",
                "Henry Clay High", "Frederick Douglass High",
                "Lafayette High KY", "Bryan Station", "Scott County KY",
            ],
            "Northern KY": [
                "Covington Catholic", "St. Henry", "Highlands High",
                "Beechwood High", "Ryle High", "Simon Kenton",
                "Dixie Heights", "Boone County",
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
                "Highlands Ranch", "Chaparral High CO",
            ],
            "Front Range": [
                "Grandview High", "Chatfield High", "Columbine High",
                "Smoky Hill", "Fairview High", "Monarch High",
                "Boulder High", "Niwot High", "Pomona High",
                "Ralston Valley", "Arvada West",
            ],
            "Northern Colorado": [
                "Fossil Ridge", "Poudre High", "Rocky Mountain CO",
                "Fort Collins High", "Rampart High",
                "Cheyenne Mountain", "Air Academy", "Pine Creek",
                "Palmer High", "Coronado High CO",
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
                "Sheridan High", "Rock Springs", "Green River WY",
                "Star Valley", "Jackson Hole", "Cody High",
                "Powell High", "Riverton High WY", "Lander Valley",
            ],
        },
    },
    "UT": {
        "name": "Utah",
        "conferences": {
            "Salt Lake Metro": [
                "Brighton High UT", "East High SLC", "Highland High UT",
                "Olympus High", "Skyline High UT", "Bingham High",
                "Herriman High", "Riverton UT", "Alta High",
                "Jordan High UT", "Cottonwood High",
            ],
            "Utah Valley": [
                "Corner Canyon", "Lone Peak", "American Fork",
                "Pleasant Grove", "Westlake UT", "Timpview",
                "Provo High", "Mountain Ridge UT", "Orem High",
                "Timpanogos High",
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
    "ID": {
        "name": "Idaho",
        "conferences": {
            "Treasure Valley": [
                "Boise High", "Bishop Kelly ID", "Timberline Boise",
                "Borah High", "Capital High Boise", "Rocky Mountain ID",
                "Eagle High", "Meridian High",
                "Centennial High ID", "Mountain View ID",
            ],
            "Eastern Idaho": [
                "Idaho Falls High", "Skyline High ID", "Bonneville High",
                "Highland High ID", "Thunder Ridge ID",
                "Twin Falls High", "Jerome High ID",
                "Pocatello High", "Century High",
            ],
        },
    },
    "AZ": {
        "name": "Arizona",
        "conferences": {
            "Phoenix Metro": [
                "Brophy College Prep", "Xavier College Prep AZ",
                "Scottsdale Prep", "Phoenix Country Day", "Arizona Prep",
                "Chandler High", "Hamilton High AZ", "Basha High",
                "Highland High AZ", "Desert Vista", "Mountain Pointe",
            ],
            "East Valley": [
                "Red Mountain", "Mesa High", "Dobson High",
                "Gilbert High", "Williams Field", "Campo Verde",
                "Queen Creek", "Eastmark High",
            ],
            "Tucson": [
                "Salpointe Catholic", "Catalina Foothills",
                "Canyon del Oro", "Cienega High", "Tucson High",
                "Rincon University", "Palo Verde Tucson",
                "Ironwood Ridge",
            ],
        },
    },
    "NM": {
        "name": "New Mexico",
        "conferences": {
            "Metro": [
                "La Cueva High", "Sandia High", "Eldorado High NM",
                "Volcano Vista", "Cibola High", "Albuquerque Academy",
                "St. Pius X Albuquerque", "Manzano High",
                "Rio Rancho High", "Cleveland High NM",
            ],
            "Southern NM": [
                "Las Cruces High", "Centennial High NM", "Mayfield High",
                "Oñate High", "Gadsden High", "Hobbs High",
                "Carlsbad High", "Artesia High",
            ],
        },
    },
    "NV": {
        "name": "Nevada",
        "conferences": {
            "Las Vegas": [
                "Bishop Gorman", "Coronado Henderson", "Green Valley High",
                "Foothill Henderson", "Liberty High NV", "Centennial High NV",
                "Arbor View", "Faith Lutheran",
                "Desert Pines", "Shadow Ridge", "Palo Verde LV",
            ],
            "Northern Nevada": [
                "Reno High", "McQueen High", "Galena High",
                "Damonte Ranch", "Bishop Manogue", "Spanish Springs",
                "Reed High", "Hug High",
            ],
        },
    },
    "ND": {
        "name": "North Dakota",
        "conferences": {
            "Eastern Dakota": [
                "Fargo Davies", "Fargo South", "Fargo North", "Fargo Shanley",
                "West Fargo", "West Fargo Sheyenne",
                "Grand Forks Central", "Grand Forks Red River",
            ],
            "Western Dakota": [
                "Bismarck High", "Bismarck Century", "Bismarck Legacy",
                "Mandan High", "Minot High", "Dickinson High",
                "Williston High ND", "Jamestown High",
            ],
        },
    },
    "SD": {
        "name": "South Dakota",
        "conferences": {
            "East River": [
                "O'Gorman High", "Roosevelt SD", "Washington SD",
                "Lincoln SD", "Jefferson SD", "Brandon Valley",
                "Harrisburg SD", "Brookings High",
            ],
            "West River": [
                "Stevens Rapid City", "Central Rapid City", "St. Thomas More SD",
                "Mitchell High SD", "Yankton High", "Huron High",
                "Pierre Riggs", "Aberdeen Central",
            ],
        },
    },

    # ═══════════════ PACIFIC NORTHWEST ═══════════════
    "OR": {
        "name": "Oregon",
        "conferences": {
            "Metro League": [
                "Jesuit Portland", "Central Catholic OR", "Sunset High",
                "Westview High OR", "Beaverton High", "Southridge High",
                "Catlin Gabel School", "Oregon Episcopal School",
            ],
            "Portland Interscholastic": [
                "Lincoln Portland", "Grant Portland", "Cleveland Portland",
                "Wilson Portland", "Franklin Portland", "Roosevelt Portland",
                "Jefferson Portland", "Madison Portland", "Benson Portland",
            ],
            "Three Rivers": [
                "Lake Oswego", "Lakeridge High", "West Linn",
                "Tualatin High", "Tigard High", "Sheldon High OR",
                "South Eugene", "North Medford", "Thurston High",
                "Springfield High OR", "Corvallis High",
            ],
            "Southern Oregon": [
                "Crater High", "Ashland High", "South Medford",
                "Grants Pass", "Roseburg High", "Bend High",
                "Summit High OR", "Mountain View OR",
            ],
        },
    },
    "WA": {
        "name": "Washington",
        "conferences": {
            "Seattle Private": [
                "Lakeside School", "O'Dea High", "Bishop Blanchet",
                "Eastside Catholic", "Seattle Prep", "Forest Ridge",
                "Northwest School", "Bush School",
            ],
            "Seattle Public": [
                "Roosevelt WA", "Garfield WA", "Ballard High",
                "Ingraham High", "Nathan Hale WA", "Rainier Beach",
                "Franklin High WA", "Chief Sealth",
            ],
            "Eastside-Bellevue": [
                "Bellevue High", "Issaquah High", "Skyline WA",
                "Woodinville High", "Bothell High", "Redmond High",
                "Lake Washington", "Juanita High",
                "Newport High WA", "Interlake High",
            ],
            "South Puget Sound": [
                "Olympia High", "Capital High WA", "Tumwater High",
                "Bellarmine Prep WA", "Stadium High", "Lincoln WA",
                "Curtis High", "Rogers Puyallup",
            ],
            "Spokane": [
                "Gonzaga Prep", "Lewis & Clark WA", "Mead High WA",
                "University High Spokane", "Ferris High",
                "Central Valley WA", "Mt. Spokane", "Cheney High",
            ],
        },
    },

    # ═══════════════ CALIFORNIA ═══════════════
    "CA": {
        "name": "California",
        "conferences": {
            "LA Prep": [
                "Harvard-Westlake", "Crossroads LA", "Windward",
                "Marlborough", "Archer School", "Polytechnic Pasadena",
                "Loyola High LA", "Brentwood School LA",
            ],
            "LA Private": [
                "Campbell Hall", "Sierra Canyon", "Oaks Christian",
                "Alemany High", "Chaminade Prep CA", "St. Francis Prep CA",
                "Crespi Carmelite", "Notre Dame Sherman Oaks",
                "Bishop Amat", "St. John Bosco",
            ],
            "LA Public": [
                "Gardena Serra", "Long Beach Poly", "St. Bernard's",
                "Narbonne High", "Carson High", "Westchester High",
                "Los Alamitos", "Edison High CA",
                "Lakewood High", "Compton High",
            ],
            "Inland Empire": [
                "Centennial Corona", "Norco High", "Rancho Verde",
                "Roosevelt Eastvale", "King High Riverside",
                "Cajon High", "Aquinas High", "Upland High",
                "Rancho Cucamonga", "Etiwanda High",
            ],
            "NorCal Prep": [
                "Bellarmine CA", "Sacred Heart Prep CA",
                "Crystal Springs Uplands", "Menlo School", "Castilleja",
                "St. Ignatius SF", "Mitty Archbishop", "Presentation High",
            ],
            "NorCal Public": [
                "Palo Alto High", "Gunn High", "Mountain View High CA",
                "Los Gatos High", "Saratoga High", "Leland High",
                "Lynbrook High", "Monta Vista",
            ],
            "East Bay-Valley": [
                "De La Salle CA", "Carondelet", "Monte Vista CA",
                "Amador Valley", "San Ramon Valley", "California High",
                "Dublin High", "Foothill Pleasanton",
                "Granada High", "San Leandro High",
            ],
            "Central Valley": [
                "Clovis North", "Clovis West", "Buchanan High",
                "Edison Fresno", "Bullard High", "San Joaquin Memorial",
                "Central High Fresno", "Bakersfield High",
                "Stockton Lincoln", "St. Mary's Stockton",
            ],
            "Sacramento": [
                "Folsom High", "Granite Bay High", "Del Oro High",
                "Jesuit Sacramento", "Christian Brothers Sac",
                "Sheldon High CA", "Elk Grove High", "Franklin High CA",
                "Oak Ridge High", "Davis Senior High",
            ],
            "Orange County": [
                "Mater Dei", "Servite", "JSerra Catholic",
                "Santa Margarita", "Tesoro High", "San Clemente",
                "Mission Viejo", "El Toro High",
                "St. Margaret's", "Capistrano Valley",
            ],
            "San Diego": [
                "Torrey Pines", "Cathedral Catholic SD", "La Jolla Country Day",
                "Francis Parker SD", "Granite Hills SD", "Helix High",
                "Rancho Bernardo", "Poway High",
                "Eastlake High", "Otay Ranch", "Mira Mesa High",
                "St. Augustine SD", "Madison High SD",
            ],
        },
    },

    # ═══════════════ PACIFIC ═══════════════
    "HI": {
        "name": "Hawaii",
        "conferences": {
            "Interscholastic League": [
                "Punahou School", "Iolani School", "Kamehameha Schools",
                "Mid-Pacific Institute", "St. Louis School HI",
                "Maryknoll School", "Damien Memorial",
                "Kahuku High", "Mililani High", "Campbell High HI",
                "Kapolei High", "Saint Francis HI",
            ],
        },
    },
    "AK": {
        "name": "Alaska",
        "conferences": {
            "Cook Inlet": [
                "East Anchorage", "West Anchorage", "Service High",
                "South Anchorage", "Bartlett High", "Dimond High",
                "Eagle River High", "Chugiak High",
                "Juneau-Douglas", "Thunder Mountain", "Soldotna High",
                "Wasilla High",
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
