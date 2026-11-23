# AAR: Coach playbooks
## November 23, 2026

## What Ron asked

Coaches should use plays from other playbooks instead of sticking to one book. Check what
other sports do (AFL, rugby, lacrosse), and check what has landed on every branch first.

## Branches checked

| Branch | PR | What it holds |
|---|---|---|
| claude/fix-league-hub-null-status | #323 | This session's work through lines in the app (a1f39c0) |
| fix/defensive-tactics-def-01-02-03 | #325 | Another agent: defensive reads, scheme matchups, formation read fix, built on #323 at ad6551f |
| analysis/def-06-full-matchup-matrix | #326 | Another agent: defense matchup study on top of #325 (scripts and tests only) |
| docs/engine-assessment-work-queue-2026-11-23 | #324 | Another agent: assessment and work queue, from main |

No branch had playbook work. #325 merges into this work cleanly, so `claude/coach-playbooks`
starts from #323's head with #325 merged in.

## How other sports do it

- AFL: called set plays mostly at kick-ins and center bounces, where players have time to
  set up; otherwise teams play to structures and abandon plays when the game breaks down.
- Rugby union: teams keep a playbook of first phase moves from lineouts and scrums, raided
  near the line, then play phases by shape.
- Rugby league: patterns and shapes across a set of six, with set moves off scrums and
  penalties.
- Lacrosse: a few offensive sets (2-3-1, 1-4-1, 2-2-2), and teams learn several and switch.

The common thread is a base system plus a short list of called packages for set moments.

## Before

- Each team had one offensive style and one defensive scheme, and every play came from them.
- Five of the sixteen offensive books (Six Shooter, Quick Strike, Mousetrap, Mismatch,
  Ironclad) were missing from `PHILOSOPHY_TO_OFFENSE`, so no AI team ever got them.
- `auto_assign_all_teams` seeded each team with Python's `hash()`, which is salted per
  process, so scheme assignments changed every run (part of work queue VAL-02).

## Changes

**`engine/playbooks.py` (new)**
- `build_playbook`: one to three borrowed books, mostly ones the roster suits. Total share of
  calls is 5% plus 40% times the staff's appetite.
- `borrow_appetite`: from the coordinator's adaptability minus stubbornness, head coach at a
  third, with noise. Teams with no staff roll it.
- `situation_tags`: short yardage, goal line, long yardage, Launch Pad, kick range, downs 4
  to 6, protecting a lead, chasing, two minute drill; the engine adds tired defense.
- `choose_call`: picks the book for this play. A borrowed book is weighted 2.5 times its
  share in its own situation and 0.6 outside it, then scaled by how well it matches this
  opponent (from `OFFENSE_VS_DEFENSE_MATCHUP`).
- `merged_offense`: a borrowed call takes the book's play types, kick pass mix, formation mix
  and situational modes whole; the home book keeps tempo, conditioning and signature
  mechanics; execution bonuses are half the borrowed book's.
- `merged_defense`: a borrowed package takes its personnel, rush and situational settings
  whole and plays halfway between the home scheme and the package on effectiveness.
- `defense_package_situations`: where each scheme's own ratings in `DEFENSE_STYLES` say it is
  strong. My first list came from the scheme descriptions and had Blitz Pack on long
  yardage, where its own rating (1.20) says it is weak; the derived list fixes that.

**`engine/game_engine.py`**
- `Team.offense_playbook`, `Team.defense_playbook`; `Play.call_book`, `Play.def_call`.
- `_setup_playbooks` (derives a stable playbook when a team has none), `_make_play_calls`
  before each normal play, `_tag_play_call` (play by play tags like "[Boot Raid play]" and
  "[vs Fortress package]").
- `_current_style`, `_current_defense` and `_current_defense_name` return the called book.
  The scheme matchup (#325's `_defense_style_multiplier`) and formation matchup now read the
  called book and package instead of the team's home scheme.
- `game_day.playbook` in each result: home books, playbooks and call counts.
- `playbooks_enabled` switch for paired tests.

**`engine/ai_coach.py`**: every AI team gets an offense and defense playbook; the five
missing books join the philosophy lists; labels come from the style tables; team seeds use
`zlib.crc32`. Same seed now gives the same assignments under different hash seeds.

**`engine/season.py`**: playbooks travel with each team's scheme config into games.

**API and app**: `playbook` on both team roster endpoints (home books, borrowed books with
shares and when each is called, season call totals). New Playbook tab on the team page.
Box score rows for plays from other books and defensive packages.

**README**: new Coach Playbooks section.

## Measurements (PYTHONHASHSEED=0, fresh rosters, season schemes)

Benchmark, 300 games:

| Version | Points per team | Touchdowns | Snap kicks | Field goals |
|---|---|---|---|---|
| #323 head | 57.95 | 3.51 | 3.25 | 1.85 |
| #325 head | 53.59 | 2.88 | 3.25 | 2.12 |
| This branch, playbooks off | 53.69 | 2.86 | 3.35 | 2.12 |
| This branch, playbooks on | 52.77 | 2.75 | 3.37 | 2.09 |

#325's defensive wiring accounts for 4.4 of the points; playbooks cost about one more.
All inside the README ranges.

360 games: the middle team calls 24% of offensive plays and 31% of defensive snaps from
other books (10th to 90th percentile: 9% to 44% offense, 12% to 51% defense).

Situation results, 360 games, yards per play with 95% ranges:

| Situation | Home call | Borrowed call |
|---|---|---|
| Long yardage, offense | 4.94 ±0.10 | 5.35 ±0.26 |
| Launch Pad, offense | 4.27 ±0.15 | 3.84 ±0.43 |
| Goal line, offense | 2.31 ±0.13 | 2.73 ±0.49 |
| Chasing, defense (yards allowed) | 5.27 ±0.24 | 5.84 ±0.54 |
| Long yardage, defense | 4.98 ±0.11 | 4.99 ±0.21 |

Other splits overlap. Borrowed long yardage calls clearly gain more; borrowed Boot Raid and
Six Shooter plays on the Launch Pad gain a little less, because Boot Raid's Launch Pad payoff
is its kicking system, which stays home; gambling packages give up more yards when chasing.

One change made from the data: Stampede and Slick 'n Slide packages were first called on
early downs. Over 1,154 plays they gained 3.36 yards against 4.25 for home calls, because
both books win through systems that stay home (tempo, reads). Stampede is now called against
a tired defense (on field defenders under 75 energy) and Slick 'n Slide on matchups.

Full season, seed 2026, 1,231 games: 52.7 points per team, home 48.5%, lower prestige wins
35.3%, median margin 19.5, 30 point margins 24%.

Tests: 94 pass (8 new in `tests/test_playbooks.py`).

## Findings for the work queue

- Defensive schemes rated strong in short yardage (Fortress 0.70, Blitz Pack 0.80, Chaos
  0.85) do not hold short yardage gains below other schemes in these runs. The
  `short_yardage_modifier` may not reach the yardage roll the way its value suggests.
- VAL-02: `auto_assign_all_teams` is now stable across processes. The season roster loader's
  unsorted file order is still open.

## Open

- Coaches do not yet learn in game which borrowed packages are working.
- A human coach cannot edit the playbook in the app yet; the tab shows it.
