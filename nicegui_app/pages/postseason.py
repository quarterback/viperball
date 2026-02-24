"""Postseason display components — visual bracket and bowl game cards.

Renders playoff brackets as a round-by-round tournament view with matchup
cards, seed numbers, and champion highlight.  Bowl games are displayed as
tier-grouped cards with team records and scores.
"""

from __future__ import annotations
from typing import Optional
from nicegui import ui
from nicegui_app.helpers import fmt_vb_score
from engine.season import BOWL_TIERS


ROUND_LABELS = {
    995: "Play-In Round",
    996: "Round of 32",
    997: "Round of 16",
    998: "Quarterfinals",
    999: "Semifinals",
    1000: "CVL National Championship",
}

ROUND_LABELS_SMALL = {
    999: "Semifinals",
    1000: "CVL National Championship",
}


def _round_label_for(week: int, total_teams: int) -> str:
    if total_teams <= 4:
        return ROUND_LABELS_SMALL.get(week, f"Round (wk {week})")
    if total_teams <= 8:
        labels = {998: "Quarterfinals", 999: "Semifinals", 1000: "CVL National Championship"}
        return labels.get(week, f"Round (wk {week})")
    if total_teams <= 12:
        labels = {997: "First Round", 998: "Quarterfinals", 999: "Semifinals", 1000: "CVL National Championship"}
        return labels.get(week, f"Round (wk {week})")
    if total_teams <= 16:
        labels = {997: "Round of 16", 998: "Quarterfinals", 999: "Semifinals", 1000: "CVL National Championship"}
        return labels.get(week, f"Round (wk {week})")
    if total_teams <= 24:
        labels = {996: "First Round", 997: "Round of 16", 998: "Quarterfinals", 999: "Semifinals", 1000: "CVL National Championship"}
        return labels.get(week, f"Round (wk {week})")
    labels = {996: "Round of 32", 997: "Round of 16", 998: "Quarterfinals", 999: "Semifinals", 1000: "CVL National Championship"}
    return labels.get(week, f"Round (wk {week})")


def _derive_seeds(bracket: list) -> dict:
    first_round_week = min(g.get("week", 9999) for g in bracket)
    first_games = [g for g in bracket if g.get("week") == first_round_week]

    seed_map = {}
    seed_counter = 1
    for g in first_games:
        home = g.get("home_team", "")
        away = g.get("away_team", "")
        if home and home not in seed_map:
            seed_map[home] = seed_counter
            seed_counter += 1
        if away and away not in seed_map:
            seed_map[away] = seed_counter
            seed_counter += 1

    for g in bracket:
        for team_key in ("home_team", "away_team"):
            t = g.get(team_key, "")
            if t and t not in seed_map:
                seed_map[t] = seed_counter
                seed_counter += 1
    return seed_map


def _matchup_card(game: dict, seed_map: dict, user_team: str | None = None,
                  is_championship: bool = False):
    home = game.get("home_team", "")
    away = game.get("away_team", "")
    hs = game.get("home_score") or 0
    aws = game.get("away_score") or 0
    completed = game.get("completed", False)
    h_seed = seed_map.get(home, "")
    a_seed = seed_map.get(away, "")

    if completed:
        h_won = hs > aws
        a_won = aws > hs
    else:
        h_won = a_won = False

    border = "border-amber-400 border-2" if is_championship else "border border-slate-200"
    card_bg = "bg-white"

    with ui.card().classes(f"{card_bg} {border} p-0 rounded-lg shadow-sm w-full"):
        _team_row(home, h_seed, hs, completed, h_won, user_team, is_top=True)
        ui.separator().classes("my-0")
        _team_row(away, a_seed, aws, completed, a_won, user_team, is_top=False)


def _team_row(team: str, seed, score, completed: bool, is_winner: bool,
              user_team: str | None, is_top: bool = True):
    weight = "font-bold" if is_winner else "font-normal"
    bg = "bg-green-50" if is_winner else ""
    text_color = "text-slate-800" if is_winner else "text-slate-500"
    if not completed:
        text_color = "text-slate-700"
        bg = ""
    is_user = user_team and team == user_team
    if is_user:
        bg = "bg-blue-50" if not is_winner else "bg-green-100"

    round_cls = "rounded-t-lg" if is_top else "rounded-b-lg"

    with ui.row().classes(f"w-full items-center px-3 py-1.5 gap-2 {bg} {round_cls} no-wrap"):
        if seed:
            ui.label(str(seed)).classes("text-xs text-slate-400 font-mono w-5 text-right shrink-0")
        ui.label(team).classes(f"text-sm {weight} {text_color} truncate").style("flex:1; min-width:0")
        if completed:
            score_weight = "font-bold" if is_winner else "font-normal"
            ui.label(fmt_vb_score(score)).classes(
                f"text-sm {score_weight} {text_color} shrink-0 text-right"
            ).style("min-width:32px")
        else:
            ui.label("-").classes("text-sm text-slate-300 shrink-0 text-right").style("min-width:32px")


def render_playoff_bracket(bracket_data: dict, user_team: str | None = None):
    bracket = bracket_data.get("bracket", [])
    champion = bracket_data.get("champion")

    if not bracket:
        ui.label("No playoff bracket available.").classes("text-sm text-gray-400 italic")
        return

    seed_map = _derive_seeds(bracket)
    all_teams = set()
    for g in bracket:
        all_teams.add(g.get("home_team", ""))
        all_teams.add(g.get("away_team", ""))
    all_teams.discard("")
    total_teams = len(all_teams)

    weeks = sorted(set(g.get("week", 0) for g in bracket))

    if champion:
        with ui.card().classes("bg-gradient-to-r from-amber-50 to-yellow-50 border-2 border-amber-400 p-4 rounded-xl w-full mb-4"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("emoji_events").classes("text-amber-500 text-3xl")
                with ui.column().classes("gap-0"):
                    ui.label("CVL National Champions").classes("text-xs uppercase tracking-wider text-amber-600 font-semibold")
                    ui.label(champion).classes("text-xl font-bold text-amber-900")

    with ui.card().classes("w-full p-4 bg-slate-50 rounded-xl"):
        ui.label("CVL Playoff Bracket").classes("text-lg font-bold text-slate-700 mb-3")
        ui.label(f"{total_teams}-Team Field").classes("text-xs text-slate-400 -mt-2 mb-3")

        for week in weeks:
            round_games = [g for g in bracket if g.get("week") == week]
            if not round_games:
                continue

            is_championship = (week == 1000)
            label = _round_label_for(week, total_teams)

            if is_championship:
                ui.separator().classes("my-3")
                with ui.row().classes("items-center gap-2 mb-2"):
                    ui.icon("emoji_events").classes("text-amber-500")
                    ui.label(label).classes("font-bold text-amber-800 text-base uppercase tracking-wide")
            else:
                ui.label(label).classes("font-semibold text-slate-600 text-sm mt-3 mb-1 uppercase tracking-wide")

            cols = 1 if len(round_games) <= 2 else (2 if len(round_games) <= 4 else 3)
            if is_championship:
                cols = 1

            grid_cls = f"grid-cols-{cols}" if cols <= 3 else "grid-cols-3"
            with ui.element("div").classes(f"grid {grid_cls} gap-3 w-full"):
                for game in round_games:
                    with ui.element("div").classes("w-full"):
                        _matchup_card(game, seed_map, user_team, is_championship=is_championship)


def render_playoff_field(playoff_teams: list, user_team: str | None = None):
    if not playoff_teams:
        return

    with ui.card().classes("w-full p-4 bg-white rounded-xl border border-slate-200 mb-3"):
        ui.label("Playoff Field").classes("text-lg font-bold text-slate-700 mb-2")
        with ui.element("div").classes("grid grid-cols-1 sm:grid-cols-2 gap-2"):
            for i, t in enumerate(playoff_teams, 1):
                team_name = t.get("team_name", t) if isinstance(t, dict) else str(t)
                record = ""
                conf = ""
                bid = ""
                if isinstance(t, dict):
                    record = f"{t.get('wins', 0)}-{t.get('losses', 0)}"
                    conf = t.get("conference", "")
                    conf_rec = f"{t.get('conf_wins', 0)}-{t.get('conf_losses', 0)}"
                    bid = t.get("bid_type", "")

                is_user = user_team and team_name == user_team
                bg = "bg-blue-50 border-blue-200" if is_user else "bg-slate-50 border-slate-100"

                with ui.card().classes(f"{bg} border p-2 rounded-lg shadow-none w-full"):
                    with ui.row().classes("items-center gap-2 w-full no-wrap"):
                        seed_bg = "bg-amber-100 text-amber-800" if i <= 4 else "bg-slate-200 text-slate-600"
                        ui.label(str(i)).classes(
                            f"text-xs font-bold {seed_bg} rounded-full w-6 h-6 "
                            "flex items-center justify-center shrink-0"
                        )
                        with ui.column().classes("gap-0").style("flex:1; min-width:0"):
                            ui.label(team_name).classes("text-sm font-semibold text-slate-800 truncate")
                            details = []
                            if record:
                                details.append(record)
                            if conf:
                                details.append(conf)
                                if conf_rec:
                                    details.append(f"({conf_rec} conf)")
                            if bid:
                                details.append(bid.upper())
                            if details:
                                ui.label(" | ".join(details)).classes("text-xs text-slate-400")


def render_bowl_games(bowls_data: dict, user_team: str | None = None, show_results: bool = True):
    bowl_results = bowls_data.get("bowl_results", [])
    if not bowl_results:
        ui.label("No bowl games available.").classes("text-sm text-gray-400 italic")
        return

    with ui.card().classes("w-full p-4 bg-slate-50 rounded-xl"):
        with ui.row().classes("items-center gap-2 mb-3"):
            ui.icon("stadium").classes("text-slate-500 text-xl")
            ui.label("Bowl Season").classes("text-lg font-bold text-slate-700")

        tiers_grouped: dict[int, list] = {}
        for bowl in bowl_results:
            tier = bowl.get("tier", 0)
            tiers_grouped.setdefault(tier, []).append(bowl)

        for tier in sorted(tiers_grouped.keys()):
            tier_bowls = tiers_grouped[tier]
            tier_label = BOWL_TIERS.get(tier, "Bowl Games")

            tier_colors = {
                1: ("bg-amber-50", "text-amber-700", "border-amber-200"),
                2: ("bg-blue-50", "text-blue-700", "border-blue-200"),
                3: ("bg-green-50", "text-green-700", "border-green-200"),
                4: ("bg-slate-50", "text-slate-600", "border-slate-200"),
            }
            bg, text_col, border = tier_colors.get(tier, ("bg-slate-50", "text-slate-600", "border-slate-200"))

            ui.label(tier_label).classes(f"font-semibold {text_col} text-sm mt-2 mb-1 uppercase tracking-wide")

            cols = 1 if len(tier_bowls) <= 2 else 2
            with ui.element("div").classes(f"grid grid-cols-{cols} gap-2 w-full mb-2"):
                for bowl in tier_bowls:
                    _bowl_card(bowl, user_team, bg, border, show_results)


def _bowl_card(bowl: dict, user_team: str | None, bg: str, border: str,
               show_results: bool = True):
    game = bowl.get("game", {})
    name = bowl.get("name", "Bowl Game")
    home = game.get("home_team", "")
    away = game.get("away_team", "")
    hs = game.get("home_score") or 0
    aws = game.get("away_score") or 0
    completed = game.get("completed", False)

    h_rec = bowl.get("team_1_record", "")
    a_rec = bowl.get("team_2_record", "")

    if completed:
        h_won = hs > aws
        a_won = aws > hs
    else:
        h_won = a_won = False

    is_user_game = user_team and user_team in (home, away)
    card_border = "border-blue-300" if is_user_game else border

    with ui.card().classes(f"{bg} {card_border} border p-3 rounded-lg shadow-none w-full"):
        ui.label(name).classes("text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1")

        with ui.column().classes("gap-0 w-full"):
            _bowl_team_line(home, h_rec, hs, completed, h_won, user_team)
            _bowl_team_line(away, a_rec, aws, completed, a_won, user_team)


def _bowl_team_line(team: str, record: str, score, completed: bool,
                    is_winner: bool, user_team: str | None):
    weight = "font-semibold" if is_winner else "font-normal"
    text_color = "text-slate-800" if is_winner else "text-slate-500"
    if not completed:
        text_color = "text-slate-700"
        weight = "font-normal"

    with ui.row().classes("w-full items-center gap-1 no-wrap py-0.5"):
        if is_winner and completed:
            ui.icon("check").classes("text-green-500 text-sm shrink-0")
        else:
            ui.element("span").classes("w-5 shrink-0")
        ui.label(team).classes(f"text-sm {weight} {text_color} truncate").style("flex:1; min-width:0")
        if record:
            ui.label(f"({record})").classes("text-xs text-slate-400 shrink-0")
        if completed:
            ui.label(fmt_vb_score(score)).classes(
                f"text-sm {weight} {text_color} shrink-0 text-right"
            ).style("min-width:28px")
