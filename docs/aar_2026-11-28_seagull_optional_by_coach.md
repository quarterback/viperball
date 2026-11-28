# AAR: the Seagull is optional, by personnel and coach preference

November 28, 2026. Third run of the session, after
`aar_2026-11-28_formations_motion_seagull.md` and
`aar_2026-11-28_position_fit_short_line_seagull_college.md`. Same branch and PR (#410).

## What was asked

Ron compared the Seagull to volleyball's libero, which most codes make optional. He wants the
Seagull conditional on a team's players and its coaches' preference, for more offensive and
defensive variety across the sport. Before this run, the engine listed a Seagull whenever a
player qualified, so nearly every college team listed two.

## What changed

1. **Coach preference** (`presnap.seagull_preference`). Each coach gets a 0 to 1 preference
   from his personality sliders: adaptability 35%, chaos appetite 25%, risk tolerance 20% and
   the opposite of stubbornness 20%. His tactical profile, when he has one, nudges it.
   Spread motion and vertical attack offenses lean toward Seagulls and run to kick and
   territory offenses away; turnover hunt and pursuit zone defenses lean toward them and run
   wall defenses away. A missing coach is neutral at 0.5.
2. **Program policy** (`presnap.seagull_policy`). The head coach decides with his
   coordinators' input (60% head coach, 20% each coordinator).
   * Below 0.47 the staff lists no Seagull. From 0.47 it lists one. From 0.535 it lists two
     when it has the players.
   * Keen staffs accept a candidate up to 4% below the player she would replace. Reluctant
     ones want her up to 2% better.
   * The coordinators' own preferences set how she is used. On offense, that's how often she
     plays on the line (half to one and a half times the style's rate) and how much better
     than the line's Viper she must be to take the jersey (0% to 6%). On defense, it's how
     much better than the player on the field she must be to come on (1% to 9%).
   * Preferences bunch near the middle, so each is read as a lean of plus or minus 0.08
     around 0.5.
3. **Personnel still decides.** A staff that wants two lists only the players who qualify by
   position fit, so a keen staff without the players lists fewer.
4. **Records.** The result carries `seagull_policy` for each team. The college game page says
   whether a team's coaches chose not to list a Seagull or no player qualified.
5. Rules and README updated: listing is optional and a team may list none. README describes
   the preference and policy.

## Effect

Two weeks of a real season (180 games, real coaching staffs):

* 29% of teams listed no Seagull, 42% listed one and 30% listed two. Teams stay consistent
  from game to game.
* Usage spreads widely. Seagull snaps on the line per team ran from 0 to 71 over the two
  weeks, and defensive back snaps from 0 to 171.

Real season benchmark (`scripts/benchmark_engine.py --season 2`), code before the session
against now:

| | Before | After |
|---|---|---|
| Points per team | 51.8 | 51.7 |
| Touchdowns per team | 2.73 | 2.81 |
| Turnovers per team | 2.79 | 2.65 |
| Median margin | 20.0 | 17.8 |
| Games within 9 | 27% | 32% |

Games with no coaching staffs, such as the random matchup benchmark, use the neutral
preference and list one Seagull.

## Checks

The Seagull tests now use generated staffs, with a keen staff and a reluctant one. A new test
checks that a reluctant staff lists none, a keen staff can list two and a neutral one lists
one. These pass: the new tests, rules doc, option read, officiating, snap participation, box
score, offensive package execution, reproducibility, opening script, discipline, clinic,
coach tactics gameplay, NiceGUI frozen, high school pages, UI unslop and PWA tests. Thirty
college game pages rendered through the API; 15 showed a team whose coaches chose not to
list one. The full suite was not run.

## Left for later

1. The preference is derived each game from the coach's sliders. It is not stored on the
   coach card or shown on coach pages.
2. Coaches don't learn from how their Seagulls did.
