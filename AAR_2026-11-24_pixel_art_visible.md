# AAR: Make the team banners and stadiums visible again

## What the owner saw
The pixel art team banners and stadiums seemed to be gone from team pages.

## What had happened
They were still rendered, but styled to be almost invisible:
- The stadium was a fixed page background at 5% opacity with a blur, so it
  read as faint pixel noise behind the tables.
- The banner was cropped to a 100 px strip at 60% opacity with a fade into
  the page color. On the light theme that fade turned most of it white.
These styles predate the light theme; the light theme made them worse.

## What changed
- `.team-banner` is a full color hero strip, 120 to 260 px tall depending on
  window width, framed and cropped toward the field instead of the lights.
- `.stadium-bg` is now the home stadium as a crisp 128 px tile (80 px on
  phones) floated beside the page header, on team pages and box scores
  alike. Grids, tabs and tables after it clear the tile.
- College, pro and international team pages put the banner first and the
  stadium tile after it.
- One CSS change covers every page that already used these classes (team
  pages, box scores, pro and international game and team pages).

## Checked
Alabama, Duke and Texas team pages at 1440 px, Alabama at 420 px, and a box
score, on the light theme.
