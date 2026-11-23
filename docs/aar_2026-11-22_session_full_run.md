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

1. Merge PR #323 and redeploy; click through college season, dynasty and stats site.
2. Recruiting, development and the high school league still generate players the old way
   (around one number); move them to the talent ladder.
3. Pro leagues, WVL and the high school league still use the fast sim.
4. The even program count rule still blocks a 205 team dynasty; the scheduler does not need it.
5. `RULES.md` and `docs/RULES.md` still describe the old rules; the README is current.
6. `test_season.py` loads a team file that no longer exists.
7. The design work from step 1.
