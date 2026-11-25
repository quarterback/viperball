# VAL-04 observed results and integration handoff

Evidence: PR #370 head 19c1c6169122bafcc53e9e1f210e80362299cb74, [workflow 45500633089](https://github.com/quarterback/viperball/actions/runs/45500633089), national jobs 138827105174 and 138827105219, reduced/rare job 138822648890. All three jobs passed; all five PR workflows passed. Results are from job logs, not from the later merged rating/officiating/sack baseline.

| Seed | Year | Regular | Playoffs | Installed slots | Distinct IDs | Activations | Fit violations |
|---|---|---:|---:|---:|---:|---:|---:|
| 20261124 | 2026 | 1224 | 7 | 368 | 12 | 29363 | 0 |
| 20261124 | 2027 | 1224 | 7 | 402 | 13 | 52550 | 0 |
| 20261125 | 2026 | 1224 | 7 | 375 | 12 | 28686 | 0 |
| 20261125 | 2027 | 1224 | 7 | 416 | 13 | 51498 | 0 |

Total 4924 games, 162097 activations, 204 active programs per year. Schedule, unique identities, full-engine game accounting, roster identity/position parity, postseason, fit and database gates passed. Offseasons: 231/233 hires, 811/812 signed recruits, 12/8 transfers, 204 retained installations each, roster sizes 36–44/36–46. DC changes in second seasons 37/39. Both DB roundtrips passed. Three reduced-league trajectories also completed 891 games with six successful transitions after the identity fix.

## Adoption

End-season installation snapshots and full-season eligible/selected calls are different denominators. No equal-usage target.

| Package ID | Installable program-seasons | Installed program-seasons | Eligible calls | Selected calls |
|---|---:|---:|---:|---:|
| afl_kick_in_press | 122 | 37 | 4189 | 935 |
| blitz_short_yardage_pressure | 286 | 133 | 8846 | 3234 |
| chaos_lateral_trap | 149 | 62 | 32498 | 5653 |
| drift_prevent | 650 | 462 | 136986 | 45420 |
| fortress_goal_line_stand | 160 | 52 | 9144 | 2670 |
| fortress_short_yardage_wall | 348 | 125 | 8009 | 2303 |
| lax_ride | 129 | 19 | 2338 | 565 |
| lockdown_kick_range_shell | 298 | 114 | 34028 | 10955 |
| lockdown_long_yardage_bracket | 650 | 416 | 177452 | 57339 |
| predator_exhaustion_press | 122 | 11 | 697 | 203 |
| rugby_rush_line | 286 | 100 | 70301 | 28245 |
| shadow_robber | 165 | 2 | 1222 | 66 |
| swarm_containment | 170 | 28 | 20422 | 4509 |

Both rare packages are naturally reachable; no evidence of a categorical installation block. Qualified but uninstalled counts 111 and 163 respectively. DEF-11 should distinguish preference ties and roster/situation differences after combined-baseline validation, not force more adoption.

## Relative fatigue replay

Same source snapshots, 24 pairs per response per energy cell; package on minus off mean yards, offense/defense energy:

| Energy | Quick kick | Territory | Bomb |
|---|---:|---:|---:|
| 65/50 | -1.917 | -2.208 | +11.125 |
| 65/65 | -2.208 | -2.833 | +11.125 |
| 65/90 | -0.125 | -0.625 | +15.792 |
| 72/50 | -1.917 | -2.208 | +11.125 |
| 72/65 | -2.208 | -2.833 | +11.125 |
| 72/90 | -0.125 | -0.625 | +15.792 |

Pressure changes 0 to +0.0833 in these cells. Deep completion concessions and defensive energy costs are visible, not a demonstrated monotonic relative-fatigue benefit. Source snapshots are reused and correlated; do not claim independent observations or significance. Keep mechanics unchanged until the new baseline is evaluated.

## Next gate

The other agent owns merger reconciliation. VAL-05 runs existing reduced and national studies on the merged SHA, preserving actual schedule and identity gates. Recheck package fit with remapped personnel thresholds; do not compare raw scoring or sack rates across changed rating baselines as though controlled. PRO-02 and HS-01 can prepare isolated validation harnesses without modifying merger branches. Live deployment not verified.
