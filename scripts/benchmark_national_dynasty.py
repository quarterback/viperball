#!/usr/bin/env python3
"""Full national dynasty validation via the existing API calibration harness."""
import argparse
from pathlib import Path

from benchmark_dynasty_tactics import run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261124)
    parser.add_argument("--seasons", type=int, default=2)
    parser.add_argument("--out", type=Path, default=Path("reports/national-dynasty"))
    parser.add_argument("--analytics", action="store_true", help="Collect and evaluate the offline analytics corpus")
    args = parser.parse_args()
    if args.seasons < 2:
        parser.error("At least two seasons are required for offseason validation")
    run(args.seasons, 0, args.seed, args.out, national=True, analytics=args.analytics)
