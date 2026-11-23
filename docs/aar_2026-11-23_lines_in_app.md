# AAR: Midfield lines in the app
## November 23, 2026

## What Ron asked

Show the lines: a Line column on the team roster and My Team, and line changes in the box score.

## Changes

**Engine (`engine/game_engine.py`)**
- `build_midfield_lines`: the line builder now lives at module level, and the engine and the
  roster pages share it.
- `_rush_score` was moved out of `assign_game_roles` so roster pages can pick the same starters
  the engine picks. `_tackle_score` is shared too.
- `preview_midfield_lines(team, unavailable)`: the lines a team would start its next game
  with, plus the defensive specialist (the best tackler off line one who beats line one's
  fourth best tackler by 8%). Injured players are left out.
- Checked against the engine on 20 teams: 300 of 300 midfielders on the same line.
- Play by play: a play run while the other team is caught changing starts with
  "FAST BREAK, (team) caught changing." The first season week had 51 of them.

**API (`api/main.py`)**: `line` and `def_specialist` on the season roster, the team roster
and the My Team roster.

**Web**
- New `components/LineCell.tsx`: the line number, plus a DS badge with a tooltip for the
  specialist. Sorting puts line 1 first and non-midfielders last.
- Line column after Pos on the team roster (`TeamPage.tsx`) and My Team (`MyTeam.tsx`).
- Box score team stats gain Line changes and Caught changing rows.
- Cleanup: the box score's empty message still mentioned the removed fast sim. It now says
  "No box score for this game yet."

**README**: the Rotations section says where lines show in the app.

## Checks

Tests: 72 pass. TypeScript check and production build pass. The My Team endpoint returns line
and specialist fields; a sample team showed a Wingback on line 2 as its specialist.
