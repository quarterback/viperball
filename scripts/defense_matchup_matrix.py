#!/usr/bin/env python3
"""DEF-06: reproducible 16-offense × 8-defense × 4-formation full-engine study.

The matrix holds offensive personnel constant and changes the defending scheme
on the same weak/strong defensive rosters. Each condition is also mirrored with
the offense home/away. Formation is *forced on the focal offense* so the four
formation shells are actually tested, rather than merely sampled when chosen.

Run from repository root (or any directory):
  PYTHONHASHSEED=0 python scripts/defense_matchup_matrix.py --reps 1 --out reports/def06
  python scripts/defense_matchup_matrix.py --offenses boot_raid,ground_control \\
      --weathers clear,rain --formations split,spread --reps 2 --out reports/def06_weather

This is an observational sensitivity experiment, not a final tuning target.
A seeded replay does not promise identical random streams once paths diverge.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine import ViperballEngine  # noqa: E402
from engine.game_engine import load_team_from_json  # noqa: E402
from engine.season import _pick_ai_archetype  # noqa: E402
from scripts.generate_rosters import CONFERENCE_FLOORS  # noqa: E402
from engine.game_engine import (  # noqa: E402
    DEFENSE_STYLES, OFFENSE_STYLES, FORMATION_VS_DEFENSE,
    OFFENSE_VS_DEFENSE_MATCHUP, V2_ENGINE_CONFIG,
)

FORMATIONS = ("tight", "split", "spread", "heavy")
TIERS = ("weak", "strong")
VENUES = ("home", "away")
RUN_FAMILIES = ("dive_option", "power", "sweep_option", "speed_option",
                "counter", "draw", "viper_jet")
ACTIVE_FAMILIES = (*RUN_FAMILIES, "lateral_spread", "kick_pass", "trick_play")
SCORING_RESULTS = {"touchdown", "successful_kick", "pindown", "safety",
                   "punt_return_td", "int_return_td", "missed_dk_return_td"}
CSV_FIELDS = (
    "offense", "defense", "formation", "defense_tier", "venue", "weather",
    "rep", "seed", "offense_roster", "defense_roster", "offensive_points",
    "touchdowns", "snap_kicks_made", "place_kicks_made", "drives",
    "attacking_drive_points", "scoring_drives", "stops", "points_per_drive",
    "plays", "run_plays", "run_yards", "run_ypp", "kick_pass_attempts",
    "kick_pass_completions", "kick_pass_completion", "sacks_allowed",
    "sacks_per_kick_pass", "kick_pass_yards", "lateral_plays",
    "lateral_yards", "lateral_ints", "fumbles_lost", "turnovers",
    "defensive_bells", "explosive_20", "explosive_30", "punt_attempts",
    "pindowns", "read_attempts", "read_successes", "read_rate",
    "defense_energy_end", "late_down_plays", "late_down_stops",
    "observed_formation_plays",
)
FAMILY_FIELDS = ("offense", "defense", "formation", "defense_tier",
                 "venue", "weather", "rep", "family", "attempts", "yards",
                 "nonpositive", "explosive_30")


def stable_seed(base: int, *parts: object) -> int:
    digest = hashlib.sha256(":".join(map(str, (base, *parts))).encode()).digest()
    return int.from_bytes(digest[:4], "big")


def sample_ci(values, seed=0):
    """Percentile 95% bootstrap CI over *games*, not dependent plays."""
    v = [float(x) for x in values if x is not None]
    if len(v) < 2:
        return (None, None)
    rng = random.Random(seed)
    n = len(v)
    bs = sorted(sum(v[rng.randrange(n)] for _ in range(n)) / n for _ in range(600))
    return (round(bs[int(0.025 * len(bs))], 3),
            round(bs[int(0.975 * len(bs)) - 1], 3))


def ratio(n, d):
    return n / d if d else None


def avg(xs):
    return statistics.mean(xs) if xs else None


def roster_score(team, defense=False):
    players = [p for p in team.players if
               p.position in ("Defensive Line", "Keeper", "Viper", "Wingback",
                              "Halfback", "Slotback")] if defense else team.players
    if not players:
        raise ValueError("No rating-eligible players for " + team.name)
    if defense:
        return statistics.mean(
            .50 * p.tackling + .30 * getattr(p, "awareness", 35) + .20 * p.speed
            for p in players
        )
    return statistics.mean(p.overall for p in players)


def load_stable_fresh_rosters(directory: Path):
    """Mirror Season fresh roster generation with sorted file iteration.

    Season.load_teams_from_directory() currently loops over Path.glob with
    filesystem order. Fresh roster generation draws from the process RNG,
    so two clean checkouts can pick different 'median' and tier rosters
    under the same seed. Sorting files makes this experiment repeatable
    without changing production roster behavior.
    """
    teams = {}
    for team_file in sorted(directory.glob("*.json")):
        data = json.loads(team_file.read_text(encoding="utf8"))
        info = data.get("team_info", {})
        conf_floor = CONFERENCE_FLOORS.get(info.get("conference", ""), 0)
        arch = _pick_ai_archetype()
        team = load_team_from_json(
            str(team_file), fresh=True, program_archetype=arch,
            conference_floor=conf_floor,
        )
        teams[team.name] = team
    if not teams:
        raise ValueError("No roster files in " + str(directory))
    return teams


def selected_roster_fingerprint(profile):
    """Detect accidental changes to baseline roster selection across runs."""
    data = json.dumps(profile, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf8")).hexdigest()[:20]


def choose_rosters(teams):
    """Real fresh CVL rosters at median offense and ~15th/85th defensive quality."""
    ranked = sorted(teams.values(), key=lambda t: (roster_score(t), t.name))
    offense = ranked[len(ranked) // 2]
    defenders = sorted(
        (t for t in teams.values() if t.name != offense.name),
        key=lambda t: (roster_score(t, defense=True), t.name),
    )
    weak = defenders[round((len(defenders) - 1) * .15)]
    strong = defenders[round((len(defenders) - 1) * .85)]
    if len({offense.name, weak.name, strong.name}) != 3:
        raise ValueError("Benchmark teams must have distinct names")
    if roster_score(weak, True) >= roster_score(strong, True):
        raise ValueError("Defensive roster bands are not ordered")
    return offense, {"weak": weak, "strong": strong}


class ObservedEngine(ViperballEngine):
    """Attach pre-snap offense and chosen formation to analysis output.

    A turnover play may already have changed state.possession by the time the
    normal Play object is returned, so play.possession is not reliable for
    attributing the offensive attempt. This subclass does not change gameplay.
    """

    def simulate_play(self):
        attacking_side = self.state.possession
        play = super().simulate_play()
        play.attack_side_at_snap = attacking_side
        return play

    def play_to_dict(self, play):
        row = super().play_to_dict(play)
        row["attack_side_at_snap"] = getattr(
            play, "attack_side_at_snap", row.get("possession"))
        row["formation"] = getattr(play, "formation", "") or ""
        row["kick_pass_subfamily"] = getattr(play, "kick_pass_subfamily", "") or ""
        return row


def observed_drive_points(drives, focus_side):
    """Score changes on focal offensive possessions, including live bells.

    A return TD by the defense stays credited to the defending side. These
    are within-drive scoreboard increments, not total team points per game.
    """
    prev = {"home": 0.0, "away": 0.0}
    result = []
    for drive in drives:
        now = {s: float(drive.get(s + "_score_after", prev[s])) for s in prev}
        if drive.get("team") == focus_side:
            gained = max(0.0, now[focus_side] - prev[focus_side])
            result.append(gained)
        prev = now
    return result


def summarize_game(result, offense, defense, formation, tier, venue,
                   weather, rep, seed, offense_name, defender_name):
    focus = venue
    other = "away" if focus == "home" else "home"
    stats = result["stats"][focus]
    opposing_stats = result["stats"][other]
    plays = [p for p in result["play_by_play"]
             if p.get("attack_side_at_snap", p.get("possession")) == focus]
    drives = [d for d in result["drive_summary"] if d.get("team") == focus]
    points_on_drives = observed_drive_points(result["drive_summary"], focus)
    family_data = {}
    for fam in ACTIVE_FAMILIES:
        ps = [p for p in plays if p.get("play_family") == fam]
        family_data[fam] = {
            "attempts": len(ps),
            "yards": sum(p.get("yards") or 0 for p in ps),
            "nonpositive": sum((p.get("yards") or 0) <= 0 for p in ps),
            "explosive_30": sum((p.get("yards") or 0) >= 30 for p in ps),
        }
    runs = [p for p in plays if p.get("play_family") in RUN_FAMILIES]
    kick_passes = [p for p in plays if p.get("play_family") == "kick_pass"]
    lateral = [p for p in plays if p.get("play_family") == "lateral_spread"]
    # The engine's player/team stats count completions even when a completed
    # kick pass ends in a later fumble; result labels alone would undercount.
    kick_attempts = int(stats.get("kick_passes_attempted", len(kick_passes)))
    kick_completions = int(stats.get("kick_passes_completed", 0))
    if kick_completions > kick_attempts:
        raise ValueError("More kick-pass completions than attempts")
    sacks = sum(int(p.get("sacks", 0) or 0)
                for p in result.get("player_stats", {}).get(other, []))
    read = result.get("defensive_reads", {}).get(other, {})
    energy = [float(p["energy_end"]) for p in result.get("game_day", {})
              .get("energy", {}).get(other, []) if p.get("energy_end") is not None]
    family_rows = [
        dict(offense=offense, defense=defense, formation=formation,
             defense_tier=tier, venue=venue, weather=weather,
             rep=rep, family=fam, **counts)
        for fam, counts in family_data.items()
    ]
    late = [p for p in plays if p.get("down", 0) >= 4]
    attempted_points = float(result["final_score"][focus]["score"])
    scored = sum(x > 0 for x in points_on_drives)
    stops = sum(x <= 0 for x in points_on_drives)
    if len(points_on_drives) != len(drives):
        raise AssertionError("Drive-point attribution lost drives")
    return {
        "offense": offense, "defense": defense, "formation": formation,
        "defense_tier": tier, "venue": venue, "weather": weather,
        "rep": rep, "seed": seed, "offense_roster": offense_name,
        "defense_roster": defender_name,
        "offensive_points": attempted_points,
        "touchdowns": int(stats.get("touchdowns", 0)),
        "snap_kicks_made": int(stats.get("drop_kicks_made", 0)),
        "place_kicks_made": int(stats.get("place_kicks_made", 0)),
        "drives": len(drives),
        "attacking_drive_points": sum(points_on_drives),
        "scoring_drives": scored, "stops": stops,
        "points_per_drive": ratio(sum(points_on_drives), len(drives)),
        "plays": len(plays),
        "run_plays": len(runs),
        "run_yards": sum(p.get("yards") or 0 for p in runs),
        "run_ypp": ratio(sum(p.get("yards") or 0 for p in runs), len(runs)),
        "kick_pass_attempts": kick_attempts,
        "kick_pass_completions": kick_completions,
        "kick_pass_completion": ratio(kick_completions, kick_attempts),
        "sacks_allowed": sacks,
        "sacks_per_kick_pass": ratio(sacks, kick_attempts),
        "kick_pass_yards": sum(p.get("yards") or 0 for p in kick_passes),
        "lateral_plays": len(lateral),
        "lateral_yards": sum(p.get("yards") or 0 for p in lateral),
        "lateral_ints": int(stats.get("lateral_interceptions", 0)),
        "fumbles_lost": int(stats.get("fumbles_lost", 0)),
        "turnovers": sum(int(stats.get(k, 0))
                         for k in ("fumbles_lost", "kick_pass_interceptions", "lateral_interceptions")),
        "defensive_bells": int(opposing_stats.get("bells", 0)),
        "explosive_20": sum((p.get("yards") or 0) >= 20 for p in plays),
        "explosive_30": sum((p.get("yards") or 0) >= 30 for p in plays),
        "punt_attempts": int(stats.get("punts", 0)),
        "pindowns": int(stats.get("pindowns", 0)),
        "read_attempts": int(read.get("attempts", 0)),
        "read_successes": int(read.get("reads", 0)),
        "read_rate": ratio(int(read.get("reads", 0)), int(read.get("attempts", 0))),
        "defense_energy_end": avg(energy),
        "late_down_plays": len(late),
        "late_down_stops": sum((p.get("yards") or 0) <= 0 for p in late),
        "observed_formation_plays": sum(
            p.get("formation") == formation for p in plays),
    }, family_rows


def render_one(attacking_team, defending_team, offense, defense, formation,
               tier, venue, weather, rep, seed):
    if attacking_team.name == defending_team.name:
        raise ValueError("A roster cannot attack itself")
    random.seed(seed)  # Some role/archetype rolls precede engine's internal seed.
    home, away = ((attacking_team, defending_team) if venue == "home"
                  else (defending_team, attacking_team))
    overrides = {
        attacking_team.name: offense,
        attacking_team.name + "_defense": "swarm",
        attacking_team.name + "_st": "aces",
        defending_team.name: "balanced",
        defending_team.name + "_defense": defense,
        defending_team.name + "_st": "aces",
    }
    game = ObservedEngine(
        home, away, seed=seed, style_overrides=overrides,
        weather=weather, neutral_site=True,
    )
    natural_formation = game.select_formation
    game.select_formation = lambda: (formation if game.state.possession == venue
                                    else natural_formation())
    result = game.simulate_game()
    if result["home_style" if venue == "home" else "away_style"] != offense:
        raise AssertionError("Offense override was ignored: " + offense)
    if result["away_defense_style" if venue == "home" else "home_defense_style"] != defense:
        raise AssertionError("Defense override was ignored: " + defense)
    if "defensive_reads" not in result:
        raise AssertionError("DEF-01 read instrumentation missing")
    return summarize_game(result, offense, defense, formation, tier, venue,
                          weather, rep, seed, attacking_team.name,
                          defending_team.name)


def aggregate(rows):
    """One row per offense/defense with denominators, not averaged percentages."""
    blocks = defaultdict(list)
    for row in rows:
        blocks[row["offense"], row["defense"]].append(row)
    out = []
    for (off, defense), group in sorted(blocks.items()):
        attempts = sum(r["kick_pass_attempts"] for r in group)
        runs = sum(r["run_plays"] for r in group)
        drives = sum(r["drives"] for r in group)
        reads = sum(r["read_attempts"] for r in group)
        ppds = [r["points_per_drive"] for r in group]
        ci_lo, ci_hi = sample_ci(ppds, stable_seed(12, off, defense))
        out.append({
            "offense": off, "defense": defense, "games": len(group),
            "ppd": round(sum(r["attacking_drive_points"] for r in group) / drives, 3)
                   if drives else None,
            "ppd_ci_low": ci_lo, "ppd_ci_high": ci_hi,
            "points_per_game": round(avg([r["offensive_points"] for r in group]), 3),
            "run_ypp": round(sum(r["run_yards"] for r in group) / runs, 3) if runs else None,
            "run_attempts": runs,
            "kick_pass_pct": round(sum(r["kick_pass_completions"] for r in group) / attempts, 3)
                             if attempts else None,
            "kick_pass_attempts": attempts,
            "sacks_per_kick_pass": round(sum(r["sacks_allowed"] for r in group) / attempts, 3)
                                   if attempts else None,
            "explosive_30_per_game": round(avg([r["explosive_30"] for r in group]), 3),
            "turnovers_per_game": round(avg([r["turnovers"] for r in group]), 3),
            "bells_per_game": round(avg([r["defensive_bells"] for r in group]), 3),
            "stops_per_game": round(avg([r["stops"] for r in group]), 3),
            "stop_rate": round(sum(r["stops"] for r in group) / drives, 3) if drives else None,
            "read_rate": round(sum(r["read_successes"] for r in group) / reads, 3) if reads else None,
            "punt_per_game": round(avg([r["punt_attempts"] for r in group]), 3),
            "pindown_per_game": round(avg([r["pindowns"] for r in group]), 3),
            "defense_energy_end": round(avg([
                r["defense_energy_end"] for r in group if r["defense_energy_end"] is not None
            ]) or 0, 2),
        })
    return out


def paired_scheme_contrasts(rows, baseline="swarm"):
    """Match defense changes to the same offensive context, roster tier and seed."""
    blocks = defaultdict(dict)
    for r in rows:
        key = (r["offense"], r["formation"], r["defense_tier"],
               r["venue"], r["weather"], r["rep"])
        blocks[key][r["defense"]] = r
    result = []
    schemes = sorted({r["defense"] for r in rows})
    for defense in schemes:
        if defense == baseline:
            continue
        for metric in ("points_per_drive", "run_ypp", "kick_pass_completion",
                       "explosive_30", "sacks_allowed", "stops", "defensive_bells"):
            deltas = []
            for block in blocks.values():
                a, b = block.get(defense), block.get(baseline)
                if a is None or b is None:
                    continue
                if a.get(metric) is None or b.get(metric) is None:
                    continue
                deltas.append(a[metric] - b[metric])
            lo, hi = sample_ci(deltas, stable_seed(49, defense, metric))
            result.append({
                "defense": defense,
                "baseline": baseline,
                "metric": metric,
                "paired_games": len(deltas),
                "mean_delta": round(avg(deltas), 3) if deltas else None,
                "delta_ci_low": lo,
                "delta_ci_high": hi,
            })
    return result


def write_csv(path: Path, rows, fields=None):
    if not rows:
        raise ValueError("No rows produced: " + str(path))
    cols = list(fields) if fields is not None else list(rows[0].keys())
    with path.open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


def format_v(x, digits=2):
    if x is None:
        return "n/a"
    return f"{x:.{digits}f}"


def markdown_report(rows, matrix, contrasts, profile, args):
    from collections import Counter
    lines = [
        "# DEF-06: full-engine defensive matchup study",
        "",
        "Generated by scripts/defense_matchup_matrix.py. Figures are measurements",
        "from simulated games, not approved design targets or final balance decisions.",
        "",
        "## Experiment",
        "",
        f"- Games: **{len(rows)}**; offensive styles: **{len(set(r['offense'] for r in rows))}**;",
        f"  defensive schemes: **{len(set(r['defense'] for r in rows))}**;",
        f"  formations: **{', '.join(sorted(set(r['formation'] for r in rows)))}**.",
        f"- Repetitions per condition: {args.reps}; weather: {args.weathers};",
        f"  seed: {args.seed}; home/away mirrored for the focal offense.",
        "- The focal attack uses one fixed real, freshly generated median-strength",
        "  college roster under every offensive style. Defending rosters are a",
        "  matched weak (~15th percentile) and strong (~85th percentile) set,",
        "  held fixed across all schemes. All games use neutral_site=True.",
        f"- Offensive roster: **{profile['offense']['name']}**, rating {profile['offense']['overall']:.1f}.",
        f"- Roster selection fingerprint: `{profile['selection_fingerprint']}`.",
        f"- Weak defense: **{profile['weak']['name']}**, defensive rating {profile['weak']['defense']:.1f}.",
        f"- Strong defense: **{profile['strong']['name']}**, defensive rating {profile['strong']['defense']:.1f}.",
        "- Requested formations are forcibly selected on the focal offense on",
        "  normal scrimmage plays; the opponent's offense retains its usual",
        "  formation choice. Formation results measure a stress test, not",
        "  ordinary coaching frequency or the probability of choosing a shell.",
        "- Distinct rows are game observations. Family statistics count the",
        "  team in possession **before** the snap, including turnover plays.",
        "- 95% intervals below are deterministic percentile bootstrap intervals",
        "  over games. They describe sample variability; they are NOT a proof",
        "  of causal dominance or season-wide league performance.",
        "",
        "## Per-defense summary across the tested contexts",
        "",
        "| Defense | Games | Pts/attacking drive | Run yds/play | Kick pass % | Sacks/KP attempt | 30+ yd plays/game | Stop rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    by_scheme = defaultdict(list)
    for r in rows:
        by_scheme[r["defense"]].append(r)
    for defense, group in sorted(by_scheme.items()):
        drives = sum(g["drives"] for g in group)
        attempts = sum(g["kick_pass_attempts"] for g in group)
        runs = sum(g["run_plays"] for g in group)
        lines.append(
            f"| {defense} | {len(group)} | "
            f"{format_v(ratio(sum(g['attacking_drive_points'] for g in group), drives))} | "
            f"{format_v(ratio(sum(g['run_yards'] for g in group), runs))} | "
            f"{format_v(100 * ratio(sum(g['kick_pass_completions'] for g in group), attempts) if attempts else None, 1)}% | "
            f"{format_v(ratio(sum(g['sacks_allowed'] for g in group), attempts), 3)} | "
            f"{format_v(avg([g['explosive_30'] for g in group]))} | "
            f"{format_v(100 * ratio(sum(g['stops'] for g in group), drives) if drives else None, 1)}% |"
        )
    lines += [
        "",
        "## Paired effects relative to Swarm",
        "",
        "Each difference uses the SAME offense, formation, defensive roster,",
        "home/away role, weather and repetition. Random draw sequences can",
        "diverge once a play outcome changes. Negative differences in points",
        "per attacking drive, run yards or kick completion favor the defense;",
        "positive differences in forced stops or sacks favor the defense.",
        "",
        "| Defense | Δ points/drive (95% CI) | Δ run yds/play | Δ kick-pass completion | Δ 30+ yd plays/game |",
        "|---|---:|---:|---:|---:|",
    ]
    contrast_lookup = {(r["defense"], r["metric"]): r for r in contrasts}
    for defense in sorted(set(r["defense"] for r in contrasts)):
        def get(metric):
            return contrast_lookup[defense, metric]
        ppd = get("points_per_drive")
        run = get("run_ypp")
        kick = get("kick_pass_completion")
        big = get("explosive_30")
        lines.append(
            f"| {defense} | {format_v(ppd['mean_delta'])}"
            f" [{format_v(ppd['delta_ci_low'])}, {format_v(ppd['delta_ci_high'])}] | "
            f"{format_v(run['mean_delta'])} | {format_v(kick['mean_delta'],3)} | "
            f"{format_v(big['mean_delta'])} |"
        )
    lines += [
        "",
        "## Offensive-style × defense matrix",
        "",
        "Metric: points scored **on focal attacking possessions** divided by",
        "the number of those possessions, including live-ball half points.",
        "The per-cell 95% bootstrap intervals are in matrix.csv.",
        "",
        "| Offensive style | " + " | ".join(sorted(set(r["defense"] for r in matrix))) + " |",
        "|---|" + "---:|" * len(set(r["defense"] for r in matrix)),
    ]
    idx = {(r["offense"], r["defense"]): r for r in matrix}
    defenses = sorted({r["defense"] for r in matrix})
    for off in sorted({r["offense"] for r in matrix}):
        lines.append("| " + off + " | " + " | ".join(
            format_v(idx[off, d]["ppd"]) for d in defenses) + " |")
    lines += [
        "",
        "## Interpretation boundaries and follow-up",
        "",
        "- Conditional denominators are in matrix.csv and family.csv. A high",
        "  completion percentage from few kick attempts must not be ranked as",
        "  evidence of better coverage.",
        "- Stop rate is the share of attacking drives with no attacker points",
        "  credited during that drive. Points/drive includes scores logged on",
        "  the attacking drive, including bells, but omits scores while the",
        "  opponent was attacking; it differs from total team points per game.",
        "- 'Sacks' uses defensive player box-score sack counts, while 'pressure'",
        "  without a sack is not exposed as a consistent per-play field. Do not",
        "  infer a blitz or hurry rate from the number of sacks.",
        "- Defensive bells use current opposing team bell totals, which do",
        "  not distinguish a recovery on the focal offense's specific play.",
        "- In-game form, fatigue, field position, turnovers, special teams and",
        "  score-difference restarts still affect these outcomes. The study",
        "  averages some of them but does not individually disable them.",
        "- Compare matched clear/rain observations when both are sampled;",
        "  increase repetitions, test other attacking rosters and rotate the neutral",
        "  opponent's offense before making balance decisions.",
        "- DEF-06 supplies evidence for design decisions; it does not authorize",
        "  any fixed target for close games, home wins, or scoring.",
        "",
        "## Reproduce",
        "",
        "```sh",
        "PYTHONHASHSEED=0 python scripts/defense_matchup_matrix.py"
        + " --reps " + str(args.reps) + " --seed " + str(args.seed)
        + " --offenses " + args.offenses
        + " --defenses " + args.defenses
        + " --formations " + args.formations
        + " --tiers " + args.tiers
        + " --venues " + args.venues
        + " --weathers " + args.weathers + " --out reports/def06",
        "```",
        "",
        "CSV artifacts: games.csv (one row/game), family.csv",
        "(one row/play family/game), matrix.csv (16×8 aggregated cells),",
        "contrasts.csv (paired differences and bootstrap intervals),",
        "metadata.json (schema, rosters and selected conditions).",
        "",
    ]
    return "\n".join(lines)


def parse_choices(raw, universe, label):
    requested = tuple(x.strip() for x in raw.split(",") if x.strip())
    if not requested or len(requested) != len(set(requested)):
        raise ValueError(label + " needs a nonempty list without duplicates")
    unknown = set(requested) - set(universe)
    if unknown:
        raise ValueError(label + " unknown: " + ", ".join(sorted(unknown)))
    return requested


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--seed", type=int, default=20261123)
    p.add_argument("--out", default="reports/def06")
    p.add_argument("--offenses", default=",".join(sorted(OFFENSE_STYLES)))
    p.add_argument("--defenses", default=",".join(sorted(DEFENSE_STYLES)))
    p.add_argument("--formations", default=",".join(FORMATIONS))
    p.add_argument("--tiers", default=",".join(TIERS))
    p.add_argument("--venues", default=",".join(VENUES))
    p.add_argument("--weathers", default="clear")
    args = p.parse_args(argv)
    if args.reps < 1:
        p.error("--reps must be at least one")
    offenses = parse_choices(args.offenses, OFFENSE_STYLES, "offenses")
    defenses = parse_choices(args.defenses, DEFENSE_STYLES, "defenses")
    forms = parse_choices(args.formations, FORMATIONS, "formations")
    tiers = parse_choices(args.tiers, TIERS, "tiers")
    venues = parse_choices(args.venues, VENUES, "venues")
    weather_options = parse_choices(
        args.weathers, ("clear", "rain", "snow", "sleet", "extreme_heat", "heavy_wind"),
        "weathers")
    random.seed(args.seed)
    teams = load_stable_fresh_rosters(ROOT / "data" / "teams")
    attacker, defender_rosters = choose_rosters(teams)
    profile = {
        "offense": {"name": attacker.name, "overall": roster_score(attacker)},
        **{k: {"name": t.name, "defense": roster_score(t, True)}
           for k, t in defender_rosters.items()},
    }
    profile["selection_fingerprint"] = selected_roster_fingerprint(profile)
    total = (len(offenses) * len(defenses) * len(forms) * len(tiers)
             * len(venues) * len(weather_options) * args.reps)
    print("DEF-06 full-engine factorial: " + str(total) + " games", flush=True)
    print("Roster bands: " + json.dumps(profile, sort_keys=True), flush=True)
    print("No score or margin target will be forced.", flush=True)

    rows = []
    family = []
    for offense in offenses:
        for form in forms:
            for tier in tiers:
                for venue in venues:
                    for weather in weather_options:
                        for rep in range(args.reps):
                            # Same seed on all 8 defenses for this context.
                            seed = stable_seed(args.seed, offense, form, tier,
                                               venue, weather, rep)
                            for defense in defenses:
                                row, fam = render_one(
                                    attacker, defender_rosters[tier],
                                    offense, defense, form, tier, venue,
                                    weather, rep, seed)
                                rows.append(row)
                                family.extend(fam)
        print("Completed " + offense + " (" + str(len(rows))
              + "/" + str(total) + " games)", flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    matrix = aggregate(rows)
    contrasts = paired_scheme_contrasts(rows)
    write_csv(out / "games.csv", rows, CSV_FIELDS)
    write_csv(out / "family.csv", family, FAMILY_FIELDS)
    write_csv(out / "matrix.csv", matrix)
    if contrasts:
        write_csv(out / "contrasts.csv", contrasts)
    metadata = {
        "seed": args.seed, "reps": args.reps, "games": len(rows),
        "offenses": offenses, "defenses": defenses, "formations": forms,
        "defense_tiers": tiers, "venues": venues, "weathers": weather_options,
        "rosters": profile, "baseline": "swarm",
        "engine_config": {
            "defensive_reads_enabled": V2_ENGINE_CONFIG.get("defensive_reads_enabled"),
            "defense_scheme_effects_enabled": V2_ENGINE_CONFIG.get("defense_scheme_effects_enabled"),
        },
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf8")
    report = markdown_report(rows, matrix, contrasts, profile, args)
    (out / "report.md").write_text(report, encoding="utf8")
    print("\n" + report, flush=True)
    print("Generated " + str(out) + " (6 files)", flush=True)


if __name__ == "__main__":
    main()
