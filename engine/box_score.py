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
        self.tempo = game_data.get('tempo', 'standard')
    
    def generate(self) -> str:
        """Generate complete box score"""
        lines = []

        # Header
        lines.append("# VIPERBALL BOX SCORE")
        lines.append("")
        if self.tempo == "uptempo":
            lines.append("> **TEMPO: UP-TEMPO** -- Fast-paced, lateral-heavy offensive game")
            lines.append("")
        lines.append(f"**{self.away['team']}** @ **{self.home['team']}**")
        lines.append("")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Quarter-by-Quarter Scoring
        lines.append("## SCORING SUMMARY")
        lines.append("")

        # Build quarter scores from play-by-play
        away_q = {1: 0, 2: 0, 3: 0, 4: 0}
        home_q = {1: 0, 2: 0, 3: 0, 4: 0}
        for play in self.game_data['play_by_play']:
            q = play['quarter']
            if q not in away_q:
                continue
            if play['result'] == 'touchdown':
                if play['possession'] == 'home':
                    home_q[q] += 6
                else:
                    away_q[q] += 6
            elif play['result'] == 'successful_kick':
                pts = 5 if play['play_type'] == 'drop_kick' else 3
                if play['possession'] == 'home':
                    home_q[q] += pts
                else:
                    away_q[q] += pts

        lines.append("| Team | Q1 | Q2 | Q3 | Q4 | Final |")
        lines.append("|------|----|----|----|----|-------|")
        lines.append(f"| {self.away['team']} | {away_q[1]} | {away_q[2]} | {away_q[3]} | {away_q[4]} | **{self.away['score']}** |")
        lines.append(f"| {self.home['team']} | {home_q[1]} | {home_q[2]} | {home_q[3]} | {home_q[4]} | **{self.home['score']}** |")
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

        # Scoring Breakdown
        lines.append("## SCORING BREAKDOWN")
        lines.append("")
        away_td = self.away_stats.get('touchdowns', 0)
        home_td = self.home_stats.get('touchdowns', 0)
        lines.append(f"| Category | {self.away['team']} | {self.home['team']} |")
        lines.append(f"|----------|" + "-" * (len(self.away['team']) + 2) + "|" + "-" * (len(self.home['team']) + 2) + "|")
        lines.append(f"| Touchdowns (6 pts) | {away_td} ({away_td * 6} pts) | {home_td} ({home_td * 6} pts) |")
        lines.append(f"| Drop Kicks (5 pts) | {self.away_stats['drop_kicks_made']} ({self.away_stats['drop_kicks_made'] * 5} pts) | {self.home_stats['drop_kicks_made']} ({self.home_stats['drop_kicks_made'] * 5} pts) |")
        lines.append(f"| Place Kicks (3 pts) | {self.away_stats['place_kicks_made']} ({self.away_stats['place_kicks_made'] * 3} pts) | {self.home_stats['place_kicks_made']} ({self.home_stats['place_kicks_made'] * 3} pts) |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Standard Statistics
        lines.append("## TEAM STATISTICS")
        lines.append("")
        lines.append(f"| Statistic | {self.away['team']} | {self.home['team']} |")
        lines.append(f"|-----------|" + "-" * (len(self.away['team']) + 2) + "|" + "-" * (len(self.home['team']) + 2) + "|")
        lines.append(f"| Total Yards | {self.away_stats['total_yards']} | {self.home_stats['total_yards']} |")
        lines.append(f"| Total Plays | {self.away_stats['total_plays']} | {self.home_stats['total_plays']} |")
        lines.append(f"| Yards/Play | {self.away_stats['yards_per_play']} | {self.home_stats['yards_per_play']} |")
        lines.append(f"| Touchdowns | {self.away_stats.get('touchdowns', 0)} | {self.home_stats.get('touchdowns', 0)} |")
        lines.append(f"| Lateral Chains | {self.away_stats['lateral_chains']} | {self.home_stats['lateral_chains']} |")
        lines.append(f"| Successful Laterals | {self.away_stats['successful_laterals']} | {self.home_stats['successful_laterals']} |")
        lines.append(f"| Fumbles Lost | {self.away_stats.get('fumbles_lost', 0)} | {self.home_stats.get('fumbles_lost', 0)} |")
        lines.append(f"| Turnovers on Downs | {self.away_stats.get('turnovers_on_downs', 0)} | {self.home_stats.get('turnovers_on_downs', 0)} |")
        lines.append(f"| Drop Kicks Made | {self.away_stats['drop_kicks_made']} | {self.home_stats['drop_kicks_made']} |")
        lines.append(f"| Place Kicks Made | {self.away_stats['place_kicks_made']} | {self.home_stats['place_kicks_made']} |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Advanced Metrics
        lines.append("## ADVANCED METRICS")
        lines.append("")
        lines.append("### Viper Efficiency")
        lines.append("*Formula: (Total Yards / Plays) x (1 + Lateral Success Rate) x Viper Impact*")
        lines.append("")
        lines.append(f"| Team | Viper Efficiency |")
        lines.append(f"|------|------------------|")
        lines.append(f"| {self.away['team']} | {self.away_stats['viper_efficiency']:.2f} |")
        lines.append(f"| {self.home['team']} | {self.home_stats['viper_efficiency']:.2f} |")
        lines.append("")

        lines.append("### Micro-Scoring Differential")
        lines.append("*Formula: (Drop Kicks Made x 5) - (Place Kicks Made x 3)*")
        lines.append("")
        lines.append(f"| Team | Micro-Scoring Diff |")
        lines.append(f"|------|-------------------|")
        lines.append(f"| {self.away['team']} | {self.away_stats['micro_scoring_differential']:+d} |")
        lines.append(f"| {self.home['team']} | {self.home_stats['micro_scoring_differential']:+d} |")
        lines.append("")

        lines.append("### Lateral Efficiency")
        lines.append("*Formula: (Successful Lateral Chains / Total Lateral Attempts) x 100%*")
        lines.append("")
        lines.append(f"| Team | Lateral Efficiency |")
        lines.append(f"|------|--------------------|")
        lines.append(f"| {self.away['team']} | {self.away_stats['lateral_efficiency']:.1f}% |")
        lines.append(f"| {self.home['team']} | {self.home_stats['lateral_efficiency']:.1f}% |")
        lines.append("")

        # Tempo section for uptempo games
        if self.tempo == "uptempo":
            lines.append("### Tempo Analysis")
            lines.append("*Plays per quarter breakdown -- up-tempo games average 35+ plays per team*")
            lines.append("")
            away_ppq = self.away_stats.get('plays_per_quarter', {})
            home_ppq = self.home_stats.get('plays_per_quarter', {})
            lines.append(f"| Team | Q1 | Q2 | Q3 | Q4 | Total |")
            lines.append(f"|------|----|----|----|----|-------|")
            aq = [away_ppq.get(str(q), away_ppq.get(q, 0)) for q in range(1, 5)]
            hq = [home_ppq.get(str(q), home_ppq.get(q, 0)) for q in range(1, 5)]
            lines.append(f"| {self.away['team']} | {aq[0]} | {aq[1]} | {aq[2]} | {aq[3]} | {sum(aq)} |")
            lines.append(f"| {self.home['team']} | {hq[0]} | {hq[1]} | {hq[2]} | {hq[3]} | {sum(hq)} |")
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
            elif play.get('fumble'):
                key_plays.append(play)

        if key_plays:
            for play in key_plays[:15]:  # Show top 15 key plays for uptempo
                quarter = play['quarter']
                time = play['time_remaining']
                minutes = time // 60
                seconds = time % 60
                team_label = "HOME" if play['possession'] == 'home' else 'AWAY'
                lines.append(f"- **Q{quarter} {minutes:02d}:{seconds:02d}** [{team_label}] {play['description']}")
        else:
            lines.append("*No significant plays recorded*")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Game Notes
        lines.append("## GAME NOTES")
        lines.append("")
        lines.append(f"- **CVL Rules:** 5-for-20 down system, 15-minute quarters")
        if self.tempo == "uptempo":
            lines.append(f"- **Tempo:** Up-tempo offense (both teams)")
        lines.append(f"- **Total Plays:** {self.home_stats['total_plays'] + self.away_stats['total_plays']}")
        lines.append(f"- **Combined Yards:** {self.home_stats['total_yards'] + self.away_stats['total_yards']}")

        # Identify the more aggressive team
        total_drop_kicks = self.home_stats['drop_kicks_made'] + self.away_stats['drop_kicks_made']
        if total_drop_kicks > 0:
            lines.append(f"- **Aggressive Play:** {total_drop_kicks} drop kick(s) made in this game")

        total_laterals = self.home_stats['lateral_chains'] + self.away_stats['lateral_chains']
        if total_laterals > 10:
            lines.append(f"- **High Lateral Usage:** {total_laterals} lateral chains executed")

        total_fumbles = self.home_stats.get('fumbles_lost', 0) + self.away_stats.get('fumbles_lost', 0)
        if total_fumbles > 0:
            lines.append(f"- **Turnovers:** {total_fumbles} fumble(s) lost in this game")

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
