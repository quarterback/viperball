"""SIM-01: pro, WVL and HS title games run on the full engine."""
import random
import statistics

from engine.game_engine import Player, Team, ViperballEngine
from engine.pro_scale import (
    current_to_legacy, engine_scale, is_legacy_team, legacy_to_engine, PRO_LEAGUE_CENTER,
)

ATTRS = ("speed", "stamina", "kicking", "lateral_skill", "tackling", "agility",
         "power", "awareness", "hands", "kick_power", "kick_accuracy")
POSITIONS = (["Offensive Line"] * 7 + ["Defensive Line"] * 8 + ["Zeroback"] * 2
             + ["Viper"] * 3 + ["Halfback"] * 4 + ["Wingback"] * 4 + ["Slotback"] * 4
             + ["Keeper"] * 4)


def _legacy_team(name, center, rng):
    players = []
    for i, pos in enumerate(POSITIONS):
        vals = {a: int(rng.gauss(center, 4)) for a in ATTRS}
        players.append(Player(number=i + 1, name=f"{name} {i}", position=pos, **vals))
    return Team(name=name, abbreviation=name[:3].upper(), mascot="X", players=players,
                avg_speed=center, avg_stamina=center, kicking_strength=center,
                lateral_proficiency=center, defensive_strength=center)


def test_conversion_centers_and_restores():
    rng = random.Random(1)
    home, away = _legacy_team("Home", 84, rng), _legacy_team("Away", 82, rng)
    assert is_legacy_team(home)
    before = [(p.speed, p.kicking) for p in home.players] + [home.avg_speed]
    with engine_scale(home, away, center=83):
        mean = statistics.mean(p.overall for p in home.players + away.players)
        assert abs(mean - PRO_LEAGUE_CENTER) < 6
        assert home.avg_speed < 50
        ViperballEngine(home, away, seed=3).simulate_game()
    assert [(p.speed, p.kicking) for p in home.players] + [home.avg_speed] == before


def test_scale_helpers_round_trip():
    assert legacy_to_engine(70, center=70) == round(PRO_LEAGUE_CENTER)
    assert current_to_legacy(35) == 70
    assert current_to_legacy(75) == 90


def test_hs_title_game_uses_engine():
    from engine.hs_league import _hs_engine_game, create_hs_league
    rng = random.Random(2)
    league = create_hs_league(2026, rng=rng)
    home, away = list(league.teams.values())[:2]
    result = _hs_engine_game(home, away, rng, playoff_round="state_final")
    assert result.home_score != result.away_score
    assert result.home_score + result.away_score > 20
    assert home.wins + home.losses == 1
