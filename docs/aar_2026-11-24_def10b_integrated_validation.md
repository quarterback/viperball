# DEF-10B — Integrated natural package adoption validation

Status: validation harness committed; independent dynasty results pending. Integration branch contains #364, #365 and #366. The other agent's #367 was open at inspection and is not included in this baseline.

## Observed CI evidence

ENG-01 workflow run 45487719197, job 138777443389, on commit 9537c940: 2026 and 2027 both completed 96 regular games and three playoff games. Both offseason database roundtrip checks passed; 2028 start failed the roster-name equality assertion. 2026/2027 recorded 2,133/4,598 defensive-package calls and 11/9 distinct installed IDs. This is partial evidence, not a completed dynasty study. The separate integration regression workflow succeeded; the combined calibration failed.

The assertion previously compared names extracted from a dictionary keyed by player identity with the full saved roster list. A duplicate identity could be hidden by this dictionary. Compare raw roster entries instead, print duplicate identity counts separately, and emit exact missing/extra name multisets on actual mismatch. This is a diagnostic correction, not proof of a roster persistence fix. Keep the equality gate. The benchmark writes partial results after each season and offseason transition.

## Independent validation

Existing integrated CI runs three isolated process trajectories: seeds 20261124, 20261125, 20261126, each 16 programs and three seasons (297 games per trajectory if fully completed, 891 total). Run the rare-state study as well when its script changes. Retain artifacts even on failure and preserve failed exit status. This is a reduced-league study, not a national study. Natural adoption is measured by #365's per-package compatibility, personnel eligibility, ranking, installation and activation fields; #366 supplies controlled fatigue comparison. Do not infer causality from selected snaps or compare whole-season activation counts directly with end-of-season snapshot counts.

No score or sack targets. #367 modifies sack resolution, scheme normalization, recruiting and other shared mechanics, so rerun on the final integrated baseline after that PR is reconciled. Do not merge the integration PR and its component branches independently. No successful multi-seed result or deployment claim yet.
