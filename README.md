# Viperball

**A collegiate dynasty simulator for a sport that never existed — and plays like nothing you've seen.**

---

## Where This Started

It started with a Reddit thread.

Someone in r/CFB posted a hypothetical: *[What if the entire 1894 Yale team came back to life and played a modern college football team?](https://www.reddit.com/r/CFB/comments/1r4qgd3/what_if_the_entire_1894_yale_team_came_back_to/)* The discussion spiraled into something more interesting than the original question — if early football teams played under rules closer to their own era, no forward pass, heavier emphasis on kicking, no specialized roles, what would a *modern* version of that game actually look like?

That question is Viperball.

**Viperball** is a gridiron football code designed for speed, tactical kicking, and lateral ball movement. It is the primary sport of the **Collegiate Viperball League (CVL)**, a 187-team women's collegiate athletic conference system across the United States.

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
19. [Roster and Substitution Rules](#roster-and-substitution-rules)
20. [Glossary](#glossary)

---

## Overview

Viperball is played between two teams of 11 players on a 100-yard field. The objective is to advance the ball into the opposing team's end zone or score through kicking. There is no forward pass. The ball is advanced by running, lateral passing (backward or sideways), and kick passing (a kicked ball to a teammate downfield). Kicking is both an offensive weapon and a scoring method — teams routinely score by drop-kicking the ball through the uprights during live play.

A typical CVL game produces scores in the 45–70 point range per team, with points coming from touchdowns, snap kicks, field goals, safeties, pindowns, and bells. The sport rewards versatile athletes who can run, kick, catch, and tackle — most players contribute on both sides of the ball.

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

A regulation game consists of **four 15-minute quarters** with a running game clock:

- **1st and 2nd quarters** make up the first half
- **Halftime** interval between the 2nd and 3rd quarters
- **3rd and 4th quarters** make up the second half

### The Clock

The game clock runs continuously with the following exceptions:

- **Scoring plays** — clock stops until the subsequent restart
- **Out of bounds** — clock stops (final 2 minutes of each half only)
- **Timeouts** — each team receives 3 per half
- **Penalties** — clock stops during enforcement
- **Injuries** — clock stops; team charged a timeout if injury occurs in final 2 minutes of a half
- **Official reviews** — clock stops

Play clock between snaps runs 25 seconds. Delay of game is a 5-yard penalty.

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

If a team fails to gain 20 yards in six downs, the opposing team takes possession at the spot of the ball. There is no automatic punt situation — teams may attempt to convert on 5th or 6th down, punt at any time, or attempt a kick for points.

---

## Movement of the Ball

There are three legal methods of advancing the ball in Viperball:

### 1. Running

The ball carrier may run in any direction. Standard running plays include dives, power runs, sweeps, counters, draws, and option plays. The Zeroback (see [Positions](#positions)) is the primary ball handler, but any player may carry the ball.

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
| **Pindown** | **1** | A single is awarded when the ball is kicked into the end zone by any legal means—other than a convert (successful or not) or a successful field goal—and the receiving team does not return (or kick) the ball out of its end zone (see [Pindown](#pindown)) |
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

A pindown is worth **1 point** and is awarded to the kicking team when the receiving team begins a possession inside its own 10-yard line. This occurs most commonly after punts that pin the opponent deep.

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

A typical CVL game might produce a final score like **63–49**. The winning team's points could break down as:

- 3 touchdowns (27 pts)
- 4 snap kicks (20 pts)
- 2 field goals (6 pts)
- 3 pindowns (3 pts)
- 1 safety (2 pts)
- 10 bells across the game (5 pts)

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

Many players contribute on both offense and defense. The Viper may play as a defensive back on the opposing team's possessions. Flankers frequently serve as kick coverage specialists. The 36-player roster ensures depth, but the best athletes on each team regularly play both ways.

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

A punt is a territorial kick used to surrender possession while pushing the opponent deep into their own territory. The punter drops the ball and kicks it before it hits the ground. Punts are the primary weapon for teams seeking **pindowns** — a punt that pins the opponent inside the 10-yard line scores 1 point.

A punt that enters the end zone without being fielded results in a **touchback** — the receiving team takes over at the 25-yard line.

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

A kick pass intercepted by a defender results in an immediate change of possession. The intercepting player may return the ball. An interception returned for a touchdown scores 9 points.

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

Viperball does not use traditional kickoffs. After every score, the non-scoring team receives the ball and begins its possession from a designated starting field position, typically between their own 20 and 35-yard line. The elimination of the kickoff removes the most dangerous collision play in gridiron sports while maintaining the flow of the game.

### Punt Returns

A player who catches a punt may return it upfield. Punt returns are among the most exciting plays in Viperball — a fast returner with open space can take a punt the distance for a 9-point touchdown. Muffed punts (drops) are live balls recoverable by either team, with the recovering team earning a bell.

### Kick Returns

Missed field goals and missed snap kicks that travel into the field of play may be fielded and returned by the defense. These returns follow the same rules as punt returns — the returner may advance the ball, lateral to teammates, or be tackled. Return touchdowns are worth 9 points.

---

## Penalties

Viperball enforces a comprehensive penalty system across five phases of play. Penalties are enforced as yardage from the spot of the foul unless otherwise noted.

### Pre-Snap Penalties

| Penalty | Yards | On |
|---|---|---|
| False Start | 5 | Offense |
| Offsides | 5 | Defense |
| Delay of Game | 5 | Offense |
| Illegal Formation | 5 | Offense |
| Encroachment | 5 | Defense |
| Too Many Men on Field | 5 | Either |
| Illegal Substitution | 5 | Either |
| Illegal Viper Alignment | 5 | Offense |

### During-Play Penalties (Run)

| Penalty | Yards | On | Notes |
|---|---|---|---|
| Holding | 10 | Offense | |
| Illegal Block | 10 | Offense | |
| Clipping | 15 | Offense | |
| Chop Block | 15 | Offense | |
| Defensive Holding | 5 | Defense | Automatic first down |
| Facemask | 15 | Defense | Automatic first down |
| Unnecessary Roughness | 15 | Either | |
| Horse Collar | 15 | Defense | Automatic first down |
| Personal Foul | 15 | Either | |
| Tripping | 10 | Either | |

### During-Play Penalties (Lateral)

| Penalty | Yards | On | Notes |
|---|---|---|---|
| Holding | 10 | Offense | |
| Illegal Forward Lateral | 5 | Offense | Loss of down |
| Illegal Block in Back | 10 | Offense | |
| Lateral Interference | 10 | Defense | Automatic first down |
| Illegal Contact | 5 | Defense | Automatic first down |
| Defensive Holding | 5 | Defense | Automatic first down |
| Facemask | 15 | Defense | Automatic first down |
| Clipping | 15 | Offense | |
| Illegal Screen | 10 | Offense | |
| Illegal Viper Contact | 10 | Defense | Automatic first down |
| Unnecessary Roughness | 15 | Either | |
| Personal Foul | 15 | Either | |

### During-Play Penalties (Kick)

| Penalty | Yards | On | Notes |
|---|---|---|---|
| Roughing the Kicker | 15 | Defense | Automatic first down |
| Running Into Kicker | 5 | Defense | |
| Fair Catch Interference | 15 | Defense | |
| Kick Catch Interference | 15 | Defense | |
| Illegal Kick | 10 | Offense | |
| Holding | 10 | Offense | |
| Illegal Block in Back | 10 | Either | |

### Post-Play Penalties

| Penalty | Yards | On |
|---|---|---|
| Taunting | 15 | Either |
| Unsportsmanlike Conduct | 15 | Either |
| Late Hit | 15 | Defense |
| Excessive Celebration | 15 | Offense |
| Sideline Interference | 15 | Either |

### Automatic First Down

Certain defensive penalties award the offense an automatic new set of downs regardless of the yardage gained. These are marked in the tables above.

### Loss of Down

The **Illegal Forward Lateral** is the only penalty that carries a loss of down. This harsh punishment reflects the fundamental rule of Viperball: the ball may never travel forward through the air from a player's hand.

---

## Officials

A standard CVL officiating crew consists of:

- **Referee** — Final authority on all calls
- **Umpire** — Watches the line of scrimmage
- **Head Linesman** — Manages the down markers and sideline
- **Line Judge** — Opposite sideline, watches for out-of-bounds
- **Back Judge** — Deep field, rules on kicks through the uprights and deep plays
- **Side Judge** — Watches the Viper position for alignment violations and illegal contact

The sixth official (Side Judge) is unique to Viperball and exists because the Viper position's pre-snap freedom creates officiating challenges not found in other gridiron sports.

---

## Overtime

If the score is tied at the end of regulation, the game proceeds to overtime.

Each team receives one possession starting from the opponent's 35-yard line. The team that scores more points on its possession wins. If both teams score the same number of points, additional overtime periods are played until the tie is broken.

There are no timeouts in overtime. The play clock runs normally. All scoring rules remain in effect.

---

## Weather

CVL games are played outdoors in all weather conditions. The six recognized weather categories are:

- **Clear** — No impact on play
- **Rain** — Wet ball increases fumble and muff rates; reduced kick accuracy
- **Snow** — Cold conditions significantly reduce kick accuracy; moderate fumble increase; slower play
- **Sleet** — Worst conditions; extreme fumble risk, severely reduced kicking accuracy
- **Extreme Heat** — Rapid fatigue accumulation; slight fumble increase from slippery hands
- **Heavy Wind** — Significant impact on kick accuracy and punt distance; gusts create unpredictable ball flight

Weather affects Viperball more dramatically than most gridiron sports because kicking is so central to the offense. A rain game neutralizes a team's kicking advantage and turns the contest into a ground-and-lateral battle. Snow and sleet games produce chaotic, fumble-heavy affairs where the bell becomes a significant scoring channel. Wind games penalize snap kick-dependent offenses and reward teams that can grind on the ground.

---

## Roster and Substitution Rules

### Active Roster

Teams maintain a **36-player active game-day roster**. All active players are eligible to play on any down.

### Substitution

- Unlimited substitutions are permitted
- Substitutions may only occur during dead-ball stoppages (after the play is ruled dead and before the next snap)
- On-the-fly substitutions during live play are prohibited
- A player exiting the field must fully leave the playing surface before their replacement enters
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

**Diving Wing** — A flanker specializing in kick-blocking. Times the kicker's release and dives at the ball.

**DK** — Abbreviation for drop kick. See Snap Kick.

**Down** — One play. Viperball uses six downs per possession series.

**Flanker** — A skill position player (Halfback, Wingback, or Slotback) who lines up on the perimeter or in the backfield.

**Ghost Formation** — An offensive scheme using the Viper's pre-snap motion to create confusion. Misdirection-heavy.

**Ground & Pound** — An offensive scheme built around power running, using all six downs to grind 20 yards.

**Keeper** — The last line of defense; analogous to a safety. Also fields kicks and serves as a returner.

**Kick Pass (KP)** — A kicked ball intended for a teammate downfield. Viperball's aerial game.

**Lateral** — A backward or sideways pass to a teammate. Legal at any time during live play.

**Lateral Spread** — An offensive scheme that stretches the defense horizontally using 2–4 lateral chains per play.

**Pindown** — 1-point score awarded when the opponent begins a possession inside their own 10-yard line.

**PK** — Abbreviation for place kick. See Field Goal.

**Rouge Hunt** — A defense-first offensive scheme that punts early, pins deep, and scores through pindowns, bells, and safeties.

**Snap Kick** — A 5-point drop kick through the uprights during live play. Viperball's signature scoring play.

**Triple Threat** — An offensive scheme using single-wing misdirection with direct snaps to multiple players.

**Viper** — A versatile skill player who lines up in various positions and moves before the snap. Unique to Viperball.

**YAC** — Yards after catch. Distance gained by a receiver after catching a kick pass.

**Zeroback (ZB)** — The central offensive player who receives the snap. Simultaneously the primary ball carrier, kicker, and lateral chain initiator.
