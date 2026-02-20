"""Population generator based on ABS demographic data."""

import re
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from common.types import PatientContext

_DEFAULT_DATA = Path(__file__).parent / "data" / "32350DS0001_2024.xlsx"

# Non-binary distribution by age group
NB_RATES = {
    "16_24": 0.025,   # 2.5% for ages 15-19, 20-24
    "25_74": 0.015,   # 1.5% for ages 25-74
    "75_plus": 0.005  # 0.5% for ages 75+
}


def load_abs_table(file_path, sheet_name):
    """Reads an ABS table and returns a cleaned dataframe."""
    df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=6, usecols="A:B,K:AB")
    df = df.rename(columns={df.columns[1]: "S/T name"})
    df = df.dropna(subset=["S/T name"])
    df = df[~df["S/T name"].str.contains("Total", case=False, na=False)]
    return df


def reshape_and_aggregate(df, sex):
    """Reshape ABS data to long form and aggregate by S/T name + Age group."""
    id_vars = ["S/T name"]
    value_vars = [col for col in df.columns if "Unnamed" not in col and col not in id_vars]

    melted = df.melt(id_vars=id_vars, value_vars=value_vars,
                     var_name="AgeGroup", value_name="Population")
    melted["Sex"] = sex

    melted["Population"] = pd.to_numeric(melted["Population"], errors="coerce").fillna(0)

    grouped = melted.groupby(["S/T name", "AgeGroup", "Sex"], as_index=False)["Population"].sum()
    return grouped


def combine_and_add_nonbinary(male_df, female_df):
    """Combine M/F and add non-binary group with proportional rates."""
    combined = pd.concat([male_df, female_df], ignore_index=True)
    totals = combined.groupby(["S/T name", "AgeGroup"], as_index=False)["Population"].sum()

    def get_nb_rate(age_group):
        age_group = str(age_group)
        if any(k in age_group for k in ["15\u201319", "20\u201324"]):
            return NB_RATES["16_24"]
        elif any(k in age_group for k in [
            "25\u201329", "30\u201334", "35\u201339", "40\u201344", "45\u201349",
            "50\u201354", "55\u201359", "60\u201364", "65\u201369", "70\u201374"
        ]):
            return NB_RATES["25_74"]
        elif any(k in age_group for k in ["75\u201379", "80\u201384", "85"]):
            return NB_RATES["75_plus"]
        else:
            return 0

    totals["Population"] = pd.to_numeric(totals["Population"], errors="coerce").fillna(0)
    totals["NB_rate"] = totals["AgeGroup"].apply(get_nb_rate)

    totals["NB_pop"] = (totals["Population"] * totals["NB_rate"]).round()
    totals["Sex"] = "Non-binary"

    nb_df = totals.loc[totals["NB_pop"] > 0, ["S/T name", "AgeGroup", "Sex", "NB_pop"]]
    nb_df = nb_df.rename(columns={"NB_pop": "Population"})

    combined_all = pd.concat([combined, nb_df], ignore_index=True)
    return combined_all


def parse_age_range(age_group) -> Tuple[Optional[int], Optional[int]]:
    """Parse age group string and return (min_age, max_age)."""
    age_group = str(age_group).strip()

    if "85" in age_group and ("over" in age_group.lower() or "+" in age_group):
        return (85, 100)

    numbers = re.findall(r'\d+', age_group)

    if len(numbers) >= 2:
        return (int(numbers[0]), int(numbers[1]))
    elif len(numbers) == 1:
        age = int(numbers[0])
        return (age, age)
    else:
        return (None, None)


def assign_lifestyle_factors(age, sex):
    """Assign lifestyle factors based on age and sex with realistic probability distributions.

    Args:
        age: int, age of the individual
        sex: str, any case accepted ("Male", "male", "Female", "female", etc.)

    Returns:
        list of lifestyle factors (can be empty or contain multiple factors)
    """
    factors = []

    sex_lower = str(sex).lower()
    is_male = sex_lower == "male"
    is_female = sex_lower == "female"

    # === SMOKER ===
    if age >= 16:
        if age < 25:
            smoker_rate = 0.08
        elif age < 35:
            smoker_rate = 0.10
        elif age < 45:
            smoker_rate = 0.11
        elif age < 55:
            smoker_rate = 0.12
        elif age < 65:
            smoker_rate = 0.149
        elif age < 75:
            smoker_rate = 0.11
        else:
            smoker_rate = 0.07

        if is_male:
            smoker_rate *= 1.19
        elif is_female:
            smoker_rate *= 0.82

        if np.random.random() < smoker_rate:
            factors.append("smoker")

    # === HEAVY DRINKER ===
    if age >= 14:
        if age < 18:
            drinker_rate = 0.15
        elif age < 25:
            drinker_rate = 0.361
        elif age < 30:
            drinker_rate = 0.30
        elif age < 40:
            drinker_rate = 0.28
        elif age < 50:
            drinker_rate = 0.29
        elif age < 60:
            drinker_rate = 0.323
        elif age < 70:
            drinker_rate = 0.332
        else:
            drinker_rate = 0.25

        if is_male:
            drinker_rate *= 1.15
        elif is_female:
            drinker_rate *= 0.58

        if np.random.random() < drinker_rate:
            factors.append("heavy_drinker")

    # === SEDENTARY vs ATHLETE (mutually exclusive) ===
    if age < 15:
        sedentary_rate = 0.70
        athlete_rate = 0.36
    elif age < 18:
        sedentary_rate = 0.83
        athlete_rate = 0.42
    elif age < 25:
        sedentary_rate = 0.34
        athlete_rate = 0.42
    elif age < 35:
        sedentary_rate = 0.36
        athlete_rate = 0.66
    elif age < 45:
        sedentary_rate = 0.38
        athlete_rate = 0.60
    elif age < 55:
        sedentary_rate = 0.40
        athlete_rate = 0.55
    elif age < 65:
        sedentary_rate = 0.42
        athlete_rate = 0.50
    else:
        sedentary_rate = 0.57
        athlete_rate = 0.40

    if age >= 18 and age < 65:
        if is_male:
            sedentary_rate *= 0.92
        elif is_female:
            sedentary_rate *= 1.11

    activity_roll = np.random.random()
    if activity_roll < athlete_rate:
        factors.append("athlete")
    elif activity_roll < athlete_rate + sedentary_rate:
        factors.append("sedentary")

    # === HIGH BMI ===
    if age < 2:
        high_bmi_rate = 0.10
    elif age < 5:
        high_bmi_rate = 0.196
    elif age < 15:
        high_bmi_rate = 0.26
    elif age < 18:
        high_bmi_rate = 0.294
    elif age < 25:
        high_bmi_rate = 0.50
    elif age < 35:
        high_bmi_rate = 0.60
    elif age < 45:
        high_bmi_rate = 0.65
    elif age < 55:
        high_bmi_rate = 0.68
    elif age < 65:
        high_bmi_rate = 0.70
    elif age < 75:
        high_bmi_rate = 0.68
    else:
        high_bmi_rate = 0.60

    if age >= 18:
        if is_male:
            high_bmi_rate *= 1.08
        elif is_female:
            high_bmi_rate *= 0.93

    if np.random.random() < high_bmi_rate:
        factors.append("high_bmi")

    return factors


def generate_height_weight(age, sex, has_high_bmi=False):
    """Generate realistic height (cm) and weight (kg) based on Australian population statistics.

    Args:
        age: int, age of the individual
        sex: str, any case accepted ("Male", "male", "Female", "female", etc.)
        has_high_bmi: bool, whether to adjust weight to ensure BMI > 30

    Returns:
        tuple: (height_cm, weight_kg) as integers
    """
    sex_lower = str(sex).lower()
    is_male = sex_lower == "male"
    is_female = sex_lower == "female"

    # Infants and toddlers (0-2 years)
    if age < 1:
        height = np.random.normal(75, 5)
        weight = np.random.normal(9, 1.5)
    elif age < 3:
        height = np.random.normal(90, 5)
        weight = np.random.normal(13, 2)
    # Children (3-12 years)
    elif age < 13:
        if is_male or not is_female:
            height = 90 + (age - 3) * 6 + np.random.normal(0, 4)
            weight = 13 + (age - 3) * 3 + np.random.normal(0, 3)
        else:
            height = 90 + (age - 3) * 6 + np.random.normal(0, 4)
            weight = 13 + (age - 3) * 2.8 + np.random.normal(0, 3)
    # Adolescents (13-17 years)
    elif age < 18:
        if is_male or not is_female:
            height = 150 + (age - 13) * 5 + np.random.normal(0, 6)
            weight = 45 + (age - 13) * 7 + np.random.normal(0, 8)
        else:
            height = 145 + (age - 13) * 3.5 + np.random.normal(0, 5)
            weight = 45 + (age - 13) * 5 + np.random.normal(0, 7)
    # Adults (18+ years)
    else:
        if is_male:
            height = np.random.normal(175.6, 7)
            weight = np.random.normal(85.9, 15)
        elif is_female:
            height = np.random.normal(161.8, 6.5)
            weight = np.random.normal(71.1, 14)
        else:
            height = np.random.normal(168.7, 9)
            weight = np.random.normal(78.5, 15)

        if age >= 65:
            height -= np.random.uniform(0, 3)
        if age >= 75:
            height -= np.random.uniform(0, 2)
            weight -= np.random.uniform(0, 5)

    height = max(45, min(220, height))
    weight = max(2, min(250, weight))

    height = round(height)
    weight = round(weight)

    if has_high_bmi:
        height_m = height / 100
        bmi = weight / (height_m ** 2)
        while bmi <= 30:
            weight += np.random.randint(1, 7)
            bmi = weight / (height_m ** 2)

    return height, weight


def _load_demographic_frame(file_path: Optional[str] = None) -> pd.DataFrame:
    """Load and prepare the ABS demographic DataFrame."""
    fp = file_path or str(_DEFAULT_DATA)
    male_df = load_abs_table(fp, "Table 1")
    female_df = load_abs_table(fp, "Table 2")
    male_grouped = reshape_and_aggregate(male_df, "Male")
    female_grouped = reshape_and_aggregate(female_df, "Female")
    combined = combine_and_add_nonbinary(male_grouped, female_grouped)
    return combined


def generate_contexts(
    n: int,
    file_path: Optional[str] = None,
) -> List[PatientContext]:
    """Generate n PatientContext objects weighted by ABS population data.

    This is the standardised module interface for the population module.
    """
    combined = _load_demographic_frame(file_path)
    combined = combined.rename(columns={"S/T name": "State"})
    combined["Weight"] = combined["Population"] / combined["Population"].sum()

    sampled = combined.sample(n=n, weights="Weight", replace=True).reset_index(drop=True)

    contexts = []
    for _, row in sampled.iterrows():
        age_range = parse_age_range(row["AgeGroup"])
        if age_range[0] is None:
            continue
        age = int(np.random.randint(age_range[0], age_range[1] + 1))
        sex_title = row["Sex"]  # "Male", "Female", "Non-binary"

        lifestyle = assign_lifestyle_factors(age, sex_title)
        has_high_bmi = "high_bmi" in lifestyle
        height, weight = generate_height_weight(age, sex_title, has_high_bmi)

        ctx = PatientContext(
            sex=sex_title,       # __post_init__ lowercases
            age=age,
            lifestyle=lifestyle,
            state=row["State"],
            height_cm=int(height),
            weight_kg=int(weight),
        )
        contexts.append(ctx)

    return contexts
