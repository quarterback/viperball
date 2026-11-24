# Viperball Official Rulebook (v2.0)

This is the full rulebook. The README carries the same rules in shorter form, and the two
must agree. When the engine and this book disagree, the disagreement is a bug in one of
them. `tests/test_rules_doc.py` checks the numbers in this book against the engine.

## Contents

1. [Fundamentals](#1-fundamentals)
2. [Field](#2-field)
3. [Game Length and Clock](#3-game-length-and-clock)
4. [Downs and Possession](#4-downs-and-possession)
5. [Moving the Ball](#5-moving-the-ball)
6. [Scoring](#6-scoring)
7. [Restarts and Delta Yards](#7-restarts-and-delta-yards)
8. [Kicking](#8-kicking)
9. [Loose Balls, Turnovers and Bonus Possession](#9-loose-balls-turnovers-and-bonus-possession)
10. [Out of Bounds](#10-out-of-bounds)
11. [Players and Positions](#11-players-and-positions)
12. [Formations, Snap and Motion](#12-formations-snap-and-motion)
13. [Substitution and Rotations](#13-substitution-and-rotations)
14. [Tackling and Player Safety](#14-tackling-and-player-safety)
15. [Penalties](#15-penalties)
16. [Officials, Enforcement and Review](#16-officials-enforcement-and-review)
17. [Overtime](#17-overtime)
18. [Weather](#18-weather)
19. [Glossary](#19-glossary)
20. [Version History](#20-version-history)

---

## 1. Fundamentals

Viperball began as a thought experiment from a Reddit discussion about whether the 1894
Yale team could compete in modern football
([original thread](https://www.reddit.com/r/CFB/comments/1r4qgd3/what_if_the_entire_1894_yale_team_came_back_to/)).
It imagines a timeline where the forward pass never took over, kicking stayed central,
players kept playing both ways, and the game grew around space, stamina and field
position.

- Two teams of 11 players.
- No forward pass of any kind.
- The ball moves by running, lateral passing and kick passing.
- Points come from six channels: touchdowns, snap kicks, field goals, safeties, pindowns
  and bells.
- The ball is a CFL spec Canadian football: 12⅞ to 13⅛ inches around the short axis,
  27¾ to 28¼ inches around the long axis, 14 to 15 ounces, inflated to 12.5 to 13.5 psi.

---

## 2. Field

- 100 yards goal line to goal line, with 10 yard end zones (120 yards in all).
- 53⅓ yards wide.
- Yard lines every 5 yards, numbered every 10 from each goal line to midfield.
- Hash marks at standard NCAA spacing. A ball downed outside the hashes is spotted on the
  nearest hash.
- Goal posts at the back line of each end zone, standard college dimensions.
- No kickoff restraining lines; the game has no kickoff.

---

## 3. Game Length and Clock

### Quarters

- Four 10 minute quarters, a 40 minute game.
- Halftime between the 2nd and 3rd quarters.
- The away team receives to start the 3rd quarter.

### Running clock

The game clock runs between plays except:

- After a score, until the restart.
- Out of bounds, in the final 2 minutes of each half only.
- Timeouts.
- The 3 minute warning: the clock stops once in each half when it crosses 3:00.
- Penalty enforcement.
- Injuries. An injury in the final 2 minutes of a half costs the injured player's team a
  timeout.
- Official reviews.

### Timeouts

Each team has 4 timeouts per half. Unused timeouts do not carry over.

### Play clock

The offense has 40 seconds to snap. A team that fails gets a delay of game: 5 yards and the
down is replayed. A clock management minded staff snaps in time more often.

### Final play

If time expires during a live play, the play continues until the ball is dead. A half can
end on a defensive foul that would give the offense an untimed down.

### Coin toss

The visiting team calls the toss. The winner chooses to receive, kick or defer to the
second half. The loser picks the end to defend.

---

## 4. Downs and Possession

- A team has **six downs to gain 20 yards**. Gaining 20 yards earns a new set of six downs.
- If a team fails to gain 20 yards in six downs, the other team takes over at the spot of
  the ball with 1st and 20.
- A team may kick (snap kick, field goal or punt) on any down.

### When teams kick

A missed snap kick on downs 1 through 5 keeps the ball (see [Missed snap kicks](#missed-snap-kicks)),
so coaches follow a simple logic:

- **Downs 1 to 3:** advance the ball and chase the touchdown. In the last two minutes of a
  half, a team in range takes the shot on any down when the points matter.
- **4th down:** kick only when the drive has stalled, the first down is far away and the
  kicker is in range.
- **5th down:** the natural kicking down. A miss still leaves 6th down for a second try.
- **6th down:** the last chance. A missed snap kick is a turnover, so a team kicks, punts
  or goes for it. A trailing team never punts on 6th down.

A field goal is the answer when a drive stalls outside snap kick range. Near the goal line,
teams keep driving for the touchdown. Late in a game, a team does not take a kick that
cannot tie or win.

---

## 5. Moving the Ball

### Running

The ball carrier may run in any direction. Any player may carry the ball.

### Lateral passing

A player may throw, toss or hand the ball to a teammate who is **beside or behind** her.
There is no limit on laterals in a play. A lateral that travels forward, even slightly, is
an Illegal Forward Lateral: 5 yards and loss of down. A dropped lateral is a live ball and
either team may recover it.

### Kick passing

A kick pass is a ball kicked to a teammate downfield. It is Viperball's aerial game.

- A catch by the intended receiver keeps the play alive: she may run, lateral or kick again.
- A catch by a defender is an interception. Possession changes and the defender may return
  it.
- A kick pass that hits the ground is incomplete. The ball is dead, the offense keeps it and
  the down is used.
- One kick pass per play. A second is Illegal Double Kickpass (10 yards and loss of down).
- A kick pass that goes out of bounds is a foul on the offense (5 yards and loss of down).

---

## 6. Scoring

| Score | Points | How |
|---|---|---|
| Touchdown | 9 | Carrying the ball into, or catching it in, the opponent's end zone |
| Snap kick | 5 | Drop kicking the ball through the uprights during live play |
| Field goal | 3 | Place kicking the ball through the uprights from scrimmage |
| Safety | 2 | The ball carrier downed in her own end zone, or an offensive foul there |
| Pindown | 1 | A punt, missed snap kick or missed field goal goes into the end zone and is not returned out |
| Bell | 0.5 | Recovering a loose ball: a fumble, a muff, or a blocked or bouncing kick |

There are no conversion attempts after a touchdown.

### Pindown

The kicking team scores 1 point when a punt, missed snap kick or missed field goal goes
into the end zone and the receiving team cannot return it out. The receiving team then
starts at its own 25. A team that returns the ball out of its end zone starts where the
return ends and no point is scored. This is the same score as the rouge in Canadian
football.

### Bell

A team scores half a point the moment it recovers a loose ball, and play continues. A
defense that recovers a blocked kick and returns it for a touchdown scores 9.5.

---

## 7. Restarts and Delta Yards

There is no kickoff. After every score the team that did not score receives the ball.

- **Delta Yards.** The receiving team starts at its own 20, moved back one yard for every
  point it leads by and forward one yard for every point it trails by. A team down 14 starts
  at its own 34; a team up 10 starts at its own 10. A drive never starts behind the 1 or
  past the opponent's 20.
- **After a safety,** the team that conceded it restarts from its own 20.
- **After a pindown,** the receiving team starts at its own 25.
- **Opening and second half possessions** start at the receiving team's own 20.

---

## 8. Kicking

### Snap kick

A drop kick during live play: the kicker drops the ball, lets it bounce once and kicks it.
No holder and no stoppage. It is legal on any down from anywhere. It is reliable within
40 yards and plausible out to about 55.

#### Missed snap kicks

- On downs 1 to 5, a miss that stays in the field of play is a dead ball. The kicking team
  keeps the ball and the down advances.
- Misses from beyond about 50 yards may be fielded and returned by the defense as a live
  ball. The longer the kick, the more likely the return.
- On 6th down, a miss from any distance is a turnover at the spot of the kick.
- A miss into the end zone that is not returned out is a pindown.

### Field goal

A place kick from scrimmage with a holder. It carries farther than a snap kick: its
comfortable range runs about 15 yards beyond the kicker's snap kick range, and attempts are
possible out to about 71 yards. A missed field goal can be fielded and returned like a
missed snap kick.

### Punt

A territorial kick that gives up the ball. The punter kicks it before it touches the ground.
There is no fair catch; the kick catch interference fouls protect the returner. A muffed
punt is a live ball and the team that recovers it scores a bell.

### Blocked kicks

Any kick may be blocked before it clears the line.

- A defensive recovery is a bell, and the defense may return the ball.
- A kicking team recovery is dead and the down is used.

---

## 9. Loose Balls, Turnovers and Bonus Possession

### Fumbles

A fumbled ball is live and either team may recover it. The recovering team scores a bell
and takes possession. A fumble that goes out of bounds stays with the team that last had
it, at the spot it went out.

### Interceptions

A kick pass or lateral caught by a defender changes possession at once, and she may return
it. A return touchdown scores 9.

### Bonus possession

An interception earns the intercepting team a bonus possession. After it finishes the
drive that follows its interception, it gets the ball again from its own 20 before the
opponent's next possession.

- Any fumble or interception while a bonus is pending cancels it.
- An interception during a bonus drive does not earn another one.
- A pending bonus does not carry past halftime or the end of the game.

### Turnover on downs

See [Downs and Possession](#4-downs-and-possession).

---

## 10. Out of Bounds

- A ball carrier is out when any part of her body touches the sideline or beyond. The ball
  is spotted where she went out.
- A lateral or kick pass that goes out of bounds is dead at the sideline. A lateral out of
  bounds behind the line is spotted where it crossed the sideline.
- The clock stops on out of bounds only in the final 2 minutes of each half.

---

## 11. Players and Positions

Each side fields 11 players. A team carries a 36 player game day roster, and every active
player may play on any down.

### Offense

| Position | Count | Role |
|---|---|---|
| Offensive Line | 5 | Blocks and protects the kicker; may receive laterals and advance |
| Zeroback | 1 | Takes the snap; primary runner, kicker and lateral chain starter |
| Viper | 1 | Free alignment mismatch player |
| Flankers | 4 | A Halfback, a Wingback, a Slotback and the best remaining flanker |

### Defense

| Position | Count | Role |
|---|---|---|
| Defensive Line | 5 | Rushes the kicker and stops the run |
| Keeper | 2 | Deepest defenders; field missed kicks and return them |
| Defensive backs | 4 | The four best tacklers of the midfield line on the field |

### Two way play

The Viper and the four flankers play as one two way midfield line. On defense, the line's
four best tacklers play defensive back. See [Substitution and Rotations](#13-substitution-and-rotations).

---

## 12. Formations, Snap and Motion

- At least five offensive players on the line at the snap. The rest may line up anywhere
  behind it.
- The Viper may line up anywhere on the offensive side but must be set for one full second
  before the snap, unless she is the single player in legal motion. Breaking this is an
  Illegal Viper Alignment (5 yards).
- One player may be in motion at the snap, moving parallel to or away from the line.
- Any legally positioned player may take the snap; it is usually the Zeroback.
- Once the ball is snapped, every positional restriction is lifted. Any player may carry,
  kick, lateral or receive the ball.

---

## 13. Substitution and Rotations

Substitution is unlimited and allowed at any time, including during live play, through the
team's substitution zone at midfield. A player leaving must be fully off the field before
her replacement enters, or it is Illegal Substitution (5 yards).

- **Midfield lines.** Each team carries three lines of a Viper and four flankers and changes
  them as a unit. The top line takes the longest shifts.
- **Defensive specialist.** The best tackler on the other lines may come on for one of the
  defensive backs while she is fresh.
- **Anchors.** The Zeroback and the two Keepers stay on almost all game.
- **Offensive line.** A set five that rarely changes.
- **Defensive line.** Rotates heavily, one player at a time.
- **Cover.** A spare offensive lineman can cover the defensive line and a bench midfielder
  can cover Keeper, at 90% of her rating.
- **Changing on the fly.** A team that loses the ball during live play may change while the
  ball is live. If it is caught changing, the other side gets a fast break on the next play.

### Fatigue and work rate

Every player on the field spends energy each snap and recovers on the sideline, most at
halftime. Stamina sets how fast she tires and recovers. Work rate sets how much tiredness
costs her and how long a coach leaves her on. Part of a game's fatigue carries into the
next week.

### Injuries

- A player removed with an injury may not return for at least one play.
- A player removed under concussion protocol may not return to the same game.

---

## 14. Tackling and Player Safety

A ball carrier is down when any part of her body other than hands or feet touches the
ground while in a defender's grasp, or when her forward progress is stopped.

Tackling is rugby style wrap tackling. Targeting the head or neck, horse collar tackles,
clipping, chop blocks, late hits and wedge formations are fouls (see the penalty table).

A player who shows signs of a concussion is removed at once and may not return. Officials
and medical staff decide, regardless of the player's or coach's wishes.

Targeting, fighting and throwing a punch are 15 yard fouls. The game does not eject players.

---

## 15. Penalties

Penalties are enforced from the spot of the foul unless the table says otherwise.

- **Automatic first down** gives the offense a new set of downs whatever the distance.
- **Loss of down** uses the down as well as the yardage.
- Live ball fouls may be accepted or declined by the team fouled against.
- An accepted live ball foul by the offense wipes out the play, including any score and any
  change of possession on it.
- Post play fouls are enforced from the succeeding spot.
- Fair Catch Interference and Kick Catch Interference are fouls by the kicking team on
  punts.

The table below is the engine's full penalty catalog, grouped by the phase of play in which
each foul can be called. Some fouls appear in more than one phase.

<!-- PENALTY_TABLE -->

### Before the snap

| Foul | Yards | On | Notes |
|---|---|---|---|
| False Start | 5 | Offense |  |
| Offsides | 5 | Defense |  |
| Delay of Game | 5 | Offense |  |
| Delay of Game (Defense) | 5 | Defense |  |
| Illegal Formation | 5 | Offense |  |
| Encroachment | 5 | Defense |  |
| Too Many Men on Field | 5 | Either |  |
| Illegal Substitution | 5 | Either |  |
| Illegal Viper Alignment | 5 | Offense |  |
| Illegal Motion | 5 | Offense |  |
| Illegal Snap | 5 | Offense |  |
| Illegal Defensive Formation | 5 | Defense |  |
| Missing Viper Jersey | 5 | Offense |  |
| Illegal Shift | 5 | Offense |  |
| Disconcerting Signals | 5 | Defense |  |
| Player Out of Bounds at Snap | 5 | Either |  |
| Illegal Viper Substitution | 5 | Offense |  |
| Illegal Numbering | 5 | Offense |  |
| Illegal Formation (Numbering Exception) | 5 | Offense |  |

### During a run

| Foul | Yards | On | Notes |
|---|---|---|---|
| Holding | 10 | Offense |  |
| Illegal Block | 10 | Offense |  |
| Clipping | 15 | Offense |  |
| Chop Block | 15 | Offense |  |
| Defensive Holding | 5 | Defense | Automatic first down |
| Facemask | 15 | Defense | Automatic first down |
| Unnecessary Roughness | 15 | Either |  |
| Horse Collar | 15 | Defense | Automatic first down |
| Personal Foul | 15 | Either |  |
| Tripping | 10 | Either |  |
| Targeting | 15 | Either |  |
| Blindside Block | 15 | Offense |  |
| Illegal Use of Hands | 10 | Offense |  |
| Lowering the Helmet | 15 | Either |  |
| Illegal Block in Back | 10 | Offense |  |
| Blocking Below the Waist | 15 | Offense |  |
| Hurdling | 15 | Either |  |
| Hands to the Face | 15 | Either |  |
| Interlocked Interference | 5 | Offense |  |
| Illegal Contact Against Snapper | 15 | Defense | Automatic first down |
| Fouling Out of Play | 15 | Either |  |
| Too Many Men on Field | 5 | Either |  |
| Striking | 15 | Either |  |
| Piling On | 15 | Defense |  |
| Assisting the Runner | 5 | Offense |  |
| Roughing the Zeroback | 15 | Defense | Automatic first down |
| Illegal Participation | 5 | Either |  |

### During a lateral play

| Foul | Yards | On | Notes |
|---|---|---|---|
| Holding | 10 | Offense |  |
| Illegal Forward Lateral | 5 | Offense | Loss of down |
| Illegal Block in Back | 10 | Offense |  |
| Lateral Interference | 10 | Defense | Automatic first down |
| Illegal Contact | 5 | Defense | Automatic first down |
| Defensive Holding | 5 | Defense | Automatic first down |
| Facemask | 15 | Defense | Automatic first down |
| Clipping | 15 | Offense |  |
| Illegal Screen | 10 | Offense |  |
| Illegal Viper Contact | 10 | Defense | Automatic first down |
| Unnecessary Roughness | 15 | Either |  |
| Personal Foul | 15 | Either |  |
| Wedge Formation | 15 | Offense |  |
| Double Forward Lateral | 10 | Offense | Loss of down |
| Blindside Block | 15 | Offense |  |
| Targeting | 15 | Either |  |
| Illegal Viper Handoff | 10 | Offense |  |
| Lowering the Helmet | 15 | Either |  |
| Illegal Lateral Beyond Scrimmage | 5 | Offense |  |
| Concealing the Ball | 15 | Offense |  |
| Illegal Use of Hands | 10 | Offense |  |
| Blocking Below the Waist | 15 | Offense |  |
| Hurdling | 15 | Either |  |
| Interlocked Interference | 5 | Offense |  |
| Hands to the Face | 15 | Either |  |
| Horse Collar | 15 | Defense | Automatic first down |
| Tripping | 10 | Either |  |
| Illegal Lateral Formation | 10 | Offense |  |
| Contact Before Lateral Arrives | 10 | Defense | Automatic first down |
| Excessive Contact on Lateral Receiver | 15 | Defense | Automatic first down |
| Too Many Men on Field | 5 | Either |  |
| Illegal Participation | 5 | Either |  |
| Piling On | 15 | Defense |  |
| Striking | 15 | Either |  |

### During a kick pass

| Foul | Yards | On | Notes |
|---|---|---|---|
| Contact on Kickpass Receiver | 15 | Defense | Automatic first down |
| Roughing the Kickpasser | 15 | Defense | Automatic first down |
| Hit on Defenseless Kickpass Receiver | 15 | Defense | Automatic first down |
| Kickpass Interference | 15 | Defense | Automatic first down |
| Offensive Kickpass Interference | 10 | Offense |  |
| Illegal Kickpass Formation | 5 | Offense |  |
| Illegal Double Kickpass | 10 | Offense | Loss of down |
| Kickpass Out of Bounds | 5 | Offense | Loss of down |
| Shielding the Kickpass | 10 | Offense |  |
| Illegal Kickpass Touch | 5 | Offense |  |
| Holding | 10 | Offense |  |
| Defensive Holding | 5 | Defense | Automatic first down |
| Facemask | 15 | Defense | Automatic first down |
| Illegal Block in Back | 10 | Offense |  |
| Illegal Use of Hands | 10 | Offense |  |
| Blindside Block | 15 | Offense |  |
| Targeting | 15 | Either |  |
| Lowering the Helmet | 15 | Either |  |
| Unnecessary Roughness | 15 | Either |  |
| Personal Foul | 15 | Either |  |
| Horse Collar | 15 | Defense | Automatic first down |
| Illegal Viper Contact | 10 | Defense | Automatic first down |
| Too Many Men on Field | 5 | Either |  |
| Illegal Bat | 10 | Either |  |

### During a punt, snap kick or field goal

| Foul | Yards | On | Notes |
|---|---|---|---|
| Roughing the Kicker | 15 | Defense | Automatic first down |
| Running Into Kicker | 5 | Defense |  |
| Fair Catch Interference | 15 | Offense | Punts only |
| Kick Catch Interference | 15 | Offense | Punts only |
| Illegal Kick | 10 | Offense |  |
| Holding | 10 | Offense |  |
| Illegal Block in Back | 10 | Either |  |
| Illegal Wedge Formation | 15 | Offense |  |
| Leverage | 15 | Defense |  |
| Illegal Bat | 10 | Either |  |
| Targeting | 15 | Either |  |
| Offside on Kick | 5 | Offense |  |
| Illegal Touch | 5 | Offense |  |
| Illegal Free Kick Formation | 5 | Offense |  |
| Player Out of Bounds During Kick | 5 | Offense |  |
| Kicker Simulating Being Roughed | 15 | Offense |  |
| Clipping | 15 | Either |  |
| Defensive Holding | 5 | Defense | Automatic first down |
| Facemask | 15 | Defense | Automatic first down |
| Blindside Block | 15 | Offense |  |
| Too Many Men on Field | 5 | Either |  |
| Unnecessary Roughness | 15 | Either |  |
| Blocking Below the Waist | 15 | Offense |  |
| Free Kick Out of Bounds | 5 | Offense |  |

### After the play

| Foul | Yards | On | Notes |
|---|---|---|---|
| Taunting | 15 | Either |  |
| Unsportsmanlike Conduct | 15 | Either |  |
| Late Hit | 15 | Defense |  |
| Late Hit Out of Bounds | 15 | Defense |  |
| Excessive Celebration | 15 | Offense |  |
| Sideline Interference | 15 | Either |  |
| Throwing Punch | 15 | Either |  |
| Helmet-to-Helmet Contact | 15 | Either |  |
| Bench Area Violation | 15 | Either |  |
| Persons Illegally on Field | 15 | Either |  |
| Player Not Returning Ball | 15 | Either |  |
| Continued Play Without Helmet | 15 | Either |  |
| Provoking Ill Will | 15 | Either |  |
| Obscene Language | 15 | Either |  |
| Removal of Helmet | 15 | Either |  |
| Spiking the Ball | 15 | Either |  |
| Piling On | 15 | Defense |  |
| Fighting | 15 | Either |  |

<!-- /PENALTY_TABLE -->

---

## 16. Officials, Enforcement and Review

### Crew

| Official | Watches |
|---|---|
| Referee | Final authority on all calls |
| Umpire | The line of scrimmage |
| Head Linesman | The down markers and one sideline |
| Line Judge | The opposite sideline |
| Back Judge | Deep plays and kicks through the uprights |
| Side Judge | The Viper's alignment and contact on her |

The Side Judge is unique to Viperball because the Viper's pre snap freedom needs its own
official. Crews differ in accuracy and consistency, and some lean slightly toward the home
side on close calls.

### Calls, no calls and missed calls

Officials do not flag every foul. A foul that happens can be called, let go because it did not affect the play (holding away from the ball, a word after the whistle instead of a flag), or missed. Fouls in plain view, such as false starts and forward laterals, are almost always flagged; holding and coverage contact are flagged mostly when they affect the play. Crews differ in how tightly they call a game, a crew that leans toward the home side misses a few more home fouls on close calls, and late in a close fourth quarter officials let more judgment calls go. Crews also throw the occasional flag for a foul that did not happen. The box score shows each game's flags, fouls let go, missed calls and bad flags.

### Coach's challenge

Each team has 3 challenges per game. A coach may challenge the spot of the ball, a turnover
on downs, a fumble or interception ruling, a kick pass catch or a short touchdown.
Penalties cannot be challenged. Inside the 3 minute warning, plays are reviewed
automatically.

---

## 17. Overtime

- Regular season games tied after regulation end in a tie.
- Postseason games (bowls and playoffs) go to overtime.
- Each overtime period is 8 minutes. The visiting team receives first and possession
  alternates each period. Each period starts from the receiving team's own 20.
- Each team gets 4 fresh timeouts per period, and the 3 minute warning applies.
- Periods continue until the tie is broken, up to five.

---

## 18. Weather

Games are played outdoors in six weather categories:

| Weather | Effect |
|---|---|
| Clear | None |
| Rain | More fumbles and muffs; less kick accuracy |
| Snow | Much less kick accuracy; more fumbles; slower play |
| Sleet | Worst conditions; extreme fumble risk; kicking badly hurt |
| Extreme Heat | Faster fatigue; slightly more fumbles |
| Heavy Wind | Kick accuracy and punt distance hurt; unpredictable ball flight |

---

## 19. Glossary

**Bell:** half point score for recovering a loose ball. Play continues.

**Bonus possession:** an extra drive from the team's own 20 after it intercepts a kick
pass or lateral.

**Delta Yards:** the restart rule after a score. The receiving team starts at its own 20,
minus its lead or plus its deficit in yards.

**Drop kick (DK):** see snap kick.

**Flanker:** a Halfback, Wingback or Slotback, the skill players of the midfield line.

**Kick pass (KP):** a ball kicked to a teammate downfield.

**Keeper:** one of the two deepest defenders. Fields missed kicks and returns them.

**Lateral:** a backward or sideways pass, legal at any time in live play.

**Lateral chain:** two or more laterals in a row on one play.

**Midfield line:** the Viper and four flankers, who play offense and defense together.

**Pindown:** one point for a kick into the end zone that is not returned out.

**Place kick (PK):** see field goal.

**Snap kick:** a 5 point drop kick through the uprights during live play.

**Viper:** the free alignment skill player unique to Viperball.

**Zeroback (ZB):** the player who takes the snap; primary runner, kicker and lateral chain
starter.

---

## 20. Version History

### v2.0, November 24, 2026

Rewritten to match the engine and the README after the 2026 rules changes.

- Six downs to gain 20 yards (v1.1 said five).
- Four 10 minute quarters (v1.1 said 12 to 15 minutes).
- No kickoff: Delta Yards restarts after every score. The kickoff, touchback and onside
  rules are removed.
- Pindown (1 point) and bell (half a point) added to scoring.
- Snap kick legal on any down, with the missed snap kick rule.
- Kick pass, interception and bonus possession rules added.
- 3 minute warning replaces the 2 minute warning.
- Positions match the game: five line, Zeroback, Viper and four flankers on offense; five
  line, two Keepers and four defensive backs on defense.
- Midfield lines, live substitution, fatigue and work rate added.
- Penalty table taken from the engine catalog.
- Six officials, three challenges per game and the current overtime format.

### v1.1, February 15, 2026

Full sections for field, clock, formations, snap, penalties, officials, safety and
overtime.

### v1.0

Original rulebook.
