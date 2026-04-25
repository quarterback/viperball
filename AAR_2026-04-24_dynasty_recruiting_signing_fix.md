# AAR: Dynasty Recruiting & Signing Pipeline Fix
## Viperball College Dynasty — April 2026

### Summary

Player report: "I just did a whole dynasty season and the recruiting isn't working — no one is signing at all early, middle, or late. And those same players don't appear on the rosters the following year."

Two layered bugs were responsible. The interactive offseason API never produced phased-signing data, so the Signing Day Tracker rendered an empty page that read "No signings recorded" under all three phase columns. Even when signings did occur in memory, the offseason-complete handoff never converted those recruits into PlayerCards on next year's roster, and graduating seniors stayed on as roster zombies. From the player's seat the recruiting class was invisible coming and going.

Both are now fixed. Phased signing is the canonical path for the API offseason, signed recruits land on rosters as Freshman PlayerCards, and graduates are dropped before persistence.

---

### What Was Wrong

#### 1. Signing Tracker showed "No signings recorded" for every phase

`POST /sessions/{id}/offseason/recruiting/resolve` (`api/main.py:3004`) called the legacy single-pass `simulate_recruit_decisions` and returned a flat `class_rankings` blob. It never wrote anything to `dynasty.recruiting_history`.

The Signing Day Tracker page (`stats_site/router.py:6597`) reads exclusively from `dynasty.recruiting_history[latest_year]` and unpacks `phase_summary` and `signing_log`. With nothing written, the template fell through to its empty state for the **early**, **regular**, and **post_bowl** columns — the exact "early/middle/late" the player described.

The phased signing logic (`engine/recruiting.py:simulate_phased_signing`) and the persistence shape were already implemented for the auto-dynasty path; the interactive API path simply never used either.

#### 2. Signed recruits never appeared on the next season's roster

`POST /sessions/{id}/offseason/complete` (`api/main.py:3127`) was responsible for snapshotting `player_cards` into `dynasty._next_season_rosters` so `dynasty_start_season` could rebuild teams from developed rosters instead of fresh JSON loads. The handler:

- Applied portal transfers to `player_cards`.
- **Did not** drop graduating seniors (`year == "Graduate"`).
- **Did not** convert signed recruits into PlayerCards.

Net effect: the new freshman class never reached `_next_season_rosters`. When `dynasty_start_season` (`api/main.py:2113-2126`) restored the persisted cards back into `team.players`, the roster was last year's roster minus portal departures — recruits gone, graduates still on the depth chart.

#### 3. Scholarship math collapsed to the floor

Both the API endpoint (`api/main.py:3043`) and `Dynasty.run_offseason` (`engine/dynasty.py:1525`) used:

```python
open_spots = max(3, min(12, grads + portal_losses - portal_adds))
```

The comment in `dynasty.py` aspired to "roster target (36) minus current players minus portal additions plus graduating players," but `_roster_maintenance` always backfills rosters to 36 with generated freshmen, so the `36 − current_players` term collapses to zero in practice. A net-positive portal season (which is common after a successful year) drove the inner expression negative and clamped to the **3-scholarship** floor — small enough that even when signings happened, classes felt empty.

#### 4. Latent crash in `Dynasty.run_offseason`

The infrastructure-investment loop at line 1188 referenced `human_team` ~30 lines before `human_team = self.coach.team_name` was assigned, raising `NameError` whenever `_team_infrastructure` was populated (always, after first invocation). No automated test covered the college `Dynasty.run_offseason` path — `test_commissioner.py` exercises `WVLCommissionerDynasty.run_offseason`, a separate class — so the bug had been latent since the file's initial commit (`df9229e`).

---

### What Changed

#### `api/main.py` — `offseason_recruiting_resolve`

- Imports and calls `simulate_phased_signing` instead of `simulate_recruit_decisions`.
- Builds `team_rosters` from `offseason["player_cards"]` and threads it through both `auto_recruit_team` (so CPU offers respect position depth) and the signing simulator (so recruits factor depth into their decision).
- Writes a complete record to `dynasty.recruiting_history[year]`:

  ```python
  {
      "class_rankings": [...],
      "signed_count": {team: count},
      "pool_size": int,
      "signing_log": [...],
      "phase_summary": {"early": {...}, "regular": {...}, "post_bowl": {...}},
      "walkons": {},
  }
  ```

- Stashes `_last_recruit_pool` and `_pending_signed_recruits` on the dynasty for downstream consumers (recruit profile pages, the next offseason-complete call).
- Returns `phase_summary` in the API response so the resolve UI could surface it directly if desired.

#### `api/main.py` — `offseason_complete`

After portal transfers are applied to `player_cards`:

- Drop every card whose `year == "Graduate"`.
- Iterate `dynasty._pending_signed_recruits` and append each `Recruit.to_player_card(team_name)` (a Freshman) to the team's roster.
- Clear `_pending_signed_recruits` after consumption.
- Serialize the updated `player_cards` to `_next_season_rosters` as before.

`dynasty_start_season` continues to restore from `_next_season_rosters`, so the new freshmen show up automatically.

#### `engine/dynasty.py` — `Dynasty.run_offseason`

- Move `human_team = self.coach.team_name` to the top of the method (right after the `result` dict init) so the infrastructure-investment loop can reference it. Drop the redundant reassignment further down.
- Apply the same scholarship-floor change as the API.

#### Scholarship formula (both call sites)

```python
open_spots = max(6, min(12, grads + portal_losses - portal_adds + 4))
```

Floor of 6 keeps net-positive portal seasons from collapsing the class. The `+4` baseline covers redshirts and walk-on conversions that `_roster_maintenance` does not charge against the scholarship count.

---

### Verification

End-to-end repro (8 SEC teams, fresh HS pipeline, mock portal, manual offers from the human team):

```
=== BEFORE offseason_complete ===
  Alabama:  34 cards (5 Graduate),  2 signed
  Auburn:   34 cards (5 Graduate),  4 signed
  Arkansas: 34 cards (5 Graduate),  6 signed

=== Signing phases ===
  early:     25 signings  by_stars={3: 7, 4: 14, 5: 4}
  regular:   14 signings  by_stars={3: 2, 4: 7, 5: 5}
  post_bowl:  3 signings  by_stars={3: 2, 4: 1}

=== AFTER offseason_complete + restore ===
  Alabama:  31 players, 11 Freshman, 0 Graduate, signed-on-roster: 2/2
  Auburn:   33 players, 12 Freshman, 0 Graduate, signed-on-roster: 4/4
  Arkansas: 35 players, 18 Freshman, 0 Graduate, signed-on-roster: 6/6

✓ All 43 signed recruits appear on next season's rosters
✓ All graduates removed
```

`test_recruiting.py` still passes 11/12 (the failing `test_roster_prestige_estimation` is a pre-existing portal-prestige issue, unrelated to signing).

---

### Design Decisions

**Why phased signing in the API path instead of bridging to `Dynasty.run_offseason`?**
`Dynasty.run_offseason` is a 600-line method that owns the full auto-dynasty offseason: prestige regression, infrastructure decay/AI investment, coaching staff churn, NIL programs, the transfer portal, the HS league season, and recruiting. The interactive API has its own equivalents for most of these spread across `dynasty_advance`, `season_portal_*`, and the offseason endpoints. Routing the API through `run_offseason` would double-run those subsystems. Replacing the single-pass signing call was a one-line swap; the rest is the same plumbing the auto path uses.

**Why drop graduates in `offseason_complete` rather than at season end?**
The graduates dict is already computed in the offseason endpoint (`api/main.py:2322-2326`) and used by the portal and recruiting endpoints to estimate scholarship needs. The "drop them from the roster" step needs to happen exactly once, immediately before `_next_season_rosters` is serialized — which is what `offseason_complete` is for. Doing it earlier would break the portal/recruiting endpoints that still need to know who graduated.

**Why a `+4` baseline scholarship instead of computing from real roster size?**
`_roster_maintenance` always backfills rosters to 36 with generated freshmen, so any roster-size-aware formula reads 36 every year and the differential vanishes. The +4 baseline approximates the redshirts and preferred walk-ons that escape the scholarship accounting. A future improvement could thread real scholarship counts (rather than headcount) through, but that's a larger refactor and not what the player was complaining about.

**Why fix the `human_team` NameError if no live UI hits that path?**
Tests, `batch_sim`, and any future commissioner-style automation will hit it. It's a one-line change with zero risk and removes a trip wire.

---

### Interaction with Other Systems

- **Signing Day Tracker (`/recruiting/signing-tracker`)** — was the player-visible symptom; now reads real `phase_summary` data and renders three populated columns.
- **Recruit Profile pages (`/recruiting/recruit/{id}`)** — fall back to `dynasty.recruiting_history.signing_log` for signed recruits no longer in the active pool. Now actually populated.
- **Class Rankings** — the resolve response and `recruiting_history.class_rankings` now exclude walk-ons from the average-stars calculation (`is_walkon` filter), matching `run_full_recruiting_cycle` behavior.
- **Transfer Portal** — unchanged, still applied first in `offseason_complete`. Portal transfers + graduate drop + signed recruits compose cleanly because each operation targets a disjoint slice of the roster.
- **HS Recruiting Pipeline** — unchanged. The pipeline still hands 12th graders to `recruit_pool` at the start of the offseason; phased signing consumes them; `to_player_card` converts the signed subset.

---

### Known Limitations

- **No class-year advancement on the API offseason path.** `Dynasty.advance_season` does call `apply_team_development` (which advances years), so the cards arriving at offseason already have the correct years. But there's no second-stage development applied during the offseason itself the way `Dynasty.run_offseason` does. Out of scope for this fix.
- **No fallback backfill for short rosters.** If a team's churn (graduates + portal departures) exceeds its signing class plus walk-ons, the roster will be under 36 next year. `_roster_maintenance` handles this in the auto path; the API path doesn't yet.
- **Walk-ons are not generated by the API resolve.** `simulate_phased_signing` returns the unsigned pool; the API doesn't currently route those through `assign_walkon_players`. The `walkons` dict in `recruiting_history` is always empty.

---

### Files Changed

- `engine/dynasty.py` — Fix `human_team` NameError, raise scholarship floor, comment cleanup.
- `api/main.py` — Switch `offseason_recruiting_resolve` to phased signing and persist to `recruiting_history`; convert signed recruits and drop graduates in `offseason_complete`.

### Commits

- `a3d90b9` — Fix dynasty recruiting showing zero signings in early/regular/post-bowl
- `9c43d60` — Apply signed recruits + drop graduates in offseason_complete
