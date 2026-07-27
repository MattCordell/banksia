"""
Analyse generated patient data and produce a metrics summary.

Reads raw_data.csv from the same directory, computes Q1-Q37 boolean flag
columns, and writes metrics.txt, TrainingDataSet.csv, solution.csv,
and sample_submission.csv.

Each question has a dedicated ``q<nn>_*`` function that takes the dataframe
and a per-edition :class:`CodeSets` and returns a boolean Series. The
``QUESTION_FUNCS`` registry maps question number to function, and ``QUESTIONS``
holds the criterion-phrased description of what each flag means.

Criteria are expressed against the columns that are actually published in
TrainingDataSet.csv (Clinical_Note_Code/Display, Medicine_*_Code/Display, labs
and demographics). ``Condition`` and ``Medicine_*_Category`` are generator
bookkeeping and are withheld from competitors, so questions that still rely on
them are marked in the notes below and cannot be answered from the released
data.
"""

import os
import random
import sys
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Dict, Optional, Set

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TX_SERVER = "https://r4.ontoserver.csiro.au/fhir"

SNOMED_CODE_COLS = ["SNOMED_Code", "Medicine_1_Code", "Medicine_2_Code", "Medicine_3_Code"]

# Must stay in sync with generate_data.py PERIODS.
# Each period covers the active SNOMED CT-AU edition from the day after publication.
PERIODS = [
    {"start": date(2021, 2, 1), "end": date(2022, 1, 31), "edition": "20210131"},
    {"start": date(2022, 2, 1), "end": date(2023, 1, 31), "edition": "20220131"},
    {"start": date(2023, 2, 1), "end": date(2024, 1, 31), "edition": "20230131"},
    {"start": date(2024, 2, 1), "end": date(2025, 1, 31), "edition": "20240131"},
    {"start": date(2025, 2, 1), "end": date(2026, 1, 31), "edition": "20250131"},
    {"start": date(2026, 2, 1), "end": date(2027, 1, 31), "edition": "20260131"},
]


def edition_for_date(d: date) -> str:
    """Return the SNOMED CT-AU edition string for a given encounter date."""
    for period in PERIODS:
        if period["start"] <= d <= period["end"]:
            return period["edition"]
    return PERIODS[-1]["edition"]  # fallback to latest

MED_CATS = ["Medicine_1_Category", "Medicine_2_Category", "Medicine_3_Category"]
MED_DISPLAYS = ["Medicine_1_Display", "Medicine_2_Display", "Medicine_3_Display"]
MED_CODES = ["Medicine_1_Code", "Medicine_2_Code", "Medicine_3_Code"]


def load_data():
    return pd.read_csv(
        os.path.join(SCRIPT_DIR, "raw_data.csv"),
        dtype={col: str for col in SNOMED_CODE_COLS},
    )


def ecl_code_set(ecl: str, tx_server: str, edition: str = None) -> set:
    """Expand an ECL expression via Ontoserver and return the set of concept codes."""
    from conditions.snomed import expand_ecl
    concepts = expand_ecl(ecl, tx_server=tx_server, edition=edition)
    return {c["code"] for c in concepts}


def resolve_ecl_template(template_key: str) -> str:
    """Look up a named product ECL template from medicines/ecl_templates.json."""
    from medicines.generator import resolve_ecl_template as _resolve
    return _resolve(template_key)


def best_cholesterol(df):
    """Return total cholesterol, preferring the Lipid Panel, falling back to MBAP.

    The lipid panel is absent on a minority of rows; MBAP carries a total
    cholesterol for most of them, so the fallback widens Q3's coverage.
    """
    lipid = "Lipid Panel - Total Cholesterol (mmol/L)"
    mbap = "MBAP - Cholesterol (mmol/L)"
    if lipid not in df.columns:
        return df[mbap]
    return df[lipid].fillna(df[mbap]) if mbap in df.columns else df[lipid]


def add_derived_columns(df):
    """Add Year, BMI, and CholHDL_Ratio columns."""
    df["Year"] = pd.to_datetime(df["EncounterDate"]).dt.year
    df["BMI"] = df["Weight_kg"] / (df["Height_cm"] / 100) ** 2
    hdl_col = "Lipid Panel - HDL (mmol/L)"
    if hdl_col in df.columns:
        df["CholHDL_Ratio"] = best_cholesterol(df) / df[hdl_col]
    return df


def has_med_category(df, category):
    """Return boolean mask for patients with the given medicine category in any slot."""
    return df[MED_CATS].eq(category).any(axis=1)


def product_ecl_template_for_edition(edition):
    """Return the ecl_templates.json key matching the product model used for edition.

    Must stay in sync with generate_data.py PERIODS: "product" (SNOMED CT international
    medicinal product hierarchy) pre-2025, "amt-tpuu" (AMT Trade Product Unit of Use) from
    2025 onwards.
    """
    return "amt-tpuu" if edition >= "20250131" else "product"


# ---------------------------------------------------------------------------
# ECL definitions
#
# Condition criteria are matched against SNOMED_Code (published as
# Clinical_Note_Code) rather than the withheld Condition label, because the
# label is a sampling bucket and the coded concept is often only loosely
# related to it (e.g. a "Hyperthyroidism" row coded as
# |Dysprealbuminaemic euthyroidal hyperthyroxinaemia|).
# ---------------------------------------------------------------------------

CONDITION_ECLS = {
    # Q4. |Healthy| plus |No current problems or disability|, which is not a
    # descendant of |Healthy| but carries the same meaning here.
    "healthy": "(<<102499006) OR (<<160245001)",
    # Q5. |Hyperthyroidism|.
    "hyperthyroidism": "<<34486009",
    # Q8 (and the other osteoarthritis-year questions, if switched over).
    # SNOMED classifies |Gout| and |Chondrocalcinosis| beneath |Osteoarthritis|;
    # both are excluded so the criterion means degenerative OA.
    "osteoarthritis": "(<<396275006) MINUS ((<<90560007) OR (<<239838005))",
    "rheumatoid_arthritis": "<<69896004",
    # Q19. Mycosis with a foot finding site, plus |Tinea pedis| explicitly
    # (its finding site is a skin structure that is not subsumed by
    # |Foot structure|). Returns 0 on small cohorts.
    "fungal_foot": "(<<3218000) AND ((<404684003:363698007=(<<56459004)) OR (<<6020002))",
    # Q21. Laterality is not modelled on these disorders, so an attribute-based
    # ECL expands to nothing; a term filter is the terminology-native
    # equivalent of scanning the display string.
    "bilateral": '<<404684003 {{ term = "bilateral" }}',
    # Q27, Q33. |Pregnant| minus postnatal/puerperal states. |Pregnancy|
    # (77386006) is deliberately omitted: it contributes no rows the |Pregnant|
    # hierarchy does not already cover.
    "pregnancy": (
        "(<<118185001) MINUS ("
        '(<<118185001 {{term = "postpartum"}}) OR '
        '(<<118185001 {{term = "postnatal"}}) OR '
        '(<<118185001 {{term = "puerper"}}))'
    ),
    # Q34. |Causative agent| rather than a wildcard attribute, so the criterion
    # means "caused by" instead of "mentions a bacterium in any role".
    "bacterial_joint_non_strep": "(<<363162000:246075003=((<<409822003) MINUS (<<58800005)))",
    # Q35. Infection disorders: the |Infection| root, anything with a causative
    # organism, specific pathogen domains, and pyogenic/purulent/suppurative
    # terms; minus non-pyogenic and other known false positives.
    "infection": (
        "(\n  <<40733004\n  OR (<404684003:(*=<<441862004))\n"
        "  OR (<404684003:*=(<<409822003 OR <<49872002 OR <<84073006 OR <<441649000))\n"
        "  OR (<404684003:42752001=(<404684003:(*=<<441862004)))\n"
        '  OR (<404684003 {{term = ("Pyogenic" "Purulent" "Suppurative") }})\n)\n'
        ' MINUS ( ((<404684003 {{term = ("non-pyogenic" "non-purulent" "non-Suppurative")}})'
        " OR <<200722003 OR <<1149322001 OR <<66091009 OR <<1172608001 OR <<399981008"
        " OR <<235076008) )"
    ),
}


@dataclass(frozen=True)
class MedicineEcl:
    """A medicine criterion: an ingredient ECL plus a display-text fallback.

    ``ingredients`` is substituted into the product ECL template for the row's
    SNOMED CT-AU edition. ``display_regex`` catches products whose code is
    missing or falls outside the expansion; a row matches if either hits.
    ``oral_only`` swaps in the product-oral template, constraining the
    manufactured dose form to |Oral dose form|.
    """

    ingredients: str
    display_regex: Optional[str] = None
    oral_only: bool = False


MEDICINE_ECLS = {
    # Q15, Q27. Any product containing an ACE inhibitor, combinations included.
    "acei": MedicineEcl("<<372733002", r"pril"),
    # Q27. |Angiotensin II receptor antagonist|.
    "arb": MedicineEcl("<<372913009", r"sartan"),
    # Q16. |Digitalis glycoside| covers digoxin, digitoxin, medigoxin etc.
    "cardiac_glycoside": MedicineEcl("<<406759007", r"digoxin|digitoxin|lanoxin|sigmaxin"),
    # Q31. Digoxin specifically, as the question names it.
    "digoxin": MedicineEcl("<<387461009", r"digoxin|lanoxin|sigmaxin"),
    # Q20.
    "paracetamol": MedicineEcl("<<387517004", r"paracetamol|acetaminophen|panadol|dymadon"),
    # Q25, Q27.
    "methotrexate": MedicineEcl("<<387381009", r"methotrexate"),
    # Q27 teratogens.
    "tetracycline": MedicineEcl("<<372809001", r"cycline"),
    "carbimazole": MedicineEcl("<<395831005", r"carbimazole|neo-mercazole"),
    "statin": MedicineEcl("<<372912004", r"statin"),
    "warfarin": MedicineEcl("<<372756006", r"warfarin|coumadin|marevan"),
    "valproate": MedicineEcl("<<264325000", r"valpro|epilim"),
    "isotretinoin": MedicineEcl("<<387208003", r"isotretinoin|roaccutane"),
    # Q29. Oral NSAIDs, aspirin and salicylates included.
    "nsaid_oral": MedicineEcl(
        "<<372665008",
        r"ibuprofen|naproxen|diclofenac|celecoxib|meloxicam|indometh|ketoprofen|piroxicam|aspirin",
        oral_only=True,
    ),
    # Q31.
    "loop_diuretic": MedicineEcl("<<372691009", r"frusemide|furosemide|bumetanide|ethacrynic|lasix"),
    # Q36. |Iron and/or iron compound| under an oral-only product template.
    # An earlier version navigated ingredients out of |Iron-containing product in
    # oral dose form| ("(<13790009.<<762951001) AND <<767270007"); that resolved
    # to a single ingredient in the 2021-2024 editions and 8 in 2025+, so it
    # silently under-counted every pre-2025 row. The substance grouper is stable
    # across editions (78-87 members).
    "oral_iron": MedicineEcl("<<767270007", oral_only=True),
    # Q37. |Mineral| minus sodium and potassium (both descendants) and chloride
    # (not a descendant, excluded defensively).
    "mineral": MedicineEcl("<<87918000 MINUS (<<39972003 OR <<88480006 OR <<50213009)"),
}

# Q27. Medicines contraindicated or of concern in pregnancy.
TERATOGENIC_MEDICINES = (
    "acei",
    "arb",
    "methotrexate",
    "tetracycline",
    "carbimazole",
    "statin",
    "warfarin",
    "valproate",
    "isotretinoin",
)


@dataclass
class CodeSets:
    """Expanded SNOMED code sets for a single SNOMED CT-AU edition."""

    edition: str
    conditions: Dict[str, Set[str]] = field(default_factory=dict)
    medicines: Dict[str, Set[str]] = field(default_factory=dict)


def build_code_sets(edition, tx_server, verbose=True):
    """Expand every condition and medicine ECL for one edition."""
    sets = CodeSets(edition=edition)

    for key, ecl in CONDITION_ECLS.items():
        sets.conditions[key] = ecl_code_set(ecl, tx_server, edition=edition)

    product_template = resolve_ecl_template(product_ecl_template_for_edition(edition))
    oral_template = resolve_ecl_template("product-oral")
    for key, spec in MEDICINE_ECLS.items():
        template = oral_template if spec.oral_only else product_template
        sets.medicines[key] = ecl_code_set(
            template.format(ingredients=spec.ingredients), tx_server, edition=edition
        )

    if verbose:
        conditions = ", ".join(f"{k}={len(v)}" for k, v in sorted(sets.conditions.items()))
        medicines = ", ".join(f"{k}={len(v)}" for k, v in sorted(sets.medicines.items()))
        print(f"    conditions: {conditions}")
        print(f"    medicines:  {medicines}")

    return sets


def has_condition(df, sets, key):
    """Return boolean mask for rows whose clinical note code is in the code set."""
    return df["SNOMED_Code"].isin(sets.conditions[key])


def count_med_matches(df, sets, key):
    """Count medicine slots matching a MEDICINE_ECLS key (code set OR display regex)."""
    codes = sets.medicines[key]
    pattern = MEDICINE_ECLS[key].display_regex
    matches = {}
    for code_col, display_col in zip(MED_CODES, MED_DISPLAYS):
        hit = df[code_col].isin(codes)
        if pattern:
            hit = hit | df[display_col].str.contains(pattern, case=False, na=False)
        matches[code_col] = hit
    return pd.DataFrame(matches).sum(axis=1)


def has_med(df, sets, key):
    """Return boolean mask for rows with a medicine matching a MEDICINE_ECLS key."""
    return count_med_matches(df, sets, key) > 0


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


def select_questions_interactive(questions_dict):
    """Prompt user to interactively select which questions to include.

    Args:
        questions_dict: Dict of {question_num: question_text}

    Returns:
        List of selected question numbers, sorted numerically
    """
    print("\n" + "=" * 60)
    print("SELECT PRODUCTION QUESTIONS")
    print("=" * 60)
    print("\nAvailable questions:\n")
    for q_num in sorted(questions_dict.keys()):
        print(f"  Q{q_num}: {questions_dict[q_num]}")

    while True:
        print("\nEnter question numbers separated by commas (e.g., 1,4,5,17,22):")
        user_input = input("Selection: ").strip()

        if not user_input:
            print("  ERROR: Please enter at least one question number.")
            continue

        try:
            selected = [int(x.strip()) for x in user_input.split(",")]
        except ValueError:
            print("  ERROR: Invalid input. Please enter only numbers separated by commas.")
            continue

        invalid = [q for q in selected if q not in questions_dict]
        if invalid:
            print(f"  ERROR: Invalid question numbers: {invalid}. Valid range: 1-{max(questions_dict.keys())}")
            continue

        duplicates = [q for q in set(selected) if selected.count(q) > 1]
        if duplicates:
            print(f"  ERROR: Duplicate question numbers: {duplicates}")
            continue

        selected = sorted(set(selected))
        print(f"\n  Selected {len(selected)} questions: {selected}")
        return selected


def parse_question_selection(selection_str, questions_dict):
    """Parse and validate a comma-separated question selection string.

    Same validation rules as select_questions_interactive, for non-interactive use
    (e.g. --questions "1,4,5,17,22").

    Args:
        selection_str: Comma-separated question numbers, e.g. "1,4,5,17,22"
        questions_dict: Dict of {question_num: question_text}

    Returns:
        List of selected question numbers, sorted numerically
    """
    try:
        selected = [int(x.strip()) for x in selection_str.split(",")]
    except ValueError:
        raise ValueError("Invalid --questions value. Please enter only numbers separated by commas.")

    invalid = [q for q in selected if q not in questions_dict]
    if invalid:
        raise ValueError(f"Invalid question numbers: {invalid}. Valid range: 1-{max(questions_dict.keys())}")

    duplicates = [q for q in set(selected) if selected.count(q) > 1]
    if duplicates:
        raise ValueError(f"Duplicate question numbers: {duplicates}")

    return sorted(set(selected))


def filter_and_renumber_questions(df, selected_question_nums):
    """Filter dataframe to selected Q columns and renumber sequentially.

    Args:
        df: DataFrame with Q1-Q37 columns
        selected_question_nums: List of question numbers to keep (e.g., [1, 4, 5])

    Returns:
        DataFrame with only selected questions, renumbered to Q1, Q2, Q3...
        Also returns mapping dict {original_q_num: display_q_num}
    """
    q_cols_to_keep = [f"Q{q}" for q in selected_question_nums]
    q_cols_present = [c for c in q_cols_to_keep if c in df.columns]

    if not q_cols_present:
        raise ValueError(f"No Q columns found in dataframe. Available columns: {df.columns.tolist()}")

    # Create mapping: original Q num -> display Q num (1, 2, 3, ...)
    renumber_map = {}
    for display_idx, original_q in enumerate(selected_question_nums, start=1):
        renumber_map[original_q] = display_idx

    # Select columns and renumber
    filtered_df = df[q_cols_present].copy()
    new_columns = {f"Q{original_q}": f"Q{renumber_map[original_q]}" for original_q in selected_question_nums}
    filtered_df = filtered_df.rename(columns=new_columns)

    return filtered_df, renumber_map


# ---------------------------------------------------------------------------
# Question functions
#
# Each takes (df, sets) and returns a boolean Series aligned to df.index.
# Functions marked "NOT ANSWERABLE" still read the withheld Condition or
# Medicine_*_Category columns and were out of scope for the current tuning pass.
# ---------------------------------------------------------------------------


def female(df):
    """Shared helper: recorded sex is female (excludes non-binary)."""
    return df["Sex"] == "female"


def q01_female(df, sets):
    return female(df)


def q02_adult(df, sets):
    return df["Age"] >= 18


def q03_obese_high_chol_hdl(df, sets):
    """BMI from recorded height/weight; ratio uses lipid panel then MBAP cholesterol."""
    return (df["BMI"] >= 30) & (df["CholHDL_Ratio"] > 5)


def q04_healthy(df, sets):
    return has_condition(df, sets, "healthy")


def q05_hyperthyroidism(df, sets):
    """Coded hyperthyroid disorder, or biochemical thyrotoxicosis on the thyroid panel."""
    tsh = df["Thyroid Panel - TSH (mIU/L)"]
    free_t4 = df["Thyroid Panel - Free T4 (pmol/L)"]
    biochemical = (tsh < 0.4) & (free_t4 > 20)
    return has_condition(df, sets, "hyperthyroidism") | biochemical


def q06_hyperthyroidism_2021(df, sets):
    # NOT ANSWERABLE: uses Condition. Q5 was tuned to ECL; this was not.
    return (df["Condition"] == "Hyperthyroidism") & (df["Year"] == 2021)


def q07_osteoarthritis_2023(df, sets):
    # NOT ANSWERABLE: uses Condition. Q8 was tuned to ECL; this was not.
    return (df["Condition"] == "Osteoarthritis") & (df["Year"] == 2023)


def q08_osteoarthritis_2024(df, sets):
    return has_condition(df, sets, "osteoarthritis") & (df["Year"] == 2024)


def q09_osteoarthritis_2025(df, sets):
    # NOT ANSWERABLE: uses Condition. Q8 was tuned to ECL; this was not.
    return (df["Condition"] == "Osteoarthritis") & (df["Year"] == 2025)


def q10_osteoarthritis_2026(df, sets):
    # NOT ANSWERABLE: uses Condition. Q8 was tuned to ECL; this was not.
    return (df["Condition"] == "Osteoarthritis") & (df["Year"] == 2026)


def q11_rheumatoid_2021(df, sets):
    # NOT ANSWERABLE: uses Condition.
    return (df["Condition"] == "Rheumatoid Arthritis") & (df["Year"] == 2021)


def q12_rheumatoid_2022(df, sets):
    # NOT ANSWERABLE: uses Condition.
    return (df["Condition"] == "Rheumatoid Arthritis") & (df["Year"] == 2022)


def q13_rheumatoid_2023(df, sets):
    # NOT ANSWERABLE: uses Condition.
    return (df["Condition"] == "Rheumatoid Arthritis") & (df["Year"] == 2023)


def q14_thiamine(df, sets):
    # NOT ANSWERABLE: uses Medicine_*_Category.
    return has_med_category(df, "Thiamine")


def q15_ace_inhibitor(df, sets):
    """Any product containing an ACE inhibitor, fixed-dose combinations included."""
    return has_med(df, sets, "acei")


def q16_cardiac_glycoside(df, sets):
    return has_med(df, sets, "cardiac_glycoside")


def q17_statins(df, sets):
    # NOT ANSWERABLE: uses Medicine_*_Category. A "statin" code set exists in
    # MEDICINE_ECLS if this is switched over.
    return has_med_category(df, "Statins (HMG-CoA reductase inhibitor)")


def q18_acei_and_ccb(df, sets):
    # NOT ANSWERABLE: uses Medicine_*_Category.
    return (
        has_med_category(df, "ACE Inhibitors")
        & has_med_category(df, "Calcium Channel Blockers")
    )


def q19_fungal_foot(df, sets):
    return has_condition(df, sets, "fungal_foot")


def q20_multiple_paracetamol(df, sets):
    """Two or more distinct prescribed products containing paracetamol."""
    return count_med_matches(df, sets, "paracetamol") >= 2


def q21_bilateral(df, sets):
    return has_condition(df, sets, "bilateral")


def q22_metformin_low_egfr(df, sets):
    # NOT ANSWERABLE: uses Medicine_*_Category.
    return has_med_category(df, "Biguanide hypoglycaemic agent") & (best_egfr(df) < 30)


def q23_hand_wrist(df, sets):
    hand_wrist_pattern = r"(?i)(?:hand|wrist|carpal|metacarpo|finger|digit|phalanx|phalangeal)"
    return df["SNOMED_Display"].str.contains(hand_wrist_pattern, na=False)


def q24_female_15_49_acei_arb(df, sets):
    # NOT ANSWERABLE: uses Medicine_*_Category. Q25 was tuned; this was not.
    acei_or_arb = (
        has_med_category(df, "ACE Inhibitors")
        | has_med_category(df, "Angiotensin Receptor Blockers")
        | has_med_category(df, "ACE Inhibitors / ARBs")
    )
    return female(df) & (df["Age"] >= 15) & (df["Age"] <= 49) & acei_or_arb


def q25_female_15_49_methotrexate(df, sets):
    return (
        female(df)
        & (df["Age"] >= 15)
        & (df["Age"] <= 49)
        & has_med(df, sets, "methotrexate")
    )


def q26_female_50_plus_methotrexate(df, sets):
    # NOT ANSWERABLE: uses Medicine_*_Category. Q25 was tuned; this was not.
    return female(df) & (df["Age"] >= 50) & has_med_category(df, "Methotrexate")


def q27_pregnant_teratogenic(df, sets):
    """Currently pregnant (postnatal states excluded) and on a teratogenic medicine."""
    teratogenic = pd.Series(False, index=df.index)
    for key in TERATOGENIC_MEDICINES:
        teratogenic = teratogenic | has_med(df, sets, key)
    return has_condition(df, sets, "pregnancy") & teratogenic


def q28_female_ra_15_49(df, sets):
    # NOT ANSWERABLE: uses Condition. A "rheumatoid_arthritis" code set exists
    # in CONDITION_ECLS if this is switched over.
    return (
        (df["Condition"] == "Rheumatoid Arthritis")
        & female(df)
        & (df["Age"] >= 15)
        & (df["Age"] <= 49)
    )


def q29_oa_ra_nsaid_low_egfr(df, sets):
    """Coded OA or RA, on an oral NSAID (aspirin included), with eGFR below 60."""
    oa_ra = has_condition(df, sets, "osteoarthritis") | has_condition(
        df, sets, "rheumatoid_arthritis"
    )
    return oa_ra & has_med(df, sets, "nsaid_oral") & (best_egfr(df) < 60)


def q30_cirrhosis_nsbb(df, sets):
    # NOT ANSWERABLE: uses Condition and Medicine_*_Category.
    return (
        (df["Condition"] == "Chronic Liver Disease / Cirrhosis")
        & has_med_category(df, "Non-Selective Beta-Blockers")
    )


def q31_digoxin_toxicity_risk(df, sets):
    """Digoxin plus eGFR below 30 plus a loop diuretic."""
    return (
        has_med(df, sets, "digoxin")
        & (best_egfr(df) < 30)
        & has_med(df, sets, "loop_diuretic")
    )


def q32_digoxin_hypokalaemia(df, sets):
    # NOT ANSWERABLE: uses Medicine_*_Category. Q31 was tuned; this was not.
    return has_med_category(df, "Digoxin") & (best_potassium(df) < 3.5)


def q33_pregnant_high_glucose(df, sets):
    gluc_col = "MBAP - Glucose (fasting) (mmol/L)"
    return has_condition(df, sets, "pregnancy") & (df[gluc_col] >= 5.1)


def q34_bacterial_joint_non_strep(df, sets):
    return has_condition(df, sets, "bacterial_joint_non_strep")


def q35_infection(df, sets):
    return has_condition(df, sets, "infection")


def q36_oral_iron(df, sets):
    return has_med(df, sets, "oral_iron")


def q37_mineral_supplement(df, sets):
    return has_med(df, sets, "mineral")


QUESTION_FUNCS: Dict[int, Callable] = {
    1: q01_female,
    2: q02_adult,
    3: q03_obese_high_chol_hdl,
    4: q04_healthy,
    5: q05_hyperthyroidism,
    6: q06_hyperthyroidism_2021,
    7: q07_osteoarthritis_2023,
    8: q08_osteoarthritis_2024,
    9: q09_osteoarthritis_2025,
    10: q10_osteoarthritis_2026,
    11: q11_rheumatoid_2021,
    12: q12_rheumatoid_2022,
    13: q13_rheumatoid_2023,
    14: q14_thiamine,
    15: q15_ace_inhibitor,
    16: q16_cardiac_glycoside,
    17: q17_statins,
    18: q18_acei_and_ccb,
    19: q19_fungal_foot,
    20: q20_multiple_paracetamol,
    21: q21_bilateral,
    22: q22_metformin_low_egfr,
    23: q23_hand_wrist,
    24: q24_female_15_49_acei_arb,
    25: q25_female_15_49_methotrexate,
    26: q26_female_50_plus_methotrexate,
    27: q27_pregnant_teratogenic,
    28: q28_female_ra_15_49,
    29: q29_oa_ra_nsaid_low_egfr,
    30: q30_cirrhosis_nsbb,
    31: q31_digoxin_toxicity_risk,
    32: q32_digoxin_hypokalaemia,
    33: q33_pregnant_high_glucose,
    34: q34_bacterial_joint_non_strep,
    35: q35_infection,
    36: q36_oral_iron,
    37: q37_mineral_supplement,
}


def compute_flags(df, sets):
    """Run every question function against df. Returns dict of {"Qn": Series}."""
    flags = {}
    for q_num, func in QUESTION_FUNCS.items():
        result = func(df, sets)
        flags[f"Q{q_num}"] = result.fillna(False).astype(bool)
    return flags


# Criterion phrasing: what it means for a row to be flagged True, stated against
# the columns published in TrainingDataSet.csv. Questions still reading withheld
# columns (Condition, Medicine_*_Category) are marked; they cannot be answered
# from the released data.
QUESTIONS = {
    1: "The patient's recorded sex is female.",
    2: 'The patient is aged 18 years or over at the encounter date.',
    3: 'The patient has a BMI of 30 or more (from recorded height and weight) and a '
       'total cholesterol to HDL ratio greater than 5.',
    4: 'The clinical note records the patient as healthy or free of current problems.',
    5: 'The clinical note codes a hyperthyroid disorder, or the thyroid panel shows '
       'biochemical thyrotoxicosis (TSH below 0.4 mIU/L with free T4 above 20 pmol/L).',
    6: '[Uses withheld Condition column] The patient has hyperthyroidism and the '
       'encounter occurred in 2021.',
    7: '[Uses withheld Condition column] The patient has osteoarthritis and the '
       'encounter occurred in 2023.',
    8: 'The clinical note codes an osteoarthritis (excluding gout and chondrocalcinosis) '
       'and the encounter occurred in 2024.',
    9: '[Uses withheld Condition column] The patient has osteoarthritis and the '
       'encounter occurred in 2025.',
    10: '[Uses withheld Condition column] The patient has osteoarthritis and the '
        'encounter occurred in 2026.',
    11: '[Uses withheld Condition column] The patient has rheumatoid arthritis and the '
        'encounter occurred in 2021.',
    12: '[Uses withheld Condition column] The patient has rheumatoid arthritis and the '
        'encounter occurred in 2022.',
    13: '[Uses withheld Condition column] The patient has rheumatoid arthritis and the '
        'encounter occurred in 2023.',
    14: '[Uses withheld Medicine Category column] The patient is prescribed thiamine.',
    15: 'The patient is prescribed a product containing an ACE inhibitor, including '
        'fixed-dose combination products.',
    16: 'The patient is prescribed a product containing a cardiac (digitalis) glycoside.',
    17: '[Uses withheld Medicine Category column] The patient is prescribed a statin.',
    18: '[Uses withheld Medicine Category column] The patient is prescribed both an ACE '
        'inhibitor and a calcium channel blocker.',
    19: 'The clinical note codes a fungal infection with a foot finding site, or tinea pedis.',
    20: 'The patient is prescribed two or more distinct products containing paracetamol.',
    21: 'The clinical note codes a bilateral condition.',
    22: '[Uses withheld Medicine Category column] The patient is prescribed metformin and '
        'has an eGFR below 30.',
    23: 'The clinical note display contains a hand or wrist term.',
    24: '[Uses withheld Medicine Category column] The patient is female, aged 15 to 49, '
        'and prescribed an ACE inhibitor or an angiotensin receptor blocker.',
    25: 'The patient is female, aged 15 to 49, and prescribed a product containing methotrexate.',
    26: '[Uses withheld Medicine Category column] The patient is female, aged 50 or over, '
        'and prescribed methotrexate.',
    27: 'The clinical note codes a current pregnancy (postnatal states excluded) and the '
        'patient is prescribed a teratogenic medicine: an ACE inhibitor, angiotensin '
        'receptor blocker, methotrexate, tetracycline, carbimazole, statin, warfarin, '
        'valproate, or isotretinoin.',
    28: '[Uses withheld Condition column] The patient is female, aged 15 to 49, with '
        'rheumatoid arthritis.',
    29: 'The clinical note codes osteoarthritis or rheumatoid arthritis, the patient is '
        'prescribed an oral NSAID (aspirin and salicylates included), and the eGFR is '
        'below 60.',
    30: '[Uses withheld Condition and Medicine Category columns] The patient has cirrhosis '
        'and is prescribed a non-selective beta-blocker.',
    31: 'The patient is prescribed digoxin, has an eGFR below 30, and is prescribed a loop '
        'diuretic.',
    32: '[Uses withheld Medicine Category column] The patient is prescribed digoxin and has '
        'a potassium below 3.5 mmol/L.',
    33: 'The clinical note codes a current pregnancy (postnatal states excluded) and the '
        'fasting glucose is 5.1 mmol/L or greater.',
    34: 'The clinical note codes a joint infection whose causative agent is a bacterium '
        'other than a Streptococcus species.',
    35: 'The clinical note codes an infection.',
    36: 'The patient is prescribed an oral product containing iron.',
    37: 'The patient is prescribed a product containing a mineral providing a chemical '
        'element, other than sodium, potassium or chloride.',
}


def compute_metrics(df, questions_dict=None):
    """Produce metrics text from the flagged dataframe.

    Args:
        df: DataFrame with Q1-Qn boolean flag columns
        questions_dict: Optional dict of {question_num: criterion_text}. If None, uses global QUESTIONS.
    """
    if questions_dict is None:
        questions_dict = QUESTIONS

    lines = []

    lines.append("=" * 60)
    lines.append("Analytics Questions")
    lines.append("=" * 60)
    lines.append("")

    for q_num in sorted(questions_dict):
        col = f"Q{q_num}"
        count = int(df[col].sum())
        lines.append(f"Q{q_num}. {questions_dict[q_num]}: {count}")

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
    import argparse
    parser = argparse.ArgumentParser(description="Analyse generated patient data.")
    parser.add_argument(
        "--mode",
        choices=["exploratory", "production"],
        default="exploratory",
        help="Pipeline mode: exploratory (all Q1-Q37) or production (select subset)",
    )
    parser.add_argument(
        "--tx-server",
        default=DEFAULT_TX_SERVER,
        help=f"FHIR terminology server base URL (default: {DEFAULT_TX_SERVER})",
    )
    parser.add_argument(
        "--questions",
        default=None,
        help="Comma-separated question numbers for production mode (e.g. '1,4,5,17,22'). "
             "Skips the interactive prompt. Ignored in exploratory mode.",
    )
    args = parser.parse_args()

    print("Loading data...")
    df = load_data()

    print("Computing derived columns...")
    df = add_derived_columns(df)

    # Map each row to its SNOMED CT-AU edition based on EncounterDate
    encounter_dates = pd.to_datetime(df["EncounterDate"]).dt.date
    df["_edition"] = encounter_dates.map(edition_for_date)

    # Expand every ECL once per edition (cached by conditions.snomed.expand_ecl)
    edition_code_sets = {}
    for edition in sorted(df["_edition"].unique()):
        print(f"  Expanding ECLs for edition {edition}...")
        edition_code_sets[edition] = build_code_sets(edition, args.tx_server)

    print("Computing Q1-Q37 flags per edition...")
    flag_parts = []
    for edition, group in df.groupby("_edition"):
        part_flags = compute_flags(group, edition_code_sets[edition])
        flag_parts.append(pd.DataFrame(part_flags, index=group.index))

    flag_df = pd.concat(flag_parts).sort_index()
    df = pd.concat([df, flag_df], axis=1)
    df = df.drop(columns=["_edition"])

    # Handle production mode: select subset of questions and renumber
    if args.mode == "production":
        if args.questions:
            selected_questions = parse_question_selection(args.questions, QUESTIONS)
            print(f"\nSelected {len(selected_questions)} questions: {selected_questions}")
        else:
            selected_questions = select_questions_interactive(QUESTIONS)
        q_filtered_df, renumber_map = filter_and_renumber_questions(df, selected_questions)
        # Create filtered QUESTIONS dict with renumbered keys
        questions_to_use = {i: QUESTIONS[selected_questions[i-1]] for i in range(1, len(selected_questions) + 1)}
        q_cols = [f"Q{i}" for i in range(1, len(selected_questions) + 1)]
        # Replace Q columns in df with filtered/renumbered versions
        df = df.drop(columns=[f"Q{i}" for i in range(1, 38)])
        df = pd.concat([df, q_filtered_df], axis=1)
    else:
        questions_to_use = QUESTIONS
        q_cols = [f"Q{i}" for i in range(1, 38)]

    print("Computing metrics...")
    output = compute_metrics(df, questions_dict=questions_to_use)

    # Write metrics.txt
    metrics_path = os.path.join(SCRIPT_DIR, "metrics.txt")
    with open(metrics_path, "w") as f:
        f.write(output)
        f.write("\n")
    print(f"Metrics written to {metrics_path}")

    drop_cols = ["Year", "BMI", "CholHDL_Ratio"]

    # Write TrainingDataSet.csv (Episode Number + original data columns, no Q flags)
    all_q_cols = [f"Q{i}" for i in range(1, 38)]
    training_exclude = all_q_cols + drop_cols + [
        "Age", "LifestyleFactors", "Condition",
        # BirthDate contradicted DateOfBirth (see formatters/csv_writer.py).
        # Dropped here so existing raw_data.csv files stop publishing it;
        # regenerated data will not contain the column at all.
        "BirthDate",
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
