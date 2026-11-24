# Special teams, penalties and injuries — living AAR
November 24, 2026. Status: audit only; no runtime changes or validation as of this entry.

## Repository status
The branch engine/special-teams-penalties-injuries was created from 0eddeda. At inspection main was 8cbc03e; branch zero commits ahead and four behind. Refresh before implementation. Shared work queue: ASSESSMENT_PRD_ENGINE_TACTICS_2026-11-23.md.

## Findings
- PEN-01: mutable post-play possession is used for foul attribution; accepted live-ball penalties can leave scores, possession and statistical credits intact while replaying a down. Remaining distance and kick-pass automatic-first-down lookup are incomplete. Delay of game can be imposed after resolution.
- INJ-01: injury team attribution depends on possession, defensive risk lacks the offensive fatigue adjustment, and special teams/rush exposure requires explicit participant checks.
- ST-01: five existing special teams schemes and saved STC field-position/return-aggression preferences exist. Connect bounded preferences to legal tactical decisions and real tradeoffs.
- ST-02: separate returner draws for muff, TD and normal return; fake punts grant first downs regardless of distance and cap field position before TD check; ordinary punt return subtracts return yards from receiving-team position; drop kick block omits ST scheme modifier; some selection pools omit availability checks.
- STI-VAL: not run. Compare all five schemes, two coach profiles, depth and fatigue, with fixed seeds and full games. Record net punt/starting field position, blocks, muffs, returns, fake conversions, scoring kicks, penalty enforcement, injuries and substitutions. Use existing workflow and existing suite at integration; no standalone test campaign per work item.

## Prior evidence
Defensive rare-situation study #342 and dynasty study #344 are separate completed workstreams, not evidence for special teams. See shared queue for links.

## Next
Refresh branch from main, implement ST-01/ST-02 plus PEN-01/INJ-01 integrity corrections, run STI-VAL after integration, append actual results and limitations here. No merge/deployment or runtime claims yet.

## PEN-01 and INJ-01 status
Implemented on `claude/pen01-inj01`. Details, numbers and limits in `aar_2026-11-24_pen01_inj01_enforcement_injuries.md`. ST-01/ST-02 untouched; trial merge with #349 is clean.
