# AAR: Light default theme and a type system for the stats site

## Decision
Part of retiring the React workbench: the stats site becomes the whole app, so
its look was modernized with it. The owner chose light as the default with the
dark look kept as a theme, and wants the pixel art kept and expanded.

## What was hard to read
- Every word was monospace at 11 to 12px: names, labels, sentences, numbers.
- Dim text was #666 on #0a0a0a, about 3.4:1 (needs 4.5:1).
- Every team name was an orange link, so orange carried no meaning.
- Headings were small, uppercase and tracked; stats sat in bordered boxes.

## What changed (all in `stats_site/templates/base.html` unless noted)
- New default theme `viperball`: cool light ground, ink text, dim text at about
  5.9:1, one darker orange (#c74400) that passes as text and as a button fill,
  team names in ink. The dark strip at the top stays in every theme.
- `Bloomberg dark` is the old look, now as a theme, with its dim text raised to
  #8f8f8f. A saved theme choice still wins.
- Type: General Sans (Fontshare CDN) for reading, with Geist self-hosted as the
  fallback; Geist Mono only for numbers in table cells and stat figures;
  Departure Mono (pixel) for the wordmark and page titles. Body 14px, tables
  13px, h2 19px, no uppercase tracking.
- Tables: zebra rows, no row rules. Tabs: no rule, ink active tab with an orange
  underline. Stat tiles: open figures, no boxes.
- Fonts in `stats_site/static/fonts/` with their licenses (Geist OFL, Departure
  Mono MIT).
- Season page: dropped the "Through Week N" line that repeated the subtitle.
  Game page: game rating values were 11px; now readable.

## Checked
Screenshots of the season overview, team, player, box score and New season
pages in the light theme, and the team page in the dark theme.

## Not done
- General Sans could not be downloaded in the build sandbox, so the screenshots
  show Geist. In a browser with network the CDN loads General Sans.
- Some templates put names inside number cells, so those names render in the
  number face. Fix per template as pages are touched.
- Pixel art expansion (icons for nav, positions, trophies, weather) is next.
