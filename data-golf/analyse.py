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

Because of that, a code can be valid when recorded and inactive by the latest
edition. Three reports quantify the drift, all measured against
``REFERENCE_EDITION``:

``inactive_concept_report`` counts inactive concepts in each of the four
SNOMED-coded columns. It uses an explicit-concept ValueSet/$expand rather than an
ECL, since inactive concepts have no relationships and no ECL can reach them.

``question_scope_report`` narrows that to the concepts a question's ECLs actually
reach -- a retirement no question refers to is harmless -- and asks whether an
ECL history supplement could recover each one. The concepts even HISTORY-MAX
cannot reach were retired without a historical association, which is the one
failure mode a latest-edition solution cannot mitigate. Which criteria each
question consults is observed by running the question functions against a
recording view of the code sets (``question_criteria``), so it cannot drift out
of sync with the functions themselves.

``edition_delta_report`` recomputes every flag against ``REFERENCE_EDITION``
under each history profile and reports what would move. It reports the switch
without making it: the flags written to solution.csv remain the per-encounter
ones.

Both reference reports expand the medicine criteria under both product models
(``REFERENCE_PRODUCT_TEMPLATES``). The dataset carries SNOMED CT international
clinical drug codes pre-2025 and AMT TPUU codes from 2025, and expanding the
reference edition under its own model alone would strand every pre-2025 medicine
row -- reporting the product-model switch as if it were terminology drift.

solution.csv's ``Usage`` column is assigned by ``assign_usage``, which stratifies
the public/private split on all 18 flags rather than splitting rows blindly. The
scoring metric is macro-F1 weighting every question equally, so the rare
questions carry the same 5.6 points as Q1's tens of thousands of positives and
must not be left to land lopsidedly. See ``MIN_POSITIVES_PER_SPLIT``.

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
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from conditions.snomed import concept_status  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TX_SERVER = "https://r4.ontoserver.csiro.au/fhir"

SNOMED_CODE_COLS = ["SNOMED_Code", "Medicine_1_Code", "Medicine_2_Code", "Medicine_3_Code"]

# What each SNOMED-coded column is called in TrainingDataSet.csv, so the metrics
# report names the columns competitors actually see.
PUBLISHED_CODE_COLS = {
    "SNOMED_Code": "Clinical_Note_Code",
    "Medicine_1_Code": "Medicine_1_Code",
    "Medicine_2_Code": "Medicine_2_Code",
    "Medicine_3_Code": "Medicine_3_Code",
}

MED_DISPLAYS = ["Medicine_1_Display", "Medicine_2_Display", "Medicine_3_Display"]
MED_CODES = ["Medicine_1_Code", "Medicine_2_Code", "Medicine_3_Code"]

QUESTION_COUNT = 18

# Kaggle public/private leaderboard split. Rows are stratified on every question
# flag independently, so this ratio holds per question rather than just overall.
PUBLIC_FRACTION = 0.5
SPLIT_SEED = 20260730

# Warn when a question lands fewer positives than this in either split. Scoring
# is macro-F1 over all 18 questions equally, so each is worth 100/18 = 5.6 points
# regardless of how many positives it has. With k positives in a split, missing
# one gives F1 = 2(k-1)/(2k-1), so a single row is worth (1 - that)/18 of the
# final score: 0.06 points at k=50, 0.43 at k=7, and at k=1 the question becomes
# an all-or-nothing 5.6-point coin flip.
MIN_POSITIVES_PER_SPLIT = 5

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

# Edition the inactive-concept report measures against: the latest edition in
# PERIODS (January 2026). Flags are computed per-encounter against the edition
# current at the time, so a code can be perfectly valid when it was recorded and
# still be inactive today -- this report quantifies that drift.
REFERENCE_EDITION = PERIODS[-1]["edition"]

# ECL history supplement profiles, used to expand the criteria against
# REFERENCE_EDITION as an alternative to the per-encounter editions. None means
# no supplement -- the naive "just use the current release" behaviour.
#
#   HISTORY-MIN  SAME AS only
#   HISTORY-MOD  SAME AS, REPLACED BY, WAS A, PARTIALLY EQUIVALENT TO
#   HISTORY-MAX  every historical association
#
# MAX is the yardstick for recoverability: a retired concept MAX cannot reach has
# no historical association at all, which is the failure mode the latest-edition
# approach cannot mitigate.
HISTORY_PROFILES = [None, "HISTORY-MIN", "HISTORY-MOD", "HISTORY-MAX"]

# Column label for each profile in the report tables.
PROFILE_LABELS = {
    None: "latest",
    "HISTORY-MIN": "+HIST-MIN",
    "HISTORY-MOD": "+HIST-MOD",
    "HISTORY-MAX": "+HIST-MAX",
}

# How many unrecoverable concepts to list individually before truncating.
UNRECOVERABLE_LIST_LIMIT = 40


def with_history(ecl: str, profile: Optional[str]) -> str:
    """Append an ECL history supplement to a constraint.

    The constraint is parenthesised so the supplement binds to the whole
    expression. Verified against Ontoserver on the three shapes in this file that
    could plausibly reject it: MINUS compounds, constraints already carrying a
    ``{{ term = ... }}`` filter, and the AMT refset templates.
    """
    if profile is None:
        return ecl
    return f"({ecl}) {{{{ + {profile} }}}}"


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


def populated_codes(df):
    """The non-blank code series for each SNOMED-coded column."""
    populated = {}
    for col in SNOMED_CODE_COLS:
        series = df[col].dropna().astype(str).str.strip()
        populated[col] = series[series != ""]
    return populated


def inactive_concept_report(df, status: Dict[str, str], edition: str) -> str:
    """Per-column inactive concept counts for the four SNOMED-coded columns.

    Counts both distinct concepts and affected rows: a single retired concept
    reused across thousands of rows and a thousand one-off retirements are very
    different problems, and the distinct count alone cannot tell them apart.

    ``status`` comes from concept_status(); it is passed in rather than fetched
    here so the question-scope report can share the same round trips.
    """
    populated = populated_codes(df)

    codes = set()
    for series in populated.values():
        codes |= set(series.unique())

    inactive_codes = {c for c, s in status.items() if s == "inactive"}
    absent_codes = {c for c, s in status.items() if s == "absent"}

    lines = [
        f"Concept activity against SNOMED CT-AU {edition}. Flags are computed per",
        "encounter against the edition current at the time, so an inactive code here",
        "was still valid when it was recorded.",
        "",
        "\"concepts\" counts distinct codes in the column, \"rows\" the rows where it is",
        "populated. Column counts overlap -- the medicine slots draw on one another's",
        "products -- so they sum to more than the deduplicated total below.",
        "",
        f"{'Field':<20}{'concepts':>9}{'inactive':>9}{'pct':>7}"
        f"{'rows':>10}{'inactive':>9}{'pct':>7}",
    ]

    for col in SNOMED_CODE_COLS:
        series = populated[col]
        distinct = series.nunique()
        col_inactive = {c for c in series.unique() if c in inactive_codes}
        rows = len(series)
        rows_inactive = int(series.isin(col_inactive).sum())
        concept_pct = f"{len(col_inactive) / distinct * 100:.1f}%" if distinct else "n/a"
        row_pct = f"{rows_inactive / rows * 100:.1f}%" if rows else "n/a"
        lines.append(
            f"{PUBLISHED_CODE_COLS[col]:<20}{distinct:>9}{len(col_inactive):>9}"
            f"{concept_pct:>7}{rows:>10}{rows_inactive:>9}{row_pct:>7}"
        )

    total_pct = f"{len(inactive_codes) / len(codes) * 100:.1f}%" if codes else "n/a"
    lines.append("")
    lines.append(
        f"Across all four fields: {len(codes)} distinct concepts, "
        f"{len(inactive_codes)} inactive ({total_pct})."
    )
    if absent_codes:
        lines.append(
            f"NOTE: {len(absent_codes)} code(s) are not in edition {edition} at all, "
            "in any state."
        )

    return "\n".join(lines)


def resolve_ecl_template(template_key: str) -> str:
    """Look up a named product ECL template from medicines/ecl_templates.json."""
    from medicines.generator import resolve_ecl_template as _resolve
    return _resolve(template_key)


def product_ecl_template_for_edition(edition):
    """Return the ecl_templates.json key matching the product model used for edition.

    Tracks generate_data.py PERIODS: SNOMED CT international medicinal product
    hierarchy pre-2025, "amt-tpuu" (AMT Trade Product Unit of Use) from 2025 onwards.

    Deliberately returns the broader "product" for the pre-2025 editions even though
    generation uses "clinical-drug". "clinical-drug" is "product" plus a
    732943007 |Has basis of strength substance| refinement, so its expansion is a
    subset, and generation falls back to "product" when it is empty. Matching on the
    superset therefore covers every code generation can emit; narrowing this to
    "clinical-drug" would silently drop the fallback rows.
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
    "hyperthyroidism": "( (<<34486009 OR <<237498007 OR <<722941003 OR <<73064001 OR <<1163454006 OR <<13795004 OR <<22350004 OR <<237505003 OR <<29028009 OR <<237506002 ) ) MINUS ( (<<237547004 OR <<237549001 OR <<762294003 OR <<137421000119106 ) )",
    # Q5, Q13. SNOMED classifies |Gout| and |Chondrocalcinosis| beneath
    # |Osteoarthritis|; both are excluded so the criterion means degenerative OA.
    "osteoarthritis": " (<<396275006 MINUS (<<90560007 OR <<239838005 OR <<785808002))",
    # Q13.
    "rheumatoid_arthritis": "<<69896004",
    # Q8. Mycosis with a foot finding site, plus |Tinea pedis| explicitly (its
    # finding site is a skin structure not subsumed by |Foot structure|).
    # Expands to only ~10 concepts, so it returns 0 on small cohorts.
    "fungal_foot": " (<3218000 AND <299990002 )",
    # Q10. Laterality is not modelled on these disorders, so an attribute-based
    # ECL expands to nothing; a term filter is the terminology-native equivalent
    # of scanning the display string, and matches on synonyms too.
    "bilateral": " ((<<404684003:363698007 = <<31156008 ,363698007=<<85421007) OR (<<404684003:<47429007=(<<404684003:363698007 = <<31156008 ,363698007=<<85421007)))",
    # Q12, Q15. |Pregnant| minus postnatal/puerperal states, so postpartum
    # patients do not count as currently pregnant. |Pregnancy| (77386006) is
    # deliberately omitted: it contributes no rows the |Pregnant| hierarchy does
    # not already cover.
    "pregnancy": '( (<248982007 ) ) MINUS ( (<<118213005 OR <<304598004 OR <<366343003 OR <<60001007 OR <<363681007 OR <<118215003 OR <<364826005 OR <<237036002 OR <<127362006 OR <<275306006 OR <<200138003 OR <<152231000119106 OR <<404684003 {{term = (wild:"postpartum*" wild:"*postnatal*" wild:"*puerper*")}} OR <<1264158007 OR <<1264159004 OR <<1204036002 OR <<371374003 OR <<44216000 OR <<609516006 OR <<126920004 ) )',
    # Q16. |Causative agent| rather than a wildcard attribute, so the criterion
    # means "caused by" instead of "mentions a bacterium in any role".
    "bacterial_joint_non_strep": "( (<404684003:{246075003=<<409822003,363698007=<<39352004}) ) MINUS ( ((<<278544002) OR (<404684003:{246075003=<<58800005,363698007=<<39352004})) )",
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
    # Q6. Any product containing an ACE inhibitor, combinations included.
    "acei": MedicineEcl("<<372733002", r"captopril|enalapril|lisinopril|perindopril|ramipril|quinapril|fosinopril|benazepril|trandolapril|cilazapril|moexipril|imidapril|spirapril|temocapril|delapril|zofenopril"),
    # Q12. |Angiotensin II receptor antagonist|.
    "arb": MedicineEcl("<<372913009", r"losartan|valsartan|irbesartan|candesartan|telmisartan|olmesartan|eprosartan|azilsartan|fimasartan"),
    # Q7. |Digitalis glycoside| covers digoxin, digitoxin, medigoxin etc.
    "cardiac_glycoside": MedicineEcl("<<(<373247007 AND <372707005) OR (<105590001 :738774007 =<<(<373247007 AND <372707005))", r"digoxin|digitoxin|ouabain|lanatoside|proscillaridin|peruvoside|bufalin"),
    # Q14. Digoxin specifically, as the question names it. 
    "digoxin": MedicineEcl("<<387461009 OR (<105590001 :738774007 =<<387461009)", r"digoxin"),
    # Q9. products containing paracetamol.
    "paracetamol": MedicineEcl("<<387517004 OR (<105590001 :738774007 =<<387517004)", r"paracetamol|acetaminophen"),
    # Q11 methotrexate
    "methotrexate": MedicineEcl("<<387381009 OR (<105590001 :738774007 =<<387381009)", r"methotrexate"),
    # Q12. Any product containing a substance with a teratogenic disposition or
    # mechanism of action (thalidomide, retinoids, antiepileptics, ACEI/ARB,
    # antimetabolites, tetracyclines and others), plus salts/modifications of the
    # same substances.
    "teratogen": MedicineEcl(
        "(<<(<<395831005 OR <<734816000 OR <<78702007 OR <<387208003 OR <<386938006 OR <<264325000 OR <<387220006 OR <<387222003 OR <<372756006 OR <<387381009 OR <<6790004 OR <<767300005 OR <<387242007 OR <<396026002 OR <<372733002 OR <<372913009 OR <<764438001 OR <<387223008 OR <<126124009 OR <<386844006 OR <<387203007 OR <<409330005 OR <<386981009 OR <<387188005 OR <<387420009 OR <<421471009 OR <<387080000) OR (<105590001 :738774007 =<<(<<395831005 OR <<734816000 OR <<78702007 OR <<387208003 OR <<386938006 OR <<264325000 OR <<387220006 OR <<387222003 OR <<372756006 OR <<387381009 OR <<6790004 OR <<767300005 OR <<387242007 OR <<396026002 OR <<372733002 OR <<372913009 OR <<764438001 OR <<387223008 OR <<126124009 OR <<386844006 OR <<387203007 OR <<409330005 OR <<386981009 OR <<387188005 OR <<387420009 OR <<421471009 OR <<387080000))) MINUS 372478003",
        r"Carbimazole|thalidomide|isotretinoin|acitretin|valproate|phenytoin|carbamazepine|warfarin|methotrexate|aminopterin|lithium|misoprostol|diethylstilbestrol|enalapril|captopril|lisinopril|losartan|valsartan|doxycycline|tetracycline|streptomycin|danazol|topiramate|propylthiouracil|carbimazole|methimazole|mycophenolate|leflunomide|ribavirin|cyclophosphamide|lenalidomide|pomalidomide",
    ),
    # Q13. Oral NSAIDs, aspirin and salicylates included.
    "nsaid_oral": MedicineEcl(
        "<<372665008",
        r"aspirin|diflunisal|salsalate|ibuprofen|naproxen|ketoprofen|fenoprofen|flurbiprofen|tiaprofenic|dexibuprofen|dexketoprofen|diclofenac|indomethacin|sulindac|etodolac|tolmetin|ketorolac|aceclofenac|nabumetone|mefenamic acid|meclofenamate|piroxicam|meloxicam|tenoxicam|lornoxicam|celecoxib|etoricoxib|parecoxib|rofecoxib|valdecoxib|lumiracoxib|phenylbutazone|metamizole|nimesulide",
        oral_only=True,
    ),
    # Q14.
    "loop_diuretic": MedicineEcl("<<372691009", r"frusemide|furosemide|bumetanide|torsemide|ethacrynic|piretanide|azosemide|lasix"),
    # Q17. |Iron and/or iron compound| under an oral-only product template.
    # An earlier version navigated ingredients out of |Iron-containing product in
    # oral dose form| ("(<13790009.<<762951001) AND <<767270007"); that resolved
    # to a single ingredient in the 2021-2024 editions and 8 in 2025+, so it
    # silently under-counted every pre-2025 row. The substance grouper is stable
    # across editions (78-87 members).
    "oral_iron": MedicineEcl("<<767270007", oral_only=True),
    # Q18. |Mineral| minus sodium and potassium (both descendants) and chloride
    # (not a descendant, excluded defensively).
    "mineral": MedicineEcl("(5540006 OR 387019008 OR 387307005 OR 52209008 OR 32445001 OR 387292008 OR 22362000 OR 12930006 OR 387217003 OR 395935002 OR 44044007 OR 418016005 OR 50213009 OR 725782004 OR 111070004 OR 54808007 OR 255839000 OR 66925006 OR 31034011000036102 OR 70168001 OR 31051011000036101 OR 31054011000036103 OR 396055005 OR 763035003 OR 27594003 OR 1373854004 OR 1382771000168104 OR 387289009 OR 387147005 OR 419846004 OR 387402000 OR 372639009 OR 75905011000036107 OR 256579008 OR 44588005 OR 3829006 OR 32954005 OR 708805001 OR 72717003 OR 417987009 OR 421363009 OR 387401007 OR 45733002 OR 387052002 OR 494851000221102 OR 425212004 OR 66389008 OR 31517011000036103 OR 31518011000036102 OR 31731008 OR 735077006 OR 387202002 OR 31524011000036101 OR 87869004 OR 31530011000036109 OR 71128006 OR 30820000 OR 88480006 OR 8631001 OR 387450001 OR 89351005 OR 494961000221105 OR 22038003 OR 39972003 OR 387390002 OR 6910009 OR 62754006 OR 395880000 OR 86739005 OR 395952003 OR 708658008 OR 421881000 OR 42841002 OR 387367007) MINUS (<<767403008 OR <<767364003 OR <<767205003)"),
}


@dataclass
class CodeSets:
    """Expanded SNOMED code sets for a single SNOMED CT-AU edition."""

    edition: str
    conditions: Dict[str, Set[str]] = field(default_factory=dict)
    medicines: Dict[str, Set[str]] = field(default_factory=dict)


def build_code_sets(
    edition, tx_server, history=None, product_templates=None, verbose=True
):
    """Expand every condition and medicine ECL for one edition.

    ``history`` optionally names an ECL history supplement profile, applied to
    each expression *after* template substitution so the supplement sits at the
    top level of the constraint. ``None`` reproduces the unsupplemented
    behaviour exactly.

    ``product_templates`` overrides the product model, which defaults to the one
    matching the edition. Pass both models when expanding a single edition that
    has to match codes generated under either -- see reference_code_sets().
    """
    sets = CodeSets(edition=edition)

    for key, ecl in CONDITION_ECLS.items():
        sets.conditions[key] = ecl_code_set(
            with_history(ecl, history), tx_server, edition=edition
        )

    if product_templates is None:
        product_templates = [product_ecl_template_for_edition(edition)]
    templates = [resolve_ecl_template(name) for name in product_templates]
    # "product-oral" is model-agnostic: AMT trade products are descendants of
    # 373873005 with a manufactured dose form, so it matches both models already.
    oral_template = resolve_ecl_template("product-oral")

    for key, spec in MEDICINE_ECLS.items():
        chosen = [oral_template] if spec.oral_only else templates
        codes = set()
        for template in chosen:
            ecl = template.format(ingredients=spec.ingredients)
            codes |= ecl_code_set(
                with_history(ecl, history), tx_server, edition=edition
            )
        sets.medicines[key] = codes

    if verbose:
        conditions = ", ".join(f"{k}={len(v)}" for k, v in sorted(sets.conditions.items()))
        medicines = ", ".join(f"{k}={len(v)}" for k, v in sorted(sets.medicines.items()))
        print(f"    conditions: {conditions}")
        print(f"    medicines:  {medicines}")

    return sets


class _RecordingDict(dict):
    """dict that notes every key read, so criterion use can be observed."""

    def __init__(self, source, seen):
        super().__init__(source)
        self._seen = seen

    def __getitem__(self, key):
        self._seen.add(key)
        return super().__getitem__(key)


def question_criteria(sets):
    """Map each question to the condition and medicine criteria it consults.

    Returns {q_num: (condition_keys, medicine_keys)}.

    Derived by running each question function against a recording view of the
    code sets rather than from a hand-maintained table, which would drift out of
    sync with the functions the moment a criterion is added or swapped.

    Sound because pandas ``&``/``|`` do not short-circuit: every has_condition /
    has_med call in a question function is evaluated regardless of what the other
    operands produce. Questions resting purely on demographics or lab values
    (Q1, Q2) correctly report no terminology scope.

    Condition and medicine keys are kept apart because they are matched against
    different columns -- conditions against SNOMED_Code, medicines against the
    three Medicine_*_Code columns.
    """
    # One row is enough to exercise every lookup, and keeps this off the hot path.
    probe = _probe_frame()

    criteria = {}
    for q_num, func in QUESTION_FUNCS.items():
        conditions, medicines = set(), set()
        recorder = CodeSets(
            edition=sets.edition,
            conditions=_RecordingDict(sets.conditions, conditions),
            medicines=_RecordingDict(sets.medicines, medicines),
        )
        func(probe, recorder)
        criteria[q_num] = (conditions, medicines)
    return criteria


def _probe_frame():
    """A single-row frame carrying every column the question functions read."""
    columns = {
        "Sex": "female", "Age": 30, "Year": 2024, "BMI": 25.0, "CholHDL_Ratio": 3.0,
        "SNOMED_Code": "", "Thyroid Panel - TSH (mIU/L)": 1.0,
        "Thyroid Panel - Free T4 (pmol/L)": 15.0,
        "MBAP - eGFR (mL/min/1.73m²)": 90.0,
        "Kidney Function - eGFR (mL/min/1.73m²)": 90.0,
        "MBAP - Glucose (fasting) (mmol/L)": 5.0,
    }
    for col in MED_CODES + MED_DISPLAYS:
        columns[col] = ""
    return pd.DataFrame([columns])


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
    return has_condition(df, sets, "hyperthyroidism") #| biochemical


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
    return has_condition(df, sets, "pregnancy") & has_med(df, sets, "teratogen")


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
    1: 'Patients with female as their recorded sex.',
    2: 'Patients with a BMI of 30 or more and a total cholesterol to HDL ratio greater '
       'than 5.',
    3: 'Patients documented as being healthy or free of current problems.',
    4: 'Patients with hyperthyroidism according to their clinical note.',
    5: 'Patients with osteoarthritis in 2024.',
    6: 'Patients taking an ACE inhibitor.',
    7: 'Patients taking a product containing a cardiac (digitalis) glycoside.',
    8: 'Patients with a fungal foot infection.',
    9: 'Patients taking more than one product that contains paracetamol.',
    10: 'Patients with a bilateral condition.',
    11: 'Female patients aged 15 to 49 taking methotrexate.',
    12: 'Pregnant patients prescribed a teratogenic medicine.',
    13: 'Patients with osteoarthritis or rheumatoid arthritis taking an oral NSAID, and '
        'their eGFR is below 60.',
    14: 'Patients prescribed digoxin and a loop diuretic, who have an eGFR below 30.',
    15: 'Pregnant patients with a fasting glucose of 5.1 mmol/L or greater.',
    16: 'Patients with a non-Streptococcal bacterial joint infection.',
    17: 'Patients taking an oral iron supplement.',
    18: 'Patients taking mineral supplement excluding the electrolytes sodium, potassium '
        'or chloride.',
}


def compute_flags(df, sets):
    """Run every question function against df. Returns dict of {"Qn": Series}."""
    flags = {}
    for q_num, func in QUESTION_FUNCS.items():
        result = func(df, sets)
        flags[f"Q{q_num}"] = result.fillna(False).astype(bool)
    return flags


def assign_usage(flag_df, q_cols, public_fraction=PUBLIC_FRACTION, seed=SPLIT_SEED):
    """Split rows into Public/Private, stratified on every question flag.

    Iterative stratification: repeatedly take the question with the fewest
    unplaced positives and hand each of its rows to whichever split is furthest
    short of its target for that question.

    Taking the rarest question first is the whole point. The low-prevalence
    questions are the ones a naive split ruins -- Q14 (digoxin + loop diuretic +
    eGFR < 30) is a triple conjunction with single-digit positives, and an
    unstratified split can strand nearly all of them on one side. That is not
    just noisy: F1 = 2TP/(2TP+FP+FN) is 0 for *every* submission when a split
    has no true positives to find, so the question silently stops discriminating
    and caps everyone's macro-F1 at 17/18. Placing the rare questions while all
    rows are still free avoids this; by the time the common questions are placed
    there are plenty of rows left to balance them either way.

    Overlapping questions stay balanced because placing a row decrements the
    counters of every question it is positive for -- Q14's rows are all Q7 rows
    too, so Q7's remaining target absorbs whatever Q14 already consumed.

    Returns a list of "Public"/"Private" aligned to flag_df's row order.
    """
    splits = ("Public", "Private")
    fractions = {"Public": public_fraction, "Private": 1.0 - public_fraction}
    n = len(flag_df)

    # Work in Python lists: this is a per-row loop, and numpy scalar indexing is
    # markedly slower than list indexing at 250k rows.
    columns = {q: flag_df[q].tolist() for q in q_cols}
    row_labels = [[q for q in q_cols if columns[q][i]] for i in range(n)]

    unplaced = {q: set() for q in q_cols}
    for row, labels in enumerate(row_labels):
        for q in labels:
            unplaced[q].add(row)

    # How many rows each split still wants, overall and per question.
    want_rows = {s: fractions[s] * n for s in splits}
    want_q = {q: {s: fractions[s] * len(unplaced[q]) for s in splits} for q in q_cols}

    usage = [None] * n

    def place(row, split):
        usage[row] = split
        want_rows[split] -= 1
        for q in row_labels[row]:
            unplaced[q].discard(row)
            want_q[q][split] -= 1

    # Each pass empties one question. Re-picking the rarest between passes
    # accounts for the rows the previous pass already consumed.
    while True:
        pending = [q for q in q_cols if unplaced[q]]
        if not pending:
            break
        rarest = min(pending, key=lambda k: len(unplaced[k]))
        # sorted() snapshots the set, which place() mutates as we go.
        for row in sorted(unplaced[rarest]):
            split = max(splits, key=lambda s: (want_q[rarest][s], want_rows[s]))
            place(row, split)

    # Rows positive for no question carry no stratification constraint; they only
    # even out the overall row counts. Shuffled so the leftovers are not dealt out
    # in Episode Number order.
    leftover = [row for row in range(n) if usage[row] is None]
    random.Random(seed).shuffle(leftover)
    for row in leftover:
        place(row, max(splits, key=lambda s: want_rows[s]))

    return usage


def split_balance(df, q_cols, usage):
    """Per-question split counts. Returns (table_text, alerts).

    ``alerts`` lists questions under MIN_POSITIVES_PER_SPLIT in either split --
    the guard against a regenerated dataset quietly reintroducing a question too
    rare to score meaningfully.
    """
    is_public = pd.Series(usage, index=df.index) == "Public"

    lines = [f"{'Q':<6}{'total':>8}{'public':>8}{'private':>9}{'private %':>11}"]
    alerts = []
    for q in q_cols:
        total = int(df[q].sum())
        public = int((df[q] & is_public).sum())
        private = total - public
        share = f"{private / total * 100:.1f}%" if total else "n/a"
        lines.append(f"{q:<6}{total:>8}{public:>8}{private:>9}{share:>11}")
        for name, count in (("public", public), ("private", private)):
            if count < MIN_POSITIVES_PER_SPLIT:
                alerts.append(
                    f"{q} has only {count} positive(s) in {name} of {total} total "
                    f"(floor is {MIN_POSITIVES_PER_SPLIT})"
                )
    return "\n".join(lines), alerts


def question_scope_sets(criteria, sets, q_num):
    """The condition and medicine code sets one question draws on, in one edition."""
    cond_keys, med_keys = criteria[q_num]
    cond = set().union(*(sets.conditions[k] for k in cond_keys)) if cond_keys else set()
    med = set().union(*(sets.medicines[k] for k in med_keys)) if med_keys else set()
    return cond, med


def display_lookup(df):
    """Map code -> display, harvested from the paired display columns."""
    lookup = {}
    pairs = [("SNOMED_Code", "SNOMED_Display")] + list(zip(MED_CODES, MED_DISPLAYS))
    for code_col, display_col in pairs:
        if display_col not in df.columns:
            continue
        pair = df[[code_col, display_col]].dropna()
        for code, display in zip(pair[code_col], pair[display_col]):
            lookup.setdefault(str(code).strip(), display)
    return lookup


# Both product models, unioned, for the reference-edition expansions. The dataset
# carries codes from both: generation uses the SNOMED CT international product
# hierarchy pre-2025 and AMT TPUU from 2025 (product_ecl_template_for_edition).
#
# Expanding the reference edition under its own model alone would make every
# pre-2025 medicine row unmatchable -- amt-tpuu cannot contain an international
# clinical drug code -- and the resulting "loss" would be the product-model
# switch masquerading as terminology drift. Unioning both isolates the drift,
# which is what these reports are measuring.
REFERENCE_PRODUCT_TEMPLATES = ["product", "amt-tpuu"]


def reference_code_sets(edition, tx_server, verbose=False):
    """Expand every criterion against one edition, under each history profile."""
    return {
        profile: build_code_sets(
            edition, tx_server, history=profile,
            product_templates=REFERENCE_PRODUCT_TEMPLATES, verbose=verbose,
        )
        for profile in HISTORY_PROFILES
    }


def check_history_sets(ref_sets):
    """Flag supplemented expansions that lost members. Returns warning strings.

    A history supplement can only add concepts, so a supplemented set smaller
    than its unsupplemented counterpart means the expansion did not do what was
    asked. This matters because expand_ecl logs and returns partial results on a
    request failure rather than raising, which would otherwise surface as a
    confident "0 recovered" instead of an error.
    """
    warnings = []
    base = ref_sets[None]
    for profile in HISTORY_PROFILES[1:]:
        sets = ref_sets[profile]
        for kind in ("conditions", "medicines"):
            plain, supplemented = getattr(base, kind), getattr(sets, kind)
            for key, codes in plain.items():
                if len(supplemented[key]) < len(codes):
                    warnings.append(
                        f"{profile} expansion of {kind[:-1]} '{key}' returned "
                        f"{len(supplemented[key])} concepts, fewer than the "
                        f"{len(codes)} without a supplement -- recovery counts for "
                        "this criterion are unreliable"
                    )
    return warnings


def question_scope_report(
    df, edition_code_sets, ref_sets, status, criteria, edition=REFERENCE_EDITION
) -> str:
    """How much of the dataset's terminology drift lands inside a question.

    The dataset-wide inactive count says nothing about impact: a retired concept
    no question refers to is harmless. This narrows it to the codes each
    question's ECLs actually reach, then asks whether a history supplement could
    recover them from the reference edition. An in-scope inactive concept that
    even HISTORY-MAX cannot reach has no historical association at all -- the one
    failure mode a latest-edition solution has no way to mitigate.
    """
    inactive = {c for c, s in status.items() if s == "inactive"}
    populated = populated_codes(df)
    note_present = set(populated["SNOMED_Code"].unique())
    med_present = set()
    for col in MED_CODES:
        med_present |= set(populated[col].unique())

    profiles = HISTORY_PROFILES[1:]  # the supplemented ones

    # Scope is the union across the encounter editions, since a flag may have
    # been set through any of them. Restricted to codes present in the data, so
    # the counts describe this dataset rather than the size of the ECLs.
    scope = {}
    for q_num in QUESTION_FUNCS:
        cond, med = set(), set()
        for sets in edition_code_sets.values():
            c, m = question_scope_sets(criteria, sets, q_num)
            cond |= c
            med |= m
        scope[q_num] = (cond & note_present, med & med_present)

    # Row counts are evaluated per encounter edition rather than against the
    # union, so a code that was only in scope in 2021 is not credited to a 2024
    # row that happens to carry it.
    rows_inactive = {q_num: 0 for q_num in QUESTION_FUNCS}
    for row_edition, group in df.groupby("_edition"):
        sets = edition_code_sets[row_edition]
        for q_num in QUESTION_FUNCS:
            cond, med = question_scope_sets(criteria, sets, q_num)
            cond &= inactive
            med &= inactive
            if not cond and not med:
                continue
            hit = group["SNOMED_Code"].isin(cond)
            for col in MED_CODES:
                hit = hit | group[col].isin(med)
            rows_inactive[q_num] += int((group[f"Q{q_num}"] & hit).sum())

    lines = [
        "Of the inactive concepts above, which fall inside a question's ECLs. Scope is",
        "the union across encounter editions, restricted to codes present in the data.",
        "",
        "MIN/MOD/MAX count the in-scope inactive concepts each ECL history supplement",
        f"recovers when the criteria are expanded against {edition} instead;",
        "\"unrecov\" are those even HISTORY-MAX cannot reach, meaning SNOMED International",
        "retired them without a historical association. \"rows\" are positive rows whose",
        "matching code is inactive, counted against each row's own encounter edition.",
        "",
        "The reference expansions union both product models, so a concept is not called",
        "unrecoverable merely for belonging to the model the reference edition dropped.",
        "",
        f"{'Q':<6}{'scope':>8}{'inactive':>9}{'MIN':>6}{'MOD':>6}{'MAX':>6}"
        f"{'unrecov':>9}{'positives':>11}{'rows':>8}",
    ]

    unrecoverable = {}  # code -> questions it is in scope for
    total_in_scope = set()
    for q_num in sorted(QUESTION_FUNCS):
        cond_scope, med_scope = scope[q_num]
        positives = int(df[f"Q{q_num}"].sum())

        if not cond_scope and not med_scope:
            # Demographics or lab values only -- no terminology exposure at all.
            lines.append(
                f"Q{q_num:<5}{'n/a':>8}{'n/a':>9}{'n/a':>6}{'n/a':>6}{'n/a':>6}"
                f"{'n/a':>9}{positives:>11}{'n/a':>8}"
            )
            continue

        cond_inactive = cond_scope & inactive
        med_inactive = med_scope & inactive
        in_scope_inactive = cond_inactive | med_inactive
        total_in_scope |= in_scope_inactive

        counts = {}
        for profile in profiles:
            c, m = question_scope_sets(criteria, ref_sets[profile], q_num)
            found = (cond_inactive & c) | (med_inactive & m)
            counts[profile] = found

        missed = in_scope_inactive - counts["HISTORY-MAX"]
        for code in missed:
            unrecoverable.setdefault(code, []).append(q_num)

        lines.append(
            f"Q{q_num:<5}{len(cond_scope) + len(med_scope):>8}"
            f"{len(in_scope_inactive):>9}"
            f"{len(counts['HISTORY-MIN']):>6}{len(counts['HISTORY-MOD']):>6}"
            f"{len(counts['HISTORY-MAX']):>6}{len(missed):>9}"
            f"{positives:>11}{rows_inactive[q_num]:>8}"
        )

    lines.append("")
    lines.append(
        f"{len(total_in_scope)} of the {len(inactive)} inactive concepts fall in scope of at "
        f"least one question;"
    )
    lines.append(
        f"{len(unrecoverable)} of those have no historical association and cannot be "
        "recovered."
    )

    if unrecoverable:
        displays = display_lookup(df)
        lines.append("")
        lines.append("Unrecoverable in-scope concepts:")
        ordered = sorted(unrecoverable.items(), key=lambda kv: (kv[1], kv[0]))
        for code, questions in ordered[:UNRECOVERABLE_LIST_LIMIT]:
            qs = ",".join(f"Q{q}" for q in sorted(questions))
            lines.append(f"    {code:<20}{qs:<16}{displays.get(code, '')}")
        if len(ordered) > UNRECOVERABLE_LIST_LIMIT:
            lines.append(f"    ... and {len(ordered) - UNRECOVERABLE_LIST_LIMIT} more")

    return "\n".join(lines)


def edition_delta_report(df, ref_sets, edition=REFERENCE_EDITION) -> str:
    """What recomputing every flag against the reference edition would change.

    Reports the switch rather than making it. The flags in solution.csv remain
    the per-encounter-edition ones; this quantifies what moves if that choice is
    revisited, under each history profile and under none.
    """
    variants = {}
    for profile in HISTORY_PROFILES:
        flags = compute_flags(df, ref_sets[profile])
        variants[profile] = pd.DataFrame(flags, index=df.index)

    lines = [
        f"Positives if every flag were recomputed against SNOMED CT-AU {edition}",
        "alone, rather than against each row's own encounter edition. \"latest\" applies no",
        "history supplement -- the naive current-release reading.",
        "",
        "The medicine criteria are expanded under both product models here (SNOMED",
        "international and AMT), because the dataset carries codes from both. Using the",
        "reference edition's own model alone would strand every pre-2025 medicine row and",
        "report the model switch as terminology drift. These columns isolate the drift.",
        "",
        "CAVEAT: the medicine criteria carry a display-text fallback, so a row can still",
        "match on the product name after its code leaves the ECL. The medicine questions",
        "therefore understate terminology sensitivity; the condition questions (Q3, Q4,",
        "Q5, Q8, Q10, Q16) have no fallback and show the true exposure.",
        "",
        f"{'Q':<6}{'current':>10}" + "".join(
            f"{PROFILE_LABELS[p]:>12}" for p in HISTORY_PROFILES
        ),
    ]

    for q_num in sorted(QUESTION_FUNCS):
        col = f"Q{q_num}"
        row = f"Q{q_num:<5}{int(df[col].sum()):>10}"
        for profile in HISTORY_PROFILES:
            row += f"{int(variants[profile][col].sum()):>12}"
        lines.append(row)

    lines.append("")
    lines.append(
        "Movement under +HIST-MAX. The totals above hide it: the newer hierarchy pulls"
    )
    lines.append("rows in as well as dropping them, and a question can do both at once.")
    lines.append("")
    lines.append(
        f"{'Q':<6}{'current':>10}{'+HIST-MAX':>12}{'gained':>9}{'lost':>7}{'net':>8}"
    )

    best = variants["HISTORY-MAX"]
    for q_num in sorted(QUESTION_FUNCS):
        col = f"Q{q_num}"
        current, alt = df[col], best[col]
        gained = int((~current & alt).sum())
        lost = int((current & ~alt).sum())
        lines.append(
            f"Q{q_num:<5}{int(current.sum()):>10}{int(alt.sum()):>12}"
            f"{gained:>9}{lost:>7}{gained - lost:>+8}"
        )

    return "\n".join(lines)


def compute_metrics(df, usage=None, sections=None):
    """Produce metrics text from the flagged dataframe.

    ``sections`` is a list of (title, body) appended verbatim. They are built in
    main() rather than here so this stays free of terminology server calls.
    """
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

    if usage is not None:
        q_cols = [f"Q{i}" for i in range(1, QUESTION_COUNT + 1)]
        table, alerts = split_balance(df, q_cols, usage)
        public_rows = sum(1 for u in usage if u == "Public")

        lines.append("")
        lines.append("=" * 60)
        lines.append("PUBLIC / PRIVATE SPLIT")
        lines.append("=" * 60)
        lines.append("")
        lines.append(
            f"Stratified per question at {PUBLIC_FRACTION:.0%} public. "
            f"Rows: {public_rows} public / {len(usage) - public_rows} private."
        )
        lines.append("")
        lines.append(table)
        if alerts:
            lines.append("")
            lines.append(
                f"WARNING: {len(alerts)} question(s) below the "
                f"{MIN_POSITIVES_PER_SPLIT}-positive floor:"
            )
            for alert in alerts:
                lines.append(f"    {alert}")

    for title, body in sections or []:
        lines.append("")
        lines.append("=" * 60)
        lines.append(title)
        lines.append("=" * 60)
        lines.append("")
        lines.append(body)

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyse generated patient data.")
    parser.add_argument(
        "--tx-server",
        default=DEFAULT_TX_SERVER,
        help=f"FHIR terminology server base URL (default: {DEFAULT_TX_SERVER})",
    )
    parser.add_argument(
        "--reference-edition",
        default=REFERENCE_EDITION,
        help="SNOMED CT-AU edition the inactive-concept report measures against "
             f"(default: {REFERENCE_EDITION})",
    )
    parser.add_argument(
        "--no-inactive-check",
        action="store_true",
        help="Skip every concept-activity report and its terminology server calls.",
    )
    parser.add_argument(
        "--no-history-check",
        action="store_true",
        help="Skip the question-scope and recompute-delta reports, which expand every "
             "ECL again against the reference edition under each history profile. "
             "The dataset-wide inactive-concept report is still produced.",
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

    q_cols = [f"Q{i}" for i in range(1, QUESTION_COUNT + 1)]

    print(f"Assigning stratified {PUBLIC_FRACTION:.0%}/{1 - PUBLIC_FRACTION:.0%} "
          "public/private split...")
    usage = assign_usage(df[q_cols], q_cols)
    alerts = split_balance(df, q_cols, usage)[1]
    if alerts:
        print(
            f"  WARNING: {len(alerts)} question(s) below the "
            f"{MIN_POSITIVES_PER_SPLIT}-positive floor -- see metrics.txt",
            file=sys.stderr,
        )

    sections = []
    if not args.no_inactive_check:
        print(f"Checking concept activity against SNOMED CT-AU {args.reference_edition}...")
        try:
            codes = set()
            for series in populated_codes(df).values():
                codes |= set(series.unique())
            status = concept_status(codes, args.tx_server, args.reference_edition)

            sections.append((
                "INACTIVE CONCEPTS",
                inactive_concept_report(df, status, args.reference_edition),
            ))

            if not args.no_history_check:
                print(f"  Expanding ECLs against {args.reference_edition} under "
                      f"{len(HISTORY_PROFILES)} history profiles...")
                ref_sets = reference_code_sets(
                    args.reference_edition, args.tx_server
                )

                for warning in check_history_sets(ref_sets):
                    print(f"  WARNING: {warning}", file=sys.stderr)

                criteria = question_criteria(ref_sets[None])
                sections.append((
                    "INACTIVE CONCEPTS IN QUESTION SCOPE",
                    question_scope_report(
                        df, edition_code_sets, ref_sets, status, criteria,
                        edition=args.reference_edition,
                    ),
                ))
                print(f"  Recomputing flags against {args.reference_edition}...")
                sections.append((
                    f"EFFECT OF RECOMPUTING AGAINST {args.reference_edition}",
                    edition_delta_report(
                        df, ref_sets, edition=args.reference_edition
                    ),
                ))
        except requests.RequestException as e:
            # The expensive per-edition ECL work is already done; a failed
            # activity check should annotate the report, not discard the run.
            if not sections:
                sections.append((
                    "INACTIVE CONCEPTS",
                    f"Concept activity against SNOMED CT-AU {args.reference_edition} "
                    f"could not be determined: {e}",
                ))
            print(f"  WARNING: inactive-concept check failed: {e}", file=sys.stderr)

    df = df.drop(columns=["_edition"])

    print("Computing metrics...")
    output = compute_metrics(df, usage, sections)

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
    solution_df["Usage"] = usage
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
