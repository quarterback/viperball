# ENG-01 — Schedule fulfillment

Status: implementation committed; regression and API dynasty validation pending. Base: main 6d106f70. No scoring, sack-rate or tactical coefficient changes.

## Cause and correction

The prior scheduler's second nonconference fill accepted a pairing whenever either school was short, permitting over-quota opponents. Its cleanup handled only a particular two-overfull case. Greedy matching could also strand short teams. The replacement never adds a game above quota, adds direct missing matchups where possible, and repairs deficits by replacing one unprotected game with two legal games. With multiple conferences, the repair preserves existing conference games and adds only nonconference games. Pinned games and rivalries cannot be removed. A warning names residual shortfalls instead of manufacturing opponents or exceeding quotas. This bounded repair is not a general proof of feasibility for arbitrary protected matchups or conference structures.

## Validation

Added focused tests for reduced two-conference dynasties, unconferenced schedules, protected home/away selection and odd-degree shortfalls. The existing dynasty API benchmark now checks quotas, duplicate pairs and weekly double-booking before simulation. Tests have not yet run in this editing environment. Run the existing Python regression and multi-seed API dynasty benchmark before marking ENG-01 complete.

## Agent coordination

User assigned touchdown/turnover drift, sack rate, talent ladder/player generation, fast simulation, and rulebooks to the other agent. Do not duplicate them. There is no target touchdown count, final score, or imported football sack-rate requirement. This track owns schedule fulfillment, dynasty continuity, natural defensive package adoption and deployment verification. Coordinate any shared event schema changes with analytics agents. Open a PR for every completed implementation batch; do not wait for a separate instruction to do so.
