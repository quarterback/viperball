# AAR: season data tables for Observable

November 27, 2026

## What was asked

Ron wants Viperball game data to go straight into Observable notebooks. The stats pages
don't paste cleanly, and the only data downloads were standings JSON, whole archive JSON,
and the analytics portal's CSV of the current view.

## What changed

1. New module `stats_site/data_export.py` builds seven flat tables from each game's full
   result. Every row holds one value per column with no nesting, so `d3.csv` or
   `FileAttachment` reads them as is.
   * games: teams, score, winner, margin, conferences, schemes, weather, rivalry.
   * team_games: one row per team per game with the whole team box score. Scalar stats
     come through as they are, and one level of nested stats (EPA, Viperball metrics,
     down conversions) comes through as prefixed columns.
   * player_games: one row per player per game.
   * players: season totals, from the same totals the players page uses.
   * plays: down, distance, field position, formation, call, defensive alignment, blitz,
     result, yards, score, EP and EPA, and the play text.
   * drives: start, length, yards, result and points for each drive.
   * standings: record and efficiency ratings, the same rows as the standings JSON.
2. New routes:
   * `/stats/data/college/{session}/{table}.csv`
   * `/stats/data/college/{session}/{table}.json`
   * `/stats/data/college/{session}/`, which lists every table with its full addresses.
   Any table takes `?week=N` and `?team=Name`. The responses allow any origin, so a
   notebook on observablehq.com can fetch them from the live site.
3. The Export page lists the tables for each running season and shows a two line
   Observable example with the site's own address.
4. The standings JSON route now shares its row builder with the standings table.
5. New test `tests/test_data_export.py` sims a week and checks every table in both
   formats, the filters, the CORS header, the 404s and the Export page links.

## Sizes

One week of a 205 team season comes to 90 games, 15,249 plays (3.1 MB as CSV) and
5,899 player game rows (1.6 MB). A full season of plays is about 16 times that, so the
week filter is the practical way to pull plays.

## Checks

The full suite passes: 335 tests.

## Not verified

Fetching from a notebook on observablehq.com against the live Fly site was not tried.
Locally hosted seasons can only be read by a notebook running on the same machine.
