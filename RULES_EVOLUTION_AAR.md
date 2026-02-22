# Viperball Rules Evolution: Primer v1 vs Current Engine

**Audit date:** 2026-02-22
**Source of truth:** `engine/game_engine.py` (357KB), `engine/coaching.py`, `engine/weather.py`, `engine/injuries.py`, `engine/epa.py`
**Compared against:** Narrative Primer document (Feb 2026 snapshot)

This document catalogs every area where the simulation engine has evolved beyond what the Primer describes. Items are grouped by significance: structural changes that alter how the game plays, mechanical additions the Primer doesn't mention, and numerical recalibrations.

---

## STRUCTURAL CHANGES (Game-Altering)

### 1. Quarter Length: 10 Minutes, Not 15

| | Primer | Engine |
|---|---|---|
| Quarter length | 15 min (60-min game) | 10 min (40-min game) |
| Play clock per play | 11-36 seconds | Fixed 18s base, modified by tempo multiplier |
| Plays per team | ~80-85 | Variable by tempo (max_plays = 20 + tempo * 15) |

The engine runs **10-minute quarters** (`GameState.time_remaining = 600`). This is a 33% shorter game than the Primer describes. Combined with the fixed 18-second play clock (modulated by tempo from 0.85x to 1.15x), actual plays per team land in the 40-60 range, not 80-85. This fundamental change affects every calibration number in the Primer.

### 2. The 4th Down Movement Mechanic (Pesapallo Rule)

**Not in the Primer at all.** This is the single biggest structural addition since the Primer was written.

Drives now have three phases:
- **Advancement (downs 1-3):** Build yardage toward a first down or scoring position
- **Decision (down 4):** The coaching staff makes a critical choice — go for the first down, enter **kick mode**, or punt
- **Specialist (downs 5-6):** If the team entered kick mode on 4th down, the kicker gets two clean shots

**Kick mode** (`GameState.kick_mode`) is a boolean flag. Once activated, the offense commits to kicking plays (snap kicks or field goals) on 5th and 6th down. Each offensive style has a `kick_mode_aggression` parameter (0.25 for Ground & Pound up to 0.80 for Boot Raid) that determines how eagerly it enters this phase.

**The Pesapallo Rule:** Missed snap kicks and field goals in kick mode **retain possession** — the ball is dead at the line of scrimmage and the down advances. This is a borrowed mechanic from Finnish baseball (pesapallo) where failed scoring attempts don't turn the ball over. This eliminated the old problem where most drives stalled into aimless kicks with no narrative arc.

The result type `MISSED_SNAP_KICK_RETAINED` exists specifically for this mechanic.

### 3. Penalties Use Power Plays, Not Yardage

| | Primer | Engine |
|---|---|---|
| Penalty enforcement | Yards added/subtracted from field position | **Power play** (man-advantage for N plays) |
| Penalty yardage | 5/10/15 yard values enforced | Yardage values exist in catalog but are **not applied to field position** |

The Primer describes a traditional penalty yardage system. The engine has replaced this with a **power play / man-advantage system**. When a penalty occurs, instead of moving the ball, the non-penalized team gets a man-advantage for 1-3 plays. During a power play, the advantaged team gets a performance bonus on play resolution.

The `Penalty` dataclass still carries a `yards` field (marked as "legacy — kept for catalog but NOT applied to field position") and now has a `power_play_plays` field for the man-advantage duration.

The scaffolding is shipped (`_start_power_play()`, `get_power_play_bonus()`, `_tick_power_play()`) — though the actual bonus application in play resolution is still being wired.

### 4. Lateral Interceptions Exist

The Primer does not mention lateral interceptions. The engine has a `LATERAL_INTERCEPTED` play result and tracks `game_lateral_interceptions` per player. Defenders can intercept lateral pitches during chain plays, with explosive return potential including pick-sixes. This adds a new turnover dimension to the lateral chain risk calculus.

### 5. Timeouts and 3-Minute Warning

**Not in the Primer.** The engine has:
- **3 timeouts per half per team** (`home_timeouts`, `away_timeouts`, reset at halftime)
- **3-minute warning:** Auto clock-stop once per half when the clock crosses 180 seconds remaining (in Q2 and Q4)
- **AI timeout usage:** Coaching AI calls timeouts based on game situation — trailing teams use them to stop the clock, leading teams use them defensively

---

## V2 ENGINE ARCHITECTURE (Not in Primer)

The engine underwent a full V2 architecture rebuild that the Primer predates entirely. These systems run on top of the Primer's base mechanics:

### 6. Halo Model (Prestige-to-Engine Integration)

Every team has a `prestige` rating (0-99) that derives a **team halo** — baseline offensive and defensive ratings. For 90% of plays (non-star plays), contest resolution uses the team halo instead of individual player stats. This means a high-prestige program performs well even with individually average players, while a low-prestige program with a few stars still struggles on most possessions.

The `PRESTIGE_TO_HALO` table maps prestige tiers to (halo_offense, halo_defense) pairs, with linear interpolation between breakpoints. Prestige 90+ gets (88, 86); prestige 10 gets (48, 47).

### 7. Power Ratio Contest Resolution

The Primer implicitly assumes play outcomes are determined by some resolution system but doesn't describe it. The engine now uses a **multiplicative power ratio** model instead of the original additive sigmoid:

The V2 model computes `(carrier_rating / tackler_rating) ** exponent` (default exponent 1.8), creating more separation between mismatched talent levels. This is gated by the `V2_ENGINE_CONFIG["contest_model"]` flag.

### 8. R/E/C Variance Archetypes

Every player has **two** archetype layers:
1. **Position archetype** (what they do): `kicking_zb`, `speed_flanker`, `power_viper`, etc. — described in the Primer
2. **Variance archetype** (how consistently): `Reliable`, `Explosive`, or `Clutch` — **not in the Primer**

- **Reliable:** Clamp roll to rating +/- 10 (tight band, consistent output)
- **Explosive:** Full 0-100 roll range with no floor (feast or famine)
- **Clutch:** Standard variance + 15% boost in pressure situations (Q4, close game, composure < 80)

This creates meaningful player differentiation beyond raw talent. A Reliable flanker with 75 speed always performs near 75; an Explosive one might produce 50 or 95 on any given play.

### 9. Star Designation System

Before each game, up to **3 players per team** are designated as **stars** based on overall rating. Stars get:
- Individual stat resolution (bypassing the team halo)
- A performance floor: `max(roll, player_rating - 10)`
- Priority in play design and ball distribution

This creates the narrative dynamic of star players who can take over games, while the bulk of the roster operates at the team's prestige-driven baseline.

### 10. Hero Ball + Defensive Keying

When a star player gets hot (consecutive successful touches), the offense force-feeds them more touches — **Hero Ball**. This creates dynamic run-the-hot-hand situations.

But defenses counter with **keying** — after enough consecutive star touches, the defense keys on the star, reducing their effectiveness. This creates a natural oscillation: star gets hot -> hero ball -> defense keys -> star's effectiveness drops -> offense redistributes.

Tracked via `hero_ball_target` and `consecutive_star_touches` on the GameState.

### 11. Composure System (Dynamic, Per-Game)

**Not in the Primer.** Each team has a dynamic composure rating (60-140 range, starting at 100) that shifts throughout the game based on events:

| Event | Composure Change |
|---|---|
| Turnover committed | -8 |
| Turnover forced | +5 |
| Touchdown scored | +6 |
| Touchdown allowed | -4 |
| Failed conversion | -10 |
| Successful late conversion | +8 |
| Sack | -3 |
| Big play allowed (20+ yards) | -5 |
| Big play scored (20+ yards) | +4 |
| Penalty committed | -2 |
| Blocked kick | -6 |

**Tilt state:** Below composure 70, a team enters **tilt** — awareness drops 15%, fumble rate multiplied by 1.2x, and the AI makes panic decisions. Exiting tilt requires recovering above 75 (5-point hysteresis prevents flip-flopping).

**Pregame modifiers:** Rivalries add +15% variance to both teams. Playoffs add +25%. Trap games give the favorite -15% and the underdog +15%.

Composure timelines are recorded for post-game narrative generation.

### 12. Yardage Polarization (Bimodal Distribution)

The Primer describes run plays gaining "3-7 yards on average with high variance." The engine now uses a **bimodal yardage distribution** on every run contest:

- **4% bust rate** (early downs): Play gains only ~40% of expected yardage
- **26% explosive rate** (early downs): Play gains ~180% of expected yardage
- **70% normal:** Standard gaussian around expected center

On late downs (4+), bust rate drops to 3% and explosive rate drops to 25% — offenses are more focused and consistent when it matters. This creates the dramatic variance the sport needs while keeping average production stable.

### 13. Prestige-Driven Decision Matrix

The Primer describes play-calling as driven by offensive style weights. The engine adds a **prestige-driven layer** on top: high-prestige teams make better situational decisions (4th down accuracy, halftime adjustments), while low-prestige teams are more prone to suboptimal calls. This is gated by `V2_ENGINE_CONFIG["prestige_decisions_enabled"]`.

---

## COACHING SYSTEM (Not in Primer)

The Primer mentions "coaching adjustments take effect at halftime" as a one-liner. The engine has a full coaching staff simulation:

### 14. Four-Person Coaching Staff

Each team has a **Head Coach, Offensive Coordinator, Defensive Coordinator, and Special Teams Coordinator** — each modeled with:
- **6 attributes** (25-95): instincts (hidden), leadership, composure, rotations, development, recruiting
- **1 classification badge:** Scheme Master, Gameday Manager, Motivator, Players' Coach, or Disciplinarian
- **Sub-archetype** (V2.2): 3 sub-types per classification (e.g., Disciplinarian -> Enforcer / Technician / Stoic)
- **9 personality sliders** (0-100): aggression, risk_tolerance, chaos_appetite, tempo_preference, composure_tendency, adaptability, stubbornness, player_trust, variance_tolerance
- **Hidden traits** (0-2 per coach): 20 possible traits like "red_zone_gambler", "chaos_merchant", "wind_whisperer", "punt_hater", "lateral_enthusiast"

### 15. Coaching Affects 8 Game Engine Decision Points

Personality sliders, sub-archetypes, and hidden traits modulate:
1. Play family selection weights
2. Kick/go-for-it decisions
3. Run yardage variance (boom/bust tendency)
4. Fumble rates under pressure
5. Defensive read quality
6. Halftime adjustments
7. Defensive fatigue pressure
8. Hero Ball star-targeting weight

This means two teams running the same offensive style will play differently based on their coaching personality. A "punt_hater" HC running Ground & Pound behaves very differently from a "field_position_purist" HC running the same scheme.

### 16. Coaching Contracts, Salary Pools, Marketplace

Full economic simulation: coaching budgets by prestige tier, contract years/buyout, offseason marketplace with free agents and poaching targets, CPU team evaluation/firing/hiring logic. The Primer mentions none of this.

---

## WEATHER SYSTEM (Expanded Beyond Primer)

### 17. Location-Aware Weather Generation

The Primer describes 6 weather conditions with static modifiers. The engine adds:
- **Climate zone mapping:** Every US state is classified into one of 11 climate zones (new_england, pacific_northwest, texas_arid, mountain, california, etc.)
- **Season-aware probability tables:** Weather probability varies by season period (early_fall, late_fall, early_winter, winter) within each climate zone
- **A game in Wisconsin in December** has a 32% chance of snow and 12% chance of sleet; the **same week in Florida** has 60% clear and 0% snow

The 6 weather types and their gameplay modifiers are unchanged from the Primer. What changed is how weather is selected — it's no longer random; it's geographically and temporally realistic.

---

## INJURY & AVAILABILITY SYSTEM (Not in Primer)

### 18. Full Injury Model

The Primer doesn't mention injuries at all. The engine has a comprehensive system:

- **5 injury tiers:** Day-to-day (0-1 games), Minor (1-2 weeks), Moderate (3-5 weeks), Major (6-8 weeks), Severe (season-ending)
- **4 injury categories:** On-field contact, on-field non-contact, practice/training, off-field (academic/personal/illness)
- **In-game injuries:** 0.2-0.4% per play for involved players, scaled by fatigue and position
- **Recovery variance:** 25% chance of early return when within 1 week; 8% chance of setback (adds 1-3 extra weeks)
- **Substitution system:** Same-position backup -> flexible position (with 15% stat penalty) -> emergency fill
- **DTD (day-to-day):** Players can play through minor injuries at 90% effectiveness

### 19. Off-Field Availability Issues

Unique to the women's college context: players can miss games for academic probation, mental health breaks, family emergencies, iron deficiency recovery, study abroad commitments, or entering the transfer portal. These use the same tier system as physical injuries.

---

## EPA / ANALYTICS SYSTEM (Not in Primer)

### 20. VPA (Viperball Points Added)

The engine has a full expected points / points-added system:
- **EP table** calibrated for 6-down, 9-point-TD Viperball (EP ranges from 0.05 at the 1-yard line to 9.0 at the 99)
- **Down multiplier:** D1=1.00, D2=0.97, D3=0.93, D4=0.85, D5=0.72, D6=0.50
- **Per-play VPA attribution** to individual players
- **Game-level metrics:** Total VPA, VPA/play, offense VPA, special teams VPA, success rate, explosiveness

The EP table uses a different terminology: "strike" for Bell (0.5 points) in the EPA system, though the game engine uses "Bell" everywhere else.

---

## NUMERICAL RECALIBRATIONS

### 21. Scoring Values Confirmed Unchanged

| Scoring Play | Primer | Engine | Status |
|---|---|---|---|
| Touchdown | 9 pts | 9 pts | Match |
| Drop Kick (Snap Kick) | 5 pts | 5 pts | Match |
| Place Kick (Field Goal) | 3 pts | 3 pts | Match |
| Safety | 2 pts | 2 pts | Match |
| Pindown | 1 pt | 1 pt | Match |
| Bell (fumble recovery) | 0.5 pts | 0.5 pts | Match |

### 22. Down System Confirmed Unchanged

6 downs for 20 yards — matches Primer exactly. `yards_to_go: int = 20` in GameState.

### 23. Sacrifice System Confirmed Unchanged

The formula is identical: `start_position = max(1, 20 - point_differential)`. Leading teams start deeper; trailing teams start further upfield. The Primer's description is accurate.

The engine adds **sacrifice tracking stats** not in the Primer: sacrifice_yards, sacrifice_drives, sacrifice_scores, and "Compelled Efficiency" (scoring rate when starting under sacrifice).

### 24. Pindown — Receiving Team Starts at 25, Not 20

| | Primer | Engine |
|---|---|---|
| Receiving team start after pindown | Own 25-yard line | Own 25-yard line |

The Primer says 25. The engine confirms 25 (`game_engine.py:2485`). Consistent.

### 25. Typical Score Ranges Need Recalibration

The Primer says "typically 45-75 points per team" and "4-6 touchdowns per team." Per the AAR batch sim data:
- **Current average:** ~45-50 points per team (slightly below Primer low end)
- **TDs per team:** ~1.9-3.5 (significantly below Primer's 4-6 target)
- **Snap kicks made:** ~3-5 per team (in range)
- **FGs per team:** ~3 (in range)

The scoring gravity is tilted toward kicking plays (5+3 pts) rather than touchdowns (9 pts). The Primer's 4-6 TD target is aspirational; the engine currently produces fewer TDs and more kick-based scoring.

### 26. Run Play Base Yards Differ from Primer

The Primer says "3-7 yards on average." Engine `RUN_PLAY_CONFIG` shows base yards ranges of (2.0, 3.5) to (2.5, 4.5) before modifiers. After accounting for offensive/defensive matchups, variance, and explosive plays, realized yards are in the right neighborhood but the base values are lower than the Primer implies.

### 27. Kick Pass Completion Rates

The Primer provides completion rates by distance (72% short, 62% medium, etc.). These are calibrated in `_contest_kick_pass_prob()` using a contest-based model rather than fixed lookup tables. Actual rates will vary based on kicker skill, receiver hands, defensive coverage, weather, and halo vs individual resolution.

---

## MISSING FROM ENGINE (In Primer But Not Implemented)

### 28. No Overtime System

The Primer doesn't describe overtime either, and the RULES.md has an "Overtime Rules" section, but the engine has no overtime implementation. Games that end tied stay tied.

### 29. No Explicit Field Dimension

The Primer says "100 yards long with end zones." The engine uses a 1-99 yard line system but doesn't model field width or end zone depth explicitly.

---

## GLOSSARY ADDITIONS

Terms the engine uses that aren't in the Primer vocabulary:

| Term | Meaning |
|---|---|
| **Kick Mode** | State flag indicating the offense has committed to kicking plays on downs 5-6 (entered via 4th down decision) |
| **Power Play** | Man-advantage system replacing penalty yardage; advantaged team gets performance boost for N plays |
| **Halo** | Team-level offensive/defensive baseline derived from prestige; used for non-star play resolution |
| **Tilt** | Composure state below 70; team suffers awareness and ball-security penalties |
| **Surge** | Composure boost when underdog leads late; reduces fatigue for trailing team |
| **VPA** | Viperball Points Added — EPA analog measuring play value above expectation |
| **Compelled Efficiency** | Scoring rate on drives that start under sacrifice penalty |
| **R/E/C** | Reliable/Explosive/Clutch — variance archetype system orthogonal to position archetypes |
| **Star Override** | Performance floor for designated star players (max 3 per team) |
| **Hero Ball** | Force-feeding touches to a hot star player; countered by defensive keying |
| **Keeper Bell** | A Bell (0.5 pts) specifically generated by a Keeper's deflection leading to a recovery |
| **DTD** | Day-to-day — player is injured but available at 90% effectiveness |

---

## SUMMARY: What the Primer Gets Right vs. What's Moved

### Still Accurate
- Core identity (no forward pass, lateral chains, kick passes)
- Scoring values (9/5/3/2/1/0.5)
- Down system (6 for 20)
- Sacrifice system (start at 20 minus lead)
- Position groups and roster size (36 players, same distribution)
- All 9 offensive styles (names, descriptions, strategic identities)
- All 8 defensive schemes (names, matchup dynamics)
- All 5 special teams schemes
- All 6 weather conditions and their gameplay effects
- Penalty types and categories
- Play types and play families

### Materially Changed
- Quarter length (10 min, not 15 — games are 33% shorter)
- Penalty enforcement (power plays, not yardage)
- Drive structure (three-phase with 4th down decision point + kick mode)
- Missed kicks retain possession (Pesapallo rule)
- Lateral interceptions added as a turnover type
- TD production below Primer targets (~2-3 vs 4-6)

### Major Additions Not in Primer
- V2 architecture: Halo Model, Power Ratio contests, R/E/C archetypes, Star Override, Hero Ball, Composure System, Prestige Decision Matrix
- Full coaching staff simulation (4 coaches, 6 attributes, classifications, sub-archetypes, personality sliders, hidden traits)
- Injury/availability system (5 tiers, 4 categories, in-game injuries, substitutions, recovery variance)
- Location-aware weather generation (11 climate zones, seasonal probability tables)
- VPA analytics system (Expected Points, per-play attribution)
- Timeouts (3 per half) and 3-minute warning
- Coaching marketplace and economic simulation

---

*Audited 2026-02-22 against engine commit history and live code.*
