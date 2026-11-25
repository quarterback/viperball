# Delta Yards and Mess Rate

Current definitions are in [ANALYTICS.md](../ANALYTICS.md) and [RULES.md](../RULES.md).

After a score the receiving team starts at clamp(20 minus its score lead, 1, 80). The signed delta_cost is neutral baseline minus the actual starting yard line.

| Bucket | Condition |
|---|---|
| Power play | delta_cost < 0 (gained yards) |
| Penalty kill | delta_cost > 0 (lost yards) |
| Neutral | delta_cost = 0 |

Only actual Delta restarts use this field-position rule; do not infer a bucket from the score alone. Drives carry delta_cost and bonus flags. TD/made-kick incidence = qualifying scoring drives / bucket drives. PPD uses actual drive-credited points, including eligible pindowns but excluding non-drive scoring. The scoring-incidence numerator excludes a pindown alone.

Mess Rate = power-play scoring percentage minus penalty-kill scoring percentage when both are supported. A positive gap does not prove the team depends causally on the advantage. Report counts, PPD, TD/kick rates and actual field position; leave unsupported comparisons unavailable. Bonus context and field-position values in the portal are separate experimental conditional contrasts.

The historical terminology proposal is preserved in repository history; this is the current definition.
