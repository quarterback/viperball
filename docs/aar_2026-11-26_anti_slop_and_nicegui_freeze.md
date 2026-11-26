# AAR: stats site anti-slop pass and NiceGUI freeze

November 26, 2026

## What was asked

Ron saw "205 teams · 92/1230 games played" on the archive page and said the game counts
should not be there at all. He called the rest of the leftover filler slop, asked for an
anti-slop pass, and asked that agents stop changing the NiceGUI app, which is deprecated.
Another agent had just added a newspaper tab to it.

## What changed

Stats site:

1. Game counts are gone everywhere: page subtitles, the export and archive tables, and the
   compare page. The earlier "92 of 1230" change in `aar_2026-11-26_archive_and_site_slop.md`
   is replaced by this removal.
2. Count subtitles are gone from saves, finalize, dynasty pages, players, KenPom, standings,
   luck, alumni, referees, high school, recruiting rankings, international rankings and the
   WVL pages. The WVL header now reads "Week X of Y".
3. Taglines that repeated the heading or the nav are gone from the home, search, archive,
   college, dynasty, pro, international, recruiting, commissioner, signing tracker, pro
   pipeline and WVL index pages.
4. The footer keyboard hint and the footer rule are gone. The table Copy buttons were removed and then put back: Ron uses them to paste game data, since the pages don't paste cleanly otherwise.
5. The duplicate Analytics portal button on the season page is gone. "DQ" tabs read
   "DraftyQueenz".
6. Scheme keys show as their labels through a new `scheme` template filter.
7. The archive poll heading says "Final poll" or "Poll after week N" instead of claiming a
   final poll for an unfinished season. "Standings (Top 25)" is "Standings".
8. A heading right under the tabs no longer gets a top margin, so the season page sits tight.
9. Twenty three all caps page titles (SEARCH, PRO LEAGUES, KENPOM EFFICIENCY METRICS and
   others) now use sentence case to match titles like "2026 CVL Season".

NiceGUI:

1. Reverted commit 76f8431, the other agent's newspaper tab in `nicegui_app/pages/league.py`.
   Its stats site newspaper page and nav links stay.
2. Added `AGENTS.md` and `CLAUDE.md` at the repo root. Both say `nicegui_app/` and `ui/` are
   frozen, that all interface work goes in `stats_site/`, that `web/` stays retired, and list
   the standing rules.
3. Added `tests/test_nicegui_frozen.py`. It hashes every file under `nicegui_app/` and `ui/`
   and fails on any change. The file says not to update the hash to make it pass.

## Checks

The full test suite passes: 334 tests. Pages were rendered in Chrome before the title change
to confirm the spacing fix and the removed buttons.

## What went wrong

The earlier unslop agent audited only the pages it was given, so archive pages and several
others kept their filler. I first reworded the game count instead of asking whether it
belonged on the page at all.

## Left alone

The home page title "Viperball" repeats the logo. It stays until Ron says otherwise.
