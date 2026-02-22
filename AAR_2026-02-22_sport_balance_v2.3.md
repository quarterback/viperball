# After-Action Report: V2.3 Sport Balance — Turnovers, Breakaways, Defensive Bonus Possession

**Date:** 2026-02-22
**Branch:** `claude/balance-sport-mechanics-g67sa`
**Scope:** Five interconnected balance changes to increase chaos, big-play frequency, and defensive agency

---

## Objective

Viperball as a sport was too orderly. Drives were grinding forward with low turnover rates, laterals were too efficient for a chaos play, big breakaway plays (70+ yards) were nearly nonexistent, interceptions were a rarity, and the defense had no equivalent of the pesäpallo possession mechanic that the offense already benefits from. This workstream addressed five specific interventions from playtesting:

1. Dramatically increase turnovers
2. Reduce lateral chain efficiency by 20%
3. Make 70+ yard breakaway plays routine across all phases
4. Raise interception rate to ~5% with explosive return potential
5. Implement defensive bonus possession — interceptions give the ball back (pesäpallo for defense)

---

## Starting State

- Fumble rates: 0.6–1.1% base per run play family
- Lateral base yards: `gauss(1.5, 1.0)` + `0.5/lateral` chain bonus
- Lateral fumble: 8% base + 4%/extra lateral
- Lateral interception: 0.5% base per lateral, capped 0.1–1.5%
- Kick pass INT rate: 1% of incompletes → ~0.37% global
- Breakaway: required 8+ yard initial gain, max 25 extra yards
- EXPLOSIVE_CHANCE: 5–18% per play family
- No defensive bonus possession mechanic
- 70+ yard plays: nearly zero per game
- Total turnovers: ~1–2 per game

---

## Work Performed

### 1. Fumble Rate Overhaul (`RUN_PLAY_CONFIG`)

Tripled fumble rates across all seven run play families:

| Play Family | Before | After |
|---|---|---|
| Dive Option | 0.6% | 1.8% |
| Power | 0.7% | 2.0% |
| Sweep Option | 0.8% | 2.4% |
| Speed Option | 0.8% | 2.4% |
| Counter | 0.7% | 2.2% |
| Draw | 0.7% | 2.0% |
| Viper Jet | 1.1% | 3.0% |

Viper Jet retains the highest fumble risk — fitting for its high-reward, high-chaos identity. Lateral fumble base rate also raised from 8% → 12%, with per-lateral escalation from +4% → +5%.

### 2. Lateral Efficiency Reduction (–20%)

Two levers pulled:
- **Base yards**: `gauss(1.5, 1.0)` → `gauss(0.8, 1.0)` — center shifted down 47%
- **Chain bonus**: `0.5/lateral` → `0.4/lateral` — 20% reduction

Combined effect: a 3-lateral chain previously expected ~3.0 yards now expects ~2.0. Laterals remain viable for first-down chains (especially with breakaway upside) but are no longer a reliable yardage engine. They're chaos spice.

### 3. Breakaway System Overhaul

Three changes to make 70+ yard plays routine:

**a) EXPLOSIVE_CHANCE doubled+**

| Play Family | Before | After |
|---|---|---|
| Dive Option | 5% | 14% |
| Power | 6% | 16% |
| Sweep Option | 10% | 24% |
| Speed Option | 9% | 22% |
| Counter | 12% | 26% |
| Draw | 7% | 18% |
| Viper Jet | 15% | 30% |
| Lateral Spread | 12% | 26% |
| Trick Play | 18% | 32% |
| Kick Pass | — | 22% (new) |

**b) Breakaway trigger lowered**: 8+ yards → 5+ yards, with tiered bonus chances (+8% at 7+ yards, +15% at 10+ yards).

**c) Extra breakaway yards massively increased**:

| Initial Gain | Before | After |
|---|---|---|
| 12+ yards | 8–25 extra | 40–85 extra |
| 8–11 yards | 5–18 extra | 25–70 extra |
| 5–7 yards | N/A (didn't trigger) | 15–55 extra |

**d) Kick pass breakaway check added**: Completions now run through `_breakaway_check()`. This creates the "deep ball catch → house call" play that was completely missing. A 14-yard kick pass + 7 YAC = 21 yards, which now triggers a breakaway check with a 22% base chance. If it fires: +25-70 more yards = 46-91 yard play.

### 4. Interception Rate → ~5%

**Kick pass INTs**: `int_chance` on incompletes raised from 1% → 10%. With ~40% incompletion rate, this produces `0.40 × 0.10 = 4–5%` global INT rate on kick passes. Batch sim confirmed 5.0% actual.

**Lateral INTs**: Base per-lateral raised from 0.5% → 3.0%, clamped range widened from [0.1%, 1.5%] → [1.5%, 6.0%]. Batch sim confirmed 10.6% per lateral play.

**INT return yards boosted**: Both kick pass and lateral interception returns shifted from `gauss(30 + talent*20, 12)` → `gauss(50 + talent*30, 18)`. This means the average INT return is 50-80 yards (up from 30-50), with pick-sixes as a genuine threat.

### 5. Defensive Bonus Possession (Pesäpallo for Defense)

The signature rule change of this workstream. Modeled on how the offense's pesäpallo rule works for snap kicks, but applied to the defense via interceptions.

**Rule**: When a team throws an interception (kick pass or lateral), the intercepted team receives a **bonus possession** after the intercepting team's next drive. The bonus drive starts from the intercepted team's own 25-yard line.

**Cancellation conditions**:
- **INT-back**: If the intercepting team throws an interception on their drive, the bonus is cancelled. No new bonus is created — it neutralizes.
- **Half expires**: Bonus does not carry over between halves.

**Implementation**: Three-component system:

1. **`GameState.bonus_possession_team`** — Set in `simulate_drive()` when an INT occurs. Stores the team that should receive the bonus.

2. **`_bonus_drives_remaining` countdown** — In the `simulate_game()` loop, when `bonus_possession_team` is set:
   - Phase 1: Start countdown at 1 (intercepting team gets their drive first)
   - Phase 2: Decrement after intercepting team's drive
   - Phase 3: When countdown hits 0, force possession to bonus team at their 25

3. **INT-back detection** — In `simulate_drive()`, if an INT occurs while a bonus is pending (`_bonus_recipient` is set and `_bonus_drives_remaining >= 0`), both the pending bonus and the new INT are cancelled.

---

## Files Modified

| File | Lines Changed | Summary |
|---|---|---|
| `engine/game_engine.py` | +125 / -44 | All five balance changes in one commit |

---

## Key Metrics (30-game batch sim)

| Metric | Before | After | Target | Assessment |
|---|---|---|---|---|
| Turnovers/game | ~1.5 | 4.5 | More | Hit |
| Fumbles/game | ~0.5 | 1.1 | More | Hit |
| INTs/game | ~0.5 | 3.4 | More | Hit |
| KP INT rate | 0.37% | 5.0% | ~5% | Hit |
| Lateral INT rate | ~1% | 10.6% | Higher | Hit |
| 30+ yard plays/game | ~2 | 11.7 | More | Hit |
| 50+ yard plays/game | ~0.5 | 8.2 | More | Hit |
| 70+ yard plays/game | ~0 | 3.0 | Routine | Hit |
| 80+ yard plays/game | 0 | 1.3 | Possible | Hit |
| 90+ yard plays/game | 0 | 0.2 | Rare | Hit |
| Avg drives/game | ~28 | 35.4 | — | Up (bonus possessions) |
| Avg combined score | ~100 | 166.5 | — | Higher (more drives) |

---

## Architecture Decisions

1. **Fumble rates tripled, not doubled** — The chaos level needed to be dramatic. At 2x, batch sims still produced only ~0.8 fumbles/game. At 3x, combined with the INT increases, total turnovers hit 4.5/game which feels right for a sport this chaotic. Ball security (hands attribute) and coaching discipline still modulate the rate down for elite players/programs.

2. **Breakaway extra yards uncapped** — The old 25-yard cap prevented house calls by design. But the user's feedback was explicit: 70+ yard plays should be routine. Removing the cap and raising the floor to 15–85 extra yards means a 12-yard run can become a 97-yard TD. This is intentional — viperball is an open-field sport with lateral motion; once a defender is beaten, nobody else is in position.

3. **Kick pass breakaway added as a new mechanic** — Kick passes previously had no explosive play path. A completion was always `kick_distance + YAC - tackle_reduction` = 8–26 yards max. Adding the breakaway check creates the "deep ball" archetype that was missing. The 22% EXPLOSIVE_CHANCE for kick passes is justified because the receiver has already beaten coverage.

4. **INT rate set via incomplete conditional, not flat rate** — Setting `int_chance = 0.10` on incompletes (rather than 0.05 on all kick passes) means good kickers who complete more passes also throw fewer INTs. This creates a natural skill differentiation: an 80% completion kicker faces `0.20 × 0.10 = 2%` INT risk, while a 55% kicker faces `0.45 × 0.10 = 4.5%`. Skill matters.

5. **Bonus possession uses a countdown, not immediate trigger** — The intercepting team must complete their drive before the bonus fires. This prevents the bonus from interrupting the natural flow of the game. The 3-phase countdown (`set → arm → trigger`) ensures the intercepting team gets their earned possession first.

6. **INT-back cancels without creating new bonus** — A strict reading would allow chain bonuses (A throws INT → bonus for A, B throws INT-back → bonus for B). This was rejected to avoid infinite possession ping-pong. INT-back simply neutralizes — both teams ate their INT and move on.

7. **Bonus clears at halftime** — Carrying a bonus between halves would create confusing possession sequences where Q3 starts with an extra drive from Q2 events. Clean slate each half.

---

## What Worked

### The five changes are synergistic, not independent
Higher fumble rates + higher INT rates = more turnovers. More turnovers + bonus possession = more total drives. More total drives × higher breakaway rates = more 70+ yard plays per game. The combined effect is greater than the sum of parts — the sport feels fundamentally different.

### Kick pass breakaway creates a missing play archetype
Before this change, the kick pass was a short-to-medium range possession play (8–26 yards). Now it can produce 80+ yard TDs on catch-and-run plays. This single addition created more 70+ yard plays than all the run-play breakaway tuning combined, because kick passes are ~35% of all plays.

### The bonus possession rule is clean and intuitive
"You get the ball back after an interception, unless they intercept you back or the half ends." That's a one-sentence rule that any fan can understand. The implementation complexity (3-phase countdown, INT-back detection) is entirely hidden from the game surface.

---

## What Didn't Work / Risks

### Combined scoring may be too high
166.5 avg combined points is significantly above prior levels (~100). The primary driver is the bonus possession system adding ~7 extra drives per game. This may need a tuning pass — possibly reducing the bonus starting position from the 25 to the 15, or only granting bonus possession on kick pass interceptions (not lateral INTs).

### Lateral INT rate (10.6%) may be too punishing
Lateral chains are already risky (12% fumble base + escalation). Adding 3% INT chance per lateral on top means a 4-lateral chain faces `1 - (0.97^4)` = 11.5% INT chance PLUS 12%+ fumble chance = ~23% total turnover risk. This may push lateral usage toward extinction for conservative teams. Monitor in next round.

### No UI/narrative support for bonus possession
The bonus possession triggers silently — there's no play log entry or narrative text announcing "BONUS POSSESSION" to the user. The drive log shows consecutive same-team drives, but without context it's confusing. Next workstream should add a synthetic play entry or drive annotation.

---

## What's Next

### Immediate
- **Add bonus possession narrative** — Synthetic play/drive annotation when bonus triggers ("BONUS POSSESSION — Gonzaga gets the ball back after the interception")
- **Monitor scoring levels** — 166 combined may be too high; consider bonus from the 15 instead of 25

### Short-term
- **Lateral survival audit** — With 23%+ total turnover risk per lateral chain, check if lateral_spread offense style is still viable or if it's been killed
- **Deep ball YAC tuning** — Kick pass breakaway creates 80+ yard plays, but the YAC formula (3–12 for short kicks, 0–5 for long) may need adjustment so "deep balls" (long kicks) have more breakaway potential than short screens
- **INT return TD rate check** — With 50+ yard mean returns, what % of INTs are pick-sixes? If >50% this may need dampening

### Medium-term
- **Offensive response to high INT rate** — Teams should become more conservative when leading late; the coaching decision AI may need INT-awareness
- **Bonus possession stat tracking** — Track bonus drives in box score / game summary for analytics
- **Defensive identity scoring** — INTs now earn bonus possession; combined with the existing Bell (½ pt for fumble recovery), defense has meaningful agency. Consider adding defensive prestige bonuses for high-INT teams.

---

## Lessons Learned

**Explosive plays need explicit pathways, not just probability bumps.** Doubling EXPLOSIVE_CHANCE and raising breakaway yards helped, but the biggest impact came from adding the breakaway check to kick passes — a play type that previously had no explosive pathway at all. The missing mechanic was more important than the tuning of existing ones.

**Defensive agency makes the sport better.** The bonus possession rule gives defense its own version of the pesäpallo mechanic. Before, interceptions were just turnovers. Now they're possession multipliers — a defense that forces an INT not only stops the drive but earns their team an extra shot. This creates a clear "defense wins championships" narrative pathway that the sport previously lacked.

**Balance changes compound.** Five "moderate" adjustments produced a dramatic shift in game character. The combined scoring went from ~100 to ~167 — a 67% increase. Each individual change seemed reasonable in isolation, but the interaction effects (more drives × more breakaways × more turnovers) multiplied. Future balance passes should batch-sim after each individual change, not just after all changes together.
