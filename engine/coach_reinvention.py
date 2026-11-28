"""A long-serving head coach changes the program's system (casebook case 6).

Saban moved Alabama's offense to a spread system after watching it beat
teams like his. This module lets a CPU head coach do the same once the
evidence is sustained:

* She has led the program for at least four seasons.
* On the side she does not specialize in, the program finished in the
  bottom 40 percent of the league for two straight seasons: points per drive
  for the offense, points allowed per game for the defense.
* Another school on that side did clearly better across the league last
  season, run by at least three programs.
* She is adaptable enough to change. A stubborn coach keeps her system.

The new school replaces the old one on that side only. The program's own
installation, which already charges a cost when the school changes, is the
transition cost. The coach's personal tactical signature does not change.
"""
import random

POLICY_VERSION = 1
MIN_TENURE = 4
BOTTOM_SHARE = 0.40
MIN_PROGRAMS = 3


def tenure(hc, team, year):
    """Seasons this head coach has led this program before `year`."""
    starts = [s.year_start for s in getattr(hc, "career_history", []) or []
              if s.team_name == team and s.role == "head_coach" and s.year_end is None]
    return year - min(starts) if starts else 0


def _metric(record, side):
    if side == "offense":
        return record.get("avg_ppd")
    games = record.get("wins", 0) + record.get("losses", 0)
    return -(record.get("points_against", 0) / games) if games else None


def _bottom(values, team):
    """Whether `team` sits in the bottom share of `values` (higher is better)."""
    if team not in values or len(values) < 10:
        return False
    ordered = sorted(values.values())
    cutoff = ordered[int(len(ordered) * BOTTOM_SHARE)]
    return values[team] <= cutoff


def season_values(histories, year, side):
    out = {}
    for team, history in histories.items():
        rec = (getattr(history, "season_records", {}) or {}).get(year)
        if rec:
            value = _metric(rec, side)
            if value is not None:
                out[team] = value
    return out


def best_school(values, configs, side, catalog, current):
    """The school whose programs did best last season, if it clearly leads."""
    key = f"{side}_style"
    by_school = {}
    for team, value in values.items():
        school = (configs.get(team) or {}).get(key)
        if school in catalog:
            by_school.setdefault(school, []).append(value)
    means = {s: sum(v) / len(v) for s, v in by_school.items() if len(v) >= MIN_PROGRAMS}
    if current not in means or len(means) < 2:
        return None
    best = max(means, key=means.get)
    spread = max(means.values()) - min(means.values())
    if best == current or means[best] - means[current] < 0.25 * spread:
        return None
    return best


def consider(team, hc, config, histories, configs_by_year, year, catalogs, rng):
    """Return a school change for this program, or None."""
    from .coach_career import management
    from .coach_tactics import _slider

    if hc is None or tenure(hc, team, year) < MIN_TENURE:
        return None
    specialty = management(hc).get("specialty")
    side = "defense" if specialty == "oc" else "offense"
    last, before = year - 1, year - 2
    now_vals = season_values(histories, last, side)
    then_vals = season_values(histories, before, side)
    if not (_bottom(now_vals, team) and _bottom(then_vals, team)):
        return None
    key = f"{side}_style"
    current = config.get(key)
    target = best_school(now_vals, configs_by_year.get(last, {}), side, catalogs[side], current)
    if not target:
        return None
    adapt, stubborn = _slider(hc, "adaptability"), _slider(hc, "stubbornness")
    chance = max(0.0, min(0.75, 0.25 + 0.8 * (adapt - stubborn)))
    if rng.random() >= chance:
        return None
    return {"team": team, "side": side, "from": current, "to": target, "coach_id": hc.coach_id,
            "coach_name": f"{getattr(hc, 'first_name', '')} {getattr(hc, 'last_name', '')}".strip(),
            "tenure": tenure(hc, team, year), "year": year, "policy_version": POLICY_VERSION}
