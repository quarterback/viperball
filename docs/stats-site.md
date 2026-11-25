# Stats site and analytics portal

The main browser surface is /stats/, mounted on the same FastAPI application as the simulation and NiceGUI. It supports both reference pages and live session management. Read [architecture](../ARCHITECTURE_STATS_SITE_AND_RECRUITING.md) and [quick start](../QUICKSTART.md).

## Routes

| Area | Path (relative to app origin) |
|---|---|
| Home / saves / search | /stats/, /stats/saves, /stats/search?q=... |
| College season creation | /stats/college/new |
| Single game | /stats/game-sim |
| Dynasty hub | /stats/dynasty/ and /stats/dynasty/{session_id}/ |
| My Team | /stats/my-team/ |
| College season | /stats/college/{session_id}/ |
| Standings / schedule / polls | season path + standings, schedule, polls |
| Team / player / coach | season path + team/{team_name}, player/{team_name}/{player_name}, coach/{team_name}/{coach_role} |
| Box score / defensive calls | season path + game/{week}/{game_idx}, game/{week}/{game_idx}/calls |
| Analytics | season path + analytics |
| Efficiency / luck / ratings | season path + kenpom, luck, ratings |
| Player and team tables | season path + players, team-stats |
| Awards / injuries / referees / postseason | season path + awards, injuries, referees, playoffs, bracketology |
| Alumni / data | season path + alumni, data |
| High school | /stats/high-school/ |
| Professional leagues | /stats/pro/ |
| WVL | /stats/wvl/ |
| International | /stats/international/ |
| Archives / export | /stats/archives/, /stats/export |

Use the router for the complete route contract, including form actions and specific league/team/game parameters. The standalone /stats/recruiting tree redirects to the dynasty hub; it is not a separate recruiting system.

## Analytics

The college Analytics link opens thirteen views. See [analytics reference](../ANALYTICS.md) for formulas. Example queries (replace SID with a live session ID):

```text
/stats/college/SID/analytics?view=plays&group=down
/stats/college/SID/analytics?view=plays&group=raw&down=6
/stats/college/SID/analytics?view=drives&group=origin&scope=regular
/stats/college/SID/analytics?view=scoring&sort=points
/stats/college/SID/analytics?view=expected
/stats/college/SID/analytics?view=plays&group=down&export=csv
```

The game page links to game-filtered play and drive finders. Heatmaps, grouped splits, player/team comparison, CSV exports and customizable table columns all derive from actual session data. Training uses earlier games and displays experimental state values only on held-out later games; statistical support controls availability. The portal does not replace the legacy published EPA/DTW or train a national model on request.

## Implementation

stats_site/router.py defines route handlers and uses lazy API access; stats_site/analytics_portal.py implements query and reporting functions. Jinja templates extend templates/base.html. Use _ctx and the existing season cache where appropriate; never change raw stats when deriving display values. Preserve links to source box scores, use actual player/team identifiers, and guard against ambiguous possession and incomplete events. Use the shared CSS tokens and responsive tables. The default theme is light; Bloomberg dark and other themes remain selectable. Pixel artwork and intentional animation should be preserved.

Box scores distinguish drive and non-drive points, six scoring channels, actual defender credits, line changes, weather, tactical calls, injuries and timeout context. Lateral yards are inside rushing; return touchdowns and defensive INTs have separate credits.

For new routes use actual session objects and existing API actions. Add regression coverage in the existing tests and use browser smoke where interaction matters. No parallel data generator or retired React app. See [development plan](DEVELOPMENT_PLAN.md) for release/verification status.
