# AAR — PR #342: rare defensive situations
Date: 2026-11-24 UTC / November 23 Pacific. Merged d3a2f158f334fd31ed1d08ae739f192128aa0d9b. [PR](https://github.com/quarterback/viperball/pull/342) | [Successful calibration](https://github.com/quarterback/viperball/actions/runs/45337499565), job 138252943533.

## Scope and method
192 full games (48 per case), seed 20261124, two roster matchups, alternating DC profiles, Boot Raid offense, clear weather, neutral venue, explicitly installed fully familiar packages. 740 sampled pre-snap states: Kick-In 171, Ride 240, Exhaustion 262 (240 controlled energy), overload 67. Clone state and RNG, call defense before forcing the offensive response; package off/on or 2/4/6 intended rushers. Maximum four samples per scenario per game and 120 per scenario. Natural frequencies are from the unforced games with installed fixtures, not league-wide adoption estimates. No production engine changes in #342.

## Natural results
| Case | Calls | Primary eligible | Secondary eligible | Activated | Secondary activated | Sampled |
|---|---:|---:|---:|---:|---:|---:|
| Kick-In Press | 3067 | 65 | 353 | 211 | 157 | 171 |
| Ride | 3134 | 191 | 310 | 301 | 126 | 240 |
| Exhaustion Press | 3041 | 1 | 30 | 14 | 13 | 262 |
| Overload | 3288 | — | — | — | — | 67 |

Overload urgent eligibility 234, natural six-rusher kick-pass attempts zero. Other cases recorded 4, 3 and 2 six-rusher attempts respectively. This does not establish a league-wide six-rusher frequency.

## Physical commitment
| Release | Pairs | Pressure 2/4/6 | Sack 2/4/6 | Yards 2/4/6 | Defense energy loss 2/4/6 |
|---|---:|---|---|---|---|
| Quick | 23 | 21.7/26.1/34.8% | 4.3/8.7/8.7% | 5.22/7.91/13.22 | 1.670/2.535/3.311 |
| Territory | 22 | 40.9/50.0/81.8% | 13.6/18.2/31.8% | 10.00/10.18/9.45 | 1.659/2.468/3.358 |
| Bomb | 22 | 63.6/81.8/86.4% | 31.8/40.9/50.0% | 7.95/7.18/3.00 | 1.754/2.572/3.391 |

Six versus two: quick +8 yards, explosive rate 4.3 to 17.4%; bomb -4.955 yards, explosive rate 9.1 to 4.5%; territory -0.545 yards. Territory released completion rises 52.6 to 73.3%, offsetting pressure. Energy is total defending roster energy loss per replay, not per-player fatigue. The overload test only fixes kick passes; no evidence yet about its run counter.

## Package results (paired on minus off yards)
| Package / tier | Quick | Territory | Bomb | Power | Speed option |
|---|---:|---:|---:|---:|---:|
| Kick-In primary (10–11 pairs/cell) | -6.455 | -5.600 | -0.500 | 0 | 0 |
| Kick-In secondary (24/cell) | -5.000 | -2.208 | +5.083 | +0.042 | +0.042 |
| Ride primary (24/cell) | 0 | -2.583 | +1.458 | +0.083 | -0.375 |
| Ride secondary (24/cell) | 0 | -2.417 | +4.125 | +0.042 | -0.417 |
| Exhaustion controlled 65 (24/cell) | -0.958 | +0.708 | +3.708 | +0.125 | -0.250 |
| Exhaustion controlled 78 (24/cell) | +3.125 | -2.458 | +8.583 | +0.167 | -1.167 |

Kick-In primary quick completion 45.5 to 18.2% (11 pairs); secondary quick 41.7 to 29.2% (24 pairs). Ride shows modest territory denial and deep vulnerability, little quick or run effect. Exhaustion controlled 65 and 78 increased kick-pass energy cost in every subtype; pressure gains inconsistent. Natural primary one pair and secondary 21 total, too sparse for calibration. Secondary bomb +14.75 yards and territory +13.75 each from only four pairs. Controlled energy arms alter all offensive players' energy; no evidence these are natural fatigue distributions.

## Assessment and follow-up
Retain Kick-In and Ride provisionally; do not raise global pressure or six-rusher frequency on this evidence. Six-rusher commitment has a plausible release-time tradeoff and energy cost; natural usage in urgent Blitz Pack context remains unobserved. Audit the actual decision gate and denominator (urgent calls vs eligible kick-pass attempts) before widening. Exhaustion should be investigated for exposure/trigger mismatch and pressure benefit before making it more common. Inspect player-level fatigue and rotation rather than reducing recovery globally. Reuse this replay harness for run/lateral counters, score/clock urgency and roster variation. Report paired intervals with game-level clustering or independent game seeds; existing sums and squared deltas allow descriptive snap-level variance, not reliable independent inference. Avoid interpreting forced activation as a win-rate effect or forced responses as autonomous offensive adaptation. No new tests required for this report. Workflow success confirms study execution, not dynasty turnover or live deployment.