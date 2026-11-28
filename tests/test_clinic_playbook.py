"""Clinic policy unit checks plus existing package selector integration."""
import random

from engine.clinic_playbook import CONCEPTS, concept_weight, lateral_length
from engine.team_installation import choose_offensive_package
from engine.playbook_catalog import get_package


def state(**changes):
    return dict({"down": 3, "yards_to_go": 12, "field_position": 55,
                 "quarter": 2, "time_remaining": 400, "score_diff": 0,
                 "offense_energy": 90, "defense_energy": 90}, **changes)


def test_catalog_contract():
    for pid, c in CONCEPTS.items():
        p = get_package(pid)
        assert set(p["formation_tags"]) == set(c.formation)
        assert p["countered_by"] == list(c.defensive_counters)
        assert c.code_origin and c.read_progression


def test_early_late_and_urgency():
    assert concept_weight("clinic_anchor_crease", state(down=1)) > 0
    assert concept_weight("clinic_anchor_crease", state(down=3)) == 0
    assert concept_weight("clinic_last_wave", state(down=6, yards_to_go=15)) == 0
    assert concept_weight("clinic_last_wave", state(down=6, yards_to_go=15,
                          quarter=4, score_diff=-12, time_remaining=120)) > 0


def test_archetype_alignment():
    for pid, good, other in (
        ("clinic_anchor_crease", ("running_zb", "power_viper"), ("kicking_zb", "receiving_viper")),
        ("clinic_pod_two", ("distributor_zb", "hybrid_viper"), ("kicking_zb", "power_viper")),
        ("clinic_corridor_switch", ("dual_threat_zb", "decoy_viper"), ("running_zb", "power_viper")),
        ("clinic_launch_option", ("kicking_zb", "decoy_viper"), ("running_zb", "power_viper")),
    ):
        context = state(down=1 if pid == "clinic_anchor_crease" else 3)
        assert concept_weight(pid, dict(context, clinic_archetypes=good)) > concept_weight(pid, dict(context, clinic_archetypes=other))


def test_chain_length_and_risk_context():
    for pid, n in (("clinic_pod_two", 2), ("clinic_edge_three", 3), ("clinic_last_wave", 4)):
        assert lateral_length({"package_id": pid}, 6) == n
        assert lateral_length({"package_id": pid}, 2) == 1
        assert lateral_length({"package_id": pid}, 1) is None
    pid = "clinic_pod_two"
    assert concept_weight(pid, state(defense_energy=60)) > concept_weight(pid, state())
    assert concept_weight(pid, state(offense_energy=60)) < concept_weight(pid, state())
    assert concept_weight(pid, state(clinic_bonus_pending=True)) < concept_weight(pid, state())


def test_counter_preference():
    assert concept_weight("clinic_pod_two", state(clinic_defense_school="swarm")) < concept_weight("clinic_pod_two", state())
    assert concept_weight("clinic_corridor_switch", state(clinic_defense_school="lockdown")) < concept_weight("clinic_corridor_switch", state())
    assert concept_weight("clinic_corridor_switch", state(clinic_defense_school="fortress")) > concept_weight("clinic_corridor_switch", state())
    assert concept_weight("unknown", state()) == 1
    assert lateral_length({"package_id": "unknown"}, 6) is None


def test_live_selector_uses_clinic_eligibility():
    p = dict(get_package("clinic_last_wave"), familiarity=1.0)
    tactics = {"packages": [p], "authority": 1.0}
    picked, eligible, _ = choose_offensive_package(tactics, state(down=5), random.Random(1))
    assert picked is None and not eligible
    picked, eligible, _ = choose_offensive_package(tactics, state(down=5, quarter=4,
                                                 score_diff=-12, time_remaining=120),
                                                 random.Random(1))
    assert picked["package_id"] == p["package_id"] and p["package_id"] in eligible
