"""
Complete Dynasty Mode Test

Simulates 10+ seasons with:
- Coach career tracking
- Team historical records
- Award history
- Conference management
- Record book
"""

import random
from engine import load_team_from_json
from engine.season import create_season
from engine.season_ui import display_complete_season_report
from engine.dynasty import create_dynasty
from engine.dynasty_ui import (
    display_coach_dashboard,
    display_team_history,
    display_award_history,
    display_record_book,
    display_dynasty_summary,
    display_multi_season_comparison,
    display_conference_history,
)


def main():
    print("=" * 100)
    print("VIPERBALL DYNASTY MODE - 10 SEASON SIMULATION")
    print("=" * 100)

    # Create dynasty
    print("\n🎓 Creating dynasty...")
    dynasty = create_dynasty(
        dynasty_name="Big East Dynasty",
        coach_name="Coach Smith",
        coach_team="Gonzaga",
        starting_year=2026
    )

    # Load teams
    print("📋 Loading teams...")
    teams = {
        "Gonzaga": load_team_from_json("data/teams/gonzaga.json"),
        "Villanova": load_team_from_json("data/teams/villanova.json"),
        "Xavier": load_team_from_json("data/teams/xavier.json"),
        "Marquette": load_team_from_json("data/teams/marquette.json"),
        "Butler": load_team_from_json("data/teams/butler.json"),
        "Creighton": load_team_from_json("data/teams/creighton.json"),
        "Providence": load_team_from_json("data/teams/providence.json"),
        "St. John's": load_team_from_json("data/teams/st_johns.json"),
    }

    # Add conference
    print("🏟️  Setting up Big East Conference...")
    dynasty.add_conference("Big East", list(teams.keys()))

    # Configure diverse styles
    style_configs = {
        "Gonzaga": {"offense_style": "boot_raid", "defense_style": "coverage_defense"},
        "Villanova": {"offense_style": "lateral_spread", "defense_style": "contain_defense"},
        "Xavier": {"offense_style": "balanced", "defense_style": "pressure_defense"},
        "Marquette": {"offense_style": "ground_pound", "defense_style": "run_stop_defense"},
        "Butler": {"offense_style": "ghost", "defense_style": "base_defense"},
        "Creighton": {"offense_style": "rouge_hunt", "defense_style": "base_defense"},
        "Providence": {"offense_style": "chain_gang", "defense_style": "pressure_defense"},
        "St. John's": {"offense_style": "triple_threat", "defense_style": "contain_defense"},
    }

    # Simulate 10 seasons
    num_seasons = 10
    print(f"\n🏈 Simulating {num_seasons} seasons...\n")

    for i in range(num_seasons):
        year = dynasty.current_year
        print(f"{'=' * 100}")
        print(f"SEASON {year}")
        print(f"{'=' * 100}")

        # Create season
        random.seed(100 + i)  # Different seed each year
        season = create_season(
            name=f"{year} Big East Season",
            teams=teams,
            style_configs=style_configs
        )

        # Generate and simulate season
        season.generate_round_robin_schedule()
        season.simulate_season(verbose=False)

        # Simulate playoffs
        season.simulate_playoff(num_teams=8, verbose=False)

        # Add to dynasty
        dynasty.advance_season(season)

        # Display quick summary
        standings = season.get_standings_sorted()
        print(f"\nChampion: {season.champion}")
        print(f"Best Record: {standings[0].team_name} ({standings[0].wins}-{standings[0].losses})")
        print(f"Coach {dynasty.coach.name} ({dynasty.coach.team_name}): {season.standings[dynasty.coach.team_name].wins}-{season.standings[dynasty.coach.team_name].losses}")
        print()

    print(f"\n{'=' * 100}")
    print("✅ ALL SEASONS COMPLETE!")
    print(f"{'=' * 100}\n")

    # Display dynasty summary
    display_dynasty_summary(dynasty)

    # Display coach dashboard
    display_coach_dashboard(dynasty.coach)

    # Display award history
    display_award_history(dynasty)

    # Display record book
    display_record_book(dynasty.record_book)

    # Display team history for champion team
    print("\n📊 DETAILED TEAM HISTORIES:\n")

    # Find team with most championships
    sorted_teams = sorted(
        dynasty.team_histories.values(),
        key=lambda h: (h.total_championships, h.win_percentage),
        reverse=True
    )

    # Display top 3 programs
    for history in sorted_teams[:3]:
        display_team_history(history)

    # Display conference history
    display_conference_history(dynasty, "Big East")

    # Display multi-season comparison (last 5 years)
    recent_years = list(range(dynasty.current_year - 5, dynasty.current_year))
    display_multi_season_comparison(dynasty, recent_years)

    # Save dynasty
    print("\n💾 Saving dynasty...")
    dynasty.save("dynasty_save.json")
    print("✅ Dynasty saved to dynasty_save.json\n")


if __name__ == "__main__":
    main()
