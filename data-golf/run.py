"""
Orchestrator script: runs data generation then analysis sequentially.

Usage:
    python data-golf/run.py --n 10 --seed 42
"""

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    print("=" * 60)
    print("Step 1: Generating data")
    print("=" * 60)
    subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "generate_data.py")] + sys.argv[1:],
        check=True,
    )

    print()
    print("=" * 60)
    print("Step 2: Analysing data")
    print("=" * 60)
    subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "analyse.py")],
        check=True,
    )

    print()
    print("=" * 60)
    print("Done")
    print("=" * 60)


if __name__ == "__main__":
    main()
