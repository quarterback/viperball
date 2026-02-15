"""
Collegiate Viperball Poll System
Weekly Top 25 rankings based on W-L, SOS, and Viper Efficiency
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
import json


@dataclass
class TeamRecord:
    """Team's season record and stats"""
    name: str
    abbreviation: str
    conference: str
    wins: int
    losses: int
    viper_efficiency: float
    strength_of_schedule: float
    points_scored: int
    points_allowed: int
    
    @property
    def win_percentage(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0


class PollSystem:
    """CVL Top 25 Poll System"""
    
    def __init__(self):
        self.teams: List[TeamRecord] = []
    
    def add_team(self, team: TeamRecord):
        """Add a team to the poll"""
        self.teams.append(team)
    
    def calculate_ranking_score(self, team: TeamRecord) -> float:
        """
        Calculate overall ranking score
        
        Formula:
        Score = (Win% × 40) + (SOS × 30) + (Viper Efficiency × 20) + (Point Diff × 10)
        """
        win_score = team.win_percentage * 40
        sos_score = team.strength_of_schedule * 30
        viper_score = (team.viper_efficiency / 10) * 20  # Normalize to 0-20 scale
        
        point_diff = (team.points_scored - team.points_allowed) / max(1, team.wins + team.losses)
        point_diff_score = min(10, max(0, (point_diff + 14) / 2.8))  # Normalize to 0-10
        
        return win_score + sos_score + viper_score + point_diff_score
    
    def generate_top_25(self) -> List[Tuple[int, TeamRecord, float]]:
        """Generate Top 25 rankings"""
        # Calculate scores for all teams
        team_scores = [(team, self.calculate_ranking_score(team)) for team in self.teams]
        
        # Sort by score (descending)
        team_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top 25 with rankings
        return [(i + 1, team, score) for i, (team, score) in enumerate(team_scores[:25])]
    
    def generate_poll_markdown(self) -> str:
        """Generate markdown-formatted poll"""
        lines = []
        
        lines.append("# CVL TOP 25 POLL")
        lines.append("")
        lines.append("**Collegiate Viperball League Weekly Rankings**")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        top_25 = self.generate_top_25()
        
        lines.append("| Rank | Team | Record | Conf | Viper Eff | SOS | Score |")
        lines.append("|------|------|--------|------|-----------|-----|-------|")
        
        for rank, team, score in top_25:
            record = f"{team.wins}-{team.losses}"
            lines.append(
                f"| {rank} | {team.name} ({team.abbreviation}) | {record} | "
                f"{team.conference} | {team.viper_efficiency:.2f} | "
                f"{team.strength_of_schedule:.3f} | {score:.2f} |"
            )
        
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Ranking Methodology")
        lines.append("")
        lines.append("**Ranking Score Formula:**")
        lines.append("- Win Percentage: 40%")
        lines.append("- Strength of Schedule: 30%")
        lines.append("- Viper Efficiency: 20%")
        lines.append("- Point Differential: 10%")
        lines.append("")
        lines.append("**Viper Efficiency:** (Total Yards / Downs Used) × (1 + Lateral Success Rate) × Viper Impact Factor")
        lines.append("")
        lines.append("**Strength of Schedule:** Based on opponent win percentage and cross-conference adjustments")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*National Champion is determined by #1 ranking at end of season*")
        
        return "\n".join(lines)
    
    def get_champion(self) -> TeamRecord:
        """Get the #1 ranked team (National Champion)"""
        top_25 = self.generate_top_25()
        if top_25:
            return top_25[0][1]
        return None
    
    def save_poll_to_file(self, filepath: str):
        """Save poll to markdown file"""
        content = self.generate_poll_markdown()
        with open(filepath, 'w') as f:
            f.write(content)


def calculate_strength_of_schedule(team_record: str, opponent_records: List[str]) -> float:
    """
    Calculate strength of schedule based on opponents
    
    Args:
        team_record: e.g., "8-3"
        opponent_records: List of opponent records, e.g., ["7-4", "9-2", ...]
    
    Returns:
        SOS value (0.0 to 1.0)
    """
    opponent_win_pcts = []
    
    for record in opponent_records:
        try:
            wins, losses = map(int, record.split('-'))
            total = wins + losses
            win_pct = wins / total if total > 0 else 0.0
            opponent_win_pcts.append(win_pct)
        except ValueError:
            continue
    
    if not opponent_win_pcts:
        return 0.5
    
    return sum(opponent_win_pcts) / len(opponent_win_pcts)
