"""CCH-01: identities belong to coaches, not schools or per-game RNG."""

from copy import deepcopy
import json
import random

import pytest

from engine.coaching import CoachCard, generate_coach_card, generate_coaching_staff
from engine.coach_tactics import (
    PROFILE_VERSION, SEED_VERSION, generate_coach_tactical_profile,
    ensure_coach_tactical_profile,
)


def make_coach(coach_id="coach_stable_001", role="oc", **kw):
    return CoachCard(
        coach_id=coach_id,
        first_name="Ava",
        last_name="Lewis",
        gender="female",
        age=47,
        role=role,
        classification="scheme_master",
        instincts=75,
        leadership=67,
        composure=71,
        rotations=62,
        development=70,
        recruiting=61,
        personality_sliders={
            "aggression": 82,
            "risk_tolerance": 76,
            "tempo_preference": 73,
            "chaos_appetite": 62,
            "adaptability": 77,
            "stubbornness": 24,
            "player_trust": 79,
        },
        **kw,
    )


def test_generated_coach_owns_versioned_profile():
    coach = make_coach()
    p = coach.tactical_profile
    assert p["version"] == PROFILE_VERSION
    assert p["coach_id"] == coach.coach_id
    assert p["signature_seed_version"] == SEED_VERSION
    assert p["identity"]["offense_interpretation"]
    assert p["identity"]["defense_interpretation"]
    assert len(p["specialties"]) == 2
    assert len(p["vulnerabilities"]) == 1
    assert p["revision"] == 0
    assert all(-0.2 <= value <= 0.2 for group in (
        p["offense"]["formation_bias"],
        p["offense"]["family_bias"],
        p["offense"]["kick_pass_bias"],
    ) for value in group.values())


def test_signature_generation_is_reproducible_across_instances_and_team_changes():
    a = make_coach(team_name="Old School")
    b = make_coach(team_name="New School")
    assert a.tactical_profile == b.tactical_profile
    a.team_name = "Coastal State"
    a.role = "head_coach"  # retain established signature upon promotion
    assert ensure_coach_tactical_profile(a) == b.tactical_profile


def test_preserves_profile_through_full_json_roundtrip():
    coach = make_coach()
    original = deepcopy(coach.tactical_profile)
    coach.tactical_profile["revision"] = 2
    coach.tactical_profile["lineage"] = [{"coach_id": "mentor-42", "weight": .2}]
    record = json.loads(json.dumps(coach.to_dict()))
    restored = CoachCard.from_dict(record)
    assert restored.tactical_profile == record["tactical_profile"]
    assert restored.tactical_profile["revision"] == 2
    assert original["revision"] == 0


def test_legacy_coach_save_deterministically_backfills_without_changing_old_fields():
    coach = make_coach()
    old_record = coach.to_dict()
    del old_record["tactical_profile"]
    a = CoachCard.from_dict(old_record)
    b = CoachCard.from_dict(old_record)
    assert a.tactical_profile == b.tactical_profile
    assert a.first_name == old_record["first_name"]
    assert a.contract_salary == old_record["contract_salary"]


def test_new_tactical_generation_does_not_consume_global_random():
    random.seed(123456)
    before = random.getstate()
    _ = make_coach("no-rng-consumption")
    assert random.getstate() == before
    _ = generate_coach_tactical_profile(make_coach("no-rng-consumption"))
    assert random.getstate() == before


def test_different_coaches_have_distinct_persistent_interpretations():
    profiles = [make_coach("coach_" + str(i)).tactical_profile for i in range(24)]
    signatures = {
        (p["identity"]["offense_interpretation"],
         p["identity"]["defense_interpretation"],
         tuple(p["offense"]["formation_bias"].items()))
        for p in profiles
    }
    assert len(signatures) > 20


def test_correlated_offensive_preference_keeps_meaningful_tradeoffs():
    from engine.coach_tactics import OFFENSIVE_ARCHETYPES
    for name, traits in OFFENSIVE_ARCHETYPES.items():
        if name == "vertical_attack":
            assert traits["formation_bias"]["spread"] > 0
            assert traits["kick_pass_bias"]["bomb"] > 0
            assert traits["kick_pass_bias"]["quick_kick"] < 0
        if name == "run_to_kick":
            assert traits["family_bias"]["power"] > 0
            assert traits["kick_pass_bias"]["quick_kick"] > 0
            assert traits["formation_bias"]["heavy"] > 0


def test_invalid_profile_from_another_coach_is_rejected():
    a, b = make_coach("coach_a"), make_coach("coach_b")
    b.tactical_profile = deepcopy(a.tactical_profile)
    with pytest.raises(ValueError, match="different coach"):
        ensure_coach_tactical_profile(b)


@pytest.mark.parametrize("role", ["head_coach", "oc", "dc", "stc"])
def test_all_existing_coaching_roles_get_profiles(role):
    coach = make_coach(role=role)
    assert coach.tactical_profile["origin_role"] == role


def test_existing_coaching_staff_generator_returns_valid_cards():
    staff = generate_coaching_staff(team_name="College", rng=random.Random(20261123))
    assert set(staff) == {"head_coach", "oc", "dc", "stc"}
    for role, coach in staff.items():
        assert coach.tactical_profile["coach_id"] == coach.coach_id
        assert coach.tactical_profile["origin_role"] == role
        assert CoachCard.from_dict(coach.to_dict()).tactical_profile == coach.tactical_profile
