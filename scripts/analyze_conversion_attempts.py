#!/usr/bin/env python3
"""Analyze why certain teams have very few 6th down conversion attempts.

6th down conversion attempts are rare events requiring a specific chain:
1. Team fails to convert on downs 1-3 (doesn't gain 20 yards)
2. On 4th down, team either goes for it and fails, OR enters kick mode and
   misses (pesäpallo rule retains possession)
3. On 5th down, same thing happens again
4. On 6th down, team must choose to "go for it" (run/lateral/kick-pass)
   rather than kick — only non-kick plays count as conversion attempts

This script simulates games for a specific team and breaks down exactly
where the funnel narrows: how many drives reach each down, how many result
in kicks vs. going for it, and why 6th down attempts are so scarce.
"""

import json
import sys
import random
import glob
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import ViperballEngine, load_team_from_json


def analyze_team_conversions(team_id: str, num_games: int = 30):
    """Run games featuring a specific team and analyze its conversion funnel."""
    team_file = Path(__file__).resolve().parent.parent / "data" / "teams" / f"{team_id}.json"
    if not team_file.exists():
        print(f"Team file not found: {team_file}")
        return

    team_files = glob.glob(str(Path(__file__).resolve().parent.parent / "data" / "teams" / "*.json"))
    opponents = [f for f in team_files if Path(f).stem != team_id]

    if not opponents:
        print("No opponent team files found")
        return

    # Tracking metrics
    total_drives = 0
    drives_reaching = defaultdict(int)       # drives that reach down N
    attempts_by_down = defaultdict(int)       # "go for it" attempts on down N
    conversions_by_down = defaultdict(int)    # successful conversions on down N
    kicks_by_down = defaultdict(int)          # kick plays on down N
    turnovers_on_downs = 0
    punts_by_down = defaultdict(int)

    # Play type breakdown on late downs
    play_type_by_down = defaultdict(lambda: defaultdict(int))
    play_type_conv_by_down = defaultdict(lambda: defaultdict(int))

    # Load Team object for simulation, raw JSON for metadata
    team_obj = load_team_from_json(str(team_file))
    with open(team_file, "r") as f:
        team_raw = json.load(f)
    team_name = team_obj.name
    team_style = team_raw.get("identity", {}).get("philosophy", "unknown")

    print(f"\n{'='*70}")
    print(f"CONVERSION ATTEMPT ANALYSIS: {team_name}")
    print(f"Style: {team_style} | Games: {num_games}")
    print(f"{'='*70}\n")

    for i in range(num_games):
        opp_file = random.choice(opponents)
        opp = load_team_from_json(opp_file)

        # Alternate home/away
        try:
            if i % 2 == 0:
                engine = ViperballEngine(team_obj, opp)
                our_side = "home"
            else:
                engine = ViperballEngine(opp, team_obj)
                our_side = "away"
            result = engine.simulate_game()
        except Exception as e:
            print(f"  Game {i+1} ERROR: {e}")
            continue

        pbp = result.get("play_by_play", [])

        # Walk the play-by-play to reconstruct down state for our team
        actual_down = 1
        actual_ytg = 20
        last_possession = None
        drive_max_down = 1

        for p in pbp:
            poss = p.get("possession")

            # Possession change = new drive
            if poss != last_possession and last_possession is not None:
                if last_possession == our_side:
                    # Record the previous drive's max down reached
                    total_drives += 1
                    for d in range(1, drive_max_down + 1):
                        drives_reaching[d] += 1
                actual_down = 1
                actual_ytg = 20
                drive_max_down = 1
            last_possession = poss

            # Only track our team's plays
            if poss != our_side:
                continue

            play_type = p.get("play_type", "unknown")
            result_val = p.get("result", "")
            yards = p.get("yards_gained", 0)

            drive_max_down = max(drive_max_down, actual_down)

            is_kick = play_type in ("punt", "drop_kick", "place_kick")

            if actual_down >= 4:
                if is_kick:
                    kicks_by_down[actual_down] += 1
                    if play_type == "punt":
                        punts_by_down[actual_down] += 1
                else:
                    attempts_by_down[actual_down] += 1
                    play_type_by_down[actual_down][play_type] += 1

            # Check conversion
            is_conversion = (
                result_val in ("first_down", "touchdown", "punt_return_td", "int_return_td")
                or yards >= actual_ytg
            )

            if is_conversion:
                if actual_down >= 4 and not is_kick:
                    conversions_by_down[actual_down] += 1
                    play_type_conv_by_down[actual_down][play_type] += 1
                actual_down = 1
                actual_ytg = 20
            else:
                # Drive-ending events
                if result_val in (
                    "fumble", "kick_pass_intercepted", "int_return_td",
                    "lateral_intercepted", "safety", "turnover_on_downs",
                    "successful_kick", "missed_kick"
                ):
                    if result_val == "turnover_on_downs":
                        turnovers_on_downs += 1
                    actual_down = 1
                    actual_ytg = 20
                else:
                    actual_down += 1
                    actual_ytg = max(1, actual_ytg - max(0, yards))

        # Final drive
        if last_possession == our_side:
            total_drives += 1
            for d in range(1, drive_max_down + 1):
                drives_reaching[d] += 1

        if (i + 1) % 10 == 0:
            print(f"  Simulated {i+1}/{num_games} games...")

    # ── Report ──
    print(f"\n{'─'*70}")
    print(f"DRIVE FUNNEL (how drives progress through downs)")
    print(f"{'─'*70}")
    print(f"\n  Total drives: {total_drives}")
    print(f"  Turnovers on downs: {turnovers_on_downs}\n")

    print(f"  {'Down':<8} {'Drives':>10} {'% of Total':>12} {'Go-For-It':>12} {'Kicks':>8} {'Punts':>8}")
    print(f"  {'-'*58}")
    for d in range(1, 7):
        dr = drives_reaching.get(d, 0)
        pct = (dr / total_drives * 100) if total_drives > 0 else 0
        att = attempts_by_down.get(d, 0)
        k = kicks_by_down.get(d, 0)
        pu = punts_by_down.get(d, 0)
        extra = ""
        if d >= 4:
            extra = f"  {att:>12} {k:>8} {pu:>8}"
        print(f"  {d:<8} {dr:>10} {pct:>11.1f}%{extra}")

    print(f"\n{'─'*70}")
    print(f"CONVERSION ATTEMPTS (non-kick plays only)")
    print(f"{'─'*70}\n")

    print(f"  {'Down':<8} {'Attempts':>10} {'Converted':>10} {'Rate':>8}")
    print(f"  {'-'*40}")
    for d in [4, 5, 6]:
        att = attempts_by_down.get(d, 0)
        conv = conversions_by_down.get(d, 0)
        rate = (conv / att * 100) if att > 0 else 0
        print(f"  {d:<8} {att:>10} {conv:>10} {rate:>7.1f}%")

    print(f"\n{'─'*70}")
    print(f"PLAY TYPE BREAKDOWN ON LATE DOWNS")
    print(f"{'─'*70}\n")

    for d in [4, 5, 6]:
        types = play_type_by_down.get(d, {})
        if not types:
            print(f"  Down {d}: No go-for-it attempts")
            continue
        print(f"  Down {d}:")
        for pt in sorted(types.keys(), key=lambda x: -types[x]):
            att = types[pt]
            conv = play_type_conv_by_down.get(d, {}).get(pt, 0)
            rate = (conv / att * 100) if att > 0 else 0
            print(f"    {pt:<20} {att:>5} att  {conv:>5} conv  {rate:>6.1f}%")
        print()

    # ── Analysis summary ──
    print(f"{'─'*70}")
    print(f"WHY SO FEW 6TH DOWN ATTEMPTS?")
    print(f"{'─'*70}\n")

    d4_drives = drives_reaching.get(4, 0)
    d5_drives = drives_reaching.get(5, 0)
    d6_drives = drives_reaching.get(6, 0)
    d4_kicks = kicks_by_down.get(4, 0)
    d5_kicks = kicks_by_down.get(5, 0)
    d6_kicks = kicks_by_down.get(6, 0)
    d6_att = attempts_by_down.get(6, 0)

    print(f"  The funnel from 4th → 6th down narrows dramatically:\n")

    if d4_drives > 0:
        print(f"  1. Of {total_drives} total drives, {d4_drives} ({d4_drives/total_drives*100:.1f}%) reached 4th down")

    if d4_drives > 0:
        d4_kick_pct = d4_kicks / d4_drives * 100 if d4_drives > 0 else 0
        print(f"  2. On 4th down, {d4_kicks} ({d4_kick_pct:.1f}%) were kicks (snap kick/FG/punt)")
        print(f"     → Only {d4_drives - d4_kicks} were 'go for it' attempts")

    if d5_drives > 0:
        print(f"  3. Only {d5_drives} drives ({d5_drives/d4_drives*100:.1f}% of 4th-down drives) reached 5th down")
        d5_kick_pct = d5_kicks / d5_drives * 100 if d5_drives > 0 else 0
        print(f"     Of those, {d5_kicks} ({d5_kick_pct:.1f}%) were kicks")
    else:
        print(f"  3. NO drives reached 5th down")

    if d6_drives > 0:
        print(f"  4. Only {d6_drives} drives reached 6th down")
        d6_kick_pct = d6_kicks / d6_drives * 100 if d6_drives > 0 else 0
        print(f"     Of those, {d6_kicks} ({d6_kick_pct:.1f}%) were kicks, {d6_att} were go-for-it attempts")
    else:
        print(f"  4. NO drives reached 6th down")

    print(f"\n  Key factors for {team_name}:")
    print(f"  - Philosophy: {team_style}")
    if team_style == "ground_and_pound":
        print(f"    → kick_mode_aggression = 0.25 (lowest in the game)")
        print(f"    → This team almost never enters kick mode on 4th down")
        print(f"    → Without kick mode, failed 4th-down plays usually end in TOD")
        print(f"    → Fewer kick mode entries = fewer chances to reach 5th/6th via pesäpallo rule")
    print(f"  - 6th down conversion attempts require reaching 6th down AND choosing")
    print(f"    to go for it instead of kicking — an extremely rare combination")

    coaching = team_raw.get("coaching_staff", {})
    hc = coaching.get("head_coach", {})
    oc = coaching.get("oc", {})
    if hc:
        sliders = hc.get("personality_sliders", {})
        print(f"  - HC {hc.get('first_name', '')} {hc.get('last_name', '')}: "
              f"risk_tolerance={sliders.get('risk_tolerance', '?')}, "
              f"aggression={sliders.get('aggression', '?')}")
    if oc:
        sliders = oc.get("personality_sliders", {})
        traits = oc.get("hidden_traits", [])
        print(f"  - OC {oc.get('first_name', '')} {oc.get('last_name', '')}: "
              f"risk_tolerance={sliders.get('risk_tolerance', '?')}, "
              f"aggression={sliders.get('aggression', '?')}, "
              f"traits={traits}")

    print()


if __name__ == "__main__":
    team = sys.argv[1] if len(sys.argv) > 1 else "wash_u"
    games = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    analyze_team_conversions(team, games)
