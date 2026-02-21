#!/usr/bin/env python3
"""Batch simulation for verifying engine rebalance metrics."""

import sys
import os
import random
import glob
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from engine import ViperballEngine, load_team_from_json


def run_batch(num_games=200):
    team_files = glob.glob("data/teams/*.json")
    if len(team_files) < 2:
        print("Need at least 2 team files")
        return

    # Accumulators
    total_plays = []
    home_scores = []
    away_scores = []
    home_tds = []
    away_tds = []
    home_fgs = []
    away_fgs = []
    home_snap_kicks = []
    away_snap_kicks = []
    home_fumbles = []
    away_fumbles = []
    home_turnovers_on_downs = []
    away_turnovers_on_downs = []
    home_yards = []
    away_yards = []
    lateral_attempts = []
    lateral_successes = []
    lateral_interceptions_total = []
    down_4_attempts = []
    down_4_conversions = []
    down_5_attempts = []
    down_5_conversions = []
    down_6_attempts = []
    down_6_conversions = []
    home_timeouts_used = []
    away_timeouts_used = []
    punts_total = []
    kick_pass_attempts = []
    kick_pass_completions = []
    kick_pass_ints = []
    first_downs_total = []
    drives_total = []

    for i in range(num_games):
        # Pick two random different teams
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

        fs = result['final_score']
        home_scores.append(fs['home']['score'])
        away_scores.append(fs['away']['score'])

        hs = result.get('stats', {}).get('home', {})
        aws = result.get('stats', {}).get('away', {})

        # Plays
        h_plays = hs.get('total_plays', 0)
        a_plays = aws.get('total_plays', 0)
        total_plays.append(h_plays + a_plays)

        # TDs
        home_tds.append(hs.get('touchdowns', 0))
        away_tds.append(aws.get('touchdowns', 0))

        # FGs (place_kicks_made)
        home_fgs.append(hs.get('place_kicks_made', 0))
        away_fgs.append(aws.get('place_kicks_made', 0))

        # Snap kicks (drop_kicks_made)
        home_snap_kicks.append(hs.get('drop_kicks_made', 0))
        away_snap_kicks.append(aws.get('drop_kicks_made', 0))

        # Fumbles
        home_fumbles.append(hs.get('fumbles_lost', 0))
        away_fumbles.append(aws.get('fumbles_lost', 0))

        # Turnovers on downs
        home_turnovers_on_downs.append(hs.get('turnovers_on_downs', 0))
        away_turnovers_on_downs.append(aws.get('turnovers_on_downs', 0))

        # Yards
        home_yards.append(hs.get('total_yards', 0))
        away_yards.append(aws.get('total_yards', 0))

        # Laterals
        lat_att = hs.get('lateral_chains', 0) + aws.get('lateral_chains', 0)
        lat_suc = hs.get('successful_laterals', 0) + aws.get('successful_laterals', 0)
        lateral_attempts.append(lat_att)
        lateral_successes.append(lat_suc)

        # Lateral interceptions
        lat_int = hs.get('lateral_interceptions', 0) + aws.get('lateral_interceptions', 0)
        lateral_interceptions_total.append(lat_int)

        # Down conversions - nested as {4: {'attempts': N, 'converted': N}}
        h_dc = hs.get('down_conversions', {})
        a_dc = aws.get('down_conversions', {})

        d4h = h_dc.get(4, {})
        d4a = a_dc.get(4, {})
        down_4_attempts.append(d4h.get('attempts', 0) + d4a.get('attempts', 0))
        down_4_conversions.append(d4h.get('converted', 0) + d4a.get('converted', 0))

        d5h = h_dc.get(5, {})
        d5a = a_dc.get(5, {})
        down_5_attempts.append(d5h.get('attempts', 0) + d5a.get('attempts', 0))
        down_5_conversions.append(d5h.get('converted', 0) + d5a.get('converted', 0))

        d6h = h_dc.get(6, {})
        d6a = a_dc.get(6, {})
        down_6_attempts.append(d6h.get('attempts', 0) + d6a.get('attempts', 0))
        down_6_conversions.append(d6h.get('converted', 0) + d6a.get('converted', 0))

        # Timeouts - check the engine's game_state if available
        # The stats don't track timeouts directly, so estimate from game_state
        # For now, just track what we can
        home_timeouts_used.append(0)
        away_timeouts_used.append(0)

        # Punts
        punts_total.append(hs.get('punts', 0) + aws.get('punts', 0))

        # Kick pass stats
        kp_att = hs.get('kick_passes_attempted', 0) + aws.get('kick_passes_attempted', 0)
        kp_comp = hs.get('kick_passes_completed', 0) + aws.get('kick_passes_completed', 0)
        kp_int = hs.get('kick_pass_interceptions', 0) + aws.get('kick_pass_interceptions', 0)
        kick_pass_attempts.append(kp_att)
        kick_pass_completions.append(kp_comp)
        kick_pass_ints.append(kp_int)

        # First downs from play-by-play
        pbp = result.get('play_by_play', [])
        fd_count = len([p for p in pbp if p.get('result') == 'first_down'])
        first_downs_total.append(fd_count)

        # Avg yards_to_go on down 4
        d4_plays = [p for p in pbp if p.get('down') == 4 and p.get('play_type') not in ['punt', 'drop_kick', 'place_kick']]
        if d4_plays:
            avg_ytg_d4 = sum(p.get('yards_to_go', 0) for p in d4_plays) / len(d4_plays)
        else:
            avg_ytg_d4 = 0
        if not hasattr(run_batch, '_d4_ytg_samples'):
            run_batch._d4_ytg_samples = []
        run_batch._d4_ytg_samples.append(avg_ytg_d4)

        # Track drive outcomes
        if not hasattr(run_batch, '_drive_outcomes'):
            run_batch._drive_outcomes = defaultdict(int)
        for ds in result.get('drive_summary', []):
            outcome = ds.get('result', 'unknown')
            run_batch._drive_outcomes[outcome] += 1

        if (i + 1) % 25 == 0:
            print(f"  Completed {i+1}/{num_games} games...")

    # Compute stats
    def avg(lst):
        return sum(lst) / len(lst) if lst else 0

    def pct(num_list, denom_list):
        n = sum(num_list)
        d = sum(denom_list)
        return (n / d * 100) if d > 0 else 0

    n = len(total_plays)
    print(f"\n{'='*60}")
    print(f"BATCH SIMULATION RESULTS ({n} games)")
    print(f"{'='*60}\n")

    print(f"{'Metric':<35} {'Result':>12} {'Target':>12}")
    print(f"{'-'*60}")

    avg_plays = avg(total_plays)
    print(f"{'Plays/game':<35} {avg_plays:>12.1f} {'140-220':>12}")
    if total_plays:
        print(f"{'  Min/Max plays':<35} {min(total_plays):>5}/{max(total_plays):<6}")

    avg_home = avg(home_scores)
    avg_away = avg(away_scores)
    avg_score = (avg_home + avg_away) / 2
    print(f"{'Avg score/team':<35} {avg_score:>12.1f} {'65-85':>12}")
    print(f"{'  Home/Away avg':<35} {avg_home:>5.1f}/{avg_away:<6.1f}")

    avg_h_td = avg(home_tds)
    avg_a_td = avg(away_tds)
    avg_td = (avg_h_td + avg_a_td) / 2
    print(f"{'Avg TDs/team':<35} {avg_td:>12.1f} {'6-8':>12}")

    avg_h_sk = avg(home_snap_kicks)
    avg_a_sk = avg(away_snap_kicks)
    avg_sk = (avg_h_sk + avg_a_sk) / 2
    print(f"{'Snap kicks made/team':<35} {avg_sk:>12.1f} {'2-4':>12}")

    avg_h_fg = avg(home_fgs)
    avg_a_fg = avg(away_fgs)
    avg_fg = (avg_h_fg + avg_a_fg) / 2
    print(f"{'FGs made/team':<35} {avg_fg:>12.1f} {'1-3':>12}")

    avg_h_fum = avg(home_fumbles)
    avg_a_fum = avg(away_fumbles)
    avg_fum = (avg_h_fum + avg_a_fum) / 2
    print(f"{'Fumbles/team':<35} {avg_fum:>12.1f} {'~1.6':>12}")

    avg_h_tod = avg(home_turnovers_on_downs)
    avg_a_tod = avg(away_turnovers_on_downs)
    avg_tod = (avg_h_tod + avg_a_tod) / 2
    print(f"{'Turnovers on downs/team':<35} {avg_tod:>12.1f} {'2-3':>12}")

    avg_h_yds = avg(home_yards)
    avg_a_yds = avg(away_yards)
    avg_yds = (avg_h_yds + avg_a_yds) / 2
    print(f"{'Avg yards/team':<35} {avg_yds:>12.1f} {'600-750':>12}")

    # Lateral efficiency
    total_lat_att = sum(lateral_attempts)
    total_lat_suc = sum(lateral_successes)
    lat_eff = (total_lat_suc / total_lat_att * 100) if total_lat_att > 0 else 0
    print(f"{'Lateral efficiency':<35} {lat_eff:>11.1f}% {'59-72%':>12}")
    print(f"{'  Total laterals att/suc':<35} {total_lat_att:>5}/{total_lat_suc:<6}")

    total_lat_int = sum(lateral_interceptions_total)
    print(f"{'Lateral interceptions (total)':<35} {total_lat_int:>12}")
    if total_lat_att > 0:
        print(f"{'  Lat INT rate':<35} {total_lat_int/total_lat_att*100:>11.1f}%")

    d4_pct = pct(down_4_conversions, down_4_attempts)
    d5_pct = pct(down_5_conversions, down_5_attempts)
    d6_pct = pct(down_6_conversions, down_6_attempts)
    print(f"{'4th down conversion':<35} {d4_pct:>11.1f}% {'~85%':>12}")
    print(f"{'  4th down att/conv':<35} {sum(down_4_attempts):>5}/{sum(down_4_conversions):<6}")
    print(f"{'5th down conversion':<35} {d5_pct:>11.1f}% {'~71%':>12}")
    print(f"{'  5th down att/conv':<35} {sum(down_5_attempts):>5}/{sum(down_5_conversions):<6}")
    print(f"{'6th down conversion':<35} {d6_pct:>11.1f}% {'~63%':>12}")
    print(f"{'  6th down att/conv':<35} {sum(down_6_attempts):>5}/{sum(down_6_conversions):<6}")

    avg_punts = avg(punts_total)
    print(f"{'Punts/game':<35} {avg_punts:>12.1f}")

    total_kp_att = sum(kick_pass_attempts)
    total_kp_comp = sum(kick_pass_completions)
    total_kp_int = sum(kick_pass_ints)
    kp_comp_pct = (total_kp_comp / total_kp_att * 100) if total_kp_att > 0 else 0
    kp_int_pct = (total_kp_int / total_kp_att * 100) if total_kp_att > 0 else 0
    print(f"{'Kick pass completion %':<35} {kp_comp_pct:>11.1f}%")
    print(f"{'  KP att/comp/int':<35} {total_kp_att:>4}/{total_kp_comp:>4}/{total_kp_int:<4}")
    print(f"{'Kick pass INT rate':<35} {kp_int_pct:>11.1f}% {'3-4%':>12}")

    avg_fd = avg(first_downs_total)
    print(f"{'First downs/game':<35} {avg_fd:>12.1f}")
    if avg_plays > 0:
        fd_rate = avg_fd / avg_plays * 100
        print(f"{'First down rate (% of plays)':<35} {fd_rate:>11.1f}%")
    if hasattr(run_batch, '_d4_ytg_samples') and run_batch._d4_ytg_samples:
        avg_d4_ytg = avg(run_batch._d4_ytg_samples)
        print(f"{'Avg yards_to_go on 4th down':<35} {avg_d4_ytg:>12.1f}")

    # Drive outcome breakdown
    if hasattr(run_batch, '_drive_outcomes'):
        outcomes = run_batch._drive_outcomes
        total_dr = sum(outcomes.values())
        print(f"\n{'DRIVE OUTCOMES':<35} {'Count':>8} {'%':>8}")
        for k in sorted(outcomes.keys(), key=lambda x: -outcomes[x]):
            pct_val = outcomes[k] / total_dr * 100 if total_dr > 0 else 0
            print(f"  {k:<33} {outcomes[k]:>8} {pct_val:>7.1f}%")

    # Avg fatigue (from the single-game sample)
    print(f"\n{'='*60}")
    print("SCORE DISTRIBUTION")
    print(f"{'='*60}")
    all_scores = home_scores + away_scores
    buckets = defaultdict(int)
    for s in all_scores:
        bucket = int(s // 10) * 10
        buckets[bucket] += 1
    for b in sorted(buckets.keys()):
        bar = '#' * (buckets[b] // 2)
        print(f"  {b:>3}-{b+9:<3}: {buckets[b]:>4} {bar}")


if __name__ == "__main__":
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    print(f"Running {num} game batch simulation...")
    run_batch(num)
