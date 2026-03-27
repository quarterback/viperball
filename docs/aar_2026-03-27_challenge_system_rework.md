# AAR: Challenge System Rework — No Perfect Information

**Date:** 2026-03-27
**Branch:** `claude/referee-bias-system-B6KAy`

---

## Problem

The original challenge system gave coaches perfect information. Two separate code paths existed:

1. `_coach_challenge()` — called ONLY on actual blown calls. The coach "knew" the call was wrong because the code only invoked this method when the engine had already determined the ref made an error. 90% challenge rate, 100% success rate.

2. `_coach_wastes_challenge()` — called after every play, randomly burning challenges on correct calls. The coach "knew" this was a waste because the code structure explicitly labeled it as such.

This is backwards. A real coach sees a play, has an instinct about whether the ruling was correct, and decides whether to bet a challenge on that instinct. They don't have access to the truth until replay tells them.

Additionally, the original system only challenged **penalties**. In real football (NFL), penalties CANNOT be challenged. Coaches challenge **plays**: spot of the ball, catch/no-catch, fumble rulings, and scoring plays.

## What Changed

### Architecture: One Decision Point, No Perfect Information

The two methods (`_coach_challenge` + `_coach_wastes_challenge`) were replaced with a single method: `_coach_considers_challenge(play)`.

This method runs after EVERY play in the drive loop. The coach evaluates the play and decides whether to challenge — without knowing if the ref got it right.

### What Can Be Challenged (Viperball Rules)

| Situation | Challenger | Base Rate | Trigger |
|-----------|-----------|-----------|---------|
| Spot of the ball | Offense | 12% | Gain within 2 yards of first-down marker |
| Late-down spot | Offense | 6% | 4th-6th down, within 4 yards of marker |
| Turnover on downs | Offense | 10% | TOD ruling (high stakes) |
| Fumble / INT ruling | Offense | 8% | Any turnover |
| Catch / no-catch | Offense | 4% | Incomplete kick pass |
| Scoring play | Defense | 6% | TD with ≤5 yards gained |

**NOT challengeable:**
- Penalties (same as NFL — fouls are judgment calls)
- Plays inside the 3-minute warning (auto-reviewed)

### Coach Decision Factors

The coach doesn't know the truth. Their decision is based on:

1. **Ref crew reputation** — worse crews (lower accuracy) make coaches more suspicious of every ruling. This is the closest a coach gets to "information" — it's scouting the officials, not reading the replay.

2. **Coach judgment quality** — `clock_management` as proxy. Bad coaches challenge MORE (lower threshold) but succeed LESS. Good coaches are selective (higher threshold) and succeed MORE. This creates the NFL-style spread.

3. **Game situation** — close games (within 9 points) and second-half plays increase challenge likelihood by 30-40%.

4. **Budget awareness** — checked against remaining challenges before deciding.

### Replay Determines the Truth

When a coach throws the flag:

- For **penalty challenges** (phantom flags): if `blown_call=True` → overturned. But penalties can't be challenged, so this only matters in the post-game review log.
- For **play challenges** (spot, catch, fumble, scoring): a success rate roll determines the outcome. The success rate scales with coach quality:
  - `clock_mgmt 0.0` → 25% success (Mike McDaniel tier)
  - `clock_mgmt 0.5` → 42% success (NFL average)
  - `clock_mgmt 1.0` → 60% success (Brian Daboll tier)

This means the same coach will sometimes be right and sometimes be wrong — exactly like real NFL data shows.

### Auto-Review Inside 3-Minute Warning

Inside the 3-minute warning (Viperball's equivalent of the NFL 2-minute warning), plays are auto-reviewed by officials. Coaches cannot throw challenge flags during this period.

## Results (100-game sample)

| Metric | Value |
|--------|-------|
| Challenges per game | 1.58 |
| Games with challenges | 80% |
| Success rate | 43.7% |
| Challenges overturned | 69 |
| Challenges failed | 89 |

### Challenge Breakdown by Reason

| Reason | Count | Description |
|--------|-------|-------------|
| Catch | 54 | Incomplete kick pass disputed |
| Turnover | 49 | Fumble/INT ruling disputed |
| Spot | 38 | Ball placement near first-down marker |
| Scoring | 17 | Close touchdown disputed by defense |

### NFL Comparison

| Metric | Viperball | NFL Average |
|--------|-----------|-------------|
| Success rate | 43.7% | ~40-45% |
| Challenges/game | 1.58 | ~1-2 |
| Games with challenges | 80% | ~70-85% |
| Best coach success | ~60% | 71% (Daboll) |
| Worst coach success | ~25% | 21% (McDaniel) |

## Key Design Principle

> The coach is always sure they're right — they just sometimes aren't.

The system never tells the coach "this is a bad challenge." The coach evaluates the play through their own lens (ref reputation, game situation, instinct), throws the flag with confidence, and finds out the truth when replay announces the ruling. Sometimes their read is correct and they look brilliant. Sometimes it's wrong and they look like McDaniel.

## What's Not Done Yet

- **Failed challenge = lost timeout**: NFL penalizes failed challenges with a timeout loss. Not implemented yet.
- **Third challenge earned**: NFL gives a third challenge if the first two succeed. Could add this.
- **Challenge success tracking on coach cards**: The referee card tracks challenges, but the coach card doesn't yet track their career challenge success rate.
- **Announcer-style narrative**: "Coach Smith throws the red flag... and after review, the ruling on the field is OVERTURNED!" Not generated in play descriptions yet.
