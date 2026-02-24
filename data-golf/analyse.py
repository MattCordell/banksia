"""
Analyse generated patient data and produce a metrics summary.

Reads train_raw.csv and test_raw.csv from the same directory,
computes numbered metrics, and writes metrics.txt.
"""

import os

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_data():
    train = pd.read_csv(os.path.join(SCRIPT_DIR, "train_raw.csv"))
    test = pd.read_csv(os.path.join(SCRIPT_DIR, "test_raw.csv"))
    return train, test


def add_derived_columns(df):
    """Add Year, BMI, and CholHDL_Ratio columns."""
    df["Year"] = pd.to_datetime(df["EncounterDate"]).dt.year
    df["BMI"] = df["Weight_kg"] / (df["Height_cm"] / 100) ** 2
    chol_col = "Lipid Panel - Total Cholesterol (mmol/L)"
    hdl_col = "Lipid Panel - HDL (mmol/L)"
    if chol_col in df.columns and hdl_col in df.columns:
        df["CholHDL_Ratio"] = df[chol_col] / df[hdl_col]
    return df


def count_med_category(df, category):
    """Count patients who have the given medicine category in any slot."""
    mask = (
        (df["Medicine_1_Category"] == category)
        | (df["Medicine_2_Category"] == category)
        | (df["Medicine_3_Category"] == category)
    )
    return int(mask.sum())


def condition_proportion_by_year(df, condition, year):
    """Proportion of patients with the given condition in a specific year."""
    year_df = df[df["Year"] == year]
    if len(year_df) == 0:
        return 0.0
    return (year_df["Condition"] == condition).sum() / len(year_df)


def condition_counts(df):
    """Return condition value counts as a formatted string."""
    counts = df["Condition"].value_counts().sort_index()
    lines = []
    for condition, count in counts.items():
        lines.append(f"    {condition}: {count}")
    return "\n".join(lines)


def compute_metrics(train, test):
    lines = []

    def add(num, question, answer):
        lines.append(f"Q{num}. {question}: {answer}")

    def add_block(num, question, block):
        lines.append(f"Q{num}. {question}:\n{block}")

    # --- TRAIN metrics ---
    lines.append("=" * 60)
    lines.append("TRAIN DATA METRICS")
    lines.append("=" * 60)
    lines.append("")

    # Q1: Count of females
    female_count = int((train["Sex"] == "female").sum())
    add(1, "How many females in the dataset", female_count)

    # Q2: Count of adults
    adult_count = int((train["Age"] >= 18).sum())
    add(2, "How many adults (Age >= 18)", adult_count)

    # Q3: Proportion of obese patients with Chol:HDL > 5
    obese = train[train["BMI"] >= 30].copy()
    obese_with_lipids = obese.dropna(subset=["CholHDL_Ratio"])
    if len(obese_with_lipids) > 0:
        high_chol_hdl = (obese_with_lipids["CholHDL_Ratio"] > 5).sum()
        prop_obese_high = high_chol_hdl / len(obese_with_lipids)
    else:
        prop_obese_high = 0.0
    add(
        3,
        "Proportion of obese patients (BMI >= 30) with Chol:HDL > 5",
        f"{prop_obese_high:.4f} ({int(high_chol_hdl)} of {len(obese_with_lipids)} obese patients with lipid data)",
    )

    # Q4: Count of Healthy patients
    healthy_count = int((train["Condition"] == "Healthy").sum())
    add(4, 'How many "Healthy" condition patients', healthy_count)

    # Q5: Count of Hyperthyroidism patients
    hyper_count = int((train["Condition"] == "Hyperthyroidism").sum())
    add(5, 'How many patients have "Hyperthyroidism"', hyper_count)

    # Q6: Count of Hyperthyroidism in 2021
    hyper_2021 = int(
        ((train["Condition"] == "Hyperthyroidism") & (train["Year"] == 2021)).sum()
    )
    add(6, 'How many patients had "Hyperthyroidism" in 2021', hyper_2021)

    lines.append("")

    # Q7-Q12: Osteoarthritis proportion per year
    oa_props = {}
    years = range(2021, 2027)
    for i, year in enumerate(years):
        prop = condition_proportion_by_year(train, "Osteoarthritis", year)
        oa_props[year] = prop
        add(
            7 + i,
            f'Proportion of patients with "Osteoarthritis" in {year}',
            f"{prop:.4f}",
        )

    # Q13: Year with greatest Osteoarthritis proportion
    max_oa_year = max(oa_props, key=oa_props.get)
    add(
        13,
        'Year with greatest proportion of "Osteoarthritis"',
        f"{max_oa_year} ({oa_props[max_oa_year]:.4f})",
    )

    # Q14: Average Osteoarthritis proportion
    avg_oa = sum(oa_props.values()) / len(oa_props)
    add(
        14,
        'Average proportion of "Osteoarthritis" across 2021-2026',
        f"{avg_oa:.4f}",
    )

    lines.append("")

    # Q15-Q20: Rheumatoid Arthritis proportion per year
    ra_props = {}
    for i, year in enumerate(years):
        prop = condition_proportion_by_year(train, "Rheumatoid Arthritis", year)
        ra_props[year] = prop
        add(
            15 + i,
            f'Proportion of patients with "Rheumatoid Arthritis" in {year}',
            f"{prop:.4f}",
        )

    # Q21: Year with greatest RA proportion
    max_ra_year = max(ra_props, key=ra_props.get)
    add(
        21,
        'Year with greatest proportion of "Rheumatoid Arthritis"',
        f"{max_ra_year} ({ra_props[max_ra_year]:.4f})",
    )

    lines.append("")

    # Q22: Condition distribution (train)
    add_block(22, "Condition counts across whole train dataset", condition_counts(train))

    lines.append("")

    # --- TEST metrics ---
    lines.append("=" * 60)
    lines.append("TEST DATA METRICS")
    lines.append("=" * 60)
    lines.append("")

    # Q23: Condition distribution (test)
    add_block(23, "Condition counts across whole test dataset", condition_counts(test))

    lines.append("")

    # --- Additional TRAIN metrics ---
    lines.append("=" * 60)
    lines.append("ADDITIONAL TRAIN METRICS - MEDICATIONS")
    lines.append("=" * 60)
    lines.append("")

    # Q25-Q27: Medicine counts
    thiamine_count = count_med_category(train, "Thiamine")
    add(25, "How many patients have a Thiamine medication", thiamine_count)

    ace_count = count_med_category(train, "ACE Inhibitors")
    add(26, "How many patients have an ACE Inhibitors medication", ace_count)

    digoxin_count = count_med_category(train, "Digoxin")
    add(27, "How many patients have a Digoxin medication", digoxin_count)

    statins_count = count_med_category(train, "Statins (HMG-CoA reductase inhibitor)")
    add(28, "How many patients have a Statins medication", statins_count)

    # Q29: Patients on both ACE Inhibitors AND Calcium Channel Blockers
    med_cols = ["Medicine_1_Category", "Medicine_2_Category", "Medicine_3_Category"]
    has_ace = train[med_cols].eq("ACE Inhibitors").any(axis=1)
    has_ccb = train[med_cols].eq("Calcium Channel Blockers").any(axis=1)
    both_count = int((has_ace & has_ccb).sum())
    add(29, 'How many patients are on both "ACE Inhibitors" AND "Calcium Channel Blockers"', both_count)

    return "\n".join(lines)


def main():
    print("Loading data...")
    train, test = load_data()

    print("Computing derived columns...")
    train = add_derived_columns(train)
    test = add_derived_columns(test)

    print("Computing metrics...")
    output = compute_metrics(train, test)

    out_path = os.path.join(SCRIPT_DIR, "metrics.txt")
    with open(out_path, "w") as f:
        f.write(output)
        f.write("\n")

    print(f"Metrics written to {out_path}")
    print()
    print(output)


if __name__ == "__main__":
    main()
