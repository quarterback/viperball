# Tactical schools and playbooks

Current college engine reference: engine/game_engine.py (OFFENSE_STYLES, DEFENSE_STYLES, ST_SCHEMES, play selection and resolution), engine/playbook_catalog.py, engine/coach_tactics.py, engine/team_installation.py, engine/defensive_commitments.py, engine/ai_coach.py and data/playbooks/.

A school is the team's base philosophy. The actual coach's signature, installed packages, players, fatigue, opponent, game state and weather determine which legal actions occur. The descriptions below are intended identities, not guarantees of win rate, play share or scoring output. Do not treat old numerical tuning examples as current constants.

## Sixteen offensive schools

| School key | Identity |
|---|---|
| ground_control | Ground Control: touchdown-first run game and short kick-pass support |
| lateral_spread | Horizontal lateral movement and explosive chains |
| boot_raid | Advance to snap-kick range, then take high-value kicks |
| ball_control | Conservative possession and available points |
| ghost | Viper motion and misdirection |
| stampede | Fast perimeter runs and tempo |
| chain_gang | Long lateral chains, high variance |
| slick_n_slide | Two-back, read-based run/kick-pass attack |
| balanced | Adaptable mix |
| east_coast | Short kick passes and chain movement |
| shock_and_awe | High-tempo vertical kick passing |
| six_shooter | Early-down setup, late-down scoring kicks |
| quick_strike | Transition and bonus-possession attack |
| mousetrap | Repeated looks followed by counters |
| mismatch | Find and attack weak matchups with the Viper |
| ironclad | Clock, territory and field position |

Ground & Pound is renamed Ground Control. East Coast already supplies the possession-kick-pass school; no separate Possession KP school. Chain Gang and Lateral Spread remain distinct older rugby-like identities; they are also used in high-school competition. Six Shooter, Ball Control and Ironclad have separate finishing philosophies from Ground Control and Stampede.

## Ten defensive schools

| School | Primary strength | Concession |
|---|---|---|
| Fortress | Inside run defense | Space outside and kick-pass seams |
| Lockdown | Kick-pass coverage | Run exposure |
| Swarm | Lateral pursuit and interceptions | Kick-pass seams |
| Predator | Takeaways | Risk of explosives |
| Drift | Explosive prevention | Steady yards |
| Blitz Pack | Pressure and forced fumbles | Counters and draws |
| Chaos | Disguise and disruption | Exploitable reads after adjustment |
| Shadow | Viper containment | Power runs |
| Keeper Hunt | Kick pressure and blocks, especially consequential on sixth down | Short-yardage conversions |
| Rotation | Fatigue resistance against tempo | Modest per-snap cost |

Legacy defensive aliases are not additional independent schools. Weekly game plans move some of the base matchup tendencies toward a counter-school without replacing the defense's identity. Defensive packages specify pre-snap commitments and coverage; physical rushers, pressure, hurries, sacks and credits are measured separately. Rare package adoption/effectiveness is a calibration question.

## Five special-teams schemes

Iron Curtain (coverage), Lightning Returns (return threats), Block Party (kick rush), Chaos Unit (surprise plays), Aces (balanced). Actual STC tendencies, available personnel, scheme and legal kick outcomes govern decisions; kicks on early downs may preserve possession on a miss.

## Play families and installation

The engine contains run, lateral, kick-pass and kicking families. Kick-pass subfamilies include quick, territory, bomb and kick-lateral. A school is not a fixed sequence of plays. Call selection considers game context, coach authority, opponent reads, installed package eligibility, familiarity, personnel and situational finishing decisions. Execution depends on the actual player contest and legal resolution, not on a label.

The catalog lives in data/playbooks; read the catalog itself for package IDs, requirements and effects. Program installation persists across seasons, revalidates roster fit and responds to coaching turnover. No new family or package should bypass the existing eligibility and game-result contracts. See [coaching](../COACHING_SPEC.md), [full rules](../RULES.md), [development plan](DEVELOPMENT_PLAN.md) and the dated package/calibration AARs.

When adding or tuning a school, document tradeoffs, legal choices, roster requirements, matched controls, context-specific outcomes and natural adoption. Test the combined engine. No blanket scoring bonus or guaranteed balance target.
