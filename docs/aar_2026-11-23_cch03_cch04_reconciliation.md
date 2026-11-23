# AAR: CCH-03/CCH-04 reconciliation and playbook handoff

**Date:** November 23, 2026  
**Merged result:** [Integration PR #334](https://github.com/quarterback/viperball/pull/334), commit [35ca4e40](https://github.com/quarterback/viperball/commit/35ca4e40a9078f70b998b539fa4b67529b32a40b), based on `main` after CCH-03 merge [82e21fcb](https://github.com/quarterback/viperball/commit/82e21fcb539db2a42a3d59be19113ff5f102f158). **Both are on main; no live deployment verified.**  
**Original CCH-04:** [PR #333](https://github.com/quarterback/viperball/pull/333) and [CCH-04 AAR](aar_2026-11-23_cch04_team_installation.md).  
**Prior prototype:** [PR #329](https://github.com/quarterback/viperball/pull/329), explicitly a draft reference, not intended for production merge. See [coach playbooks AAR on its archival branch](https://github.com/quarterback/viperball/blob/claude/coach-playbooks/docs/aar_2026-11-23_coach_playbooks.md).  
**CCH-03:** [Merged PR #332](https://github.com/quarterback/viperball/pull/332), [CCH-03 AAR](aar_2026-11-23_cch03_defensive_coordinator_tactics.md).  
**Catalog:** [Merged PR #330](https://github.com/quarterback/viperball/pull/330).

## Merge strategy

The original CCH-04 branch was based on pre-CCH-03 main. When #332 merged, GitHub reported that #333 was no longer auto-mergeable. The conflict involves neighboring changes in `engine/game_engine.py`, notably feature switches, setup of tactical profiles and game-day weight resolution.

To preserve #333's original commits and author record, this integration branch was created **from the CCH-03 merge on main**. The changed files from #333 were copied into it. The game engine was reconciled explicitly: it retains the new DC pre-snap call, pass-rush and alignment integration, focused defensive reads and play-log reporting from #332, while incorporating CCH-04's OC installation, package triggers and referee RNG isolation. The integration adds a focused DC familiarity bridge, dedicated integration tests and GitHub CI. #334 merged after all checks passed. Original #333 was closed as **superseded**, retaining its authorship/history and benchmark report. The separate prototype #329 was archived and closed without merge.

## Defensive familiarity integration

CCH-04 records defense installation but intentionally left its game-day effect for CCH-03. The integration calls `team_installation.defense_execution_factor(team.installation)` when a DC tactical profile has been resolved. The factor scales only **the DC's personal discretionary authority** used by pre-snap alignment, blitz propensity and read-focus allocation. It does not weaken a team's baseline defensive scheme, the original DC gameplan, player contest, or existing defensive-read machinery.

- **No record** → factor 1.0, exactly the merged CCH-03 DC behavior.
- **New installation** → initially lower factor (for example, 0.30 when book familiarity is 1.0 and coordinator familiarity is 0.30).
- **Full installation** → factor 1.0, full DC tactical expression.
- **Stale record from a different DC** → no reduction until CCH-04's existing pregame `sync_installation` aligns the team with its current staff.
- **`team_installation_enabled=False`** → full CCH-03 behavior remains; **`defensive_coach_tactics_enabled=False`** → no new DC calls.
- The full result's `defensive_coach_tactics.<side>.installation_execution_factor` exposes the value applied.

The DC's pre-snap alignment and blitz decision remain a single decision before the offense reveals its play family. No second pressure roll or global defensive suppression bonus was introduced. A CCH-04 **defensive package installation** may be visible in team data, but this merge does **not yet implement situational defensive package effects**. That requires a separate, measured decision resolver; do not claim those packages already alter the defense.

## CCH-04 content retained

- `engine/team_installation.py`: offense and defense installation records, coach familiarity, scheme familiarity, predecessor influence, catalog packages, player/roster fit and deterministic save/load.
- Offense: package activation changes bounded CCH-02 formation/family/kick-pass choice weights in the applicable situations.
- `engine/dynasty.py`: persistent records, offseason growth, coach carousel separated for app `/dynasty/advance`.
- `engine/season.py`: pregame installation sync, postgame learning increments and same records passed between weeks.
- `api/main.py` and React: visibility of installation on team pages; dynasty advance runs coaching decisions.
- `data/playbooks/vocabulary.json` and catalog package records: longer yardage defined relative to **six downs to gain twenty**, not gridiron ten yards.
- First-game referee pool: name generation no longer perturbs the global simulation stream.
- Odd-program dynasty start policy from original CCH-04: retire Coast Guard when needed (or Merchant Marine if Coast Guard is the selected program).

## Evidence and tests

Prior isolated CCH-03 validated **150 tests and 320 full-engine games**. Isolated CCH-04 PR #333 reports **157 tests and 300-game comparisons**, plus a reported **168-test trial integration**. These are **historical branch results, not evidence of this final integration branch**.

This integration branch includes:
- `tests/test_cch03_cch04_reconciliation.py`: with real engine games, verify that a DC's applied authority scales at 0.30/0.75/1.00 familiarity without changing the scheme, and that no-record and both off switches preserve older behavior.
- `.github/workflows/cch03-cch04-reconciliation.yml`: targeted tests, the complete `tests/` suite, 80 games per installation condition and 40 paired games per DC/scheme/mode using the original CCH-03 benchmark.
- **Final CI:** [CCH-03/CCH-04 integration run 45284723882](https://github.com/quarterback/viperball/actions/runs/45284723882) passed **35 targeted tests, all 174 repository tests, the React TypeScript/Vite production build, and both full-engine benchmark jobs**. Additional [CCH-02](https://github.com/quarterback/viperball/actions/runs/45284723887), [CCH-03](https://github.com/quarterback/viperball/actions/runs/45284723845) and [DEF-01/02/03](https://github.com/quarterback/viperball/actions/runs/45284724323) workflow checks passed.
- **Integrated installation study:** 80 matched games per condition, five conditions (400 games). Fully established installation reproduced the no-installation game logs exactly. New hire reduced Spread selection to 49.9% versus 52.4% with no installation; second-year familiarity reached 51.1%. The two observed packages activated 627 and 223 times across the 80-game package condition. These are conditional choices, not score targets.
- **Integrated DC study:** 40 games × two saved DC profiles × two defensive schemes × enabled/disabled (320 full-engine games). Lockdown selective-pressure DC called blitz on 15.9% of snaps versus 4.0% for run-wall DC; Blitz Pack 54.6% versus 42.9%. Disabled-profile per-game scoring controls matched exactly. These counts are calls, not proven pressures or sacks.
- [Integrated benchmark artifact](https://github.com/quarterback/viperball/actions/runs/45284723882), 90-day CI artifact retention. Final validated result is merged on `main` as PR #334.

## Provenance of closed draft prototype PR #329

PR #329 tested **whole-book borrowing**, mixed defensive package borrowing, package selection by situation and matchup, and prototype UI. Its AAR reported 300/360-game diagnostics, including borrowed long-yardage calls gaining 5.35 yards against 4.94 for home calls and weaker results from borrowing system-level identity bonuses. Those observations motivated the **bounded, situational, catalog-package** implementation in PR #333.

The original prototype's `engine/playbooks.py`, whole-book swapping and extra multipliers are deliberately **not copied** into the merged system. PR #330 supplies catalog package metadata; PR #333 supplies a team installation and observed offensive package influence; PR #332 supplies the pre-snap defense decision machinery. The proper next extension is measurable defensive package selection through a single DC call, not resurrection of draft #329.

## Remaining work

1. Complete a live-site deployment smoke test, plus a full dynasty season and staff turnover path on the deployed app. Branch CI has already passed its full tests, matched benchmarks and React build. No deployment is claimed here.
2. Add defensive package calling only after a distinct, roster-compatible defensive effect and its cost can be validated against DEF-06/DEF-07.
3. Improve event data for first-play-of-drive, after-turnover, after-score and defensive fatigue situations. Until that exists, CCH-04 excludes packages whose situations cannot trigger.
4. Add actual pass-rush pressure/hurry instrumentation (DEF-07). `blitz_calls` is a play-call count, **not** a measurement of pressure.
5. Keep PR #329 linked as an archive of the original prototype and its findings; do not merge its branch into this implementation.
