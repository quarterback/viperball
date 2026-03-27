# AAR: Penalty Catalog Expansion & Kickpass Penalty Phase

**Date:** 2026-03-27
**Branch:** `claude/add-game-penalties-EkTLj`

---

## Overview

Full audit and expansion of the penalty system from 42 infractions across 5 phases to **99 unique infractions across 6 phases** (146 total catalog entries including duplicates across phases). Added a dedicated kickpass penalty phase, Viperball-specific physicality rules, and backfilled missing NFHS-standard penalties.

---

## 1. Starting State

### Problem

The penalty catalog had only 42 infractions — thin compared to real football officiating. Several penalties documented in RULES.md (Targeting, Blindside Block, Illegal Motion, Wedge Formation, Illegal Defensive Formation) were missing from the engine. More critically:

- **No kickpass-specific penalties.** Viperball's signature mechanic was routed through the generic `during_play_kick` phase alongside punts and place kicks. A kickpass receiver getting drilled before the ball arrives would generate a "Fair Catch Interference" call — wrong penalty, wrong flavor.
- **No Viperball-specific physicality rules.** The Zeroback (QB-equivalent) had no roughing protection. Lateral receivers had no defenseless-player protections despite being in vulnerable catching positions.
- **Missing standard football penalties.** No Hurdling, Blocking Below the Waist, Hands to the Face, Piling On, Striking, Assisting the Runner, Fighting, or Removal of Helmet.
- **"Too Many Men on Field" only callable pre-snap.** In real football this is frequently a live-ball penalty.
- **Post-play phase was thin** — only 5 infractions for all the things that can go wrong between whistles.

### Counts (before)

| Phase | Count |
|-------|-------|
| pre_snap | 8 |
| during_play_run | 10 |
| during_play_lateral | 12 |
| during_play_kick | 7 |
| post_play | 5 |
| **Total** | **42** |

---

## 2. New Kickpass Penalty Phase

### Why

Kickpassing is to Viperball what the forward pass is to football. It deserves its own penalty vocabulary — not recycled kicking-game penalties. The kickpass involves a kicker launching the ball to a receiver in space, creating unique contact situations that don't exist in punting or place-kicking.

### Implementation

Added `"during_play_kick_pass"` as a new catalog key with 24 penalties. Updated `_check_penalties()` routing:

```python
elif play_type in ("kick_pass",):
    catalog_key = "during_play_kick_pass"
```

### Kickpass-Specific Infractions (10 new)

| Penalty | Yards | Team | Notes |
|---------|-------|------|-------|
| Contact on Kickpass Receiver | 15 | defense | Auto first down. Hit before ball arrives. |
| Roughing the Kickpasser | 15 | defense | Auto first down. Late hit on kicker after release. |
| Hit on Defenseless Kickpass Receiver | 15 | defense | Auto first down. Forceful hit during catch window. |
| Kickpass Interference | 15 | defense | Auto first down. Viperball's pass interference equivalent. |
| Offensive Kickpass Interference | 10 | offense | Pick plays, illegal screens for kickpass. |
| Illegal Kickpass Formation | 5 | offense | Wrong alignment for kickpass play. |
| Illegal Double Kickpass | 10 | offense | Loss of down. Two kickpasses on same play. |
| Kickpass Out of Bounds | 5 | offense | Loss of down. Deliberately uncatchable. |
| Shielding the Kickpass | 10 | offense | Illegal blocking for kickpass receiver. |
| Illegal Kickpass Touch | 5 | offense | Ineligible player touching kickpass. |

Plus 14 standard penalties that also apply during kickpass plays (holding, facemask, targeting, etc.).

---

## 3. Viperball-Specific Physicality Rules

### Philosophy

Viperball emphasizes rugby-style tackling and restricts dangerous play (RULES.md §25). The lateral-heavy game puts players in vulnerable positions that don't exist in traditional football — receiving a lateral with your back to defenders, catching a kickpass in open space with no blockers. These situations need specific protections.

### New Penalties

| Penalty | Phase | Yards | Rationale |
|---------|-------|-------|-----------|
| Roughing the Zeroback | run | 15 + auto 1st | Zeroback is the QB-equivalent. Deserves passer-style protection after releasing a lateral or kickpass. |
| Contact Before Lateral Arrives | lateral | 10 + auto 1st | Equivalent to hitting a receiver before the ball arrives. Lateral receivers are defenseless during the catch window. |
| Excessive Contact on Lateral Receiver | lateral | 15 + auto 1st | Crusher hits on players still securing a lateral. Protects the unique catching posture of lateral plays. |
| Illegal Viper Substitution | pre-snap | 5 | Viper jersey swap without proper substitution procedure. |
| Missing Viper Jersey | pre-snap | 5 | Viper not wearing the required distinct jersey. |

### RULES.md Update

Added a new "Viperball-Specific Physicality Rules" subsection under §23 Penalties explaining the defenseless-player doctrine for kickpass receivers, Zeroback protection, and lateral receiver contact rules.

---

## 4. NFHS Backfill

Cross-referenced against the SDCFOA (San Diego County Football Officials Association) official NFHS penalty summary. Added penalties that were standard in real football but missing from the catalog:

### 5-Yard Penalties Added
- Delay of Game (Defense), Illegal Shift, Disconcerting Signals, Player Out of Bounds at Snap, Illegal Numbering, Illegal Formation (Numbering Exception), Illegal Participation, Assisting the Runner, Offside on Kick, Illegal Free Kick Formation, Free Kick Out of Bounds, Player Out of Bounds During Kick, Illegal Touch

### 10-Yard Penalties Added
- Illegal Use of Hands (extended to lateral + kickpass phases), Illegal Bat (extended to kickpass phase)

### 15-Yard Penalties Added
- Blocking Below the Waist, Hurdling, Hands to the Face, Striking, Piling On, Fouling Out of Play, Illegal Contact Against Snapper, Kicker Simulating Being Roughed, Late Hit Out of Bounds, Throwing Punch, Fighting, Helmet-to-Helmet Contact, Removal of Helmet, Spiking the Ball, Continued Play Without Helmet, Provoking Ill Will, Obscene Language

---

## 5. "Too Many Men" During Live Play

Previously only a pre-snap dead-ball foul. Now appears in `during_play_run`, `during_play_lateral`, `during_play_kick_pass`, and `during_play_kick` phases at prob 0.001-0.002, reflecting the real-game scenario where a 12th player participates in a live play.

---

## 6. Final Counts

| Phase | Before | After | Delta |
|-------|--------|-------|-------|
| pre_snap | 8 | 19 | +11 |
| during_play_run | 10 | 27 | +17 |
| during_play_lateral | 12 | 34 | +22 |
| during_play_kick_pass | — | 24 | +24 (new) |
| during_play_kick | 7 | 24 | +17 |
| post_play | 5 | 18 | +13 |
| **Total entries** | **42** | **146** | **+104** |
| **Unique names** | **42** | **99** | **+57** |

The difference between total entries (146) and unique names (99) reflects penalties that appear in multiple phases (e.g., Holding, Facemask, Targeting appear in run, lateral, kickpass, and kick phases with phase-appropriate probabilities).

---

## 7. Probability Philosophy

All new penalties use conservative probabilities (0.001-0.005), lower than the most common existing penalties. The high-frequency penalties remain unchanged:

| Penalty | Prob | Phase |
|---------|------|-------|
| Holding (offense) | 0.018 | run |
| Holding (offense) | 0.016 | lateral |
| False Start | 0.014 | pre-snap |
| Offsides | 0.012 | pre-snap |
| Running Into Kicker | 0.010 | kick |

New Viperball-specific penalties like Contact on Kickpass Receiver (0.008) and Kickpass Interference (0.006) are set at moderate frequencies to reflect that these are common game situations in Viperball's kick-heavy meta, comparable to defensive pass interference rates in football.

Weather boost (+0.003 rain/snow/sleet, +0.002 heat) and late-game intensity (1.15x in final 5 min of Q4) apply uniformly to all new penalties via the existing `_check_penalties()` logic.

---

## 8. Files Changed

| File | Change |
|------|--------|
| `engine/game_engine.py` | Expanded `PENALTY_CATALOG` from 42 to 146 entries. Added `during_play_kick_pass` phase. Updated `_check_penalties()` routing for kick_pass play type. |
| `RULES.md` | Rewrote §23 penalty table (99 entries organized by phase). Added Kickpass Infractions section. Added Viperball-Specific Physicality Rules subsection. Added notes on ejection rules and live-play Too Many Men. |

---

## 9. What We Didn't Do

- **Ejection tracking.** Targeting, Fighting, and Throwing Punch should trigger automatic ejection. The `Penalty` dataclass doesn't have an `ejection` field. This is a follow-up.
- **Two-unsportsmanlike auto-ejection.** RULES.md §25 says two unsportsmanlike penalties = ejection. Not tracked per-player in the engine yet.
- **Penalty replay descriptions.** The play description generator doesn't have templates for the new penalty names. New penalties will show generic "Flag on the play" descriptions until templates are added.
- **Probability tuning.** All probabilities are first-pass estimates. Need to sim 1000+ games and check penalty-per-game rates against target (~12-14 penalties per game total, matching real football).
