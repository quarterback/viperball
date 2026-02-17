# Viperball: Building a Fictional Sport from Scratch and the Simulation Engine That Plays It

**A case study in game design, iterative calibration, and the surprising depth of building something no one's ever seen before.**

---

## Part 1: What is Viperball?

### The Elevator Pitch

Viperball is a fictional full-contact field sport — think American football meets Australian Rules meets CFL rugby chaos. It's played on a 100-yard field with 6 downs to gain 20 yards, lateral chains that let the ball fly backward through four or five sets of hands on a single play, snap kicks worth 5 points that can be attempted on any down, and a scoring system where half-points exist because a defensive player dove on a loose ball in the mud.

It is, fundamentally, a sport designed to create stories. Every game produces moments — a Viper catching a lateral at the 40, pitching it to a Flanker who breaks a tackle and dives into the end zone. A kicker lining up a 52-yard snap kick in a sleet storm. A Chain Gang offense stringing together four laterals in the final minute of a tie game, with every handoff carrying the risk of a fumble that ends everything.

### The Field and Flow

The basic structure will feel familiar if you've watched football:

- **100-yard field**, goal line to goal line
- **6 downs** to gain **20 yards** for a new set of downs
- Possession changes on turnovers, punts, scores, or failure to convert

But that's where the similarities start to diverge.

### Scoring

Viperball uses a multi-tiered scoring system that rewards different types of success:

| Score | Points | How It Happens |
|-------|--------|----------------|
| **Touchdown** | 9 | Ball crosses the goal line on a run or lateral play |
| **Snap Kick** | 5 | Drop kick through the uprights (can be attempted on any down) |
| **Field Goal** | 3 | Place kick through the uprights (traditional set piece) |
| **Safety** | 2 | Defense tackles the ball carrier in their own end zone |
| **Pindown** | 1 | CFL-style rouge — a kick reaches the end zone and isn't returned |
| **Bell / Strike** | ½ | Recovering an opponent's loose ball — fumbles, blocked kicks, snap kick deflections |

The half-point scoring is one of Viperball's signature elements. Bells can happen on any play — a fumbled handoff, a botched lateral, a blocked punt recovered by the defense, or even a Keeper deflecting a snap kick attempt and pouncing on the ball. Final scores routinely include halves — 47½ to 38, 52 to 41½ — and it means the game is never truly "over" until the clock hits zero, because a loose ball recovery can always shift the margin.

### The Positions

Viperball rosters are built around four position groups, each with distinct archetypes:

**Zeroback (ZB)** — The primary ball handler and field general. Doesn't throw forward passes (there are none in Viperball), but handles the snap, makes option reads, and can attempt snap kicks. Four archetypes:
- *Kicking ZB*: Snap kick threat from anywhere past midfield
- *Running ZB*: Elusive runner, forces the defense to stack the box
- *Distributor ZB*: Lateral chain maestro, feeds the Vipers
- *Dual-Threat ZB*: Does everything at a B+ level

**Viper (VP)** — The playmaker. Lines up in motion, takes laterals, runs jet sweeps, creates chaos. The position the sport is named after. Four archetypes:
- *Receiving Viper*: Lateral target, chain finisher
- *Power Viper*: Runs through contact, short-yardage weapon
- *Decoy Viper*: Draws coverage, creates space for others
- *Hybrid Viper*: Can do anything, unpredictable

**Flanker (WB/HB)** — The workhorses. Halfbacks and wingbacks who carry the ball on dives, powers, and sweeps. Four archetypes:
- *Speed Flanker*: Breakaway threat, stretch plays
- *Power Flanker*: Between-the-tackles grinder
- *Elusive Flanker*: Juke moves, hard to bring down
- *Reliable Flanker*: Rarely fumbles, consistent yards

**Keeper (KP)** — A unique position with no real-world equivalent. The Keeper is the last line of defense on kick plays — they field missed kicks and punts in the end zone, deciding whether to return the ball or take the pindown. Three archetypes:
- *Return Keeper*: Speed demon, turns missed kicks into scoring chances
- *Sure-Hands Keeper*: Never muffs, secures possession
- *Tackle Keeper*: Closing speed, makes last-ditch stops on breakaways

### The Lateral Chain

This is the heart of Viperball. There are no forward passes. Instead, the ball moves laterally or backward through chains of players:

1. The Zeroback takes the snap
2. They can hand off, pitch, or run
3. At any point during the play, the ball carrier can throw a lateral to any teammate behind them
4. That player can lateral again, and again
5. Each lateral carries compounding fumble risk — the more hands the ball touches, the more likely something goes wrong

A typical lateral chain play might involve 2-3 laterals. An aggressive Chain Gang offense might string together 4-5 in a single play. Every lateral is a dice roll — the defense is sprinting to converge, the ball is moving backward, and one bad toss means a live ball on the ground.

When the defense recovers a loose ball — whether from a fumbled lateral, a muffed handoff, or a blocked kick — that's a **Bell**. Half a point for the recovering team, plus possession. Lateral chains are the most common source of Bells because every handoff is a chance for something to go wrong, but they can happen on any play. It's the sport's way of making every loose ball meaningful.

### The Kicking Game

Viperball has a deep, nuanced kicking game with multiple kick types:

**Snap Kicks (Drop Kicks)** — Worth 5 points. The kicker drops the ball and kicks it as it bounces off the ground, through the uprights. Can be attempted on *any* down, from anywhere on the field. This is the high-risk, high-reward option — harder to execute than a place kick, but worth nearly double the points. A Kicking ZB archetype lives for these moments.

**Place Kicks (Field Goals)** — Worth 3 points. Traditional set-piece kick. Teams line up, the ball is snapped and held, and the kicker boots it through the uprights. More reliable but worth fewer points. The current game philosophy heavily favors attempting field goals over punting — if your drive stalls at the opponent's 45-yard line, you take the shot. Even from 50+ yards out, the chance at 3 points is typically better than flipping field position.

**Punts** — No points, but a critical tool for field position. A good punter can pin the opponent deep, and if a punt reaches the end zone and isn't returned, it's a Pindown (1 point) under CFL-style rouge rules.

**Kickoffs** — After scores, the ball is kicked off. If the kickoff reaches the end zone and isn't returned, it can also result in a pindown.

### The Rouge/Pindown System

Borrowed directly from the CFL, the pindown (rouge) adds a fascinating strategic layer:

When any kick — punt, missed field goal, missed snap kick, or kickoff — reaches the end zone, the receiving team's Keeper must decide: try to return it, or take a knee. If they take a knee (or fail to get the ball out of the end zone), the kicking team gets 1 point and the receiving team gets the ball at the 25-yard line.

This means every kick has point-scoring potential, even punts. A team's punting strategy isn't just about field position — it's about whether they can boom a 60-yard punt into the end zone for a free point.

### Weather

Six weather conditions that meaningfully impact gameplay:

- **Clear**: No modifiers. Pure football.
- **Rain**: Wet ball, slippery field. Fumbles up, kick accuracy down, everyone slower.
- **Snow**: Cold and slippery. Major kick accuracy loss, moderate fumble increase.
- **Sleet**: The worst. Extreme fumble risk, terrible kicking, exhausting conditions.
- **Extreme Heat**: Rapid stamina drain. Teams fatigue fast, but the ball stays dry.
- **Heavy Wind**: Kick accuracy heavily impacted, but punt distance gets a boost from the gusts.

Weather isn't cosmetic — it changes how games play out. A Chain Gang offense built on high-risk lateral plays is terrifying on a clear day and a turnover factory in sleet. A Boot Raid team that relies on snap kicks becomes much less dangerous in heavy wind.

### Penalties

42 penalty types across 5 phases of play (pre-snap, during run plays, during lateral plays, during kick plays, post-play). Includes standard football penalties plus Viperball-specific infractions:

- **Illegal Viper Alignment**: The Viper lined up wrong
- **Illegal Viper Contact**: Hitting the Viper illegally
- **Lateral Interference**: Disrupting a legal lateral throw
- **Illegal Forward Lateral**: The lateral went forward — that's not allowed

Weather increases penalty rates (wet conditions = more false starts, more holding). The 4th quarter with under 5 minutes left increases penalty rates by 15% — pressure does that to players.

---

## Part 2: The Offensive Playbook — 9 Styles of Viperball

One of the deepest features in the simulation is the offensive playstyle system. There are 9 distinct offensive philosophies, each producing noticeably different games:

### Ground & Pound
*"Grind 20 yards, punch it in. Old-school power football using all 6 downs."*

Heavy on dives and power runs. Low tempo, low lateral risk. This offense doesn't need to be fancy — it just needs to gain 3-4 yards per play consistently and let the 6-down system do the rest. Strongest against defenses that can't stop the run.

### Lateral Spread
*"Stretch the defense horizontally with constant lateral chains."*

The opposite of Ground & Pound. High variance, high reward. The ball flies sideways constantly, creating big plays and big turnovers in equal measure. Bell rates are high — both for and against. This is a style that makes highlight reels and blooper reels.

### Boot Raid
*"Get to the Launch Pad, then bomb it through the uprights."*

An aggressive kick-focused offense that tries to advance the ball to the "Launch Pad" zone (field position 55-85) and then switches to kick-heavy play selection. When in the Launch Pad, the offense dramatically increases its snap kick and place kick attempts. Essentially, this offense treats the 40-yard line the way other offenses treat the red zone.

### Ball Control
*"Don't turn it over. Don't give it back. Take the points."*

Conservative, clock-eating, mistake-free football. Favors dive options and power runs, rarely risks laterals. When the ball gets into field goal range, this offense kicks it — no heroics, just points. Lowest fumble rates of any style.

### Ghost Formation
*"Misdirection and Viper chaos. The defense never knows what's coming."*

Counter plays, Viper jets, and constant motion. This offense uses the Viper position more aggressively than any other style, running jet sweeps and counter misdirection plays at a high rate. When it works, the defense is guessing wrong on every play. When it doesn't, it can stall.

### Rouge Hunt
*"Defense-first offense. Pin them deep, force mistakes, score on the margins."*

The most unusual philosophy. This offense actually *wants* to punt — deep punts into the end zone for pindown points. When trailing with long yards to go in their own territory, they'll punt early (even on 3rd down) to flip the field and generate rouge points. It's a death-by-a-thousand-cuts approach that wins ugly.

### Chain Gang
*"Four laterals. Five laterals. Who's counting? The ball doesn't stop moving."*

Maximum lateral plays. In close games, the Chain Gang amplifies its lateral selection even further. This offense generates the most Bells (defensive fumble recoveries) of any style — both for and against. It's feast or famine, and it's incredibly fun to watch.

### Triple Threat
*"Single-wing misdirection. Direct snaps to the Power Flanker. Three players who can all score."*

Old-school formation with modern chaos. Heavy on counters and draws on early downs, keeping the defense off-balance about who's actually getting the ball. The Zeroback, Viper, and Flanker are all primary threats, making defensive assignment nearly impossible.

### Balanced
*"Read the defense, take what they give you."*

No strong tendencies. Adapts to the game situation with moderate tempo and a mix of everything. It's the default style and the hardest to game-plan against because it doesn't commit to anything. Jack of all trades, master of none.

---

## Part 3: Building the Simulation Sandbox

### What Is It?

The Viperball Simulation Sandbox is a browser-accessible playtesting and debugging environment for the game engine. It's not a consumer game — it's a development tool, built in Python with a Streamlit frontend, designed to let you run thousands of simulated games and analyze every detail of what happened.

Think of it as the "test lab" for the sport itself. When a rule change is proposed, we simulate 500 games and see how it shifts the statistical landscape. When a new playstyle is added, we validate it against every other style to make sure it produces reasonable outputs.

### The Five Pages

**Game Simulator** — Pick two teams, choose their offensive and defensive styles, select weather conditions, and simulate a single game. Get a full box score, drive-by-drive breakdown, play-by-play log with quarter filters, penalty tracker, player archetype performance table, and a debug panel with fatigue curves, explosive play data, and custom Viperball sabermetrics (OPI, Territory, Pressure, Chaos, Kicking, Drive Quality, Turnover Impact).

**Season Simulator** — Configure 8-12 game regular seasons with conference round-robin scheduling, 4/8/12/16-team playoff brackets, and a bowl system for non-playoff teams. Features standings tables, radar charts comparing team profiles, and score distributions. Every game gets random weather.

**Dynasty Mode** — The crown jewel. A multi-season career mode where you coach a team across years. Features:
- Customizable conference structures with auto-generated themed names (geographic, mythological, Viperball lore)
- Top 25 poll system tracking team rankings across the season
- Coach dashboard with career wins, championships, playoff appearances
- Team history tracking across seasons
- Record book (most wins, highest scoring, best defense, most chaos, best kicking)
- Season awards (champion, best record, individual honors)
- Injury tracking and player development

**Debug Tools** — Batch simulation mode. Run 5-200 games at once, select weather conditions, and analyze aggregated statistics: average fatigue curves, turnover rates, drive outcome distributions, and calibration metrics. This is where tuning happens.

**Play Inspector** — Execute a single play repeatedly under controlled conditions. Set the down, distance, field position, weather, and offensive/defensive styles, then run the same play 100 times to see the distribution of outcomes. Essential for tuning individual play mechanics.

### The API

In addition to the Streamlit UI, there's a FastAPI REST API that provides programmatic access:
- `POST /simulate` — Run a single game
- `POST /simulate_many` — Batch simulation
- `POST /debug/play` — Single play inspection
- `GET /teams` — List available teams

All endpoints accept weather parameters and return detailed statistical breakdowns.

---

## Part 4: The Development Journey — Iterating on Chaos

### The Calibration Problem

The fundamental challenge of building a sports simulation is that everything is connected. Change the fumble rate and you change the scoring. Change the scoring and you change the kick decision logic. Change the kick decision logic and you change the punt rate. Change the punt rate and you change the pindown frequency. And on and on.

We maintain 7 per-team-per-game statistical targets that the engine must hit:

| Stat | Target Range |
|------|-------------|
| Touchdowns | 3-5 per team |
| Place Kick Attempts | 3-5 per team |
| Snap Kicks | 1.5-2.5 per team |
| Bells (Fumble Recoveries) | 2-4 per team |
| Punts | 3-5 per team |
| Safeties | 0.1-0.3 per team |
| Total Score | 40-60 per team |

Getting all 7 into their target ranges simultaneously is like tuning a 7-string guitar where tightening one string loosens another. It took multiple major calibration passes to get right.

### Key Iterations

**The Place Kick Crisis (v3.6)**
Early in development, place kicks were basically non-existent — teams were attempting 0.02 field goals per game. The kick decision engine was too aggressive about "going for it," and the expected value calculation for field goals was underweighting the certainty of 3 points versus the risk of a turnover on downs.

The fix was a complete overhaul of the kick decision engine: EV-based kick evaluation with a reliability boost for place kicks, reduced go-for-it aggression on later downs, a probabilistic "take the points" mechanic, and hard override rules. Place kicks went from 0.02/game to 1.5/game overnight.

But we didn't stop there. The philosophy evolved further — the user's vision was that teams should be attempting field goals *aggressively*, even from 40+ yards out. Instead of punting when a drive stalls at midfield, teams should be taking a shot. In the current version, the EV multiplier for place kicks is 2.60x (meaning the engine values a field goal attempt at 2.6 times its raw expected value), and teams can attempt kicks from up to 65 yards out. The kick evaluation now triggers as early as 3rd down when a team is in range with long yards to go.

The result: 3+ place kick attempts per team per game, with teams regularly lining up for 48, 52, even 55-yard field goals instead of punting. Success rate is secondary — the attempt frequency is what matters.

**The Snap Kick Saga**
Snap kicks went through the opposite journey. The original calibration target was 0.5-1.5 per team per game, and early versions struggled to hit even the low end. Through multiple rounds of tuning — boosting shot play frequency, increasing drop kick success rates, giving the Kicking ZB archetype a 1.20x boost with a snap kick trigger — the rate climbed to 1.78-2.23 per game.

The revelation was that this was actually *better* than the original target. Snap kicks are one of Viperball's most exciting plays — a 5-point drop kick from 45 yards on 3rd down changes the entire complexion of a game. Having nearly 2 per game per team means they're a regular part of the action without being so common they lose their impact.

The original 0.5-1.5 target was updated to 1.5-2.5 to reflect the reality that more snap kicks make better games.

**The CFL Rouge/Pindown Overhaul**
Adding CFL-style rouge rules was a significant mechanical addition. Every kick type — punts, missed field goals, missed snap kicks, kickoffs — now checks whether the ball reaches the end zone. If it does, the receiving team's Keeper has a return chance based on speed, with a pindown bonus for sure-handed Keepers. If the ball isn't returned, it's 1 point for the kicking team.

This created a fascinating strategic dynamic: punt distance had to be boosted (punts from deep in your own territory now average 55-62 yards) to make rouge hunting viable, and the Rouge Hunt offensive style was built entirely around exploiting this mechanic.

**The Keeper Position (v3.6)**
The Keeper was added specifically to give the rouge/pindown system a human element. Instead of punts into the end zone being automatic pindowns, there's now a player back there making decisions. The three Keeper archetypes create different defensive identities: a Return Keeper turns your opponent's deep kicks into scoring chances, while a Sure-Hands Keeper guarantees you'll never muff a catch.

Keepers also have a snap kick deflection mechanic — they can tip an incoming snap kick attempt, potentially recovering the ball and earning a half-point Bell for their team.

**The 9-Style Overhaul (v3.12)**
The original engine had 5 offensive styles. The v3.12 overhaul replaced them with 9 mechanically distinct philosophies, each with:
- Unique play family weights (what percentage of plays are dives vs. sweeps vs. laterals)
- Style-specific situational modifiers that activate under certain game conditions
- Different tempo, lateral risk, kick rate, and option read tendencies

The style-specific situational system is the most technically interesting piece. Each style has triggers that modify play selection based on game context:
- Boot Raid switches to kick-heavy weights when in the "Launch Pad" zone
- Ghost Formation boosts counter and Viper jet play rates
- Rouge Hunt triggers early punts when trailing with long yards-to-go in their own half
- Chain Gang amplifies lateral selection in close games
- Triple Threat boosts counter and draw plays on early downs

Validation required running 100 games per style (900 total) and confirming that all 9 styles produce statistics within the target ranges while still feeling mechanically distinct from each other.

### The Run Game Resolution System

Every run play goes through a 5-phase resolution:

1. **Carrier Selection**: Based on the play family and available player archetypes
2. **Yard Calculation**: Base yards from play config, modified by offensive/defensive style matchup, player speed, archetype bonuses, fatigue, and weather
3. **Defensive Resolution**: Tackles for loss, defensive wall stiffening at certain field positions, breakaway checks
4. **Fumble Check**: Base fumble rate per play type, modified by weather, fatigue, and player archetype
5. **Result Determination**: Touchdown, first down, gain, loss, fumble, or safety

There are 7 distinct run play families, each with different risk/reward profiles:

| Play Family | Base Yards | Fumble Rate | Character |
|-------------|-----------|-------------|-----------|
| Dive Option | 7.5-9.5 | 2.0% | Safe, consistent, bread-and-butter |
| Power | 8.0-10.0 | 2.2% | Physical, between the tackles |
| Sweep Option | 8.5-11.5 | 2.6% | Wide, high ceiling |
| Speed Option | 9.0-12.5 | 2.8% | Explosive, risky |
| Counter | 8.0-12.0 | 2.4% | Misdirection, high variance |
| Draw | 8.5-12.5 | 2.2% | Delayed handoff, breaks containment |
| Viper Jet | 10.0-14.0 | 3.0% | Highest ceiling, highest risk |

### Weather as a Game-Changer

Weather isn't just a flavor modifier — it fundamentally changes which strategies are viable:

| Condition | Fumble Impact | Kick Impact | Stamina Impact | Speed Impact |
|-----------|--------------|------------|----------------|-------------|
| Clear | — | — | — | — |
| Rain | +2.5% | -8% accuracy | +10% drain | -3% |
| Snow | +2.0% | -12% accuracy | +15% drain | -5% |
| Sleet | +3.5% | -15% accuracy | +20% drain | -6% |
| Heat | +1.0% | -2% accuracy | +30% drain | -2% |
| Wind | +0.5% | -10% accuracy | +5% drain | -1% |

A Chain Gang offense (high lateral rate, high fumble exposure) in sleet is a disaster waiting to happen. A Boot Raid offense (kick-dependent) in heavy wind loses its primary weapon. Weather forces adaptation, and the best teams are the ones whose style can survive bad conditions.

---

## Part 5: Lessons Learned

### 1. Everything Is Connected
You cannot change one variable in a sports simulation without affecting others. The kick decision engine, the fumble rate, the punt distance, the rouge probability, the scoring rate — they're all in a web of dependencies. Calibration is always a holistic exercise.

### 2. Targets Are Guidelines, Not Laws
The snap kick rate taught us this. The original target was 0.5-1.5 per game. The actual rate settled at 1.78-2.23. Rather than forcing the number down, we asked: does this produce better games? The answer was yes. The target was wrong, not the simulation.

### 3. Batch Validation Is Non-Negotiable
You cannot tune a stochastic simulation by running 5 games and eyeballing it. We validate with 100-500 game batches, check per-style breakdowns, and only accept changes when all metrics across all styles land in their target ranges. Individual games are too noisy to draw conclusions from.

### 4. Style Differentiation Requires Situational Triggers
Early playstyles were just different weight distributions for play selection. That made them statistically different but not *mechanically* different. Adding situational triggers — Boot Raid's Launch Pad, Rouge Hunt's early punt, Chain Gang's close-game amplification — made each style play differently in ways you can actually feel during a simulated game.

### 5. Half-Points Are Brilliant
The half-point Bell scoring was a late addition, and it transformed the sport. Final scores with halves feel distinctly *Viperball*. Every fumble recovery matters. A 47½ to 47 game means someone won because they dove on a loose ball in the 3rd quarter. It adds a layer of granularity to scoring that makes every play consequential.

---

## Current State (v3.12)

The simulation currently produces these per-team-per-game averages across all 9 offensive styles:

- **Touchdowns**: 3.0-4.0
- **Place Kick Attempts**: 2.4-3.2
- **Snap Kicks Attempted**: 1.6-2.1
- **Bells**: 1.0-4.0 (varies heavily by style)
- **Punts**: 2.2-2.6
- **Safeties**: 0.07-0.30
- **Total Score**: 42-52

The sandbox runs in a browser via Streamlit, with a FastAPI backend for programmatic access. It supports single-game simulation, season mode, dynasty mode, debug batch testing, and single-play inspection.

---

*Viperball doesn't exist yet. But it has rules, statistics, archetypes, weather effects, 30+ penalties, 9 offensive philosophies, a dynasty mode with a record book, and a simulation engine that's been calibrated across thousands of games. Sometimes the best way to understand a sport is to build one from scratch.*
