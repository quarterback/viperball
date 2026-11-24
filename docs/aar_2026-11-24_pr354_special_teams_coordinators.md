# AAR 2026-11-24: PR #354, special teams coordinators and kick execution (ST-01, ST-02)

This records what PR #354 changes and how it measures. The three commits on the branch had no description or AAR. #349 is a separate draft of the same two items and is not part of this.

## What the PR changes

### ST-01: the special teams coordinator now makes choices
- `coach_tactics.resolve_special_teams_tactics` reads the saved coordinator's `field_position_bias` and `return_aggression`, each held to ±0.5. Both are scaled by the coordinator's authority, which comes from the head coach's delegation (0.4 to 1.0; 1.0 with no head coach). No coordinator means no change. The setting `special_teams_tactics_enabled` turns it off.
- Field position bias moves three decisions, by up to the amounts below at the full ±0.5 setting. A positive (territory) bias does the first set, a negative bias the opposite.
  - On 5th down, the shortest yardage at which the team takes a snap kick drops by up to 2 yards.
  - On 6th down, the line inside which the team punts instead of going for it moves out by up to 5 yards.
  - The fake punt rate is cut by up to half (a negative bias raises it by up to half).
- Return aggression tilts who returns punts toward speed and away from hands. It also moves return yards, return touchdown chances on punts and missed kicks, and muff risk up or down by up to 15%.
- Each game records the coordinator's profile and a count of special teams calls by kind and result (`special_teams_tactics` in the game result). Each kicking play carries a `special_teams_event` with the kicker, returner, coverage tackler, return yards, start and end spots, and whether it was nullified.

### ST-02: kick execution fixes
- **Punt returns move the right way.** A return used to move the receiving team backward from the catch, about 13 yards a game. It now moves them forward, held short of the goal line.
- **Return touchdown yards.** Punt return touchdowns credited the catch spot as the return length. They now credit the distance actually run. Missed kick return touchdowns had the same fault and are fixed too.
- **Blocked punts.** Field position after a blocked punt was measured from the wrong goal line for the team that took over. It now flips correctly.
- **One returner per punt.** The muff check, the return touchdown check and the return each picked their own returner, so one punt could credit three people. One returner is now picked and used for all three.
- **Fake punts.** A fake used to be a first down at any distance. It now converts only if it reaches the line to gain. Otherwise it is the next down, and on 6th down a turnover on downs. Fakes are less likely on long yardage and deep in the team's own end. The ball carrier comes from the skill players instead of the first six names on the roster.
- **Fatigue and availability.** Tired returners and coverage players are less likely to be chosen, and a tired returner is more likely to muff. Injured players are skipped for coverage credit and for the diving wing who blocks drop kicks.
- **Scheme effects that were missing.** Kicking team coverage now affects whether a punt can be returned out of the end zone. The rushing team's block modifier now applies to drop kicks. Return and coverage modifiers now apply to missed kick return touchdowns.

### Added in this write up
- The branch was merged with current main (which now carries #350 and #352); there were no conflicts.
- A fake punt that fell short printed `GAIN!` and a conversion printed `FIRST_DOWN!`. It now reads `FIRST DOWN!` or `TURNOVER ON DOWNS!`, and a short gain still reads `GAIN!`.

## How it measures

All counts come from seeded full engine games on independent matchups (`scripts/benchmark_engine.py` teams). The earlier special teams benchmark reused 20 seeds across every scheme and profile, so the same few random draws repeated in every cell and its absolute rates were not trustworthy.

### Baseline engine, no coordinator: 400 games each

| | main | this PR |
|---|---|---|
| Punt calls per game | 2.24 | 2.23 |
| Fake punts | 14 (5 first downs) | 9 (2 first downs) |
| Muff rate per punt | 5.9% | 5.0% |
| Return touchdown rate per punt | 3.1% | 1.8% |
| Blocked punt rate | 2.9% | 2.6% |
| Blocked kick rate | 3.63% | 3.88% |
| Points per game, both teams | 102.8 | 104.2 |

On this branch, 469 punt returns over 300 games all ended within 15 yards of the catch spot plus the return yards. The 15 yards is the largest accepted foul added to the end of a return.

The return touchdown rate per check is about the same on both (3.7% here, 4.1% on main). The lower overall rate comes from fewer punts reaching the check, and from small numbers: 400 games produced a few dozen return touchdowns either way.

### Coordinator profiles: 300 games each, home coordinator only

Same matchups and seeds in every row. Field position bias and return aggression are listed in that order.

| Profile | Home punt calls | Fakes | Snap kicks | Muff rate | Return TD rate | Yards per return | Home points per game |
|---|---|---|---|---|---|---|---|
| Neutral (0, 0) | 310 | 3 | 1175 | 5.3% | 3.0% | 9.0 | 51.5 |
| Territory (+0.5, −0.5) | 305 | 3 | 1175 | 5.1% | 2.6% | 8.0 | 51.2 |
| Attack (−0.5, +0.5) | 310 | 3 | 1161 | 5.4% | 4.1% | 9.6 | 51.8 |

Return aggression shows up clearly in return yards and return touchdowns. Field position bias barely moves punt and snap kick calls at this size. Scoring is flat.

## Validation

Existing suite (`tests/`) on the branch merged with main: 181 passed.

## Notes for whoever finishes ST-01/ST-02
- Fakes are now rare: 9 in 400 games, against 14 on main. Check that this is intended before tuning anything that relies on them.
- #349 also counts blocked kicks as kick attempts and awards a recovery bell on blocked drop kicks and place kicks. This PR does neither, so the two versions disagree on those stats.
- Field position bias lowers the 5th down snap kick yardage line, so a special teams coordinator who favors field position takes more short 5th down snap kicks. That may be the opposite of the intent.
