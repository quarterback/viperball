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
    "stampede": "Stampede",
    "chain_gang": "Chain Gang",
    "slick_n_slide": "Slick 'n Slide",
    "balanced": "Balanced",
}

DEFENSE_STYLE_NAMES = {
    "pressure_defense": "Pressure",
    "swarm": "Swarm",
    "blitz_pack": "Blitz Pack",
    "shadow": "Shadow",
    "fortress": "Fortress",
    "predator": "Predator",
    "drift": "Drift",
    "chaos": "Chaos",
    "lockdown": "Lockdown",
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
    print(f"{'Record:':<25} {record.record_str} ({record.win_percentage*100:.1f}%)")
    print(f"{'Offense:':<25} {format_offense_style(record.offense_style)}")
    print(f"{'Defense:':<25} {format_defense_style(record.defense_style)}")
    print(f"{'Points For/Game:':<25} {record.points_for / max(1, record.games_played):.1f}")
    print(f"{'Points Against/Game:':<25} {record.points_against / max(1, record.games_played):.1f}")
    print(f"{'Point Differential:':<25} {record.point_differential:+.1f}")

    # Metrics
    print(f"\n{'SEASON AVERAGES':^70}")
    print(f"{'-' * 70}")

    metrics = [
        ("Team Rating", record.avg_team_rating, 100),
        ("PPD (Pts/Drive)", record.avg_ppd, 10),
        ("Conversion %", record.avg_conversion_pct, 100),
        ("Lateral %", record.avg_lateral_pct, 100),
        ("Explosive Plays/G", record.avg_explosive, 15),
        ("TO Margin/G", record.avg_to_margin, 5),
    ]

    for label, value, max_val in metrics:
        bar_width = 30
        norm = min(1.0, max(0.0, value / max_val)) if max_val > 0 else 0.0
        filled = int(norm * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        if norm >= 0.8:
            rating = "ELITE"
        elif norm >= 0.6:
            rating = "GREAT"
        elif norm >= 0.4:
            rating = "GOOD"
        elif norm >= 0.2:
            rating = "AVG"
        else:
            rating = "POOR"

        print(f"  {label:<20} {bar} {value:>6.1f} {rating:>5}")

    # Conversion by zone (season aggregate)
    print(f"\n{'LATE-DOWN CONVERSION BY FIELD ZONE':^70}")
    print(f"{'-' * 70}")
    conv = record.season_conversion_by_zone
    zone_labels = {
        "own_deep": "Own 1-25",
        "own_half": "Own 26-50",
        "opp_half": "Opp 51-75",
        "opp_deep": "Opp 76-99",
    }
    print(f"  {'Zone':<15} {'4D%':>10} {'5D%':>10} {'6D%':>10}")
    print(f"  {'─'*15} {'─'*10} {'─'*10} {'─'*10}")
    for zone_key, zone_label in zone_labels.items():
        zd = conv.get(zone_key, {})
        cols = []
        for d in (4, 5, 6):
            att = zd.get(f'd{d}_att', 0)
            pct = zd.get(f'd{d}_pct', 0)
            cols.append(f"{pct:.0f}% ({att})" if att > 0 else "—")
        print(f"  {zone_label:<15} {cols[0]:>10} {cols[1]:>10} {cols[2]:>10}")

    # Delta profile
    print(f"\n  {'Season 5D%:':<20} {record.season_5d_pct:.1f}%")
    print(f"  {'5D% Own Deep:':<20} {record.season_5d_own_deep_pct:.1f}%")
    print(f"  {'KILL%:':<20} {record.season_kill_pct:.1f}%")
    print(f"  {'Net YPG:':<20} {record.avg_delta_yds:+.1f}")


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
        print(f"{'#':<3} {'TEAM':<20} {'STYLES':<22} {'W-L':<7} {'PF':<6} {'PA':<6} {'DIFF':<7} {'RTG':<5} {'PPD':<5} {'5D%':<5} {'KILL':<5}")
        print(f"{'-' * 115}")
    else:
        print(f"{'#':<3} {'TEAM':<20} {'O/D STYLES':<25} {'W-L':<8} {'PF':<6} {'PA':<6} {'DIFF':<7}")
        print(f"{'-' * 85}")

    # Rows
    for i, record in enumerate(standings, start=1):
        rank = f"{i}."
        team = record.team_name[:19]
        styles = f"{format_offense_style(record.offense_style)[:10]}/{format_defense_style(record.defense_style)[:9]}"
        wl = record.record_str
        pf = f"{record.points_for / max(1, record.games_played):.1f}"
        pa = f"{record.points_against / max(1, record.games_played):.1f}"
        diff = f"{record.point_differential:+.1f}"

        if show_metrics:
            rtg = f"{record.avg_team_rating:.0f}"
            ppd = f"{record.avg_ppd:.1f}"
            d5 = f"{record.season_5d_pct:.0f}%"
            kill = f"{record.season_kill_pct:.0f}%"
            print(f"{rank:<3} {team:<20} {styles:<22} {wl:<7} {pf:<6} {pa:<6} {diff:<7} {rtg:<5} {ppd:<5} {d5:<5} {kill:<5}")
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
        print(f"{'Final Record: ' + champion_record.record_str:^100}")
        print(f"{'Offense: ' + format_offense_style(champion_record.offense_style) + ' / Defense: ' + format_defense_style(champion_record.defense_style):^100}")

    # Season awards
    standings = season.get_standings_sorted()

    print(f"\n{'SEASON AWARDS':^100}")
    print(f"{'-' * 100}")

    # Best record
    best_record = standings[0]
    print(f"  🥇 Best Record: {best_record.team_name} ({best_record.record_str})")

    # Highest scoring
    highest_scoring = max(standings, key=lambda r: r.points_for / max(1, r.games_played))
    print(f"  ⚡ Highest Scoring: {highest_scoring.team_name} ({highest_scoring.points_for / max(1, highest_scoring.games_played):.1f} PPG)")

    # Best defense
    best_defense = min(standings, key=lambda r: r.points_against / max(1, r.games_played))
    print(f"  🛡️  Best Defense: {best_defense.team_name} ({best_defense.points_against / max(1, best_defense.games_played):.1f} PPG allowed)")

    # Highest Team Rating
    highest_rtg = max(standings, key=lambda r: r.avg_team_rating)
    print(f"  Team Rating: {highest_rtg.team_name} ({highest_rtg.avg_team_rating:.1f}/100)")

    # Best PPD
    best_ppd = max(standings, key=lambda r: r.avg_ppd)
    print(f"  Best PPD: {best_ppd.team_name} ({best_ppd.avg_ppd:.2f} pts/drive)")

    # Best 5D conversion
    best_5d = max(standings, key=lambda r: r.season_5d_pct)
    print(f"  Best 5D%: {best_5d.team_name} ({best_5d.season_5d_pct:.1f}%)")

    # Best survival (5D from own deep)
    best_survival = max(standings, key=lambda r: r.season_5d_own_deep_pct if r.conv_zone_own_deep_5d_att >= 3 else 0)
    if best_survival.conv_zone_own_deep_5d_att >= 3:
        print(f"  Best Survival (5D Own Deep): {best_survival.team_name} ({best_survival.season_5d_own_deep_pct:.1f}%)")

    # Lowest KILL%
    lowest_kill = min(standings, key=lambda r: r.season_kill_pct if r.total_team_drives_for_kill > 0 else 100)
    if lowest_kill.total_team_drives_for_kill > 0:
        print(f"  Lowest KILL%: {lowest_kill.team_name} ({lowest_kill.season_kill_pct:.1f}%)")

    # Best TO margin
    best_to = max(standings, key=lambda r: r.avg_to_margin)
    print(f"  Best TO Margin: {best_to.team_name} ({best_to.avg_to_margin:+.1f}/game)")

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
