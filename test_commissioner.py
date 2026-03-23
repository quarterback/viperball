#!/usr/bin/env python3
"""
Commissioner Mode Tests
========================

Unit tests for PlayerCareerTracker, HallOfFame, and WVLCommissionerDynasty.
"""

import random
import pytest

from engine.player_career_tracker import PlayerCareerTracker, PlayerCareerRecord
from engine.hall_of_fame import HallOfFame, HallOfFameEntry
from engine.wvl_commissioner import (
    WVLCommissionerDynasty, create_commissioner_dynasty,
)


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def tracker():
    return PlayerCareerTracker()


@pytest.fixture
def hof():
    return HallOfFame()


def _make_career(
    name="Jane Doe",
    position="RB",
    nationality="USA",
    pro_seasons=0,
    yards_per_season=500,
    tds_per_season=5,
    peak_overall=80,
    status="active",
    caps=0,
    world_cups=0,
    awards=None,
):
    """Helper to build a PlayerCareerRecord with specified stats."""
    record = PlayerCareerRecord(
        player_id="test-001",
        full_name=name,
        position=position,
        nationality=nationality,
        peak_overall=peak_overall,
        career_status=status,
        international_caps=caps,
        world_cup_appearances=world_cups,
        career_awards=awards or [],
    )
    for i in range(pro_seasons):
        record.pro_seasons.append({
            "year": 2026 + i,
            "team_key": "arsenal",
            "team_name": "Arsenal",
            "tier": 1,
            "games": 20,
            "yards": yards_per_season,
            "tds": tds_per_season,
            "overall": peak_overall,
        })
    return record


# ═══════════════════════════════════════════════════════════════
# PLAYER CAREER TRACKER
# ═══════════════════════════════════════════════════════════════

class TestPlayerCareerTracker:

    def test_get_or_create_new(self, tracker):
        record = tracker.get_or_create("Jane Doe", position="QB")
        assert record.full_name == "Jane Doe"
        assert record.position == "QB"

    def test_get_or_create_existing(self, tracker):
        r1 = tracker.get_or_create("Jane Doe", position="QB")
        r2 = tracker.get_or_create("Jane Doe", position="RB")
        assert r1 is r2
        assert r1.position == "QB"  # first call wins

    def test_case_insensitive_lookup(self, tracker):
        r1 = tracker.get_or_create("Jane Doe")
        r2 = tracker.get_or_create("jane doe")
        assert r1 is r2

    def test_career_totals(self):
        record = _make_career(pro_seasons=5, yards_per_season=600, tds_per_season=8)
        assert record.career_pro_games == 100
        assert record.career_pro_yards == 3000
        assert record.career_pro_tds == 40
        assert record.career_pro_seasons_count == 5

    def test_pro_teams_summary(self):
        record = PlayerCareerRecord(
            player_id="x", full_name="Test Player", position="RB", nationality="USA",
        )
        record.pro_seasons = [
            {"year": 2026, "team_name": "Arsenal", "games": 20},
            {"year": 2027, "team_name": "Arsenal", "games": 20},
            {"year": 2028, "team_name": "Bayern Munich", "games": 20},
        ]
        record.career_status = "retired"
        summary = record.pro_teams_summary
        assert len(summary) == 2
        assert "Arsenal (2026-2027)" in summary[0]
        assert "Bayern Munich (2028-2028)" in summary[1]

    def test_pro_teams_summary_active(self):
        record = PlayerCareerRecord(
            player_id="x", full_name="Test Player", position="RB", nationality="USA",
        )
        record.pro_seasons = [
            {"year": 2026, "team_name": "Arsenal", "games": 20},
            {"year": 2027, "team_name": "Arsenal", "games": 20},
        ]
        record.career_status = "active"
        summary = record.pro_teams_summary
        assert "present" in summary[0]

    def test_record_wvl_season_stat_mapping(self, tracker):
        """Verify stats are matched by player name via composite key."""
        # Simulate the actual data format from ProLeagueSeason
        from dataclasses import dataclass

        @dataclass
        class FakeCard:
            first_name: str = "Jane"
            last_name: str = "Doe"
            player_id: str = "pid-001"
            position: str = "RB"
            nationality: str = "USA"
            overall: int = 85

            @property
            def full_name(self):
                return f"{self.first_name} {self.last_name}"

        card = FakeCard()
        team_rosters = {"arsenal": [card]}

        # Stats keyed by composite f"{team_key}_{player_name}" like pro_league.py does
        season_stats = {
            "arsenal": {
                "arsenal_Jane Doe": {
                    "name": "Jane Doe",
                    "team_key": "arsenal",
                    "games": 18,
                    "total_yards": 1200,
                    "rushing_yards": 900,
                    "kick_pass_yards": 300,
                    "touchdowns": 12,
                    "tackles": 5,
                },
            },
        }

        tracker.record_wvl_season(
            team_rosters=team_rosters,
            season_stats=season_stats,
            tier_assignments={"arsenal": 1},
            year=2026,
            team_names={"arsenal": "Arsenal"},
        )

        career = tracker.get_career("Jane Doe")
        assert career is not None
        assert len(career.pro_seasons) == 1
        s = career.pro_seasons[0]
        assert s["games"] == 18
        assert s["yards"] == 1200
        assert s["tds"] == 12
        assert s["rushing_yards"] == 900
        assert s["team_name"] == "Arsenal"

    def test_record_wvl_season_fallback_key(self, tracker):
        """Stats matched by stripping team_key prefix when 'name' field is missing."""
        from dataclasses import dataclass

        @dataclass
        class FakeCard:
            first_name: str = "Alice"
            last_name: str = "Smith"
            player_id: str = "pid-002"
            position: str = "QB"
            nationality: str = "CAN"
            overall: int = 78

            @property
            def full_name(self):
                return f"{self.first_name} {self.last_name}"

        card = FakeCard()

        # Stats without "name" field — should fall back to prefix stripping
        season_stats = {
            "bayern_munich": {
                "bayern_munich_Alice Smith": {
                    "games": 10,
                    "total_yards": 500,
                    "touchdowns": 4,
                },
            },
        }

        tracker.record_wvl_season(
            team_rosters={"bayern_munich": [card]},
            season_stats=season_stats,
            tier_assignments={"bayern_munich": 2},
            year=2027,
        )

        career = tracker.get_career("Alice Smith")
        assert career is not None
        assert career.pro_seasons[0]["yards"] == 500

    def test_record_retirement(self, tracker):
        tracker.get_or_create("Jane Doe")
        tracker.record_retirement("Jane Doe", 2030)
        career = tracker.get_career("Jane Doe")
        assert career.career_status == "retired"
        assert career.retirement_year == 2030

    def test_search_players(self, tracker):
        tracker.get_or_create("Jane Doe", position="RB", nationality="USA")
        tracker.get_or_create("John Smith", position="QB", nationality="CAN")
        tracker.get_or_create("Jane Smith", position="K", nationality="USA")

        results = tracker.search_players(query="Jane")
        assert len(results) == 2

        results = tracker.search_players(position="QB")
        assert len(results) == 1
        assert results[0].full_name == "John Smith"

        results = tracker.search_players(nationality="USA")
        assert len(results) == 2

    def test_get_all_time_leaders(self, tracker):
        # Manually add careers with known stats
        r1 = tracker.get_or_create("Player A")
        r1.pro_seasons = [{"games": 20, "yards": 1000, "tds": 10, "year": 2026}]
        r2 = tracker.get_or_create("Player B")
        r2.pro_seasons = [{"games": 20, "yards": 2000, "tds": 5, "year": 2026}]

        leaders = tracker.get_all_time_leaders("yards", limit=2)
        assert leaders[0]["record"].full_name == "Player B"
        assert leaders[0]["value"] == 2000

        td_leaders = tracker.get_all_time_leaders("tds", limit=2)
        assert td_leaders[0]["record"].full_name == "Player A"

    def test_serialization_round_trip(self, tracker):
        r = tracker.get_or_create("Jane Doe", position="RB", nationality="USA")
        r.pro_seasons.append({"year": 2026, "games": 20, "yards": 800, "tds": 6})
        r.peak_overall = 88

        data = tracker.to_dict()
        tracker2 = PlayerCareerTracker.from_dict(data)
        r2 = tracker2.get_career("Jane Doe")

        assert r2 is not None
        assert r2.position == "RB"
        assert r2.peak_overall == 88
        assert len(r2.pro_seasons) == 1
        assert r2.pro_seasons[0]["yards"] == 800

    def test_ingest_cvl_graduates(self, tracker):
        grads = [
            {
                "first_name": "Maria",
                "last_name": "Garcia",
                "player_id": "cvl-001",
                "position": "QB",
                "nationality": "Mexico",
                "graduating_from": "USC",
                "conference": "Pac-12",
                "college_prestige": 85,
                "ratings": {"overall": 82, "speed": 75, "power": 80},
            },
        ]
        tracker.ingest_cvl_graduates(grads, year=2026)

        career = tracker.get_career("Maria Garcia")
        assert career is not None
        assert career.college_team == "USC"
        assert career.pro_entry_year == 2026
        assert career.peak_overall == 82

    def test_record_fiv_cycle(self, tracker):
        tracker.get_or_create("Jane Doe", nationality="USA")

        stats = {
            "Jane Doe": {
                "nation": "USA",
                "caps": 6,
                "games": 6,
                "yards": 300,
                "tds": 3,
                "competition": "FIV World Cup",
                "world_cup": True,
            },
        }
        tracker.record_fiv_cycle(stats, year=2026)

        career = tracker.get_career("Jane Doe")
        assert career.international_caps == 6
        assert career.national_team == "USA"
        assert career.world_cup_appearances == 1
        assert len(career.international_seasons) == 1


# ═══════════════════════════════════════════════════════════════
# HALL OF FAME
# ═══════════════════════════════════════════════════════════════

class TestHallOfFame:

    def test_no_auto_induction_for_active(self, hof):
        career = _make_career(status="active", pro_seasons=10)
        assert hof.auto_evaluate(career) is None

    def test_auto_induction_two_criteria(self, hof):
        """Needs 2+ criteria met for auto-induction."""
        career = _make_career(
            status="retired",
            pro_seasons=8,       # criterion: 8+ seasons
            peak_overall=90,     # criterion: 90+ OVR
        )
        reason = hof.auto_evaluate(career)
        assert reason is not None
        assert "8+ pro seasons" in reason
        assert "90+ peak overall" in reason

    def test_no_auto_induction_one_criterion(self, hof):
        """Only 1 criterion met — should NOT auto-induct."""
        career = _make_career(
            status="retired",
            pro_seasons=8,       # only this criterion met
            peak_overall=70,     # not 90+
        )
        reason = hof.auto_evaluate(career)
        assert reason is None

    def test_auto_induction_yards(self, hof):
        """5000+ career yards criterion."""
        career = _make_career(
            status="retired",
            pro_seasons=8,                # criterion 1
            yards_per_season=700,         # 8 * 700 = 5600 > 5000 criterion 2
        )
        reason = hof.auto_evaluate(career)
        assert reason is not None
        assert "5000+ career yards" in reason

    def test_auto_induction_tds(self, hof):
        """50+ career TDs criterion."""
        career = _make_career(
            status="retired",
            pro_seasons=8,                # criterion 1
            tds_per_season=7,             # 8 * 7 = 56 > 50 criterion 2
        )
        reason = hof.auto_evaluate(career)
        assert reason is not None
        assert "50+ career TDs" in reason

    def test_auto_induction_awards(self, hof):
        career = _make_career(
            status="retired",
            pro_seasons=8,
            awards=["MVP", "All-Pro", "ROTY"],
        )
        reason = hof.auto_evaluate(career)
        assert reason is not None
        assert "3+ career awards" in reason

    def test_auto_induction_international(self, hof):
        career = _make_career(
            status="retired",
            pro_seasons=8,
            caps=15,
        )
        reason = hof.auto_evaluate(career)
        assert reason is not None
        assert "10+ international caps" in reason

    def test_auto_induction_world_cup(self, hof):
        career = _make_career(
            status="retired",
            pro_seasons=8,
            world_cups=1,
        )
        reason = hof.auto_evaluate(career)
        assert reason is not None
        assert "World Cup appearance" in reason

    def test_manual_induction(self, hof):
        career = _make_career(name="Star Player", status="active", pro_seasons=3)
        entry = hof.induct(career, year=2030, reason="Commissioner selection")

        assert entry.full_name == "Star Player"
        assert entry.induction_year == 2030
        assert entry.induction_reason == "Commissioner selection"
        assert career.career_status == "hall_of_fame"

    def test_no_duplicate_induction(self, hof):
        career = _make_career(
            status="retired", pro_seasons=10, peak_overall=95,
        )
        reason1 = hof.auto_evaluate(career)
        assert reason1 is not None
        hof.induct(career, year=2030, reason=reason1)

        # Second evaluation should return None (already inducted)
        reason2 = hof.auto_evaluate(career)
        assert reason2 is None

    def test_process_retirements(self, hof):
        tracker = PlayerCareerTracker()
        r1 = tracker.get_or_create("Great Player")
        r1.career_status = "retired"
        r1.peak_overall = 92
        r1.pro_seasons = [{"year": y, "games": 20, "yards": 700, "tds": 8}
                          for y in range(2026, 2034)]  # 8 seasons, 5600 yards, 64 TDs

        r2 = tracker.get_or_create("Average Player")
        r2.career_status = "retired"
        r2.pro_seasons = [{"year": 2026, "games": 10, "yards": 100, "tds": 1}]

        new_inductees = hof.process_retirements(
            ["Great Player", "Average Player"], tracker, year=2034,
        )
        assert len(new_inductees) == 1
        assert new_inductees[0].full_name == "Great Player"

    def test_get_inductees_sorted(self, hof):
        c1 = _make_career(name="Player A", status="retired", peak_overall=95, pro_seasons=10)
        c2 = _make_career(name="Player B", status="retired", peak_overall=88, pro_seasons=10)
        hof.induct(c1, year=2028)
        hof.induct(c2, year=2030)

        by_year = hof.get_inductees(sort_by="year")
        assert by_year[0].full_name == "Player B"  # 2030 > 2028

        by_ovr = hof.get_inductees(sort_by="overall")
        assert by_ovr[0].full_name == "Player A"  # 95 > 88

    def test_serialization_round_trip(self, hof):
        career = _make_career(name="Test Player", status="retired", pro_seasons=5)
        hof.induct(career, year=2030)

        data = hof.to_dict()
        hof2 = HallOfFame.from_dict(data)

        assert len(hof2.entries) == 1
        entry = hof2.get_entry("Test Player")
        assert entry is not None
        assert entry.induction_year == 2030


# ═══════════════════════════════════════════════════════════════
# WVL COMMISSIONER DYNASTY
# ═══════════════════════════════════════════════════════════════

class TestWVLCommissionerDynasty:

    def test_create_dynasty(self):
        d = create_commissioner_dynasty("Test", starting_year=2026)
        assert d.dynasty_name == "Test"
        assert d.current_year == 2026
        assert len(d.team_histories) == 64
        assert len(d.ai_team_owners) == 64

    def test_full_season_cycle(self):
        """Sim a full season, verify standings and career tracking."""
        d = create_commissioner_dynasty("Test", starting_year=2026)

        season = d.start_season()
        assert season is not None
        assert len(season.tier_seasons) == 4

        d.sim_full_season(use_fast_sim=True)
        d.advance_season(season)

        # Should have champions
        assert len(d.last_season_champions) > 0

        # Career tracker should have players
        assert len(d.career_tracker.careers) > 0

        # Stats should actually have non-zero values
        leaders = d.career_tracker.get_all_time_leaders("yards", limit=1)
        assert len(leaders) > 0
        assert leaders[0]["value"] > 0, "Yards should be > 0 after stat mapping fix"

    def test_offseason_advances_year(self):
        d = create_commissioner_dynasty("Test", starting_year=2026)
        season = d.start_season()
        d.sim_full_season(use_fast_sim=True)
        d.advance_season(season)

        rng = random.Random(42)
        d.run_offseason(season, rng=rng)
        assert d.current_year == 2027

    def test_move_player(self):
        d = create_commissioner_dynasty("Test", starting_year=2026)
        season = d.start_season()
        d.sim_full_season(use_fast_sim=True)
        d.advance_season(season)

        keys = list(d._team_rosters.keys())[:2]
        roster = d._team_rosters[keys[0]]
        assert len(roster) > 0

        player_name = roster[0].full_name
        original_len = len(roster)
        ok = d.move_player(player_name, keys[0], keys[1])

        assert ok is True
        assert len(d._team_rosters[keys[0]]) == original_len - 1

    def test_move_player_nonexistent(self):
        d = create_commissioner_dynasty("Test", starting_year=2026)
        season = d.start_season()
        d.sim_full_season(use_fast_sim=True)
        d.advance_season(season)

        keys = list(d._team_rosters.keys())[:2]
        ok = d.move_player("NONEXISTENT PLAYER", keys[0], keys[1])
        assert ok is False

    def test_nominate_hall_of_fame(self):
        d = create_commissioner_dynasty("Test", starting_year=2026)
        season = d.start_season()
        d.sim_full_season(use_fast_sim=True)
        d.advance_season(season)

        leaders = d.career_tracker.get_all_time_leaders("yards", limit=1)
        assert len(leaders) > 0
        name = leaders[0]["record"].full_name

        entry = d.nominate_hall_of_fame(name)
        assert entry is not None
        assert entry["full_name"] == name

        # Should be in HoF now
        assert d.hall_of_fame.get_entry(name) is not None

    def test_nominate_nonexistent_player(self):
        d = create_commissioner_dynasty("Test", starting_year=2026)
        result = d.nominate_hall_of_fame("Nobody McFakerson")
        assert result is None

    def test_serialization_round_trip(self):
        d = create_commissioner_dynasty("Test", starting_year=2026)
        season = d.start_season()
        d.sim_full_season(use_fast_sim=True)
        d.advance_season(season)

        data = d.to_dict()
        d2 = WVLCommissionerDynasty.from_dict(data)

        assert d2.dynasty_name == "Test"
        assert d2.current_year == d.current_year
        assert len(d2.team_histories) == 64
        assert len(d2.career_tracker.careers) == len(d.career_tracker.careers)

    def test_get_team_roster(self):
        d = create_commissioner_dynasty("Test", starting_year=2026)
        season = d.start_season()
        d.sim_full_season(use_fast_sim=True)
        d.advance_season(season)

        keys = list(d._team_rosters.keys())
        roster = d.get_team_roster(keys[0])
        assert len(roster) > 0
        assert "name" in roster[0]
        assert "position" in roster[0]
        assert "overall" in roster[0]

    def test_add_nation(self):
        d = create_commissioner_dynasty("Test", starting_year=2026)
        d.add_nation("TST", "Testland", "EVV", tier="developing")
        assert len(d.custom_nations) == 1
        assert d.custom_nations[0]["code"] == "TST"

    def test_fiv_cycle(self):
        """FIV cycle runs without crashing and records results."""
        d = create_commissioner_dynasty("Test", starting_year=2026)
        season = d.start_season()
        d.sim_full_season(use_fast_sim=True)
        d.advance_season(season)

        result = d.run_fiv_cycle(host="USA", rng=random.Random(42))
        assert "error" not in result
        assert result.get("champion") is not None
        assert len(d.fiv_history) == 1

        # Check international caps were recorded
        caps_leaders = d.career_tracker.get_all_time_leaders("caps", limit=1)
        assert len(caps_leaders) > 0
        assert caps_leaders[0]["value"] > 0

    def test_multi_season(self):
        """Two full seasons maintain continuity."""
        d = create_commissioner_dynasty("Test", starting_year=2026)

        # Season 1
        s1 = d.start_season()
        d.sim_full_season(use_fast_sim=True)
        d.advance_season(s1)
        d.run_offseason(s1, rng=random.Random(1))

        players_after_s1 = len(d.career_tracker.careers)

        # Season 2
        s2 = d.start_season()
        d.sim_full_season(use_fast_sim=True)
        d.advance_season(s2)

        assert d.current_year == 2027  # started 2026, offseason bumped to 2027, season 2 played but no offseason yet
        assert len(d.career_tracker.careers) >= players_after_s1

        # Players who played both seasons should have 2 season entries
        leaders = d.career_tracker.get_all_time_leaders("seasons", limit=1)
        # Note: some players may have been generated fresh each season
        # so we just verify the tracker kept growing
        assert leaders[0]["value"] >= 1


# ═══════════════════════════════════════════════════════════════
# DB PERSISTENCE
# ═══════════════════════════════════════════════════════════════

class TestDBPersistence:

    def test_save_and_load_commissioner_dynasty(self):
        from engine.db import save_commissioner_dynasty, load_commissioner_dynasty

        d = create_commissioner_dynasty("DB Test", starting_year=2026)
        save_commissioner_dynasty(d, save_key="pytest_test")

        loaded = load_commissioner_dynasty(save_key="pytest_test")
        assert loaded is not None
        assert loaded.dynasty_name == "DB Test"
        assert loaded.current_year == 2026

        # Cleanup
        from engine.db import delete_commissioner_dynasty
        delete_commissioner_dynasty(save_key="pytest_test")

    def test_save_and_load_hof_entry(self):
        from engine.db import save_hall_of_fame_entry, load_hall_of_fame

        entry = {
            "player_id": "test-hof",
            "full_name": "Test HoFer",
            "position": "QB",
            "nationality": "USA",
            "induction_year": 2030,
            "induction_reason": "test",
            "peak_overall": 95,
        }
        save_hall_of_fame_entry(entry, "test-hof-key")

        all_entries = load_hall_of_fame()
        found = [e for e in all_entries if e.get("full_name") == "Test HoFer"]
        assert len(found) >= 1

        # Cleanup
        from engine.db import delete_blob
        delete_blob("hall_of_fame", "test-hof-key")
