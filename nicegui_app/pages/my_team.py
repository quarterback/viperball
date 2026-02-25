"""My Team section for the NiceGUI Viperball app.

Provides dashboard, roster, schedule, and dynasty history views for
the user's human-coached team(s).  Migrated from the Streamlit version
in ui/page_modules/section_my_team.py.
"""

from __future__ import annotations

import io
import csv

import plotly.graph_objects as go

from nicegui import ui, run

from ui import api_client
from nicegui_app.helpers import (
    fmt_vb_score,
    format_time,
    safe_filename,
    generate_box_score_markdown,
    generate_play_log_csv,
    generate_drives_csv,
    compute_quarter_scores,
    drive_result_label,
)
from nicegui_app.components import (
    metric_card,
    stat_table,
    notify_error,
    notify_info,
    notify_warning,
    download_button,
    coaching_snapshot_card,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_dashboard_text(team_name: str, record: dict, rank, mode: str) -> str:
    lines = [f"{team_name} Team Summary", "=" * 40, ""]
    lines.append(f"Record: {record['wins']}-{record['losses']}")
    lines.append(f"Power Ranking: #{rank}" if rank else "Power Ranking: N/A")
    if record.get("conference"):
        lines.append(f"Conference: {record.get('conference', '')}")
        lines.append(f"Conference Record: {record.get('conf_wins', 0)}-{record.get('conf_losses', 0)}")
    lines.append(f"Points For: {fmt_vb_score(record['points_for'])}")
    lines.append(f"Points Against: {fmt_vb_score(record['points_against'])}")
    lines.append(f"Point Differential: {fmt_vb_score(record.get('point_differential', 0))}")
    lines.append("")
    lines.append("Viperball Metrics:")
    lines.append(f"  Team Rating: {record.get('avg_opi', 0):.1f}")
    lines.append(f"  Avg Start: {record.get('avg_territory', 0):.1f}")
    lines.append(f"  Conv %: {record.get('avg_pressure', 0):.1f}")
    lines.append(f"  Lateral %: {record.get('avg_chaos', 0):.1f}")
    lines.append(f"  Kick Rating: {record.get('avg_kicking', 0):.1f}")
    if record.get("offense_style"):
        lines.append(f"\nOffense: {record.get('offense_style', '')}")
    if record.get("defense_style"):
        lines.append(f"Defense: {record.get('defense_style', '')}")
    return "\n".join(lines)


def _build_roster_csv(team_name: str, players: list) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "#", "Name", "Position", "Archetype", "Year", "OVR",
        "Speed", "Power", "Agility", "Hands", "Awareness", "Kicking", "Stamina",
    ])
    for p in players:
        ovr = int(round((
            p.get("speed", 0) + p.get("stamina", 0) + p.get("agility", 0)
            + p.get("power", 0) + p.get("awareness", 0) + p.get("hands", 0)
        ) / 6))
        writer.writerow([
            p.get("number", ""),
            p.get("name", ""),
            p.get("position", ""),
            p.get("archetype", ""),
            p.get("year_abbrev", p.get("year", "")),
            ovr,
            p.get("speed", 0),
            p.get("power", 0),
            p.get("agility", 0),
            p.get("hands", 0),
            p.get("awareness", 0),
            p.get("kicking", 0),
            p.get("stamina", 0),
        ])
    return buf.getvalue()


def _build_roster_text(team_name: str, players: list) -> str:
    lines = [f"{team_name} Roster", "=" * len(f"{team_name} Roster"), ""]
    lines.append(
        f"{'#':>3} {'Name':<24} {'Pos':<6} {'Archetype':<18} {'Yr':<6} "
        f"{'OVR':>3} {'SPD':>3} {'PWR':>3} {'AGI':>3} {'HND':>3} "
        f"{'AWR':>3} {'KCK':>3} {'STM':>3}"
    )
    lines.append("-" * 100)
    for p in players:
        ovr = int(round((
            p.get("speed", 0) + p.get("stamina", 0) + p.get("agility", 0)
            + p.get("power", 0) + p.get("awareness", 0) + p.get("hands", 0)
        ) / 6))
        lines.append(
            f"{p.get('number', ''):>3} {p.get('name', ''):<24} {p.get('position', ''):<6} "
            f"{p.get('archetype', ''):<18} {p.get('year_abbrev', p.get('year', '')):<6} "
            f"{ovr:>3} {p.get('speed', 0):>3} {p.get('power', 0):>3} "
            f"{p.get('agility', 0):>3} {p.get('hands', 0):>3} "
            f"{p.get('awareness', 0):>3} {p.get('kicking', 0):>3} {p.get('stamina', 0):>3}"
        )
    return "\n".join(lines)


def _build_team_schedule_csv(team_name: str, entries: list) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Week", "Opponent", "Result", "Score", "Location", "Phase"])
    for e in entries:
        writer.writerow([e["label"], e["opponent"], e["result"], e["score"], e["location"], e["phase"]])
    return buf.getvalue()


def _build_team_schedule_text(team_name: str, entries: list, wins: int, losses: int) -> str:
    lines = [f"{team_name} Schedule ({wins}-{losses})", "=" * 50, ""]
    lines.append(
        f"{'Week':<20} {'Opponent':<28} {'Result':<4} {'Score':<14} {'Loc':<6} {'Phase'}"
    )
    lines.append("-" * 85)
    for e in entries:
        lines.append(
            f"{e['label']:<20} {e['opponent']:<28} {e['result']:<4} "
            f"{e['score']:<14} {e['location']:<6} {e['phase']}"
        )
    lines.append("")
    lines.append(f"Season Record: {wins}-{losses}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Game detail renderer (ported from ui/helpers.py render_game_detail)
# ---------------------------------------------------------------------------

def _render_game_detail_nicegui(result: dict, key_prefix: str = "gd"):
    """Render a full game detail view using NiceGUI components."""
    home = result["final_score"]["home"]
    away = result["final_score"]["away"]
    hs = result["stats"]["home"]
    as_ = result["stats"]["away"]
    plays = result["play_by_play"]
    home_name = home["team"]
    away_name = away["team"]

    winner = home_name if home["score"] > away["score"] else away_name
    w_score = max(home["score"], away["score"])
    l_score = min(home["score"], away["score"])
    loser = away_name if winner == home_name else home_name

    rivalry_tag = ""
    if result.get("is_rivalry_game"):
        rivalry_tag = " -- **RIVALRY**"
    ui.markdown(f"### {winner} {fmt_vb_score(w_score)} - {loser} {fmt_vb_score(l_score)}{rivalry_tag}")

    weather = result.get("weather", "clear")
    seed = result.get("seed", "N/A")
    ui.label(f"Weather: {weather.title()} | Seed: {seed}").classes("text-sm text-gray-500")

    # Coaching snapshot
    home_snap = result.get("home_coaching_snapshot", {})
    away_snap = result.get("away_coaching_snapshot", {})
    if home_snap or away_snap:
        with ui.row().classes("w-full gap-4 mb-2 mt-2"):
            with ui.column().classes("flex-1"):
                coaching_snapshot_card(home_snap, home_name, bg_class="bg-blue-50")
            with ui.column().classes("flex-1"):
                coaching_snapshot_card(away_snap, away_name, bg_class="bg-red-50")

    # Quarter scoring
    home_q, away_q = compute_quarter_scores(plays)
    q_data = [
        {
            "Team": home_name,
            "Q1": fmt_vb_score(home_q[1]), "Q2": fmt_vb_score(home_q[2]),
            "Q3": fmt_vb_score(home_q[3]), "Q4": fmt_vb_score(home_q[4]),
            "Final": fmt_vb_score(home["score"]),
        },
        {
            "Team": away_name,
            "Q1": fmt_vb_score(away_q[1]), "Q2": fmt_vb_score(away_q[2]),
            "Q3": fmt_vb_score(away_q[3]), "Q4": fmt_vb_score(away_q[4]),
            "Final": fmt_vb_score(away["score"]),
        },
    ]
    stat_table(q_data)

    # Team stats
    ui.markdown("**Team Stats**")
    stat_rows = [
        {"Stat": "Touchdowns (9pts)", home_name: f"{hs['touchdowns']} ({hs['touchdowns']*9}pts)", away_name: f"{as_['touchdowns']} ({as_['touchdowns']*9}pts)"},
        {"Stat": "Snap Kicks (5pts)", home_name: f"{hs['drop_kicks_made']}/{hs.get('drop_kicks_attempted',0)}", away_name: f"{as_['drop_kicks_made']}/{as_.get('drop_kicks_attempted',0)}"},
        {"Stat": "Field Goals (3pts)", home_name: f"{hs['place_kicks_made']}/{hs.get('place_kicks_attempted',0)}", away_name: f"{as_['place_kicks_made']}/{as_.get('place_kicks_attempted',0)}"},
        {"Stat": "Pindowns (1pt)", home_name: str(hs.get('pindowns', 0)), away_name: str(as_.get('pindowns', 0))},
        {"Stat": "Strikes (1/2pt)", home_name: str(hs.get('fumble_recoveries', 0)), away_name: str(as_.get('fumble_recoveries', 0))},
        {"Stat": "Total Yards", home_name: str(hs['total_yards']), away_name: str(as_['total_yards'])},
        {"Stat": "Rushing", home_name: f"{hs.get('rushing_carries',0)} car, {hs.get('rushing_yards',0)} yds", away_name: f"{as_.get('rushing_carries',0)} car, {as_.get('rushing_yards',0)} yds"},
        {"Stat": "Lateral Yards", home_name: str(hs.get('lateral_yards', 0)), away_name: str(as_.get('lateral_yards', 0))},
        {"Stat": "KP (Comp/Att)", home_name: f"{hs.get('kick_passes_completed',0)}/{hs.get('kick_passes_attempted',0)}", away_name: f"{as_.get('kick_passes_completed',0)}/{as_.get('kick_passes_attempted',0)}"},
        {"Stat": "Receiving Yds", home_name: str(hs.get('kick_pass_yards', 0)), away_name: str(as_.get('kick_pass_yards', 0))},
        {"Stat": "Receiving TDs", home_name: str(hs.get('kick_pass_tds', 0)), away_name: str(as_.get('kick_pass_tds', 0))},
        {"Stat": "KP INTs", home_name: str(hs.get('kick_pass_interceptions', 0)), away_name: str(as_.get('kick_pass_interceptions', 0))},
        {"Stat": "Yards/Play", home_name: str(hs['yards_per_play']), away_name: str(as_['yards_per_play'])},
        {"Stat": "Total Plays", home_name: str(hs['total_plays']), away_name: str(as_['total_plays'])},
        {"Stat": "Fumbles Lost", home_name: str(hs['fumbles_lost']), away_name: str(as_['fumbles_lost'])},
        {"Stat": "Penalties", home_name: f"{hs.get('penalties',0)} for {hs.get('penalty_yards',0)} yds", away_name: f"{as_.get('penalties',0)} for {as_.get('penalty_yards',0)} yds"},
    ]
    h_delta_dr = hs.get('delta_drives', 0)
    a_delta_dr = as_.get('delta_drives', 0)
    if h_delta_dr or a_delta_dr:
        stat_rows.extend([
            {"Stat": "Delta Yards", home_name: str(hs.get('delta_yards', 0)), away_name: str(as_.get('delta_yards', 0))},
            {"Stat": "Adjusted Yards", home_name: str(hs.get('adjusted_yards', hs['total_yards'])), away_name: str(as_.get('adjusted_yards', as_['total_yards']))},
            {"Stat": "Delta Drives", home_name: str(h_delta_dr), away_name: str(a_delta_dr)},
            {"Stat": "Delta Scores", home_name: str(hs.get('delta_scores', 0)), away_name: str(as_.get('delta_scores', 0))},
        ])
        h_ce = hs.get('compelled_efficiency')
        a_ce = as_.get('compelled_efficiency')
        if h_ce is not None or a_ce is not None:
            stat_rows.append({
                "Stat": "Compelled Eff %",
                home_name: f"{h_ce}%" if h_ce is not None else "\u2014",
                away_name: f"{a_ce}%" if a_ce is not None else "\u2014",
            })
    stat_table(stat_rows)

    # Player stats
    ps = result.get("player_stats", {})
    home_ps = ps.get("home", [])
    away_ps = ps.get("away", [])

    if home_ps or away_ps:
        with ui.expansion("Individual Player Stats", value=True).classes("w-full"):
            for side_label, side_ps, side_name in [("Home", home_ps, home_name), ("Away", away_ps, away_name)]:
                if not side_ps:
                    continue
                ui.markdown(f"**{side_name}**")

                rush_rows = [p for p in side_ps if p.get("rush_carries", 0) > 0]
                if rush_rows:
                    ui.label("Rushing").classes("text-sm text-gray-500")
                    rush_data = []
                    for p in rush_rows:
                        rush_data.append({
                            "Player": f"{p['tag']} {p['name']}",
                            "Arch": p.get("archetype", ""),
                            "CAR": p.get("rush_carries", 0),
                            "Rush Yds": p.get("rushing_yards", 0),
                            "Lat Yds": p.get("lateral_yards", 0),
                            "TD": p["tds"], "FUM": p["fumbles"],
                        })
                    stat_table(rush_data)

                recv_rows = [p for p in side_ps if p.get("kick_pass_receptions", 0) > 0]
                if recv_rows:
                    ui.label("Receiving").classes("text-sm text-gray-500")
                    recv_data = []
                    for p in recv_rows:
                        recv_data.append({
                            "Player": f"{p['tag']} {p['name']}",
                            "Arch": p.get("archetype", ""),
                            "REC": p.get("kick_pass_receptions", 0),
                            "Rec Yds": p.get("kick_pass_yards", 0),
                            "Rec TD": p.get("kick_pass_tds", 0),
                        })
                    stat_table(recv_data)

                passer_rows = [p for p in side_ps if p.get("kick_passes_thrown", 0) > 0]
                if passer_rows:
                    ui.label("Kick Passing").classes("text-sm text-gray-500")
                    kp_data = []
                    for p in passer_rows:
                        kp_data.append({
                            "Player": f"{p['tag']} {p['name']}",
                            "Att": p.get("kick_passes_thrown", 0),
                            "Comp": p.get("kick_passes_completed", 0),
                            "Yds": p.get("kick_pass_yards", 0),
                            "TD": p.get("kick_pass_tds", 0),
                            "INT": p.get("kick_pass_interceptions_thrown", 0),
                        })
                    stat_table(kp_data)

                kick_rows = [p for p in side_ps if p.get("kick_att", 0) > 0]
                if kick_rows:
                    ui.label("Kicking").classes("text-sm text-gray-500")
                    kick_data = []
                    for p in kick_rows:
                        kick_data.append({
                            "Player": f"{p['tag']} {p['name']}",
                            "ATT": p["kick_att"], "MADE": p["kick_made"],
                            "PCT": f"{(p['kick_made']/p['kick_att']*100):.0f}%" if p["kick_att"] > 0 else "\u2014",
                            "BLK": p.get("kick_deflections", 0),
                        })
                    stat_table(kick_data)

                st_rows = [p for p in side_ps if (
                    p.get("kick_returns", 0) + p.get("punt_returns", 0)
                    + p.get("st_tackles", 0) + p.get("keeper_bells", 0)
                    + p.get("coverage_snaps", 0)
                ) > 0]
                if st_rows:
                    ui.label("Special Teams & Defense").classes("text-sm text-gray-500")
                    st_data = []
                    for p in st_rows:
                        st_data.append({
                            "Player": f"{p['tag']} {p['name']}",
                            "KR": p.get("kick_returns", 0),
                            "KR Yds": p.get("kick_return_yards", 0),
                            "KR TD": p.get("kick_return_tds", 0),
                            "PR": p.get("punt_returns", 0),
                            "PR Yds": p.get("punt_return_yards", 0),
                            "PR TD": p.get("punt_return_tds", 0),
                            "Muffs": p.get("muffs", 0),
                            "ST Tkl": p.get("st_tackles", 0),
                            "Bells": p.get("keeper_bells", 0),
                            "Cov": p.get("coverage_snaps", 0),
                        })
                    stat_table(st_data)
                ui.separator()

    # In-game injuries
    in_game_inj = result.get("in_game_injuries", [])
    if in_game_inj:
        with ui.expansion("In-Game Injuries & Substitutions", value=True).classes("w-full"):
            for ig in in_game_inj:
                severity = "OUT FOR SEASON" if ig.get("season_ending") else (ig.get("tier") or "").replace("_", "-").upper()
                cat_labels = {
                    "on_field_contact": "Contact",
                    "on_field_noncontact": "Non-Contact",
                    "practice": "Practice",
                    "off_field": "Off-Field",
                }
                cat = cat_labels.get(ig.get("category", ""), ig.get("category", ""))
                line = f"**{ig['player']}** ({ig['position']}) -- {ig['description']} [{severity}] *({cat})*"
                if ig.get("substitute"):
                    oop = " *(out of position)*" if ig.get("out_of_position") else ""
                    line += f"  \n-> {ig['substitute']} ({ig['sub_position']}) sub in{oop}"
                ui.markdown(line)

    # Drive summary
    drives = result.get("drive_summary", [])
    if drives:
        with ui.expansion("Drive Summary").classes("w-full"):
            drive_rows = []
            for i, d in enumerate(drives):
                team_label = home_name if d["team"] == "home" else away_name
                result_lbl = drive_result_label(d["result"])
                if d.get("delta_drive"):
                    result_lbl += " Δ"
                drive_rows.append({
                    "#": i + 1,
                    "Team": team_label,
                    "Qtr": f"Q{d['quarter']}",
                    "Start": f"{d['start_yard_line']}yd",
                    "Plays": d["plays"],
                    "Yards": d["yards"],
                    "Result": result_lbl,
                })
            stat_table(drive_rows)

    # Play-by-play
    with ui.expansion("Play-by-Play").classes("w-full"):
        play_rows = []
        for p in plays:
            team_label = home_name if p["possession"] == "home" else away_name
            play_rows.append({
                "#": p["play_number"],
                "INJ": "!" if "INJURY:" in p.get("description", "") else "",
                "Team": team_label,
                "Qtr": f"Q{p['quarter']}",
                "Time": format_time(p["time_remaining"]),
                "Down": f"{p['down']}&{p.get('yards_to_go', '')}",
                "FP": f"{p['field_position']}yd",
                "Family": p.get("play_family", ""),
                "Description": p["description"],
                "Yds": p["yards"],
                "Result": p["result"],
            })
        stat_table(play_rows)


# ---------------------------------------------------------------------------
# Dashboard tab
# ---------------------------------------------------------------------------

async def _render_dashboard(session_id: str, mode: str, team_name: str, standings: list):
    record = next((r for r in standings if r["team_name"] == team_name), None)
    if not record:
        notify_warning(f"No standings data found for {team_name}.")
        return

    rank = next((i for i, r in enumerate(standings, 1) if r["team_name"] == team_name), None)

    ui.label(team_name).classes("text-2xl font-bold")

    # Row 1: core record metrics
    with ui.row().classes("w-full flex-wrap gap-4"):
        with ui.column():
            metric_card("Record", f"{record['wins']}-{record['losses']}")
        with ui.column():
            metric_card("Power Index", "\u2014", delta=f"Rank #{rank}" if rank else "")
        with ui.column():
            if record.get("conference"):
                metric_card("Conference", f"{record.get('conf_wins', 0)}-{record.get('conf_losses', 0)}")
            else:
                metric_card("Win %", f"{record.get('win_percentage', 0):.3f}")
        with ui.column():
            if record.get("conference"):
                conf_standing_val = "\u2014"
                try:
                    conf_resp = await run.io_bound(api_client.get_conference_standings, session_id)
                    conf_standings_data = conf_resp.get("conference_standings", {})
                    team_conf = record.get("conference", "")
                    conf_teams = conf_standings_data.get(team_conf, [])
                    conf_standing = next(
                        (i for i, r in enumerate(conf_teams, 1) if r["team_name"] == team_name),
                        None,
                    )
                    if conf_standing:
                        conf_standing_val = f"#{conf_standing}"
                except api_client.APIError:
                    pass
                metric_card("Conf Standing", conf_standing_val)
            else:
                metric_card("Games", str(record.get("games_played", 0)))

    # Row 2: scoring
    with ui.row().classes("w-full flex-wrap gap-4"):
        with ui.column():
            metric_card("Points For", fmt_vb_score(record["points_for"]))
        with ui.column():
            metric_card("Points Against", fmt_vb_score(record["points_against"]))

    # Row 3: viperball metrics
    with ui.row().classes("w-full flex-wrap gap-4"):
        with ui.column():
            metric_card("Team Rating", f"{record.get('avg_opi', 0):.1f}")
        with ui.column():
            metric_card("Avg Start", f"{record.get('avg_territory', 0):.1f}")
        with ui.column():
            metric_card("Conv %", f"{record.get('avg_pressure', 0):.1f}")
        with ui.column():
            metric_card("Lateral %", f"{record.get('avg_chaos', 0):.1f}")
        with ui.column():
            metric_card("Kick Rating", f"{record.get('avg_kicking', 0):.1f}")

    # Radar chart
    if standings:
        n = len(standings)
        avgs = {
            "Team Rating": sum(r.get("avg_opi", 0) for r in standings) / n,
            "Avg Start": sum(r.get("avg_territory", 0) for r in standings) / n,
            "Conv %": sum(r.get("avg_pressure", 0) for r in standings) / n,
            "Lateral %": sum(r.get("avg_chaos", 0) for r in standings) / n,
            "Kick Rating": sum(r.get("avg_kicking", 0) for r in standings) / n,
        }
        categories = list(avgs.keys())
        team_values = [
            record.get("avg_opi", 0), record.get("avg_territory", 0),
            record.get("avg_pressure", 0), record.get("avg_chaos", 0),
            record.get("avg_kicking", 0),
        ]
        avg_values = [avgs[c] for c in categories]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=team_values + [team_values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=team_name,
        ))
        fig.add_trace(go.Scatterpolar(
            r=avg_values + [avg_values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name="League Average",
            opacity=0.4,
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title="Team Metrics vs League Average",
            height=420,
            template="plotly_white",
        )
        ui.plotly(fig).classes("w-full")

    # Dynasty coach profile
    if mode == "dynasty":
        ui.separator()
        ui.label("Coach Profile").classes("text-xl font-bold")
        try:
            dyn_status = await run.io_bound(api_client.get_dynasty_status, session_id)
            coach = dyn_status.get("coach", {})
            with ui.row().classes("w-full flex-wrap gap-4"):
                with ui.column():
                    metric_card("Career Record", f"{coach.get('career_wins', 0)}-{coach.get('career_losses', 0)}")
                with ui.column():
                    metric_card("Win %", f"{coach.get('win_percentage', 0):.3f}")
                with ui.column():
                    metric_card("Championships", str(coach.get("championships", 0)))
                with ui.column():
                    metric_card("Years Experience", str(coach.get("years_experience", 0)))
        except api_client.APIError:
            pass

    # Injury report
    ui.separator()
    ui.label("Injury Report").classes("text-xl font-bold")
    try:
        inj_resp = await run.io_bound(api_client.get_injuries, session_id, team=team_name)
        active_inj = inj_resp.get("active", [])
        team_log = inj_resp.get("season_log", [])
        penalties = inj_resp.get("penalties", {})

        q_count = sum(1 for i in active_inj if i.get("tier") == "day_to_day")
        out_count = sum(
            1 for i in active_inj
            if i.get("tier") not in ("day_to_day", "severe") and not i.get("is_season_ending")
        )
        se_count = sum(
            1 for i in active_inj
            if i.get("is_season_ending") or i.get("tier") == "severe"
        )

        with ui.row().classes("w-full flex-wrap gap-4"):
            with ui.column():
                metric_card("Active Injuries", len(active_inj))
            with ui.column():
                metric_card("Questionable", q_count)
            with ui.column():
                metric_card("Out", out_count)
            with ui.column():
                metric_card("Season-Ending", se_count)
            with ui.column():
                metric_card("Season Total", len(team_log))

        if active_inj:
            inj_rows = []
            for inj in active_inj:
                status = (
                    "OUT FOR SEASON"
                    if inj.get("is_season_ending") or inj.get("tier") == "severe"
                    else (inj.get("game_status") or "OUT").upper()
                )
                orig_wks = inj.get("original_weeks_out", inj.get("weeks_out", 0))
                cur_wks = inj.get("weeks_out", 0)
                if status == "OUT FOR SEASON":
                    timeline = "Season-ending"
                elif orig_wks != cur_wks and orig_wks > 0:
                    timeline = f"{cur_wks} wk (was {orig_wks})"
                else:
                    timeline = f"{cur_wks} wk" if cur_wks else "DTD"
                recovery = inj.get("recovery_note", "")
                inj_rows.append({
                    "Player": inj.get("player_name", ""),
                    "Position": inj.get("position", ""),
                    "Injury": inj.get("description", ""),
                    "Status": status,
                    "Timeline": timeline,
                    "Return": (
                        "Season-ending" if status == "OUT FOR SEASON"
                        else f"Wk {inj.get('week_return', '?')}"
                    ),
                    "Recovery": recovery if recovery else "\u2014",
                })
            stat_table(inj_rows)
        else:
            ui.label("No active injuries -- full health!").classes("text-sm text-gray-500")

        if penalties and any(v != 1.0 for v in penalties.values()):
            ui.markdown("**Injury Impact on Performance**")
            yards_delta = round((penalties.get("yards_penalty", 1.0) - 1.0) * 100, 1)
            kick_delta = round((penalties.get("kick_penalty", 1.0) - 1.0) * 100, 1)
            lat_delta = round((penalties.get("lateral_penalty", 1.0) - 1.0) * 100, 1)
            with ui.row().classes("w-full flex-wrap gap-4"):
                with ui.column():
                    metric_card("Yards Impact", f"{yards_delta:+.1f}%", delta=f"{yards_delta:.1f}%")
                with ui.column():
                    metric_card("Kicking Impact", f"{kick_delta:+.1f}%", delta=f"{kick_delta:.1f}%")
                with ui.column():
                    metric_card("Lateral Impact", f"{lat_delta:+.1f}%", delta=f"{lat_delta:.1f}%")

        if team_log:
            with ui.expansion("Season Injury History").classes("w-full"):
                log_rows = []
                for inj in team_log:
                    log_rows.append({
                        "Week": inj.get("week_injured", ""),
                        "Player": inj.get("player_name", ""),
                        "Injury": inj.get("description", ""),
                        "Body Part": (inj.get("body_part") or "").title(),
                        "Severity": (inj.get("tier") or "").replace("_", "-").title(),
                        "In-Game": "Yes" if inj.get("in_game") else "No",
                        "Weeks Out": inj.get("weeks_out", ""),
                    })
                stat_table(log_rows)
    except api_client.APIError:
        ui.label("Injury data not available.").classes("text-sm text-gray-500")

    # Export
    ui.separator()
    summary = _build_dashboard_text(team_name, record, rank, mode)
    with ui.row().classes("w-full flex-wrap gap-4"):
        with ui.column():
            download_button(
                "Download Team Summary (Text)",
                summary,
                filename=f"{safe_filename(team_name)}_summary.txt",
                mime="text/plain",
            )
        with ui.column():
            copy_container = ui.column().classes("w-full")

            def _show_copy_summary():
                copy_container.clear()
                with copy_container:
                    ui.code(summary)
                    ui.label("Select all and copy the text above.").classes("text-sm text-gray-500")

            ui.button("Copy Team Summary", on_click=_show_copy_summary, icon="content_copy")


# ---------------------------------------------------------------------------
# Roster tab
# ---------------------------------------------------------------------------

async def _render_roster(session_id: str, team_name: str):
    try:
        roster_resp = await run.io_bound(api_client.get_team_roster, session_id, team_name)
        players = roster_resp.get("players", [])
    except api_client.APIError:
        notify_warning(f"Could not load roster for {team_name}.")
        return

    inj_map: dict[str, str] = {}
    try:
        inj_resp = await run.io_bound(api_client.get_injuries, session_id, team=team_name)
        for inj in inj_resp.get("active", []):
            pname = inj.get("player_name", "")
            if inj.get("is_season_ending") or inj.get("tier") == "severe":
                inj_map[pname] = f"OUT FOR SEASON ({inj.get('description', '')})"
            elif inj.get("tier") in ("moderate", "major"):
                inj_map[pname] = f"OUT ({inj.get('description', '')}, Wk {inj.get('week_return', '?')})"
            elif inj.get("tier") == "minor":
                inj_map[pname] = f"DOUBTFUL ({inj.get('description', '')})"
            elif inj.get("tier") == "day_to_day":
                inj_map[pname] = f"QUESTIONABLE ({inj.get('description', '')})"
            else:
                inj_map[pname] = f"OUT ({inj.get('description', '')})"
    except api_client.APIError:
        pass

    # Build roster data
    roster_data = []
    for p in players:
        ovr = p.get("overall", int(round((
            p.get("speed", 0) + p.get("stamina", 0) + p.get("agility", 0)
            + p.get("power", 0) + p.get("awareness", 0) + p.get("hands", 0)
        ) / 6)))
        depth = p.get("depth_rank", 0)
        role = "Starter" if depth == 1 else f"Backup #{depth}" if depth <= 3 else "Reserve"
        rs_status = ""
        if p.get("redshirt", False):
            rs_status = "RS"
        elif p.get("redshirt_used", False):
            rs_status = "Used"
        elif p.get("redshirt_eligible", False):
            rs_status = "Eligible"
        player_name = p.get("name", "")
        health_status = inj_map.get(player_name, "HEALTHY")
        roster_data.append({
            "Name": f"{player_name} ({p.get('position', '')} #{p.get('number', '')})",
            "Year": p.get("year_abbr", p.get("year_abbrev", p.get("year", ""))),
            "Status": health_status,
            "Role": role,
            "RS": rs_status,
            "Archetype": p.get("archetype", ""),
            "Position": p.get("position", ""),
            "OVR": ovr,
            "GP": p.get("season_games_played", 0),
            "Speed": p.get("speed", 0),
            "Power": p.get("power", 0),
            "Agility": p.get("agility", 0),
            "Hands": p.get("hands", 0),
            "Awareness": p.get("awareness", 0),
            "Kicking": p.get("kicking", 0),
            "Stamina": p.get("stamina", 0),
        })

    if not roster_data:
        notify_info("No players found on this roster.")
        return

    # Refreshable roster view container
    roster_container = ui.column().classes("w-full")

    def _render_full_roster():
        roster_container.clear()
        with roster_container:
            stat_table(roster_data)

    def _render_depth_chart():
        roster_container.clear()
        with roster_container:
            positions_order = [
                "Viper", "VP", "Zeroback", "ZB", "Halfback", "HB",
                "Wingback", "WB", "Slotback", "SB", "Keeper", "KP",
                "Offensive Line", "OL", "Defensive Line", "DL",
            ]
            pos_groups: dict[str, list] = {}
            for r in roster_data:
                pos = r["Position"]
                pos_groups.setdefault(pos, []).append(r)
            for pos in sorted(
                pos_groups.keys(),
                key=lambda x: positions_order.index(x) if x in positions_order else 99,
            ):
                group = sorted(pos_groups[pos], key=lambda x: -int(x["OVR"]))
                ui.markdown(f"**{pos}**")
                dc_cols = ["Name", "Status", "Role", "Year", "RS", "OVR", "GP", "Archetype", "Speed", "Power", "Awareness"]
                dc_rows = [{k: r[k] for k in dc_cols} for r in group]
                stat_table(dc_rows, columns=dc_cols)

    # View toggle using radio
    view_toggle = ui.radio(
        ["Full Roster", "Depth Chart"],
        value="Full Roster",
    ).props("inline")

    def _on_view_change(e):
        if e.value == "Depth Chart":
            _render_depth_chart()
        else:
            _render_full_roster()

    view_toggle.on("update:model-value", _on_view_change)

    # Initial render
    _render_full_roster()

    # Export buttons
    ui.separator()
    with ui.row().classes("w-full flex-wrap gap-4"):
        with ui.column():
            download_button(
                "Download Roster CSV",
                _build_roster_csv(team_name, players),
                filename=f"{safe_filename(team_name)}_roster.csv",
                mime="text/csv",
            )
        with ui.column():
            roster_text = _build_roster_text(team_name, players)
            download_button(
                "Download Roster (Text)",
                roster_text,
                filename=f"{safe_filename(team_name)}_roster.txt",
                mime="text/plain",
            )
        with ui.column():
            copy_container = ui.column().classes("w-full")

            def _show_copy_roster():
                copy_container.clear()
                with copy_container:
                    ui.code(_build_roster_text(team_name, players))
                    ui.label("Select all and copy the text above.").classes("text-sm text-gray-500")

            ui.button("Copy Roster to Clipboard", on_click=_show_copy_roster, icon="content_copy")


# ---------------------------------------------------------------------------
# Schedule tab
# ---------------------------------------------------------------------------

async def _render_schedule(session_id: str, mode: str, team_name: str):
    # Fetch completed games (with full result) AND all games (for upcoming)
    try:
        def _fetch_both():
            completed = api_client.get_schedule(session_id, team=team_name, completed_only=True, include_full_result=True)
            all_games = api_client.get_schedule(session_id, team=team_name)
            return completed, all_games
        completed_resp, all_resp = await run.io_bound(_fetch_both)
        completed_games = completed_resp.get("games", [])
        all_games = all_resp.get("games", [])
    except api_client.APIError:
        completed_games = []
        all_games = []

    try:
        bracket_resp = await run.io_bound(api_client.get_playoff_bracket, session_id)
        bracket = bracket_resp.get("bracket", [])
    except api_client.APIError:
        bracket = []

    try:
        bowls_resp = await run.io_bound(api_client.get_bowl_results, session_id)
        bowl_results = bowls_resp.get("bowl_results", [])
    except api_client.APIError:
        bowl_results = []

    entries: list[dict] = []

    # Completed games (with full result data)
    for g in completed_games:
        if g.get("completed") and (g.get("home_team") == team_name or g.get("away_team") == team_name):
            is_home = g.get("home_team") == team_name
            opponent = g.get("away_team") if is_home else g.get("home_team")
            team_score = g.get("home_score") if is_home else g.get("away_score")
            opp_score = g.get("away_score") if is_home else g.get("home_score")
            won = (team_score or 0) > (opp_score or 0)
            entries.append({
                "game": g,
                "week": g.get("week", 0),
                "opponent": opponent,
                "result": "W" if won else "L",
                "score": f"{fmt_vb_score(team_score or 0)} - {fmt_vb_score(opp_score or 0)}",
                "location": "Home" if is_home else "Away",
                "phase": "Regular Season",
                "sort_key": g.get("week", 0),
                "label": f"Wk {g.get('week', 0)}",
            })

    # Upcoming games
    completed_weeks = {e["week"] for e in entries}
    for g in all_games:
        if not g.get("completed") and (g.get("home_team") == team_name or g.get("away_team") == team_name):
            wk = g.get("week", 0)
            if wk in completed_weeks:
                continue
            is_home = g.get("home_team") == team_name
            opponent = g.get("away_team") if is_home else g.get("home_team")
            is_conf = g.get("is_conference_game", False)
            entries.append({
                "game": g,
                "week": wk,
                "opponent": opponent,
                "result": "—",
                "score": f"{'Conf' if is_conf else 'NC'}",
                "location": "Home" if is_home else "Away",
                "phase": "Regular Season",
                "sort_key": wk,
                "label": f"Wk {wk}",
            })

    if bracket:
        playoff_round_names = {
            996: "Opening Round", 997: "First Round",
            998: "Quarterfinals", 999: "Semi-Finals", 1000: "Championship",
        }
        for g in bracket:
            if g.get("completed") and (g.get("home_team") == team_name or g.get("away_team") == team_name):
                is_home = g.get("home_team") == team_name
                opponent = g.get("away_team") if is_home else g.get("home_team")
                team_score = g.get("home_score") if is_home else g.get("away_score")
                opp_score = g.get("away_score") if is_home else g.get("home_score")
                won = (team_score or 0) > (opp_score or 0)
                round_label = playoff_round_names.get(g.get("week", 0), f"Playoff R{g.get('week', 0)}")
                entries.append({
                    "game": g,
                    "week": 900 + g.get("week", 0),
                    "opponent": opponent,
                    "result": "W" if won else "L",
                    "score": f"{fmt_vb_score(team_score or 0)} - {fmt_vb_score(opp_score or 0)}",
                    "location": "Home" if is_home else "Away",
                    "phase": "Playoff",
                    "sort_key": 900 + g.get("week", 0),
                    "label": round_label,
                })

    if bowl_results:
        for i, bowl in enumerate(bowl_results):
            bg = bowl.get("game", {})
            if bg.get("completed") and (bg.get("home_team") == team_name or bg.get("away_team") == team_name):
                is_home = bg.get("home_team") == team_name
                opponent = bg.get("away_team") if is_home else bg.get("home_team")
                team_score = bg.get("home_score") if is_home else bg.get("away_score")
                opp_score = bg.get("away_score") if is_home else bg.get("home_score")
                won = (team_score or 0) > (opp_score or 0)
                entries.append({
                    "game": bg,
                    "week": 800 + i,
                    "opponent": opponent,
                    "result": "W" if won else "L",
                    "score": f"{fmt_vb_score(team_score or 0)} - {fmt_vb_score(opp_score or 0)}",
                    "location": "Home" if is_home else "Away",
                    "phase": "Bowl",
                    "sort_key": 800 + i,
                    "label": bowl.get("name", f"Bowl {i+1}"),
                })

    entries.sort(key=lambda e: e["sort_key"])

    if not entries:
        notify_info("No games scheduled for this team yet.")
        return

    played = [e for e in entries if e["result"] in ("W", "L")]
    wins = sum(1 for e in played if e["result"] == "W")
    losses = len(played) - wins

    # Schedule table
    sched_rows = []
    for e in entries:
        sched_rows.append({
            "Week": e["label"],
            "Opponent": e["opponent"],
            "Result": e["result"],
            "Score": e["score"],
            "Location": e["location"],
            "Phase": e["phase"],
        })
    stat_table(sched_rows)

    # Export buttons
    ui.separator()
    sched_csv = _build_team_schedule_csv(team_name, entries)
    sched_text = _build_team_schedule_text(team_name, entries, wins, losses)

    with ui.row().classes("w-full flex-wrap gap-4"):
        with ui.column():
            download_button(
                "Download Schedule CSV",
                sched_csv,
                filename=f"{safe_filename(team_name)}_schedule.csv",
                mime="text/csv",
            )
        with ui.column():
            download_button(
                "Download Schedule (Text)",
                sched_text,
                filename=f"{safe_filename(team_name)}_schedule.txt",
                mime="text/plain",
            )
        with ui.column():
            copy_container = ui.column().classes("w-full")

            def _show_copy_schedule():
                copy_container.clear()
                with copy_container:
                    ui.code(sched_text)
                    ui.label("Select all and copy the text above.").classes("text-sm text-gray-500")

            ui.button("Copy Schedule to Clipboard", on_click=_show_copy_schedule, icon="content_copy")

    # Game detail selector
    ui.separator()
    game_labels = [f"{e['label']}: vs {e['opponent']} ({e['result']}) {e['score']}" for e in entries]
    game_detail_container = ui.column().classes("w-full")

    def _on_game_selected(e):
        selected = e.value
        if not selected:
            return
        idx = game_labels.index(selected)
        g = entries[idx]["game"]
        full_result = g.get("full_result")

        game_detail_container.clear()
        with game_detail_container:
            if full_result:
                with ui.expansion("Game Details", value=True).classes("w-full"):
                    _render_game_detail_nicegui(full_result, key_prefix=f"myteam_gd_{idx}")

                box_md = generate_box_score_markdown(full_result)
                with ui.expansion("Share This Game").classes("w-full"):
                    ui.label("Copy the box score below to share on forums or elsewhere.").classes("text-sm text-gray-500")
                    with ui.row().classes("w-full flex-wrap gap-4"):
                        with ui.column():
                            download_button(
                                "Download Box Score (Markdown)",
                                box_md,
                                filename=f"{safe_filename(team_name)}_wk{entries[idx]['week']}_boxscore.md",
                                mime="text/markdown",
                            )
                        with ui.column():
                            download_button(
                                "Download Play Log (CSV)",
                                generate_play_log_csv(full_result),
                                filename=f"{safe_filename(team_name)}_wk{entries[idx]['week']}_plays.csv",
                                mime="text/csv",
                            )
                        with ui.column():
                            download_button(
                                "Download Drives (CSV)",
                                generate_drives_csv(full_result),
                                filename=f"{safe_filename(team_name)}_wk{entries[idx]['week']}_drives.csv",
                                mime="text/csv",
                            )

                    box_copy_container = ui.column().classes("w-full")

                    def _show_box_copy(md=box_md):
                        box_copy_container.clear()
                        with box_copy_container:
                            ui.code(md, language="markdown")
                            ui.label("Select all and copy the text above.").classes("text-sm text-gray-500")

                    ui.button("Show Box Score for Copying", on_click=_show_box_copy, icon="content_copy")

    ui.select(
        game_labels,
        label="Select a game to view details",
        on_change=_on_game_selected,
    ).classes("w-full max-w-xl")


# ---------------------------------------------------------------------------
# History tab (dynasty only)
# ---------------------------------------------------------------------------

async def _render_history(session_id: str):
    try:
        dyn_status = await run.io_bound(api_client.get_dynasty_status, session_id)
        coach = dyn_status.get("coach", {})
    except api_client.APIError:
        notify_error("Could not load dynasty data.")
        return

    team_name = coach.get("team", "")

    ui.label("Coach Career").classes("text-xl font-bold")
    with ui.row().classes("w-full flex-wrap gap-4"):
        with ui.column():
            metric_card("Career Record", f"{coach.get('career_wins', 0)}-{coach.get('career_losses', 0)}")
        with ui.column():
            metric_card("Win %", f"{coach.get('win_percentage', 0):.3f}")
        with ui.column():
            metric_card("Championships", str(coach.get("championships", 0)))
        with ui.column():
            metric_card("Seasons", str(coach.get("years_experience", 0)))

    season_records = coach.get("season_records", {})
    if season_records:
        season_rows = []
        for year in sorted(season_records.keys(), key=lambda y: int(y)):
            sr = season_records[year]
            season_rows.append({
                "Year": year,
                "W-L": f"{sr.get('wins', 0)}-{sr.get('losses', 0)}",
                "PF": fmt_vb_score(sr.get("points_for", 0)),
                "PA": fmt_vb_score(sr.get("points_against", 0)),
                "Playoff": "Y" if sr.get("playoff") else "N",
                "Champion": "Y" if sr.get("champion") else "N",
            })
        stat_table(season_rows)

        # Wins per season bar chart
        import plotly.express as px
        wins_data = {
            "Year": [],
            "Wins": [],
        }
        for y in sorted(season_records.keys(), key=lambda y: int(y)):
            wins_data["Year"].append(str(y))
            wins_data["Wins"].append(season_records[y].get("wins", 0))
        if wins_data["Year"]:
            fig = px.bar(wins_data, x="Year", y="Wins", title="Wins Per Season")
            fig.update_layout(height=350, template="plotly_white")
            ui.plotly(fig).classes("w-full")

    # Coaching history
    ui.separator()
    ui.label("Coaching History").classes("text-xl font-bold")
    try:
        ch_resp = await run.io_bound(api_client.get_dynasty_coaching_history, session_id)
        coaching_hist = ch_resp.get("coaching_history", {})
        current_staffs = ch_resp.get("current_staffs", {})
    except api_client.APIError:
        coaching_hist = {}
        current_staffs = {}

    my_staff = current_staffs.get(team_name, {})
    if my_staff:
        with ui.row().classes("w-full flex-wrap gap-4"):
            with ui.column():
                metric_card("Head Coach", my_staff.get("hc_name", "Unknown"))
            with ui.column():
                metric_card(
                    "Classification",
                    my_staff.get("hc_classification", "unclassified").replace("_", " ").title(),
                )
            with ui.column():
                metric_card("HC Record", my_staff.get("hc_record", "0-0"))

    if coaching_hist:
        with ui.expansion("Coaching Changes by Year").classes("w-full"):
            def _safe_year_sort(y):
                try:
                    return int(y)
                except (ValueError, TypeError):
                    return 0

            for year in sorted(coaching_hist.keys(), key=_safe_year_sort):
                yr_data = coaching_hist[year]
                n_changes = yr_data.get("teams_with_changes", 0)
                if n_changes > 0:
                    changes = yr_data.get("changes", {})
                    my_changes = changes.get(team_name, {})
                    if my_changes:
                        ui.markdown(f"**Year {year}** -- Your team had coaching changes:")
                        for role, info in my_changes.items():
                            if isinstance(info, dict):
                                ui.label(
                                    f"  {role}: {info.get('new', 'N/A')} (replaced {info.get('old', 'N/A')})"
                                ).classes("text-sm text-gray-500")
                            else:
                                ui.label(f"  {role}: {info}").classes("text-sm text-gray-500")
                    else:
                        ui.label(
                            f"Year {year}: {n_changes} team(s) had coaching changes (none on your team)"
                        ).classes("text-sm text-gray-500")

    # Team history
    ui.separator()
    ui.label("Team History").classes("text-xl font-bold")
    try:
        histories_resp = await run.io_bound(api_client.get_dynasty_team_histories, session_id)
        team_hist = histories_resp.get("team_histories", {}).get(team_name, {})
    except api_client.APIError:
        team_hist = {}

    if team_hist:
        with ui.row().classes("w-full flex-wrap gap-4"):
            with ui.column():
                metric_card(
                    "All-Time Record",
                    f"{team_hist.get('total_wins', 0)}-{team_hist.get('total_losses', 0)}",
                )
            with ui.column():
                metric_card("Win %", f"{team_hist.get('win_percentage', 0):.3f}")
            with ui.column():
                metric_card("Championships", str(team_hist.get("total_championships", 0)))
            with ui.column():
                metric_card("Playoff Appearances", str(team_hist.get("total_playoff_appearances", 0)))

        champ_years = team_hist.get("championship_years", [])
        if champ_years:
            ui.label(
                f"Championship Years: {', '.join(str(y) for y in sorted(champ_years))}"
            ).classes("text-sm text-gray-500")

    # Record book
    ui.separator()
    ui.label("Record Book").classes("text-xl font-bold")
    try:
        rb = await run.io_bound(api_client.get_dynasty_record_book, session_id)
    except api_client.APIError:
        rb = {}

    ui.markdown("**Single-Season Records**")
    ss_records = []
    most_wins = rb.get("most_wins_season", {})
    if most_wins.get("team"):
        ss_records.append({
            "Record": "Most Wins", "Team": most_wins["team"],
            "Value": str(most_wins.get("wins", 0)), "Year": str(most_wins.get("year", "")),
        })
    most_points = rb.get("most_points_season", {})
    if most_points.get("team"):
        ss_records.append({
            "Record": "Most Points", "Team": most_points["team"],
            "Value": fmt_vb_score(most_points.get("points", 0)), "Year": str(most_points.get("year", "")),
        })
    best_def = rb.get("best_defense_season", {})
    if best_def.get("team"):
        ss_records.append({
            "Record": "Best Defense (PPG)", "Team": best_def["team"],
            "Value": f"{best_def.get('ppg_allowed', 0):.1f}", "Year": str(best_def.get("year", "")),
        })
    highest_opi = rb.get("highest_opi_season", {})
    if highest_opi.get("team"):
        ss_records.append({
            "Record": "Highest Team Rating", "Team": highest_opi["team"],
            "Value": f"{highest_opi.get('opi', 0):.1f}", "Year": str(highest_opi.get("year", "")),
        })
    most_chaos = rb.get("most_chaos_season", {})
    if most_chaos.get("team"):
        ss_records.append({
            "Record": "Best Lateral %", "Team": most_chaos["team"],
            "Value": f"{most_chaos.get('chaos', 0):.1f}", "Year": str(most_chaos.get("year", "")),
        })
    if ss_records:
        stat_table(ss_records)

    ui.markdown("**All-Time Records**")
    at_records = []
    most_champs = rb.get("most_championships", {})
    if most_champs.get("team"):
        at_records.append({
            "Record": "Most Championships",
            "Team/Coach": most_champs["team"],
            "Value": str(most_champs.get("championships", 0)),
        })
    highest_win = rb.get("highest_win_percentage", {})
    if highest_win.get("team"):
        at_records.append({
            "Record": "Highest Win %",
            "Team/Coach": highest_win["team"],
            "Value": f"{highest_win.get('win_pct', 0):.3f}",
        })
    most_coaching = rb.get("most_coaching_wins", {})
    if most_coaching.get("coach"):
        at_records.append({
            "Record": "Most Coaching Wins",
            "Team/Coach": most_coaching["coach"],
            "Value": str(most_coaching.get("wins", 0)),
        })
    most_coach_champs = rb.get("most_coaching_championships", {})
    if most_coach_champs.get("coach"):
        at_records.append({
            "Record": "Most Coaching Championships",
            "Team/Coach": most_coach_champs["coach"],
            "Value": str(most_coach_champs.get("championships", 0)),
        })
    if at_records:
        stat_table(at_records)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def render_my_team_section(state, shared):
    """Render the My Team page.

    Parameters
    ----------
    state : UserState
        Per-user mutable state (replaces st.session_state).
    shared : dict
        Shared application data (teams, styles, etc.).
    """
    session_id = state.session_id
    mode = state.mode

    if not session_id or not mode:
        ui.label("My Team").classes("text-2xl font-bold")
        notify_info("No active session found. Go to Play to start a new season or dynasty.")
        return

    # -- Parallel initial fetch ------------------------------------------------
    if mode == "dynasty":
        try:
            def _do_fetch():
                return api_client.fetch_parallel(
                    lambda: api_client.get_dynasty_status(session_id),
                    lambda: api_client.get_standings(session_id),
                )
            dyn_resp, standings_resp = await run.io_bound(_do_fetch)
            human_teams = [dyn_resp.get("coach", {}).get("team", "")]
        except api_client.APIError:
            ui.label("My Team").classes("text-2xl font-bold")
            notify_error("Could not load dynasty data.")
            return
    else:
        human_teams = state.human_teams or []
        try:
            standings_resp = await run.io_bound(api_client.get_standings, session_id)
        except api_client.APIError:
            ui.label("My Team").classes("text-2xl font-bold")
            notify_info("No season data available yet. Simulate a season from Play to see your team's data.")
            return

    if not human_teams or not any(human_teams):
        ui.label("My Team").classes("text-2xl font-bold")
        notify_info("No human-coached teams in this session. Go to Play to start a new one with your team selected.")
        return

    standings = standings_resp.get("standings", []) if standings_resp else []
    if not standings:
        ui.label("My Team").classes("text-2xl font-bold")
        notify_info("No season data available yet. Simulate a season from Play to see your team's data.")
        return

    if not standings:
        ui.label("My Team").classes("text-2xl font-bold")
        notify_info("No season data available yet. Simulate a season from Play to see your team's data.")
        return

    # Team selector (for multi-team sessions)
    selected_team_ref = {"value": human_teams[0]}

    # Build tab names
    tab_names = ["Dashboard", "Roster", "Schedule"]
    if mode == "dynasty":
        tab_names.append("History")

    # Content container that gets refreshed when team selection changes
    content_container = ui.column().classes("w-full")

    async def _render_content(team_name: str):
        content_container.clear()
        with content_container:
            with ui.tabs().classes("w-full").props("mobile-arrows outside-arrows") as tabs:
                dashboard_tab = ui.tab("Dashboard")
                roster_tab = ui.tab("Roster")
                schedule_tab = ui.tab("Schedule")
                history_tab = None
                if mode == "dynasty":
                    history_tab = ui.tab("History")

            with ui.tab_panels(tabs, value=dashboard_tab).classes("w-full"):
                with ui.tab_panel(dashboard_tab):
                    await _render_dashboard(session_id, mode, team_name, standings)

                with ui.tab_panel(roster_tab):
                    await _render_roster(session_id, team_name)

                with ui.tab_panel(schedule_tab):
                    await _render_schedule(session_id, mode, team_name)

                if mode == "dynasty" and history_tab is not None:
                    with ui.tab_panel(history_tab):
                        await _render_history(session_id)

    if len(human_teams) > 1:
        async def _on_team_change(e):
            selected_team_ref["value"] = e.value
            await _render_content(e.value)

        ui.select(
            human_teams,
            value=human_teams[0],
            label="Select Team",
            on_change=_on_team_change,
        )

    await _render_content(selected_team_ref["value"])
