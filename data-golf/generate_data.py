"""
Generate multi-year synthetic patient data using banksia.

Shells out to generate.py for each SNOMED CT-AU edition period,
adds EncounterDate and DateOfBirth columns, splits into train/test,
and exports raw and kaggle CSV formats.
"""

import argparse
import math
import os
import random
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
GENERATE_PY = os.path.join(PROJECT_ROOT, "generate.py")
DEFAULT_TX_SERVER = "https://r4.ontoserver.csiro.au/fhir"

# Each period starts the day after the SNOMED CT-AU edition is published.
# ecl_template: "product" for pre-2025, "amt-tpuu" for 2025 onwards.
PERIODS = [
    {"start": date(2021, 2, 1), "end": date(2022, 1, 31), "edition": "20210131", "ecl_template": "product"},
    {"start": date(2022, 2, 1), "end": date(2023, 1, 31), "edition": "20220131", "ecl_template": "product"},
    {"start": date(2023, 2, 1), "end": date(2024, 1, 31), "edition": "20230131", "ecl_template": "product"},
    {"start": date(2024, 2, 1), "end": date(2025, 1, 31), "edition": "20240131", "ecl_template": "product"},
    {"start": date(2025, 2, 1), "end": date(2026, 1, 31), "edition": "20250131", "ecl_template": "amt-tpuu"},
    {"start": date(2026, 2, 1), "end": date(2027, 1, 31), "edition": "20260131", "ecl_template": "amt-tpuu"},
]

# Columns that contain SNOMED CT codes (must be treated as text, not numeric).
SNOMED_CODE_COLS = [
    "SNOMED_Code",
    "Medicine_1_Code",
    "Medicine_2_Code",
    "Medicine_3_Code",
]

KAGGLE_EXCLUDE_COLS = [
    "Age",
    "LifestyleFactors",
    "Condition",
    "Medicine_1_Category",
    "Medicine_2_Category",
    "Medicine_3_Category",
]

# Test kaggle additionally excludes all SNOMED/medicine code+display columns
TEST_KAGGLE_EXTRA_EXCLUDE = [
    "SNOMED_Code",
    "SNOMED_Display",
    "Medicine_1_Code",
    "Medicine_1_Display",
    "Medicine_2_Code",
    "Medicine_2_Display",
    "Medicine_3_Code",
    "Medicine_3_Display",
]

DEFAULT_N = 10
DEFAULT_SEED = 42


def random_date_in_range(rng, start, end):
    """Return a random date between start and end inclusive."""
    delta_days = (end - start).days
    return start + timedelta(days=rng.randint(0, delta_days))


def compute_dob(rng, age, encounter_date):
    """Compute a random DateOfBirth such that the patient is exactly `age`
    years old on `encounter_date`."""
    # Latest possible DOB: the encounter_date minus `age` years
    # (birthday is on or before encounter_date)
    try:
        latest_dob = encounter_date.replace(year=encounter_date.year - age)
    except ValueError:
        # Feb 29 edge case
        latest_dob = encounter_date.replace(
            year=encounter_date.year - age, month=2, day=28
        )

    # Earliest possible DOB: one day after (encounter_date minus (age+1) years)
    try:
        day_before_earliest = encounter_date.replace(
            year=encounter_date.year - age - 1
        )
    except ValueError:
        day_before_earliest = encounter_date.replace(
            year=encounter_date.year - age - 1, month=2, day=28
        )
    earliest_dob = day_before_earliest + timedelta(days=1)

    delta = (latest_dob - earliest_dob).days
    if delta <= 0:
        return latest_dob
    return earliest_dob + timedelta(days=rng.randint(0, delta))


def generate_period(period, actual_n, period_seed, rng):
    """Generate a cohort for one SNOMED CT-AU edition period."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".csv")
    os.close(tmp_fd)

    try:
        cmd = [
            sys.executable,
            GENERATE_PY,
            "--mode", "cohort",
            "--n", str(actual_n),
            "--seed", str(period_seed),
            "--snomed-edition", period["edition"],
            "--med-ecl-template", period["ecl_template"],
            "--tx-server", DEFAULT_TX_SERVER,
            "--output", tmp_path,
        ]
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"  [{timestamp}] Generating {actual_n} patients for edition "
              f"{period['edition']} (ecl: {period['ecl_template']})...")
        subprocess.run(cmd, check=True)

        # Read SNOMED code columns as strings to avoid float conversion
        dtype_overrides = {col: str for col in SNOMED_CODE_COLS}
        df = pd.read_csv(tmp_path, dtype=dtype_overrides)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Add EncounterDate as the first column
    encounter_dates = [
        random_date_in_range(rng, period["start"], period["end"])
        for _ in range(len(df))
    ]
    df.insert(0, "EncounterDate", [d.isoformat() for d in encounter_dates])

    # Add DateOfBirth as the second column
    dobs = [
        compute_dob(rng, int(row["Age"]), enc_date)
        for (_, row), enc_date in zip(df.iterrows(), encounter_dates)
    ]
    df.insert(1, "DateOfBirth", [d.isoformat() for d in dobs])

    return df


def main():
    parser = argparse.ArgumentParser(
        description="Generate multi-year synthetic patient data."
    )
    parser.add_argument(
        "--n",
        type=int,
        default=DEFAULT_N,
        help=f"Target patients per period (default: {DEFAULT_N}). "
        f"Actual count is random between floor(n*0.9) and n.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for reproducibility (default: {DEFAULT_SEED}).",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # Pre-generate per-period seeds
    period_seeds = [rng.randint(0, 2**31) for _ in PERIODS]

    all_dfs = []
    for i, period in enumerate(PERIODS):
        lower = math.floor(args.n * 0.9)
        actual_n = rng.randint(lower, args.n)
        df = generate_period(period, actual_n, period_seeds[i], rng)
        all_dfs.append(df)

    combined = pd.concat(all_dfs, ignore_index=True)

    # Clean up SNOMED code columns: replace "nan" strings with empty string
    for col in SNOMED_CODE_COLS:
        if col in combined.columns:
            combined[col] = combined[col].fillna("").replace("nan", "")

    print(f"\nTotal patients generated: {len(combined)}")

    # Sort by EncounterDate and assign Episode Number
    combined = combined.sort_values("EncounterDate").reset_index(drop=True)
    combined.insert(0, "Episode Number", range(1, len(combined) + 1))

    # Export single raw CSV
    raw_path = os.path.join(SCRIPT_DIR, "raw_data.csv")
    combined.to_csv(raw_path, index=False)
    print(f"Saved {raw_path}")


if __name__ == "__main__":
    main()
