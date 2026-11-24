# AAR: status check, stale fixes and what's next (November 24, 2026)

## What Ron asked

Check the repo, rebase, see where things are and assess what's next.

## Where main is

Main is at #360. Since the last run, other agents merged #334 to #360:

- CCH-03 and CCH-04 integrated (#332, #334). My original CCH-04 PR #333 was closed as
  superseded; its code and the session AAR step 19 are on main through #334.
- Defensive packages, pressure events, rusher assignments, 13 packages with one to six
  rushers, rare situation and dynasty calibration (#337, #339, #340, #342, #344).
- The React app is retired. `web/` is gone and the game runs from the stats site (#336, #353).
  The installation panel moved to the stats team page.
- Penalties, injuries, spot errors, special teams coordinators and a 3,000 game special
  teams benchmark (#350, #352, #354, #356, #358, #359).
- Box score ledger reconciliation (#351), rusher credit and Delta Yards definitions (#355),
  scoring value and analytics scope (#360).

Nothing of mine was left unmerged, so the rebase was a reset onto main. The 181 test suite
passes.

## Fixed in this run

- **Work queue was stale.** `ASSESSMENT_PRD_ENGINE_TACTICS_2026-11-23.md` still listed
  PEN-01, INJ-01, ST-01, ST-02, STI-VAL, DEL-01 and DEL-02 as open after they merged.
  Statuses now link their PRs, and DEF-08, BOX-01, AN-01, DTW-01 and EPA-01 have rows.
- **Transfer portal prestige never moved to the new rating scale.**
  `engine/transfer_portal.estimate_prestige_from_roster` still used 0.9 times average
  overall. Fresh rosters now average 25 to 49 overall, so every program came out between
  22 and 47 and none read as strong. The stats site and the API use this number for the
  portal and NIL budgets. It now uses the same map as the engine's own prestige
  (35 overall is 50, each point is 1.9). Spread on a fresh league is 30 to 79.
- **Four root test scripts were broken.** `test_season.py` and `test_dynasty.py` loaded
  Xavier and St. John's files that no longer exist (now Georgetown and Johns Hopkins).
  `test_recruiting.py` had fixtures on the old rating scale. `test_wvl.py` imported a
  revenue function the Bourse economy replaced. All four run clean.

## Measurements

Standard benchmark (`scripts/benchmark_engine.py`, 200 games, seed 2026) at each merge:

| Merge | Points | TDs | Snap kicks | FGs | Turnovers | 30+ margins |
|---|---|---|---|---|---|---|
| #323 | 56.7 | 3.32 | 3.28 | 1.90 | 2.40 | 25% |
| #325 defensive reads | 53.8 | 2.90 | 3.26 | 2.06 | 2.37 | 20% |
| #328 | 54.1 | 2.92 | 3.36 | 1.94 | 2.62 | 20% |
| #331 VAL-02 | 53.2 | 2.73 | 3.33 | 2.16 | 2.48 | 22% |
| #334 CCH-04 | 53.2 | 2.73 | 3.35 | 2.15 | 2.49 | 22% |
| #337 | 52.2 | 2.65 | 3.29 | 2.14 | 2.51 | 22% |
| #340 | 51.7 | 2.57 | 3.38 | 2.07 | 2.45 | 17% |
| #355 | 52.1 | 2.61 | 3.32 | 2.39 | 2.76 | 20% |
| #359 (main) | 52.0 | 2.50 | 3.46 | 2.37 | 2.84 | 19% |

VAL-02 changed how seeds produce rosters, so rows before and after it are not the same
rosters. Confirmed with 500 games on seed 7: #331 gives 2.78 TDs and 2.43 turnovers,
main gives 2.65 and 2.72.

Findings:

- Touchdowns fell from 3.32 to about 2.6 per team per game. The biggest single drop is
  #325 (defensive reads). The rest is a slow slide through the defensive package work.
  Points held at 52 because field goals rose.
- Turnovers rose about 0.3 per team per game across #355 to #359.
- Touchdown rate barely depends on field position inside your own half: 16% from your own
  1 to 14, 15% from 15 to 25, 14% from 26 to 49, then 23% in the opponent's half.
- Physical sack rate is 13.1% of rush attempts (#355 national season), about twice real
  football. No agent has changed the sack coefficients.

## What's next

1. Touchdown and turnover drift. Find which defensive and special teams changes cost the
   touchdowns and added the turnovers, then decide with Ron whether 2.6 is the sport he
   wants.
2. Sack rate. 13% is the main outlier left in the pass rush work.
3. ROST-01: recruiting, development and the high school league still generate players
   around one number instead of the talent ladder.
4. SIM-01: WVL and the high school league still run the fast sim.
5. RULE-01: `RULES.md` and `docs/RULES.md` still describe the old rules.
6. Live deploy: nobody has confirmed the Fly machine serves current main.

## Not verified

Live site. Benchmarks are one or two seeds each.
