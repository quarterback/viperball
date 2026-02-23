"""
Viperball Coaching Portal — NRMP-Style Mutual Matching

A "coaching portal" where assistant coaches (OC, DC, STC) can be pursued by
teams that need them, and where fired/expired-contract coaches seek new jobs.

How it works (simplified Gale-Shapley / medical-school matching):

1. **Portal opens** after each season:
   - Coaches whose contracts expired enter the portal.
   - Fired coaches enter the portal.
   - Assistants with ``wants_hc=True`` can be pursued for HC openings.
   - A pool of generated free-agent coaches is added.

2. **Teams rank coaches** (1-5 per vacancy) based on:
   - Coach overall rating (weighted by role-relevant attributes)
   - Coach classification fit for the team's needs
   - Development rating (the "player dev skill")

3. **Coaches rank teams** (1-5) based on:
   - Player talent (average overall of the roster)
   - Best 3 players in the coach's area (OC→offense, DC→defense, STC→ST)
   - Team prestige
   - Conference strength (avg prestige of conference opponents)
   - Alumni bonus (coach.alma_mater == team_name → +15 pts)

4. **Stable matching** runs:
   - Team-proposing Gale-Shapley — teams propose to their top-ranked
     coaches in order; coaches tentatively accept their best offer and
     reject others; rejected teams propose to their next choice.
   - Produces a stable assignment where no team-coach pair would both
     prefer each other over their current match.

5. **HC Preferential**: Assistants with ``wants_hc=True`` appear in
   HC vacancy pools and get a ranking boost when a team is looking for
   an HC.  They will leave their current team if matched as HC.

Usage (dynasty):
    from engine.coaching_portal import (
        CoachingPortal, populate_coaching_portal,
        run_coaching_match,
    )

    portal = CoachingPortal(year=2027)
    populate_coaching_portal(
        portal, coaching_staffs, team_records, team_prestige,
        team_rosters, conferences, rng=rng,
    )
    results = run_coaching_match(
        portal, team_prestige, team_rosters, conferences, rng=rng,
    )
    # results: Dict[team_name, Dict[role, CoachCard]]
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from engine.coaching import (
    CoachCard,
    CoachContract,
    ROLES,
    generate_coach_card,
    calculate_coach_salary,
    compute_hc_ambition,
    try_hc_contract_extension,
    get_acceptable_roles,
)


# ──────────────────────────────────────────────
# PORTAL ENTRY
# ──────────────────────────────────────────────

PORTAL_REASONS = (
    "contract_expired",
    "fired",
    "seeking_hc",
    "mutual_parting",
    "free_agent",
)

# Position groups for area-of-interest scoring
_OFFENSE_POSITIONS = {"Zeroback", "Halfback", "Wingback", "Slotback", "Viper", "Offensive Line"}
_DEFENSE_POSITIONS = {"Defensive Line", "Keeper"}
_ST_POSITIONS = {"Keeper"}  # kicking duties overlap


@dataclass
class CoachingPortalEntry:
    """A single coach available in the coaching portal."""

    coach: CoachCard
    origin_team: str
    reason: str                      # one of PORTAL_REASONS
    year_entered: int
    seeking_roles: List[str] = field(default_factory=list)  # roles they'll accept

    # Matching state
    matched_to: Optional[str] = None       # team_name once matched
    matched_role: Optional[str] = None     # role once matched

    @property
    def coach_id(self) -> str:
        return self.coach.coach_id

    @property
    def name(self) -> str:
        return self.coach.full_name

    def get_summary(self) -> dict:
        return {
            "name": self.name,
            "coach_id": self.coach_id,
            "role": self.coach.role,
            "overall": self.coach.overall,
            "classification": self.coach.classification_label,
            "development": self.coach.development,
            "origin_team": self.origin_team,
            "reason": self.reason,
            "seeking_roles": self.seeking_roles,
            "wants_hc": self.coach.wants_hc,
            "matched_to": self.matched_to,
            "ambition": compute_hc_ambition(self.coach) if self.coach.role == "head_coach" else None,
            "coaching_tree": self.coach.coaching_tree,
        }


# ──────────────────────────────────────────────
# COACHING PORTAL
# ──────────────────────────────────────────────

@dataclass
class CoachingPortal:
    """
    The coaching portal for a single offseason.

    Holds all available coaches and team vacancies, then runs
    NRMP-style matching to fill positions.
    """

    year: int
    entries: List[CoachingPortalEntry] = field(default_factory=list)
    resolved: bool = False

    # Team vacancies: team_name -> list of role strings that need filling
    vacancies: Dict[str, List[str]] = field(default_factory=dict)

    # Completed hires
    hires: List[dict] = field(default_factory=list)

    def add_entry(self, entry: CoachingPortalEntry) -> None:
        self.entries.append(entry)

    def add_vacancy(self, team_name: str, role: str) -> None:
        self.vacancies.setdefault(team_name, []).append(role)

    def get_available(self) -> List[CoachingPortalEntry]:
        """Coaches not yet matched."""
        return [e for e in self.entries if e.matched_to is None]

    def get_by_role(self, role: str) -> List[CoachingPortalEntry]:
        """Coaches who will accept the given role."""
        return [
            e for e in self.get_available()
            if role in e.seeking_roles
        ]

    def get_summary(self) -> dict:
        return {
            "year": self.year,
            "total_entries": len(self.entries),
            "available": len(self.get_available()),
            "vacancies": {t: list(roles) for t, roles in self.vacancies.items()},
            "hires": self.hires,
            "resolved": self.resolved,
            "top_available": [
                e.get_summary()
                for e in sorted(self.get_available(),
                                key=lambda e: e.coach.overall, reverse=True)[:5]
            ],
        }


# ──────────────────────────────────────────────
# POPULATE PORTAL
# ──────────────────────────────────────────────

def populate_coaching_portal(
    portal: CoachingPortal,
    coaching_staffs: Dict[str, Dict[str, CoachCard]],
    team_records: Dict[str, Tuple[int, int]],
    team_prestige: Dict[str, int],
    fired_roles: Optional[Dict[str, List[str]]] = None,
    human_team: str = "",
    rng: Optional[random.Random] = None,
) -> None:
    """
    Populate the coaching portal with available coaches.

    Sources:
    1. Fired coaches (from fired_roles) — any role.
    2. Head coaches whose contracts expired AND whose ambition exceeds
       their current team's prestige (they want a bigger job).
       If their ambition fits the current program, they get an extension
       instead (contract parlay).
    3. Non-HC coaches whose contracts expired — 50% re-sign, 50% portal.
    4. Assistants with wants_hc who have offers from HC-seeking teams.
    5. Generated free agents to fill the pool.

    Args:
        portal:           CoachingPortal to populate.
        coaching_staffs:  Dict of team_name -> {role -> CoachCard}.
        team_records:     Dict of team_name -> (wins, losses).
        team_prestige:    Dict of team_name -> prestige 0-100.
        fired_roles:      Dict of team_name -> [role] that were fired.
        human_team:       Human team name (excluded from auto-vacancies).
        rng:              Seeded Random.
    """
    if rng is None:
        rng = random.Random()

    if fired_roles is None:
        fired_roles = {}

    all_team_names = list(coaching_staffs.keys())

    # ── 1. Expired contracts & fired coaches ──
    for team_name, staff in coaching_staffs.items():
        for role, card in staff.items():
            # Skip human team (they manage their own staff)
            if team_name == human_team:
                continue

            reason = None
            if team_name in fired_roles and role in fired_roles[team_name]:
                reason = "fired"
            elif card.contract_years_remaining <= 0:
                if role == "head_coach":
                    # HC departure: only leave if ambition > team prestige.
                    # Otherwise they parlay their success into an extension.
                    tw, tl = team_records.get(team_name, (5, 5))
                    tp = team_prestige.get(team_name, 50)
                    extended = try_hc_contract_extension(
                        card, tp, tw, tl, portal.year, rng=rng,
                    )
                    if not extended:
                        reason = "contract_expired"
                else:
                    # Non-HC: 50% chance they re-sign, 50% hit portal
                    if rng.random() < 0.50:
                        reason = "contract_expired"

            if reason is not None:
                # Determine what roles they'll accept.
                # Roles are fluid: HCs can take coordinator jobs and
                # coordinators can seek HC positions.
                seeking = get_acceptable_roles(card)
                # Coordinators also consider adjacent coordinator roles
                if card.role in ("oc", "dc", "stc"):
                    for r in ("oc", "dc", "stc"):
                        if r not in seeking:
                            if rng.random() < 0.30:
                                seeking.append(r)

                entry = CoachingPortalEntry(
                    coach=card,
                    origin_team=team_name,
                    reason=reason,
                    year_entered=portal.year,
                    seeking_roles=seeking,
                )
                portal.add_entry(entry)

                # Create vacancy
                portal.add_vacancy(team_name, role)

    # ── 2. HC-aspiring assistants who are still under contract ──
    # These coaches don't leave automatically but are available if
    # a team offers them an HC position.  The HC meter determines
    # readiness: 75+ = wants_hc, 90+ = "hot name".
    for team_name, staff in coaching_staffs.items():
        if team_name == human_team:
            continue
        for role, card in staff.items():
            if role == "head_coach":
                continue
            if not card.wants_hc and card.hc_meter < 75:
                continue
            # Already in portal?
            if any(e.coach_id == card.coach_id for e in portal.entries):
                continue
            # HC meter 90+ = hot name, always enters pool (if overall ok)
            # HC meter 75-89 = wants it, needs overall 65+ and 30% chance
            if card.hc_meter >= 90 and card.overall >= 60:
                entry = CoachingPortalEntry(
                    coach=card,
                    origin_team=team_name,
                    reason="seeking_hc",
                    year_entered=portal.year,
                    seeking_roles=get_acceptable_roles(card),
                )
                portal.add_entry(entry)
            elif card.overall >= 65 and rng.random() < 0.30:
                entry = CoachingPortalEntry(
                    coach=card,
                    origin_team=team_name,
                    reason="seeking_hc",
                    year_entered=portal.year,
                    seeking_roles=get_acceptable_roles(card),
                )
                portal.add_entry(entry)
                # Note: no vacancy created — their team keeps them unless matched

    # ── 3. Generated free agents ──
    # Ensure the portal has enough coaches to fill vacancies
    total_vacancies = sum(len(roles) for roles in portal.vacancies.values())
    pool_target = max(15, total_vacancies * 2)
    current_count = len(portal.entries)
    to_generate = max(0, pool_target - current_count)

    for _ in range(to_generate):
        role = rng.choice(["head_coach", "oc", "dc", "stc"])
        card = generate_coach_card(
            role=role,
            team_name="",
            prestige=rng.randint(20, 70),
            year=portal.year,
            rng=rng,
        )
        # Free agents will consider any compatible role (roles are fluid)
        seeking = get_acceptable_roles(card)

        # Give free agents a random alma mater from the league
        if all_team_names and rng.random() < 0.35:
            card.alma_mater = rng.choice(all_team_names)

        entry = CoachingPortalEntry(
            coach=card,
            origin_team="",
            reason="free_agent",
            year_entered=portal.year,
            seeking_roles=seeking,
        )
        portal.add_entry(entry)


# ──────────────────────────────────────────────
# SCORING: HOW TEAMS RANK COACHES
# ──────────────────────────────────────────────

def _team_score_coach(
    coach: CoachCard,
    role: str,
    team_prestige: int,
    rng: random.Random,
) -> float:
    """
    How a team scores a coach candidate for a given role.

    Higher is better.  Components:
    - Overall rating (weight: 40%)
    - Role-relevant attribute emphasis (weight: 30%)
    - Development rating — the player dev skill (weight: 20%)
    - Classification fit bonus (weight: 10%)
    """
    # Overall
    overall_score = coach.overall

    # Role-relevant emphasis
    if role == "head_coach":
        role_score = (coach.leadership * 0.35
                      + coach.instincts * 0.30
                      + coach.composure * 0.20
                      + coach.recruiting * 0.15)
    elif role == "oc":
        role_score = (coach.instincts * 0.35
                      + coach.development * 0.25
                      + coach.rotations * 0.20
                      + coach.composure * 0.20)
    elif role == "dc":
        role_score = (coach.instincts * 0.40
                      + coach.rotations * 0.25
                      + coach.composure * 0.20
                      + coach.leadership * 0.15)
    else:  # stc
        role_score = (coach.rotations * 0.35
                      + coach.composure * 0.25
                      + coach.instincts * 0.20
                      + coach.development * 0.20)

    # Player development skill
    dev_score = coach.development

    # Classification fit bonus
    cls_bonus = 0
    if role == "head_coach" and coach.classification in ("motivator", "gameday_manager"):
        cls_bonus = 8
    elif role == "oc" and coach.classification == "scheme_master":
        cls_bonus = 8
    elif role == "dc" and coach.classification == "disciplinarian":
        cls_bonus = 8
    elif role == "stc" and coach.classification in ("disciplinarian", "scheme_master"):
        cls_bonus = 5

    # Postseason pedigree bonus: teams value HCs with playoff/championship success
    pedigree = 0
    if role == "head_coach":
        pedigree += coach.conference_titles * 2
        pedigree += coach.playoff_wins * 1.5
        pedigree += coach.championship_appearances * 3
        pedigree += coach.championships * 5

    # HC meter "hot name" bonus: coordinators with 90+ meter are in-demand
    hot_name_bonus = 0
    if role == "head_coach" and coach.role != "head_coach":
        if coach.hc_meter >= 90:
            hot_name_bonus = 8
        elif coach.hc_meter >= 75:
            hot_name_bonus = 4

    # Noise
    noise = rng.uniform(-4, 4)

    return (
        overall_score * 0.40
        + role_score * 0.30
        + dev_score * 0.20
        + cls_bonus
        + pedigree
        + hot_name_bonus
        + noise
    )


# ──────────────────────────────────────────────
# SCORING: HOW COACHES RANK TEAMS
# ──────────────────────────────────────────────

def _get_area_positions(role: str) -> set:
    """Which player positions a coach cares about for area scoring."""
    if role in ("oc", "head_coach"):
        return _OFFENSE_POSITIONS
    elif role == "dc":
        return _DEFENSE_POSITIONS
    else:
        return _ST_POSITIONS


def _coach_score_team(
    coach: CoachCard,
    team_name: str,
    role: str,
    team_prestige: int,
    roster_overalls: List[int],
    area_overalls: List[int],
    conference_strength: float,
    rng: random.Random,
) -> float:
    """
    How a coach scores a team opportunity.

    Higher is better.  Components (the 5 criteria):
    1. Player talent — average overall of entire roster        (25%)
    2. Best 3 in area — avg of top 3 players at coach's       (20%)
       position group (OC→offense, DC→defense, STC→ST)
    3. Team prestige                                           (25%)
    4. Conference strength — avg prestige of conf opponents    (15%)
    5. Alumni bonus — coach.alma_mater == team_name            (flat +15)

    Plus: HC promotion bonus for wants_hc coaches getting HC   (flat +12)
    """
    # 1. Player talent
    talent_score = sum(roster_overalls) / max(1, len(roster_overalls)) if roster_overalls else 65

    # 2. Best 3 in area
    sorted_area = sorted(area_overalls, reverse=True)
    top3 = sorted_area[:3] if len(sorted_area) >= 3 else sorted_area
    area_score = sum(top3) / max(1, len(top3)) if top3 else 60

    # 3. Prestige
    prestige_score = team_prestige

    # 4. Conference strength
    conf_score = conference_strength

    # 5. Alumni bonus
    alumni_bonus = 15 if coach.alma_mater == team_name else 0

    # HC promotion bonus
    hc_bonus = 12 if (role == "head_coach" and coach.wants_hc
                      and coach.role != "head_coach") else 0

    # HC ambition: successful coaches gravitate toward programs that
    # match their ambition level.  They penalise teams far below their
    # perceived worth and slightly prefer teams slightly above it.
    ambition_bonus = 0.0
    if coach.role == "head_coach" or (role == "head_coach" and coach.wants_hc):
        ambition = compute_hc_ambition(coach)
        gap = team_prestige - ambition
        # Positive gap = program prestige exceeds ambition → attractive
        # Negative gap = program prestige below ambition → penalty
        ambition_bonus = max(-15, min(10, gap * 0.3))

    noise = rng.uniform(-5, 5)

    return (
        talent_score * 0.25
        + area_score * 0.20
        + prestige_score * 0.25
        + conf_score * 0.15
        + alumni_bonus
        + hc_bonus
        + ambition_bonus
        + noise
    )


# ──────────────────────────────────────────────
# NRMP-STYLE STABLE MATCHING
# ──────────────────────────────────────────────

def _build_preference_lists(
    portal: CoachingPortal,
    team_prestige: Dict[str, int],
    team_rosters: Optional[Dict[str, list]] = None,
    conferences: Optional[Dict[str, List[str]]] = None,
    max_rank: int = 5,
    rng: Optional[random.Random] = None,
) -> Tuple[
    Dict[Tuple[str, str], List[str]],  # team_prefs: (team, role) -> [coach_ids]
    Dict[str, Dict[Tuple[str, str], float]],  # coach_prefs: coach_id -> {(team, role): score}
]:
    """
    Build mutual preference lists for all vacancies and available coaches.

    Returns:
        team_prefs:  For each (team, role) vacancy, ranked list of coach_ids.
        coach_prefs: For each coach_id, dict of (team, role) -> preference score.
    """
    if rng is None:
        rng = random.Random()

    # Pre-compute roster data
    roster_data: Dict[str, Tuple[List[int], Dict[str, List[int]]]] = {}
    if team_rosters:
        for tn, roster in team_rosters.items():
            all_ovrs = []
            area_ovrs: Dict[str, List[int]] = {}
            for p in roster:
                ovr = getattr(p, "overall", 70)
                pos = getattr(p, "position", "")
                all_ovrs.append(ovr)
                # Categorize by area
                if pos in _OFFENSE_POSITIONS:
                    area_ovrs.setdefault("offense", []).append(ovr)
                if pos in _DEFENSE_POSITIONS:
                    area_ovrs.setdefault("defense", []).append(ovr)
                if pos in _ST_POSITIONS:
                    area_ovrs.setdefault("st", []).append(ovr)
            roster_data[tn] = (all_ovrs, area_ovrs)

    # Pre-compute conference strength
    conf_strength: Dict[str, float] = {}
    if conferences:
        for conf_name, teams in conferences.items():
            avg_p = sum(team_prestige.get(t, 50) for t in teams) / max(1, len(teams))
            for t in teams:
                conf_strength[t] = avg_p

    # Build team preference lists
    team_prefs: Dict[Tuple[str, str], List[str]] = {}
    for team_name, roles in portal.vacancies.items():
        for role in roles:
            candidates = portal.get_by_role(role)
            # Score each candidate
            scored: List[Tuple[float, str]] = []
            for entry in candidates:
                score = _team_score_coach(
                    entry.coach, role,
                    team_prestige.get(team_name, 50),
                    rng,
                )
                scored.append((score, entry.coach_id))
            scored.sort(key=lambda x: x[0], reverse=True)
            team_prefs[(team_name, role)] = [cid for _, cid in scored[:max_rank]]

    # Build coach preference lists
    coach_prefs: Dict[str, Dict[Tuple[str, str], float]] = {}
    for entry in portal.entries:
        if entry.matched_to is not None:
            continue
        prefs: Dict[Tuple[str, str], float] = {}
        for team_name, roles in portal.vacancies.items():
            for role in roles:
                if role not in entry.seeking_roles:
                    continue
                # Get roster data
                all_ovrs, area_ovrs = roster_data.get(team_name, ([], {}))
                role_area = "offense" if role in ("oc", "head_coach") else (
                    "defense" if role == "dc" else "st"
                )
                area_list = area_ovrs.get(role_area, [])

                score = _coach_score_team(
                    entry.coach, team_name, role,
                    team_prestige.get(team_name, 50),
                    all_ovrs, area_list,
                    conf_strength.get(team_name, 50),
                    rng,
                )
                prefs[(team_name, role)] = score

        # Rank: top max_rank preferences
        sorted_prefs = sorted(prefs.items(), key=lambda x: x[1], reverse=True)
        coach_prefs[entry.coach_id] = {
            k: v for k, v in sorted_prefs[:max_rank]
        }

    return team_prefs, coach_prefs


def _gale_shapley(
    team_prefs: Dict[Tuple[str, str], List[str]],
    coach_prefs: Dict[str, Dict[Tuple[str, str], float]],
) -> Dict[Tuple[str, str], str]:
    """
    Run team-proposing Gale-Shapley stable matching.

    Args:
        team_prefs:  (team, role) -> ranked list of coach_ids (best first).
        coach_prefs: coach_id -> {(team, role): preference_score}.

    Returns:
        Dict of (team, role) -> matched coach_id.
        Unmatched vacancies are omitted.
    """
    # Track proposal index for each vacancy
    proposal_idx: Dict[Tuple[str, str], int] = {
        key: 0 for key in team_prefs
    }

    # Current matches: coach_id -> (team, role) they're tentatively matched to
    coach_match: Dict[str, Tuple[str, str]] = {}
    # Vacancy match: (team, role) -> coach_id
    vacancy_match: Dict[Tuple[str, str], str] = {}

    # Free vacancies (not yet matched)
    free_vacancies = set(team_prefs.keys())

    max_iterations = len(team_prefs) * 20  # safety limit
    iterations = 0

    while free_vacancies and iterations < max_iterations:
        iterations += 1

        # Pick a free vacancy
        vacancy = next(iter(free_vacancies))
        prefs = team_prefs.get(vacancy, [])
        idx = proposal_idx[vacancy]

        if idx >= len(prefs):
            # No more candidates to propose to
            free_vacancies.discard(vacancy)
            continue

        # Propose to the next candidate
        coach_id = prefs[idx]
        proposal_idx[vacancy] = idx + 1

        # Does this coach have preferences that include this vacancy?
        coach_pref_scores = coach_prefs.get(coach_id, {})
        if vacancy not in coach_pref_scores:
            # Coach doesn't want this role/team — skip
            continue

        current_match = coach_match.get(coach_id)

        if current_match is None:
            # Coach is free — accept
            coach_match[coach_id] = vacancy
            vacancy_match[vacancy] = coach_id
            free_vacancies.discard(vacancy)
        else:
            # Coach is already matched — compare
            current_score = coach_pref_scores.get(current_match, -999)
            new_score = coach_pref_scores.get(vacancy, -999)

            if new_score > current_score:
                # Coach prefers new vacancy — switch
                old_vacancy = current_match
                del vacancy_match[old_vacancy]
                free_vacancies.add(old_vacancy)  # old vacancy is free again

                coach_match[coach_id] = vacancy
                vacancy_match[vacancy] = coach_id
                free_vacancies.discard(vacancy)
            # else: coach rejects, vacancy stays free and proposes next

    return vacancy_match


# ──────────────────────────────────────────────
# RUN COACHING MATCH (PUBLIC API)
# ──────────────────────────────────────────────

def run_coaching_match(
    portal: CoachingPortal,
    coaching_staffs: Dict[str, Dict[str, CoachCard]],
    team_prestige: Dict[str, int],
    team_rosters: Optional[Dict[str, list]] = None,
    conferences: Optional[Dict[str, List[str]]] = None,
    year: int = 2026,
    rng: Optional[random.Random] = None,
) -> Dict[str, Dict[str, CoachCard]]:
    """
    Run the full coaching portal matching cycle.

    1. Builds mutual preference lists.
    2. Runs Gale-Shapley matching.
    3. Creates contracts for matched coaches.
    4. Updates coaching_staffs in-place.
    5. Fills any remaining vacancies with generated coaches.

    Args:
        portal:          Populated CoachingPortal.
        coaching_staffs: Dict of team_name -> {role -> CoachCard}. Modified in-place.
        team_prestige:   Dict of team_name -> prestige 0-100.
        team_rosters:    Optional dict of team_name -> list of player objects.
        conferences:     Optional dict of conf_name -> list of team_names.
        year:            Current dynasty year.
        rng:             Seeded Random.

    Returns:
        Dict of team_name -> {role -> CoachCard} for all changes made.
    """
    if rng is None:
        rng = random.Random()

    if not portal.vacancies:
        portal.resolved = True
        return {}

    # Build preference lists
    team_prefs, coach_prefs = _build_preference_lists(
        portal, team_prestige, team_rosters, conferences,
        max_rank=5, rng=rng,
    )

    # Run matching
    matches = _gale_shapley(team_prefs, coach_prefs)

    # Build coach lookup
    coach_lookup: Dict[str, CoachingPortalEntry] = {
        e.coach_id: e for e in portal.entries
    }

    changes: Dict[str, Dict[str, CoachCard]] = {}

    for (team_name, role), coach_id in matches.items():
        entry = coach_lookup.get(coach_id)
        if entry is None:
            continue

        coach = entry.coach
        # Set up the new contract
        contract_years = rng.randint(2, 4) if role != "head_coach" else rng.randint(3, 5)
        salary = calculate_coach_salary(coach, rng=rng)

        coach.team_name = team_name
        coach.role = role
        coach.contract_salary = salary
        coach.contract_years_remaining = contract_years
        coach.contract_buyout = int(salary * contract_years * 0.5)
        coach.year_signed = year

        # Update the staff
        coaching_staffs.setdefault(team_name, {})[role] = coach
        changes.setdefault(team_name, {})[role] = coach

        # Mark entry as matched
        entry.matched_to = team_name
        entry.matched_role = role

        # If this coach left another team (seeking_hc or poaching), create
        # a vacancy there too (handled by the caller in dynasty.py)
        portal.hires.append({
            "coach_name": coach.full_name,
            "coach_id": coach_id,
            "from_team": entry.origin_team,
            "to_team": team_name,
            "role": role,
            "reason": entry.reason,
            "salary": salary,
            "years": contract_years,
            "development": coach.development,
            "overall": coach.overall,
        })

    # Fill remaining vacancies with generated coaches
    filled_vacancies = set(matches.keys())
    for team_name, roles in portal.vacancies.items():
        for role in roles:
            if (team_name, role) in filled_vacancies:
                continue
            # Generate a fallback coach
            prestige = team_prestige.get(team_name, 40)
            fill = generate_coach_card(
                role=role,
                team_name=team_name,
                prestige=max(20, prestige - 15),  # slightly below team level
                year=year,
                rng=rng,
            )
            fill.contract_years_remaining = rng.randint(1, 3)
            coaching_staffs.setdefault(team_name, {})[role] = fill
            changes.setdefault(team_name, {})[role] = fill

            portal.hires.append({
                "coach_name": fill.full_name,
                "coach_id": fill.coach_id,
                "from_team": "",
                "to_team": team_name,
                "role": role,
                "reason": "generated_fill",
                "salary": fill.contract_salary,
                "years": fill.contract_years_remaining,
                "development": fill.development,
                "overall": fill.overall,
            })

    portal.resolved = True
    return changes
