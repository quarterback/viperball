# AAR — Viperball interface polish (Unslop)

Method: [Unslop](https://github.com/heydamir/unslop) by Damir Sokolovsky ([@heydamir](https://x.com/heydamir)), CC BY 4.0. Adapted to the existing product, not adopted as a replacement visual identity.

## Direction and owner constraints

- Product: a playable sports simulation and reference site for managing teams and following leagues.
- Character: statistical, sport-specific, archival.
- World: the sports reference desk and scoreboard, with the established pixel-art universe.
- Moments: actual scores, standings, brackets, player/coach faces, stadium and team art.
- Signature: existing Departure Mono titles and hand-drawn pixel icons. Preserve light default, alternate themes, team colors, and existing sports data density.
- **Explicit owner instruction: keep the animated backgrounds.** The P5.js ambient background, nav glow, transition sketch, mount points, trigger and CSS are retained unchanged. Do not remove or disable these in a future cleanup. Existing animation source files are not touched. The static gradient panels on individual cards are a separate issue.

## Audit and changes

| Location | Observed problem | Change |
|---|---|---|
| Shared stats base | Old mobile rules compete with later type layer; 9–10px labels, tiny controls, inconsistent gaps, no keyboard sort focus, shadows | Harmonized spacing, min-width grids, table scrolling, responsive type and control sizes; visible focus; keyboard sortable headers and aria-sort; quiet shared controls |
| Home | Four narrow columns force crowded league tables; nested anchor/button markup; oversized promo accent | Two-column directory, horizontal table wrappers, valid action links, quieter hierarchy |
| College team and playoffs | Multicolor gradient achievement badges; tracked labels | Theme-aware surfaces; actual championship and team identity still meaningful |
| Game log | Hard-coded near-black scoring/turnover/penalty backgrounds on light themes | Theme-aware edge markers and existing textual result indicators |
| Luck / analytics / tactical details | Saturated callouts, redundant rhetorical copy, tracked tiny labels | Neutral panels, data-led text, larger labels, existing numeric values and definitions retained |
| My Team, NIL, retention, portal and finalization | Repeated cards, arbitrary green/gold progress colors, hype, tiny labels; inaccurate CPU program count from positional categories | Shared panels and meters; quieter task links; clear action copy, same forms and endpoints |
| Recruiting commissioner | Fixed amber-on-light colors, hover-only styling, unclear override language | Theme-aware warning and primary action; original permission/assignment workflow |
| Legacy NiceGUI home and shared components | Competing static hue-gradient mode cards, repeated icon-heavy metric cards, tracked headers and heavy weights | Static cards and panels use existing theme surfaces; concise headings, quiet labels, consistent metrics, explicit keyboard-operable Open buttons |
| Legacy WVL, pro, international, DraftyQueenz | Static gradient headers and decorative tier treatment | Flat existing theme surfaces; no modification of game behavior, animation source, ambient layers or animated transitions |

No game engine, scoring, roster generation, database schema, or rules modifications. Existing pixel art, semantic scoring/status colors, flags used as data, and active app theme options remain. The nine Unslop passes were treated as targeted polish, not a demand for generic minimalism. No new imagery or animations were generated. The active stats site and still-mounted NiceGUI entry were both reviewed in source. Other templates inherit shared changes; not every route or every historical theme received an individual visual audit.

## Verification

Added Jinja syntax compilation, actual rendered stats pages, keyboard sorting and animation-wiring checks, plus a Chromium screenshot workflow for real season data on light/dark and narrow/wide views. Screenshots and browser checks are produced by CI; the connector session cannot directly run the app/browser, so visual sign-off is pending. Do not represent screenshots as manually inspected until actually reviewed. Existing P5 sketch blobs should be checked against main when merging. Keep this PR separate from engine work.
