# DEF-10C — Relative fatigue and Exhaustion Press

Status: implementation committed; runtime evidence pending. Stacked on DEF-10A (#365) and ENG-01 (#364).

## Findings from inspection

The existing call eligibility uses mean attacking XI energy, while the rush resolution uses actual assigned rushers and blockers. Exhaustion Press changes pressure commitment, coverage and energy cost; the earlier rare-state study did not hold defensive readiness constant. It did not establish a reliable pressure advantage. The rush event previously exposed participant identities and skill but not their mean energy before the rush charge.

## Changes

Add actual assigned blocker and rusher mean energy to existing rush events (null when none). No change to the contest, probabilities, player selection or scoring. Extend the existing rare-tactics replay, keeping the previous cases, with a crossed controlled fatigue study: offensive energy 65 or 72; defensive energy 90, 65 or 50. Each scenario uses matched source snaps, legal offensive responses and restored random state across package-off and eligible-package-on arms. Report actual participant energy, relative energy, protection/rush skill, sack probability, coverage cost, completion and yards, and defensive energy loss. These are enriched snapshots, not natural activation estimates. Uniform whole-roster energy intervention is a diagnostic simplification, not a model of actual rotation.

## Acceptance and remaining work

Run the existing rare-tactics benchmark and integrated regression; inspect paired outcomes by response and fatigue combination, including deep-kick concessions. Collect independent natural dynasty observations using #365. Do not tune any sack coefficients or scoring distributions; other agent owns those. Do not increase Exhaustion Press usage to manufacture samples. If results do not establish a benefit, document uncertainty and preserve the current bounded mechanics until a specific defect is identified. Existing benchmark command: PYTHONHASHSEED=0 python scripts/benchmark_rare_tactics.py --games 48 --cap 120 --seed 20261124 --out reports/rare-defense. Repeat with an independent seed. Expanded study increases replay workload; CI runtime not measured yet. No runtime or deployment claim.
