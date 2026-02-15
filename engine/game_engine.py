"""
Collegiate Viperball Simulation Engine
Core game simulation logic for CVL games
"""

import random
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class PlayType(Enum):
    """Types of plays in Viperball"""
    RUN = "run"
    LATERAL_CHAIN = "lateral_chain"
    PUNT = "punt"
    DROP_KICK = "drop_kick"
    PLACE_KICK = "place_kick"


class PlayResult(Enum):
    """Possible results of a play"""
    GAIN = "gain"
    FIRST_DOWN = "first_down"
    TOUCHDOWN = "touchdown"
    FUMBLE = "fumble"
    TURNOVER_ON_DOWNS = "turnover_on_downs"
    SUCCESSFUL_KICK = "successful_kick"
    MISSED_KICK = "missed_kick"
    SAFETY = "safety"


@dataclass
class GameState:
    """Current state of the game"""
    quarter: int = 1
    time_remaining: int = 900  # seconds (15 minutes)
    home_score: int = 0
    away_score: int = 0
    possession: str = "home"  # "home" or "away"
    field_position: int = 20  # yards from own goal line
    down: int = 1
    yards_to_go: int = 20  # 5-for-20 system
    play_number: int = 0
    
    # Fatigue tracking (0-100, lower is more fatigued)
    home_stamina: float = 100.0
    away_stamina: float = 100.0


@dataclass
class Player:
    """Player stats and attributes"""
    number: int
    name: str
    position: str
    speed: int
    stamina: int
    kicking: int
    lateral_skill: int
    tackling: int
    current_stamina: float = 100.0


@dataclass
class Team:
    """Team data and roster"""
    name: str
    abbreviation: str
    mascot: str
    players: List[Player]
    avg_speed: int
    avg_stamina: int
    kicking_strength: int
    lateral_proficiency: int
    defensive_strength: int


@dataclass
class Play:
    """Record of a single play"""
    play_number: int
    quarter: int
    time: int
    possession: str
    field_position: int
    down: int
    yards_to_go: int
    play_type: str
    players_involved: List[str]
    yards_gained: int
    result: str
    description: str
    laterals: int = 0
    fumble: bool = False


class ViperballEngine:
    """Main simulation engine for Viperball games"""
    
    def __init__(self, home_team: Team, away_team: Team):
        self.home_team = home_team
        self.away_team = away_team
        self.state = GameState()
        self.play_log: List[Play] = []
        self.viper_position = "free"  # "free", "left", "right", "deep"
        
    def simulate_game(self) -> Dict:
        """Simulate a complete game and return results"""
        # Kickoff to start the game
        self.kickoff("away")
        
        # Play through 4 quarters
        for quarter in range(1, 5):
            self.state.quarter = quarter
            self.state.time_remaining = 900
            
            # Simulate drives for this quarter
            while self.state.time_remaining > 0:
                self.simulate_drive()
                if self.state.time_remaining <= 0:
                    break
        
        return self.generate_game_summary()
    
    def kickoff(self, receiving_team: str):
        """Simulate a kickoff"""
        self.state.possession = receiving_team
        self.state.field_position = 20  # Average kickoff return
        self.state.down = 1
        self.state.yards_to_go = 20
        
    def simulate_drive(self):
        """Simulate a single offensive drive"""
        max_plays = 20  # Prevent infinite loops
        plays_in_drive = 0
        
        while plays_in_drive < max_plays and self.state.time_remaining > 0:
            play = self.simulate_play()
            self.play_log.append(play)
            
            # Update time
            time_elapsed = random.randint(15, 45)
            self.state.time_remaining = max(0, self.state.time_remaining - time_elapsed)
            
            # Check if drive is over
            if play.result in ["touchdown", "turnover_on_downs", "fumble", "successful_kick"]:
                break
            
            plays_in_drive += 1
    
    def simulate_play(self) -> Play:
        """Simulate a single play"""
        self.state.play_number += 1
        
        # Select play type based on situation
        play_type = self.select_play_type()
        
        # Execute the play
        if play_type == PlayType.RUN:
            return self.simulate_run()
        elif play_type == PlayType.LATERAL_CHAIN:
            return self.simulate_lateral_chain()
        elif play_type == PlayType.PUNT:
            return self.simulate_punt()
        elif play_type == PlayType.DROP_KICK:
            return self.simulate_drop_kick()
        elif play_type == PlayType.PLACE_KICK:
            return self.simulate_place_kick()
        else:
            return self.simulate_run()
    
    def select_play_type(self) -> PlayType:
        """Choose play type based on game situation"""
        # Apply fatigue factor
        fatigue_factor = self.get_fatigue_factor()
        
        # 5th down considerations
        if self.state.down == 5:
            if self.state.field_position + self.state.yards_to_go >= 50:
                # In field goal range
                if random.random() < 0.6:
                    return PlayType.PLACE_KICK
                else:
                    return PlayType.DROP_KICK if random.random() < 0.3 else PlayType.RUN
            else:
                # Too far for field goal, likely punt
                if random.random() < 0.7:
                    return PlayType.PUNT
                else:
                    return PlayType.RUN if random.random() < 0.6 else PlayType.LATERAL_CHAIN
        
        # Normal downs
        if self.state.down <= 2:
            # Early downs - be aggressive
            weights = [0.5, 0.3, 0.1, 0.05, 0.05]  # run, lateral, punt, drop, place
        elif self.state.down == 3:
            weights = [0.4, 0.3, 0.15, 0.1, 0.05]
        else:  # down 4
            weights = [0.3, 0.25, 0.25, 0.15, 0.05]
        
        play_types = [PlayType.RUN, PlayType.LATERAL_CHAIN, PlayType.PUNT, 
                     PlayType.DROP_KICK, PlayType.PLACE_KICK]
        
        return random.choices(play_types, weights=weights)[0]
    
    def simulate_run(self) -> Play:
        """Simulate a standard running play"""
        team = self.get_offensive_team()
        
        # Base yards calculation
        base_yards = random.gauss(4, 3)
        
        # Apply team strength and fatigue
        strength_factor = team.avg_speed / 90
        fatigue_factor = self.get_fatigue_factor()
        viper_factor = self.calculate_viper_impact()
        
        yards_gained = int(base_yards * strength_factor * fatigue_factor * viper_factor)
        yards_gained = max(-5, min(yards_gained, 25))  # Bounds checking
        
        # Select random player
        player = random.choice(team.players[:5])  # Use top 5 players
        
        # Update field position
        new_position = min(100, self.state.field_position + yards_gained)
        
        # Check for touchdown
        if new_position >= 100:
            result = PlayResult.TOUCHDOWN
            self.add_score(6)
            description = f"{player.name} rushes for {yards_gained} yards - TOUCHDOWN!"
        else:
            # Check for first down
            if yards_gained >= self.state.yards_to_go:
                result = PlayResult.FIRST_DOWN
                self.state.field_position = new_position
                self.state.down = 1
                self.state.yards_to_go = 20
                description = f"{player.name} rushes for {yards_gained} yards - FIRST DOWN!"
            else:
                result = PlayResult.GAIN
                self.state.field_position = new_position
                self.state.down += 1
                self.state.yards_to_go -= yards_gained
                description = f"{player.name} rushes for {yards_gained} yards"
                
                # Check for turnover on downs
                if self.state.down > 5:
                    result = PlayResult.TURNOVER_ON_DOWNS
                    self.change_possession()
                    description += " - TURNOVER ON DOWNS!"
        
        # Apply stamina drain
        self.apply_stamina_drain(3)
        
        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="run",
            players_involved=[player.name],
            yards_gained=yards_gained,
            result=result.value,
            description=description
        )
    
    def simulate_lateral_chain(self) -> Play:
        """Simulate a multi-player lateral sequence"""
        team = self.get_offensive_team()
        
        # Determine chain length (2-5 players)
        chain_length = random.randint(2, 5)
        players_involved = random.sample(team.players[:8], min(chain_length, 8))
        
        # Calculate fumble probability (increases with chain length)
        base_fumble_prob = 0.05
        fumble_prob = base_fumble_prob * (1 + (chain_length - 2) * 0.15)
        fumble_prob /= (team.lateral_proficiency / 85)  # Adjust for team skill
        
        # Check for broken chain (fumble)
        if random.random() < fumble_prob:
            # Fumble occurred
            yards_gained = random.randint(-5, 8)
            self.change_possession()
            self.state.field_position = max(1, self.state.field_position - yards_gained)
            
            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1,
                yards_to_go=20,
                play_type="lateral_chain",
                players_involved=[p.name for p in players_involved],
                yards_gained=yards_gained,
                result=PlayResult.FUMBLE.value,
                description=f"Lateral chain with {chain_length} players - FUMBLE! Recovered by defense",
                laterals=chain_length,
                fumble=True
            )
        
        # Successful lateral chain
        base_yards = random.gauss(7, 4)
        lateral_bonus = chain_length * 1.5
        fatigue_factor = self.get_fatigue_factor()
        viper_factor = self.calculate_viper_impact()
        
        yards_gained = int((base_yards + lateral_bonus) * fatigue_factor * viper_factor)
        yards_gained = max(-3, min(yards_gained, 35))
        
        new_position = min(100, self.state.field_position + yards_gained)
        
        # Check for touchdown
        if new_position >= 100:
            result = PlayResult.TOUCHDOWN
            self.add_score(6)
            description = f"Lateral chain with {chain_length} players for {yards_gained} yards - TOUCHDOWN!"
        elif yards_gained >= self.state.yards_to_go:
            result = PlayResult.FIRST_DOWN
            self.state.field_position = new_position
            self.state.down = 1
            self.state.yards_to_go = 20
            description = f"Lateral chain with {chain_length} players for {yards_gained} yards - FIRST DOWN!"
        else:
            result = PlayResult.GAIN
            self.state.field_position = new_position
            self.state.down += 1
            self.state.yards_to_go -= yards_gained
            description = f"Lateral chain with {chain_length} players for {yards_gained} yards"
            
            if self.state.down > 5:
                result = PlayResult.TURNOVER_ON_DOWNS
                self.change_possession()
                description += " - TURNOVER ON DOWNS!"
        
        # Apply stamina drain (more for lateral chains)
        self.apply_stamina_drain(5)
        
        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="lateral_chain",
            players_involved=[p.name for p in players_involved],
            yards_gained=yards_gained,
            result=result.value,
            description=description,
            laterals=chain_length
        )
    
    def simulate_punt(self) -> Play:
        """Simulate a live-ball punt"""
        team = self.get_offensive_team()
        
        # Select punter
        punter = max(team.players[:8], key=lambda p: p.kicking)
        
        # Calculate punt distance
        base_distance = random.gauss(45, 10)
        kicking_factor = punter.kicking / 80
        distance = int(base_distance * kicking_factor)
        distance = max(20, min(distance, 70))
        
        # Punt changes field position and possession
        new_position = 100 - min(99, self.state.field_position + distance)
        
        self.change_possession()
        self.state.field_position = new_position
        self.state.down = 1
        self.state.yards_to_go = 20
        
        self.apply_stamina_drain(2)
        
        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="punt",
            players_involved=[punter.name],
            yards_gained=-distance,
            result="punt",
            description=f"{punter.name} punts {distance} yards"
        )
    
    def simulate_drop_kick(self) -> Play:
        """Simulate a drop-kick attempt (5 points)"""
        team = self.get_offensive_team()
        
        # Select kicker
        kicker = max(team.players[:8], key=lambda p: p.kicking)
        
        # Calculate distance to goal
        distance = 100 - self.state.field_position + 10  # Add 10 for end zone depth
        
        # Success probability based on distance and kicker skill
        base_prob = 0.6
        distance_factor = max(0, 1 - (distance - 30) / 70)
        skill_factor = kicker.kicking / 90
        success_prob = base_prob * distance_factor * skill_factor
        
        if random.random() < success_prob:
            # Successful drop kick
            self.add_score(5)
            self.kickoff(self.state.possession)  # Kicking team kicks off
            
            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1,
                yards_to_go=20,
                play_type="drop_kick",
                players_involved=[kicker.name],
                yards_gained=0,
                result=PlayResult.SUCCESSFUL_KICK.value,
                description=f"{kicker.name} DROP KICK is GOOD from {distance} yards! +5 points"
            )
        else:
            # Missed drop kick
            self.change_possession()
            self.state.field_position = 100 - self.state.field_position
            self.state.down = 1
            self.state.yards_to_go = 20
            
            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1,
                yards_to_go=20,
                play_type="drop_kick",
                players_involved=[kicker.name],
                yards_gained=0,
                result=PlayResult.MISSED_KICK.value,
                description=f"{kicker.name} DROP KICK is NO GOOD from {distance} yards"
            )
    
    def simulate_place_kick(self) -> Play:
        """Simulate a place kick attempt (3 points)"""
        team = self.get_offensive_team()
        
        # Select kicker
        kicker = max(team.players[:8], key=lambda p: p.kicking)
        
        # Calculate distance
        distance = 100 - self.state.field_position + 10
        
        # Success probability (easier than drop kick)
        base_prob = 0.75
        distance_factor = max(0, 1 - (distance - 35) / 60)
        skill_factor = kicker.kicking / 85
        success_prob = base_prob * distance_factor * skill_factor
        
        if random.random() < success_prob:
            self.add_score(3)
            self.kickoff(self.state.possession)
            
            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1,
                yards_to_go=20,
                play_type="place_kick",
                players_involved=[kicker.name],
                yards_gained=0,
                result=PlayResult.SUCCESSFUL_KICK.value,
                description=f"{kicker.name} PLACE KICK is GOOD from {distance} yards! +3 points"
            )
        else:
            self.change_possession()
            self.state.field_position = 100 - self.state.field_position
            self.state.down = 1
            self.state.yards_to_go = 20
            
            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1,
                yards_to_go=20,
                play_type="place_kick",
                players_involved=[kicker.name],
                yards_gained=0,
                result=PlayResult.MISSED_KICK.value,
                description=f"{kicker.name} PLACE KICK is NO GOOD from {distance} yards"
            )
    
    def get_offensive_team(self) -> Team:
        """Get the team currently on offense"""
        return self.home_team if self.state.possession == "home" else self.away_team
    
    def add_score(self, points: int):
        """Add points to the team with possession"""
        if self.state.possession == "home":
            self.state.home_score += points
        else:
            self.state.away_score += points
    
    def change_possession(self):
        """Switch possession to the other team"""
        self.state.possession = "away" if self.state.possession == "home" else "home"
    
    def get_fatigue_factor(self) -> float:
        """Calculate fatigue impact on performance"""
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
        # Fatigue starts to impact significantly below 70
        if stamina >= 70:
            return 1.0
        else:
            return 0.7 + (stamina / 70) * 0.3
    
    def apply_stamina_drain(self, amount: float):
        """Drain stamina from the offensive team"""
        if self.state.possession == "home":
            self.state.home_stamina = max(40, self.state.home_stamina - amount)
        else:
            self.state.away_stamina = max(40, self.state.away_stamina - amount)
    
    def calculate_viper_impact(self) -> float:
        """Calculate the Viper positioning impact on play success"""
        # Viper position changes dynamically (simplified model)
        positions = ["free", "left", "right", "deep"]
        self.viper_position = random.choice(positions)
        
        # Impact factor based on position (1.0 to 1.3)
        impacts = {
            "free": 1.15,
            "left": 1.1,
            "right": 1.1,
            "deep": 1.05
        }
        return impacts.get(self.viper_position, 1.0)
    
    def generate_game_summary(self) -> Dict:
        """Generate final game summary with stats"""
        # Calculate advanced stats
        home_plays = [p for p in self.play_log if p.possession == "home"]
        away_plays = [p for p in self.play_log if p.possession == "away"]
        
        home_stats = self.calculate_team_stats(home_plays)
        away_stats = self.calculate_team_stats(away_plays)
        
        return {
            "final_score": {
                "home": {
                    "team": self.home_team.name,
                    "score": self.state.home_score
                },
                "away": {
                    "team": self.away_team.name,
                    "score": self.state.away_score
                }
            },
            "stats": {
                "home": home_stats,
                "away": away_stats
            },
            "play_by_play": [self.play_to_dict(p) for p in self.play_log]
        }
    
    def calculate_team_stats(self, plays: List[Play]) -> Dict:
        """Calculate statistics for a team"""
        total_yards = sum(p.yards_gained for p in plays if p.yards_gained > 0)
        total_plays = len(plays)
        
        laterals = [p for p in plays if p.laterals > 0]
        total_laterals = sum(p.laterals for p in laterals)
        successful_laterals = sum(1 for p in laterals if not p.fumble)
        
        drop_kicks = [p for p in plays if p.play_type == "drop_kick" and p.result == "successful_kick"]
        place_kicks = [p for p in plays if p.play_type == "place_kick" and p.result == "successful_kick"]
        
        # Advanced metrics
        viper_efficiency = (total_yards / max(1, total_plays)) * (1 + successful_laterals / max(1, total_laterals))
        micro_scoring_diff = len(drop_kicks) * 5 - len(place_kicks) * 3
        lateral_efficiency = (successful_laterals / max(1, len(laterals))) * 100 if laterals else 0
        
        return {
            "total_yards": total_yards,
            "total_plays": total_plays,
            "yards_per_play": round(total_yards / max(1, total_plays), 2),
            "lateral_chains": len(laterals),
            "successful_laterals": successful_laterals,
            "drop_kicks_made": len(drop_kicks),
            "place_kicks_made": len(place_kicks),
            "viper_efficiency": round(viper_efficiency, 2),
            "micro_scoring_differential": micro_scoring_diff,
            "lateral_efficiency": round(lateral_efficiency, 1)
        }
    
    def play_to_dict(self, play: Play) -> Dict:
        """Convert Play object to dictionary"""
        return {
            "play_number": play.play_number,
            "quarter": play.quarter,
            "time_remaining": play.time,
            "possession": play.possession,
            "field_position": play.field_position,
            "down": play.down,
            "yards_to_go": play.yards_to_go,
            "play_type": play.play_type,
            "players": play.players_involved,
            "yards": play.yards_gained,
            "result": play.result,
            "description": play.description,
            "laterals": play.laterals if play.laterals > 0 else None,
            "fumble": play.fumble if play.fumble else None
        }


def load_team_from_json(filepath: str) -> Team:
    """Load team data from JSON file"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    players = []
    for p_data in data['roster']['players'][:10]:  # Use top 10 players
        players.append(Player(
            number=p_data['number'],
            name=p_data['name'],
            position=p_data['position'],
            speed=p_data['stats']['speed'],
            stamina=p_data['stats']['stamina'],
            kicking=p_data['stats']['kicking'],
            lateral_skill=p_data['stats']['lateral_skill'],
            tackling=p_data['stats']['tackling']
        ))
    
    return Team(
        name=data['team_info']['school'],
        abbreviation=data['team_info']['abbreviation'],
        mascot=data['team_info']['mascot'],
        players=players,
        avg_speed=data['team_stats']['avg_speed'],
        avg_stamina=data['team_stats']['avg_stamina'],
        kicking_strength=data['team_stats']['kicking_strength'],
        lateral_proficiency=data['team_stats']['lateral_proficiency'],
        defensive_strength=data['team_stats']['defensive_strength']
    )
