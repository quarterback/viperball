"""CCH-07 college coaching employment and career regression checks."""
import json
import random
from copy import deepcopy

from engine.coaching import CoachCard, CoachCareerStop, generate_coaching_staff
from engine.coach_tactics import ensure_coach_tactical_profile
from engine.coaching_portal import (
    CoachingPortal, CoachingPortalEntry, run_coaching_match,
    populate_coaching_portal,
)
from engine.dynasty import create_dynasty


def test_promotion_vacates_old_job_and_preserves_coach_identity():
    rng = random.Random(827)
    staffs = {t: generate_coaching_staff(t, rng=rng) for t in ("A", "B")}
    assistant = staffs["A"]["dc"]
    old_hc = staffs["B"]["head_coach"]
    profile = deepcopy(ensure_coach_tactical_profile(assistant))
    portal = CoachingPortal(year=2027)
    portal.add_vacancy("B", "head_coach")
    portal.add_entry(CoachingPortalEntry(assistant, "A", "seeking_hc", 2027,
                                        ["head_coach"]))
    run_coaching_match(portal, staffs, {"A": 40, "B": 70}, year=2027, rng=rng)
    assert staffs["B"]["head_coach"] is assistant
    assert staffs["A"]["dc"] is not assistant
    assert assistant.role == "head_coach" and assistant.team_name == "B"
    assert ensure_coach_tactical_profile(assistant) == profile
    ids = [c.coach_id for staff in staffs.values() for c in staff.values()]
    assert len(ids) == len(set(ids)) == 8
    assert old_hc.coach_id not in ids
    assert any(h["to_team"] == "A" and h["role"] == "dc" for h in portal.hires)


def test_unmatched_employed_assistant_stays_and_duplicate_vacancy_is_ignored():
    rng = random.Random(23)
    staffs = {t: generate_coaching_staff(t, rng=rng) for t in ("A", "B")}
    assistant = staffs["A"]["oc"]
    portal = CoachingPortal(year=2027)
    portal.add_vacancy("B", "dc")
    portal.add_vacancy("B", "dc")
    portal.add_entry(CoachingPortalEntry(assistant, "A", "seeking_hc", 2027,
                                        ["head_coach"]))
    run_coaching_match(portal, staffs, {"A": 40, "B": 70}, year=2027, rng=rng)
    assert staffs["A"]["oc"] is assistant
    assert len(portal.hires) == 1
    assert portal.vacancies["B"] == ["dc"]


def test_expired_assistant_who_stays_receives_new_contract(monkeypatch):
    rng = random.Random(101)
    staff = generate_coaching_staff("A", rng=rng)
    for coach in staff.values():
        coach.contract_years_remaining = 2
        coach.wants_hc = False
        coach.hc_meter = 0
    assistant = staff["oc"]
    assistant.contract_years_remaining = 0
    monkeypatch.setattr(rng, "random", lambda: .9)
    portal = CoachingPortal(year=2027)
    populate_coaching_portal(portal, {"A":staff}, {"A":(6,6)}, {"A":50}, rng=rng)
    assert assistant.contract_years_remaining >= 2
    assert assistant.year_signed == 2027
    assert "oc" not in portal.vacancies.get("A", [])


def test_frozen_staff_not_aged_or_developed():
    rng = random.Random(123)
    dyn = create_dynasty("Career", "Coach", "A", starting_year=2026)
    dyn.add_conference("Test", ["A", "B"])
    dyn.current_year = 2027
    dyn.retired_programs = ["B"]
    dyn._coaching_staffs = {t:generate_coaching_staff(t, rng=rng) for t in ("A","B")}
    dyn.team_histories["A"].season_records[2026] = {"wins":6,"losses":6}
    before = {role:deepcopy(c.to_dict()) for role,c in dyn._coaching_staffs["B"].items()}
    result = dyn.run_coaching_offseason({}, rng=rng)
    assert {role:c.to_dict() for role,c in dyn._coaching_staffs["B"].items()} == before
    assert {e["team"] for e in result["development"]} == {"A"}
    assert len(result["development"]) == 4


def test_coach_card_roundtrip_preserves_awards_and_stints():
    c = generate_coaching_staff("A", rng=random.Random(88))["dc"]
    c.career_history.append(CoachCareerStop(2026,2027,"A","dc",wins=14,losses=10))
    c.career_awards.append({"year":2027,"award":"Conference champion"})
    ensure_coach_tactical_profile(c)
    restored = CoachCard.from_dict(json.loads(json.dumps(c.to_dict())))
    assert restored.career_history == c.career_history
    assert restored.career_awards == c.career_awards
    assert restored.tactical_profile == c.tactical_profile
