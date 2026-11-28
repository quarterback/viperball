# COACH-CASE-03 after action record

November 27, 2026. Added live same look sequencing, bounded possession memory, situational pacing and box score explanations. Built on the local Cookbook branch at `6952d66` with CASE-02 and the cross code packages. Standalone college seasons and dynasty seasons use the common `Season` game path. [Coaching spec](../COACHING_SPEC.md) · [Policy audit](COACH_CASE_01_POLICY_AUDIT.md)

## Game behavior

A completed probe preserves the previous action and the defensive front shown, with a four snap window on the same possession. The caller considers the other installed package after a stacked or aggressive front. The existing selector uses the target package's own authority and familiarity gate. Its normal eligibility rules, formation weights, family gates and subtype weights still apply. Nullified snaps pause the observation window. Kick mode, down and distance, clock priority, a missing package and an unavailable action have separate traces. CPU books can derive pairs from compatible installed catalog packages. Explicit version 2 books use the authored pairs.

For an immediately available counter after a gain or first down, a caller with tempo preference at least 60 can choose quicker setup if an eligible Zeroback on the field has at least 55 energy and the clock is running. The clock model applies the four second base setup reduction before its normal limits. The trace shows chosen pace, setup time and actual game time elapsed. This package uses the caller selected at game setup and the established special package resolvers. Midgame handoffs and additional player reads remain separate work.

## Verification

`venv/bin/python -m pytest -q tests` passed 350 tests with 50 dependency deprecation warnings. The final focused rerun passed 34 tests. Python compilation and `git diff --check` passed.

The standalone season regression uses four real teams and a version 2 Ghost book. It assigns the book at setup, simulates Week 1, checks the paired decision and revision in the play log, opens the box score and verifies the archived trace. The existing test also exercises computer team Cookbook adoption. For the reported dynasty trouble, a fresh local Gonzaga dynasty with an assigned book passed the stats site creation and Start season forms, college hub, preseason portal skip, Week 1 and the box score. The reported failure in the user's run remains unidentified.

Matched full engine games used the Alabama and Duke files, roster seed 104 and game seeds 14 and 31. The same Ghost staff and full familiarity Split pair used Third Strike as the probe and Viper Trail as the answer. The table counts observed results from the two games per defense.

| Opposing scheme | Probe snaps | Counters | Quick setup decisions |
|---|---:|---:|---:|
| Fortress | 57 | 34 | 7 |
| Drift | 88 | 8 | 4 |
| Blitz Pack | 48 | 27 | 13 |
| Lockdown | 76 | 7 | 2 |

Matched regression checks covered staying with ordinary calls against width, eligible counters that differed from the probe, caller attribution, erased plays, down and distance, depleted Zerobacks, a patient caller and the feature switched off. The sample shows differences in choices. National and long career calibration remains under CASE-VAL.
