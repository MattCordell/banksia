"""Count True values per question column in solution.csv.

Usage:
    python data-golf/count_true.py
    python data-golf/count_true.py --file data-golf/solution.csv
"""

import argparse
import csv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        default=str(Path(__file__).parent / "solution.csv"),
        help="Path to CSV file (default: data-golf/solution.csv)",
    )
    args = parser.parse_args()

    with open(args.file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        question_cols = [c for c in reader.fieldnames if c.startswith("Q")]
        counts = {c: 0 for c in question_cols}
        total_rows = 0
        for row in reader:
            total_rows += 1
            for c in question_cols:
                if row[c].strip().lower() == "true":
                    counts[c] += 1

    print(f"Total rows: {total_rows}\n")
    print(f"{'Column':<8}{'True count':<12}{'%':<8}")
    for c in question_cols:
        pct = (counts[c] / total_rows * 100) if total_rows else 0
        print(f"{c:<8}{counts[c]:<12}{pct:<8.1f}")


if __name__ == "__main__":
    main()
