# Plan: Career Archive / Hall of Fame + International Game Integration

## Goal
Let users follow college players after graduation — see their full career arc
(college stats, international play, retirement) on the stats site. Wire the
existing international/pro league system so it can use CVL graduates as rosters,
and show those accomplishments on college player pages.

---

## Phase 1: Career Archive on the Stats Site

The infrastructure already exists but isn't surfaced:
- `Dynasty._publish_graduates_to_bridge()` writes graduates to DB
- `PlayerCareerTracker` can ingest graduates and record pro/international seasons
- `PlayerCard.career_seasons` and `career_awards` already render in the college
  player template

### 1a. Add a "Hall of Fame / Alumni" page to the college stats site

**New route:** `/stats/college/{session_id}/alumni`

- Pull all graduated players from the dynasty's history
  (dynasty stores completed seasons with full rosters)
- Show a sortable table: Name, Position, Team, Years Active, Career Yards,
  Career TDs, Awards, Peak Overall
- Link each player to a detailed alumni profile page

### 1b. Add individual alumni profile pages

**New route:** `/stats/college/{session_id}/alumni/{player_name}`

- Show full college career: season-by-season stats from `career_seasons`
- Awards section from `career_awards`
- Attributes at graduation (peak ratings)
- If the player went on to play internationally (Phase 2), show that too
- Bio: hometown, nationality, position, draft class year

### 1c. Wire dynasty graduation into PlayerCareerTracker

- `Dynasty.advance_season()` already calls `_publish_graduates_to_bridge()`
- Add: also feed graduates into a `PlayerCareerTracker` stored on the dynasty
- This tracker persists across seasons and accumulates career data
- Save/restore with dynasty DB serialization

---

## Phase 2: International Game Using CVL Graduates

Rather than fixing WVL, create a lighter "International Tournament" mode that
pulls from college graduates. This is closer to the existing Champions League
pattern but uses player rosters built from CVL graduates.

### 2a. "All-Star International" tournament creator

After a dynasty has graduated players (1+ completed seasons), allow creating
an international tournament:

- Group graduates by `nationality` (already on PlayerCard)
- Form national teams (e.g., "USA", "Japan", "Nigeria") from available graduates
- Fill out small rosters (15-20 per nation) from the graduate pool
- Use the existing `ProLeagueSeason` engine for simulation (round-robin + playoff)

### 2b. Wire international results back to career tracker

- After the international tournament completes, call
  `PlayerCareerTracker.record_fiv_cycle()` with player stats
- This populates `international_seasons`, `international_caps`, `national_team`
- These show up on the alumni profile page from Phase 1b

### 2c. Stats site integration for international tournaments

- Add routes under `/stats/college/{session_id}/international/` for the
  tournament standings, schedule, box scores
- Reuse existing pro league templates (they already handle `ProLeagueSeason`)
- Link back to alumni profiles for each player

### 2d. Show international accomplishments on college player pages

- On the existing `/stats/college/{session_id}/player/{team}/{name}` page,
  add an "International Career" section if the player has international data
- Show: national team, caps, tournament stats, career international yards/TDs

---

## What already exists (no new engine work needed)

- `ProLeagueSeason` — can simulate any tournament given teams + config
- `PlayerCareerTracker` — tracks college → pro → international phases
- `save_graduating_pool()` / `load_graduating_pools()` — bridge DB
- `Dynasty._publish_graduates_to_bridge()` — exports graduates
- College player template already has career_seasons and career_awards sections
- Stats site has full pro league templates that can be reused

## What needs to be built

1. Alumni list page + template (Phase 1a)
2. Alumni profile page + template (Phase 1b)
3. PlayerCareerTracker integration with Dynasty (Phase 1c)
4. National team builder from graduate pool (Phase 2a)
5. International tournament session management in API (Phase 2a)
6. Career tracker recording after tournament (Phase 2b)
7. Stats site routes for international tournament (Phase 2c)
8. Cross-linking between college player pages and international data (Phase 2d)

## Suggested order

Start with Phase 1 (career archive) since it's self-contained and immediately
useful. Phase 2 builds on it by giving graduates somewhere to play after college.
