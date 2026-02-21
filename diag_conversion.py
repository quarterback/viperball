#!/usr/bin/env python3
"""Diagnostic: measure actual per-down conversion rates by tracking
consecutive plays in the play log, not relying on p.down values."""

import sys
import random
import glob
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from engine import ViperballEngine, load_team_from_json


def run_diagnostic(num_games=50):
    team_files = glob.glob("data/teams/*.json")
    if len(team_files) < 2:
        print("Need at least 2 team files")
        return

    # Track: for each down, how many plays started on that down,
    # and how many resulted in first_down or touchdown
    down_attempts = defaultdict(int)
    down_conversions = defaultdict(int)
    down_ytg_sum = defaultdict(float)
    down_yards_sum = defaultdict(float)

    # Also track play type breakdown on late downs
    late_down_play_types = defaultdict(int)
    late_down_play_type_conversions = defaultdict(int)

    for i in range(num_games):
        pair = random.sample(team_files, 2)
        try:
            home = load_team_from_json(pair[0])
            away = load_team_from_json(pair[1])
            engine = ViperballEngine(home, away)
            result = engine.simulate_game()
        except Exception as e:
            print(f"Game {i+1} ERROR: {e}")
            import traceback
            traceback.print_exc()
            continue

        # Walk through play log and reconstruct actual down state
        # We track actual_down and actual_ytg before each play
        pbp = result.get('play_by_play', [])

        actual_down = 1
        actual_ytg = 20
        last_possession = None

        for p in pbp:
            # Possession change = new drive, reset
            if p.get('possession') != last_possession and last_possession is not None:
                actual_down = 1
                actual_ytg = 20
            last_possession = p.get('possession')

            play_type = p.get('play_type', 'unknown')
            result_val = p.get('result', '')
            yards = p.get('yards_gained', 0)

            # Skip kicking plays
            if play_type in ('punt', 'drop_kick', 'place_kick'):
                continue

            # Record this play's actual down
            if actual_down >= 1 and actual_down <= 6:
                down_attempts[actual_down] += 1
                down_ytg_sum[actual_down] += actual_ytg
                down_yards_sum[actual_down] += max(0, yards)

                if actual_down >= 4:
                    key = f"{play_type}_d{actual_down}"
                    late_down_play_types[key] += 1

                # Did this play convert?
                is_conversion = (result_val in ('first_down', 'touchdown', 'punt_return_td', 'int_return_td')
                                or yards >= actual_ytg)

                if is_conversion:
                    down_conversions[actual_down] += 1
                    if actual_down >= 4:
                        late_down_play_type_conversions[key] += 1
                    actual_down = 1
                    actual_ytg = 20
                else:
                    # Drive-ending events reset
                    if result_val in ('fumble', 'kick_pass_intercepted', 'int_return_td',
                                     'lateral_intercepted', 'safety', 'turnover_on_downs',
                                     'successful_kick', 'missed_kick'):
                        actual_down = 1
                        actual_ytg = 20
                    else:
                        actual_down += 1
                        actual_ytg = max(1, actual_ytg - max(0, yards))

        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{num_games} games...")

    print(f"\n{'='*60}")
    print(f"PER-DOWN CONVERSION DIAGNOSTIC ({num_games} games)")
    print(f"{'='*60}\n")

    print(f"{'Down':<8} {'Attempts':>10} {'Converted':>10} {'Conv%':>8} {'AvgYTG':>8} {'AvgYds':>8} {'Target':>8}")
    print("-" * 60)
    for d in range(1, 7):
        att = down_attempts[d]
        conv = down_conversions[d]
        pct = (conv / att * 100) if att > 0 else 0
        avg_ytg = (down_ytg_sum[d] / att) if att > 0 else 0
        avg_yds = (down_yards_sum[d] / att) if att > 0 else 0
        target = {4: "~85%", 5: "~71%", 6: "~63%"}.get(d, "")
        print(f"  {d:<6} {att:>10} {conv:>10} {pct:>7.1f}% {avg_ytg:>7.1f} {avg_yds:>7.1f} {target:>8}")

    print(f"\n{'LATE-DOWN PLAY TYPE BREAKDOWN':}")
    print(f"{'Type':<25} {'Attempts':>10} {'Converted':>10} {'Conv%':>8}")
    print("-" * 55)
    for key in sorted(late_down_play_types.keys()):
        att = late_down_play_types[key]
        conv = late_down_play_type_conversions.get(key, 0)
        pct = (conv / att * 100) if att > 0 else 0
        print(f"  {key:<23} {att:>10} {conv:>10} {pct:>7.1f}%")


if __name__ == "__main__":
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run_diagnostic(num)
