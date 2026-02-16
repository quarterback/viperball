"""
Dynasty Mode UI

Beautiful displays for:
- Coach career dashboard
- Team historical records
- Award history (Hall of Fame)
- Record book
- Conference standings history
- Multi-season summaries
"""

from typing import List, Dict, Optional
from engine.dynasty import Dynasty, Coach, TeamHistory, SeasonAwards, RecordBook


# ========================================
# COACH CAREER DASHBOARD
# ========================================

def display_coach_dashboard(coach: Coach):
    """Display complete coach career dashboard"""
    print(f"\n{'=' * 70}")
    print(f"{'COACH: ' + coach.name.upper():^70}")
    print(f"{'=' * 70}")

    print(f"{'Team:':<25} {coach.team_name}")
    print(f"{'Years of Experience:':<25} {coach.years_experience}")
    print(f"{'First Season:':<25} {coach.first_year or 'N/A'}")
    print(f"{'Current Season:':<25} {coach.current_year or 'N/A'}")

    print(f"\n{'CAREER RECORD':^70}")
    print(f"{'-' * 70}")
    print(f"{'Overall Record:':<25} {coach.career_wins}-{coach.career_losses} ({coach.win_percentage*100:.1f}%)")
    print(f"{'Championships:':<25} {coach.championships}")
    print(f"{'Playoff Appearances:':<25} {coach.playoff_appearances}")

    # Season-by-season breakdown
    if coach.season_records:
        print(f"\n{'SEASON-BY-SEASON RECORD':^70}")
        print(f"{'-' * 70}")
        print(f"{'YEAR':<8} {'W-L':<10} {'PF':<10} {'PA':<10} {'PLAYOFF':<10} {'CHAMPION':<10}")
        print(f"{'-' * 70}")

        for year in sorted(coach.season_records.keys()):
            record = coach.season_records[year]
            wl = f"{record['wins']}-{record['losses']}"
            pf = f"{record['points_for']:.1f}"
            pa = f"{record['points_against']:.1f}"
            playoff = "✓" if record.get('playoff', False) else "-"
            champion = "🏆" if record.get('champion', False) else "-"

            print(f"{year:<8} {wl:<10} {pf:<10} {pa:<10} {playoff:<10} {champion:<10}")

    print(f"{'=' * 70}\n")


# ========================================
# TEAM HISTORY
# ========================================

def display_team_history(history: TeamHistory):
    """Display all-time history for a team"""
    print(f"\n{'=' * 70}")
    print(f"{history.team_name.upper() + ' ALL-TIME HISTORY':^70}")
    print(f"{'=' * 70}")

    print(f"{'ALL-TIME RECORD':^70}")
    print(f"{'-' * 70}")
    print(f"{'Overall Record:':<30} {history.total_wins}-{history.total_losses} ({history.win_percentage*100:.1f}%)")
    print(f"{'Points Per Game:':<30} {history.points_per_game:.1f}")
    print(f"{'Championships:':<30} {history.total_championships}")
    print(f"{'Playoff Appearances:':<30} {history.total_playoff_appearances}")

    if history.championship_years:
        print(f"\n{'CHAMPIONSHIP YEARS':^70}")
        print(f"{'-' * 70}")
        print(f"  {', '.join(map(str, history.championship_years))}")

    if history.best_season_year:
        print(f"\n{'BEST SEASON':^70}")
        print(f"{'-' * 70}")
        print(f"  {history.best_season_year}: {history.best_season_wins} wins")

    # Season-by-season records
    if history.season_records:
        print(f"\n{'SEASON-BY-SEASON RECORD':^70}")
        print(f"{'-' * 70}")
        print(f"{'YEAR':<8} {'W-L':<10} {'PF':<10} {'PA':<10} {'OPI':<8} {'PLAYOFF':<10} {'CHAMPION':<10}")
        print(f"{'-' * 70}")

        for year in sorted(history.season_records.keys()):
            record = history.season_records[year]
            wl = f"{record['wins']}-{record['losses']}"
            pf = f"{record['points_for']:.1f}"
            pa = f"{record['points_against']:.1f}"
            opi = f"{record.get('avg_opi', 0):.1f}"
            playoff = "✓" if record.get('playoff', False) else "-"
            champion = "🏆" if record.get('champion', False) else "-"

            print(f"{year:<8} {wl:<10} {pf:<10} {pa:<10} {opi:<8} {playoff:<10} {champion:<10}")

    print(f"{'=' * 70}\n")


# ========================================
# AWARD HISTORY (HALL OF FAME)
# ========================================

def display_award_history(dynasty: Dynasty):
    """Display complete award history across all seasons"""
    print(f"\n{'=' * 100}")
    print(f"{'HALL OF FAME - AWARD WINNERS':^100}")
    print(f"{'=' * 100}")

    if not dynasty.awards_history:
        print("\n  No awards recorded yet.\n")
        return

    print(f"{'YEAR':<8} {'CHAMPION':<20} {'BEST REC':<20} {'SCORING':<15} {'DEFENSE':<15}")
    print(f"{'-' * 100}")

    for year in sorted(dynasty.awards_history.keys()):
        awards = dynasty.awards_history[year]
        print(f"{year:<8} {awards.champion:<20} {awards.best_record:<20} {awards.highest_scoring:<15} {awards.best_defense:<15}")

    print(f"\n{'YEAR':<8} {'HIGHEST OPI':<20} {'MOST CHAOS':<20} {'BEST KICKING':<20}")
    print(f"{'-' * 100}")

    for year in sorted(dynasty.awards_history.keys()):
        awards = dynasty.awards_history[year]
        print(f"{year:<8} {awards.highest_opi:<20} {awards.most_chaos:<20} {awards.best_kicking:<20}")

    print(f"{'=' * 100}\n")


# ========================================
# RECORD BOOK
# ========================================

def display_record_book(record_book: RecordBook):
    """Display complete record book"""
    print(f"\n{'=' * 70}")
    print(f"{'VIPERBALL RECORD BOOK':^70}")
    print(f"{'=' * 70}")

    print(f"\n{'SINGLE-SEASON RECORDS':^70}")
    print(f"{'-' * 70}")

    # Most wins
    if record_book.most_wins_season["team"]:
        print(f"{'Most Wins:':<30} {record_book.most_wins_season['wins']} - {record_book.most_wins_season['team']} ({record_book.most_wins_season['year']})")

    # Most points
    if record_book.most_points_season["team"]:
        print(f"{'Most Points:':<30} {record_book.most_points_season['points']:.1f} - {record_book.most_points_season['team']} ({record_book.most_points_season['year']})")

    # Best defense
    if record_book.best_defense_season["team"]:
        print(f"{'Best Defense (PPG):':<30} {record_book.best_defense_season['ppg_allowed']:.1f} - {record_book.best_defense_season['team']} ({record_book.best_defense_season['year']})")

    # Highest OPI
    if record_book.highest_opi_season["team"]:
        print(f"{'Highest OPI:':<30} {record_book.highest_opi_season['opi']:.1f} - {record_book.highest_opi_season['team']} ({record_book.highest_opi_season['year']})")

    # Most chaos
    if record_book.most_chaos_season["team"]:
        print(f"{'Most Chaos:':<30} {record_book.most_chaos_season['chaos']:.1f} - {record_book.most_chaos_season['team']} ({record_book.most_chaos_season['year']})")

    print(f"\n{'ALL-TIME RECORDS':^70}")
    print(f"{'-' * 70}")

    # Most championships
    if record_book.most_championships["team"]:
        print(f"{'Most Championships:':<30} {record_book.most_championships['championships']} - {record_book.most_championships['team']}")

    # Highest win percentage
    if record_book.highest_win_percentage["team"]:
        print(f"{'Highest Win % (20+ games):':<30} {record_book.highest_win_percentage['win_pct']*100:.1f}% - {record_book.highest_win_percentage['team']} ({record_book.highest_win_percentage['games']} games)")

    print(f"\n{'COACHING RECORDS':^70}")
    print(f"{'-' * 70}")

    # Most coaching wins
    if record_book.most_coaching_wins["coach"]:
        print(f"{'Most Coaching Wins:':<30} {record_book.most_coaching_wins['wins']} - {record_book.most_coaching_wins['coach']}")

    # Most championships
    if record_book.most_coaching_championships["coach"]:
        print(f"{'Most Championships:':<30} {record_book.most_coaching_championships['championships']} - {record_book.most_coaching_championships['coach']}")

    print(f"{'=' * 70}\n")


# ========================================
# DYNASTY SUMMARY
# ========================================

def display_dynasty_summary(dynasty: Dynasty):
    """Display complete dynasty summary"""
    print(f"\n{'=' * 100}")
    print(f"{dynasty.dynasty_name.upper() + ' SUMMARY':^100}")
    print(f"{'=' * 100}")

    print(f"{'Current Year:':<30} {dynasty.current_year}")
    print(f"{'Seasons Played:':<30} {len(dynasty.seasons)}")
    print(f"{'Conferences:':<30} {len(dynasty.conferences)}")
    print(f"{'Teams:':<30} {len(dynasty.team_histories)}")

    print(f"\n{'COACH SUMMARY':^100}")
    print(f"{'-' * 100}")
    print(f"{'Name:':<30} {dynasty.coach.name}")
    print(f"{'Team:':<30} {dynasty.coach.team_name}")
    print(f"{'Career Record:':<30} {dynasty.coach.career_wins}-{dynasty.coach.career_losses} ({dynasty.coach.win_percentage*100:.1f}%)")
    print(f"{'Championships:':<30} {dynasty.coach.championships}")

    # Recent champions
    if dynasty.awards_history:
        print(f"\n{'RECENT CHAMPIONS':^100}")
        print(f"{'-' * 100}")
        recent_years = sorted(dynasty.awards_history.keys(), reverse=True)[:5]
        for year in recent_years:
            awards = dynasty.awards_history[year]
            print(f"  {year}: {awards.champion}")

    # Top programs (by championships)
    print(f"\n{'TOP PROGRAMS (BY CHAMPIONSHIPS)':^100}")
    print(f"{'-' * 100}")
    sorted_teams = sorted(
        dynasty.team_histories.values(),
        key=lambda h: (h.total_championships, h.win_percentage),
        reverse=True
    )[:5]

    for i, history in enumerate(sorted_teams, 1):
        print(f"  {i}. {history.team_name}: {history.total_championships} championships, {history.total_wins}-{history.total_losses} ({history.win_percentage*100:.1f}%)")

    print(f"{'=' * 100}\n")


# ========================================
# MULTI-SEASON COMPARISON
# ========================================

def display_multi_season_comparison(dynasty: Dynasty, years: List[int]):
    """Compare multiple seasons side-by-side"""
    print(f"\n{'=' * 100}")
    print(f"{'MULTI-SEASON COMPARISON':^100}")
    print(f"{'=' * 100}")

    print(f"{'TEAM':<20}", end="")
    for year in years:
        print(f"{str(year):<15}", end="")
    print()
    print(f"{'-' * 100}")

    # Get all teams
    all_teams = set()
    for year in years:
        if year in dynasty.seasons:
            all_teams.update(dynasty.seasons[year].standings.keys())

    # Display records for each team across years
    for team in sorted(all_teams):
        print(f"{team:<20}", end="")
        for year in years:
            if year in dynasty.seasons:
                season = dynasty.seasons[year]
                if team in season.standings:
                    record = season.standings[team]
                    wl = f"{record.wins}-{record.losses}"
                    print(f"{wl:<15}", end="")
                else:
                    print(f"{'N/A':<15}", end="")
            else:
                print(f"{'N/A':<15}", end="")
        print()

    print(f"{'=' * 100}\n")


# ========================================
# CONFERENCE HISTORY
# ========================================

def display_conference_history(dynasty: Dynasty, conference_name: str):
    """Display historical standings for a conference"""
    if conference_name not in dynasty.conferences:
        print(f"\n⚠️  Conference '{conference_name}' not found\n")
        return

    conference = dynasty.conferences[conference_name]

    print(f"\n{'=' * 100}")
    print(f"{conference_name.upper() + ' CONFERENCE HISTORY':^100}")
    print(f"{'=' * 100}")

    # Championship history
    if conference.championship_history:
        print(f"\n{'CHAMPIONSHIP HISTORY':^100}")
        print(f"{'-' * 100}")
        for year in sorted(conference.championship_history.keys()):
            champion = conference.championship_history[year]
            print(f"  {year}: {champion}")

    # All-time conference standings
    print(f"\n{'ALL-TIME CONFERENCE STANDINGS':^100}")
    print(f"{'-' * 100}")

    # Aggregate records for conference teams
    team_totals = {}
    for team_name in conference.teams:
        if team_name in dynasty.team_histories:
            history = dynasty.team_histories[team_name]
            team_totals[team_name] = {
                "wins": history.total_wins,
                "losses": history.total_losses,
                "championships": history.total_championships,
                "win_pct": history.win_percentage,
            }

    # Sort by championships, then win%
    sorted_teams = sorted(
        team_totals.items(),
        key=lambda x: (x[1]["championships"], x[1]["win_pct"]),
        reverse=True
    )

    print(f"{'#':<5} {'TEAM':<25} {'W-L':<15} {'WIN%':<10} {'CHAMP':<10}")
    print(f"{'-' * 100}")
    for i, (team, totals) in enumerate(sorted_teams, 1):
        wl = f"{totals['wins']}-{totals['losses']}"
        win_pct = f"{totals['win_pct']*100:.1f}%"
        champ = totals['championships']
        print(f"{i:<5} {team:<25} {wl:<15} {win_pct:<10} {champ:<10}")

    print(f"{'=' * 100}\n")
