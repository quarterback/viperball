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
    PINDOWN = "pindown"
    PUNT_RETURN_TD = "punt_return_td"
    CHAOS_RECOVERY = "chaos_recovery"


PLAY_FAMILY_TO_TYPE = {
    PlayFamily.DIVE_OPTION: PlayType.RUN,
    PlayFamily.SPEED_OPTION: PlayType.RUN,
    PlayFamily.SWEEP_OPTION: PlayType.RUN,
    PlayFamily.LATERAL_SPREAD: PlayType.LATERAL_CHAIN,
    PlayFamily.TERRITORY_KICK: PlayType.PUNT,
}

POSITION_TAGS = {
    "Lineman": "LM",
    "Zeroback/Back": "ZB",
    "Halfback/Back": "HB",
    "Wingback/End": "WB",
    "Wing/End": "WB",
    "Shiftback/Back": "SB",
    "Viper/Back": "VP",
    "Back/Safety": "LB",
    "Back/Corner": "CB",
    "Wedge/Line": "LA",
    "Viper": "VP",
    "Back": "BK",
    "Wing": "WB",
    "Wedge": "LA",
    "Safety": "KP",
    "End": "ED",
    "Line": "LA",
    "Corner": "CB",
}


def player_tag(player) -> str:
    pos = player.position
    tag = POSITION_TAGS.get(pos, pos[:2].upper())
    return f"{tag}{player.number}"


def player_label(player) -> str:
    tag = player_tag(player)
    return f"{tag} {player.name}"


@dataclass
class GameState:
    quarter: int = 1
    time_remaining: int = 900
    home_score: float = 0.0
    away_score: float = 0.0
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
            "dive_option": 0.25,
            "speed_option": 0.12,
            "sweep_option": 0.18,
            "lateral_spread": 0.10,
            "territory_kick": 0.35,
        },
        "tempo": 0.5,
        "lateral_risk": 0.8,
        "kick_rate": 0.35,
        "option_rate": 0.55,
        "run_bonus": 0.10,
        "fatigue_resistance": 0.05,
        "kick_accuracy_bonus": 0.0,
        "explosive_lateral_bonus": 0.0,
        "option_read_bonus": 0.0,
        "broken_play_bonus": 0.0,
        "pindown_bonus": 0.0,
    },
    "lateral_spread": {
        "label": "Lateral Spread",
        "description": "High lateral chain usage, spread the field",
        "weights": {
            "dive_option": 0.08,
            "speed_option": 0.10,
            "sweep_option": 0.10,
            "lateral_spread": 0.40,
            "territory_kick": 0.32,
        },
        "tempo": 0.7,
        "lateral_risk": 1.4,
        "kick_rate": 0.32,
        "option_rate": 0.25,
        "run_bonus": 0.0,
        "fatigue_resistance": 0.0,
        "kick_accuracy_bonus": 0.0,
        "explosive_lateral_bonus": 0.20,
        "option_read_bonus": 0.0,
        "broken_play_bonus": 0.0,
        "pindown_bonus": 0.0,
        "lateral_success_bonus": 0.10,
        "tired_def_yardage_bonus": 0.05,
    },
    "territorial": {
        "label": "Territorial",
        "description": "Field position game, frequent kicks and punts — AFL-style",
        "weights": {
            "dive_option": 0.10,
            "speed_option": 0.05,
            "sweep_option": 0.10,
            "lateral_spread": 0.10,
            "territory_kick": 0.65,
        },
        "tempo": 0.3,
        "lateral_risk": 0.8,
        "kick_rate": 0.55,
        "option_rate": 0.25,
        "run_bonus": 0.0,
        "fatigue_resistance": 0.0,
        "kick_accuracy_bonus": 0.10,
        "explosive_lateral_bonus": 0.0,
        "option_read_bonus": 0.0,
        "broken_play_bonus": 0.0,
        "pindown_bonus": 0.15,
    },
    "option_spread": {
        "label": "Option Spread",
        "description": "Speed-based option reads with lateral chains",
        "weights": {
            "dive_option": 0.12,
            "speed_option": 0.22,
            "sweep_option": 0.15,
            "lateral_spread": 0.22,
            "territory_kick": 0.29,
        },
        "tempo": 0.8,
        "lateral_risk": 1.25,
        "kick_rate": 0.29,
        "option_rate": 0.50,
        "run_bonus": 0.0,
        "fatigue_resistance": 0.0,
        "kick_accuracy_bonus": 0.0,
        "explosive_lateral_bonus": 0.0,
        "option_read_bonus": 0.15,
        "broken_play_bonus": 0.10,
        "pindown_bonus": 0.0,
        "tired_def_broken_play_bonus": 0.10,
    },
    "balanced": {
        "label": "Balanced",
        "description": "No strong tendency, adapts to situation",
        "weights": {
            "dive_option": 0.13,
            "speed_option": 0.13,
            "sweep_option": 0.13,
            "lateral_spread": 0.13,
            "territory_kick": 0.48,
        },
        "tempo": 0.5,
        "lateral_risk": 1.0,
        "kick_rate": 0.48,
        "option_rate": 0.40,
        "run_bonus": 0.05,
        "fatigue_resistance": 0.025,
        "kick_accuracy_bonus": 0.05,
        "explosive_lateral_bonus": 0.05,
        "option_read_bonus": 0.05,
        "broken_play_bonus": 0.05,
        "pindown_bonus": 0.05,
    },
}


class ViperballEngine:

    def __init__(self, home_team: Team, away_team: Team, seed: Optional[int] = None,
                 style_overrides: Optional[Dict[str, str]] = None):
        self.home_team = deepcopy(home_team)
        self.away_team = deepcopy(away_team)
        self.state = GameState()
        self.play_log: List[Play] = []
        self.drive_log: List[Dict] = []
        self.viper_position = "free"
        self.seed = seed
        self.drive_play_count = 0

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
        kick_distance = random.randint(40, 65)
        return_yards = random.randint(10, 30)
        start_position = max(10, min(40, return_yards))
        self.state.field_position = start_position
        self.state.down = 1
        self.state.yards_to_go = 20

    def simulate_drive(self):
        style = self._current_style()
        tempo = style["tempo"]
        max_plays = int(15 + tempo * 15)
        self.drive_play_count = 0

        drive_team = self.state.possession
        drive_start = self.state.field_position
        drive_quarter = self.state.quarter
        drive_plays = 0
        drive_yards = 0
        drive_result = "stall"

        while self.drive_play_count < max_plays and self.state.time_remaining > 0:
            self.drive_play_count += 1
            play = self.simulate_play()
            self.play_log.append(play)
            drive_plays += 1
            if play.yards_gained > 0 and play.play_type not in ["punt"]:
                drive_yards += play.yards_gained

            base_time = random.randint(15, 45)
            time_elapsed = int(base_time * (1.2 - tempo * 0.4))
            self.state.time_remaining = max(0, self.state.time_remaining - time_elapsed)

            if play.result in ["touchdown", "turnover_on_downs", "fumble", "successful_kick", "missed_kick", "punt", "pindown", "punt_return_td", "chaos_recovery", "safety"]:
                drive_result = play.result
                if play.result == "touchdown":
                    scoring_team = self.state.possession
                    receiving = "away" if scoring_team == "home" else "home"
                    self.kickoff(receiving)
                elif play.result == "successful_kick":
                    kicking_team = self.state.possession
                    receiving = "away" if kicking_team == "home" else "home"
                    self.kickoff(receiving)
                elif play.result == "punt_return_td":
                    scoring_team = self.state.possession
                    receiving = "away" if scoring_team == "home" else "home"
                    self.kickoff(receiving)
                elif play.result == "safety":
                    scored_team = "away" if drive_team == "home" else "home"
                    self.state.possession = drive_team
                    self.state.field_position = 20
                    self.state.down = 1
                    self.state.yards_to_go = 20
                break

        self.drive_log.append({
            "team": drive_team,
            "quarter": drive_quarter,
            "start_yard_line": drive_start,
            "plays": drive_plays,
            "yards": drive_yards,
            "result": drive_result,
        })

    def _resolve_kick_type(self) -> PlayType:
        fp = self.state.field_position
        down = self.state.down

        if down == 5:
            if fp >= 70:
                return random.choices(
                    [PlayType.PLACE_KICK, PlayType.DROP_KICK],
                    weights=[0.65, 0.35]
                )[0]
            elif fp >= 50:
                return random.choices(
                    [PlayType.DROP_KICK, PlayType.PLACE_KICK, PlayType.PUNT],
                    weights=[0.45, 0.25, 0.30]
                )[0]
            else:
                return random.choices(
                    [PlayType.PUNT, PlayType.DROP_KICK],
                    weights=[0.80, 0.20]
                )[0]

        if fp >= 65:
            return random.choices(
                [PlayType.DROP_KICK, PlayType.PLACE_KICK, PlayType.PUNT],
                weights=[0.45, 0.30, 0.25]
            )[0]
        elif fp >= 50:
            return random.choices(
                [PlayType.DROP_KICK, PlayType.PUNT],
                weights=[0.40, 0.60]
            )[0]
        elif fp >= 35:
            return random.choices(
                [PlayType.DROP_KICK, PlayType.PUNT],
                weights=[0.20, 0.80]
            )[0]
        else:
            return random.choices(
                [PlayType.PUNT, PlayType.DROP_KICK],
                weights=[0.90, 0.10]
            )[0]

    def simulate_play(self) -> Play:
        self.state.play_number += 1
        play_family = self.select_play_family()
        play_type = PLAY_FAMILY_TO_TYPE.get(play_family, PlayType.RUN)

        if play_type == PlayType.PUNT:
            play_type = self._resolve_kick_type()
            play_family = PlayFamily.TERRITORY_KICK

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
        weights = dict(style["weights"])

        if self.state.down >= 3 and self.state.yards_to_go >= 15:
            weights["territory_kick"] = weights.get("territory_kick", 0.3) + 0.12
        if self.state.down >= 4:
            weights["territory_kick"] = weights.get("territory_kick", 0.3) + 0.10
        if self.state.field_position <= 30:
            weights["territory_kick"] = weights.get("territory_kick", 0.3) + 0.08
        if self.state.field_position >= 55:
            weights["territory_kick"] = weights.get("territory_kick", 0.3) + 0.05

        families = list(PlayFamily)
        w = [weights.get(f.value, 0.2) for f in families]
        return random.choices(families, weights=w)[0]

    def _current_style(self) -> Dict:
        if self.state.possession == "home":
            return self.home_style
        return self.away_style

    def _defensive_fatigue_factor(self) -> float:
        if self.drive_play_count >= 12:
            return 1.25
        elif self.drive_play_count >= 8:
            return 1.15
        elif self.drive_play_count >= 5:
            return 1.05
        return 1.0

    def _red_zone_td_check(self, new_position: int, yards_gained: int, team: Team) -> bool:
        if yards_gained < 2:
            return False
        if new_position >= 93:
            td_chance = 0.25 + (team.avg_speed - 85) * 0.008
            if self.drive_play_count >= 8:
                td_chance += 0.08
            return random.random() < td_chance
        elif new_position >= 85:
            td_chance = 0.08 + (team.avg_speed - 85) * 0.004
            if self.drive_play_count >= 8:
                td_chance += 0.04
            return random.random() < td_chance
        return False

    def _breakaway_check(self, yards_gained: int, team: Team) -> int:
        if yards_gained >= 12:
            speed_gap = (team.avg_speed - 85) / 100
            def_fatigue_bonus = (self._defensive_fatigue_factor() - 1.0)
            breakaway_chance = 0.15 + speed_gap + def_fatigue_bonus
            if self.state.field_position >= 50:
                breakaway_chance += 0.10
            if random.random() < breakaway_chance:
                extra = random.randint(10, 40)
                return yards_gained + extra
        return yards_gained

    def simulate_run(self, family: PlayFamily = PlayFamily.DIVE_OPTION) -> Play:
        team = self.get_offensive_team()
        player = random.choice(team.players[:5])
        plabel = player_label(player)
        ptag = player_tag(player)

        if family == PlayFamily.DIVE_OPTION:
            base_yards = random.gauss(4.5, 3)
            action = "keep"
        elif family == PlayFamily.SPEED_OPTION:
            base_yards = random.gauss(5.5, 4.5)
            action = "pitch"
        elif family == PlayFamily.SWEEP_OPTION:
            base_yards = random.gauss(4, 5.5)
            action = "sweep"
        else:
            base_yards = random.gauss(4.5, 3.5)
            action = "run"

        style = self._current_style()
        strength_factor = team.avg_speed / 90
        fatigue_factor = self.get_fatigue_factor()
        fatigue_resistance = style.get("fatigue_resistance", 0.0)
        fatigue_factor = min(1.0, fatigue_factor + fatigue_resistance)
        viper_factor = self.calculate_viper_impact()
        def_fatigue = self._defensive_fatigue_factor()

        run_bonus = style.get("run_bonus", 0.0)
        if family in (PlayFamily.DIVE_OPTION, PlayFamily.SWEEP_OPTION):
            run_bonus_factor = 1.0 + run_bonus
        else:
            run_bonus_factor = 1.0

        option_read_bonus = style.get("option_read_bonus", 0.0)
        if family in (PlayFamily.SPEED_OPTION, PlayFamily.DIVE_OPTION) and option_read_bonus > 0:
            run_bonus_factor *= (1.0 + option_read_bonus)

        yards_gained = int(base_yards * strength_factor * fatigue_factor * viper_factor * def_fatigue * run_bonus_factor)
        yards_gained = max(-5, min(yards_gained, 30))

        broken_play_bonus = style.get("broken_play_bonus", 0.0)
        tired_def_broken = style.get("tired_def_broken_play_bonus", 0.0)
        if def_fatigue > 1.0 and tired_def_broken > 0:
            broken_play_bonus += tired_def_broken
        if broken_play_bonus > 0 and yards_gained >= 8:
            if random.random() < broken_play_bonus:
                yards_gained += random.randint(5, 15)

        yards_gained = self._breakaway_check(yards_gained, team)

        new_position = min(100, self.state.field_position + yards_gained)

        if new_position <= 0:
            self.change_possession()
            self.add_score(2)
            self.change_possession()
            self.apply_stamina_drain(3)
            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
            self.state.field_position = 20
            self.state.down = 1
            self.state.yards_to_go = 20
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
                players_involved=[plabel],
                yards_gained=yards_gained,
                result=PlayResult.SAFETY.value,
                description=f"{ptag} {action} → tackled in end zone — SAFETY! (+2 defensive)",
                fatigue=round(stamina, 1),
            )

        if new_position >= 100 or self._red_zone_td_check(new_position, yards_gained, team):
            result = PlayResult.TOUCHDOWN
            yards_gained = 100 - self.state.field_position
            self.add_score(9)
            description = f"{ptag} {action} → {yards_gained} — TOUCHDOWN!"
        elif yards_gained >= self.state.yards_to_go:
            result = PlayResult.FIRST_DOWN
            self.state.field_position = new_position
            self.state.down = 1
            self.state.yards_to_go = 20
            description = f"{ptag} {action} → {yards_gained} — FIRST DOWN"
        else:
            result = PlayResult.GAIN
            self.state.field_position = new_position
            self.state.down += 1
            self.state.yards_to_go -= yards_gained
            description = f"{ptag} {action} → {yards_gained}"

            if self.state.down > 5:
                result = PlayResult.TURNOVER_ON_DOWNS
                self.change_possession()
                self.state.field_position = 100 - self.state.field_position
                description += " — TURNOVER ON DOWNS"

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
            players_involved=[plabel],
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
        chain_tags = " → ".join(player_tag(p) for p in players_involved)
        chain_labels = [player_label(p) for p in players_involved]

        base_fumble_prob = random.uniform(0.08, 0.12)
        fumble_prob = base_fumble_prob
        fumble_prob += (chain_length - 1) * 0.03
        if self.drive_play_count >= 3:
            fumble_prob += random.uniform(0.04, 0.06)
        if chain_length >= 3:
            fumble_prob += 0.04
        if chain_length >= 4:
            fumble_prob += 0.04
        fatigue_factor_lat = self.get_fatigue_factor()
        if fatigue_factor_lat < 0.9:
            fumble_prob += 0.05

        tempo = style.get("tempo", 0.5)
        fumble_prob *= (1 + (tempo - 0.5) * 0.10)

        lateral_success_bonus = style.get("lateral_success_bonus", 0.0)
        fumble_prob *= (1 - lateral_success_bonus)

        fumble_prob *= style.get("lateral_risk", 1.0)
        prof_reduction = max(0.85, team.lateral_proficiency / 100)
        fumble_prob /= prof_reduction

        if random.random() < fumble_prob:
            yards_gained = random.randint(-5, 8)
            old_pos = self.state.field_position
            self.change_possession()
            self.state.field_position = max(1, 100 - old_pos)
            self.state.down = 1
            self.state.yards_to_go = 20
            self.add_score(0.5)

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
                players_involved=chain_labels,
                yards_gained=yards_gained,
                result=PlayResult.FUMBLE.value,
                description=f"{chain_tags} lateral → FUMBLE! Defense recovers (+0.5)",
                fatigue=round(stamina, 1),
                laterals=chain_length,
                fumble=True,
            )

        base_yards = random.gauss(8, 5)
        lateral_bonus = chain_length * 2.0
        fatigue_factor = self.get_fatigue_factor()
        viper_factor = self.calculate_viper_impact()
        def_fatigue = self._defensive_fatigue_factor()

        tired_def_yardage = style.get("tired_def_yardage_bonus", 0.0)
        if def_fatigue > 1.0 and tired_def_yardage > 0:
            def_fatigue += tired_def_yardage

        yards_gained = int((base_yards + lateral_bonus) * fatigue_factor * viper_factor * def_fatigue)
        yards_gained = max(-3, min(yards_gained, 40))

        explosive_lateral_bonus = style.get("explosive_lateral_bonus", 0.0)
        explosive_chance = chain_length * 0.05 + explosive_lateral_bonus
        if yards_gained >= 10 and random.random() < explosive_chance:
            extra = random.randint(8, 30)
            yards_gained += extra

        new_position = min(100, self.state.field_position + yards_gained)

        if new_position >= 100 or self._red_zone_td_check(new_position, yards_gained, team):
            result = PlayResult.TOUCHDOWN
            yards_gained = 100 - self.state.field_position
            self.add_score(9)
            description = f"{chain_tags} lateral → {yards_gained} — TOUCHDOWN!"
        elif yards_gained >= self.state.yards_to_go:
            result = PlayResult.FIRST_DOWN
            self.state.field_position = new_position
            self.state.down = 1
            self.state.yards_to_go = 20
            description = f"{chain_tags} lateral → {yards_gained} — FIRST DOWN"
        else:
            result = PlayResult.GAIN
            self.state.field_position = new_position
            self.state.down += 1
            self.state.yards_to_go -= yards_gained
            description = f"{chain_tags} lateral → {yards_gained}"

            if self.state.down > 5:
                result = PlayResult.TURNOVER_ON_DOWNS
                self.change_possession()
                self.state.field_position = 100 - self.state.field_position
                description += " — TURNOVER ON DOWNS"

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
            players_involved=chain_labels,
            yards_gained=yards_gained,
            result=result.value,
            description=description,
            fatigue=round(stamina, 1),
            laterals=chain_length,
        )

    def simulate_punt(self, family: PlayFamily = PlayFamily.TERRITORY_KICK) -> Play:
        team = self.get_offensive_team()
        punter = max(team.players[:8], key=lambda p: p.kicking)
        ptag = player_tag(punter)

        base_distance = random.gauss(45, 10)
        kicking_factor = punter.kicking / 80
        distance = int(base_distance * kicking_factor)
        distance = max(20, min(distance, 70))

        if random.random() < 0.04:
            tipped_distance = random.randint(5, 15)
            kicking_team_pos = self.state.possession
            self.change_possession()
            self.state.field_position = min(99, self.state.field_position + tipped_distance)
            self.state.down = 1
            self.state.yards_to_go = 20

            if random.random() < 0.12:
                self.change_possession()
                self.state.field_position = min(99, self.state.field_position)
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=self.state.possession,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="punt", play_family=family.value,
                    players_involved=[player_label(punter)], yards_gained=tipped_distance,
                    result=PlayResult.CHAOS_RECOVERY.value,
                    description=f"{ptag} punt TIPPED! Kicking team recovers at {self.state.field_position}!",
                    fatigue=round(stamina, 1),
                )

            self.apply_stamina_drain(2)
            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
            return Play(
                play_number=self.state.play_number, quarter=self.state.quarter,
                time=self.state.time_remaining, possession=self.state.possession,
                field_position=self.state.field_position, down=1, yards_to_go=20,
                play_type="punt", play_family=family.value,
                players_involved=[player_label(punter)], yards_gained=tipped_distance,
                result="punt",
                description=f"{ptag} punt TIPPED! {tipped_distance} yards, recovered by defense",
                fatigue=round(stamina, 1),
            )

        if random.random() < 0.07:
            bounce_extra = random.choice([-15, -10, 10, 15, 20, 25])
            distance = max(10, min(distance + bounce_extra, 80))

        landing_position = self.state.field_position + distance

        if landing_position >= 100:
            receiving_team = self.get_defensive_team()
            return_speed = receiving_team.avg_speed
            pindown_bonus = self._current_style().get("pindown_bonus", 0.0)
            can_return_out = random.random() < (return_speed / 110) * (1.0 - pindown_bonus)

            if can_return_out:
                self.change_possession()
                self.state.field_position = random.randint(5, 20)
                self.state.down = 1
                self.state.yards_to_go = 20
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
                return Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=self.state.possession,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="punt", play_family=family.value,
                    players_involved=[player_label(punter)], yards_gained=-distance,
                    result="punt",
                    description=f"{ptag} punt → {distance} yards into end zone, returned out to {self.state.field_position}",
                    fatigue=round(stamina, 1),
                )
            else:
                kicking_team = self.state.possession
                self.add_score(1)
                self.apply_stamina_drain(2)
                stamina = self.state.home_stamina if kicking_team == "home" else self.state.away_stamina
                play = Play(
                    play_number=self.state.play_number, quarter=self.state.quarter,
                    time=self.state.time_remaining, possession=kicking_team,
                    field_position=self.state.field_position, down=1, yards_to_go=20,
                    play_type="punt", play_family=family.value,
                    players_involved=[player_label(punter)], yards_gained=-distance,
                    result=PlayResult.PINDOWN.value,
                    description=f"{ptag} punt → {distance} yards — PINDOWN! +1",
                    fatigue=round(stamina, 1),
                )
                receiving = "away" if kicking_team == "home" else "home"
                self.kickoff(receiving)
                return play

        if random.random() < 0.08:
            def_team = self.get_defensive_team()
            returner = max(def_team.players[:5], key=lambda p: p.speed)
            rtag = player_tag(returner)
            self.change_possession()
            self.add_score(9)
            new_pos = 100 - min(99, self.state.field_position + distance)
            self.apply_stamina_drain(2)
            stamina = self.state.home_stamina if self.state.possession == "home" else self.state.away_stamina
            return Play(
                play_number=self.state.play_number, quarter=self.state.quarter,
                time=self.state.time_remaining, possession=self.state.possession,
                field_position=self.state.field_position, down=1, yards_to_go=20,
                play_type="punt", play_family=family.value,
                players_involved=[player_label(punter), player_label(returner)],
                yards_gained=new_pos,
                result=PlayResult.PUNT_RETURN_TD.value,
                description=f"{ptag} punt → {rtag} RETURNS IT ALL THE WAY — TOUCHDOWN! +9",
                fatigue=round(stamina, 1),
            )

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
            players_involved=[player_label(punter)],
            yards_gained=-distance,
            result="punt",
            description=f"{ptag} punt → {distance} yards",
            fatigue=round(stamina, 1),
        )

    def get_defensive_team(self) -> Team:
        return self.away_team if self.state.possession == "home" else self.home_team

    def simulate_drop_kick(self, family: PlayFamily = PlayFamily.TERRITORY_KICK) -> Play:
        team = self.get_offensive_team()
        kicker = max(team.players[:8], key=lambda p: p.kicking)
        ptag = player_tag(kicker)

        distance = 100 - self.state.field_position + 10

        base_prob = 0.75
        if distance <= 20:
            distance_factor = 1.0
        elif distance <= 30:
            distance_factor = 0.92
        elif distance <= 40:
            distance_factor = 0.80
        elif distance <= 50:
            distance_factor = 0.60
        else:
            distance_factor = max(0.1, 1 - (distance - 30) / 60)
        skill_factor = kicker.kicking / 85
        kick_acc = self._current_style().get("kick_accuracy_bonus", 0.0)
        success_prob = base_prob * distance_factor * skill_factor * (1.0 + kick_acc)

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
                players_involved=[player_label(kicker)],
                yards_gained=0,
                result=PlayResult.SUCCESSFUL_KICK.value,
                description=f"{ptag} snap kick {distance}yd — GOOD! +5",
                fatigue=round(stamina, 1),
            )
        else:
            if self.state.field_position >= 50:
                def_team = self.get_defensive_team()
                pindown_bonus = self._current_style().get("pindown_bonus", 0.0)
                can_return = random.random() < (def_team.avg_speed / 115) * (1.0 - pindown_bonus)
                if not can_return:
                    kicking_team = self.state.possession
                    self.add_score(1)
                    self.apply_stamina_drain(2)
                    stamina = self.state.home_stamina if kicking_team == "home" else self.state.away_stamina
                    play = Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=kicking_team,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="drop_kick", play_family=family.value,
                        players_involved=[player_label(kicker)], yards_gained=0,
                        result=PlayResult.PINDOWN.value,
                        description=f"{ptag} snap kick {distance}yd — NO GOOD → PINDOWN! +1",
                        fatigue=round(stamina, 1),
                    )
                    receiving = "away" if kicking_team == "home" else "home"
                    self.kickoff(receiving)
                    return play

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
                players_involved=[player_label(kicker)],
                yards_gained=0,
                result=PlayResult.MISSED_KICK.value,
                description=f"{ptag} snap kick {distance}yd — NO GOOD",
                fatigue=round(stamina, 1),
            )

    def simulate_place_kick(self, family: PlayFamily = PlayFamily.TERRITORY_KICK) -> Play:
        team = self.get_offensive_team()
        kicker = max(team.players[:8], key=lambda p: p.kicking)
        ptag = player_tag(kicker)

        distance = 100 - self.state.field_position + 10

        if distance <= 20:
            success_prob = 0.95
        elif distance <= 30:
            success_prob = 0.88
        elif distance <= 40:
            success_prob = 0.75
        elif distance <= 50:
            success_prob = 0.55
        else:
            success_prob = max(0.10, 0.55 - (distance - 50) * 0.02)
        skill_factor = kicker.kicking / 85
        kick_acc = self._current_style().get("kick_accuracy_bonus", 0.0)
        success_prob *= skill_factor * (1.0 + kick_acc)

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
                players_involved=[player_label(kicker)],
                yards_gained=0,
                result=PlayResult.SUCCESSFUL_KICK.value,
                description=f"{ptag} field goal {distance}yd — GOOD! +3",
                fatigue=round(stamina, 1),
            )
        else:
            if self.state.field_position >= 50:
                def_team = self.get_defensive_team()
                pindown_bonus = self._current_style().get("pindown_bonus", 0.0)
                can_return = random.random() < (def_team.avg_speed / 115) * (1.0 - pindown_bonus)
                if not can_return:
                    kicking_team = self.state.possession
                    self.add_score(1)
                    self.apply_stamina_drain(2)
                    stamina = self.state.home_stamina if kicking_team == "home" else self.state.away_stamina
                    play = Play(
                        play_number=self.state.play_number, quarter=self.state.quarter,
                        time=self.state.time_remaining, possession=kicking_team,
                        field_position=self.state.field_position, down=1, yards_to_go=20,
                        play_type="place_kick", play_family=family.value,
                        players_involved=[player_label(kicker)], yards_gained=0,
                        result=PlayResult.PINDOWN.value,
                        description=f"{ptag} field goal {distance}yd — NO GOOD → PINDOWN! +1",
                        fatigue=round(stamina, 1),
                    )
                    receiving = "away" if kicking_team == "home" else "home"
                    self.kickoff(receiving)
                    return play

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
                players_involved=[player_label(kicker)],
                yards_gained=0,
                result=PlayResult.MISSED_KICK.value,
                description=f"{ptag} field goal {distance}yd — NO GOOD",
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

    def add_score(self, points: float):
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

        away_fumbles = len([p for p in away_plays if p.fumble])
        home_fumbles = len([p for p in home_plays if p.fumble])
        home_stats["fumble_recoveries"] = away_fumbles
        away_stats["fumble_recoveries"] = home_fumbles
        home_stats["fumble_recovery_points"] = away_fumbles * 0.5
        away_stats["fumble_recovery_points"] = home_fumbles * 0.5

        for stats, plays in [(home_stats, home_plays), (away_stats, away_plays)]:
            plays_by_q = {q: 0 for q in range(1, 5)}
            for p in plays:
                if p.quarter in plays_by_q:
                    plays_by_q[p.quarter] += 1
            stats["plays_per_quarter"] = plays_by_q

        from .epa import calculate_ep, calculate_epa, calculate_game_epa

        play_dicts = []
        for i, p in enumerate(self.play_log):
            pd = self.play_to_dict(p)
            ep_before = calculate_ep(p.field_position, p.down)

            if i + 1 < len(self.play_log):
                next_p = self.play_log[i + 1]
                if next_p.possession == p.possession:
                    ep_after = calculate_ep(next_p.field_position, next_p.down)
                else:
                    opp_yard = 100 - next_p.field_position
                    ep_after = -calculate_ep(opp_yard, 1)
            else:
                ep_after = 0

            is_chaos = p.result in ("chaos_recovery", "punt_return_td")
            fp_after = self.play_log[i + 1].field_position if i + 1 < len(self.play_log) else p.field_position
            epa_data = {
                "ep_before": ep_before,
                "ep_after": ep_after,
                "result": p.result,
                "play_type": p.play_type,
                "laterals": p.laterals,
                "chaos_event": is_chaos,
                "field_position_after": fp_after,
            }
            epa_val = calculate_epa(epa_data)
            pd["ep_before"] = ep_before
            pd["epa"] = epa_val
            pd["chaos_event"] = is_chaos
            play_dicts.append(pd)

        home_epa = calculate_game_epa(play_dicts, "home")
        away_epa = calculate_game_epa(play_dicts, "away")
        home_stats["epa"] = home_epa
        away_stats["epa"] = away_epa

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
            "drive_summary": self.drive_log,
            "play_by_play": play_dicts,
        }

        return summary

    def calculate_team_stats(self, plays: List[Play]) -> Dict:
        total_yards = sum(p.yards_gained for p in plays if p.yards_gained > 0)
        total_plays = len(plays)

        laterals = [p for p in plays if p.laterals > 0]
        total_laterals = sum(p.laterals for p in laterals)
        successful_laterals = sum(1 for p in laterals if not p.fumble)

        drop_kicks = [p for p in plays if p.play_type == "drop_kick" and p.result == "successful_kick"]
        drop_kicks_attempted = [p for p in plays if p.play_type == "drop_kick"]
        place_kicks = [p for p in plays if p.play_type == "place_kick" and p.result == "successful_kick"]
        place_kicks_attempted = [p for p in plays if p.play_type == "place_kick"]
        touchdowns = [p for p in plays if p.result == "touchdown"]
        punt_return_tds = [p for p in plays if p.result == "punt_return_td"]
        fumbles_lost = [p for p in plays if p.fumble]
        turnovers_on_downs = [p for p in plays if p.result == "turnover_on_downs"]
        pindowns = [p for p in plays if p.result == "pindown"]
        punts = [p for p in plays if p.play_type == "punt"]
        chaos_recoveries = [p for p in plays if p.result == "chaos_recovery"]

        kick_plays = [p for p in plays if p.play_type in ["punt", "drop_kick", "place_kick"]]
        kick_percentage = round(len(kick_plays) / max(1, total_plays) * 100, 1)

        play_family_counts = {}
        for p in plays:
            fam = p.play_family
            play_family_counts[fam] = play_family_counts.get(fam, 0) + 1

        viper_efficiency = (total_yards / max(1, total_plays)) * (1 + successful_laterals / max(1, total_laterals))
        lateral_efficiency = (successful_laterals / max(1, len(laterals))) * 100 if laterals else 0

        fatigue_values = [p.fatigue for p in plays if p.fatigue is not None]
        avg_fatigue = round(sum(fatigue_values) / max(1, len(fatigue_values)), 1) if fatigue_values else 100.0

        down_conversions = {}
        for d in [3, 4, 5]:
            down_plays = [p for p in plays if p.down == d and p.play_type not in ["punt", "drop_kick", "place_kick"]]
            converted = [p for p in down_plays if p.yards_gained >= p.yards_to_go or p.result in ("touchdown", "punt_return_td")]
            down_conversions[d] = {
                "attempts": len(down_plays),
                "converted": len(converted),
                "rate": round(len(converted) / max(1, len(down_plays)) * 100, 1) if down_plays else 0.0,
            }

        return {
            "total_yards": total_yards,
            "total_plays": total_plays,
            "yards_per_play": round(total_yards / max(1, total_plays), 2),
            "touchdowns": len(touchdowns),
            "punt_return_tds": len(punt_return_tds),
            "lateral_chains": len(laterals),
            "successful_laterals": successful_laterals,
            "fumbles_lost": len(fumbles_lost),
            "turnovers_on_downs": len(turnovers_on_downs),
            "drop_kicks_made": len(drop_kicks),
            "drop_kicks_attempted": len(drop_kicks_attempted),
            "place_kicks_made": len(place_kicks),
            "place_kicks_attempted": len(place_kicks_attempted),
            "punts": len(punts),
            "pindowns": len(pindowns),
            "chaos_recoveries": len(chaos_recoveries),
            "kick_percentage": kick_percentage,
            "viper_efficiency": round(viper_efficiency, 2),
            "lateral_efficiency": round(lateral_efficiency, 1),
            "play_family_breakdown": play_family_counts,
            "avg_fatigue": avg_fatigue,
            "safeties_conceded": len([p for p in plays if p.result == "safety"]),
            "down_conversions": down_conversions,
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
