# AAR: the site root opens the stats site

November 28, 2026

## What was asked

Ron sent a screenshot of the live site's root address. It showed the old NiceGUI home page
with its card grid, which is the deprecated interface.

## What happened

The live server runs `main.py`, which mounts the NiceGUI app at the root. The stats site
has always been at /stats/, and nothing sent the root there, so anyone opening the bare
address landed on the old app.

## What changed

`main.py` now answers the root address with a redirect to /stats/. The route is registered
before NiceGUI mounts, so it takes the root. `nicegui_app/` and `ui/` are untouched, and the
freeze test still passes. The old NiceGUI pages at their own addresses still load until Ron
decides to remove the app.

## Checks

Loaded `main.fastapi_app` locally: the root returns a 307 redirect to /stats/, and /stats/
loads the stats site.
