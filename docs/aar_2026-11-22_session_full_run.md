# AAR: Full run, November 22, 2026 — rebooting Viperball

One record of everything done in this session, in order. Detail for each part is in the
linked AARs. All work is on branch `claude/fix-league-hub-null-status`, PR #323.

## How the session went

1. **Design review.** Ron asked what design work the React app (`web/`) needs after five
   months away. Findings were given in chat only (no code): the sport's own data (play by
   play, composure, Delta Yards, bells) is missing from the new app, team colors are unused,
   the look is stock Mantine, Compare Runs is thin, the command palette has no search, and
   mobile navigation is broken. None of this is built yet.
2. **Two app crashes.** League Hub (`null.phase`) and Dynasty Record Book (React error #31).
   → `aar_2026-11-22_league_hub_and_record_book_crashes.md`
3. **API name errors.** Pro league creation and autosave; dynasty creation's recruiting
   pipeline. Same AAR.
4. **Turnover on downs carryover.** New offense started on 7th down.
   → `aar_2026-11-22_turnover_on_downs_and_engine_audit.md`
5. **Fast sim removed from college seasons**, plus early down field goals and punts, quarter
   break punts, bonus possession resets, blocked kick recoveries, a stats site portal bug.
   → `aar_2026-11-22_fast_sim_removal_and_kick_logic.md`
6. **README updated to the current rules** and `scripts/benchmark_engine.py` added.
   → `aar_2026-11-22_readme_rules_and_benchmark.md`
7. **Snap kick decision logic** changed to Ron's design: legal on any down, 5th down the main
   kicking down, earlier late in a half.
   → `aar_2026-11-22_snap_kick_any_down_logic.md`
8. **Kick range root cause** (formulas never rescaled after the March talent drop), goal line
   bonus touchdowns removed, field compression added.
   → `aar_2026-11-22_kick_range_and_field_compression.md`

9. **Rating rescale.** Inventory of old scale formulas, then the core contest, speed,
   breakaways, turnovers, yards after catch and prestige moved to the current rating scale.
   → `rating_scale_inventory_2026-11-22.md`, `aar_2026-11-22_rating_rescale.md`

10. **Blowouts, snap kicks, prestige.** Rating gap dial, earlier kicks in range, prestige
    kept in season games, real season mode in the benchmark.
    → `aar_2026-11-22_blowouts_snap_kicks_prestige.md`

11. **Rosters, pace, field goals.** Players rolled against a league talent ladder (the
    baseball game's design), a faster clock between plays, field goals out to 71 yards.
    → `aar_2026-11-22_rosters_pace_field_goals.md`

12. **Game day** (November 23). Flat home bonus removed, travel fatigue, per-game and per-half
    team form, work rate fatigue carried between games, fatigue bar in the box score.
    → `aar_2026-11-23_game_day_form_fatigue_home_field.md`

13. **Work rate and shift rotation** (November 23). Work rate rating on roster and My Team,
    stamina versus work rate split, position group rotation at every dead ball, two-way
    defensive backs. → `aar_2026-11-23_work_rate_and_shift_rotation.md`

14. **Lacrosse style line changes** (November 23). Three two way midfield lines, defensive
    specialist, live turnover changes that can get caught, players picked only from the
    eleven on the field, cover across groups. → `aar_2026-11-23_lacrosse_line_changes.md`

15. **Lines in the app** (November 23). Line column with specialist badge on the team roster
    and My Team, line changes and caught changing in the box score, fast break tag in the
    play by play. → `aar_2026-11-23_lines_in_app.md`

16. **Coach playbooks prototype** (November 23). Branch `claude/coach-playbooks`, PR #329, now a
    draft reference: home books plus borrowed packages wired into the engine, measured.
    → `aar_2026-11-23_coach_playbooks.md` on that branch.
17. **Playbook catalog** (November 23). A coach and playbook plan from another agent landed on
    docs PR #324 during step 16 and split the work into COACH (runtime) and PLAYBOOK
    (catalog). Ron chose the split. PR #330 from main: PBK-01, PBK-02, PBK-04, new files
    only. → `aar_2026-11-23_playbook_catalog_pbk.md` on that branch.

18. **Merged the stack and made runs repeatable** (November 23). #323, #325, #326, #324, #330,
    #327 merged in order; #328 reconciled with the merged engine and merged; unseeded
    chemistry, 22 salted hash seeds and unsorted loads fixed so seeded runs repeat in every
    process (VAL-02). → `aar_2026-11-23_merge_stack_and_val02.md`

19. **Team installation** (November 23). CCH-04 built while another agent built CCH-03, PR #333:
    per program familiarity with each coordinator's system, coaching tree and promotion
    carryover, fading habits from departed coordinators, and up to two catalog packages per
    coordinator, shown on the team page. Found and fixed three problems: the app's dynasty
    never ran the coaching carousel, long yardage used a football distance (now 5 or more
    yards per remaining down), and the referee pool shifted the first game's random rolls.
    Odd program counts now retire Coast Guard, or Merchant Marine when Coast Guard is the
    human team. Trial merge with CCH-03 (#332) passes 168 tests.
    → `aar_2026-11-23_cch04_team_installation.md` on that branch.

20. **Status check and next steps** (November 24). Rebased onto main after #334 to #360
    landed from other agents. Fixed the stale work queue, the four broken root test scripts
    and the transfer portal prestige map, which was never moved to the new rating scale and
    put every program between 22 and 47. Measured touchdowns per team across ten merge
    points: 3.32 after #323, about 2.6 now. → `aar_2026-11-24_status_and_next.md`

21. **Rules, drift, sacks, ladder, fast sim** (November 24). RULES.md v2.0 checked against the
    engine; defensive scheme tables centered (touchdowns back to about 3); rain penalty
    doubling fixed; sacks 7% of kick passes; recruits, HS and portal players on the talent
    ladder with development fixed; pro leagues, WVL and HS title games on the full engine.
    → `aar_2026-11-24_rules_drift_sacks_ladder_fastsim.md`

22. **Calls, no calls and missed calls; one rating scale** (November 24). Fouls can now be
    called, let go or missed by class, crew and situation: accepted flags per team 14.4 to
    8.4, about 3 missed calls a game. Every team file and pro system moved to the current
    rating scale; the per game conversion is gone. → `aar_2026-11-24_officiating_and_rating_scale.md`

23. **Fast sim removed, scoring floats, officiating levels** (November 24). The fast sim and
    its options are gone (back history now plays real engine games); scoring targets
    removed from the benchmark and README; college crews less accurate and more spread out
    than pro crews. → `aar_2026-11-24_fast_sim_removed_scoring_floats_ref_levels.md`

24. **High School section** (November 24). The HS league now has its own menu entry with
    champions, the national bracket, state standings, team schedules and rosters.
    → `aar_2026-11-24_high_school_section.md`

25. **Merged the open PRs** (November 24). #367, #363, #364, #365, #366, #368, #369, #370 and
    #361 merged into main; #362 closed because #367 already carried it.
    → `aar_2026-11-24_merge_open_prs.md`

26. **Weather model task** (November 24). Audited the weather code and wrote WEA-02, a fuller
    weather model, into the queue; logged SCALE-01 for raw rating checks still on the old
    scale. → `WEA-02_weather_model.md`

27. **Old scale cutoffs** (November 25). Fourteen fixed cutoffs in the engine still compared
    current ratings to old scale numbers; all now read the old scale equivalent. Nearly every
    player had been getting the default archetype. → `aar_2026-11-25_scale01_old_scale_cutoffs.md`

28. **Weather model** (November 25). Weather by quarter with a field that soaks and freezes,
    wind by end, venues with roofs, turf and altitude, and real places and calendars for every
    league. Fixed the FIV, heavy wind and fumble rule bugs and two more old scale leftovers.
    → `aar_2026-11-25_wea02_weather_model.md`

29. **Merged the open PRs, second round** (November 25). #371 through #377 marked ready and
    merged with no conflicts. → `aar_2026-11-25_merge_open_prs_round2.md`

30. **Merged #378** (November 25). Coach learning, workload and defensive XI; no conflicts.
    → `aar_2026-11-25_merge_pr378.md`

31. **Full suite after the merges** (November 25). Everything passes. Fixed a High School page
    crash from HS-01: the high school overall added ratings in a different order and rounded
    one point off for 3 of 4,800 players. → `aar_2026-11-25_full_suite_after_merges.md`

## Numbers, start to end (benchmark, per team per game)

| | Start | End | Target |
|---|---|---|---|
| Points | 40.5 | 60.6 | 45 to 70 (README) |
| Touchdowns | 4.2 | 3.7 | about 3 |
| Snap kicks made | 0.3 | 3.2 | about 4 |
| Field goals made | 0.06 | 2.0 | about 2 |
| Games decided by 30+ | 54% | 21% | |
| Plays on 7th down or later | 131 per 60 games | 0 | 0 |

## What went wrong in the process

- **Asked Ron questions the repo already answered.** The AARs record the rules; they should
  have been read before any question about which rulebook is current.
- **Treated the README as current** when it predated the February and March changes.
- **Measured with the wrong rosters twice.** First with team file defaults (`base_defense`,
  which is no real scheme), then with saved team files whose ratings are on the old scale.
  Real seasons generate fresh rosters. This hid the kick range problem for most of the day
  and produced a wrong claim (drives scoring 50% from anywhere) that had to be corrected.
- **Reported a 47 second season sim time** that was a fast sim run; the full engine takes
  about 2 minutes.
- **Replies were not in plain language** until Ron said so.
- **Stopped after each round and handed back a list of leftovers** instead of working until
  the targets were met. Ron called it out; the last run was done in one pass.
- **The rescale plan named the wrong first target.** It said prestige drives most plays; the
  prestige team rating has been off since March. Caught while writing the inventory.

## Lessons

- Benchmark on what a real season runs: `fresh=True` rosters and season assigned schemes.
  `scripts/benchmark_engine.py` now does this.
- When a rebalance moves a rating scale, every formula with a hard coded rating in it
  (`skill - 60`) needs the same move. Search for them at the time.
- A rule written into an AAR by an agent is a record of what that agent did. Ron's stated
  design decides the rules.

## Not verified

Nothing was run against the live site; the sandbox cannot reach viperball.xyz. Checks were
the `tests/` suite, the benchmark, and replaying API calls locally with FastAPI's test client.

## Open work

Updated November 24 after step 23.

1. A live Fly deploy and a click through of the stats site are still unverified.
2. Done: recruiting, development, HS and portal players use the talent ladder.
3. Done: the fast sim is deleted and back history plays engine games. The HS regular
   season still uses a quick model.
4. Done: odd program counts retire Coast Guard or Merchant Marine.
5. Done: rulebooks rewritten and checked by tests.
6. Done: the root test scripts run again.
7. Done: scoring is no longer measured against targets.
8. Done: sack rate about 7%.
9. Done: accepted flags about 8 per team with no calls and missed calls (PEN-02).
10. Done: every league on the current rating scale (PRO-01).
