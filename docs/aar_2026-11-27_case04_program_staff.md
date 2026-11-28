# CASE-04 implementation AAR
Branch clinic/case04-program-staff, PR #402. Existing coaching, career, staffing, recruiting, transfer, dynasty and game-day decision systems inspected.

## Implemented
- Program policy derived from existing persistent HC management and adaptability; roster horizon excludes graduates; CPU recruiting adds bounded developmental upside and depth preference (±4%); CPU transfer offers rank immediate roster needs, remaining development runway and scheme fit (±5 score points).
- Dynasty passes actual staff, planned school and roster to transfer ranking and retains policy snapshots. Staff matching adds bounded preference for experienced complementary outside coordinators when an adaptive HC favors innovation.
- Upward learning uses shared recorded seasons and actual caller-attributed evidence with existing six-game/30-per-arm minimum and mentorship annual/lifetime limits; no automatic identity or school replacement.
- Shared pregame HC objectives use known own and opposing school plus existing HC preferences: territory control, transition attack or balanced. Nonneutral plans adapt to late-game score/clock. Existing OC family weights, DC alignment weights and ST field-position/return preferences consume the same side-specific objective. Positive legal weights are adjusted; zero weights remain zero. No new caller, extra players or execution bonuses. Game result records plan and offensive/defensive application counts.
- Technical curriculum derives skill priorities from existing school and caller recruiting preferences and redistributes existing dedicated-teacher instructional weights without increasing their total or the development allowance. Dynasty passes current school configuration into actual development calls. Existing position-teacher slots, retention and succession remain.
- Finite practice allocation is already implemented on overlapping CASE-02/03 PR #398 (60 familiarity points per unit/game, 500 per offseason; no duplicate budget introduced here). Integrate that PR's installation implementation with this branch. CASE-04 neither changes its allocation nor adds free familiarity.

## Files
engine/program_policy.py, engine/coach_career.py, engine/coach_learning.py, engine/recruiting.py, engine/transfer_portal.py, engine/dynasty.py, engine/game_engine.py, engine/position_staff.py, tests/test_program_policy.py, this AAR.

## Verification and integration
Added tests for roster horizon, development vs immediate acquisition, attributable upward learning, shared objective clock behavior and conserved instruction weights. Run python -m pytest tests/test_program_policy.py tests/test_coach_career.py tests/test_coach_learning.py and existing position/recruiting/portal/dynasty and full-engine regression. Tests authored but not executed by this agent. PR #398 overlaps game_engine.py; reconcile both call paths, retain one caller and all existing package/sequence constraints. Other clinic PRs also touch game_engine.py. No new CI workflow. Combined dynasty calibration explicitly assigned to another agent; no duplicate long-run job launched.

## Limits
No rating generation or signing probability changes, no new staff payroll, no automatic same-HC school replacement, no causal interpretation of observational learning, no evidence of real-world numerical coefficients. Upward learning affects HC tactical tendencies when calling; no automatic transfer to autonomous coordinators. Existing succession rules and practice budget reused. Shared objective uses coarse existing game decisions, not a new spatial model; ST preferences are bounded and no independent execution multiplier is added. New program coefficients are candidate policy values requiring integrated calibration. No deployment or merge claim.
