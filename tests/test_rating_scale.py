"""PRO-01: every league on the current rating scale."""
import glob
import json
import os
import random
import statistics

from engine.rating_scale import convert_card_dict, current_to_legacy, legacy_to_current

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _files(sub):
    return sorted(glob.glob(os.path.join(ROOT, "data", sub, "*.json")))


def _mean_stat(path):
    d = json.load(open(path))
    vals = [v for p in d["roster"]["players"] for k, v in p["stats"].items() if k != "work_rate"]
    return statistics.mean(vals)


def test_all_team_files_are_on_the_current_scale():
    subs = ["teams", "nvl_teams", "al_teams", "el_teams", "la_teams", "pl_teams",
            "wvl_teams/tier1", "wvl_teams/tier2", "wvl_teams/tier3", "wvl_teams/tier4"]
    for sub in subs:
        for path in _files(sub):
            d = json.load(open(path))
            if "roster" not in d:
                continue
            assert d.get("rating_scale") == "current", path
            assert _mean_stat(path) < 75, path


def test_wvl_tiers_keep_their_order():
    means = [statistics.mean(_mean_stat(p) for p in _files(f"wvl_teams/tier{t}")) for t in (1, 2, 3, 4)]
    assert means == sorted(means, reverse=True)
    assert means[0] - means[3] > 30


def test_conversion_helpers():
    assert legacy_to_current(70) == 35 and legacy_to_current(90) == 75
    assert current_to_legacy(35) == 70
    d = convert_card_dict({"ratings": {"speed": 80, "kicking": 60}})
    assert d["ratings"] == {"speed": 55, "kicking": 15}


def test_old_wvl_career_save_migrates_synthetic_cards():
    from engine.player_card import PlayerCard
    from engine.wvl_career import WVLCareerLeague
    card = PlayerCard(player_id="synthgrad_1", first_name="A", last_name="B", number=1,
                      position="Viper", archetype="none", nationality="", hometown_city="",
                      hometown_state="", hometown_country="", high_school="", height="5-8",
                      weight=150, year="Pro", speed=80, stamina=80, agility=80, power=80,
                      awareness=80, hands=80, kicking=80, kick_power=80, kick_accuracy=80,
                      lateral_skill=80, tackling=80, potential=3, development="normal")
    grad = PlayerCard.from_dict(card.to_dict())
    grad.player_id = "cvl_1"
    data = {"league_id": "t", "cards": {"synthgrad_1": card.to_dict(), "cvl_1": grad.to_dict()},
            "roster_cards": {}}
    league = WVLCareerLeague.from_dict(data)
    assert league.cards["synthgrad_1"].speed == 55
    assert league.cards["cvl_1"].speed == 80


def test_ai_schemes_still_spread_across_offenses():
    import collections
    from engine.ai_coach import auto_assign_all_teams
    styles = auto_assign_all_teams(os.path.join(ROOT, "data", "teams"), human_teams=[], seed=2026)
    counts = collections.Counter(v["offense_style"] for v in styles.values())
    assert counts.most_common(1)[0][1] < 0.25 * len(styles)
    assert counts["boot_raid"] >= 15
