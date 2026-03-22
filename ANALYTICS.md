# Viperball Analytics Guide

A reference for writers, analysts, and language models trying to make sense
of Viperball statistics. Every metric below is mapped to its closest real-sport
analogue so you can reason about the numbers even if you've never seen a game.

---

## The Sport in 60 Seconds

Viperball is women's collegiate gridiron football where **the forward pass was
never invented**. Teams move the ball three ways: running, lateral passing
(backward/sideways only), and kick passing (punting the ball to a teammate
downfield). It plays on a standard 100-yard field with 6 downs to gain 20
yards (vs. football's 4-for-10).

**Why the numbers look different from football:**
- Touchdowns are worth **9 points** (no extra point attempt)
- Snap kicks (drop kicks through the uprights during live play) are worth **5**
- Field goals (place kicks from scrimmage) are worth **3**
- Safeties are **2**, pindowns (territorial scores) are **1**, bells (fumble
  recoveries) are **½**
- Typical game scores: **45-70 points per team** (combined 90-140)
- A team runs **70-90 plays per game** (similar to up-tempo college football)

Think of it as rugby's ball movement married to football's territorial
structure, with a kicking game that functions like soccer set pieces woven
into live play.

---

## Scoring Channels — The Six Ways to Score

Viperball has six distinct scoring methods. No other major sport has this many
concurrent point values in play. This is the single biggest thing that makes
the analytics different.

| Score | Points | Real-Sport Analogue | Strategic Role |
|-------|--------|---------------------|----------------|
| **Touchdown (TD)** | 9 | NFL touchdown (6+PAT=7) | Terminal goal of every drive |
| **Snap Kick (DK)** | 5 | Rugby drop goal (3) | High-risk/high-reward; attempted during live play |
| **Field Goal (PK)** | 3 | NFL field goal (3) | Safe points; end-of-drive consolation |
| **Safety** | 2 | NFL safety (2) | Defensive territory win |
| **Pindown** | 1 | Rugby penalty kick to touch | Punt that pins opponent inside the 10 |
| **Bell** | ½ | — (unique to Viperball) | Recovering a loose ball (fumble, muff) |

**Key insight for analysis:** A team can win without touchdowns. A "Boot Raid"
offense that hits 8 snap kicks (40 pts) and a few pindowns can outscore a team
with 4 TDs (36 pts). When analyzing scoring, always check the **scoring
profile** — *how* a team scores matters as much as *how much*.

---

## Team Metrics — The Numbers That Tell the Story

### Points Per Drive (PPD)
**What it is:** Average points scored per offensive possession.
**Football analogue:** NFL "points per drive" (used by Football Outsiders).
**Scale:**

| Rating | PPD | What it means |
|--------|-----|---------------|
| Elite | 5.0+ | Scoring almost every drive (think 2019 LSU, 2023 Michigan) |
| Good | 3.5–5.0 | Consistently moving the ball, converting drives |
| Average | 2.5–3.5 | Mixed results, some stalled drives |
| Poor | <2.5 | Struggling to sustain drives |

**Why it matters:** PPD is the single best measure of offensive quality. Unlike
total points, it adjusts for pace (a team with fewer possessions isn't
penalized). Unlike yards, it captures scoring efficiency.

---

### Conversion Rate (Conversion %)
**What it is:** Percentage of 3rd-down-or-later plays that result in a first
down or score.
**Football analogue:** 3rd-down conversion rate.
**Scale:**

| Rating | Conv % | Translation |
|--------|--------|-------------|
| Elite | 55%+ | Sustaining drives at will |
| Good | 45–55% | Reliable chain-mover |
| Average | 35–45% | Inconsistent on pressure downs |
| Poor | <35% | Stalling out constantly |

**Viperball wrinkle:** With 6 downs instead of 4, teams have more chances to
convert, so the overall conversion rate is higher than football. But "pressure
downs" (4th, 5th, 6th) carry compounding urgency — the engine models a
performance cliff on 6th down where success probability drops ~35%.

---

### Lateral Completion Rate (Lateral %)
**What it is:** Percentage of lateral-chain plays that don't result in a
turnover.
**Closest analogue:** Completion percentage in football, but for a fundamentally
different mechanic.
**Scale:**

| Rating | Lat % | Translation |
|--------|-------|-------------|
| Elite | 80%+ | Clean ball movement, disciplined hands |
| Good | 65–80% | Occasional bobble but mostly reliable |
| Average | 50–65% | Turnover-prone in the lateral game |
| Poor | <50% | Hemorrhaging the ball |

**Why this matters for Viperball specifically:** Laterals are the *only* way to
pass the ball. Every lateral chain compounds fumble risk (+4% per additional
lateral in a chain, starting from an 8% base). A 3-lateral chain has ~16%
fumble risk per play. Teams with high lateral rates are either very disciplined
or very lucky — and over a season, discipline wins.

**Cross-sport context:** Think of lateral % as the Viperball equivalent of
turnover rate in basketball. The 65-80% "good" range means even strong teams
are losing the ball on ~25% of their lateral attempts. This is *by design* —
the sport is built around controlled chaos.

---

### Explosive Play Rate
**What it is:** Plays gaining 15+ yards.
**Football analogue:** ESPN's "explosive play" stat (20+ yard plays in NFL).
**Typical range:** 4-12 per game. 8+ is dangerous; 12+ is a dominant
performance.

**The Viperball twist:** Explosive plays in Viperball often come from lateral
chains that break containment or kick passes that connect downfield. A
breakaway run gets a 15% chance of extending into a bigger play, and that
chance increases when the defense is fatigued (12+ plays into a drive → 1.25x
breakaway rate). So explosive plays are partly about talent and partly about
grinding the defense down.

---

### Turnover Margin (TO+/-)
**What it is:** Turnovers forced minus turnovers committed.
**Football analogue:** Exactly the same stat.
**Typical range:** -5 to +5 in a single game.

**Viperball context:** Turnovers are *more frequent* than in football because
laterals are inherently risky and kick passes can be intercepted. A typical
game produces 4-8 total turnovers (vs. 2-4 in an NFL game). Being +3 in
Viperball is roughly equivalent to being +2 in the NFL — significant but not
as dominant as the raw number suggests.

---

### WPA (Win Probability Added)
**What it is:** How much each play shifted the team's probability of winning.
Summed across all plays for a game total.
**Football/baseball analogue:** Exactly WPA from MLB and NFL analytics.
**Scale:** A game-total WPA of +5.0 means "this team's plays collectively
added 5 expected points of win equity." Context-dependent — a TD in a
blowout adds less WPA than a TD in a tie game.

**Components:**
- **Offense WPA:** Value added by rushing/lateral/kick-pass plays
- **Special Teams WPA:** Value added by kicks (snap kicks, FGs, punts)
- **Success Rate:** % of plays with positive WPA (healthy offense: 45-55%)
- **Explosiveness:** Average WPA on successful plays only (big-play ability)

---

### Team Rating (0-100)
**What it is:** Composite team quality score.
**Football analogue:** ESPN's SP+, College Football Playoff rankings, or
Madden team overall rating.
**Components:**
- PPD (25%) — scoring is king
- TO margin (20%) — turnover battle decides close games
- Conversion % (15%) — sustaining drives
- Lateral % (10%) — Viperball's signature skill
- Explosive plays (10%) — big-play threat
- Kicking game (10%) — DK%, FG%, punt average
- Field position (10%) — average starting yard line

---

### Delta Profile (Operating Environment)
**What it is:** The conditions each team operates in — not performance, but
difficulty. Measures yardage differential, drive count differential, and
scoring differential to describe whether a team is playing in easy or hard
states.

**Components:**
- **Δ Yards** — net yardage gained vs allowed. Positive = gaining more.
- **Δ Drives** — net drive count differential. More drives = more chances.
- **Δ Scores** — net scoring drive differential.
- **KILL%** — percentage of drives ending in total failure (turnover on
  downs or punt with <5 yards gained).

**The key insight (from analysis of league-wide data):**
High disruption (high KILL%) does NOT correlate with winning. Controlled
outcomes do. The teams that win are not the ones that blow up the most
opponent drives — they're the ones that limit their own catastrophic
sequences. A team with 40% KILL% that loses is disrupting but not
controlling. A team with 11% KILL% that wins is surviving consistently.

---

### Conversion by Field Position (The Missing Layer)
**What it is:** Late-down conversion rates (4th, 5th, 6th down) split by
where on the field the attempt happens.

**Why this is the most important metric in Viperball:**

Two teams can both convert 53% on 5th down. But:
- Team A converts at midfield
- Team B converts from their own 15

Those are completely different teams. The flat conversion rate treats them
as identical. This metric reveals which teams survive when the field is
worst.

**Field zones:**
| Zone | Yard Lines | Meaning |
|------|-----------|---------|
| Own Deep | 1-25 | Backed up, hostile territory |
| Own Half | 26-50 | Manageable, can build a drive |
| Opp Half | 51-75 | Opponent's side, scoring approaches |
| Opp Deep | 76-99 | Red zone, should score from here |

**What the data shows across league play:**
- Winning teams have slightly higher 5D% — not dramatically, but consistently
- The gap is small (2-5%) but it compounds over a season
- The separation is clearest in the own-deep zone: teams that can convert
  5th-and-long from their own 15 survive; teams that can't get buried
- 6D% varies wildly (small samples) and is less predictive than 5D%

**Bottom line:** The league is decided by small edges in late-down conversion,
conditioned by field position. Winners survive slightly more often, in
slightly worse conditions, over many repetitions.

---

## Player Metrics

### ZBR (Zeroback Rating)
**What it is:** Composite rating for the Zeroback (the primary ball handler —
Viperball's equivalent of a quarterback).
**Football analogue:** QBR or passer rating. Uses the **same 0-158.3 scale**
as NFL passer rating so the numbers feel familiar.
**Components:** Lateral accuracy, yards generated, touchdowns, turnovers.
**Scale:** 158.3 = perfect game, ~100 = great, ~80 = solid, <60 = struggling.

**Key difference from QBR:** A Zeroback doesn't throw forward passes. ZBR
measures lateral distribution, rushing production, and kicking. A
"distributing" Zeroback with high lateral accuracy and low turnovers can rate
as highly as a "rushing" Zeroback who gains yards with their legs.

---

### VPR (Viper Rating)
**What it is:** Composite rating for the Viper — a unique position with no
real-sport equivalent. The Viper is alignment-exempt (can line up anywhere),
wears a distinct jersey, and functions as a wild card.
**Scale:** Same 0-158.3 scale as ZBR.
**Emphasis:** Explosiveness and big-play ability (the Viper is the X-factor).

**Think of the Viper as:** A combination of a punt returner, a wide receiver
who can't catch forward passes, and a designated hitter who bats for the
pitcher. They exist to create chaos.

---

### WAR (Wins Above Replacement)
**What it is:** Total player value in wins compared to a replacement-level
player at the same position.
**Baseball analogue:** Exactly baseball WAR.
**Calculation:** Yards above replacement × points per yard ÷ points per win,
with diminishing returns on volume.
**Typical range:** 0-3.0 WAR for a full season. A 2.0+ WAR Zeroback is an
All-Conference performer.

---

## Viperball-Specific Concepts (No Direct Analogue)

### Scoring Profile
Not a single number but a breakdown of *how* a team scores:
- **Rush TD %** — touchdowns from straight rushing
- **Lateral TD %** — touchdowns involving lateral chains
- **Kick-Pass TD %** — touchdowns from kick passes (the "aerial" game)
- **Snap Kick %** — points from drop kicks (the aggressive kicking option)
- **Field Goal %** — points from place kicks (the conservative option)
- **Return TD %** — touchdowns on punt/kick returns
- **Bonus %** — points scored on bonus possessions (defense-generated offense)

**Why this matters:** Two teams can score 55 points with completely different
profiles. One might be a "ground and pound" team (70% rush TDs), another
might be a "boot raid" team (50% snap kick points). The scoring profile
tells you *what kind* of team you're watching.

### Kicking Aggression Index
The share of a team's kick attempts that are snap kicks (5 pts, risky) vs.
field goals (3 pts, safe). A team with 80%+ snap kick share is playing a
high-variance kicking game — they'll either dominate or give up return TDs.

### Bonus Possessions (Defense-Generated Offense)
Unique to Viperball: when the defense forces certain turnovers, the team gets
an *extra* possession on top of the normal change of possession. This means
defense directly generates offensive opportunities. Track:
- **Bonus possessions earned** — how many extra possessions the defense created
- **Bonus conversion rate** — what % of those extra possessions scored
- **Bonus points** — total points from defense-generated drives

### Composure
A dynamic mental state (0-140 scale, 100 = neutral) that shifts during the
game based on events. TDs boost composure (+6), turnovers crater it (-8),
failed conversions erode it (-10). Think of it as "momentum" made measurable.
Composure modifies play success probabilities, creating snowball effects —
a team that gets tilted (composure <70) starts failing at higher rates,
creating more tilt.

### Fatigue Cliff
Players operate at full capacity above 80% energy, but there's a brutal
cliff between 40-20% energy where performance drops to 55-85% of normal.
Below 20%, players are nearly useless (40% capacity) and 4x more likely
to get injured. This forces roster rotation and makes depth a real strategic
resource — you can't ride your star for 15+ plays without consequences.

---

## Cross-Sport Translation Guide

For writers trying to contextualize Viperball against sports readers know:

| Viperball Concept | NFL Equivalent | NBA Equivalent | Baseball Equivalent |
|-------------------|---------------|----------------|---------------------|
| PPD 5.0+ | Top-5 offense | 115+ offensive rating | .800+ OPS lineup |
| Lateral % 80+ | 70%+ completion rate | 50%+ FG% | .300+ team BA |
| TO margin +3 | +2 turnover differential | +5 turnover margin | — |
| 8+ explosive plays | 6+ plays of 20+ yards | 10+ fast break pts | 3+ extra-base hits |
| ZBR 120+ | 110+ passer rating | — | — |
| WAR 2.0+ | — | — | 5.0+ WAR (position player) |
| Composure <70 | "Rattled" QB, 3+ INTs | Cold shooting + turnovers | Pitcher losing command |
| 6th-down conversion | 4th-and-long conversion | End of shot clock | 2-strike at-bat |

### Scoring Pace Comparison
| Sport | Typical Combined Score | Scoring Events/Game |
|-------|----------------------|---------------------|
| NFL | 40-50 | 8-12 |
| College Football | 50-70 | 10-16 |
| **Viperball** | **90-140** | **15-25** |
| NBA | 210-230 | 80-100 |
| NHL | 5-7 | 5-7 |

Viperball's scoring pace sits between football and basketball. There are
enough scoring events to create statistical significance within a single game,
but each score still matters individually (unlike basketball where a single
basket is noise).

---

## What Makes the Math Different

If you're an LLM or analyst encountering Viperball data for the first time,
here's why the numbers might seem "off" compared to real football:

1. **Touchdowns are worth 9, not 7.** Don't mentally convert to NFL scoring.
   A 45-point performance in Viperball is ~5 TDs worth, which maps to roughly
   a 35-point NFL game. Adjust by multiplying Viperball scores by ~0.78 to
   get a feel for NFL-equivalent dominance.

2. **There are no forward passes.** Zero passing yards, zero completion
   percentage in the traditional sense. Lateral chains and kick passes replace
   the aerial game. Lateral % is the closest thing to completion %, and kick
   pass yards are the closest thing to passing yards.

3. **Half-point scores exist.** Bells (½ pt) mean final scores can be
   fractional: 47½ to 39 is a valid score. This isn't an error.

4. **6 downs inflates conversion opportunities.** Teams convert more often
   than in football because they get two extra downs. A 45% conversion rate
   in Viperball maps to roughly a 35% 3rd-down rate in the NFL — both are
   "average."

5. **The kicking game is part of the offense.** Snap kicks happen during
   live play, not as a set-piece stoppage. A team might attempt 4-6 snap
   kicks per game. This is like if NFL teams had an option to attempt a
   field goal on any down from anywhere on the field, with the risk that a
   miss becomes a live ball the defense can return.

6. **Turnover rates are higher than football.** Laterals compound fumble
   risk. 4-8 turnovers per game is normal, not sloppy. Adjust your "this
   team is careless" threshold upward.

7. **Two-way play is mandatory.** There is no separate offense and defense.
   Every player plays both sides. This means fatigue management and depth
   matter far more than in football, and individual players accumulate both
   offensive and defensive stats.

---

## Using This Data for Writing

When writing about a Viperball game or season, lead with:

1. **The scoring profile** — *how* the team won, not just the score
2. **The key matchup** — which positional contest (ZB vs defense, Viper
   impact, lateral game vs tackling) decided the game
3. **The momentum story** — composure swings create natural narrative arcs
   (early tilt, comeback surge, fourth-quarter collapse)
4. **The fatigue story** — did depth win? Did a team ride a star too hard?
5. **The kicking gamble** — did aggressive snap kicking pay off or backfire?

A good Viperball game story reads like a rugby match report crossed with a
baseball analytics column: the flow of play matters, but the numbers tell
you things the eye test misses.
