# Viperball browser interface

The main league and management interface is the server-rendered stats site at /stats/. The single Python application also mounts NiceGUI for remaining interactive screens. The older desktop GUI and React application are not current launch targets.

## Navigation

Start at /stats/ (see [Quick start](QUICKSTART.md)). College and Dynasty create or reopen live sessions. Use My Team for program actions, Saves for saved games, High School for feeder competition, Pro and WVL for club leagues, International for FIV, and Archives for archived seasons. Some management actions depend on the session's current phase.

College season navigation includes standings, schedule, polls, players, team statistics, KenPom, Luck, referees, Analytics, ratings, injuries, bracketology, playoffs, awards, alumni and data. Team pages link to rosters, coaching staff, installations and schedules. Game pages show score, team/player credit, plays and drives. Analytics is a full portal, not only a player leaderboard.

The shared stats template uses light Viperball styling by default, alternative themes including Bloomberg dark, responsive navigation, scrollable tables, pixel artwork and icons. The interface is designed for browser use on desktop and mobile. Actual visual/browser regression status is in the development plan.

## Implementation

- stats_site/router.py: routes and session access.
- stats_site/templates/: Jinja templates extending base.html.
- stats_site/analytics_portal.py: read-only season analytics queries.
- nicegui_app/: remaining NiceGUI pages and shared UI.
- api/main.py: game and management actions.

Read [stats-site guide](docs/stats-site.md) for URLs and developer conventions. Use the existing style tokens and components; preserve the site's compact statistical presentation and animated elements. Do not introduce a parallel database, disconnected recruiting pool, or a separate UI runtime.
