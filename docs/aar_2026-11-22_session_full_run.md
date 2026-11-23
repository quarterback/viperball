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

## Numbers, start to end (benchmark, per team per game)

| | Start | End | Target |
|---|---|---|---|
| Points | 40.5 | 39.9 | 45 to 50 |
| Touchdowns | 4.2 | 3.0 | 1.9 to 3.5 |
| Snap kicks made | 0.3 | 2.1 | 3 to 5 |
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
2. Rescale the other formulas built for 60 to 100 ratings (prestige halo first), aimed at
   blowouts between unequal teams and the last 5 points of scoring.
3. Pro leagues, WVL and the high school league still use the fast sim.
4. The even program count rule still blocks a 205 team dynasty; the scheduler does not need it.
5. `RULES.md` and `docs/RULES.md` still describe the old rules; the README is current.
6. `test_season.py` loads a team file that no longer exists.
7. The design work from step 1.
