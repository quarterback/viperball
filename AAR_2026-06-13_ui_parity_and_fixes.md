# AAR: SPA Course-Correction — Parity, Live-Fixes, and Saves
## viperball.fly.dev React SPA — June 13, 2026 (segment 2)

Continues `AAR_2026-06-13_ui_rebuild_analysis.md`. This segment covers the correction after
the owner deployed the SPA and found it had re-skinned *less* of the app than it should have:
restoring feature parity, fixing the production crashes/blockers surfaced on deploy, a
verification pass, and wiring saves to actually work. Companion: `POSTMORTEM_2026-06-13_ui_rebuild.md`.

---

## 1. Where it started

The SPA deployed but the owner hit, in order: a runtime crash, then missing features
("can't run a dynasty mode," "you don't let me pick teams how I once did," "made the playoffs
smaller"), then "the sim fails," then "you kept the engine toggle out too." The root issue:
the brief was a **re-skin of the NiceGUI app minus the convoluted UX**, and I had built a
from-scratch SPA that reimplemented a *subset*. The owner chose **"SPA → full parity"**, then
later **"take what you have and make it work 1:1"** (no more scope, no re-skin pivot).

---

## 2. What was restored to parity

- **Full Season Setup** (replaced the stripped wizard): up to 4 human teams each with
  offense/defense/ST styles (from `/styles`), an editable conference alignment seeded from
  `/conference-defaults`, playoff size as a team-count-constrained radio, bowl slider capped at
  `(teams−playoff)/2`, history-years, AI seed. Sends the full `CreateSeasonRequest`.
- **Real Dynasty mode** (replaced the read-only viewer): create (coach/team/program-archetype/
  format/conferences), a phase-aware command center (Start Season → Play in the League hub →
  Advance when finished), and the offseason loop NIL → portal → recruiting → finalize.
- **My Team made playable**: retain (NIL amount), portal bid, advance round, finalize, simulate,
  run-it-back.
- **Full-engine vs fast-sim toggle** restored per-week in the League hub (`fast_sim`).
- Extracted a shared `ConferenceEditor` and gave `useDataGrid` row-action support.

## 3. Production bugs fixed (all surfaced only on deploy)

| Symptom | Cause | Fix |
|---|---|---|
| Machine crash-loop on boot | `/app` mount logged via `logger` defined ~40 lines later → `NameError` at import | use `logging.getLogger(...)` directly |
| First deploy build failed | root `.gitignore` (Python template) `lib/` rule excluded `web/src/lib/queryClient.ts` → never committed | scoped negation `!web/src/**` |
| "Unexpected error: localeCompare is not a function" — every grid | mantine-react-table sorts faceted **select** filter values with `localeCompare`; numeric columns (week) threw | removed `enableFacetedValues` + numeric select filters |
| Volume deploy error / crash-loop blamed on machines | needed a Fly volume; then NameError (not machine count) | owner created volume + scaled to 1; fixed the NameError |
| **"Sim failed"** | (a) season opens in pre-season **"portal"** phase but `simulate-week` requires `"regular"`; (b) bodyless POST 422'd a required Pydantic body | added `SeasonPortalPanel` (sign/skip → regular); `apiSend` now sends `{}` for write methods |
| Dynasty list blank rows | `GET /dynasties` returned only save metadata, not name/coach/team/year | load each blob, return display fields |

## 4. Verification pass (owner: "make it work 1:1")

Ran a static cross-check of all ~60 SPA calls vs. backend routes/models/serializers (the
empty-grid and 422 class of bug). Result was **mostly clean** — one real mismatch (`/dynasties`,
fixed). Independently confirmed Pro standings (`divisions` structure in `engine/pro_league.py`)
and Dynasty status coach fields are correct. Stated the honest limit: static checks can't catch
phase/logic behavior (the portal-phase bug only showed at runtime), so a deploy walkthrough
remains the real 1:1 check.

## 5. Saves — made to actually work

Discovery: there is **no `Season` serializer** and building a resume-able one is the riskiest
change in the codebase. But the **college archive snapshot** (`_build_college_archive`) already
captures standings/schedule/polls/conferences/rosters/awards/champion via the same serializers
the live views use. So:

- **College seasons auto-persist** on every sim — `_autosave_college` upserts one light snapshot
  per session inside `_persist_box_scores`. Experiments now survive restarts/deploys and appear
  in the Saves Library.
- **`/api/saves`** resolves `season_archive` rows to their real mode (college/fiv) + champion/team
  count from the meta, instead of mislabeling all as "fiv".
- **Library "Open" routes by type** (was a dead `/league?save=` link): college → read-only
  `ArchiveView` (standings/schedule/polls from the snapshot), dynasty → load into a session, pro
  → Pro tab. Delete cleans up archive meta + box scores. Verified list/open-id/delete via a
  FastAPI `TestClient`.
- **Honest limit:** opening a college save is **read-only** (view/compare, not resume) — the
  engine can't rebuild a live mid-sim `Season`; nothing in the app resumes mid-season.

## 6. What changed in process this segment

- **Verify before building** — before each parity piece I read the real request models /
  serializers (caught the team key-vs-name bug and the `/dynasties` shape before shipping), and
  verified the saves flow with a `TestClient`.
- **Smaller, true claims** — "builds, unverified at runtime" where I couldn't run it; the owner's
  deploy is the final gate, and each report says what's verified vs. not.
- **No scope creep** — once the owner said "make it work 1:1," I stopped adding features and
  switched to correctness; the `/stats` redesign is parked as deferred Phase 6.

## 7. State at end of segment

All on branch `claude/cool-galileo-d3yyng` / PR #310, pending the owner's next deploy:
Season Setup (parity), Dynasty (playable), My Team (playable), engine toggle, sim-fail fixed,
`/dynasties` fixed, and durable+reloadable college saves. Remaining confidence step is a deploy
walkthrough of each mode; anything it surfaces is a direct fix, not a rebuild.

## 8. Files

- Frontend: `web/src/pages/league/{NewSeason,SeasonPortalPanel,ArchiveView}.tsx`,
  `web/src/pages/dynasty/{DynastyCreate,DynastyCommand,OffseasonFlow}.tsx`,
  `web/src/components/ConferenceEditor.tsx`, `web/src/pages/MyTeam.tsx`, `SavesLibrary.tsx`,
  `web/src/api/{season,dynasty,myteam,client}.ts`, grid/filters across pages.
- Backend: `api/main.py` (logger fix, `/api/sessions/college`, `_autosave_college`, `/dynasties`),
  `api/saves_api.py` (archive mode + delete), `engine/db.py` (earlier), `.gitignore`, `Dockerfile`,
  `fly.toml`.
