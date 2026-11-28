# AAR: report on the kicking counterweight

November 28, 2026

## What was asked

Ron asked for a report on the philosophical change behind the November 28 kicking work. His
months of data and research said snap kicks were too easy and field goals too rare. With
punting fixed as well, the sport now has a counterweight to offense.

## What was done

1. Measured 200 engine games before (commit 44a8f35) and after (commit ded034c) with the same
   team pairs and seeds, using the new `scripts/measure_kicking_counterweight.py`.
2. Wrote `docs/report_2026_11_28_kicking_counterweight.md`: the change, before and after
   figures, the February 2026 calibration targets, and what is still open.
3. README, The Snap Kick: the line saying snap kicks are reliably accurate within 40 yards
   was left from the old model. It now gives the current accuracy.

## Findings

Points fell from 106.1 to 85.4 a game, the share of drives that score from 64 to 55 percent,
and the share of points from kicks from 42 to 23 percent. Touchdowns rose from 5.4 to 6.3.
Made field goals now outnumber made snap kicks. Every February target line is now in range;
before, snap kicks ran at more than twice the top of theirs. Margins and close games did not
change.

## Checks

The script runs from the repo root. No engine code changed. The full suite was not run, at
Ron's request.
