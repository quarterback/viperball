"""Persistent, coach-owned tactical signatures (CCH-01).

This module contains *identity metadata only*. It does not choose live plays,
change engine probabilities or define the scheme catalog. In later PRs the
game engine will combine these individual signatures with existing scheme
families and the team's installed repertoire.

Profiles use a local SHA-256 seeded RNG derived from coach_id. They are stable
across processes and save/load cycles, including when a coach changes teams.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import random
from typing import Any, Dict

PROFILE_VERSION = 1
SEED_VERSION = "coach-tactics-v1"

# Each coherent signature changes several related preferences together.
# These relative biases are *descriptive until CCH-02*, not gameplay modifiers.
OFFENSIVE_ARCHETYPES = {
    "vertical_attack": {
        "formation_bias": {"spread": 0.12, "split": 0.04, "tight": -0.07, "heavy": -0.09},
        "family_bias": {"kick_pass": 0.14, "counter": 0.05, "power": -0.08},
        "kick_pass_bias": {"bomb": 0.12, "territory": 0.04, "quick_kick": -0.09},
        "featured_position": "Viper",
        "specialties": ("deep_kick_after_run", "spread_against_pressure"),
        "vulnerability": "long_release_exposure",
    },
    "territory_control": {
        "formation_bias": {"tight": 0.06, "split": 0.07, "spread": -0.07, "heavy": -0.06},
        "family_bias": {"power": 0.05, "dive_option": 0.06, "kick_pass": -0.04},
        "kick_pass_bias": {"territory": 0.11, "quick_kick": 0.07, "bomb": -0.14},
        "featured_position": "Zeroback",
        "specialties": ("territory_kick_placement", "protect_possession"),
        "vulnerability": "limited_deep_threat",
    },
    "run_to_kick": {
        "formation_bias": {"heavy": 0.09, "tight": 0.08, "spread": -0.10, "split": -0.07},
        "family_bias": {"power": 0.12, "dive_option": 0.09, "kick_pass": -0.08},
        "kick_pass_bias": {"quick_kick": 0.13, "territory": 0.04, "bomb": -0.11},
        "featured_position": "Halfback",
        "specialties": ("quick_kick_after_power", "short_yardage"),
        "vulnerability": "predictable_interior_runs",
    },
    "spread_motion": {
        "formation_bias": {"spread": 0.13, "split": 0.06, "heavy": -0.11, "tight": -0.08},
        "family_bias": {"sweep_option": 0.09, "speed_option": 0.08, "viper_jet": 0.05},
        "kick_pass_bias": {"kick_lateral": 0.11, "quick_kick": 0.06, "bomb": -0.05},
        "featured_position": "Wingback",
        "specialties": ("perimeter_mismatch", "kick_lateral_spacing"),
        "vulnerability": "weak_interior_protection",
    },
    "balanced": {
        "formation_bias": {"split": 0.07, "spread": 0.02, "heavy": -0.05, "tight": -0.04},
        "family_bias": {"counter": 0.06, "dive_option": 0.04, "kick_pass": 0.02},
        "kick_pass_bias": {"territory": 0.06, "quick_kick": 0.04, "bomb": -0.05},
        "featured_position": "Slotback",
        "specialties": ("mixed_down_calls", "formation_disguise"),
        "vulnerability": "no_single_dominant_attack",
    },
}

DEFENSIVE_ARCHETYPES = {
    "selective_pressure": {
        "pressure_bias": 0.11, "run_support_bias": -0.03,
        "coverage_focus": "intermediate", "read_focus": ["kick_pass", "trick"],
        "specialties": ("timed_pressure", "late_down_disguise"),
        "vulnerability": "uncovered_perimeter",
    },
    "run_wall": {
        "pressure_bias": -0.04, "run_support_bias": 0.13,
        "coverage_focus": "short", "read_focus": ["run", "lateral"],
        "specialties": ("interior_gap_fit", "short_yardage_stand"),
        "vulnerability": "deep_kick_seams",
    },
    "deep_coverage": {
        "pressure_bias": -0.10, "run_support_bias": -0.04,
        "coverage_focus": "deep", "read_focus": ["kick_pass", "trick"],
        "specialties": ("bomb_containment", "zone_switching"),
        "vulnerability": "uncontested_interior",
    },
    "pursuit_zone": {
        "pressure_bias": -0.04, "run_support_bias": 0.06,
        "coverage_focus": "perimeter", "read_focus": ["lateral", "run"],
        "specialties": ("lateral_pursuit", "open_field_tackling"),
        "vulnerability": "inside_misdirection",
    },
    "turnover_hunt": {
        "pressure_bias": 0.06, "run_support_bias": -0.06,
        "coverage_focus": "opportunistic", "read_focus": ["kick_pass", "lateral"],
        "specialties": ("ball_hawk", "turnover_disguise"),
        "vulnerability": "overpursuit",
    },
}


def _slider(coach: Any, name: str) -> float:
    sliders = getattr(coach, "personality_sliders", {}) or {}
    return max(0.0, min(100.0, float(sliders.get(name, 50)))) / 100.0


def _stable_rng(coach_id: str) -> random.Random:
    if not coach_id:
        raise ValueError("A persistent tactical profile requires coach_id")
    payload = (SEED_VERSION + ":" + coach_id).encode("utf-8")
    return random.Random(int.from_bytes(hashlib.sha256(payload).digest()[:16], "big"))


def _pick_offensive_archetype(coach: Any, rng: random.Random) -> str:
    risk = _slider(coach, "risk_tolerance")
    agg = _slider(coach, "aggression")
    chaos = _slider(coach, "chaos_appetite")
    tempo = _slider(coach, "tempo_preference")
    weights = [
        0.35 + agg + risk * 0.7 + tempo * 0.35,
        0.35 + (1.0 - risk) + (1.0 - chaos) * 0.4,
        0.35 + (1.0 - chaos) + (1.0 - tempo) * 0.4,
        0.35 + chaos + tempo * 0.6,
        0.65 + (1.0 - abs(0.5 - risk) * 2.0),
    ]
    return rng.choices(tuple(OFFENSIVE_ARCHETYPES), weights=weights, k=1)[0]


def _pick_defensive_archetype(coach: Any, rng: random.Random) -> str:
    agg = _slider(coach, "aggression")
    adapt = _slider(coach, "adaptability")
    chaos = _slider(coach, "chaos_appetite")
    trust = _slider(coach, "player_trust")
    weights = [
        0.30 + agg + adapt * 0.5,
        0.35 + (1.0 - chaos) + trust * 0.3,
        0.35 + (1.0 - agg) + adapt * 0.3,
        0.35 + trust + (1.0 - chaos) * 0.2,
        0.30 + chaos + agg * 0.3,
    ]
    return rng.choices(tuple(DEFENSIVE_ARCHETYPES), weights=weights, k=1)[0]


def generate_coach_tactical_profile(coach: Any) -> Dict[str, Any]:
    """Generate a stable profile without consuming the season/game RNG.

    The same coach_id yields the same archetype tie-breaking; existing
    personality sliders influence probabilities and remain the coach's
    source-of-truth. This function has no global random side effects.
    """
    coach_id = str(getattr(coach, "coach_id", "") or "")
    rng = _stable_rng(coach_id)
    offensive_style = _pick_offensive_archetype(coach, rng)
    defensive_style = _pick_defensive_archetype(coach, rng)
    off = OFFENSIVE_ARCHETYPES[offensive_style]
    defense = DEFENSIVE_ARCHETYPES[defensive_style]

    # Small, correlated shifts around templates; never roll each play
    # independently. Profile values are stored even though CCH-01 is data-only.
    amplitude = 0.85 + rng.random() * 0.30
    def bias_map(values):
        return {k: round(max(-0.20, min(0.20, v * amplitude)), 3)
                for k, v in values.items()}

    adapt = _slider(coach, "adaptability")
    stubbornness = _slider(coach, "stubbornness")
    player_trust = _slider(coach, "player_trust")
    delegation = round(max(0.25, min(0.85,
                                    0.35 + (1 - stubbornness) * 0.30
                                    + player_trust * 0.20)), 3)

    role = str(getattr(coach, "role", "") or "")
    if role not in ("head_coach", "oc", "dc", "stc"):
        raise ValueError("Unknown coach role: " + role)
    return {
        "version": PROFILE_VERSION,
        "coach_id": coach_id,
        "origin_role": role,
        "signature_seed_version": SEED_VERSION,
        "identity": {
            "offense_interpretation": offensive_style,
            "defense_interpretation": defensive_style,
        },
        "offense": {
            "formation_bias": bias_map(off["formation_bias"]),
            "family_bias": bias_map(off["family_bias"]),
            "kick_pass_bias": bias_map(off["kick_pass_bias"]),
            "featured_position": off["featured_position"],
        },
        "defense": {
            "pressure_bias": round(defense["pressure_bias"] * amplitude, 3),
            "run_support_bias": round(defense["run_support_bias"] * amplitude, 3),
            "coverage_focus": defense["coverage_focus"],
            "read_focus": list(defense["read_focus"]),
        },
        "head_coach": {
            "delegation": delegation,
            "adaptation_preference": round(adapt - stubbornness, 3),
        },
        "special_teams": {
            "field_position_bias": round(0.5 - _slider(coach, "risk_tolerance"), 3),
            "return_aggression": round(_slider(coach, "aggression") - 0.5, 3),
        },
        "specialties": list(off["specialties"] if role in ("head_coach", "oc")
                            else defense["specialties"]),
        "vulnerabilities": [off["vulnerability"] if role in ("head_coach", "oc")
                            else defense["vulnerability"]],
        "revision": 0,
    }


def ensure_coach_tactical_profile(coach: Any) -> Dict[str, Any]:
    """Populate only missing profiles. Preserve save data and coach moves."""
    existing = getattr(coach, "tactical_profile", None)
    if existing:
        if not isinstance(existing, dict):
            raise ValueError("Coach tactical_profile must be an object")
        if existing.get("coach_id") != coach.coach_id:
            raise ValueError("Coach tactical profile belongs to a different coach")
        if existing.get("version") != PROFILE_VERSION:
            raise ValueError("Unsupported coach tactical profile version")
        return existing
    profile = generate_coach_tactical_profile(coach)
    coach.tactical_profile = deepcopy(profile)
    return coach.tactical_profile
