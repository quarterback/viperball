# CCH-03 AAR: defensive coordinator tactical identity

**Date:** November 23, 2026  
**Implementation:** [PR #332](https://github.com/quarterback/viperball/pull/332), `feature/coach-tactics-cch-03-defense`, based on current `main` after PRs #323–#328 and #331 merged.  
**Status:** Code and tests complete in PR; not merged/deployed as of this report.  
**Tests and benchmark:** [GitHub Actions run 45272756445](https://github.com/quarterback/viperball/actions/runs/45272756445), both jobs successful: 11 targeted tests, 150 total tests, 320 full games.  
**Parallel ownership:** Another agent owns CCH-04 (team installation, coaching movement, borrowing packages). No CCH-04 implementation files or package catalog data are changed here.

## Why

CCH-01 gave each coordinator a saved, career-long tactical signature. CCH-02 wired OC preferences into legal offensive play-calling. The DC's persistent signature was still metadata; every Lockdown or Blitz Pack coordinator made the same *style-level* alignments and blitz decisions, other than existing HC coaching rolls and situational scheme modifiers.

DEF-06 showed that base defenses have meaningful costs: Lockdown covers kick passing at a cost in ground yardage, Fortress limits ground gains but concedes kicks, and Blitz Pack did not demonstrate more sacks in a controlled matchup even as it conceded explosives. CCH-03 must express **which decisions the DC makes** without fabricating better results or adding a second broad suppression multiplier.

## Implemented

### 1. DC signature with HC delegation

`engine/coach_tactics.py::resolve_defensive_tactics(staff)` reads the persistent `CoachCard.tactical_profile.defense` recorded by CCH-01. It preserves the original coach card. Without a DC it returns empty preferences, so existing scheme choices and randomness remain unchanged. Without an HC it grants full authority; with an HC it applies the same documented delegation scale as CCH-02.

The existing five generated defensive interpretations are still used: `selective_pressure`, `run_wall`, `deep_coverage`, `pursuit_zone`, `turnover_hunt`. Each has a pressure bias, run support bias, coverage focus and two favored read categories. This PR adds no new named defensive scheme or package.

### 2. One pre-snap call, before knowing the play

On ordinary scrimmage snaps, the offense chooses its formation; the DC can see formation, down and yards to go. The engine calls `_begin_defensive_call(formation)` **before** the offense chooses a play family or kick-pass subfamily. The DC independently selects:

- One of four **existing run-defense alignments**: `balanced`, `spread`, `stacked`, `aggressive`. The base scheme's native alignment remains the largest weight. The DC can favor another existing alignment, responding modestly to short yardage or a spread/long-yardage look.
- A **blitz/no-blitz pre-snap call**, using `STYLE_BLITZ_CHANCE` from the actual selected defense as the starting probability. A persistent pressure preference and chosen alignment shift that chance within bounds (2–65%). A spread/stacked look trades away rush potential. The existing `compute_sack_probability` consumes the same call rather than rolling a new chance after learning the actual kick-pass type.

These calls use a dedicated per-side game-seeded RNG, so the offense's global random stream is not perturbed by defensive planning draws. On no-DC or feature-off games, the old scheme-only alignment and blitz random draw remain.

**Important:** `blitz_calls` counts pre-snap decisions on all ordinary offensive snaps. It is **not** a count of pass-rush pressure events, hurries, or rushers physically sent on kick-pass plays. DEF-07 still needs that instrumentation.

### 3. Focused read allocation, with concessions

`get_defensive_read` already combines scheme read rate, play-family gameplan, situational modifiers, personnel and HC gameplan. CCH-03 now reallocates up to ±4 percentage points (then scaled by HC delegation) toward two favored categories and away from the other categories, *only on a DC-called snap*. The same final min/max bounds remain.

No general yards multiplier, blanket pressure bonus, or extra defensive success roll was introduced. The original eight defensive families, all 128 offense–defense matchup pairs, existing personnel contests and special-teams rules remain intact.

### 4. Observability

Full-engine results now include `defensive_coach_tactics.home/away`:

```json
{
  "away": {
    "dc_id": "coach_...",
    "signature": "selective_pressure",
    "authority": 0.77,
    "coverage_focus": "intermediate",
    "read_focus": ["kick_pass", "trick"],
    "calls": 30,
    "alignments": {"spread": 25, "aggressive": 5},
    "blitz_calls": 4,
    "read_attempts": {"run": 15, "kick_pass": 10},
    "read_successes": {"run": 5, "kick_pass": 6}
  }
}
```

This example is illustrative; the actual simulator reports measured values. The defending side in `play_by_play[*].defensive_call` is stamped when the play resolves, before any turnover changes possession. The existing `defensive_reads` counters stay backward compatible.

A separate `V2_ENGINE_CONFIG["defensive_coach_tactics_enabled"]` switch disables CCH-03 independently of offensive CCH-02 or the original defensive read and scheme mechanics. No API endpoint or frontend work was needed to preserve the new fields in full game results; no UI presentation has been implemented.

## Matched full-engine study

`python scripts/benchmark_defensive_coaches.py --games 40 --seed 20261123` compared two DCs, `selective_pressure` and `run_wall`, on exactly the same defensive roster, head coach, team setup, Boot Raid opponent, weather, and game seed. The coaches had identical existing attributes and sliders. Only their **saved defensive tactical profiles** differed. Both ran Lockdown and Blitz Pack in separate tests.

Two DCs × 40 games × two schemes × CCH-03 on/off = **320 full-engine games**. The benchmark asserts per-game scoring equality when CCH-03 is off, not merely equality of averages.

| Base defensive scheme | DC | Called blitz rate | Stacked alignment | Aggressive alignment | Opponent points/game | Opponent yards/game |
|---|---|---:|---:|---:|---:|---:|
| Lockdown | Selective Pressure | 15.9% | 6.4% | 17.0% | 55.80 | 263.98 |
| Lockdown | Run Wall | 4.0% | 20.1% | 6.2% | 56.65 | 273.52 |
| Blitz Pack | Selective Pressure | 54.6% | 6.4% | 72.4% | 71.16 | 433.55 |
| Blitz Pack | Run Wall | 42.9% | 18.7% | 64.4% | 68.44 | 407.48 |

The base scheme's **dominant alignment remains dominant**: Lockdown still uses Spread on roughly 68–71% of defensive calls, while Blitz Pack still uses Aggressive on roughly 64–72%. Across the same scheme, different DCs choose different numbers of blitzes and stacked alignments. Neither DC is universally stronger: the pressure-oriented coordinator allowed fewer opponent points under Lockdown but more under Blitz Pack in this sample.

**Interpreting these observations:** The demo has 40 games per DC/scheme, one matched set of two rosters, and no confidence intervals on points. Changing the defensive alignment can change the game's future random-number consumption and possesssion sequence. It proves meaningful decision differences, not a causal ranking of coaches or the optimality of one scheme.

**Controls:** With CCH-03 disabled, both coordinators produced *identical scores in every matched game* under both schemes. The existing HC effects and base defensive scheme remain active; only new personal DC decisions disappear.

## Tests

- Tests assert stable DC signature persistence after a job move or promotion, HC delegation bounds, missing-DC neutrality, and stable seeded local call behavior.
- They check the same named defensive scheme uses different alignment and blitz weights under different DCs; reads have a positive focus and negative nonfocus tradeoff.
- The pre-snap call is made without seeing the offensive play family, stays assigned to the defending side, and cannot leak into the next possession.
- A live game emits defender-attributed calls and read results; the feature switch produces identical outputs for identical-attribute coordinators with different saved signatures.
- [GitHub Actions](https://github.com/quarterback/viperball/actions/runs/45272756445): **11 targeted tests passed; 150 full tests passed; 320 benchmark games succeeded.**

## Remaining work and coordination with CCH-04

**For the other agent (CCH-04):**
- Build the team-level package installation/borrowing mechanism against the **already merged** `engine.playbook_catalog` v1 API, not the unmerged PR #329 runtime branch.
- New defensive package calls must integrate with `_begin_defensive_call` rather than adding a second, independent defensive decision/pressure roll after the offensive play is chosen. Package selection can alter the *input tactical weights* for the pre-snap call, but only once and under validated compatibility and staff/roster limits.
- When the other agent creates CCH-04's branch, identify and reconcile any overlapping `engine/game_engine.py` edits. The agent should avoid rewriting `engine/coach_tactics.py::resolve_defensive_tactics`, `_begin_defensive_call`, and `get_defensive_read` on its branch. CCH-03 should merge into main before final CCH-04 runtime integration, or CCH-04 should be rebased on CCH-03 with both agents' tests.
- Preserve the `defensive_coach_tactics` game-result contract and `defensive_call` play-by-play field if extending reports. Do not treat called blitzes as observed pressures or sacks.
- Staff moves retain their DC tactical profile through existing CCH-01 CoachCard persistence. Actual learned packages and program continuity are CCH-04's responsibilities.

**Still open beyond CCH-03:**
- DEF-07: record pass-rush pressure/hurries and player involvement on actual kick-pass plays; current `blitz_calls` is a pre-snap tactical decision.
- DEF-04: defensive lineup roles/rotation impacts and accurate attribution across every defensive surface.
- Full-year validation of coaching changes across additional rosters and defensive styles; this study is only Lockdown and Blitz Pack.
- Player-facing defensive coaching tendencies in React and live deploy smoke test.
- Reconcile outdated work queue statuses for merged PRs and mark CCH-03 done *only after* this PR merges.

## Reproduce

```sh
PYTHONHASHSEED=0 python -m pytest tests/test_coach_tactics_defense.py -q
PYTHONHASHSEED=0 python -m pytest tests/ -q
PYTHONHASHSEED=0 python scripts/benchmark_defensive_coaches.py --games 40 --seed 20261123 --out reports/cch03
```

CI downloadable results (90-day artifact retention): [CCH-03 full results.json](https://github.com/quarterback/viperball/actions/runs/45272756445/artifacts/14866017532).

### Source and boundaries

- `engine/game_engine.py`: scheme-derived alignments, `STYLE_BLITZ_CHANCE`, `compute_sack_probability`, `get_defensive_read`, game summary, play log.
- `engine/coach_tactics.py`: persistent signatures generated and serialized by CCH-01; new DC resolver, alignment budget, blitz chance and focused read allocation by CCH-03.
- `docs/PRD_COACH_OWNED_SCHEMES_AND_PLAYBOOKS_2026-11-23.md`: original two-agent work boundary.
- `docs/aar_2026-11-23_def06_full_defense_matrix.md`: defensive scheme strengths and concessions.
- `engine/playbook_catalog.py` and `data/playbooks/**`: existing merged read-only catalog, unmodified here.

Nothing in this PR changes actual offensive packages, coach hiring/contract APIs, team installation, a sport rule, or the current score/Delta Yards mechanics.
