# AAR — WVL rebuilt as a CVL-graduate career league (2026-06-13)

## Problem

The SPA shipped a "WVL" that was a generic 4-tier sim league (create →
multi-tier standings with promotion/relegation → sim). The owner was blunt
that this was useless: *"your basic sim league is not useful to me."* WVL has
exactly one purpose for them:

> "the idea is that i want a pro league for the CVL players to continue their
> careers, porting the cards over into the game... they stay the same, you
> don't create a new player for those CVL players — they get imported and
> their careers persist, which is key. I want a full sim that can use the real
> engine, that simulates game by game not season after season, and track their
> careers not as a one-shot."

So the rebuild had to deliver four things the old version didn't: **import the
same player cards** (not generate new players), **full real-engine game-by-game
sim**, **persistent multi-season careers**, and a UI to **watch those careers**.

## What was already there (and reused)

- **The CVL→WVL bridge.** `engine/db.py` already had
  `save_graduating_pool` / `load_graduating_pools` / `consume_graduating_pool`,
  and CVL dynasty already auto-publishes a graduate pool on graduation. That
  pipeline existed but nothing user-facing consumed it the way the owner wanted.
- **PlayerCard carries its own career.** `PlayerCard.career_seasons:
  List[SeasonStats]` plus `get_or_create_season()` means "careers persist" is
  literally just *keep the same card object and append a season to it.* No new
  tracking system was needed — the card **is** the career.
- **The real engine runs fine on persistent rosters.** `ProLeagueSeason`
  already reuses the same `Team`/`Player` objects across games and reads each
  game's production from `result["player_stats"]`. I followed that exact pattern
  rather than reading per-game counters off the player objects.
- **Club rosters exist on disk.** `data/wvl_teams/tier1/*.json` load via
  `load_team_from_json` into full 36-player Teams, so clubs have a real roster
  to field with CVL imports spliced in.

## What was built

`engine/wvl_career.py` — `WVLCareerLeague`:

- **One league, the 18-club Galactic Premiership** (Tier 1). A single strong
  pro league is the right shape for "watch my college players' pro careers";
  multi-tier pro/rel was noise.
- **Import = same card.** `import_graduates()` pulls unconsumed bridge pools,
  rebuilds each `PlayerCard` from its dict, keeps it in `self.cards` keyed by
  `player_id` (the source of truth), distributes imports to clubs by prestige
  (stars to big clubs), and **splices the card onto the club's game Team** by
  replacing the weakest filler 1:1 so roster size stays at 36 and imports
  actually play.
- **Full-engine game-by-game.** `sim_week()` runs `ViperballEngine(...).
  simulate_game()` on each matchup (round-robin schedule via the circle
  method), records standings, and `_accumulate()` appends each tracked card's
  line to its `SeasonStats` for the current year.
- **Careers persist across seasons.** `advance_season()` files the season into
  history, ages every card, retires those past 34 (keeping their history),
  imports the new CVL class, and starts the next year — the same card now has
  N career seasons.
- **Durable.** `to_dict`/`from_dict` serialize only the durable state (cards,
  rosters, standings, results, history); Teams/schedule rebuild deterministically
  on load. Persisted via `save_blob("wvl_career_league", ...)`, so leagues
  survive restarts/deploys. `wvl_sessions` is now just an in-memory cache.

`api/main.py` — replaced the old multi-tier endpoints with the career-league
API: `new / active / status / standings / schedule / players / player/{id} /
leaders / history / roster/{club} / sim-week / sim-all / advance-season /
import-graduates / graduate-pools`.

`web/` — rebuilt `WVLIndex` (create/list leagues, surface importable CVL
classes) and `WVLHub` (Standings, **Careers**, Leaders, Schedule, History,
season controls, and a **player career modal** that shows the same card's
CVL + WVL seasons side by side, league-tagged).

## Verification (before commit)

Ran the engine module standalone and the API via `TestClient`:

- 18 clubs load, 17-week round-robin, 9 full-engine games/week (~0.7s/week).
- A tracked card accumulated a full season (e.g. 17 G, ~5.6k yds) from real
  game output.
- Persist → reload preserved careers exactly.
- `advance_season()` carried the **same player** forward: career_seasons went
  `[2027]` → `[2027, 2028]`, confirming "careers persist, not a one-shot."
- All 15 endpoints returned 200 end-to-end (new → sim-week → standings →
  players → player detail → leaders → schedule → roster → sim-all → advance).
- `web` build (`tsc -b && vite build`) is green.

## Bugs found & fixed during the build

- **Double-counted stats in the synthetic-seed path.** The empty-league
  bootstrap created cards from existing filler players that *stayed* on the
  roster, so both the original and the card duplicate matched by name and
  stats counted twice. Fixed by sourcing synthetic cards from the *weakest*
  fillers — exactly the ones the splice step drops — so each card replaces its
  source 1:1 with no name collision, and routing the seed through the same
  `setup_season()` splice as real imports (so persistence round-trips identically).
- Removed dead code in the roster-splice helper (`_ovr`, unused `replace_n`).

## Notes / boundaries

- Synthetic seeding only fires when **no** real CVL class exists yet, purely so
  a fresh league isn't empty to explore. Real usage: graduate a CVL dynasty
  class, then the WVL imports those exact cards.
- Career tracking is intentionally scoped to imported CVL cards (the owner's
  whole interest). The clubs' generated filler women fill out the field and
  drive standings but don't carry persistent careers.
- `sim-all` blocks ~11s for a 153-game season; acceptable, and the primary
  flow is week-by-week. If it ever grates, move it to a background task.
- The legacy `WVLMultiTierSeason` engine class is untouched (still used by the
  NiceGUI/stats paths); only the SPA's API surface switched.
