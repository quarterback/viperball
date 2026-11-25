# AAR: full test run after the merges (November 25, 2026)

## What was asked

Ron asked for the full suite after the recent run of merges (#361 to #378, SCALE-01 and WEA-02) and a report on what turned up.

## What ran

Main at `b2bc68a`, then with the fix below.

| Check | Result |
|---|---|
| `tests/` | 278 passed, 1 failed at first; 279 passed after the fix |
| `test_recruiting.py` | 12 passed |
| `test_wvl.py` | 34 passed |
| `test_commissioner.py` | 41 passed, in 28 minutes |
| `test_season.py` (script) | ran clean, 6 seconds |
| `test_dynasty.py` (script) | ran clean, 52 seconds |
| `scripts/benchmark_engine.py --games 200` | ran clean |
| `scripts/benchmark_engine.py --season 3` | ran clean, 265 games |
| `scripts/benchmark_weather.py --games 100` | ran clean |

## What was found and fixed

1. **The High School section crashed** (`tests/test_high_school_pages.py`). HS-01 (#377) now builds the college recruiting board from the actual high school players and checks that every recruit matches her high school record. The check failed on 3 of 4,800 players, each off by one point of overall rating.
2. **The cause was floating point order, not the ratings.** Every individual rating matched. The high school overall added the weighted ratings in a different order from the recruit and player card overall. A sum like 46.999 truncates to 46 where 47.0 gives 47.
3. **The fix:** the high school overall now adds the ratings in the same order as the other two. All 4,800 players match, and the page test passes.

## Findings that need no fix

1. **Scoring, 200 game benchmark, per team per game:**
   1. Points 52.0, touchdowns 2.74, snap kicks made 3.21 of 3.50, field goals 2.19, turnovers 2.56.
   2. Median margin 19.2, with 22% of games decided by 30 or more.
   3. Close to the WEA-02 run (52.8 points, 2.78 touchdowns).
2. **Three real season weeks:** 52.5 points, 2.62 touchdowns, 3.47 snap kicks, 2.28 field goals, 2.66 turnovers per team. Median margin 20.5, with 24% decided by 30 or more.
3. **Weather effects held through the other agents' merges.**
   1. Heavy rain cost about 5 points per team against clear, raised fumbles, cut bombs from 2.58 to 1.52 and pushed the run share from 48% to 52%.
   2. A 25 mph crosswind dropped snap kicks from 92% to 82%.
   3. Punts averaged 68 yards with a 25 mph wind and 39 into it.
4. **Commissioner tests are slow.** One full WVL commissioner season (four tiers, 64 clubs) takes about three minutes on the full engine, and the file runs about ten of them. That's the cost of removing the fast sim; nothing is wrong.

## Not done

The live site was not checked.
