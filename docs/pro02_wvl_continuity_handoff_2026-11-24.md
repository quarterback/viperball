# PRO-02 — WVL owner-mode continuity

Inspection baseline: PR #367 branch claude/rules-drift-sacks-ladder-fastsim. The other agent owns the open-PR merger; this branch adds only new documentation and a diagnostic script so it does not compete for shared engine files.

## Confirmed code paths

- WVLDynasty.run_offseason() loads live rosters, processes retirements, promotion/relegation, free agency, development and cuts; the resulting cards are stored in _team_rosters.
- WVLDynasty.to_dict() persists only owner_roster; from_dict() restores that roster, not all clubs.
- WVLDynasty.start_season() constructs WVLMultiTierSeason from tier assignments and team files, then injects investment modifiers. It does not apply finalized _team_rosters.
- _load_rosters_from_season() replaces the card cache each offseason by converting live Player objects; professional age, contract, career and transaction metadata must be preserved rather than reconstructed from transient player objects.
- WVLCareerLeague is a separate mode with its own durable cards, roster assignments and season history. Do not conflate that with owner-mode persistence or assume a repair in one mode fixes the other.

## Implementation after merger

Persist all club cards in owner-mode saves, preserve old owner_roster saves, and restore authoritative cards into each new season's team objects by stable club key after promotion/relegation. Preserve age, contracts, career identity, free-agent status, investment and depth chart handling. Explicitly reconcile the authoritative card and live game roster rather than overwrite durable metadata. Validate all-club membership, unique IDs, no silent disappearance of players, and distinguish retirements and released players from actual losses. Inspect midseason save/load independently because existing WVL season serializers may intentionally omit heavy box score payloads.

The new scripts/benchmark_wvl_dynasty_continuity.py is a diagnostic acceptance harness for the existing owner engine, not a new CI workflow or a runtime fix. It runs full seasons, checks full-engine regular results and champions, promotion capacity, finalized rosters after file save/load and next season start, and retains JSON partial evidence. Uses a temporary DB and redirects only the WVL dynasty tier-assignment export. This harness is expected to expose the identified defect on the inspected baseline; not executed in this turn. No production implementation or live verification claim.

After the merged baseline is available, run two independent three-season trajectories and add the verified results to the existing integrated release gate. Also check WVL career mode and other professional competitions separately; no scoring or ratings target.
