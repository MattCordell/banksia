"""
Analyse generated patient data and produce a metrics summary.

Reads raw_data.csv from the same directory, computes Q1-Q34 boolean flag
columns, and writes metrics.txt, TrainingDataSet.csv, solution.csv,
and sample_submission.csv.
"""

import os
import random

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

MED_CATS = ["Medicine_1_Category", "Medicine_2_Category", "Medicine_3_Category"]
MED_DISPLAYS = ["Medicine_1_Display", "Medicine_2_Display", "Medicine_3_Display"]


def load_data():
    return pd.read_csv(os.path.join(SCRIPT_DIR, "raw_data.csv"))


def add_derived_columns(df):
    """Add Year, BMI, and CholHDL_Ratio columns."""
    df["Year"] = pd.to_datetime(df["EncounterDate"]).dt.year
    df["BMI"] = df["Weight_kg"] / (df["Height_cm"] / 100) ** 2
    chol_col = "Lipid Panel - Total Cholesterol (mmol/L)"
    hdl_col = "Lipid Panel - HDL (mmol/L)"
    if chol_col in df.columns and hdl_col in df.columns:
        df["CholHDL_Ratio"] = df[chol_col] / df[hdl_col]
    return df


def has_med_category(df, category):
    """Return boolean mask for patients with the given medicine category in any slot."""
    return df[MED_CATS].eq(category).any(axis=1)


def has_med_display(df, pattern):
    """Return boolean mask for patients with pattern in any Medicine Display."""
    return pd.DataFrame(
        {col: df[col].str.contains(pattern, case=False, na=False) for col in MED_DISPLAYS}
    ).any(axis=1)


def count_med_display_matches(df, pattern):
    """Count how many medicine slots contain pattern in Display (case-insensitive)."""
    return pd.DataFrame(
        {col: df[col].str.contains(pattern, case=False, na=False) for col in MED_DISPLAYS}
    ).sum(axis=1)


def best_egfr(df):
    """Return eGFR series, preferring MBAP panel, falling back to Kidney Function."""
    mbap = "MBAP - eGFR (mL/min/1.73m\u00b2)"
    kf = "Kidney Function - eGFR (mL/min/1.73m\u00b2)"
    return df[mbap].fillna(df[kf]) if kf in df.columns else df[mbap]


def best_potassium(df):
    """Return potassium series, preferring MBAP panel."""
    mbap = "MBAP - Potassium (mmol/L)"
    kf = "Kidney Function - Potassium (mmol/L)"
    return df[mbap].fillna(df[kf]) if kf in df.columns else df[mbap]


def condition_counts(df):
    """Return condition value counts as a formatted string."""
    counts = df["Condition"].value_counts().sort_index()
    lines = []
    for condition, count in counts.items():
        lines.append(f"    {condition}: {count}")
    return "\n".join(lines)


def compute_flags(df):
    """Compute Q1-Q34 boolean flag columns on the dataframe. Returns dict of {col: Series}."""
    flags = {}

    # Q1: Female
    flags["Q1"] = df["Sex"] == "female"

    # Q2: Adult (Age >= 18)
    flags["Q2"] = df["Age"] >= 18

    # Q3: Obese (BMI >= 30) with Chol:HDL > 5
    flags["Q3"] = (df["BMI"] >= 30) & (df["CholHDL_Ratio"] > 5)

    # Q4: Healthy condition
    flags["Q4"] = df["Condition"] == "Healthy"

    # Q5: Hyperthyroidism
    flags["Q5"] = df["Condition"] == "Hyperthyroidism"

    # Q6: Hyperthyroidism in 2021
    flags["Q6"] = (df["Condition"] == "Hyperthyroidism") & (df["Year"] == 2021)

    # Q7: Osteoarthritis in 2023
    flags["Q7"] = (df["Condition"] == "Osteoarthritis") & (df["Year"] == 2023)

    # Q8: Osteoarthritis in 2024
    flags["Q8"] = (df["Condition"] == "Osteoarthritis") & (df["Year"] == 2024)

    # Q9: Osteoarthritis in 2025
    flags["Q9"] = (df["Condition"] == "Osteoarthritis") & (df["Year"] == 2025)

    # Q10: Osteoarthritis in 2026
    flags["Q10"] = (df["Condition"] == "Osteoarthritis") & (df["Year"] == 2026)

    # Q11: Rheumatoid Arthritis in 2021
    flags["Q11"] = (df["Condition"] == "Rheumatoid Arthritis") & (df["Year"] == 2021)

    # Q12: Rheumatoid Arthritis in 2022
    flags["Q12"] = (df["Condition"] == "Rheumatoid Arthritis") & (df["Year"] == 2022)

    # Q13: Rheumatoid Arthritis in 2023
    flags["Q13"] = (df["Condition"] == "Rheumatoid Arthritis") & (df["Year"] == 2023)

    # Q14: Thiamine medication
    flags["Q14"] = has_med_category(df, "Thiamine")

    # Q15: ACE Inhibitors medication
    flags["Q15"] = has_med_category(df, "ACE Inhibitors")

    # Q16: Digoxin medication
    flags["Q16"] = has_med_category(df, "Digoxin")

    # Q17: Statins medication
    flags["Q17"] = has_med_category(df, "Statins (HMG-CoA reductase inhibitor)")

    # Q18: Both ACE Inhibitors AND Calcium Channel Blockers
    flags["Q18"] = (
        has_med_category(df, "ACE Inhibitors")
        & has_med_category(df, "Calcium Channel Blockers")
    )

    # Q19: Fungal Infection with foot-related SNOMED Display
    foot_pattern = r"(?i)(?:pedis|foot|feet|plantar|toe[\s,]|toenail|hallux)"
    flags["Q19"] = (
        (df["Condition"] == "Fungal Infection")
        & df["SNOMED_Display"].str.contains(foot_pattern, na=False)
    )

    # Q20: >1 product containing paracetamol
    flags["Q20"] = count_med_display_matches(df, r"paracetamol") >= 2

    # Q21: "bilateral" in SNOMED_Display
    flags["Q21"] = df["SNOMED_Display"].str.contains(r"(?i)bilateral", na=False)

    # Q22: Metformin (Biguanide) with eGFR < 30
    flags["Q22"] = has_med_category(df, "Biguanide hypoglycaemic agent") & (best_egfr(df) < 30)

    # Q23: Hand/wrist terms in SNOMED_Display
    hand_wrist_pattern = r"(?i)(?:hand|wrist|carpal|metacarpo|finger|digit|phalanx|phalangeal)"
    flags["Q23"] = df["SNOMED_Display"].str.contains(hand_wrist_pattern, na=False)

    # Q24: Females 15-49 prescribed ACE Inhibitors or ARBs
    female_15_49 = (df["Sex"] == "female") & (df["Age"] >= 15) & (df["Age"] <= 49)
    acei_or_arb = (
        has_med_category(df, "ACE Inhibitors")
        | has_med_category(df, "Angiotensin Receptor Blockers")
        | has_med_category(df, "ACE Inhibitors / ARBs")
    )
    flags["Q24"] = female_15_49 & acei_or_arb

    # Q25: Females 15-49 prescribed Methotrexate
    flags["Q25"] = female_15_49 & has_med_category(df, "Methotrexate")

    # Q26: Females 50+ prescribed Methotrexate
    female_50_plus = (df["Sex"] == "female") & (df["Age"] >= 50)
    flags["Q26"] = female_50_plus & has_med_category(df, "Methotrexate")

    # Q27: Pregnant patients prescribed teratogenic medicines
    # (ACE Inhibitors, ARBs, Methotrexate, Macrolides/Tetracyclines, Carbimazole by display)
    pregnant = df["Condition"] == "Pregnancy"
    teratogenic = (
        has_med_category(df, "ACE Inhibitors")
        | has_med_category(df, "ACE Inhibitors / ARBs")
        | has_med_category(df, "Angiotensin Receptor Blockers")
        | has_med_category(df, "Methotrexate")
        | has_med_category(df, "Macrolides / Tetracyclines")
        | has_med_display(df, r"carbimazole")
    )
    flags["Q27"] = pregnant & teratogenic

    # Q28: Female RA patients aged 15-49
    flags["Q28"] = (
        (df["Condition"] == "Rheumatoid Arthritis")
        & (df["Sex"] == "female")
        & (df["Age"] >= 15)
        & (df["Age"] <= 49)
    )

    # Q29: OA/RA on NSAIDs with eGFR < 60
    oa_ra = df["Condition"].isin(["Osteoarthritis", "Rheumatoid Arthritis"])
    on_nsaids = has_med_category(df, "Oral NSAIDs")
    flags["Q29"] = oa_ra & on_nsaids & (best_egfr(df) < 60)

    # Q30: Cirrhosis on NSBB
    flags["Q30"] = (
        (df["Condition"] == "Chronic Liver Disease / Cirrhosis")
        & has_med_category(df, "Non-Selective Beta-Blockers")
    )

    # Q31: Digoxin + eGFR<30 + loop diuretic (toxicity risk)
    flags["Q31"] = (
        has_med_category(df, "Digoxin")
        & (best_egfr(df) < 30)
        & has_med_category(df, "Loop Diuretics")
    )

    # Q32: Digoxin with hypokalaemia (Potassium < 3.5)
    flags["Q32"] = has_med_category(df, "Digoxin") & (best_potassium(df) < 3.5)

    # Q33: Pregnant patients with fasting glucose >= 5.1 mmol/L
    gluc_col = "MBAP - Glucose (fasting) (mmol/L)"
    flags["Q33"] = (df["Condition"] == "Pregnancy") & (df[gluc_col] >= 5.1)

    # Q34: Pseudomonadaceae infection not caused by Pseudomonas sp.
    flags["Q34"] = (
        df["SNOMED_Display"].str.contains(r"(?i)pseudomonad", na=False)
        & ~df["SNOMED_Display"].str.contains(r"(?i)pseudomonas", na=False)
    )

    return flags


# Question text for metrics output
QUESTIONS = {
    1: 'How many females in the dataset',
    2: 'How many adults (Age >= 18)',
    3: 'How many obese patients (BMI >= 30) have Chol:HDL > 5',
    4: 'How many "Healthy" condition patients',
    5: 'How many patients have "Hyperthyroidism"',
    6: 'How many patients had "Hyperthyroidism" in 2021',
    7: 'How many patients had "Osteoarthritis" in 2023',
    8: 'How many patients had "Osteoarthritis" in 2024',
    9: 'How many patients had "Osteoarthritis" in 2025',
    10: 'How many patients had "Osteoarthritis" in 2026',
    11: 'How many patients had "Rheumatoid Arthritis" in 2021',
    12: 'How many patients had "Rheumatoid Arthritis" in 2022',
    13: 'How many patients had "Rheumatoid Arthritis" in 2023',
    14: 'How many patients have a Thiamine medication',
    15: 'How many patients have an ACE Inhibitors medication',
    16: 'How many patients have a Digoxin medication',
    17: 'How many patients have a Statins medication',
    18: 'How many patients are on both "ACE Inhibitors" AND "Calcium Channel Blockers"',
    19: 'How many Fungal Infection patients with foot-related SNOMED Display',
    20: 'How many Patients on >1 product containing paracetamol',
    21: 'How many Patients with "bilateral" in SNOMED_Display',
    22: 'How many Metformin patients with eGFR<30',
    23: 'How many Patients with hand/wrist terms in SNOMED_Display',
    24: 'How many Females 15-49 prescribed ACE Inhibitors or ARBs',
    25: 'How many Females 15-49 prescribed Methotrexate',
    26: 'How many Females 50+ prescribed Methotrexate',
    27: 'How many pregnant patients prescribed Teratogenic Medicines '
        '(ACE inhibitors, ARBs, Methotrexate, Tetracycline, Carbimazole)',
    28: 'How many female RA patients aged 15-49',
    29: 'How many OA/RA on NSAIDs with eGFR < 60 (subclinical renal impairment)',
    30: 'How many Cirrhosis on NSBB',
    31: 'How many patients prescribed digoxin + eGFR<30 + loop diuretic (toxicity risk)',
    32: 'How many patients prescribed digoxin have hypokalaemia (Potassium <3.5)',
    33: 'How many pregnant patients have a Glucose 5.1 mmol/L or greater',
    34: 'How many patients have a Pseudomonadaceae infection - not caused by Pseudomonas sp.',
}


def compute_metrics(df):
    """Produce metrics text from the flagged dataframe."""
    lines = []

    lines.append("=" * 60)
    lines.append("Analytics Questions")
    lines.append("=" * 60)
    lines.append("")

    for q_num in sorted(QUESTIONS):
        col = f"Q{q_num}"
        count = int(df[col].sum())
        lines.append(f"Q{q_num}. {QUESTIONS[q_num]}: {count}")

    lines.append("")
    lines.append("=" * 60)
    lines.append("DATA SUMMARY")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Total rows: {len(df)}")
    lines.append("")
    lines.append("Condition counts:")
    lines.append(condition_counts(df))

    return "\n".join(lines)


def main():
    print("Loading data...")
    df = load_data()

    print("Computing derived columns...")
    df = add_derived_columns(df)

    print("Computing Q1-Q34 flags...")
    flags = compute_flags(df)
    flag_df = pd.DataFrame(flags, index=df.index)
    df = pd.concat([df, flag_df], axis=1)

    print("Computing metrics...")
    output = compute_metrics(df)

    # Write metrics.txt
    metrics_path = os.path.join(SCRIPT_DIR, "metrics.txt")
    with open(metrics_path, "w") as f:
        f.write(output)
        f.write("\n")
    print(f"Metrics written to {metrics_path}")

    q_cols = [f"Q{i}" for i in range(1, 35)]
    drop_cols = ["Year", "BMI", "CholHDL_Ratio"]

    # Write TrainingDataSet.csv (Episode Number + original data columns, no Q flags)
    training_exclude = q_cols + drop_cols + [
        "Age", "LifestyleFactors", "Condition",
        "Medicine_1_Category", "Medicine_2_Category", "Medicine_3_Category",
    ]
    training_cols = [c for c in df.columns if c not in training_exclude]
    training_df = df[training_cols].rename(columns={
        "SNOMED_Code": "Clinical_Note_Code",
        "SNOMED_Display": "Clinical_Note_Display",
    })
    training_path = os.path.join(SCRIPT_DIR, "TrainingDataSet.csv")
    training_df.to_csv(training_path, index=False)
    print(f"Training dataset written to {training_path}")

    # Write solution.csv (Episode Number + Q flag columns only + Usage for Kaggle)
    solution_path = os.path.join(SCRIPT_DIR, "solution.csv")
    solution_df = df[["Episode Number"] + q_cols].copy()
    solution_df["Usage"] = ["Public" if i % 2 == 0 else "Private" for i in range(len(solution_df))]
    solution_df.to_csv(solution_path, index=False)
    print(f"Solution written to {solution_path}")

    # Write sample_submission.csv (Episode Number + random Q flags)
    rng = random.Random(42)
    sample_df = df[["Episode Number"]].copy()
    for col in q_cols:
        sample_df[col] = [rng.choice([True, False]) for _ in range(len(sample_df))]
    sample_path = os.path.join(SCRIPT_DIR, "sample_submission.csv")
    sample_df.to_csv(sample_path, index=False)
    print(f"Sample submission written to {sample_path}")

    print()
    print(output)


if __name__ == "__main__":
    main()
