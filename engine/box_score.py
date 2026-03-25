"""
Box Score Generator for Collegiate Viperball
Generates markdown-formatted box scores with advanced metrics
"""

from typing import Dict, List
from datetime import datetime


def _fmt_pts(v):
    """Format a point value: whole numbers without .0, half-points with ½."""
    if isinstance(v, (int, float)):
        whole = int(v)
        frac = v - whole
        if abs(frac) < 0.01:
            return str(whole)
        elif abs(frac - 0.5) < 0.01:
            return f"{whole}½" if whole > 0 else "½"
    return str(v)


def _fmt_time(seconds: int) -> str:
    """Format seconds as MM:SS."""
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


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

        away_name = self.away['team']
        home_name = self.home['team']
        away_score = self.away['score']
        home_score = self.home['score']

        # ══════════════════════════════════════════════════════════
        # HEADER — Prominent matchup with HOME/AWAY clearly marked
        # ══════════════════════════════════════════════════════════
        lines.append("# VIPERBALL BOX SCORE")
        lines.append("")
        if self.tempo == "uptempo":
            lines.append("> **TEMPO: UP-TEMPO** -- Fast-paced, lateral-heavy offensive game")
            lines.append("")

        # Big scoreboard-style header
        lines.append(f"## {away_name} {_fmt_pts(away_score)}  —  {home_name} {_fmt_pts(home_score)}")
        lines.append("")
        lines.append(f"| | **{away_name}** | | **{home_name}** |")
        lines.append("|---|---|---|---|")
        lines.append(f"| Role | AWAY | | HOME |")
        lines.append(f"| Final | **{_fmt_pts(away_score)}** | | **{_fmt_pts(home_score)}** |")
        lines.append("")

        # Determine winner
        margin = abs(home_score - away_score)
        if home_score > away_score:
            winner = f"**{home_name}** (HOME) wins by {_fmt_pts(margin)}"
        elif away_score > home_score:
            winner = f"**{away_name}** (AWAY) wins by {_fmt_pts(margin)}"
        else:
            winner = "Game ended in a tie"
        lines.append(winner)
        lines.append("")

        # Weather and context
        weather_label = self.game_data.get('weather_label', '')
        if weather_label:
            lines.append(f"*Conditions: {weather_label}*")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ══════════════════════════════════════════════════════════
        # SCORING SUMMARY — Quarter-by-quarter
        # ══════════════════════════════════════════════════════════
        lines.append("## SCORING SUMMARY")
        lines.append("")

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
        lines.append(f"| {away_name} (AWAY) | {_fmt_pts(away_q[1])} | {_fmt_pts(away_q[2])} | {_fmt_pts(away_q[3])} | {_fmt_pts(away_q[4])} | **{_fmt_pts(away_score)}** |")
        lines.append(f"| {home_name} (HOME) | {_fmt_pts(home_q[1])} | {_fmt_pts(home_q[2])} | {_fmt_pts(home_q[3])} | {_fmt_pts(home_q[4])} | **{_fmt_pts(home_score)}** |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ══════════════════════════════════════════════════════════
        # SCORING BREAKDOWN — All 6 scoring channels
        # ══════════════════════════════════════════════════════════
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
                if pos == 'home':
                    away_safeties += 1
                else:
                    home_safeties += 1
            elif r == 'fumble':
                if pos == 'home':
                    home_bells += 1
                else:
                    away_bells += 1

        lines.append(f"| Category | {away_name} (AWAY) | {home_name} (HOME) |")
        lines.append(f"|----------|" + "-" * (len(away_name) + 9) + "|" + "-" * (len(home_name) + 9) + "|")
        lines.append(f"| Touchdowns (9 pts) | {away_all_td} ({away_all_td * 9} pts) | {home_all_td} ({home_all_td * 9} pts) |")
        lines.append(f"| Snap Kicks (5 pts) | {self.away_stats['drop_kicks_made']} ({self.away_stats['drop_kicks_made'] * 5} pts) | {self.home_stats['drop_kicks_made']} ({self.home_stats['drop_kicks_made'] * 5} pts) |")
        lines.append(f"| Field Goals (3 pts) | {self.away_stats['place_kicks_made']} ({self.away_stats['place_kicks_made'] * 3} pts) | {self.home_stats['place_kicks_made']} ({self.home_stats['place_kicks_made'] * 3} pts) |")
        if away_safeties or home_safeties:
            lines.append(f"| Safeties (2 pts) | {away_safeties} ({away_safeties * 2} pts) | {home_safeties} ({home_safeties * 2} pts) |")
        if away_pindowns or home_pindowns:
            lines.append(f"| Pindowns (1 pt) | {away_pindowns} ({away_pindowns} pts) | {home_pindowns} ({home_pindowns} pts) |")
        if away_bells or home_bells:
            lines.append(f"| Bells (½ pt) | {away_bells} ({_fmt_pts(away_bells * 0.5)} pts) | {home_bells} ({_fmt_pts(home_bells * 0.5)} pts) |")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ══════════════════════════════════════════════════════════
        # TEAM STATISTICS
        # ══════════════════════════════════════════════════════════
        lines.append("## TEAM STATISTICS")
        lines.append("")
        hdr = f"| Statistic | {away_name} (AWAY) | {home_name} (HOME) |"
        sep = f"|-----------|" + "-" * (len(away_name) + 9) + "|" + "-" * (len(home_name) + 9) + "|"
        lines.append(hdr)
        lines.append(sep)
        lines.append(f"| Total Yards | {self.away_stats['total_yards']} | {self.home_stats['total_yards']} |")
        lines.append(f"| Total Plays | {self.away_stats['total_plays']} | {self.home_stats['total_plays']} |")
        lines.append(f"| Yards/Play | {self.away_stats['yards_per_play']} | {self.home_stats['yards_per_play']} |")
        lines.append(f"| Touchdowns | {self.away_stats.get('touchdowns', 0)} | {self.home_stats.get('touchdowns', 0)} |")

        # Time of Possession (estimated from play counts and tempo)
        away_plays = self.away_stats.get('total_plays', 0)
        home_plays = self.home_stats.get('total_plays', 0)
        total_plays = away_plays + home_plays
        if total_plays > 0:
            # 2400 total seconds in a game (4 x 10-minute quarters)
            total_seconds = 2400
            away_top = round(total_seconds * away_plays / total_plays)
            home_top = total_seconds - away_top
            lines.append(f"| Time of Possession | {_fmt_time(away_top)} | {_fmt_time(home_top)} |")

        # Rushing
        away_rc = self.away_stats.get('rushing_carries', 0)
        home_rc = self.home_stats.get('rushing_carries', 0)
        away_ry = self.away_stats.get('rushing_yards', 0)
        home_ry = self.home_stats.get('rushing_yards', 0)
        lines.append(f"| **--- RUSHING ---** | | |")
        lines.append(f"| Rushing | {away_rc} car, {away_ry} yds | {home_rc} car, {home_ry} yds |")
        lines.append(f"| Rushing TDs | {self.away_stats.get('rushing_touchdowns', 0)} | {self.home_stats.get('rushing_touchdowns', 0)} |")

        # Kick Passing
        away_kp_comp = self.away_stats.get('kick_passes_completed', 0)
        away_kp_att = self.away_stats.get('kick_passes_attempted', 0)
        home_kp_comp = self.home_stats.get('kick_passes_completed', 0)
        home_kp_att = self.home_stats.get('kick_passes_attempted', 0)
        lines.append(f"| **--- KICK PASSING ---** | | |")
        lines.append(f"| Kick Passes | {away_kp_comp}/{away_kp_att} | {home_kp_comp}/{home_kp_att} |")
        lines.append(f"| Kick Pass Yards | {self.away_stats.get('kick_pass_yards', 0)} | {self.home_stats.get('kick_pass_yards', 0)} |")
        lines.append(f"| Kick Pass TDs | {self.away_stats.get('kick_pass_tds', 0)} | {self.home_stats.get('kick_pass_tds', 0)} |")
        lines.append(f"| Kick Pass INTs | {self.away_stats.get('kick_pass_interceptions', 0)} | {self.home_stats.get('kick_pass_interceptions', 0)} |")

        # Laterals
        lines.append(f"| **--- LATERALS ---** | | |")
        lines.append(f"| Lateral Chains | {self.away_stats['lateral_chains']} | {self.home_stats['lateral_chains']} |")
        lines.append(f"| Successful Laterals | {self.away_stats['successful_laterals']} | {self.home_stats['successful_laterals']} |")
        lines.append(f"| Lateral INTs | {self.away_stats.get('lateral_interceptions', 0)} | {self.home_stats.get('lateral_interceptions', 0)} |")

        # Turnovers
        away_total_to = (self.away_stats.get('fumbles_lost', 0)
                         + self.away_stats.get('turnovers_on_downs', 0)
                         + self.away_stats.get('kick_pass_interceptions', 0)
                         + self.away_stats.get('lateral_interceptions', 0))
        home_total_to = (self.home_stats.get('fumbles_lost', 0)
                         + self.home_stats.get('turnovers_on_downs', 0)
                         + self.home_stats.get('kick_pass_interceptions', 0)
                         + self.home_stats.get('lateral_interceptions', 0))
        lines.append(f"| **--- TURNOVERS ---** | | |")
        lines.append(f"| **Total Turnovers** | **{away_total_to}** | **{home_total_to}** |")
        lines.append(f"| Fumbles Lost | {self.away_stats.get('fumbles_lost', 0)} | {self.home_stats.get('fumbles_lost', 0)} |")
        lines.append(f"| Turnovers on Downs | {self.away_stats.get('turnovers_on_downs', 0)} | {self.home_stats.get('turnovers_on_downs', 0)} |")

        # Kicking
        lines.append(f"| **--- KICKING ---** | | |")
        lines.append(f"| Drop Kicks | {self.away_stats['drop_kicks_made']}/{self.away_stats.get('drop_kicks_attempted', 0)} | {self.home_stats['drop_kicks_made']}/{self.home_stats.get('drop_kicks_attempted', 0)} |")
        lines.append(f"| Place Kicks | {self.away_stats['place_kicks_made']}/{self.away_stats.get('place_kicks_attempted', 0)} | {self.home_stats['place_kicks_made']}/{self.home_stats.get('place_kicks_attempted', 0)} |")
        lines.append(f"| Punts | {self.away_stats.get('punts', 0)} | {self.home_stats.get('punts', 0)} |")

        # Special Teams Returns
        away_kr = self.away_stats.get('kick_returns', 0)
        away_kr_yds = self.away_stats.get('kick_return_yards', 0)
        home_kr = self.home_stats.get('kick_returns', 0)
        home_kr_yds = self.home_stats.get('kick_return_yards', 0)
        away_pr = self.away_stats.get('punt_returns', 0)
        away_pr_yds = self.away_stats.get('punt_return_yards', 0)
        home_pr = self.home_stats.get('punt_returns', 0)
        home_pr_yds = self.home_stats.get('punt_return_yards', 0)
        if away_kr or home_kr or away_pr or home_pr:
            lines.append(f"| **--- SPECIAL TEAMS ---** | | |")
            if away_kr or home_kr:
                lines.append(f"| Kick Returns | {away_kr} for {away_kr_yds} yds | {home_kr} for {home_kr_yds} yds |")
                away_kr_tds = self.away_stats.get('kick_return_tds', 0)
                home_kr_tds = self.home_stats.get('kick_return_tds', 0)
                if away_kr_tds or home_kr_tds:
                    lines.append(f"| Kick Return TDs | {away_kr_tds} | {home_kr_tds} |")
            if away_pr or home_pr:
                lines.append(f"| Punt Returns | {away_pr} for {away_pr_yds} yds | {home_pr} for {home_pr_yds} yds |")
                away_pr_tds = self.away_stats.get('punt_return_tds', 0)
                home_pr_tds = self.home_stats.get('punt_return_tds', 0)
                if away_pr_tds or home_pr_tds:
                    lines.append(f"| Punt Return TDs | {away_pr_tds} | {home_pr_tds} |")
            away_muffs = self.away_stats.get('muffs', 0)
            home_muffs = self.home_stats.get('muffs', 0)
            if away_muffs or home_muffs:
                lines.append(f"| Muffs | {away_muffs} | {home_muffs} |")

        # Penalties
        away_pen = self.away_stats.get('penalties', 0)
        home_pen = self.home_stats.get('penalties', 0)
        away_pen_dec = self.away_stats.get('penalties_declined', 0)
        home_pen_dec = self.home_stats.get('penalties_declined', 0)
        if away_pen or home_pen or away_pen_dec or home_pen_dec:
            lines.append(f"| **--- PENALTIES ---** | | |")
            lines.append(f"| Penalties | {away_pen} for {self.away_stats.get('penalty_yards', 0)} yds | {home_pen} for {self.home_stats.get('penalty_yards', 0)} yds |")
            if away_pen_dec or home_pen_dec:
                lines.append(f"| Penalties Declined | {away_pen_dec} | {home_pen_dec} |")

        # Down Conversions
        away_dc = self.away_stats.get('down_conversions', {})
        home_dc = self.home_stats.get('down_conversions', {})
        has_dc = False
        for d in [4, 5, 6]:
            adc = away_dc.get(d, away_dc.get(str(d), {}))
            hdc = home_dc.get(d, home_dc.get(str(d), {}))
            a_att = adc.get('attempts', 0) if isinstance(adc, dict) else 0
            h_att = hdc.get('attempts', 0) if isinstance(hdc, dict) else 0
            if a_att or h_att:
                if not has_dc:
                    lines.append(f"| **--- DOWN CONVERSIONS ---** | | |")
                    has_dc = True
                a_conv = adc.get('converted', 0) if isinstance(adc, dict) else 0
                h_conv = hdc.get('converted', 0) if isinstance(hdc, dict) else 0
                a_rate = round(a_conv / max(1, a_att) * 100) if a_att else 0
                h_rate = round(h_conv / max(1, h_att) * 100) if h_att else 0
                lines.append(f"| {d}th Down Conv. | {a_conv}/{a_att} ({a_rate}%) | {h_conv}/{h_att} ({h_rate}%) |")

        # Bonus Possessions
        away_bp = self.away_stats.get('bonus_possessions', 0)
        home_bp = self.home_stats.get('bonus_possessions', 0)
        if away_bp or home_bp:
            lines.append(f"| Bonus Possessions | {away_bp} | {home_bp} |")
            lines.append(f"| Bonus Poss. Yards | {self.away_stats.get('bonus_possession_yards', 0)} | {self.home_stats.get('bonus_possession_yards', 0)} |")
            lines.append(f"| Bonus Poss. Scores | {self.away_stats.get('bonus_possession_scores', 0)} | {self.home_stats.get('bonus_possession_scores', 0)} |")

        lines.append("")
        lines.append("---")
        lines.append("")

        # ══════════════════════════════════════════════════════════
        # INDIVIDUAL LEADERS
        # ══════════════════════════════════════════════════════════
        home_players = self.game_data.get('player_stats', {}).get('home', [])
        away_players = self.game_data.get('player_stats', {}).get('away', [])

        if home_players or away_players:
            lines.append("## INDIVIDUAL LEADERS")
            lines.append("")

            # Rushing leaders
            all_rushers = ([(p, away_name) for p in away_players if p.get('rush_carries', 0) > 0]
                          + [(p, home_name) for p in home_players if p.get('rush_carries', 0) > 0])
            all_rushers.sort(key=lambda x: x[0].get('rushing_yards', 0), reverse=True)
            if all_rushers:
                lines.append("### Rushing")
                lines.append("")
                lines.append("| Player | Team | Car | Yds | TDs |")
                lines.append("|--------|------|-----|-----|-----|")
                for rusher, team in all_rushers[:5]:
                    lines.append(f"| {rusher['name']} | {team} | {rusher.get('rush_carries', 0)} | {rusher.get('rushing_yards', 0)} | {rusher.get('rushing_tds', 0)} |")
                lines.append("")

            # Kick passing leaders (throwers)
            all_passers = ([(p, away_name) for p in away_players if p.get('kick_passes_thrown', 0) > 0]
                          + [(p, home_name) for p in home_players if p.get('kick_passes_thrown', 0) > 0])
            all_passers.sort(key=lambda x: x[0].get('kick_pass_yards', 0), reverse=True)
            if all_passers:
                lines.append("### Kick Passing")
                lines.append("")
                lines.append("| Player | Team | Comp/Att | Yds | TDs | INTs |")
                lines.append("|--------|------|----------|-----|-----|------|")
                for passer, team in all_passers[:3]:
                    comp = passer.get('kick_passes_completed', 0)
                    att = passer.get('kick_passes_thrown', 0)
                    lines.append(f"| {passer['name']} | {team} | {comp}/{att} | {passer.get('kick_pass_yards', 0)} | {passer.get('kick_pass_tds', 0)} | {passer.get('kick_pass_interceptions_thrown', 0)} |")
                lines.append("")

            # Receiving leaders
            all_receivers = ([(p, away_name) for p in away_players if p.get('kick_pass_receptions', 0) > 0]
                            + [(p, home_name) for p in home_players if p.get('kick_pass_receptions', 0) > 0])
            all_receivers.sort(key=lambda x: x[0].get('kick_pass_yards', 0), reverse=True)
            if all_receivers:
                lines.append("### Receiving")
                lines.append("")
                lines.append("| Player | Team | Rec | Yds | TDs |")
                lines.append("|--------|------|-----|-----|-----|")
                for recv, team in all_receivers[:5]:
                    # kick_pass_yards on a receiver is receiving yards
                    lines.append(f"| {recv['name']} | {team} | {recv.get('kick_pass_receptions', 0)} | {recv.get('kick_pass_yards', 0)} | {recv.get('kick_pass_tds', 0)} |")
                lines.append("")

            # Defensive leaders
            all_defenders = ([(p, away_name) for p in away_players if p.get('tackles', 0) > 0]
                            + [(p, home_name) for p in home_players if p.get('tackles', 0) > 0])
            all_defenders.sort(key=lambda x: x[0].get('tackles', 0), reverse=True)
            if all_defenders:
                lines.append("### Defense")
                lines.append("")
                lines.append("| Player | Team | Tkl | TFL | Sacks | Hurries |")
                lines.append("|--------|------|-----|-----|-------|---------|")
                for defender, team in all_defenders[:5]:
                    lines.append(f"| {defender['name']} | {team} | {defender.get('tackles', 0)} | {defender.get('tfl', 0)} | {defender.get('sacks', 0)} | {defender.get('hurries', 0)} |")
                lines.append("")

            lines.append("---")
            lines.append("")

        # ══════════════════════════════════════════════════════════
        # ADVANCED METRICS
        # ══════════════════════════════════════════════════════════
        lines.append("## ADVANCED METRICS")
        lines.append("")
        lines.append("### Viper Efficiency")
        lines.append("*Yards per play boosted by lateral success. Higher = better. Think of it as 'how well does this team use Viperball mechanics?' Average ~5, elite 8+.*")
        lines.append("")
        lines.append(f"| Team | Viper Efficiency |")
        lines.append(f"|------|------------------|")
        lines.append(f"| {away_name} (AWAY) | {self.away_stats['viper_efficiency']:.2f} |")
        lines.append(f"| {home_name} (HOME) | {self.home_stats['viper_efficiency']:.2f} |")
        lines.append("")

        lines.append("### Kicking Aggression Index")
        lines.append("*Snap Kick share of total kick attempts — higher = more aggressive kicking*")
        lines.append("*DKs risk return TDs on misses but pay 5 pts vs 3 for safe FGs*")
        lines.append("")
        away_dk_att = self.away_stats.get('drop_kicks_attempted', 0)
        away_pk_att = self.away_stats.get('place_kicks_attempted', 0)
        home_dk_att = self.home_stats.get('drop_kicks_attempted', 0)
        home_pk_att = self.home_stats.get('place_kicks_attempted', 0)
        away_total_kicks = away_dk_att + away_pk_att
        home_total_kicks = home_dk_att + home_pk_att
        away_kai = round(away_dk_att / max(1, away_total_kicks) * 100, 1)
        home_kai = round(home_dk_att / max(1, home_total_kicks) * 100, 1)
        away_kick_pts = self.away_stats['drop_kicks_made'] * 5 + self.away_stats['place_kicks_made'] * 3
        home_kick_pts = self.home_stats['drop_kicks_made'] * 5 + self.home_stats['place_kicks_made'] * 3
        lines.append(f"| Team | DK/Total Kicks | Kick Points |")
        lines.append(f"|------|----------------|-------------|")
        lines.append(f"| {away_name} | {away_dk_att}/{away_total_kicks} ({away_kai}%) | {away_kick_pts} |")
        lines.append(f"| {home_name} | {home_dk_att}/{home_total_kicks} ({home_kai}%) | {home_kick_pts} |")
        lines.append("")

        lines.append("### Lateral Efficiency")
        lines.append("*How often lateral chains succeed without turnovers. 70%+ is solid, below 50% means too many fumbles.*")
        lines.append("")
        lines.append(f"| Team | Lateral Efficiency |")
        lines.append(f"|------|--------------------|")
        lines.append(f"| {away_name} | {self.away_stats['lateral_efficiency']:.1f}% |")
        lines.append(f"| {home_name} | {self.home_stats['lateral_efficiency']:.1f}% |")
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
            lines.append(f"| {away_name} | {aq[0]} | {aq[1]} | {aq[2]} | {aq[3]} | {sum(aq)} |")
            lines.append(f"| {home_name} | {hq[0]} | {hq[1]} | {hq[2]} | {hq[3]} | {sum(hq)} |")
            lines.append("")

        lines.append("---")
        lines.append("")

        # ══════════════════════════════════════════════════════════
        # REFEREE SCORECARD
        # ══════════════════════════════════════════════════════════
        referee = self.game_data.get('referee', {})
        if referee:
            lines.append("## REFEREE SCORECARD")
            lines.append("")
            accuracy_pct = round(referee.get('accuracy', 0.95) * 100, 1)
            consistency_pct = round(referee.get('consistency', 0.94) * 100, 1)
            home_favor = referee.get('home_favor', 0)
            blown_calls = referee.get('blown_calls', 0)

            # Favor label
            if abs(home_favor) < 0.05:
                favor_label = "Neutral"
            elif home_favor > 0:
                favor_label = f"+{round(home_favor, 2)} toward {home_name}"
            else:
                favor_label = f"+{round(abs(home_favor), 2)} toward {away_name}"

            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Overall Accuracy | {accuracy_pct}% |")
            lines.append(f"| Consistency | {consistency_pct}% |")
            lines.append(f"| Favor | {favor_label} |")
            lines.append(f"| Blown Calls | {blown_calls} |")
            lines.append("")

            blown_call_log = referee.get('blown_call_log', [])
            if blown_call_log:
                lines.append("### Blown Call Details")
                lines.append("")
                for bc in blown_call_log:
                    q = bc.get('quarter', '?')
                    time = bc.get('time_remaining', 0)
                    bc_type = bc.get('type', 'unknown')
                    if bc_type == "phantom_flag":
                        pen_name = bc.get('penalty_called', '?')
                        on_team = bc.get('on_team', '?')
                        team_label = home_name if on_team == 'home' else away_name
                        lines.append(f"- **Q{q} {_fmt_time(time)}** — Phantom flag: {pen_name} called on {team_label} ({bc.get('player', '?')}). No actual infraction.")
                    elif bc_type == "swallowed_whistle":
                        pen_name = bc.get('penalty_missed', '?')
                        on_team = bc.get('on_team', '?')
                        team_label = home_name if on_team == 'home' else away_name
                        lines.append(f"- **Q{q} {_fmt_time(time)}** — Swallowed whistle: {pen_name} on {team_label} ({bc.get('player', '?')}) went uncalled.")
                    elif bc_type == "spot_error":
                        error = bc.get('error_yards', 0)
                        direction = "forward" if error > 0 else "back"
                        poss = bc.get('possession', '?')
                        team_label = home_name if poss == 'home' else away_name
                        lines.append(f"- **Q{q} {_fmt_time(time)}** — Spot error: Ball spotted {abs(error)} yd(s) {direction} of correct position ({team_label} possession).")
                lines.append("")

            lines.append("---")
            lines.append("")

        # ══════════════════════════════════════════════════════════
        # KEY PLAYS
        # ══════════════════════════════════════════════════════════
        lines.append("## KEY PLAYS")
        lines.append("")

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
            for play in key_plays[:15]:
                quarter = play['quarter']
                time = play['time_remaining']
                pos = play['possession']
                team_label = f"{home_name}" if pos == 'home' else f"{away_name}"
                side_label = "HOME" if pos == 'home' else "AWAY"
                lines.append(f"- **Q{quarter} {_fmt_time(time)}** [{side_label} — {team_label}] {play['description']}")
        else:
            lines.append("*No significant plays recorded*")

        lines.append("")
        lines.append("---")
        lines.append("")

        # ══════════════════════════════════════════════════════════
        # GAME NOTES
        # ══════════════════════════════════════════════════════════
        lines.append("## GAME NOTES")
        lines.append("")
        lines.append(f"- **CVL Rules:** 6-for-20 down system, 10-minute quarters")
        if self.tempo == "uptempo":
            lines.append(f"- **Tempo:** Up-tempo offense (both teams)")
        if weather_label:
            lines.append(f"- **Weather:** {weather_label}")
        lines.append(f"- **Total Plays:** {self.home_stats['total_plays'] + self.away_stats['total_plays']}")
        lines.append(f"- **Combined Yards:** {self.home_stats['total_yards'] + self.away_stats['total_yards']}")

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
        lines.append(f"*Collegiate Viperball League (CVL) Official Box Score — {away_name} (AWAY) at {home_name} (HOME)*")

        return "\n".join(lines)

    def save_to_file(self, filepath: str):
        """Save box score to markdown file"""
        content = self.generate()
        with open(filepath, 'w') as f:
            f.write(content)
