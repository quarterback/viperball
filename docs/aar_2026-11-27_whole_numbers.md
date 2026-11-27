# AAR: Whole numbers without decimals in stat tables (November 27, 2026)

## Ask

Ron, pasting the Analytics scoring table: "the data should not use .000 unless there needs
to be digitals… it's distracting, taks up spaces and doesn't look clean when the nmumbers
are just whole".

## Cause

Points are stored as floats because a bell is worth half a point, so every point total is a
float even when it is whole. The Analytics table printed every float with `"%.3f"`
(`828.500`, `261.000`, `0.000`). The standings and season pages printed the raw float
(`293.0`), and the team stats and game pages used `'%.1f'`.

## Change

- A `stat` filter in `stats_site/router.py`. A whole value prints with no decimals. Any other
  value prints with only the digits it needs, up to three by default (`828.5`, `261`, `0`,
  `.538`). `stat(1)` keeps the one-place rounding the team stats pages used.
- Used in:
  - the Analytics table cell, which every Analytics view renders through;
  - points for and against on the college season and standings pages;
  - points for and against on the college, pro and WVL team stats pages;
  - the drive points on the game page.
- Nothing under `nicegui_app/` or `ui/` changed.

## Not changed

Rates that are always fractions (win percentage, WPA per play, the three-place `.538` style)
keep their fixed places, because there every value needs the digits and a fixed width lines
the column up. About 280 other `%.Nf` formats in the templates were left alone. Those are
averages and rates, which are rarely whole.

## Checked

See the addendum below for the local run.
