"""College recruiting and cohort continuity."""
import json
import random
from types import SimpleNamespace
from statistics import mean

from engine.recruiting import generate_single_recruit, generate_hs_class
from engine.player_card import PlayerCard, card_to_player, player_to_card
from engine.roster_continuity import projected_rosters, fill_college_roster_gaps, COLLEGE_DEPTH
from engine.coaching import CoachCard, generate_coaching_staff


def test_hs_classes_begin_at_grade_appropriate_strength():
    ninth = generate_hs_class("9th", 200, rng=random.Random(44))
    senior = generate_hs_class("12th", 200, rng=random.Random(44))
    assert mean(p.recruit.true_overall for p in ninth) < mean(p.recruit.true_overall for p in senior)


def test_transfer_uses_identity_not_name_and_excludes_graduates():
    a = generate_single_recruit("one", rng=random.Random(11)).to_player_card("A")
    b = generate_single_recruit("two", rng=random.Random(12)).to_player_card("A")
    b.first_name, b.last_name = a.first_name, a.last_name
    g = generate_single_recruit("grad", rng=random.Random(13)).to_player_card("A")
    g.year = "Graduate"
    entry = SimpleNamespace(origin_team="A", committed_to="B", player_card=a)
    result = projected_rosters({"A":[a,b,g], "B":[]}, SimpleNamespace(entries=[entry]))
    assert [c.player_id for c in result["A"]] == ["two"]
    assert [c.player_id for c in result["B"]] == ["one"]
    assert result["B"][0].transfer_count == 1
    assert result["B"][0].current_team == "B"
    assert a.transfer_count == 0


def test_walkons_fill_only_remaining_depth_and_keep_signed_players():
    rng = random.Random(71)
    cards = []
    for position, n in COLLEGE_DEPTH.items():
        for i in range(n - (position == "Keeper")):
            cards.append(generate_single_recruit(f"{position}-{i}", position=position, rng=rng).to_player_card("A"))
    prospect = generate_single_recruit("unsigned", position="Keeper", rng=rng)
    rosters = {"A":cards}
    ledger = fill_college_roster_gaps(rosters, [prospect], 2027, rng)
    assert len(rosters["A"]) == 36
    assert ledger["A"][0]["source"] == "unsigned"
    assert rosters["A"][-1].player_id == "unsigned"
    assert prospect.is_walkon and prospect.signed
    assert len({c.number for c in cards}) == 36
    assert fill_college_roster_gaps(rosters, [], 2027, rng) == {}


def test_recruit_metadata_survives_save_and_live_roster():
    r = generate_single_recruit("prospect", rng=random.Random(39))
    card = r.to_player_card("A")
    card.transfer_count = 1
    card.loyalty = .19
    restored = PlayerCard.from_dict(json.loads(json.dumps(card.to_dict())))
    final = player_to_card(card_to_player(restored), "A")
    for key in ("player_id", "original_stars", "transfer_count", "loyalty",
                "field_intelligence", "coachability", "gpa", "sat_score",
                "academic_risk", "work_rate"):
        assert getattr(final, key) == getattr(card, key)


def test_saved_neutral_coach_chemistry_not_backfilled():
    coach = generate_coaching_staff("A", rng=random.Random(7))["dc"]
    coach.standard = coach.growth = 50
    coach.leadership = coach.development = 71
    data = json.loads(json.dumps(coach.to_dict()))
    assert CoachCard.from_dict(data).to_dict() == data
