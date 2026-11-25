# VAL-05 — Combined college engine validation

Baseline: main 49d3a1d832b32bfd741cdc3d464afe2946e742ec, after the other agent merged #367 and #364–370. This work is college-only; professional and international work is deferred.

The prior national study (#370, workflow 45500633089) completed 4,924 games on its own branch, with 162,097 defensive-package calls, 1,623 recruits and 464 coaching hires. All 13 packages were naturally installed by year two. Exhaustion Press had 203 calls and Robber Coverage 66. This is historical comparison evidence, not validation of the merged engine.

Reuse existing integrated CI. Run three reduced-league three-season trajectories, rare tactical replays and two independent national two-season trajectories. Preserve schedule, player identity, roster, playoff and database gates. The national job follows successful reduced validation. Explicit manual national dispatch also runs the reduced and rare studies first. Record class-level rating distributions and positional counts as descriptive evidence for ROST-02. No gameplay changes, scoring targets or forced package usage.

Next after results: DEF-11 package preferences on the merged rating and officiating baseline; CCH-07 coaching continuity; PBK-05 offensive package diversity; ROST-02 college roster development; HS-01 recruiting continuity only insofar as college rosters are affected. Analytics remains a separate track. Live deployment remains unverified.

Status: implementation committed; combined run pending. No successful merged-baseline result claimed yet.
