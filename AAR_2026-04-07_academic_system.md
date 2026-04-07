# AAR: Academic & Mental Attributes System
## Viperball Recruiting Intelligence — April 2026

### Summary

Added a comprehensive academic and mental attributes system to Viperball's recruiting engine. This makes recruiting feel like a real marketplace where academic eligibility gates who can go where, and mental traits (field intelligence, coachability) determine how well recruits develop once they arrive.

**No other college sports sim does this well.** Most games treat academics as a binary pass/fail or ignore it entirely. Viperball now models the full spectrum: from Stanford's 3.85 median GPA / 1480 median VAT making it impossible to offer a 2.1 GPA recruit, to a mid-major with a 2.80 median GPA happily taking the same kid.

---

### What Was Built

#### 1. Recruit Mental Attributes

Every generated recruit now has four new attributes beyond their physical ratings:

- **Field Intelligence (25-95):** How smart the player is on the field. Loosely correlated with awareness but fundamentally different — a player can have elite technique (high awareness) but poor instincts (low field IQ), or vice versa. Generated as a Gaussian distribution around the player's awareness rating with ±15 noise and σ=10.

- **Coachability (25-95):** An independent personality trait. Determines how well a player responds to coaching. High coachability + a great coaching staff (especially a Program Changer archetype) = a 2-star prospect developing into a contributor. Low coachability = talent ceiling is hard to reach regardless of resources. Bell curve centered at 60 with σ=14.

- **GPA (1.5-4.0):** Weighted high school GPA on a bell curve centered at 3.0 (σ=0.45). Loosely correlated with field intelligence (~20% influence). Distribution: ~15% below 2.5, ~70% between 2.5-3.5, ~15% above 3.5.

- **VAT Score (600-1600):** Viperball Aptitude Test. Bell curve centered at 1050 (σ=150). ~40% correlation with GPA, but with a 10% outlier chance — the "good student who tests badly" or "bad student who aces standardized tests." ~5% below 850, ~5% above 1400, ~1% above 1500. Rounded to 10-point increments like the real SAT.

- **Academic Risk:** Computed from GPA + VAT. `clear` (vast majority), `at_risk` (~5%), `ineligible` (~0.5%). The clearinghouse surprise — you invest in a kid all recruiting cycle and find out at signing time she can't qualify. Rare enough to be surprising, common enough to plan around.

#### 2. School Academic Profiles

All 205 team JSON files now carry `median_gpa` and `median_vat` scores:

| Tier | Example Schools | Median GPA | Median VAT | Admissions Flex |
|------|----------------|-----------|-----------|----------------|
| Elite | Stanford, Air Force, Georgetown, Harvard | 3.65-3.90 | 1350-1510 | Very low (0.10-0.15) |
| High | Duke, Northwestern, Vanderbilt, Rice, Notre Dame | 3.40-3.64 | 1250-1349 | Low (0.20-0.35) |
| Above Average | Ohio State, UCLA, Georgia, Clemson | 3.15-3.39 | 1100-1249 | Moderate (0.40-0.55) |
| Standard | Most D1 programs | 2.80-3.14 | 950-1099 | High (0.60-0.75) |
| Flexible | Open admission, mid-majors | 2.30-2.79 | 820-949 | Very high (0.80-0.90) |

Academic tier is now **computed** from the median values, not a static label. This means:
- Schools can theoretically shift tiers if you modify their JSON
- The numbers are visible on the team page (Academic Profile section)
- The system is data-driven, not hardcoded

#### 3. Academic Gating in Recruiting

Offers are now gated by academic eligibility:

- **Floor calculation:** A school's admission floor = median minus a buffer (GPA - 0.50, VAT - 200). NCAA absolute minimum: 2.0 GPA, 800 VAT.
- **Elite schools won't even show interest** in academically at-risk recruits. Stanford doesn't waste recruiting hours on a 2.1 GPA kid.
- **Stochastic flex:** Borderline cases are resolved probabilistically. A kid 0.2 GPA below the floor at a mid-major has a decent shot (athletic department pulls strings). The same gap at an elite academic school? Almost never.
- **Ineligible recruits get zero offers.** They can't play anywhere until they fix their academics.

#### 4. VAT & GPA on Team Pages

The college team page now shows an **Academic Profile** section with:
- Median GPA (color-coded by tier)
- Median VAT (color-coded by tier)
- Computed academic tier label
- Inline display in the team subtitle next to prestige

#### 5. Recruit Profile Enrichment

Recruit profile pages now display:
- GPA and VAT scores with color coding
- Field Intelligence and Coachability ratings
- Academic risk flags (AT RISK / INELIGIBLE in red/yellow)
- Full attribute bars for scouted recruits

---

### Design Decisions

**Why separate Field Intelligence from Awareness?**
Real sports have this distinction. A quarterback who can read a Cover 2 shell (field IQ) is different from one who has perfect footwork (awareness/technique). You want both, but they develop differently and are scouted differently.

**Why is Coachability independent?**
It's a personality trait, not a skill. Some elite athletes are uncoachable — they've always been the best and never learned to take instruction. Some walk-ons are incredibly coachable and outperform their talent ceiling. This interacts directly with the coaching system: a Program Changer HC with a roster of high-coachability players is a cheat code.

**Why bell curves with outliers instead of flat distributions?**
Reality. Most recruits cluster around the middle. The outliers (1500+ VAT, sub-2.0 GPA) are rare and notable. The GPA-VAT mismatch at 10% reflects real-world data on standardized testing vs. classroom performance.

**Why compute tier from medians instead of static labels?**
Moddability. You can change a school's median_gpa in the JSON and the tier updates automatically. Dynasty mode can eventually drift school academics based on program success, coaching changes, or conference realignment.

---

### Interaction with Other Systems

- **Program Changer coaches** effectively bypass academic barriers through their virtual prestige boost — they make a low-prestige school look attractive enough that elite academic recruits choose the coach over the institution.
- **NIL system** doesn't override academics. You can offer $500K to a kid but if they can't get into Stanford, they can't get into Stanford.
- **Transfer portal** uses the same eligibility check — a portal player transferring to a high-academic school needs to clear the bar.
- **APR metric** (`compute_team_apr()`) tracks team-wide academic health. Below 92.5% = NCAA penalty zone.

---

### Files Changed

- `engine/recruiting.py` — Recruit dataclass (4 new fields), academic tier system, eligibility check, GPA/VAT/field_intelligence/coachability generation, APR computation
- `data/teams/*.json` (205 files) — Added `median_gpa`, `median_vat`, `academic_tier` to team_info
- `stats_site/templates/college/team.html` — Academic Profile section
- `stats_site/templates/recruiting/recruit_profile.html` — GPA, VAT, Field IQ, Coachability display
- `stats_site/router.py` — Academic data loading and passing to templates
