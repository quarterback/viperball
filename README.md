# Viperball

Viperball is a fictional gridiron sport and a playable sports simulation universe. Manage a women's college program across generations, follow professional and international competitions, or study the game through its play-by-play and analytics.

## Start playing

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Open [http://localhost:5000/stats/](http://localhost:5000/stats/). Use College or Dynasty to start a season or career. The stats site is the main interface for league play and management; the Python application also retains NiceGUI pages. No Node/React build or desktop GUI launcher is required.

- [Quick start](QUICKSTART.md) — installation, first season, saves and analytics.
- [Game modes and features](FEATURES.md) — the college, high-school, professional, WVL and international systems.
- [Full rulebook](RULES.md) and [CVL competition rules](COLLEGE_RULES.md) — the sport and league regulations.
- [Analytics](ANALYTICS.md) — the portal, formulas, scoring and model limitations.
- [Coaching](COACHING_SPEC.md) and [tactical schools](docs/OFFENSE_SCHEMAS.md) — game plans, staff and careers.
- [Engine](ENGINE_README.md), [application architecture](ARCHITECTURE_STATS_SITE_AND_RECRUITING.md) and [stats-site guide](docs/stats-site.md) — for developers.
- [Documentation index](docs/README.md) and [current development plan](docs/DEVELOPMENT_PLAN.md) — current references and unresolved validation.

## Playbook Cookbook

Choose **Playbooks** in the main menu to open `/stats/playbooks`. Choose an offensive or defensive school, add one to four compatible packages, and preview their formations and intended actions on an animated 2D field. Save your book or share it as JSON. Imported books open as drafts for review before saving.

Open **Practice and paired plays** to share a fixed amount of practice across eligible packages. A compact book builds familiarity faster. A broader book prepares more ways to respond. You can give one package extra practice or group two offensive packages that start in the same formation. The college team page shows how much practice each package received.

During a college game, a caller can use one play in a pair to observe the defensive front and follow with a different action from the same formation. If the defense crowds the formation and the other package fits, the caller may come back to that look. See **Drive plan** in the box score for the observed front, eligible packages and what took priority on a given snap.

Choose an offensive book, a defensive book, or both when setting up a standalone college season or a dynasty. The coordinator considers package fit and game situation during the normal season simulation. Enable **Let computer teams use saved playbooks** to give some computer teams compatible books, even in a college season where you manage zero teams. The box score shows which packages the coordinator could call, selected, and ran.

Offensive packages include **Viper Trail**, which gives a receiver the option to lateral to a support runner after a short kick pass. **Far Side Coil** and **Third Strike** use earlier calls in the same drive to set up an attack to the other side. **Bonus Guard** favors inside runs and short outlets while an extra drive is pending. **Pindown Chase** can trade a low value sixth down scoring attempt for a directional punt when the score is tied or the team leads by at most five points. **Cape Cod** comes in two halves. On offense, a lateral chain goes toward one sideline; if the defense chases it, the next call hooks back inside with a counter run on the other side, and if the defense crowds the middle, the next call kicks across the field. On defense, the trap lets the chain reach the sideline, makes each later pitch riskier and clogs the cutback lane, at the cost of a thinner middle against straight inside runs and an early kick across.

See the [quick start](QUICKSTART.md#build-a-custom-playbook) and [package catalog](docs/playbook_packages/INVENTORY.md).

## The simulation today

The engine resolves individual plays with actual participating players, six-down possession, legal kicks and returns, defensive commitments, line changes, injuries and officiating. Weather evolves by period and affects the field and kicking conditions. The college dynasty connects recruiting, high-school competition, transfers, development, contracts, coaching careers and installed playbooks. Professional, WVL and international games use the full engine; ordinary high-school games use a fitted quicker model, with title games on the full engine.

The college Analytics tab opens thirteen views including player and team leaderboards, all scoring channels, expected points, decision value, Delta and bonus context, DTW, play and drive finders, comparisons and a glossary. Group plays by school, down or field zone; inspect individual records and export CSV. State-value and decision estimates are experimental and use supported held-out observations. The existing published EPA and DTW remain separate.

**Documentation status:** November 27, 2026. The [development plan](docs/DEVELOPMENT_PLAN.md) tracks deployment and national validation.

---

## Where This Started

It started with a Reddit thread.

Someone in r/CFB posted a hypothetical: *[What if the entire 1894 Yale team came back to life and played a modern college football team?](https://www.reddit.com/r/CFB/comments/1r4qgd3/what_if_the_entire_1894_yale_team_came_back_to/)* The discussion spiraled into something more interesting than the original question — if early football teams played under rules closer to their own era, no forward pass, heavier emphasis on kicking, no specialized roles, what would a *modern* version of that game actually look like?

That question is Viperball.

**Viperball** is a gridiron football code designed for speed, tactical kicking, and lateral ball movement. It is the primary sport of the **Collegiate Viperball League (CVL)**, a 205-team women's collegiate athletic conference system across the United States.

The sport evolved from early American football's pre-forward-pass era, retaining the centrality of kicking, two-way play, and lateral ball handling while developing its own modern strategic identity. Viperball uses a Canadian football (CFL-spec) ball, employs no forward passing of any kind, and features a distinctive multi-channel scoring system.

## Contents

1. [Overview](#overview)
2. [The Field](#the-field)
3. [Game Structure](#game-structure)
4. [Downs and Possession](#downs-and-possession)
5. [Movement of the Ball](#movement-of-the-ball)
6. [Scoring](#scoring)
7. [Positions](#positions)
8. [Kicking](#kicking)
9. [The Lateral Game](#the-lateral-game)
10. [Fumbles and Turnovers](#fumbles-and-turnovers)
11. [Out of Bounds](#out-of-bounds)
12. [Formations and Motion](#formations-and-motion)
13. [Tackling and Player Safety](#tackling-and-player-safety)
14. [Special Teams and Restarts](#special-teams-and-restarts)
15. [Penalties](#penalties)
16. [Officials](#officials)
17. [Overtime](#overtime)
18. [Weather](#weather)
19. [Game Day](#game-day)
20. [Coaching Staffs and Team Installation](#coaching-staffs-and-team-installation)
21. [Roster and Substitution Rules](#roster-and-substitution-rules)
22. [Glossary](#glossary)

---

## Overview

Viperball is played between two teams of 11 players on a 100-yard field. The objective is to advance the ball into the opposing team's end zone or score through kicking. There is no forward pass. The ball is advanced by running, lateral passing (backward or sideways), and kick passing (a kicked ball to a teammate downfield). Kicking is both an offensive weapon and a scoring method — teams routinely score by drop-kicking the ball through the uprights during live play.

Points come from touchdowns, snap kicks, field goals, safeties, pindowns, and bells. How much a game scores comes from the rules and the players. The sport rewards versatile athletes who can run, kick, catch, and tackle — most players contribute on both sides of the ball.

### Design Heritage

Viperball occupies a distinct place in the gridiron family. It shares field dimensions and down-based possession with American and Canadian football, but its prohibition of the forward pass and emphasis on live-ball kicking give it a rhythm closer to rugby union's kicking game or Australian rules football's contested ball. The sport was intentionally developed to reward technical proficiency, lateral coordination, and endurance — qualities common in elite women's athletics across soccer, rugby sevens, and track.

### The Ball

The official game ball is a **CFL-spec Canadian football**:

- **Circumference:** 12⅞ to 13⅛ inches (short axis); 27¾ to 28¼ inches (long axis)
- **Weight:** 14 to 15 ounces
- **Inflation:** 12.5 to 13.5 psi

The Canadian football's slightly rounder profile compared to an American football improves drop-kick accuracy and bounce predictability, both of which are central to Viperball strategy.

---

## The Field

The playing surface is a standard 100-yard gridiron:

- **Playing field:** 100 yards, goal line to goal line
- **End zones:** 10 yards deep at each end
- **Width:** 53⅓ yards
- **Yard lines** marked every 5 yards, numbered every 10 from each goal line to midfield
- **Hash marks** at standard NCAA spacing
- **Goal posts** at the back of each end zone, standard dimensions

The field is identical to a standard American college football field. No additional markings are required.

---

## Game Structure

### Quarters and Halftime

A regulation game consists of **four 10-minute quarters** (a 40-minute game) with a running game clock:

- **1st and 2nd quarters** make up the first half
- **Halftime** interval between the 2nd and 3rd quarters
- **3rd and 4th quarters** make up the second half

### The Clock

The game clock runs continuously with the following exceptions:

- **Scoring plays** — clock stops until the subsequent restart
- **Out of bounds** — clock stops (final 2 minutes of each half only)
- **Timeouts** — each team receives 4 per half; unused timeouts do not carry over
- **3-minute warning** — the clock stops once in each half when it crosses three minutes remaining
- **Penalties** — clock stops during enforcement
- **Injuries** — clock stops; team charged a timeout if injury occurs in final 2 minutes of a half
- **Official reviews** — clock stops

The offense has 40 seconds to snap. Delay of game is a 5 yard penalty and the down is replayed.

### Coach's Challenge

Each team has 3 challenges per game. A coach may challenge the spot of the ball, a turnover on downs, a fumble or interception ruling, a catch on a kick pass, or a short touchdown. Penalties cannot be challenged. The coach decides without seeing the replay, and replay decides whether the ruling stands.

### Coin Toss

The visiting team calls the coin toss. The winner chooses to receive, kick, or defer to the second half. The loser selects which end of the field to defend.

---

## Downs and Possession

Viperball uses a **6-down, 20-yard** system.

When a team takes possession of the ball, it has **six downs (plays) to advance the ball 20 yards**. If the team gains 20 or more yards from its starting field position, it earns a new set of six downs. This continues until the team scores, turns the ball over, or punts.

### Key Differences from American Football

| | American Football | Viperball |
|---|---|---|
| Downs | 4 | 6 |
| Yards to gain | 10 | 20 |
| Forward pass | Yes | No |
| Aerial game | Forward pass | Kick pass |

The 6-down/20-yard structure gives offenses more plays to work with but demands more total yardage per series. This creates longer, more sustained drives where fatigue becomes a genuine tactical factor. Teams cannot rely on a single explosive play to move the chains — they must string together consistent gains or use the kicking game strategically.

### Turnover on Downs

If a team fails to gain 20 yards in six downs, the opposing team takes possession at the spot of the ball and starts a fresh series: 1st and 20.

### When Teams Kick

A snap kick is legal on any down. It is a shot at goal from open play, in the spirit of Australian rules and Gaelic football. Because a missed snap kick on downs 1 through 5 keeps the ball (see [Missed Snap Kicks](#missed-snap-kicks)), coaches follow a simple logic:

- **Downs 1 through 3:** advance the ball and chase the 9-point touchdown. The exception is late in a half: in the last two minutes, a team in range takes the shot on any down when the points matter.
- **4th down:** kick only when the drive has stalled, the first down is far away, and the kicker is in range.
- **5th down:** the natural kicking down. A miss still leaves 6th down for a second try.
- **6th down:** the last chance. A miss here is a turnover, so a team kicks, punts, or goes for it. A trailing team never punts on 6th down.

A field goal is the answer when a drive stalls outside snap kick range. Off a tee the ball carries farther than a drop kick, so a team that cannot get close enough for its snap kicker still puts 3 points on the board on 4th, 5th or 6th down.

Near the goal line, teams keep driving for the touchdown. Late in a game, a team does not take a kick that cannot tie or win.

How soon a team kicks depends on its offense. Kick first offenses such as Boot Raid and Six Shooter take the shot earlier and from longer. Touchdown first offenses, Ground Control above all, keep driving on 4th down, need a longer 5th down before they kick, and go for it on 6th down with short yardage, more often inside the 25. Each offense also has its own appetite for going for it on 6th down instead of punting, and field position offenses such as Ironclad punt from farther up the field.

---

## Movement of the Ball

There are three legal methods of advancing the ball in Viperball:

### 1. Running

The ball carrier may run in any direction. Standard running plays include dives, power runs, sweeps, counters, draws, and option plays. The Zeroback (see [Positions](#positions)) is the primary ball handler, but any player may carry the ball.

Option plays are read live. On a dive option the Zeroback reads one defender: if that defender takes her, she gives to the diving back; if the defender takes the back, she keeps. On a speed or sweep option she keeps or pitches the same way. A Zeroback with more awareness than the defender reads it right more often, and some offenses train the read more than others. Kicking and distributing Zerobacks do not read; they hand off or pitch on the call.

### 2. Lateral Passing

A player may throw, toss, or hand the ball to a teammate who is **beside or behind** them. There is no limit to the number of lateral passes on a single play. A lateral that travels forward, even slightly, is an **Illegal Forward Lateral** (5 yards, loss of down).

Lateral passing is the primary method of distributing the ball to playmakers in space. Some offenses build their entire identity around multi-player lateral chains — sequences of 3, 4, or even 5 consecutive laterals on a single play. These chains are high-reward but carry genuine risk: every exchange is a potential fumble, and the risk compounds with each additional lateral.

A lateral that is dropped or not caught is a **live ball** — either team may recover it.

### 3. Kick Passing

A kick pass is a **kicked ball intended for a teammate downfield**. The kicker (typically the Zeroback) punts or drop-kicks the ball toward a receiver, who catches it and continues play. The ball is live until caught, meaning:

- If the intended receiver catches the ball, play continues — they may run, lateral, or kick again
- If a defender catches the ball, it is an **interception** — possession changes immediately and the defender may return the ball
- If the ball hits the ground without being caught, it is an **incomplete kick pass** — the ball is dead at the spot where it lands, and the offense retains possession but loses the down

Kick passing functions as Viperball's aerial game. It fills the strategic role that the forward pass occupies in American football, but with distinct characteristics: the ball takes longer to arrive, receivers have more time to find space, and the kicking team's coverage must react to a bouncing ball rather than a spiral.

**Yards after catch (YAC)** on kick passes tends to be high because receivers catch the ball in open space rather than in traffic.

---

## Scoring

Viperball uses a **six-channel scoring system**. Points are awarded for the following:

| Score | Points | How |
|---|---|---|
| **Touchdown (TD)** | **9** | Carrying or kicking the ball into the opponent's end zone |
| **Snap Kick (DK)** | **5** | Drop-kicking the ball through the uprights during live play |
| **Field Goal (PK)** | **3** | Place-kicking the ball through the uprights from scrimmage |
| **Safety** | **2** | Tackling the ball carrier in their own end zone, or the offense committing a foul in their own end zone |
| **Pindown** | **1** | A punt, missed snap kick, or missed field goal goes into the end zone and the receiving team does not return it out (see [Pindown](#pindown)) |
| **Bell** | **0.5** | Recovering a loose ball — fumble, muff, or bouncing kick (see [Bell](#bell)) |

There are **no extra point attempts or conversion plays** after touchdowns. The 9-point touchdown is a terminal score — after a TD, play restarts with the opposing team receiving.

### Why 9 Points for a Touchdown?

The 9-point touchdown is Viperball's most significant departure from other gridiron codes. By making a touchdown worth nearly twice a snap kick (5 points), the scoring system creates a natural risk/reward calculation: teams in scoring range must decide whether to take the guaranteed 5 points from a snap kick or push for the 9-point touchdown. This tension — kick or drive? — is the central strategic question in Viperball and is present on virtually every possession that crosses midfield.

### The Snap Kick

The snap kick (also called a **drop kick** or **DK**) is the signature scoring play of Viperball. The kicker drops the ball, lets it bounce once, and kicks it through the uprights — all during live play, without a holder or set piece. It can be attempted from anywhere on the field at any time during a possession.

In practice, snap kicks are reliably accurate within 40 yards and plausible out to 55 yards. Beyond that distance, the risk of a miss increases substantially and the ball may be fielded and returned by the defense (see [Missed Snap Kicks](#missed-snap-kicks)).

Snap kicks are to Viperball what the three-pointer is to basketball — the premium scoring play that defines offensive philosophy. Teams with elite kickers build their entire offense around reaching snap kick range (roughly the opponent's 40-yard line), while teams without a kicking specialist may prefer to grind for touchdowns.

### The Field Goal

A field goal (also called a **place kick** or **PK**) is a standard set-piece kick from scrimmage using a holder. It is worth 3 points. Place kicks are accurate at longer range than snap kicks — teams have successfully converted place kicks from beyond 60 yards — but they require stopping play to set up the kick, which means they cannot be used opportunistically the way snap kicks can.

The maximum practical range for a place kick in the CVL is approximately **71 yards**, though attempts beyond 55 yards are low-percentage.

Teams typically attempt place kicks when:
- They are outside reliable snap kick range but within field goal distance
- They want the higher accuracy of a placed ball vs. a drop kick
- The situation calls for guaranteed points rather than the risk of a longer drive

### Pindown

A pindown is worth **1 point** and is awarded to the kicking team when a punt, a missed snap kick, or a missed field goal goes into the end zone and the receiving team cannot return it out. The receiving team then takes possession at its own 25-yard line. A receiving team that does return the ball out of its end zone starts where the return ends, and no point is scored. Pindowns come most often from punts aimed at the corner of the end zone.

The pindown is Viperball's equivalent of the **rouge** or **single** in Canadian football — a field-position score that rewards directional kicking. Teams that specialize in territorial offense (notably those running the **Rouge Hunt** scheme) actively hunt pindowns as a scoring strategy, treating punts as offensive weapons rather than concessions.

A team that earns 4–6 pindowns in a game has added 4–6 points to its total without ever crossing midfield on offense. In close games, pindowns are often the margin of victory.

### Bell

A bell is worth **0.5 points** and is awarded when a team recovers a loose ball. This includes:

- Fumble recoveries
- Muffed punt recoveries
- Recovery of a bouncing or blocked kick

Play continues after a bell is awarded — the recovering team maintains possession and may advance the ball. The bell is a **live-ball score**: the half-point is added to the scoreboard immediately upon recovery, and the play continues.

The bell rewards aggressive, opportunistic defense. A team that forces 6 fumble recoveries in a game earns 3 additional points from bells alone. Combined with the field position advantage of the recovery, bells create compounding value from turnovers.

### Scoring Context

The multi-channel system means games are rarely decided by a single type of play. A team can fall behind on touchdowns but stay competitive through relentless kicking and field position — or vice versa.

---

## Positions

Viperball uses **11 players per side**. Positions fall into six categories:

### Offensive Positions

**Zeroback (ZB)** — The most important player on the field. The Zeroback lines up behind the offensive line and receives the snap. They are simultaneously the primary ball carrier, the team's kicker (for snap kicks and kick passes), and the lateral chain initiator. The name "Zeroback" reflects their position at the zero point of the offense — everything flows through them.

Zerobacks are classified by playing style:
- **Kicking ZB** — Primary threat is the snap kick. Rarely carries the ball; instead, reaches kicking range and fires. An elite Kicking ZB may attempt 6–8 snap kicks per game.
- **Running ZB** — Primary ball carrier who forces defenses to commit to the run. Less accurate kicker. Generates touchdowns through sustained drives.
- **Dual-Threat ZB** — Balanced runner and kicker with no clear defensive answer. The most common type.
- **Distributor ZB** — Gets playmakers the ball in space through lateral chains rather than running themselves. Orchestrates rather than executes.

**Viper (VP)** — A versatile skill player who lines up in various positions and moves before the snap. The Viper is Viperball's answer to the slot receiver — a mismatch creator who can line up anywhere and exploit defensive confusion. The Viper position is unique to Viperball.

Viper archetypes:
- **Receiving Viper** — Chain target in space, creates mismatches against slower defenders
- **Power Viper** — Short-yardage specialist and lead blocker
- **Decoy Viper** — Draws coverage and creates space for others through pre-snap motion
- **Hybrid Viper** — Competent at everything, defensive nightmare to game-plan against

**Flankers (Halfback, Wingback, Slotback)** — The supporting skill players. Flankers line up on the edges and in the backfield, serving as lateral chain targets, perimeter runners, and kick return specialists. Flanker archetypes:
- **Speed Flanker** — Breakaway threat on perimeter plays
- **Power Flanker** — Yards after contact, inside running, chain extensions
- **Elusive Flanker** — Missed-tackle generator in the open field
- **Reliable Flanker** — Low fumble rate, clock-control specialist
- **Diving Wing** — Kick-block specialist who times the kicker's release (see [Blocked Kicks](#blocked-kicks))

**Offensive Line (OL)** — Five linemen who block for the ball carrier and protect the Zeroback during kick passes and snap kicks. Offensive linemen are credited with **blocks** on positive-yardage run plays and **pancake blocks** on explosive gains.

### Defensive Positions

**Defensive Line (DL)** — The front line of the defense. DL players rush the Zeroback, stuff the run, and generate tackles for loss, sacks, and hurries.

**Keeper (KP)** — The last line of defense, analogous to a safety in American football. Keepers patrol the deep field, field missed kicks, make open-field tackles, and serve as kick returners.

Keeper archetypes:
- **Return Keeper** — Speed and open-field running; missed kicks become scoring chances
- **Sure-Hands Keeper** — Secures possession reliably, rarely muffs
- **Tackle Keeper** — Closing speed and last-ditch stops on breakaways

### Two-Way Play

The Viper and the flankers play both ways as midfield lines: the line on the field plays offense, and its four best tacklers play defensive back when the other team has the ball (see [Rotations](#rotations)). Flankers also frequently serve as kick coverage specialists.

---

## Kicking

Kicking is the most strategically distinctive element of Viperball. There are four types of kicks:

### Snap Kick (Drop Kick)

The snap kick is a live-ball scoring kick worth 5 points. The kicker drops the ball from their hands, allows it to bounce once on the ground, and kicks it through the uprights. Unlike a field goal, a snap kick does not require a holder, set piece, or stoppage — it is attempted during the flow of live play.

Snap kicks can be attempted from anywhere on the field. Practical range extends to approximately 55 yards, with accuracy declining sharply beyond 40 yards.

#### Missed Snap Kicks

On downs 1 through 5, a missed snap kick that stays in the field of play is treated as a **dead ball** — the kicking team retains possession and the down advances. This "retained possession on miss" rule (borrowed from Finnish baseball's foul-ball mechanic) means that short-range snap kick attempts carry very little risk.

However, **long-range misses (beyond approximately 50 yards)** may be fielded and returned by the defense as a live ball. The longer the attempt, the more likely the ball travels deep enough for a defender to field it. A missed 65-yard snap kick is more likely than not to be returned. This creates a natural risk/reward curve: short snap kicks are nearly free, but bombing from long range can give the opponent a return opportunity — or even a return touchdown.

On **6th down**, a missed snap kick of any distance is a turnover — the defense takes over at the spot of the kick.

### Place Kick (Field Goal)

The place kick is a set-piece scoring kick worth 3 points. The ball is held on the ground by a teammate while the kicker drives it through the uprights. Place kicks are more accurate at distance than snap kicks but require the offense to line up in a kicking formation, giving the defense time to set up a block attempt.

### Punt

A punt is a territorial kick used to surrender possession while pushing the opponent deep into their own territory. The punter drops the ball and kicks it before it hits the ground. Punts are the primary weapon for teams seeking **pindowns**: a punt into the end zone that the receiving team cannot return out scores 1 point, and the receiving team takes over at its own 25-yard line.

### Kick Pass

See [Movement of the Ball — Kick Passing](#3-kick-passing) for full details. The kick pass is an offensive play, not a special teams play.

### Blocked Kicks

Any kick — snap kick, place kick, or punt — may be blocked by a defender who gets a hand or body on the ball before it clears the line of scrimmage. A blocked kick produces a **loose ball** that either team may recover:

- If the defense recovers, they take possession and may return the ball. The recovering team earns a bell (0.5 points).
- If the kicking team recovers, the ball is dead and the down is consumed.
- A blocked kick returned for a touchdown scores 9 points plus the bell.

Certain flanker specialists — the **Diving Wing** archetype — are trained to time the kicker's release point and dive at the ball, increasing their team's chances of blocking kicks.

---

## The Lateral Game

Lateral passing is legal at any time during live play. A player with the ball may toss, flip, or hand it to any teammate who is **beside or behind** them relative to the line of scrimmage. There is no limit on the number of laterals per play.

### Lateral Chains

A **lateral chain** is a sequence of two or more consecutive laterals on a single play. Chains are a defining feature of Viperball — they create the sport's most exciting and chaotic moments.

A typical chain works like this:

1. The Zeroback takes the snap and runs right
2. They lateral to the Wingback trailing behind them
3. The Wingback reverses field and laterals to the Viper cutting left
4. The Viper turns upfield and is tackled — or laterals again

Each lateral in the chain carries risk. A bobbled exchange, a pass that drifts forward, or a defender reading the chain and jumping the lateral can all produce turnovers. The risk increases with each additional lateral in the chain — a 4-lateral chain is significantly more dangerous than a 2-lateral chain.

Teams that build their offense around lateral chains (the **Chain Gang** and **Lateral Spread** schemes) accept higher turnover rates in exchange for explosive, multi-directional plays that are nearly impossible to defend consistently.

### Fumbles on Laterals

A dropped lateral is a **live ball**. Either team may recover it. The recovering team earns a bell (0.5 points). Lateral fumbles are the primary source of turnovers in Viperball — they occur more frequently than kick pass interceptions and are often more impactful because they happen in open space with players scattered.

---

## Fumbles and Turnovers

### Fumbles

A fumble occurs when a ball carrier loses possession of the ball before being ruled down. A fumbled ball is **live** — either team may recover it. The team that recovers the fumble earns a **bell** (0.5 points) and possession.

Fumbles can result from:
- A ball carrier being stripped or losing grip during a tackle
- A dropped or bobbled lateral exchange
- A muffed kick or punt catch
- A blocked kick

If a fumble goes out of bounds, the team that last possessed the ball retains possession at the spot where the ball went out.

### Interceptions

A kick pass or lateral intercepted by a defender results in an immediate change of possession. The intercepting player may return the ball. An interception returned for a touchdown scores 9 points.

#### Bonus Possession

An interception also earns the intercepting team a **bonus possession**, a borrowed idea from pesäpallo and the hockey power play. After the intercepting team finishes the drive that follows its interception, it gets the ball again for an extra drive starting from its own 20-yard line, before the opponent's next possession. Any fumble or interception while a bonus is pending cancels it, and an interception during a bonus drive does not earn another one. A pending bonus does not carry over past halftime or the end of the game.

### Turnover on Downs

If the offense fails to gain 20 yards in six downs, the defense takes over at the spot of the ball. See [Downs and Possession](#downs-and-possession).

---

## Out of Bounds

A ball carrier is ruled out of bounds when any part of their body touches the sideline or the area beyond it. The ball is placed at the yard line where the carrier went out.

During the **final two minutes of each half**, the clock stops when a ball carrier goes out of bounds. At all other times, the clock continues to run.

A lateral or kick pass that goes out of bounds is dead at the sideline. If a lateral goes out of bounds behind the line of scrimmage, the ball is placed at the spot where it crossed the sideline.

---

## Formations and Motion

### Pre-Snap Requirements

The offense must have at least **five players on the line of scrimmage** at the time of the snap. The remaining six players may be positioned anywhere behind the line.

### The Viper Alignment

The Viper is permitted to line up in any position on the offensive side of the ball — on the line, in the backfield, on either edge, or in motion. However, the Viper must be **set for one full second** before the snap unless they are the single player in legal pre-snap motion. An **Illegal Viper Alignment** penalty (5 yards) is called when the Viper is not properly set or when multiple players are in motion at the snap.

### Pre-Snap Motion

One player may be in motion at the time of the snap, provided they are moving **parallel to or away from** the line of scrimmage (not toward it). The Viper is the most common motion player, but any eligible player may go in motion.

### Positional Freedom After the Snap

Once the ball is snapped, all positional restrictions are lifted. Any player may carry, kick, lateral, or receive the ball. Offensive linemen may receive laterals and advance the ball. The Zeroback may move to any position on the field. This complete positional freedom after the snap is a fundamental principle of Viperball.

---

## Tackling and Player Safety

### Legal Tackles

A ball carrier is ruled **down** when any part of their body other than their hands or feet touches the ground while in the grasp of a defender, or when their forward progress is stopped by contact.

### Prohibited Contact

The following forms of contact are illegal and result in penalties:

- **Facemask** — Grasping or pulling an opponent's face mask (15 yards, automatic first down)
- **Horse Collar** — Tackling by grabbing the back or inside collar of the shoulder pads (15 yards, automatic first down)
- **Chop Block** — An illegal low block on a defender already engaged by another blocker (15 yards)
- **Clipping** — Blocking an opponent from behind below the waist (15 yards)
- **Late Hit** — Contacting a ball carrier after the play is dead (15 yards)
- **Unnecessary Roughness** — Excessive force beyond what is needed to make a tackle (15 yards)
- **Roughing the Kicker** — Contacting the kicker during or after a kick (15 yards, automatic first down)

### Concussion Protocol

A player who exhibits signs of a concussion is immediately removed from the game and may not return. This is not discretionary — officials and medical staff have the authority to remove a player regardless of the player's or coach's wishes.

---

## Special Teams and Restarts

### Restarts After Scoring

Viperball does not use traditional kickoffs. After every score, the non-scoring team receives the ball and begins its possession under **Delta Yards**: the starting spot is its own 20-yard line, moved back one yard for every point it leads by and forward one yard for every point it trails by. A team down 14 starts at its own 34; a team up 10 starts at its own 10. A drive never starts behind the 1-yard line or past the opponent's 20. The elimination of the kickoff removes the most dangerous collision play in gridiron sports while maintaining the flow of the game, and Delta Yards keeps trailing teams within reach.

After a safety, the team that conceded it restarts from its own 20-yard line.

### Punt Returns

A player who catches a punt may return it upfield. Punt returns are among the most exciting plays in Viperball — a fast returner with open space can take a punt the distance for a 9-point touchdown. Muffed punts (drops) are live balls recoverable by either team, with the recovering team earning a bell.

### Kick Returns

Missed field goals and missed snap kicks that travel into the field of play may be fielded and returned by the defense. These returns follow the same rules as punt returns — the returner may advance the ball, lateral to teammates, or be tackled. Return touchdowns are worth 9 points.

---

## Penalties

The full penalty table, with every foul the game can call, is in [RULES.md](RULES.md#15-penalties). It is built from the engine's penalty catalog. These are the fouls called most often:

| Penalty | Yards | On | Notes |
|---|---|---|---|
| Holding | 10 | Offense | |
| Defensive Holding | 5 | Defense | Automatic first down |
| Illegal Block in Back | 10 | Offense | |
| Facemask | 15 | Defense | Automatic first down |
| False Start | 5 | Offense | |
| Offsides | 5 | Defense | |
| Unnecessary Roughness | 15 | Either | |
| Too Many Men on Field | 5 | Either | |
| Running Into Kicker | 5 | Defense | |
| Contact on Kickpass Receiver | 15 | Defense | Automatic first down |
| Illegal Forward Lateral | 5 | Offense | Loss of down |

Enforcement:

- Penalties are enforced from the spot of the foul unless noted; post play fouls from the succeeding spot.
- **Automatic first down** gives the offense a new set of downs whatever the distance.
- **Loss of down** applies to four fouls, all about the ball going forward illegally: Illegal Forward Lateral, Double Forward Lateral, Illegal Double Kickpass and Kickpass Out of Bounds.
- Live ball fouls may be accepted or declined by the team fouled against. An accepted live ball foul by the offense wipes out the play, including any score or change of possession on it.
- Fair Catch Interference and Kick Catch Interference are fouls by the kicking team on punts.

---

Targeting, fighting and throwing a punch require ejection. A second qualifying unsportsmanlike foul in the same game also requires ejection. The ejected player cannot return, even if the penalty yardage is declined; a legal substitute may play. See the full rulebook for qualifying conduct.

## Officials

A standard CVL officiating crew consists of:

- **Referee** — Final authority on all calls
- **Umpire** — Watches the line of scrimmage
- **Head Linesman** — Manages the down markers and sideline
- **Line Judge** — Opposite sideline, watches for out-of-bounds
- **Back Judge** — Deep field, rules on kicks through the uprights and deep plays
- **Side Judge** — Watches the Viper position for alignment violations and illegal contact

The sixth official (Side Judge) is unique to Viperball and exists because the Viper position's pre-snap freedom creates officiating challenges not found in other gridiron sports.

Officials do not flag every foul. A foul that happens can be called, let go because it did not affect the play (holding away from the ball, a word after the whistle instead of a flag), or missed. Fouls in plain view, such as false starts and forward laterals, are almost always flagged; holding and coverage contact are flagged mostly when they affect the play. Crews differ in how tightly they call a game, a crew that leans toward the home side misses a few more home fouls on close calls, and late in a close fourth quarter officials let more judgment calls go. Crews also throw the occasional flag for a foul that did not happen. College crews are less accurate on average than pro crews and spread much further apart, in accuracy, in how tightly they call a game and in home lean, because there are far more of them with less training and review; high school crews spread further still. The box score shows each game's flags, fouls let go, missed calls and bad flags.

---

## Overtime

Regular season games that are tied at the end of regulation end in a tie. Postseason games (bowls and playoffs) that are tied go to overtime.

Overtime is played in **8-minute periods**. Possession alternates to start each period, with the visiting team receiving first, and each period starts from the receiving team's own 20-yard line. Each team gets 4 fresh timeouts per period, and the 3-minute warning applies. Periods continue until the tie is broken, up to five. All scoring rules remain in effect.

---

## Weather

Games are played in the weather at the home venue, or at the neutral site, for that place and time of year. Each quarter has its own conditions: the temperature, rain, snow or sleet and how hard it is falling, the wind's speed and direction, and the humidity. Conditions carry over from one quarter to the next, so rain can start, ease off or stop, the wind can pick up, and the temperature can fall as the game goes on.

**The field.** Rain soaks the field, and it stays wet after the rain stops. Grass turns to mud and holds water longer than turf, which drains. Snow builds up on the field and melts off when it warms above freezing. A wet field below 28°F freezes.

**Ends and the wind.** The home team attacks the north end in the first and third quarters and in odd overtime periods; the teams switch ends every quarter. A wind at the kicker's back adds range to snap kicks and field goals and length to punts. A headwind takes them away. A crosswind costs accuracy.

**What the conditions do.**

- **Rain, snow and sleet** make the ball harder to hold (fumbles, muffs, dropped laterals), cost kick accuracy and kick pass completions, and slow runners on a wet or snowy field. The harder it falls, the bigger the effect. Sleet is the worst of the three.
- **Cold** shortens kicks and makes the ball harder to hold below 35°F.
- **Heat and humidity** drain players faster and draw more fouls.
- **Altitude** carries kicks farther.
- **Domes** have no weather. A retractable roof closes for rain, snow, cold or extreme heat.

**Coaches.** Coaches see the conditions. They kick from longer with the wind and shorter into it, call fewer bombs into the wind or in the rain, and move to tighter formations as the ball and field get wetter. A weatherproof head coach's team loses less to the conditions, and a coach with a feel for the wind loses less kicking into it.

Weather affects Viperball more than most gridiron sports because kicking is so central to the offense. A rain game blunts a team's kicking advantage and turns the contest into a ground and lateral battle. Snow and sleet games are full of fumbles, and the bell becomes a bigger scoring channel. A strong wind makes the quarters going into it a grind.

---

## Game Day

Talent decides most games, but no team plays the same way every week.

### Form

Every team brings a form for the day, rolled once before kickoff, and a hot or cold spell in each half on top of it. Form lifts or drags everything a team does together: its runs, its kicks and its defense. Teams with a real star run hot more often than teams without one. A flat day can make a mismatch close, and a hot day can turn a close matchup into a rout.

### Work Rate and Fatigue

Every player on the field spends energy on every snap, the way players do in Australian rules, Gaelic football and rugby. Linemen work hardest, Keepers and Zerobacks least. A player on the sideline gets energy back, and halftime gives back the most. A short timeout or a change of possession gives back very little.

Two ratings decide how a player handles the load:

- **Stamina** sets how fast she tires and how fast she recovers on the sideline.
- **Work rate** sets how much tiredness costs her and how long a coach can leave her on. A high work rate player keeps playing well when tired and stays in longer; a low work rate player fades early.

Tiredness costs a player a little on every play, and the cost grows sharply below 40 energy. Part of how tired a player finishes a game carries into the next week, and players with more stamina recover more of it. A team that leans on the same starters every week starts later games tired.

### Rotations

Substitution is unlimited and allowed at any time, including during live play, so coaches change players the way lacrosse teams do:

- **Midfield lines.** The Viper and four flankers (a Halfback, a Wingback, a Slotback and the best remaining flanker) play together as one two way line, on offense and defense. Each team carries three lines and changes them as a unit. The top line takes the longest shifts, and the second and third lines take shorter ones. When the top line is rested it goes back out; otherwise the coach rolls to the next line in order.
- **Defense from the line.** On defense, the line's four best tacklers play defensive back. A defensive specialist, the best tackler on the other lines, can come on for one of them while she is fresh.
- **Anchors.** The Zeroback and the two Keepers stay on almost all game.
- **The offensive line** is a set five that rarely changes.
- **The defensive line** rotates heavily, one player at a time.
- **Cover.** When a team runs out of fresh defensive linemen, a spare offensive lineman fills in; a bench midfielder can fill in at Keeper. A player covering another group plays at 90% of her rating.

A tired player or line comes off only if a fresh replacement would play about as well as the tired one can right now, so deep teams rotate more and thin teams ride their starters. Coaches ride starters longer in a close fourth quarter, and every mark depends on the players' work rate, so the whole team never changes at once.

The team roster and My Team pages show each midfielder's line (1, 2 or 3) for the next game, with a DS badge on the defensive specialist. The box score shows each team's line changes and how often it was caught changing, and the play by play marks each fast break.

**Changing on the fly.** Every down ends in a dead ball, so most changes happen between plays with no risk. The risk comes when the ball turns over during live play: a fumble, an intercepted lateral or kick pass, a muffed or blocked kick, or a returned missed snap kick. The team that lost the ball can rush its defensive specialist on, or change a tired line, while play is live. If it does, it can be caught short, and the other side gets a fast break on the next play. A coach can also wait one play and change safely at the next dead ball.

### Home Field and Travel

There is no automatic home field bonus. The home team's edge comes from the visitors' travel: an away team starts with less energy the farther it travelled, from nothing for a same-state trip to the most for a cross-country one. Officiating crews can also lean slightly toward the home side on close calls.

---

## Coaching Staffs and Team Installation

Every coordinator has a lasting tactical signature, such as Vertical Attack, Territory Control or Run to Kick for an offensive coordinator, and she takes it with her when she changes jobs. The head coach decides how much room the coordinator gets. Signatures shift which legal plays get called (formation, play type, kick pass type and featured player) by at most 20% either way, and never make an illegal play possible.

A program also has its own installation: what its players have actually learned.

- **Familiarity.** A team executes its coordinator's signature only as well as it knows her system. A staff in place when tracking starts begins at 0.75. A new coordinator from outside starts at 0.30. Familiarity rises a little each game and 0.20 each season together, up to full.
- **Coaching trees.** A new coordinator who worked under the current head coach, or under the same head coach as the coordinator she replaces, starts 0.25 higher. One who reads the book the same way as her predecessor starts 0.20 higher, up to 0.85 in all. A coach promoted from the same staff keeps at least 0.70.
- **Old habits.** When a coordinator leaves, a trace of her tendencies stays with the program and fades over the next season or two.
- **Base book.** Switching offensive or defensive books resets the team's familiarity with the book to 0.35, which trims how much of the coordinator's signature shows until it is learned.
- **Opening scripts.** Many play callers write an ordered script of three to six opening calls before a game: an inside run, a perimeter run, a quick kick pass, Viper motion, a draw and a deep kick pass, using only calls the offense runs. The script plays out over the offense's first snaps of the first half. A call is held, not dropped, when short yardage, a late down, the red zone, a kick or the clock takes priority. The caller notes the front the defense showed on each scripted call. When the script is done, the call that gained the most against a front, at least five yards, becomes the first call of a later first half drive when the defense shows that front again. Some callers do not script.
- **Play calling during a game.** At halftime a struggling offense, down nine or more or behind with fewer than fifteen points, can change callers. A head coach who delegated the offense can take it over if she is ready to call it and does not like to delegate; a head coach who kept the calls can hand them to her coordinator. A coordinator who has been a head coach keeps her calls. Between series, the coach who is not calling the offense suggests the play family that has gained the most this game when it stands out by a yard and a half, and an adaptable caller is more likely to take it. A taken suggestion is the first call of the next drive.
- **Packages.** Each coordinator installs up to two packages from the playbook catalog (`data/playbooks`) that fit her preferences, the team's book and its roster, up to four per side. A package nudges play calls toward its formations and plays only in its own situations, such as Heavy Push in short yardage, and only as much as the team knows it. Packages act in eligible situations; defensive commitments and offensive package calls now execute in the engine. Rare-package effectiveness and adoption remain research questions.
- **Defense.** Defensive installation controls eligible pre-snap commitments and roster-specific execution. Called rushers and actual rushers are tracked separately.

Each offseason, CPU programs review their staffs, fire and hire through the coaching portal, and every coach ages and develops. The human program controls senior staff decisions, with automatic retirement replacements and newly funded position assignments. Installations are saved with the dynasty, and the team page shows each team's familiarity, any fading habits and its installed packages.

**Career and teaching continuity.** Programs cover six position groups through dedicated coaches or coordinators: Zerobacks, Backs & Vipers, Offensive Line, Defensive Line, Keepers & Coverage, and Kicking & Returns. Prestige funds two, four or six dedicated assignments in addition to the four core staff jobs. Coaches can pursue lifelong specialization, move between disciplines when qualified, or advance through the market. Seasonal adaptation and mentorship are bounded; recruiting accounts for school fit and technical instruction. Retirement and delayed alumni entry allow staff turnover without requiring every coach to become a head coach. See [COACHING_SPEC.md](COACHING_SPEC.md) for current mechanisms and calibration limits.

**Defensive schools.** Each of the ten defenses has a strength that shows up in specific outcomes and a weakness something else can beat.

| Defense | Strength | Weakness |
|---|---|---|
| Fortress | Stops inside runs and forces 5th and 6th downs | Kick passes and laterals get outside it |
| Lockdown | Shuts down kick passes | Power runs work against its light box |
| Swarm | Contains lateral chains and intercepts them | Kick passes find the seams |
| Predator | Hunts turnovers: more interceptions and forced fumbles | Gives up big plays when the gamble fails |
| Drift | Bends, then tightens in scoring range and forces kicks | Gives up steady yards |
| Blitz Pack | Pressure, forced fumbles and kick rush | Counters and draws |
| Chaos | Disguise, some interceptions and kick rush | Gets carved up once the offense adjusts |
| Shadow | Spies the Viper | Power runs |
| Keeper Hunt | Rushes every kick, with more blocks and rushed 6th down kicks | Ordinary everywhere else, and gives up short yardage conversions |
| Rotation | Stays fresh against tempo and long drives | A little softer every snap |

A missed snap kick on downs 1 to 5 keeps the ball, so pressuring a kick mostly hands the offense another down. Keeper Hunt does its real damage on 6th down and with blocks.

**Weekly game plans.** Before every game, the defensive staff leans part of the way toward the scheme that best counters the opponent's offense: Fortress against the run offenses, Lockdown against the kick pass offenses, Predator against the lateral offenses, Shadow against Ghost and Mismatch, and Drift against East Coast. The defense keeps its own name and signature; only its numbers move. An adaptable head coach moves up to 60% of the way, a stubborn one barely moves, and a coach of average adaptability and stubbornness moves 35%.

**Coach fingerprints.** Two coaches with the same offense still call different games. Each head coach has six fingerprint traits:

- touchdown finish: chase the 9 rather than take the 5
- late down aggression
- run lean
- kick pass lean
- lateral lean
- turnover caution

They move the offense's kicking, go-for-it and turnover settings and its play mix. The coach page shows the fingerprint measured from the season's games: run, kick pass and lateral share, the share of points from touchdowns, how often the team goes for it on 5th and 6th down past midfield, how often it kicks when in range on 4th to 6th down, plays per game, and the defense its game plans lean toward.

**Program count.** A dynasty season needs an even number of programs. If the count is odd when a season starts, Coast Guard is retired, or Merchant Marine if Coast Guard is the human's program. Retiring a different program beforehand keeps the count even and skips this.

## Roster and Substitution Rules

### Active Roster

Teams maintain a **36-player active game-day roster**. All active players are eligible to play on any down.

### Substitution

- Unlimited substitutions are permitted
- Substitutions may happen at any time, during dead balls or on the fly during live play
- Players change through their team's substitution zone at midfield on their own sideline
- A player exiting the field must fully leave the playing surface before her replacement enters
- Violation: **Illegal Substitution** (5 yards)

### Injury Protocol

- A player removed due to injury may not return for a minimum of one play
- If an injury occurs during the final two minutes of a half, the injured player's team is charged a timeout
- Players removed under concussion protocol may not return to the same game

---

## Glossary

**Bell** — 0.5-point score awarded for recovering a loose ball (fumble, muff, bouncing kick). Play continues live after recovery.

**Boot Raid** — An offensive scheme built around kick passing and snap kicks. The Viperball equivalent of the Air Raid.

**Chain** — A sequence of two or more consecutive laterals on a single play. Also called a "lateral chain."

**Chain Gang** — An offensive scheme that maximizes lateral chains on every play. High-variance, high-entertainment football.

**Bonus Possession** — An extra drive, from the team's own 20-yard line, awarded to a team after it intercepts a kick pass or lateral. See [Interceptions](#interceptions).

**Delta Yards** — The restart rule after a score: the receiving team starts at its own 20, minus its lead or plus its deficit in yards. Leading teams start deeper; trailing teams start closer.

**Diving Wing** — A flanker specializing in kick-blocking. Times the kicker's release and dives at the ball.

**DK** — Abbreviation for drop kick. See Snap Kick.

**Down** — One play. Viperball uses six downs per possession series.

**Flanker** — A skill position player (Halfback, Wingback, or Slotback) who lines up on the perimeter or in the backfield.

**Ghost Formation** — An offensive scheme using the Viper's pre-snap motion to create confusion. Misdirection-heavy.

**Ground Control** — The touchdown first offense. It runs the ball, uses short kick passes to keep the defense honest, goes for it on short 5th and 6th downs, and kicks only when a drive has truly stalled or the clock says take the points.

**Keeper** — The last line of defense; analogous to a safety. Also fields kicks and serves as a returner.

**Kick Pass (KP)** — A kicked ball intended for a teammate downfield. Viperball's aerial game.

**Lateral** — A backward or sideways pass to a teammate. Legal at any time during live play.

**Lateral Spread** — An offensive scheme that stretches the defense horizontally using 2–4 lateral chains per play.

**Pindown** — 1-point score awarded when a punt, missed snap kick, or missed field goal goes into the end zone and the receiving team does not return it out.

**PK** — Abbreviation for place kick. See Field Goal.

**Rouge Hunt** — A defense-first offensive scheme that punts early, pins deep, and scores through pindowns, bells, and safeties.

**Snap Kick** — A 5-point drop kick through the uprights during live play. Viperball's signature scoring play.

**Triple Threat** — An offensive scheme using single-wing misdirection with direct snaps to multiple players.

**Viper** — A versatile skill player who lines up in various positions and moves before the snap. Unique to Viperball.

**YAC** — Yards after catch. Distance gained by a receiver after catching a kick pass.

**Zeroback (ZB)** — The central offensive player who receives the snap. Simultaneously the primary ball carrier, kicker, and lateral chain initiator.
