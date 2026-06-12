# AAR: Stale Box Scores Surfaced as Ghost College Leagues on the Hub
## Viperball ↔ vroomtv (Rocky Mountain News) — June 2026

### Summary

User report: "the rocky site is picking up old artifacts or retaining old viperball content after a new one has been loaded… it's creating clutter and also bad data since I can't clear that off the rocky site."

The screenshot showed three different College session hashes side by side on the hub — `College (5eb86616)`, `College (93d8a338)`, `College (c03fbd76)` — with headlines and standings for each. Only one of those was the current session; the other two were dead.

Root cause was a data-hygiene gap on the viperball side amplified by the hub's "trust whatever is in the DB" parse. Every `box_score` row that's ever been written survives in `viperball.db` unless its owning session goes through `DELETE /sessions/{id}` or hits the `MAX_SESSIONS` eviction. Sessions abandoned via a tab close — or wiped by a process restart, since `sessions` is in-memory — leave their box scores behind forever. The hub pulls the whole DB on each sync and groups every `box_score` row by `session_id`, so each orphan turned into its own ghost college league on the front page.

Fixed on both sides:

1. **Viperball** now prunes `box_score` rows whose `session_id` isn't in the live `sessions` dict, on `create_session` and immediately before `/export/db` streams a snapshot.
2. **vroomtv** filters `_college_leagues()` against the synced `viperball_sessions.json`, and `sync.py` deletes `vb_kp_*.json` files for sessions the sim no longer reports.

---

### What Was Wrong

#### 1. Box scores outlived their sessions

`engine/db.py:save_box_scores_bulk` writes one row per completed game keyed `{session_id}__w{week}__{away}_at_{home}`. Cleanup only happened in two narrow places:

- `DELETE /sessions/{id}` (`api/main.py:1033`) — requires the client to actually call it.
- `create_session` eviction at `MAX_SESSIONS` (`api/main.py:1008`) — only fires once the cap is reached.

A user closing the tab, an API restart, or anything below the cap left every prior session's box scores in the table. The rows are small individually but they're authoritative for the export.

#### 2. The hub treats every `box_score` row as a live session

`adapters/viperball.py:_rebuild_college` runs `SELECT save_key, data FROM saves WHERE save_type='box_score'`, regexes the `session_id` out of each key, and emits one league per distinct sid. There was no filter — every orphan `box_score` row became a league on `/`, `/scores`, `/standings`, `/leaders`, and (via `newsroom.build_wire`) a headline on the front page.

The label format `College ({sid[:8]})` made the symptom visually obvious as soon as more than one session existed: distinct hashes side by side, all looking equally current.

#### 3. KenPom JSONs were never garbage-collected on the hub

`sync.py` (the original `viperball_kenpom` block) iterated `viperball_sessions.json` and wrote one `vb_kp_{sid}.json` per active session. It never removed files for sessions that dropped out of the list. The adapter's `_portal_kenpom` then `glob`'d them all back in:

```python
for fp in _glob.glob(os.path.join(os.path.dirname(path) or ".", "vb_kp_*.json")):
    ...
    out[blob.get("session_id", "")] = blob.get("standings", [])
```

So even after the box-score fix, dead sessions would have retained their KenPom decoration on whatever stale rows remained.

---

### The Fix

#### Viperball side

**`engine/db.py:1473` — new `prune_orphan_box_scores(active_session_ids)`** scans every `box_score` row, parses the `session_id` out of `save_key` via `split("__w", 1)[0]`, and deletes any whose sid isn't in the active set. One transaction, idempotent, returns the count removed.

Wired in two places:

- **`api/main.py:create_session`** — runs the prune right after a new session is inserted so each new run sweeps the prior tenant's leftovers, even if the prior session never went through `DELETE` or eviction.
- **`api/main.py:export_db`** — runs the prune immediately before the SQLite `backup()` so the snapshot the hub downloads is already clean. This matters because the hub's sync is what populates the front page; a clean export means the hub stops surfacing ghosts on the next pull, without needing its own filter to catch up.

Both call sites swallow exceptions and `logger.debug` the failure — pruning is hygiene, not a hard precondition for the request.

#### vroomtv side

**`adapters/viperball.py:_active_session_ids`** reads `viperball_sessions.json` (already synced by `sync.py`) and returns the set of `session_id`s under `college`. Returns `None` when the file is missing, which is the signal `_rebuild_college` uses to fall through to "trust the DB" — important for local dev and the pre-first-sync window so we don't blank the page out.

**`adapters/viperball.py:_rebuild_college`** now skips `box_score` rows whose sid isn't in `_active_session_ids(path)` when the set is known. Belt-and-suspenders with the viperball-side prune: if the hub's snapshot is older than the prune fix, or if a session vanished from `sessions.json` between syncs, the hub still hides it.

**`sync.py`** — the viperball KenPom fanout block now collects active sids first, then loops a single `glob("vb_kp_*.json")` and `os.unlink`s any file whose sid isn't in the set. Reported as `viperball_kenpom_pruned` in the `/sync` results so it's visible in the manual sync response.

---

### Files touched

- `viperball/engine/db.py` — `prune_orphan_box_scores`
- `viperball/api/main.py` — wire prune into `create_session` and `/export/db`
- `vroomtv/adapters/viperball.py` — `_active_session_ids` + filter in `_rebuild_college`
- `vroomtv/sync.py` — collect active sids, delete stale `vb_kp_*.json`

### What this doesn't cover

- **Pro and WVL sessions.** Only college `box_score` rows accumulate per-game; pro leagues use a single `pro_league` blob whose lifecycle the user already controls. If pro sessions ever start persisting per-game rows, the prune helper takes a set so it's a one-line extension.
- **Restoring a session after an API restart.** `sessions` is in-memory; if a college session's box scores still mattered after a restart, the user would lose them on the next `create_session` call. Today the season object itself doesn't survive a restart either, so this is consistent with existing behavior — not a regression. If session persistence ever lands, the prune call needs to move after the restore step.
- **Box scores from a session whose `session.season` was never set.** `/export/sessions.json` filters on `s.get("season") is not None`. A freshly-created session that wrote box scores but never finished setup would be pruned. Box scores can't actually be written without a season, so this is theoretical.
