"""VAL-02: seeded rosters, schemes and games repeat across processes.

Python salts str hashes per process, so each check runs in fresh
interpreters with different PYTHONHASHSEED values.
"""

import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")

_SCRIPT = r'''
import sys, hashlib, json, random, importlib.util
sys.path.insert(0, ".")
spec = importlib.util.spec_from_file_location("bm", "scripts/benchmark_engine.py")
bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)
from engine import ViperballEngine
teams, styles, pairs = bm.build_matchups(1, 2026)
h = lambda o: hashlib.md5(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
a, b = pairs[0]
roster = [(p.name, p.position, p.overall, p.agility, p.reach, p.glue, p.fit)
          for p in teams[a].players + teams[b].players]
r = ViperballEngine(teams[a], teams[b], seed=2026,
                    style_overrides=bm.overrides(styles, a, b)).simulate_game()
print(h(roster), h(styles), h([p["description"] for p in r["play_by_play"]]))
'''


def _run(hash_seed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed)
    out = subprocess.run([sys.executable, "-c", _SCRIPT], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=600, check=True)
    return out.stdout.strip().splitlines()[-1]


def test_rosters_schemes_and_game_repeat_across_processes():
    first = _run("1")
    assert first == _run("2") == _run("3")


def test_stable_hash_is_fixed():
    from engine.stable_hash import stable_hash
    assert stable_hash("Gonzaga") == stable_hash("Gonzaga")
    assert stable_hash("viperball") == 3357638475


def test_chemistry_comes_from_player_identity():
    from engine.chemistry import generate_chemistry_attributes
    from engine.game_engine import Player

    def make():
        p = Player(number=7, name="Test Player", position="Viper", speed=80, stamina=80,
                   kicking=70, lateral_skill=75, tackling=60)
        generate_chemistry_attributes(p)
        return (p.reach, p.pull, p.glue, p.voice, p.fit, p.reach_range)

    assert make() == make()
