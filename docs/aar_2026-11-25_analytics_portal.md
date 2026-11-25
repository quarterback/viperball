# Viperball analytics portal — November 25, 2026

User direction: reference-style analytics in the game menu, drawing particularly on Baseball Savant, alongside FanGraphs and Pro Football Reference. New simulations are the target; no historical-save migration is required.

## Research and design decisions

- [Baseball Savant Statcast Search](https://baseballsavant.mlb.com/statcast_search): event-level queries, combined situational filters, grouping, minimum observations and selectable columns. Adapted as Play finder and Drive finder; no baseball metrics imported.
- [Baseball Savant custom leaderboards](https://baseballsavant.mlb.com/leaderboard/custom) and [comparison tool](https://baseballsavant.mlb.com/changelog/2026-07-20-player-comparison-tool): customize tables, compare peer percentiles, expose actual values and sample qualification. Adapted to team and position-matched player comparisons.
- [FanGraphs splits tools](https://blogs.fangraphs.com/updated-splits-leaderboards-and-splits-tools-are-here/): separate statistics by purpose and let users examine context. Adapted as dedicated scoring, EPA, decision, Delta and DTW views.
- [Pro Football Reference advanced statistics](https://www.pro-football-reference.com/years/2026/advanced.htm): compact sortable league reference tables, team/player navigation and separate metric categories. Preserve the current Viperball site shell and familiar data-table presentation.

## Delivered

College season Analytics opens the portal overview; game box scores link directly to the corresponding play and drive query. Thirteen views: overview, player and team leaderboards, scoring, expected points, decision value, Delta/bonus, DTW, play and drive finders, team and player comparison, glossary. Filters include team/opponent, conference, week, postseason scope, down, distance, field zone, margin, outcome, play family, schools, pressure and restart context where applicable. Query results support group-by, sortable columns, pagination and CSV. Raw event links use the actual game route; team/player links use existing profiles. Heatmap cells show down/field-zone net points with sample counts. Percentile comparison uses real qualified peers and direction-specific metrics.

Observed statistics are computed from completed live-session games and reconciled score events, not placeholder datasets. Whole-season player tables reuse the existing aggregation. The model is season-local: earlier regular-season games train a bounded sampled model, separate earlier games train the retrospective DTW candidate, later games are held out. It uses the AN-02–EPA-04 implementation in this PR; it is not a national pretrained model or a validated causal action evaluator. Unknown or unsupported values are shown as unavailable. No automatic simulation or coefficient changes. No save migration.

Existing UI smoke is extended to request all portal views, grouped and raw search, CSV, comparison and game drilldowns. Full CI and browser verification are required before declaring release complete. Live deployment is not performed by this PR.
