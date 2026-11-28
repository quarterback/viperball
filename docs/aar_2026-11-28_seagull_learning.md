# AAR: coaches learn from how their Seagulls did

November 28, 2026. Fourth run of the session (branch and PR #410). Earlier runs:
`aar_2026-11-28_formations_motion_seagull.md`,
`aar_2026-11-28_position_fit_short_line_seagull_college.md`,
`aar_2026-11-28_seagull_optional_by_coach.md`.

## What was asked

Ron approved the plan for Seagull learning: coaches learn from Seagull performance the way
coordinators already learn their kick mix and pressure (CCH-08). He also wanted to know what
that learning would change.

## What changed

1. **Per play record of the defensive Seagull.** Each play's `motion` now includes
   `defense_seagull` (name and role) when the defense has a Seagull on.
2. **`coach_learning.observe_seagulls(season, team)`.** For one team's completed games, it
   computes four matched contrasts. Plays are matched by down 4 or later, short yardage, red
   zone and backed up, and valued the way CCH-08 values them (gain against the task, a
   turnover counts as -1).
   * Our offense, with our Seagull on (line or jersey) or not.
   * Opponents' offense, with our defensive Seagull on or not.
   * Opponents' offense, with their Seagull on or not.
   * Our offense, with their defensive Seagull on or not.
3. **`coach_learning.adapt_seagull(card, role, team, year, season)`**, run each offseason in
   `dynasty.py` next to the existing learning.
   * The offensive coordinator learns from our offense. The defensive coordinator learns
     from our defense and, at half weight, from opponents' offensive Seagulls. The head coach
     learns from both sides of his own team and, at half weight, from opponents' Seagulls on
     both sides.
   * "Copy what beat us": when opponents' Seagulls hurt the team, preference rises. A staff
     with no Seagulls of its own learns only this way.
   * Coordinators learn only from games they called. Each contrast needs 6 games and 20 plays
     on its smaller side, and evidence is shrunk by plays / (plays + 60).
   * The change is the signal times receptivity (adaptability times one minus stubbornness).
     It is capped at 0.03 a year and 0.08 over a career, in preference units. Learning
     happens once per coach per role per year.
   * Stored in the coach's tactical profile under `learning.seagull` (`listing`, `offense`,
     `defense`, with history). It travels with the coach and survives save and load.
4. **`presnap.seagull_preference`** adds the learned change for the coach's role, so the per
   game policy reads personality, identity and what the coach has learned.
5. README describes the learning.

## What it changed, over a 16 team dynasty run (4 seasons)

| Season | No Seagull | One | Two | Mean preference |
|---|---|---|---|---|
| 2026 | 24% | 32% | 44% | 0.526 |
| 2027 | 19% | 44% | 38% | 0.522 |
| 2028 | 19% | 31% | 50% | 0.525 |
| 2029 | 19% | 24% | 56% | 0.531 |

About 43 Seagull learning events each offseason, nearly all with enough evidence. Yearly
moves ranged from -0.03 to +0.03, and by 2029 most coaches had learned something. In this
league Seagulls worked well enough that two Seagull programs went from 44% to 56% while the
holdouts stayed at about a fifth. That is one 16 team run, not a league wide finding; another
league or seed can trend the other way.

## Checks

New `tests/test_seagull_learning.py` covers:

* good Seagull results raise preference, within the step and the cap, and survive save and
  load
* bad results lower it
* a stubborn coach barely moves
* games a coordinator didn't call don't teach him
* a staff with no Seagulls learns from opponents' Seagulls that hurt it
* real engine games produce evidence on both sides

These pass: the new tests, coach learning, Seagull rules, coach career, coaching career
continuity, coach tactics and gameplay, rules doc, reproducibility, box score ledger, option
read and NiceGUI frozen tests. The 4 season dynasty ran through the API. The full suite was
not run.

## Left for later

1. The mentor path (assistants learning from the head coach) carries only kick mix and
   pressure, not Seagull lean. A coach's own Seagull learning moves with him.
2. Learned Seagull preference is not shown on coach pages.
