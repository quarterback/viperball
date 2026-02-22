# Viperball: Rules, Mechanics, and Narrative Primer

**A complete reference for understanding the sport of Viperball**
**For use by narrative engines, writers, commentators, and world-builders**

---

## What Is Viperball?

Viperball is a women's college football sport played by 187 teams across 16 conferences in the Collegiate Viperball League (CVL). It is not a variant of any existing sport. It synthesizes elements from American football, Canadian football, rugby, Australian rules, and arena football into something original.

The core identity: **there is no forward pass.** The ball moves downfield through running, lateral pitches between teammates, and kick passes — punting the ball to a teammate downfield. This creates a game that is physically closer to rugby but strategically closer to chess, where field position, risk tolerance, and scheme matchups determine outcomes.

Games are high-scoring (typically 45-75 points per team), fast-paced, and volatile. A 20-point lead is not safe. The sport's built-in comeback mechanics — the Sacrifice system — ensure that dominant teams face increasing difficulty holding their advantage.

---

## The Field and Game Structure

**The field** is 100 yards long with end zones at each end, identical to an American football field.

**Game length:** 4 quarters of 15 minutes each (60 minutes total). Each play consumes 11-36 seconds of game clock. A typical game produces roughly 80-85 plays per team.

**There are no kickoffs.** Possession alternates after every scoring play and at the start of each half. Starting field position is determined by the Sacrifice system (explained below).

**Halftime** occurs between the 2nd and 3rd quarters. Coaching adjustments take effect at halftime — trailing teams may receive strategic boosts based on their coaching staff's attributes.

---

## The Down System

Teams have **6 downs to gain 20 yards** for a first down. This is the sport's fundamental rhythm — more generous than American football's 4-for-10, but demanding enough that failed drives are common.

The extra downs and longer distance create a different strategic calculus:
- Teams can afford to take risks on early downs (1st-3rd) without feeling desperate
- 4th down is not a crisis — teams still have two more chances
- 5th and 6th down decisions are where the real drama lives: go for it, kick a field goal, attempt a drop kick, or punt?
- Late-down aggression is high. Teams go for it on 4th down with a 1.6x aggression multiplier, 5th down at 1.5x, and 6th down at 1.7x (desperation factor)

**The 20-yard requirement** means first downs are harder to earn. A 15-yard run that would be a first down in American football leaves a Viperball team still needing 5 more yards. This makes explosive plays — breakaway runs, completed kick passes, successful lateral chains — genuinely exciting and momentum-shifting.

---

## Scoring

Viperball has six ways to score. From most to least valuable:

### Touchdown — 9 points
Carrying or receiving the ball into the opponent's end zone. This is the primary scoring play. There are no conversion attempts (no extra points or two-point conversions). A touchdown is simply 9 points, clean.

Touchdowns can come from:
- Running plays that break through for long gains
- Lateral chains where the final receiver reaches the end zone
- Kick pass completions where the receiver scores on the catch or on yards after catch
- Fumble recoveries returned to the end zone
- Punt return touchdowns
- Blocked kick return touchdowns

A typical team scores 4-6 touchdowns per game. Elite offenses can reach 7-8.

### Drop Kick (Snap Kick) — 5 points
The sport's premium scoring play — its equivalent of the NBA three-pointer. A player drop kicks the ball through the uprights during live play. Unlike a place kick, the ball is not held by a teammate; the kicker drops it and kicks it on the bounce.

Drop kicks are attempted from the offense's current field position plus 17 yards (the distance to the uprights behind the end zone). A team at the opponent's 30-yard line is attempting a 47-yard drop kick.

**Range:** Realistic up to about 55 yards. Elite kicking specialists (skill 85+) make 97% from 20 yards or closer, 76% from 40 yards, and 52% from 45-54 yards. Beyond 55 yards, even specialists hit only 38%.

**Strategic philosophy:** Drop kicks are strongly preferred over place kicks at close range. From 25 yards or closer, the logic is simple: why take 3 points when you can get 5? Teams with kicking specialists attempt drop kicks aggressively, especially on 5th and 6th down when field goal range is available.

A typical team attempts 8-12 drop kicks per game and makes 3.5-5. Kicking specialist teams may hit 5-6+ per game.

### Place Kick (Field Goal) — 3 points
A traditional held field goal kick. More accurate than a drop kick but worth 2 fewer points — the conservative option.

**Range:** Maximum 71 yards. Success rates: 97% from 25 yards or closer, 84% from 35-44 yards, 72% from 45-54 yards, declining to roughly 12-25% beyond 65 yards.

**Strategic role:** Teams attempt place kicks when they're outside comfortable drop kick range but still in field goal territory. A team at the opponent's 45 might choose a 62-yard place kick (3 points, decent odds) over a 62-yard drop kick (5 points, low odds). Teams also use place kicks when a drop kick attempt has already failed or been blocked.

A typical team attempts 3-5 place kicks per game.

### Safety — 2 points
When the offense is tackled, fumbles, or commits a penalty in their own end zone, the defense scores 2 points. After a safety, the scoring team receives possession.

Safeties are rare but dramatic. They most commonly occur when a team starts a drive deep in their own territory (which happens more often due to the Sacrifice system — see below) and a running play goes backward.

### Pindown — 1 point
Viperball's version of the CFL rouge. When a punt lands in or through the opponent's end zone and the receiving team fails to return it out, the kicking team scores 1 point. The receiving team then gets possession at their own 25-yard line.

Pindown probability depends on punt distance, the receiving team's return ability, and their defensive scheme's pindown defense rating. Some offensive styles — particularly Rouge Hunt — are specifically designed to generate pindowns.

Pindowns are a small but meaningful scoring mechanic. They reward good punting, create field position pressure, and can be the margin in close games.

### Bell — ½ point
When the defense recovers a fumble, they score half a point. This is called a Bell — a small reward for forcing and recovering a turnover beyond just getting possession.

Bells are unique to Viperball. They create situations where a fumble recovery isn't just a momentum play — it literally changes the score. Over the course of a game with 3-6 fumbles, Bells can add 1-3 points to a team's total. In a close game, that matters.

Bells can come from:
- Run play fumbles recovered by the defense
- Lateral chain fumbles (the most common source — laterals are risky)
- Kick pass catch fumbles
- Muffed punt recoveries by the kicking team

---

## The Sacrifice System

This is Viperball's most distinctive structural mechanic and the key to understanding game flow.

**There are no kickoffs.** After every score, possession alternates. But instead of kicking the ball to the other team, the receiving team simply starts a drive — and where they start depends on the score.

**The rule:** The receiving team starts at their own 20-yard line, minus however many points they lead by, minimum the 1-yard line.

- **Tied game:** Start at the 20.
- **Leading by 7:** Start at the 13.
- **Leading by 14:** Start at the 6.
- **Leading by 20+:** Start at the 1-yard line.
- **Trailing by 10:** Start at the 30.
- **Trailing by 20:** Start at the 40.

This means **the team that is winning is punished with worse field position on every drive.** A team up by 21 points starts every drive at their own 1-yard line — 99 yards from the end zone, with the constant threat of a safety (2 points for the opponent) on any negative play.

The Sacrifice system makes blowouts rare and comebacks common. It also creates a fascinating strategic question: is it better to score quickly and build a lead (accepting worse field position) or to control the clock and score slowly (maintaining better field position)?

**Sacrifice yards** are tracked as a stat — how many total yards behind the 20 a team started across all their drives. A team with high sacrifice yards was leading for most of the game and paid for it with field position.

---

## Positions

Viperball rosters have 36 players. The position groups are unique to the sport.

### Zeroback (ZB) — 3 per roster
The closest equivalent to a quarterback, but not a passer. The Zeroback is the primary ball-handler who initiates plays, executes option reads, distributes laterals, and — for kicking specialists — attempts drop kicks and kick passes.

**Archetypes:**
- **Kicking ZB** — The most valuable archetype. A Zeroback who can drop kick and kick pass at elite levels. Changes the entire offensive calculus because they can score 5 points from the Launch Pad (opponent's 40-45 yard line). Teams with a Kicking ZB run Boot Raid or balanced offenses that funnel opportunities to their kicker.
- **Running ZB** — A power runner who takes direct carries. Functions like a rushing quarterback — tough to bring down, piles up yards between the tackles.
- **Distributor ZB** — An option-read specialist who gets the ball to playmakers. Excels at reading the defense and pitching to the right lateral target. Low personal stats, high team efficiency.
- **Dual-Threat ZB** — Combines running and kicking ability. Not elite at either, but the defense can't key on one skill. Creates mismatches through versatility.

### Viper (VP) — 3 per roster
The sport's signature position — a hybrid offensive weapon with no real equivalent in other sports. The Viper lines up in various alignments (wide, slot, backfield, motion) and can run, catch kick passes, take jet sweeps, and participate in lateral chains.

The **Viper Alignment System** places the Viper in different positions pre-snap, and the defense must account for their versatility. An elite Viper changes how the defense plays every snap.

**Archetypes:**
- **Receiving Viper** — The primary kick pass target. Lines up wide, runs routes, catches punted balls in stride. High hands, high speed.
- **Power Viper** — A physical runner who takes Viper Jet handoffs and trucks through contact. More like a fullback than a wide receiver.
- **Decoy Viper** — Draws defensive attention through motion and fakes. May not touch the ball often, but their presence on the field creates opportunities for everyone else.
- **Hybrid Viper** — Can do everything but nothing at an elite level. Keeps the defense guessing because any play could be designed for them.

### Flankers — 12 per roster (4 Halfbacks, 4 Wingbacks, 4 Slotbacks)
The skill position group. Flankers are the runners, lateral chain participants, and kick pass receivers who form the core of every offensive play.

**Halfback (HB):** The primary ball carrier. Gets the most rushing touches, runs between the tackles, takes dive and power handoffs. The workhorse.

**Wingback (WB):** An edge runner and lateral chain participant. Takes sweeps, speed options, and counters. More of a perimeter threat than the Halfback.

**Slotback (SB):** Lines up in the slot — between the line and the edge. Versatile enough to run inside or outside. Often the best hands on the team for kick pass receptions.

**Flanker Archetypes (shared across HB/WB/SB):**
- **Speed Flanker** — Breakaway threat. Lower yards per carry average but higher chance of explosive runs (20+ yards).
- **Power Flanker** — Gains yards after contact. Reliable 4-6 yards per carry. Hard to bring down on lateral chain receptions.
- **Elusive Flanker** — Makes defenders miss in the open field. Best in lateral chains and counter plays where they receive the ball in space.
- **Reliable Flanker** — Low fumble rate, consistent production. The safe option on critical downs.

### Keeper (KP) — 3 per roster
A defensive specialist and return player. Keepers are the last line of defense on special teams and play a role similar to a safety or punt returner.

**Archetypes:**
- **Return Keeper** — An explosive returner who can take punt returns to the house. Higher muff risk because they play aggressively.
- **Sure-Hands Keeper** — Rarely muffs punts. Won't break many long returns, but secures the football.
- **Tackle Keeper** — A hard hitter who excels in coverage. Makes tackles on special teams and in the open field.

Keepers also have a unique defensive mechanic: they can deflect drop kick and place kick attempts. A Keeper with high speed and tackling can slightly reduce the opponent's kicking accuracy.

### Offensive Line — 8 per roster
Block for run plays and kick attempts. Their collective talent determines the offensive line's push, which affects run yardage and kicker protection time.

### Defensive Line — 7 per roster
Rush the ball carrier, pressure the kicker, and fill gaps. Defensive linemen generate tackles, tackles for loss (TFL), sacks, and hurries.

---

## Play Types

Every play in Viperball falls into one of these categories:

### Run Plays
The foundation of every offense. Running plays gain 3-7 yards on average with high variance. There are seven run families:

- **Dive Option** — Up the middle. The Zeroback reads the defense and either keeps or hands off. Moderate yards, low risk.
- **Power** — A downhill run behind lead blockers. Higher yards potential but slightly higher fumble rate.
- **Sweep Option** — An edge run with an option pitch. High variance — can gain 0 or gain 15.
- **Speed Option** — Quick pitch to the perimeter. Relies on the ball carrier's speed to beat defenders to the edge.
- **Counter** — Fake one direction, run the other. Devastating against aggressive defenses that over-commit to initial reads.
- **Draw** — Fake a kick pass, hand off for a run. Exploits defenses that drop into coverage expecting the kick.
- **Viper Jet** — A jet sweep handoff to the Viper in motion. High variance, higher fumble risk, but the Viper in space is dangerous.

### Lateral Chain
The most exciting and most dangerous play type. The ball carrier pitches (laterals) the ball sideways or backward to a teammate, who can run, pitch again, or score. Chains of 2-5 laterals are common.

**The risk:** Every lateral exchange carries a fumble probability. The chance of fumbling increases with each additional lateral in the chain. A 4-lateral chain has roughly a 25% total fumble rate. This makes lateral plays a genuine gamble — you might gain 30 yards and score, or you might fumble and give the opponent a Bell (½ point) plus possession.

Lateral chains are the signature play of the Chain Gang and Lateral Spread offensive styles, which accept the fumble risk in exchange for explosive play potential.

### Kick Pass
The aerial game of Viperball. A player (usually the Zeroback) punts the ball to a teammate downfield. This is not a desperation heave — it's a designed play with route concepts, timing, and real accuracy.

**Completion rates by distance:**
- Short (≤8 yards): ~72%
- Medium (9-12 yards): ~62%
- Long (13-16 yards): ~50%
- Deep (17-20 yards): ~38%
- Bomb (21-25 yards): ~28%
- Hail Mary (26+ yards): ~18%

Most kick passes travel 4-18 yards in the air, biased toward shorter, completable distances.

**On completion:** The receiver catches the ball and can gain yards after catch (YAC). YAC is typically 0-5 yards but can be more with fast receivers.

**On incompletion:** The ball is dead — no change of possession — but the down is used. This is a key distinction from American football where incomplete passes stop the clock; in Viperball, the clock keeps running.

**Interceptions:** Only happen on *failed* completions. A defender doesn't intercept a ball that was going to be caught anyway. The base interception rate is low (~5.5% of attempts), making kick passing a relatively safe play. However, certain defensive schemes (Predator, Lockdown) increase interception probability.

**Kick pass touchdowns:** On completions of 20+ yards, there's a chance the receiver breaks free for a touchdown. This creates a big-play threat that keeps defenses honest.

A typical team attempts 40-45 kick passes per game, completing 55-65% of them. Kick passing is the most common play type in most offensive schemes.

### Trick Play
Misdirection plays involving fake handoffs, reverses, and deceptive formations. Trick plays are high-variance: they either gain big yards or get stuffed. They're most effective against aggressive defenses (Blitz Pack, Predator) that over-commit to their reads.

### Territory Kick (Punt)
Punting the ball to pin the opponent deep. Punts travel 30-60 yards with variance for bounces. Punting is less common in Viperball than in traditional football because:
- Teams have 6 downs instead of 4, so they're less likely to stall
- Field goal and drop kick attempts are preferred over punts when in range
- The Sacrifice system already penalizes leading teams, so giving up possession via punt has a higher opportunity cost

However, punting is central to the **Rouge Hunt** offensive style, which deliberately punts on early downs to pin opponents deep and score Pindowns.

### Drop Kick
A live-play scoring attempt worth 5 points. (See Scoring section above.)

### Place Kick
A held field goal attempt worth 3 points. (See Scoring section above.)

---

## Offensive Styles

Every team runs one of 9 offensive systems. The style determines play selection tendencies, tempo, risk tolerance, and strategic priorities.

### Ground & Pound
*"Grind 20 yards, punch it in. Old-school power football using all 6 downs."*

Heavy run emphasis. Uses all 6 downs to methodically gain yardage. Slow tempo, low lateral risk. Best against spread defenses that lack run-stopping bodies. Vulnerable to stacked defenses (Fortress) that wall off the interior.

### Lateral Spread
*"Stretch the defense horizontally with 2-4 lateral chains. High-variance, big-play offense."*

Maximum lateral chains. Every play is a potential 4-5 exchange sequence. Extremely high-variance — games feature both explosive touchdowns and costly fumbles. Fast tempo. Best against stacked defenses. Destroyed by Swarm defense (which converges on lateral exchanges).

### Boot Raid
*"Air Raid with the foot. Get to the Launch Pad, then fire snap kicks."*

The kick pass-heavy offense. Moves the ball downfield through kick passes, then attempts drop kicks from the Launch Pad (opponent's 40-45 yard line). Requires a Kicking ZB to maximize effectiveness. Best against Fortress (which sells out to stop the run, leaving kick pass lanes open). Vulnerable to Lockdown defense (which specializes in kick pass coverage).

### Ball Control
*"Conservative, mistake-free football. Take the points when available. Win 24-21."*

Low-risk, low-reward. Runs the ball reliably, takes field goals when available, avoids turnovers. Clock-burning tempo. Best against chaos-style defenses that gamble. Vulnerable to patient defenses (Drift) that bend but don't break.

### Ghost
*"Viper-centric misdirection. Pre-snap motion, jet sweeps, option reads — who has the ball?"*

Built around the Viper position. Heavy pre-snap motion, misdirection, and Viper Jet plays. The defense never knows who has the ball. Best against Blitz Pack (which over-commits and gets burned by misdirection). Vulnerable to Shadow defense (which mirrors the Viper's movement).

### Rouge Hunt
*"Defense-first offense. Punt early, pin deep, force mistakes. Score Pindowns, Bells, Safeties."*

An unusual philosophy: this offense tries to score through *defense*. Early punts pin the opponent deep. Pindowns (1 point each), forced safeties (2 points), and Bell fumble recoveries (½ point each) add up. The offense only needs to score occasionally because the defense is generating points. Low tempo, territory-focused. Best against teams with weak special teams.

### Chain Gang
*"Maximum laterals, maximum chaos. Every play is a 4-5 lateral chain. Showtime Viperball."*

An extreme version of Lateral Spread. Nearly every play involves 4+ lateral exchanges. The fastest tempo in the sport. Fumble rates are enormous, but so is the big-play potential. This is the most entertaining style to watch and the most nerve-wracking to coach.

### Triple Threat
*"Single-wing misdirection. Power Flankers take direct snaps. No one knows who has the ball."*

A throwback to early football. Multiple players can receive the snap directly, creating confusion about who the ball carrier is. Heavy option reads, moderate lateral chains. The misdirection bonus makes every play harder for the defense to diagnose.

### Balanced
*"No strong tendency, adapts to situation. Multiple threats, adaptable gameplan."*

The default style. No extreme tendencies — moderate kick pass rate, moderate lateral chains, moderate running game. Adapts situationally. Doesn't have the ceiling of specialized styles, but doesn't have the floor either. Best for teams without a dominant archetype player.

---

## Defensive Schemes

Every team runs one of 8 defensive systems. Each scheme has strengths and vulnerabilities that create rock-paper-scissors dynamics with offensive styles.

### Swarm Defense
*Tampa 2 analog. Zone-based rally defense.*

Everyone flows to the ball. Elite against lateral chains (multiple defenders converge on each handoff). Vulnerable to kick pass (gaps between zone drops create open receivers). The safe, balanced defensive choice.

### Blitz Pack
*46 Defense analog. Relentless pressure.*

Send extra rushers every play. Generates tackles for loss, sacks, and forced fumbles in the backfield. But the empty gaps left behind are exploited by counter plays, draws, and trick plays. High risk, high reward.

### Shadow Defense
*Man coverage analog. Mirror the playmakers.*

Assigns defenders to shadow the offense's best players, especially the Viper. Shuts down Viper-centric offenses (Ghost) but gets bulldozed by power running games that don't rely on individual playmakers.

### Fortress
*3-4 run-stop analog. Wall off the interior.*

Stacks the box to stop inside runs. Power plays and dive options are nearly impossible against the Fortress. But lateral chains go around the edges, and kick passes sail over the top. Best deployed against Ground & Pound; worst against Boot Raid and Chain Gang.

### Predator Defense
*Aggressive man coverage / turnover-hunting.*

Gambles for interceptions on kick passes and jumps routes aggressively. When the gamble works, it's a takeaway and momentum swing. When it fails, the receiver is wide open for a big gain or touchdown. The most volatile defensive scheme.

### Drift Defense
*Cover 3 / prevent analog. Bends but doesn't break.*

Gives up short yardage willingly but prevents explosive plays and deep kick passes. Patient and disciplined. Destroys Boot Raid offenses that need deep completions. Vulnerable to Ball Control offenses that are happy to take the short gains all day.

### Chaos Defense
*Unpredictable looks and stunts.*

Changes alignments constantly. Sometimes blitzes, sometimes drops back, sometimes stunts the defensive line. Wrecks predictable offenses (Ground & Pound, Rouge Hunt) but experienced, balanced offenses adapt and exploit the inconsistency.

### Lockdown
*Shutdown kick pass coverage.*

Specifically designed to deny kick pass completions. Drops extra defenders into coverage, takes away the deep ball, and creates more interception opportunities. The counter to Boot Raid. But the light box means the ground game runs wild — Ground & Pound and Ball Control feast on Lockdown.

---

## Special Teams Schemes

Each team selects one of 5 special teams philosophies:

### Iron Curtain
Elite coverage on punts and kicks. Gunners force muffs and pin returners. Your own return game is conservative — secure the ball, take the field position. The disciplined, field-position-first approach.

### Lightning Returns
Built around explosive returners. The Keeper and Viper get maximum return touches. Accept thin coverage for game-breaking return yardage and return touchdowns. High variance.

### Block Party
Rush the kicker every time. Highest blocked punt and blocked kick rate in the sport. But if the kick gets off, the coverage behind is thin and returners have room to operate.

### Chaos Unit
Fake punts, trick returns, surprise plays. 12% of punts are fakes. The opponent never knows what's coming. Sometimes genius, sometimes disaster.

### Aces
Well-rounded. Slight bonus across the board, no weakness. The safe pick for teams without a special teams identity.

---

## Weather

Games are played in one of 6 weather conditions, each affecting gameplay:

### Clear
No modifiers. The baseline.

### Rain
Wet ball, slippery field. Increased fumble rate (+2.5%), reduced kick accuracy (-8%), increased lateral fumble risk, higher muff rates on punt returns. Players are slightly slower.

### Snow
Cold and slippery. Major kick accuracy penalty (-12%), moderate fumble increase (+2%), significantly higher stamina drain. The worst conditions for kicking teams.

### Sleet
The worst weather condition. Extreme fumble risk (+3.5%), terrible kicking accuracy (-15%), exhausting stamina drain (+20%). Games played in sleet are chaos — turnovers everywhere, low scores, and survival matters more than scheme.

### Extreme Heat
100°F+. Rapid stamina drain (+30%) means players fatigue quickly. Slight fumble increase from sweaty hands. Kicking is mostly unaffected. Favors teams with deep rosters and good conditioning.

### Heavy Wind
Strong gusts. Kick accuracy heavily impacted (-10%). Punts travel further but with wild variance. Minimal effect on running and lateral plays. Changes the kicking calculus dramatically — drop kicks from 40+ yards become very risky.

---

## Penalties

Viperball has a comprehensive penalty system with 30+ infraction types across 5 phases:

**Pre-snap penalties** (5 yards each): False Start, Offsides, Delay of Game, Illegal Formation, Encroachment, Too Many Men on Field, Illegal Substitution, Illegal Viper Alignment.

**During-play penalties (run):** Holding (10 yards, offense), Illegal Block (10), Clipping (15), Defensive Holding (5, auto first down), Facemask (15, auto first down), Unnecessary Roughness (15), Horse Collar (15, auto first down), Personal Foul (15).

**During-play penalties (lateral):** Everything from run penalties, plus Illegal Forward Lateral (5, loss of down), Illegal Block in Back (10), Lateral Interference (10, auto first down), Illegal Viper Contact (10, auto first down).

**During-play penalties (kick):** Roughing the Kicker (15, auto first down), Running Into Kicker (5), Fair Catch Interference (15), Kick Catch Interference (15), Illegal Kick (10).

**Post-play penalties** (15 yards each): Taunting, Unsportsmanlike Conduct, Late Hit, Excessive Celebration, Sideline Interference.

Weather conditions increase penalty probability slightly — wet conditions cause more holding, heat causes more personal fouls.

---

## The Vocabulary of Viperball

**Bell** — Half a point scored by the defense for recovering a fumble. Named for the sound it makes on the scoreboard. "That's a Bell for the defense — half point, and they've got the ball."

**Boot** — A kick pass. "She boots it 15 yards to the Slotback in stride."

**Chain** — A lateral chain. "Three-link chain from the Halfback to the Wingback to the Viper — and she's gone for 25 yards!"

**Drop Kick / Snap Kick / DK** — A 5-point drop kick through the uprights. The terms are interchangeable. "DK from 38 yards — it's good! That's 5!"

**Flanker** — General term for Halfbacks, Wingbacks, and Slotbacks. The skill position players who run, catch, and lateral.

**Launch Pad** — The opponent's 40-45 yard line. The range from which drop kicks become viable for specialist kickers. "They've reached the Launch Pad — expect a snap kick attempt."

**Link** — One lateral exchange within a chain. "That was a four-link chain."

**Pindown** — A 1-point score for punting the ball into the end zone without a return. "Pindown! The punt dies in the end zone, and that's a point for the kicking team."

**Rouge** — An older term for Pindown, borrowed from the CFL. Sometimes used interchangeably.

**Sacrifice** — The field position penalty imposed on the leading team. "They're up 14, so they start at their own 6 — that's a heavy sacrifice."

**Snap Kick** — Drop kick. The "snap" refers to receiving the snap and immediately kicking without a holder.

**Territory Kick** — A strategic punt aimed at pinning the opponent deep. Not a desperation play — a weapon.

**Viper Jet** — A jet sweep handoff to the Viper in motion. "Viper Jet to the boundary — she takes it 12 yards before the Keeper brings her down."

**Zeroback** — The primary ball-handler. Called "Zeroback" because the position originated as a "back" who lines up at zero depth behind the line.

---

## What Dramatic Moments Look Like

For narrative purposes, here are the types of moments that define Viperball games:

**The Sacrifice Comeback:** A team trails by 20 in the 3rd quarter. They're starting every drive at their own 40 (Sacrifice bonus for trailing). They rip off three straight touchdown drives because they're working with short fields. The leading team, meanwhile, is starting at the 1-yard line and can barely avoid safeties. The lead evaporates. The game is tied entering the 4th quarter.

**The Drop Kick Duel:** Two Kicking ZBs on opposite sidelines. Every time one team reaches the Launch Pad, they fire a snap kick through the uprights for 5. The score is 55-50, and neither defense can get a stop. The game comes down to who hits the last drop kick.

**The Lateral Chain Disaster:** A Chain Gang team is rolling — four straight drives with 30+ yard lateral chains. Then on the fifth drive, the third lateral in a 4-link chain hits the ground. Fumble. Defense recovers — Bell, half a point, plus possession. The momentum swings entirely.

**The Pindown War:** A Rouge Hunt offense facing a team with weak special teams. The offense punts on 3rd down three times in the first half, pinning the opponent deep each time. Two Pindowns (2 points), plus a safety when the opponent fumbles at their own 2-yard line. The Rouge Hunt team is winning 4-0 without ever reaching the opponent's territory on offense.

**The Sleet Game:** Snow turns to sleet in the 3rd quarter. Both kickers can barely hit from 20 yards. Fumbles happen on every other play. The final score is 22-19½, with 8 Bells between the two teams. The box score looks like a crime scene.

**The Viper Game:** A Receiving Viper catches 8 kick passes for 95 yards, runs 3 Viper Jets for 40 yards, and scores 3 touchdowns. She's unguardable because the Shadow defense can't figure out where she's lining up. The opposing coordinator switches to Lockdown at halftime, but the Ghost offense adjusts to power runs and the Viper becomes a decoy, drawing coverage while the Halfback rushes for 80 second-half yards.

---

## League Structure

The Collegiate Viperball League (CVL) comprises 187 teams across 16 conferences:

| Conference | Teams | Identity |
|---|---|---|
| Big Pacific | 12 | West Coast powers |
| Border Conference | 14 | Southwest and border region |
| Collegiate Commonwealth | 9 | Mid-Atlantic and Southern |
| Galactic League | 10 | Experimental, expansion-era programs |
| Giant 14 | 13 | Major Midwest institutions |
| Interstate Athletic Association | 12 | Multi-region independent programs |
| Midwest States Interscholastic Assoc. | 13 | Heartland college programs |
| Moonshine League | 13 | Appalachian and Southern mountain |
| National Collegiate League | 8 | Small, prestigious programs |
| Northern Shield | 12 | Upper Midwest and Great Lakes |
| Outlands Coast Conference | 12 | Coastal and Gulf programs |
| Pioneer Athletic Association | 14 | Historic programs, diverse regions |
| Potomac Athletic Conference | 13 | East Coast corridor |
| Prairie Athletic Union | 12 | Great Plains |
| Southern Sun Conference | 9 | Deep South |
| Yankee Fourteen | 11 | New England |

The league includes HBCUs, women's colleges, military academies, and small institutions alongside major universities. This diversity is intentional — Viperball is a sport where a 2,000-student women's college can compete with a 40,000-student state university.

**Seasons** consist of conference schedules plus non-conference games, culminating in a playoff with conference champion auto-bids and at-large selections based on Power Index (a 100-point ranking considering win%, strength of schedule, quality wins, conference strength, and point differential).

**Rivalries** are designated between specific teams, with guaranteed annual games and in-game performance boosts for the underdog.

**Dynasty mode** spans multiple seasons with recruiting classes, player graduation, coaching changes, and program history accumulating year over year.

---

## Key Numbers for Narrative Calibration

These are the statistical ranges a narrative engine should use for realistic game descriptions:

| Stat | Typical Range Per Team |
|---|---|
| Final score | 40-75 points |
| Touchdowns | 4-6 |
| Drop kick attempts | 8-12 |
| Drop kicks made | 3-5 |
| Place kick attempts | 3-5 |
| Kick pass attempts | 40-45 |
| Kick pass completions | 55-65% |
| Kick pass TDs | 1-3 |
| Rush yards | 80-120 |
| Lateral chain plays | 15-25 |
| Fumbles | 2-5 |
| Punts | 0-3 |
| Penalties | 4-8 |
| Plays per team | 75-90 |

---

*This document reflects the Viperball engine as of February 2026.*
*Source: engine/game_engine.py and supporting simulation code.*
**Ready to build your Viperball dynasty? Let's go! 🏈**
