# Review of 2D options for Viperball

## Findings

The college box score and standalone Game Sim already share a template. A film room can use the saved game result and the analytics adapter for its timeline. The engine records the lineup, formation, defensive calls, rush details, scoring, and game state around each snap. It resolves outcomes at the play level. Player paths and ball flight would need to be illustrated from those outcomes.

Four seeded games produced 675 play log entries. The analytics adapter returned a row for every entry. Both state snapshots were present for 668 rows. The other seven rows were bonus possession markers. A scoring kick pass in the first game kept the same field position in both snapshots, so a diagram must use the scoring event and play type when placing a touchdown.

## Proposed first build

Add a field diagram and timeline to the college game page. Include line of scrimmage, gain line, score, and play descriptions. Let the user jump to kick passes, lateral chains, and recoveries. Use the actual team that scored and distinguish the destination on a scoring play from the next restart spot.

SVG and vanilla JavaScript are enough for the diagram. PixiJS fits a followup with sprite animation. Konva fits a playbook editor. Phaser fits an arcade mode with direct controls. A Godot project makes more sense if the arcade game needs its own desktop release. A mode where the coach calls the next play would need a resumable simulation session in Python.

The review used the checked out engine and upstream project descriptions. It did not install a renderer or change application code.
