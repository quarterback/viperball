# ROST-02 / HS-01 — College roster and recruiting cohort continuity

Status: implementation committed, runtime validation pending. Consolidates #375/#374/#373/#372. College only. Main has advanced to SCALE-01 (8a06988); final combined validation must include that change, not assume an older candidate's results transfer.

## Evidence and causes

VAL-05 observed opening national freshman mean 32.39; second-season freshman mean 35.80/35.81. Reduced trajectories by year three produced incoming freshman means about 42–43, above senior means about 39.6. Source inspection identifies two mechanisms, not a quantified causal decomposition:

1. Dynasty.advance_season ran the standalone roster maintenance fallback before the interactive API began recruiting. Graduates were removed and vacancies filled with generated freshmen; the API then saw no graduates and added another class. The roster ledger did not distinguish those invisible additions.
2. HSRecruitingPipeline generated every grade with the same college freshman rating modifier. Younger players then gained attributes during their HS progression, effectively receiving development on top of college-entry strength. The separate simulated HS competition already used grade offsets, but the recruiting prospect generator did not.

Additional defects: transfers matched display names rather than player IDs; player-card conversion and save/load lost original stars, loyalty, transfer count and academic information. New recruits retained number zero; the API did not expose walk-on additions.

## Implementation

- Defer automatic roster fill for the interactive college API until after recruiting and portal resolution. Other callers of advance_season retain their existing default path. Use actual developed survivors and committed eligible transfers to calculate scholarship space; no automatic six-scholarship minimum or extra four. Exclude exhausted graduates from portal availability; preserve stable IDs and increment transfer count on a completed move.
- Land scholarship and manual signings first. Then fill remaining vacancies toward the existing 36-player roster template with unsigned prospects by positional deficit; where no matching prospect remains, generate an explicit emergency walk-on from the existing ladder. Preserve larger rosters rather than silently cutting signed/returning players. Rotate selection order with seeded randomness; retain count-compatible walkons in recruiting history and detailed source/ID ledger separately. Assign unique jersey numbers where available. No arbitrary rating, scoring or signing-rate targets.
- Generate HS prospect classes with existing HS_YEAR_GAP offsets, not a new rating scale. Increase prospective class capacity from eight to twelve per college program for ordinary graduation vacancies; legacy pipeline classes keep their saved sizes. Restrict initial interest to the active school list and handle small leagues safely. Carry recruit academic information, original stars, work rate, loyalty and transfer count through cards and live roster restoration. This work concerns the recruiting pipeline; it does not yet unify its separate simulated HS competition with the recruit identities.
- Fix CCH-07/PBK-05 integrated save parity failures: CoachCard.__post_init__ treated an explicitly saved neutral chemistry score of 50 as a missing field and backfilled it from an attribute that may have developed since generation. Restore explicit persisted scores after construction. Benchmark now reports specific mismatched card fields if parity still fails.

## Validation

Five focused tests for grade strength, same-name transfer identity, walk-on depth/numbering, player metadata roundtrip and neutral coach chemistry persistence. Integrated benchmark checks no invisible additions before recruiting, exact league-wide identity reconciliation after graduation/signing/walk-ons, existing roster floor and DB parity. Reports cohort pool means, graduating and signed counts, walk-ons and emergency walk-ons by transition. Reuse existing national/reduced and rare replay jobs. Validate long-run class growth and recruitment selection effects independently after the immediate pipeline correction; no claim that class distributions are now calibrated.

Previous CCH-07 corrected HTTP-client rerun 45515088072 failed two seeds at coach-card DB parity, one completed 297 games. PBK-05 run 45515322003 similarly failed two seeds at coach-card parity, one completed 297 games; focused defensive workflows passed. These are real failures, not a completed integration. Candidate rerun required. No historic save migration or full midseason player metadata persistence validation. No professional/international work or live deployment claim.

Next: finish integrated verification, inspect multi-year roster and position outcomes; CCH-08 adaptation only once career/roster persistence is reliable.
