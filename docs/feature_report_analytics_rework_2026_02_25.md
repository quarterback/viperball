# Feature Report — Analytics Rework (February 25, 2026)

## Summary

Complete rework of the Viperball analytics system. Replaced abstract sabermetric scales (VPA, OPI, Territory Rating, Pressure Index, Chaos Factor) with fan-friendly metrics modeled after real sports analytics concepts: WPA (from baseball/NFL), WAR (from baseball), ZBR (like QBR), and Team Rating (like ESPN SP+). Added Scoring Profile and Defensive Impact as new analytical dimensions.

---

## 1. Core Metrics Rework (VPA/OPI → WPA/Team Rating)

### What Changed

The entire `engine/viperball_metrics.py` module was rewritten. The old system used abstract 0-100 composite scores (OPI, Territory Rating, Pressure Index, Chaos Factor, Kicking Efficiency, Drive Quality, Turnover Impact) that didn't correspond to anything a sports fan would recognize. The new system uses metrics every sports fan already knows.

### Old System (Removed)

| Metric | Scale | Problem |
|---|---|---|
| OPI (Overall Performance Index) | 0-100 | Abstract composite — unclear what it measured |
| Territory Rating | 0-100 | Field position weighted by arcane formula |
| Pressure Index | 0-100 | "Pressure" is ambiguous |
| Chaos Factor | 0-100 | Viperball-specific jargon, not intuitive |
| Kicking Efficiency | 0-100 | Overly compressed, hard to interpret |
| Drive Quality | 0-100 | Vague — quality of what? |
| Turnover Impact | 0-100 | Non-standard scale |
| VPA (Viperball Points Added) | Unbounded | EPA clone with unfamiliar name |

### New System

| Metric | Scale | Real-World Analog | Fan Usage |
|---|---|---|---|
| **WPA** (Win Probability Added) | Unbounded | WPA from MLB/NFL | "That play was worth +0.8 WPA" |
| **WAR** (Wins Above Replacement) | Unbounded | WAR from baseball | "Their Viper is worth 1.8 WAR" |
| **ZBR** (Zeroback Rating) | 0-158.3 | NFL Passer Rating | "He posted a 112.4 ZBR" |
| **VPR** (Viper Rating) | 0-158.3 | NFL Passer Rating | "The Viper had a 98.7 VPR" |
| **PPD** (Points Per Drive) | ~0-10 | PPD from NFL analytics | "They averaged 4.2 points per drive" |
| **Team Rating** | 0-100 | ESPN SP+ / Madden OVR | "They're a 78-rated team" |
| **TO+/-** (Turnover Margin) | Integer | Universal stat | "They were plus-3 in turnovers" |
| **Conversion %** | 0-100% | 3rd-down conversion % | "They converted 55% of pressure downs" |
| **Lateral %** | 0-100% | Completion % | "They completed 78% of lateral chains" |
| **Explosive Plays** | Count | ESPN explosive plays | "They had 8 explosive plays" |
| **Avg Start** | Yard line | Avg starting FP | "Started drives at their own 32" |

### Design Principle

**"A fan should be able to explain every metric in one sentence using concepts they already know from watching other sports."**

### Backward Compatibility

All legacy property names are preserved as aliases throughout the codebase:
- `TeamRecord.avg_opi` → delegates to `avg_team_rating`
- `total_vpa` / `total_epa` → aliases for `wpa` in `calculate_game_epa()`
- `territory_rating`, `pressure_index`, `chaos_factor`, etc. → computed as proxy values from new metrics in `calculate_comprehensive_rating()`
- `Player.game_vpa` → mirrors `game_wpa`

---

## 2. ZBR & VPR: Passer Rating Scale (0-158.3)

### What Changed

ZBR (Zeroback Rating) and VPR (Viper Rating) were initially implemented on a 0-100 scale, but elite games only reached ~78.8, compressing the meaningful range. The scale was changed to the NFL passer rating 0-158.3 formula structure that every football fan recognizes.

### Formula

Both ZBR and VPR use four components, each clamped to 0-2.375 (identical to NFL passer rating):

```
Rating = (a + b + c + d) / 6 * 100
Perfect = (2.375 × 4) / 6 × 100 = 158.3
```

### ZBR Components

| Component | Formula | Analog |
|---|---|---|
| a: Yards Per Touch | `(YPT - 3.0) × 0.3393` | Yards/Attempt |
| b: TD Rate | `TDs/touches × 11.875` | TD% |
| c: Fumble Rate (inv) | `2.375 - fumbles/touches × 11.875` | INT% inverted |
| d: Lateral Accuracy | `lateral_assists/laterals_thrown × 2.375` | Completion % |

If no laterals thrown, component d defaults to 1.1875 (neutral midpoint).

### VPR Components

| Component | Formula | Difference from ZBR |
|---|---|---|
| a: Yards Per Touch | `(YPT - 2.0) × 0.2969` | Lower baseline (Vipers should be more explosive) |
| b: TD Rate | Same as ZBR | — |
| c: Fumble Rate (inv) | Same as ZBR | — |
| d: All-Purpose Efficiency | `(APY/touch - 3.0) × 0.2639` | Replaces Lateral Accuracy (Vipers contribute in all phases) |

### Interpretive Scale

| ZBR/VPR | Rating |
|---|---|
| 158.3 | Perfect game |
| ~100+ | Great game |
| ~85 | Good / above average |
| ~65 | Average |
| ~40 | Below average |
| <20 | Terrible |

---

## 3. Scoring Profile

### What Changed

New `calculate_scoring_profile()` function breaks down HOW a team scores their points, answering the fan question: "What kind of team is this?"

### Output

| Field | Description |
|---|---|
| `rush_td_pts` / `rush_pct` | Points and % from rushing touchdowns |
| `lateral_td_pts` / `lateral_pct` | Points and % from lateral-chain touchdowns |
| `kp_td_pts` / `kp_pct` | Points and % from kick-pass touchdowns |
| `dk_pts` / `dk_pct` | Points and % from drop kicks (5 pts each) |
| `pk_pts` / `pk_pct` | Points and % from place kicks (3 pts each) |
| `return_td_pts` / `return_pct` | Points and % from return touchdowns |
| `bonus_pts` / `bonus_pct` | Points and % scored on bonus possessions (defense-generated) |
| `snapkick_pct` | Combined DK + PK percentage |

### Fan Usage

"They're a snapkick team — 60% of their points come from the boot."
"Their defense wins games — 14 points off bonus possessions."

---

## 4. Defensive Impact

### What Changed

New `calculate_defensive_impact()` function measures how much a team's defense generates for the offense. This is unique to Viperball — the first sport where the defense can win you extra offensive possessions.

### Output

| Field | Description |
|---|---|
| `bonus_possessions` | Extra possessions earned from defensive plays |
| `bonus_scores` | How many bonus possessions resulted in scores |
| `bonus_conv_rate` | Bonus possession → score conversion rate (%) |
| `bonus_pts` | Estimated points scored on bonus drives |
| `bonus_yards` | Total yards gained on bonus drives |
| `turnovers_forced` | Total turnovers forced (fumbles + TOD + INTs) |
| `defensive_stops` | Opponent drives held without scoring |
| `stop_rate` | % of opponent drives stopped |

### Fan Usage

"Their defense created 3 bonus possessions and converted 2 of them — that's 14 points from the defense."

---

## 5. WPA Rename (epa.py)

### What Changed

The EPA (Expected Points Added) module was renamed to WPA (Win Probability Added) in its user-facing output. The internal calculation is unchanged — it still computes expected point deltas per play. The rename reflects that fans know "WPA" from baseball and NFL broadcasts.

### Key Changes in `calculate_game_epa()`

Primary return keys: `wpa`, `wpa_per_play`, `offense_wpa`, `special_teams_wpa`, `success_rate`, `explosiveness`

Legacy aliases preserved: `total_vpa`, `vpa_per_play`, `total_epa`, `epa_per_play`, `chaos_epa`

---

## Files Modified

| File | Changes |
|---|---|
| `engine/viperball_metrics.py` | Complete rewrite — all new metric calculations |
| `engine/epa.py` | VPA→WPA rename in return keys, docstrings updated |
| `engine/game_engine.py` | Post-game summary uses new metrics, player WPA attribution |
| `engine/season.py` | TeamRecord new accumulator fields and properties |
| `engine/__init__.py` | Updated exports (WAR, ZBR, VPR, scoring_profile, defensive_impact) |
| `engine/export.py` | CSV column names updated |
| `engine/fast_sim.py` | Added team_rating alias |
| `api/main.py` | New API response keys |
| `nicegui_app/pages/game_simulator.py` | Scoring Profile + Defensive Impact UI sections |
| `nicegui_app/pages/league.py` | Radar chart labels, standings columns, statistical leaders |
| `nicegui_app/pages/my_team.py` | OPI→Team Rating, VPA→WPA label updates |
| `nicegui_app/pages/export.py` | Label updates |
| `nicegui_app/pages/dq_mode.py` | Label updates |
| `nicegui_app/pages/debug_tools.py` | Label updates |
| `nicegui_app/pages/draftyqueenz.py` | Label updates |
| `ui/page_modules/game_simulator.py` | Scoring Profile + Defensive Impact tables |
| `ui/page_modules/section_league.py` | Statistical leaders added |
| `ui/page_modules/season_simulator.py` | Label updates |
| `ui/page_modules/section_my_team.py` | Label updates |
| `ui/page_modules/section_export.py` | Label updates |
| `ui/page_modules/dynasty_mode.py` | Label updates |
| `ui/page_modules/debug_tools.py` | Label updates |

## Commits

| Hash | Description |
|---|---|
| `606bdac` | Rework VPA/OPI metrics into fan-friendly analytics (WPA, WAR, ZBR, VPR, PPD) |
| `a4d3500` | Retune ZBR and VPR to passer-rating 0-158.3 scale |
| `319b2e0` | Add Scoring Profile and Defensive Impact analytics |
