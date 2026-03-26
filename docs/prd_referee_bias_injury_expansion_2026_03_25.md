# PRD: Referee Bias System & Injury Catalog Expansion

**Date:** 2026-03-25
**Status:** Implemented
**Branch:** `claude/referee-bias-system-B6KAy`

---

## Problem Statement

Two gaps in the simulation model reduce immersion:

1. **Officiating is perfect.** Every penalty call is correct, every spot is precise. Real sports have a human element — refs miss calls, throw bad flags, and spot the ball wrong. This matters because it creates narrative moments ("that blown call cost them the game") and strategic depth (coach challenges).

2. **Injuries are too shallow.** The existing catalog has ~50 entries with no metadata about re-injury risk, nagging potential, surgery requirements, or per-attribute impact. Too many players stay healthy across a season, which isn't realistic for college athletics. The injury profile also skews too heavily toward football-specific contact injuries when Viperball (no hard helmets, more lateral movement) should lean closer to soccer/basketball soft tissue profiles.

---

## Referee Bias System

### Design Philosophy

The ref system should be **immersive, not game-breaking**. Across a full season (~120 games), 0.5-3% of total penalty situations should have an error. Most games are completely clean. Maybe 1-3 games per season have a blown call that meaningfully shifts the outcome. The system adds narrative, not noise.

### Referee Pool

- **300 named referees** generated dynamically using the player name generator (`scripts/generate_names.py`) — enough for 100 3-person crews to cover a 200-team league
- Pool is cached per session; call `generate_referee_pool(n, seed)` to regenerate or expand
- Each ref has **hidden attributes** (not exposed in UI):

| Attribute | Range | Description |
|-----------|-------|-------------|
| `accuracy` | 0.905-0.98 | How often the ref gets calls right |
| `home_favor` | -0.5 to +0.5 | Lean toward home team on close calls |
| `consistency` | 0.87-0.97 | Stability of calls within a game |

### Tier Distribution

| Tier | Count | Accuracy Range |
|------|-------|----------------|
| Elite | ~3 | 97-98% |
| Good | ~10 | 95-97% |
| Solid | ~10 | 93-95% |
| Average | ~5 | 92-93% |
| Below-average | ~2 | 90.5-92% |

### Crew Structure

- Referees are grouped into **3-person crews** (head ref, umpire, side judge)
- Head ref = highest accuracy in the trio
- Crew accuracy = average of all three members
- **Playoff games** always use top-third rated crews
- **Bowl/non-conference games** can use any crew
- Conference assignment is tracked for future enforcement (refs assigned to conferences like teams)

### Blown Call Types

| Type | Description | Per-play rate (elite crew) | Per-play rate (below-avg crew) |
|------|-------------|---------------------------|-------------------------------|
| Phantom flag | Penalty called when no infraction occurred | ~0.07% | ~0.15% |
| Swallowed whistle | Legitimate penalty goes uncalled | ~0.10% | ~0.19% |
| Spot error | Ball spotted 1-3 yards off correct position | ~0.13% | ~0.24% |

With ~60 plays per game, this means:
- Elite crew: ~0.18 blown calls per game (1 every 5-6 games)
- Below-avg crew: ~0.35 blown calls per game (1 every 3 games)
- Season average across all crews: ~0.25 per game

### Coach Challenge System

- **3 challenges per game** per team (not per half)
- The **replay system always gets the correct call** — if a coach challenges a genuine blown call, it is overturned
- Coaches **don't always challenge**: ~60% of blown calls are noticed and challenged
- Coaches **sometimes waste challenges** on correct calls (~0.1% per play chance)
- Net effect: ~60% of blown calls get challenged, and all challenged blown calls are overturned
- Residual uncorrected error rate: ~0.1 blown calls per game (1 every 10 games that actually sticks)

### Box Score Integration

Officials listed subtly at the bottom of the box score alongside weather:

```
**Officials:** Heather Martin, Henrique Rodrigues, Ghassan Al-Balushi | **Weather:** Clear
```

Challenge summary and post-game officiating review shown only when there were incidents.

### Game Summary Data

```python
result["referee"] = {
    "name": "Crew member names",
    "blown_calls": 0,           # Uncorrected blown calls
    "challenged_calls": 0,      # Total challenges used
    "overturned_calls": 0,      # Successful challenges
    "blown_call_log": [...],    # Detailed log of all incidents
    "home_challenges_remaining": 3,
    "away_challenges_remaining": 3,
}
```

---

## Injury Catalog Expansion

### Design Philosophy

Viperball injury profiles should be closer to **soccer and basketball** than American football:
- **No hard helmets** means concussions are more common (not less — no protection)
- More **soft tissue injuries** (hamstrings, groins, ankles, knees) from lateral movement
- Fewer gruesome collision injuries (no linemen smashing into each other with helmets)
- Real **college athlete availability issues** (academics, mental health, personal, disciplinary)

### Catalog Structure (OOTP-inspired)

Each injury entry now carries rich metadata:

```python
{
    "desc": "sprained ankle",           # Diagnosis shown to user
    "body": "ankle",                     # Body part for re-injury tracking
    "freq": 5,                           # 1 (rare) to 5 (common) — weights selection
    "reinjury": 1,                       # 0=none, 1=sometimes, 2=often
    "nagging": 1,                        # 0 or 1 — can flare up after return
    "surgery": 0,                        # 0=no, 1=sometimes, 2=yes
    "inf_run": 2,                        # 0-3 influence on running/speed
    "inf_kick": 0,                       # 0-3 influence on kicking
    "inf_lateral": 0,                    # 0-3 influence on lateral skill
    "min_weeks": 3,                      # Override tier default min
    "max_weeks": 8,                      # Override tier default max
}
```

### Catalog Size

| Category | Before | After |
|----------|--------|-------|
| On-field contact | 33 | 61 |
| On-field non-contact | 16 | 47 |
| Practice/training | 14 | 30 |
| Off-field | 20 | 48 |
| **Total** | **83** | **186** |

### Key Changes

**Tier week ranges expanded:**
- Minor: 1-2 weeks -> 1-3 weeks
- Moderate: 3-5 weeks -> 3-6 weeks
- Major: 6-8 weeks -> 6-10 weeks

**Re-injury system:** If a player injures the same body part they've had before, recovery time increases by 1-2 weeks (scaled by `reinjury` rating).

**Frequency weighting:** Common injuries (freq=5) appear much more often than rare ones (freq=1). Sprained ankles, hamstring tightness, and the flu dominate the injury report — just like real college sports.

**Concussions elevated:** No hard helmets means concussions are freq=4 (common) at the day-to-day level and freq=3 at moderate. This is realistic for a contact sport without full head protection.

**Off-field expansion:** Covers the full range of real college athlete availability:
- Illness (cold, flu, mono, pneumonia, COVID protocol)
- Academic (probation, ineligibility, exam conflicts)
- Personal (family emergency, bereavement, personal leave)
- Mental health (breaks, stress-related leave)
- Disciplinary (team suspension, conduct violations)
- Administrative (visa issues, transfer portal)

### Injury Dataclass Changes

New fields added to the `Injury` dataclass:

```python
reinjury_chance: int = 0    # 0=none, 1=sometimes, 2=often
nagging: bool = False       # Can flare up after return
requires_surgery: int = 0   # 0=no, 1=sometimes, 2=yes
inf_run: int = 0            # 0-3 influence on running when playing through
inf_kick: int = 0           # 0-3 influence on kicking
inf_lateral: int = 0        # 0-3 influence on lateral skill
```

All fields included in `to_dict()` for API/UI consumption.

---

## Future Work

- **Injury report UI** on /stats page with searchable dropdown by conference/team showing current injuries, expected return dates, and game status
- **Conference-assigned referee crews** — refs belong to conferences and can't officiate their own conference's games in conference play; any crew can work non-conference games
- **Nagging injury flare-ups** — players with nagging=True have elevated re-injury risk for 2-3 weeks after returning
- **Surgery decision modeling** — when surgery is required (surgery=2), add realistic recovery timelines (6-12 months)
- **Per-attribute DTD penalties** — use inf_run/inf_kick/inf_lateral to apply targeted stat reductions when a DTD player plays through an injury (e.g., ankle injury reduces speed but not kicking)
- **Referee reputation tracking** — track blown calls across a season, assign crew quality ratings that evolve
