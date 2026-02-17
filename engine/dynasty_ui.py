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
from engine.injuries import InjuryTracker


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

    print(f"{'YEAR':<8} {'CHAMPION':<22} {'BEST REC':<22} {'SCORING':<18} {'DEFENSE':<18}")
    print(f"{'-' * 100}")

    for year in sorted(dynasty.awards_history.keys()):
        awards = dynasty.awards_history[year]
        print(f"{year:<8} {awards.champion:<22} {awards.best_record:<22} {awards.highest_scoring:<18} {awards.best_defense:<18}")

    print(f"\n{'YEAR':<8} {'HIGHEST OPI':<22} {'BEST KICKING':<22} {'VIPERBALL AWARD':<24} {'COACH OF YEAR'}")
    print(f"{'-' * 100}")

    for year in sorted(dynasty.awards_history.keys()):
        awards = dynasty.awards_history[year]
        viperball_award = ""
        coy = ""
        if awards.honors:
            for a in awards.honors.get("individual_awards", []):
                if a.get("award_name") == "The Viperball Award":
                    viperball_award = a.get("player_name", "")
            coy = awards.honors.get("coach_of_year", "")
        print(f"{year:<8} {awards.highest_opi:<22} {awards.best_kicking:<22} {viperball_award:<24} {coy}")

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

# ========================================
# END-OF-SEASON HONORS
# ========================================

def display_individual_awards(dynasty: Dynasty, year: int):
    """Display all individual award winners for a given season."""
    honors = dynasty.get_honors(year)
    if not honors:
        print(f"\n  No honors data for {year}\n")
        return

    print(f"\n{'=' * 80}")
    print(f"{'CVL INDIVIDUAL AWARDS — ' + str(year):^80}")
    print(f"{'=' * 80}")

    for award in honors.get("individual_awards", []):
        name = award.get("player_name", "N/A")
        team = award.get("team_name", "N/A")
        pos = award.get("position", "N/A")
        yr = award.get("year_in_school", "")
        ovr = award.get("overall_rating", 0)
        reason = award.get("reason", "")
        yr_label = f" · {yr}" if yr else ""
        print(f"\n  {award['award_name']}")
        print(f"  {'─' * 50}")
        print(f"  {name} ({pos}{yr_label}) — {team}  OVR {ovr}")
        print(f"  \"{reason}\"")

    coy = honors.get("coach_of_year", "")
    improved = honors.get("most_improved", "")
    if coy:
        print(f"\n  Coach of the Year:        {coy}")
    if improved:
        print(f"  Most Improved Program:    {improved}")
    print(f"\n{'=' * 80}\n")


def display_all_american(dynasty: Dynasty, year: int):
    """Display All-CVL teams (1st, 2nd, 3rd, HM) and All-Freshman for a given season."""
    honors = dynasty.get_honors(year)
    if not honors:
        print(f"\n  No honors data for {year}\n")
        return

    print(f"\n{'=' * 80}")
    print(f"{'ALL-CVL TEAMS — ' + str(year):^80}")
    print(f"{'=' * 80}")

    tiers = [
        ("all_american_first",  "FIRST TEAM ALL-CVL"),
        ("all_american_second", "SECOND TEAM ALL-CVL"),
        ("all_american_third",  "THIRD TEAM ALL-CVL"),
        ("honorable_mention",   "HONORABLE MENTION"),
        ("all_freshman",        "ALL-FRESHMAN TEAM"),
    ]

    for team_key, label in tiers:
        team_data = honors.get(team_key)
        if not team_data or not team_data.get("slots"):
            continue
        print(f"\n  {label}")
        print(f"  {'─' * 72}")
        print(f"  {'POSITION':<28} {'PLAYER':<22} {'YR':<5} {'TEAM':<20} {'OVR'}")
        print(f"  {'─' * 72}")
        for slot in team_data.get("slots", []):
            yr = slot.get("year_in_school", "")[:2]   # Fr / So / Jr / Sr / Gr
            print(f"  {slot['award_name']:<28} {slot['player_name']:<22} {yr:<5} {slot['team_name']:<20} {slot['overall_rating']}")

    print(f"\n{'=' * 80}\n")


def display_all_conference(dynasty: Dynasty, year: int, conference_name: str = None):
    """
    Display All-Conference teams (1st and 2nd) for a given year.
    If conference_name is None, shows all conferences.
    """
    honors = dynasty.get_honors(year)
    if not honors:
        print(f"\n  No honors data for {year}\n")
        return

    all_conf = honors.get("all_conference_teams", {})
    if not all_conf:
        print(f"\n  No All-Conference data for {year}\n")
        return

    to_show = ({conference_name: all_conf[conference_name]}
               if conference_name and conference_name in all_conf else all_conf)

    print(f"\n{'=' * 80}")
    print(f"{'ALL-CONFERENCE TEAMS — ' + str(year):^80}")
    print(f"{'=' * 80}")

    for conf_name, tiers in to_show.items():
        for tier_key, tier_label in [("first", "FIRST TEAM"), ("second", "SECOND TEAM")]:
            conf_data = tiers.get(tier_key) if isinstance(tiers, dict) else None
            if not conf_data:
                continue
            slots = conf_data.get("slots", []) if isinstance(conf_data, dict) else conf_data.slots
            if not slots:
                continue
            print(f"\n  {conf_name.upper()} — {tier_label} ALL-CONFERENCE")
            print(f"  {'─' * 72}")
            print(f"  {'POSITION':<28} {'PLAYER':<22} {'YR':<5} {'TEAM':<20} {'OVR'}")
            print(f"  {'─' * 72}")
            for slot in slots:
                yr = slot.get("year_in_school", "")[:2] if isinstance(slot, dict) else ""
                name = slot.get("award_name", "") if isinstance(slot, dict) else slot.award_name
                player = slot.get("player_name", "") if isinstance(slot, dict) else slot.player_name
                team = slot.get("team_name", "") if isinstance(slot, dict) else slot.team_name
                ovr = slot.get("overall_rating", 0) if isinstance(slot, dict) else slot.overall_rating
                print(f"  {name:<28} {player:<22} {yr:<5} {team:<20} {ovr}")

    print(f"\n{'=' * 80}\n")


def display_season_injury_report(dynasty: Dynasty, year: int):
    """Display the full season injury report for a given year."""
    report = dynasty.get_injury_report(year)
    if not report:
        print(f"\n  No injury data recorded for {year}\n")
        return

    print(f"\n{'=' * 80}")
    print(f"{'INJURY REPORT — ' + str(year):^80}")
    print(f"{'=' * 80}")

    total = sum(len(v) for v in report.values())
    print(f"\n  Total injuries recorded: {total}\n")

    for team_name, injuries in sorted(report.items()):
        if not injuries:
            continue
        print(f"\n  {team_name}  ({len(injuries)} injury/injuries)")
        print(f"  {'─' * 60}")
        for inj in injuries:
            tier_label = inj["tier"].upper()
            status = "OUT FOR SEASON" if inj.get("is_season_ending") else f"{inj['weeks_out']} wk(s)"
            print(f"    {inj['player_name']} ({inj['position']}) — {inj['description']} [{tier_label}] | Week {inj['week_injured']}, {status}")

    print(f"\n{'=' * 80}\n")


def display_development_report(dynasty: Dynasty, year: int):
    """Display notable player development events from the offseason following a given year."""
    events = dynasty.get_development_events(year)
    if not events:
        print(f"\n  No notable development events recorded for offseason after {year}\n")
        return

    print(f"\n{'=' * 80}")
    print(f"{'OFFSEASON DEVELOPMENT — ' + str(year) + ' → ' + str(year + 1):^80}")
    print(f"{'=' * 80}")

    breakouts = [e for e in events if e["event_type"] == "breakout"]
    declines = [e for e in events if e["event_type"] == "decline"]

    if breakouts:
        print(f"\n  BREAKOUT PLAYERS ({len(breakouts)})")
        print(f"  {'─' * 60}")
        for ev in breakouts:
            print(f"    {ev['player']} ({ev['team']}) — {ev['description']}")

    if declines:
        print(f"\n  DECLINING PLAYERS ({len(declines)})")
        print(f"  {'─' * 60}")
        for ev in declines:
            print(f"    {ev['player']} ({ev['team']}) — {ev['description']}")

    print(f"\n{'=' * 80}\n")


# ========================================
# FULL SEASON HONORS SUMMARY (combines all above)
# ========================================

def display_full_season_honors(dynasty: Dynasty, year: int):
    """Display all honors, awards, injuries, and development for a season."""
    display_individual_awards(dynasty, year)
    display_all_american(dynasty, year)
    display_all_conference(dynasty, year)
    display_season_injury_report(dynasty, year)
    display_development_report(dynasty, year)


# ========================================
# CONFERENCE HISTORY (original)
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
