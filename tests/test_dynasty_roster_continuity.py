"""Regression tests for dynasty roster and high-school cohort continuity."""
import json
import random
from types import SimpleNamespace

import pytest

from engine.db import serialize_dynasty, deserialize_dynasty
from engine.dynasty import create_dynasty
from engine.recruiting import HSRecruitingPipeline, generate_recruit_class
from engine.roster_continuity import restore_finalized_rosters


def test_hs_cohort_ids_survive_save_and_do_not_repeat():
    pipeline = HSRecruitingPipeline()
    pipeline.generate_initial_pipeline(base_seed=2026, size_per_class=8)
    first = {p.recruit.recruit_id for p in pipeline.classes["9th"]}
    assert all(pid.startswith("HS-2030-") for pid in first)
    # The public bridge representation remains the existing flat grade map.
    assert set(pipeline.to_dict()) == {"9th", "10th", "11th", "12th"}
    seen = set()
    for i in range(7):
        saved = json.loads(json.dumps(pipeline.save_state()))
        pipeline = HSRecruitingPipeline.from_save_state(saved)
        assert pipeline.save_state() == saved
        assert len({p.recruit.recruit_id for ps in pipeline.classes.values()
                    for p in ps}) == 32
        # Repeat the same random seed to prove IDs depend on cohort sequence,
        # not a random stream or a new grade label.
        graduates = pipeline.advance_year(new_9th_seed=2027, size=8,
                                         rng=random.Random(100 + i))
        graduated = {p.recruit.recruit_id for p in graduates}
        assert len(graduated) == 8
        assert not (seen & graduated)
        if i == 3:
            assert graduated == first
        seen.update(graduated)


def test_dynasty_database_roundtrip_keeps_pipeline():
    dynasty = create_dynasty("Continuity", "Coach", "School", starting_year=2026)
    dynasty._hs_pipeline = HSRecruitingPipeline()
    dynasty._hs_pipeline.generate_initial_pipeline(base_seed=2026, size_per_class=8)
    dynasty._hs_pipeline.advance_year(new_9th_seed=2027, size=8)
    saved = json.loads(json.dumps(serialize_dynasty(dynasty)))
    restored = deserialize_dynasty(saved)
    assert restored._hs_pipeline.save_state() == dynasty._hs_pipeline.save_state()
    # Older saves are still readable and use the existing lazy setup path.
    saved.pop("hs_pipeline_state")
    assert deserialize_dynasty(saved)._hs_pipeline is None


def _card():
    return generate_recruit_class(year=2027, size=1)[0].to_player_card("School").to_dict()


def test_roster_restore_preserves_entries_and_does_not_rewrite_legacy_ids():
    card = _card()
    team = SimpleNamespace(players=["old"])
    restore_finalized_rosters({"School": team}, {"School": [card]})
    assert len(team.players) == 1
    assert team.players[0].player_id == card["player_id"]
    assert team.players[0].name == card["first_name"] + " " + card["last_name"]


def test_invalid_saved_roster_does_not_partially_replace_other_team():
    first = SimpleNamespace(players=["first old"])
    second = SimpleNamespace(players=["second old"])
    with pytest.raises(ValueError, match="Second"):
        restore_finalized_rosters(
            {"First": first, "Second": second},
            {"First": [_card()], "Second": [None]},
        )
    assert first.players == ["first old"]
    assert second.players == ["second old"]
