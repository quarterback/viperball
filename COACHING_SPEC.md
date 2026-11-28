# Coaching system: current implementation

Source: engine/coaching.py, coach_roles.py, coach_career.py, coach_tactics.py, coach_learning.py, coaching_portal.py, coach_school_continuity.py, position_staff.py, team_installation.py, coach_recruiting_fit.py, and their integration in game_engine.py, dynasty.py, recruiting.py and api/main.py. November 25, 2026.

## Staff and actual callers

| Role | Responsibility |
|---|---|
| Head coach (HC) | Program leadership, delegation, weekly plans, staff and continuity; may call a unit instead of a coordinator. |
| Offensive coordinator (OC) | Offensive calls and packages, tendencies and installation. |
| Defensive coordinator (DC) | Defensive reads, coverage and pre-snap commitments, package selection. |
| Special teams coordinator (STC) | Field-position/return preferences and special-teams tactics. |
| Position coaches | Technical teaching, scouting and personnel evaluation; not independent play callers. |

Coach cards persist attributes, role and contract, personality/tactical signature, history, and career development. The caller is the person who actually controls the unit, not necessarily the nominal coordinator. Delegation and unfamiliar-role readiness constrain influence. Coaching attributes use their own scale; do not apply the physical-player rating conversion to coaches.

## Tactical identity and weekly plans

The program's offensive/defensive school determines base philosophy, separate from the caller's persistent tactical signature and installed situational packages. The HC's six fingerprints (touchdown finish, late-down aggression, run lean, kick-pass lean, lateral lean, turnover caution) adjust play mix and decisions. Weekly defensive plans lean toward a measured counter-school, bounded by adaptability and stubbornness; the defense retains its signature and name. Coaches respond to game context, including score, clock, half, fatigue and weather.

The catalog defines package compatibility, roster requirements and situational eligibility. Familiarity determines execution strength. Defensive calls commit real rushers and coverage participants; pressure and hurry are resolved outcomes, not synonyms for calling a blitz. Offensive package calls and effects are also tracked. See [tactical schools](docs/OFFENSE_SCHEMAS.md).

## Installation and careers

A program retains its practiced book, familiarity and packages across seasons and saves. New staff, scheme switches and roster changes affect installation. Continuity and previous shared employment can preserve familiarity; traces of old tendencies fade. Same-HC and lineage successor retain the planned CPU school; outside specialists may switch their own side. The postseason plan is shared by recruiting and next-season setup.

New installations use a shared package practice budget for each unit. An actual caller has a stable preference for one, two or three catalog packages. The team first retains compatible packages it already knows. Practice points total 60 per game and 500 per offseason for each unit. A formation variant shares the package's familiarity. An optional Cookbook focus gets twice the practice weight of each other eligible package. When the roster fails the focus package's requirements, the other eligible packages divide the budget evenly. Older installations and version 1 Cookbook books use fixed package growth.

Version 2 Cookbook books save an immutable revision in each season or dynasty that selects them. A same look pair stores a common offensive formation and two catalog packages with different actions. The installation exposes the pair when both packages are ready. Each package has its own live call conditions. The team page shows the last game and offseason practice allocations.

## Drive decisions

Installed same look pairs feed the existing formation, family and kick pass selectors in standalone college seasons and dynasties. New computer installations can derive pairs from their compatible packages. A completed probe records the defensive front shown on that snap, which can inform a counter within the next four snaps of that possession. A stacked or aggressive front makes the alternate package a candidate. It must be eligible and pass the caller's authority and familiarity check. The selected action must differ from the probe's family or kick pass subtype. The existing down, kick and clock decisions can take priority. Erased snaps pause the plan and loss of possession clears it.

A caller with a high tempo preference may shave four seconds from the base setup time on an immediate, ready counter after a gain. The clock must be running and an available Zeroback must have enough energy. Existing live action time and clock enforcement determine the actual elapsed time. A play's offensive trace records the actual caller, observed front, available packages, fallback reason and pace. The box score shows those decisions in each snap's **Drive plan** details.

## Season learning

Evidence-based seasonal learning uses actual attributed caller games, comparable contexts, at least six games and 30 observations per comparison arm. Drift is bounded (0.015 annual step, 0.06 lifetime); additional mentorship adjustments require documented shared seasons and are limited to 0.005/year and 0.025 lifetime. These are candidate calibration values, not evidence of universally beneficial adaptation.

## Career paths and staffing

Career intentions are stable draws by coach identity, not annual lotteries.

| Origin | Configured intent mix |
|---|---|
| STC | 65% career specialist, 25% coordinator aspiration, 10% HC aspiration |
| OC/DC | 75% primary specialist, 20% secondary discipline, 5% generalist |
| Position coach | 55% coordination aspiration, 45% teaching career |

An aspiring crossover generally needs 4–7 years of coordinator experience and instincts >=55; position-to-coordinator promotion needs three years of teaching and instincts >=55. Prior experience matters. Unfamiliar coordinator authority begins at 0.65 and rises by 0.12 per role year, capped at 1.0. Intent percentages are not observed promotion rates. Actual crossover frequency, role longevity, payroll and alumni entry still require 10/20/30-season calibration.

Coaches age, develop, accrue experience and reputation, move through the market, and retire. Retirement begins probabilistically at age 60 and is compulsory at 80. A retired coach is archived rather than eligible for new employment. HC leadership and familiarity affect staff preference. An assistant may seek a promotion without first vacating an existing post. Vacancies may still require generated candidates. User senior staffing decisions are manual except automatic retirement replacement; funded position slots can be filled automatically.

## Position coaches

Six assignments: Zerobacks, Backs & Vipers, Offensive Line, Defensive Line, Keepers & Coverage, Kicking & Returns. Coordinators cover assignments without a dedicated teacher.

| Program prestige | Dedicated positions normally funded |
|---|---:|
| Below 45 | 2 |
| 45–74 | 4 |
| 75+ | 6 |

Existing contracts are retained when funding changes. Dedicated position salary allowance per contract is capped at $85,000 + $1,800 × prestige (clamped 0–100). This is incremental to the senior payroll, not a guarantee of whole-program budget balance.

Instruction concentrates an existing development allowance on technical skills. It does not add a new blanket game-day modifier. Teaching affects recruiting targets (up to ±3%), scouting uncertainty, bounded retention, offseason installation and technical personnel recommendations. Kicking instruction shares the existing allowance rather than stacking. Graduates may become delayed alumni candidates (approximately 2–4% configured selection probability, not measured appointments); identity and prior employment history prevent duplicate entry.

## Recruiting fit

CPU targeting combines school skill priorities and the actual caller (65/35 when both apply, adjusted for authority), capped at ±8% of the existing ranking score. The separate position-teacher factor is bounded at ±3%. Talent, stars, depth, geography and existing signing rules remain relevant. The model influences which recruits CPU programs pursue, not their physical ratings or automatic signing outcomes. Human recruiting remains manual.

## Where to inspect

- College team page: staff, role coverage, installation and team tactics.
- Coach profile: traits, actual caller, experience, market reputation, career intent and fingerprint derived from played games.
- Dynasty: coaching changes, recruiting, offseason and saved histories.
- Analytics: team/drive and scheme splits, not causal coaching attribution.

See [step 7 AAR](docs/aar_2026-11-25_step7_dynasty_continuity.md), [career paths and position staff AAR](docs/aar_2026-11-25_coaching_career_paths_position_staff.md), [leadership study](docs/aar_2026-11-25_val06_cch10_leadership_followup.md), and [development plan](docs/DEVELOPMENT_PLAN.md). The pre-position-coach longitudinal study is not validation of the newer combined career system.
