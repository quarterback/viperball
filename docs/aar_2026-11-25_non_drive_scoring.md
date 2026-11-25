# AAR: drive and non-drive scoring reconciliation

Date: November 25, 2026. Follow-up to PR #360 and BOX-01.

## Defect

The Delta drive buckets measured the possessing side's change in the scoreboard between drive ends. That included some recovery bells in offensive PPD and omitted scores by the other side. The college page displayed rates but did not show an explicit total that could be reconciled with the final score.

## Accounting contract

Use the finalized play scoreboard ledger, including compound events (e.g., a return TD plus a bell). Each new drive records a half-open span of indices into the play log. Assign a scoring event to the owning team's drive only if it is an offensive TD, made scoring kick, or a pindown scored during that team's drive. All bells, safeties, and return TDs are non-drive points, regardless of when they occur. A pindown outside the kicking team's drive is also non-drive scoring. Bonus drives are ordinary drive attribution, not an additional scoring channel. Overtime uses the same attribution.

DYE bucket points and overall offensive PPD share the same drive totals. TD and kick incidence comes from the corresponding offensive events; pindowns do not count as TDs or made scoring kicks. Non-drive points are summed from the recorded events, not derived by subtracting drive totals from the final score. Unknown scoring methods remain visible under the non-drive breakdown. The final-score residual is reported separately and is never absorbed into non-drive points.

The college table shows actual points in each bucket, drive subtotal, non-drive subtotal and method breakdown, official final score, and unreconciled points. Historical results without explicit spans and reconciliation data show an unavailable notice instead of manufactured values. No changes to play resolution, scoring rules or EPA.

## Verification

Added targeted ledger tests for a recovery on the owning drive, a return TD plus bell, pindown attribution, safety, overtime marker and scoring, missing points, invalid/overlapping drive spans, and PPD consistency. Extended the existing analytics CI smoke to check exact reconciliation, bell/safety parity with the scoring profile, and matching drive totals and PPD. Full simulation and integration results must be confirmed in CI before merging; no local full-suite execution is claimed.
