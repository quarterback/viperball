"""Team chemistry — composition math + generation (Phase 1).

Computes a `TeamChemistryState` from a roster + head coach. Chemistry is
read pregame and modulates `game_rhythm` (see `game_engine._kickoff`).

Layers:
- Stable attributes (voice/glue/pull/reach/drama_baseline/fit) live on Player.
- Permanent flags (franchise/big_stage/baggage) shape composition math.
- Coach archetype (chemistry_archetype, derived from classification) mediates
  drag and provides modifiers to drift in Phase 2.

The four outputs (tone, fabric, drag, tilt) all live on a 0-100 scale.
None of them dominates `game_rhythm` on its own — see `apply_chemistry_to_rhythm`.
"""

from __future__ import annotations

import random as _random_module
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from engine.game_engine import Player, Team, TeamChemistryState
    from engine.coaching import CoachCard


# ──────────────────────────────────────────────────────────────────────
# Player chemistry attribute generation
# ──────────────────────────────────────────────────────────────────────

# Distribution targets:
#   - Most players land in 40-60 current values (the unspectacular middle).
#   - ~10% have one stable attribute with ceiling 80+ (rare voices, high glue).
#   - ~5% have drama_baseline ceiling 75+ (the volatile ones).

_STABLE_ATTRS = ("voice", "glue", "pull", "reach")
_DRAMA_HIGH_CEILING_RATE = 0.05
_RARE_HIGH_CEILING_RATE = 0.10


def _roll_range(rng: "_random_module.Random", *, allow_high: bool = False) -> Tuple[int, int]:
    """Roll an innate range on the 25-95 scale.

    Range width is typically 30-50 points, anchored anywhere in the band.
    `allow_high` flags this attribute as one of the player's "high ceiling"
    attributes — ceiling lifts to 80-95.
    """
    width = rng.randint(30, 50)
    if allow_high:
        ceiling = rng.randint(80, 95)
    else:
        ceiling = rng.randint(60, 78)
    floor = max(25, ceiling - width)
    return (floor, ceiling)


def _roll_drama_range(rng: "_random_module.Random", *, allow_volatile: bool = False) -> Tuple[int, int]:
    """Drama ranges skew low — most players just aren't dramatic.

    A volatile player gets ceiling 75+ (the locker-room problem cases).
    """
    if allow_volatile:
        ceiling = rng.randint(75, 95)
        floor = max(25, ceiling - rng.randint(30, 50))
    else:
        ceiling = rng.randint(40, 60)
        floor = max(25, ceiling - rng.randint(15, 30))
    return (floor, ceiling)


def generate_chemistry_attributes(
    player: "Player",
    rng: Optional["_random_module.Random"] = None,
) -> None:
    """Roll innate ranges + initial current values for chemistry attrs.

    Called once at player creation. Mutates `player` in place. Idempotent
    re-calls would re-roll; only call on freshly generated players.
    """
    rng = rng or _random_module.Random()

    # Roll which attributes get high ceilings (~10% chance per attribute).
    # This is per-attribute, so a player could rarely get two high-ceiling traits.
    for attr in _STABLE_ATTRS:
        allow_high = rng.random() < _RARE_HIGH_CEILING_RATE
        rng_lo, rng_hi = _roll_range(rng, allow_high=allow_high)
        setattr(player, f"{attr}_range", (rng_lo, rng_hi))
        # Initial current value: uniformly in range, but biased toward middle.
        midpoint = (rng_lo + rng_hi) / 2
        spread = (rng_hi - rng_lo) / 2
        current = int(rng.gauss(midpoint, spread * 0.4))
        current = max(rng_lo, min(rng_hi, current))
        setattr(player, attr, current)

    # Drama gets its own roll — most players are in the low band.
    is_volatile = rng.random() < _DRAMA_HIGH_CEILING_RATE
    drama_lo, drama_hi = _roll_drama_range(rng, allow_volatile=is_volatile)
    player.drama_baseline_range = (drama_lo, drama_hi)
    drama_mid = (drama_lo + drama_hi) / 2
    drama_spread = (drama_hi - drama_lo) / 2
    drama_current = int(rng.gauss(drama_mid, drama_spread * 0.4))
    player.drama_baseline = max(drama_lo, min(drama_hi, drama_current))

    # Fit defaults to the middle of a generated range; gets recomputed
    # game-by-game in Phase 3. Range exists for future scheme-fit logic.
    fit_lo, fit_hi = _roll_range(rng, allow_high=False)
    player.fit_range = (fit_lo, fit_hi)
    fit_mid = (fit_lo + fit_hi) / 2
    player.fit = int(fit_mid)

    # Permanent flags always start False on freshly generated players.
    # They are earned in Phase 2; veteran imports may seed them post-hoc.
    player.franchise = False
    player.big_stage = False
    player.baggage = False


# ──────────────────────────────────────────────────────────────────────
# Playing-time weights
# ──────────────────────────────────────────────────────────────────────

_STARTER_WEIGHT = 1.0
_ROTATION_WEIGHT = 0.4
# When game_role has not been assigned, treat the top-N by overall as starters.
# 22 ≈ offense + defense first units.
_DEFAULT_STARTER_COUNT = 22


def playing_time_weighted_roster(team: "Team") -> List[Tuple["Player", float]]:
    """Return [(player, weight)] where weight is a proxy for chemistry voice.

    Uses `game_role` if set (post-pregame role assignment), otherwise falls
    back to overall-based starter identification.
    """
    players = list(team.players)
    if not players:
        return []

    has_role = any(getattr(p, "game_role", "ROTATION") == "STARTER" for p in players)
    if has_role:
        return [
            (p, _STARTER_WEIGHT if p.game_role == "STARTER" else _ROTATION_WEIGHT)
            for p in players
        ]

    ranked = sorted(players, key=lambda p: p.overall, reverse=True)
    starter_set = set(id(p) for p in ranked[:_DEFAULT_STARTER_COUNT])
    return [
        (p, _STARTER_WEIGHT if id(p) in starter_set else _ROTATION_WEIGHT)
        for p in players
    ]


# ──────────────────────────────────────────────────────────────────────
# Phase 3: Variable layer (per-game values)
# ──────────────────────────────────────────────────────────────────────


def compute_pregame_variables(
    player: "Player",
    *,
    contract_year: bool = False,
    team_losing_streak: int = 0,
    team_winning_streak: int = 0,
    recent_demotion: bool = False,
    recent_personal_achievement: bool = False,
    off_field_noise: int = 0,           # 0-3, scaled negative on head_current
    recent_strong_performance: bool = False,
    scheme_change_recency: int = 99,    # games since scheme change; <5 → fit penalty
    snap_share_actual: float = 0.5,
    snap_share_ideal: float = 0.5,
) -> None:
    """Populate `drama_current`, `head_current`, `fit_current` for this game.

    Called pregame after roster decisions are final but before chemistry
    composition. The composition math reads `drama_current` (not baseline)
    once Phase 3 is wired into compute_chemistry — see `_drag_phase3`.
    """
    # ── drama_current ───────────────────────────────────────────
    drama = player.drama_baseline
    if contract_year and team_losing_streak >= 3:
        drama += 15
    if recent_demotion:
        drama += 10
    if team_winning_streak >= 3:
        drama -= 10
    if recent_personal_achievement:
        drama -= 8

    # Permanent flag caps/floors.
    if player.franchise:
        drama = min(drama, 60)  # icons can't go fully toxic
    if player.baggage:
        drama = max(drama, 50)  # never below the baggage floor

    player.drama_current = max(0, min(100, drama))

    # ── head_current ───────────────────────────────────────────
    # Veterans (8+ seasons) have suppressed variance.
    is_veteran = player.seasons_in_career >= 8
    head = 50
    if recent_strong_performance:
        head += 12 if not is_veteran else 8
    head -= off_field_noise * (8 if not is_veteran else 5)
    player.head_current = max(0, min(100, head))

    # ── fit_current ────────────────────────────────────────────
    # Compare actual usage to ideal. Penalty for recent scheme change.
    diff = abs(snap_share_actual - snap_share_ideal)
    fit = player.fit - int(round(diff * 60))  # diff of 0.3 → -18
    if scheme_change_recency < 5:
        fit -= 10 - (2 * scheme_change_recency)  # fades over ~5 games
    floor, ceiling = player.fit_range
    player.fit_current = max(floor, min(ceiling, fit))


# ──────────────────────────────────────────────────────────────────────
# Composition curves
# ──────────────────────────────────────────────────────────────────────

# Voice saturation: yield as a function of "effective voices" (count of
# voice >= 70 players, weighted by playing time). big_stage flag halves
# a player's contribution to saturation since they've proven they can
# play in stacked rooms.
#
# Tuning: 1 voice strongest, 2 still strong, 3 flat, 4+ declining.
def _voice_saturation_yield(effective_voices: float, glue_total: float) -> float:
    """Map effective voices → tone (0-100).

    A roster with NO loud voice still gets baseline tone (HC compensates a bit).
    Glue shifts the saturation *point* outward — high-glue rosters tolerate
    more voices before friction sets in — but does NOT pull rising-regime
    voice counts down. (Otherwise high glue would penalize quiet rooms.)
    """
    # Yield in the "rising regime" (0-2 voices): unaffected by glue shift.
    if effective_voices <= 0:
        return 45.0  # baseline — quiet room
    if effective_voices <= 1:
        return 45.0 + 30.0 * effective_voices  # 45 → 75
    if effective_voices <= 2:
        return 75.0 + 10.0 * (effective_voices - 1)  # 75 → 85

    # Saturation regime: glue extends tolerance.
    # +1 voice of headroom for every ~350 glue-points above 700 (avg-ish for 22 starters).
    glue_shift = max(0.0, (glue_total - 700.0) / 350.0)
    n = max(2.0, effective_voices - glue_shift)
    if n <= 3:
        return 85.0 - 2.0 * (n - 2)        # gentle dip 85 → 83
    if n <= 5:
        return 83.0 - 12.0 * (n - 3)       # declining: 83 → 59
    return max(35.0, 59.0 - 6.0 * (n - 5))


def _voice_saturation_curve(weighted: List[Tuple["Player", float]]) -> float:
    """Tone score: piecewise voice saturation with glue + big_stage modifiers."""
    if not weighted:
        return 50.0
    effective_voices = 0.0
    glue_total = 0.0
    for p, w in weighted:
        glue_total += p.glue * w
        if p.voice >= 70:
            # big_stage players count as 0.5 voices for saturation purposes —
            # they've proven they can play in voice-stacked rooms without friction.
            voice_weight = 0.5 if p.big_stage else 1.0
            effective_voices += voice_weight * w
    return _voice_saturation_yield(effective_voices, glue_total)


def _fabric(weighted: List[Tuple["Player", float]]) -> float:
    """Fabric: weighted Σ(glue × pull/100), franchise pull-multiplier, normalized.

    A roster of high-glue, high-pull players with one franchise icon hits
    ~80. A roster of low-glue, low-pull no-flag players hits ~30-40.
    """
    if not weighted:
        return 50.0
    raw = 0.0
    weight_total = 0.0
    for p, w in weighted:
        pull = p.pull * (1.3 if p.franchise else 1.0)
        raw += (p.glue * pull / 100.0) * w
        weight_total += w
    if weight_total == 0:
        return 50.0
    avg = raw / weight_total
    # avg is glue × pull / 100 ≈ 25-95 range maps to roughly the same scale.
    return max(0.0, min(100.0, avg))


def _drag(
    weighted: List[Tuple["Player", float]], hc: "CoachCard", glue_total: float
) -> float:
    """Drag: roster drama load, archetype-modulated, message-suppressed.

    Per drama-prone player (drama_baseline >= 60, OR baggage flag):
      raw_load = drama_val × weight × (1 + pull/100)
      protection = 60 / mean_team_glue   (>1 → low-glue room, <1 → high-glue)
      load = raw_load × protection × archetype_mod × franchise_mod
    HC `message` reduces sum multiplicatively.

    Calibration target:
      - 1 high-drama (80) under players_coach (good HC, glue=70) → drag ~15-25
      - 4 high-drama (80) on the same roster → drag ~55-80 (structural)
    """
    if not weighted:
        return 0.0
    archetype = hc.chemistry_archetype if hc is not None else "tactician"
    weight_total = sum(w for _, w in weighted) or 1.0
    mean_glue = max(25.0, glue_total / weight_total)
    protection = 60.0 / mean_glue  # 60 = neutral team glue

    raw = 0.0
    for p, w in weighted:
        # Phase 3: read drama_current when populated; else fall back to baseline.
        # `drama_current == 0` is the "unset" sentinel from Player default.
        drama_val_source = p.drama_current if p.drama_current > 0 else p.drama_baseline
        is_dramatic = drama_val_source >= 60 or p.baggage
        if not is_dramatic:
            continue
        drama_val = drama_val_source
        if p.baggage:
            # Baggage adds a permanent +20 to drama contribution.
            drama_val = drama_val + 20
        load = drama_val * w * (1.0 + p.pull / 100.0) * protection

        # Archetype modifier — depends on whether the player's talent
        # justifies the drama (high overall = "earned it"; low = mismatch).
        talent_justifies = p.overall >= 80
        if archetype == "players_coach":
            load *= 0.7
        elif archetype == "disciplinarian":
            load *= 0.6 if talent_justifies else 1.2
        elif archetype == "mentor":
            load *= 0.85
        # tactician: 1.0 (no change)

        if p.franchise:
            load *= 0.5

        raw += load

    # `message` suppression: high-message coach (75+) cuts ~12-22%.
    if hc is not None:
        message_factor = 1.0 - max(0.0, (hc.message - 50)) * 0.005
        raw *= message_factor

    # Normalize so 1 high-drama player produces ~20 drag, 4 produces ~75.
    # Per-player raw under players_coach + message=60 + glue=70 + drama=80
    # is ~68 (drama_val × 1.5 × 0.857 × 0.7 × 0.95). 4× = 272. / 3.5 = 78.
    return max(0.0, min(100.0, raw / 3.5))


def _tilt(
    weighted: List[Tuple["Player", float]],
    hc: "CoachCard",
    fabric: float,
    franchise_count: int,
) -> float:
    """Tilt risk: high pull × high drama presence, suppressed by fabric/HC/franchise."""
    if not weighted:
        return 0.0
    risk = 0.0
    for p, w in weighted:
        if p.pull >= 70 and p.drama_baseline >= 60:
            risk += (p.pull / 100.0) * (p.drama_baseline / 100.0) * w * 35.0
    risk -= (fabric - 50.0) * 0.6
    if hc is not None:
        risk -= max(0.0, hc.message - 50) * 0.3
    risk -= franchise_count * 5.0
    return max(0.0, min(100.0, risk))


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────


def compute_chemistry(team: "Team", hc: "CoachCard | None") -> "TeamChemistryState":
    """Pregame chemistry snapshot. Sets `team.chemistry` and returns it."""
    from engine.game_engine import TeamChemistryState  # avoid circular import

    weighted = playing_time_weighted_roster(team)
    if not weighted:
        state = TeamChemistryState()
        team.chemistry = state
        return state

    glue_total = sum(p.glue * w for p, w in weighted)
    franchise_count = sum(1 for p, _ in weighted if p.franchise)

    tone = _voice_saturation_curve(weighted)
    fabric = _fabric(weighted)
    drag = _drag(weighted, hc, glue_total)
    tilt = _tilt(weighted, hc, fabric, franchise_count)

    state = TeamChemistryState(
        tone=tone,
        fabric=fabric,
        drag=drag,
        tilt=tilt,
        franchise_count=franchise_count,
        pipeline=compute_pipeline(team),
    )
    team.chemistry = state
    return state


# ──────────────────────────────────────────────────────────────────────
# Phase 2: Per-game drift signals
# ──────────────────────────────────────────────────────────────────────
#
# Drift is NOT applied per game. Each game appends signals to the player's
# buffer; they are aggregated, HC-modulated, and applied once at season end.
# This keeps season-arc shapes recognizable rather than noisy.
#
# Signal types tracked:
#   high_snap_share_win        : +voice, +glue
#   low_snap_share_streak      : -voice, +drama_baseline
#   comeback_win_carried       : +glue (large)
#   demoted_starter            : +drama_baseline (suppressed by high reach)
#   mentee_breakout            : +glue
#   coaching_change_survived   : +voice
#   injury_comeback            : +voice, +glue


def log_drift_signal(
    player: "Player",
    attr: str,
    delta: float,
    weight: float = 1.0,
) -> None:
    """Append a drift signal to the player's season buffer.

    `weight` lets callers communicate signal strength (e.g., comeback wins
    weigh more than routine wins).
    """
    player.chemistry_drift_log.append({"attr": attr, "delta": delta, "weight": weight})


def log_path_event(player: "Player", event: str) -> None:
    """Append a one-off path event tag to the player's career log."""
    if event not in player.chemistry_career_events:
        player.chemistry_career_events.append(event)


# ── Game-end signal generation ────────────────────────────────────────


def log_game_drift_signals(
    player: "Player",
    *,
    snap_share: float,
    team_won: bool,
    was_comeback: bool = False,
    is_demoted_starter: bool = False,
    mentee_breakout: bool = False,
    injury_comeback: bool = False,
    coaching_change_survived: bool = False,
) -> None:
    """Read the player's game outcome → emit drift signals.

    `snap_share` is on [0, 1]. The caller decides how to compute it
    (offensive_snaps / total_team_offensive_snaps usually).
    """
    if snap_share >= 0.7 and team_won:
        log_drift_signal(player, "voice", +0.2)
        log_drift_signal(player, "glue", +0.15)

    if snap_share < 0.25:
        log_drift_signal(player, "voice", -0.1)
        log_drift_signal(player, "drama_baseline", +0.15)

    if was_comeback and snap_share >= 0.5:
        log_drift_signal(player, "glue", +0.4, weight=2.0)
        log_path_event(player, "comeback_win_carried")

    if is_demoted_starter:
        # Suppressed by high reach (receptive players don't sulk).
        magnitude = 0.4 if player.reach < 70 else 0.1
        log_drift_signal(player, "drama_baseline", +magnitude)
        log_path_event(player, "demotion")

    if mentee_breakout:
        log_drift_signal(player, "glue", +0.25)
        log_drift_signal(player, "pull", +0.15)
        log_path_event(player, "mentored_breakout")

    if injury_comeback:
        log_drift_signal(player, "voice", +0.2)
        log_drift_signal(player, "glue", +0.2)
        log_path_event(player, "injury_comeback")

    if coaching_change_survived:
        log_drift_signal(player, "voice", +0.15)
        log_path_event(player, "coaching_change_survived")


# ──────────────────────────────────────────────────────────────────────
# Phase 2: Season-end consolidation
# ──────────────────────────────────────────────────────────────────────


def _aggregate_drift(player: "Player") -> dict:
    """Sum the buffer per attribute. Returns {attr: total_delta}."""
    totals: dict = {}
    for entry in player.chemistry_drift_log:
        attr = entry["attr"]
        totals[attr] = totals.get(attr, 0.0) + entry["delta"] * entry.get("weight", 1.0)
    return totals


def apply_season_end_drift(player: "Player", hc: "CoachCard | None") -> dict:
    """Consolidate this player's drift buffer, apply, clip to innate range.

    Returns the applied deltas (post-modulation) for inspection. Clears
    the buffer.
    """
    totals = _aggregate_drift(player)
    if not totals:
        return {}

    # HC×player interaction: reach mediates how much HC influence lands.
    # coach_rating in [25, 95]; reach in [25, 95]. Multiplier in roughly
    # 0.5-1.6 range; high-reach + high-rating coach = full effect.
    if hc is not None:
        reach_factor = 0.5 + (player.reach / 100.0)            # 0.75-1.45
        coach_factor = 0.6 + (hc.coach_rating / 100.0) * 0.8   # 0.8-1.36
        base_mult = reach_factor * coach_factor
        archetype = hc.chemistry_archetype
    else:
        base_mult = 1.0
        archetype = "tactician"

    applied: dict = {}
    is_young = (
        getattr(player, "year", "").lower() in {"freshman", "sophomore"}
        or player.seasons_in_career <= 2
    )
    talent_mismatch = player.overall < 75

    for attr, total in totals.items():
        delta = total * base_mult

        # Mentor archetype: ×1.25 on positive signals for young players.
        if archetype == "mentor" and delta > 0 and is_young:
            delta *= 1.25
        # Players_coach: ×1.15 on glue-related signals.
        if archetype == "players_coach" and attr == "glue" and delta > 0:
            delta *= 1.15
        # Disciplinarian: ×1.2 on negative signals for talent-mismatch players
        # (the friction compounds — they can't win the room).
        if archetype == "disciplinarian" and delta < 0 and talent_mismatch:
            delta *= 1.2

        # Apply and clip to innate range.
        current = getattr(player, attr)
        rng_attr = f"{attr}_range"
        floor, ceiling = getattr(player, rng_attr, (25, 95))
        new_val = int(round(current + delta))
        new_val = max(floor, min(ceiling, new_val))
        setattr(player, attr, new_val)
        applied[attr] = new_val - current

    player.chemistry_drift_log.clear()
    return applied


# ──────────────────────────────────────────────────────────────────────
# Phase 2.3: Innate range pressure
# ──────────────────────────────────────────────────────────────────────


def apply_innate_range_pressure(
    player: "Player",
    consecutive_at_ceiling: dict,
    consecutive_below_floor: dict,
    rng=None,
) -> None:
    """Once-per-season range-shift roll per attribute.

    `consecutive_at_ceiling[attr]` and `consecutive_below_floor[attr]` are
    int counters maintained by the caller across seasons.

    Rules:
      - Current at ceiling for 2+ seasons → small chance ceiling lifts 1-3.
      - Current below floor 3+ seasons → floor revises down 1-3.
    """
    rng = rng or _random_module.Random()
    for attr in (*_STABLE_ATTRS, "drama_baseline", "fit"):
        rng_attr = f"{attr}_range"
        floor, ceiling = getattr(player, rng_attr, (25, 95))

        if consecutive_at_ceiling.get(attr, 0) >= 2 and rng.random() < 0.20:
            lift = rng.randint(1, 3)
            ceiling = min(95, ceiling + lift)

        if consecutive_below_floor.get(attr, 0) >= 3:
            drop = rng.randint(1, 3)
            floor = max(25, floor - drop)

        setattr(player, rng_attr, (floor, ceiling))


# ──────────────────────────────────────────────────────────────────────
# Phase 2.4: Permanent flag awards
# ──────────────────────────────────────────────────────────────────────


_FRANCHISE_TENURE = 5
_FRANCHISE_OVR_FLOOR = 80  # career production proxy
_BAGGAGE_TEAMS_THRESHOLD = 3
_BAGGAGE_TEAMS_WINDOW = 5
_BAGGAGE_INCIDENT_THRESHOLD = 3


def evaluate_permanent_flags(player: "Player") -> dict:
    """End-of-season check. Awards (or partially recovers) permanent flags.

    Returns {flag_name: bool} for any newly-changed flags.
    """
    changed: dict = {}

    # ── franchise ──────────────────────────────────────────
    has_major_award = any(
        a.get("type") in {"mvp", "championship", "league_leader"}
        for a in player.chemistry_major_awards
    )
    elite_production = player.overall >= _FRANCHISE_OVR_FLOOR
    if (
        not player.franchise
        and player.seasons_with_team >= _FRANCHISE_TENURE
        and has_major_award
        and elite_production
    ):
        player.franchise = True
        changed["franchise"] = True

    # ── big_stage ───────────────────────────────────────────
    # Earned by being a major-award winner on a 2+ award-stacked roster
    # during a deep playoff run.
    if not player.big_stage:
        for award in player.chemistry_major_awards:
            if (
                award.get("stacked_roster", False)
                and award.get("deep_playoff_run", False)
                and award.get("type") in {"mvp", "all_league", "championship"}
            ):
                player.big_stage = True
                changed["big_stage"] = True
                break

    # ── baggage ────────────────────────────────────────────
    # Award if any of: 3+ teams in 5 seasons, 3+ incidents, or
    # released-and-resigned-mid-season twice (tracked as path events).
    teams_in_window = len(player.teams_played_for[-_BAGGAGE_TEAMS_WINDOW:])
    if not player.baggage:
        if (
            teams_in_window >= _BAGGAGE_TEAMS_THRESHOLD
            or player.locker_room_incidents >= _BAGGAGE_INCIDENT_THRESHOLD
            or player.chemistry_career_events.count("released_for_cause") >= 2
        ):
            player.baggage = True
            changed["baggage"] = True

    # ── baggage recovery (partial) ─────────────────────────
    # 3+ low-drama seasons under a players_coach lowers the drama floor by 5
    # via drama_baseline_range adjustment. Flag never fully removed.
    if player.baggage and player.low_drama_seasons_for_baggage_recovery >= 3:
        floor, ceiling = player.drama_baseline_range
        new_floor = max(25, floor - 5)
        if new_floor != floor:
            player.drama_baseline_range = (new_floor, ceiling)
            changed["baggage_recovery"] = True
        # Reset the counter so next 3 stretches earn another reduction.
        player.low_drama_seasons_for_baggage_recovery = 0

    return changed


# ──────────────────────────────────────────────────────────────────────
# Phase 2: Combined season-end pass
# ──────────────────────────────────────────────────────────────────────


def season_end_chemistry_pass(
    player: "Player",
    hc: "CoachCard | None",
    *,
    consecutive_at_ceiling: dict | None = None,
    consecutive_below_floor: dict | None = None,
    is_low_drama_season: bool = False,
    rng=None,
) -> dict:
    """Run drift consolidation + range pressure + flag awards in order.

    Returns a summary dict for the season-end UI. Caller is responsible for
    incrementing `seasons_with_team` and `seasons_in_career` and pushing
    awards/team-history before this call.
    """
    drift_applied = apply_season_end_drift(player, hc)

    if consecutive_at_ceiling is not None and consecutive_below_floor is not None:
        apply_innate_range_pressure(
            player, consecutive_at_ceiling, consecutive_below_floor, rng=rng
        )

    # Track baggage recovery progress: a low-drama season under a
    # players_coach (chemistry_archetype == "players_coach") counts.
    if (
        player.baggage
        and is_low_drama_season
        and hc is not None
        and hc.chemistry_archetype == "players_coach"
    ):
        player.low_drama_seasons_for_baggage_recovery += 1

    flag_changes = evaluate_permanent_flags(player)
    return {"drift_applied": drift_applied, "flag_changes": flag_changes}


# ──────────────────────────────────────────────────────────────────────
# Phase 4: Spine + adversity moments
# ──────────────────────────────────────────────────────────────────────


def initialize_spine(team: "Team", hc: "CoachCard | None") -> float:
    """Compute starting spine for a game.

    spine = fabric + composure_contribution + crisis_anchor_bonus + 10*franchise_count

    Mutates `team.chemistry.spine` and returns the value.
    """
    state = team.chemistry
    spine = float(state.fabric)

    if hc is not None:
        # composure on the existing CoachCard scale (25-95). Centering at 50.
        spine += (hc.composure - 50) * 0.4  # ±18 from extreme composure

    # Crisis anchor: any rostered player with voice >= 75 AND glue >= 75.
    if any(p.voice >= 75 and p.glue >= 75 for p in team.players):
        spine += 10.0

    spine += 10.0 * state.franchise_count

    state.spine = max(0.0, min(100.0, spine))
    return state.spine


def adversity_boost_with_spine(
    base_boost: float, state: "TeamChemistryState"
) -> Tuple[float, "TeamChemistryState"]:
    """Apply spine to an adversity-moment boost. Depletes spine by 5.

    High-tilt teams crumble: when tilt >= 60, the response goes the wrong way
    (negative magnitude added to base). Otherwise spine extends the boost up
    to +20% at full pool.

    Returns (modified_boost, mutated_state). Caller threads the state back.
    """
    if state.spine <= 0:
        return base_boost, state

    if state.tilt >= 60:
        # Crumble: high tilt + adversity = response WORSE than baseline.
        # Magnitude scales with tilt; spine partially counteracts.
        crumble = (state.tilt - 60) / 100.0 * 0.30   # up to 12% worse at tilt=100
        spine_relief = (state.spine / 100.0) * 0.10
        boost = base_boost - crumble + spine_relief
    else:
        boost = base_boost + (state.spine / 100.0) * 0.20

    state.spine = max(0.0, state.spine - 5.0)
    return boost, state


# ──────────────────────────────────────────────────────────────────────
# Phase 5: Pipeline + drift indicators + UI surfacing
# ──────────────────────────────────────────────────────────────────────


def compute_pipeline(team: "Team") -> float:
    """Pipeline: succession health.

    Counts age <= 26 (or freshman/sophomore/junior class) players with
    rising drift on voice or pull AND innate ceilings >= 75, weighted by
    a playing-time proxy (here: overall rating).
    """
    if not team.players:
        return 0.0
    score = 0.0
    age_buckets = {"freshman", "sophomore", "junior"}
    for p in team.players:
        is_young = (
            getattr(p, "year", "").lower() in age_buckets
            or p.seasons_in_career <= 4
        )
        if not is_young:
            continue
        rising = (
            p.chemistry_recent_drift.get("voice", 0.0) > 0.5
            or p.chemistry_recent_drift.get("pull", 0.0) > 0.5
        )
        ceiling_high = p.voice_range[1] >= 75 or p.pull_range[1] >= 75
        if rising and ceiling_high:
            playing_time_proxy = p.overall / 100.0
            score += 10.0 * playing_time_proxy
    return min(100.0, score)


def update_recent_drift(player: "Player", attr: str, delta: float) -> None:
    """Roll the trailing-window drift counter forward by `delta`.

    A simple decay-and-add: existing value gets pulled toward 0 by 10% then
    `delta` is added. This simulates a 10-game rolling window without
    persisting individual game entries.
    """
    current = player.chemistry_recent_drift.get(attr, 0.0)
    player.chemistry_recent_drift[attr] = current * 0.9 + delta


def drift_indicator(player: "Player", attr: str) -> str:
    """Return 'rising', 'stable', or 'declining' for the player card UI."""
    drift = player.chemistry_recent_drift.get(attr, 0.0)
    if drift > 0.5:
        return "rising"
    if drift < -0.5:
        return "declining"
    return "stable"


# ──────────────────────────────────────────────────────────────────────
# Phase 5: Player card / team chemistry view
# ──────────────────────────────────────────────────────────────────────


def render_player_card(player: "Player") -> str:
    """One-screen text rendering of the player card chemistry block."""
    flags = []
    if player.franchise:
        flags.append("FRANCHISE")
    if player.big_stage:
        flags.append("BIG STAGE")
    if player.baggage:
        flags.append("BAGGAGE")
    flag_str = " ".join(f"[{f}]" for f in flags) if flags else ""

    lines = [
        f"{player.name} | {player.position} | Y{player.seasons_with_team} with team",
    ]
    if flag_str:
        lines.append(flag_str)
    lines.append("─" * 50)

    rows = [
        ("Voice", player.voice, player.voice_range, drift_indicator(player, "voice")),
        ("Glue", player.glue, player.glue_range, drift_indicator(player, "glue")),
        ("Pull", player.pull, player.pull_range, drift_indicator(player, "pull")),
        ("Reach", player.reach, player.reach_range, drift_indicator(player, "reach")),
        ("Drama (base)", player.drama_baseline, player.drama_baseline_range,
         drift_indicator(player, "drama_baseline")),
    ]
    arrows = {"rising": "↑ rising", "stable": "→ stable", "declining": "↓ declining"}
    for label, val, rng, ind in rows:
        lines.append(f"{label:<14}{val:<4}{arrows[ind]:<14}(range: {rng[0]}-{rng[1]})")

    if player.drama_current > 0:
        lines.append(f"  today (drama)  {player.drama_current}")
    if player.fit_current != 50:
        lines.append(f"Fit (today)     {player.fit_current}")
    if player.head_current != 50:
        lines.append(f"Head (today)    {player.head_current}")

    return "\n".join(lines)


def render_team_chemistry(team: "Team", hc: "CoachCard | None" = None) -> str:
    """One-screen text rendering of the team chemistry view."""
    state = team.chemistry
    lines = [
        f"TEAM CHEMISTRY — {team.name}",
        "─" * 50,
        f"Tone        {int(state.tone):<5}",
        f"Fabric      {int(state.fabric):<5}",
        f"Drag        {int(state.drag):<5}",
        f"Tilt        {int(state.tilt):<5}",
        f"Spine       {int(state.spine):<5}",
        f"Pipeline    {int(state.pipeline):<5}",
        f"Franchise   {state.franchise_count}",
    ]
    if hc is not None:
        lines.append(f"HC archetype: {hc.chemistry_archetype}")
    return "\n".join(lines)


def apply_chemistry_to_rhythm(rhythm: float, state: "TeamChemistryState") -> float:
    """Apply chemistry modifiers to `game_rhythm` (capped at the system's 0.65-1.35).

    Each component is a small lever — chemistry is a modifier in normal play,
    not a determinant. (Phase 4 lifts spine into a major lever for adversity.)
    """
    rhythm += (state.fabric - 50.0) * 0.001     # ±5% max
    rhythm += (state.tone - 50.0) * 0.0005      # ±2.5% max
    rhythm -= state.drag * 0.001                # 0 → -10% max
    return max(0.65, min(1.35, rhythm))
