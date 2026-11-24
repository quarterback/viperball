# WEA-02: a fuller weather model

**Priority:** P1. **Status:** open. **Replaces:** WEA-01, which only asked to isolate rain effects.

## What the game does now

1. **Six fixed labels.** Every game gets one of clear, rain, snow, sleet, heat or wind, picked once from the home state's climate zone and the week (`engine/weather.py`). Each label carries a flat set of modifiers (`WEATHER_CONDITIONS` in `engine/game_engine.py`). A light drizzle and a downpour play the same.
2. **Temperature is only for show.** College games get a temperature (`generate_game_weather_full`), but the engine never reads it. A 20 degree night plays like a 60 degree one unless the label is snow or sleet, and heat is a label instead of a reading.
3. **Weather never changes during a game.** The label set at kickoff holds to the final whistle.
4. **Wind has no speed or direction.** Wind lowers kick accuracy and adds 8% to every punt for both teams, whichever way they face. Switching ends does nothing.
5. **No roofs, surfaces or altitude.** The stadium generator writes up domed stadiums and turf fields, but the engine plays every game outdoors on the same footing. Mountain venues play like sea level.
6. **Most leagues get no real weather.**
   1. Pro leagues call `generate_game_weather()` with no location, so every pro game draws from the default climate at week 5.
   2. WVL and the high school league don't pass weather, so their games are clear.
   3. FIV calls `generate_game_weather(season_month="June")`, an argument the function doesn't take. The error is swallowed, so every international match is clear.
7. **Bugs in the engine's weather code.**
   1. Formation selection checks for `"heavy_wind"`, a condition that doesn't exist, so wind never changes formations.
   2. Run play fumbles multiply by 1.2 in rain, snow and sleet. Every other fumble check adds the condition's modifier instead. The same weather has two different rules.

## What to build

1. **Weather as readings, not labels.** For each game, track:
   1. temperature
   2. precipitation, from none through light and moderate to heavy
   3. wind speed and direction
   4. humidity, to work out the heat index
   5. field state: dry, wet, muddy, snow covered or frozen. The field gets worse the longer precipitation lasts and stays bad after it stops.
2. **Weather that moves.** Give each period its own conditions, mostly carried over from the period before, so rain can start, stop or get heavier, wind can pick up, and the temperature can drop after dark.
3. **Wind relative to the field.** One end plays into the wind. The teams switch ends on the game's normal schedule. Kick distance and accuracy depend on how much wind is with or against the kick and across it, so a snap kick into a 20 mph wind is a different decision than one with it.
4. **Effects driven by readings.**
   1. Ball handling (fumbles, muffs, lateral drops) depends on wetness and cold.
   2. Kick distance and accuracy depend on the wind and on temperature, since a cold ball travels shorter.
   3. Footing and speed depend on the field state.
   4. Fatigue depends on the heat index.
   5. One rule per effect across every kind of play, replacing the current mix of added and multiplied modifiers.
5. **Venues.**
   1. Roof type: open, dome or retractable. A closed roof means no weather.
   2. Surface: grass or turf. Grass turns to mud and turf doesn't.
   3. Altitude: thinner air carries kicks farther.
   Store these with the stadium so the same venue plays the same way every season.
6. **Real places for every league.** Draw college and high school weather from the home state and the date, pro and WVL weather from the home city, and FIV weather from the host nation. Neutral sites and bowls use the venue's location.
7. **Coaches react.** Coaches should plan from the forecast and adjust during the game: lean on the run in heavy rain, choose kicks by wind direction, and rotate more in heat.
8. **Reporting.**
   1. Box scores show conditions by period, including wind direction.
   2. Season and team pages can split results by conditions, such as kick success into the wind or fumbles on a wet field.

## Fix first

These are broken now and can be fixed before the new model lands:

1. the FIV weather call
2. the `"heavy_wind"` check
3. pro, WVL and high school games getting a location
4. one fumble rule for weather

## How to check it

1. **Matched games.** Play the same matchups and seeds under controlled conditions (clear, light rain, heavy rain, cold, strong wind each way, heat, dome). Report how each effect moves and by how much: fumbles, kick distance and accuracy, sacks, explosive plays, fatigue, play mix and coach choices.
2. **Climate sanity.** Over a full season, the share of games by condition should look like the real place and date. Snow should be common in Minnesota in December and close to absent in Florida, with rain most common in the Pacific Northwest.
3. **No scoring target.** Scoring floats on the mechanics. Report how scoring shifts by condition, but don't tune it toward a number.
4. **Tests.**
   1. Roofs block weather.
   2. Wind direction flips with ends.
   3. Every league passes a location.
   4. The field state builds up with precipitation and doesn't reset in the middle of a game.
