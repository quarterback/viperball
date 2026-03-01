#!/usr/bin/env python3
"""
WVL Integration Tests
======================

Tests for the Women's Viperball League (Galactic Premiership) system.
"""

import json
import os
import random
import tempfile
import pytest

from engine.wvl_config import (
    ALL_CLUBS, CLUBS_BY_KEY, CLUBS_BY_TIER, ALL_WVL_TIERS,
    TIER_BY_NUMBER, RIVALRIES, get_default_tier_assignments,
    get_rival_teams, is_rivalry_match,
)
from engine.wvl_owner import (
    OWNER_ARCHETYPES, PRESIDENT_ARCHETYPES,
    ClubOwner, TeamPresident, InvestmentAllocation,
    generate_president_pool, apply_investment_boosts,
    compute_season_revenue, compute_season_expenses, compute_financials,
)
from engine.wvl_free_agency import (
    generate_synthetic_fa_pool, run_free_agency,
    compute_fa_attractiveness, process_retirements, apply_roster_cuts,
)
from engine.promotion_relegation import (
    compute_tier_movements, PromotionRelegationResult,
    persist_tier_assignments, load_tier_assignments,
)
from engine.development import apply_pro_development, should_retire
from engine.player_card import PlayerCard
from engine.wvl_dynasty import create_wvl_dynasty, WVLDynasty


# ═══════════════════════════════════════════════════════════════
# CONFIG TESTS
# ═══════════════════════════════════════════════════════════════

class TestWVLConfig:
    def test_total_teams(self):
        assert len(ALL_CLUBS) == 64

    def test_tier_counts(self):
        assert len(CLUBS_BY_TIER[1]) == 18
        assert len(CLUBS_BY_TIER[2]) == 20
        assert len(CLUBS_BY_TIER[3]) == 13
        assert len(CLUBS_BY_TIER[4]) == 13

    def test_unique_keys(self):
        keys = [c.key for c in ALL_CLUBS]
        assert len(keys) == len(set(keys)), "Duplicate club keys found"

    def test_all_tiers_have_configs(self):
        for i in range(1, 5):
            assert i in TIER_BY_NUMBER

    def test_season_lengths(self):
        assert TIER_BY_NUMBER[1].games_per_season == 34
        assert TIER_BY_NUMBER[2].games_per_season == 38
        assert TIER_BY_NUMBER[3].games_per_season == 24
        assert TIER_BY_NUMBER[4].games_per_season == 24

    def test_rivalries_exist(self):
        assert len(RIVALRIES) >= 13

    def test_rivalry_lookup(self):
        assert is_rivalry_match("real_madrid", "fc_barcelona") == "El Clásico"
        assert is_rivalry_match("celtic", "rangers") == "Old Firm"
        assert is_rivalry_match("real_madrid", "liverpool") is None

    def test_rival_teams(self):
        rivals = get_rival_teams("ac_milan")
        assert "inter_milan" in rivals

    def test_default_tier_assignments(self):
        assignments = get_default_tier_assignments()
        assert len(assignments) == 64
        assert assignments["real_madrid"] == 1
        assert assignments["vimpeli"] == 4

    def test_narrative_tags(self):
        assert CLUBS_BY_KEY["wrexham"].narrative_tag == "vanity_project"
        assert CLUBS_BY_KEY["portland"].narrative_tag == "american_outpost"
        assert CLUBS_BY_KEY["vimpeli"].narrative_tag == "cinderella"


# ═══════════════════════════════════════════════════════════════
# OWNER TESTS
# ═══════════════════════════════════════════════════════════════

class TestOwnerMode:
    def test_owner_archetypes_exist(self):
        assert len(OWNER_ARCHETYPES) >= 7
        for key, arch in OWNER_ARCHETYPES.items():
            assert "starting_bankroll" in arch
            assert "patience_threshold" in arch

    def test_president_archetypes_exist(self):
        assert len(PRESIDENT_ARCHETYPES) >= 6
        for key, arch in PRESIDENT_ARCHETYPES.items():
            assert "acumen_range" in arch
            assert "coaching_style_bias" in arch

    def test_generate_president_pool(self):
        pool = generate_president_pool(5, random.Random(42))
        assert len(pool) == 5
        for p in pool:
            assert 0 <= p.acumen <= 100
            assert p.contract_years >= 2

    def test_owner_serialization(self):
        owner = ClubOwner(
            name="Test Owner",
            archetype="sugar_daddy",
            club_key="wrexham",
            bankroll=80.0,
        )
        d = owner.to_dict()
        restored = ClubOwner.from_dict(d)
        assert restored.name == "Test Owner"
        assert restored.bankroll == 80.0

    def test_investment_allocation(self):
        inv = InvestmentAllocation(training=0.3, coaching=0.2, stadium=0.2, youth=0.1, science=0.1, marketing=0.1)
        assert abs(inv.total - 1.0) < 0.01

    def test_season_revenue(self):
        rev = compute_season_revenue(tier=1, wins=25, losses=9)
        assert rev > 0
        # Tier 1 should generate more than Tier 4
        rev4 = compute_season_revenue(tier=4, wins=10, losses=14)
        assert rev > rev4


# ═══════════════════════════════════════════════════════════════
# FREE AGENCY TESTS
# ═══════════════════════════════════════════════════════════════

class TestFreeAgency:
    def test_synthetic_pool_generation(self):
        pool = generate_synthetic_fa_pool(50, random.Random(42))
        assert len(pool) == 50
        for fa in pool:
            assert fa.player_card.age is not None
            assert fa.player_card.pro_status == "free_agent"
            assert 40 <= fa.player_card.overall <= 99

    def test_fa_attractiveness(self):
        score_t1 = compute_fa_attractiveness(tier=1, recent_wins=20, total_games=34, prestige=90)
        score_t4 = compute_fa_attractiveness(tier=4, recent_wins=5, total_games=24, prestige=40)
        assert score_t1 > score_t4

    def test_run_free_agency(self):
        rng = random.Random(42)
        pool = generate_synthetic_fa_pool(30, rng)

        # Create minimal team rosters
        team_rosters = {"team_a": [], "team_b": []}
        team_attractiveness = {"team_a": 70, "team_b": 40}
        team_budgets = {"team_a": 10, "team_b": 5}

        result = run_free_agency(
            pool=pool,
            team_rosters=team_rosters,
            team_attractiveness=team_attractiveness,
            team_budgets=team_budgets,
            rng=rng,
        )
        assert len(result.signings) > 0

    def test_owner_targeted_fa(self):
        rng = random.Random(42)
        pool = generate_synthetic_fa_pool(20, rng)
        target_name = pool[0].player_card.full_name

        team_rosters = {"owner_team": [], "other_team": []}
        result = run_free_agency(
            pool=pool,
            team_rosters=team_rosters,
            team_attractiveness={"owner_team": 50, "other_team": 50},
            team_budgets={"owner_team": 10, "other_team": 10},
            owner_club_key="owner_team",
            owner_targeted_fa_name=target_name,
            rng=rng,
        )
        assert result.owner_targeted_signing is not None
        assert result.owner_targeted_signing["player_name"] == target_name


# ═══════════════════════════════════════════════════════════════
# PRO DEVELOPMENT TESTS
# ═══════════════════════════════════════════════════════════════

class TestProDevelopment:
    def _make_card(self, age: int, **kwargs) -> PlayerCard:
        defaults = dict(
            player_id="test", first_name="Test", last_name="Player",
            number=10, position="Viper", archetype="hybrid_viper",
            nationality="English", hometown_city="London",
            hometown_state="ENG", hometown_country="England",
            high_school="", height="5-10", weight=170, year="Veteran",
            speed=75, stamina=75, agility=75, power=75, awareness=75,
            hands=75, kicking=75, kick_power=75, kick_accuracy=75,
            lateral_skill=75, tackling=75, potential=3, development="normal",
            age=age, pro_status="active",
        )
        defaults.update(kwargs)
        return PlayerCard(**defaults)

    def test_young_player_growth(self):
        card = self._make_card(age=21)
        rng = random.Random(42)
        event = apply_pro_development(card, rng)
        assert card.age == 22
        # Young players should generally improve
        # (not guaranteed per-instance, but age curve is positive)

    def test_old_player_decline(self):
        card = self._make_card(age=34, speed=70, stamina=70, agility=70)
        rng = random.Random(42)
        original_speed = card.speed
        apply_pro_development(card, rng)
        assert card.age == 35
        # Sharp decline at 34+ means speed should drop
        assert card.speed <= original_speed

    def test_retirement_old(self):
        card = self._make_card(age=38)
        assert should_retire(card) is True

    def test_no_retirement_young(self):
        card = self._make_card(age=25)
        assert should_retire(card) is False


# ═══════════════════════════════════════════════════════════════
# PROMOTION/RELEGATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestPromotionRelegation:
    def _make_standings(self, tier: int, count: int) -> list:
        """Generate fake standings for a tier."""
        teams = []
        for i in range(count):
            teams.append({
                "team_key": f"t{tier}_{i}",
                "team_name": f"Team {tier}-{i}",
                "wins": count - i,  # best team first
                "losses": i,
                "points_for": (count - i) * 25,
                "points_against": i * 20,
            })
        return teams

    def test_tier1_tier2_movements(self):
        rng = random.Random(42)
        tier_standings = {
            1: self._make_standings(1, 18),
            2: self._make_standings(2, 20),
            3: self._make_standings(3, 13),
            4: self._make_standings(4, 13),
        }
        assignments = {}
        for tier, standings in tier_standings.items():
            for team in standings:
                assignments[team["team_key"]] = tier

        result = compute_tier_movements(tier_standings, assignments, teams={}, rng=rng)
        assert len(result.movements) > 0

        # Check auto-relegation from T1
        relegated_from_t1 = [m for m in result.movements if m.from_tier == 1 and m.reason == "auto_relegated"]
        assert len(relegated_from_t1) >= 2  # Bottom 2 auto-relegated (16th goes to playoff)

        # Check auto-promotion from T2
        promoted_from_t2 = [m for m in result.movements if m.from_tier == 2 and m.reason == "auto_promoted"]
        assert len(promoted_from_t2) == 2

    def test_tier3_tier4_no_playoff(self):
        rng = random.Random(42)
        tier_standings = {
            3: self._make_standings(3, 13),
            4: self._make_standings(4, 13),
        }
        # Only process T3↔T4 boundary
        assignments = {}
        for tier, standings in tier_standings.items():
            for team in standings:
                assignments[team["team_key"]] = tier

        result = compute_tier_movements(tier_standings, assignments, teams={}, rng=rng)

        # No playoffs for T3↔T4
        t3_t4_playoffs = [p for p in result.playoffs if p.higher_tier == 3]
        assert len(t3_t4_playoffs) == 0

    def test_tier_assignments_persist(self):
        assignments = {"team_a": 1, "team_b": 2}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            persist_tier_assignments(assignments, filepath)
            loaded = load_tier_assignments(filepath)
            assert loaded == assignments
        finally:
            os.unlink(filepath)


# ═══════════════════════════════════════════════════════════════
# DYNASTY TESTS
# ═══════════════════════════════════════════════════════════════

class TestWVLDynasty:
    def test_create_dynasty(self):
        dynasty = create_wvl_dynasty(
            dynasty_name="Test WVL",
            owner_name="Test Owner",
            owner_archetype="underdog_dreamer",
            club_key="vimpeli",
        )
        assert dynasty.owner.name == "Test Owner"
        assert dynasty.owner.club_key == "vimpeli"
        assert dynasty.owner.bankroll == 25.0  # underdog dreamer
        assert len(dynasty.tier_assignments) == 64

    def test_save_load_roundtrip(self):
        dynasty = create_wvl_dynasty(
            dynasty_name="Roundtrip Test",
            owner_name="Test",
            owner_archetype="patient_builder",
            club_key="wrexham",
        )
        dynasty.current_year = 2028
        dynasty.owner.bankroll = 42.5

        pool = generate_president_pool(1, random.Random(42))
        dynasty.president = pool[0]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            dynasty.save(filepath)
            loaded = WVLDynasty.load(filepath)

            assert loaded.dynasty_name == "Roundtrip Test"
            assert loaded.current_year == 2028
            assert loaded.owner.bankroll == 42.5
            assert loaded.owner.club_key == "wrexham"
            assert loaded.president is not None
            assert loaded.president.name == dynasty.president.name
            assert len(loaded.tier_assignments) == 64
        finally:
            os.unlink(filepath)


# ═══════════════════════════════════════════════════════════════
# PLAYER CARD PRO FIELDS TESTS
# ═══════════════════════════════════════════════════════════════

class TestPlayerCardProFields:
    def test_pro_fields_default_none(self):
        card = PlayerCard(
            player_id="test", first_name="A", last_name="B",
            number=1, position="Viper", archetype="hybrid_viper",
            nationality="English", hometown_city="", hometown_state="",
            hometown_country="England", high_school="", height="5-10",
            weight=170, year="Sophomore",
            speed=75, stamina=75, agility=75, power=75, awareness=75,
            hands=75, kicking=75, kick_power=75, kick_accuracy=75,
            lateral_skill=75, tackling=75, potential=3, development="normal",
        )
        assert card.age is None
        assert card.pro_team is None
        assert card.contract_years is None

    def test_pro_fields_serialization(self):
        card = PlayerCard(
            player_id="pro_test", first_name="Pro", last_name="Player",
            number=10, position="Viper", archetype="hybrid_viper",
            nationality="Spanish", hometown_city="Madrid",
            hometown_state="ESP", hometown_country="Spain",
            high_school="", height="5-8", weight=155, year="Veteran",
            speed=85, stamina=80, agility=82, power=70, awareness=78,
            hands=80, kicking=75, kick_power=72, kick_accuracy=74,
            lateral_skill=83, tackling=68, potential=4, development="normal",
            age=25, pro_team="real_madrid", contract_years=3,
            contract_salary=4, pro_status="active",
        )
        d = card.to_dict()
        assert d["age"] == 25
        assert d["pro_team"] == "real_madrid"
        assert d["pro_status"] == "active"

        restored = PlayerCard.from_dict(d)
        assert restored.age == 25
        assert restored.pro_team == "real_madrid"
        assert restored.contract_salary == 4


# ═══════════════════════════════════════════════════════════════
# TEAM DATA TESTS
# ═══════════════════════════════════════════════════════════════

class TestTeamData:
    def test_team_files_exist(self):
        """Check that the generated team files exist."""
        from pathlib import Path
        base = Path(__file__).parent / "data" / "wvl_teams"
        for tier_num in [1, 2, 3, 4]:
            tier_dir = base / f"tier{tier_num}"
            clubs = CLUBS_BY_TIER[tier_num]
            for club in clubs:
                filepath = tier_dir / f"{club.key}.json"
                assert filepath.exists(), f"Missing: {filepath}"

    def test_team_file_format(self):
        """Check that team files have the correct format."""
        from pathlib import Path
        filepath = Path(__file__).parent / "data" / "wvl_teams" / "tier1" / "real_madrid.json"
        with open(filepath) as f:
            data = json.load(f)

        assert "team_info" in data
        assert "style" in data
        assert "prestige" in data
        assert "roster" in data
        assert data["roster"]["size"] == 36
        assert len(data["roster"]["players"]) == 36

        # Check player format
        player = data["roster"]["players"][0]
        assert "name" in player
        assert "position" in player
        assert "stats" in player
        assert "age" in player

    def test_tier_assignments_file(self):
        from pathlib import Path
        filepath = Path(__file__).parent / "data" / "wvl_tier_assignments.json"
        assert filepath.exists()
        with open(filepath) as f:
            assignments = json.load(f)
        assert len(assignments) == 64


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
