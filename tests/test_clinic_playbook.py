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


def test_observable_reads_and_compound_risk():
    from engine.clinic_playbook import clinic_read, compound_fumble_probability
    read, bias = clinic_read({"package_id": "clinic_pod_two"}, "spread")
    assert read == "edge_contained" and bias["lateral_spread"] < 0
    assert clinic_read({"package_id": "clinic_pod_two"}, "stacked")[1]["lateral_spread"] > 0
    assert clinic_read({"package_id": "clinic_corridor_switch"}, "aggressive")[1]["kick_pass"] < 0
    assert clinic_read({"package_id": "unknown"}, "stacked") == (None, {})
    risks = [compound_fumble_probability(n) for n in (2, 3, 4)]
    assert abs(risks[0] - .12) < 1e-8 and risks[0] < risks[1] < risks[2]


def test_launch_option_threshold_is_bounded():
    from engine.clinic_playbook import snap_kick_threshold_shift
    t = {"authority": 1, "packages": [{"package_id": "clinic_launch_option", "familiarity": 1}]}
    c = state(down=5)
    shift = snap_kick_threshold_shift(t, c, "kicking_zb")
    assert 0 < shift <= 2
    assert snap_kick_threshold_shift(t, c, "dual_threat_zb") > 0
    assert snap_kick_threshold_shift(t, c, "running_zb") == 0
    assert snap_kick_threshold_shift(t, state(down=2), "kicking_zb") == 0
    assert snap_kick_threshold_shift(t, dict(c, clinic_defense_school="keeper_hunt"), "kicking_zb") < shift


def test_existing_defensive_counter_eligibility_responds_to_scouting():
    from engine.defensive_commitments import eligibility
    assert eligibility("chaos_lateral_trap", {"early_down"}, {"recent_lateral_rate": .3}, []) == 1
    assert eligibility("chaos_lateral_trap", {"early_down"}, {"recent_lateral_rate": 0}, []) == .45
    assert eligibility("shadow_robber", {"late_downs"}, {"down": 5, "recent_kick_rate": .5}, []) == 1
    assert eligibility("shadow_robber", {"late_downs"}, {"down": 5, "recent_kick_rate": 0}, []) == .45


def test_full_engine_clinic_selection():
    from pathlib import Path
    from engine.game_engine import ViperballEngine, load_team_from_json
    from engine.coaching import CoachCard
    from engine.team_installation import new_installation
    paths = sorted((Path(__file__).resolve().parents[1] / "data" / "teams").glob("*.json"))
    a, b = [load_team_from_json(str(p), fresh=False) for p in paths[:2]]
    staff = {}
    for role in ("head_coach", "oc"):
        staff[role] = CoachCard(coach_id="clinic-" + role, first_name="Clinic",
            last_name=role, age=47, gender="female", role=role,
            classification="scheme_master", instincts=76, leadership=72,
            composure=70, rotations=65, development=65, recruiting=65)
    a.installation = new_installation(a.name, staff, "lateral_spread", "balanced", 2026)
    a.installation["offense"].update(familiarity=1.0, family_familiarity=1.0,
        packages=[{"package_id": "clinic_pod_two", "familiarity": 1.0}])
    game = ViperballEngine(a, b, seed=20261127, home_coaching=staff,
        style_overrides={a.name: "lateral_spread", b.name: "balanced"},
        weather="clear", neutral_site=True).simulate_game()
    calls = [p.get("offensive_call") or {} for p in game["play_by_play"]]
    selected = [c for c in calls if c.get("package_id") == "clinic_pod_two"]
    assert selected, "installed clinic concept never selected"
    assert all("clinic_pod_two" in c["eligible"] for c in selected)
    for c in selected:
        if "clinic_transfer_target" in c:
            assert c["clinic_transfer_target"] in (1, 2)
