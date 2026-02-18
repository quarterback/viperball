#!/usr/bin/env python3
"""
Test suite for the Viperball Recruiting, Transfer Portal, and NIL systems.

Tests:
1. Recruit generation and class composition
2. Scouting mechanics (basic / full)
3. Recruiting board operations (scout, offer, commit)
4. Transfer portal population and resolution
5. Quick portal for one-off season mode
6. NIL budget generation, allocation, and deals
7. Retention risk assessment
8. Full recruiting cycle integration
9. Dynasty offseason integration
"""

import random
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from engine.recruiting import (
    generate_recruit_class,
    generate_single_recruit,
    scout_recruit,
    RecruitingBoard,
    Recruit,
    run_full_recruiting_cycle,
    auto_recruit_team,
)
from engine.transfer_portal import (
    TransferPortal,
    PortalEntry,
    populate_portal,
    generate_quick_portal,
    auto_portal_offers,
)
from engine.nil_system import (
    NILProgram,
    generate_nil_budget,
    auto_nil_program,
    compute_team_prestige,
    estimate_market_tier,
    assess_retention_risks,
)
from engine.player_card import PlayerCard


def divider(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ──────────────────────────────────────────────
# TEST 1: Recruit Generation
# ──────────────────────────────────────────────

def test_recruit_generation():
    divider("TEST 1: Recruit Generation")

    rng = random.Random(42)
    pool = generate_recruit_class(year=2027, size=300, rng=rng)

    print(f"  Generated {len(pool)} recruits")
    assert len(pool) == 300, f"Expected 300, got {len(pool)}"

    # Check star distribution is reasonable
    star_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in pool:
        star_counts[r.stars] += 1

    print(f"  Star distribution: {star_counts}")
    assert star_counts[5] > 0, "Should have at least one 5-star"
    assert star_counts[5] < star_counts[3], "5-stars should be rarer than 3-stars"

    # Check pool is sorted by stars descending
    for i in range(len(pool) - 1):
        assert pool[i].stars >= pool[i + 1].stars or (
            pool[i].stars == pool[i + 1].stars
        ), "Pool should be sorted by stars descending"

    # Verify recruit attributes are in valid range
    sample = pool[0]
    print(f"\n  Top recruit: {sample.full_name}")
    print(f"    Position: {sample.position}")
    print(f"    Stars: {sample.stars}")
    print(f"    True Overall: {sample.true_overall}")
    print(f"    Region: {sample.region}")
    print(f"    Hometown: {sample.hometown}")

    assert 40 <= sample.true_overall <= 99, f"Overall out of range: {sample.true_overall}"
    assert 1 <= sample.stars <= 5, f"Stars out of range: {sample.stars}"
    assert sample.first_name, "First name should not be empty"
    assert sample.last_name, "Last name should not be empty"

    print("  ✓ Recruit generation passed")


# ──────────────────────────────────────────────
# TEST 2: Scouting
# ──────────────────────────────────────────────

def test_scouting():
    divider("TEST 2: Scouting Mechanics")

    rng = random.Random(123)
    recruit = generate_single_recruit(recruit_id="TEST-001", stars=4, rng=rng)

    # Before scouting
    visible = recruit.get_visible_attrs()
    assert "scouted" not in visible, "Should not have scouted data initially"
    assert recruit.scout_level == "none"
    print(f"  Before scout: {visible['name']} ({visible['stars']}★)")

    # Basic scout
    basic_result = scout_recruit(recruit, level="basic", rng=rng)
    assert recruit.scout_level == "basic"
    assert "scouted" in basic_result
    assert len(basic_result["scouted"]) == 3, "Basic scout should reveal 3 attributes"
    assert "potential_range" in basic_result
    print(f"  After basic scout: {basic_result['scouted']}")
    print(f"  Potential range: {basic_result['potential_range']}")

    # Full scout
    full_result = scout_recruit(recruit, level="full", rng=rng)
    assert recruit.scout_level == "full"
    assert len(full_result["scouted"]) == 11, "Full scout should reveal all 11 attributes"
    assert "potential" in full_result
    assert "development" in full_result
    assert "true_overall" in full_result
    print(f"  After full scout: OVR {full_result['true_overall']}, "
          f"Potential {full_result['potential']}★, Dev: {full_result['development']}")

    print("  ✓ Scouting passed")


# ──────────────────────────────────────────────
# TEST 3: Recruiting Board
# ──────────────────────────────────────────────

def test_recruiting_board():
    divider("TEST 3: Recruiting Board Operations")

    rng = random.Random(77)
    pool = generate_recruit_class(year=2027, size=50, rng=rng)

    board = RecruitingBoard(
        team_name="Gonzaga",
        scholarships_available=8,
        scouting_points=10,
    )

    # Scouting
    assert board.can_scout("basic"), "Should be able to basic scout"
    result = board.scout(pool[0], level="basic", rng=rng)
    assert result is not None, "Scout should return data"
    assert board.scouting_points == 9, "Should have spent 1 point"
    assert pool[0].recruit_id in board.watchlist

    result = board.scout(pool[1], level="full", rng=rng)
    assert board.scouting_points == 6, "Full scout costs 3 points"
    print(f"  Scouted 2 players (remaining points: {board.scouting_points})")

    # Offering
    assert board.offer(pool[0]), "Should be able to offer"
    assert board.offer(pool[1]), "Should be able to offer second recruit"
    assert not board.offer(pool[0]), "Should not double-offer"
    assert "Gonzaga" in pool[0].offers
    assert len(board.offered) == 2
    print(f"  Made {len(board.offered)} offers")

    # Withdraw
    assert board.withdraw_offer(pool[1])
    assert len(board.offered) == 1
    assert "Gonzaga" not in pool[1].offers
    print(f"  Withdrew offer, now {len(board.offered)} offers")

    # Serialisation
    board_dict = board.to_dict()
    assert board_dict["team_name"] == "Gonzaga"
    assert len(board_dict["offered"]) == 1

    print("  ✓ Recruiting board passed")


# ──────────────────────────────────────────────
# TEST 4: Transfer Portal (Dynasty)
# ──────────────────────────────────────────────

def test_transfer_portal_dynasty():
    divider("TEST 4: Transfer Portal (Dynasty Mode)")

    rng = random.Random(42)

    # Create some mock rosters
    def make_card(name, pos, year, ovr_base=75, team="Team A"):
        return PlayerCard(
            player_id=f"P-{name.replace(' ', '-')}",
            first_name=name.split()[0],
            last_name=name.split()[-1],
            number=rng.randint(1, 99),
            position=pos,
            archetype="none",
            nationality="American",
            hometown_city="Anytown",
            hometown_state="CA",
            hometown_country="USA",
            high_school="Anytown HS",
            height="5-10",
            weight=170,
            year=year,
            speed=ovr_base + rng.randint(-5, 5),
            stamina=ovr_base + rng.randint(-5, 5),
            agility=ovr_base + rng.randint(-5, 5),
            power=ovr_base + rng.randint(-5, 5),
            awareness=ovr_base + rng.randint(-5, 5),
            hands=ovr_base + rng.randint(-5, 5),
            kicking=ovr_base + rng.randint(-5, 5),
            kick_power=ovr_base + rng.randint(-5, 5),
            kick_accuracy=ovr_base + rng.randint(-5, 5),
            lateral_skill=ovr_base + rng.randint(-5, 5),
            tackling=ovr_base + rng.randint(-5, 5),
            potential=rng.randint(2, 5),
            development="normal",
            current_team=team,
        )

    teams = {
        "Team A": [
            make_card("Alice Johnson", "Viper/Back", "Senior", 85, "Team A"),
            make_card("Beth Smith", "Halfback/Back", "Junior", 78, "Team A"),
            make_card("Cora Davis", "Lineman", "Graduate", 80, "Team A"),
            make_card("Diana Brown", "Zeroback/Back", "Sophomore", 72, "Team A"),
        ],
        "Team B": [
            make_card("Eve Wilson", "Viper/Back", "Junior", 82, "Team B"),
            make_card("Faye Clark", "Back/Safety", "Graduate", 77, "Team B"),
            make_card("Gina Lee", "Wingback/End", "Senior", 75, "Team B"),
            make_card("Hana Kim", "Halfback/Back", "Sophomore", 70, "Team B"),
        ],
    }

    records = {"Team A": (8, 4), "Team B": (3, 9)}

    portal = TransferPortal(year=2027)
    entries = populate_portal(portal, teams, records, rng=rng)

    print(f"  Portal entries: {len(entries)}")
    for e in entries:
        print(f"    {e.player_name} ({e.position}, OVR {e.overall}) "
              f"from {e.origin_team} — {e.reason}")

    # Make offers
    available = portal.get_available()
    if available:
        portal.make_offer("Team A", available[0], nil_amount=50_000)
        portal.make_offer("Team B", available[0], nil_amount=30_000)
        print(f"\n  Offers on {available[0].player_name}: {available[0].offers}")

    # Resolve
    prestige = {"Team A": 75, "Team B": 40}
    regions = {"Team A": "west_coast", "Team B": "midwest"}
    result = portal.resolve_all(prestige, regions, rng=rng)

    for team, entries_list in result.items():
        for e in entries_list:
            print(f"  Transfer: {e.player_name} → {team}")

    summary = portal.get_class_summary()
    print(f"\n  Total transfers completed: {len(summary)}")
    print("  ✓ Transfer portal (dynasty) passed")


# ──────────────────────────────────────────────
# TEST 5: Quick Portal (One-Off Season)
# ──────────────────────────────────────────────

def test_quick_portal():
    divider("TEST 5: Quick Portal (One-Off Season Mode)")

    rng = random.Random(99)
    team_names = ["Alpha Uni", "Beta College", "Gamma State"]

    portal = generate_quick_portal(team_names, year=2027, size=40, rng=rng)

    print(f"  Quick portal generated: {len(portal.entries)} players")
    assert len(portal.entries) == 40

    # Check portal is sorted by overall
    overalls = [e.overall for e in portal.entries]
    assert overalls == sorted(overalls, reverse=True), "Should be sorted by OVR descending"

    # Show top 5
    for e in portal.entries[:5]:
        print(f"    {e.player_name:20s} {e.position:16s} OVR {e.overall:2d}  "
              f"{e.player_card.year:10s} from {e.origin_team}")

    # Test instant commit
    success = portal.instant_commit("Alpha Uni", portal.entries[0])
    assert success, "Instant commit should succeed"
    assert portal.entries[0].committed_to == "Alpha Uni"
    print(f"\n  Instant commit: {portal.entries[0].player_name} → Alpha Uni")

    # Can't commit same player again
    assert not portal.instant_commit("Beta College", portal.entries[0])

    # Available should be 39 now
    assert len(portal.get_available()) == 39

    # Filter by position
    vipers = portal.get_by_position("Viper")
    print(f"  Vipers available: {len(vipers)}")

    # Filter by overall
    elite = portal.get_by_overall(min_ovr=80)
    print(f"  Players OVR 80+: {len(elite)}")

    print("  ✓ Quick portal passed")


# ──────────────────────────────────────────────
# TEST 6: NIL System
# ──────────────────────────────────────────────

def test_nil_system():
    divider("TEST 6: NIL Budget, Allocation, and Deals")

    rng = random.Random(42)

    # Budget generation
    budget_high = generate_nil_budget(prestige=90, market="mega", previous_season_wins=12, championship=True, rng=rng)
    budget_low = generate_nil_budget(prestige=30, market="small", previous_season_wins=3, rng=rng)

    print(f"  High-prestige budget: ${budget_high:,.0f}")
    print(f"  Low-prestige budget:  ${budget_low:,.0f}")
    assert budget_high > budget_low, "High prestige should get more money"
    assert budget_high > 0 and budget_low > 0, "Budgets should be positive"

    # NIL Program
    program = NILProgram(team_name="Gonzaga", annual_budget=1_000_000)
    print(f"\n  Budget: ${program.annual_budget:,.0f}")

    # Allocation
    assert program.allocate("recruiting", 500_000)
    assert program.allocate("portal", 300_000)
    assert program.allocate("retention", 200_000)
    assert program.unallocated == 0.0

    # Can't over-allocate
    assert not program.allocate("recruiting", 900_000), "Should reject over-allocation"
    print(f"  Allocated: R=${program.recruiting_pool:,.0f} / P=${program.portal_pool:,.0f} / Ret=${program.retention_pool:,.0f}")

    # Make deals
    deal1 = program.make_deal("recruiting", "REC-001", "Alex Smith", 100_000, year=2027)
    assert deal1 is not None
    deal2 = program.make_deal("recruiting", "REC-002", "Jane Doe", 150_000, year=2027)
    assert deal2 is not None
    print(f"  Made 2 recruiting deals, spent: ${program.recruiting_spent:,.0f}")
    assert program.recruiting_spent == 250_000
    assert program.recruiting_remaining == 250_000

    # Portal deal
    portal_deal = program.make_deal("portal", "PORT-001", "Transfer Star", 200_000, year=2027)
    assert portal_deal is not None
    print(f"  Portal deal: ${program.portal_spent:,.0f} / ${program.portal_pool:,.0f}")

    # Cancel a deal
    assert program.cancel_deal(deal1.deal_id)
    assert program.recruiting_spent == 150_000
    print(f"  After cancel: recruiting spent = ${program.recruiting_spent:,.0f}")

    # Summary
    summary = program.get_deal_summary()
    assert summary["active_deals"] == 2  # deal2 + portal_deal (deal1 cancelled)
    print(f"\n  Summary: {summary}")

    # Auto allocate
    auto_prog = auto_nil_program("Test U", prestige=60, market="medium", rng=rng)
    print(f"\n  Auto NIL: budget=${auto_prog.annual_budget:,.0f}")
    print(f"    R=${auto_prog.recruiting_pool:,.0f} / P=${auto_prog.portal_pool:,.0f} / Ret=${auto_prog.retention_pool:,.0f}")

    print("  ✓ NIL system passed")


# ──────────────────────────────────────────────
# TEST 7: Prestige & Market
# ──────────────────────────────────────────────

def test_prestige_and_market():
    divider("TEST 7: Prestige Computation & Market Estimation")

    # Prestige
    p1 = compute_team_prestige(all_time_wins=80, all_time_losses=20, championships=3, recent_wins=10)
    p2 = compute_team_prestige(all_time_wins=30, all_time_losses=70, championships=0, recent_wins=3)
    p3 = compute_team_prestige(all_time_wins=0, all_time_losses=0, championships=0)

    print(f"  Dominant program: prestige {p1}")
    print(f"  Weak program: prestige {p2}")
    print(f"  New program: prestige {p3}")

    assert p1 > p2, "Dominant program should have higher prestige"
    assert p3 == 50, "New program should default to 50"
    assert 10 <= p1 <= 99
    assert 10 <= p2 <= 99

    # Market estimation
    assert estimate_market_tier("CA") == "mega"
    assert estimate_market_tier("TX") == "mega"
    assert estimate_market_tier("WY") == "small"
    assert estimate_market_tier("OH") == "large"
    print(f"\n  CA → {estimate_market_tier('CA')}")
    print(f"  TX → {estimate_market_tier('TX')}")
    print(f"  OH → {estimate_market_tier('OH')}")
    print(f"  WY → {estimate_market_tier('WY')}")

    print("  ✓ Prestige & market passed")


# ──────────────────────────────────────────────
# TEST 8: Retention Risk
# ──────────────────────────────────────────────

def test_retention_risk():
    divider("TEST 8: Retention Risk Assessment")

    rng = random.Random(42)

    def make_card(name, ovr, potential, year):
        return PlayerCard(
            player_id=f"P-{name.replace(' ', '-')}",
            first_name=name.split()[0],
            last_name=name.split()[-1],
            number=rng.randint(1, 99),
            position="Viper/Back",
            archetype="none",
            nationality="American",
            hometown_city="",
            hometown_state="",
            hometown_country="USA",
            high_school="",
            height="5-10",
            weight=170,
            year=year,
            speed=ovr, stamina=ovr, agility=ovr, power=ovr,
            awareness=ovr, hands=ovr, kicking=ovr, kick_power=ovr,
            kick_accuracy=ovr, lateral_skill=ovr, tackling=ovr,
            potential=potential,
            development="normal",
        )

    roster = [
        make_card("Star Player", 90, 5, "Junior"),      # high risk
        make_card("Solid Starter", 78, 4, "Sophomore"),  # medium risk
        make_card("Average Joe", 68, 2, "Junior"),       # low risk
        make_card("Fresh Face", 70, 3, "Freshman"),      # skip (freshman)
        make_card("Graduating", 85, 4, "Graduate"),      # skip (graduating)
    ]

    # Low prestige, bad record = more risk
    risks = assess_retention_risks(roster, team_prestige=35, team_wins=3, rng=rng)

    print(f"  Players at risk: {len(risks)}")
    for r in risks:
        print(f"    {r.player_name}: {r.risk_level} risk "
              f"(OVR {r.overall}, {r.potential}★, suggest ${r.suggested_amount:,.0f})")

    assert len(risks) >= 1, "Should have at least one at-risk player"

    # High prestige, great record = less risk
    risks_good = assess_retention_risks(roster, team_prestige=90, team_wins=11, rng=rng)
    print(f"\n  Risks with prestige=90, wins=11: {len(risks_good)}")
    # High-prestige winning teams should have fewer at-risk players
    # (or at least no more than low-prestige losing teams)

    print("  ✓ Retention risk passed")


# ──────────────────────────────────────────────
# TEST 9: Full Recruiting Cycle
# ──────────────────────────────────────────────

def test_full_recruiting_cycle():
    divider("TEST 9: Full Recruiting Cycle")

    rng = random.Random(2027)
    teams = ["Alpha Uni", "Beta College", "Gamma State", "Delta Tech"]

    prestige = {"Alpha Uni": 80, "Beta College": 60, "Gamma State": 45, "Delta Tech": 30}
    regions = {"Alpha Uni": "west_coast", "Beta College": "midwest",
               "Gamma State": "south", "Delta Tech": "northeast"}
    scholarships = {t: 8 for t in teams}
    nil_budgets = {t: 500_000 for t in teams}

    result = run_full_recruiting_cycle(
        year=2027,
        team_names=teams,
        human_team="Alpha Uni",
        human_board=None,  # auto for human too
        human_nil_offers=None,
        team_prestige=prestige,
        team_regions=regions,
        scholarships_per_team=scholarships,
        nil_budgets=nil_budgets,
        pool_size=100,
        rng=rng,
    )

    pool = result["pool"]
    signed = result["signed"]
    rankings = result["class_rankings"]

    print(f"  Pool size: {len(pool)}")
    print(f"  Teams that signed players: {len(signed)}")

    total_signed = sum(len(v) for v in signed.values())
    print(f"  Total signed: {total_signed}")
    assert total_signed > 0, "At least some players should be signed"

    print(f"\n  Class Rankings:")
    for team, avg_stars, count in rankings:
        print(f"    {team:20s}: {count} signees, avg {avg_stars:.1f}★")

    # Higher prestige should generally get better classes
    alpha_rank = next((i for i, (t, _, _) in enumerate(rankings) if t == "Alpha Uni"), -1)
    print(f"\n  Alpha Uni (prestige=80) ranked #{alpha_rank + 1}")

    print("  ✓ Full recruiting cycle passed")


# ──────────────────────────────────────────────
# TEST 10: Recruit → PlayerCard conversion
# ──────────────────────────────────────────────

def test_recruit_to_player_card():
    divider("TEST 10: Recruit → PlayerCard Conversion")

    rng = random.Random(55)
    recruit = generate_single_recruit(recruit_id="TEST-CONV-001", stars=5, rng=rng)

    card = recruit.to_player_card(team_name="Gonzaga")

    print(f"  Recruit: {recruit.full_name} ({recruit.position})")
    print(f"  → Card: {card.full_name} ({card.position})")
    print(f"    Year: {card.year}")
    print(f"    Overall: {card.overall}")
    print(f"    Potential: {card.potential}★")
    print(f"    Development: {card.development}")
    print(f"    Team: {card.current_team}")

    assert card.year == "Freshman", "Signed recruits should be Freshmen"
    assert card.current_team == "Gonzaga"
    assert card.speed == recruit.true_speed
    assert card.potential == recruit.true_potential
    assert card.player_id == recruit.recruit_id

    # Serialise roundtrip
    d = card.to_dict()
    card2 = PlayerCard.from_dict(d)
    assert card2.full_name == card.full_name
    assert card2.overall == card.overall

    print("  ✓ Recruit → PlayerCard conversion passed")


# ──────────────────────────────────────────────
# RUN ALL TESTS
# ──────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  VIPERBALL RECRUITING / TRANSFER / NIL TEST SUITE")
    print("=" * 60)

    tests = [
        test_recruit_generation,
        test_scouting,
        test_recruiting_board,
        test_transfer_portal_dynasty,
        test_quick_portal,
        test_nil_system,
        test_prestige_and_market,
        test_retention_risk,
        test_full_recruiting_cycle,
        test_recruit_to_player_card,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n  FAILED: {test_fn.__name__}")
            print(f"    Error: {e}")
            import traceback
            traceback.print_exc()

    divider("RESULTS")
    print(f"  Passed: {passed}/{len(tests)}")
    print(f"  Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n  ALL TESTS PASSED")
    else:
        print(f"\n  {failed} TEST(S) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
