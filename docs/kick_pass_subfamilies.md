# Kick Pass Sub-Families (Phase 1) — Feature Report

## What Changed

The monolithic `simulate_kick_pass()` has been split into **4 distinct sub-families**, each with a different **player-vs-player contest surface**:

| Sub-Family | Distance | Completion | INT Risk | Key Attributes |
|---|---|---|---|---|
| **Quick Kick** | 5-13 yd | ~60% center | 5% | Kicker accuracy, defender speed |
| **Territory** | 10-24 yd | ~50% center | 10% | Balanced kicker acc+power, defender awareness |
| **Bomb** | 22-42 yd | ~35% center | 16% | Kicker power, defender speed |
| **Kick-Lateral** | 5-13 yd + chain | ~60% kick, chain risk | 5% + per-lateral | Kicker accuracy + receiver lateral_skill |

## What Was Removed

- **Flat 55% completion rate** → replaced by sub-family-specific H2H contests
- **Team-average awareness** as the sole defensive metric → replaced by individual defender selection per sub-family
- **Flat 10% sack rate** → replaced by DL rusher vs OL blocker H2H contest with sub-family release time modifiers
- **Flat 10% INT rate** on incompletes → replaced by sub-family-specific H2H-driven INT rates
- **`Random(5, 14)` distance** → replaced by player-driven distance from `kick_power` and `kick_accuracy`

## How Styles Play Differently Now

- **Ground & Pound**: 80% Quick Kicks (play-action safe throws off heavy runs)
- **Chain Gang**: 60% Kick-Laterals (scheme identity = lateral chaos)
- **Boot Raid**: 50% Territory in Launch Pad range, Quick Kicks elsewhere
- **Ghost**: Bombs on early downs (misdirection deep shots), Quick Kicks on late downs
- **Balanced**: Even 35/35/15/15 split — adapts to game state

## How Defense Interacts

- **Individual defender matchup**: Each sub-family picks a specific defender for the H2H. Bombs pick the fastest defender (deep safety). Territory picks the highest-awareness defender (coverage man). Quick Kicks pick the nearest closer (speed + awareness + tackling).
- **DC adaptation at sub-family granularity**: The DC can "solve" Quick Kicks without affecting Territory. This creates a cat-and-mouse: if the DC solves your dominant sub-family, you shift to another. The solved-puzzle decay mechanic means the OC can recover by changing tendency for 3+ plays.
- **No-Fly Zone** now hits Bombs hardest (-10%), Territory medium (-5%), Quick Kicks least (-2%)

## H2H Contest Surfaces

### Quick Kick
- **Offense**: `kick_accuracy * 0.70 + receiver.hands * 0.30`
- **Defense**: `defender.speed * 0.50 + defender.awareness * 0.30 + defender.tackling * 0.20`
- Defender selection: weighted by speed + awareness, favoring Keepers (short-zone closers)

### Territory
- **Offense**: `kick_accuracy * 0.45 + kick_power * 0.25 + receiver.hands * 0.30`
- **Defense**: `defender.awareness * 0.45 + defender.speed * 0.30 + defender.tackling * 0.25`
- Defender selection: weighted by awareness + speed (read-and-react coverage)

### Bomb
- **Offense**: `kick_power * 0.55 + kick_accuracy * 0.20 + receiver.speed * 0.25`
- **Defense**: `defender.speed * 0.60 + defender.awareness * 0.25 + defender.agility * 0.15`
- Defender selection: weighted by speed + agility (deep safety matchup)

### Kick-Lateral
- Kick phase uses Quick Kick surface; chain phase uses lateral_skill-gated fumble/INT checks per lateral

## Sack Model (H2H)

```
rush_skill = rusher.tackling * 0.4 + rusher.power * 0.3 + rusher.speed * 0.3
block_skill = blocker.power * 0.5 + blocker.awareness * 0.3
sack_prob = 0.12 * (rush_skill / block_skill) * sub_family_modifier
```

Sub-family modifiers: Quick Kick 0.60x, Territory 1.00x, Bomb 1.40x, Kick-Lateral 0.70x

## Distance Model (Player-Driven)

| Sub-Family | Base | kick_power bonus | kick_accuracy bonus | Range |
|---|---|---|---|---|
| Quick Kick | 5-8 | 0-3 yd | 0-2 yd | 3-13 |
| Territory | 10-16 | 0-5 yd | 0-3 yd | 7-24 |
| Bomb | 22-30 | 0-12 yd | — | 18-42 |
| Kick-Lateral | Quick Kick distance | — | — | 3-13 + chain |
