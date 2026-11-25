# Viperball current development plan
Updated November 25, 2026. Baseline main a6f1660a96a87934651cfcb76bd91ecdc50b89f4. This is the current queue; earlier assessment, handoff, analytics plan and AARs are historical evidence and retain their original statuses. Initial queue reviewed before #385; analytics and portal merged in #385, defender-credit reconciliation merged in #386. Do not reopen work based solely on stale OPEN headings.

## Closed implementation work
- DEF-01–08, CCH-01–06, PBK-01/02/04, VAL-02, DEL-01/02, PEN-01/02, INJ-01, ST-01/02 and STI-VAL: merged #325–361; see assessment and special-teams AARs. DEF-09 sack-rate investigation/tuning, ROST-01, SIM-01 and RULE-01 merged #367; HS regular season intentionally uses fitted quick model, not full engine.
- ENG-01 schedule quota repair #364; DEF-10/10B/10C adoption/fatigue instrumentation #365/366/368; DYNA-01/02 #369/370; VAL-04/05 #371/372; DEF-11 #373; CCH-07 #374; PBK-05 #375; ROST-02/HS-01 #376/377; CCH-08/09, FAT-01, DEF-04/05 #378; VAL-06/CCH-10 #379. Earlier 32-team schedule failure repaired; [all seven jobs passed](https://github.com/quarterback/viperball/actions/runs/45547173141) on pre-position-coach candidate, not current main.
- WEA-02 weather, DEF-12/13 and COACH-FP-01 school/weekly/trait/fingerprint implementation on main (see Nov 25 AAR). BOX-02 #382; Step 7 #383; position coaches/career paths #384. Combined merge resolves overlapping recruiting inputs and plain-season NameError. #384 integrated smoke, national two-season seeds and offense calibration passed on branch; browser test timed out. #383 regression had NameError fixed in combined merge; combined revision not yet verified. Do not conflate merged with calibrated.

## Active work in order
| ID | Work | Status / acceptance |
|---|---|---|
| AN-02 | Versioned score/possession event adapter | Implemented v1; score/drive reconciliation, explicit missing attribution and current candidate validation outstanding |
| EPA-02 | Empirical state value | Implemented experimental possession-exchange model and corpus; held-out acceptance pending |
| EPA-03 | Legal-action alternative values | Implemented observational action comparisons and support gates; causal paired replay and independent acceptance not complete |
| EPA-04 | Delta/bonus decomposition | Implemented conditional context decomposition; causal entitlement value and calibration not complete |
| DTW-02 | Audit/recalibration | Implemented offline symmetric recalibration and ablations; no public DTW change until evidence reviewed |
| AN-03 | National statistical baselines | Implemented national corpus/reporting and historical comparison harness; actual outputs pending |
| AN-VAL | Integrated release gate | Implemented CI gates and two-seed national study; acceptance outstanding |
| AN-UI | Viperball analytics portal | Implemented 13 college views, grouped/raw queries, model coverage, comparisons, CSV and game navigation in #385; UI/engine acceptance pending ([portal AAR](aar_2026-11-25_analytics_portal.md)) |
| VAL-07 | Combined main / long dynasty | Open; 10/20/30-season runs after #383/#384, compare VAL-06 cohort growth, actual STC careers, crossovers, salaries, generated fills, alumni, fit and schedule |
| UI-VAL | Browser regression | Open; #384 browser wait timed out; verify merged main; preserve mobile changes |
| UI-01 / DEL-03 | Remaining game/team/season reporting | Partial; scoring/drive/game-plan/fingerprint displays shipped; audit remaining halftime, weather splits and career/analytics presentation against live surfaces |
| DEF-10 follow-up | Natural rare package adoption/effectiveness | Instrumented; further tuning only if repeated evidence supports it; no forced prevalence |
| ENG-02 | TD/turnover drift | Investigated and tuned in #367 and later school work; monitor current distributions, no automatic scoring target |
| PBK-03 | Additional playbook families | Deferred; new schools now exist; expand only with explicit gameplay need |
| PEN follow-up | Keeper Hunt roughing fouls | Open research from Nov 25 identity AAR; no approved rate change |
| DEP-01 / OPS-01 | Live Fly deployment / release proof | Open; verify deployed revision, game/season/dynasty paths and stats site |

## Ownership and gates
Current analytics implementation follows [the detailed analytics contract](analytics_development_plan_2026-11-24.md). Use current main and existing integrated regression workflow; no duplicate feature workflows. Keep published legacy EPA and DTW distinct from research models; accounting corrections can change statistical credit without changing gameplay. Any remaining estimate, missing event attribution, unsupported counterfactual or failed CI check is explicit. No rule or balance changes in analytics. Record code revision, seeds, corpus sizes, tests and failures in the AAR. Future work should update this plan, not rewrite historical AARs.

Implementation details: [advanced analytics AAR](aar_2026-11-25_advanced_analytics.md). The analytics code is a research candidate; current public EPA/DTW remain unchanged. Final acceptance is not equivalent to merging the code.

## November 25 documentation and accounting follow-up

#385 merged the analytics pipeline and thirteen-view portal. #386 corrects defensive interception/return touchdown and WPA credit, lateral efficiency and timeout reporting; lateral yards remain within rushing. The previous byte-identical trace comparison was removed per the owner; the regression gate now includes box-score credit tests. No national validation or live deployment claim is inferred from either merge. Current user/developer references are indexed in [README.md](README.md). Historical AARs and old plans remain dated evidence.
