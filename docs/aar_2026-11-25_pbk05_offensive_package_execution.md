# PBK-05 — College offensive package execution

Status: implementation committed; candidate runtime validation pending. Builds on CCH-07 #374 and DEF-11 #373, including VAL-05 #372. College-only scope.

## Findings

The previous offensive path applied every installed package whose situation tags had any overlap with live conditions. This meant Kick-In Breakout could activate on any first snap, Restart Go-To on the wrong drive origin, Fast Break after any first snap, and Last Tackle Kick outside the launch pad. Formation, play family and kick-pass subtype independently recalculated package pull; multiple plans could stack. The existing selected.packages counter recorded eligible biases, not a deliberately selected plan or a successful choice.

## Implementation

- Require both catalog conditions for Kick-In Breakout, Restart Go-To, Fast Break and Last Tackle Kick. Preserve alternative triggers for packages such as Vertical Shot and Launch Pad Kick Set.
- Choose zero or one eligible plan before formation selection, using a separate seeded random stream for each offense. Keep an ordinary home-book call available, even at full familiarity. Selection ceiling is .90 times coordinator authority times maximum eligible familiarity; competing packages are weighted by familiarity. These are proposed decision weights, not success targets.
- Carry the same plan through formation, family and kick-pass subtype selection. Keep the existing .12 familiarity-scaled pull and bounded proportional OC weight adjustment. No additional yardage, completion, turnover or scoring modifiers; existing down/range constraints remain authoritative.
- Record an offensive_call event with snapping side, live situations, eligible package IDs, selected plan and actual choices. Keep selected.packages as plan-call counts; add packages_eligible, packages_family_matched and packages_all_matched. A match is an observed alignment with the plan, not causal proof or successful execution. All-matched refers to evaluated choice categories.
- Retain the previous situational_bias helper for existing direct callers; engine snaps use the new coherent plan path.

## Acceptance

Four focused tests cover compound triggers, alternatives, deterministic single-plan selection with an ordinary-call option, legal weight preservation, and actual-choice matching. Existing full-engine team-installation test reconciles play-level calls with summary counters. Integrated dynasty benchmark reconciles offensive eligibility/selection/matching counts for each game and records non-nullified outcomes by selected package. Existing schedule, roster, staff, postseason and persistence gates remain active. Compare natural usage and outcomes to the merged baseline; no required usage frequencies or scoring target. No new CI workflow.

## CCH-07 follow-up

Initial integrated run 45514603235 reached the offseason after all three first seasons, then failed because a loop variable named c shadowed the HTTP client. Commit 6cb9627 renames the API client; included here. This is a benchmark error, not proof that the coaching lifecycle is fully validated. The corrected rerun remains pending. DEF-11 reduced calibration passed; national jobs were still in progress at last inspection.

Next: ROST-02 and HS-01, investigating actual recruited cohort strength, college development, positional depth and player transitions over longer dynasties. Separate later work: coaching tactical adaptation, finer offensive package tradeoffs and stats-site display of the new detailed offensive calls. No pro or international changes requested.
