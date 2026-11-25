# Viperball engine: next-stage handoff and agent coordination

**Current status and ownership:** See [the consolidated development plan](DEVELOPMENT_PLAN.md). This document retains its original assessment, requirements and historical task statuses; it is no longer an independent active queue.

**Reviewed:** 2026-11-24 (Pacific). **Base:** main at `6d106f70b99a037b2cfc5e52cf8afc7041060809`. **Status:** planning only; no new gameplay mechanics or validation claimed.

## Correction to previous handoff

The statement “installed defensive packages have records but no game-day effects” was true immediately after CCH-04 (#334), **not** after subsequent integrations. CCH-05, DEF-07 and CCH-06 landed in #337/#339; expanded 13-package, one-to-six-rusher commitments landed in #340; targeted rare-state replay in #342; and three-season dynasty persistence/calibration in #344. Do **not** reimplement CCH-05. Sources: `docs/aar_2026-11-23_defensive_packages_pressure_events.md`, `docs/aar_2026-11-24_expanded_defensive_commitments.md`, `docs/aar_2026-11-24_rare_tactical_situations.md`, and `docs/aar_2026-11-24_dynasty_tactical_calibration.md`.

PEN-01/INJ-01 (#350), special-teams integration (#354/#356), blocked-kick/seed benchmark follow-up (#358), DEF-08/DEL-01/02 (#355), BOX-01 (#351), and AN-01/DTW-01/EPA-01 (#360) have also merged. Earlier OPEN lines in `docs/ASSESSMENT_PRD_ENGINE_TACTICS_2026-11-23.md` are historical and must not be treated as the current queue.

## Concurrent work — check before touching shared files

- **#361 (open at review):** STI-VAL wider seeded 3,000-game benchmark and last-play blocked-place-kick attribution. Owner: other agent. Review/merge or supersede before modifying special-teams benchmark or terminal-half kick logic.
- **#362 (open at review):** queue cleanup, transfer-portal prestige scale and root test-script repairs, with `docs/aar_2026-11-24_status_and_next.md`. Owner: other agent. Avoid editing the existing queue document before #362 merges; reconcile its status afterward.
- **Analytics plan already on main:** `docs/analytics_development_plan_2026-11-24.md` describes AN-02/03, EPA-02/03/04 and DTW-02. That is a separate parallel workstream. Coordinate game event/ledger fields, do not create a competing EPA or analytics plan.
- Retired React `web/` is not the target. Current rendering lives in `stats_site/router.py` and `stats_site/templates/`.

## Proposed order after #361/#362 disposition

### ENG-01 — Schedule fulfillment and multi-seed dynasty reproducibility (P0)

**Finding:** The #344 natural 16-program, three-season API study produced 94/95/95 regular games against 96 requested per year. All *generated* games completed; missing schedule entries caused the shortfall. Only one dynasty seed was tested.

**Implementation:** Diagnose the scheduling algorithm and bye/opponent constraints; make schedule length fulfillment explicit for each school, including uneven/reduced leagues. Preserve valid calendar/conference constraints; report impossible requested schedules rather than silently dropping games. Test through the actual app API, database reload, season progression and playoffs, then run independent multi-seed natural dynasty trajectories. Scale to national league only after reduced-league fulfillment passes.

**Acceptance:** Each feasible requested program schedule matches its count; sum of team-game counts equals twice the regular games; no duplicate matchups outside intended format; all scheduled games and playoffs resolve; team/game/stat ledger reconciles. Capture seeds, leagues, requested versus actual schedules, failures, runtime, package installation and coaching turnover.

### DEF-09 — Pressure/sack realism and player credit (P0 investigation, conditional tuning)

**Finding:** The three-week all-program audit after #340 found 32.1% pressure and 13.1% sacks on 15,750 kick-pass attempts, with leader credit still concentrated; #344 natural dynasty saw 11.6–12.4% sacks across seasons. #355 changed credit assignment, not the sack physics. No calibrated coefficient change has been approved.

**Implementation:** Establish whether `kick-pass attempts`, `rush attempts`, sacks, early stops and pressure share consistent denominators. Break down sack/hurry by quick/territory/bomb/kick-lateral releases, protection, called vs physical rushers, fatigue, weather, schemes and installed package. Compare matched control with limited hypotheses; distinguish excess sack generation from attribution concentration. Do not import an NFL sack target as Viperball's rule.

**Acceptance:** Event-level reconciliation (one resolved rush outcome and legitimate eligible defender credit), repeatable paired samples, subtype and roster strata, defensible explanation and observed tradeoffs for any tuning. No broad scoring fix via hidden sack multipliers.

### DEF-10 — Natural catalog adoption and rare-package effectiveness (P1)

**Finding:** Of 13 defensive packages, #344 installed 11 in year one and 9 in each later year. Exhaustion Press and Robber Coverage were never installed; Exhaustion Press had no calls despite 3,379 fatigue-exposed DC calls. Six-rusher usage remained rare. #342 replay supports conditional effects but not natural adoption.

**Implementation:** Decompose catalog recommendation, coordinator preference, package compatibility, roster fit, familiarity, opportunity and actual call counts **for every catalog ID**. Determine why packages are never installed or called before changing eligibility. For Exhaustion Press, verify relative protection/defensive fatigue predicates and their costs with matched replay and naturally eligible lineups. For other rare packages, collect matched tactical conditions without forcing production call frequencies.

**Acceptance:** Per-package funnel and matched on/off outcomes by opponent/play family/formation, including benefits and concessions; observed selection across independent dynasties and after staff changes; explicit not-enough-data status where appropriate. Do not boost rare package frequencies solely for prettier distributions.

### ENG-02 — Touchdown/turnover drift diagnosis (P1; no blanket retune)

**Finding:** #362's draft AAR reports a 200-game seed-2026 points/TD/turnover comparison across merges: touchdowns fell from ~3.32 after #323 to ~2.5 after #359; 52 points/team remained as place kicks rose; turnovers rose late. #331 changed roster seeding, so these are not all apples-to-apples comparisons.

**Implementation:** Once #362 is reconciled, reproduce adjacent merge comparisons with fixed roster fingerprints and independent seeds; examine drive start, kick/pass/run shares, punt/field-go choice, penalty nullifications, defensive pressure, turnovers, scoring by channel, and full ledger. Run causal toggles where existing switches allow. User decides whether resulting sport distributions need changes.

**Acceptance:** Locate specific code paths and measurable attributable shifts rather than asserting scoring must be a fixed target. Preserve 9/5/3/2/1/0.5, six downs for 20, legal returns and Delta rules.

### ROST-01 / SIM-01 / RULE-01 — Separate downstream contracts (P1–P2)

- **ROST-01:** Reconcile player rating ladder across recruiting, development, transfers and high-school game. Keep roster changes out of the pressure-calibration baseline until explicitly versioned.
- **SIM-01:** Document which competitions still use the fast simulator, and how/when they should use the full engine; avoid treating fast-sim results as college-game validation.
- **RULE-01:** Diff `RULES.md`, `docs/RULES.md`, actual engine paths and current AARs. Propose canonical documentation reconciliation separately from rule changes; do not silently adopt outdated rules baselines.

### DEP-01 — Live deployment smoke (nonblocking but still open)

Check actual deployed Fly service identity/version and gameplay/season/installation screens, including staff turnover and stats-site routes. A passed local FastAPI TestClient run is **not** live deployment verification. Record observed URL/version/time and failures without claiming service availability from config alone.

## Integration and evidence policy

1. Recheck **main and active PRs at start of every branch**. Do not assume #361/#362 have merged; avoid conflict with analytics work or current engine files.
2. Prefer ENG-01 first, then DEF-09/DEF-10 in one coordinated engine calibration pass; ENG-02 can collect baseline data in parallel. ROST-01 and SIM-01 require their own explicit ownership.
3. For each study report main SHA, code switches, seed strategy, roster fingerprint, sample size, outcome denominator, event reconciliation and uncertainty. Separate ordinary natural-game outcomes from forced rare-state replay and selected-snap comparisons.
4. Use the **existing test/regression/CI path**, not a new workflow for each feature. Add focused tests for demonstrated bugs and critical invariants; run full integrated validation before merge.
5. Update the source AAR and shared assessment queue **after** the implementation is observed and merged. This handoff records work to be done, not verified results.
