# Feature Report — Women's Viperball League (WVL): Galactic Premiership

**Date:** March 1, 2026
**Branch:** `claude/add-womens-pro-league-PIkzg`
**Commit:** `c412a86` — Add Women's Viperball League (WVL) — Galactic Premiership with owner mode

---

## Problem Statement

College women's players in the CVL (187 teams across 13 conferences) graduate into a dead end. Their only post-college path is FIV international play — there's no women's professional league. The NVL, EL, AL, PL, and LA leagues are all men's leagues (spectator-only). College seniors graduate, some get mapped to national teams via the FIV heritage system, and the rest disappear from the game entirely.

This is a gap both in the sport's universe and in gameplay. College dynasty mode builds attachment to players across 4 years, and then those players have nowhere to go.

---

## What Was Built

A complete 64-team, 4-tier women's professional league with EPL-style promotion/relegation, operating as a **standalone game mode** where the human plays as a **club owner** (not a coach).

### League Structure

| Tier | Name | Teams | Countries | Games/Season | Format |
|------|------|-------|-----------|-------------|--------|
| 1 | Galactic Premiership | 18 | 7 | 34 | Home-and-away |
| 2 | Galactic League 1 | 20 | 10 | 38 | Home-and-away |
| 3 | Galactic League 2 | 13 | 5 | 24 | Home-and-away |
| 4 | Galactic League 3 | 13 | 8 | 24 | Home-and-away |

14 countries represented: England, Scotland, Wales, Spain, Italy, Germany, France, Portugal, Netherlands, Turkey, Greece, Finland, Norway, USA.

### Promotion/Relegation Rules

| Boundary | Auto Down | Auto Up | Playoff |
|----------|-----------|---------|---------|
| T1 ↔ T2 | Bottom 3 in T1 | Top 2 in T2 | 3rd in T2 vs 16th in T1 (single match) |
| T2 ↔ T3 | Bottom 3 in T2 | Top 2 in T3 | 3rd in T3 vs 18th in T2 (single match) |
| T3 ↔ T4 | Bottom 2 in T3 | Top 2 in T4 | None |

### Built-In Rivalries (13 groups)

El Clásico (Real Madrid vs Barcelona), English Triangle (Man United vs Liverpool vs Man City), Derby della Madonnina (AC Milan vs Inter), North London Derby (Arsenal vs Tottenham), Old Firm (Celtic vs Rangers), Scottish Triangle (Celtic/Rangers vs Hearts), Italian Rivalry (Juventus vs Napoli), Eredivisie Triangle (Ajax vs Feyenoord vs PSV), Portuguese Big Three (Benfica vs Porto vs Sporting), Turkish Derby (Galatasaray vs Fenerbahce), Der Klassiker (Bayern vs Dortmund), Olympique Derby (Lyon vs Marseille), Ostrobothnian Derby (Lapua Virkiä vs Vimpelin Veto).

### Narrative Arcs (baked into team metadata)

- **Wrexham** in Tier 1 — vanity project ownership made real. Can they stay up?
- **Portland Timbers** in Tier 2 — the lone American outpost. Every match is an away match.
- **Vimpelin Veto** starting in Tier 4 — the Cinderella story. Four promotions to reach the top.
- **Nottingham Forest, Leeds, Everton** — fallen giants grinding through Tier 3.
- **Bodø/Glimt** — already did the impossible in real football.

---

## Owner Mode — Design Philosophy

This is not a coaching sim. The dynasty mode already handles that for college. The WVL is an **ownership sim** — you make high-level decisions and watch the consequences play out through layers of delegation. Deep pockets don't guarantee success. A bad president wastes your money. A good one stretches it. The boosts you invest in are marginal — they often cancel out league-wide since every club invests in something — but they can be the small edge that matters, or despite them, you still get relegated but you keep trying anyway.

### Four Owner Levers

**1. Owner Archetype** (chosen once at setup)

| Archetype | Bankroll | Patience | FA Rep | Style |
|-----------|----------|----------|--------|-------|
| Sugar Daddy | $80M | 2 seasons | +15% | Overspends, impatient |
| Patient Builder | $50M | 5 seasons | +0% | Long-term vision |
| Youth Evangelist | $45M | 4 seasons | +5% | Training focus, young players |
| Trophy Hunter | $70M | 2 seasons | +20% | Star signings, neglects infra |
| Hometown Hero | $40M | 4 seasons | +0% | Fan loyalty, moderate |
| Corporate Group | $65M | 3 seasons | +10% | Expects ROI, will sell |
| Underdog Dreamer | $25M | 6 seasons | -10% | Scrappy, smart president needed |

**2. President Hire/Fire** (between seasons)

6 archetypes: Old Guard, Innovator, Moneyball, Big Spender, Developer, Dealmaker. Each shapes coaching hires and strategy through their ratings (acumen, budget management, recruiting eye, staff hiring). Presidents cost salary and have buyout clauses.

**3. One Targeted Free Agent** per offseason

The owner picks exactly one FA from the pool — signed at any cost. Everything else is autonomous.

**4. Investment Allocation** (annual, temporary boosts)

| Area | Player Effect | Club Effect |
|------|-------------|-------------|
| Training Facilities | +1-3 physical (speed, stamina, agility) | — |
| Coaching Staff | +1-3 mental (awareness, tackling) | — |
| Stadium | — | +FA attractiveness, +attendance |
| Youth Academy | +development for <25 players | — |
| Sports Science | +stamina, +power | — |
| Marketing/Brand | — | +FA attractiveness, +prestige |

---

## Architecture

### Decoupled from College Dynasty

```
┌─────────────────────┐         ┌─────────────────────┐
│   COLLEGE DYNASTY    │         │  WVL GALACTIC MODE   │
│   (existing mode)    │         │   (new standalone)    │
│                      │  EXPORT │                      │
│  Run dynasty seasons ├────────►│  Import as FA pool   │
│  Graduate seniors    │  JSON   │  for a given year    │
│                      │  file   │                      │
│  Separate save       │         │  Separate save       │
└─────────────────────┘         └─────────────────────┘
```

The two modes are completely independent. No shared state, no code coupling. The bridge is a JSON file on disk: college dynasty exports graduating seniors, WVL mode can optionally import them as that year's free agent pool. WVL also runs standalone with synthetic FA generation.

### Player Lifecycle Differences

| Aspect | College (existing) | Pro (WVL) |
|--------|-------------------|-----------|
| Progression | Year-based (FR→SO→JR→SR→GR) | Age-based (22-38) |
| Peak | Junior/Senior year | Ages 23-28 |
| Decline | Graduates out | Physical attrs drop 29+, sharp at 34+ |
| Exit | Graduation | Retirement (auto at 38, chance-based 32+) |
| Acquisition | Recruiting, transfer portal | Free agency only |
| Management | Coach (human) | President (AI), owner picks 1 FA |

---

## Files Delivered

### New Files (9)

| File | Lines | Purpose |
|------|-------|---------|
| `engine/wvl_config.py` | 260 | 64 clubs, 4 tier configs, 13 rivalry groups, country→style mappings |
| `engine/promotion_relegation.py` | 280 | Pro/rel engine with custom rules per boundary, playoff simulation |
| `engine/wvl_free_agency.py` | 310 | Free agent pool (import or synthetic), autonomous AI signing, owner targeted FA |
| `engine/wvl_owner.py` | 420 | 7 owner archetypes, 6 president archetypes, investment system, financials |
| `engine/wvl_dynasty.py` | 300 | Multi-season dynasty with offseason pipeline, save/load |
| `engine/wvl_season.py` | 250 | Multi-tier season orchestrator wrapping ProLeagueSeason per tier |
| `scripts/generate_wvl_teams.py` | 370 | 64-team generation with country-appropriate names, culture-based styles |
| `nicegui_app/pages/wvl_mode.py` | 270 | Owner mode UI: setup, dashboard, sim, standings with pro/rel zones |
| `test_wvl.py` | 310 | 34 integration tests across all subsystems |

### Modified Files (4)

| File | Change | Risk |
|------|--------|------|
| `engine/player_card.py` | Added 5 optional pro fields (`age`, `pro_team`, `contract_years`, `contract_salary`, `pro_status`) | Low — all `Optional` with `None` defaults, no impact on existing college code |
| `engine/development.py` | Added `apply_pro_development()` and `should_retire()` | Low — new functions only, existing college development untouched |
| `engine/dynasty.py` | Added `export_graduating_class()` method | Low — new method on existing class, no changes to existing methods |
| `nicegui_app/app.py` | Added "WVL" to `NAV_SECTIONS` + routing | Low — additive only |

### Generated Data (64 team files + 1 assignment file)

```
data/wvl_teams/
├── tier1/   (18 files: real_madrid.json, fc_barcelona.json, ... wrexham.json)
├── tier2/   (20 files: as_roma.json, napoli.json, ... portland.json)
├── tier3/   (13 files: west_ham.json, aston_villa.json, ... atalanta.json)
├── tier4/   (13 files: sassuolo.json, hoffenheim.json, ... torino.json)
data/wvl_tier_assignments.json
```

Each team JSON follows the existing NVL format: `team_info`, `identity`, `style`, `prestige`, `roster` (36 players with age, contract, country-appropriate names, and tier-scaled attributes). Additional `wvl_metadata` block carries tier, country, city, and narrative tag.

---

## Test Results

34/34 passing:

```
TestWVLConfig        (10 tests) — club counts, unique keys, season lengths, rivalries, narrative tags
TestOwnerMode        (6 tests)  — archetypes, president pool, serialization, financials
TestFreeAgency       (4 tests)  — synthetic pool, attractiveness, signing, owner targeted FA
TestProDevelopment   (4 tests)  — young growth, old decline, retirement logic
TestPromotionRelegation (3 tests) — tier movements, T3↔T4 no-playoff, persistence
TestWVLDynasty       (2 tests)  — creation, save/load roundtrip
TestPlayerCardProFields (2 tests) — default None, serialization with pro fields
TestTeamData         (3 tests)  — file existence, format validation, tier assignments
```

No regressions in existing test suite (pre-existing failure in `test_recruiting.py::test_roster_prestige_estimation` is unrelated — verified failing on clean branch before changes).

---

## What's Not Yet Done (future work)

1. **Full season simulation through the UI** — the multi-tier sim orchestrator works in engine but the UI only has a basic sim button; week-by-week stepping with standings display is stubbed
2. **Offseason UI flow** — investment allocation, president hire/fire, and targeted FA selection are engine-complete but need dedicated UI screens
3. **Pro/rel drama screen** — the promotion/relegation results deserve a dramatic reveal UI (who went up, who went down, playoff result)
4. **History/timeline view** — promotion/relegation history across seasons, financial graphs, which tier each club was in each year
5. **League map** — 14-country geographic view showing tier assignments
6. **College export UI button** — the `export_graduating_class()` method is wired but the dynasty UI doesn't expose it yet
7. **AI president coaching changes** — the president's `coaching_style_bias` exists but doesn't yet propagate to the team's `style` dict between seasons
8. **Inter-tier cup competition** — like a League Cup where teams from all 4 tiers compete in a knockout bracket
