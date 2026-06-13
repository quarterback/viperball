# AAR: Recruiting Disconnect, In-App Editor, and Geography
## Viperball college editor / recruiting — June 13, 2026

Covers: the college editor (teams/players), the recruiting-flow disconnect between the `/stats`
site and the core game, the fix (in-app recruit editor + assignment, `/stats` recruiting
deprecated), and the geography question. Continues `AAR_2026-06-13_ui_parity_and_fixes.md`.

---

## 1. The asks
- A **college editor**: rename teams; edit player names/attributes; move/add players anywhere.
- **Edit recruits**, not just add players; assign recruits/players wherever.
- Fix a **broken recruiting flow**: `/stats` had a recruiting flow disconnected from the core
  game. Owner clarified it "was just meant to give me an editor and it ended up recreating the
  flow, so that ought to be deprecated."
- Does the game know where college teams are located geographically?

---

## 2. Geography — yes, the game knows
- Each team JSON (`data/teams/*.json`) has `team_info.city` / `state` / `conference`, plus a
  `recruiting_pipeline` map of region weights (e.g. Alabama: south 0.45, west_coast 0.17, …).
- `engine/geography.py` defines `REGION_MAP` (state → region) and
  `get_geographic_conference_defaults()` (used when the owner doesn't hand-set conferences).
- Recruits carry a `region`, and team pipelines skew generation toward preferred regions. So
  team location and region-weighted recruiting are real, first-class data.

---

## 3. The problem — a dual-pool recruiting disconnect

There were **two recruiting pools that never reconciled**:

- **Core game (per session):** dynasty offseason builds `session["offseason"]["recruit_pool"]`;
  `…/offseason/recruiting/{scout,offer,resolve}` operate on it; `resolve()` sets
  `dynasty._pending_signed_recruits`; `offseason/complete` promotes those to PlayerCards on
  rosters (`api/main.py`).
- **`/stats` hub (global):** `stats_site/router.py:_get_recruit_pool()` reads a *different*
  source — `dynasty._last_recruit_pool` or a separate `dynasty._hs_pipeline` / HS League — not
  tied to the running session.

**The break:** `/stats/recruiting/commissioner/force-sign` mutated a recruit object in that
parallel pool but **never wrote back to the session's offseason state or
`_pending_signed_recruits`**. So a recruit "signed" in `/stats` **never landed on a roster** in
the game. The `/stats` recruiting hub had quietly grown from "an editor" into a second,
disconnected recruiting flow.

---

## 4. The challenges
- **`resolve()` overwrites, not appends** (`dynasty._pending_signed_recruits = signed`,
  `api/main.py`). A naive "assign" written before resolve would be wiped. So assignment had to
  survive resolve regardless of order.
- **No serializer round-trip to lean on.** Recruit visible attributes depend on scout level
  (`_serialize_recruit` → `recruit.get_visible_attrs()`), so an editor can't assume the true
  attributes are present to pre-fill — it must default them.
- **Team-name keys are everywhere.** Renaming a college team means updating the roster key, the
  schedule, conferences, `team_conferences`, `style_configs`, and postseason — not just a label.
- **`overall` is computed**, not stored — editing it directly is meaningless; attributes must be
  edited and OVR recomputes.
- **Don't rip out a 7.5k-line router.** Deprecating `/stats` recruiting had to be low-risk.

---

## 5. The fixes

**College editor (any session):**
- `PATCH /season/team/{team}/rename` — `_rename_team_everywhere` updates teams / schedule /
  conferences / team_conferences / style_configs / postseason (verified propagation against the
  real engine with a mock season).
- `PATCH /season/player/{team}/{player}` — edit name + attributes (allowlist `setattr`).
- `POST /season/player/move` — move a player to any team (re-numbers on jersey clash).
- `POST /season/player/add` — create/assign a new player on any team.
- UI: Team page gains a rename pencil, Edit/Move row actions, an Add-player button, and the
  attribute/move modals.

**Recruiting — make the editor authoritative in the game:**
- `PATCH /offseason/recruiting/{index}` — edit a recruit's name/position/stars/potential/
  development/attributes/GPA/SAT in the session's real pool.
- `POST /offseason/recruiting/assign` — sign a recruit to **any** team. Routed through
  `offseason["manual_signings"]`, which `offseason/complete` **also** promotes to rosters
  (alongside `_pending_signed_recruits`), with id-dedup — so it **survives `resolve()` overwriting
  pending** and actually lands the recruit. This is the in-session replacement for the broken
  `/stats` force-sign.
- UI: the Dynasty offseason recruiting phase gains **Edit** and **Sign** actions per recruit
  (`RecruitEditModal`, `AssignRecruitModal`).

**Deprecate the disconnected `/stats` flow:**
- Catch-all redirects registered at the top of `stats_site/router.py` shadow the whole
  `/recruiting/*` tree (GET + POST) → `307 /app/dynasty`. Verified with a TestClient that
  `/recruiting/`, `/recruiting/hs-rankings`, `/recruiting/commissioner`, and the force-sign POST
  all redirect. The old route handlers remain in the file but are unreachable (safe, reversible).

---

## 6. Verification & honest limits
- Backend compiles; `_rename_team_everywhere` propagation and the `/stats` recruiting redirects
  were exercised with real imports / TestClient. Frontend builds clean.
- **Unverified at runtime:** the edit/move/add/assign endpoints are simple `setattr`/list ops on
  the live session and weren't run against a full simulated season here (no FastAPI runtime in
  the build sandbox) — the owner's deploy is the final check.
- **Recruit editing pre-fill** defaults hidden (unscouted) attributes to 70; editing still writes
  the true values regardless of scout state.
- **Rename is best done early**; past weekly polls keep the old name (historical, harmless).
- The `/stats` recruiting *templates/handlers* still exist (just shadowed). Full removal can come
  later if desired.

---

## 7. Files
- Backend: `api/main.py` (team rename, player edit/move/add, recruit edit/assign, offseason
  manual-signing land), `stats_site/router.py` (recruiting deprecation redirect).
- Frontend: `web/src/pages/league/{TeamPage,PlayerEditor}.tsx`,
  `web/src/pages/dynasty/{OffseasonFlow,RecruitEditor}.tsx`, `web/src/api/{season,dynasty}.ts`.
