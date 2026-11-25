# CCH-07 — College coaching employment and career continuity

Status: implementation committed; candidate regression and integrated results pending. Builds on DEF-11 #373, which includes VAL-05 #372. College-only; no pro or international changes.

## Defects found by source inspection

- A contracted assistant matched to a head coaching position was assigned to the new team without removing the old staff entry. The same mutable CoachCard could hold two positions and accrue another program's record or change its identity metadata. An origin vacancy was never actually filled.
- HC career wins, losses and seasons were credited during advance_season and again during run_coaching_offseason. Fired assistants skipped season credit altogether. Retired programs continued to age staff and enter the carousel.
- Expired assistants who elected to remain could retain a zero-year contract. Playoff credit used a fixed eight-team field even for a different configured playoff size. CoachCard saves omitted career awards.

## Implementation

Resolve departures before appointments, using original staff slots, then fill every remaining vacancy using the existing generated-fill fallback. A contracted assistant seeking promotion is eligible for HC jobs only; an unmatched assistant stays. Vacancies are deduplicated and matching takes the next free vacancy in deterministic order. Portal-generated IDs are checked against active staff and the current pool; this is not a migration of historical duplicate identities. Newly opened jobs do not trigger another matching wave; fallback hires are explicitly recorded. Retained assistants get an actual renewed contract.

Credit each active coach's completed season in advance_season before employment decisions; append or extend observed career stints, track actual playoff participants, preserve assistant mentoring history across uninterrupted employment, and award postseason credit. Offseason ticks age and contract, advances HC readiness and develops attributes using the existing model; it no longer credits career W/L or seasons. Freeze retired staffs out of automated matching and development. Log attribute deltas and readiness gains for every coach from the prior active season. Preserve career awards in CoachCard serialization. Historic totals are not retroactively reconstructed.

## Validation

Five new focused tests: promotion and origin vacancy, unmatched retention, duplicate vacancy handling, contract renewal, frozen staff and card roundtrip (combined assertions in five tests). Existing integrated benchmark checks four roles per active team, coach identity uniqueness, employment metadata, season credit for continuing and moved coaches, stable tactical profiles, exactly one development event per prior active coach, full coach-card DB parity, and the existing college schedule/roster/tactical gates. National matrix uses same seeds as VAL-05. No candidate runtime pass yet. DEF-11 candidate CI was still in progress when checked.

## Scope boundary

Existing tactical profiles are deliberately stable across career transitions. No new learning-from-match-results algorithm or arbitrary coaching effectiveness bonus. CCH-07 follow-up can assess longitudinal development and team-relative adaptation after this employment ledger passes. Existing save duplicates, manual marketplace poaching paths, persistent unemployed-coach pool and historical coach record migration are not repaired by this PR. Next production work after the integrated evidence is PBK-05 offensive situational diversity, then ROST-02/HS-01. No scoring targets or live deployment claims.
