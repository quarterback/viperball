#!/usr/bin/env python3
"""
Generate coaching staffs for all team JSON files.

Reads each team JSON, generates a 4-person coaching staff (HC, OC, DC, STC)
with attributes, classifications, contracts, and biographical details.
Writes the coaching_staff section back to the JSON.

Usage:
    python scripts/generate_coaching_staffs.py
    python scripts/generate_coaching_staffs.py --seed 42
    python scripts/generate_coaching_staffs.py --dry-run
"""

import argparse
import json
import random
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.coaching import generate_coaching_staff, CoachCard


TEAMS_DIR = Path(__file__).parent.parent / "data" / "teams"


def estimate_prestige_from_json(data: dict) -> int:
    """Estimate a team's prestige from JSON data."""
    team_stats = data.get("team_stats", {})
    identity = data.get("identity", {})
    coaching = data.get("coaching", {})

    # Base from team stats
    avg_speed = team_stats.get("avg_speed", 78)
    avg_stamina = team_stats.get("avg_stamina", 80)
    kicking = team_stats.get("kicking_strength", 72)
    lateral = team_stats.get("lateral_proficiency", 78)
    defense = team_stats.get("defensive_strength", 74)

    # Overall team quality → rough prestige
    quality = (avg_speed + avg_stamina + kicking + lateral + defense) / 5
    # 70 quality → ~40 prestige, 85 quality → ~70 prestige, 95 quality → ~90 prestige
    prestige = int((quality - 60) * 2.5 + 10)
    prestige = max(15, min(90, prestige))

    # Experience bonus from coaching section
    exp_str = coaching.get("experience", "5 years")
    try:
        years = int(exp_str.split()[0])
        if years >= 15:
            prestige += 5
        elif years >= 10:
            prestige += 3
    except (ValueError, IndexError):
        pass

    return max(15, min(95, prestige))


def main():
    parser = argparse.ArgumentParser(description="Generate coaching staffs for all teams")
    parser.add_argument("--seed", type=int, default=2026, help="Random seed")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")
    parser.add_argument("--year", type=int, default=2026, help="Dynasty year")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    if not TEAMS_DIR.exists():
        print(f"Teams directory not found: {TEAMS_DIR}")
        sys.exit(1)

    team_files = sorted(TEAMS_DIR.glob("*.json"))
    print(f"Found {len(team_files)} team files in {TEAMS_DIR}")

    for filepath in team_files:
        with open(filepath) as f:
            data = json.load(f)

        team_info = data.get("team_info", {})
        team_name = team_info.get("school") or team_info.get("school_name", "Unknown")

        # Use existing HC name/gender if present
        coaching = data.get("coaching", {})
        existing_hc_name = coaching.get("head_coach", "")

        prestige = estimate_prestige_from_json(data)

        # Generate coaching staff
        staff = generate_coaching_staff(
            team_name=team_name,
            prestige=prestige,
            year=args.year,
            rng=rng,
        )

        # Override HC name with existing name if present
        if existing_hc_name and "head_coach" in staff:
            hc = staff["head_coach"]
            parts = existing_hc_name.split()
            if len(parts) >= 2:
                hc.first_name = parts[0]
                hc.last_name = " ".join(parts[1:])
            hc_gender = coaching.get("head_coach_gender", "neutral")
            hc.gender = hc_gender
            # Update coach_id to match new name
            hc.coach_id = f"coach_{hc.first_name.lower()}_{hc.last_name.lower().replace(' ', '_')}_{rng.randint(100, 999)}"

            # Preserve philosophy from existing coaching section
            if coaching.get("philosophy"):
                hc.philosophy = coaching["philosophy"]
            if coaching.get("coaching_style"):
                hc.coaching_style = coaching["coaching_style"]
            if coaching.get("background"):
                hc.background = coaching["background"]

        # Serialize to dict
        staff_dict = {role: card.to_dict() for role, card in staff.items()}

        if args.dry_run:
            print(f"\n{team_name} (prestige: {prestige})")
            for role, card in staff.items():
                print(f"  {role}: {card.full_name} ({card.classification_label}) "
                      f"OVR:{card.overall} INS:{card.instincts} "
                      f"LED:{card.leadership} CMP:{card.composure} "
                      f"ROT:{card.rotations} DEV:{card.development} "
                      f"REC:{card.recruiting}")
        else:
            data["coaching_staff"] = staff_dict
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    action = "Would write" if args.dry_run else "Wrote"
    print(f"\n{action} coaching staffs for {len(team_files)} teams.")


if __name__ == "__main__":
    main()
