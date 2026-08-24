"""Condition assignment based on Australian epidemiological prevalence data."""

import json
import logging
import random
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from common.types import PatientContext
from .snomed import expand_ecl, choose_concept, doomed_codes, DEFAULT_TX_SERVER

logger = logging.getLogger(__name__)

_EPIDEMIOLOGY_PATH = Path(__file__).parent / "epidemiology.json"
_SNOMED_EXCLUSIONS_PATH = Path(__file__).parent / "snomed_exclusions.json"


@lru_cache(maxsize=1)
def _load_epidemiology() -> Dict[str, Any]:
    """Load and cache epidemiology config."""
    with open(_EPIDEMIOLOGY_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_snomed_exclusions() -> Dict[str, Any]:
    """Load and cache SNOMED CT exclusion category config."""
    if not _SNOMED_EXCLUSIONS_PATH.exists():
        return {}
    with open(_SNOMED_EXCLUSIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _should_exclude(rules: Dict[str, Any], sex: str, age: int) -> bool:
    """Check whether a patient matches any exclusion rule (OR logic)."""
    if rules.get("always"):
        return True
    if sex in rules.get("sex", []):
        return True
    if "min_age" in rules and age >= rules["min_age"]:
        return True
    if "max_age" in rules and age <= rules["max_age"]:
        return True
    return False


def _build_exclusion_set(
    sex: str,
    age: int,
    tx_server: str,
    edition: Optional[str],
) -> Set[str]:
    """Build the set of SNOMED codes to exclude for this patient's demographics."""
    exclusions = _load_snomed_exclusions()
    excluded_codes: Set[str] = set()

    for _category, cfg in exclusions.items():
        rules = cfg.get("exclude_when", {})
        ecl = cfg.get("ecl", "")
        if not ecl or ecl == "...":
            continue
        if _should_exclude(rules, sex, age):
            concepts = expand_ecl(ecl, tx_server=tx_server, edition=edition)
            for c in concepts:
                excluded_codes.add(c["code"])

    return excluded_codes


def _get_age_band(age: int, age_bands: List[Dict]) -> Optional[Dict]:
    """Find the age band covering a given age, or None if uncovered."""
    for band in age_bands:
        if band["min_age"] <= age <= band["max_age"]:
            return band
    return None


def _get_sex_multiplier(sex: str, sex_ratios: Dict[str, float]) -> float:
    """Look up the sex multiplier, falling back to "other" then 1.0."""
    return sex_ratios.get(sex, sex_ratios.get("other", 1.0))


def _compute_adjusted_prevalence(
    condition_cfg: Dict[str, Any],
    sex: str,
    age: int,
    lifestyle: List[str],
) -> float:
    """Compute the demographic-adjusted prevalence for a single condition."""
    base = condition_cfg.get("base_prevalence")
    if base is None:
        return 0.0

    # Age adjustment
    age_bands = condition_cfg.get("age_prevalence", [])
    band = _get_age_band(age, age_bands)
    age_mult = band["multiplier"] if band else 1.0

    # Sex adjustment. A band may carry its own "sex_ratio", which replaces the
    # condition-level one for that age range only (e.g. a male-skewed
    # adolescent/young-adult band in an otherwise sex-neutral condition).
    sex_ratios = condition_cfg.get("sex_ratio", {})
    if band and "sex_ratio" in band:
        sex_ratios = band["sex_ratio"]
    sex_mult = _get_sex_multiplier(sex, sex_ratios)

    # Lifestyle adjustment (multiplicative stacking)
    lifestyle_mults = condition_cfg.get("lifestyle_multipliers", {})
    lifestyle_product = 1.0
    for factor in lifestyle:
        if factor in lifestyle_mults:
            lifestyle_product *= lifestyle_mults[factor]

    return base * sex_mult * age_mult * lifestyle_product


def assign_condition(
    context: PatientContext,
    history: Optional[List[str]] = None,
) -> str:
    """Select a condition based on the patient's demographics and lifestyle.

    Uses Australian epidemiological prevalence data (AIHW/ABS) with
    adjustments for age, sex, and lifestyle factors. "Healthy" is assigned
    when no condition is selected (complement probability).

    Args:
        context: PatientContext with sex, age, lifestyle populated.
        history: Optional list of prior condition names (reserved for future
            comorbidity support, currently unused).

    Returns:
        Condition name string matching keys in epidemiology.json and
        laboratory/conditions.json.
    """
    epi = _load_epidemiology()

    conditions = []
    weights = []

    for name, cfg in epi.items():
        if name == "Healthy":
            continue
        adjusted = _compute_adjusted_prevalence(
            cfg, context.sex, context.age, context.lifestyle or []
        )
        conditions.append(name)
        weights.append(adjusted)

    # Healthy gets the remainder (minimum 10% floor to avoid all-sick cohorts)
    total_disease = sum(weights)
    healthy_weight = max(1.0 - total_disease, 0.10)

    conditions.append("Healthy")
    weights.append(healthy_weight)

    return random.choices(conditions, weights=weights, k=1)[0]


def resolve_snomed_code(
    condition: str,
    sex: str = "",
    age: int = -1,
    tx_server: Optional[str] = None,
    edition: Optional[str] = None,
    inactive_rate: float = 0.0,
    inactive_reference_edition: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """Resolve a SNOMED CT code for the given condition via ECL expansion.

    Expands the condition's ECL expression against the specified terminology
    server, filters out demographically inappropriate concepts (e.g.
    pregnancy codes for males), and randomly selects one code from the
    remaining result set.

    Args:
        condition: Condition name matching a key in epidemiology.json.
        sex: Patient sex for demographic filtering. If empty, no filtering.
        age: Patient age for demographic filtering. If -1, no filtering.
        tx_server: FHIR terminology server URL. Defaults to Ontoserver.
        edition: Optional SNOMED CT edition version (e.g. "20250131").
            If None, the server default is used.
        inactive_rate: Probability of biasing the pick toward the subset of
            the expansion that is active at `edition` but inactive at
            `inactive_reference_edition`. 0.0 (default) reproduces the
            unbiased behaviour exactly.
        inactive_reference_edition: SNOMED CT edition to classify concepts
            against when computing the doomed pool. Required for
            inactive_rate to have any effect.

    Returns:
        Dict with "code", "system", "display" keys, or None if expansion
        fails or returns no results.
    """
    epi = _load_epidemiology()
    cfg = epi.get(condition)
    if not cfg:
        return None

    ecl = cfg.get("ecl")
    if not ecl:
        return None

    server = tx_server or DEFAULT_TX_SERVER
    concepts = expand_ecl(ecl, tx_server=server, edition=edition)

    if not concepts:
        return None

    # Apply demographic filtering if sex and age are provided
    if sex and age >= 0:
        excluded = _build_exclusion_set(sex, age, server, edition)
        if excluded:
            filtered = [c for c in concepts if c["code"] not in excluded]
            if filtered:
                concepts = filtered
            else:
                logger.warning(
                    "All %d concepts excluded for %s (sex=%s, age=%d); "
                    "falling back to unfiltered list",
                    len(concepts), condition, sex, age,
                )

    doomed = set()
    if inactive_rate > 0 and inactive_reference_edition:
        doomed = doomed_codes(
            ecl,
            tx_server=server,
            edition=edition,
            reference_edition=inactive_reference_edition,
        )

    chosen = choose_concept(concepts, doomed, inactive_rate)
    return {
        "code": chosen["code"],
        "system": "http://snomed.info/sct",
        "display": chosen["display"],
    }
