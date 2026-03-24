# The Nerdiest Problem in Sports (And Why a Fake Sport Might Be the Best Version of It)

In 2007, I got my name on a list.

Not a prestigious list. Not a list anyone outside a very specific corner of the internet would care about. Kenneth Massey — a math professor at Carson-Newman University in Tennessee — maintains a website called the Massey Ratings Composite. It tracks every known computer ranking system for college football. When I started watching, there were maybe 60 or 70 systems on the list. By the time I stopped, there were over 100.

My system was called the **Omnivore Rankings**. It was on that list from roughly 2007 to 2014. And its purpose was not to determine who was "the best team in college football."

The Omnivore Rankings were **retrodictive** — they looked backward. The goal was to evaluate what actually happened, not to predict what would happen next. And the specific thing I was interested in was a question nobody else seemed to be asking: **who is the best mid-major team, and could they be a national champion?**

That question — not "is Alabama better than Oregon" but "is Boise State actually elite or are they just feasting on a weak schedule" — is what sucked me into the whole thing. And it's the same question that has sucked in hundreds of math nerds for decades.

---

## The Problem That Won't Stay Solved

In 2012, the New York Times ran a piece about the proliferation of college football computer rankings. The headline framed it as a quirky hobby story — "Rankers by the Dozen Ask the No. 1 Question" — but buried in the article was something more interesting. Jon Dokter, an astronomy professor who'd been running his Entropy System since 1993, explained why college football specifically attracts this kind of obsessive ranking behavior:

> "The bowl system not producing an official national champion, the small number of games. Unlike most other sports, college football teams can only play about 10 percent of all other teams in a given year; that necessitates the power ranking."

That's the core of it. In the NFL, every team plays 17 games and eventually meets in the playoffs. In MLB, you play 162 games. The cream rises. But in college football, you have 130+ teams playing 12 games each, mostly against teams in their own conference, and then you have to figure out whether the team that went 12-0 in the Sun Belt is better than the team that went 10-2 in the SEC. You literally cannot know, because they never played each other and they share almost no common opponents.

It's an **incomplete information problem**. You're trying to infer a total ordering of 130 teams from a sparse graph of ~800 games. There is no unique solution. Every ranking system is making assumptions about what matters — wins vs. margins, schedule strength vs. raw performance, recent form vs. full-season body of work — and those assumptions produce meaningfully different answers.

Kenneth Massey, whose composite tracks all of these systems, put it simply: "It's kind of a nerdy hobby. It combines sports with math and computers, three things that don't ordinarily go together."

But here's what the Times article didn't quite get into: the ranking problem isn't just nerdy. It's **genuinely hard mathematics**. The same linear algebra and graph theory that power Google's PageRank algorithm are the same tools people use to rank football teams. Jeff Sagarin's work has been applied to tax policy and presidential politics. The American Statistical Association publishes an entire journal — *The Journal of Quantitative Analysis in Sports* — dedicated to this stuff. When Soren Sorensen, a physics professor at Tennessee, described his system, he warned that "it is not easily explainable to people who have not had linear algebra."

The BCS used six computer systems to help determine its championship game matchup. The NCAA famously prohibited those systems from using margin of victory, which Sagarin called out directly: "When you throw away the scores, you're throwing away a huge amount of important information." His BCS-compliant system — the one that ignored margins — had Alabama at number three. He knew it was wrong. The NCAA didn't care. "They love the cliché 'a win is a win,'" he said, "which to me is one of the most vapid clichés of all time."

The College Football Playoff has mostly killed the urgency of the debate. But the mathematical problem hasn't gone away. It's just moved underground, to the people who do it because the problem itself is beautiful.

---

## A Fake Sport With a Real Math Problem

I built Viperball as a game — a collegiate dynasty simulator for a sport that never existed. It started from a Reddit thread about what modern football would look like if the forward pass had never been invented. The game has 187 women's collegiate teams, no forward passing, six different ways to score, and a rubber-band mechanic called the delta yards system that punishes leading teams with worse field position.

I did not build it to be a ranking problem. But it turns out I accidentally built the *perfect* ranking problem.

Here's why.

**The sparsity problem is identical.** 187 teams play 12-game schedules. They're organized into conferences. They mostly play each other. The playoff takes 16 teams. You have to figure out who those 16 should be from a graph where each team has played fewer than 7% of the league. It's the exact same structural problem as real college football.

**But the scoring is way more interesting.** Viperball has a six-channel scoring system:

| Score | Points |
|-------|--------|
| Touchdown | 9 |
| Snap Kick (drop kick) | 5 |
| Field Goal (place kick) | 3 |
| Safety | 2 |
| Pindown | 1 |
| Bell (loose ball recovery) | 0.5 |

A team that wins 45-40 by scoring five touchdowns has a completely different profile than a team that wins 45-40 by mixing three touchdowns with six snap kicks and a few pindowns. The margin is the same. The *meaning* of the margin is not. This is something real football ranking systems never have to deal with — in the NFL, a point is a point. In Viperball, you have to decide whether multi-channel scoring efficiency is more informative than raw margin.

**The delta yards system breaks traditional assumptions.** In Viperball, when you're winning, the game gets harder. Leading teams start their drives further back on the field — the larger the lead, the worse the starting position. Trailing teams get the opposite boost. This means a 20-point blowout in Viperball is *more impressive* than a 20-point blowout in real football, because the winning team was fighting a field position penalty the entire second half. It also means close games aren't necessarily indicative of evenly matched teams — the delta system *compresses* margins by design.

Every existing ranking methodology has to be rethought. Massey's least-squares regression on margins? You need to account for the fact that margins are mechanically compressed. Elo's margin-of-victory K-factor? The same margin means different things depending on how much delta penalty the winner absorbed. Pythagorean expectation? The exponent needs recalibration because the scoring distribution is fundamentally different from any real sport.

**You have perfect information.** This is the really interesting part. In real college football, you're working from box scores. You know the final score, maybe the yards, maybe the turnovers. In Viperball, I have every play of every game — every drive, every yard, every decision, every fumble, every delta-penalized possession. I can compute EPA (Expected Points Added) on every single play. I can track which teams score efficiently when penalized by the delta system. I can measure game control quarter by quarter. I can see how teams perform when trailing at halftime.

Real ranking nerds would kill for this data. They have to scrape box scores and estimate. Viperball gives you the complete play-by-play for 1,000+ games per season.

**And you can run it again.** This might be the biggest thing. In real college football, you get one season. Your ranking system either matches the consensus or it doesn't, and you argue about it on message boards for four months. In Viperball, you can simulate a thousand seasons and see which ranking systems are actually *predictive* — which ones correctly identify the best teams before the playoff proves it. You can test your methodology against ground truth in a way that's impossible with real sports.

---

## 28 Systems, One Grid

So I built what Massey built — but for a sport that doesn't exist.

The CVL Ranking Composite runs **28 independent ranking algorithms** against every season of Viperball. Each one produces its own ordering of all 187 teams. The composite is the average rank across all systems. But the composite isn't really the point. **The variance between systems is the point.**

When all 28 systems agree that a team is #1, that team is #1. That's boring. What's interesting is when Elo says #3 and Colley says #40 and the Resume Index says #1. That team is *controversial* — and the disagreement tells you something real about their profile. Maybe they beat everyone they played but their schedule was weak (Colley doesn't care about margins, so it sees the weak schedule; Elo does care about margins, so it rewards the blowouts). Maybe they have three quality wins and two bad losses (Resume loves the quality wins; the math models hate the bad losses).

The systems range from the well-known — Elo, Colley Matrix, Massey Ratings, Bradley-Terry — to the Viperball-specific. The **Delta Yards Index** measures how well teams handle the rubber-band mechanic. The **Comeback Success Rate** tracks win percentage when trailing at halftime combined with power play scoring efficiency. The **Margin Compression MOV** applies logarithmic dampening to blowouts, because in a sport with a built-in equalizer, a 40-point win is logarithmically, not linearly, more impressive than a 10-point win.

There are three systems I deliberately included because they're opaque and controversial — the **Billingsley** (a chain-based system where beating a team means inheriting a fraction of their rating), **Dokter Entropy** (named for Jon Dokter from the Times article, using information theory to reward consistency), and **PageRank** (literally Google's algorithm applied to the win-loss graph). These systems are included *because* they're weird. The composite is richer when it contains systems that see the world differently.

---

## Why This Matters (Or Doesn't, Which Is the Point)

Dokter said something in that 2012 article that's stuck with me: "I would consider sports prediction more difficult than professional research science on the physical world. Predicting sports is one of the hardest things there is."

He's right. And the reason it's hard is that sports contain irreducible randomness. The best team doesn't always win. The ranking problem isn't about eliminating that randomness — it's about building systems that can see through it.

I ran the Omnivore Rankings for seven years because the problem was beautiful. Not because I thought I'd solve it. Not because anyone cared what my system said about Boise State. Because the act of building a ranking system forces you to articulate what you believe about competition. Do you believe margins matter? Do you believe recent games are more informative than early-season games? Do you believe schedule strength should be measured by your opponents' records or by their opponents' opponents' records? Every choice is a philosophical position disguised as a coefficient.

Viperball is, ultimately, a silly thing. It's a fake sport with fake teams playing fake games in a simulator I built because a Reddit thread made me curious about what football would look like without the forward pass. But the ranking problem it generates is *real*. The math is real. The sparsity is real. The disagreements between systems are real. And because it's simulated, you can do something you can never do with real sports: you can run the experiment again and see if you were right.

If you're the kind of person who spent weekends in 2008 arguing about whether the BCS computers were wrong about Texas — if you've ever opened a spreadsheet to see if your homemade rating system agrees with the AP Poll — Viperball might be for you. Not because the sport matters, but because the problem does. And the problem is the same one it's always been: 187 teams, 12 games each, and the question that keeps math nerds up at night.

Who is number one?

---

*The CVL Ranking Composite and full glossary of all 28 systems is available at [viperball.fly.dev/stats](https://viperball.fly.dev/stats). The Viperball rules, game engine, and dynasty simulator are open source.*
