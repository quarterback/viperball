"""
Box Score Generator for Collegiate Viperball
Generates markdown-formatted box scores with advanced metrics
"""

from typing import Dict
from datetime import datetime


def _fmt_pts(v):
    """Format a point value: whole numbers without .0, half-points with \u00bd."""
    if isinstance(v, (int, float)):
        whole = int(v)
        frac = v - whole
        if abs(frac) < 0.01:
            return str(whole)
        elif abs(frac - 0.5) < 0.01:
            return f"{whole}\u00bd" if whole > 0 else "\u00bd"
    return str(v)


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

        # Build quarter scores from running score deltas in play-by-play
        away_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        home_q = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        plays = self.game_data['play_by_play']
        if plays and 'home_score' in plays[0]:
            prev_home = 0.0
            prev_away = 0.0
            for play in plays:
                q = play['quarter']
                if q not in home_q:
                    continue
                cur_home = play.get('home_score', prev_home)
                cur_away = play.get('away_score', prev_away)
                home_q[q] += cur_home - prev_home
                away_q[q] += cur_away - prev_away
                prev_home = cur_home
                prev_away = cur_away

        lines.append("| Team | Q1 | Q2 | Q3 | Q4 | Final |")
        lines.append("|------|----|----|----|----|-------|")
        lines.append(f"| {self.away['team']} | {_fmt_pts(away_q[1])} | {_fmt_pts(away_q[2])} | {_fmt_pts(away_q[3])} | {_fmt_pts(away_q[4])} | **{_fmt_pts(self.away['score'])}** |")
        lines.append(f"| {self.home['team']} | {_fmt_pts(home_q[1])} | {_fmt_pts(home_q[2])} | {_fmt_pts(home_q[3])} | {_fmt_pts(home_q[4])} | **{_fmt_pts(self.home['score'])}** |")
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

        # Scoring Breakdown — all 6 channels
        # Count all scoring events directly from play-by-play to avoid
        # stats-dict ambiguity (possession is already set to scoring team
        # by the engine for TDs, kicks, pindowns; recovering team for fumbles).
        lines.append("## SCORING BREAKDOWN")
        lines.append("")
        home_all_td = 0
        away_all_td = 0
        away_pindowns = 0
        home_pindowns = 0
        away_safeties = 0
        home_safeties = 0
        away_bells = 0
        home_bells = 0
        for play in self.game_data['play_by_play']:
            r = play['result']
            pos = play['possession']
            if r in ('touchdown', 'punt_return_td', 'int_return_td', 'missed_dk_return_td'):
                if pos == 'home':
                    home_all_td += 1
                else:
                    away_all_td += 1
            elif r == 'pindown':
                if pos == 'home':
                    home_pindowns += 1
                else:
                    away_pindowns += 1
            elif r == 'safety':
                # possession = offense that committed it; opponent scores
                if pos == 'home':
                    away_safeties += 1
                else:
                    home_safeties += 1
            elif r == 'fumble':
                # possession = recovering team
                if pos == 'home':
                    home_bells += 1
                else:
                    away_bells += 1

        lines.append(f"| Category | {self.away['team']} | {self.home['team']} |")
        lines.append(f"|----------|" + "-" * (len(self.away['team']) + 2) + "|" + "-" * (len(self.home['team']) + 2) + "|")
        lines.append(f"| Touchdowns (9 pts) | {away_all_td} ({away_all_td * 9} pts) | {home_all_td} ({home_all_td * 9} pts) |")
        lines.append(f"| Snap Kicks (5 pts) | {self.away_stats['drop_kicks_made']} ({self.away_stats['drop_kicks_made'] * 5} pts) | {self.home_stats['drop_kicks_made']} ({self.home_stats['drop_kicks_made'] * 5} pts) |")
        lines.append(f"| Field Goals (3 pts) | {self.away_stats['place_kicks_made']} ({self.away_stats['place_kicks_made'] * 3} pts) | {self.home_stats['place_kicks_made']} ({self.home_stats['place_kicks_made'] * 3} pts) |")
        if away_safeties or home_safeties:
            lines.append(f"| Safeties (2 pts) | {away_safeties} ({away_safeties * 2} pts) | {home_safeties} ({home_safeties * 2} pts) |")
        if away_pindowns or home_pindowns:
            lines.append(f"| Pindowns (1 pt) | {away_pindowns} ({away_pindowns} pts) | {home_pindowns} ({home_pindowns} pts) |")
        if away_bells or home_bells:
            lines.append(f"| Bells (\u00bd pt) | {away_bells} ({_fmt_pts(away_bells * 0.5)} pts) | {home_bells} ({_fmt_pts(home_bells * 0.5)} pts) |")
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
        away_total_to = (self.away_stats.get('fumbles_lost', 0)
                         + self.away_stats.get('turnovers_on_downs', 0)
                         + self.away_stats.get('kick_pass_interceptions', 0)
                         + self.away_stats.get('lateral_interceptions', 0))
        home_total_to = (self.home_stats.get('fumbles_lost', 0)
                         + self.home_stats.get('turnovers_on_downs', 0)
                         + self.home_stats.get('kick_pass_interceptions', 0)
                         + self.home_stats.get('lateral_interceptions', 0))
        lines.append(f"| **Total Turnovers** | **{away_total_to}** | **{home_total_to}** |")
        lines.append(f"| Fumbles Lost | {self.away_stats.get('fumbles_lost', 0)} | {self.home_stats.get('fumbles_lost', 0)} |")
        lines.append(f"| Turnovers on Downs | {self.away_stats.get('turnovers_on_downs', 0)} | {self.home_stats.get('turnovers_on_downs', 0)} |")
        lines.append(f"| Kick Pass INTs | {self.away_stats.get('kick_pass_interceptions', 0)} | {self.home_stats.get('kick_pass_interceptions', 0)} |")
        lines.append(f"| Lateral INTs | {self.away_stats.get('lateral_interceptions', 0)} | {self.home_stats.get('lateral_interceptions', 0)} |")
        lines.append(f"| Bonus Possessions | {self.away_stats.get('bonus_possessions', 0)} | {self.home_stats.get('bonus_possessions', 0)} |")
        lines.append(f"| Bonus Poss. Yards | {self.away_stats.get('bonus_possession_yards', 0)} | {self.home_stats.get('bonus_possession_yards', 0)} |")
        lines.append(f"| Bonus Poss. Scores | {self.away_stats.get('bonus_possession_scores', 0)} | {self.home_stats.get('bonus_possession_scores', 0)} |")
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
        lines.append("*Formula: (Snap Kicks Made x 5) - (Field Goals Made x 3)*")
        lines.append("")
        away_msd = self.away_stats['drop_kicks_made'] * 5 - self.away_stats['place_kicks_made'] * 3
        home_msd = self.home_stats['drop_kicks_made'] * 5 - self.home_stats['place_kicks_made'] * 3
        lines.append(f"| Team | Micro-Scoring Diff |")
        lines.append(f"|------|-------------------|")
        lines.append(f"| {self.away['team']} | {away_msd:+d} |")
        lines.append(f"| {self.home['team']} | {home_msd:+d} |")
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
            if play['result'] in ('touchdown', 'punt_return_td', 'int_return_td', 'missed_dk_return_td'):
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
        lines.append(f"- **CVL Rules:** 6-for-20 down system, 15-minute quarters")
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

        total_turnovers = (self.home_stats.get('fumbles_lost', 0) + self.away_stats.get('fumbles_lost', 0)
                           + self.home_stats.get('turnovers_on_downs', 0) + self.away_stats.get('turnovers_on_downs', 0)
                           + self.home_stats.get('kick_pass_interceptions', 0) + self.away_stats.get('kick_pass_interceptions', 0)
                           + self.home_stats.get('lateral_interceptions', 0) + self.away_stats.get('lateral_interceptions', 0))
        if total_turnovers > 0:
            lines.append(f"- **Turnovers:** {total_turnovers} total turnovers in this game")

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
