# AAR: analytics portal model and bowl box score audit

November 27, 2026

## What was asked

Ron asked why the analytics portal said it was trained on 120 games through week 8 when
nearly a whole season had been played, and pointed out the portal was still full of the
slop he had removed elsewhere. He then shared four bowl box scores with an outside review
of them and called the problems bugs to fix.

## Analytics portal

The portal fit its state value model on the first half of the completed weeks only, capped
at 120 games, and showed estimates only for later weeks. The design kept the training games
out of the graded games. For a sim season that meant half the season had no estimates.

* The model now fits on every completed regular season week, up to 600 games picked by a
  stable hash across the whole season, and its estimates show for every game. The first
  page load after a week is simmed takes a few seconds more; the result is cached until the
  season changes.
* The Deserve to Win research fit keeps its own disjoint sample and is still only scored
  on games it did not train on.
* The anti slop pass had skipped this page. Removed: the kicker line, the record count
  subtitle, the overview stat strip, the tool cards that repeated the tabs, the
  "Experimental state values" note, the grouped results note, the scoring and Deserve to Win
  disclaimers, and the "N matching rows" counter. The model note now appears only when
  there is not enough data.

## Box scores

1. Scoring profile. Each method now shows count, points and share of points, such as
   "6 · 54 pts (57%)". The share was always of points, but it sat next to the count.
2. Return touchdowns are split by kind: interception, kick, punt, missed kick, blocked kick
   and fumble returns. The ledger records the kind for new games; older games keep the
   single row.
3. The reconciliation now itemizes the drive scoring subtotal by method, so pindowns on a
   team's own punts show as their own line.
4. Removed two filler notes from the Delta section: "Points, not just scoring frequency" and
   "Static field-position table; not points above replacement".
5. Adjusted yards added the Delta yards scheduled by the engine, including restarts never
   played, while the box score showed only the played figure. Adjusted yards now equal total
   yards plus the Delta yards shown.
6. A possession that ran across the end of the first or third quarter was logged as two
   drives, and the second carried the previous drive's origin label. That inflated drive
   counts and lowered points per drive. The drive log now joins them into one drive. One
   week went from about 27.5 to 26.3 drives per game.
7. Defensive player WPA. Each play's EPA was charged to the tacklers in full. The EP table
   runs high for this sport, so the average snap carries about +0.26 EPA, and every tackle
   on an ordinary gain cost the tackler. Winning defenses averaged negative WPA. Defenders
   are now charged against the game's average EPA per snap. Winning defenses now average
   +6.3, and players with two or more interceptions average +2.1.

## Not bugs

* Navy's player disciplinary records sum to 11 accepted penalties, which matches the team
  figure. The flag column sums to 12 because one flag was declined.

## Play count gaps

One week of games shows a median gap of 27 plays between the teams and a maximum of 90. In
the 20 widest games the team with more plays had 4.5 more drives, 2.6 more plays per drive,
2.7 more bonus possessions and a run share 34 points higher. Teams throw about two
interceptions per game, and each one gives the other side a bonus drive. The gaps come from
the bonus possession rule and long run drives. No scheduling error turned up. Whether that
size of gap is intended is a rules question for Ron.

## Checks

The box score and analytics tests pass. A simmed week had zero unreconciled sides and no
split drives left. The full suite was not run, at Ron's request.
