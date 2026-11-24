# VAL-04 / DYNA-02 — National dynasty validation

Status: implementation committed, runtime results pending. Consolidates #369 and its predecessor work. Base: main 6d106f70; separate agent's #367 not incorporated.

## National coverage

The earlier #355 national study ran a single regular season with all 205 program files. The #368 study ran 891 full games over nine reduced-league seasons, and exposed player identity collisions. #369 addresses cohort identity and pipeline persistence; its new integrated rerun was still in progress at inspection.

The playable dynasty differs from a standalone season: its existing API requires an even active program count and automatically retires Coast Guard (or Merchant Marine when appropriate) for an odd league. With the current 205 files, the expected active league is 204 programs, 1,224 regular games and seven playoff games per season. The harness does not change that policy or silently drop arbitrary schools.

## Implementation

- Reuse the existing dynasty API benchmark with all program files and default geographic conference alignment; no artificial two-conference grouping in national mode.
- Validate the explicitly reported retirement, exact active program membership, quotas, duplicate games, weekly double-bookings, full-engine game counts, playoff champion, score consistency when supplied, roster identity/position parity, no package fit violations, and database continuity.
- Checkpoint schedule inventory and partial season/transition results.
- Code inspection uncovered repeated redistribution of freshly generated rosters from already-retired programs. Persist pending retirements and limit dispersal to newly retired programs or authoritative saved rosters. Remove retired programs from automated NIL, portal and recruiting offers, and filter stale portal offers. Prevent retiring the human-coached program. Do not rewrite retired program history or alter scoring/talent generation.
- Add focused tests for one-time retirement and database roundtrip state. Existing old saves lacking the pending marker default to an empty list; a saved roster remains an eligible dispersal source. The manual retirement/restore path and full national offseason still need runtime validation; broader frozen-staff lifecycle and existing historical collisions are not repaired here.

## Execution

The existing integrated calibration workflow gains a national matrix gated by successful reduced-league validation. Two seeds (20261124 and 20261125), two seasons each, real API season, playoffs, coaching, recruiting, portal and DB reload. Expected 4,924 full games if 204 programs are active. Artifacts retained on failure; the new national job also supports explicit workflow dispatch. No new standalone workflow.

Reproduce: PYTHONHASHSEED=0 python scripts/benchmark_national_dynasty.py --seed 20261124 --out reports/national-dynasty.

## Remaining acceptance

Observe actual results, not planned counts. Investigate any schedule, identity, playoff or persistence failure without weakening validation. Rerun on the final reconciled #367 baseline; changes to recruiting and pressure physics there make this branch's tactical results provisional. Review natural package adoption only after successful independent national runs. No activation, scoring or sack-rate target. No live deployment claim. Do not merge predecessor branches independently if this consolidated candidate is merged.
