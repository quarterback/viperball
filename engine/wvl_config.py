"""
Women's Viperball League (WVL) — Galactic Premiership Configuration
====================================================================

64-team, 4-tier pyramid with EPL-style promotion/relegation.

Tier 1 — Galactic Premiership  (18 teams, 34 matches home-and-away)
Tier 2 — Galactic League 1     (20 teams, 38 matches home-and-away)
Tier 3 — Galactic League 2     (13 teams, 24 matches home-and-away)
Tier 4 — Galactic League 3     (13 teams, 24 matches home-and-away)

14 countries: England, Scotland, Wales, Spain, Italy, Germany, France,
Portugal, Netherlands, Turkey, Greece, Finland, Norway, USA.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


# ═══════════════════════════════════════════════════════════════
# TIER CONFIG
# ═══════════════════════════════════════════════════════════════

@dataclass
class WVLTierConfig:
    """Configuration for a single tier of the WVL pyramid."""
    tier_number: int
    tier_name: str
    teams_dir: str
    team_keys: List[str]
    games_per_season: int
    attribute_range: Tuple[int, int]
    franchise_rating_range: Tuple[int, int]

    # Pro/rel rules for the boundary BELOW this tier
    # (e.g., tier 1 config describes the tier1↔tier2 boundary)
    relegate_count: int = 0           # auto-relegated from this tier
    promote_from_below_count: int = 0  # auto-promoted from tier below
    playoff_enabled: bool = False      # promotion/relegation playoff?
    playoff_higher_seed_pos: int = 0   # position in THIS tier that plays playoff
    playoff_lower_seed_pos: int = 0    # position in tier BELOW that plays playoff


# ═══════════════════════════════════════════════════════════════
# TEAM DATA — all 64 clubs
# ═══════════════════════════════════════════════════════════════

@dataclass
class WVLClub:
    """Metadata for a single WVL club."""
    key: str               # filesystem-safe key, e.g., "real_madrid"
    name: str              # display name
    country: str
    city: str
    tier: int              # starting tier (1-4)
    prestige: int          # 0-99
    narrative_tag: str = ""  # optional narrative arc identifier


# Tier 1 — Galactic Premiership (18 teams)
TIER_1_CLUBS = [
    WVLClub("real_madrid", "Real Madrid", "Spain", "Madrid", 1, 97),
    WVLClub("fc_barcelona", "FC Barcelona", "Spain", "Barcelona", 1, 96),
    WVLClub("man_united", "Manchester United", "England", "Manchester", 1, 94),
    WVLClub("liverpool", "Liverpool", "England", "Liverpool", 1, 93),
    WVLClub("bayern_munich", "Bayern Munich", "Germany", "Munich", 1, 95),
    WVLClub("juventus", "Juventus", "Italy", "Turin", 1, 91),
    WVLClub("ac_milan", "AC Milan", "Italy", "Milan", 1, 89),
    WVLClub("psg", "Paris Saint-Germain", "France", "Paris", 1, 92),
    WVLClub("arsenal", "Arsenal", "England", "London", 1, 88),
    WVLClub("chelsea", "Chelsea", "England", "London", 1, 87),
    WVLClub("inter_milan", "Inter Milan", "Italy", "Milan", 1, 88),
    WVLClub("atletico_madrid", "Atletico Madrid", "Spain", "Madrid", 1, 86),
    WVLClub("dortmund", "Borussia Dortmund", "Germany", "Dortmund", 1, 85),
    WVLClub("man_city", "Manchester City", "England", "Manchester", 1, 93),
    WVLClub("tottenham", "Tottenham Hotspur", "England", "London", 1, 83),
    WVLClub("lyon", "Olympique Lyonnais", "France", "Lyon", 1, 80),
    WVLClub("wrexham", "Wrexham", "Wales", "Wrexham", 1, 62, narrative_tag="vanity_project"),
    WVLClub("newcastle", "Newcastle United", "England", "Newcastle", 1, 81),
]

# Tier 2 — Galactic League 1 (20 teams)
TIER_2_CLUBS = [
    WVLClub("as_roma", "AS Roma", "Italy", "Rome", 2, 82),
    WVLClub("napoli", "Napoli", "Italy", "Naples", 2, 83),
    WVLClub("sevilla", "Sevilla", "Spain", "Seville", 2, 79),
    WVLClub("ajax", "Ajax", "Netherlands", "Amsterdam", 2, 81),
    WVLClub("benfica", "Benfica", "Portugal", "Lisbon", 2, 80),
    WVLClub("porto", "Porto", "Portugal", "Porto", 2, 79),
    WVLClub("celtic", "Celtic", "Scotland", "Glasgow", 2, 76),
    WVLClub("rangers", "Rangers", "Scotland", "Glasgow", 2, 75),
    WVLClub("marseille", "Olympique de Marseille", "France", "Marseille", 2, 77),
    WVLClub("monaco", "AS Monaco", "France", "Monaco", 2, 76),
    WVLClub("leverkusen", "Bayer Leverkusen", "Germany", "Leverkusen", 2, 78),
    WVLClub("rb_leipzig", "RB Leipzig", "Germany", "Leipzig", 2, 77),
    WVLClub("villarreal", "Villarreal", "Spain", "Villarreal", 2, 74),
    WVLClub("real_sociedad", "Real Sociedad", "Spain", "San Sebastián", 2, 73),
    WVLClub("lazio", "Lazio", "Italy", "Rome", 2, 76),
    WVLClub("fiorentina", "Fiorentina", "Italy", "Florence", 2, 73),
    WVLClub("sporting_cp", "Sporting CP", "Portugal", "Lisbon", 2, 77),
    WVLClub("psv", "PSV Eindhoven", "Netherlands", "Eindhoven", 2, 74),
    WVLClub("feyenoord", "Feyenoord", "Netherlands", "Rotterdam", 2, 73),
    WVLClub("portland", "Portland Timbers", "USA", "Portland", 2, 65, narrative_tag="american_outpost"),
]

# Tier 3 — Galactic League 2 (13 teams)
TIER_3_CLUBS = [
    WVLClub("west_ham", "West Ham United", "England", "London", 3, 72),
    WVLClub("aston_villa", "Aston Villa", "England", "Birmingham", 3, 73),
    WVLClub("everton", "Everton", "England", "Liverpool", 3, 70, narrative_tag="fallen_giant"),
    WVLClub("leeds", "Leeds United", "England", "Leeds", 3, 71, narrative_tag="fallen_giant"),
    WVLClub("nott_forest", "Nottingham Forest", "England", "Nottingham", 3, 69, narrative_tag="fallen_giant"),
    WVLClub("brighton", "Brighton & Hove Albion", "England", "Brighton", 3, 68),
    WVLClub("swansea", "Swansea City", "Wales", "Swansea", 3, 62),
    WVLClub("hearts", "Heart of Midlothian", "Scotland", "Edinburgh", 3, 63),
    WVLClub("real_betis", "Real Betis", "Spain", "Seville", 3, 71),
    WVLClub("athletic_bilbao", "Athletic Bilbao", "Spain", "Bilbao", 3, 72),
    WVLClub("deportivo", "Deportivo de La Coruña", "Spain", "A Coruña", 3, 60),
    WVLClub("valencia", "Valencia", "Spain", "Valencia", 3, 74),
    WVLClub("atalanta", "Atalanta", "Italy", "Bergamo", 3, 73),
]

# Tier 4 — Galactic League 3 (13 teams)
TIER_4_CLUBS = [
    WVLClub("sassuolo", "Sassuolo", "Italy", "Sassuolo", 4, 58),
    WVLClub("hoffenheim", "TSG Hoffenheim", "Germany", "Sinsheim", 4, 60),
    WVLClub("frankfurt", "Eintracht Frankfurt", "Germany", "Frankfurt", 4, 65),
    WVLClub("lapua", "Lapua Virkiä", "Finland", "Lapua", 4, 40),
    WVLClub("vimpeli", "Vimpelin Veto", "Finland", "Vimpeli", 4, 38, narrative_tag="cinderella"),
    WVLClub("bodo_glimt", "Bodø/Glimt", "Norway", "Bodø", 4, 52, narrative_tag="cinderella"),
    WVLClub("lille", "Lille", "France", "Lille", 4, 63),
    WVLClub("nice", "Nice", "France", "Nice", 4, 62),
    WVLClub("galatasaray", "Galatasaray", "Turkey", "Istanbul", 4, 68),
    WVLClub("fenerbahce", "Fenerbahce", "Turkey", "Istanbul", 4, 67),
    WVLClub("olympiacos", "Olympiacos", "Greece", "Piraeus", 4, 64),
    WVLClub("braga", "Braga", "Portugal", "Braga", 4, 61),
    WVLClub("torino", "Torino", "Italy", "Turin", 4, 60),
]

ALL_CLUBS = TIER_1_CLUBS + TIER_2_CLUBS + TIER_3_CLUBS + TIER_4_CLUBS
CLUBS_BY_KEY = {c.key: c for c in ALL_CLUBS}
CLUBS_BY_TIER = {
    1: TIER_1_CLUBS,
    2: TIER_2_CLUBS,
    3: TIER_3_CLUBS,
    4: TIER_4_CLUBS,
}


# ═══════════════════════════════════════════════════════════════
# TIER CONFIGS
# ═══════════════════════════════════════════════════════════════

GALACTIC_PREMIERSHIP = WVLTierConfig(
    tier_number=1,
    tier_name="Galactic Premiership",
    teams_dir="data/wvl_teams/tier1",
    team_keys=[c.key for c in TIER_1_CLUBS],
    games_per_season=34,
    attribute_range=(70, 97),
    franchise_rating_range=(65, 97),
    relegate_count=3,
    promote_from_below_count=2,
    playoff_enabled=True,
    playoff_higher_seed_pos=16,  # 16th in Tier 1
    playoff_lower_seed_pos=3,    # 3rd in Tier 2
)

GALACTIC_LEAGUE_1 = WVLTierConfig(
    tier_number=2,
    tier_name="Galactic League 1",
    teams_dir="data/wvl_teams/tier2",
    team_keys=[c.key for c in TIER_2_CLUBS],
    games_per_season=38,
    attribute_range=(62, 90),
    franchise_rating_range=(55, 88),
    relegate_count=3,
    promote_from_below_count=2,
    playoff_enabled=True,
    playoff_higher_seed_pos=18,  # 18th in Tier 2
    playoff_lower_seed_pos=3,    # 3rd in Tier 3
)

GALACTIC_LEAGUE_2 = WVLTierConfig(
    tier_number=3,
    tier_name="Galactic League 2",
    teams_dir="data/wvl_teams/tier3",
    team_keys=[c.key for c in TIER_3_CLUBS],
    games_per_season=24,
    attribute_range=(55, 85),
    franchise_rating_range=(45, 80),
    relegate_count=2,
    promote_from_below_count=2,
    playoff_enabled=False,
)

GALACTIC_LEAGUE_3 = WVLTierConfig(
    tier_number=4,
    tier_name="Galactic League 3",
    teams_dir="data/wvl_teams/tier4",
    team_keys=[c.key for c in TIER_4_CLUBS],
    games_per_season=24,
    attribute_range=(48, 78),
    franchise_rating_range=(35, 72),
    # Tier 4 is the bottom — no relegation below
    relegate_count=0,
    promote_from_below_count=0,
    playoff_enabled=False,
)

ALL_WVL_TIERS = [GALACTIC_PREMIERSHIP, GALACTIC_LEAGUE_1, GALACTIC_LEAGUE_2, GALACTIC_LEAGUE_3]
TIER_BY_NUMBER = {t.tier_number: t for t in ALL_WVL_TIERS}


# ═══════════════════════════════════════════════════════════════
# RIVALRIES
# ═══════════════════════════════════════════════════════════════

RIVALRIES: List[Dict] = [
    {"name": "El Clásico", "teams": ["real_madrid", "fc_barcelona"]},
    {"name": "English Triangle", "teams": ["man_united", "liverpool", "man_city"]},
    {"name": "Derby della Madonnina", "teams": ["ac_milan", "inter_milan"]},
    {"name": "North London Derby", "teams": ["arsenal", "tottenham"]},
    {"name": "Old Firm", "teams": ["celtic", "rangers"]},
    {"name": "Scottish Triangle", "teams": ["celtic", "rangers", "hearts"]},
    {"name": "Italian Rivalry", "teams": ["juventus", "napoli"]},
    {"name": "Eredivisie Triangle", "teams": ["ajax", "feyenoord", "psv"]},
    {"name": "Portuguese Big Three", "teams": ["benfica", "porto", "sporting_cp"]},
    {"name": "Turkish Derby", "teams": ["galatasaray", "fenerbahce"]},
    {"name": "Der Klassiker", "teams": ["bayern_munich", "dortmund"]},
    {"name": "Olympique Derby", "teams": ["lyon", "marseille"]},
    {"name": "Ostrobothnian Derby", "teams": ["lapua", "vimpeli"]},
]


def get_rival_teams(team_key: str) -> List[str]:
    """Return all rival team keys for a given team."""
    rivals = []
    for r in RIVALRIES:
        if team_key in r["teams"]:
            rivals.extend(k for k in r["teams"] if k != team_key)
    return list(set(rivals))


def is_rivalry_match(team_a: str, team_b: str) -> Optional[str]:
    """If teams are rivals, return the rivalry name. Otherwise None."""
    for r in RIVALRIES:
        if team_a in r["teams"] and team_b in r["teams"]:
            return r["name"]
    return None


# ═══════════════════════════════════════════════════════════════
# COUNTRY → PLAY STYLE MAPPING
# ═══════════════════════════════════════════════════════════════
# Maps country football culture to viperball offense/defense style tendencies

COUNTRY_STYLE_TENDENCIES: Dict[str, Dict] = {
    "Spain": {
        "offense_styles": ["lateral_spread", "ball_control", "slick_n_slide"],
        "defense_styles": ["shadow", "drift"],
        "st_schemes": ["aces", "lightning_returns"],
    },
    "England": {
        "offense_styles": ["ground_pound", "chain_gang", "boot_raid"],
        "defense_styles": ["fortress", "blitz_pack"],
        "st_schemes": ["iron_curtain", "block_party"],
    },
    "Italy": {
        "offense_styles": ["ball_control", "chain_gang", "ground_pound"],
        "defense_styles": ["lockdown", "fortress", "shadow"],
        "st_schemes": ["iron_curtain", "aces"],
    },
    "Germany": {
        "offense_styles": ["stampede", "ground_pound", "boot_raid"],
        "defense_styles": ["blitz_pack", "swarm", "predator"],
        "st_schemes": ["block_party", "iron_curtain"],
    },
    "France": {
        "offense_styles": ["slick_n_slide", "lateral_spread", "ghost"],
        "defense_styles": ["drift", "chaos", "shadow"],
        "st_schemes": ["lightning_returns", "chaos_unit"],
    },
    "Portugal": {
        "offense_styles": ["lateral_spread", "slick_n_slide", "boot_raid"],
        "defense_styles": ["shadow", "drift"],
        "st_schemes": ["lightning_returns", "aces"],
    },
    "Netherlands": {
        "offense_styles": ["lateral_spread", "ghost", "slick_n_slide"],
        "defense_styles": ["swarm", "predator"],
        "st_schemes": ["lightning_returns", "chaos_unit"],
    },
    "Scotland": {
        "offense_styles": ["ground_pound", "stampede", "chain_gang"],
        "defense_styles": ["fortress", "blitz_pack"],
        "st_schemes": ["iron_curtain", "block_party"],
    },
    "Wales": {
        "offense_styles": ["boot_raid", "chain_gang", "ground_pound"],
        "defense_styles": ["fortress", "blitz_pack"],
        "st_schemes": ["iron_curtain", "aces"],
    },
    "Turkey": {
        "offense_styles": ["stampede", "shock_and_awe", "boot_raid"],
        "defense_styles": ["blitz_pack", "chaos"],
        "st_schemes": ["chaos_unit", "block_party"],
    },
    "Greece": {
        "offense_styles": ["ball_control", "chain_gang", "ground_pound"],
        "defense_styles": ["lockdown", "fortress"],
        "st_schemes": ["iron_curtain", "aces"],
    },
    "Finland": {
        "offense_styles": ["ghost", "lateral_spread", "balanced"],
        "defense_styles": ["drift", "swarm"],
        "st_schemes": ["chaos_unit", "lightning_returns"],
    },
    "Norway": {
        "offense_styles": ["stampede", "boot_raid", "ghost"],
        "defense_styles": ["predator", "swarm"],
        "st_schemes": ["lightning_returns", "chaos_unit"],
    },
    "USA": {
        "offense_styles": ["shock_and_awe", "lateral_spread", "stampede"],
        "defense_styles": ["blitz_pack", "predator"],
        "st_schemes": ["lightning_returns", "block_party"],
    },
}


def get_default_tier_assignments() -> Dict[str, int]:
    """Return initial team→tier mapping (key → tier_number)."""
    return {c.key: c.tier for c in ALL_CLUBS}
