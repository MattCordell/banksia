# Data Golf

A Kaggle-style analytics competition dataset built on the banksia synthetic patient generator.

Participants receive a multi-year cohort of synthetic patient encounters and must answer 34 boolean analytics questions (Q1–Q34) per episode. Questions range from simple demographic lookups to multi-condition clinical safety flags requiring reasoning across labs, medications, and SNOMED CT codes.

## Pipeline

```
generate_data.py  →  raw_data.csv  →  analyse.py  →  TrainingDataSet.csv
                                                    →  solution.csv
                                                    →  sample_submission.csv
                                                    →  metrics.txt
```

Run both steps in sequence:

```bash
python data-golf/run.py --n 8500 --seed 42
```

Or run each step individually:

```bash
# Step 1 – generate raw cohort data
python data-golf/generate_data.py --n 8500 --seed 42

# Step 2 – compute flags and write competition files
python data-golf/analyse.py --tx-server https://r4.ontoserver.csiro.au/fhir
```

### Arguments

| Script | Argument | Default | Description |
|--------|----------|---------|-------------|
| `generate_data.py` | `--n` | 10 | Target patients per SNOMED CT-AU edition period. Actual count is randomised between `floor(n×0.9)` and `n`. |
| `generate_data.py` | `--seed` | 42 | Random seed for reproducibility. |
| `analyse.py` | `--tx-server` | `https://r4.ontoserver.csiro.au/fhir` | FHIR terminology server for ECL expansion. |

## How it works

### Step 1 – Data generation (`generate_data.py`)

Iterates over six SNOMED CT-AU edition periods (2021–2026), calling the main banksia `generate.py` for each:

| Period | Edition | ECL template |
|--------|---------|--------------|
| 2021-02-01 → 2022-01-31 | 20210131 | product |
| 2022-02-01 → 2023-01-31 | 20220131 | product |
| 2023-02-01 → 2024-01-31 | 20230131 | product |
| 2024-02-01 → 2025-01-31 | 20240131 | product |
| 2025-02-01 → 2026-01-31 | 20250131 | amt-tpuu |
| 2026-02-01 → 2027-01-31 | 20260131 | amt-tpuu |

Each period's cohort is assigned random `EncounterDate` values within the period window and a consistent `DateOfBirth` (derived from the generated `Age`). The six cohorts are concatenated, sorted by `EncounterDate`, and saved as `raw_data.csv` with a sequential `Episode Number`.

### Step 2 – Analysis (`analyse.py`)

1. Reads `raw_data.csv`, casting SNOMED code columns as strings.
2. Maps each row's `EncounterDate` to its SNOMED CT-AU edition period.
3. Expands two ECL expressions per edition via Ontoserver (results are cached within the run):
   - **Pregnancy:** `<<77386006 OR <<118185001`
   - **Bacterial joint infections (non-Streptococcus):** `(<<363162000:*=(<<409822003 MINUS <<58800005))`
4. Computes Q1–Q34 boolean flags per edition group, then concatenates back to the full dataset.
5. Writes the four output files.

Terminology lookups use edition-specific ValueSet URLs so that a concept added or retired between editions is classified correctly for each patient's encounter date.

## Output files

| File | Description | Distribute to participants? |
|------|-------------|---------------------------|
| `TrainingDataSet.csv` | Patient demographics, labs, SNOMED codes, and medicine displays. Strips `Age`, `Condition`, `LifestyleFactors`, and medicine categories. SNOMED columns renamed to `Clinical_Note_Code` / `Clinical_Note_Display`. | Yes |
| `sample_submission.csv` | Same structure as a submission (Episode Number + Q1–Q34), filled with random True/False. | Yes |
| `solution.csv` | Correct Q1–Q34 answers per episode + `Usage` column (Public/Private for Kaggle leaderboard split). | **No — keep private** |
| `metrics.txt` | Human-readable Q1–Q34 counts and condition summary for the organiser. | No |
| `raw_data.csv` | Full generated data including `Age`, `Condition`, and medicine categories — the source of truth for `solution.csv`. | No |

> **Note:** `solution.csv` and `raw_data.csv` contain information that would allow participants to answer the questions directly. Do not publish them alongside the competition dataset.

## Questions

See [Questions.md](Questions.md) for the full list of Q1–Q34.

Questions are implemented in `analyse.py` → `compute_flags()`. Questions that require SNOMED subsumption (Q27, Q33, Q34) use ECL-expanded code sets rather than text matching, so the answers are edition-aware and reproducible.

## At scale

For a full competition dataset (~50 000 episodes), use `--n 8500`. Generation takes approximately 60–90 minutes due to Ontoserver calls across six edition periods. ECL expansions during analysis are cached and add only a few minutes.

Questions Q31 and Q32 (Digoxin toxicity flags) require sufficient Heart Failure patient volume to produce non-zero counts — they are only meaningful at `--n 8500` or above.
