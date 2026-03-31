"""
High School League Engine — Season simulation, playoffs, and recruiting pipeline.

Hierarchy: Conference → Division (State) → Region → National
"""

from __future__ import annotations

import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from engine.hs_league_data import (
    REGIONS, STATE_TO_REGION, STATES, HS_MASCOTS,
    HS_OFFENSE_STYLES, HS_DEFENSE_STYLES,
    HS_ROSTER_TEMPLATE, HS_STAT_RANGES, HS_YEAR_ORDER,
)


# ──────────────────────────────────────────────
# HS PLAYER
# ──────────────────────────────────────────────

@dataclass
class HSPlayer:
    """A high school player on a team roster."""
    name: str
    number: int
    position: str
    year: str  # Freshman / Sophomore / Junior / Senior
    speed: int = 30
    stamina: int = 30
    agility: int = 30
    power: int = 30
    awareness: int = 30
    hands: int = 30
    kicking: int = 30
    kick_power: int = 30
    kick_accuracy: int = 30
    lateral_skill: int = 30
    tackling: int = 30
    # Hidden scouting fields
    potential: int = 3
    development: str = "normal"
    hometown: str = ""
    high_school: str = ""
    region: str = ""
    state: str = ""
    # Season stats (accumulated during HS season sim)
    season_yards: int = 0
    season_tds: int = 0
    season_tackles: int = 0
    season_kicks_made: int = 0
    season_games: int = 0

    @property
    def overall(self) -> int:
        weights = {
            "Zeroback": (1.2, 1.0, 1.3, 1.0, 0.5, 1.0, 0.6, 1.4, 0.8, 1.2, 1.2),
            "Viper": (1.4, 1.0, 0.6, 1.3, 0.6, 1.3, 0.7, 1.0, 1.3, 0.4, 0.4),
            "Halfback": (1.2, 1.1, 0.6, 1.2, 0.7, 1.1, 1.1, 1.0, 1.0, 0.5, 0.5),
            "Wingback": (1.3, 1.0, 0.6, 1.2, 0.6, 1.2, 0.8, 0.9, 1.1, 0.4, 0.4),
            "Slotback": (1.2, 1.0, 0.6, 1.3, 0.6, 1.2, 0.9, 1.0, 1.1, 0.4, 0.4),
            "Offensive Line": (0.7, 1.2, 0.5, 0.8, 1.6, 0.7, 1.6, 0.9, 0.6, 0.3, 0.3),
            "Defensive Line": (0.8, 1.1, 0.5, 0.8, 1.5, 0.8, 1.5, 1.0, 0.6, 0.3, 0.3),
            "Keeper": (1.2, 1.0, 0.6, 1.0, 1.3, 1.1, 0.9, 1.3, 0.9, 0.4, 0.4),
        }
        w = weights.get(self.position, (1,) * 11)
        vals = (self.speed, self.stamina, self.kicking, self.lateral_skill,
                self.tackling, self.agility, self.power, self.awareness,
                self.hands, self.kick_power, self.kick_accuracy)
        total_w = sum(w)
        raw = sum(v * wt for v, wt in zip(vals, w)) / total_w
        return max(10, min(99, int(raw)))


# ──────────────────────────────────────────────
# HS TEAM
# ──────────────────────────────────────────────

@dataclass
class HSTeam:
    """A high school team."""
    school_name: str
    mascot: str
    state: str
    conference: str
    offense_style: str = "balanced"
    defense_style: str = "zone"
    players: List[HSPlayer] = field(default_factory=list)
    prestige: int = 50
    wins: int = 0
    losses: int = 0
    points_for: float = 0
    points_against: float = 0
    conf_champ: bool = False
    state_champ: bool = False
    region_champ: bool = False
    national_champ: bool = False

    @property
    def name(self) -> str:
        return self.school_name

    @property
    def record(self) -> str:
        return f"{self.wins}-{self.losses}"

    @property
    def strength(self) -> float:
        if not self.players:
            return 30.0
        return sum(p.overall for p in self.players) / len(self.players)

    @property
    def kicking_strength(self) -> float:
        kickers = [p.kicking for p in self.players if p.position == "Zeroback"]
        return sum(kickers) / max(1, len(kickers)) if kickers else 40.0

    @property
    def seniors(self) -> List[HSPlayer]:
        return [p for p in self.players if p.year == "Senior"]


# ──────────────────────────────────────────────
# HS GAME RESULT
# ──────────────────────────────────────────────

@dataclass
class HSGameResult:
    home: str
    away: str
    home_score: float
    away_score: float
    week: int = 0
    playoff_round: str = ""

    @property
    def winner(self) -> str:
        return self.home if self.home_score > self.away_score else self.away

    @property
    def loser(self) -> str:
        return self.away if self.home_score > self.away_score else self.home


# ──────────────────────────────────────────────
# TEAM GENERATION
# ──────────────────────────────────────────────

def _generate_hs_player(
    position: str, year: str, state: str, school_name: str,
    rng: random.Random,
) -> HSPlayer:
    """Generate a single HS player with year-appropriate stats."""
    from engine.recruiting import _FIRST_NAMES, _LAST_NAMES, _STAR_DISTRIBUTION, _DEV_BY_STARS

    first = rng.choice(_FIRST_NAMES)
    last = rng.choice(_LAST_NAMES)
    lo, hi = HS_STAT_RANGES[year]

    def _stat():
        return rng.randint(lo, hi)

    speed, stamina, agility = _stat(), _stat(), _stat()
    power, awareness, hands = _stat(), _stat(), _stat()
    kicking, kick_power, kick_accuracy = _stat(), _stat(), _stat()
    lateral_skill, tackling = _stat(), _stat()

    # Position boosts
    if position in ("Viper", "Halfback", "Wingback", "Slotback"):
        speed = min(70, speed + rng.randint(2, 5))
        lateral_skill = min(70, lateral_skill + rng.randint(1, 4))
    elif position in ("Offensive Line", "Defensive Line"):
        tackling = min(70, tackling + rng.randint(2, 6))
        power = min(70, power + rng.randint(2, 6))
    elif position == "Zeroback":
        awareness = min(70, awareness + rng.randint(2, 5))
        kicking = min(70, kicking + rng.randint(2, 5))
    elif position == "Keeper":
        tackling = min(70, tackling + rng.randint(2, 5))
        awareness = min(70, awareness + rng.randint(2, 4))

    # Stars and dev trait
    star_vals = list(_STAR_DISTRIBUTION.keys())
    star_wts = list(_STAR_DISTRIBUTION.values())
    stars = rng.choices(star_vals, weights=star_wts, k=1)[0]
    potential = rng.randint(max(1, stars - 1), min(5, stars + 1))
    dev_options, dev_weights = zip(*_DEV_BY_STARS[stars])
    dev = rng.choices(dev_options, weights=dev_weights, k=1)[0]

    region = STATE_TO_REGION.get(state, "midwest")
    number = rng.randint(1, 99)

    return HSPlayer(
        name=f"{first} {last}", number=number, position=position,
        year=year, speed=speed, stamina=stamina, agility=agility,
        power=power, awareness=awareness, hands=hands,
        kicking=kicking, kick_power=kick_power, kick_accuracy=kick_accuracy,
        lateral_skill=lateral_skill, tackling=tackling,
        potential=potential, development=dev,
        hometown=f"{school_name.split()[0]}, {state}",
        high_school=school_name, region=region, state=state,
    )


def generate_hs_team(
    school_name: str, state: str, conference: str,
    rng: random.Random,
) -> HSTeam:
    """Generate a full HS team with 24 players across 4 class years."""
    mascot = rng.choice(HS_MASCOTS)
    offense = rng.choice(HS_OFFENSE_STYLES)
    defense = rng.choice(HS_DEFENSE_STYLES)
    prestige = rng.randint(25, 80)

    years = ["Freshman"] * 6 + ["Sophomore"] * 6 + ["Junior"] * 6 + ["Senior"] * 6
    rng.shuffle(years)

    players = []
    for i, pos in enumerate(HS_ROSTER_TEMPLATE):
        yr = years[i] if i < len(years) else rng.choice(HS_YEAR_ORDER)
        p = _generate_hs_player(pos, yr, state, school_name, rng)
        players.append(p)

    return HSTeam(
        school_name=school_name, mascot=mascot, state=state,
        conference=conference, offense_style=offense,
        defense_style=defense, players=players, prestige=prestige,
    )


# ──────────────────────────────────────────────
# HS LEAGUE
# ──────────────────────────────────────────────

@dataclass
class HSLeague:
    """The full high school league across all states."""
    year: int
    teams: Dict[str, HSTeam] = field(default_factory=dict)
    schedule: List[HSGameResult] = field(default_factory=list)
    conf_champions: Dict[str, str] = field(default_factory=dict)
    state_champions: Dict[str, str] = field(default_factory=dict)
    region_champions: Dict[str, str] = field(default_factory=dict)
    national_champion: str = ""

    @property
    def all_seniors(self) -> List[HSPlayer]:
        seniors = []
        for team in self.teams.values():
            seniors.extend(team.seniors)
        return seniors

    def get_teams_by_state(self, state: str) -> List[HSTeam]:
        return [t for t in self.teams.values() if t.state == state]

    def get_teams_by_conference(self, conf: str) -> List[HSTeam]:
        return [t for t in self.teams.values() if t.conference == conf]

    def get_teams_by_region(self, region: str) -> List[HSTeam]:
        states = REGIONS.get(region, [])
        return [t for t in self.teams.values() if t.state in states]


# ──────────────────────────────────────────────
# LEAGUE CREATION
# ──────────────────────────────────────────────

def create_hs_league(year: int, rng: Optional[random.Random] = None) -> HSLeague:
    """Create the full HS league from all states/conferences."""
    if rng is None:
        rng = random.Random(year)

    league = HSLeague(year=year)

    for state_code, state_data in STATES.items():
        for conf_name, schools in state_data["conferences"].items():
            for school_name in schools:
                key = f"{school_name}_{state_code}"
                team = generate_hs_team(school_name, state_code, conf_name, rng)
                league.teams[key] = team

    return league


# ──────────────────────────────────────────────
# FAST SIM (ultra-light HS game simulation)
# ──────────────────────────────────────────────

def _hs_team_strength(team: HSTeam) -> float:
    if not team.players:
        return 30.0
    avail = [p for p in team.players if p.year in ("Junior", "Senior")]
    if len(avail) < 5:
        avail = team.players
    n = len(avail)
    avg_ovr = sum(p.overall for p in avail) / n
    return min(85, max(15, avg_ovr * 0.7 + team.prestige * 0.3))


def _hs_fast_sim(
    home: HSTeam, away: HSTeam, rng: random.Random,
    week: int = 0, playoff_round: str = "",
) -> HSGameResult:
    """Ultra-fast HS game sim. Returns score + accumulates player stats."""
    home_str = _hs_team_strength(home)
    away_str = _hs_team_strength(away)

    diff = home_str - away_str + 2.0  # slight home advantage
    home_wp = 1.0 / (1.0 + math.exp(-diff / 10.0))
    home_wp = max(0.08, min(0.92, home_wp))

    # Generate scores
    base_pts = 22.0  # HS games score lower than college
    home_pts = max(0, base_pts + (home_str - 50) * 0.5 + rng.gauss(0, 8))
    away_pts = max(0, base_pts + (away_str - 50) * 0.5 + rng.gauss(0, 8))

    # Snap to viperball scoring increments
    home_score = max(0, round(home_pts * 2) / 2)
    away_score = max(0, round(away_pts * 2) / 2)

    # Ensure no ties
    if home_score == away_score:
        if rng.random() < home_wp:
            home_score += 9  # OT touchdown
        else:
            away_score += 9

    # Accumulate basic player stats for seniors (for recruit eval)
    winner = home if home_score > away_score else away
    loser = away if home_score > away_score else home

    for team, scored in [(home, home_score), (away, away_score)]:
        for p in team.players:
            p.season_games += 1
            if p.position in ("Viper", "Halfback", "Wingback", "Slotback", "Zeroback"):
                p.season_yards += rng.randint(5, int(15 + p.speed * 0.3))
                if rng.random() < 0.15 + p.overall * 0.002:
                    p.season_tds += 1
            if p.position in ("Keeper", "Defensive Line", "Offensive Line"):
                p.season_tackles += rng.randint(1, int(3 + p.tackling * 0.1))
            if p.position == "Zeroback" and rng.random() < 0.3:
                p.season_kicks_made += 1

    # Update team records
    if home_score > away_score:
        home.wins += 1
        away.losses += 1
    else:
        away.wins += 1
        home.losses += 1
    home.points_for += home_score
    home.points_against += away_score
    away.points_for += away_score
    away.points_against += home_score

    return HSGameResult(
        home=home.name, away=away.name,
        home_score=home_score, away_score=away_score,
        week=week, playoff_round=playoff_round,
    )


# ──────────────────────────────────────────────
# SCHEDULE + SEASON SIM
# ──────────────────────────────────────────────

def _round_robin_pairs(teams: List[str]) -> List[Tuple[str, str]]:
    """Generate round-robin matchups."""
    n = len(teams)
    if n < 2:
        return []
    if n % 2 == 1:
        teams = teams + ["BYE"]
        n += 1
    pairs = []
    ts = list(teams)
    for r in range(n - 1):
        for i in range(n // 2):
            a, b = ts[i], ts[n - 1 - i]
            if a != "BYE" and b != "BYE":
                pairs.append((a, b))
        ts.insert(1, ts.pop())
    return pairs


def simulate_hs_season(league: HSLeague, rng: Optional[random.Random] = None) -> HSLeague:
    """Run a full HS season: conference play → state → regional → national."""
    if rng is None:
        rng = random.Random(league.year)

    team_lookup = {t.name: t for t in league.teams.values()}

    # ── 1. Conference regular season (round-robin) ──
    week = 1
    all_conferences = set()
    for t in league.teams.values():
        all_conferences.add((t.state, t.conference))

    for state_code, conf_name in sorted(all_conferences):
        conf_teams = [t for t in league.teams.values()
                      if t.state == state_code and t.conference == conf_name]
        names = [t.name for t in conf_teams]
        pairs = _round_robin_pairs(names)

        for i, (h, a) in enumerate(pairs):
            ht, at = team_lookup[h], team_lookup[a]
            result = _hs_fast_sim(ht, at, rng, week=week + i // (len(names) // 2))
            league.schedule.append(result)

    # ── 2. Conference championships (top 2 teams by wins) ──
    week = 100
    for state_code, conf_name in sorted(all_conferences):
        conf_teams = [t for t in league.teams.values()
                      if t.state == state_code and t.conference == conf_name]
        conf_teams.sort(key=lambda t: (-t.wins, -t.points_for))
        if len(conf_teams) >= 2:
            t1, t2 = conf_teams[0], conf_teams[1]
            result = _hs_fast_sim(t1, t2, rng, week=week, playoff_round="conf_final")
            league.schedule.append(result)
            champ = team_lookup[result.winner]
            champ.conf_champ = True
            league.conf_champions[f"{state_code}_{conf_name}"] = result.winner

    # ── 3. State/Division championships ──
    week = 200
    for state_code in STATES:
        state_teams = league.get_teams_by_state(state_code)
        if not state_teams:
            continue
        # Top 4 by record, bracket semifinal → final
        state_teams.sort(key=lambda t: (-t.wins, -t.points_for))
        bracket = state_teams[:min(4, len(state_teams))]
        if len(bracket) >= 4:
            r1 = _hs_fast_sim(bracket[0], bracket[3], rng, week=week, playoff_round="state_semi")
            r2 = _hs_fast_sim(bracket[1], bracket[2], rng, week=week, playoff_round="state_semi")
            league.schedule.extend([r1, r2])
            f1, f2 = team_lookup[r1.winner], team_lookup[r2.winner]
            final = _hs_fast_sim(f1, f2, rng, week=week + 1, playoff_round="state_final")
            league.schedule.append(final)
        elif len(bracket) >= 2:
            final = _hs_fast_sim(bracket[0], bracket[1], rng, week=week + 1, playoff_round="state_final")
            league.schedule.append(final)
        else:
            continue
        champ = team_lookup[final.winner]
        champ.state_champ = True
        league.state_champions[state_code] = final.winner

    # ── 4. Regional championships ──
    week = 300
    for region_name, region_states in REGIONS.items():
        # State champs from this region compete
        regional_contenders = []
        for st in region_states:
            champ_name = league.state_champions.get(st)
            if champ_name and champ_name in team_lookup:
                regional_contenders.append(team_lookup[champ_name])

        if len(regional_contenders) < 2:
            if regional_contenders:
                regional_contenders[0].region_champ = True
                league.region_champions[region_name] = regional_contenders[0].name
            continue

        # Seed by record, run single-elim bracket
        regional_contenders.sort(key=lambda t: (-t.wins, -t.points_for))
        # Pad to power of 2 if needed by giving byes to top seeds
        while len(regional_contenders) > 1:
            next_round = []
            for i in range(0, len(regional_contenders) - 1, 2):
                t1, t2 = regional_contenders[i], regional_contenders[i + 1]
                result = _hs_fast_sim(t1, t2, rng, week=week, playoff_round="regional")
                league.schedule.append(result)
                next_round.append(team_lookup[result.winner])
            if len(regional_contenders) % 2 == 1:
                next_round.append(regional_contenders[-1])
            regional_contenders = next_round
            week += 1

        champ = regional_contenders[0]
        champ.region_champ = True
        league.region_champions[region_name] = champ.name

    # ── 5. National championship bracket ──
    week = 400
    national_contenders = []
    for region_name, champ_name in league.region_champions.items():
        if champ_name in team_lookup:
            national_contenders.append(team_lookup[champ_name])

    if len(national_contenders) >= 2:
        national_contenders.sort(key=lambda t: (-t.wins, -t.points_for))
        while len(national_contenders) > 1:
            next_round = []
            for i in range(0, len(national_contenders) - 1, 2):
                t1, t2 = national_contenders[i], national_contenders[i + 1]
                rd = "national_semi" if len(national_contenders) > 2 else "national_final"
                result = _hs_fast_sim(t1, t2, rng, week=week, playoff_round=rd)
                league.schedule.append(result)
                next_round.append(team_lookup[result.winner])
            if len(national_contenders) % 2 == 1:
                next_round.append(national_contenders[-1])
            national_contenders = next_round
            week += 1

        champ = national_contenders[0]
        champ.national_champ = True
        league.national_champion = champ.name

    return league


# ──────────────────────────────────────────────
# HS → COLLEGE RECRUITING PIPELINE
# ──────────────────────────────────────────────

def graduating_class_to_recruits(league: HSLeague):
    """Convert HS seniors into Recruit objects for college recruiting.

    Returns a list of Recruit objects sorted by star rating.
    """
    from engine.recruiting import Recruit, _pick_region

    recruits = []
    for team in league.teams.values():
        for p in team.seniors:
            rid = f"HS-{league.year}-{team.state}-{len(recruits):04d}"

            # Star rating influenced by performance + overall
            perf_bonus = 0
            if p.season_tds >= 8:
                perf_bonus += 1
            if p.season_yards >= 500:
                perf_bonus += 1
            if team.state_champ:
                perf_bonus += 1

            # Base stars from potential, boosted by performance
            stars = min(5, max(1, p.potential + (1 if perf_bonus >= 2 else 0)))

            recruit = Recruit(
                recruit_id=rid,
                first_name=p.name.split()[0] if " " in p.name else p.name,
                last_name=p.name.split()[-1] if " " in p.name else "Smith",
                position=p.position,
                region=p.region,
                hometown=p.hometown,
                high_school=p.high_school,
                height=f"{5}-{random.randint(4, 11)}",
                weight=random.randint(140, 210),
                stars=stars,
                true_speed=p.speed,
                true_stamina=p.stamina,
                true_agility=p.agility,
                true_power=p.power,
                true_awareness=p.awareness,
                true_hands=p.hands,
                true_kicking=p.kicking,
                true_kick_power=p.kick_power,
                true_kick_accuracy=p.kick_accuracy,
                true_lateral_skill=p.lateral_skill,
                true_tackling=p.tackling,
                true_potential=p.potential,
                true_development=p.development,
            )
            recruits.append(recruit)

    recruits.sort(key=lambda r: (-r.stars, -r.true_overall))
    return recruits


# ──────────────────────────────────────────────
# OFFSEASON: ADVANCE HS PLAYERS
# ──────────────────────────────────────────────

def advance_hs_league(
    league: HSLeague, new_year: int, rng: Optional[random.Random] = None,
) -> HSLeague:
    """Advance the HS league by one year.

    - Seniors graduate (removed — fed to college recruiting)
    - Juniors → Seniors, Sophomores → Juniors, Freshmen → Sophomores
    - New Freshmen generated to fill rosters
    - Team records reset
    - Player stats reset
    - Development applied to returning players
    """
    if rng is None:
        rng = random.Random(new_year)

    new_league = HSLeague(year=new_year)

    for key, team in league.teams.items():
        # Remove seniors, advance years
        returning = []
        for p in team.players:
            if p.year == "Senior":
                continue  # graduated
            idx = HS_YEAR_ORDER.index(p.year)
            p.year = HS_YEAR_ORDER[idx + 1]
            # Apply development
            _apply_hs_player_development(p, rng)
            # Reset season stats
            p.season_yards = 0
            p.season_tds = 0
            p.season_tackles = 0
            p.season_kicks_made = 0
            p.season_games = 0
            returning.append(p)

        # Fill roster with new freshmen
        slots_needed = len(HS_ROSTER_TEMPLATE) - len(returning)
        current_pos = {}
        for p in returning:
            current_pos[p.position] = current_pos.get(p.position, 0) + 1

        template_counts = {}
        for pos in HS_ROSTER_TEMPLATE:
            template_counts[pos] = template_counts.get(pos, 0) + 1

        fill_positions = []
        for pos, target in template_counts.items():
            deficit = target - current_pos.get(pos, 0)
            fill_positions.extend([pos] * max(0, deficit))
        while len(fill_positions) < slots_needed:
            fill_positions.append(rng.choice(HS_ROSTER_TEMPLATE))

        for pos in fill_positions[:slots_needed]:
            p = _generate_hs_player(pos, "Freshman", team.state, team.school_name, rng)
            returning.append(p)

        # Reset team record
        new_team = HSTeam(
            school_name=team.school_name, mascot=team.mascot,
            state=team.state, conference=team.conference,
            offense_style=team.offense_style, defense_style=team.defense_style,
            players=returning, prestige=team.prestige,
        )
        new_league.teams[key] = new_team

    return new_league


def _apply_hs_player_development(player: HSPlayer, rng: random.Random):
    """Apply one year of HS development to a player."""
    dev = player.development
    year = player.year

    # Base gain range by dev trait
    if dev == "quick":
        lo, hi = 1, 4
    elif dev == "late_bloomer":
        lo, hi = (0, 1) if year in ("Sophomore", "Junior") else (2, 5)
    elif dev == "bust":
        lo, hi = -2, 0
    elif dev == "slow":
        lo, hi = 0, 1
    else:  # normal
        lo, hi = 0, 3

    for attr in ("speed", "stamina", "agility", "power", "awareness",
                 "hands", "kicking", "kick_power", "kick_accuracy",
                 "lateral_skill", "tackling"):
        delta = rng.randint(lo, hi)
        old = getattr(player, attr)
        setattr(player, attr, max(10, min(75, old + delta)))


# ──────────────────────────────────────────────
# LEAGUE SUMMARY (for UI / debug)
# ──────────────────────────────────────────────

def league_summary(league: HSLeague) -> dict:
    """Summary stats for display."""
    total_teams = len(league.teams)
    states = set(t.state for t in league.teams.values())
    conferences = set(t.conference for t in league.teams.values())
    total_players = sum(len(t.players) for t in league.teams.values())
    total_seniors = len(league.all_seniors)

    return {
        "year": league.year,
        "total_teams": total_teams,
        "states": len(states),
        "conferences": len(conferences),
        "total_players": total_players,
        "graduating_seniors": total_seniors,
        "games_played": len(league.schedule),
        "state_champions": dict(league.state_champions),
        "region_champions": dict(league.region_champions),
        "national_champion": league.national_champion,
    }
