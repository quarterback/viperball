"""Opening scripts (coaching casebook case 3, Bill Walsh).

A play caller who scripts writes an ordered list of opening calls before the
game. Each call probes the defense in a different way. The script runs over
the offense's first snaps of the first half, skipping a call when the game
situation takes priority and coming back to it afterward. The defense's
front and the result of each scripted call are recorded. When the script is
done, the call that worked best against a front becomes the answer the
caller goes to on the first snap of a later drive when the defense shows
that front again.

The script only chooses among calls the offense's style can legally make.
It uses only what the caller can see: the down, distance, field, clock,
score and the fronts the defense has already shown.
"""
import hashlib

POLICY_VERSION = 1

# Probe order and the families that can carry each probe, best first.
PROBES = (
    ("inside_run", ("dive_option", "power", "counter")),
    ("perimeter_run", ("sweep_option", "speed_option")),
    ("quick_kick_pass", ("kick_pass",)),
    ("viper_motion", ("viper_jet",)),
    ("draw", ("draw",)),
    ("deep_kick_pass", ("kick_pass",)),
)
_SUBTYPE = {"quick_kick_pass": "quick_kick", "deep_kick_pass": "territory"}

# Script lengths a caller can prefer. Some callers do not script at all.
_LENGTHS = (0, 0, 3, 4, 4, 5, 5, 6)


def script_length(coach_id):
    """A stable preference from the caller's identity."""
    if not coach_id:
        return 0
    digest = hashlib.sha256(f"script:{coach_id}".encode()).hexdigest()
    return _LENGTHS[int(digest[:8], 16) % len(_LENGTHS)]


def build_script(coach_id, family_weights, formation_weights):
    """The ordered opening calls for one offense, or an empty list."""
    length = script_length(coach_id)
    if not length:
        return []
    formations = {k: v for k, v in (formation_weights or {}).items() if v > 0}
    formation = max(formations, key=formations.get) if formations else None
    calls = []
    for probe, families in PROBES:
        family = next((f for f in families if (family_weights or {}).get(f, 0) > 0), None)
        if not family:
            continue
        call = {"probe": probe, "family": family}
        if formation:
            call["formation"] = formation
        if family == "kick_pass":
            call["kick_pass"] = _SUBTYPE.get(probe, "quick_kick")
        calls.append(call)
        if len(calls) == length:
            break
    return calls


def interrupt_reason(down, yards_to_go, quarter, seconds, score_diff, kick_mode, field_position):
    """The situations that take priority over the next scripted call."""
    from .coach_drive import interrupt_reason as drive_interrupt

    reason = drive_interrupt(down, yards_to_go, quarter, seconds, score_diff, kick_mode)
    if reason:
        return reason
    if down >= 3 and yards_to_go <= 2:
        return "short_yardage"
    if field_position >= 85:
        return "red_zone"
    return None


def best_answer(observations):
    """For each front seen, the probe that gained the most, if it gained 5+."""
    by_front = {}
    for obs in observations:
        front = obs.get("front")
        if not front or obs.get("yards") is None:
            continue
        best = by_front.get(front)
        if best is None or obs["yards"] > best["yards"]:
            by_front[front] = obs
    return {front: {k: obs[k] for k in ("probe", "family", "formation", "kick_pass") if k in obs}
            for front, obs in by_front.items() if obs["yards"] >= 5}
