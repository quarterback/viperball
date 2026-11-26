# AAR: slop left on the archive pages and elsewhere (November 26, 2026)

## What was asked

Ron found slop still on an archived season page, after #380 (the Unslop pass) had been merged:

1. conference names cut off ("Heritage Lea", "Moonshine Le")
2. an all caps ARCHIVED tag
3. "92/1230 games played"
4. "All polls →" links

## Why it was still there

#380 fixed the shared site shell and a list of individual pages: home, college team and playoffs, game log, analytics, My Team, recruiting and the old app. Its AAR says other templates only got the shared changes and weren't audited one by one. The archive pages were among those. The same leftovers showed up on several pages it didn't reach.

## What changed (22 templates)

1. **Cut off names.** Conference, division and team names are no longer chopped at 12 or 15 characters. This covers:
   1. the archive season and standings pages
   2. college season, standings, alumni and analytics
   3. pro team stats
   4. the play by play tables in the college, pro, WVL and international game pages
2. **Arrows on links removed:**
   1. "Full poll", "Full standings" and "Full schedule" on the college season page
   2. "All polls" and "Full standings" on the archive season page
   3. "Details" and "Full rankings" on the international page
   4. "What are these?" on the ratings page

   Arrows that show a sequence stayed, because they aren't links: the CVL to WVL pipeline steps, class years and a player's pro teams.
3. **Game counts read "92 of 1,230 games played"** instead of "92/1230" on the archive season page, the archive index, season compare and export.
4. **The ARCHIVED tag is gone** from the titles of all nine archive pages. The archive season page's subtitle now starts with "Archived".

## Tests

The `tests` suite passes, including the rendered page checks from #380.

## Not done

1. The pages haven't been checked in a browser.
2. The column abbreviations (PWR, PPD) and the table Copy buttons were left as they are.
