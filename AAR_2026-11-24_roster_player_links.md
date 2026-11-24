# AAR: Roster names link to player pages on every school page

## What the owner reported
School pages did not link roster names to individual player pages.

## What I found
The live college team page already links each roster name. Two school pages
did not:
- **Archived team pages** (`/stats/archives/{key}/team/{team}`): the roster
  was plain text, and archives had no player page at all.
- **My Team** dashboard roster: plain text.
Pro, WVL and international team pages already link their rosters.

## What changed
- New archived player page,
  `/stats/archives/{key}/team/{team}/player/{name}`: profile and attributes
  from the archived roster, awards from the archived season, and a game log
  with season totals read from that season's saved box scores. Opponents link
  to their archived team pages. If no box scores were saved, the page says so.
- Archived team rosters link each name to that page.
- My Team roster names link to the live college player page.

## Checked
An archived team roster links through to a player page with a one game log
and totals. The My Team link uses the session and team the dashboard already
has; it was not clicked through in a browser.
