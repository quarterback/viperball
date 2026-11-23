# AAR: Playbook catalog (PBK-01, PBK-02, PBK-04)
## November 23, 2026

## What Ron asked

Work on the coach playbooks section, so coaches can use plays from other playbooks instead of
sticking to one book. Look at what AFL, rugby and lacrosse do. Check every branch first.

## What the branches showed

During this run another agent added a coach and playbook plan to docs PR #324
(`PRD_COACH_OWNED_SCHEMES_AND_PLAYBOOKS_2026-11-23.md`) and opened CCH-01 (#327) and CCH-02
(#328) for the COACH track. The plan gives runtime wiring and team installation to the COACH
track and a package catalog in new files to the PLAYBOOK track. My first build (#329) had
wired borrowing into `game_engine.py`, `ai_coach.py` and `season.py`, which collides with
#328. Ron chose to follow the split: #329 became a draft reference and this branch, from
main, touches only PLAYBOOK files.

## What was built

| Item | Files |
|---|---|
| PBK-01 inventory and validation | `engine/playbook_catalog.py`, `data/playbooks/vocabulary.json`, `data/playbooks/families.json`, `docs/playbook_packages/INVENTORY.md` |
| PBK-02 package library | `data/playbooks/packages.json`: 14 offensive and 9 defensive packages |
| PBK-04 roster fit | `roster_tags`, `packages_for_roster` |
| Docs | `docs/playbook_packages/README.md`; out of date note on `docs/VIPERBALL_PLAYBOOK_DEVELOPMENT_BASELINE.md` |
| Tests | `tests/test_playbook_catalog.py`: 20 tests |

- Family records for all 16 offenses and 8 defenses, joined with the engine's own numbers.
  Defensive strengths are read from each scheme's ratings.
- Packages from seven offensive origins (Ground & Pound, Ironclad, Boot Raid, Shock & Awe,
  East Coast, Chain Gang, Ghost, Slick 'n Slide, Six Shooter, Quick Strike, Stampede) and
  five defensive origins (Fortress, Lockdown, Drift, Blitz Pack, Predator, Chaos). Most can
  be installed by several other families, which is the borrowing Ron described.
- AFL, rugby union, rugby league and lacrosse inspired packages: Kick-In Breakout, Restart
  Go-To, Kick-In Press, First Phase Strike, Last Tackle Kick, Rush Line, Fast Break, Ride,
  Extra Attacker.
- The plan's three lookup functions (`get_scheme_family`, `get_package`,
  `list_compatible_packages`), using the engine's slugs and IDs with no aliases.

## Checks

- The validator caught two of my own packages naming a kick pass type without the kick pass
  play family (Four Minute Grind, Chase Chain); fixed.
- 92 tests pass on this branch (72 on main plus 20 new). No engine file changed.
- Roster fit across the 205 team files: 21% of teams can run Vertical Shot, 27% Goal Line
  Stand, 44% the kicking packages, 46% the power packages, 100% the packages with no needs.

## For the COACH track

See the handoff notes in `docs/playbook_packages/README.md`: from the #329 prototype,
borrowed packages that are only play design did better (long yardage, 5.35 against 4.94
yards a play), packages whose payoff is a home system did worse (Boot Raid on the Launch Pad,
3.84 against 4.27), and defense situations should come from scheme ratings. Three situations
(`first_play_of_drive`, `after_takeaway`, `after_score_restart`) need the engine to report
how a drive started.

## Open

- PBK-03 (new families) is not needed yet: every package here fits an existing family.
- Player level personnel tags (a fast Viper, a deep defensive line) wait for one rating scale
  across team files and fresh rosters.
