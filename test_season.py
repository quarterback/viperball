"""
Complete Season Simulation Test

Tests:
- Season creation with 8 teams
- Diverse style configurations
- Round-robin schedule
- Full season simulation
- Playoff bracket (8 teams)
- Championship resolution
- Complete UI dashboard
"""

import random
from engine import load_team_from_json
from engine.season import Season, create_season
from engine.season_ui import (
    display_standings,
    display_playoff_bracket,
    display_season_summary,
    display_team_dashboard,
    display_complete_season_report
)


def main():
    print("=" * 100)
    print("VIPERBALL SEASON SIMULATION - FULL DYNASTY MODE TEST")
    print("=" * 100)

    # Load 8 teams for season (Big East Conference)
    print("\n📋 Loading teams...")
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

    # Configure diverse styles for strategic matchups
    style_configs = {
        "Gonzaga": {
            "offense_style": "territorial",
            "defense_style": "coverage_defense"  # Anti-kicking package
        },
        "Villanova": {
            "offense_style": "lateral_spread",
            "defense_style": "contain_defense"  # Anti-lateral package
        },
        "Xavier": {
            "offense_style": "balanced",
            "defense_style": "pressure_defense"  # Aggressive, creates turnovers
        },
        "Marquette": {
            "offense_style": "power_option",
            "defense_style": "run_stop_defense"  # Anti-run package
        },
        "Butler": {
            "offense_style": "option_spread",
            "defense_style": "base_defense"  # Balanced defense
        },
        "Creighton": {
            "offense_style": "territorial",
            "defense_style": "base_defense"  # Kicking-focused
        },
        "Providence": {
            "offense_style": "lateral_spread",
            "defense_style": "pressure_defense"  # High-risk chaos
        },
        "St. John's": {
            "offense_style": "power_option",
            "defense_style": "contain_defense"  # Disciplined defense
        },
    }

    print("✅ Teams loaded:")
    for team_name, config in style_configs.items():
        print(f"  • {team_name}: {config['offense_style']} O / {config['defense_style']} D")

    # Create season
    print("\n⚙️  Creating 2026 season...")
    random.seed(100)  # For reproducibility
    season = create_season(
        name="2026 Viperball Season",
        teams=teams,
        style_configs=style_configs
    )

    # Generate schedule
    print("📅 Generating round-robin schedule...")
    season.generate_round_robin_schedule()
    print(f"✅ {len(season.schedule)} games scheduled")

    # Simulate regular season
    print("\n🏈 Simulating regular season...")
    print("=" * 100)

    season.simulate_season(verbose=False)  # Set to True to see all games

    print("✅ Regular season complete!")

    # Display standings
    display_standings(season, show_metrics=True)

    # Simulate playoffs (8 teams)
    print("\n🏆 BEGINNING PLAYOFFS...")
    print("=" * 100)

    season.simulate_playoff(num_teams=8, verbose=True)

    print(f"\n✅ Playoffs complete!")

    # Display playoff bracket
    display_playoff_bracket(season)

    # Display complete season report
    print("\n📊 GENERATING SEASON REPORT...")
    display_complete_season_report(season)


if __name__ == "__main__":
    main()
