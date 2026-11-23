# AAR: League Hub and Dynasty Record Book crashes
## viperball.xyz/app, November 22, 2026

## What happened

Opening a season in the League Hub threw "Unexpected Application Error! Cannot read
properties of null (reading 'phase')" and the whole page failed to render.

The live bundle (`index-DkE4PROw.js`) was rebuilt locally from `main` at `9e7758a`, and it
produced the same hash. The crash offset maps to `LeagueHub.tsx`, at `const s = status.data!`
followed by `s.phase === "portal"`.

## Cause

Three screens read season status under the same TanStack Query key,
`["season-status", sessionId]`, with two different query functions:

| Screen | Query function | On a 400 or 404 |
|---|---|---|
| League Hub | `seasonApi.status(sid)` | throws, hub shows its error card |
| Dynasty command card | `seasonApi.status(sid).catch(() => null)` | caches `null` |
| DraftyQueenz board | `seasonApi.status(sid).catch(() => null)` | caches `null` |

A dynasty with no season running returns 400 from `/sessions/{id}/season/status`, so the
Dynasty card caches `null` under the shared key. The query client keeps data fresh for 60
seconds (`staleTime: 60_000`), so the League Hub reused that cached `null` without refetching.
`isLoading` and `isError` were both false, the hub skipped its guards, and the non-null
assertion let `null.phase` through to render.

## Fix

- `seasonApi.status` is now the one query function for the shared key. It resolves to `null`
  when the session has no season (400) and still throws when the session is gone (404). Its
  return type is `SeasonStatus | null`, so the compiler makes every caller handle `null`.
- The Dynasty command card and DraftyQueenz board drop their own `.catch(() => null)` and use
  that function. The shared cache now holds one meaning for every screen.
- The League Hub renders a "no season running yet" state with links to the session's Dynasty
  page and the League Hub index, replacing the `status.data!` assertion.

Behavior on the other two screens is unchanged. The Dynasty card still shows Start Season
when status is `null` or errors, and the DraftyQueenz board already read `season.data?.`.

## Checked

- `tsc -b --noEmit` and `npm run build` pass.
- The other `status.data!` reads (Pro hub, WVL hub, Dynasty hub, DraftyQueenz status) sit
  behind keys whose query functions never resolve to `null`, so they are not exposed to this
  bug.
- Not run against a live backend from this sandbox, which cannot reach viperball.xyz. To
  confirm after deploy, start a dynasty, open its League Hub link before starting the season,
  and check that the page shows the "no season" state.

## Lesson

A query key has to mean one thing. Two query functions with different error handling under
one key turn the cache into a race between screens.

---

## Second crash: Dynasty Record Book

## What happened

Opening the Record Book tab on a dynasty threw "Minified React error #31", which React raises
when it is handed a plain object to render. The object in the error had the keys
`{coach, championships}`.

## Cause

`/sessions/{id}/dynasty/record-book` returns each record as an object from
`engine/dynasty.py` `RecordBook`: the holder (`team` or `coach`), the value under its own key
(`wins`, `points`, `ppg_allowed`, `championships`, `win_pct`), and `year` for single season
records. The frontend typed the payload as `Record<string, number>` and rendered each entry
straight into a `<Text>`. The first object React met crashed the whole page. The type was
written from a code audit in June and never checked against a running server, which the June
AARs flagged as a risk.

## Fix

- `api/dynasty.ts` types the payload as `Record<string, RecordBookEntry>`, matching the engine.
- `DynastyHub.tsx` maps each of the seven records it already showed to its value key and
  format, and renders the value, the holder, and the year when there is one. Win percentage
  stays scaled from the engine's 0 to 1 value. Records with no holder yet are skipped, and the
  tab shows "No records yet." when none are set. The two records the page never showed (OPI
  and chaos) are still left out.

## Checked

`tsc -b --noEmit` and `npm run build` pass. The value keys were read from the engine's
`RecordBook` defaults and the code that updates each record. Not run against a live backend.
