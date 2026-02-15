"""
Viperball Engine v2 - Player Model

Every player on the field is an agent with:
- Base traits (0-100 scale)
- Position archetype
- Fatigue state
- Role-specific logic

This is the foundation of the agent-based simulation.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Literal
import random


@dataclass
class PlayerTraits:
    """
    Base traits for all players (0-100 scale).

    These feed every outcome in the simulation.
    """
    # Physical traits
    speed: int = 75          # Sprint speed, breakaway potential
    power: int = 75          # Physical strength, breaking tackles
    agility: int = 75        # Change of direction, evasiveness
    stamina: int = 80        # Resistance to fatigue

    # Mental/skill traits
    decision: int = 75       # Read quality, option execution
    awareness: int = 75      # Field vision, positioning
    discipline: int = 75     # Penalty avoidance, assignment adherence

    # Technical traits
    kick: int = 70           # Kicking distance and accuracy
    hands: int = 75          # Catching laterals, ball security
    tackle: int = 70         # Defensive tackling ability

    def __post_init__(self):
        """Validate all traits are 0-100."""
        for trait_name in ['speed', 'power', 'agility', 'stamina', 'decision',
                          'awareness', 'discipline', 'kick', 'hands', 'tackle']:
            value = getattr(self, trait_name)
            if not 0 <= value <= 100:
                raise ValueError(f"{trait_name} must be 0-100, got {value}")

    def apply_fatigue(self, fatigue_level: float) -> 'PlayerTraits':
        """
        Return trait values modified by fatigue.

        Fatigue (0.0 = fresh, 1.0 = exhausted) reduces:
        - Speed
        - Decision quality
        - Agility
        - Tackling
        """
        fatigue_penalty = int(fatigue_level * 20)  # Up to -20 points when exhausted

        return PlayerTraits(
            speed=max(0, self.speed - fatigue_penalty),
            power=self.power,  # Power not affected by fatigue
            agility=max(0, self.agility - int(fatigue_penalty * 0.5)),
            stamina=self.stamina,
            decision=max(0, self.decision - fatigue_penalty),
            awareness=max(0, self.awareness - int(fatigue_penalty * 0.7)),
            discipline=max(0, self.discipline - int(fatigue_penalty * 0.3)),
            kick=max(0, self.kick - fatigue_penalty),
            hands=max(0, self.hands - int(fatigue_penalty * 0.5)),
            tackle=max(0, self.tackle - fatigue_penalty)
        )


@dataclass
class Player:
    """
    Represents a single player on the field.

    Each player is an agent with:
    - Identity (name, position, number)
    - Traits (physical and mental attributes)
    - Archetype (playing style)
    - State (fatigue, current role)
    """

    # Identity
    name: str
    number: int
    position: str  # "Zeroback", "Halfback", "Viper", etc.

    # Attributes
    traits: PlayerTraits
    archetype: str = "Balanced"  # Position-specific archetype

    # State
    fatigue: float = 0.0  # 0.0 = fresh, 1.0 = exhausted
    snaps_played: int = 0
    is_on_field: bool = True

    # Metadata
    height: str = "5-10"
    weight: int = 175
    year: str = "Junior"
    hometown: Dict = field(default_factory=dict)

    def get_effective_traits(self) -> PlayerTraits:
        """Get trait values adjusted for current fatigue."""
        return self.traits.apply_fatigue(self.fatigue)

    def add_fatigue(self, amount: float):
        """
        Add fatigue to this player.

        Amount depends on:
        - Play intensity
        - Player stamina
        - Position demands
        """
        # High stamina resists fatigue
        stamina_factor = (100 - self.traits.stamina) / 100
        actual_fatigue = amount * (0.5 + stamina_factor)

        self.fatigue = min(1.0, self.fatigue + actual_fatigue)
        self.snaps_played += 1

    def recover_fatigue(self, amount: float = 0.05):
        """Recover some fatigue (happens when player rests or between plays)."""
        self.fatigue = max(0.0, self.fatigue - amount)

    def is_exhausted(self) -> bool:
        """Check if player is too tired to be effective."""
        return self.fatigue > 0.7

    def get_trait_value(self, trait_name: str) -> int:
        """
        Get a single trait value (fatigue-adjusted).

        Used by position logic to make decisions.
        """
        effective = self.get_effective_traits()
        return getattr(effective, trait_name, 75)

    @classmethod
    def from_roster_data(cls, roster_data: Dict) -> 'Player':
        """
        Create a Player from roster JSON data.

        Converts old stat format to new trait system:
        - speed → speed
        - stamina → stamina
        - kicking → kick
        - lateral_skill → hands + agility
        - tackling → tackle
        """
        stats = roster_data.get('stats', {})

        # Map old stats to new traits
        speed = stats.get('speed', 75)
        stamina = stats.get('stamina', 80)
        kick = stats.get('kicking', 70)
        lateral_skill = stats.get('lateral_skill', 75)
        tackling = stats.get('tackling', 70)

        # Derive other traits
        hands = lateral_skill  # Lateral skill → catching ability
        agility = min(100, int(lateral_skill * 0.9 + speed * 0.1))
        decision = min(100, int(stamina * 0.3 + lateral_skill * 0.4 + random.randint(-5, 5)))
        awareness = min(100, int((speed + lateral_skill) // 2 + random.randint(-5, 5)))
        discipline = min(100, int(stamina * 0.7 + random.randint(-5, 10)))
        power = min(100, int((100 - speed * 0.5) + tackling * 0.3 + random.randint(-5, 5)))

        traits = PlayerTraits(
            speed=speed,
            power=power,
            agility=agility,
            stamina=stamina,
            decision=decision,
            awareness=awareness,
            discipline=discipline,
            kick=kick,
            hands=hands,
            tackle=tackling
        )

        return cls(
            name=roster_data['name'],
            number=roster_data['number'],
            position=roster_data['position'],
            traits=traits,
            archetype="Balanced",  # Will be assigned by position logic
            height=roster_data.get('height', '5-10'),
            weight=roster_data.get('weight', 175),
            year=roster_data.get('year', 'Junior'),
            hometown=roster_data.get('hometown', {})
        )

    def __repr__(self):
        return f"#{self.number} {self.name} ({self.position})"


# Position-specific archetype definitions
# These will be imported by position modules

ZEROBACK_ARCHETYPES = {
    'option_master': {
        'name': 'Option Master',
        'read_quality': 1.2,         # Better decision-making
        'turnover_rate': 0.7,        # Fewer turnovers
        'big_play_rate': 1.0,        # Average explosiveness
        'kick_frequency': 0.9        # Slightly less kicking
    },
    'chaos_operator': {
        'name': 'Chaos Operator',
        'read_quality': 0.9,
        'turnover_rate': 1.4,        # More turnovers
        'big_play_rate': 1.5,        # More big plays
        'kick_frequency': 0.7,
        'lateral_tendency': 1.6      # Loves to lateral
    },
    'territorialist': {
        'name': 'Territorialist',
        'read_quality': 1.1,
        'turnover_rate': 0.8,
        'big_play_rate': 0.7,        # Fewer big plays
        'kick_frequency': 1.5,       # Kicks often
        'conservative': True
    },
    'tempo_driver': {
        'name': 'Tempo Driver',
        'read_quality': 1.0,
        'turnover_rate': 1.1,
        'big_play_rate': 1.2,
        'tempo_bonus': 1.4,          # Faster snaps
        'fatigue_rate': 1.3          # Tires team faster
    }
}

HALFBACK_ARCHETYPES = {
    'power': {
        'name': 'Power',
        'inside_run_bonus': 1.3,     # Better between tackles
        'breakaway_rate': 0.7,       # Fewer long runs
        'stamina_drain': 0.9         # Tires slower
    },
    'explosive': {
        'name': 'Explosive',
        'inside_run_bonus': 1.0,
        'breakaway_rate': 1.8,       # More long runs
        'stamina_drain': 1.4         # Tires faster
    },
    'connector': {
        'name': 'Connector',
        'inside_run_bonus': 1.0,
        'lateral_continuation': 1.4,  # Improves lateral chains
        'hands_bonus': 1.2
    }
}

VIPER_ARCHETYPES = {
    'deep_threat': {
        'name': 'Deep Threat',
        'explosive_rate': 1.6,
        'kick_return_bonus': 1.3,
        'stamina_drain': 1.5         # Low stamina
    },
    'chaos': {
        'name': 'Chaos',
        'explosive_rate': 1.4,
        'turnover_swing': 1.8,       # High variance (big plays OR turnovers)
        'unpredictable': True
    },
    'stabilizer': {
        'name': 'Stabilizer',
        'explosive_rate': 0.9,
        'turnover_prevention': 1.4,  # Reduces catastrophic plays
        'awareness_bonus': 1.2
    }
}

DEFENSIVE_ARCHETYPES = {
    'penetrator': {
        'name': 'Penetrator',
        'tfl_rate': 1.5,             # More tackles for loss
        'big_run_allowed': 1.3       # But gives up more big runs
    },
    'wall': {
        'name': 'Wall',
        'tfl_rate': 0.9,
        'big_run_allowed': 0.6,      # Very stable
        'consistency': 1.3
    },
    'stripper': {
        'name': 'Stripper',
        'fumble_force_rate': 1.7,    # Forces turnovers
        'tackle_miss_rate': 1.2      # But misses more tackles
    }
}


def assign_archetype(player: Player, team_style: Optional[str] = None) -> str:
    """
    Assign an archetype to a player based on their traits and team style.

    Returns the archetype name.
    """
    position = player.position.lower()
    traits = player.traits

    # Zeroback archetypes
    if 'zeroback' in position:
        if traits.kick >= 85 and traits.decision >= 80:
            return 'territorialist'
        elif traits.decision >= 85 and traits.discipline >= 80:
            return 'option_master'
        elif traits.speed >= 85 and traits.agility >= 80:
            return 'tempo_driver'
        else:
            return 'chaos_operator'

    # Halfback archetypes
    elif 'halfback' in position:
        if traits.power >= 80:
            return 'power'
        elif traits.speed >= 88:
            return 'explosive'
        else:
            return 'connector'

    # Viper archetypes
    elif 'viper' in position:
        if traits.speed >= 90 and traits.awareness <= 75:
            return 'chaos'
        elif traits.speed >= 90:
            return 'deep_threat'
        else:
            return 'stabilizer'

    # Default
    return 'balanced'


if __name__ == "__main__":
    print("Testing Viperball Engine v2 - Player Model\n")
    print("=" * 60)

    # Create a test player
    traits = PlayerTraits(
        speed=92,
        power=70,
        agility=88,
        stamina=85,
        decision=78,
        awareness=82,
        discipline=75,
        kick=65,
        hands=90,
        tackle=68
    )

    player = Player(
        name="Sarah Martinez",
        number=1,
        position="Viper",
        traits=traits,
        archetype="Deep Threat"
    )

    print(f"Created player: {player}")
    print(f"\nBase traits:")
    print(f"  Speed: {player.traits.speed}")
    print(f"  Decision: {player.traits.decision}")
    print(f"  Hands: {player.traits.hands}")

    print(f"\nFatigue: {player.fatigue:.1%}")
    print(f"Effective speed: {player.get_trait_value('speed')}")

    # Simulate fatigue
    print(f"\n--- After 15 snaps ---")
    for _ in range(15):
        player.add_fatigue(0.04)

    print(f"Fatigue: {player.fatigue:.1%}")
    print(f"Effective speed: {player.get_trait_value('speed')} (penalty: -{player.traits.speed - player.get_trait_value('speed')})")
    print(f"Effective decision: {player.get_trait_value('decision')} (penalty: -{player.traits.decision - player.get_trait_value('decision')})")
    print(f"Is exhausted: {player.is_exhausted()}")

    print("\n" + "=" * 60)
    print("✅ Player model test complete!")
