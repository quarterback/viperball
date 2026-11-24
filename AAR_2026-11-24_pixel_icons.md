# AAR: Pixel icon set for the stats site

## Decision
The owner loves the pixel art and wanted it carried further as part of the
stats site refresh. The existing art (player and coach faces, referees,
stadiums, banners) came from PixelLab and lives in `stats_site/static`. Icons
are small and need to follow every theme, so they are drawn by hand in code
instead of generated.

## What shipped
- `stats_site/pixel_icons.py`: 21 hand drawn 16x16 icons (home, ball, crown,
  trophy, planet, globe, box, search, floppy, wrench, shield, play, forward,
  bracket, bowl, flag, door, coin, card, people, dice). Each is a character
  grid: `#` takes the text color and `+` takes the theme accent, so the icons
  recolor with the theme. `icon(name, size)` returns inline SVG built from pixel
  runs with crisp edges. It is a Jinja global, so any template can call it.
- Nav: every section has its icon.
- Run bars and main actions: sim week (play), sim rest (fast forward), bowls,
  playoffs (bracket), start season (flag), archive (box), the dynasty, pro,
  WVL, FIV, DraftyQueenz, Saves and Game Sim buttons.
- Empty states show a large icon and link to the action that fills them. This
  also removed the leftover "start one from the main app" text that pointed at
  the retired React app.
- Home: section headings carry icons; the DraftyQueenz banner uses the theme
  accent and a coin icon instead of a fixed teal.
- Team roster: each player row shows that player's pixel face from the
  existing face pool.

## Checked
Screenshots of the icon sheet at 16, 32 and 64 px on light and dark grounds,
the nav, the season run bar, the roster with faces, the home and college empty
states, and a narrow window. The first ball and planet drawings read poorly at
16 px and were redrawn.

## Follow up (same day)
- Pixel faces now show in the season player stats table and in every player
  row of the college box score, through one cached name to face map per season.
  One off Game Sim games have no player ids, so they show no faces.
- Between 769 and 1240 px wide the nav shows icons only, keeps the active
  section's name, and puts each label in the link title. Below 769 px the
  existing menu button opens the full list with labels.
- Found while checking: older templates used an undefined `--bg-card` color,
  so the player stats filters rendered as dark boxes with dark text on the
  light theme. `--bg-card` now points at the theme's panel color.

## Not done
- Page titles have no icons; the pixel title face already carries them.
