"""
Zeroback Position Logic

The Zeroback is the MOST IMPORTANT position in Viperball.

This position determines what the play becomes:
- Read interior
- Give to HB
- Keep and run
- Pitch to wing
- Quick kick
- Initiate lateral chain

Decision tree runs every snap and controls:
- Branch probabilities
- Play tempo
- Kick frequency
- Turnover risk
"""

import random
from typing import Dict, Optional, Tuple, Literal
from ..player import Player, ZEROBACK_ARCHETYPES


class ZerobackDecision:
    """
    Represents a Zeroback's decision on a given play.

    The decision tree looks like:

    Read interior
    ├─ Give to HB (most common)
    ├─ Keep (if edge is open)
    ├─ Pitch to wing (if numbers favor perimeter)
    ├─ Quick kick (if field position dictates)
    └─ Lateral (if chaos archetype)
    """

    def __init__(self,
                 zeroback: Player,
                 game_state: Dict,
                 team_style: Dict):
        """
        Initialize decision context.

        Args:
            zeroback: The Zeroback player making decisions
            game_state: Current game situation (down, distance, field position, etc.)
            team_style: Team's offensive philosophy
        """
        self.zeroback = zeroback
        self.game_state = game_state
        self.team_style = team_style

        # Get archetype modifiers
        archetype_name = zeroback.archetype.lower().replace(' ', '_')
        self.archetype = ZEROBACK_ARCHETYPES.get(archetype_name, {})

    def make_decision(self) -> Tuple[str, Dict]:
        """
        Execute the Zeroback decision tree.

        Returns:
            (decision_type, decision_data)

        decision_type: 'give', 'keep', 'pitch', 'kick', 'lateral'
        decision_data: Additional info about the decision
        """

        # Get effective traits (adjusted for fatigue)
        decision_rating = self.zeroback.get_trait_value('decision')
        kick_rating = self.zeroback.get_trait_value('kick')
        speed_rating = self.zeroback.get_trait_value('speed')
        discipline = self.zeroback.get_trait_value('discipline')

        # Apply archetype modifiers
        read_quality = self.archetype.get('read_quality', 1.0)
        kick_tendency = self.archetype.get('kick_frequency', 1.0)
        lateral_tendency = self.archetype.get('lateral_tendency', 1.0)

        # Get game context
        down = self.game_state.get('down', 1)
        distance = self.game_state.get('distance', 10)
        field_position = self.game_state.get('field_position', 50)
        score_diff = self.game_state.get('score_diff', 0)

        # Base probabilities
        probs = {
            'give': 0.45,     # Most common: hand to HB
            'keep': 0.25,     # Keep and run
            'pitch': 0.15,    # Pitch to wing
            'kick': 0.10,     # Quick kick
            'lateral': 0.05   # Start lateral chain
        }

        # Modify based on decision quality
        if decision_rating >= 85:
            # Good decision-makers choose better based on situation
            if distance >= 7:
                probs['pitch'] += 0.10  # More outside runs on long distance
                probs['give'] -= 0.05
            if field_position <= 35:
                probs['kick'] += 0.15  # Kick more in own territory
                probs['give'] -= 0.10
        elif decision_rating <= 65:
            # Poor decision-makers are more random
            probs['lateral'] += 0.08
            probs['give'] -= 0.05

        # Modify based on kick ability
        if kick_rating >= 80:
            probs['kick'] *= kick_tendency
            probs['kick'] = min(0.40, probs['kick'])  # Cap at 40%

        # Modify based on archetype
        if self.archetype.get('conservative'):
            probs['give'] += 0.15
            probs['lateral'] -= 0.03
            probs['kick'] += 0.10
        elif lateral_tendency > 1.3:
            probs['lateral'] += 0.12
            probs['pitch'] += 0.08
            probs['give'] -= 0.10

        # Field position adjustments
        if field_position <= 25:  # Deep in own territory
            probs['kick'] += 0.20
            probs['lateral'] -= 0.05
        elif field_position >= 65:  # In scoring range
            probs['kick'] -= 0.08
            probs['lateral'] += 0.05

        # Down and distance adjustments
        if down >= 4:  # 4th or 5th down
            if distance >= 8:
                probs['kick'] += 0.25  # Much more likely to kick
            else:
                probs['give'] += 0.10  # Go for it

        # Normalize probabilities
        total = sum(probs.values())
        probs = {k: v/total for k, v in probs.items()}

        # Make decision
        decision = random.choices(
            list(probs.keys()),
            weights=list(probs.values()),
            k=1
        )[0]

        # Generate decision data
        decision_data = {
            'decision_rating': decision_rating,
            'read_quality': read_quality,
            'probabilities': probs,
            'archetype': self.zeroback.archetype,
            'fatigue': self.zeroback.fatigue
        }

        return decision, decision_data

    def get_turnover_risk(self, decision_type: str) -> float:
        """
        Calculate turnover risk for this decision.

        Returns probability of turnover (0.0 - 1.0).
        """
        base_risk = {
            'give': 0.02,      # Handoffs are safe
            'keep': 0.04,      # Keeping has some risk
            'pitch': 0.06,     # Pitches can be dropped
            'kick': 0.01,      # Kicks rarely turn over
            'lateral': 0.12    # Laterals are risky
        }

        risk = base_risk.get(decision_type, 0.03)

        # Adjust for decision quality
        decision_rating = self.zeroback.get_trait_value('decision')
        if decision_rating >= 85:
            risk *= 0.7
        elif decision_rating <= 65:
            risk *= 1.4

        # Adjust for archetype
        turnover_modifier = self.archetype.get('turnover_rate', 1.0)
        risk *= turnover_modifier

        # Adjust for fatigue (tired players make mistakes)
        if self.zeroback.fatigue > 0.6:
            risk *= 1.5

        return min(0.30, risk)  # Cap at 30%

    def get_tempo_modifier(self) -> float:
        """
        Get tempo modifier based on Zeroback's archetype.

        Higher = faster snaps.

        Returns multiplier (1.0 = normal, 1.5 = very fast).
        """
        return self.archetype.get('tempo_bonus', 1.0)


def execute_zeroback_read(
    zeroback: Player,
    game_state: Dict,
    team_style: Dict
) -> Tuple[str, Dict]:
    """
    Execute the Zeroback decision tree for a play.

    This is called every snap to determine what happens.

    Args:
        zeroback: The Zeroback player
        game_state: Current game situation
        team_style: Team's offensive philosophy

    Returns:
        (decision, decision_data)
    """
    decision_maker = ZerobackDecision(zeroback, game_state, team_style)
    decision, data = decision_maker.make_decision()

    # Add turnover risk to data
    data['turnover_risk'] = decision_maker.get_turnover_risk(decision)
    data['tempo_modifier'] = decision_maker.get_tempo_modifier()

    return decision, data


if __name__ == "__main__":
    print("Testing Zeroback Decision Engine\n")
    print("=" * 70)

    # Import Player model
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from viperball_v2.player import Player, PlayerTraits

    # Create test Zerobacks with different archetypes
    print("\n1. OPTION MASTER ZEROBACK")
    print("-" * 70)

    option_master_traits = PlayerTraits(
        speed=80,
        power=72,
        agility=78,
        stamina=85,
        decision=92,       # Excellent decision-making
        awareness=88,
        discipline=90,
        kick=75,
        hands=82,
        tackle=65
    )

    option_master = Player(
        name="Sarah Chen",
        number=7,
        position="Zeroback",
        traits=option_master_traits,
        archetype="Option Master"
    )

    game_state = {
        'down': 1,
        'distance': 10,
        'field_position': 50,
        'score_diff': 0
    }

    team_style = {'philosophy': 'power_option'}

    # Run 10 decisions
    decisions = {'give': 0, 'keep': 0, 'pitch': 0, 'kick': 0, 'lateral': 0}
    for i in range(10):
        decision, data = execute_zeroback_read(option_master, game_state, team_style)
        decisions[decision] += 1
        if i == 0:
            print(f"First decision: {decision}")
            print(f"  Decision rating: {data['decision_rating']}")
            print(f"  Turnover risk: {data['turnover_risk']:.1%}")
            print(f"  Probabilities: {{{', '.join([f'{k}: {v:.1%}' for k, v in data['probabilities'].items()])}}}")

    print(f"\nDecision distribution (10 plays):")
    for decision, count in decisions.items():
        print(f"  {decision}: {count}/10 ({count*10}%)")

    print("\n" + "=" * 70)
    print("\n2. CHAOS OPERATOR ZEROBACK")
    print("-" * 70)

    chaos_traits = PlayerTraits(
        speed=90,
        power=68,
        agility=88,
        stamina=82,
        decision=75,       # Average decision-making
        awareness=78,
        discipline=70,
        kick=68,
        hands=88,
        tackle=62
    )

    chaos_operator = Player(
        name="Riley Martinez",
        number=12,
        position="Zeroback",
        traits=chaos_traits,
        archetype="Chaos Operator"
    )

    # Run 10 decisions
    decisions = {'give': 0, 'keep': 0, 'pitch': 0, 'kick': 0, 'lateral': 0}
    for i in range(10):
        decision, data = execute_zeroback_read(chaos_operator, game_state, team_style)
        decisions[decision] += 1
        if i == 0:
            print(f"First decision: {decision}")
            print(f"  Decision rating: {data['decision_rating']}")
            print(f"  Turnover risk: {data['turnover_risk']:.1%}")
            print(f"  Probabilities: {{{', '.join([f'{k}: {v:.1%}' for k, v in data['probabilities'].items()])}}}")

    print(f"\nDecision distribution (10 plays):")
    for decision, count in decisions.items():
        print(f"  {decision}: {count}/10 ({count*10}%)")

    print("\n" + "=" * 70)
    print("✅ Zeroback decision engine test complete!")
