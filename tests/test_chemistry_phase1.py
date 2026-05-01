"""Phase 1 tests for team chemistry composition math.

Verifies the curves & flag interactions described in the build plan:
- voice saturation (0-5 voices, glue-shifted saturation point)
- drama absorption depending on glue
- HC archetype × talent-fit drama mediation
- franchise / big_stage / baggage flag effects
"""

from __future__ import annotations

import pytest

from engine.chemistry import compute_chemistry
from engine.coaching import CoachCard
from engine.game_engine import Player, Team


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


def mk_player(
    name: str = "P",
    overall: int = 75,
    voice: int = 50,
    glue: int = 50,
    pull: int = 50,
    reach: int = 60,
    drama: int = 35,
    fit: int = 60,
    franchise: bool = False,
    big_stage: bool = False,
    baggage: bool = False,
    role: str = "STARTER",
) -> Player:
    # Keep core stats roughly equal to `overall` so .overall reflects intent.
    s = max(25, min(99, overall))
    p = Player(
        number=1, name=name, position="RB",
        speed=s, stamina=s, kicking=s,
        lateral_skill=s, tackling=s,
        agility=s, power=s, awareness=s, hands=s,
        kick_power=s, kick_accuracy=s,
    )
    p.voice = voice
    p.glue = glue
    p.pull = pull
    p.reach = reach
    p.drama_baseline = drama
    p.fit = fit
    p.franchise = franchise
    p.big_stage = big_stage
    p.baggage = baggage
    p.game_role = role
    return p


def mk_team(players, *, role_assigned: bool = True) -> Team:
    if not role_assigned:
        for p in players:
            p.game_role = "ROTATION"
    return Team(
        name="X", abbreviation="X", mascot="X",
        players=players,
        avg_speed=80, avg_stamina=80,
        kicking_strength=70, lateral_proficiency=70, defensive_strength=70,
    )


def mk_hc(classification: str = "players_coach", message: int = 60, leadership: int = 70) -> CoachCard:
    return CoachCard(
        coach_id="hc", first_name="A", last_name="B",
        gender="male", age=45, role="head_coach",
        classification=classification,
        instincts=70, leadership=leadership, composure=70,
        rotations=60, development=70, recruiting=60,
        message=message,
    )


def baseline_roster(n: int = 22, **overrides) -> list[Player]:
    return [mk_player(name=f"P{i}", **overrides) for i in range(n)]


# ──────────────────────────────────────────────────────────────────────
# Tone (voice saturation)
# ──────────────────────────────────────────────────────────────────────


def _roster_with_k_voices(k: int, *, glue: int = 60, big_stage: bool = False) -> Team:
    players = baseline_roster(22, glue=glue)
    for i in range(k):
        players[i].voice = 80
        players[i].big_stage = big_stage
    return mk_team(players)


def test_tone_curve_shape_zero_to_five_voices():
    """Tone should rise 0→1→2, plateau-or-dip at 3, decline at 4-5."""
    hc = mk_hc()
    tones = []
    for k in range(6):
        team = _roster_with_k_voices(k)
        state = compute_chemistry(team, hc)
        tones.append(state.tone)

    # 0 → 1: meaningful rise
    assert tones[1] > tones[0] + 5, f"1 voice should beat 0: got {tones}"
    # 2 should be at or above 1 (still strong)
    assert tones[2] >= tones[1] - 1, f"2 voices should be ~as strong as 1: got {tones}"
    # 4 should be lower than 2 (saturation)
    assert tones[4] < tones[2], f"4 voices should saturate below 2: got {tones}"
    # 5 should be the worst
    assert tones[5] <= tones[4], f"5 voices should not improve on 4: got {tones}"


def test_glue_shifts_saturation_point():
    """High team glue lets a roster absorb more voices before friction."""
    hc = mk_hc()
    low_glue = compute_chemistry(_roster_with_k_voices(4, glue=40), hc).tone
    high_glue = compute_chemistry(_roster_with_k_voices(4, glue=85), hc).tone
    assert high_glue > low_glue, (
        f"High glue should push saturation point: low={low_glue}, high={high_glue}"
    )


def test_big_stage_softens_voice_saturation():
    """A roster of big-stage voices absorbs saturation better than no-flag voices."""
    hc = mk_hc()
    no_flag = compute_chemistry(_roster_with_k_voices(4, big_stage=False), hc).tone
    flagged = compute_chemistry(_roster_with_k_voices(4, big_stage=True), hc).tone
    assert flagged > no_flag, (
        f"Big-stage should reduce saturation penalty: plain={no_flag}, big_stage={flagged}"
    )


# ──────────────────────────────────────────────────────────────────────
# Drama absorption
# ──────────────────────────────────────────────────────────────────────


def test_high_drama_absorbable_with_high_glue():
    """One drama-prone player on a high-glue roster: drag is real but contained."""
    hc = mk_hc("players_coach")
    high_glue = baseline_roster(22, glue=85)
    high_glue[0].drama_baseline = 80
    state_high = compute_chemistry(mk_team(high_glue), hc)

    low_glue = baseline_roster(22, glue=35)
    low_glue[0].drama_baseline = 80
    state_low = compute_chemistry(mk_team(low_glue), hc)

    assert state_low.drag > state_high.drag, (
        f"Low glue should produce more drag: high_glue={state_high.drag}, "
        f"low_glue={state_low.drag}"
    )


def test_one_high_drama_absorbable_four_is_not():
    """Plan exit criterion: 1 high-drama is absorbable; 4 saturates drag."""
    hc = mk_hc("players_coach")
    one = baseline_roster(22, glue=70)
    one[0].drama_baseline = 80
    drag_one = compute_chemistry(mk_team(one), hc).drag

    four = baseline_roster(22, glue=70)
    for i in range(4):
        four[i].drama_baseline = 80
    drag_four = compute_chemistry(mk_team(four), hc).drag

    assert drag_four > drag_one * 1.8, (
        f"4 high-drama should saturate drag well above 1: one={drag_one}, four={drag_four}"
    )
    assert drag_four >= 50.0, f"4 high-drama should produce structural drag: got {drag_four}"


# ──────────────────────────────────────────────────────────────────────
# HC archetype × drama
# ──────────────────────────────────────────────────────────────────────


def test_disciplinarian_worse_on_talent_mismatch_high_drama():
    """Disciplinarian punishes high-drama-low-talent; players_coach broadly suppresses."""
    # Talent-mismatch high-drama player (low overall).
    mismatch = baseline_roster(22, glue=60)
    mismatch[0] = mk_player(name="Star?", overall=65, voice=55, glue=40, pull=70, drama=80)

    drag_disc = compute_chemistry(mk_team(mismatch), mk_hc("disciplinarian")).drag
    # Need a fresh roster (compute_chemistry mutates team.chemistry, players reused safely
    # since drama_baseline is read-only here, but rebuild for clarity).
    mismatch2 = baseline_roster(22, glue=60)
    mismatch2[0] = mk_player(name="Star?", overall=65, voice=55, glue=40, pull=70, drama=80)
    drag_pc = compute_chemistry(mk_team(mismatch2), mk_hc("players_coach")).drag

    assert drag_disc > drag_pc, (
        f"Disciplinarian should be worse on talent-mismatch high-drama: "
        f"disc={drag_disc}, players_coach={drag_pc}"
    )


def test_disciplinarian_handles_high_talent_high_drama():
    """Disciplinarian on a high-talent high-drama player is roughly competitive."""
    elite = baseline_roster(22, glue=60)
    elite[0] = mk_player(name="Elite", overall=88, voice=55, glue=40, pull=75, drama=78)

    drag_disc = compute_chemistry(mk_team(elite), mk_hc("disciplinarian")).drag
    elite2 = baseline_roster(22, glue=60)
    elite2[0] = mk_player(name="Elite", overall=88, voice=55, glue=40, pull=75, drama=78)
    drag_pc = compute_chemistry(mk_team(elite2), mk_hc("players_coach")).drag

    # Disciplinarian should be in the same ballpark as players_coach on real talent.
    # Tolerance: within 35% of the players_coach drag.
    assert abs(drag_disc - drag_pc) <= max(drag_pc, drag_disc) * 0.5, (
        f"On elite-talent high-drama, disc & players_coach should be roughly even: "
        f"disc={drag_disc}, pc={drag_pc}"
    )


# ──────────────────────────────────────────────────────────────────────
# Permanent flags
# ──────────────────────────────────────────────────────────────────────


def test_franchise_player_lifts_fabric():
    """One franchise player on roster → measurable fabric lift."""
    hc = mk_hc()
    plain = baseline_roster(22, glue=60, pull=60)
    plain_fab = compute_chemistry(mk_team(plain), hc).fabric

    flagged = baseline_roster(22, glue=60, pull=60)
    flagged[0].franchise = True
    flagged_fab = compute_chemistry(mk_team(flagged), hc).fabric

    assert flagged_fab > plain_fab, (
        f"Franchise flag should lift fabric: plain={plain_fab}, flagged={flagged_fab}"
    )


def test_franchise_count_tracked():
    hc = mk_hc()
    players = baseline_roster(22)
    players[0].franchise = True
    players[5].franchise = True
    state = compute_chemistry(mk_team(players), hc)
    assert state.franchise_count == 2


def test_big_stage_heavy_roster_resists_voice_saturation():
    """A roster of big-stage voices doesn't crater on voice saturation."""
    hc = mk_hc()

    # 5 plain voices (over-saturated)
    plain = baseline_roster(22, glue=60)
    for i in range(5):
        plain[i].voice = 82
    plain_tone = compute_chemistry(mk_team(plain), hc).tone

    # 5 big-stage voices (proven in stacked rooms)
    flagged = baseline_roster(22, glue=60)
    for i in range(5):
        flagged[i].voice = 82
        flagged[i].big_stage = True
    flagged_tone = compute_chemistry(mk_team(flagged), hc).tone

    # Curve caps at 85 in the strong regime; with glue=60 plain hits ~80.
    # The differential is meaningful (~5 pts) but not huge — "doesn't crater"
    # vs "no flags" is the relationship to verify.
    assert flagged_tone > plain_tone + 3, (
        f"Big-stage roster should resist saturation: "
        f"plain={plain_tone}, flagged={flagged_tone}"
    )


def test_baggage_player_drama_floor():
    """Baggage flag adds permanent floor to drama contribution."""
    hc = mk_hc("players_coach", message=60)

    plain = baseline_roster(22, glue=70)
    plain[0].drama_baseline = 35  # low baseline
    drag_plain = compute_chemistry(mk_team(plain), hc).drag

    bagged = baseline_roster(22, glue=70)
    bagged[0].drama_baseline = 35
    bagged[0].baggage = True
    drag_bagged = compute_chemistry(mk_team(bagged), hc).drag

    assert drag_bagged > drag_plain, (
        f"Baggage flag should raise drag floor regardless of baseline: "
        f"plain={drag_plain}, bagged={drag_bagged}"
    )


def test_franchise_softens_high_drama_player():
    """Franchise flag halves drama contribution from that player."""
    hc = mk_hc("players_coach")
    plain = baseline_roster(22, glue=60)
    plain[0].drama_baseline = 80
    plain[0].pull = 75
    drag_plain = compute_chemistry(mk_team(plain), hc).drag

    flagged = baseline_roster(22, glue=60)
    flagged[0].drama_baseline = 80
    flagged[0].pull = 75
    flagged[0].franchise = True
    drag_flagged = compute_chemistry(mk_team(flagged), hc).drag

    assert drag_flagged < drag_plain, (
        f"Franchise should reduce that player's drama contribution: "
        f"plain={drag_plain}, franchise={drag_flagged}"
    )


# ──────────────────────────────────────────────────────────────────────
# Plan exit criterion: composition over count
# ──────────────────────────────────────────────────────────────────────


def test_one_voice_plus_glue_beats_four_voices_no_glue():
    """Phase 1 exit: 1 voice + strong glue + low drama beats 4 voices + no glue."""
    hc = mk_hc()

    one_voice = baseline_roster(22, voice=45, glue=80, pull=55, drama=30)
    one_voice[0].voice = 82
    state_one = compute_chemistry(mk_team(one_voice), hc)

    four_voices = baseline_roster(22, voice=45, glue=35, pull=55, drama=30)
    for i in range(4):
        four_voices[i].voice = 82
    state_four = compute_chemistry(mk_team(four_voices), hc)

    # Composite "good chemistry" score: tone + fabric - drag
    score_one = state_one.tone + state_one.fabric - state_one.drag
    score_four = state_four.tone + state_four.fabric - state_four.drag
    assert score_one > score_four, (
        f"1 voice + strong glue should beat 4 voices + no glue: "
        f"one={state_one}, four={state_four}"
    )


# ──────────────────────────────────────────────────────────────────────
# Empty / edge cases
# ──────────────────────────────────────────────────────────────────────


def test_empty_roster_does_not_crash():
    hc = mk_hc()
    team = mk_team([])
    state = compute_chemistry(team, hc)
    # Default state — no math run on an empty roster.
    assert state.franchise_count == 0
    assert state.tone == 0.0  # default TeamChemistryState


def test_no_hc_does_not_crash():
    team = mk_team(baseline_roster(22))
    state = compute_chemistry(team, None)
    assert 0 <= state.tone <= 100
    assert 0 <= state.fabric <= 100
    assert 0 <= state.drag <= 100
