# After-Action Report: V2.5 — HC Ambition System, Coaching Trees, Assistant HC Meter, and Coach Development

**Date:** 2026-02-23
**Branch:** `claude/fix-season-mode-flyio-PH0pe`
**Scope:** Twelve commits spanning fly.io deployment fixes, game engine balancing (touch distribution, hero ball nerfs), the coaching portal NRMP matching system, in-game dev aura, and — in the final commit — the HC ambition/departure overhaul, coaching tree tracker, assistant HC readiness meter, coach attribute development, and role fluidity between HC and coordinator positions.

---

## Objective

The coaching system through V2.4 treated head coaches like permanent fixtures. An HC stayed at a school until fired or until their contract expired (50% coin flip to leave). There was no model for why a successful coach would leave a low-prestige program, no mechanism for assistant coaches to earn their way into HC candidacy beyond a simple `wants_hc` boolean, and no career lineage connecting a coordinator's development to the head coaches they served under.

Five problems needed solving:

1. **HC departure was random, not meritocratic** — A 50% coin flip decided whether an expired-contract HC left. A championship-winning HC at a 30-prestige school had the same chance of staying as a .400 HC at a blue blood. Real coaching markets are driven by ambition: successful coaches seek bigger stages.

2. **No parlay mechanism** — Coaches who were happy at their program had no way to extend. They either left or stayed on expired terms. In reality, a 7-5 HC at a prestige-55 school isn't looking to leave — they're looking for a raise and more years.

3. **Assistants couldn't earn HC candidacy** — The `wants_hc` flag was set at generation time and never changed. A coordinator who coached a Heisman-level player, won a conference title, and worked under a championship HC for 5 years still had the same HC aspiration as the day they were hired. There was no development pathway.

4. **No coaching tree** — Every coach existed in isolation. There was no record of which HCs a coordinator served under, which meant no lineage, no "coaching family" narrative, and no way to display a Saban-style coaching tree on the coach card.

5. **Coaches didn't develop** — Players gained attributes every offseason through `apply_offseason_development`, but coaches were static. A 35-year-old coordinator had the same ratings at 55 as at 35. Roles were permanent: an HC could never become a coordinator, and a coordinator's only path to HC was through the `wants_hc` flag.

---

## Starting State (V2.4 Baseline)

| Feature | V2.4 State |
|---|---|
| HC departure trigger | Contract expired → 50% coin flip |
| Contract extension | None — re-sign or portal |
| HC ambition model | None |
| `wants_hc` flag | Set at generation, never updated |
| HC readiness meter | None |
| Coaching tree | None |
| Coach attribute development | None |
| Role fluidity | Permanent — HC stays HC, OC stays OC |
| Postseason stat tracking | `championships` only on CoachCard |
| Portal scoring (HC candidates) | Overall rating + classification fit |

---

## Work Performed

### 1. CoachCard Data Model Expansion (`engine/coaching.py`)

**New Fields:**

| Field | Type | Purpose |
|---|---|---|
| `conference_titles` | `int` | Career conference championships won |
| `playoff_appearances` | `int` | Career playoff berths |
| `playoff_wins` | `int` | Individual playoff game wins (deeper runs = more) |
| `championship_appearances` | `int` | Championship game appearances |
| `coaching_tree` | `List[dict]` | Every HC this coach served under as an assistant |
| `hc_meter` | `int` (0-100) | HC readiness meter for assistants |

All fields are serialised in `to_dict()` / `from_dict()` and survive dynasty save/load roundtrips.

**Why these fields:** The ambition formula needs postseason data beyond just `championships`. A coach who went 12-1 with a conference title and a semifinal loss has different market value than a 12-1 coach who missed the playoffs entirely. `playoff_wins` specifically rewards depth — an HC who went to three straight semifinals accumulates 6+ playoff wins, making them extremely attractive to elite programs.

---

### 2. HC Ambition System (`compute_hc_ambition`)

**Formula:**

```
ambition = int(win_percentage * 80)
         + conference_titles * 5
         + playoff_appearances * 3
         + playoff_wins * 4
         + championship_appearances * 5
         + championships * 8
```

Clamped to [10, 99].

**Design rationale:** Win percentage provides the base (0-80 range), ensuring a .500 HC maxes at ~40 ambition while an 80% HC starts at ~64. Postseason bonuses stack on top, creating separation between regular-season-only success and deep playoff runs. The multipliers are tuned so that:

| Profile | Approx. Ambition |
|---|---|
| First-year HC, no record | 10 |
| 7-5 HC, 1 conf title | ~54 |
| 9-3 HC, 2 playoff trips, 1 conf title | ~68 |
| 11-1 HC, 3 playoffs, 5 PO wins, 1 championship | ~92 |
| Dynasty HC, multiple rings | 99 |

---

### 3. Contract Extension Parlay (`try_hc_contract_extension`)

**Logic:**

1. Compute HC ambition.
2. If `ambition > team_prestige + 10` → coach has outgrown the program → **no extension** (enters portal).
3. If recent season record is below .500 → **no extension** (not parlaying on a losing year).
4. Otherwise → **extend**: 3-5 new years, salary re-calculated with a 10% loyalty bump.

The +10 buffer is critical. A prestige-55 school can retain an HC with ambition up to 65, which covers most "solid but not elite" coaches. But a coach who wins a championship at that school jumps to ambition ~80+ and leaves — exactly as intended.

**Why not just re-sign at 50%?** Because the old model was degenerate. It created two failure modes: (a) a great coach randomly leaves a great program for no reason, and (b) a great coach randomly stays at a terrible program forever. The ambition model makes departures legible — the player can look at an HC's ambition score and their team's prestige and predict whether the coach will stay.

---

### 4. HC Departure Rewrite (`coaching_portal.py :: populate_coaching_portal`)

**Old logic:**
```
if contract expired:
    if random() < 0.50:
        enter_portal()
```

**New logic:**
```
if role == "head_coach" and contract expired:
    if try_hc_contract_extension(coach, team_prestige, wins, losses):
        stay()       # Coach extended — contract refilled
    else:
        enter_portal()   # Ambition > prestige — wants a bigger job
elif contract expired:
    if random() < 0.50:  # Non-HC: coin flip unchanged
        enter_portal()
```

Head coaches now **never** leave by coin flip. They leave because their ambition demands it, or they stay because the program fits. Coordinator departure remains probabilistic (50/50) since their market dynamics are less prestige-driven.

---

### 5. HC Readiness Meter (`advance_hc_meter`)

**The Problem:** `wants_hc` was a boolean set at generation time with weighted probability. A coordinator hired at age 32 with `wants_hc=False` would never seek an HC job, even after 20 years of winning. Conversely, a freshly-hired coordinator could spawn with `wants_hc=True` despite zero accomplishments.

**The Meter (0-100):**

Each offseason, assistants accumulate meter points:

| Source | Points | Condition |
|---|---|---|
| Tenure | +2 | Per year as coordinator |
| Star player in area | +5 to +10 | Best player in position group is 80-90+ overall |
| Team winning record | +2 to +8 | Win% ≥ .500 to ≥ .750 |
| Made playoffs | +3 to +5 | Team made postseason |
| Won conference | +2 to +4 | Team won conference championship |
| HC success | +2 to +6 | HC win% ≥ .550, bonus for HC championships |
| Own quality | +1 to +3 | Coach overall ≥ 75 |

**Thresholds:**

| Meter | Effect |
|---|---|
| < 75 | No HC aspiration |
| ≥ 75 | `wants_hc` flips to True, enters HC candidate pool (30% chance if overall ≥ 65) |
| ≥ 90 | "Hot name" — always enters pool (if overall ≥ 60), +8 ranking boost in portal matching |

**Progression speed:** A coordinator on a playoff team with a star player and a great HC gains ~20-30 points/year. They hit 75 in ~3 years and 90 in ~4. A coordinator on a losing team with mediocre talent and an average HC gains ~6-10 points/year — they might never hit 75, which is realistic. Not every coordinator is HC material.

**Why a meter instead of a formula?** A formula would be stateless — the same coordinator on the same team would get the same answer every year. The meter is cumulative, which means history matters. A coordinator who spent 3 years on a playoff team and then moved to a rebuilding program still carries those meter points. Their development doesn't reset.

---

### 6. Coach Attribute Development (`apply_coach_development`)

**Problem:** Players developed every offseason but coaches were frozen. A 35-year-old OC hired at 65 overall would still be 65 at age 55. This made coaching staffs feel static and reduced the impact of "growing with a coach."

**Solution:** Each offseason, every coach (HC and coordinators) gets small attribute changes:

| Season Record | Gain Range per Attribute |
|---|---|
| Win% ≥ .650 | 0 to +2 |
| Win% ≥ .500 | 0 to +1 |
| Win% < .500 | -1 to +1 |

**Age decline:** Coaches 60+ get -1 penalty per attribute; 65+ get -2. This creates natural retirement pressure without forcing it.

**Net effect:** A winning coordinator improves ~3-6 total attribute points per year. Over a 5-year stint at a good program, they could gain +15-30 points across attributes — enough to jump from 65 overall to 72-75 overall. Combined with the HC meter filling, this creates a satisfying arc: hire a young coordinator, watch them develop into a legitimate HC candidate, and then either promote them or lose them to the portal.

---

### 7. Role Fluidity (`get_acceptable_roles`)

**Problem:** Roles were permanent. A fired HC could only seek another HC job. A coordinator could only seek the same coordinator role (plus a 30% chance at adjacent roles). This ignored the reality that fired HCs frequently take coordinator positions, and it artificially constrained the portal pool.

**Solution:** `get_acceptable_roles(card)` returns all roles a coach would consider:

| Current Role | Acceptable Roles |
|---|---|
| HC (defensive_mind) | head_coach, dc |
| HC (offensive_mind) | head_coach, oc |
| HC (special_teams_guru) | head_coach, stc |
| HC (balanced) | head_coach, oc or dc |
| Coordinator (meter ≥ 75) | current_role, head_coach |
| Coordinator (meter < 75) | current_role only |

This means a fired HC with `hc_affinity: defensive_mind` will appear in both the HC pool and the DC pool. Teams looking for a DC might hire a former HC — giving them an elite coordinator with HC-level instincts. And coordinators whose HC meter has matured appear in HC vacancy pools.

The portal's free-agent generation also uses `get_acceptable_roles`, so generated free agents can cross role boundaries too.

---

### 8. Coaching Tree Tracker (`dynasty.py :: advance_season`)

**Implementation:** Every offseason, after postseason stats are recorded, the dynasty iterates all coaching staffs. For each assistant coach:

1. If the last entry in their `coaching_tree` has the same `coach_id` as the current HC → extend `year_end` to the current year.
2. Otherwise → append a new entry: `{coach_name, coach_id, team_name, year_start, year_end}`.

This means a DC who worked under Coach Smith from 2026-2029, then under Coach Jones from 2030-2032, will have:
```json
[
  {"coach_name": "A. Smith", "coach_id": "coach_...", "team_name": "Xavier", "year_start": 2026, "year_end": 2029},
  {"coach_name": "B. Jones", "coach_id": "coach_...", "team_name": "Xavier", "year_start": 2030, "year_end": 2032}
]
```

The tree persists across team changes. If that DC moves to a new team, their tree continues with the new HC appended.

---

### 9. Portal Scoring Updates

Two new scoring factors in the coaching portal:

**Teams scoring coaches (`_team_score_coach`):**
- **Postseason pedigree:** Conference titles (×2), playoff wins (×1.5), championship appearances (×3), championships (×5). This makes accomplished HCs more attractive to bigger programs.
- **Hot name bonus:** Coordinators with HC meter ≥ 90 get +8 ranking boost; meter ≥ 75 gets +4. Teams actively prefer coordinators who have "earned it."

**Coaches scoring teams (`_coach_score_team`):**
- **Ambition matching:** `gap = team_prestige - ambition`, then `bonus = clamp(gap × 0.3, -15, +10)`. Successful coaches penalise low-prestige teams and prefer programs that match their perceived worth.

---

### 10. Dynasty Integration

The dynasty offseason (`run_offseason`) now runs three new phases between contract-ticking and portal population:

1. **HC meter advancement** — For each team, compute the best player overall in each position area (offense/defense/ST), then call `advance_hc_meter` for every assistant.
2. **Coach attribute development** — Call `apply_coach_development` for every coach on every staff.
3. **Postseason stat tracking** — In `advance_season`, before coach records update: compute conference champions, count playoff wins from the bracket, identify championship game participants, and update each HC's postseason stats. Also update coaching trees for all assistants.

---

## Testing

| Test | Result |
|---|---|
| Import verification (coaching, coaching_portal, dynasty) | Pass |
| Serialization roundtrip (to_dict → from_dict) | Pass — hc_meter, coaching_tree, postseason fields survive |
| HC ambition for various profiles | 54 (modest), 65 (good), 92+ (dominant), 99 (dynasty) |
| Extension parlay: modest HC at matching prestige | Extended (3 years) |
| Extension parlay: dominant HC at low prestige | Rejected — enters portal |
| HC meter progression: 5 years on playoff team | 0 → 25 → 49 → 78 → 100 (wants_hc flips at year 3) |
| Coach development: winning team | +2-6 total attr points per year |
| Role fluidity: fired HC acceptable roles | [head_coach, oc] for offensive_mind affinity |
| `test_dynasty.py` full integration | Pass — 5-season dynasty runs cleanly |

---

## Before/After Summary

| Feature | Before (V2.4) | After (V2.5) |
|---|---|---|
| HC departure | 50% coin flip on expired contract | Ambition vs. prestige comparison |
| Contract extension | None | Automatic for content coaches (ambition ≤ prestige + 10) |
| HC candidate pool | `wants_hc` boolean, set at generation | HC meter (0-100), earned through performance |
| Coaching tree | None | Full lineage: every HC each coach served under |
| Coach development | Static | 0-2 attr gains/year, age decline 60+ |
| Role fluidity | Permanent roles | HCs ↔ coordinators based on affinity + meter |
| Postseason tracking | `championships` only | conf_titles, playoff_appearances, playoff_wins, championship_appearances |
| Portal scoring | Overall + classification | + pedigree bonus, hot name bonus, ambition matching |

---

## Known Limitations & Future Work

1. **Human team coaching tree display** — The coaching tree data is tracked but there's no UI panel yet to display it on the coach card page.
2. **HC meter visibility** — The meter is computed but not surfaced in the season mode UI. Dynasty mode could show a "rising star" indicator for assistants approaching 75.
3. **Extension negotiation** — Currently automatic. Could become interactive for the human team: "Coach Smith wants an extension. Offer 3 years / $X?" with a risk of losing them if you lowball.
4. **Fired HC stigma** — A fired HC currently enters the portal with no penalty. Could add a "cooling off" mechanic where recently-fired HCs accept lower salaries.
5. **Conference title tracking for assistants** — Currently only HCs get postseason stat bonuses. Coordinators on championship teams could get a smaller HC meter boost per playoff win (they already get the team-level playoff/conf bonus, but not individual playoff win tracking).
