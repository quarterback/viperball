# AAR: coaching identity, steps 4, 5, 6 and 8 (November 25, 2026)

## What was asked

Ron shared another agent's coaching identity plan and answered the open questions:

1. Rename Ground & Pound to Ground Control.
2. No Possession KP, since East Coast already does that.
3. Keep the eight defense names, sharpen them, and add Keeper Hunt and Rotation.
4. Every defense should be balanced against the field.
5. Chain Gang and Lateral Spread stay weak but distinct. They are the old, rugby like offenses and should be more common in high school.
6. Build on the existing coaching system. Saves don't need to survive.
7. Do steps 4, 5, 6 and 8 in that order. Leave step 7 (adaptation over seasons, recruiting fit, coaching trees) and dynasty testing for later.

## What changed

1. **Ground Control.** `ground_pound` is now `ground_control` everywhere in code and data. The old key maps through `STYLE_MIGRATION`.
2. **High school offenses.** Lateral Spread and Chain Gang joined the high school list, weighted so each runs at about 16% of schools. The full list is balanced 18%, Ground Control 17%, Chain Gang 16%, Lateral Spread 16%, tempo 12%, triple option 11% and smashmouth 11%.
3. **Step 4: defenses as real counterparts (DEF-12).**
   1. A defense's strengths and weaknesses by play family were weighted at 0.35 in the per play matchup, which flattened every defense toward the same one. The weight is now 0.6, with bounds of 0.72 to 1.25.
   2. New `DEFENSE_SIGNATURES` give each defense specific outcomes: kick pass interceptions (Predator 1.40, Lockdown 1.15, Chaos 1.10, Drift 0.85), lateral interceptions (Swarm 1.45, Predator 1.25, Chaos 1.15), forced run fumbles (Blitz Pack 1.25, Predator 1.20, Fortress 1.10, Swarm 1.05) and kick rush (Keeper Hunt 3.0, Blitz Pack 1.20, Chaos 1.15).
   3. Kick rush raises blocked snap kicks and place kicks, and lowers snap kick success, mostly on 6th down. Coaches see the lower success when they decide whether to kick.
   4. **Keeper Hunt** is new: the kick rush, average numbers everywhere else, and it gives up short yardage conversions.
   5. **Rotation** is new: 0.60 fatigue resistance, ignores most of the extra tempo fatigue, and is slightly below average on every snap.
   6. The tables keyed by defense name, the matchup table, the formation table, the playbook families, the AI scheme lists and the labels all include the two new defenses.
4. **Step 5: weekly game plans (DEF-13).**
   1. Before every game, each defense leans part of the way toward the scheme that best counters the opponent's offense. The `COUNTER_DEFENSE` choices come from the measured defense by offense matrix.
   2. The lean is 0.35 times the head coach's adaptability, times two minus stubbornness, capped at 0.6. The defense keeps its name, label, alignment and signature.
   3. The plan is in each game result under `game_plans`.
5. **Step 6: coach fingerprints (COACH-FP-01).**
   1. Head coaches have six new personality sliders: touchdown finish, late down aggression, run lean, kick pass lean, lateral lean and turnover caution.
   2. At slider 0 or 100, they move the style's kick eagerness by 0.20, its go-for-it appetite by 0.20 and its turnover caution by 0.30, and scale the run, kick pass and lateral weights by 0.75 to 1.25.
6. **Step 8: the fingerprint panel.**
   1. `engine/fingerprint.py` measures a team from its season's play by play: run, kick pass and lateral share; the share of points from touchdowns; how often it goes for it on 5th and 6th down past midfield; how often it kicks when in range on 4th to 6th down; plays per game; and its game plan lean.
   2. The college coach page shows it, with the offense and defense, and the tendencies table lists the new sliders.

## Results

**Defenses against the field** (160 games each, both sides; the teams' own offenses):

| Defense | Win % | Points allowed | Opponent TDs | Opponent yards per carry | Opponent kick pass % | Takeaways |
|---|---|---|---|---|---|---|
| Swarm | 55 | 49.6 | 2.73 | 4.90 | 58.7 | 2.57 |
| Predator | 55 | 50.4 | 2.93 | 5.46 | 48.6 | 2.74 |
| Drift | 53 | 47.9 | 2.39 | 5.07 | 51.5 | 2.33 |
| Lockdown | 52 | 46.9 | 2.56 | 5.26 | 45.5 | 2.58 |
| Rotation | 50 | 49.8 | 2.73 | 5.10 | 52.5 | 2.34 |
| Blitz Pack | 48 | 52.8 | 3.21 | 5.32 | 53.8 | 2.54 |
| Shadow | 48 | 50.9 | 2.76 | 5.22 | 52.7 | 2.47 |
| Fortress | 48 | 50.8 | 2.90 | 4.67 | 61.1 | 2.33 |
| Chaos | 48 | 51.0 | 2.91 | 5.06 | 54.7 | 2.30 |
| Keeper Hunt | 48 | 51.3 | 3.22 | 5.19 | 55.3 | 2.37 |

Before this run the spread was 40% (Chaos) to 56% (Lockdown), and Predator's takeaways matched everyone else's.

**Matchups.** Points allowed, 50 games per cell, with the defending team on a Balanced offense:

1. Against Ground Control: Fortress 45.9, Lockdown 58.1.
2. Against Shock & Awe: Lockdown 54.1 and Drift 54.3, Blitz Pack 69.6.
3. Against Chain Gang: Predator 43.3, Lockdown 44.2.

**Keeper Hunt.** It cut snap kicks made against Boot Raid from 3.76 to 3.0 a game. But Boot Raid's touchdowns rose from 2.84 to 3.68, because a missed snap kick on downs 1 to 5 keeps the ball. Kick pressure mostly turns kicks into extra downs. It was refocused on 6th down and blocks, and it ends up about even with Swarm against kick first teams.

**Offenses against a Balanced offense** (60 games each). In the share of points from touchdowns:

1. Ground Control 57%, Stampede 56%, Chain Gang 56%.
2. Six Shooter 39%, Ball Control 36%, Ironclad 34%.

The run offenses still win the most: Ironclad 73%, Ground Control 68%, Stampede 62%. That was true before this run too.

**Fingerprints over six real weeks.** Kicks when in range:

1. Six Shooter 78%, Boot Raid 71%, Ball Control 70%.
2. Stampede 44%, Ground Control 36%.

Within Ground Control, the share of points from touchdowns ran from 35% to 84%, and the late down go rate from 32% to 85%.

**League, per team per game:**

| | Before | Now |
|---|---|---|
| 200 random games: points | 52.3 | 50.2 |
| 200 random games: touchdowns | 3.02 | 2.90 |
| 200 random games: field goals | 1.77 | 1.69 |
| 3 real season weeks: points | 51.8 | 50.1 |
| 3 real season weeks: touchdowns | 2.80 | 2.59 |
| 3 real season weeks: field goals | 1.91 | 1.98 |
| 3 real season weeks: median margin | | 19.0 |
| 3 real season weeks: decided by 30 or more | 21% | 20% |

## Fixed along the way

The diving wing snap kick block check compared raw speed to an old scale 78 (SCALE-01).

## Tests

1. Added `tests/test_coaching_identity.py`.
2. Updated the defense table tests for ten defenses and the new matchup weight.
3. The `tests` suite passes (295).

## Not done

1. Step 7: adaptation over seasons, recruiting fit and coaching trees. No dynasty testing.
2. Keeper Hunt's roughing fouls were not added to officiating.
3. The fingerprint panel is on the college coach page only.
