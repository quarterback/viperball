# AAR: WEA-02, a fuller weather model (November 25, 2026)

## What was asked

After the SCALE-01 hotfix, Ron asked for the weather work in `WEA-02_weather_model.md`.

## What was built

1. **Readings, not labels** (`engine/weather.py`).
   1. Each game now has a `GameWeather`: four periods of readings (temperature, rain, snow or sleet and how hard it falls, wind speed and direction, humidity), a venue, and the field state at the start of each period.
   2. The six labels still come from the climate tables. They set the broad day; the readings set how much it matters.
2. **Weather that moves.**
   1. Each quarter carries over from the one before. Rain stops about 15% of the time per quarter or gets heavier or lighter. A dry game can turn wet, more often in wet climates.
   2. Wind drifts in speed and direction, and the temperature falls about a degree a quarter.
3. **The field.**
   1. Rain soaks it and it stays wet after the rain stops.
   2. Grass holds water longer than turf and turns to mud.
   3. Snow builds up and melts above freezing.
   4. A wet field below 28°F freezes.
4. **Ends and the wind.** The home team attacks north in the first and third quarters and odd overtimes, and the teams switch ends every quarter.
   1. A tailwind adds 0.3 yards of kick range per mph; a headwind takes it away.
   2. Punts gain or lose 1% per mph.
   3. Crosswind costs kick accuracy.
5. **Effects driven by readings, one rule each.**
   1. Ball handling is one multiplier for run fumbles, trick play fumbles, catch fumbles and lateral drops. Muffs use the same multiplier at double weight, and wind adds to it.
   2. This replaces the old mix where run fumbles multiplied by 1.2 and other plays added a flat amount.
   3. Speed depends on the field state and heat. Fatigue depends on the heat index, a wet field and cold. Kick range depends on wind, cold, a wet ball and altitude. Penalties scale with how wet and how hot it is.
6. **Venues.**
   1. Each team has a venue (dome, retractable roof or open; grass or turf; altitude). It's built from a hash of the team's name, so it never changes. Roof and turf rates are set by league, and cold and very hot cities get more roofs.
   2. Altitude comes from the state or country, with city and school overrides (Air Force 7,258 ft, Laramie 7,220, Mexico City 7,350, Bogotá 8,660, Addis Ababa 7,726).
   3. Domes have no weather. A retractable roof closes for rain, snow, cold under 45°F or a heat index over 90.
7. **Real places for every league.**
   1. **College:** home venue, or the neutral site for overseas classics and late playoff rounds. History seasons get weather too.
   2. **Pro leagues:** the home city, with each league's own calendar month (the NVL runs September to February, EL March to July, and so on).
   3. **WVL:** March to November, with tier playoffs in November.
   4. **FIV:** June. World Cup games play in the host nation; other matches in the first-named nation.
   5. **High school:** title games at the home field late in the season.
   6. Southern hemisphere places get their own seasons, so Buenos Aires in December is summer. Tropical places stay warm all year and tropical highlands stay mild.
8. **Coaches react.**
   1. Kick decisions read the conditions: range grows with the wind and shrinks into it.
   2. Bombs drop into the wind and in the rain, and quick kicks rise. A strong tailwind invites the bomb.
   3. Formations tighten as the ball and field get wetter.
   4. Two coach traits that were in the trait table but never used now work. A weatherproof head coach cuts weather penalties by 30%. A wind whisperer cuts headwind and kick weather losses by 20%.
9. **Reporting.** Each game result now has a kickoff line (`weather_label`), for example "Heavy snow, 23°F, crosswind 15 mph, snow on the field". It also has a story line (`weather_description`) with the venue and each later quarter where conditions really changed, and `weather_detail` with every reading. The college, pro, WVL and international game pages show both lines.

## Fixed along the way

1. **FIV matches were always clear.** The weather call passed an argument the function doesn't take, and the error was swallowed.
2. **Pro games drew weather with no location; WVL and high school games had none.**
3. **The `heavy_wind` formation check could never fire.** Wind now shifts formations by its real speed.
4. **Two more old scale leftovers (SCALE-01).**
   1. Punt length was multiplied by `kicking / 80`, so a median punter kicked at 44% of the intended length.
   2. Fumbles on the catch read `hands / 100`.
   3. Both now read the old scale equivalent. The catch fumble check also now feels the weather.
5. **Snow was too common.** The climate tables gave snow and sleet about twice as often as real games see them, and 2 to 5% of Florida, Oregon and England games got snow. Frozen precipitation is now scaled by zone to real snowfall frequency. Places whose low temperature for that time of year is above 36°F get rain instead.
6. **Engines built without `__init__`** (unit test stubs) get calm weather by default.

## Results

`scripts/benchmark_weather.py`, 100 matched games per condition, same matchups and seeds, per team per game:

| Condition | Points | Fumbles lost | Muffs | Snap kick % | FG % | Kick pass % | Bombs | Run share | Penalties | Yards |
|---|---|---|---|---|---|---|---|---|---|---|
| Clear, 65°F | 53.1 | 0.80 | 0.05 | 91.1 | 80.9 | 54.0 | 2.65 | 48.0% | 8.3 | 401 |
| Light rain | 52.1 | 0.97 | 0.09 | 90.3 | 76.3 | 52.6 | 2.38 | 49.6% | 9.5 | 398 |
| Heavy rain, grass | 48.9 | 1.26 | 0.11 | 84.7 | 76.2 | 51.2 | 1.77 | 51.8% | 9.4 | 369 |
| Heavy rain, turf | 49.5 | 1.11 | 0.12 | 84.6 | 74.3 | 51.7 | 1.80 | 51.8% | 9.8 | 374 |
| Snow | 49.7 | 1.09 | 0.10 | 84.5 | 75.2 | 52.7 | 1.81 | 50.8% | 10.0 | 389 |
| Cold, 20°F | 52.1 | 0.90 | 0.04 | 92.4 | 80.5 | 53.8 | 2.67 | 49.2% | 8.2 | 406 |
| Heat, 96°F humid | 51.6 | 0.81 | 0.01 | 92.0 | 81.5 | 52.4 | 2.67 | 48.9% | 8.6 | 381 |
| Wind 25 mph, end to end | 53.7 | 0.92 | 0.04 | 90.1 | 78.6 | 52.3 | 2.41 | 49.4% | 8.5 | 406 |
| Crosswind 25 mph | 51.3 | 0.78 | 0.04 | 81.1 | 69.8 | 51.9 | 2.06 | 48.8% | 7.9 | 397 |
| Dome, 70°F | 52.2 | 0.84 | 0.06 | 91.1 | 79.8 | 53.3 | 2.68 | 47.8% | 8.2 | 397 |
| Altitude 7,000 ft | 54.5 | 0.89 | 0.06 | 93.0 | 78.7 | 53.6 | 2.71 | 48.4% | 8.4 | 406 |

1. **Wind end to end:** 735 kicks with the wind (84% made) against 559 into it (82%). Coaches kick more with the wind and from longer. Punts averaged 70.7 yards with the wind and 37.2 into it.
2. **Cold, 20°F:** snap kick attempts fell from 3.61 to 3.14 as range shrank.
3. **Altitude 7,000 ft:** attempts rose to 4.00.
4. **Heat:** energy fell from 47.2 to 45.6, and yards fell 20.
5. **Noise:** the dome and clear rows differ only by five degrees, so their gap shows the noise in a 100 game sample. That's about 1 point and 0.05 fumbles.

Scoring wasn't tuned toward any number.

**Default games.** A game built with no weather (benchmarks, matched studies, tools) gets fixed conditions from its label for the whole game, so studies stay controlled. Clear is 65°F with no wind. The 120 game benchmark against the SCALE-01 run, which includes the punt fix:

| | SCALE-01 | Now |
|---|---|---|
| Points | 53.9 | 52.8 |
| Touchdowns | 3.00 | 2.78 |
| Snap kicks made | 3.22 | 3.35 |
| Field goals made | 2.21 | 2.30 |
| Turnovers | 2.58 | 2.55 |

**Real places.** A three week real season (265 games) with located weather averaged 53.6 points, 2.84 touchdowns, 3.49 snap kicks and 2.07 field goals per team.

Share of December games (week 16) by condition over 800 draws:

| Place | Snow | Rain | Clear | Wind |
|---|---|---|---|---|
| Minnesota | 35% | 15% | 39% | 11% |
| Illinois | 22% | 24% | 41% | 12% |
| Massachusetts | 23% | 24% | 41% | 11% |
| New York | 11% | 30% | 47% | 11% |
| Tennessee | 8% | 29% | 49% | 14% |
| Washington | 4% | 56% | 23% | 17% |
| Florida | 0% | 30% | 64% | 6% |

## Tests

1. Added `tests/test_weather_model.py` (10 tests):
   1. Domes block weather, and retractable roofs close in bad weather.
   2. The field gets wetter in rain and stays wet afterward, and turf drains faster.
   3. Wind direction flips with ends.
   4. Effects scale with intensity, and every league's location codes resolve.
   5. Southern hemisphere seasons are flipped.
   6. Snow is common in a Minnesota December and rare in Florida.
   7. Venues stay the same every season.
   8. Label-only games stay fixed all game.
2. The full `tests` suite passes (243), and so do `test_wvl.py` and `test_season.py`.
3. Ran an FIV match in Mexico and one in Bolivia, plus EL and NVL pro weeks.

## Not done

1. `test_commissioner.py` under pytest hit a 15 minute timeout before it finished. It wasn't rerun.
2. The live site was not checked.
3. Season and team pages don't yet split results by conditions (WEA-02 item 8.2).
