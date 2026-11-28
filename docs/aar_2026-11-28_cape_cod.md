# AAR: Cape Cod offensive hook and defensive trap

November 28, 2026

## What was asked

Ron described a coach's concept called the Cape Cod: a peninsula with a hook and a narrow
neck, used on offense to pull a lateral chain to the sideline and hook back inside, and on
defense to trap the chain against the sideline and choke the cutback. He asked for it to
be built now, with the defensive half as the first of the cross sport defensive answers.

## Engine limits that shaped it

The engine has no sideline or hash position. It has a left or right lane on a planned
call and the defense's pre-snap front and blitz. Both halves use those.

## What changed

1. Catalog (`data/playbooks/packages.json`)
   * `cape_cod_hook`, offense, from Lateral Spread; also Chain Gang, Slick 'n Slide and
     Stampede. Early down and drive building situations.
   * `cape_cod_trap`, defense, from Swarm; also Shadow and Chaos. Early down.
2. Offense (`engine/offensive_concepts.py`, `cape_cod_call`). The setup is a lateral chain
   toward one lane. After one setup, an aggressive or spread front or a blitz gets the hook,
   a counter run on the other side. A stacked front gets a territory kick across the field.
   A balanced front sees another setup. The setup records the front and blitz it drew, and
   lateral chains now count as setups.
3. Defense (`engine/game_engine.py`, `engine/defensive_commitments.py`). Primary on early
   downs when the opponent's recent lateral plus perimeter rate is at least 25 percent,
   secondary at 20 percent. Spread posture. It takes yards away from lateral chains, sweeps,
   speed options and counters, and concedes yards to power, dive and draw. Each later
   lateral in a chain is more likely to be intercepted, and the chain's fumble chance rises
   with its length. Quick kicks gain completion chance against it and territory kicks lose
   some. It counts as a coverage package.
4. README rules record and `tests/test_cape_cod.py`.

## Effect over three weeks with every team on a Cape Cod book

| Call | Snaps | Yards per play |
|---|---|---|
| Hook setup, no trap | 1,229 | 2.77 |
| Hook, no trap | 270 | 8.22 |
| Kick across, no trap | 74 | 8.12 |
| Hook setup into the trap | 41 | 1.85 |
| Hook into the trap | 18 | 4.94 |

Against the trap, lateral chains averaged 1.70 yards (2.86 with no package), speed options
2.65 (4.57) and counters 5.11 (6.00). 18 of 70 lateral chains into the trap ended in an
interception or fumble. Power and dive also averaged less against the trap in this sample
(3.60 and 2.95 against 4.71 and 4.26), so the intended inside concession did not show at
this sample size and needs a larger run.

## Checks

New tests, catalog, box score ledger and custom playbook tests pass. The full suite was not
run, at Ron's request.
