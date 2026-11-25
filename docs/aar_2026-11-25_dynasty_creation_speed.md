# AAR: faster dynasty creation (November 25, 2026)

## What was asked

Ron said dynasty creation is too slow on mobile.

## What was slow

Profiled `POST /sessions/{id}/dynasty` with the defaults (no history years) on the dev machine. It took **44.5 seconds**:

| Step | Seconds |
|---|---|
| High school season before the dynasty starts | 35.3 |
| (of which 101 title games on the full engine) | 32.7 |
| Building the 1,538 school high school league | 2.5 |
| Building the recruiting board from it | 2.7 |
| Saving the dynasty (most of it the high school league and board) | 2.2 |
| Loading fresh college rosters | 1.5 |

The 101 title games are the state finals and the regional and national rounds. HS-01 (#377) made dynasty creation build the high school league up front and play a full season so the recruiting board starts with real players.

## What changed

1. **The season before the dynasty starts plays on the quick model** (`engine/college_feeder.py` `_backstory_sim`, `simulate_hs_season(engine_rounds=...)`). That season is backstory: it happened before the player arrived, the same as history. Seasons played during the dynasty still run their title games on the full engine.
2. **The high school build runs after the response goes out** (`build_college_feeder_in_background`). The dynasty saves first, then the high school league and recruiting board build on a background thread, and the dynasty saves again with them.
   1. Any page or offseason step that needs the feeder (the High School section, the Recruiting Hub, the offseason advance) waits for that build instead of starting a second one.
   2. Every feeder build and advance now runs under one lock.
   3. The build uses only its own seeded random streams and never Python's global one (checked), so running it on a thread can't change the college schedule or game results.
3. **High school team strength is worked out once per season** instead of on every game. Ratings don't change during a season. Results are identical (checked game by game).

## Results

| | Before | After |
|---|---|---|
| Dynasty creation response | 44.5 s | 0.6 to 1.6 s |
| Background high school build | none | about 6 s |
| High School page opened right after creating | 44.5 s already spent | waits about 3 s, once |
| High School page after that | | 0.13 s |

The saved dynasty includes the high school league and recruiting board once the background build finishes.

## Tests

The `tests` suite passes (285).

## Found, not changed

**History years are very slow.** One history year took **120 seconds**, because history seasons play every college game on the full engine since the fast sim was removed. The setup slider goes up to 100 years, which would be over three hours. History years default to 0, so the default path is fast.
