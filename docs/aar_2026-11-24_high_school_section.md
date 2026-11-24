# AAR: High School section in the stats site (November 24, 2026)

Branch `claude/rules-drift-sacks-ladder-fastsim` (PR #367).

## What Ron asked

He could not find the high school league anywhere in the app, and asked for a section that
makes it visible.

## What was there

The HS league (1,538 teams, about 37,000 players, about 7,200 games a season) ran inside
every dynasty but had no page. Its seniors showed up only as prospects on the HS rankings
page, which was not in the main menu.

## What was added

- **High School** in the main menu (new schoolhouse icon), at `/stats/high-school/`.
- Overview: national champion and the national bracket, regional champions, top 25 teams,
  the top 25 seniors with ratings, stars and season stats, and every state with its champion.
  Links to HS rankings and the recruiting hub.
- State page (`/stats/high-school/state/{code}`): postseason games and standings for every
  conference.
- Team page (`/stats/high-school/team/{key}`): schedule with results and the full roster by
  class, with rating, stars, development and season stats.
- A dynasty loaded from a save rebuilds its HS season the way the API does (same year seed),
  so the section is never empty while a dynasty is open. Without a dynasty the page says the
  league runs inside one.
- National bracket rounds were all labelled semifinals; early rounds are now "national
  round" and only the last four are semifinals. Those rounds still run on the full engine.

## Checks

`tests/test_high_school_pages.py` builds a dynasty through the API and loads the overview, a
state and a team page. 202 tests pass.

## Not verified

The pages in a browser on the live site.
