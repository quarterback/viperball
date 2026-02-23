# Case Study AAR: The Diving Wing Archetype

## The Shutdown Corner Problem

Every level of football has one — the defensive back who lives to disrupt the kicking game. In the NFL, it's the edge rusher who times the snap count and gets a hand on the field goal. In college, it's the athletic safety who crashes off the corner. In Viperball, where drop kicks are a primary scoring weapon (4-6 per team per game), the ability to block a kick isn't just a special teams curiosity — it's a defensive philosophy.

The question was: how do you model a kick-block specialist in a sport where kicking is woven into the offensive identity?

## Version 1: The Unicorn (Too Rare)

The first implementation set the bar too high. A Diving Wing needed:
- Tackling ≥ 82
- Speed ≥ 88  
- Kicking awareness ≥ 60

These thresholds described an elite athlete — a flanker who could tackle like a linebacker, run like a sprinter, and read a kicker's release like a punting coach. Across 187 teams, roughly zero players qualified from pre-generated rosters. The archetype existed in the code but almost never appeared on the field.

The block bonus was flat: +0.8% on top of the 2.5% base rate. You either were a Diving Wing or you weren't. A flanker with 81 tackling and 87 speed — one tick below each threshold — contributed nothing to the block game.

**Result**: Blocked drop kicks happened at 2.5% (the base rate), entirely uninfluenced by personnel. The Diving Wing was a ghost archetype.

## The Insight: Every Team Has a Shutdown Corner

The user's observation was simple and correct: *"I think every level has their own version of a shutdown corner. It should just be indexed higher based on meeting attribute criteria."*

This reframed the design problem entirely. The question wasn't "does this team have an elite kick-block specialist?" — it was "how good is this team's best kick-block option?" A Division III corner with 74 tackling and 82 speed can still time a kicker's release. They're just not as good at it as the All-American with 92 tackling and 95 speed.

## Version 2: The Scaled System

### Lowered Floor

New thresholds to qualify as a Diving Wing:
- Tackling ≥ 72 (was 82)
- Speed ≥ 80 (was 88)
- Kicking awareness ≥ 45 (was 60)

These describe "athletic flanker with defensive instincts and some understanding of kicking mechanics" rather than "generational talent." Average flanker attributes across the league sit at tck 72, spd 77, kick 71 — meaning the threshold is right at the population median for tackling, slightly above for speed, and well below for kicking. A reasonable bar.

### Priority Ordering Fix

Critically, the Diving Wing check was moved from first priority to fourth in the flanker archetype cascade:

1. **Speed Flanker** (spd ≥ 93) — Pure burners stay burners
2. **Power Flanker** (tck ≥ 80, stam ≥ 88) — Physical run-blockers keep their role
3. **Elusive Flanker** (lat ≥ 88, spd ≥ 85) — Lateral-chain specialists stay
4. **Diving Wing** (tck ≥ 72, spd ≥ 80, kick ≥ 45) — Defensive-minded flankers
5. **Reliable Flanker** — Everyone else

This means Diving Wings are flankers who have athletic defensive profiles but aren't elite offensive weapons. They're the players who make their living on the other side of the ball — exactly the kind of player who ends up as a kick-block specialist in real football.

### Scaled Block Bonus

Instead of a binary +0.8%, the block bonus now scales with an attribute index:

```
tck_score = (tackling - 70) / 30       # weight: 45%
spd_score = (speed - 78) / 22          # weight: 35%  
kick_score = (kicking - 40) / 50       # weight: 20%

attr_index = tck_score × 0.45 + spd_score × 0.35 + kick_score × 0.20
block_bonus = 0.004 + attr_index × 0.008
```

The bonus ranges from **+0.4%** (barely qualifying) to **+1.2%** (theoretical maximum). In practice:

| Tier | Attr Index | Bonus | Effective Block Rate | Description |
|---|---|---|---|---|
| Low | 0.0–0.3 | +0.55% | ~3.1% | Scrappy, gets a hand up sometimes |
| Mid | 0.3–0.6 | +0.64–0.88% | ~3.2–3.4% | Solid contributor, times it well |
| High | 0.6–0.85 | +0.88–1.08% | ~3.4–3.6% | Legitimate kick-block threat |
| Elite | 0.85–1.0 | +1.08–1.2% | ~3.6–3.7% | Shutdown specialist, alters kicking gameplan |

## Measured Results (30-game batch)

| Metric | V1 (Unicorn) | V2 (Scaled) |
|---|---|---|
| Teams with a Diving Wing | ~0% | **72%** |
| Avg DW per team | ~0 | **2.4** |
| Player tier distribution | N/A | 6% Low, 90% Mid, 4% High |
| Overall DK block rate | 2.5% (base only) | **2.6%** (base + DW bonus) |

The overall block rate barely moved (2.5% → 2.6%) because the DW bonus is intentionally modest — this is a rare, high-impact play. But the important shift is that **72% of teams now have at least one player contributing to that probability**, and the best Diving Wings meaningfully outperform the worst ones.

## Design Lessons

### 1. Thresholds Create Cliffs, Indices Create Gradients

The V1 approach (hard threshold → flat bonus) created a cliff where one attribute point was the difference between "specialist" and "nothing." The V2 approach (soft threshold → scaled index) creates a gradient where every point of tackling, speed, and kicking awareness contributes proportionally. This mirrors reality: there's no magic number where a player suddenly becomes a kick-block specialist.

### 2. Archetype Priority Protects Offensive Identity

By placing DW fourth in the flanker cascade, the system ensures that elite offensive flankers keep their offensive identities. A 95-speed flanker is a Speed Flanker who happens to be fast enough to block kicks; they're not reclassified as a defensive specialist. DW captures the flankers who are "tweeners" — too physical for the elusive role, too slow for the speed role, but athletic and instinctive enough to disrupt kicks.

### 3. Small Bonuses, Large Population = Emergent Flavor

A +0.6% block bonus on one player doesn't change the game. But when 2-3 players per team carry that bonus, and some teams have High-tier Diving Wings while others have Low-tier ones, it creates emergent matchup flavor. A team with an elite DW might cause an opponent to think twice about drop-kicking from 40 yards — not because the block rate is dramatically higher, but because the narrative pressure exists.

### 4. "Every Level Has Their Version"

The user's framing — that every level of competition has its own version of a specialist — is a powerful design principle. It argues against unicorn archetypes that only appear on elite rosters. Instead, the archetype should be accessible to everyone, with excellence indexed to attributes. This keeps the mechanic relevant across the full 187-team league rather than being a feature only 5-10 teams ever see.

## Files Modified

| File | Change |
|---|---|
| `engine/game_engine.py` | Lowered DW thresholds, reordered flanker cascade, replaced flat `dk_block_bonus` with scaled attribute index calculation |
