# AAR: the rest of the cross code books and their defensive answers

November 28, 2026

## What was asked

Ron asked for the rest of the cross sport plays and the defensive answers D01 to D08 from
`docs/master_coaching_clinic_cross_code_2026-11-27.md` to be built, beyond Cape Cod, and put
on the site.

## What was already built, and counts as the clinic call

| Clinic call | Existing package |
|---|---|
| FM04 Third Runner | Third Runner (clinic phase 1) |
| PH01 Pod Carry | Pod Two |
| PH02 Same Side Reload | Third Strike, nearest match |
| PH04 Open Edge | Edge Three |
| PH06 Finish Read | Launch Option and the existing kick decision |
| RL03 Anchor Switch | Corridor Switch |
| RL04 Lead and Crumb | Viper Trail; no new live muff rule |
| TT01 to TT05 | Kick-In Breakout, Fast Break, Pindown Chase and Territory Exit, Bonus Guard, Advantage Entry |

## What was built

New module `engine/cross_code.py`, wired into `engine/game_engine.py`,
`engine/defensive_commitments.py` and the catalog (`data/playbooks/packages.json`).

**How an offensive call runs.** The caller picks the package before the snap, as for every
package. After the defense sets, the engine builds a look from what the offense can see: the
front, how many defenders the field width split put on each side, and a blitz the Zeroback
may or may not recognize (his awareness decides). For the calls that need it, the post snap
read is a contest between the actual players. The design decides the family, the side and
who carries, kicks or receives. The existing resolvers play it out. Nothing adds yards; a
defender who followed the wrong man or a decoy is taken out of his side's count, so field
width's numbers formula and the tackler pick do the rest. A call with no look to act on hands
the snap back to the normal selector.

Shared pieces added to the resolvers:
* a named carrier on runs, ahead of the option read;
* a named distributor and named receivers on kick passes;
* a named order of handlers on lateral chains, where the weakest pair of hands sets the
  fumble risk;
* an ordered second lateral after a kick catch;
* a marked defender for the kick pass contest, and a trailing penalty for a defender who
  missed a switch.

Offense, 15 calls:
* Free Motion: Switchback (FM01), Twin Trigger (FM02), False Lead (FM03), Anchor Release
  (FM05), Mirror Flood (FM06).
* Phase Attack: Pullback (PH03), Short Side Strike (PH05).
* Relay: Wall Return (RL01), Up Back Across (RL02), Safe Outlet (RL05).
* Crossfire: Slip Cross (CF01), Pivot Turn (CF02), Double Clear (CF03), Handoff Punish
  (CF04), Same Look Reverse (CF05).

FM02 and FM05 were level C in the clinic. Twin Trigger changes the actual snap recipient:
the Halfback carries or kicks with his own ratings, and a bad snap (more likely with weaker
hands) loses ground and can come loose. Anchor Release puts a real lineman in the lateral
chain with his own hands.

Defense, 8 answers:
* D01 Exchange: a switch contest on every cross, helped by practice; it bites on fakes.
* D02 Stagger: the second runner after a catch or a first lateral is picked off more often.
* D03 Edge Anchor: one box defender moves to the weak edge and is the likely tackler there.
* D04 Slide and Replace: a help tackle contest on runs past 10 yards; the helper gets the
  tackle in place of the beaten defender and pays the energy.
* D05 Channel Press: more rushers and a box defender moved to the wide side.
* D06 Transition Net: a standing assignment, not a snap call. Interception returns against
  the team are 30 percent shorter at full practice, its live line changes are caught half as
  often, and its own returns are 10 percent shorter.
* D07 Cross Rush: a pass off contest between the two lead rushers and two blockers. A clean
  pass off makes the rush late; a missed one makes it stronger.
* D08 Set Breaker: predicts the next family from what the offense ran after the same family
  earlier in the game (three samples at least) and commits to it on later downs.

The defensive triggers read new observations from the plays the defense has seen: crosses,
second runners and runs back to the weak side, plus the formation for Channel Press.

**Site.** The Playbooks page groups the new calls as Free Motion, Phase Attack, Relay,
Crossfire and Cross code answers (built on #417's groups). The college game page has a Cross
code calls table with each call's branches and what each defensive answer did. The package
inventory (`docs/playbook_packages/INVENTORY.md`) is regenerated. The README describes every
call.

**Not done.** The clinic's new schools (Free Motion, Phase Attack, Relay, Crossfire as
schools of their own) are not activated; the calls ship as packages for existing schools.
Previews on the Playbooks page were the generic ones for each family at first; each call
now has its own drawing (`aar_2026-11-28_cross_code_previews.md`).

## Study

`scripts/study_cross_code.py --games 20`. Offense: the call's origin school with only that
package installed at full practice, against defenses that are not its listed counters.
"Base" is the same team's other snaps in those games.

| Call | Snaps | Yards per snap | Turnover rate | Base yards | Branches (snaps at yards per snap) |
|---|---|---|---|---|---|
| Switchback | 785 | 5.48 | 2.2% | 5.22 | vacated pitch 111 at 8.28, vacated kick 281 at 5.62, switched outlet 198 at 5.38, switched keep 195 at 3.77 |
| Twin Trigger | 802 | 4.47 | 3.0% | 5.83 | carry 181 at 5.45, kick 578 at 4.34, bad snap 13 at -1.62 |
| False Lead | 910 | 5.23 | 2.2% | 4.89 | counter 584 at 5.27, seam kick 326 at 5.16 |
| Anchor Release | 883 | 4.29 | 2.6% | 4.87 | protect 707 at 4.80, release 176 at 2.25 |
| Mirror Flood | 714 | 6.70 | 4.1% | 4.17 | flood 484 at 6.92, weak isolation 230 at 6.23 |
| Pullback | 787 | 5.01 | 5.2% | 5.14 | kick 522 at 5.76, secure 182 at 3.44, pullback 83 at 3.71 |
| Short Side Strike | 922 | 4.61 | 2.6% | 4.71 | pitch 49 at 8.00, sweep 408 at 4.96, handed back 465 at 3.94 |
| Wall Return | 843 | 3.85 | 6.3% | 4.88 | keep 445 at 4.19, return 398 at 3.47 |
| Up Back Across | 658 | 5.18 | 6.4% | 4.68 | one branch |
| Safe Outlet | 692 | 5.72 | 3.2% | 5.18 | kick 255 at 6.04, pitch 49 at 7.22, handed back 388 at 5.31 |
| Slip Cross | 787 | 5.02 | 2.9% | 5.34 | slip 385 at 6.22, switched inside 402 at 3.88 |
| Pivot Turn | 951 | 5.09 | 0.9% | 5.06 | pivot 526 at 5.25, keep 425 at 4.89 |
| Double Clear | 781 | 6.91 | 1.7% | 4.79 | seam 517 at 7.27, kick 264 at 6.19 |
| Handoff Punish | 479 | 6.68 | 3.5% | 4.38 | punish 300 at 7.49, handed back 179 at 5.32 |
| Same Look Reverse | 922 | 4.77 | 1.0% | 5.17 | look 524 at 4.11, reverse 398 at 5.63 |

Handoff Punish was studied with Slip Cross installed too, since it needs earlier switches.

The reads point the right way where they should: the vacated pitch beats the switched keep,
the slip beats the switched run, the reverse beats the look. The branches built on a real
lateral chain (Anchor Release, Pullback, Wall Return's return) are weak, because lateral
chains in this engine average about 3 yards with a high fumble rate. Single pitches behind the
line are played as option pitches on edge runs, the way the engine already plays them.

Defense: paired games with the same teams, staffs, weather and seeds, with the answer
installed at full practice or not, against an offense running the call it answers.

| Answer | Against | Target yards per snap | Offense points per game | What it did |
|---|---|---|---|---|
| Exchange | Switchback | 4.85 to 4.24 | 48.6 to 39.1 | 562 switches, 155 misses |
| Stagger | Up Back Across | 4.63 to 3.44 | 40.1 to 35.9 | 112 second runners covered |
| Edge Anchor | Cape Cod hook | 3.10 to 2.69 | 24.3 to 20.0 | 299 anchors set |
| Slide and Replace | Pivot Turn | 4.22 to 4.82 | 46.3 to 49.4 | 25 help stops, 17 misses |
| Channel Press | Mirror Flood | 7.39 to 7.86 | 59.3 to 56.0 | 788 presses |
| Transition Net | Wall Return | 3.43 to 3.39 | 37.7 to 36.8 | 45 returns covered, 51 own returns held back |
| Cross Rush | Handoff Punish | 5.64 to 5.81 | 41.8 to 48.2 | 48 passed off, 50 came free |
| Set Breaker | Same Look Reverse | 4.56 to 4.59 | 40.3 to 38.3 | called on 531 snaps |

Exchange, Stagger and Edge Anchor take their target away. Slide and Replace, Channel Press and
Cross Rush do not in this sample: the costs (a thinner far side, a lighter box, a late rush on
a clean pass off) outweigh what they take away from these targets. Twenty games per arm
carries several points of noise on points per game. Nothing was tuned to make an answer win.

## Checks

New `tests/test_cross_code.py` (catalog and schools, every branch family listed in its
package, the switch contest, memory, fallbacks, Set Breaker's prediction, triggers, the
channel move, and full games with offensive calls and defensive answers). Catalog, Cape Cod,
clinic, Delta, custom playbook, offensive concept, package execution, defensive tactics,
field width, reproducibility, rules doc and box score ledger tests pass. The Playbooks page
was checked in Chrome: the new groups show for Ghost, East Coast and Blitz Pack with no
script errors. The full suite was not run locally, at Ron's request; CI runs it.
