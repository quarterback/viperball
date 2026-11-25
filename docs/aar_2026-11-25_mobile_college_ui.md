# AAR — Mobile college schedules, navigation and season context

## User-reported defects (November 25)

Actual iPhone Safari captures showed several rows of wrapped season navigation, clipped opponents/scores requiring lateral scrolling, an unnecessary league-wide progress line on every season overview, and undersized week-filter links. Earlier UI polish did not address information architecture or schedule reflow. The user explicitly wants aggregate team/game counts removed regardless of season progress, and animated backgrounds preserved.

## Reference review

- [Apple Human Interface Guidelines: Designing for games](https://developer.apple.com/design/human-interface-guidelines/designing-for-games): preserve legibility across aspect ratios; relative layout constraints and adequately sized touch targets. Adopted 44 CSS-pixel targets for mobile game controls (web adaptation, not a claim of native-point compliance).
- [Apple HIG: Tab bars](https://developer.apple.com/design/human-interface-guidelines/tab-bars): prefer fewer prominent navigation destinations and an appropriate hierarchy. College keeps Overview, Standings, Schedule and a clearly accessible More menu. All 18 original destinations remain; active page is marked. Desktop remains dense, and non-JavaScript fallback is a single horizontal scroll strip. No general game navigation route changes.
- [Xbox Accessibility Guideline 112: UI navigation](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/112): consistent navigation, predictable focus and reflow instead of forcing two-dimensional scrolling. Matchups keep both opponents and both scores in view; deep statistical tables remain individually scrollable.
- [Xbox Accessibility Guideline 101: Text display](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/101): keep important game text readable; use distinct hierarchy. Existing pixel display face retained for headings, proportional team names, tabular scores.
- [Xbox Accessibility Guideline 114: UI context](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/114): explain actions and location rather than surfacing internal state. Simulation button names its actual next week; no zero-week state or universe-wide game-progress text.

## Implementation

- Fixed CSS cascade: later desktop type layer had reset mobile flex-wrap to wrap. Final responsive rules restore one-row navigation everywhere and compact the repeated college section menu into three primary links and a native disclosure. The menu clones the real links, preserving current route, all destinations and keyboard support. Escape/outside click closes it.
- Both schedule and recent results use the same server-rendered matchup table. Desktop remains a table; on narrow screens rows reflow into away and home lines with scores right-aligned, then week/tags and box-score link. Long names wrap instead of disappearing. Explicit table roles preserve semantics. Existing fractional scores, tie/winner styling, rivalry/conference/neutral-site and postseason context, unfinished games, copy and desktop sorting remain. Week filter is an accessible GET form with a native selector rather than 15+ tiny links.
- Remove aggregate team/game counts and progress from college overview, home college directory, college season directory, dynasty command page and duplicate last-updated footer. Retain actual player/team statistical totals, schedule data, and explicitly requested data/administrative reports. Completed season still identifies the champion.
- Repair malformed Team Stats/Referees links in college directory. No change to simulation, API contracts, schedule generation or game results. Keep existing themes, font files, artwork and all P5 effects.

## Validation

Prior UI workflow 45601738379 failed before browser rendering: creating a human-controlled season enters the quick transfer portal, so simulate-week returned HTTP 400. Fix test setup using the real portal skip endpoint; no production behavior change. New template/page tests cover opening and active season headers, actual selected-week results, box-score links, and complete matchup markup. Expanded real-data browser checks cover Chromium desktop/mobile and WebKit 320/390/430 CSS-pixel mobile, including Sand theme; assert single-row compact navigation, preserved link destinations, disclosure interaction and Escape, no page-wide horizontal overflow on overview/schedule, both names/scores and box link inside viewport, week filter submit. Captures are CI artifacts, not yet reviewed on physical iPhone. These tests do not certify all responsive routes or game accessibility compliance.

Credit: original targeted UI polish used Unslop by Damir Sokolovsky (https://github.com/heydamir/unslop), CC BY 4.0. The owner's animated backgrounds are unchanged.
