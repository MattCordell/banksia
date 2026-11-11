# Data Golf

A Kaggle-style analytics competition dataset built on the banksia synthetic patient generator.

Participants receive a multi-year cohort of synthetic patient encounters and must answer 18 boolean questions (Q1–Q18) per episode. Each question states a **criterion**; the answer is `True` when that criterion holds for the episode. They range from simple demographic lookups to multi-condition clinical safety flags requiring reasoning across labs, medicines, and SNOMED CT codes.

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
# Step 1 - generate raw cohort data
python data-golf/generate_data.py --n 8500 --seed 42

# Step 2 - compute flags and write competition files
python data-golf/analyse.py --tx-server https://r4.ontoserver.csiro.au/fhir
```

### Arguments

| Script | Argument | Default | Description |
|--------|----------|---------|-------------|
| `generate_data.py` | `--n` | 10 | Target patients per SNOMED CT-AU edition period. Actual count is randomised between `floor(n×0.9)` and `n`. |
| `generate_data.py` | `--seed` | 42 | Random seed for reproducibility. |
| `analyse.py` | `--tx-server` | `https://r4.ontoserver.csiro.au/fhir` | FHIR terminology server for ECL expansion. |

## How it works

### Step 1 - Data generation (`generate_data.py`)

Iterates over six SNOMED CT-AU edition periods (2021–2026), calling the main banksia `generate.py` for each:

| Period | Edition | ECL template |
|--------|---------|--------------|
| 2021-02-01 → 2022-01-31 | 20210131 | clinical-drug |
| 2022-02-01 → 2023-01-31 | 20220131 | clinical-drug |
| 2023-02-01 → 2024-01-31 | 20230131 | clinical-drug |
| 2024-02-01 → 2025-01-31 | 20240131 | clinical-drug |
| 2025-02-01 → 2026-01-31 | 20250131 | amt-tpuu |
| 2026-02-01 → 2027-01-31 | 20260131 | amt-tpuu |

`clinical-drug` selects strength-bearing SNOMED CT products (those with `732943007 |Has basis of strength substance|`). Where a category's ingredients have no such concept in that edition, it falls back to the broader `product` template so the row still gets a code — on edition 20210131 that affects 6 of 68 ingredient ECLs.

Each period's cohort is assigned random `EncounterDate` values within the period window and a consistent `DateOfBirth` derived from the generated `Age`. The six cohorts are concatenated, sorted by `EncounterDate`, and saved as `raw_data.csv` with a sequential `Episode Number`.

### Step 2 - Analysis (`analyse.py`)

1. Reads `raw_data.csv`, casting SNOMED code columns as strings.
2. Adds derived columns (`Year`, `BMI`, `CholHDL_Ratio`).
3. Maps each row's `EncounterDate` to its SNOMED CT-AU edition period.
4. Expands every ECL in `CONDITION_ECLS` and `MEDICINE_ECLS` once per edition via Ontoserver (cached within the run).
5. Computes the Q1–Q18 flags per edition group, then concatenates back to the full dataset.
6. Writes the four output files.

### Criteria are answerable from the published data

Every criterion is expressed against columns that actually appear in `TrainingDataSet.csv` — `Clinical_Note_Code`/`Display`, `Medicine_*_Code`/`Display`, lab results and demographics.

The generator's `Condition` and `Medicine_*_Category` columns are deliberately **not** used. They are withheld from participants, so any flag derived from them would be unanswerable — and they are also unreliable:

- `Condition` is a *sampling bucket*, not a diagnosis. The coded concept is often only loosely related: a `Hyperthyroidism` row coded as *Dysprealbuminaemic euthyroidal hyperthyroxinaemia* (a euthyroid state), or an `Osteoarthritis` row coded as *Chronic tophaceous gout of left foot*.
- The medicine categories mislabel products — calcium channel blockers filed under `ACE Inhibitors / ARBs`, parenteral iron under `Oral Iron`.

Conditions are therefore matched by ECL against `Clinical_Note_Code`; medicines by ECL against `Medicine_*_Code`, with a display-text regex fallback for products whose code falls outside the expansion.

### Edition-aware answers

ECLs are expanded per edition and applied only to rows whose encounter falls in that edition's period, so a flag reflects the terminology active at the time of the encounter. This is deliberate, and it does mean identical clinical content can flag differently across years — `<<118185001 |Pregnant|` expands to between 782 and 1633 members depending on edition, and *Pregnancy-induced hypertension* only becomes a descendant from the 2024 edition onward.

When authoring an ECL, prefer stable substance groupers over navigation expressions. `(<13790009.<<762951001) AND <<767270007` resolved to a single ingredient in the 2021–2024 editions versus eight in 2025+, silently under-counting every pre-2025 row; `<<767270007 |Iron and/or iron compound|` is stable at 78–87 members across all six.

`analyse.py` quantifies the cost of that choice in three `metrics.txt` sections — dataset-wide inactive concepts, how many fall inside a question's ECLs and whether an ECL history supplement could recover them, and what would move if every flag were recomputed against the latest edition instead. The reports measure the alternative without applying it: `solution.csv` stays encounter-relative.

See **[TerminologyDrift.md](TerminologyDrift.md)** for the analysis. The headline: concept *retirement* touched 741 positive rows across all 18 questions, while *reclassification* moved 952 rows in Q5 alone — `<<396275006 |Osteoarthritis|` went from 431 concepts to 181 between the 2025 and 2026 editions, and only 8 of the 250 departures were retirements. History supplements address inactivation only, so they offer no protection against the larger effect.

Pass `--no-history-check` to skip the two reference-edition sections and their extra ECL expansions; `--no-inactive-check` skips all three.

## Output files

| File | Description | Distribute to participants? |
|------|-------------|---------------------------|
| `TrainingDataSet.csv` | Patient demographics, labs, SNOMED codes, and medicine codes/displays. Strips `Age`, `Condition`, `LifestyleFactors`, `BirthDate`, and the medicine categories. SNOMED columns renamed to `Clinical_Note_Code` / `Clinical_Note_Display`. | Yes |
| `sample_submission.csv` | Same structure as a submission (Episode Number + Q1–Q18), filled with random True/False. | Yes |
| `solution.csv` | Correct answers per episode + `Usage` column (Public/Private for the Kaggle leaderboard split). | **Not during the event.** Published in this repository after the event closed. |
| `metrics.txt` | Human-readable criterion counts and condition summary for the organiser. | No |
| `raw_data.csv` | Full generated data including `Age`, `Condition`, and medicine categories — the source of truth for `solution.csv`. | No |

> **Note:** `solution.csv` and `raw_data.csv` contain information that would let participants answer the questions directly. Do not publish them alongside the competition dataset of a live event. For Data Golf 2026, `solution.csv` was committed to this branch after the competition closed, as a target to compare against (it is one encounter-relative reading of each question, not absolute truth). `raw_data.csv` stays unpublished.

`Age` is withheld and must be derived from `DateOfBirth` and `EncounterDate`. Only `DateOfBirth` is published: an earlier `BirthDate` column was computed against *today* rather than the encounter date and disagreed with `DateOfBirth` by up to six years, flipping rows across the 15/18/50 age thresholds.

## Questions

See [Questions.md](Questions.md) for the full list of criteria. They are implemented one function per question in `analyse.py` (`q01_female` … `q18_mineral_supplement`), registered in `QUESTION_FUNCS`, with the criterion text in `QUESTIONS`.

This set was selected and tuned from an earlier 37-question set; the originals remain in the git history. Mapping:

| New | Old | Criterion |
|-----|-----|-----------|
| Q1 | Q1 | female |
| Q2 | Q3 | obese, high cholesterol:HDL |
| Q3 | Q4 | healthy |
| Q4 | Q5 | hyperthyroidism |
| Q5 | Q8 | osteoarthritis in 2024 |
| Q6 | Q15 | ACE inhibitor |
| Q7 | Q16 | cardiac glycoside |
| Q8 | Q19 | fungal foot infection |
| Q9 | Q20 | duplicate paracetamol |
| Q10 | Q21 | bilateral condition |
| Q11 | Q25 | female 15–49 on methotrexate |
| Q12 | Q27 | pregnant on a teratogen |
| Q13 | Q29 | OA/RA on NSAID with low eGFR |
| Q14 | Q31 | digoxin toxicity risk |
| Q15 | Q33 | pregnant with high fasting glucose |
| Q16 | Q34 | non-streptococcal bacterial joint infection |
| Q17 | Q36 | oral iron |
| Q18 | Q37 | mineral supplement |

**Q18 (Mineral supplement) known limitation:** for 2025+ encounters (AMT product model) this can flag compound products where the qualifying mineral is incidental rather than the therapeutic intent — a calcium-carbonate antacid prescribed as a phosphate binder still counts. Pre-2025 encounters (international product hierarchy) do not have this issue.

## At scale

For a full competition dataset (~50 000 episodes), use `--n 8500`. Generation takes roughly 60–90 minutes due to Ontoserver calls across six edition periods. ECL expansions during analysis are cached and add a few minutes.

Several criteria need volume to produce meaningful non-zero counts and should be re-checked on a production-sized run:

- **Q8** (fungal foot infection) — the ECL expands to only ~10 concepts, so small cohorts return 0.
- **Q9** (duplicate paracetamol) — requires two paracetamol products on one patient.
- **Q14** (digoxin toxicity risk) — requires digoxin, eGFR < 30 and a loop diuretic on the same patient.
