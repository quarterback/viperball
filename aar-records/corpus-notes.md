# AAR Corpus Notes — viperball

**Parsed:** 2026-06-10

---

## Count

- **Candidate files identified:** 53
- **Records written:** 52
- **Excluded:** 1 (PARSER_INSTRUCTIONS.md — internal parser artifact, not a source document)

---

## Section-Header Frequency Table

Every distinct heading across all 52 records, normalized to lowercase, sorted by document count. This is the schema-derivation data.

| Count | Heading |
|------:|---------|
| 14 | what changed |
| 13 | problem statement |
| 12 | files modified |
| 12 | commits |
| 10 | mission |
| 9 | objective |
| 8 | lessons learned |
| 8 | verification |
| 8 | problem |
| 7 | files changed |
| 7 | root cause analysis |
| 7 | scope |
| 6 | summary |
| 6 | fix |
| 6 | design decisions |
| 5 | work performed |
| 5 | incident / starting state |
| 4 | architecture decisions |
| 4 | what's next |
| 4 | short-term |
| 4 | medium-term |
| 4 | testing |
| 4 | what we did |
| 4 | what went well |
| 4 | what was not changed |
| 4 | changes made |
| 4 | overview |
| 3 | starting state |
| 3 | what worked |
| 3 | what didn't work / risks |
| 3 | immediate |
| 3 | what to watch |
| 3 | integration points |
| 3 | what was built |
| 3 | architecture |
| 3 | issues found & fixed |
| 3 | incident |
| 2 | philosophy |
| 2 | configuration reference |
| 2 | design principle established |
| 2 | test results (20-game batch) |
| 2 | solution |
| 2 | design principle |
| 2 | output |
| 2 | fan usage |
| 2 | architecture notes |
| 2 | the fix |
| 2 | what this enables |
| 2 | known remaining items |
| 2 | testing notes |
| 2 | design rationale |
| 2 | validation |
| 2 | key decisions |
| 2 | what's not done |
| 2 | design |
| 2 | what's not done yet |
| 2 | risk assessment |
| 2 | tier system |
| 2 | interaction with other systems |

---

## Headings Appearing in 2+ Documents With No Schema Field

These headings recur but are not directly captured by any current schema field. Candidates for new schema fields:

| Heading | Count | Notes |
|---------|------:|-------|
| lessons learned | 8 | Appears in 8 documents. Currently lands in `unmapped_content`. High-value retrospective content — recurring enough to warrant its own field. |
| root cause analysis | 7 | Appears in bug-fix AARs. Distinct from `rationale` (why we did it) — this is the technical diagnosis of what was wrong. |
| what went well | 4 | Positive retrospective distinct from validation claims. |
| what to watch | 3 | Forward-looking risk monitoring; currently mapped to `residual_risks` when explicit but often more speculative. |
| integration points | 3 | Describes how the shipped feature connects to other systems. Related to but distinct from `actions`. |
| architecture / architecture decisions | 7 combined | Structural design narrative; currently forced into `actions` or `unmapped_content`. |
| what this enables | 2 | Downstream capabilities unlocked by the work; not quite `open_hooks`. |
| interaction with other systems | 2 | System-level dependency map; currently `unmapped_content`. |
| key decisions | 2 | Explicit decision record section (appears in some docs as a named section rather than inline decisions). |
| design rationale / design principle | 4 combined | Design philosophy/principles established by the work; currently split across `delegation_events` and `unmapped_content`. |
| risk assessment | 2 | More nuanced than `residual_risks` — includes probability and severity estimates. |

---

## Documents With Weakest Quality Vectors

Documents with 3+ false flags (out of 6: has_scope, has_rationale, has_delegation_record, has_validation, has_negative_space, has_residual_risk):

| False flags | Source path | Notes |
|------------:|-------------|-------|
| 5/6 | `docs/AAR_box_score_restructure.md` | Case study genre — no rationale, delegation, validation, negative space, or residual risk |
| 4/6 | `docs/aar_missing_teams_and_rivalry_fix.md` | Data fix — no delegation record, validation, negative space, residual risk |
| 4/6 | `docs/feature_report_analytics_rework_2026_02_25.md` | Feature report — no delegation, validation, negative space, residual risk |
| 4/6 | `docs/AAR_nicegui3x_compatibility.md` | Bug fix — no scope, delegation, validation, negative space |
| 3/6 | `docs/case_study_fiv_world_cup.md` | Case study — no rationale, negative space, residual risk |
| 3/6 | `docs/AAR_diving_wing_case_study.md` | Case study — no delegation, validation, residual risk |
| 3/6 | `AAR_2026-04-07_academic_system.md` | No validation, negative space, residual risk |
| 3/6 | `docs/feature_report_talent_generation_rebalance_2026_03_27.md` | Post-feature report — no delegation, validation, negative space |
| 3/6 | `docs/aar_2026-03-25_talent_generation_balance.md` | No delegation, validation, negative space |
| 3/6 | `docs/aar_2026-03-21_tournament_scoring_awards_postseason.md` | No validation, negative space, residual risk |
| 3/6 | `docs/aar_2026-03-21_pro_league_stats_parity.md` | No validation, negative space, residual risk |
| 3/6 | `docs/aar_2026-03-18_early_down_snap_kicks.md` | No validation, negative space, residual risk |
| 3/6 | `docs/aar_2026-03-16_repeating_downs_early_kicks.md` | No validation, negative space, residual risk |
| 3/6 | `docs/AAR_late_down_defensive_clamp.md` | No delegation, validation, negative space |
| 3/6 | `docs/aar_2026-03-07_mobile_compat_state_persistence.md` | No delegation, validation, negative space |
| 3/6 | `docs/AAR_coaching_integration_fiv_pro.md` | No validation, negative space, residual risk |
| 3/6 | `docs/aar_2026-02-27_history_awards_overhaul.md` | No delegation, negative space, residual risk |
| 3/6 | `docs/AAR_missed_dk_live_ball_returns.md` | No delegation, negative space, residual risk |

---

## Files That Looked Like AARs But Were Excluded

None excluded. All ambiguous candidates were included with `genre_confidence` set:

| File | genre_confidence | Reason for reduced confidence |
|------|-----------------|-------------------------------|
| `RULES_EVOLUTION_AAR.md` | medium | Comparative audit / gap analysis, not a workstream AAR |
| `PROJECT_REPORT.md` | medium | Project report genre |
| `docs/ard_2026-03-27_blowout_backup_rotation.md` | medium | Architecture Decision Record (ADR), not AAR |
| `docs/sitrep_pro_leagues_2026_02_26.md` | medium | SITREP genre |
| `docs/feature_report_2026_02_23.md` | medium | Feature report genre |
| `docs/feature_report_analytics_rework_2026_02_25.md` | medium | Feature report genre |
| `docs/feature_report_talent_generation_rebalance_2026_03_27.md` | medium | Post-feature report genre |
| `docs/feature_report_wvl_galactic_premiership_2026_03_01.md` | medium | Feature report genre |
| `docs/project_report_wvl_owner_mode_upgrade_2026_03_03.md` | medium | Project report genre |
| `docs/case_study_fiv_world_cup.md` | low | Case study genre, no AAR structure |
| `docs/AAR_box_score_restructure.md` | medium | Title says AAR but is a case study format |
| `docs/AAR_diving_wing_case_study.md` | medium | Title says AAR but is a case study format |

---

## Other Observations

- **"What Was Hard" pattern:** Appears in `AAR_2026-05-01_team_chemistry.md` and potentially others. Implementation post-mortem on specific engineering challenges (tuning algorithm, debugging subtle bugs). Not currently captured in schema.
- **Two documents cover the same workstream:** `docs/aar_2026-03-25_talent_generation_balance.md` and `docs/feature_report_talent_generation_rebalance_2026_03_27.md` address the same talent generation rebalance, 2 days apart. The later document adds additional bugs (team_center_offset) and files (development.py, game_engine.py). Parsed as separate records; noted in parser_notes of both.
- **Two date-unknown AARs in root:** `AAR_commissioner_mode.md` and `AAR_ANALYTICS.md` have no date in body (commissioner) or have a date (analytics: 2026-03-22). Wait — `AAR_ANALYTICS.md` date is confirmed 2026-03-22 in its header.
- **"What Was Not Changed" pattern** (4 documents): Explicit section naming what the author deliberately left alone beyond the scope. Related to but distinct from `non_actions` (which are things that could have been done but weren't). Potential schema field.
- **Consistent branch/commit metadata pattern:** Nearly every document records branch name and commit hash(es) in header metadata. Not currently in schema.
- **Commits section** appears in 12 documents as a structured section listing commit hashes with descriptions. Currently mapped to `unmapped_content` or action artifacts. High structural value for traceability.
