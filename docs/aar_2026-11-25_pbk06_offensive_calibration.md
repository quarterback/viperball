# PBK-06 — Offensive tactical calibration and remaining college work

Status: benchmark implementation; no outcome evidence until the workflow runs. Current baseline PR #377, 34a00fd, includes WEA-02 and SCALE-01. College only.

## Experiment

Compare each of the fourteen offense packages against the same installed package with its plan suppressed before formation selection. The control still computes eligibility and uses the package random stream; no package success, yardage, scoring or turnover coefficients change. Both arms execute the full engine, with identical starting rosters, coach cards, seeds, venue and weather. Use deterministic fresh national roster profiles to enforce catalog personnel fit. Compare native and borrowed families, a catalog counter scheme and a noncounter scheme, and record actual opponent, weather and familiarity. Weather and familiarity rotate together in this initial small sample; do not estimate separate causal effects from them. Explicitly report cells with no fitting roster or no eligible snaps.

Whole-game policy differences are paired; differences in eligible snaps reflect changed game state and are descriptive, not per-snap causal effects. Track all eligible, selected and resolved snaps; nullified fouls; observed formation/family/subtype matching (including denominators); yards, explosive gains, first-down/TD outcomes, kick completion and sacks, turnover result labels, and full-game points, yardage, touchdowns, fumbles lost and interceptions. A fumble result is not necessarily a lost possession. No target utilization rate, score or forced success. Package counts reconcile to the engine ledger. Study runs as an independent job in the existing integrated workflow. Partial JSON is checkpointed per package.

First pass is two pairs per cell (up to 112 pairs/224 games). This is screening, not sufficient to declare balanced packages or estimate precise effects. Expand sparse or contradictory cells with independent seeds and matched pre-snap replay before changing runtime weights. Do not infer matchup superiority from raw selected/ordinary outcome splits.

## Continuation order (user requested offensive calibration first)

1. PBK-06: run the study; read results, isolate weak differentiation, adverse tradeoffs and unobserved rare situations; use matched replays where necessary. No coefficient changes without evidence.
2. VAL-05/HS-01: close the pending combined reduced and national acceptance gates, including weather, unique college/HS identities, recruiting and save parity. Resolve actual defects before claiming acceptance.
3. CCH-08: bounded coach tactical adaptation using observed multi-game evidence, explicit sample floors, shrinkage and persistent decision history. Preserve career identity; no extra generic success bonus. Existing career/roster persistence must pass before enabling adaptation.
4. Longitudinal college dynasty: 5- and 10-season trajectories using existing benchmark; track incoming and graduating class distributions, positional deficits, replacement and walk-on sources, talent tails, coach movement, installations and save/resume. Compare baseline/adaptation using matched seeds. No fixed talent target without an evidence-based decision.
5. FAT-01 / DEF-04 / DEF-05: coach-specific rotations and actual eleven-player participation, depth and energy accounting; audit legacy scheme calls and attribution before retuning. Matched fatigue/injury/roster studies and existing invariants.
6. Final integrated verification: full suite, national seeds, long-run persistence, reproducibility and deployed college smoke; document actual build SHA and known limitations. Analytics, pro and international work remain separate.

Each step belongs on the consolidated branch unless explicitly delegated. Keep main synchronized, preserve previous AARs, and add findings, exact commands and run links as evidence arrives.
