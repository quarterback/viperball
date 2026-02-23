# Viperball

**A collegiate dynasty simulator for a sport that never existed — and plays like nothing you've seen.**

---

## Where This Started

It started with a Reddit thread.

Someone in r/CFB posted a hypothetical: *[What if the entire 1894 Yale team came back to life and played a modern college football team?](https://www.reddit.com/r/CFB/comments/1r4qgd3/what_if_the_entire_1894_yale_team_came_back_to/)* The discussion spiraled into something more interesting than the original question — if early football teams played under rules closer to their own era, no forward pass, heavier emphasis on kicking, no specialized roles, what would a *modern* version of that game actually look like?

That question is Viperball.

The sport assumes a timeline where the forward pass never took over. Where kicking stayed central. Where the game evolved around space, stamina, field position, and the lateral pass instead of the aerial game. The result isn't a historical recreation — it's a fully realized modern sport with its own rules, positions, scoring system, and strategic depth, played by 187 women's collegiate programs across 16 conferences.

---

## What Kind of Game Is This

Viperball is physically closer to rugby. Strategically closer to chess.

There is no forward pass. The ball moves through running plays, lateral chains (pitches between teammates), and kick passes — punting the ball to a teammate downfield as a designed offensive play. The field is 100 yards. Games run 40 minutes of live time across 4 quarters. Scores typically land between 45 and 75 points per team, and a 20-point lead is genuinely not safe.

The sport has six ways to score:

- **Touchdown** — 9 points. Carry or receive into the end zone.
- **Drop Kick (Snap Kick)** — 5 points. A live-play drop kick through the uprights. The NBA three-pointer of Viperball — high value, high skill, changes the game.
- **Place Kick** — 3 points. A traditional held field goal. The conservative option.
- **Safety** — 2 points. Defense scores when the offense is downed in their own end zone.
- **Pindown** — 1 point. A punt that lands in or through the opponent's end zone without being returned. Borrowed from the CFL rouge.
- **Bell** — ½ point. Defense recovers a fumble. Named for the sound it makes on the scoreboard.

That last one matters. In a game with 3-6 fumbles per side, Bells accumulate. They change the score. They change the math on every lateral chain. That's intentional.

---

## The Down System

Six downs to gain 20 yards.

More generous than American football's four-for-ten, but the distance requirement means first downs are earned. A 15-yard run that would be a first down anywhere else leaves a Viperball team still needing 5 more yards. Explosive plays — breakaway runs, completed kick passes, successful lateral chains — are genuinely exciting because the game makes them matter.

The extra downs also reshape the drama:

- First through third down are where teams can afford to gamble.
- Fourth down is not a crisis — two more chances remain.
- Fifth and sixth down are where the real decisions live: go for it, kick a field goal, attempt a drop kick, or punt?

Teams go for it on fourth down with a 1.6x aggression multiplier. Fifth is 1.5x. Sixth is 1.7x — desperation that the engine calls exactly what it is.

---

## The Sacrifice System

This is the sport's most distinctive structural mechanic. The rule that makes blowouts rare and comebacks common.

**There are no kickoffs.** After every score, possession alternates. The receiving team starts their drive — and where they start depends on the score differential.

The formula: start at your own 20-yard line, minus however many points you lead by.

- Tied game → start at the 20
- Leading by 7 → start at the 13
- Leading by 14 → start at the 6
- Leading by 20+ → start at the 1-yard line

**The team that is winning is punished with worse field position on every drive.**

A team up 21 points starts 99 yards from the end zone, one bad play from a safety (2 points for the opponent). Meanwhile, the trailing team starts their drives from the 40 or beyond. The comeback is baked into the sport's architecture.

Sacrifice yards is a tracked stat — total yards behind the 20 a team started across all their drives. High sacrifice yards means you were winning most of the game, and you paid for it.

---

## The Positions

Viperball rosters carry 36 players across five position groups, all unique to the sport.

**Zeroback** (3 per roster) — The primary ball-handler. Not a quarterback, because there's no passing. The Zeroback initiates plays, executes option reads, distributes laterals, and — for kicking specialists — attempts drop kicks and kick passes. The Kicking ZB archetype is the most valuable player type in the sport. A team with an elite Kicking ZB who can fire snap kicks from the Launch Pad (opponent's 40-45 yard line) runs an entirely different offense than everyone else.

**Viper** (3 per roster) — The sport's signature position. A hybrid offensive weapon with no equivalent anywhere else. The Viper lines up in multiple alignments — wide, slot, backfield, in motion — and can run, catch kick passes, take jet sweeps, and participate in lateral chains. An elite Viper changes how the defense plays every snap. Offensive identity often builds around the Viper's archetype.

**Flankers** (12 per roster — 4 Halfbacks, 4 Wingbacks, 4 Slotbacks) — The skill position group. Runners, lateral chain participants, and kick pass receivers. Halfbacks take the most carries. Wingbacks work the edge. Slotbacks are typically the best hands on the team. Flanker archetypes — Speed, Power, Elusive, Reliable — create different personalities for how a team gains yards and whether they break big plays or grind for consistent production.

**Keeper** (3 per roster) — A defensive specialist and return player. The last line of defense on special teams. Keepers field punts, return kicks, and have a unique mechanic: they can deflect drop kick and place kick attempts, giving the defense a live-ball action on opponent scoring attempts. A Return Keeper is an explosive returner who can take punts to the house. A Sure-Hands Keeper ensures you'll never muff a catch.

**Offensive Line** (8) and **Defensive Line** (7) — Block and rush, respectively. Line quality determines how much room ball carriers have to work with, how protected kickers are, and how much pressure the defense can generate.

---

## How the Ball Moves

Every play falls into one of these categories:

**Run plays** form the foundation of every offense. Seven run families — Dive Option, Power, Sweep Option, Speed Option, Counter, Draw, and Viper Jet — with different risk profiles, matchup advantages, and tendencies. Average gain is 3-7 yards. Variance is high.

**Lateral chains** are the most exciting and most dangerous play type. The ball carrier pitches sideways or backward to a teammate, who can run, pitch again, or score. Chains of 2-5 laterals are common. Every exchange carries fumble probability that increases with each additional link. A 4-lateral chain carries roughly a 25% total fumble risk. When it works, the offense might gain 30 yards and score. When it doesn't, the defense gets a Bell plus possession.

**Kick passes** are the aerial game. A player (usually the Zeroback) punts the ball to a teammate downfield as a designed play — not a desperation heave. Completion rates run from around 72% on short throws under 8 yards to about 28% on bombs of 20+ yards, with most kick passes targeting the short-to-medium range. On incompletion, the ball is dead and the down is used, but there's no change of possession. Kick passing is the most common play type in most offensive schemes — a typical team attempts 40-45 per game.

**Drop kicks** are 5-point scoring attempts from the kicker's current field position. A player drops the ball and kicks it on the bounce, through the uprights, in live play. Realistic up to about 55 yards for elite kickers. The strategic tension: why take 3 points when you can attempt 5?

**Territory kicks (punts)** pin the opponent deep. Less common in Viperball than traditional football because teams have 6 downs and rarely stall that badly — and field goals are preferred over punts when in range. The exception is the Rouge Hunt offensive style, which weaponizes punting to generate Pindowns and field position pressure.

---

## Offensive Styles

Nine offensive systems define how teams play. Each has a strategic identity, a preferred play selection, and genuine matchup dynamics against defensive schemes.

**Ground & Pound** — Power running, all 6 downs, methodical. The grind.

**Lateral Spread** — Horizontal offense built on 2-4 lateral chains per series. High variance, explosive ceiling, fumble risk is real.

**Boot Raid** — Kick pass heavy. Move the ball through the air, then fire snap kicks from the Launch Pad. Requires a Kicking ZB to maximize.

**Ball Control** — Conservative, mistake-free, clock-burning. Win 24-21 and go home.

**Ghost** — Built around the Viper. Pre-snap motion, misdirection, jet sweeps. The defense doesn't know who has the ball.

**Rouge Hunt** — Defense-first offense. Punts early, pins deep, scores Pindowns and forces safeties. The offense only needs to score occasionally because the defense generates points.

**Chain Gang** — Maximum laterals, maximum chaos. Nearly every play involves 4+ exchanges. The most entertaining style to watch. The most nerve-wracking to coach.

**Triple Threat** — Single-wing misdirection. Multiple players can receive the snap directly. Nobody knows who the ball carrier is.

**Balanced** — No strong tendency. Adapts to situation. The default for teams without a dominant archetype player.

---

## Defensive Schemes and Special Teams

Eight defensive schemes — Swarm, Blitz Pack, Shadow, Fortress, Predator, Drift, Chaos, Lockdown — each with explicit strengths and vulnerabilities that create rock-paper-scissors matchup dynamics with the offensive styles. Five special teams philosophies — Iron Curtain, Lightning Returns, Block Party, Chaos Unit, Aces — define return game identity and coverage philosophy.

Weather matters. Rain increases fumble rates and reduces kick accuracy. Snow and sleet make kicking nearly impossible and games chaotic. Heat drains stamina fast, favoring deep rosters. Heavy wind reshapes the entire kicking calculus.

---

## The League

187 teams. 16 conferences. A sport that spans HBCUs, women's colleges, military academies, and major universities.

The Collegiate Viperball League includes programs across every region: Big Pacific powers on the West Coast, the Moonshine League in Appalachian country, the Prairie Athletic Union on the Great Plains, the Yankee Fourteen in New England. The league's intentional diversity means a 2,000-student women's college can compete with a 40,000-student state university. Viperball's structure makes that possible.

Seasons run conference schedules plus non-conference games, culminating in a playoff with conference champion auto-bids and at-large selections based on Power Index — a 100-point composite of win percentage, strength of schedule, quality wins, conference strength, and point differential.

Dynasty mode spans multiple seasons. Recruiting classes arrive, players develop and graduate, coaches move between programs, and program history accumulates. Every offseason changes the landscape.

---

## The Simulation Engine

Viperball runs on a turn-based simulation engine designed to produce realistic game outcomes at scale — 200 games at a time, across a full 187-team league, calibrated to match statistical targets that make games feel authentic.

The engine targets these per-team-per-game ranges:

| Stat | Target Range |
|------|-------------|
| Touchdowns | 4–6 |
| Drop kick attempts | 8–12 |
| Drop kicks made | 3–5 |
| Place kick attempts | 3–5 |
| Kick pass attempts | 40–45 |
| Kick pass completion | 55–65% |
| Rush yards | 80–120 |
| Lateral chain plays | 15–25 |
| Fumbles | 2–5 |
| Punts | 0–3 |
| Final score | 40–75 points |

Behind the numbers are interconnected systems: the Halo Model (team prestige as the baseline for routine plays, individual player ratings activated at Critical Contest Points), player archetypes (Reliable, Explosive, Clutch), dynamic Composure mechanics, coaching staffs with personalities and development arcs, and a recruiting system that generates new players every offseason.

The engine also exports LLM-ready data — JSON and Markdown formats designed for generating game content, box scores, player narratives, and broadcast language using AI tools.

---

## The Vocabulary

A shorthand for talking about Viperball:

**Bell** — Half a point, scored when the defense recovers a fumble. "That's a Bell — defense gets the half-point and takes possession."

**Boot** — A kick pass. "She boots it 12 yards to the Slotback in stride."

**Chain** — A lateral chain. "Three-link chain — Halfback to Wingback to Viper — and she's in the end zone."

**Drop Kick / Snap Kick / DK** — A 5-point live-play drop kick. "DK from 41 yards — it's good. Five points."

**Launch Pad** — The opponent's 40-45 yard line. Drop kick range for elite kickers.

**Link** — One lateral exchange within a chain. "Four-link chain, dropped on the third link — Bell."

**Pindown** — One point for punting the ball into the end zone without a return. The CFL rouge, Viperball version.

**Sacrifice** — The field position penalty on the leading team. "They're up 17, so they start at the 3 — that's a heavy sacrifice."

**Viper Jet** — A jet sweep handoff to the Viper in motion. High variance, high upside.

**Zeroback** — The primary ball-handler. Named for lining up at zero depth behind the line.

---

## What a Game Looks Like

A typical Viperball game runs something like this:

Both teams score on their opening drives. The Sacrifice system immediately punishes the scoring team — they start their next possession at their own 10-yard line, 90 yards to go. Meanwhile the opponent, still down 9, starts from their own 25. The early score leader is already fighting through sand.

By the second quarter, the Kicking ZB on one side has fired two snap kicks from the Launch Pad. The other team answers with a lateral chain that goes four links before the Viper breaks into open field for a 28-yard touchdown. A fumble recovery mid-drive adds a Bell to the box score. The score is 36-29 and the game is 18 minutes old.

In the fourth quarter, the trailing team's Sacrifice bonus puts them in excellent field position. They score twice in eight minutes. The leading team, starting every drive at their own 3-yard line, barely survives one series without giving up a safety. The lead shrinks to 3.

The final play of the game is a 44-yard drop kick attempt, fourth down, trailing by 3. It's good or it isn't. Either way, the game was worth watching.

---

*Viperball simulation engine — active development, February 2026.*
*187 teams. 16 conferences. No forward passes.*
