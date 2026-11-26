# Instructions for agents working in this repo

## The NiceGUI app is deprecated. Do not change it.

`nicegui_app/` and `ui/` are the old NiceGUI interface. They are frozen.

- Do not add features, pages, tabs, panels, labels or fixes to `nicegui_app/` or `ui/`.
- Do not wire new engine features into them, and do not "keep them in sync" with the stats site.
- All interface work goes in the stats site: `stats_site/router.py` and `stats_site/templates/`.
- `tests/test_nicegui_frozen.py` fails if any file under `nicegui_app/` or `ui/` changes. Don't update its hash to make it pass. Ron decides when the NiceGUI app is removed.

The React app in `web/` was retired and removed. Don't recreate it.

## Other standing rules

- Write an after action record (AAR) in `docs/` for every run of work, and add a step to the session AAR.
- The README is the rules record. Keep it current when rules change.
- Plain language in docs and on the site. No dashes in prose.
- Never credit AI tools or agents in the game's credits.
- Specs from other agents are input, not rules.
