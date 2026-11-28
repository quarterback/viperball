# Playbook catalog inventory

Catalog snapshot, November 27, 2026. The current source is [packages.json](../../data/playbooks/packages.json); use `python -m engine.playbook_catalog` for the runtime-derived inventory (including computed strengths and vocabulary labels). See [school reference](../OFFENSE_SCHEMAS.md) for the 16 offensive and 10 defensive schools.

## Offense packages

| Package | ID | Origin | Compatible schools | Situation tags | Personnel tags |
|---|---|---|---|---|---|
| Kick-In Breakout | `afl_kick_in_breakout` | east_coast | east_coast, boot_raid, ball_control, ironclad, six_shooter, slick_n_slide, ghost, mismatch, mousetrap, quick_strike, shock_and_awe, ground_control, balanced | backed_up, first_play_of_drive | strong_kicker |
| Restart Go-To | `afl_restart_go_to` | ghost | ghost, mismatch, stampede, quick_strike, slick_n_slide, lateral_spread, chain_gang, boot_raid, east_coast, balanced | after_score_restart, first_play_of_drive | team_speed |
| Launch Pad Kick Set | `br_launch_pad_kick_set` | boot_raid | boot_raid, six_shooter, east_coast, ball_control, ironclad, slick_n_slide, mousetrap, balanced | launch_pad, kick_range | strong_kicker |
| Chase Chain | `cg_chase_chain` | chain_gang | chain_gang, lateral_spread, ghost, mismatch, quick_strike, shock_and_awe, slick_n_slide, balanced | chasing | lateral_hands |
| Quick Kick Chain | `ec_quick_kick_chain` | east_coast | east_coast, boot_raid, ball_control, six_shooter, slick_n_slide, ghost, mismatch, mousetrap, quick_strike, shock_and_awe, balanced | long_yardage | strong_kicker |
| Two Minute Chain | `ec_two_minute` | east_coast | east_coast, boot_raid, ball_control, six_shooter, slick_n_slide, ghost, mismatch, mousetrap, quick_strike, shock_and_awe, lateral_spread, balanced | two_minute | — |
| Goal Line Jumbo | `gp_goal_line_jumbo` | ground_control | ground_control, ironclad, ball_control, slick_n_slide, six_shooter, boot_raid, east_coast, stampede, mousetrap, balanced | goal_line | physical_roster |
| Heavy Push | `gp_heavy_push` | ground_control | ground_control, ironclad, ball_control, slick_n_slide, six_shooter, boot_raid, east_coast, stampede, ghost, mousetrap, mismatch, quick_strike, balanced | short_yardage | physical_roster |
| Four Minute Grind | `ironclad_four_minute` | ironclad | ironclad, ground_control, ball_control, slick_n_slide, six_shooter, east_coast, boot_raid, mousetrap, balanced | protect_lead | physical_roster |
| Extra Attacker | `lax_extra_attacker` | stampede | stampede, ghost, mismatch, quick_strike, slick_n_slide, lateral_spread, chain_gang, ground_control, balanced | tired_defense | team_speed, deep_conditioning |
| Fast Break | `lax_fast_break` | quick_strike | quick_strike, shock_and_awe, stampede, ghost, mismatch, lateral_spread, chain_gang, boot_raid, east_coast, balanced | after_takeaway, first_play_of_drive | team_speed |
| Last Tackle Kick | `league_last_tackle_kick` | six_shooter | six_shooter, boot_raid, east_coast, shock_and_awe, ball_control, ironclad, balanced | late_downs, launch_pad | strong_kicker |
| First Phase Strike | `rugby_first_phase_strike` | slick_n_slide | slick_n_slide, ground_control, six_shooter, mousetrap, ghost, ironclad, ball_control, stampede, balanced | first_play_of_drive | team_speed |
| Vertical Shot | `sa_vertical_shot` | shock_and_awe | shock_and_awe, boot_raid, east_coast, quick_strike, ghost, mismatch, lateral_spread, balanced | long_yardage, chasing | elite_kicker, team_speed |
| Viper Trail | `gaelic_kick_and_follow` | east_coast | east_coast, slick_n_slide, ball_control, ghost, balanced | drive_building | lateral_hands |
| Far Side Coil | `afl_boundary_switch` | east_coast | east_coast, ghost, mousetrap, boot_raid, balanced | drive_building | strong_kicker |
| Third Strike | `rugby_carry_release` | slick_n_slide | slick_n_slide, mousetrap, ground_control, ghost, stampede, balanced | drive_building | physical_roster |
| Bonus Guard | `ball_protect_bonus` | ball_control | ball_control, quick_strike, ground_control, ironclad, balanced | pending_bonus | — |
| Pindown Chase | `cfl_corner_chase` | ironclad | ironclad, ball_control, boot_raid, six_shooter, balanced | corner_punt | strong_kicker |

## Defense packages

| Package | ID | Origin | Compatible schools | Situation tags | Personnel tags |
|---|---|---|---|---|---|
| Kick-In Press | `afl_kick_in_press` | predator | predator, blitz_pack, chaos, swarm | backed_up, first_play_of_drive | team_speed, deep_conditioning |
| Short Yardage Pressure | `blitz_short_yardage_pressure` | blitz_pack | blitz_pack, chaos, predator, swarm, fortress | short_yardage | team_speed |
| Lateral Trap | `chaos_lateral_trap` | chaos | chaos, swarm, predator, shadow | early_down | team_speed |
| Prevent | `drift_prevent` | drift | drift, lockdown, swarm, shadow, fortress, predator | two_minute, protect_lead | — |
| Goal Line Stand | `fortress_goal_line_stand` | fortress | fortress, swarm, blitz_pack, chaos, shadow, lockdown, drift, predator | goal_line, short_yardage | strong_defense, physical_roster |
| Short Yardage Wall | `fortress_short_yardage_wall` | fortress | fortress, swarm, blitz_pack, chaos, shadow, lockdown, drift, predator | short_yardage | strong_defense |
| Ride | `lax_ride` | chaos | chaos, blitz_pack, predator, swarm | after_takeaway, first_play_of_drive | deep_conditioning |
| Kick Range Shell | `lockdown_kick_range_shell` | lockdown | lockdown, drift, swarm, shadow, predator, fortress, chaos | kick_range, launch_pad | strong_defense |
| Long Yardage Bracket | `lockdown_long_yardage_bracket` | lockdown | lockdown, drift, swarm, shadow, predator, fortress | long_yardage | — |
| Exhaustion Press | `predator_exhaustion_press` | predator | predator, blitz_pack, chaos, swarm | early_down | deep_conditioning, team_speed |
| Rush Line | `rugby_rush_line` | blitz_pack | blitz_pack, swarm, chaos, predator, fortress | early_down | team_speed |
| Robber Coverage | `shadow_robber` | shadow | shadow, lockdown, drift, swarm | late_downs | strong_defense |
| Containment | `swarm_containment` | swarm | swarm, fortress, drift, shadow | early_down | strong_defense |

Counts: 19 offensive and 13 defensive packages. Eligibility, benefits and concessions come from the catalog and live engine; a package's presence does not establish that it is frequently installed or called.
