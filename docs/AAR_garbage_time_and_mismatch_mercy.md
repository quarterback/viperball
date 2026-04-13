# AAR: Garbage-Time Scoring & Mismatch-Mercy Rotation

**Date:** 2026-04-13
**Branch:** `claude/field-goal-strategy-analysis-rTVU9`
**Commit:** `27dde73`
**Files Changed:** `engine/game_engine.py` (+192 / −14 lines)

---

## Origin: The Illinois 0.5 Box Score

The investigation started from a real sim artifact — an Illinois @ Rutgers Week 6 game that finished **103.0 – 0.5**. Illinois, the statistically superior team on paper (avg OVR 84.9 vs Rutgers' 71.4), got blown out in an upset *and* failed to put a single point on the scoreboard despite the Delta Yards system spotting them drive after drive starting at the opponent's 20-yard line.

The 0.5 is a bookkeeping artifact, not a score. The question was: how did this happen? And once we understood it, a follow-on: why does the coaching AI on the *winning* side of mismatches still leave its starters in to get hit?

Three distinct-but-related logic gaps emerged, each with a realistic coaching analog that the engine didn't model.

---

## Problem 1: The Unreachable Chip Shot

Illinois started **five** drives at OPP 20 — a 30-yard field goal is a near-automatic chip shot in Viperball's place-kick model (`fg_distance <= 35`, `pk_success >= 0.75`). They converted zero of them.

### Why, mechanically

Three interlocking rules formed a cage:

1. **Downs 1–3 never kick.** `select_kick_decision()` returns `None` on every early down — the AI saves kick calls for 5th and 6th.
2. **Down 4 is "ALWAYS KEEP DRIVING."** Added in V3's 4th-down redesign to stop unnecessary bail-out kicks when 5th and 6th remain.
3. **The Q4 futility rule (V3.1) blocks kicks that can't tie or win.** Added after the Arizona State championship debacle where the AI kicked a 3-pt FG while trailing by 5.5. The rule: if `deficit > 3`, `pk_futile = True`; if `deficit > 5`, `dk_futile = True`.

Drive 24 is the canonical shutout-preservation sequence — Q4, down by 102+, ball at OPP 15:

```
4:44  OPP 20  1&20  kick pass INCOMPLETE      ← rule 1: no 1st-down kicks
4:37  OPP 20  2&20  trick play → 3            ← rule 1
4:17  OPP 17  3&17  kick pass INCOMPLETE      ← rule 1
3:53  OPP 17  4&17  speed option → 2          ← rule 2: always drive on 4th
3:35  OPP 15  5&15  kick pass SACKED -3       ← rule 3: pk_futile, dk_futile
3:16  OPP 18  6&15  kick pass INTERCEPTED     ← rule 3: best_kick = None
```

At 5-and-15 from OPP 15, a place kick is a 25-yard chip shot. The AI refused because a 3-point FG couldn't close a 102-point gap. It also refused the snap kick (can't tie either). `best_kick = None`, so 5th-down fell through to "advance and kick on 6th," and 6th-down went for the TD. Interception. Shutout preserved.

### Root cause

The V3.1 futility rule has no floor. It treats "down 4" and "down 104" identically — both fail `deficit <= 3`. The original design intent was *"don't kick when points can't win,"* but that collapses into *"never kick when badly losing,"* which is wrong in every real football code. When the game is mathematically gone, the coaching goal shifts from *win* to *don't get shut out*.

### Fix: `_is_garbage_time_trailing()`

A mirror of `_is_blowout()` from the trailing team's perspective:

```python
def _is_garbage_time_trailing(self) -> bool:
    score_diff = self._get_score_diff()
    if score_diff >= 0:
        return False
    deficit = abs(score_diff)
    if self.state.quarter >= 3:
        return deficit >= 20
    if self.state.quarter == 2 and self.state.time_remaining <= 300:
        return deficit >= 25
    return False
```

Three integration points:

1. **Futility inversion** — when `garbage_trailing`, `dk_futile` and `pk_futile` are forced to False regardless of deficit. No kick can win, but any kick beats a shutout.
2. **4th-down snap kick** — allowed in range (`fg_distance <= dk_comfort`, `dk_success >= 0.50`). Chip-shot FG also allowed if inside 35 yds with `pk_success >= 0.75`. Previously: always keep driving.
3. **5th-down kick** — snap kick allowed at slightly looser thresholds (`dk_success >= 0.40`), and FG allowed inside 40 yds with `pk_success >= 0.65`. Previously: save for 6th.

### Verification

20-sim Illinois @ Rutgers batch after the fix: **14 blowouts, 0 shutouts**, trailing-team scores ranging 18.0 – 72.5, average 41.8. Pre-fix, 0.5 was a plausible outcome. Post-fix, trailing teams consistently put up garbage-time points.

---

## Problem 2: Starters Left Exposed in Mismatch Blowouts

A separate, user-raised concern: even when the existing `_blowout_tier` system correctly ramps backup rotation for the leading team, it doesn't do so early enough in the classic non-conference-cupcake scenario. A Power-6 program up 35 at halftime against an FCS opponent has no reason to keep starters on the field — but the existing thresholds (Q3+ 35 = tier 3) mean starters stayed in well into Q3 and could take unnecessary injury hits.

The user's framing: *"this is an early season tool to keep teams from burning starters in non-conference games against widely outmatched opponents."*

### Fix: Talent-gap-aware tier escalation

Two new pieces:

**`_team_avg_overall(team)`** — mean `player.overall` across the roster.

**`_leading_team_talent_edge()`** — OVR delta between leading and trailing teams, *signed from the leading team's POV*:
- Positive = leading team is the favorite (true mismatch).
- Negative = leading team is the underdog (upset in progress).
- Zero = tied / evenly matched.

Then `_blowout_tier()` applies a mercy bump only when `talent_edge >= 6.0`:

| Trigger | Pre-fix tier | Post-fix tier |
|---|---|---|
| Late Q2, 30+ lead, mismatch | 2 | **3** |
| Opening minute Q3, 30+ lead, mismatch | 2 | **3** |
| Any existing blowout tier ≥1, mismatch | N | **min(3, N+1)** |

Critically, the bump is **suppressed during upsets**. A weaker team leading by 30 doesn't trigger — their starters stay in to close out the win. The user's explicit requirement: *"if the lead dissipates, that would go away"* is handled naturally by the score-based baseline tier computation.

### Defense, too

The user noted this should apply to both sides of the ball. The mismatch bump deliberately targets tier 3 (not tier 2), which was already wired to pull both skill-position and defensive starters. Offense and defense rest together in a clear non-conference cupcake.

### Verification

| Scenario | Pre-fix tier | Post-fix tier |
|---|---|---|
| Favorite up 40 in Q3 | 3 | 3 (already max) |
| Favorite up 32, late Q2 | 2 | **3** (offense + defense pulled at halftime) |
| Underdog upset, weaker team up 32 at half | 2 | 2 (no mercy — they earned it) |
| Trailing team (negative score diff) | 0 | 0 (unchanged) |

---

## Problem 3: The Backup ZB That Never Comes In

The third gap: Illinois's starting Zeroback threw 3 kick-pass INTs at 22% completion and never got pulled. The existing V2 performance-benching hook fires at **3+ total turnovers** (fumbles + INTs) — which technically caught the 3-INT case, but only *after* the third INT happened, by which point the game was over.

The user wanted a sooner, softer trigger — the Viperball equivalent of a real-world QB change-of-pace swap after two picks. Like pulling a struggling goalie.

### Fix: "Change-of-pace" ZB hook with talent-gap guard

New clause in `evaluate_coaching_substitutions` that fires when:
- Position is Zeroback
- `kp_ints >= 2` (even without any fumbles)
- Completion% below 40% on 6+ attempts
- A comparable backup is available
- Quarter-scaled probability fires (Q1 30%, Q2 50%, Q3+ 70%)

The user's key constraint, quoted directly:

> *"I'm not gonna bring the OVR 40 backup to replace the OVR 77 zb IN A CLOSE game even if they're getting picked off a lot because that can't help us but if OVR 80 and OVR 78 zb exist, that's a different story potentially."*

That translated to a game-state-aware talent gap tolerance:

| Game state | Max OVR gap for swap |
|---|---|
| Close game (\|diff\| ≤ 14) | 5 |
| Loose game / blowout (\|diff\| > 14) | 12 |

Rationale: in a close game, benching a better starter for a meaningfully worse backup hurts your win probability. Near-peer only. In a blowout, the calculus changes — you're not giving up a winnable game to develop the backup or give the starter a break.

Rosters in the data already reflect realistic depth:

- Rutgers: 3 ZBs at 72/71/68 (all gaps within "close game" tolerance)
- Illinois: 2 ZBs at 87/83 (gap 4, close-game-eligible)

### Verification

| Scenario | Fire rate / 100 |
|---|---|
| Close game, 4-OVR gap backup, Q3 | 65 (target ~70%) |
| Close game, 45-OVR gap (mocked bad backup) | 0 (protects starter) |
| Blowout, 45-OVR gap | 0 (gap exceeds blowout tolerance) |

The hook fires in exactly the window it should, and stays silent when the swap would be strictly worse for the team.

---

## Design Notes

**Q: Why are the garbage-time thresholds the same as blowout thresholds?**

Symmetry. When one team is `_is_blowout()`, the other should be `_is_garbage_time_trailing()` — they're the same game state viewed from opposite sidelines. Using different thresholds would create awkward windows where one team is pulling starters but the other is still playing to win.

**Q: Why 6 OVR points as the "mismatch" threshold?**

Empirically, a 6-point average-roster OVR gap roughly corresponds to a "big favorite" in CVL prestige tiers — the kind of Power-6-vs-FCS or mid-major-vs-cupcake matchup where the talent gulf is obvious at a glance. Smaller gaps (1–5 OVR) are competitive enough that coaches might still play their starters to close out a win cleanly.

**Q: Why not also trigger the change-of-pace hook on fumbles?**

The existing `fumbles >= 2` trigger already benches players for "fumbles" as a reason. Fumbles are a ball-security issue; INTs are a decision-making issue. The "change of pace" concept is specifically about the latter — a different QB who throws the same routes but reads the defense differently. The distinction is visible in game narration: "benched for fumbles" vs "change of pace swap" tell different stories.

**Q: What happens when the lead dissipates mid-game?**

The tier check runs between drives. If the trailing team mounts a comeback and the score differential drops below the tier threshold, the baseline tier drops back to 0 — no new starters get benched. Players already benched stay benched (`duration="game"`), but no *further* protection triggers. This is the correct behavior: a comeback re-engages the game, and the teams that already pulled starters have to live with that choice.

---

## What Was Not Changed

- **V3.1 championship futility logic** — unchanged for non-garbage-time Q4 situations. A team trailing by 5.5 with 1:00 left still correctly refuses a 3-point FG.
- **Red zone "always chase the TD" rule (`fp >= 90`)** — unchanged. Garbage-time doesn't override the 9-point-TD preference in the red zone.
- **Existing `turnovers` hard-benching** (3+ total turnovers) — unchanged. The new change-of-pace hook fires *before* this threshold in the 2-INT-without-fumbles window.
- **Defense-side garbage time** — defenses don't "give up" differently in blowouts; the late-down clamp still fires at full intensity.
- **Fast-sim path** — `fast_sim.py` doesn't model per-play kick decisions, so no changes needed.

---

## Commits

| # | Hash | Summary |
|---|------|---------|
| 1 | `27dde73` | Add garbage-time scoring logic and mismatch-mercy rotation |

---

## Lessons

1. **Every "don't do X" rule needs a lower bound.** The V3.1 futility rule was technically correct (don't kick when it can't win) but its unstated premise (*"the game is still winnable"*) broke down in extreme cases. Any rule that says "don't do X because X can't achieve Y" should check whether Y is even achievable — and if not, reconsider whether the rule applies.

2. **Symmetric game states deserve symmetric logic.** The engine had `_is_blowout()` (leading-team POV) for over a year without a trailing-team counterpart. Once the garbage-time problem surfaced, the fix was obvious: add the mirror helper. If a game-state query exists for one team, it should exist for both.

3. **Talent-gap awareness prevents nonsensical rotations.** The first pass of the change-of-pace hook didn't check backup quality — a pure "2 INTs and low completion" trigger. The user's correction was immediate and correct: don't bench a good player for a scrub in a winnable game. The fix — game-state-scaled OVR tolerance — is a general-purpose pattern that probably belongs in other performance-benching hooks too.
