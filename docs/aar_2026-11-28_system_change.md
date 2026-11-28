# AAR: a head coach changes the program's system (casebook case 6)

November 28, 2026

## What was asked

Ron asked for Saban's system change from the coaching casebook: a long-serving head coach
switching the program's system after a run of evidence. Before this, a program's school
changed only when a new head coach arrived.

## What changed

1. New module `engine/coach_reinvention.py`. A continuing head coach of a computer program
   changes one side's school when all of these hold:
   * she has led the program for at least four seasons, from her open head coach career
     stop;
   * the side is the one she does not specialize in (an offensive specialist changes the
     defense, anyone else the offense);
   * the program was in the bottom 40 percent of the league on that side in each of the last
     two seasons, by points per drive on offense and points allowed per game on defense,
     with at least ten programs in the comparison;
   * another school run by at least three programs beat the current school's league average
     last season by at least a quarter of the spread between schools;
   * a roll passes with a chance of 0.25 plus 0.8 times (adaptability minus stubbornness),
     between 0 and 0.75.
2. `engine/dynasty.py`. After the existing school plan for the new season, each continuing
   computer head coach is considered. A change replaces that side's school in the plan and
   is recorded in `coaching_history[year]["school_changes"]` with the side, old and new
   school, coach and tenure. The human team is never changed. The team's existing
   installation applies its normal cost for a new school, and the coach's own tactical
   signature does not change.
3. README rules record and `tests/test_system_change.py`.

## Checks

Unit tests cover the switch, a new coach, a good offense, a stubborn coach and the side
rule. Per Ron's standing instruction there is no dynasty testing yet, so this has not been
run across real dynasty seasons; how often it fires there is unmeasured.

## Left for later

The site does not yet show school changes on program or coaching pages. Hiring a coordinator
from the new system to lead the change, as Saban did, is not modeled.
