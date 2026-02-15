#!/usr/bin/env python3
"""
Generate a sample CVL Top 25 Poll

This demonstrates the poll system with sample season data
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine import PollSystem, TeamRecord


def generate_sample_poll():
    """Generate a sample Top 25 poll with fictional season data"""
    
    poll = PollSystem()
    
    # Add sample teams from all conferences with varied records
    
    # Empire Elite (East)
    poll.add_team(TeamRecord("New York University", "NYU", "Empire Elite", 9, 2, 7.8, 0.620, 312, 198))
    poll.add_team(TeamRecord("St. John's University", "SJU", "Empire Elite", 7, 4, 6.5, 0.580, 268, 245))
    poll.add_team(TeamRecord("George Mason University", "GMU", "Empire Elite", 6, 5, 6.2, 0.545, 245, 256))
    poll.add_team(TeamRecord("VCU", "VCU", "Empire Elite", 8, 3, 7.2, 0.595, 289, 215))
    poll.add_team(TeamRecord("American University", "AU", "Empire Elite", 5, 6, 5.8, 0.510, 223, 267))
    poll.add_team(TeamRecord("University of Vermont", "UVM", "Empire Elite", 4, 7, 5.3, 0.490, 198, 278))
    
    # Heartland Union (Midwest)
    poll.add_team(TeamRecord("Marquette University", "MU", "Heartland Union", 10, 1, 8.3, 0.655, 345, 189))
    poll.add_team(TeamRecord("DePaul University", "DPU", "Heartland Union", 6, 5, 6.4, 0.530, 256, 248))
    poll.add_team(TeamRecord("Loyola University Chicago", "LUC", "Heartland Union", 7, 4, 6.9, 0.575, 278, 234))
    poll.add_team(TeamRecord("Xavier University", "XU", "Heartland Union", 8, 3, 7.5, 0.605, 298, 221))
    poll.add_team(TeamRecord("Creighton University", "CU", "Heartland Union", 5, 6, 5.9, 0.520, 234, 265))
    poll.add_team(TeamRecord("Wichita State University", "WSU", "Heartland Union", 9, 2, 7.9, 0.630, 321, 207))
    
    # Coastal Vanguard (West)
    poll.add_team(TeamRecord("Gonzaga University", "GU", "Coastal Vanguard", 11, 0, 8.9, 0.680, 378, 156))
    poll.add_team(TeamRecord("Pepperdine University", "PU", "Coastal Vanguard", 6, 5, 6.3, 0.555, 251, 259))
    poll.add_team(TeamRecord("UC Irvine", "UCI", "Coastal Vanguard", 7, 4, 7.0, 0.585, 287, 238))
    poll.add_team(TeamRecord("UC Santa Barbara", "UCSB", "Coastal Vanguard", 8, 3, 7.3, 0.600, 295, 225))
    poll.add_team(TeamRecord("Cal State Fullerton", "CSUF", "Coastal Vanguard", 5, 6, 6.0, 0.515, 229, 271))
    poll.add_team(TeamRecord("Long Beach State", "LBSU", "Coastal Vanguard", 9, 2, 7.7, 0.625, 315, 210))
    
    # Southern Heritage (South)
    poll.add_team(TeamRecord("UT Arlington", "UTA", "Southern Heritage", 8, 3, 7.4, 0.610, 301, 228))
    poll.add_team(TeamRecord("High Point University", "HPU", "Southern Heritage", 6, 5, 6.1, 0.540, 241, 263))
    poll.add_team(TeamRecord("UNC Asheville", "UNCA", "Southern Heritage", 7, 4, 6.7, 0.570, 271, 247))
    poll.add_team(TeamRecord("College of Charleston", "CofC", "Southern Heritage", 9, 2, 7.6, 0.615, 308, 201))
    poll.add_team(TeamRecord("Oral Roberts University", "ORU", "Southern Heritage", 5, 6, 5.7, 0.505, 218, 274))
    poll.add_team(TeamRecord("Little Rock", "UALR", "Southern Heritage", 10, 1, 8.1, 0.645, 334, 195))
    
    # Generate and display the poll
    print("=" * 80)
    print("GENERATING CVL TOP 25 POLL")
    print("=" * 80)
    print()
    
    top_25 = poll.generate_top_25()
    
    print("TOP 25 TEAMS:")
    print()
    for rank, team, score in top_25:
        print(f"{rank:2d}. {team.name:40s} ({team.wins}-{team.losses}) - Score: {score:.2f}")
    
    print()
    print("=" * 80)
    
    # Get champion
    champion = poll.get_champion()
    if champion:
        print(f"🏆 NATIONAL CHAMPION: {champion.name} ({champion.wins}-{champion.losses})")
    
    print()
    
    # Save to file
    output_file = "examples/cvl_top_25_poll.md"
    poll.save_poll_to_file(output_file)
    print(f"Poll saved to: {output_file}")
    print()


if __name__ == "__main__":
    generate_sample_poll()
