# VAL-06 / CCH-10 — Longitudinal evidence and leadership follow-up

Baseline study run [45529194474](https://github.com/quarterback/viperball/actions/runs/45529194474), pre-HS rounding fix. 20-season (seed 20261125) and 30-season (20261124) completed 1,980 and 2,970 games, respectively; 19 and 29 DB transitions passed. 32-team seed 20261126 stopped on schedule quota mismatch: Navy and Northern Iowa 10 rather than 12. Both national two-season jobs and reduced integrated/offense jobs passed on the study head. No broad national long-term inference.

| Study | Initial / final mean coach OVR | Final mean age / max | 75+ | Assistant→HC appointments | HC→assistant appointments | Ready nonaspiring assistants | Initial / final mean player OVR |
|---|---|---|---:|---:|---:|---:|---|
| 20 years | 60.25 / 66.797 | 56.453 / 82 | 4 | 12 | 17 | 18 | 35.328 / 42.057 |
| 30 years | 60.25 / 66.766 | 59.703 / 89 | 14 | 28 | 39 | 18 | 34.068 / 41.988 |

Appointments are observed role changes, not unique first promotions. 20-year study 1,440 signed and 1,275 walk-ons; 30-year 2,097 signed and 2,050 walk-ons; no emergency walk-ons in either. Final freshman/senior mean 37.691/48.315 and 35.543/46.683. Five/ten-year roster means 44.491/41.167 and 44.005/41.686. Program growth and tier effects are not causal conclusions; job logs support these aggregate figures. Generated hires remain numerous (89 and 129 generated fills; 73 and 94 free-agent hires).

## Changes from evidence

- Reconciled main 8822600 (HS rounding parity; other agent's full-suite AAR reports 279 tests). No conflicts in study files.
- Retirement: identity/year stable annual probability from age 60 (2.5% at 60, +2.5 percentage points/year, compulsory at 80). Candidate calibration, not an observed demographic rate. Career season/learning credited before retirement; actual retired coach card archived in annual coaching history; retiree excluded from all offers, vacancy filled even for human staff (automatic replacement only for retirement, no human firing). No culture-clash model. Persistent unemployed-coach pool remains separate.
- Staffing: bounded candidate ranking adjustment from incumbent HC management, continuity, prior program/mentorship, tactical fit and complementary teaching/recruiting skills. Does not affect game outcome modifiers. If simultaneous HC vacancy, no outgoing HC influence. Existing market matching preserved.
- Program continuity: retain up to 20% of remaining practiced familiarity gap, scaled by HC continuity preference, bounded by existing carryover cap. Existing family-switch penalty, roster fit, lineage and installed package gates remain.
- Schedule repair fallback: allow unscheduled same-conference edge below cap or exchange an unprotected large-conference game for two cross-conference games when ordinary repair cannot fill deficits. Small conference round robins and pinned/rivalry matches protected. No schedule guarantee until rerun.

Runtime and outcome effects of changes pending; rerun 32-team study and long trajectories. No new scoring targets.

## Presentation and validation continuation

Existing college team and coach pages now show market reputation, actual play callers, former-HC status, recorded role experience, readiness, active leadership profile and annual reputation/expectation evidence without showing hidden development rates. Coaching history API exposes hires and retirement summaries; fixed incorrect hc.name reference. Retirement cards persist in coaching history but dedicated historical coach directory and persistent unemployed pool remain out of scope. Observer records retirement counts/ages and rejects a retired coach still employed. Focused tests cover retirement bounds, portal exclusion and staffing/continuity preferences. Large-conference repair protects existing minimum eight conference games on removed-edge endpoints. Rerun all long jobs and existing regressions; production deployment must be separately verified after merge.
