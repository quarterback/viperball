# DEF-10 — Defensive package adoption

Status: diagnostic implementation committed; runtime validation pending. Stacked on ENG-01 (#364). No change to package preference weights, eligibility thresholds, pressure physics or scoring.

## Finding

The earlier three-season dynasty study (#344) never installed Exhaustion Press or Robber Coverage. Code inspection shows that package ranking groups all pressure packages under the same pressure preference, and all coverage packages under the same coverage preference (with the same focus bonus). Native-family bonuses and alphabetical tie breaking can therefore decide which of several distinct packages receives one of two coordinator slots. This is a plausible cause of limited adoption, not proof that either unused package should be more common. Roster fit, retained packages and family compatibility also constrain adoption.

## Implementation

Extracted the existing scoring calculation unchanged and shared it with a defensive adoption snapshot. For every defensive catalog ID, the snapshot records compatibility, personnel requirements, whether its situations are evaluable, preference score and rank, installation status, familiarity, and current versus inherited coordinator ownership. The existing dynasty API benchmark records program-level snapshots and league totals for each stage, including zero-installation packages and actual eligible/selected/secondary calls. End-of-season adoption snapshots and full-season call counts are different denominators; do not divide them as though they were a single cohort.

## Next evidence

Run existing regression CI and the dynasty benchmark across independent seeds after ENG-01 validation. Compare qualified-but-not-installed packages, actual eligibility and activation counts; isolate fatigue/protection effects with matched rare-state replay. Only change package selection or execution when the evidence establishes a concrete functional problem. No forced equal adoption, scoring or sack-rate targets. Sack physics, touchdown drift, player generation, fast sim and rulebooks remain with the other agent.

No test results are claimed yet.
