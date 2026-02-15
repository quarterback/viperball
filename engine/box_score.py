"""
Box Score Generator for Collegiate Viperball
Generates markdown-formatted box scores with advanced metrics
"""

from typing import Dict
from datetime import datetime


class BoxScoreGenerator:
    """Generate detailed box scores in markdown format"""
    
    def __init__(self, game_data: Dict):
        self.game_data = game_data
        self.home = game_data['final_score']['home']
        self.away = game_data['final_score']['away']
        self.home_stats = game_data['stats']['home']
        self.away_stats = game_data['stats']['away']
    
    def generate(self) -> str:
        """Generate complete box score"""
        lines = []
        
        # Header
        lines.append("# VIPERBALL BOX SCORE")
        lines.append("")
        lines.append(f"**{self.away['team']}** @ **{self.home['team']}**")
        lines.append("")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Final Score
        lines.append("## FINAL SCORE")
        lines.append("")
        lines.append(f"| Team | Score |")
        lines.append(f"|------|-------|")
        lines.append(f"| {self.away['team']} | **{self.away['score']}** |")
        lines.append(f"| {self.home['team']} | **{self.home['score']}** |")
        lines.append("")
        
        # Determine winner
        if self.home['score'] > self.away['score']:
            winner = f"{self.home['team']} wins by {self.home['score'] - self.away['score']}"
        elif self.away['score'] > self.home['score']:
            winner = f"{self.away['team']} wins by {self.away['score'] - self.home['score']}"
        else:
            winner = "Game ended in a tie"
        
        lines.append(f"**{winner}**")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Standard Statistics
        lines.append("## TEAM STATISTICS")
        lines.append("")
        lines.append("| Statistic | " + self.away['team'] + " | " + self.home['team'] + " |")
        lines.append("|-----------|" + "-" * len(self.away['team']) + "-|-" + "-" * len(self.home['team']) + "-|")
        lines.append(f"| Total Yards | {self.away_stats['total_yards']} | {self.home_stats['total_yards']} |")
        lines.append(f"| Total Plays | {self.away_stats['total_plays']} | {self.home_stats['total_plays']} |")
        lines.append(f"| Yards/Play | {self.away_stats['yards_per_play']} | {self.home_stats['yards_per_play']} |")
        lines.append(f"| Lateral Chains | {self.away_stats['lateral_chains']} | {self.home_stats['lateral_chains']} |")
        lines.append(f"| Successful Laterals | {self.away_stats['successful_laterals']} | {self.home_stats['successful_laterals']} |")
        lines.append(f"| Drop Kicks Made | {self.away_stats['drop_kicks_made']} | {self.home_stats['drop_kicks_made']} |")
        lines.append(f"| Place Kicks Made | {self.away_stats['place_kicks_made']} | {self.home_stats['place_kicks_made']} |")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Advanced Metrics
        lines.append("## ADVANCED METRICS")
        lines.append("")
        lines.append("### Viper Efficiency")
        lines.append("*Formula: (Total Yards / Plays) × (1 + Lateral Success Rate) × Viper Impact*")
        lines.append("")
        lines.append(f"| Team | Viper Efficiency |")
        lines.append(f"|------|------------------|")
        lines.append(f"| {self.away['team']} | {self.away_stats['viper_efficiency']:.2f} |")
        lines.append(f"| {self.home['team']} | {self.home_stats['viper_efficiency']:.2f} |")
        lines.append("")
        
        lines.append("### Micro-Scoring Differential")
        lines.append("*Formula: (Drop Kicks Made × 5) - (Place Kicks Made × 3)*")
        lines.append("")
        lines.append(f"| Team | Micro-Scoring Diff |")
        lines.append(f"|------|-------------------|")
        lines.append(f"| {self.away['team']} | {self.away_stats['micro_scoring_differential']:+d} |")
        lines.append(f"| {self.home['team']} | {self.home_stats['micro_scoring_differential']:+d} |")
        lines.append("")
        
        lines.append("### Lateral Efficiency")
        lines.append("*Formula: (Successful Lateral Chains / Total Lateral Attempts) × 100%*")
        lines.append("")
        lines.append(f"| Team | Lateral Efficiency |")
        lines.append(f"|------|--------------------|")
        lines.append(f"| {self.away['team']} | {self.away_stats['lateral_efficiency']:.1f}% |")
        lines.append(f"| {self.home['team']} | {self.home_stats['lateral_efficiency']:.1f}% |")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Key Plays
        lines.append("## KEY PLAYS")
        lines.append("")
        
        # Find touchdowns and big plays
        key_plays = []
        for play in self.game_data['play_by_play']:
            if play['result'] == 'touchdown':
                key_plays.append(play)
            elif play.get('yards', 0) >= 20:
                key_plays.append(play)
            elif play['play_type'] in ['drop_kick', 'place_kick'] and play['result'] == 'successful_kick':
                key_plays.append(play)
        
        if key_plays:
            for play in key_plays[:10]:  # Show top 10 key plays
                quarter = play['quarter']
                time = play['time_remaining']
                minutes = time // 60
                seconds = time % 60
                lines.append(f"- **Q{quarter} {minutes:02d}:{seconds:02d}** - {play['description']}")
        else:
            lines.append("*No significant plays recorded*")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Game Notes
        lines.append("## GAME NOTES")
        lines.append("")
        lines.append(f"- **CVL Rules:** 5-for-20 down system, 15-minute quarters")
        lines.append(f"- **Total Plays:** {self.home_stats['total_plays'] + self.away_stats['total_plays']}")
        lines.append(f"- **Combined Yards:** {self.home_stats['total_yards'] + self.away_stats['total_yards']}")
        
        # Identify the more aggressive team
        total_drop_kicks = self.home_stats['drop_kicks_made'] + self.away_stats['drop_kicks_made']
        if total_drop_kicks > 0:
            lines.append(f"- **Aggressive Play:** {total_drop_kicks} drop kick(s) attempted in this game")
        
        total_laterals = self.home_stats['lateral_chains'] + self.away_stats['lateral_chains']
        if total_laterals > 10:
            lines.append(f"- **High Lateral Usage:** {total_laterals} lateral chains executed")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Collegiate Viperball League (CVL) Official Box Score*")
        
        return "\n".join(lines)
    
    def save_to_file(self, filepath: str):
        """Save box score to markdown file"""
        content = self.generate()
        with open(filepath, 'w') as f:
            f.write(content)
