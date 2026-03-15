# After Action Report: Bonus Possession Awarded to Wrong Team

**Date:** March 15, 2026
**Scope:** Engine bug fix — bonus possession granted to offense (INT thrower) instead of defense (intercepting team)
**Severity:** Critical — inverted a core game mechanic, corrupted all season stats involving bonus possessions
**Files Modified:** `engine/game_engine.py`, `docs/VIPERBALL_PLAYBOOK_DEVELOPMENT_BASELINE.md`, `AAR_2026-02-22_sport_balance_v2.3.md`

---

## Problem Statement

The bonus possession system — Viperball's pesäpallo-inspired interception mechanic — was awarding the bonus drive to the wrong team. Instead of rewarding the defense that made the interception with back-to-back possessions, the code was giving a free drive to the offense that threw the pick.

This is a game-breaking inversion. Under the bugged logic, throwing an interception was *advantageous*: your opponent gets one drive off the turnover, then you get a free makeup drive from the 20-yard line. A rational coaching AI should have been throwing interceptions on purpose.

## How It Happened

The bug was a single variable assignment at line 4286 of `game_engine.py`:

```python
# OLD (broken)
self.state.bonus_possession_team = drive_team
```

`drive_team` is the offense — the team whose drive just ended in an interception. The comment above it read "grant bonus possession to the team that threw it," confirming this wasn't a typo but a misunderstanding baked into the implementation.

The pesäpallo design intent (documented correctly in `docs/offensive-countermeasures.md` line 40) was always:

> An interception can create **back-to-back possessions** for the intercepting team (the possession you earned *plus* the ceded bonus possession afterward). That makes interceptions the most dangerous thing a leading team can give away, because it turns one mistake into a **sequence loss**.

The code did the opposite of what the design doc described.

### How the bonus flow was supposed to work

1. Team A (offense) throws an interception
2. Possession flips to Team B (normal turnover behavior)
3. Team B plays their drive with the intercepted ball
4. After that drive ends, Team B gets a **bonus possession** from the 20-yard line
5. Team B effectively gets back-to-back drives — the interception reward

### How the bonus flow actually worked (bugged)

1. Team A (offense) throws an interception
2. Possession flips to Team B (normal turnover behavior)
3. Team B plays their drive with the intercepted ball
4. After that drive ends, **Team A** gets a bonus possession from the 20-yard line
5. Team A is *rewarded* for throwing an interception with a free drive

## The Fix

```python
# NEW (correct)
intercepting_team = "away" if drive_team == "home" else "home"
self.state.bonus_possession_team = intercepting_team
```

Comments updated throughout the INT handling block to reflect correct attribution. The cancellation logic (INT-back neutralizes pending bonus) and half-expiry logic were already correct — only the initial assignment was wrong.

## Documentation Errors

Two docs repeated the same wrong description as the code:

- `docs/VIPERBALL_PLAYBOOK_DEVELOPMENT_BASELINE.md` line 45: "the intercepted team gets a bonus possession"
- `AAR_2026-02-22_sport_balance_v2.3.md` line 105: "the intercepted team receives a bonus possession"

Both corrected to describe the intercepting team receiving the bonus. The countermeasures doc (`docs/offensive-countermeasures.md`) already had the correct description and was not modified.

## Blast Radius

This is a critical bug that affects every game simulated since the bonus possession system was introduced. Every stat line involving bonus possessions is wrong.

### Stats that are corrupted

- **Bonus Possessions / Bonus Yards / Bonus Scores / Bonus Conv %** — attributed to the wrong team in every game. Teams that appeared to have high bonus conversion rates were actually the teams *throwing* interceptions, not making them.
- **Kill Rate (Compelled Efficiency)** — indirectly affected. The delta system itself is fine, but the bonus possession mechanic interacts with lead management. Teams that were "trailing" and receiving power play field position boosts were also getting punished by the inverted bonus logic when they intercepted passes. The two systems were partially canceling each other out.
- **Win Probability Added (WPA)** — every WPA calculation on a bonus drive attributed value to the wrong side.
- **Team records** — game outcomes themselves may have been different under correct bonus logic. An interception was effectively less punishing than intended (the thrower got a makeup drive), which dampened the swing value of turnovers across the entire league.

### Stats that are clean

- **Delta Yards / Adjusted Yards / Delta Drives** — the delta system is independent of bonus possessions and is not affected.
- **Total Yards / Rushing / Kick-Pass / Laterals** — offensive production stats are tracked per-drive and per-play, not affected by bonus attribution.
- **Penalties / Fumbles / Turnovers on Downs** — unrelated mechanics, clean.
- **Individual player stats (yards, TDs, touches, WPA)** — player-level tracking is per-play, so the actual production numbers are correct. Only the *labeling* of which drives were bonus drives is wrong.

## What Needs to Happen

1. **Full season re-simulation required.** No partial fix is possible — the wrong team receiving bonus drives changed game flow, score differentials, delta calculations within games, and therefore win/loss outcomes. The entire season is suspect.
2. **Do not publish any stats until re-sim is complete.** Bonus possession numbers on the stats site (including the Syracuse 7/7 100% figure) are attributed to the wrong team and should not be shared externally.
3. **After re-sim, audit a sample of box scores** to confirm bonus possessions now go to the intercepting team. Look for games with multiple INTs where the flow is clearly visible in the play log.

## Lessons Learned

- **The design doc was right. The code was wrong.** `offensive-countermeasures.md` described the correct behavior from the start. The implementation diverged from the spec, and neither the code comments nor the two other docs that parroted the wrong description caught the contradiction. When there's a conflict between a design doc and code, check which one matches the game design intent — don't assume the code is authoritative.
- **"intercepted team" is ambiguous.** The phrase "the intercepted team" could mean "the team that got intercepted" (offense) or "the team that intercepted" (defense). The original code and docs used this phrase and each reader interpreted it the way that felt natural. Future docs should use explicit language: "the team that threw the INT" vs. "the team that made the INT."
- **Inverted mechanics don't always surface in testing.** The bonus possession system still *functioned* — drives happened, stats were recorded, no crashes. The inversion made interceptions slightly less punishing rather than obviously broken. Without a specific test case asserting "after Team A throws an INT, the bonus goes to Team B," this class of bug is invisible to smoke testing.
- **Stats were not shared externally before this was caught.** That's the only reason this isn't worse. The instinct to hold off on publishing until the system was more mature turned out to be the right call.
