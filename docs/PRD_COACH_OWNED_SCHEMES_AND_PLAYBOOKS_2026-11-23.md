# PRD: Coach-owned tactical identities and expandable playbooks

**Date:** 2026-11-23  
**Status:** Proposal approved for parallel implementation planning; no rules or coefficient changes authorized by this document  
**Workstreams:** COACH (coach identity + game integration, assigned to ChatGPT) and PLAYBOOK (scheme catalog and future packages, assigned to a separate agent)  
**Dependency:** Viperball engine PR #323 → defensive tactics PR #325 → DEF-06 analysis PR #326. The assessment and this plan live on documentation PR #324.  
**COACH implementation status:** [CCH-01 PR #327](https://github.com/quarterback/viperball/pull/327) is open and CI-validated (13 new tests; 85 total existing-plus-new); metadata-only persistent CoachCard identities. CCH-02–04 remain proposed and unimplemented.

## Product decision

Viperball's existing named offensive and defensive systems are **families**, not fully uniform playbooks. Every coordinator has a persistent, individualized interpretation of a family. Teams install the parts they can execute with the current staff and players. Each game adds preparation and adaptations to that installation.

Two teams can both run Boot Raid and still make measurably different formation, kick-pass, carrier, tempo, and fourth/sixth-down choices. A coordinator can take a recognizable set of tendencies to another school. Her successor does not instantly erase the former system: team familiarity and installed packages persist and decay. This is intended to make coaching hires, coordinator movement, coaching trees and roster development matter over seasons.

**Do not generate a new coach identity every game. Do not hard-code dozens of new schemes to get differences that could arise within an existing scheme.**

## Observed repo baseline (as of review)

Source: `engine/coaching.py`, `engine/ai_coach.py`, `engine/game_engine.py`, `engine/season.py`, the current playbook baseline, and the 2026-03-18 playbook rebalance PRD.

- `CoachCard` has stable `coach_id`; role (HC/OC/DC/STC); six 25–95 attributes; classification, personality sliders, traits, career history and coaching tree. `to_dict()/from_dict()` serialize these fields. `generate_coach_card()` and `generate_coaching_staff()` create and persist coach cards through the coaching system.
- The engine has **16 offensive families** in `OFFENSE_STYLES`, **eight defensive families** in `DEFENSE_STYLES`, and four formation shells. The current `docs/VIPERBALL_PLAYBOOK_DEVELOPMENT_BASELINE.md` includes older counts and older numerical claims: inspect live code before using that document for implementation.
- `compute_gameday_modifiers()` blends the HC and coordinators, but most offensive personality effects in `select_play_family()` come from HC personality/traits. The DC already gets a one-game `roll_dc_gameplan()` against run, lateral, kick-pass and trick. The HC supplies five lead-management countermeasure tendencies. These systems are active and must remain intact.
- `assign_ai_scheme()` chooses scheme *families* from team identity and team_stats, with only a limited HC bias; no persistent coordinator-owned family variation exists.
- `ViperballEngine.__init__` calls `assign_game_roles` before applying final style overrides (ROST-02). This must be corrected before using player usage as proof of coach-variant fidelity.
- `docs/prd_playbook_boost_rebalance_2026_03_18.md` describes earlier runaway multiplier stacking. New coaching preferences should alter **decisions and eligibility first**, not grant more unconditional yardage or turnover modifiers.
- DEF-06 documented real tactical tradeoffs between existing defenses but not a superior pressure mechanism for Blitz Pack. New personalities must preserve those scheme costs rather than erasing them.

## Four layers of tactics

| Layer | Owner and persistence | What it controls | Changes when |
|---|---|---|---|
| **1. Scheme family** | PLAYBOOK agent; versioned catalog | Permitted formations, play families, strengths, constraints, baseline weights, counter relationships | Content catalog releases; coach changes scheme |
| **2. Coach signature** | COACH agent; saved on coach ID | Individual, correlated preferences, featured personnel, favorite situation, weaknesses, adaptability | Generated once; develops gradually between seasons; coach carries it when moving |
| **3. Team installation** | COACH agent; stored with team/season | Which coach packages the roster has learned, staff fit, familiarity, vestigial former plays, implementation limits | Hires, offseason, personnel changes, practice and season progress |
| **4. Game plan** | Existing engine + COACH adapter | Situational opponent scouting, weather, form, injuries, current score/Delta Yards, DC prep, in-game adjustment | Each opponent/game/half/drive as already defined |

All four layers are distinct. A weekly gameplan is stochastic and short-lived; a coach signature is durable; a team's installed playbook survives a staff change for a time; a scheme family defines the rules and recognizable style.

## Coach signature: data contract v0.1

**Owned by the COACH agent.** Store on `CoachCard` as a backwards-compatible, versioned optional `tactical_profile`. A coach's signature can express preferences even before choosing a particular scheme family. The team selects an active compatible family; the coordinator's preferences are interpreted relative to it.

Suggested schema (illustrative numbers, not adopted tuning):

```json
{
  "version": 1,
  "coach_id": "oc_1842",
  "role": "oc",
  "signature_seed_version": "coach-tactics-v1",
  "identity": {
    "primary_family": "boot_raid",
    "secondary_family": "east_coast",
    "decision_style": "vertical_attack"
  },
  "offense": {
    "formation_bias": {"spread": 0.12, "split": 0.04, "tight": -0.08, "heavy": -0.08},
    "family_bias": {"kick_pass": 0.14, "counter": 0.05, "power": -0.08},
    "kick_pass_bias": {"bomb": 0.12, "territory": 0.04, "quick_kick": -0.09},
    "featured_position": "Viper",
    "decision_bias": {"early_down_risk": 0.12, "late_down_attack": 0.04}
  },
  "defense": {},
  "specialties": ["deep_kick_after_run", "spread_against_pressure"],
  "vulnerabilities": ["predictable_deep_calls", "short_yardage"],
  "lineage": [],
  "revision": 0
}
```

Use `coach_id` and a stable, **cross-process** SHA-256-derived seed; do not use Python's salted `hash()` or game seeds to regenerate permanent identity. `from_dict` must preserve profiles unchanged. Missing profiles in old saves must produce a deterministic migration or explicit neutral fallback, never randomly change behavior on each load.

The first version needs only **3–4 meaningful preferences, two specialties, one weakness**, not all illustrative fields above. Favor correlated choices: a deep-kick preference should usually increase Spread usage and the need for protection; a field-position specialist should prefer Territory/Quick Kick, conservative possession, and reliable receivers. Avoid independently rolling bonuses that produce contradictory personalities.

**Boundaries:** keep the current legal play families, kick range gates, snap-kick decision rules, down/field logic and current Delta Yards restart mechanism. Bias the *relative probabilities* of legal actions. Preserve a zero weight when the engine has made an action illegal. Start with narrowly bounded ±15–20% relative shifts to nonzero weights and normalize; tune only after matched-roster benchmarks. Limit simultaneous adjustments and avoid additional direct outcome multipliers in v0.1.

### Roles and authority

- **HC:** sets team philosophy, risk appetite, pace and delegation/autonomy. Existing head-coach counters and personality modifiers continue to apply. A high-control HC reduces coordinator departures from the established family; a delegating HC permits larger but bounded coordinator signatures.
- **OC:** owns formation and offensive play-family preferences, kick-pass subfamily, featured position, setting up the kick with the run. This is the main first implementation.
- **DC:** owns persistent strengths/preferences for the current eight schemes: pressure frequency, coverage focus, run support, personnel matching, and adaptation. A unique DC should change *which* tools a defense uses, not stack another all-purpose yard penalty atop DEF-01/02.
- **STC:** owns specialist usage, return/protection emphasis and kicking decision support. Implement later after offensive/defensive identities work.

The HC can disagree with a coordinator. Combine both inputs through a documented delegation rule; do not silently let both multiply the same weight twice.

## Family/coach integration: shared contract for both agents

**Joint interface, version 1:** the PLAYBOOK agent supplies a validated, immutable catalog of families and optional packages. The COACH agent supplies a persistent coach profile, team installation and a resolver that overlays bounded preferences onto selected baseline weights.

Data format must remain simple JSON-serializable dictionaries so both game engine and API can use it without a second implementation:

```python
# PLAYBOOK-owned (proposed functions, not yet implemented)
get_scheme_family(side: str, scheme_id: str) -> dict
get_package(package_id: str) -> dict
list_compatible_packages(side: str, scheme_id: str) -> list[dict]

# COACH-owned (proposed functions, not yet implemented)
ensure_coach_tactical_profile(coach) -> dict
resolve_staff_tactics(staff, offense_scheme_id, defense_scheme_id, roster) -> dict
apply_offense_tendencies(base_weights, team_tactics, game_context) -> dict
apply_defense_tendencies(base_defense, team_tactics, game_context) -> dict
```

**Coordination rule:** scheme IDs are the existing canonical slugs; play family IDs are the existing `PlayFamily.value` strings; formation IDs are `tight/split/spread/heavy`; kick pass subfamily IDs are existing `KickPassSubFamily.value` values. Do **not** invent aliases, make a second competing `OFFENSE_STYLES` or `DEFENSE_STYLES`, or rename these keys unilaterally.

For future packages, the PLAYBOOK agent's `get_package` may return:

```json
{
  "version": 1,
  "package_id": "boot_raid_vertical",
  "side": "offense",
  "compatible_families": ["boot_raid", "shock_and_awe"],
  "formation_tags": ["spread", "split"],
  "play_family_tags": ["kick_pass", "counter"],
  "kick_pass_tags": ["bomb", "territory"],
  "personnel_tags": ["strong_kicker", "fast_viper", "reliable_protection"],
  "situation_tags": ["midfield", "long_yardage"],
  "countered_by": ["lockdown"],
  "tradeoffs": ["long_release", "interception_exposure"]
}
```

Package records describe **what can be installed and under what conditions**. They should not execute engine logic, carry arbitrary Python callbacks or inject unchecked global multipliers. A package not owned by the installed team or incompatible with the scheme/roster must not become active.

**Integration stage:** the COACH agent should first work with existing scheme dictionaries and neutral/no-package defaults; when the PLAYBOOK catalog lands, it connects via the documented adapter. No one should block profile persistence or game-day identity on new packages being written.

## Parallel execution and file ownership

### COACH track — ChatGPT (my work)

**Own:** `engine/coaching.py`, new `engine/coach_tactics.py`, `engine/game_engine.py` integration points, `engine/season.py` / `engine/dynasty.py` persistence and hire flows, `tests/test_coach_tactics.py`, and coach-profile UI/API adapters when required.

**Deliver in small PRs, in order:**

- **CCH-01: Stable individual coach signature — IN REVIEW, [PR #327](https://github.com/quarterback/viperball/pull/327).** Implemented a versioned tactical profile on CoachCard, deterministic generation, serialization, legacy backfill, correlated personal preferences and tests. Coach moves retain the signature. **No gameplay effects in this phase.** [CI: 13 new tests and 85 total passed](https://github.com/quarterback/viperball/actions/runs/45239144988).
- **CCH-02: Actual game-day use.** Translate an OC's persistent signature into bounded formation, play-family and kick-pass subfamily preference changes, after legal play gating. Move/recalculate role assignment after final style resolution (ROST-02). Trace profile ID and applied preference in game results for comparison. Do not add all-purpose yardage boosts.
- **CCH-03: DC identity and HC autonomy.** Distinct defensive style behaviors through bounded tactical decisions and the existing read/coverage/pressure mechanism. Use DEF-06 conditional benchmarks; don't double-count suppression. Ensure HC control vs delegation is explicit.
- **CCH-04: Team installation and career progression.** Team-level installed packages and familiarity; staff turnover and continuity, coach-tree inheritance, season-to-season changes and later STC effects. Verify persistence across hires/transfers/saves.

**Do not edit:** new playbook catalog definitions, `data/playbooks/**`, package prose/rosters or the future playbook editor unless the other agent specifically hands them off.

### PLAYBOOK track — another agent

**Own:** new `engine/playbook_catalog.py` (or strictly data-only catalog loader), `data/playbooks/**`, `docs/playbook_packages/**`, `tests/test_playbook_catalog.py`, scheme/package documentation. This agent may propose changes to existing `OFFENSE_STYLES`/`DEFENSE_STYLES` but should not directly edit `engine/game_engine.py` or `engine/coaching.py` while the COACH track is integrating.

**Deliver:**

- **PBK-01: Catalog inventory and validation.** Enumerate all 16 current offenses, eight defenses, four formations and four kick-pass subfamilies; reconcile obsolete docs; define immutable package metadata and compatibility validation.
- **PBK-02: Package library.** Build meaningful variations within current offensive and defensive families—first aim for 2–3 distinct packages for 4 representative offenses and 3–4 defenses. Every package needs an applicable scenario, personnel requirements, benefits, counter and cost. Do not add new sport actions or fictional positions that the current engine cannot execute.
- **PBK-03: Broader playbook expansion.** Add new named families only if their patterns cannot be represented by combinations of existing family and packages; every new family needs a demonstrated mechanical distinction and matching defense/counter behavior.
- **PBK-04: AI coach selection guidance.** Map package compatibility and team requirements to the existing scheme assignment vocabulary; present a validated package list. Selection and saving remain the COACH agent's responsibility.

**Do not edit:** CoachCard, coaching generation, game simulation, season/dynasty career flows or runtime tactical resolver. Submit an interface change proposal if a package requires engine work instead of racing a concurrent commit.

### Shared review gates

- The COACH agent **owns the runtime integration API**. The PLAYBOOK agent **owns catalog data**. At the merge gate, agree on the schema and write a cross-module integration test.
- No parallel editing of `engine/game_engine.py`, `engine/coaching.py`, `engine/season.py`, `engine/dynasty.py`, `engine/ai_coach.py` without a handoff. Avoid two branches both editing `OFFENSE_STYLES` or `DEFENSE_STYLES`.
- Both branches should eventually share the same merged ancestor. Current outstanding PRs: **#323 engine baseline, #325 defense wiring, #326 defensive analysis, #324 docs**. Because they are stacked, don't merge these out of order. The COACH branch may start from #325 once it is stable; the PLAYBOOK branch should avoid depending on changes that are not merged.
- For PR and tasks, use stable IDs `CCH-01..04` and `PBK-01..04`, linked in the PR body. Include tests and exact save/load migration behavior.

## Acceptance tests: show identity, not label changes

**A. Same family, different OC.** Keep rosters, opponent, base Boot Raid, game context and seeds matched. Two different OC profiles produce distinguishable formation distribution, kick-pass subfamily, targeted player positions and risk choices over a sufficient set of games. At the same time both still look like Boot Raid.

**B. Staff change without scheme change.** Change OC only, retain Boot Raid and players. The team's active choices change; its installed familiarity changes over time rather than resetting to zero. Hires/fire/moves retain the coach's personal profile and historical lineage.

**C. Same coach, new team.** Move the same OC to another roster. Signature/seed/revision remain the same; tactical effectiveness and usable installed packages respond to the different kicker, protection and player speed. Not every playbook is executable on every roster.

**D. Defensive identity.** Two Lockdown DCs produce different coverage/pressure choices and conditional kick-pass/run effects while preserving Lockdown's broad defensive tradeoffs. Same for Blitz Pack, with actual pressure events (DEF-07) before claiming a unique blitz advantage.

**E. Limits and compatibility.** On every existing rule gate, illegal actions remain impossible; no old save loses a coach; no tactical profile rerolls on deserialize or per-game start. Verify cross-process deterministic generation, old/missing fields, missing OC/DC/HC, invalid scheme/package IDs, and malformed catalog input.

**F. Statistical realism.** Run fresh-roster full-engine benchmarks and a full season with and without coach-specific adaptations. Track yards/play by family, kick-pass attempts and completions, snaps by role, delta yard drives, scoring channel, turnover/bells, sack/pressure events (when exposed), and coach turnover effects. No fixed score, home-win or blowout target; avoid tuning to aggregate league averages alone.

**G. Observability.** Player-facing coach/team pages can eventually show `Boot Raid — Vertical Attack` or `Lockdown — Selective Pressure` from saved data, with 2–3 tendencies and a vulnerability backed by game logs. Keep full hidden numerical sliders private if that is part of coaching simulation design.

## Implementation order and decisions deferred

1. Merge or safely base on the existing engine/defensive branches; stabilize ROST-02 and game-day source-of-truth.
2. CCH-01 may be built **in parallel** with PBK-01/02 because coach identity does not need new packages.
3. CCH-02 runs on the existing 16 offenses and existing play-family names. Use benchmark comparisons to prove the OC's signature influences playcalling.
4. When the catalog schema is ready, merge it behind a neutral adapter; keep old saves and default teams working with no packages.
5. Add persistent DC and team installation; measure each staged change before adding new styles or larger packages.

**Deferred:** exact coach-to-coach inheritance rate, family-changing career conversions, multi-year playbook drift, team package learning curves, market salary effects, new formation shells and a player-accessible playbook editor. Those need evidence and should not delay the first observable persistent signature.

## Work log template

```markdown
Work item: CCH-01 | PBK-01 | ...
Owner: COACH | PLAYBOOK
Status: OPEN | IN PROGRESS | IN REVIEW | DONE
Branch / PR:
Current implementation dependency:
Public contract added or changed:
Saved data / migration:
Tests / CI:
Benchmarks and observed in-game effect:
Conflicts or handoff to other track:
```

## Sources in repo

- `engine/coaching.py`: `CoachCard`, `generate_coach_card`, `generate_coaching_staff`, `compute_gameday_modifiers`, `compute_lead_management_profile`, `roll_dc_gameplan`.
- `engine/ai_coach.py`: `assign_ai_scheme`, `auto_assign_all_teams`.
- `engine/game_engine.py`: canonical styles/defenses, `assign_game_roles`, formation/play-family/kick-pass selection and defense resolution.
- `docs/VIPERBALL_PLAYBOOK_DEVELOPMENT_BASELINE.md`: conceptual intent; numerical details and scheme counts are historical and must be reverified.
- `docs/prd_playbook_boost_rebalance_2026_03_18.md`: past multiplier stacking failure.
- `docs/aar_2026-11-23_def06_full_defense_matrix.md`: conditional offensive/defensive matchup data and findings (on documentation PR #324).
- `docs/ASSESSMENT_PRD_ENGINE_TACTICS_2026-11-23.md`: main work queue, ROST-02, DEF-07 and VAL-02.

_This document defines a two-agent implementation contract. A first coach tactical-profile implementation exists in unmerged PR #327; package catalog and game-day integration are still proposals until separately implemented and tested._
