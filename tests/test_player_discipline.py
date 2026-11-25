"""PEN-03 regression tests: ejections are independent of yardage."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.discipline import IMMEDIATE_EJECTION, UNSPORTSMANLIKE, offender_weight
from engine.game_engine import ViperballEngine, Penalty, load_team_from_json, player_tag
from engine.officiating import decide

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def game():
    teams = sorted((ROOT / "data" / "teams").glob("*.json"))
    return ViperballEngine(load_team_from_json(str(teams[0])),
                           load_team_from_json(str(teams[1])), seed=1303)


def foul(game, player, name, side="home", declined=False):
    penalty = Penalty(name, 15, side, player_tag(player), declined=declined,
                      player_name=player.name, player_id=player.player_id)
    play = SimpleNamespace(penalty=penalty, possession="home", quarter=1,
                           time=500, play_number=1, description="Play")
    game._record_discipline(play)
    return play


@pytest.mark.parametrize("name", sorted(IMMEDIATE_EJECTION))
def test_immediate_ejection_even_if_declined(game, name):
    team = game.home_team
    player = game._lineup(team, set(), "offense")[0][0]
    play = foul(game, player, name, declined=True)
    assert play.penalty.ejection
    assert player.name in game._ejected_names(team)
    assert player.name not in game._injured_in_game(team)
    assert "EJECTED" in play.description
    assert len(game.ejection_log) == 1
    game._record_discipline(play)
    assert len(game.ejection_log) == 1
    for side in ("offense", "defense"):
        assert player.name not in {p.name for p, _ in game._lineup(team, set(), side)}
    assert player not in game._offense_all(team)
    assert player not in game._defense_players(team)
    assert player not in game._kicker_candidates(team)
    assert player not in game.get_available_players(team, 100)
    game._process_bench_expirations(team)
    game._rotate_shifts()
    game.state.quarter = 5
    assert player.name in game._unavailable_in_game(team)


def test_two_conduct_fouls_are_player_specific(game):
    a, b = game.home_team.players[:2]
    assert not foul(game, a, "Taunting").penalty.ejection
    assert not foul(game, b, "Taunting").penalty.ejection
    assert not foul(game, a, "Holding").penalty.ejection
    second = foul(game, a, "Unsportsmanlike Conduct", declined=True)
    assert second.penalty.ejection
    assert second.penalty.misconduct_count == 2
    assert b.name not in game._ejected_names(game.home_team)
    assert len(game.ejection_log) == 1
    assert game._discipline["home"][a.name]["flags"] == 3
    assert game._discipline["home"][a.name]["accepted"] == 2


def test_sides_and_games_independent(game):
    player = game.away_team.players[0]
    foul(game, player, "Fighting", side="away")
    assert player.name in game._ejected_names(game.away_team)
    assert not game._ejected_names(game.home_team)
    fresh = ViperballEngine(game.home_team, game.away_team, seed=1304)
    assert not fresh._ejected_names(fresh.away_team)
    assert not fresh.ejection_log


def test_severe_foul_is_never_discretionary_no_call():
    import random
    crew = SimpleNamespace(accuracy=.95)
    rng = random.Random(13)
    for name in IMMEDIATE_EJECTION:
        for _ in range(100):
            outcome, material = decide(name, crew, late_close=True, playoff=True, rng=rng)
            assert material and outcome in ("called", "missed")


def test_fatigue_awareness_offender_weight():
    fresh = SimpleNamespace(awareness=80, game_energy=100)
    tired = SimpleNamespace(awareness=20, game_energy=40)
    assert offender_weight(tired) > offender_weight(fresh)
