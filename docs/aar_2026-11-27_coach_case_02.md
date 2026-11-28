# COACH-CASE-02 after action record

November 27, 2026. Implemented finite practice and shared formation pairs on the local Cookbook branch at `6952d66`, using the audit of `main` at `ad32c9e`. The working tree also contains the five existing cross code package prototypes. [Policy audit](COACH_CASE_01_POLICY_AUDIT.md) · [Coaching spec](../COACHING_SPEC.md)

## Practice and books

The budget applies to each team's offense and defense independently. It matches the previous total growth of two equally practiced packages. A unit allocates 60 familiarity points after a completed game and 500 during an offseason. One point represents 0.001 familiarity before the cap. Each distinct installed package takes one share regardless of its formation variants. Version 2 books can give a focus package two shares. Unusable packages receive zero points. If none are usable, the allocation records the whole budget as unused. An installed package starts at the existing 0.30 familiarity and can reach at most 1.00. A unit's base school familiarity and coach familiarity continue through their current progression paths.

On a new installation with a computer selected repertoire, the actual caller's identity yields a stable preference for one, two or three packages. The neutral draw favors two packages. Existing fit and familiarity guide retention and adoption. Previously saved installations with no practice policy and version 1 Cookbook assignments keep their fixed growth. New installations created after loading an older save use the current installation rules.

Version 2 books store a content revision, optional practice focus and optional pairs of distinct offensive packages that share a formation. Selecting a book copies the revision into the season or dynasty. The installation exposes ready pairs and familiarity for later selector work. Automatic sequencing and response to opposing calls belong to CASE-03. A package continues to earn a call through the current formation, action and situation constraints.

## Verification

`venv/bin/python -m pytest -q tests` passed 347 tests with 49 dependency deprecation warnings. The final focused rerun passed 37 tests. The regression cases covered allocation, missed personnel requirements, CPU caller changes, version 1 and 2 books, revisions and dynasty persistence. In headless Chromium, the Cookbook accepted two Ghost packages in Tight, saved a practice focus, exported version 2 JSON, restored the controls on import and removed the pair when a package was unchecked. The editor also passed `node --check`.

For a small full engine check, Gonzaga ran Ghost against the identical Alabama roster in Lockdown and Blitz Pack. Each defense and book combination used game seeds 110, 211, 312, 413, 514 and 615, clear weather and a neutral site. Loading the rosters used seed 104. The same staff and school ran both books. The single package was East Coast Quick Kick Chain. The wide book added Heavy Push, Extra Attacker and Vertical Shot. One game interval and one offseason gave each book 560 practice points. The compact package reached 0.86 familiarity, and the four broad packages reached 0.44 each. All selected packages in the traces belonged to the installed book and were eligible on the snap.

| Defense | Book | Distinct packages selected | Selected snaps | Family matches | Package selection entropy, bits | Scrimmage yards per snap | Fumbles lost / kick pass INT / lateral INT |
|---|---|---:|---:|---:|---:|---:|---:|
| Lockdown | Compact | 1 | 53 | 26 | 0.00 | 4.46 | 2 / 26 / 7 |
| Lockdown | Broad | 4 | 48 | 19 | 1.02 | 4.32 | 2 / 27 / 8 |
| Blitz Pack | Compact | 1 | 49 | 24 | 0.00 | 5.83 | 4 / 15 / 7 |
| Blitz Pack | Broad | 4 | 46 | 21 | 1.52 | 6.31 | 5 / 17 / 6 |

The compact book used its core package more often and the broad book used a wider set of answers. Efficiency varied by defense in this sample. The study used one roster matchup per defense and six pairs each. National adoption, long career effects and balance remain part of CASE-VAL.
