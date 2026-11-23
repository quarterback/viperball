# Viperball engine and tactics assessment: implementation PRD and agent work queue

**Assessment date:** 2026-11-23  
**Status:** Open for implementation; documentation-only baseline  
**Repository:** quarterback/viperball  
**Current implementation follow-up:** [PR #325](https://github.com/quarterback/viperball/pull/325) (draft, unbenchmarked; targets PR #323).  
**Reviewed implementation:** [PR #323](https://github.com/quarterback/viperball/pull/323), branch claude/fix-league-hub-null-status, head 3aedd95d59f5c44291d473e4fd30c7b50e69151b at review. PR #323 was open and mergeable, **not merged**, at the time of writing. Main did not yet contain those changes.

## Purpose and decision

This is the shared work queue for agents making Viperball's simulation coherent, tactically differentiated, measurable, and visible to players. It preserves the findings of the November 23 repository/branch review and turns them into bounded, testable engineering tasks. It is **not** a change to the sport's rules, a blanket authorization to retune scoring, or a claim that all the listed defects are already proven by tests.

**Priority order:** (1) connect and verify defensive tactics, (2) establish meaningful eleven-player defense/rotation, (3) validate and explain Delta Yards, (4) make player development and scheme assignment consistent, (5) show the sport in the React app, (6) reconcile remaining simulation paths and documentation.

The key principle: explain results from **players, decisions, conditions, field position, and matchups** instead of tuning only the league's aggregate points, kicks, and final margins. Do not impose a predetermined close-game, blowout, or home-win percentage.

## Coordinated coach/playbook workstream

The parallel implementation specification is
[Coach-owned tactical identities and expandable playbooks](PRD_COACH_OWNED_SCHEMES_AND_PLAYBOOKS_2026-11-23.md).

- **COACH track (ChatGPT):** CCH-01 stable CoachCard tactical identity is [in review in PR #327](https://github.com/quarterback/viperball/pull/327) with passing CI. CCH-02 game-day integration, CCH-03 DC/HC decisions, CCH-04 team installation and career continuity are open.
- **PLAYBOOK track (separate agent):** PBK-01 catalog/schema, PBK-02 family packages, PBK-03 wider playbook expansion, PBK-04 compatibility guidance.
- COACH owns `engine/coaching.py`, `engine/coach_tactics.py`, `engine/game_engine.py`, season/dynasty integration and tests. PLAYBOOK owns `engine/playbook_catalog.py`, `data/playbooks/**` and catalog/package tests and documentation. Coordinate any changes to shared files.
- Keep existing 16 offenses, eight defenses and canonical play-family names. Avoid multiplying coaching bonuses without bounds.

## Source control and evidence rules for every agent

1. **Read PR #323 before starting.** The Nov 22 engine fixes and Nov 23 game-day work are on its open branch, not main. The newer Nov 23 [work-rate and shift-rotation AAR](https://github.com/quarterback/viperball/blob/claude/fix-league-hub-null-status/docs/aar_2026-11-23_work_rate_and_shift_rotation.md) supersedes parts of the earlier fatigue assessment. Refresh status before changing code; merge or rebase decisions belong to the implementing agent.
2. Read this PRD and the relevant files below, including existing AARs and RULES_EVOLUTION_AAR.md. A past AAR describes what was done at the time; recheck live code before treating a finding as current.
3. Work on **one scoped work item per implementation PR** (or a justified tightly related group). Reference its identifier in PR title/body. Do not put unrelated engine, UI, and roster changes in one large PR. Keep this assessment document updated as work is merged.
4. For every change provide **before/after seeded full-engine benchmarks**, tests for the mechanism, and a brief description of downstream consequences. Measure per scheme, per game state, and per roster; do not just cite an overall season average. No success claims from the fast simulator for the college game.
5. Report whether a statement is **verified directly in code**, **reported by PR #323 AAR**, or **proposed / needs experiment**. In particular, an unused-looking field may be intentionally superseded: verify before reviving it, and avoid double-applying modifiers.
6. Acceptance requires a reproducible test, a demonstrable player/game consequence, and parity of the relevant reported metric. Update changelog/AAR and this queue status. No item is complete because it was only documented.
7. Preserve canonical rules (six downs for 20 yards; scoring 9/5/3/2/1/0.5; no forward throw; Delta Yards after scores; interception bonus possession; current clock and restart rules). Proposed rule changes require an explicit design decision, not an accidental balance fix.

### Work status key

- **OPEN:** observed code gap or actionable missing work; not implemented.
- **IN PROGRESS:** implementation exists on a branch/PR but is not verified and merged.
- **IN REVIEW:** code or evidence passed the stated tests; PR not yet merged and other dependencies may remain.
- **PARTIAL (PR #323):** current PR implements part; finish integration/tests after PR #323 is merged.
- **INVESTIGATE:** plausible problem or conflict requiring confirmation before editing.
- **BLOCKED:** depends on an earlier work item or PR.
- **DONE:** merged, tests recorded, this document updated with the closing PR.

## Findings snapshot

| ID | Priority | Status on 2026-11-23 | Work item / dependency |
|---|---|---|---|
| DEF-01 | P0 | IN PROGRESS ([PR #325](https://github.com/quarterback/viperball/pull/325), draft) | Canonical defensive read now called on live plays; tests and full benchmark pending |
| DEF-02 | P0 | IN PROGRESS ([PR #325](https://github.com/quarterback/viperball/pull/325), draft) | Matchup, coverage and explosive effects wired; final benchmark pending |
| DEF-03 | P0 | IN PROGRESS ([PR #325](https://github.com/quarterback/viperball/pull/325), draft) | Formation-read formula corrected; tests pending |
| DEF-04 | P1 | PARTIAL (PR #323) | Eleven-player defense, position assignments, and accurate snap accounting |
| DEF-05 | P1 | INVESTIGATE | Resolve legacy five-style defensive call vs eight current schemes |
| DEF-06 | P1 | IN REVIEW ([PR #326](https://github.com/quarterback/viperball/pull/326)) | 2,048 full-matrix and 1,024 weather games; 94 tests passed; [final analysis](aar_2026-11-23_def06_full_defense_matrix.md) |
| DEF-07 | P1 | OPEN | Measure defensive rush/pressure events, not just sacks, especially Blitz Pack |
| WEA-01 | P2 | INVESTIGATE | Isolate rain-related turnovers, fatigue and explosive gains; no scoring increase established |
| DEL-01 | P1 | OPEN | Counterfactual Delta Yards analysis, including comeback impact |
| DEL-02 | P1 | OPEN | Consolidate conflicting delta, kill, and points-per-drive definitions |
| DEL-03 | P2 | BLOCKED on DEL-02 and UI-01 | Make Delta Yards legible in game and season reporting |
| ROST-01 | P1 | PARTIAL (PR #323) | Carry talent ladder and work rate into recruits, development, HS and careers |
| ROST-02 | P1 | INVESTIGATE | Verify scheme assignment uses the same roster actually fielded |
| FAT-01 | P1 | PARTIAL (PR #323) | Coach-dependent shifts, depth effects, and persistence |
| UI-01 | P1 | OPEN | Complete React game report and team tactical statistics |
| SIM-01 | P1 | OPEN | Audit fast-sim dependencies beyond college mode |
| VAL-01 | P0 | PARTIAL (PR #323) | Regression/benchmark suite and live verification |
| VAL-02 | P1 | OPEN | Make production fresh-roster generation deterministic across checkouts and runs |
| RULE-01 | P2 | OPEN | Rulebook/version/terminology reconciliation |
| OPS-01 | P2 | OPEN | Repair obsolete tests and close deploy/test gaps |

P0 means correctness/integrity; P1 means core game consequence; P2 means presentation/maintenance. The order is a proposal, not a commitment to ship all tasks in one PR.

## Detailed work items and acceptance criteria

### DEF-01 — Defensive play recognition defined but not invoked (P0, OPEN)

**Evidence:** engine/game_engine.py defines get_defensive_read(play_family) with scheme read_success_rate, gameplan_bias, situational boosts, personnel and coaching. Searching that module at PR #323 head found its **definition but no call site**. The function's advertised read behavior therefore does not run through that pathway. Trick-play code has a separate read roll; do not confuse these.

**Work:** Trace every play-resolution family (run, laterals, kick-pass, trick). Decide whether to wire this function into one canonical defense-read stage or explicitly remove/replace it. Make reads alter a bounded play outcome and emit an observable reason. Do not blindly add a second read roll if another path already represents the same effect.

**Accept when:** targeted tests demonstrate read frequency and play outcomes respond to scheme, personnel, coaching, and situation; an ablation disabling reads produces the predicted direction; no double suppression, invalid gains, or unbounded stacking; play/game summaries expose enough evidence to debug it.

### DEF-02 — Scheme modifiers and matchup table have incomplete runtime pathways (P0, OPEN)

**Evidence:** engine/game_engine.py defines OFFENSE_VS_DEFENSE_MATCHUP, eight DEFENSE_STYLES entries with play_family_modifiers, explosive_suppression, kick_pass_coverage, and a FORMATION_VS_DEFENSE table. At the reviewed head, there is no runtime lookup of OFFENSE_VS_DEFENSE_MATCHUP, nor a lookup of several listed scheme fields. Other defense mechanics **are** active: per-surface tackler/coverage selection, rush/blitz, fumble-recovery pressure, lateral pursuit, formation modifier, special-teams pressure. Do not characterize the entire defense as inactive.

**Work:** Produce a field-by-field audit table: declared -> read at call site -> event type -> effective magnitude -> observable metric. Connect missing scheme mechanics only where there is no equivalent existing effect. Reconcile signs (whether a multiplier favors offense or defense) and bounds across all eight defenses and current offensive styles. Consider removing dead fields rather than preserving misleading configuration.

**Accept when:** every retained DEFENSE_STYLES and matchup field has tested runtime behavior or is clearly marked descriptive/retired; scheme tradeoffs appear in controlled benchmark outcomes; no all-purpose best scheme or compounding modifier exploit introduced without evidence.

### DEF-03 — Formation recognition can reverse an advantage (P0, OPEN)

**Evidence:** _formation_defense_multiplier() calculates base_mult from FORMATION_VS_DEFENSE. If the DC recognizes a formation it returns **1 + (1 - base_mult) * 0.5**. For an offense-favoring 1.08 this becomes 0.96; for a defense-favoring 0.92 it becomes 1.04. It crosses neutral rather than reducing the advantage's size.

**Work:** Specify intended behavior and test. For 'halfway to neutral' use a result between base_mult and 1.0, not across 1.0. Preserve the direction of any genuinely intended benefit only with a documented design decision.

**Accept when:** tests cover values below, at, and above 1.0; recognized formations partially neutralize, but do not flip, the unrecognized advantage; per-scheme matchups still show a meaningful spread.

### DEF-04 — Defense must use real eleven-player units (P1, PARTIAL in PR #323)

**Original finding:** before the last Nov 23 commit, defense had two Keeper and three DL starters; _get_defenders_by_group selected DL/Keepers, while older snap counters credited every available player with every snap. This could not model a weak coverage player, a substituted defender's matchup, or a true eleven-player fatigue burden.

**New work already on PR #323:** shift rotation now defines five DL, two Keepers, and four two-way defensive backs drawn from Vipers/flankers, with dead-ball position-group rotations, game_field_snaps and game_shifts. The former finding **must not** be marked wholly unresolved. See [work-rate AAR](https://github.com/quarterback/viperball/blob/claude/fix-league-hub-null-status/docs/aar_2026-11-23_work_rate_and_shift_rotation.md).

**Remaining work:** Confirm every snap uses exactly eleven eligible defenders (also on special plays), real lineup participation determines contest/tackle/coverage/blitz eligibility, defensive backs can be individually targeted, and substitution changes matchup and fatigue. Reconcile game_offensive_snaps / game_defensive_snaps / game_coverage_snaps with game_field_snaps; decide which represent participation versus on-field presence.

**Accept when:** lineup integrity tests pass under injury, benching, travel fatigue, and substitutions; a weak/depleted defender changes targeted coverage results; snap totals reconcile by team/unit and no bench player receives phantom field snaps. Do not revert PR #323's shift rotation.

### DEF-05 — Retire or integrate the old defensive play-call generator (P1, INVESTIGATE)

**Evidence:** engine/ai_coach.py contains choose_defensive_call() and _DEFENSE_STYLE_TENDENCIES for the **old five** defensive names (pressure_defense, run_stop_defense, coverage_defense, contain_defense, base_defense). The full engine uses **eight** newer schemes with a migration map. No call to choose_defensive_call() appeared in the inspected engine code. It may be compatibility/unused legacy rather than a missing must-call feature.

**Work:** Find all callers across modes and tests. Choose a canonical defensive decision interface; migrate any still-needed behaviors (including Counterpunch under Delta Yards) to current schemes, or explicitly deprecate the old function and correct its documentation.

**Accept when:** no stale scheme names silently fall back to a generic defense; current eight schemes cover needed situations; tests exercise play-call effects or confirm safe removal.

### DEF-06 — Quantify defensive identity and tradeoffs (P1, BLOCKED)

**Work:** Cross the current offensive styles with the eight defenses and formations on matched rosters using repeated fixed seeds. Run both strong and weak defensive personnel; isolate reads, pressure, coverage, run suppression, fatigue, weather, late-down stops, and turnover recovery.

**Required output:** for each pairing, attempts and yards/play by play family, kick-pass completion, sacks/pressure, explosive gains allowed, lateral outcomes, forced turnovers/bells, punts/pindowns, defensive stops, points per opponent drive, and sample sizes/confidence intervals.

**Accept when:** the scheme's claimed strengths and concessions show up in the relevant *conditional* data (for example, Lockdown should limit a suitable kick-pass attack while paying a run-defense cost). Avoid choosing victory rate alone as the success measure.

### DEF-07 — Record actual defensive pressure and its tradeoffs (P1, OPEN)

**Evidence:** The full [DEF-06 assessment](aar_2026-11-23_def06_full_defense_matrix.md)
measured no reliably greater sack count for Blitz Pack compared with Swarm
under matched personnel (matched difference −0.10 sacks/game, bootstrap 95%
interval −0.34 to +0.15). Yet Blitz Pack yielded about one additional
30+ yard play/game and roughly 0.49 more rushing yards/play. The current
play-by-play does not consistently expose rushers sent, hurry, pressure or
protection failure. A sack-count-only approach is inadequate to confirm this
scheme's claimed identity.

**Work:** At the defensive contest point, record rushers committed, blitz
decision, pressure/hurry, actual sack, pass/kick completion effect, and
offense's resulting yards. Capture defensive personnel and formation
context without inventing 'pressure' from a sack result after the fact.
Use matching offense/defense rosters and benchmark the Blitz Pack risk/reward
profile against Swarm and Lockdown.

**Accept when:** blitz frequency and pressure can be distinguished from sacks,
the same play/drive can be traced to the defensive scheme, and scheme
strengths/concessions appear in conditional stats with sample sizes and
intervals. Do not force a target sack count.

### WEA-01 — Investigate weather interactions (P2, INVESTIGATE)

**Evidence:** The corrected [DEF-06 study](aar_2026-11-23_def06_full_defense_matrix.md)
found that rain increased turnovers (+0.37/game), fatigue (−3.74 defensive
energy points at game's end) and 30+ yard gains (+0.29/game), but did not
reliably change points per attacking drive (+0.02; uncertainty crosses zero).
The earlier unpinned-roster pilot produced a scoring increase that did
not reproduce after the seed/order fix.

**Work:** Isolate wet-ball fumble risk, stamina/work rate, kick accuracy,
formation selection, breakaway chance and plays/possessions using paired
full-engine experiments; include multiple offensive roster profiles and
seeds. Document which rule or modifier is responsible for any effect.

**Accept when:** observed weather differences can be attributed to a
specific active rule pathway and replicated across independently generated
rosters, without an imposed target scoring level.

### DEL-01 — Test the effect of Delta Yards instead of guessing its strength (P1, OPEN)

**Existing rule, confirmed in engine/game_engine.py kickoff():** after a score, the next receiver starts at yard line **clamp(20 - its score lead, 1, 80)**. A side up 15 starts at its own 5; a side down 15 at its own 35. The engine records delta_cost = baseline - start_position per affected drive, net delta_yards, delta_drives and delta_scores. This *already changes actual field position*; it is not only a statistic.

**Work:** Add a benchmark-only on/off control for this restart calculation, without altering the default sport rule. Replay balanced/imbalanced matchups across seeds and score states. Measure comeback probability by deficit/time, drive start positions, possessions, touchdown/kick/turnover rates, field position, and scoring by offense/defense scheme. Preserve other rules, especially punt-generated field position and bonus possessions; these are different mechanisms.

**Accept when:** a documented matched-run study reports the mechanism's effect with spread/uncertainty, including clamping at 1 and 80, ties, half boundaries and multiple scoring events. No hard-coded comeback or home-win target; change the rule's strength only after a separate design decision.

### DEL-02 — One vocabulary and data definition for Delta Yards (P1, OPEN)

**Evidence:** game_engine.py delta_yards is **restart-position cost/benefit**; viperball_metrics.py calculate_delta_profile().delta_yds instead measures **actual team yardage minus opponent yardage**, while its team_kill_pct measures failed possessions. The engine's kill_rate means **scoring on delta-penalized drives**; DYE has power_play, penalty_kill, neutral, pk_efficiency, pp_efficiency, mess_rate. Fast-sim delta fields are currently approximations, not results of live restart mechanics. In viperball_metrics.py calculate_ppd() uses **4.2 estimated points per successful kick**, rather than distinguishing 5-point snap kicks and 3-point place kicks.

**Work:** Define separate, explicit names and units for (a) restart delta yard cost, (b) net conventional yards, (c) scoring/yardage on penalty-kill, power-play and neutral drives, (d) defensive stop/drive failure, and (e) actual vs estimated points per drive. Standardize keys or supply a compatibility layer; specify negative/positive sign conventions. Audit collection -> season accumulators -> stats-site templates -> API -> React.

**Accept when:** sample drive logs exactly reconcile to game/team/season totals; renamed fields cannot silently conflate different meanings; scoring/kicking aggregations derive from real kick types; tests cover zero denominators, tied states, negative delta, and legacy saves.

### DEL-03 — Show Delta Yards as a strategic story in the app (P2, BLOCKED)

**Work:** In React GameBoxScore add each scoring restart's before/after starting field position, delta cost, field-position context, team PP / penalty-kill / neutral scoring and adjusted yards. In team/season views include accumulated delta cost, power-play conversion, kill rate, mess rate (with sample sizes), and how the offense performed when pinned deep. Pair statistics with the associated play/drive, not a disconnected number.

**Accept when:** a player can answer 'How much field did the leader have to overcome?', 'Did the underdog exploit its bonus starts?', and 'Which stop or kick mattered?' from one game page without inspecting JSON. Do not interpret a better scoring rate as *caused by* delta without DEL-01.

### ROST-01 — Extend talent ladder and work rate across careers (P1, PARTIAL in PR #323)

**Evidence:** PR #323's scripts/generate_rosters.py applies a per-player talent ladder instead of rolling each athlete around a single team mean; team talent becomes spiky with real strengths/weaknesses. Its latest work adds a work_rate rating and a backward-compatible derived value for older players. AARs explicitly state that recruiting, development and the high-school league still create talent the old way; new recruits do not yet roll work_rate, and work_rate does not develop.

**Work:** Carry documented talent distributions through new recruiting classes, development, transfers, HS and professional pathways. Use role-appropriate distributions, not identical rolls everywhere. Preserve diversity of rosters over seasons, with meaningful improvement, decline, attrition and transfer role changes. Include work_rate/stamina growth and persistence.

**Accept when:** multi-season simulations show within-team strengths and weaknesses remain present without implausible regression to a homogeneous mean, and skill/role progression follows the adopted model. Validate historical saves and team generation compatibility.

### ROST-02 — Audit AI scheme assignment against generated game rosters (P1, INVESTIGATE)

**Evidence:** ai_coach.py auto_assign_all_teams() reads team_stats and identity from team JSON files and applies thresholds such as kicking >= 77 and speed >= 86. PR #323's season benchmarks use freshly generated rosters on a revised rating scale, and previous AARs document old/new roster scale mismatches. It is **not yet demonstrated** whether those team_stats represent the same team the engine fields.

**Additional direct code finding (DEF-06 review):** In `engine/game_engine.py`, `assign_game_roles(self.home_team, home_style)` and the away equivalent execute **before** `style_overrides` are applied. When a Season game passes a selected offense through overrides, roster touch/receiver role assignment may still reflect the team object's prior default offense. This could mask style differences even when the matchups and play-family weights are active. The DEF-06 study mimics this current behavior; it must not claim that roster role selection is correctly adapted.

**Work:** Compare configured offensive, defensive and special-teams schemes against actual fresh roster strengths. Confirm migration/default paths, seeded reproducibility and whether scheme candidates should use derived roster indicators on the same rating scale. Move or repeat role assignment after final styles are resolved, then test differences in selected lead carriers and receivers under the same roster across schemes.

**Accept when:** a generated roster with elite kicking can qualify for an appropriate kicking scheme, a weak kicking unit is not assigned that scheme by stale data, and assignments repeat under the same seed and inputs.

### FAT-01 — Complete coach-sensitive shifts and workload outcomes (P1, PARTIAL in PR #323)

**New behavior:** PR #323 implements dead-ball position-group shifts, work_rate affecting fatigue cost and coaching rest thresholds, two-way defensive backs, and work rate/stamina visible on roster/My Team. The box score **energy bar was removed** in the newer Nov 23 commit by user request; do **not** restore it as a default requirement. AAR reports starter median energy 82 and only limited starter-rest events for some groups.

**Remaining work:** connect rotation decisions to coaching personality, depth and matchup; verify benching/rest changes playing time, game outcomes and between-game fatigue. Ensure injuries and two-way duty do not double-charge or fail to charge energy. Show carried fatigue in the management context if useful, not as a forced box-score feature.

**Accept when:** coaches with different rotation profiles make different choices under the same game conditions; good bench depth matters; unit snap/energy totals reconcile; season persistence and save/load pass tests.

### UI-01 — Restore the actual game's information in React (P1, OPEN)

**Evidence:** web/src/pages/league/GameBoxScore.tsx at the reviewed PR #323 head shows a final score, four basic team-stat rows (total yards, touchdowns, turnovers, fumbles lost), and a basic player table. It does not expose full play-by-play, drive summaries, defensive scheme impact, scores by channel, Delta Yards, bonus possessions, bells, or halftime adjustments, despite much of that existing in engine result payloads and stats_site templates. The other agent's Nov 22 session AAR records further UI debt: stock Mantine appearance, unused team colors, thin Compare Runs, weak command-palette search and mobile navigation. Those were findings, **not implemented UI features**.

**Work:** Start with a complete single-game report: score by channel/period, drive timeline, kick attempts/makes by kind, turnovers/bells, pindowns, bonus possessions, play-by-play, defensive stops/adjustments and Delta Yards. Then add comparable scheme identity and defensive splits to team/season pages. Preserve box-score readability; prioritize data fidelity over decoration. Track general visual polish as separate UI work rather than mixing it into engine changes.

**Accept when:** React game view and established stats-site view reconcile against the same full_result JSON; no stats invented on the client; navigation works at mobile widths; UI shows clearly when a stat is genuinely unavailable in older saves.

### SIM-01 — Stop parallel engines from producing contradictory sports (P1, OPEN)

**Evidence:** PR #323 removes engine/fast_sim.py from college regular season, postseason, dynasty, My Team and DraftyQueenz game paths, but explicitly retains it for pro, WVL and the high-school recruiting league. Earlier tests found fast/full radically different scoring mixes and schemes: a 200-matchup sample had 0.4 vs 3.9 TDs and 5.0 vs 0.2 made snap kicks per team, and the fast sim reads stale scheme names/defaults. Fast sim generates synthetic delta_yards, kill_rate and other outputs without executing the real mechanisms. Dynasty history generation's ratings-only fast_sim_season is **distinct** and should not be removed automatically.

**Work:** Map every mode's execution path and which rulebook/scoring/stat generation it actually uses. Determine where full engine fidelity is required and where approximate historical simulation is acceptable; make differences explicit. Avoid silent conversion of fake metrics into authoritative box scores.

**Accept when:** each mode declares its engine/rules version; statistically comparable modes obey the same core rules or document differences; API/test coverage prevents a future regression to fast sim in college; migration/performance implications recorded.

### VAL-01 — Seeded integration checks, quantitative guardrails and deployment (P0, PARTIAL in PR #323)

**Existing:** PR #323 introduces scripts/benchmark_engine.py with full-engine fixed-seed games and season mode, reports 72 passing tests, fixes seventh-down turnover carryover, range gates, quarter/half resets, and tracks actual season play. Latest Nov 23 AAR (work rate + shifts) reports a 1,230-game season at 62.0 points per team, 47.7% home wins, 35.3% lower-prestige wins and median margin 23; a separate benchmark reports 59.1 points, 3.7 TD, 3.2 snap kicks and 1.9 field goals per team. These are **reported results from that agent**, not fresh measurements in this assessment.

**Work:** Add invariant tests for downs, restarts, scoring, punts/pindowns, bonus possessions, fatigue/snaps/lineups, formation-defense interactions, scheme/roster selection and save/export parity. Include a controlled matchup matrix in the benchmark. Run actual fresh=True rosters and real season-assigned schemes; earlier AARs were misled twice by saved/old-scale team files. Add basic variance/ranges and comparisons over multiple seeds. After PR #323 merges, verify real app flows and deployed site; previous AAR explicitly says live site not tested.

**Accept when:** repeatable benchmarks fail on meaningful rule/engine regressions without freezing natural margin distributions; test commands, sample sizes, seeds and results are recorded; live college season, dynasty, stats site and saves are actually exercised.

### VAL-02 — Deterministic fresh-roster generation (P1, OPEN)

**New direct code evidence from DEF-06:** `engine/season.py::load_teams_from_directory` and
`load_teams_with_states` loop over `Path.glob("*.json")` without sorting.
Fresh roster generation calls randomized archetype and player rolls in that order.
Two GitHub Actions jobs using the same `random.seed(20261123)` and
`PYTHONHASHSEED=0` selected different median/strong/weak rosters. Results
were paired *inside each job*, but the cross-job starting populations differed.
This is a production reproducibility issue, not simply a reporting bug.

**Temporary solution in [DEF-06 PR #326](https://github.com/quarterback/viperball/pull/326):**
The benchmark recreates the same fresh-roster steps with sorted file enumeration,
records a roster fingerprint, and tests repeat selection under one seed. It does
**not** modify the production season loader.

**Work:** Sort input files in both production roster-loading functions; audit
all other uses of process-salted `hash()` for seeds (including
`ai_coach.py::auto_assign_all_teams` and season referee seeding). Preserve
real session/dynasty save compatibility. Adopt one deterministic, explicitly
versioned seed derivation for simulation experiments.

**Accept when:** two independent clean-checkout processes produce identical
fresh player IDs/ratings and scheme assignments for a given seed, and repeated
full-engine matchups produce identical summary stats under the same settings.
Record a fingerprint and verify it in CI.

### RULE-01 — Canonical rules and docs, with mechanical tests (P2, OPEN)

**Evidence:** PR #323 updated README based on RULES_EVOLUTION_AAR.md and March AARs: 205-team CVL, four 10-minute quarters, four timeouts per half, current restart/pindown and bonus rules, postseason-only overtime. Main README and legacy RULES.md / docs/RULES.md still use old descriptions; there are older docs claiming different lateral and snap-kick frequencies and conflicting definitions.

**Work:** Establish one canonical current rules reference with revision note; mark historical guides as historical rather than silently rewriting evidence. Align narrative/press guides and UI terminology where they conflict with live mechanics (including Delta Yards and pindown). Preserve deliberately different editorial voices without reintroducing incorrect rules.

**Accept when:** no current player-facing page contradicts tested engine behavior on points, downs, timeouts, restarts, kicks, bonus possessions, or overtime; canonical docs are linked and dated.

### OPS-01 — Housekeeping and release proof (P2, OPEN)

**Evidence:** PR #323's session AAR notes a broken root test_season.py that refers to removed data/teams/xavier.json, an even-program-count restriction despite scheduler support for odd counts, and lack of live-site testing. It also notes the React UI design work was unbuilt. These are separate issues, not grounds to mix UI design into a mechanics PR.

**Work:** Repair/retire obsolete root test, verify 205-team dynasty scheduling, smoke-test save/load and exports, and document release/deploy verification after #323 is merged. Keep compatibility of old saves explicit.

**Accept when:** the supported test entry points pass on clean checkout, 205-team season/dynasty paths work, and a release checklist documents live verification.

## Implementation sequence and boundaries

**Stage 0 — Land and verify baseline:** Review/merge PR #323 separately; reconcile this queue with its final head. Run its suite and full-engine benchmark on the merged code. Do not recreate the already-implemented shifts or resurrect the deleted box-score energy bar.

**Stage 1 — Defensive correctness:** DEF-03 (small isolated bug), DEF-01, DEF-02; implement tests as you wire mechanics. Then DEF-04 + DEF-05 integration, followed by DEF-06 benchmarking. Check that old and new defensive suppression systems are not applied twice.

**Stage 2 — Delta mechanics and measurement:** DEL-02 definitions and invariant tests; DEL-01 paired counterfactual experiments; DEL-03 display only after the data contract is stable. This ordering separates measurements from assumptions about comeback strength.

**Stage 3 — Player and coaching continuity:** ROST-02 generated-roster/scheme parity, ROST-01 recruitment-development pipeline, FAT-01 coach-level rotation choices. Validate multi-season consequences.

**Stage 4 — Player-visible sport:** UI-01 game report and team/season tactical views; SIM-01 mode parity; RULE-01 + OPS-01 cleanup. VAL-01 runs across every stage.

**Explicit non-goals:** Adding ninth/tenth defensive schemes before eight existing schemes work; setting target blowout/home-win rates and forcing results to match; turning laterals into the default offensive game; replacing real game logs with synthetic stats; imposing box-score fatigue UI contrary to the newer user direction.

## Work item update template

Use the following when an agent takes or closes a task. Preserve the ID so that future agents can search the repository/PRs.

~~~markdown
### <ID> — <short name>
Status: OPEN | IN PROGRESS | BLOCKED | DONE
Branch / PR: <link>
Depends on: <IDs>
Code evidence: <path + symbol + head SHA>
Change made: <precise mechanism>
Tests: <command / new test names / pass-fail>
Benchmarks: <seeds, sample sizes, before/after, distribution>
UI/data contract: <what changed, if anything>
Remaining risk: <specific issue>
Decision required: <only if a rules/behavior decision is unavoidable>
~~~

For new discoveries, assign the next stable ID in the relevant group, state whether the finding is direct code evidence or hypothesis, and give one acceptance test. For every completed item, link the merged PR and leave a short note rather than deleting its history.

## Core source links

- [PR #323: current college-engine fixes and game-day work](https://github.com/quarterback/viperball/pull/323)
- [Reviewed engine at 3aedd95](https://github.com/quarterback/viperball/blob/3aedd95d59f5c44291d473e4fd30c7b50e69151b/engine/game_engine.py)
- [Reviewed AI defensive calls](https://github.com/quarterback/viperball/blob/3aedd95d59f5c44291d473e4fd30c7b50e69151b/engine/ai_coach.py)
- [Reviewed delta/defensive analytics](https://github.com/quarterback/viperball/blob/3aedd95d59f5c44291d473e4fd30c7b50e69151b/engine/viperball_metrics.py)
- [Reviewed React game box score](https://github.com/quarterback/viperball/blob/3aedd95d59f5c44291d473e4fd30c7b50e69151b/web/src/pages/league/GameBoxScore.tsx)
- [Nov 22 full session / known gaps](https://github.com/quarterback/viperball/blob/claude/fix-league-hub-null-status/docs/aar_2026-11-22_session_full_run.md)
- [Nov 22 fast/full engine difference and rule audit](https://github.com/quarterback/viperball/blob/claude/fix-league-hub-null-status/docs/aar_2026-11-22_turnover_on_downs_and_engine_audit.md)
- [Nov 22 rating rescale and roster generation](https://github.com/quarterback/viperball/blob/claude/fix-league-hub-null-status/docs/aar_2026-11-22_rosters_pace_field_goals.md)
- [Nov 23 team form / travel and fatigue](https://github.com/quarterback/viperball/blob/claude/fix-league-hub-null-status/docs/aar_2026-11-23_game_day_form_fatigue_home_field.md)
- [Nov 23 shift rotation and work rate (newest)](https://github.com/quarterback/viperball/blob/claude/fix-league-hub-null-status/docs/aar_2026-11-23_work_rate_and_shift_rotation.md)
- [Delta/Mess Rate terminology spec](https://github.com/quarterback/viperball/blob/main/docs/mess_rate_implementation.md)

_This assessment was compiled from direct repository inspection and the existing agent's AARs. It is a task specification, not evidence that the proposed fixes have already been built or tested._
