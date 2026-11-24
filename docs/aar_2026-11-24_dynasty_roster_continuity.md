# DYNA-01 — Dynasty roster and recruiting identity continuity

Status: implementation committed; regression and integrated rerun pending. Based on #368, which contains #364–366. The separate agent's #367 is not incorporated into this branch.

## Observed evidence

The integrated workflow run [45498006438](https://github.com/quarterback/viperball/actions/runs/45498006438), job 138813524833, completed successfully on commit b924ad6b. Seeds 20261124, 20261125 and 20261126 each completed three seasons, with 96 regular games plus three playoff games per season. Total: 891 full games and 30,419 defensive-package activations. All raw roster-name multiset comparisons and database roundtrips in that study passed. All nine seasons had zero roster-fit violations. Other existing PR #368 workflows also passed.

The original 2028 mismatch was attributable to the dictionary-based roster comparison dropping duplicate identities. Within-program collisions were found in all three 2028 rosters: 3, 7 and 1 extra entries sharing keys, respectively. The revised benchmark logs exact identities and owners and treats a league-wide identity collision as a failure. A raw name match alone is not sufficient.

Exhaustion Press had 25 qualified-but-not-installed program-season observations; Robber Coverage had 35. Neither was installed or called in the nine-season sample. These are snapshots, not independent programs or evidence that the packages should be given preferential treatment.

## Production defects identified by inspection

- The high-school pipeline used grade-index IDs for every newly generated class. IDs persisted as players moved grades, so repeated generations could reuse an existing prospect's identity.
- The application dynasty DB did not preserve the HS pipeline. Reloading could recreate the prospect population rather than continue the same cohorts. The WVL bridge preview is not a lossless dynasty save.
- Season start swallowed errors while converting saved PlayerCards, could fall back to freshly generated rosters, and consumed the saved snapshot before setup completed. Custom programs were constructed after restoration.

## Implementation

Assign pipeline-generated prospects stable graduation-cohort IDs. Persist the cohort sequence separately from random seeds; repeated seeds do not cause ID reuse within a continuing pipeline. Existing public flattened pipeline output is unchanged. Persist full nested prospect/recruit state with a versioned application DB save format. Older saves with no pipeline state continue through the existing lazy initialization; do not silently rewrite IDs or historical career records.

Restore known program rosters only after all saved records convert successfully, including custom programs. Invalid or empty saved rosters return an explicit conflict rather than silently skipping records. Keep the finalized snapshot until successful season setup. New programs without saved records retain their initial rosters.

The benchmark now checks league-wide ID uniqueness and full pipeline roundtrip equality in addition to roster-name equality and exact schedule quotas. Added focused regression coverage for seven successive classes, repeated seeds, database roundtrips and atomic restoration. Standalone simplified JSON dynasty save/load is not extended by this change. Existing legacy identity collisions are not migrated or deduplicated.

## Acceptance and remaining work

Run existing regression and three independent dynasty trajectories on this branch; reconcile with #367 before making final claims. No assertion yet that the 2028 collisions are resolved, nor that all legacy records can be restored. Investigate any remaining collision by reported player ID and team; do not erase duplicates to pass. This changes no talent generation formula, scoring target, sack physics or package weights. After continuity is verified, proceed to the national schedule/dynasty study and package-specific adoption assessment. Do not merge predecessor PRs separately if this consolidated candidate is merged.
