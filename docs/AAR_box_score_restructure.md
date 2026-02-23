# Case Study AAR: The Box Score Restructure

## The Wall of Numbers Problem

The original box score was a single table labeled "Offensive Stats" — 13 rows of numbers arranged in no particular philosophy. Total yards sat next to lateral chains sat next to kick pass interceptions sat next to bonus possessions. It was technically complete. Every stat the engine tracked appeared somewhere in the list.

But it told you nothing about *how* a team played.

A Ground & Pound team that ran 30 times for 180 yards and threw 8 kick passes looked identical in structure to a Boot Raid team that ran 12 times for 60 yards and threw 25 kick passes. You had to mentally parse all 13 rows, do your own arithmetic, and reconstruct the offensive identity from raw numbers. The box score was a spreadsheet, not a story.

## The Style Fingerprint Concept

The insight was that a box score should be readable the way a real football box score is — glance at it for three seconds and you know what kind of game it was. When you see 45 pass attempts and 12 rushes in an NFL box score, you know it was an Air Raid day. When you see 38 carries and 18 attempts, you know it was a ground game.

Viperball has more offensive dimensions than traditional football (rushing, kick passing, laterals, kicking, trick plays), which makes the problem harder but the payoff bigger. A properly structured box score should let you identify:

- **Ground & Pound**: High carries, high rush yards, low KP attempts, few laterals
- **Boot Raid**: High KP attempts, high completion rate, moderate rushing, snap kick volume
- **Chain Gang**: Lateral chains everywhere, high lateral efficiency, distributed touches
- **Ghost Formation**: Balanced but unpredictable, moderate across all categories
- **Lateral Spread**: Lateral-heavy with kick pass integration, high play count from tempo

If you can't tell the difference between these at a glance, the box score has failed.

## Version 1: The Flat List

```
Offensive Stats
─────────────────────────────────
Total Yards        454       389
Rush Yds           155       112
Receiving Yds      277       201
Lateral Yds         12        28
Yds/Play           8.11      6.94
Total Plays         56        56
Lat Chains          10        14
Lat Eff            60.0%     71.4%
Fumbles Lost         2         1
KP INTs              0         2
Lat INTs             0         1
Bonus Poss.          1         0
Penalties        3/35yds   2/20yds
```

This tells you the home team had more yards. It does not tell you *why*, or what kind of offense produced them. "Receiving Yds" is labeled generically — in Viperball these are kick pass yards, a fundamentally different mechanic than forward passing. The scoring section is separate but the offensive identity is invisible.

**Problems**:
- No offensive style identification
- Rushing buried among 13 undifferentiated rows
- Kick passing stats scattered (attempts missing entirely — only yards shown)
- Lateral game stats mixed into the general pile
- Kicking (DK/PK) only appears in the scoring section, not the offensive section
- Trick plays invisible (play family breakdown not surfaced)
- Every team's box score looks structurally identical

## Version 2: The Structured Box Score

### Style Fingerprint Header

Before any numbers appear, two colored cards identify each team's offensive scheme:

```
┌─────────────────────────┐  ┌─────────────────────────┐
│ Agnes Scott College     │  │ Air Force Academy       │
│ Ground & Pound | Slow   │  │ Boot Raid | Mid         │
└─────────────────────────┘  └─────────────────────────┘
```

This is pulled directly from the engine's `OFFENSE_STYLES` dict — the same data that drives play selection. The tempo classification (Fast/Mid/Slow) maps from the style's tempo float (≥0.7 = Fast, ≥0.45 = Mid, <0.45 = Slow). You know the offensive identities before reading a single stat.

### Separated Categories

The flat list becomes six distinct sections, each telling part of the offensive story:

**Rushing** — Carries, Yards, YPC, Rush TDs. The ground game gets its own block. A Ground & Pound team should dominate here; a Boot Raid team should show modest numbers. YPC (yards per carry) is now computed from the play family breakdown rather than estimated — it counts run-family plays (dive_option, power, sweep_option, speed_option, counter, draw, viper_jet) against rushing yards.

**Kick Passing** — Att, Comp, Comp%, Yards, TDs, INTs. The aerial game. Completion percentage is now displayed directly rather than requiring mental math. A Boot Raid team should show 20+ attempts and 55-65% completion. A Ground & Pound team might show 8-12 attempts.

**Lateral Game** — Chains, Successful, Efficiency, Yards, Lat INTs. Viperball's unique dimension. Chain Gang and Lateral Spread teams should show high chain counts and efficiency. Ground & Pound teams might have 5-8 chains as a secondary option.

**Kicking** — Snap Kicks (DK) made/att, Field Goals (PK) made/att, Punts. Previously kicking only appeared in the scoring section as point contributions. Now the kicking game is visible as offensive production — a team with 8 DK attempts is playing a fundamentally different game than one with 2.

**Trick Plays** — Attempts. Simple count from the play family breakdown. Some styles run 6-8% trick plays; others run 2-3%. This was completely invisible before.

**Team Totals** — Total yards, yds/play, total plays, fumbles, bonus possessions, penalties. The aggregate summary at the bottom.

### The Reading Experience

With the restructured box score, you can now do a three-second style identification:

- See "Ground & Pound | Slow" in the header → check Rushing section → confirm 25+ carries, 140+ yards
- See "Boot Raid | Mid" → check Kick Passing → confirm 20+ attempts, 55%+ completion
- See "Chain Gang | Fast" → check Lateral Game → confirm 15+ chains, 65%+ efficiency
- The kicking section reveals whether a team is leaning on DK as a scoring weapon or grinding field goals
- Trick play count separates the conventional from the creative

## The Debug Panel: Offensive Performance in Batch

The single-game box score restructure had a companion problem in the batch simulator. The debug tools page showed defensive performance (DC gameplan, suppression heatmaps, adaptation events) and player impact (VPA rankings), but had no equivalent offensive panel. You could see *how the defense shut things down* but not *what the offense was doing in the first place*.

### What Was Added

The new Offensive Performance section in batch results provides:

1. **Summary cards** — Avg total yards, avg TDs, avg yds/play, avg plays across all simulated games
2. **Category breakdown table** — Rushing, kick pass, laterals, snap kicks, field goals, trick plays with avg/game, totals, and contextual extras (completion %, efficiency %, INT counts)
3. **Play family distribution** — Expandable panel showing every play family's total calls, avg/game, and share percentage

The play family distribution is particularly useful for style verification. If a Ground & Pound team's play distribution shows 35% kick pass and 15% dive/power, something is wrong with the style weights. If a Chain Gang team shows 25% lateral_spread, the style is working. This is the tool you use to debug the playbook, not just the outcome.

### Why This Matters for Tuning

The batch offensive panel closes a gap in the tuning workflow. Previously:

1. Run batch sim
2. See aggregate scores and VPA
3. Wonder why rushing yards are low
4. Manually grep through play-by-play logs to count play families
5. Adjust weights
6. Repeat

Now:

1. Run batch sim
2. See offensive performance table — rushing avg 87.6 yds (below 100-120 target)
3. Check play family distribution — run families at 22% share (should be 30%+ for ground_pound)
4. Adjust weights with specific targets
5. Repeat

The feedback loop is faster because the data you need is surfaced rather than buried.

## Design Principle: Stat Blocks as Identity

The broader lesson is the same one that emerged from the Diving Wing case study: **presentation should reflect the system's internal logic**. The engine has distinct offensive styles with different play selection weights. The box score should make those differences visible without requiring the reader to understand the weight tables.

A flat list of numbers is style-agnostic — it treats every team identically. A structured box score with style headers and categorized stats is style-aware — it tells you *which numbers to look at* based on who's playing. Ground & Pound? Check Rushing first. Boot Raid? Check Kick Passing. Chain Gang? Check Laterals.

This is the difference between a database query and a scouting report.

## Technical Notes

- Style fingerprint reads `result["home_style"]` / `result["away_style"]` from engine output, maps through `OFFENSE_STYLES` dict for label and tempo
- Tempo classification: ≥0.7 = Fast, ≥0.45 = Mid, <0.45 = Slow (maps to engine's tempo float which influences play clock)
- Rush carry count derived from play_family_breakdown rather than a dedicated counter — counts dive_option, power, sweep_option, speed_option, counter, draw, viper_jet families
- Kick pass completion % computed from `kick_passes_completed / kick_passes_attempted`
- Trick play count pulled from `play_family_breakdown["trick_play"]`
- Batch offensive panel uses same stat keys but aggregated across N simulations with averages
- Play family share percentages computed against total plays from breakdown dict, not `total_plays` stat (which includes non-family plays like penalties)
