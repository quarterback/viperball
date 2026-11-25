# Step 7 AAR: adaptation, recruiting fit and coaching lineage

Date: November 25, 2026. Base: main at 8cd1122ce7115c7518944e196fba4696c7db8781.

## Validation before implementation

Current main already has CCH-08 season-end evidence-based adaptation, CCH-09 career development, role ownership, head-coach management, coaching-tree employment records, and program installation carryover. Do not duplicate these systems. Existing seasonal adaptation requires six attributed games and 30 observations in each comparison arm, uses comparable field/down cells, and caps individual drift. These are descriptive signals, not causal estimates.

The missing links found in code:
- The coaching tree records actual shared seasons and influences hiring and installation familiarity, but does not transfer a coach's tactical preferences to an assistant.
- CPU recruiting ranks stars, true overall, geography and depth; it does not use the school's or actual calling coach's skill priorities.
- The dynasty season-start endpoint reselects CPU schools with a new seed every year, even with unchanged staff. A school-specific recruiting policy would therefore be inconsistent with next year's game plan.
- The interactive API and the engine's standalone recruiting cycle are distinct paths and both must receive staff and school inputs.

## Implemented policy

1. Retain the existing evidence-based seasonal learning. Add a separate, persistent mentorship adjustment to the OC's kick-pass mix or the DC's pressure preference. It requires a recorded shared season with a relevant HC specialist and scales with adaptability and stubbornness. Maximum shift 0.005 per season and 0.025 in either direction over a career. No identity, player attribute, or rating changes. Assistants retain their own base signature when promoted or hired elsewhere. Mentor history survives moves and saves. Existing base tactical clamps still apply.
2. Add a CPU target-ranking fit factor based on role-specific skill specialization relative to the prospect's own mean. School and actual calling coach preferences are combined (65% school, 35% caller when both address the same position; delegation scales caller influence). At most +/-8% of the existing targeting score; stars, depth, geography and NIL allocation rules remain authoritative. Fit can change the order of similarly qualified candidates, not grant a recruit more talent. No new recruit data, extra scholarships, forced signings or changes to user-controlled boards. This uses the AI path's existing access to true ratings.
3. Plan the next CPU school's base scheme once at the end of the coaching carousel and store it in existing serialized coaching history. Retain prior schemes with the same HC or a successor who worked under that HC. An external specialist HC may switch their own side to a compatible existing school; the other side and special-teams choice remain stable. Invalid or removed engine scheme keys fall back to ordinary setup. The same plan is used in recruiting and next-season setup. Human scheme decisions remain manual. New programs without history retain normal initial assignment.
4. The existing dynasty integration benchmark verifies opening-school parity, bounded mentorship across employment transitions, one mentor event per coach/year, plan coverage, and signed-recruit fit distribution. It continues checking roster identities, save/load continuity, and existing coaching/installation invariants.

## Verification and limits

Focused regressions cover school-specific rank reversal at equal recruit quality, superior talent remaining favored, neutral legacy behavior, shared-season mentorship, stubbornness, save/load, and same-HC/internal versus external succession. Extend the existing full-engine dynasty study, rather than introduce a separate workflow. Actual balance, multi-season scheme distributions, and fit impact need the existing multi-seed CI evidence. No full local test run is claimed; the local runtime cannot reach GitHub. Hold the PR for CI and integration with the concurrent coaching/playbook work.

The school-to-skill maps and bounds are proposed calibration values, not measured estimates. Fit affects CPU recruiting offers and NIL targeting, not the recruit's signing preference formula, transfer market, player development rates or game-day ability. Existing learning is limited to kick-pass mix and pressure, not an unrestricted rewrite of offensive finish or defensive decisions. In-game and weekly adjustments remain in their existing systems; no new play-resolution or engine rules in this step. The other agent's active playbook work should be reconciled against the school maps before merge if scheme identifiers change.
