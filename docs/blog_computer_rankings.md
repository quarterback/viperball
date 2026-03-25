# The Nerdiest Problem in Sports (And Why a Fake Sport Might Be the Best Version of It)

In 2007, I got my name on a list.

Not a prestigious list. Not a list anyone outside a very specific corner of the internet would care about. Kenneth Massey — a math professor at Carson-Newman University in Tennessee — maintains a website called the Massey Ratings Composite. It tracks every known computer ranking system for college football. When I started watching, there were maybe 60 or 70 systems on the list. By the time I stopped, there were over 100.

My system was called the **Omnivore Rankings**. Getting on the list was not hard. I emailed Massey with my criteria and a link to the site. He added it. That was it. No peer review, no credential check, no minimum number of PhDs. Just: here's my system, here's where it lives. I stayed on the list each year until I stopped updating. That's how the whole ecosystem works — anyone with a methodology and a URL can play.

The Omnivore Rankings were **retrodictive** — they looked backward. The goal wasn't prediction. It was evaluation. I wanted to answer a question the BCS didn't care about and the polls couldn't answer: **who are the best mid-major programs, and what would their records look like if they played power conference schedules?** I wasn't trying to crown Alabama or USC. I was trying to figure out if Boise State or TCU or Utah were being robbed — and if so, by how much.

I went retroactive with it, too. Ran the system backward through the 1990s, decade by decade, ranking every season I could get data for. Watched the patterns emerge — which mid-major programs were consistently undervalued, which power conference teams were paper tigers propped up by weak non-conference scheduling. The system lived on Massey's list for seven years. When the College Football Playoff arrived in 2014 and the BCS died, the specific injustice the Omnivore Rankings existed to measure became less urgent. I stopped updating. The list moved on.

But the problem didn't go away. It just changed shape.

---

## The Problem That Won't Stay Solved

To understand why computer rankings even exist — and why hundreds of people have built them — you have to understand the specific madness of college football's structure.

In 1999, when the Bowl Championship Series was trying to figure out how to pick two teams for a national championship game, SEC Commissioner Roy Kramer went looking for computer rankings to incorporate into the formula. He couldn't believe what he found. There were hundreds. Hundreds of people — math professors, software engineers, retired rocket scientists, a 23-year-old grad student at Virginia Tech — had independently built systems to rank college football teams. Kramer and his assistant Charles Bloom reviewed about 60 of them and picked eight.

The people behind those systems were a wild cast. Richard Billingsley, a 5'7" personnel consultant from Nashville who'd been compiling rankings since 1970, joked he was "too small to be a high school cheerleader." He openly rooted for Oklahoma, his boyhood team — and then ranked them 48th despite a 3-0 start, which ended the fan mail. David Rothman, a former top-flight bridge player with an IQ north of 160 who'd worked on the team that designed the space shuttle's Orbiter lifting frame, built a system so pure and free of preseason bias that it was as if "689 college football teams arrived from Mars on August 25." Herman Matthews, 69, chairman of the math department at Lincoln Memorial University, had been running his system since 1965. Kenneth Massey was 23 years old, a graduate student whose father was a Virginia Tech season ticket holder — and yes, Virginia Tech was ranked #2 at the time.

None of them were paid.

The BCS had rules. All systems had to predate 1995. No gambling associations. And critically: **no margin of victory**. The NCAA insisted that a 45-0 blowout be treated identically to a one-point overtime win. They were worried coaches would run up the score. Jeff Sagarin, the dean of college rankings who'd been publishing his ratings in USA Today since 1985, was blunt about how dumb this was: "When you throw away the scores, you're throwing away a huge amount of important information." His BCS-compliant system — the neutered one — had Alabama third. He knew it was wrong. "They love the cliché 'a win is a win,'" he said, "which to me is one of the most vapid clichés of all time."

By 2012, when the New York Times profiled the proliferation of ranking systems, the community had grown even larger. Jon Dokter, an astronomy professor who'd been running his Entropy System since 1993, had retroactively ranked every college football season back to 1869. He judged the 1945 Army team — Doc Blanchard and Glenn Davis — as the most dominant team in history. And he explained why college football, specifically, attracts this obsession:

> "The bowl system not producing an official national champion, the small number of games. Unlike most other sports, college football teams can only play about 10 percent of all other teams in a given year; that necessitates the power ranking."

That's the core of it. In the NFL, every team plays 17 games and eventually meets in the playoffs. In MLB, you play 162 games. The cream rises. But in college football, you have 130+ teams playing 12 games each, mostly against teams in their own conference, and then you have to figure out whether the team that went 12-0 in the Sun Belt is better than the team that went 10-2 in the SEC. You literally cannot know, because they never played each other and they share almost no common opponents.

It's an **incomplete information problem**. You're trying to infer a total ordering of 130 teams from a sparse graph of ~800 games. There is no unique solution. Every ranking system is making assumptions about what matters — wins vs. margins, schedule strength vs. raw performance, recent form vs. full-season body of work — and those assumptions produce meaningfully different answers.

Massey put it simply: "It's kind of a nerdy hobby. It combines sports with math and computers, three things that don't ordinarily go together."

But here's what the hobby profiles never quite get into: the ranking problem isn't just nerdy. It's **genuinely hard mathematics**. The same linear algebra and graph theory that power Google's PageRank algorithm are the same tools people use to rank football teams. Massey himself pointed this out: "There are so many parallels with things Google and Facebook do. It turns out Google uses basically the same algorithm you use to rank sports teams." Sagarin's methods have been applied to tax policy and presidential politics. Sorensen, a physics professor at Tennessee who'd been running his system since the 1980s, warned that his method "is not easily explainable to people who have not had linear algebra."

Dokter went further: "I would consider sports prediction more difficult than professional research science on the physical world. Predicting sports is one of the hardest things there is."

The College Football Playoff has mostly killed the urgency of the debate. The BCS is dead. The specific injustice of a two-team system — where being #3 meant being excluded entirely — no longer exists. But the mathematical problem hasn't gone away. It's just moved underground, back to the people who do it because the problem itself is beautiful.

---

## A Fake Sport With a Real Math Problem

I built Viperball as a game — a collegiate dynasty simulator for a sport that never existed. It started from a Reddit thread about what modern football would look like if the forward pass had never been invented. The game has 187 women's collegiate teams, no forward passing, six different ways to score, and a rubber-band mechanic called the delta yards system that punishes leading teams with worse field position.

I did not build it to be a ranking problem. But it turns out I accidentally built the *perfect* ranking problem.

Here's why.

**The sparsity problem is identical.** 187 teams play 12-game schedules. They're organized into conferences. They mostly play each other. The playoff takes 16 teams. You have to figure out who those 16 should be from a graph where each team has played fewer than 7% of the league. It's the exact same structural problem as real college football — the same problem that made Kramer go looking for computer help in 1999, the same problem that has sustained Massey's composite for three decades.

**But the scoring is way more interesting.** Viperball has a six-channel scoring system:

| Score | Points |
|-------|--------|
| Touchdown | 9 |
| Snap Kick (drop kick) | 5 |
| Field Goal (place kick) | 3 |
| Safety | 2 |
| Pindown | 1 |
| Bell (loose ball recovery) | 0.5 |

A team that wins 45-40 by scoring five touchdowns has a completely different profile than a team that wins 45-40 by mixing three touchdowns with six snap kicks and a few pindowns. The margin is the same. The *meaning* of the margin is not. This is something real football ranking systems never have to deal with — in the NFL, a point is a point. In Viperball, you have to decide whether multi-channel scoring efficiency is more informative than raw margin. The BCS banned margin of victory entirely. Sagarin thought that was idiotic. In Viperball, even the people who *do* use margins have to reckon with the fact that not all margins are created equal.

**The delta yards system breaks traditional assumptions.** In Viperball, when you're winning, the game gets harder. Leading teams start their drives further back on the field — the larger the lead, the worse the starting position. Trailing teams get the opposite boost. This means a 20-point blowout in Viperball is *more impressive* than a 20-point blowout in real football, because the winning team was fighting a field position penalty the entire second half. It also means close games aren't necessarily indicative of evenly matched teams — the delta system *compresses* margins by design.

Every existing ranking methodology has to be rethought. Massey's least-squares regression on margins? You need to account for the fact that margins are mechanically compressed. Elo's margin-of-victory K-factor? The same margin means different things depending on how much delta penalty the winner absorbed. Pythagorean expectation? The exponent needs recalibration because the scoring distribution is fundamentally different from any real sport. Rothman's "arrived from Mars" purity? Fine, but Mars doesn't have a delta yards system.

**You have perfect information.** This is the really interesting part. In real college football, ranking nerds are working from box scores. They know the final score, maybe the yards, maybe the turnovers. In Viperball, I have every play of every game — every drive, every yard, every decision, every fumble, every delta-penalized possession. I can compute EPA (Expected Points Added) on every single play. I can track which teams score efficiently when penalized by the delta system. I can measure game control quarter by quarter. I can see how teams perform when trailing at halftime.

Billingsley had to lobby Kramer just to be allowed to apply common-sense judgment calls to his numbers. Kramer refused. In Viperball, you can build ranking systems that use information those BCS rankers could only dream of.

**And you can run it again.** This might be the biggest thing. In real college football, you get one season. Your ranking system either matches the consensus or it doesn't, and you argue about it on message boards for four months. In Viperball, you can simulate a thousand seasons and see which ranking systems are actually *predictive* — which ones correctly identify the best teams before the playoff proves it. You can test your methodology against ground truth in a way that's impossible with real sports.

---

## 28 Systems, One Grid

So I built what Massey built — but for a sport that doesn't exist.

The CVL Ranking Composite runs **28 independent ranking algorithms** against every season of Viperball. Each one produces its own ordering of all 187 teams. The composite is the average rank across all systems. But the composite isn't really the point. **The variance between systems is the point.**

When all 28 systems agree that a team is #1, that team is #1. That's boring. What's interesting is when Elo says #3 and Colley says #40 and the Resume Index says #1. That team is *controversial* — and the disagreement tells you something real about their profile. Maybe they beat everyone they played but their schedule was weak (Colley doesn't care about margins, so it sees the weak schedule; Elo does care about margins, so it rewards the blowouts). Maybe they have three quality wins and two bad losses (Resume loves the quality wins; the math models hate the bad losses). It's the same kind of disagreement that made Marshall fans send Billingsley hate mail when he had them ranked 32nd while other systems had them in the top five.

The systems range from the well-known — Elo, Colley Matrix, Massey Ratings, Bradley-Terry, Sagarin — to the Viperball-specific. The **Delta Yards Index** measures how well teams handle the rubber-band mechanic. The **Comeback Success Rate** tracks win percentage when trailing at halftime combined with power play scoring efficiency. The **Margin Compression MOV** applies logarithmic dampening to blowouts, because in a sport with a built-in equalizer, a 40-point win is logarithmically, not linearly, more impressive than a 10-point win.

There are three systems I deliberately included because they're opaque and controversial — the **Billingsley** (a chain-based system where beating a team means inheriting a fraction of their rating, named for the man who had Oklahoma fans doing cartwheels and then sending death threats within the same month), **Dokter Entropy** (named for Jon Dokter, using information theory to reward consistency over volatility), and **PageRank** (literally Google's algorithm applied to the win-loss graph — the same parallel Massey pointed out in that Times interview). These systems are included *because* they're weird. The composite is richer when it contains systems that see the world differently.

---

## Why This Matters (Or Doesn't, Which Is the Point)

I ran the Omnivore Rankings for seven years because the problem was beautiful. Not because I thought I'd solve it. Not because anyone outside Massey's list cared what my system said about TCU. Because the act of building a ranking system forces you to articulate what you believe about competition. Do you believe margins matter? Do you believe recent games are more informative than early-season games? Do you believe schedule strength should be measured by your opponents' records or by their opponents' opponents' records? Every choice is a philosophical position disguised as a coefficient.

The Omnivore Rankings were retrodictive because I believed the right question wasn't "who will win next week" but "what actually happened this season, and who got screwed." I retroactively ranked seasons back to the 1990s because I wanted to see if the pattern of mid-major exclusion was systemic or anecdotal. (It was systemic.) I stopped when the CFP arrived because the four-team playoff, and later the twelve-team playoff, reduced the specific injustice the Omnivore Rankings were designed to measure — though it didn't eliminate it.

Viperball is, ultimately, a silly thing. It's a fake sport with fake teams playing fake games in a simulator I built because a Reddit thread made me curious about what football would look like without the forward pass. But the ranking problem it generates is *real*. The math is real. The sparsity is real. The disagreements between systems are real. And because it's simulated, you can do something you can never do with real sports: you can run the experiment again and see if you were right.

If you're the kind of person who spent weekends in 2008 arguing about whether the BCS computers were wrong about Texas — if you've ever opened a spreadsheet to see if your homemade rating system agrees with the AP Poll — if you remember when Massey was a 23-year-old grad student and Billingsley was getting hate mail from Marshall fans and Rothman was treating every team like they'd just arrived from Mars — Viperball might be for you. Not because the sport matters, but because the problem does. And the problem is the same one it's always been: 187 teams, 12 games each, and the question that keeps math nerds up at night.

Who is number one?

---

*The CVL Ranking Composite and full glossary of all 28 systems is available at [viperball.fly.dev/stats](https://viperball.fly.dev/stats). The Viperball rules, game engine, and dynasty simulator are open source.*
