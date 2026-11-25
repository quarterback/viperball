"""Named position coaching within the existing dynasty staff and market."""
from .coach_roles import (POSITION_ROLES, POSITION_DISCIPLINE, TECHNICAL,
                          position_role, stable_rng)


def desired_positions(prestige):
    # Six assignments are covered even when a coordinator does the teaching.
    if prestige >= 75:
        return POSITION_ROLES
    if prestige >= 45:
        return ("pos_zb", "pos_backs", "pos_dl", "pos_kicks")
    return ("pos_zb", "pos_dl")


def salary_cap(prestige):
    # Incremental per-position payroll allowance. Existing senior payroll
    # is unchanged; this is not a claim that the legacy salary pool clears.
    return int(85000 + 1800 * max(0, min(100, prestige)))


def position_salary(card, prestige, rng, role=None):
    from .coaching import calculate_coach_salary
    return min(salary_cap(prestige), calculate_coach_salary(card, rng=rng, target_role=role))


def ensure_position_staff(staffs, prestige_by_team, year, active=None):
    """Fill newly funded position slots; do not replace existing contracts."""
    from .coaching import generate_coach_card
    occupied = {c.coach_id for staff in staffs.values() for c in staff.values()}
    rows = []
    names = sorted(staffs if active is None else active)
    for team in names:
        staff = staffs.get(team)
        if not staff:
            continue
        prestige = prestige_by_team.get(team, 50)
        for role in desired_positions(prestige):
            if role in staff:
                continue
            rng = stable_rng(f"position-staff-v1:{team}:{role}:{year}")
            card = generate_coach_card(role=role, team_name=team, prestige=prestige, year=year, rng=rng)
            while card.coach_id in occupied:
                card = generate_coach_card(role=role, team_name=team, prestige=prestige, year=year, rng=rng)
            occupied.add(card.coach_id)
            card.contract_salary = min(card.contract_salary, salary_cap(prestige))
            card.contract_buyout = card.contract_salary * card.contract_years_remaining // 2
            staff[role] = card
            rows.append({"team":team,"role":role,"coach_id":card.coach_id,"salary":card.contract_salary})
    return rows


def assigned_coach(staff, role):
    staff = staff or {}
    return staff.get(role) or staff.get(POSITION_DISCIPLINE.get(role))


def coverage(staff):
    result = {}
    for role in POSITION_ROLES:
        coach = assigned_coach(staff, role)
        result[role] = {"coach_id": coach.coach_id if coach else None,
                        "dedicated": role in (staff or {})}
    return result


def instruction(staff, position):
    """Focus an existing position-development allowance on technical skills.

    The dedicated teacher reallocates an existing allowance; never creates
    a new one. Kicking/return work shares the same allowance, without stacking.
    """
    role = position_role(position)
    coach = (staff or {}).get(role)
    kicking = (staff or {}).get("pos_kicks") if position in ("Zeroback", "Keeper") else None
    if coach is None and kicking is None:
        return {}
    weights = {}
    shares = []
    for member, key in ((coach, role), (kicking, "pos_kicks")):
        if member is None:
            continue
        focus = .35 + .45 * max(0., min(1., (member.development - 25) / 70))
        shares.append(focus)
        for attr in TECHNICAL[key]:
            weights[attr] = weights.get(attr, 0.) + focus / len(TECHNICAL[key])
    return {"focus": sum(shares)/len(shares), "weights": weights}


def recruiting_multiplier(staff, recruit):
    """Specialist targeting within a position, capped at +/-3%."""
    role = position_role(recruit.position)
    card = (staff or {}).get(role)
    if card is None:
        return 1.
    values = [getattr(recruit,"true_"+a,50) for a in TECHNICAL[role]]
    technical = sum(values)/len(values)
    relative = max(-1.,min(1.,(technical-recruit.true_overall)/25.))
    teaching = max(0.,min(1.,(card.recruiting-25)/70))
    return 1 + .03*relative*teaching


def scouting_error(staff, position, base=3):
    card = (staff or {}).get(position_role(position))
    if card is None:
        return base
    return max(1, base - int(card.development >= 65) - int(card.development >= 85))


def retention_bonus(staff, year=None):
    # Existing portal accepts a team-wide suppression input. Apply a small
    # average across dedicated coaches only, never one stacked bonus per coach.
    coaches = [c for r,c in (staff or {}).items() if r in POSITION_ROLES
               and (year is None or (c.career_history and c.career_history[-1].team_name==c.team_name
                    and c.career_history[-1].year_end==year-1))]
    if not coaches:
        return 0.
    return .025 * sum(max(0.,(c.leadership-50)/45) for c in coaches) / len(POSITION_ROLES)


def personnel_report(staff, roster):
    """Technical evaluations for offseason planning, not depth-chart overrides."""
    rows = {}
    for role in POSITION_ROLES:
        teacher = assigned_coach(staff, role)
        if teacher is None:
            continue
        players = [p for p in roster if position_role(p.position) == role or
                   (role == "pos_kicks" and p.position in ("Zeroback","Keeper"))]
        ranked = sorted(players, key=lambda p: (-sum(getattr(p,a,0) for a in TECHNICAL[role])/
                       len(TECHNICAL[role]), str(getattr(p,"player_id",""))))
        rows[role] = {"coach_id":teacher.coach_id, "dedicated":role in staff,
                      "recommendations":[{"player_id":p.player_id,"name":p.full_name}
                                         for p in ranked[:3]]}
    return rows


def alumni_candidates(player_cards, year, history):
    """Select actual departing players for future entry; keep a unique ID."""
    from .coaching import convert_player_to_coach
    known = {x["player_id"] for h in history.values()
             for x in h.get("alumni_candidates", [])}
    entries = []
    for team, cards in sorted(player_cards.items()):
        for p in cards:
            pid = getattr(p,"player_id",None)
            role = position_role(p.position)
            if not pid or pid in known or role is None or p.year != "Graduate":
                continue
            known.add(pid)
            rng = stable_rng("alumni-coaching-v1:" + pid)
            # Roughly 2–4% of graduates, biased toward teachable players.
            if rng.random() >= .02 + .02 * max(0.,min(1.,(getattr(p,"coachability",50)-25)/70)):
                continue
            delay = rng.randint(3,6)
            card = convert_player_to_coach(p,role=role,year=year+delay,
                                           years_after_graduation=delay,rng=rng)
            # Use the original player identity, not a potentially colliding name.
            import hashlib
            card.coach_id = "alumni_" + hashlib.sha256(pid.encode()).hexdigest()[:24]
            card.tactical_profile = {}
            card.career_development = {}
            card.alma_mater = team
            card.contract_salary = card.contract_years_remaining = card.contract_buyout = 0
            from .coach_tactics import ensure_coach_tactical_profile
            from .coach_career import ensure
            ensure_coach_tactical_profile(card)
            ensure(card)
            entries.append({"player_id":pid,"graduating_team":team,"ready_year":year+delay,
                            "card":card.to_dict()})
    return entries


def available_alumni(history, year, staffs):
    from .coaching import CoachCard
    employed = {c.coach_id for staff in staffs.values() for c in staff.values()}
    hired = {x.get("coach_id") for h in history.values() for x in h.get("portal_hires",[])}
    retired = {x.get("coach_id") for h in history.values() for x in h.get("retirements",[])}
    used = employed | hired | retired
    result = []
    for h in history.values():
        for entry in h.get("alumni_candidates", []):
            if not entry["ready_year"] <= year <= entry["ready_year"]+3:
                continue
            cid = entry["card"]["coach_id"]
            if cid in used:
                continue
            card = CoachCard.from_dict(entry["card"])
            card.age += year-entry["ready_year"]
            used.add(cid)
            result.append(card)
    return result


def installation_growth(staff, side, year):
    """At most .02 added to existing base-book offseason familiarity.

    Requires a completed season with this program; no game-day modifier.
    """
    roles = [r for r in POSITION_ROLES if POSITION_DISCIPLINE[r]==("oc" if side=="offense" else "dc")]
    total = 0.
    for role in roles:
        card = (staff or {}).get(role)
        if card and card.career_history:
            stop = card.career_history[-1]
            if stop.team_name==card.team_name and (year is None or stop.year_end==year):
                total += max(0.,min(1.,(card.development-50)/45))
    return .02*total/max(1,len(roles))
