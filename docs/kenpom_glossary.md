# Viperball Efficiency Metrics Glossary

*Inspired by KenPom's basketball efficiency system, adapted for the unique mechanics of Viperball.*

---

## Overview

These metrics measure team efficiency on a **per-drive basis**, just like KenPom measures basketball on a per-possession basis. This normalizes for pace — a slow, grinding team and a fast, lateral-heavy team can be compared fairly.

The key insight: **it's not how many points you score, it's how efficiently you score them.**

---

## Offensive Metrics

### Raw O (Offensive Efficiency)
**Points per 10 drives.**

The most important offensive number. How many points does this team produce relative to how many chances they get? A team that scores 45 points on 15 drives (3.0 PPD = 30.0 Raw O) is more efficient than one that scores 50 on 20 drives (2.5 PPD = 25.0 Raw O).

- **Elite:** 35+
- **Good:** 28-35
- **Average:** 22-28
- **Poor:** Below 22

### EK% (Effective Kick Percentage)
**Kick success rate, weighted by point value.**

Viperball's equivalent of Effective FG%. Snap kicks (5 pts) are worth 5/3 of a place kick (3 pts), so a made snap kick counts more. A team that makes 2 snap kicks on 4 attempts (EK% = 83.3%) is more valuable than one that makes 3 place kicks on 4 attempts (EK% = 75.0%).

**Formula:** `(DK_made x 1.67 + PK_made) / total_kick_attempts x 100`

- **Elite:** 55%+
- **Good:** 45-55%
- **Average:** 35-45%
- **Poor:** Below 35%

### TO% (Turnover Percentage)
**Turnovers committed per drive.**

Lower is better. Includes fumbles lost, kick pass interceptions, and lateral interceptions. A team that turns it over on 15% of drives is significantly worse than one at 8%.

- **Elite:** Below 8%
- **Average:** 12-18%
- **Poor:** Above 22%

### LR% (Lateral Recovery Rate)
**Successful lateral chains / total lateral attempts.**

Viperball's equivalent of Offensive Rebound%. How often does a team complete its lateral chains without fumbling or getting intercepted? This is critical because laterals are high-risk, high-reward — a team with 80% LR% is exploiting Viperball mechanics safely.

- **Elite:** 80%+
- **Good:** 65-80%
- **Average:** 50-65%
- **Poor:** Below 50%

### FDR (Free Down Rate)
**Penalties drawn per play (%).**

Like Free Throw Rate in basketball — how often does the opponent commit penalties that give you free yardage? A high FDR means the offense is disciplined and drawing flags. A low FDR means the offense isn't getting any help from the refs.

### RLE (Rush/Lateral Efficiency)
**Rushing yards per carry.**

The ground game efficiency. Like 2-point FG% — how effective is the team when it runs the ball? Includes all rush-type plays (dives, sweeps, powers, counters).

- **Elite:** 6.0+
- **Good:** 4.5-6.0
- **Average:** 3.0-4.5
- **Poor:** Below 3.0

### KP% (Kick Pass Percentage)
**Kick pass completion rate.**

Like 3-point FG% — how accurate is the team's kick passing game? The kick pass is Viperball's version of the forward pass, using a drop-kick trajectory.

- **Elite:** 55%+
- **Good:** 40-55%
- **Average:** 30-40%
- **Poor:** Below 30%

---

## Defensive Metrics

### Raw D (Defensive Efficiency)
**Opponent points per 10 drives.**

Lower is better. The most important defensive number. How many points does the defense allow per opponent possession? A defense that holds opponents to 18.0 Raw D is significantly better than one at 30.0.

- **Elite:** Below 20
- **Good:** 20-26
- **Average:** 26-32
- **Poor:** Above 32

### Opp EK% (Opponent Effective Kick%)
**Opponent's kick success rate, weighted by value.**

Lower is better. How well does the defense prevent opponent kicks from going through?

### TOD% (Turnover Forced Percentage)
**Forced turnovers per opponent drive.**

Higher is better. The defense's ability to take the ball away. Includes forced fumbles, kick pass interceptions, lateral interceptions, and turnovers on downs.

- **Elite:** 25%+
- **Good:** 18-25%
- **Average:** 12-18%
- **Poor:** Below 12%

### Opp RLE (Opponent Rush/Lateral Efficiency)
**Opponent rushing yards per carry allowed.**

Lower is better. How well does the defense stop the ground game?

### Opp KP% (Opponent Kick Pass%)
**Opponent kick pass completion rate allowed.**

Lower is better. How well does the defense disrupt the aerial game?

---

## Tempo

### Adj T (Adjusted Tempo)
**Plays per game.**

Raw pace metric. Higher = faster team. This contextualizes all other metrics — a team running 70 plays per game at average efficiency will look different than one running 50 plays at high efficiency.

- **Up-tempo:** 60+ plays/game
- **Standard:** 45-60 plays/game
- **Ball control:** Below 45 plays/game

---

## How to Read the Numbers Together

The power of these metrics is in the combinations:

- **High Raw O + Low TO% + High LR%** = Elite, disciplined offense that exploits Viperball mechanics without giving the ball away
- **Low Raw D + High TOD%** = Suffocating defense that forces turnovers
- **High EK% + Low KP%** = Team that wins through kicking rather than kick passing
- **High RLE + Low KP%** = Ground-and-pound team
- **High KP% + High LR%** = Aerial + lateral attack (most dangerous in Viperball)

### Net Efficiency
`Raw O - Raw D` is the single best predictor of team quality. A team with Raw O of 32 and Raw D of 20 (Net +12) is elite. A team at 25/25 (Net 0) is average.

---

*These metrics are computed from season-long accumulators and update after each game. They are not opponent-adjusted (future: AdjO/AdjD will weight by opponent quality, similar to how KenPom adjusts for schedule strength).*
