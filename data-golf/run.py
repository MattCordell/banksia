"""
Orchestrator script: runs data generation then analysis sequentially.

Usage:
    python data-golf/run.py --n 10 --seed 42 [--mode exploratory|production]
"""

import argparse
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--mode", choices=["exploratory", "production"], default="exploratory",
                        help="Pipeline mode: exploratory (all Q1-Q35) or production (select subset)")
    parser.add_argument("--n", type=int, help="Target patients per period (for generate_data.py)")
    parser.add_argument("--seed", type=int, help="Random seed (for generate_data.py)")
    parser.add_argument("--tx-server", help="FHIR terminology server (for analyse.py)")
    args, remaining = parser.parse_known_args()

    # Build args for generate_data.py (includes --n, --seed, and any other args)
    gen_args = []
    if args.n:
        gen_args.extend(["--n", str(args.n)])
    if args.seed:
        gen_args.extend(["--seed", str(args.seed)])
    if args.tx_server:
        gen_args.extend(["--tx-server", args.tx_server])
    gen_args.extend(remaining)

    # Build args for analyse.py (includes --mode and --tx-server only)
    analyse_args = ["--mode", args.mode]
    if args.tx_server:
        analyse_args.extend(["--tx-server", args.tx_server])

    print("=" * 60)
    print("Step 1: Generating data")
    print("=" * 60)
    subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "generate_data.py")] + gen_args,
        check=True,
    )

    print()
    print("=" * 60)
    print("Step 2: Analysing data")
    print("=" * 60)
    subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "analyse.py")] + analyse_args,
        check=True,
    )

    print()
    print("=" * 60)
    print("Done")
    print("=" * 60)


if __name__ == "__main__":
    main()
