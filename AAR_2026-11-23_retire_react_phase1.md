# AAR: Retire the React workbench, phase 1 (college season controls)

## Decision
The owner chose to retire the `/app` React workbench and run the game from the
stats site. Two interfaces showing the same season with different looks and
different depth was the problem; the stats site already had the identity and the
richer pages.

## What shipped
- `/stats/college/new`: a New season form (name, up to 4 human teams, playoff
  size, bowl count, years of history, AI seed). It calls `create_session` and
  `create_season_endpoint` from `api/main.py`.
- `POST /stats/college/{id}/advance`: one form route; the button pressed picks
  the action (sim week, sim rest, bowls, playoffs, skip portal). It calls the
  existing API functions, so phase rules stay in one place.
- A run bar on the season overview that shows the phase and only the buttons
  that phase allows.
- A New season button on the college index.
- `RETIRE_REACT_APP.md`: the parity checklist. `web/` is deleted only when it is
  complete.

## Checked
Walked it in a browser: create a season with one human team, skip the portal,
sim two weeks. Standings, poll and the run bar updated each time.

## Not done yet
Everything unchecked in `RETIRE_REACT_APP.md`, starting with the conference
editor and per team styles on the New season form.

## Lesson
A first edit added `phase=` to the wrong `TemplateResponse` (the home page,
where `sess` does not exist) because the anchor text appeared twice. Match on
text unique to the target function.
