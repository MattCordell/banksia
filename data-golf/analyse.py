"""
Analyse generated patient data and produce a metrics summary.

Reads raw_data.csv from the same directory, computes the Q1-Q18 boolean flag
columns, and writes metrics.txt, TrainingDataSet.csv, solution.csv and
sample_submission.csv.

Each question has a dedicated ``q<nn>_*`` function taking ``(df, sets)`` and
returning a boolean Series. ``QUESTION_FUNCS`` maps question number to
function; ``QUESTIONS`` holds the criterion each flag encodes.

Every criterion is expressed against columns actually published in
TrainingDataSet.csv -- Clinical_Note_Code/Display, Medicine_*_Code/Display,
lab results and demographics. The generator's ``Condition`` and
``Medicine_*_Category`` columns are deliberately not used: they are withheld
from competitors, and they are unreliable (``Condition`` is a sampling bucket
whose coded concept is often unrelated, and the medicine categories mislabel
products). Conditions are matched by ECL against Clinical_Note_Code, medicines
by ECL against Medicine_*_Code with a display-text fallback.

ECLs are expanded once per SNOMED CT-AU edition and applied to the rows whose
encounter falls in that edition's period, so a flag reflects the terminology
active at the time of the encounter.

This question set was selected and tuned from an earlier 37-question set. The
originals are in the git history; the mapping is:

    Q1  <- Q1   female                    Q10 <- Q21  bilateral
    Q2  <- Q3   obese, high chol:HDL      Q11 <- Q25  F 15-49 on methotrexate
    Q3  <- Q4   healthy                   Q12 <- Q27  pregnant on teratogen
    Q4  <- Q5   hyperthyroidism           Q13 <- Q29  OA/RA, NSAID, low eGFR
    Q5  <- Q8   osteoarthritis in 2024    Q14 <- Q31  digoxin toxicity risk
    Q6  <- Q15  ACE inhibitor             Q15 <- Q33  pregnant, high glucose
    Q7  <- Q16  cardiac glycoside         Q16 <- Q34  bacterial joint infection
    Q8  <- Q19  fungal foot infection     Q17 <- Q36  oral iron
    Q9  <- Q20  duplicate paracetamol     Q18 <- Q37  mineral supplement
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

MED_DISPLAYS = ["Medicine_1_Display", "Medicine_2_Display", "Medicine_3_Display"]
MED_CODES = ["Medicine_1_Code", "Medicine_2_Code", "Medicine_3_Code"]

QUESTION_COUNT = 18

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


def product_ecl_template_for_edition(edition):
    """Return the ecl_templates.json key matching the product model used for edition.

    Must stay in sync with generate_data.py PERIODS: "product" (SNOMED CT international
    medicinal product hierarchy) pre-2025, "amt-tpuu" (AMT Trade Product Unit of Use) from
    2025 onwards.
    """
    return "amt-tpuu" if edition >= "20250131" else "product"


# ---------------------------------------------------------------------------
# Derived columns and lab helpers
# ---------------------------------------------------------------------------


def best_cholesterol(df):
    """Return total cholesterol, preferring the Lipid Panel, falling back to MBAP.

    The lipid panel is absent on a minority of rows; MBAP carries a total
    cholesterol for most of them, so the fallback widens Q2's coverage.
    """
    lipid = "Lipid Panel - Total Cholesterol (mmol/L)"
    mbap = "MBAP - Cholesterol (mmol/L)"
    if lipid not in df.columns:
        return df[mbap]
    return df[lipid].fillna(df[mbap]) if mbap in df.columns else df[lipid]


def best_egfr(df):
    """Return eGFR series, preferring MBAP panel, falling back to Kidney Function."""
    mbap = "MBAP - eGFR (mL/min/1.73m²)"
    kf = "Kidney Function - eGFR (mL/min/1.73m²)"
    return df[mbap].fillna(df[kf]) if kf in df.columns else df[mbap]


def add_derived_columns(df):
    """Add Year, BMI, and CholHDL_Ratio columns."""
    df["Year"] = pd.to_datetime(df["EncounterDate"]).dt.year
    df["BMI"] = df["Weight_kg"] / (df["Height_cm"] / 100) ** 2
    hdl_col = "Lipid Panel - HDL (mmol/L)"
    if hdl_col in df.columns:
        df["CholHDL_Ratio"] = best_cholesterol(df) / df[hdl_col]
    return df


# ---------------------------------------------------------------------------
# ECL definitions
#
# Conditions are matched against SNOMED_Code (published as Clinical_Note_Code)
# rather than the withheld Condition label, because the label is a sampling
# bucket and the coded concept is often only loosely related to it -- e.g. a
# "Hyperthyroidism" row coded as |Dysprealbuminaemic euthyroidal
# hyperthyroxinaemia|, which is a euthyroid state.
# ---------------------------------------------------------------------------

CONDITION_ECLS = {
    # Q3. |Healthy| plus |No current problems or disability|, which is not a
    # descendant of |Healthy| but carries the same meaning here.
    "healthy": "(<<102499006) OR (<<160245001)",
    # Q4. |Hyperthyroidism|.
    "hyperthyroidism": "<<34486009",
    # Q5, Q13. SNOMED classifies |Gout| and |Chondrocalcinosis| beneath
    # |Osteoarthritis|; both are excluded so the criterion means degenerative OA.
    "osteoarthritis": "(<<396275006) MINUS ((<<90560007) OR (<<239838005))",
    # Q13.
    "rheumatoid_arthritis": "<<69896004",
    # Q8. Mycosis with a foot finding site, plus |Tinea pedis| explicitly (its
    # finding site is a skin structure not subsumed by |Foot structure|).
    # Expands to only ~10 concepts, so it returns 0 on small cohorts.
    "fungal_foot": "(<<3218000) AND ((<404684003:363698007=(<<56459004)) OR (<<6020002))",
    # Q10. Laterality is not modelled on these disorders, so an attribute-based
    # ECL expands to nothing; a term filter is the terminology-native equivalent
    # of scanning the display string, and matches on synonyms too.
    "bilateral": '<<404684003 {{ term = "bilateral" }}',
    # Q12, Q15. |Pregnant| minus postnatal/puerperal states, so postpartum
    # patients do not count as currently pregnant. |Pregnancy| (77386006) is
    # deliberately omitted: it contributes no rows the |Pregnant| hierarchy does
    # not already cover.
    "pregnancy": (
        "(<<118185001) MINUS ("
        '(<<118185001 {{term = "postpartum"}}) OR '
        '(<<118185001 {{term = "postnatal"}}) OR '
        '(<<118185001 {{term = "puerper"}}))'
    ),
    # Q16. |Causative agent| rather than a wildcard attribute, so the criterion
    # means "caused by" instead of "mentions a bacterium in any role".
    "bacterial_joint_non_strep": "(<<363162000:246075003=((<<409822003) MINUS (<<58800005)))",
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
    # Q6, Q12. Any product containing an ACE inhibitor, combinations included.
    "acei": MedicineEcl("<<372733002", r"pril"),
    # Q12. |Angiotensin II receptor antagonist|.
    "arb": MedicineEcl("<<372913009", r"sartan"),
    # Q7. |Digitalis glycoside| covers digoxin, digitoxin, medigoxin etc.
    "cardiac_glycoside": MedicineEcl("<<406759007", r"digoxin|digitoxin|lanoxin|sigmaxin"),
    # Q14. Digoxin specifically, as the question names it.
    "digoxin": MedicineEcl("<<387461009", r"digoxin|lanoxin|sigmaxin"),
    # Q9.
    "paracetamol": MedicineEcl("<<387517004", r"paracetamol|acetaminophen|panadol|dymadon"),
    # Q11, Q12.
    "methotrexate": MedicineEcl("<<387381009", r"methotrexate"),
    # Q12 teratogens.
    "tetracycline": MedicineEcl("<<372809001", r"cycline"),
    "carbimazole": MedicineEcl("<<395831005", r"carbimazole|neo-mercazole"),
    "statin": MedicineEcl("<<372912004", r"statin"),
    "warfarin": MedicineEcl("<<372756006", r"warfarin|coumadin|marevan"),
    "valproate": MedicineEcl("<<264325000", r"valpro|epilim"),
    "isotretinoin": MedicineEcl("<<387208003", r"isotretinoin|roaccutane"),
    # Q13. Oral NSAIDs, aspirin and salicylates included.
    "nsaid_oral": MedicineEcl(
        "<<372665008",
        r"ibuprofen|naproxen|diclofenac|celecoxib|meloxicam|indometh|ketoprofen|piroxicam|aspirin",
        oral_only=True,
    ),
    # Q14.
    "loop_diuretic": MedicineEcl("<<372691009", r"frusemide|furosemide|bumetanide|ethacrynic|lasix"),
    # Q17. |Iron and/or iron compound| under an oral-only product template.
    # An earlier version navigated ingredients out of |Iron-containing product in
    # oral dose form| ("(<13790009.<<762951001) AND <<767270007"); that resolved
    # to a single ingredient in the 2021-2024 editions and 8 in 2025+, so it
    # silently under-counted every pre-2025 row. The substance grouper is stable
    # across editions (78-87 members).
    "oral_iron": MedicineEcl("<<767270007", oral_only=True),
    # Q18. |Mineral| minus sodium and potassium (both descendants) and chloride
    # (not a descendant, excluded defensively).
    "mineral": MedicineEcl("<<87918000 MINUS (<<39972003 OR <<88480006 OR <<50213009)"),
}

# Q12. Medicines contraindicated or of concern in pregnancy.
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


def female(df):
    """Recorded sex is female (excludes the non-binary rows)."""
    return df["Sex"] == "female"


def condition_counts(df):
    """Return condition value counts as a formatted string.

    Diagnostics only -- Condition is withheld from the published dataset and is
    never used to compute a flag.
    """
    counts = df["Condition"].value_counts().sort_index()
    lines = []
    for condition, count in counts.items():
        lines.append(f"    {condition}: {count}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Question functions
#
# Each takes (df, sets) and returns a boolean Series aligned to df.index.
# ---------------------------------------------------------------------------


def q01_female(df, sets):
    return female(df)


def q02_obese_high_chol_hdl(df, sets):
    """BMI from recorded height/weight; ratio uses lipid panel then MBAP cholesterol."""
    return (df["BMI"] >= 30) & (df["CholHDL_Ratio"] > 5)


def q03_healthy(df, sets):
    return has_condition(df, sets, "healthy")


def q04_hyperthyroidism(df, sets):
    """Coded hyperthyroid disorder, or biochemical thyrotoxicosis on the thyroid panel."""
    tsh = df["Thyroid Panel - TSH (mIU/L)"]
    free_t4 = df["Thyroid Panel - Free T4 (pmol/L)"]
    biochemical = (tsh < 0.4) & (free_t4 > 20)
    return has_condition(df, sets, "hyperthyroidism") | biochemical


def q05_osteoarthritis_2024(df, sets):
    return has_condition(df, sets, "osteoarthritis") & (df["Year"] == 2024)


def q06_ace_inhibitor(df, sets):
    """Any product containing an ACE inhibitor, fixed-dose combinations included."""
    return has_med(df, sets, "acei")


def q07_cardiac_glycoside(df, sets):
    return has_med(df, sets, "cardiac_glycoside")


def q08_fungal_foot(df, sets):
    return has_condition(df, sets, "fungal_foot")


def q09_multiple_paracetamol(df, sets):
    """Two or more distinct prescribed products containing paracetamol."""
    return count_med_matches(df, sets, "paracetamol") >= 2


def q10_bilateral(df, sets):
    return has_condition(df, sets, "bilateral")


def q11_female_15_49_methotrexate(df, sets):
    return (
        female(df)
        & (df["Age"] >= 15)
        & (df["Age"] <= 49)
        & has_med(df, sets, "methotrexate")
    )


def q12_pregnant_teratogenic(df, sets):
    """Currently pregnant (postnatal states excluded) and on a teratogenic medicine."""
    teratogenic = pd.Series(False, index=df.index)
    for key in TERATOGENIC_MEDICINES:
        teratogenic = teratogenic | has_med(df, sets, key)
    return has_condition(df, sets, "pregnancy") & teratogenic


def q13_oa_ra_nsaid_low_egfr(df, sets):
    """Coded OA or RA, on an oral NSAID (aspirin included), with eGFR below 60."""
    oa_ra = has_condition(df, sets, "osteoarthritis") | has_condition(
        df, sets, "rheumatoid_arthritis"
    )
    return oa_ra & has_med(df, sets, "nsaid_oral") & (best_egfr(df) < 60)


def q14_digoxin_toxicity_risk(df, sets):
    """Digoxin plus eGFR below 30 plus a loop diuretic."""
    return (
        has_med(df, sets, "digoxin")
        & (best_egfr(df) < 30)
        & has_med(df, sets, "loop_diuretic")
    )


def q15_pregnant_high_glucose(df, sets):
    gluc_col = "MBAP - Glucose (fasting) (mmol/L)"
    return has_condition(df, sets, "pregnancy") & (df[gluc_col] >= 5.1)


def q16_bacterial_joint_non_strep(df, sets):
    return has_condition(df, sets, "bacterial_joint_non_strep")


def q17_oral_iron(df, sets):
    return has_med(df, sets, "oral_iron")


def q18_mineral_supplement(df, sets):
    return has_med(df, sets, "mineral")


QUESTION_FUNCS: Dict[int, Callable] = {
    1: q01_female,
    2: q02_obese_high_chol_hdl,
    3: q03_healthy,
    4: q04_hyperthyroidism,
    5: q05_osteoarthritis_2024,
    6: q06_ace_inhibitor,
    7: q07_cardiac_glycoside,
    8: q08_fungal_foot,
    9: q09_multiple_paracetamol,
    10: q10_bilateral,
    11: q11_female_15_49_methotrexate,
    12: q12_pregnant_teratogenic,
    13: q13_oa_ra_nsaid_low_egfr,
    14: q14_digoxin_toxicity_risk,
    15: q15_pregnant_high_glucose,
    16: q16_bacterial_joint_non_strep,
    17: q17_oral_iron,
    18: q18_mineral_supplement,
}

# The criterion each flag encodes: the flag is True when this holds for the row.
QUESTIONS = {
    1: "The patient's recorded sex is female.",
    2: 'The patient has a BMI of 30 or more (from recorded height and weight) and a '
       'total cholesterol to HDL ratio greater than 5.',
    3: 'The clinical note records the patient as healthy or free of current problems.',
    4: 'The clinical note codes a hyperthyroid disorder, or the thyroid panel shows '
       'biochemical thyrotoxicosis (TSH below 0.4 mIU/L with free T4 above 20 pmol/L).',
    5: 'The clinical note codes an osteoarthritis (excluding gout and chondrocalcinosis) '
       'and the encounter occurred in 2024.',
    6: 'The patient is prescribed a product containing an ACE inhibitor, including '
       'fixed-dose combination products.',
    7: 'The patient is prescribed a product containing a cardiac (digitalis) glycoside.',
    8: 'The clinical note codes a fungal infection with a foot finding site, or tinea pedis.',
    9: 'The patient is prescribed two or more distinct products containing paracetamol.',
    10: 'The clinical note codes a bilateral condition.',
    11: 'The patient is female, aged 15 to 49, and prescribed a product containing '
        'methotrexate.',
    12: 'The clinical note codes a current pregnancy (postnatal states excluded) and the '
        'patient is prescribed a teratogenic medicine: an ACE inhibitor, angiotensin '
        'receptor blocker, methotrexate, tetracycline, carbimazole, statin, warfarin, '
        'valproate, or isotretinoin.',
    13: 'The clinical note codes osteoarthritis or rheumatoid arthritis, the patient is '
        'prescribed an oral NSAID (aspirin and salicylates included), and the eGFR is '
        'below 60.',
    14: 'The patient is prescribed digoxin, has an eGFR below 30, and is prescribed a loop '
        'diuretic.',
    15: 'The clinical note codes a current pregnancy (postnatal states excluded) and the '
        'fasting glucose is 5.1 mmol/L or greater.',
    16: 'The clinical note codes a joint infection whose causative agent is a bacterium '
        'other than a Streptococcus species.',
    17: 'The patient is prescribed an oral product containing iron.',
    18: 'The patient is prescribed a product containing a mineral providing a chemical '
        'element, other than sodium, potassium or chloride.',
}


def compute_flags(df, sets):
    """Run every question function against df. Returns dict of {"Qn": Series}."""
    flags = {}
    for q_num, func in QUESTION_FUNCS.items():
        result = func(df, sets)
        flags[f"Q{q_num}"] = result.fillna(False).astype(bool)
    return flags


def compute_metrics(df):
    """Produce metrics text from the flagged dataframe."""
    lines = []

    lines.append("=" * 60)
    lines.append("Analytics Questions")
    lines.append("=" * 60)
    lines.append("")

    for q_num in sorted(QUESTIONS):
        count = int(df[f"Q{q_num}"].sum())
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
    import argparse
    parser = argparse.ArgumentParser(description="Analyse generated patient data.")
    parser.add_argument(
        "--tx-server",
        default=DEFAULT_TX_SERVER,
        help=f"FHIR terminology server base URL (default: {DEFAULT_TX_SERVER})",
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

    print(f"Computing Q1-Q{QUESTION_COUNT} flags per edition...")
    flag_parts = []
    for edition, group in df.groupby("_edition"):
        part_flags = compute_flags(group, edition_code_sets[edition])
        flag_parts.append(pd.DataFrame(part_flags, index=group.index))

    flag_df = pd.concat(flag_parts).sort_index()
    df = pd.concat([df, flag_df], axis=1)
    df = df.drop(columns=["_edition"])

    q_cols = [f"Q{i}" for i in range(1, QUESTION_COUNT + 1)]

    print("Computing metrics...")
    output = compute_metrics(df)

    # Write metrics.txt
    metrics_path = os.path.join(SCRIPT_DIR, "metrics.txt")
    with open(metrics_path, "w") as f:
        f.write(output)
        f.write("\n")
    print(f"Metrics written to {metrics_path}")

    # Write TrainingDataSet.csv (Episode Number + published data columns, no Q flags).
    # Age, Condition and the medicine categories are withheld because they either
    # give the answers away or are generator bookkeeping. BirthDate contradicted
    # DateOfBirth (see formatters/csv_writer.py); it is dropped here so existing
    # raw_data.csv files stop publishing it, and regenerated data will not contain
    # the column at all.
    training_exclude = q_cols + ["Year", "BMI", "CholHDL_Ratio"] + [
        "Age", "LifestyleFactors", "Condition", "BirthDate",
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
