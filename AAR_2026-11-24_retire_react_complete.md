# AAR: Retire the React workbench, completed

## Decision
The owner chose to run the whole game from the stats site and retire `/app`.
This run worked through every open item in `RETIRE_REACT_APP.md`, pushing each
piece to PR #336 as it landed, and then removed the React app.

## What shipped
- **Saves and dynasty** (earlier in the run): a Saves page with rename, tags,
  notes, open, fork and delete; dynasty create, start, the season loop, the
  offseason (NIL, portal, recruiting, signing day, finalize) and the Programs,
  Team history, Awards and Record book tabs.
- **In season editing**: the season page lists the open portal with a Sign
  button. Team pages rename the team, edit city, state, mascot and prestige,
  and add players. Player pages edit ratings, bio fields and class, and move a
  player to another team.
- **Archive season**: a plain form that lands on the new archive.
- **Pro leagues**: start a league from the index, then sim week, sim rest and
  play the playoffs a round at a time.
- **WVL**: create a career league; every league tab has sim week, sim rest,
  start the next season and import CVL graduates.
- **FIV**: one bar runs the cycle in order (continental, playoff, World Cup
  draw, group stage, knockouts), plus new cycle with an optional host and seed,
  and archive when done.
- **Tools tab**: Game Sim (one game, shown in the full box score), Compare Runs
  (team records across seasons, sorted by win swing) and Export (standings and
  archive JSON).
- **DraftyQueenz**: open the week's board, pick bets per game and place them as
  singles or one parlay, enter the fantasy contest, fill the five slots from the
  pool, settle the week.
- **Installation panel**: the CCH-04 team installation view was only in React,
  so it moved to the stats team page.
- **Removal**: `web/` is gone, along with the Node stage in the Dockerfile, the
  `/app` mount and the web build job in the CCH workflow. `/app/*` now 301s to
  the matching stats page. `/stats/recruiting/*` used to bounce into React and
  now goes to the dynasty hub; the dead Recruiting nav item is gone.

## How it is wired
All game rules stay in `api/main.py`. Most forms post to `/stats/do`, which
calls the existing endpoint in process and redirects back with a message.
`/stats/do` now also hands form values to `_next`, so a rename can land on the
renamed page. Pages that needed more than one endpoint call per click
(Game Sim, the DQ bet slip) have small routes of their own that call the same
API functions.

## Checked
Walked each flow in a browser with screenshots: portal signing, team rename,
add player, player edit, a pro season through the final, a WVL season into the
next, a full FIV cycle, a one off game, two seasons compared, singles and a
parlay placed and settled, a fantasy slot filled, and the `/app` redirects.
No test suite was run, per the owner.

## Known rough edges
- Seasons and archives share the name "2026 CVL Season", so Compare and Export
  rows are hard to tell apart.
- The archive list includes autosaves next to real archives.
- Some stat tables still put names in number cells, which renders them in the
  mono face.

## Lesson
Read the CI config before deleting a frontend. The CCH workflow built the React
app, and the CCH-04 installation panel existed only there; both would have been
lost silently.
