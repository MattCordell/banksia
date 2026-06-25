# Data Golf

A Kaggle-style analytics competition dataset built on the banksia synthetic patient generator.

Participants receive a multi-year cohort of synthetic patient encounters and must answer 35 boolean analytics questions (Q1–Q35) per episode. Questions range from simple demographic lookups to multi-condition clinical safety flags requiring reasoning across labs, medications, and SNOMED CT codes.

The pipeline supports two modes:
- **Exploratory**: All Q1–Q35 questions (default)
- **Production**: Interactive menu to select a subset of questions, renumbered sequentially

## Pipeline

```
generate_data.py  →  raw_data.csv  →  analyse.py  →  TrainingDataSet.csv
                                                    →  solution.csv
                                                    →  sample_submission.csv
                                                    →  metrics.txt
```

### Exploratory Mode (all Q1–Q35)

Run both steps in sequence with all questions:

```bash
python data-golf/run.py --n 8500 --seed 42
```

Or run each step individually:

```bash
# Step 1 – generate raw cohort data
python data-golf/generate_data.py --n 8500 --seed 42

# Step 2 – compute flags and write competition files (all Q1–Q35)
python data-golf/analyse.py --tx-server https://r4.ontoserver.csiro.au/fhir
```

### Production Mode (selected subset of questions)

Run with interactive menu to select which questions to include:

```bash
python data-golf/run.py --mode production --n 8500 --seed 42
```

The script will display all 35 questions and prompt you to select (e.g., `1,4,5,17,22`). Selected questions are renumbered sequentially in the output files (Q1, Q2, Q3, etc.).

### Arguments

| Script | Argument | Default | Description |
|--------|----------|---------|-------------|
| `run.py` | `--mode` | exploratory | Pipeline mode: `exploratory` (all Q1–Q35) or `production` (interactive menu to select subset). |
| `generate_data.py` | `--n` | 10 | Target patients per SNOMED CT-AU edition period. Actual count is randomised between `floor(n×0.9)` and `n`. |
| `generate_data.py` | `--seed` | 42 | Random seed for reproducibility. |
| `analyse.py` | `--mode` | exploratory | Pipeline mode: `exploratory` or `production`. |
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
3. Expands three ECL expressions per edition via Ontoserver (results are cached within the run):
   - **Pregnancy:** `<<77386006 OR <<118185001`
   - **Bacterial joint infections (non-Streptococcus):** `(<<363162000:*=(<<409822003 MINUS <<58800005))`
   - **Infections:** Complex ECL capturing pyogenic/bacterial/causative organism conditions
4. Computes Q1–Q35 boolean flags per edition group, then concatenates back to the full dataset.
5. **Production mode only:** Prompts user to select which questions to include; selected questions are renumbered sequentially in output files.
6. Writes the four output files.

Terminology lookups use edition-specific ValueSet URLs so that a concept added or retired between editions is classified correctly for each patient's encounter date.

## Output files

| File | Description | Distribute to participants? |
|------|-------------|---------------------------|
| `TrainingDataSet.csv` | Patient demographics, labs, SNOMED codes, and medicine displays. Strips `Age`, `Condition`, `LifestyleFactors`, and medicine categories. SNOMED columns renamed to `Clinical_Note_Code` / `Clinical_Note_Display`. | Yes |
| `sample_submission.csv` | Same structure as a submission (Episode Number + selected questions), filled with random True/False. In exploratory mode: Q1–Q35. In production mode: Q1–Qn (renumbered). | Yes |
| `solution.csv` | Correct answers per episode + `Usage` column (Public/Private for Kaggle leaderboard split). In exploratory mode: Q1–Q35. In production mode: Q1–Qn (renumbered based on user selection). | **No — keep private** |
| `metrics.txt` | Human-readable question counts and condition summary for the organiser. In exploratory mode: all Q1–Q35. In production mode: only selected questions. | No |
| `raw_data.csv` | Full generated data including `Age`, `Condition`, and medicine categories — the source of truth for `solution.csv`. | No |

> **Note:** `solution.csv` and `raw_data.csv` contain information that would allow participants to answer the questions directly. Do not publish them alongside the competition dataset.

**Production Mode Note:** When using `--mode production`, selected questions are renumbered sequentially in all output files. For example, if you select questions `1,5,17`, they appear as `Q1, Q2, Q3` in `solution.csv` and `metrics.txt`. The original question mapping is displayed at the start of the analysis.

## Questions

See [Questions.md](Questions.md) for the full list of Q1–Q35.

Questions are implemented in `analyse.py` → `compute_flags()`. Questions that require SNOMED subsumption (Q27, Q34, Q35) use ECL-expanded code sets rather than text matching, so the answers are edition-aware and reproducible.

**Q35 (Infections):** Added to capture patients with infection-related diagnoses using an ECL expression that identifies pyogenic/bacterial/causative organism conditions while excluding non-infectious codes.

## At scale

For a full competition dataset (~50 000 episodes), use `--n 8500`. Generation takes approximately 60–90 minutes due to Ontoserver calls across six edition periods. ECL expansions during analysis are cached and add only a few minutes.

Questions Q31 and Q32 (Digoxin toxicity flags) and Q35 (Infections) require sufficient patient volume to produce meaningful non-zero counts — they are only meaningful at `--n 8500` or above.

### Production Mode at Scale

For large datasets, use exploratory mode to generate the full question set (`--mode exploratory` or omit the flag). You can then create subsetted datasets for distribution using production mode on smaller pilot runs to determine which questions are most relevant for your competition.
