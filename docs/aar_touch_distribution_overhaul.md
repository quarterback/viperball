# AFTER ACTION REPORT: Rating-Driven Touch Distribution System

**Date:** February 25, 2026
**Scope:** Engine touch distribution overhaul (`engine/game_engine.py`)

---

## 1. PROBLEM STATEMENT

The spread-the-love system was suppressing star player performance. LEAD backs averaged only 2.5 carries per game because:
- Ceiling/decay applied uniformly to all players, including designated feature backs
- Forced carry percentages were too conservative (35% for balanced offense)
- LEAD/COMPLEMENT backs were excluded from the carrier pool on play families whose position lists didn't include their position tag
- Receivers had no ordinal ranking — just binary STARTER/ROTATION — so target share was a coin flip among starters rather than rating-driven
- Stars on bad teams were held back because spread-the-love forced touches to weaker rotation players

## 2. CHANGES MADE

### A. LEAD/COMPLEMENT Exemption from Ceiling/Decay
- Previously: All players hit soft decay at 75% of ceiling, hard decay at ceiling (24 touches for balanced)
- Now: LEAD and COMPLEMENT backs are classified as "designated" and skip ceiling/decay entirely. Only rotation players are managed by spread-the-love. Stars eat until fatigue (energy system) naturally slows them down.

### B. Forced Carry Percentages Increased
- LEAD forced share raised from 35→54% (balanced), up to 62% (ground_pound)
- COMPLEMENT raised from 14→20% (balanced), up to 22% (ground_pound)
- Combined LEAD+COMP forced share: ~74% of carries on run-heavy teams

### C. LEAD/COMPLEMENT Always in Carrier Pool
- Previously: Carrier pool was built from `RUN_PLAY_CONFIG` position lists (e.g., DIVE = HB/SB/ZB). A Viper designated as LEAD would be excluded from most play families.
- Now: After position-based pool is built, LEAD and COMPLEMENT players are always injected if missing. They also receive a rating-based weight multiplier (5x for LEAD, 3x for COMPLEMENT, scaled by speed/power/agility) so their ratings directly drive volume.

### D. Ordinal Receiver Ranking (recv_rank 1-5)
- Previously: Top N receivers got binary STARTER tag, all competing equally
- Now: Receivers sorted by `recv_score` (hands × 1.3 + speed × 1.0 + lateral × 0.8) and assigned ordinal ranks 1 through 5. Each rank gets a weight share proportional to their actual rating, with a rank bonus (1.6x for #1, declining 0.2 per rank). Unranked receivers get 0.08x weight — they can catch a ball, but the offense isn't designed for them.
- Result: A 90-hands #1 receiver gets substantially more targets than a 60-hands #4, but the #4 isn't locked out — they can still have a breakout game.

### E. Decay Curve Softened (Rotation Players Only)
- Hard decay: 0.75^(overage+1) → 0.82^(overage+1)
- Soft decay trigger: 75% of ceiling → 85% of ceiling
- Soft decay strength: 35% max reduction → 25% max reduction
- Minimum weight floor: 0.03 → 0.02

### F. Starter Ceiling/Rotation Ceiling Raised
- Starter ceilings raised ~25% across all styles (balanced 24→30, ground_pound 30→38)
- Rotation ceilings lowered slightly (balanced 9→8) to further concentrate touches on stars

## 3. SUPPORTING CHANGES
- Added `game_recv_rank` field to Player dataclass (int, 0=unranked, 1-5=ranked)
- `assign_game_roles()` now sets ordinal recv_rank during pregame role assignment
- `recv_rank` included in player stat output for box score/export visibility
- Team files updated: Union College → Rutgers University, Meredith College → Penn State University (unrelated, same session)

## 4. RESULTS (20-game sample across diverse matchups)

| Metric | Before | After |
|--------|--------|-------|
| LEAD avg carries | 2.5 | 6.4 |
| LEAD carry share | ~13% | ~34% |
| LEAD avg touches | ~4 | 8.9 |
| LEAD avg AP yards | ~35 | 95.5 |
| LEAD 100+ yd games | rare | 45% |
| Top player avg AP yards | ~120 | 235.7 |
| Top player 150+ yd games | ~30% | 75% |
| Top player max AP yards | ~250 | 545 |

## 5. DESIGN PHILOSOPHY

The system now mirrors the stated philosophy: *ratings dictate volume*. A star on a 1-11 team should still put up monster numbers because the rating gap between her and the #5 option naturally funnels touches upward. Spread-the-love exists only to prevent random depth players from stealing touches that belong to the best players. LEAD/COMPLEMENT designations are permanent for the game — no ceiling, no decay, no artificial throttle. Only fatigue (the energy system) and blowout garbage time naturally reduce their workload.

## 6. KNOWN LIMITATIONS
- Total rushing carries per team per game are naturally low in Viperball (~20) because the sport splits offensive touches across rushing, kick passing, and laterals. Star dominance shows up in all-purpose yards rather than carry count alone.
- The `generate_game_summary()` reconciliation step overwrites team yards from player objects. Other stat consumers (box score, exports, UI) all flow through this path, so consistency is maintained.
- Receiver recv_rank is set pregame and doesn't shift mid-game based on performance. A cold #1 receiver keeps getting looks.

## 7. FILES MODIFIED
- `engine/game_engine.py` — Core touch distribution logic, player dataclass, role assignment, stat output
- `data/teams/rutgers.json` — Renamed from union_ny.json
- `data/teams/penn_state.json` — Renamed from meredith.json
- `data/conferences.json` — Updated team references
- `data/cvl_conference_directory.txt` — Updated team references
- `scripts/generate_new_teams.py` — Updated team references
- `replit.md` — Updated feature documentation
