"""
Collegiate Viperball Simulation Engine
Core game simulation logic for CVL games
"""

import random
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy



class PlayType(Enum):
    RUN = "run"
    LATERAL_CHAIN = "lateral_chain"
    PUNT = "punt"
    DROP_KICK = "drop_kick"
    PLACE_KICK = "place_kick"


class PlayFamily(Enum):
    DIVE_OPTION = "dive_option"
    SPEED_OPTION = "speed_option"
    SWEEP_OPTION = "sweep_option"
    LATERAL_SPREAD = "lateral_spread"
    TERRITORY_KICK = "territory_kick"


class PlayResult(Enum):
    GAIN = "gain"
    FIRST_DOWN = "first_down"
    TOUCHDOWN = "touchdown"
    FUMBLE = "fumble"
    TURNOVER_ON_DOWNS = "turnover_on_downs"
    SUCCESSFUL_KICK = "successful_kick"
    MISSED_KICK = "missed_kick"
    SAFETY = "safety"


PLAY_FAMILY_TO_TYPE = {
    PlayFamily.DIVE_OPTION: PlayType.RUN,
    PlayFamily.SPEED_OPTION: PlayType.RUN,
    PlayFamily.SWEEP_OPTION: PlayType.RUN,
    PlayFamily.LATERAL_SPREAD: PlayType.LATERAL_CHAIN,
    PlayFamily.TERRITORY_KICK: PlayType.PUNT,
}


@dataclass
class GameState:
    quarter: int = 1
    time_remaining: int = 900
    home_score: int = 0
    away_score: int = 0
    possession: str = "home"
    field_position: int = 20
    down: int = 1
    yards_to_go: int = 20
    play_number: int = 0
    home_stamina: float = 100.0
    away_stamina: float = 100.0


@dataclass
class Player:
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
    name: str
    abbreviation: str
    mascot: str
    players: List[Player]
    avg_speed: int
    avg_stamina: int
    kicking_strength: int
    lateral_proficiency: int
    defensive_strength: int
    offense_style: str = "balanced"


@dataclass
class Play:
    play_number: int
    quarter: int
    time: int
    possession: str
    field_position: int
    down: int
    yards_to_go: int
    play_type: str
    play_family: str
    players_involved: List[str]
    yards_gained: int
    result: str
    description: str
    fatigue: float = 100.0
    laterals: int = 0
    fumble: bool = False


OFFENSE_STYLES = {
    "power_option": {
        "label": "Power Option",
        "description": "Heavy run game with option reads",
        "weights": {
            "dive_option": 0.35,
            "speed_option": 0.15,
            "sweep_option": 0.20,
            "lateral_spread": 0.10,
            "territory_kick": 0.20,
        },
        "tempo": 0.5,
        "lateral_risk": 0.3,
        "kick_rate": 0.20,
        "option_rate": 0.55,
    },
    "lateral_spread": {
        "label": "Lateral Spread",
        "description": "High lateral chain usage, spread the field",
        "weights": {
            "dive_option": 0.10,
            "speed_option": 0.15,
            "sweep_option": 0.15,
            "lateral_spread": 0.45,
            "territory_kick": 0.15,
        },
        "tempo": 0.7,
        "lateral_risk": 0.6,
        "kick_rate": 0.15,
        "option_rate": 0.25,
    },
    "territorial": {
        "label": "Territorial",
        "description": "Field position game, frequent kicks and punts",
        "weights": {
            "dive_option": 0.15,
            "speed_option": 0.10,
            "sweep_option": 0.10,
            "lateral_spread": 0.10,
            "territory_kick": 0.55,
        },
        "tempo": 0.3,
        "lateral_risk": 0.2,
        "kick_rate": 0.55,
        "option_rate": 0.25,
    },
    "option_spread": {
        "label": "Option Spread",
        "description": "Speed-based option reads with lateral chains",
        "weights": {
            "dive_option": 0.15,
            "speed_option": 0.30,
            "sweep_option": 0.20,
            "lateral_spread": 0.25,
            "territory_kick": 0.10,
        },
        "tempo": 0.8,
        "lateral_risk": 0.5,
        "kick_rate": 0.10,
        "option_rate": 0.50,
    },
    "balanced": {
        "label": "Balanced",
        "description": "No strong tendency, adapts to situation",
        "weights": {
            "dive_option": 0.20,
            "speed_option": 0.20,
            "sweep_option": 0.20,
            "lateral_spread": 0.20,
            "territory_kick": 0.20,
        },
        "tempo": 0.5,
        "lateral_risk": 0.4,
        "kick_rate": 0.20,
        "option_rate": 0.40,
    },
}


class ViperballEngine:

    def __init__(self, home_team: Team, away_team: Team, seed: Optional[int] = None,
                 style_overrides: Optional[Dict[str, str]] = None):
        self.home_team = deepcopy(home_team)
        self.away_team = deepcopy(away_team)
        self.state = GameState()
        self.play_log: List[Play] = []
        self.viper_position = "free"
        self.seed = seed

        if seed is not None:
            random.seed(seed)

        if style_overrides:
            for team_key, style in style_overrides.items():
                if style in OFFENSE_STYLES:
                    if team_key.lower() in [self.home_team.name.lower(), self.home_team.abbreviation.lower()]:
                        self.home_team.offense_style = style
                    elif team_key.lower() in [self.away_team.name.lower(), self.away_team.abbreviation.lower()]:
                        self.away_team.offense_style = style
                    else:
                        for t in [self.home_team, self.away_team]:
                            clean_key = team_key.lower().replace(" ", "_").replace("-", "_")
                            clean_name = t.name.lower().replace(" ", "_").replace("-", "_")
                            if clean_key in clean_name or clean_name in clean_key:
                                t.offense_style = style
                                break

        self.home_style = OFFENSE_STYLES.get(self.home_team.offense_style, OFFENSE_STYLES["balanced"])
        self.away_style = OFFENSE_STYLES.get(self.away_team.offense_style, OFFENSE_STYLES["balanced"])

    def simulate_game(self) -> Dict:
        self.kickoff("away")

        for quarter in range(1, 5):
            self.state.quarter = quarter
            self.state.time_remaining = 900

            while self.state.time_remaining > 0:
                self.simulate_drive()
                if self.state.time_remaining <= 0:
                    break

        return self.generate_game_summary()

    def kickoff(self, receiving_team: str):
        self.state.possession = receiving_team
        self.state.field_position = 20
        self.state.down = 1
        self.state.yards_to_go = 20

    def simulate_drive(self):
        style = self._current_style()
        tempo = style["tempo"]
        max_plays = int(15 + tempo * 15)
        plays_in_drive = 0

        while plays_in_drive < max_plays and self.state.time_remaining > 0:
            play = self.simulate_play()
            self.play_log.append(play)

            base_time = random.randint(15, 45)
            time_elapsed = int(base_time * (1.2 - tempo * 0.4))
            self.state.time_remaining = max(0, self.state.time_remaining - time_elapsed)

            if play.result in ["touchdown", "turnover_on_downs", "fumble", "successful_kick"]:
                if play.result == "touchdown":
                    scoring_team = self.state.possession
                    receiving = "away" if scoring_team == "home" else "home"
                    self.kickoff(receiving)
                elif play.result == "successful_kick":
                    kicking_team = self.state.possession
                    receiving = "away" if kicking_team == "home" else "home"
                    self.kickoff(receiving)
                break

            plays_in_drive += 1

    def simulate_play(self) -> Play:
        self.state.play_number += 1
        play_family = self.select_play_family()
        play_type = PLAY_FAMILY_TO_TYPE.get(play_family, PlayType.RUN)

        if self.state.down == 5:
            if self.state.field_position >= 55:
                if random.random() < 0.5:
                    play_type = PlayType.DROP_KICK
                    play_family = PlayFamily.TERRITORY_KICK
                else:
                    play_type = PlayType.PLACE_KICK
                    play_family = PlayFamily.TERRITORY_KICK
            else:
                style = self._current_style()
                if random.random() < style["kick_rate"]:
                    play_type = PlayType.PUNT
                    play_family = PlayFamily.TERRITORY_KICK
                else:
                    play_family = random.choice([PlayFamily.DIVE_OPTION, PlayFamily.SPEED_OPTION, PlayFamily.LATERAL_SPREAD])
                    play_type = PLAY_FAMILY_TO_TYPE[play_family]

        if play_type == PlayType.RUN:
            return self.simulate_run(play_family)
        elif play_type == PlayType.LATERAL_CHAIN:
            return self.simulate_lateral_chain(play_family)
        elif play_type == PlayType.PUNT:
            return self.simulate_punt(play_family)
        elif play_type == PlayType.DROP_KICK:
            return self.simulate_drop_kick(play_family)
        elif play_type == PlayType.PLACE_KICK:
            return self.simulate_place_kick(play_family)
        else:
            return self.simulate_run(play_family)

    def select_play_family(self) -> PlayFamily:
        style = self._current_style()
        weights = style["weights"]
        families = list(PlayFamily)
        w = [weights.get(f.value, 0.2) for f in families]
        return random.choices(families, weights=w)[0]

    def _current_style(self) -> Dict:
        if self.state.possession == "home":
            return self.home_style
        return self.away_style

    def simulate_run(self, family: PlayFamily = PlayFamily.DIVE_OPTION) -> Play:
        team = self.get_offensive_team()
        player = random.choice(team.players[:5])

        if family == PlayFamily.DIVE_OPTION:
            base_yards = random.gauss(4, 2.5)
            desc_prefix = "Dive option"
        elif family == PlayFamily.SPEED_OPTION:
            base_yards = random.gauss(5, 4)
            desc_prefix = "Speed option"
        elif family == PlayFamily.SWEEP_OPTION:
            base_yards = random.gauss(3.5, 5)
            desc_prefix = "Sweep option"
        else:
            base_yards = random.gauss(4, 3)
            desc_prefix = "Run"

        strength_factor = team.avg_speed / 90
        fatigue_factor = self.get_fatigue_factor()
        viper_factor = self.calculate_viper_impact()

        yards_gained = int(base_yards * strength_factor * fatigue_factor * viper_factor)
        yards_gained = max(-5, min(yards_gained, 25))

        new_position = min(100, self.state.field_position + yards_gained)

        if new_position >= 100:
            result = PlayResult.TOUCHDOWN
            self.add_score(9)
            description = f"{desc_prefix}: {player.name} rushes for {yards_gained} yards - TOUCHDOWN!"
        elif yards_gained >= self.state.yards_to_go:
            result = PlayResult.FIRST_DOWN
            self.state.field_position = new_position
            self.state.down = 1
            self.state.yards_to_go = 20
            description = f"{desc_prefix}: {player.name} rushes for {yards_gained} yards - FIRST DOWN!"
        else:
            result = PlayResult.GAIN
            self.state.field_position = new_position
            self.state.down += 1
            self.state.yards_to_go -= yards_gained
            description = f"{desc_prefix}: {player.name} rushes for {yards_gained} yards"

            if self.state.down > 5:
                result = PlayResult.TURNOVER_ON_DOWNS
                self.change_possession()
                self.state.field_position = 100 - self.state.field_position
                description += " - TURNOVER ON DOWNS!"

        self.apply_stamina_drain(3)
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="run",
            play_family=family.value,
            players_involved=[player.name],
            yards_gained=yards_gained,
            result=result.value,
            description=description,
            fatigue=round(stamina, 1),
        )

    def simulate_lateral_chain(self, family: PlayFamily = PlayFamily.LATERAL_SPREAD) -> Play:
        team = self.get_offensive_team()
        style = self._current_style()

        chain_length = random.randint(2, 5)
        players_involved = random.sample(team.players[:8], min(chain_length, len(team.players[:8])))

        base_fumble_prob = 0.05
        fumble_prob = base_fumble_prob * (1 + (chain_length - 2) * 0.15)
        fumble_prob *= (1 + style["lateral_risk"] * 0.3)
        fumble_prob /= (team.lateral_proficiency / 85)

        if random.random() < fumble_prob:
            yards_gained = random.randint(-5, 8)
            old_pos = self.state.field_position
            self.change_possession()
            self.state.field_position = max(1, 100 - old_pos)
            self.state.down = 1
            self.state.yards_to_go = 20

            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1,
                yards_to_go=20,
                play_type="lateral_chain",
                play_family=family.value,
                players_involved=[p.name for p in players_involved],
                yards_gained=yards_gained,
                result=PlayResult.FUMBLE.value,
                description=f"Lateral chain with {chain_length} players - FUMBLE! Recovered by defense",
                fatigue=round(stamina, 1),
                laterals=chain_length,
                fumble=True,
            )

        base_yards = random.gauss(7, 4)
        lateral_bonus = chain_length * 1.5
        fatigue_factor = self.get_fatigue_factor()
        viper_factor = self.calculate_viper_impact()

        yards_gained = int((base_yards + lateral_bonus) * fatigue_factor * viper_factor)
        yards_gained = max(-3, min(yards_gained, 35))

        new_position = min(100, self.state.field_position + yards_gained)

        if new_position >= 100:
            result = PlayResult.TOUCHDOWN
            self.add_score(9)
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
                self.state.field_position = 100 - self.state.field_position
                description += " - TURNOVER ON DOWNS!"

        self.apply_stamina_drain(5)
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="lateral_chain",
            play_family=family.value,
            players_involved=[p.name for p in players_involved],
            yards_gained=yards_gained,
            result=result.value,
            description=description,
            fatigue=round(stamina, 1),
            laterals=chain_length,
        )

    def simulate_punt(self, family: PlayFamily = PlayFamily.TERRITORY_KICK) -> Play:
        team = self.get_offensive_team()
        punter = max(team.players[:8], key=lambda p: p.kicking)

        base_distance = random.gauss(45, 10)
        kicking_factor = punter.kicking / 80
        distance = int(base_distance * kicking_factor)
        distance = max(20, min(distance, 70))

        new_position = 100 - min(99, self.state.field_position + distance)

        self.change_possession()
        self.state.field_position = max(1, new_position)
        self.state.down = 1
        self.state.yards_to_go = 20

        self.apply_stamina_drain(2)
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        return Play(
            play_number=self.state.play_number,
            quarter=self.state.quarter,
            time=self.state.time_remaining,
            possession=self.state.possession,
            field_position=self.state.field_position,
            down=self.state.down,
            yards_to_go=self.state.yards_to_go,
            play_type="punt",
            play_family=family.value,
            players_involved=[punter.name],
            yards_gained=-distance,
            result="punt",
            description=f"{punter.name} punts {distance} yards",
            fatigue=round(stamina, 1),
        )

    def simulate_drop_kick(self, family: PlayFamily = PlayFamily.TERRITORY_KICK) -> Play:
        team = self.get_offensive_team()
        kicker = max(team.players[:8], key=lambda p: p.kicking)

        distance = 100 - self.state.field_position + 10

        base_prob = 0.6
        distance_factor = max(0, 1 - (distance - 30) / 70)
        skill_factor = kicker.kicking / 90
        success_prob = base_prob * distance_factor * skill_factor

        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        if random.random() < success_prob:
            self.add_score(5)

            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1,
                yards_to_go=20,
                play_type="drop_kick",
                play_family=family.value,
                players_involved=[kicker.name],
                yards_gained=0,
                result=PlayResult.SUCCESSFUL_KICK.value,
                description=f"{kicker.name} DROP KICK is GOOD from {distance} yards! +5 points",
                fatigue=round(stamina, 1),
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
                play_type="drop_kick",
                play_family=family.value,
                players_involved=[kicker.name],
                yards_gained=0,
                result=PlayResult.MISSED_KICK.value,
                description=f"{kicker.name} DROP KICK is NO GOOD from {distance} yards",
                fatigue=round(stamina, 1),
            )

    def simulate_place_kick(self, family: PlayFamily = PlayFamily.TERRITORY_KICK) -> Play:
        team = self.get_offensive_team()
        kicker = max(team.players[:8], key=lambda p: p.kicking)

        distance = 100 - self.state.field_position + 10

        base_prob = 0.75
        distance_factor = max(0, 1 - (distance - 35) / 60)
        skill_factor = kicker.kicking / 85
        success_prob = base_prob * distance_factor * skill_factor

        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina

        if random.random() < success_prob:
            self.add_score(3)

            return Play(
                play_number=self.state.play_number,
                quarter=self.state.quarter,
                time=self.state.time_remaining,
                possession=self.state.possession,
                field_position=self.state.field_position,
                down=1,
                yards_to_go=20,
                play_type="place_kick",
                play_family=family.value,
                players_involved=[kicker.name],
                yards_gained=0,
                result=PlayResult.SUCCESSFUL_KICK.value,
                description=f"{kicker.name} PLACE KICK is GOOD from {distance} yards! +3 points",
                fatigue=round(stamina, 1),
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
                play_family=family.value,
                players_involved=[kicker.name],
                yards_gained=0,
                result=PlayResult.MISSED_KICK.value,
                description=f"{kicker.name} PLACE KICK is NO GOOD from {distance} yards",
                fatigue=round(stamina, 1),
            )

    def simulate_single_play(self, style: str = "balanced", field_position: int = 40,
                              down: int = 1, yards_to_go: int = 20) -> Dict:
        self.state.field_position = field_position
        self.state.down = down
        self.state.yards_to_go = yards_to_go
        self.state.possession = "home"

        old_style = self.home_team.offense_style
        self.home_team.offense_style = style
        self.home_style = OFFENSE_STYLES.get(style, OFFENSE_STYLES["balanced"])

        play = self.simulate_play()

        self.home_team.offense_style = old_style
        self.home_style = OFFENSE_STYLES.get(old_style, OFFENSE_STYLES["balanced"])

        return self.play_to_dict(play)

    def get_offensive_team(self) -> Team:
        return self.home_team if self.state.possession == "home" else self.away_team

    def add_score(self, points: int):
        if self.state.possession == "home":
            self.state.home_score += points
        else:
            self.state.away_score += points

    def change_possession(self):
        self.state.possession = "away" if self.state.possession == "home" else "home"

    def get_fatigue_factor(self) -> float:
        stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
        if stamina >= 70:
            return 1.0
        else:
            return 0.7 + (stamina / 70) * 0.3

    def apply_stamina_drain(self, amount: float):
        if self.state.possession == "home":
            self.state.home_stamina = max(40, self.state.home_stamina - amount)
        else:
            self.state.away_stamina = max(40, self.state.away_stamina - amount)

    def calculate_viper_impact(self) -> float:
        positions = ["free", "left", "right", "deep"]
        self.viper_position = random.choice(positions)
        impacts = {
            "free": 0.85,
            "left": 0.95,
            "right": 1.05,
            "deep": 1.10,
        }
        return impacts.get(self.viper_position, 1.0)

    def generate_game_summary(self) -> Dict:
        home_plays = [p for p in self.play_log if p.possession == "home"]
        away_plays = [p for p in self.play_log if p.possession == "away"]

        home_stats = self.calculate_team_stats(home_plays)
        away_stats = self.calculate_team_stats(away_plays)

        for stats, plays in [(home_stats, home_plays), (away_stats, away_plays)]:
            plays_by_q = {q: 0 for q in range(1, 5)}
            for p in plays:
                if p.quarter in plays_by_q:
                    plays_by_q[p.quarter] += 1
            stats["plays_per_quarter"] = plays_by_q

        summary = {
            "final_score": {
                "home": {
                    "team": self.home_team.name,
                    "score": self.state.home_score,
                },
                "away": {
                    "team": self.away_team.name,
                    "score": self.state.away_score,
                },
            },
            "home_style": self.home_team.offense_style,
            "away_style": self.away_team.offense_style,
            "seed": self.seed,
            "stats": {
                "home": home_stats,
                "away": away_stats,
            },
            "play_by_play": [self.play_to_dict(p) for p in self.play_log],
        }

        return summary

    def calculate_team_stats(self, plays: List[Play]) -> Dict:
        total_yards = sum(p.yards_gained for p in plays if p.yards_gained > 0)
        total_plays = len(plays)

        laterals = [p for p in plays if p.laterals > 0]
        total_laterals = sum(p.laterals for p in laterals)
        successful_laterals = sum(1 for p in laterals if not p.fumble)

        drop_kicks = [p for p in plays if p.play_type == "drop_kick" and p.result == "successful_kick"]
        place_kicks = [p for p in plays if p.play_type == "place_kick" and p.result == "successful_kick"]
        touchdowns = [p for p in plays if p.result == "touchdown"]
        fumbles_lost = [p for p in plays if p.fumble]
        turnovers_on_downs = [p for p in plays if p.result == "turnover_on_downs"]

        play_family_counts = {}
        for p in plays:
            fam = p.play_family
            play_family_counts[fam] = play_family_counts.get(fam, 0) + 1

        viper_efficiency = (total_yards / max(1, total_plays)) * (1 + successful_laterals / max(1, total_laterals))
        lateral_efficiency = (successful_laterals / max(1, len(laterals))) * 100 if laterals else 0

        fatigue_values = [p.fatigue for p in plays if p.fatigue is not None]
        avg_fatigue = round(sum(fatigue_values) / max(1, len(fatigue_values)), 1) if fatigue_values else 100.0

        return {
            "total_yards": total_yards,
            "total_plays": total_plays,
            "yards_per_play": round(total_yards / max(1, total_plays), 2),
            "touchdowns": len(touchdowns),
            "lateral_chains": len(laterals),
            "successful_laterals": successful_laterals,
            "fumbles_lost": len(fumbles_lost),
            "turnovers_on_downs": len(turnovers_on_downs),
            "drop_kicks_made": len(drop_kicks),
            "place_kicks_made": len(place_kicks),
            "viper_efficiency": round(viper_efficiency, 2),
            "lateral_efficiency": round(lateral_efficiency, 1),
            "play_family_breakdown": play_family_counts,
            "avg_fatigue": avg_fatigue,
        }

    def play_to_dict(self, play: Play) -> Dict:
        return {
            "play_number": play.play_number,
            "quarter": play.quarter,
            "time_remaining": play.time,
            "possession": play.possession,
            "field_position": play.field_position,
            "down": play.down,
            "yards_to_go": play.yards_to_go,
            "play_type": play.play_type,
            "play_family": play.play_family,
            "players": play.players_involved,
            "yards": play.yards_gained,
            "result": play.result,
            "description": play.description,
            "fatigue": play.fatigue,
            "laterals": play.laterals if play.laterals > 0 else None,
            "fumble": play.fumble if play.fumble else None,
        }


def load_team_from_json(filepath: str) -> Team:
    with open(filepath, "r") as f:
        data = json.load(f)

    players = []
    for p_data in data["roster"]["players"][:10]:
        players.append(
            Player(
                number=p_data["number"],
                name=p_data["name"],
                position=p_data["position"],
                speed=p_data["stats"]["speed"],
                stamina=p_data["stats"]["stamina"],
                kicking=p_data["stats"]["kicking"],
                lateral_skill=p_data["stats"]["lateral_skill"],
                tackling=p_data["stats"]["tackling"],
            )
        )

    style = data.get("style", {}).get("offense_style", "balanced")

    team_name = data["team_info"].get("school") or data["team_info"].get("school_name", "Unknown")

    return Team(
        name=team_name,
        abbreviation=data["team_info"]["abbreviation"],
        mascot=data["team_info"]["mascot"],
        players=players,
        avg_speed=data["team_stats"]["avg_speed"],
        avg_stamina=data["team_stats"]["avg_stamina"],
        kicking_strength=data["team_stats"]["kicking_strength"],
        lateral_proficiency=data["team_stats"]["lateral_proficiency"],
        defensive_strength=data["team_stats"]["defensive_strength"],
        offense_style=style,
    )


def get_available_teams() -> List[Dict]:
    import os
    teams_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "teams")
    teams = []
    for f in sorted(os.listdir(teams_dir)):
        if f.endswith(".json"):
            filepath = os.path.join(teams_dir, f)
            with open(filepath) as fh:
                data = json.load(fh)
            style = data.get("style", {}).get("offense_style", "balanced")
            team_name = data["team_info"].get("school") or data["team_info"].get("school_name", "Unknown")
            teams.append({
                "key": f.replace(".json", ""),
                "name": team_name,
                "abbreviation": data["team_info"]["abbreviation"],
                "mascot": data["team_info"]["mascot"],
                "default_style": style,
                "file": filepath,
            })
    return teams


def get_available_styles() -> Dict:
    return {k: {"label": v["label"], "description": v["description"]} for k, v in OFFENSE_STYLES.items()}
