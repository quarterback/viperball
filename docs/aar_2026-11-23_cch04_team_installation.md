# AAR: CCH-04 team installation and career progression
## November 23, 2026

## What Ron asked

Work on CCH-04 while the other agent works on CCH-03. Mid run: retire Coast Guard when the
program count is odd (Merchant Marine as the other usual choice).

## What CCH-04 is (from the coach and playbook plan)

Layer 3: what a team has learned. Installed packages and familiarity, staff turnover and
continuity, coaching tree inheritance, season to season change. Persistence across hires,
transfers and saves.

## Built

**`engine/team_installation.py` (new).** A versioned JSON record per program, offense and
defense each with: base book and familiarity with it, current coordinator and familiarity
with her system, games and seasons together, fading traces of past coordinators, and
installed catalog packages with their own familiarity.

- Starting familiarity: 0.75 for a staff already in place, 0.30 for an outside hire, plus
  0.25 for coaching tree ties (she worked under the current head coach, or shares a mentor
  with her predecessor, or worked under her predecessor), plus 0.20 for reading the book the
  same way, capped at 0.85; at least 0.70 for a promotion from the same staff.
- Growth: 0.02 a game, 0.20 a season together. Packages 0.03 a game, 0.25 a season.
- Old habits: a departing OC leaves 60% of the team's familiarity as a trace that loses 3%
  a game and 60% each offseason, dropped under 0.05.
- Book change: familiarity with the book resets to 0.35.
- Packages: each coordinator installs up to two catalog packages that fit her bias, the
  book and the roster; up to four per side; only packages with at least one situation the
  engine can evaluate today.
- Roster fit: fresh rosters and team files sit on different scales, so each roster measure
  is ranked in the league and mapped to the same rank in the team files' spread. Tag shares
  then match the team files within two points on every tag.

**Game effect (offense).** `apply_installation_to_offense` scales the OC's resolved CCH-02
biases by the execution factor (familiarity times 0.7 plus 0.3 times book familiarity) and
adds the traces. `situational_bias` adds each installed package's pull (0.12 times its
familiarity) toward its formation, play family and kick pass tags when one of its situations
is live, using the catalog's own rules. Everything still goes through CCH-02's
`apply_weight_bias`: plus or minus 20%, zero stays zero, scaled by head coach delegation.

**Defense.** Recorded the same way; `defense_execution_factor()` is there for CCH-03 to use.
No defensive game effect in this PR.

**Wiring.**
- `engine/game_engine.py`: installation blended into OC tactics at kickoff; one `_oc_bias`
  helper replaces the three static bias reads (formation, play family, kick pass); the
  coach tactics summary includes the installation and package activations;
  `team_installation_enabled` switch.
- `engine/season.py`: `team_installations` on Season; each game syncs both teams' records
  with their staff and books, then records the game.
- `engine/dynasty.py`: `_team_installations`, saved and loaded (old saves load with none);
  `attach_installations_to_season`; offseason growth at the end of `advance_season`.
- API: `installation` on both team roster endpoints. Web: an Installation section under the
  team page's Coaching tab.

## Found and fixed along the way

1. **The app's dynasty had no coaching carousel.** `Dynasty.run_offseason` holds firing,
   the coaching portal, hiring, coach development and head coach readiness, and the app
   never calls it: its offseason runs its own NIL, portal and recruiting steps. AI programs
   kept the same staff forever, and coaches never aged or developed. The coaching section is
   now `Dynasty.run_coaching_offseason`, called by `run_offseason` and by the app's advance
   step. In the test dynasty's first offseason, 67 programs made changes and the portal made
   238 hires; 31 programs had a new coordinator folded in at their first game.
2. **Long yardage was a football number.** The catalog said 12 or more to go, and early down
   10 or more. Viperball needs 20 yards in six downs, so 7,509 of 8,154 plays counted as long
   yardage. Long yardage is now a pace (5 or more yards a down on the downs left, such as 3rd
   and 20 or 5th and 10) and early down is 1st or 2nd with 15 or more to go. Catalog data,
   inventory and package text updated.
3. **The first game in a process played differently.** The referee pool, built on the
   first game, drew about 2,166 names from the global random stream after the game had
   seeded it. The pool now runs the name generator under its own seed and restores the
   global stream (VAL-02 follow on).
4. **Dead packages.** Packages tied only to drive start or defense energy situations could
   never fire; they are no longer installed until the engine reports those.
5. **Odd program count.** Season start now retires Coast Guard (Merchant Marine if Coast Guard
   is the human's program) instead of refusing to start; a program retired beforehand still
   counts.

## Measurements

Matched games (`scripts/benchmark_team_installation.py --games 300`): same Boot Raid roster,
opponent, head coach, vertical attack OC and seeds; only the installation differs.

| Condition | Spread | Bomb share of kick passes | Quick kick share | Short yardage power and dive | Long yardage kick pass |
|---|---|---|---|---|---|
| No record | 51.7% | 8.4% | 39.5% | 27.2% | 53.2% |
| New hire (0.30, run first trace 0.45) | 49.9% | 7.1% | 43.0% | 28.4% | 53.7% |
| Year two (0.50, trace 0.18) | 50.8% | 8.3% | 41.2% | 29.5% | 54.6% |
| Fully installed | 51.7% | 8.4% | 39.5% | 27.2% | 53.2% |
| Installed plus Heavy Push and Quick Kick Chain | 51.9% | 8.4% | 39.8% | 29.2% | 54.8% |

Fully installed replays the no record games exactly. Packages fired 2.9 (Heavy Push) and 8.4
(Quick Kick Chain) times a game.

Full season, seed 2026: installation on, 53.9 points per team, home 48.2%, lower prestige
wins 37.1%; off, 54.3, 48.8%, 37.9% (identical to main, so the switch removes the effect).
Standard benchmark (no staffs): 53.04 points, same as main. At season start a typical
program executes about 69% of its coordinator's signature (0.75 times 0.925), rising
through the season.

Dynasty through the API: one shared record across season, offseason and next season;
seasons together advance; save and load keep all 204 records.

Tests: 157 pass (16 new in `tests/test_team_installation.py`, 2 in
`tests/test_dynasty_program_count.py`).

## For CCH-03

- `team_installation.defense_execution_factor(team.installation)` returns 1.0 with no record,
  otherwise the defense's execution factor, for scaling a DC's signature.
- Both PRs edit `engine/game_engine.py`; a trial merge result is in the PR.

## Open

- Drive start reporting (first play, after a takeaway, after a score) and on field defense
  energy, so the remaining catalog situations can fire.
- Special teams coordinator effects (later STC work in the plan).
