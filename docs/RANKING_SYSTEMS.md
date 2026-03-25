# CVL Ranking Composite: 38 Systems Glossary

The CVL Ranking Composite runs **38 independent ranking algorithms** against the same season of game results, inspired by Kenneth Massey's college football ranking composite. Each method produces its own 1-to-N team ordering. The composite ranking is the average rank across all methods — and the **variance between systems IS the product**.

A team ranked #3 by every single method is a consensus top team. A team ranked #1 by half the methods and #40 by the other half is the most controversial team in the league. Both facts are interesting.

---

## How to Read the Grid

| Column | Meaning |
|--------|---------|
| **Composite** | Average rank across all methods (lower = better) |
| **Median** | Middle rank across all methods (robust to outlier systems) |
| **Std Dev** | How much methods disagree about this team (high = controversial) |
| **Individual columns** | Each team's rank in that specific system |

---

## Core Math (6 systems)

These are the foundational algorithms used by real-world ranking composites.

### 1. Elo Ratings (`elo`)
**What it measures:** Overall team strength, updated game-by-game.

Every team starts at 1500. After each game, the winner gains rating points and the loser drops. The amount depends on (a) how surprising the result was and (b) the margin of victory. Beating the #1 team gains more than beating the #200 team. Blowing out a weak team is dampened so you can't farm rating points.

*Based on:* Chess Elo system, adapted by FiveThirtyEight for NFL. Home field advantage = 50 Elo points.

### 2. Colley Matrix (`colley`)
**What it measures:** Pure winning ability, opponent-adjusted.

The only system that completely ignores score margins — a 1-point win counts exactly the same as a 50-point blowout. Solves a matrix equation where your rating depends on your W-L record relative to how your opponents performed. No preseason bias.

*Based on:* Wesley Colley's BCS-era algorithm (colleyratings.com). Was one of the six computer rankings used by the BCS.

### 3. Massey Ratings (`massey`)
**What it measures:** Expected scoring margin vs an average team.

Uses least-squares regression to find the rating for each team such that the predicted margin (home rating - away rating) best fits actual game margins. Margins are capped at 21 points to prevent blowouts from distorting ratings.

*Based on:* Kenneth Massey's original rating system (masseyratings.com).

### 4. Bradley-Terry / MOV (`bt`)
**What it measures:** Pairwise win probability between any two teams.

A probability model: "If Team A played Team B again, who would win?" Uses margin of victory to estimate the true probability of each outcome, then iterates to find ratings consistent with all observed results. A team with rating 2.0 is expected to beat a team with rating 1.0 about 67% of the time.

*Based on:* Bradley-Terry model, extended with Wobus margin-of-victory weighting.

### 5. Strength of Record (`sor`)
**What it measures:** How impressive is this team's record given their schedule?

Simulates a generic top-25 team playing each team's exact schedule 1,000 times. If a top-25 team would get your record or worse only 5% of the time, your SOR is 0.95 — meaning your record is very hard to replicate. Rewards teams with tough schedules and strong records.

*Based on:* ESPN/College Football Playoff committee's SOR concept.

### 6. Simple Rating System (`srs`)
**What it measures:** Points better/worse than average, schedule-adjusted.

`SRS = average margin + average opponent SRS`. A team with SRS +10 is expected to beat an average team by 10 points. Iterates until convergence. Centered at 0 (league average).

*Based on:* Pro-Football-Reference SRS, used extensively in NFL analytics.

---

## Simple (4 systems)

Transparent, easy-to-explain metrics that anyone can compute with a calculator.

### 7. Win Percentage (`win_pct`)
**What it measures:** Raw winning rate.

`Wins / (Wins + Losses)`. The simplest possible ranking. Ties count as half a win. Doesn't care about margin, schedule strength, or anything else. A 10-2 team in a weak conference outranks an 8-4 team in a murderer's row.

### 8. Point Differential (`point_diff`)
**What it measures:** Average scoring margin per game.

`(Points Scored - Points Allowed) / Games Played`. Teams that outscore opponents by 15 per game rank above teams that win by 3. No schedule adjustment — a +20 margin against cupcakes counts the same as +20 against contenders.

### 9. Pythagorean Expectation (`pythag`)
**What it measures:** Expected win% based on scoring efficiency.

`PF^exp / (PF^exp + PA^exp)` with exponent 2.37. Originally from baseball (Bill James), adapted for football. A team that scores 30 and allows 20 per game has a Pythagorean expectation of ~0.69 — they "should" win about 69% of games. Teams that overperform their Pythagorean are often lucky; underperformers are often unlucky.

### 10. SOS-Adjusted Win% (`sos_win_pct`)
**What it measures:** Win% scaled by schedule difficulty.

`Win% * (Average Opponent Elo / 1500)`. A team that goes 10-2 against opponents averaging 1600 Elo scores higher than a team that goes 10-2 against opponents averaging 1400 Elo. Simple schedule-aware winning rate.

---

## Elo Variants (2 systems)

Different lenses on the same Elo framework.

### 11. Recency-Weighted Elo (`elo_recent`)
**What it measures:** Current form, weighting recent games 2x.

Same algorithm as standard Elo, but the K-factor doubles for games in the second half of the season. A team that starts 2-4 but finishes 6-0 will be rated much higher by Recency Elo than by standard Elo. Captures late-season momentum and improvement.

### 12. Round Robin Win% (`round_robin`)
**What it measures:** Expected record if you played every team once.

For each team, compute the Elo-based expected win probability against every other team in the league. Average them all. This answers: "If the season were a pure round-robin, what would this team's expected winning percentage be?" Filters out schedule imbalance entirely.

---

## Resume / Context (2 systems)

These rank teams by the quality of their actual results, not predicted ability.

### 13. ISOV — Iterative Strength of Victory (`isov`)
**What it measures:** Quality of teams you've beaten, recursively.

Your rating = the average rating of the teams you've beaten. But *their* ratings also depend on who *they* beat. Iterate until convergence. Beating a team that beat a team that beat the #1 team cascades upward. Teams with no wins get rating 0.

*Based on:* Kislanko's ISOV method.

### 14. Resume Index (`resume`)
**What it measures:** Quality wins minus bad losses.

Scores each win and loss by the opponent's Elo tier:

| Win vs | Points | Loss to | Penalty |
|--------|--------|---------|---------|
| Top 5 | +10 | Top 25 | -0.5 |
| Top 10 | +7 | Top 50 | -2 |
| Top 25 | +4 | 50-100 | -3 |
| Top 50 | +2 | Below 100 | -5 |
| Top 100 | +1 | | |

A team with two top-5 wins and one bad loss scores `20 - 5 = 15`. Pure resume evaluation.

---

## Efficiency (3 systems)

How well does a team execute, independent of wins and losses?

### 15. Offensive Efficiency (`off_eff`)
**What it measures:** How good is the offense across multiple dimensions?

Composite of three normalized components:
- **40%** Points Per Drive (PPD) — scoring efficiency
- **30%** Conversion Rate — 3rd/4th/5th/6th down conversion %
- **30%** Explosive Plays — plays gaining 15+ yards

Each component is min-max normalized across the league (0-100 scale), then weighted and combined. *Requires season stats.*

### 16. Defensive Efficiency (`def_eff`)
**What it measures:** How good is the defense across multiple dimensions?

Composite of three normalized components:
- **40%** Stop Rate — inverse of opponent PPD (lower opp PPD = better)
- **30%** Turnovers Forced — total season takeaways
- **30%** KILL% — penalty kill scoring rate from DYE (scoring when delta-penalized)

*Requires season stats.*

### 17. FPI-Style EPA (`fpi`)
**What it measures:** Efficiency per play, adjusted for schedule.

EPA (Expected Points Added) per play, multiplied by a schedule-strength modifier: `epa_per_play * (1 + 0.1*(avg_opp_elo - 1500)/100)`. Teams that are efficient against strong opponents get a boost. Teams efficient only against weak opponents get discounted.

*Based on:* ESPN's Football Power Index concept. Requires season stats.*

---

## Viperball-Specific (3 systems)

Metrics unique to Viperball's delta yards system and game mechanics.

### 18. Delta Yards Index (`dye_index`)
**What it measures:** How well does a team handle the delta yards system?

In Viperball, leading teams start drives further back (penalty kill) while trailing teams get field position bonuses (power play). This composite measures:
- **40%** PK Efficiency — yards per drive when penalized vs baseline
- **30%** Mess Rate (inverted) — gap between PP and PK scoring rates (lower = more consistent)
- **30%** Wins Despite Penalty — games won while serving delta penalty

*Requires season stats.*

### 19. Comeback Success Rate (`comeback`)
**What it measures:** Resilience when trailing.

Computed from game quarter scores: what percentage of games where the team trailed at halftime did they come back to win? Combined with DYE power play scoring rate (how often they score when given field position bonuses while trailing).

`0.6 * comeback_win_rate + 0.4 * power_play_score_rate`

Teams that never trail at halftime get full comeback credit (dominance bonus).

### 20. Margin Compression MOV (`margin_comp`)
**What it measures:** Average margin with blowout dampening.

For each game: `sign(margin) * ln(1 + |margin|)`. A 3-point win = 1.39, a 10-point win = 2.40, a 40-point win = 3.71. Blowouts get diminishing returns — a 40-point win is only ~2.7x more valuable than a 3-point win, not 13x. Smoother than Massey's hard truncation.

---

## Controversial / Opaque (3 systems)

These are deliberately non-transparent. Part of the fun is that nobody fully agrees with them.

### 21. Billingsley (`billingsley`)
**What it measures:** Chain-based rating inheritance.

When you beat a team, you absorb a fraction of their rating. When they beat someone, that cascades to you. Processed in game order, so early-season wins cascade more than late-season wins. The system is path-dependent and opaque by design — small changes in game order produce different rankings.

*Based on:* Richard Billingsley's BCS-era computer ranking.

### 22. Dokter Entropy (`entropy`)
**What it measures:** Consistency of results via information theory.

Builds a histogram of each team's game margins (binned by 7 points). Computes Shannon entropy of the distribution. Lower entropy = more predictable outcomes. Combined with win%: `win_pct / (1 + entropy)`. A team that wins every game by 10-17 points has low entropy and ranks high. A team that alternates blowout wins and close losses has high entropy and ranks lower.

### 23. PageRank (`pagerank`)
**What it measures:** Authority in the win/loss graph.

Treats teams as web pages. Each win creates a "link" from the loser to the winner. Applies Google's PageRank algorithm (damping = 0.85). Teams beaten by highly-ranked teams pass more authority to their conquerors. Creates cascading credibility — beating a team that everyone else also beats isn't worth much.

---

## Sagarin-Style (2 systems)

Inspired by Jeff Sagarin's dual-component rating system.

### 25. Sagarin Predictor (`sagarin_pred`)
**What it measures:** Pure points prediction without margin limits.

Identical to Massey Ratings but with NO margin cap. A 50-point blowout counts at full value. This is the "predictive" component — it tries to predict the actual score of future games. Rewards dominant teams, punishes teams that lose big.

### 26. Sagarin Recent (`sagarin_recent`)
**What it measures:** Score-margin ratings with recency emphasis.

Massey-style least-squares but with exponential time decay. The weight of each game grows as `2^(game_index / total_games)` — the last game of the season is weighted about 2x the first game. Captures trajectory: a team improving throughout the season will rate higher than their full-season Massey suggests.

---

## Meta (2 systems)

### 24. CFQI — Team Coefficients (`cfqi`)
**What it measures:** Expected margin vs an average team, conference-adjusted.

Like SRS but with two modifications: (a) game margins are capped at 21 points (prevents blowout farming), and (b) a small conference-strength bonus is applied based on the non-conference win% of all teams in your conference. Being in a strong conference provides a slight boost.

*Based on:* College Football Quality Index v2 methodology.

### 27. Game Control (`game_control`)
**What it measures:** Average share of game time spent in the lead.

Computed from per-quarter cumulative scores. Each quarter where a team leads counts as 25% game control. Tied quarters split. A team averaging 0.80 game control dominates most of their games. A team averaging 0.50 plays close games. Rewards wire-to-wire dominance over comeback-dependent wins.

---

## Eigenvector / Graph Methods (3 systems)

These use eigenvector decomposition or graph-theoretic models on the game network, distinct from PageRank and the core math systems.

### 29. Keener Ratings (`keener`)
**What it measures:** Team strength via the dominant eigenvector of a scoring-ratio matrix.

Builds an n×n matrix where entry A[i][j] is the Laplace-smoothed fraction of total points team i scored against team j: `(score_i + 1) / (score_i + score_j + 2)`. Unlike PageRank (binary win/loss links), Keener uses *how much* you won by in a continuous way. A 35-7 win contributes differently from a 14-10 win. Power iteration finds the dominant eigenvector.

*Based on:* James Keener, "The Perron-Frobenius Theorem and the Ranking of Football Teams", SIAM Review, 1993. One of the foundational academic sports-ranking papers.

### 30. Offense-Defense Rating (`od_rating`)
**What it measures:** Overall team quality by decomposing into separate offense and defense ratings.

Iteratively solves: offense[i] = Σ(points scored against j / defense[j]) and defense[i] = Σ(points allowed from j / offense[j]). Scoring against a bad defense (high d) earns less credit. Allowing points from a bad offense (low o) is more damning. Overall rating = offense / defense. The only system that decomposes O/D from game results alone.

*Based on:* Amy Langville & Carl Meyer, "Who's #1?", Princeton University Press, 2012.

### 31. Markov Random Walker (`markov_walker`)
**What it measures:** Prestige through breadth of quality victories — the mathematical dual of PageRank.

In PageRank, links go from losers to winners (authority flows upward). Here, the walker moves from a team to teams they *beat*. The stationary distribution rewards "gateway" teams with many wins against well-connected opponents. A 1-11 team that upset the champion ranks HIGH in PageRank but LOW here. An 11-1 team beating mediocre opponents ranks LOW in PageRank but HIGH here.

---

## Eclectic Methods (3 systems)

Philosophically distinctive approaches that don't fit neatly into any other category.

### 32. Least Violations (`least_violations`)
**What it measures:** The ordering of teams that best explains the observed results.

Searches for the ranking where the fewest upsets occur (a lower-ranked team beating a higher-ranked team). This is NP-hard in general; the algorithm uses greedy hill-climbing with adjacent-pair swaps starting from a win-percentage ordering. The *only* combinatorial optimization method in the composite — every other system computes ratings and derives ranks; this one directly searches for the best ordering.

### 33. Truncated Colley (`truncated_colley`)
**What it measures:** Current form via Colley Matrix on only the last 4 games per team.

Runs the standard Colley Matrix method but only considers each team's most recent 4 games. A team that started 0-4 but finished 4-0 will diverge wildly from full-season Colley. Unlike Recency Elo (which is sequential), this is a simultaneous matrix method — everyone's recent-form rating depends on everyone else's.

### 34. Win-Score Accumulator (`win_score`)
**What it measures:** Strength of victories in a deliberately naive, non-iterative way.

Each winner gets credit equal to the losing team's win percentage. Beat a .833 team → get 0.833 points. No iteration, no matrix, no convergence — just one pass through the results. The "naive scout" counterpoint to sophisticated iterative methods. Disagrees sharply when transitive chains create cycles (A beats B beats C beats A).

---

## Published Methods (3 systems)

Well-known published ranking systems from sports analytics literature.

### 35. LRMC (`lrmc`)
**What it measures:** Team strength via a Markov chain with logistic-regression transition probabilities.

Builds a Markov chain where the probability of transitioning from team i to team j is proportional to i's probability of losing to j (estimated via logistic function on score differentials). The stationary distribution rates teams — those that are hard to transition away from (hard to beat) accumulate mass. Different iterative structure from Massey/Colley because it uses nonlinear logistic modeling.

*Based on:* Kvam & Sokol, "A Logistic Regression / Markov Chain Model for NCAA Basketball", 2006. Popular in college basketball analytics (Georgia Tech group).

### 36. Park-Newman (`park_newman`)
**What it measures:** Team strength via maximum likelihood on the game network topology.

A generalized Bradley-Terry model that weights pairwise contributions by the number of games between each pair and uses network-aware normalization. Iterative fixed-point: π_i = Σ(wins_ij) / Σ(games_ij / (π_i + π_j)). More principled than standard BT when some pairs play multiple times and the schedule is unbalanced.

*Based on:* Park & Newman, "A Network-Based Ranking System for US College Football", JASA 100(472), 2005.

### 37. Anderson-Hester (`anderson_hester`)
**What it measures:** Team quality using only wins, opponent win%, and opponents' opponents' win%.

Rating = 0.25 × WP + 0.50 × OWP + 0.25 × OOWP. Purely wins-based — no margins of victory at all. OWP excludes games against the team being rated (so you can't pad your opponents' records). The formula used by the old Seattle Times BCS computer poll. Historical significance in the BCS era.

### 38. MJS Standings (`mjs`)
**What it measures:** Team quality via win percentage plus iterative strength of schedule.

Rating = win_pct + SOS, where SOS = 0.7 × (avg_opponent_rating − 0.5). This is iterative because each opponent's rating includes their own SOS. A positive SOS means the schedule is harder than average. The 0.7 coefficient prevents SOS from dominating win percentage. The formula used by the MJS College Football Standings, a published BCS-era computer ranking system.

---

## Conference Rankings

The composite includes **conference rankings** in the same style as the Massey Composite. For each ranking method, conferences are ranked by the average team rank within that conference. A conference whose teams average rank #15 across all its members is stronger than one averaging #50. The conference composite rank is the average of all per-method conference ranks — and like the team grid, disagreement between methods reveals which conferences are controversial.

---

## Pass-Through (1 system)

### 28. CVL Official (`cvl_official`)
**What it measures:** The existing CVL Power Index.

This is the league's official ranking formula, included as one more column in the grid for comparison. It uses: Win% (40 pts), SOS (15 pts), Quality Wins (20 pts max), Non-Conference Record (10 pts), Conference Strength (5 pts), Point Differential (10 pts), minus bad-loss penalties.

---

## The Composite

The **Composite Rank** is each team's average rank across all available methods. The **Median Rank** is the middle value (more robust to a single system being an outlier). The **Standard Deviation** measures how much the systems disagree.

**Key insight:** When all 38 systems agree a team is #1, they're #1. When Elo says #3 but Colley says #40 and Resume says #1, that team is *interesting* — and the disagreement tells you something real about their profile.

### Which systems need season stats?

Most systems (33 of 38) run from game results alone. Five require season-level statistics passed in separately:

| System | Why it needs stats |
|--------|-------------------|
| Offensive Efficiency | PPD, conversion %, explosive plays |
| Defensive Efficiency | Opponent PPD, turnovers forced, KILL% |
| FPI-style EPA | EPA per play |
| Delta Yards Index | PK efficiency, mess rate, penalty wins |
| CVL Official | Power Index value from season engine |

Comeback Success Rate and Game Control prefer per-quarter scores from game data but fall back to season stats if quarter data isn't available.
