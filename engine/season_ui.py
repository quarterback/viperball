"""
Season UI and Dashboard for Viperball Dynasty Mode

Beautiful displays for:
- Standings tables
- Team metrics dashboards
- Season summaries
- Playoff brackets
- Championship reports
"""

from typing import List, Dict, Optional
from engine.season import Season, TeamRecord, Game


# ========================================
# STYLE NAME FORMATTING
# ========================================

OFFENSE_STYLE_NAMES = {
    "ground_pound": "Ground & Pound",
    "lateral_spread": "Lateral Spread",
    "boot_raid": "Boot Raid",
    "ball_control": "Ball Control",
    "ghost": "Ghost Formation",
    "rouge_hunt": "Rouge Hunt",
    "chain_gang": "Chain Gang",
    "triple_threat": "Triple Threat",
    "balanced": "Balanced",
}

DEFENSE_STYLE_NAMES = {
    "pressure_defense": "Pressure",
    "coverage_defense": "Coverage",
    "contain_defense": "Contain",
    "run_stop_defense": "Run-Stop",
    "base_defense": "Base",
}


def format_offense_style(style: str) -> str:
    """Format offense style name for display"""
    return OFFENSE_STYLE_NAMES.get(style, style.replace("_", " ").title())


def format_defense_style(style: str) -> str:
    """Format defense style name for display"""
    return DEFENSE_STYLE_NAMES.get(style, style.replace("_", " ").title())


# ========================================
# TEAM METRICS DASHBOARD
# ========================================

def display_team_dashboard(record: TeamRecord, rank: Optional[int] = None):
    """
    Display comprehensive team dashboard with record, styles, and metrics

    Args:
        record: TeamRecord to display
        rank: Optional season rank (1, 2, 3, etc.)
    """
    # Header with rank if provided
    header = f"{'#' + str(rank) + ' ' if rank else ''}{record.team_name}"
    print(f"\n{'=' * 70}")
    print(f"{header:^70}")
    print(f"{'=' * 70}")

    # Record and styles
    print(f"{'Record:':<25} {record.wins}-{record.losses} ({record.win_percentage*100:.1f}%)")
    print(f"{'Offense:':<25} {format_offense_style(record.offense_style)}")
    print(f"{'Defense:':<25} {format_defense_style(record.defense_style)}")
    print(f"{'Points For/Game:':<25} {record.points_for / max(1, record.games_played):.1f}")
    print(f"{'Points Against/Game:':<25} {record.points_against / max(1, record.games_played):.1f}")
    print(f"{'Point Differential:':<25} {record.point_differential:+.1f}")

    # Metrics
    print(f"\n{'SEASON AVERAGES':^70}")
    print(f"{'-' * 70}")

    metrics = [
        ("⭐ Overall Performance Index", record.avg_opi, 100),
        ("🗺️  Territory Rating", record.avg_territory, 100),
        ("💪 Pressure Index", record.avg_pressure, 100),
        ("⚡ Chaos Factor", record.avg_chaos, 100),
        ("👟 Kicking Efficiency", record.avg_kicking, 100),
        ("📍 Drive Quality", record.avg_drive_quality, 10),
        ("🛡️  Turnover Impact", record.avg_turnover_impact, 100),
    ]

    for label, value, max_val in metrics:
        # Create progress bar
        bar_width = 30
        filled = int((value / max_val) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Rating
        if value >= max_val * 0.8:
            rating = "ELITE"
        elif value >= max_val * 0.6:
            rating = "GREAT"
        elif value >= max_val * 0.4:
            rating = "GOOD"
        elif value >= max_val * 0.2:
            rating = "POOR"
        else:
            rating = "WEAK"

        print(f"{label:<25} {bar} {value:>6.1f}/{max_val:<3} {rating:>5}")


# ========================================
# STANDINGS TABLE
# ========================================

def display_standings(season: Season, show_metrics: bool = True):
    """
    Display season standings table

    Args:
        season: Season object
        show_metrics: Whether to show average OPI column
    """
    standings = season.get_standings_sorted()

    print(f"\n{'=' * 100}")
    print(f"{season.name + ' STANDINGS':^100}")
    print(f"{'=' * 100}")

    # Header
    if show_metrics:
        print(f"{'#':<3} {'TEAM':<20} {'O/D STYLES':<25} {'W-L':<8} {'PF':<6} {'PA':<6} {'DIFF':<7} {'OPI':<5}")
        print(f"{'-' * 100}")
    else:
        print(f"{'#':<3} {'TEAM':<20} {'O/D STYLES':<25} {'W-L':<8} {'PF':<6} {'PA':<6} {'DIFF':<7}")
        print(f"{'-' * 85}")

    # Rows
    for i, record in enumerate(standings, start=1):
        rank = f"{i}."
        team = record.team_name[:19]
        styles = f"{format_offense_style(record.offense_style)[:12]}/{format_defense_style(record.defense_style)[:10]}"
        wl = f"{record.wins}-{record.losses}"
        pf = f"{record.points_for / max(1, record.games_played):.1f}"
        pa = f"{record.points_against / max(1, record.games_played):.1f}"
        diff = f"{record.point_differential:+.1f}"

        if show_metrics:
            opi = f"{record.avg_opi:.1f}"
            print(f"{rank:<3} {team:<20} {styles:<25} {wl:<8} {pf:<6} {pa:<6} {diff:<7} {opi:<5}")
        else:
            print(f"{rank:<3} {team:<20} {styles:<25} {wl:<8} {pf:<6} {pa:<6} {diff:<7}")

    print(f"{'=' * 100}\n")


# ========================================
# PLAYOFF BRACKET
# ========================================

def display_playoff_bracket(season: Season):
    """Display playoff bracket with results"""
    if not season.playoff_bracket:
        print("\n⚠️  No playoff games played yet")
        return

    print(f"\n{'=' * 70}")
    print(f"{'PLAYOFF BRACKET':^70}")
    print(f"{'=' * 70}")

    # Group by round
    quarterfinals = [g for g in season.playoff_bracket if g.week == 998]
    semifinals = [g for g in season.playoff_bracket if g.week == 999]
    championship = [g for g in season.playoff_bracket if g.week == 1000]

    if quarterfinals:
        print(f"\n{'QUARTERFINALS':^70}")
        print(f"{'-' * 70}")
        for i, game in enumerate(quarterfinals, start=1):
            winner = game.home_team if (game.home_score or 0) > (game.away_score or 0) else game.away_team
            loser = game.away_team if (game.home_score or 0) > (game.away_score or 0) else game.home_team
            winner_score = max((game.home_score or 0), (game.away_score or 0))
            loser_score = min((game.home_score or 0), (game.away_score or 0))
            print(f"  Game {i}: {winner} {winner_score:.1f} def. {loser} {loser_score:.1f}")

    if semifinals:
        print(f"\n{'SEMIFINALS':^70}")
        print(f"{'-' * 70}")
        for i, game in enumerate(semifinals, start=1):
            winner = game.home_team if (game.home_score or 0) > (game.away_score or 0) else game.away_team
            loser = game.away_team if (game.home_score or 0) > (game.away_score or 0) else game.home_team
            winner_score = max((game.home_score or 0), (game.away_score or 0))
            loser_score = min((game.home_score or 0), (game.away_score or 0))
            print(f"  Game {i}: {winner} {winner_score:.1f} def. {loser} {loser_score:.1f}")

    if championship:
        game = championship[0]
        winner = game.home_team if (game.home_score or 0) > (game.away_score or 0) else game.away_team
        loser = game.away_team if (game.home_score or 0) > (game.away_score or 0) else game.home_team
        winner_score = max((game.home_score or 0), (game.away_score or 0))
        loser_score = min((game.home_score or 0), (game.away_score or 0))

        print(f"\n{'🏆 CHAMPIONSHIP 🏆':^70}")
        print(f"{'-' * 70}")
        print(f"  {winner} {winner_score:.1f} def. {loser} {loser_score:.1f}")
        print(f"\n{'🎉 ' + winner.upper() + ' ARE CHAMPIONS! 🎉':^70}")

    print(f"{'=' * 70}\n")


# ========================================
# SEASON SUMMARY
# ========================================

def display_season_summary(season: Season):
    """Display complete season summary with champion and awards"""
    print(f"\n{'=' * 100}")
    print(f"{season.name.upper() + ' SUMMARY':^100}")
    print(f"{'=' * 100}")

    # Champion
    if season.champion:
        champion_record = season.standings[season.champion]
        print(f"\n{'🏆 CHAMPION: ' + season.champion.upper() + ' 🏆':^100}")
        print(f"{'Final Record: ' + str(champion_record.wins) + '-' + str(champion_record.losses):^100}")
        print(f"{'Offense: ' + format_offense_style(champion_record.offense_style) + ' / Defense: ' + format_defense_style(champion_record.defense_style):^100}")

    # Season awards
    standings = season.get_standings_sorted()

    print(f"\n{'SEASON AWARDS':^100}")
    print(f"{'-' * 100}")

    # Best record
    best_record = standings[0]
    print(f"  🥇 Best Record: {best_record.team_name} ({best_record.wins}-{best_record.losses})")

    # Highest scoring
    highest_scoring = max(standings, key=lambda r: r.points_for / max(1, r.games_played))
    print(f"  ⚡ Highest Scoring: {highest_scoring.team_name} ({highest_scoring.points_for / max(1, highest_scoring.games_played):.1f} PPG)")

    # Best defense
    best_defense = min(standings, key=lambda r: r.points_against / max(1, r.games_played))
    print(f"  🛡️  Best Defense: {best_defense.team_name} ({best_defense.points_against / max(1, best_defense.games_played):.1f} PPG allowed)")

    # Highest OPI
    highest_opi = max(standings, key=lambda r: r.avg_opi)
    print(f"  ⭐ Highest OPI: {highest_opi.team_name} ({highest_opi.avg_opi:.1f}/100)")

    # Most chaos
    most_chaos = max(standings, key=lambda r: r.avg_chaos)
    print(f"  💥 Chaos Award: {most_chaos.team_name} ({most_chaos.avg_chaos:.1f}/100)")

    # Best kicking
    best_kicking = max(standings, key=lambda r: r.avg_kicking)
    print(f"  👟 Kicking Award: {best_kicking.team_name} ({best_kicking.avg_kicking:.1f}/100)")

    print(f"{'=' * 100}\n")


# ========================================
# WEEKLY SCOREBOARD
# ========================================

def display_week_scoreboard(season: Season, week: int):
    """Display all games from a specific week"""
    week_games = [g for g in season.schedule if g.week == week and g.completed]

    if not week_games:
        print(f"\n⚠️  No completed games for Week {week}")
        return

    print(f"\n{'=' * 70}")
    print(f"{'WEEK ' + str(week) + ' SCOREBOARD':^70}")
    print(f"{'=' * 70}\n")

    for game in week_games:
        winner = game.home_team if (game.home_score or 0) > (game.away_score or 0) else game.away_team
        loser = game.away_team if (game.home_score or 0) > (game.away_score or 0) else game.home_team
        winner_score = max((game.home_score or 0), (game.away_score or 0))
        loser_score = min((game.home_score or 0), (game.away_score or 0))

        print(f"  {winner} {winner_score:.1f} def. {loser} {loser_score:.1f}")
        if game.home_metrics and game.away_metrics:
            home_opi = game.home_metrics['opi']
            away_opi = game.away_metrics['opi']
            print(f"    OPI: {game.home_team} {home_opi:.1f} | {game.away_team} {away_opi:.1f}")
        print()

    print(f"{'=' * 70}\n")


# ========================================
# COMPLETE SEASON REPORT
# ========================================

def display_complete_season_report(season: Season):
    """Display comprehensive season report with all information"""
    # Season summary
    display_season_summary(season)

    # Final standings
    display_standings(season, show_metrics=True)

    # Playoff bracket
    if season.playoff_bracket:
        display_playoff_bracket(season)

    # Top 3 team dashboards
    standings = season.get_standings_sorted()
    print(f"\n{'=' * 70}")
    print(f"{'TOP 3 TEAMS - DETAILED METRICS':^70}")
    print(f"{'=' * 70}")

    for i, record in enumerate(standings[:3], start=1):
        display_team_dashboard(record, rank=i)

    print(f"\n{'=' * 70}")
    print(f"{'END OF SEASON REPORT':^70}")
    print(f"{'=' * 70}\n")
