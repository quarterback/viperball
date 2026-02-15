#!/usr/bin/env python3
"""
Simulate a Collegiate Viperball game and generate outputs

Usage:
    python simulate_game.py <home_team> <away_team>
    
Example:
    python simulate_game.py nyu gonzaga
"""

import sys
import json
import os
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent))

from engine import ViperballEngine, load_team_from_json, BoxScoreGenerator


def simulate_game(home_team_file: str, away_team_file: str):
    """Simulate a game between two teams"""
    
    print("=" * 60)
    print("COLLEGIATE VIPERBALL SIMULATION")
    print("=" * 60)
    print()
    
    # Load teams
    print(f"Loading home team from: {home_team_file}")
    home_team = load_team_from_json(home_team_file)
    
    print(f"Loading away team from: {away_team_file}")
    away_team = load_team_from_json(away_team_file)
    
    print()
    print(f"{away_team.name} @ {home_team.name}")
    print()
    
    # Initialize engine
    engine = ViperballEngine(home_team, away_team)
    
    # Simulate the game
    print("Simulating game...")
    game_data = engine.simulate_game()
    
    print()
    print("=" * 60)
    print("GAME COMPLETE")
    print("=" * 60)
    print()
    
    # Display final score
    home_score = game_data['final_score']['home']['score']
    away_score = game_data['final_score']['away']['score']
    
    print(f"FINAL SCORE:")
    print(f"  {away_team.name}: {away_score}")
    print(f"  {home_team.name}: {home_score}")
    print()
    
    if home_score > away_score:
        print(f"🏆 {home_team.name} wins by {home_score - away_score}!")
    elif away_score > home_score:
        print(f"🏆 {away_team.name} wins by {away_score - home_score}!")
    else:
        print("Game ended in a tie!")
    
    print()
    
    # Save play-by-play JSON
    pbp_filename = f"examples/play_by_play_{away_team.abbreviation}_at_{home_team.abbreviation}.json"
    os.makedirs("examples", exist_ok=True)
    
    with open(pbp_filename, 'w') as f:
        json.dump(game_data, f, indent=2)
    
    print(f"Play-by-play saved to: {pbp_filename}")
    
    # Generate and save box score
    box_score_gen = BoxScoreGenerator(game_data)
    box_score_filename = f"examples/box_scores/{away_team.abbreviation}_at_{home_team.abbreviation}.md"
    os.makedirs("examples/box_scores", exist_ok=True)
    
    box_score_gen.save_to_file(box_score_filename)
    print(f"Box score saved to: {box_score_filename}")
    
    print()
    print("Simulation complete!")
    
    return game_data


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python simulate_game.py <home_team> <away_team>")
        print("\nAvailable teams:")
        print("  - nyu")
        print("  - gonzaga")
        print("  - marquette")
        print("  - ut_arlington")
        print("\nExample: python simulate_game.py nyu gonzaga")
        sys.exit(1)
    
    home = sys.argv[1]
    away = sys.argv[2]
    
    # Construct file paths
    home_file = f"data/teams/{home}.json"
    away_file = f"data/teams/{away}.json"
    
    # Check if files exist
    if not os.path.exists(home_file):
        print(f"Error: Home team file not found: {home_file}")
        sys.exit(1)
    
    if not os.path.exists(away_file):
        print(f"Error: Away team file not found: {away_file}")
        sys.exit(1)
    
    # Run simulation
    simulate_game(home_file, away_file)
