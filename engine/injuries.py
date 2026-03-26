"""
Viperball Injury & Availability System

Comprehensive model covering:
- On-field contact injuries (football-specific, during games)
- On-field non-contact injuries (muscle pulls, ligament tears)
- Practice/training injuries (between games)
- Off-field availability issues (academics, illness, personal — women's college context)
- In-game injury events (injuries that happen mid-game, triggering substitutions)
- Substitution logic (depth chart fallback when players are unavailable)

Tiers:
    day_to_day   – Available but diminished, or misses 0-1 games
    minor        – Out 1-3 weeks
    moderate     – Out 3-6 weeks
    major        – Out 6-10 weeks
    severe       – Season-ending

Usage:
    tracker = InjuryTracker()
    new_injuries = tracker.process_week(week, teams, standings)
    unavailable = tracker.get_unavailable_names(team_name, week)
    penalties = tracker.get_team_injury_penalties(team_name, week)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ──────────────────────────────────────────────────────────────
# INJURY TIERS
# ──────────────────────────────────────────────────────────────

INJURY_TIER_WEEKS = {
    "day_to_day": (0, 1),
    "minor":      (1, 3),
    "moderate":   (3, 6),
    "major":      (6, 10),
    "severe":     (99, 99),   # season-ending
}

INJURY_SEVERITY_PENALTY = {
    "day_to_day": 0.01,
    "minor":      0.03,
    "moderate":   0.07,
    "major":      0.10,
    "severe":     0.12,
}

# Stat reduction when a DTD player plays through it (multiplied against their attributes)
DTD_PERFORMANCE_REDUCTION = 0.90  # 10% reduction


# ──────────────────────────────────────────────────────────────
# INJURY CATALOG — Expanded OOTP-style model for Viperball
#
# Each entry has:
#   desc         — diagnosis displayed to user
#   body         — body part for re-injury tracking
#   phrase       — descriptive narrative phrase (optional)
#   freq         — 1 (rare) to 5 (common)
#   reinjury     — 0 (none), 1 (sometimes), 2 (often)
#   nagging      — 0 or 1; nagging injuries linger / flare up
#   surgery      — 0 (no), 1 (sometimes), 2 (yes)
#   inf_run      — 0-3 influence on running/speed
#   inf_kick     — 0-3 influence on kicking
#   inf_lateral  — 0-3 influence on lateral skill / agility
#   min_weeks    — minimum weeks out (overrides tier default)
#   max_weeks    — maximum weeks out (overrides tier default)
#
# Fields default to 0/empty if omitted — only specify what matters.
# ──────────────────────────────────────────────────────────────

_ON_FIELD_CONTACT = {
    "day_to_day": [
        {"desc": "bruised shoulder", "body": "shoulder", "freq": 4, "inf_lateral": 1},
        {"desc": "hand contusion", "body": "hand", "freq": 3, "inf_lateral": 1},
        {"desc": "stinger", "body": "neck", "freq": 3, "reinjury": 1, "nagging": 1},
        {"desc": "minor knee bruise", "body": "knee", "freq": 4, "inf_run": 1},
        {"desc": "jammed finger", "body": "hand", "freq": 4, "inf_lateral": 1},
        {"desc": "hip pointer", "body": "hip", "freq": 3, "inf_run": 1},
        {"desc": "minor ankle tweak", "body": "ankle", "freq": 5, "inf_run": 1},
        {"desc": "bruised ribs", "body": "ribs", "freq": 3, "nagging": 1},
        {"desc": "minor wrist bruise", "body": "wrist", "freq": 3, "inf_lateral": 1},
        {"desc": "light knee contusion", "body": "knee", "freq": 4, "inf_run": 1},
        {"desc": "bruised thigh", "body": "thigh", "freq": 4, "inf_run": 1},
        {"desc": "minor elbow bruise", "body": "elbow", "freq": 2, "inf_lateral": 1},
        {"desc": "bruised shin", "body": "shin", "freq": 3, "inf_run": 1},
        {"desc": "minor back contusion", "body": "back", "freq": 2, "inf_run": 1},
        {"desc": "mild whiplash", "body": "neck", "freq": 1, "nagging": 1},
        {"desc": "tailbone bruise", "body": "back", "freq": 2, "inf_run": 1},
        {"desc": "toe contusion", "body": "foot", "freq": 3, "inf_run": 1, "inf_kick": 1},
        {"desc": "facial bruise", "body": "head", "freq": 2},
    ],
    "minor": [
        {"desc": "sprained ankle", "body": "ankle", "freq": 5, "reinjury": 1, "nagging": 1, "inf_run": 2},
        {"desc": "mild concussion (no hard helmet)", "body": "head", "freq": 4, "reinjury": 2, "inf_run": 1, "inf_kick": 1, "inf_lateral": 1},
        {"desc": "AC joint sprain", "body": "shoulder", "freq": 3, "reinjury": 1, "inf_lateral": 2},
        {"desc": "turf toe", "body": "foot", "freq": 4, "reinjury": 2, "nagging": 1, "inf_run": 2, "inf_kick": 1},
        {"desc": "bone bruise (knee)", "body": "knee", "freq": 3, "nagging": 1, "inf_run": 2},
        {"desc": "calf contusion", "body": "calf", "freq": 3, "inf_run": 1},
        {"desc": "hyperextended elbow", "body": "elbow", "freq": 2, "reinjury": 1, "inf_lateral": 2},
        {"desc": "dislocated finger", "body": "hand", "freq": 2, "inf_lateral": 1},
        {"desc": "sprained finger", "body": "hand", "freq": 4, "nagging": 1, "inf_lateral": 1},
        {"desc": "knee contusion", "body": "knee", "freq": 4, "inf_run": 2},
        {"desc": "bruised foot", "body": "foot", "freq": 3, "inf_run": 1, "inf_kick": 1},
        {"desc": "neck strain", "body": "neck", "freq": 2, "nagging": 1, "inf_run": 1},
        {"desc": "lacerated hand", "body": "hand", "freq": 1, "inf_lateral": 1},
        {"desc": "sprained wrist", "body": "wrist", "freq": 3, "reinjury": 1, "inf_lateral": 2},
        {"desc": "facial laceration", "body": "head", "freq": 2, "inf_run": 0},
        {"desc": "forearm contusion", "body": "forearm", "freq": 2, "inf_lateral": 1},
    ],
    "moderate": [
        {"desc": "MCL sprain (grade 2)", "body": "knee", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 3, "min_weeks": 3, "max_weeks": 6},
        {"desc": "high ankle sprain", "body": "ankle", "freq": 4, "reinjury": 2, "nagging": 1, "inf_run": 3, "inf_kick": 1, "min_weeks": 3, "max_weeks": 8},
        {"desc": "shoulder separation", "body": "shoulder", "freq": 3, "reinjury": 1, "surgery": 1, "inf_lateral": 2},
        {"desc": "broken hand", "body": "hand", "freq": 2, "surgery": 1, "inf_lateral": 3, "min_weeks": 4, "max_weeks": 8},
        {"desc": "fractured rib", "body": "ribs", "freq": 2, "inf_run": 2, "inf_kick": 2, "min_weeks": 4, "max_weeks": 6},
        {"desc": "concussion (extended protocol — no hard helmet)", "body": "head", "freq": 3, "reinjury": 2, "inf_run": 1, "inf_kick": 1, "inf_lateral": 1, "min_weeks": 3, "max_weeks": 6},
        {"desc": "deep thigh contusion", "body": "thigh", "freq": 3, "inf_run": 2},
        {"desc": "torn rib cage muscle", "body": "ribs", "freq": 2, "reinjury": 1, "inf_run": 1, "inf_kick": 2},
        {"desc": "sprained knee", "body": "knee", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 2},
        {"desc": "strained back", "body": "back", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 2, "inf_kick": 1},
        {"desc": "thumb ligament tear", "body": "hand", "freq": 2, "reinjury": 1, "surgery": 1, "inf_lateral": 2},
        {"desc": "knee hyperextension", "body": "knee", "freq": 2, "reinjury": 1, "inf_run": 2},
        {"desc": "orbital fracture", "body": "head", "freq": 1, "surgery": 1, "min_weeks": 4, "max_weeks": 6},
        {"desc": "dislocated wrist", "body": "wrist", "freq": 1, "surgery": 1, "inf_lateral": 3, "min_weeks": 4, "max_weeks": 8},
        {"desc": "clavicle bruise", "body": "collarbone", "freq": 2, "nagging": 1, "inf_lateral": 1},
    ],
    "major": [
        {"desc": "broken collarbone", "body": "collarbone", "freq": 2, "surgery": 1, "inf_lateral": 2, "min_weeks": 6, "max_weeks": 10},
        {"desc": "torn meniscus (partial)", "body": "knee", "freq": 3, "reinjury": 2, "surgery": 2, "inf_run": 3, "min_weeks": 6, "max_weeks": 10},
        {"desc": "Lisfranc sprain", "body": "foot", "freq": 2, "reinjury": 1, "surgery": 1, "inf_run": 3, "inf_kick": 3, "min_weeks": 8, "max_weeks": 12},
        {"desc": "dislocated elbow", "body": "elbow", "freq": 1, "surgery": 1, "inf_lateral": 3, "min_weeks": 6, "max_weeks": 10},
        {"desc": "broken wrist", "body": "wrist", "freq": 2, "surgery": 1, "inf_lateral": 3, "min_weeks": 6, "max_weeks": 10},
        {"desc": "severe concussion (multi-week protocol — no hard helmet)", "body": "head", "freq": 2, "reinjury": 2, "inf_run": 2, "inf_kick": 2, "inf_lateral": 2, "min_weeks": 6, "max_weeks": 10},
        {"desc": "torn labrum (shoulder)", "body": "shoulder", "freq": 2, "reinjury": 2, "surgery": 2, "inf_lateral": 3, "min_weeks": 8, "max_weeks": 12},
        {"desc": "broken ankle", "body": "ankle", "freq": 1, "surgery": 2, "inf_run": 3, "inf_kick": 3, "min_weeks": 8, "max_weeks": 12},
        {"desc": "herniated disc", "body": "back", "freq": 2, "reinjury": 2, "nagging": 1, "surgery": 1, "inf_run": 3, "inf_kick": 2, "min_weeks": 8, "max_weeks": 15},
        {"desc": "stress fracture (shin)", "body": "shin", "freq": 2, "reinjury": 1, "inf_run": 3, "min_weeks": 6, "max_weeks": 10},
        {"desc": "stress fracture (foot)", "body": "foot", "freq": 2, "reinjury": 1, "inf_run": 3, "inf_kick": 3, "min_weeks": 6, "max_weeks": 10},
        {"desc": "fractured hand", "body": "hand", "freq": 1, "surgery": 1, "inf_lateral": 3, "min_weeks": 6, "max_weeks": 10},
        {"desc": "broken jaw", "body": "head", "freq": 1, "surgery": 1, "min_weeks": 6, "max_weeks": 10},
    ],
    "severe": [
        {"desc": "ACL tear", "body": "knee", "freq": 3, "reinjury": 2, "surgery": 2, "inf_run": 3},
        {"desc": "Achilles rupture", "body": "achilles", "freq": 2, "reinjury": 1, "surgery": 2, "inf_run": 3, "inf_kick": 3},
        {"desc": "broken leg (tibia/fibula)", "body": "leg", "freq": 1, "surgery": 2, "inf_run": 3},
        {"desc": "dislocated shoulder (labrum tear)", "body": "shoulder", "freq": 2, "reinjury": 2, "surgery": 2, "inf_lateral": 3},
        {"desc": "torn patellar tendon", "body": "knee", "freq": 1, "surgery": 2, "inf_run": 3, "inf_kick": 3},
        {"desc": "spinal compression injury", "body": "spine", "freq": 1, "surgery": 1, "inf_run": 3, "inf_kick": 3, "inf_lateral": 3},
        {"desc": "torn PCL (knee)", "body": "knee", "freq": 1, "reinjury": 1, "surgery": 2, "inf_run": 3},
        {"desc": "torn UCL (elbow)", "body": "elbow", "freq": 1, "surgery": 2, "inf_lateral": 3, "inf_kick": 3},
        {"desc": "broken femur", "body": "leg", "freq": 1, "surgery": 2, "inf_run": 3},
        {"desc": "torn rotator cuff", "body": "shoulder", "freq": 2, "reinjury": 1, "surgery": 2, "inf_lateral": 3, "inf_kick": 2},
        {"desc": "multi-ligament knee injury", "body": "knee", "freq": 1, "surgery": 2, "inf_run": 3, "inf_lateral": 3},
        {"desc": "severe skull fracture (no hard helmet)", "body": "head", "freq": 1, "surgery": 2, "inf_run": 3, "inf_kick": 3, "inf_lateral": 3},
    ],
}


# ──────────────────────────────────────────────────────────────
# INJURY CATALOG — On-field non-contact (soft tissue / planting)
# ──────────────────────────────────────────────────────────────

_ON_FIELD_NONCONTACT = {
    "day_to_day": [
        {"desc": "minor hamstring tightness", "body": "hamstring", "freq": 5, "nagging": 1, "inf_run": 1},
        {"desc": "quad tightness", "body": "quad", "freq": 5, "nagging": 1, "inf_run": 1},
        {"desc": "cramping", "body": "general", "freq": 5, "inf_run": 1},
        {"desc": "calf tightness", "body": "calf", "freq": 5, "nagging": 1, "inf_run": 1},
        {"desc": "mild calf strain", "body": "calf", "freq": 4, "nagging": 1, "inf_run": 1},
        {"desc": "sore knee", "body": "knee", "freq": 4, "nagging": 1, "inf_run": 1},
        {"desc": "heel soreness", "body": "heel", "freq": 2, "nagging": 1, "inf_run": 1, "inf_kick": 1},
        {"desc": "mild groin tightness", "body": "groin", "freq": 4, "nagging": 1, "inf_run": 1},
        {"desc": "sore Achilles tendon", "body": "achilles", "freq": 2, "reinjury": 1, "nagging": 1, "inf_run": 2},
        {"desc": "hamstring spasms", "body": "hamstring", "freq": 3, "nagging": 1, "inf_run": 1},
        {"desc": "calf cramp", "body": "calf", "freq": 3, "inf_run": 1},
        {"desc": "shin splints", "body": "shin", "freq": 3, "nagging": 1, "inf_run": 1},
        {"desc": "foot arch soreness", "body": "foot", "freq": 3, "nagging": 1, "inf_run": 1, "inf_kick": 1},
        {"desc": "tight IT band", "body": "knee", "freq": 3, "nagging": 1, "inf_run": 1},
        {"desc": "ankle stiffness", "body": "ankle", "freq": 4, "nagging": 1, "inf_run": 1},
        {"desc": "sore Achilles", "body": "achilles", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 1},
    ],
    "minor": [
        {"desc": "strained hamstring", "body": "hamstring", "freq": 5, "reinjury": 2, "nagging": 1, "inf_run": 2},
        {"desc": "groin strain", "body": "groin", "freq": 4, "reinjury": 1, "nagging": 1, "inf_run": 2},
        {"desc": "hip flexor strain", "body": "hip", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 2},
        {"desc": "calf strain", "body": "calf", "freq": 4, "reinjury": 1, "nagging": 1, "inf_run": 2},
        {"desc": "lower back spasm", "body": "back", "freq": 4, "reinjury": 1, "nagging": 1, "inf_run": 1, "inf_kick": 1},
        {"desc": "mild oblique strain", "body": "oblique", "freq": 3, "nagging": 1, "inf_run": 1, "inf_kick": 1},
        {"desc": "quad strain", "body": "quad", "freq": 4, "reinjury": 1, "nagging": 1, "inf_run": 2},
        {"desc": "adductor strain", "body": "groin", "freq": 2, "inf_run": 2},
        {"desc": "knee tendinitis", "body": "knee", "freq": 4, "reinjury": 2, "nagging": 1, "inf_run": 2},
        {"desc": "sore hamstring", "body": "hamstring", "freq": 5, "nagging": 1, "inf_run": 2},
        {"desc": "mild hip strain", "body": "hip", "freq": 3, "nagging": 1, "inf_run": 2},
        {"desc": "back tightness", "body": "back", "freq": 4, "reinjury": 1, "nagging": 1, "inf_run": 1},
        {"desc": "patellar tendinitis", "body": "knee", "freq": 3, "reinjury": 2, "nagging": 1, "inf_run": 2, "inf_kick": 1},
        {"desc": "Achilles tendinitis", "body": "achilles", "freq": 3, "reinjury": 2, "nagging": 1, "inf_run": 2, "inf_kick": 1},
        {"desc": "plantar fasciitis", "body": "foot", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 2, "inf_kick": 1},
        {"desc": "shin splints (persistent)", "body": "shin", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 2},
        {"desc": "ankle tendinitis", "body": "ankle", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 2},
    ],
    "moderate": [
        {"desc": "pulled hamstring (grade 2)", "body": "hamstring", "freq": 4, "reinjury": 2, "nagging": 1, "inf_run": 3, "min_weeks": 3, "max_weeks": 6},
        {"desc": "quad strain (grade 2)", "body": "quad", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 3},
        {"desc": "abdominal strain", "body": "abdomen", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 1, "inf_kick": 2},
        {"desc": "groin tear (partial)", "body": "groin", "freq": 2, "reinjury": 2, "nagging": 1, "inf_run": 3, "min_weeks": 3, "max_weeks": 6},
        {"desc": "hip flexor tear (partial)", "body": "hip", "freq": 2, "reinjury": 1, "inf_run": 3},
        {"desc": "quadriceps strain (grade 2)", "body": "quad", "freq": 3, "reinjury": 1, "inf_run": 3},
        {"desc": "torn calf muscle (partial)", "body": "calf", "freq": 2, "reinjury": 1, "inf_run": 3},
        {"desc": "oblique strain", "body": "oblique", "freq": 2, "reinjury": 1, "inf_kick": 2, "inf_lateral": 1},
        {"desc": "lower back strain", "body": "back", "freq": 3, "reinjury": 2, "nagging": 1, "inf_run": 2, "inf_kick": 2},
        {"desc": "IT band syndrome", "body": "knee", "freq": 2, "reinjury": 1, "nagging": 1, "inf_run": 2},
        {"desc": "calf strain (grade 2)", "body": "calf", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 3},
        {"desc": "Achilles tendinopathy", "body": "achilles", "freq": 2, "reinjury": 2, "nagging": 1, "inf_run": 3, "inf_kick": 1},
        {"desc": "sports hernia", "body": "groin", "freq": 2, "reinjury": 1, "surgery": 1, "inf_run": 2, "inf_kick": 2, "min_weeks": 4, "max_weeks": 8},
    ],
    "major": [
        {"desc": "stress fracture (shin)", "body": "shin", "freq": 2, "reinjury": 1, "inf_run": 3, "min_weeks": 6, "max_weeks": 10},
        {"desc": "stress fracture (foot)", "body": "foot", "freq": 2, "reinjury": 1, "inf_run": 3, "inf_kick": 3, "min_weeks": 6, "max_weeks": 10},
        {"desc": "herniated disc", "body": "back", "freq": 2, "reinjury": 2, "nagging": 1, "surgery": 1, "inf_run": 3, "inf_kick": 2, "min_weeks": 8, "max_weeks": 15},
        {"desc": "torn hip labrum", "body": "hip", "freq": 2, "reinjury": 1, "surgery": 2, "inf_run": 3, "min_weeks": 8, "max_weeks": 12},
        {"desc": "torn abdominal muscle", "body": "abdomen", "freq": 2, "reinjury": 1, "surgery": 1, "inf_run": 3, "inf_kick": 3, "min_weeks": 6, "max_weeks": 10},
        {"desc": "plantar fascia tear", "body": "foot", "freq": 1, "reinjury": 1, "nagging": 1, "inf_run": 3, "inf_kick": 3, "min_weeks": 6, "max_weeks": 10},
        {"desc": "torn thigh muscle", "body": "thigh", "freq": 2, "reinjury": 1, "surgery": 1, "inf_run": 3, "min_weeks": 8, "max_weeks": 12},
        {"desc": "complete calf tear", "body": "calf", "freq": 1, "reinjury": 1, "surgery": 1, "inf_run": 3, "inf_kick": 2, "min_weeks": 8, "max_weeks": 12},
        {"desc": "stress fracture (pelvis)", "body": "hip", "freq": 1, "inf_run": 3, "min_weeks": 8, "max_weeks": 14},
    ],
    "severe": [
        {"desc": "ACL tear (non-contact)", "body": "knee", "freq": 3, "reinjury": 2, "surgery": 2, "inf_run": 3},
        {"desc": "Achilles tear (planting)", "body": "achilles", "freq": 2, "reinjury": 1, "surgery": 2, "inf_run": 3, "inf_kick": 3},
        {"desc": "complete hamstring avulsion", "body": "hamstring", "freq": 1, "surgery": 2, "inf_run": 3},
        {"desc": "torn quadriceps tendon", "body": "quad", "freq": 1, "surgery": 2, "inf_run": 3, "inf_kick": 3},
        {"desc": "complete groin tear", "body": "groin", "freq": 1, "surgery": 2, "inf_run": 3},
        {"desc": "bilateral ACL tear", "body": "knee", "freq": 1, "reinjury": 2, "surgery": 2, "inf_run": 3, "inf_lateral": 3},
        {"desc": "complete Achilles rupture (mid-stride)", "body": "achilles", "freq": 1, "surgery": 2, "inf_run": 3, "inf_kick": 3},
    ],
}


# ──────────────────────────────────────────────────────────────
# INJURY CATALOG — Practice/training injuries (between games)
# ──────────────────────────────────────────────────────────────

_PRACTICE_INJURY = {
    "day_to_day": [
        {"desc": "tweaked knee in practice", "body": "knee", "freq": 4, "inf_run": 1},
        {"desc": "rolled ankle in warmups", "body": "ankle", "freq": 5, "inf_run": 1},
        {"desc": "sore shoulder from drills", "body": "shoulder", "freq": 3, "nagging": 1, "inf_lateral": 1},
        {"desc": "minor back stiffness", "body": "back", "freq": 4, "nagging": 1, "inf_run": 1},
        {"desc": "jammed thumb in drill", "body": "hand", "freq": 3, "inf_lateral": 1},
        {"desc": "mild forearm stiffness", "body": "forearm", "freq": 2, "nagging": 1, "inf_lateral": 1},
        {"desc": "sore hip from conditioning", "body": "hip", "freq": 3, "nagging": 1, "inf_run": 1},
        {"desc": "finger discomfort", "body": "hand", "freq": 3, "inf_lateral": 1},
        {"desc": "neck stiffness from drills", "body": "neck", "freq": 2, "nagging": 1},
        {"desc": "minor shoulder strain", "body": "shoulder", "freq": 3, "nagging": 1, "inf_lateral": 1},
        {"desc": "bruised toenail", "body": "foot", "freq": 2, "inf_run": 1},
        {"desc": "mild calf cramp (conditioning)", "body": "calf", "freq": 4, "inf_run": 1},
        {"desc": "blistered feet", "body": "foot", "freq": 3, "inf_run": 1},
    ],
    "minor": [
        {"desc": "ankle sprain (practice)", "body": "ankle", "freq": 5, "reinjury": 1, "inf_run": 2},
        {"desc": "hamstring pull (conditioning)", "body": "hamstring", "freq": 5, "reinjury": 1, "nagging": 1, "inf_run": 2},
        {"desc": "shoulder impingement", "body": "shoulder", "freq": 3, "reinjury": 1, "nagging": 1, "inf_lateral": 2},
        {"desc": "knee hyperextension (practice)", "body": "knee", "freq": 2, "reinjury": 1, "inf_run": 2},
        {"desc": "shoulder tendinitis", "body": "shoulder", "freq": 3, "reinjury": 1, "nagging": 1, "inf_lateral": 2},
        {"desc": "wrist tendinitis", "body": "wrist", "freq": 2, "reinjury": 1, "nagging": 1, "inf_lateral": 1},
        {"desc": "sore elbow from drills", "body": "elbow", "freq": 3, "nagging": 1, "inf_lateral": 1},
        {"desc": "mild shoulder inflammation", "body": "shoulder", "freq": 4, "nagging": 1, "inf_lateral": 1},
        {"desc": "knee inflammation", "body": "knee", "freq": 4, "reinjury": 2, "nagging": 1, "inf_run": 2},
        {"desc": "rotator cuff strain", "body": "shoulder", "freq": 2, "reinjury": 1, "inf_lateral": 2},
        {"desc": "groin pull (agility drill)", "body": "groin", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 2},
        {"desc": "quad strain (sprints)", "body": "quad", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 2},
    ],
    "moderate": [
        {"desc": "ligament sprain (practice collision)", "body": "knee", "freq": 2, "reinjury": 1, "inf_run": 2},
        {"desc": "broken finger (practice)", "body": "hand", "freq": 2, "inf_lateral": 2},
        {"desc": "labrum aggravation", "body": "shoulder", "freq": 2, "reinjury": 2, "nagging": 1, "surgery": 1, "inf_lateral": 3},
        {"desc": "strained back (practice)", "body": "back", "freq": 3, "reinjury": 1, "nagging": 1, "inf_run": 2, "inf_kick": 1},
        {"desc": "knee bursitis", "body": "knee", "freq": 2, "nagging": 1, "inf_run": 2},
        {"desc": "lat strain", "body": "back", "freq": 2, "reinjury": 1, "inf_lateral": 2},
        {"desc": "shoulder strain", "body": "shoulder", "freq": 3, "reinjury": 1, "inf_lateral": 2},
        {"desc": "concussion (practice collision — no hard helmet)", "body": "head", "freq": 2, "reinjury": 2, "inf_run": 1, "inf_kick": 1, "inf_lateral": 1, "min_weeks": 3, "max_weeks": 5},
        {"desc": "hamstring tear (conditioning)", "body": "hamstring", "freq": 2, "reinjury": 2, "nagging": 1, "inf_run": 3, "min_weeks": 3, "max_weeks": 6},
    ],
    "major": [
        {"desc": "torn meniscus (practice)", "body": "knee", "freq": 2, "reinjury": 2, "surgery": 2, "inf_run": 3, "min_weeks": 6, "max_weeks": 10},
        {"desc": "broken foot (dropped weight)", "body": "foot", "freq": 1, "surgery": 1, "inf_run": 3, "inf_kick": 3, "min_weeks": 8, "max_weeks": 12},
        {"desc": "SLAP tear (shoulder)", "body": "shoulder", "freq": 1, "reinjury": 1, "surgery": 2, "inf_lateral": 3, "min_weeks": 8, "max_weeks": 12},
        {"desc": "shoulder labral tear", "body": "shoulder", "freq": 2, "reinjury": 1, "surgery": 2, "inf_lateral": 3, "min_weeks": 8, "max_weeks": 12},
        {"desc": "broken collarbone (practice)", "body": "collarbone", "freq": 1, "surgery": 1, "inf_lateral": 2, "min_weeks": 6, "max_weeks": 10},
    ],
    "severe": [
        {"desc": "ACL tear (practice)", "body": "knee", "freq": 2, "reinjury": 2, "surgery": 2, "inf_run": 3},
        {"desc": "neck injury (practice collision)", "body": "neck", "freq": 1, "surgery": 1, "inf_run": 3, "inf_lateral": 3},
        {"desc": "torn Achilles (conditioning)", "body": "achilles", "freq": 1, "surgery": 2, "inf_run": 3, "inf_kick": 3},
        {"desc": "patellar tendon rupture (weightlifting)", "body": "knee", "freq": 1, "surgery": 2, "inf_run": 3, "inf_kick": 3},
    ],
}


# ──────────────────────────────────────────────────────────────
# AVAILABILITY CATALOG — Off-field issues (collegiate context)
#
# Covers the full range of real college athlete availability:
# illness, academics, personal, family, mental health,
# disciplinary, and administrative issues.
# ──────────────────────────────────────────────────────────────

_OFF_FIELD = {
    "day_to_day": [
        # Illness
        {"desc": "cold", "body": "n/a", "freq": 5},
        {"desc": "minor illness", "body": "n/a", "freq": 5},
        {"desc": "stomach bug", "body": "n/a", "freq": 4},
        {"desc": "allergy flare-up", "body": "n/a", "freq": 3},
        {"desc": "migraine", "body": "n/a", "freq": 2, "nagging": 1},
        {"desc": "nausea", "body": "n/a", "freq": 2},
        {"desc": "dehydration", "body": "n/a", "freq": 2},
        {"desc": "heat exhaustion", "body": "n/a", "freq": 1},
        {"desc": "eye irritation", "body": "n/a", "freq": 1},
        {"desc": "earache", "body": "n/a", "freq": 1},
        # Academic / personal
        {"desc": "missed class — making up coursework", "body": "n/a", "freq": 3},
        {"desc": "exam conflicts — limited availability", "body": "n/a", "freq": 3},
        {"desc": "dental procedure", "body": "n/a", "freq": 1},
        {"desc": "skin rash", "body": "n/a", "freq": 1},
        {"desc": "sore throat", "body": "n/a", "freq": 4},
        {"desc": "fatigue / low energy", "body": "n/a", "freq": 3, "nagging": 1},
    ],
    "minor": [
        # Illness
        {"desc": "flu", "body": "n/a", "freq": 5},
        {"desc": "upper respiratory infection", "body": "n/a", "freq": 3},
        {"desc": "food poisoning", "body": "n/a", "freq": 3},
        {"desc": "COVID protocol", "body": "n/a", "freq": 2},
        {"desc": "sinus infection", "body": "n/a", "freq": 2},
        {"desc": "stomach virus", "body": "n/a", "freq": 3},
        {"desc": "viral infection", "body": "n/a", "freq": 3},
        {"desc": "conjunctivitis", "body": "n/a", "freq": 1},
        # Personal
        {"desc": "family emergency (brief)", "body": "n/a", "freq": 3},
        {"desc": "personal leave", "body": "n/a", "freq": 3},
        {"desc": "bereavement leave", "body": "n/a", "freq": 2},
        {"desc": "strep throat", "body": "n/a", "freq": 2},
        {"desc": "bronchitis", "body": "n/a", "freq": 2},
        {"desc": "ear infection", "body": "n/a", "freq": 1},
        {"desc": "wisdom tooth extraction", "body": "n/a", "freq": 1, "min_weeks": 1, "max_weeks": 2},
    ],
    "moderate": [
        # Illness / medical
        {"desc": "mononucleosis", "body": "n/a", "freq": 1, "min_weeks": 4, "max_weeks": 8},
        {"desc": "pneumonia", "body": "n/a", "freq": 1, "min_weeks": 3, "max_weeks": 6},
        {"desc": "iron deficiency — recovery program", "body": "n/a", "freq": 2},
        {"desc": "concussion (non-sport related)", "body": "n/a", "freq": 1, "reinjury": 1},
        # Academic / disciplinary
        {"desc": "academic probation — limited practice", "body": "n/a", "freq": 3},
        {"desc": "disciplinary suspension (1 game)", "body": "n/a", "freq": 2},
        {"desc": "team rules violation — 2-game suspension", "body": "n/a", "freq": 2, "min_weeks": 2, "max_weeks": 3},
        # Personal / mental health
        {"desc": "extended personal leave", "body": "n/a", "freq": 2},
        {"desc": "mental health break", "body": "n/a", "freq": 3},
        {"desc": "family hardship leave", "body": "n/a", "freq": 2},
        # Administrative
        {"desc": "visa issues — delayed return", "body": "n/a", "freq": 1, "min_weeks": 3, "max_weeks": 6},
        {"desc": "eating disorder treatment", "body": "n/a", "freq": 1, "min_weeks": 4, "max_weeks": 8},
        {"desc": "substance abuse program", "body": "n/a", "freq": 1, "min_weeks": 3, "max_weeks": 6},
        {"desc": "appendicitis", "body": "n/a", "freq": 1, "surgery": 2, "min_weeks": 3, "max_weeks": 5},
    ],
    "major": [
        # Academic
        {"desc": "academic ineligibility (semester)", "body": "n/a", "freq": 2, "min_weeks": 6, "max_weeks": 10},
        {"desc": "grade appeal in progress — held out", "body": "n/a", "freq": 1, "min_weeks": 4, "max_weeks": 8},
        # Personal / family
        {"desc": "extended family hardship", "body": "n/a", "freq": 2},
        {"desc": "stress-related medical leave", "body": "n/a", "freq": 2, "min_weeks": 6, "max_weeks": 10},
        # Disciplinary
        {"desc": "conduct violation — multi-game suspension", "body": "n/a", "freq": 1, "min_weeks": 4, "max_weeks": 8},
        {"desc": "team suspension — conduct detrimental", "body": "n/a", "freq": 1, "min_weeks": 4, "max_weeks": 8},
        # Medical
        {"desc": "surgery (non-sport condition)", "body": "n/a", "freq": 1, "min_weeks": 6, "max_weeks": 12},
        {"desc": "study abroad conflict — extended absence", "body": "n/a", "freq": 1, "min_weeks": 6, "max_weeks": 10},
        {"desc": "long-term mental health treatment", "body": "n/a", "freq": 1, "min_weeks": 6, "max_weeks": 12},
    ],
    "severe": [
        {"desc": "entered transfer portal", "body": "n/a", "freq": 3},
        {"desc": "medical retirement (chronic condition)", "body": "n/a", "freq": 1},
        {"desc": "left program (personal reasons)", "body": "n/a", "freq": 2},
        {"desc": "academic dismissal", "body": "n/a", "freq": 1},
        {"desc": "indefinite suspension — under investigation", "body": "n/a", "freq": 1},
        {"desc": "medical disqualification", "body": "n/a", "freq": 1},
        {"desc": "withdrew from university", "body": "n/a", "freq": 1},
        {"desc": "declared for professional draft", "body": "n/a", "freq": 1},
        {"desc": "permanent academic ineligibility", "body": "n/a", "freq": 1},
    ],
}


# ──────────────────────────────────────────────────────────────
# INJURY CATEGORY WEIGHTS — How often each category occurs
# ──────────────────────────────────────────────────────────────

# Weekly between-game roll: what kind of issue does a player develop?
WEEKLY_CATEGORY_WEIGHTS = {
    "on_field_contact":    0.30,   # Lingering from last game
    "on_field_noncontact": 0.20,   # Soft tissue from game exertion
    "practice":            0.30,   # Practice injuries
    "off_field":           0.20,   # Non-sport issues
}

_CATEGORY_CATALOG = {
    "on_field_contact":    _ON_FIELD_CONTACT,
    "on_field_noncontact": _ON_FIELD_NONCONTACT,
    "practice":            _PRACTICE_INJURY,
    "off_field":           _OFF_FIELD,
}

# In-game injury category weights (only physical categories apply mid-game)
IN_GAME_CATEGORY_WEIGHTS = {
    "on_field_contact":    0.65,
    "on_field_noncontact": 0.35,
}


# ──────────────────────────────────────────────────────────────
# TIER DISTRIBUTION
# ──────────────────────────────────────────────────────────────

# Weekly between-game tier probabilities
WEEKLY_TIER_WEIGHTS = {
    "day_to_day": 0.40,
    "minor":      0.30,
    "moderate":   0.18,
    "major":      0.08,
    "severe":     0.04,
}

# In-game tier probabilities (skew toward less severe — most in-game
# injuries are minor, the serious ones are rarer)
IN_GAME_TIER_WEIGHTS = {
    "day_to_day": 0.50,
    "minor":      0.28,
    "moderate":   0.14,
    "major":      0.05,
    "severe":     0.03,
}


# ──────────────────────────────────────────────────────────────
# POSITION INJURY RISK — Base weekly probability per position
# ──────────────────────────────────────────────────────────────

_BASE_INJURY_PROB = {
    "Viper":           0.032,   # High-touch, but agile players avoid worst hits
    "Zeroback":        0.030,   # Kicking specialists — leg/foot stress
    "Halfback":        0.038,   # Heavy contact, ball carriers
    "Wingback":        0.036,   # Speed players, soft tissue risk
    "Slotback":        0.033,   # Route runners, moderate contact
    "Keeper":          0.028,   # Last line of defense, less frequent contact
    "Offensive Line":  0.040,   # Trench warfare, most contact per play
    "Defensive Line":  0.038,   # Same
    "default":         0.032,
}

# In-game injury probability per play for involved players
# Scales by play type violence
IN_GAME_INJURY_RATE = {
    "run":         0.004,   # ~0.4% per play for ball carrier
    "lateral":     0.003,   # Slightly less — more evasive
    "kick_pass":   0.002,   # Kicker has low risk, receiver moderate
    "punt":        0.002,   # Returner risk
    "drop_kick":   0.002,
    "tackle":      0.003,   # Tackler risk
    "default":     0.002,
}

# Position groups that can substitute for each other
POSITION_FLEXIBILITY = {
    "Viper":          ["Viper", "Wingback", "Halfback"],
    "Zeroback":       ["Zeroback", "Slotback", "Halfback"],
    "Halfback":       ["Halfback", "Wingback", "Slotback"],
    "Wingback":       ["Wingback", "Halfback", "Slotback"],
    "Slotback":       ["Slotback", "Wingback", "Halfback"],
    "Keeper":         ["Keeper", "Defensive Line"],
    "Offensive Line": ["Offensive Line", "Defensive Line"],
    "Defensive Line": ["Defensive Line", "Offensive Line"],
}

# Stat penalty when playing out of position
OUT_OF_POSITION_PENALTY = 0.85  # 15% reduction in effective stats


# ──────────────────────────────────────────────────────────────
# INJURY DATACLASS
# ──────────────────────────────────────────────────────────────

@dataclass
class Injury:
    """A single player injury or availability issue.

    Extended with OOTP-style metadata for realism:
    - reinjury chance, nagging flag, surgery requirement
    - per-attribute influence (running, kicking, lateral)
    """
    player_name: str
    team_name: str
    position: str
    tier: str                   # "day_to_day" | "minor" | "moderate" | "major" | "severe"
    category: str               # "on_field_contact" | "on_field_noncontact" | "practice" | "off_field"
    description: str
    body_part: str              # "knee", "ankle", "n/a" for off-field, etc.
    week_injured: int
    weeks_out: int              # 0 for DTD who play through, 99 for season-ending
    week_return: int            # week player is available again; 9999 = season-ending
    original_weeks_out: int = -1  # original timeline (-1 = not yet set)
    recovery_note: str = ""     # "ahead of schedule", "suffered setback", etc.
    in_game: bool = False       # True if this happened during a game
    # Extended metadata
    reinjury_chance: int = 0    # 0 = none, 1 = sometimes, 2 = often
    nagging: bool = False       # True = can flare up / linger after return
    requires_surgery: int = 0   # 0 = no, 1 = sometimes, 2 = yes
    inf_run: int = 0            # 0-3 influence on running/speed when playing through
    inf_kick: int = 0           # 0-3 influence on kicking
    inf_lateral: int = 0        # 0-3 influence on lateral skill / agility

    @property
    def is_season_ending(self) -> bool:
        return self.weeks_out >= 99

    @property
    def is_day_to_day(self) -> bool:
        return self.tier == "day_to_day"

    @property
    def is_off_field(self) -> bool:
        return self.category == "off_field"

    @property
    def display(self) -> str:
        tag = ""
        if self.is_season_ending:
            tag = " [OUT FOR SEASON]"
        elif self.is_day_to_day:
            tag = " [DAY-TO-DAY]"
        else:
            tag = f" [OUT {self.weeks_out} wk(s)]"
        prefix = ""
        if self.in_game:
            prefix = "(in-game) "
        return f"{self.player_name} ({self.position}) — {prefix}{self.description}{tag}"

    @property
    def game_status(self) -> str:
        """Return game-day status label."""
        if self.is_season_ending:
            return "OUT"
        if self.tier == "major":
            return "OUT"
        if self.tier == "moderate":
            return "OUT"
        if self.tier == "minor":
            return "DOUBTFUL"
        if self.tier == "day_to_day":
            return "QUESTIONABLE"
        return "OUT"

    def to_dict(self) -> dict:
        return {
            "player_name": self.player_name,
            "team_name": self.team_name,
            "position": self.position,
            "tier": self.tier,
            "category": self.category,
            "description": self.description,
            "body_part": self.body_part,
            "week_injured": self.week_injured,
            "weeks_out": self.weeks_out,
            "original_weeks_out": self.original_weeks_out if self.original_weeks_out >= 0 else self.weeks_out,
            "week_return": self.week_return,
            "is_season_ending": self.is_season_ending,
            "in_game": self.in_game,
            "game_status": self.game_status,
            "recovery_note": self.recovery_note,
            "reinjury_chance": self.reinjury_chance,
            "nagging": self.nagging,
            "requires_surgery": self.requires_surgery,
            "inf_run": self.inf_run,
            "inf_kick": self.inf_kick,
            "inf_lateral": self.inf_lateral,
        }


# ──────────────────────────────────────────────────────────────
# IN-GAME INJURY EVENT (returned to game engine)
# ──────────────────────────────────────────────────────────────

@dataclass
class InGameInjuryEvent:
    """Describes an injury that just occurred during a play."""
    player_name: str
    position: str
    description: str
    tier: str
    category: str
    is_season_ending: bool
    substitute_name: Optional[str] = None
    substitute_position: Optional[str] = None
    is_out_of_position: bool = False

    @property
    def narrative(self) -> str:
        severity = "OUT FOR SEASON" if self.is_season_ending else self.tier.replace("_", "-").upper()
        line = f"INJURY: {self.player_name} ({self.position}) — {self.description} [{severity}]"
        if self.substitute_name:
            oop = " (out of position)" if self.is_out_of_position else ""
            line += f" | SUB IN: {self.substitute_name} ({self.substitute_position}){oop}"
        return line


# ──────────────────────────────────────────────────────────────
# INJURY TRACKER
# ──────────────────────────────────────────────────────────────

@dataclass
class InjuryTracker:
    """
    Manages all injuries and availability across a season.

    active_injuries: team_name -> list of active Injury objects
    season_log: full history of every injury/issue this season
    """
    active_injuries: Dict[str, List[Injury]] = field(default_factory=dict)
    season_log: List[Injury] = field(default_factory=list)
    rng: random.Random = field(default_factory=random.Random)

    def seed(self, s: int):
        self.rng.seed(s)

    # ── Tier / Category rolling ──────────────────────────

    def _roll_tier(self, weights: Dict[str, float] = None) -> str:
        """Roll an injury tier using weighted probabilities."""
        w = weights or WEEKLY_TIER_WEIGHTS
        tiers = list(w.keys())
        probs = list(w.values())
        return self.rng.choices(tiers, weights=probs, k=1)[0]

    def _roll_category(self, weights: Dict[str, float] = None) -> str:
        """Roll which injury category (contact, non-contact, practice, off-field)."""
        w = weights or WEEKLY_CATEGORY_WEIGHTS
        cats = list(w.keys())
        probs = list(w.values())
        return self.rng.choices(cats, weights=probs, k=1)[0]

    def _pick_flavor(self, category: str, tier: str) -> Tuple[str, str]:
        """Pick a specific injury description and body part from the catalog."""
        entry = self._pick_entry(category, tier)
        return entry["desc"], entry["body"]

    def _pick_entry(self, category: str, tier: str) -> Dict:
        """Pick a full catalog entry (with all metadata) for an injury.

        Uses frequency weighting: higher freq entries are more likely.
        """
        catalog = _CATEGORY_CATALOG.get(category, _ON_FIELD_CONTACT)
        tier_entries = catalog.get(tier, catalog.get("minor", []))
        if not tier_entries:
            return {"desc": "undisclosed injury", "body": "undisclosed"}
        # Weight by frequency (1-5), defaulting to 3
        weights = [e.get("freq", 3) for e in tier_entries]
        return self.rng.choices(tier_entries, weights=weights, k=1)[0]

    # ── Base probability ─────────────────────────────────

    def _base_prob_for_position(self, position: str) -> float:
        return _BASE_INJURY_PROB.get(position, _BASE_INJURY_PROB["default"])

    # ── Create an injury ─────────────────────────────────

    def _make_injury(self, player, team_name: str, week: int,
                     category: str = None, tier: str = None,
                     in_game: bool = False) -> Injury:
        if tier is None:
            tier_weights = IN_GAME_TIER_WEIGHTS if in_game else WEEKLY_TIER_WEIGHTS
            tier = self._roll_tier(tier_weights)
        if category is None:
            cat_weights = IN_GAME_CATEGORY_WEIGHTS if in_game else WEEKLY_CATEGORY_WEIGHTS
            category = self._roll_category(cat_weights)

        entry = self._pick_entry(category, tier)
        description = entry["desc"]
        body_part = entry["body"]

        # Use per-entry week overrides if provided, else tier defaults
        min_wks = entry.get("min_weeks", INJURY_TIER_WEEKS[tier][0])
        max_wks = entry.get("max_weeks", INJURY_TIER_WEEKS[tier][1])

        if tier == "severe":
            weeks_out = 99
            week_return = 9999
        elif tier == "day_to_day":
            weeks_out = self.rng.choice([0, 1])
            week_return = week + weeks_out
        else:
            weeks_out = self.rng.randint(min_wks, max_wks)
            week_return = week + weeks_out

        # Check re-injury: if player had same body part injury before,
        # boost severity slightly
        reinjury = entry.get("reinjury", 0)
        if reinjury > 0:
            prior_same = [
                inj for inj in self.season_log
                if inj.player_name == player.name and inj.body_part == body_part
            ]
            if prior_same and reinjury >= 1:
                # Re-injury: add 1-2 weeks to recovery
                extra = self.rng.randint(1, 1 + reinjury)
                if tier not in ("severe", "day_to_day"):
                    weeks_out += extra
                    week_return = week + weeks_out

        return Injury(
            player_name=player.name,
            team_name=team_name,
            position=player.position,
            tier=tier,
            category=category,
            description=description,
            body_part=body_part,
            week_injured=week,
            weeks_out=weeks_out,
            week_return=week_return,
            original_weeks_out=weeks_out,
            recovery_note="",
            in_game=in_game,
            reinjury_chance=reinjury,
            nagging=bool(entry.get("nagging", 0)),
            requires_surgery=entry.get("surgery", 0),
            inf_run=entry.get("inf_run", 0),
            inf_kick=entry.get("inf_kick", 0),
            inf_lateral=entry.get("inf_lateral", 0),
        )

    # ── Weekly processing (between games) ────────────────

    def process_week(self, week: int, teams: Dict, standings: Dict = None) -> List[Injury]:
        """
        Roll for new injuries/availability issues at the start of a week.

        Probability modified by:
        - Player stamina (lower = higher risk)
        - Season fatigue (more games played = higher risk)
        - Position (linemen/backs at higher risk)

        Returns list of new injuries this week.
        """
        new_injuries: List[Injury] = []

        for team_name, team in teams.items():
            if team_name not in self.active_injuries:
                self.active_injuries[team_name] = []

            current_active = [
                inj for inj in self.active_injuries[team_name]
                if week < inj.week_return
            ]
            already_out = {inj.player_name for inj in current_active}

            games_played = 0
            if standings and team_name in standings:
                games_played = standings[team_name].games_played

            fatigue_mult = 1.0 + min(0.3, games_played * 0.02)

            for player in team.players:
                if player.name in already_out:
                    continue

                base_prob = self._base_prob_for_position(player.position)
                stamina_mod = max(0.5, (100 - player.stamina) / 100.0) * 0.5
                prob = base_prob * (1.0 + stamina_mod) * fatigue_mult

                if self.rng.random() < prob:
                    injury = self._make_injury(player, team_name, week)
                    self.active_injuries[team_name].append(injury)
                    self.season_log.append(injury)
                    new_injuries.append(injury)

        return new_injuries

    def resolve_week(self, week: int):
        """Remove recovered players and apply recovery variance.

        Each week, injured players may:
        - Return early (~25% chance when within 1 week of return date)
        - Return early (~15% chance when within 2 weeks)
        - Suffer a setback (~8% chance, adds 1-3 weeks)
        Season-ending and DTD injuries are excluded from variance.
        """
        for team_name in list(self.active_injuries.keys()):
            still_active = []
            for inj in self.active_injuries[team_name]:
                if inj.week_return <= week:
                    continue

                if inj.is_season_ending or inj.is_day_to_day:
                    still_active.append(inj)
                    continue

                weeks_remaining = inj.week_return - week
                original = inj.original_weeks_out if inj.original_weeks_out >= 0 else inj.weeks_out

                if weeks_remaining <= 1 and original >= 2:
                    if self.rng.random() < 0.25:
                        inj.week_return = week
                        inj.weeks_out = week - inj.week_injured
                        inj.recovery_note = "Cleared early — ahead of schedule"
                        continue
                elif weeks_remaining <= 2 and original >= 3:
                    if self.rng.random() < 0.15:
                        inj.week_return = week
                        inj.weeks_out = week - inj.week_injured
                        inj.recovery_note = "Returned ahead of schedule"
                        continue

                if weeks_remaining >= 2 and original >= 3:
                    if self.rng.random() < 0.08:
                        extra = self.rng.randint(1, 3)
                        inj.week_return += extra
                        inj.weeks_out += extra
                        inj.recovery_note = f"Suffered setback — out {extra} extra week(s)"

                if not inj.recovery_note and original >= 2:
                    elapsed = week - inj.week_injured
                    if elapsed >= original * 0.5:
                        inj.recovery_note = "Progressing on schedule"

                still_active.append(inj)

            self.active_injuries[team_name] = still_active

    def resolve_week_bye(self, week: int, team_name: str):
        """Enhanced recovery for a team on a bye week.

        Bye weeks give players extra rest and treatment time.  Effects:
        - 40% chance any non-season-ending injury shaves 1 week off its timeline
        - Players within 1 week of return are auto-cleared
        - No setback risk (the whole point of a bye is safe recovery)
        """
        injuries = self.active_injuries.get(team_name, [])
        still_active = []
        for inj in injuries:
            if inj.week_return <= week:
                # Already recovered
                continue
            if inj.is_season_ending:
                still_active.append(inj)
                continue
            if inj.is_day_to_day:
                # DTD players are cleared on bye weeks
                inj.recovery_note = "Cleared during bye week"
                continue

            weeks_remaining = inj.week_return - week
            if weeks_remaining <= 1:
                # Close enough — bye week clears them
                inj.week_return = week
                inj.weeks_out = week - inj.week_injured
                inj.recovery_note = "Cleared during bye week rest"
                continue

            # 40% chance to shave a week off recovery
            if self.rng.random() < 0.40:
                inj.week_return -= 1
                inj.weeks_out = max(0, inj.weeks_out - 1)
                inj.recovery_note = "Bye week rest — ahead of schedule"

            still_active.append(inj)

        self.active_injuries[team_name] = still_active

    # ── In-game injury roll ──────────────────────────────

    def roll_in_game_injury(self, player, team_name: str, week: int,
                            play_type: str = "default") -> Optional[Injury]:
        """
        Roll for an in-game injury on a specific player after a play.

        Returns an Injury if the player got hurt, None otherwise.
        Called by the game engine after contact plays.
        """
        rate = IN_GAME_INJURY_RATE.get(play_type, IN_GAME_INJURY_RATE["default"])

        # Fatigue increases in-game injury risk
        current_stamina = getattr(player, 'current_stamina', 100.0)
        if current_stamina < 50:
            rate *= 1.5
        elif current_stamina < 70:
            rate *= 1.2

        # Low base stamina attribute = more fragile
        base_stamina = getattr(player, 'stamina', 75)
        if base_stamina < 65:
            rate *= 1.3
        elif base_stamina > 85:
            rate *= 0.8

        if self.rng.random() < rate:
            injury = self._make_injury(player, team_name, week, in_game=True)
            self.active_injuries.setdefault(team_name, []).append(injury)
            self.season_log.append(injury)
            return injury

        return None

    # ── Query methods ────────────────────────────────────

    def get_active_injuries(self, team_name: str, week: int) -> List[Injury]:
        """Return currently active injuries for a team at a given week."""
        return [
            inj for inj in self.active_injuries.get(team_name, [])
            if week < inj.week_return
        ]

    def get_unavailable_names(self, team_name: str, week: int) -> Set[str]:
        """Return set of player names who cannot play this week.

        DTD players with weeks_out=0 are NOT included (they play through it).
        """
        names = set()
        for inj in self.get_active_injuries(team_name, week):
            if inj.weeks_out > 0:
                names.add(inj.player_name)
        return names

    def get_dtd_names(self, team_name: str, week: int) -> Set[str]:
        """Return set of player names who are day-to-day (playing through injury)."""
        names = set()
        for inj in self.get_active_injuries(team_name, week):
            if inj.is_day_to_day and inj.weeks_out == 0:
                names.add(inj.player_name)
        return names

    def get_team_injury_penalties(self, team_name: str, week: int) -> Dict[str, float]:
        """
        Return performance penalty modifiers for a team due to injuries.

        Returns dict with keys:
            "yards_penalty"   – multiplicative modifier (e.g. 0.95 = 5% reduction)
            "kick_penalty"    – modifier for kicking effectiveness
            "lateral_penalty" – modifier for lateral chain success
        """
        active = self.get_active_injuries(team_name, week)
        if not active:
            return {"yards_penalty": 1.0, "kick_penalty": 1.0, "lateral_penalty": 1.0}

        total_penalty = 0.0
        kick_penalty = 0.0
        lateral_penalty = 0.0

        for inj in active:
            sev = INJURY_SEVERITY_PENALTY[inj.tier]
            total_penalty += sev

            pos = inj.position.lower()
            if "zero" in pos or "safety" in pos:
                kick_penalty += sev * 0.6
            if "viper" in pos or "halfback" in pos or "wingback" in pos:
                lateral_penalty += sev * 0.5

        return {
            "yards_penalty": round(1.0 - total_penalty, 3),
            "kick_penalty": round(1.0 - kick_penalty, 3),
            "lateral_penalty": round(1.0 - lateral_penalty, 3),
        }

    # ── Reporting ────────────────────────────────────────

    def get_season_injury_report(self) -> Dict[str, List[dict]]:
        """Return all injuries by team for a season summary."""
        report: Dict[str, List[dict]] = {}
        for inj in self.season_log:
            report.setdefault(inj.team_name, []).append(inj.to_dict())
        return report

    def get_season_injury_counts(self) -> Dict[str, int]:
        """Return total injury count per team for the season."""
        counts: Dict[str, int] = {}
        for inj in self.season_log:
            counts[inj.team_name] = counts.get(inj.team_name, 0) + 1
        return counts

    def get_injury_report_by_category(self) -> Dict[str, Dict[str, int]]:
        """Return injury counts broken down by category for each team."""
        report: Dict[str, Dict[str, int]] = {}
        for inj in self.season_log:
            team_cats = report.setdefault(inj.team_name, {})
            team_cats[inj.category] = team_cats.get(inj.category, 0) + 1
        return report

    def display_injury_report(self, team_name: str, week: int):
        """Print a human-readable injury report for a team."""
        active = self.get_active_injuries(team_name, week)
        if not active:
            print(f"  {team_name}: No active injuries")
            return
        print(f"\n  {team_name} INJURY REPORT (Week {week})")
        print(f"  {'-' * 60}")
        for inj in sorted(active, key=lambda i: ("OUT" if i.tier != "day_to_day" else "DTD", i.player_name)):
            print(f"    [{inj.game_status:12s}] {inj.display}")


# ──────────────────────────────────────────────────────────────
# SUBSTITUTION SYSTEM
# ──────────────────────────────────────────────────────────────

def find_substitute(team_players: List, injured_player, unavailable_names: Set[str],
                    injured_in_game: Set[str] = None) -> Tuple[Optional[object], bool]:
    """
    Find the best available substitute for an injured player.

    Search order:
    1. Same position, best overall rating
    2. Flexible position (from POSITION_FLEXIBILITY), best overall
    3. Any available player

    Returns:
        (substitute_player, is_out_of_position)
        (None, False) if no substitute available
    """
    if injured_in_game is None:
        injured_in_game = set()

    excluded = unavailable_names | injured_in_game | {injured_player.name}
    available = [p for p in team_players if p.name not in excluded]

    if not available:
        return None, False

    pos = injured_player.position
    flex_chain = POSITION_FLEXIBILITY.get(pos, [pos])

    def _player_overall(p):
        return getattr(p, 'overall', (p.speed + p.stamina + p.kicking + p.lateral_skill + p.tackling) / 5)

    # 1. Same position
    same_pos = [p for p in available if p.position == pos]
    if same_pos:
        return max(same_pos, key=_player_overall), False

    # 2. Flexible positions
    for flex_pos in flex_chain[1:]:
        flex_candidates = [p for p in available if p.position == flex_pos]
        if flex_candidates:
            return max(flex_candidates, key=_player_overall), True

    # 3. Any available player (emergency — way out of position)
    return max(available, key=_player_overall), True


def filter_available_players(team_players: List, unavailable_names: Set[str],
                             dtd_names: Set[str] = None) -> List:
    """
    Return the list of players available for a game, filtering out
    injured/unavailable players. DTD players are included but with
    a flag set for reduced performance.

    This should be called before passing a team to the game engine.
    """
    dtd = dtd_names or set()
    available = []
    for p in team_players:
        if p.name in unavailable_names:
            continue
        if p.name in dtd:
            p._is_dtd = True
        available.append(p)
    return available
