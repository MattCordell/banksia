# Data Golf: Synthetic Patient Data Challenge

## Overview

This competition uses synthetic patient encounter data spanning six years (February 2021 to January 2027). Each row represents a single patient encounter, including demographics, clinical condition coding (SNOMED CT), prescribed medications, and laboratory results across 11 pathology panels.

The dataset was generated using Australian population statistics and clinical epidemiology data. Conditions are assigned based on age, sex, and lifestyle-weighted prevalence rates. Laboratory results are condition-aware, reflecting realistic pathological patterns.

## Files

| File | Rows | Columns | Description |
|------|------|---------|-------------|
| `train_kaggle.csv` | ~25,500 | 80 | Training data with SNOMED codes and medicine codes visible |
| `test_kaggle.csv` | ~2,800 | 72 | Test data with condition, medicine, and SNOMED columns removed |
| `sample_submission.csv` | 23 | 2 | Sample submission with random placeholder answers |

## Column Descriptions

### Demographics
| Column | Description |
|--------|-------------|
| `EncounterDate` | Date of the patient encounter (YYYY-MM-DD) |
| `DateOfBirth` | Patient date of birth (YYYY-MM-DD) |
| `Sex` | Patient sex: male, female, or non-binary |
| `State` | Australian state or territory |
| `Height_cm` | Height in centimetres |
| `Weight_kg` | Weight in kilograms |

### Clinical Coding (train only)
| Column | Description |
|--------|-------------|
| `SNOMED_Code` | SNOMED CT code for the patient's condition |
| `SNOMED_Display` | Human-readable SNOMED CT display term |
| `Medicine_1_Code` | SNOMED CT code for first prescribed medicine |
| `Medicine_1_Display` | Display name for first prescribed medicine |
| `Medicine_2_Code` / `Medicine_2_Display` | Second prescribed medicine (if any) |
| `Medicine_3_Code` / `Medicine_3_Display` | Third prescribed medicine (if any) |

### Laboratory Panels

Results may be missing (blank) for any panel — not all patients receive all tests. The following panels are included:

- **MBAP** (Multi-Basic Analyte Panel): Sodium, Potassium, Chloride, Bicarbonate, Anion Gap, Calcium (corrected), Phosphate, Urea, Urate, Creatinine, eGFR, Glucose (fasting), Total Protein, Albumin, Globulin, Total Bilirubin, ALP, AST, ALT, GGT, LDH, Cholesterol
- **FBC** (Full Blood Count): WBC, Haemoglobin, Platelets, MCV, Neutrophils, Lymphocytes, Monocytes, Eosinophils, Basophils (each with % and absolute count)
- **LFT** (Liver Function Tests): ALT, AST, GGT, ALP, Total Bilirubin, Albumin
- **Lipid Panel**: Total Cholesterol, HDL, LDL, Triglycerides
- **Iron Studies**: Ferritin, Serum Iron, Transferrin, Transferrin Saturation
- **Thyroid Panel**: TSH, Free T4
- **Bone Profile**: Calcium, Phosphate, ALP
- **B12 & Folate**: Vitamin B12, Folate
- **Kidney Function**: Sodium, Potassium, Urea, Creatinine, eGFR
- **Immunoglobulins**: IgG, IgA, IgM
- **CRP**: C-Reactive Protein

## Important Notes

- **BMI** is not provided directly but can be calculated: `Weight_kg / (Height_cm / 100)^2`
- **Obese** is defined as BMI >= 30 (per Australian health guidelines)
- **Chol:HDL ratio** can be calculated from the Lipid Panel columns
- Encounter dates span 2021-02-01 to 2027-01-31. When a question refers to a year (e.g. "in 2021"), it means encounters where the EncounterDate falls in that calendar year
- Some patients have no medicines prescribed (all medicine columns blank)
- Up to 3 medicines may be prescribed per encounter

## Questions

Submit your answers in a CSV with two columns: `Question` and `Answer`.

### Train Data Questions (use train_kaggle.csv)

| Question | Description | Answer Format |
|----------|-------------|---------------|
| Q1 | How many females in the dataset? | Integer |
| Q2 | How many adults (Age >= 18)? | Integer |
| Q3 | How many obese patients are there (BMI >= 30)? | Integer |
| Q4 | What proportion of obese patients (BMI >= 30) have a Chol:HDL ratio > 5? | Decimal (4dp) |
| Q5 | How many "Healthy" condition patients? | Integer |
| Q6 | How many patients have "Hyperthyroidism"? | Integer |
| Q7 | What proportion of patients had "Osteoarthritis" in 2026? | Decimal (4dp) |
| Q8 | Which year had the greatest proportion of patients with "Rheumatoid Arthritis"? | Year (integer) |
| Q9 | How many patients have Osteoarthritis? | Integer |
| Q10 | How many patients have Viral Infection? | Integer |
| Q11 | How many patients have a lung infection? | Integer |
| Q12 | How many patients have a Gram-negative bacterial infection and are prescribed an antibiotic? | Integer |
| Q13 | How many patients have a Thiamine medication? | Integer |
| Q14 | How many patients have an ACE Inhibitors medication? | Integer |
| Q15 | How many patients have a Digoxin medication? | Integer |
| Q16 | How many patients have a Statins medication? | Integer |
| Q17 | How many patients are on both "ACE Inhibitors" AND "Calcium Channel Blockers"? | Integer |

### Test Data Prediction Questions (use test_kaggle.csv)

For these questions, you must predict answers using the test dataset where condition and medicine category columns have been removed.

| Question | Description | Answer Format |
|----------|-------------|---------------|
| Q18.1 | How many patients have Hyperlipidaemia? | Integer |
| Q18.2 | How many patients have Iron Deficiency Anaemia? | Integer |
| Q18.3 | How many patients have Hypothyroidism? | Integer |
| Q18.4 | How many patients have some sort of infection? | Integer |
| Q18.5 | How many patients with an infection would benefit from antibiotics? | Integer |
| Q18.6 | Submit full test dataset with condition predictions | CSV |

## Submission Format

```csv
Question,Answer
Q1,12744
Q2,20187
Q3,13086
...
```

## Evaluation

Submissions are scored using **MAPE (Mean Absolute Percentage Error)** across all questions.

### Formula

$$\text{MAPE} = \frac{1}{n} \sum_{i=1}^{n} \left| \frac{A_i - P_i}{A_i} \right| \times 100$$

Where:
- **A** = Actual (true) answer
- **P** = Predicted (submitted) answer
- **n** = Number of questions scored

A **lower MAPE is better**. A perfect submission scores 0.

### Scoring Details

- **Public leaderboard** (Q1–Q17): Scored immediately upon submission. These questions can be answered directly from the training data through data analysis, clinical knowledge, and SNOMED CT terminology lookups.
- **Private leaderboard** (Q18.1–Q18.6): Revealed at competition close. These questions require predicting condition counts in the test dataset where condition and medicine columns have been removed. You will need to use patterns learned from the training data (laboratory results, demographics, SNOMED codes) to infer conditions in the test set.

### Tips

- For count-based questions, round to the nearest integer.
- For proportion-based questions (Q4, Q7), provide a decimal value to 4 decimal places.
- For Q8, submit a 4-digit year.
- Small absolute answers (e.g. Q15 with a true answer in single digits) will have a large MAPE impact even for small errors — pay attention to rare conditions and medications.
- Q18.6 is scored on the accuracy of your full condition predictions across the test set.
