# Playbook catalog

The PLAYBOOK track of the coach and playbook plan (docs PR #324,
`PRD_COACH_OWNED_SCHEMES_AND_PLAYBOOKS_2026-11-23.md`): a catalog of the sport's scheme
families and the packages teams can install from them. The catalog describes what can be
installed and when. It runs no engine logic; the COACH track decides what a team installs
and calls.

- Data: `data/playbooks/vocabulary.json`, `families.json`, `packages.json`
- Loader and validator: `engine/playbook_catalog.py`
- Tests: `tests/test_playbook_catalog.py`
- Current inventory: [INVENTORY.md](INVENTORY.md); regenerate the detailed runtime inventory with `python -m engine.playbook_catalog`

## Families and packages

A family is one of the engine's 16 offensive styles or 10 defensive schemes, under its
existing slug. A family record joins the engine's own numbers (top play types, formation
mix, kick pass mix, best and worst matchups, a defense's ratings) with catalog notes: its
identity, the situations it is built for, the roster it needs, its signature fields in the
engine, and what travels when another team borrows from it.

A package starts in one family (`origin_family`) and lists every family that can install it
(`compatible_families`). That is how a coach running one book uses plays from another: an
East Coast team can install Ground Control's Heavy Push for short yardage, and a Fortress
defense can install Lockdown's Kick Range Shell. Each package carries the fields from the
PRD's package example (formation, play family, kick pass, personnel and situation tags, what
counters it, its tradeoffs) plus plain text for its inspiration, scenario, benefits, cost
and counter.

## Where the packages come from

Every sport Ron named keeps a base system and saves called plays for set moments:

- **AFL**: set plays mostly from kick-ins and center bounces, where players have time to
  set up, and abandoned when play breaks down. Packages: Kick-In Breakout, Restart Go-To,
  Kick-In Press, Launch Pad Kick Set, Kick Range Shell. Sources: [AFL.com.au on set
  plays](https://www.afl.com.au/news/1286686/all-set-the-pre-planned-plays-starting-to-gain-traction),
  [AFL.com.au on kick-ins](https://www.afl.com.au/news/1130107/mission-impossible-the-art-and-science-of-kick-ins).
- **Rugby union**: a playbook of first phase moves from lineouts and scrums, raided near
  the line, then phase play by shape. Package: First Phase Strike. Source: [World
  Rugby](https://www.world.rugby/news/505490).
- **Rugby league**: patterns across a set of six, and an attacking kick on the last tackle.
  Packages: Last Tackle Kick, Rush Line. Source: [The Roar on league
  patterns](https://www.theroar.com.au/?p=1298568).
- **Lacrosse**: several offensive sets, transition off turnovers, the ride after losing the
  ball, extra man offense. Packages: Fast Break, Ride, Extra Attacker. Sources: [Lacrosse
  Unlimited on offensive
  sets](https://www.lacrosseunlimited.com/blogs/the-scoop/coaching-101-offensive-sets),
  [Wikipedia, lacrosse strategy](https://en.wikipedia.org/wiki/Lacrosse_strategy).
- **Gridiron football**: short yardage, goal line, four minute, two minute and prevent
  packages, which Viperball's six downs and kicking game already support.

## Rules the validator enforces

- Every engine family has a record and every record is an engine family.
- IDs are the engine's: family slugs, `PlayFamily` values, the four formations, the four
  `KickPassSubFamily` values. Possession ending kicks (snap kick, field goal, punt) and
  kneels are rule gated decisions and cannot be package content.
- A package's origin can install it; Balanced has no identity of its own and is never an
  origin.
- Kick pass tags need the kick pass play family; offensive packages need a formation.
- Situations and personnel tags come from `vocabulary.json`; counters must be families or
  packages of the other side.
- Every package names a scenario, benefits, a cost, a counter and at least one tradeoff.
- Lookups return copies, so callers cannot change the catalog.

## Roster fit (PBK-04)

`packages_for_roster(side, scheme_id, team_stats)` lists every package a family can install
and whether a roster meets its personnel needs, reading the `team_stats` block that
`engine/ai_coach.py` already uses for scheme assignment. Across the 205 team files, the
share of teams that can run each package ranges from 21% (Vertical Shot: elite kicking and
speed) to 100% (Two Minute Chain, Prevent, Long Yardage Bracket). Choosing and saving
packages is the COACH track's job.

## Handoff notes for the COACH track

The COACH agent owns runtime wiring. Two things from the PR #329 prototype (now a draft
reference) bear on it:

1. **Systems stay home.** In #329, a borrowed call took its book's play design whole and got
   half its book's execution bonuses; the home book kept tempo, conditioning and signature
   mechanics. Packages whose payoff is a system did worse when borrowed: Boot Raid calls on
   the Launch Pad (3.84 yards against 4.27 for home calls over 360 games), and Stampede and
   Slick 'n Slide calls on early downs (about a yard a play worse). Packages that are only
   play design did better: borrowed long yardage calls gained 5.35 yards against 4.94. Each
   family's `travels` note says what does not travel.
2. **Defense situations from ratings.** A defensive package's situations should come from
   the scheme's own ratings, which `get_scheme_family("defense", ...)["strong_in"]` reads.
   Writing them from scheme descriptions put Blitz Pack on long yardage, where its own
   rating (1.20) says it is weak.

Situations `first_play_of_drive`, `after_takeaway` and `after_score_restart` need the
engine to report how a drive started; the vocabulary defines them so a resolver can use
them once that exists.
