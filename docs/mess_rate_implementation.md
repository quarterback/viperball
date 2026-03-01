# Implement Mess Rate and Power Play/Penalty Kill Stats

## New Terminology

The delta system drives now use hockey-borrowed language:

- **Power play drive**: A drive where the team is trailing and receiving a delta field position bonus (starting ahead of the 20)
- **Penalty kill drive**: A drive where the team is leading and paying a delta field position cost (starting behind the 20)
- **Neutral drive**: No delta adjustment (tied game or drive immediately after a non-scoring possession)

These replace the current "boosted" and "penalized" labels in the engine output and UI.

## Stats to Calculate

### Per-Game (Box Score Level)

- **PP%** (Power Play Percentage): Scoring rate on power play drives. `power_play_scores / power_play_drives * 100`
- **Kill Rate**: Scoring rate on penalty kill drives. `penalty_kill_scores / penalty_kill_drives * 100`  
- **Mess Rate**: The gap between PP% and Kill Rate. `PP% - Kill Rate`

A team that scores on 4 of 5 power play drives (80% PP%) and 2 of 5 penalty kill drives (40% kill rate) has a mess rate of 40. The delta system is significantly degrading their performance when they lead.

A team that goes 3/5 on power play (60%) and 3/5 on penalty kill (60%) has a mess rate of 0. Field position proof.

### Per-Season (Aggregate)

Same calculations but aggregated across all games:

- **Season PP%**: Total power play scores / total power play drives across all games
- **Season Kill Rate**: Total penalty kill scores / total penalty kill drives across all games  
- **Season Mess Rate**: Season PP% - Season Kill Rate

### Display Notes

- Mess rate can be negative if a team scores at a higher rate on penalty kill drives than power play drives. That's a team that actually performs better from deep. Rare but possible with elite ground-pound offenses.
- In the box score, display as a line item: `Power Play: 3/5 (60%) | Penalty Kill: 2/4 (50%) | Mess Rate: 10`
- In season stats, display as a team-level metric alongside win-loss record, point differential, etc.
- Lower mess rate = more consistent = better in close games. This is a "lower is better" stat like ERA, not a "higher is better" stat like batting average.

## Where This Comes From in Existing Data

The DYE data structure already tracks everything needed:

- `dye.boosted` → rename to power play. `count`, `scores`, `score_rate` are all there.
- `dye.penalized` → rename to penalty kill. Same fields.
- Mess rate is just `boosted.score_rate - penalized.score_rate` (or `power_play.score_rate - penalty_kill.score_rate` after rename).

The underlying drive-level data (`delta_drive`, `delta_cost`, `bonus_drive`) already flags which drives are which. This is a relabeling and a single subtraction, not a new calculation from scratch.

## Rename Map

In the JSON output and UI:

| Current Term | New Term |
|---|---|
| boosted drive | power play drive |
| penalized drive | penalty kill drive |
| dye_when_boosted | pp_efficiency |
| dye_when_penalized | pk_efficiency |
| compelled_efficiency | kill_rate |

Add `mess_rate` as a new field at the team stats level: `stats.home.mess_rate` and `stats.away.mess_rate`.

Add season-level aggregation in whatever module handles cumulative team stats.
