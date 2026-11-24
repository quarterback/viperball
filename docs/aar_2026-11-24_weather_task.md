# AAR: weather model task (November 24, 2026)

## What was asked

Ron asked for a more robust weather model to go on the task list.

## What was done

1. Read the weather code: `engine/weather.py`, the `WEATHER_CONDITIONS` table and every weather check in `engine/game_engine.py`, and the weather calls in the season, pro, WVL, FIV and high school code.
2. Wrote the findings and the build plan in `WEA-02_weather_model.md`.
3. Added WEA-02 to the queue as P1 and folded WEA-01 into it.
4. While reading the fumble code, found that run fumbles still compare `hands` to old scale numbers (60 and 85). Logged that as SCALE-01 for an audit of every raw rating check in the engine.

## What was found

1. FIV matches are always clear because the weather call uses an argument the function doesn't take, and the error is swallowed.
2. Pro games draw weather with no location. WVL and high school games get none.
3. The `heavy_wind` formation check can never fire.
4. Run fumbles and other fumbles apply weather by two different rules.
5. Temperature is generated but never used by the engine.

## Not done

1. No code changed. This run only planned the work.
2. No tests were run, because nothing in the code changed.
