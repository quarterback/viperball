# AAR: merging the open PRs (November 24, 2026)

## What was asked

Ron asked to merge all the open PRs.

## What happened

1. Rebased #367 (rules, drift, sacks, ladder, fast sim removal, officiating, rating scale, High
   School section) onto main, which had picked up the analytics plan doc, and force pushed it.
   The rebase had no conflicts.
2. Merged #367, then #363 (next engine stages doc).
3. Six PRs were drafts: #364, #365, #366, #368, #369 and #370. The merge endpoint refuses
   drafts, so each was marked ready for review first.
4. Merged #364 (ENG-01 schedule fulfillment).
5. #365 and #366 were stacked: #365 targeted the #364 branch and #366 targeted the #365
   branch. Each was retargeted to main and merged in order, so their changes reached main
   instead of landing on a branch that was already merged.
6. Merged #368 (DEF-10B), #369 (DYNA-01) and #370 (VAL-04 / DYNA-02).
7. #361 (STI-VAL) merged cleanly but changed nothing: its content was already on main
   through #358.
8. #362 had conflicts. Every change in it was already on main through #367, which carried its
   commit in rebased form. Closed it with a note saying so.

## Not done

1. No tests were run for this pass. Ron stopped the test run and asked for the merges only.
   CI on #367 had passed tests, benchmark, targeted tests and integrated checks on the
   commit before the rebase; the long matched games and regression jobs were still running.
2. #371 (VAL-04 evidence and PRO-02 WVL continuity) was opened by another agent less than a
   minute before the merges finished. It was left open because its branch was likely still
   being written.

## State after

Main is at the #361 merge plus this AAR. The only open PR is #371.
