# PEN-04: Discipline box-score presentation (2026-11-25)

Base: main after merged PR #388. No change to engine penalties or calibration rates.

## Delivered
- College game detail (including one-off simulator) has a dedicated Penalties & Discipline section instead of mixing penalties into turnovers.
- Away/home accepted flags, penalty yards, declined flags, qualifying conduct fouls and ejections; chronological ejection records with period/time, team, player, reason, yardage ruling and recorded replacement.
- Expandable accepted-foul breakdown and player discipline table; ejected labels in player tables and play-by-play.
- Markdown export and browser Copy Box Score include the discipline records, including collapsed tables.
- Legacy games retain available team penalty counts and explicitly say player discipline records are unavailable, rather than reporting false zero ejections.

## Validation
Focused regression tests: pytest -q tests/test_discipline_boxscore.py
Includes overtime, declined yardage, escaped names, and missing versus empty records.
Browser rendering, clipboard interaction, full regression suite and calibration are not verified here. Scope is the college stats site and shared Markdown generator; separate NiceGUI/pro/international views are not changed.
