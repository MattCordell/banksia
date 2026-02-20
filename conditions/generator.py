"""Condition assignment based on Australian epidemiological prevalence data."""

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.types import PatientContext
from .snomed import expand_ecl, DEFAULT_TX_SERVER

_EPIDEMIOLOGY_PATH = Path(__file__).parent / "epidemiology.json"


@lru_cache(maxsize=1)
def _load_epidemiology() -> Dict[str, Any]:
    """Load and cache epidemiology config."""
    with open(_EPIDEMIOLOGY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _get_age_multiplier(age: int, age_bands: List[Dict]) -> float:
    """Find the age-band multiplier for a given age."""
    for band in age_bands:
        if band["min_age"] <= age <= band["max_age"]:
            return band["multiplier"]
    return 1.0


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

    # Sex adjustment
    sex_ratios = condition_cfg.get("sex_ratio", {})
    sex_mult = sex_ratios.get(sex, sex_ratios.get("other", 1.0))

    # Age adjustment
    age_bands = condition_cfg.get("age_prevalence", [])
    age_mult = _get_age_multiplier(age, age_bands)

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
    tx_server: Optional[str] = None,
    edition: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """Resolve a SNOMED CT code for the given condition via ECL expansion.

    Expands the condition's ECL expression against the specified terminology
    server and randomly selects one code from the result set.

    Args:
        condition: Condition name matching a key in epidemiology.json.
        tx_server: FHIR terminology server URL. Defaults to Ontoserver.
        edition: Optional SNOMED CT edition version (e.g. "20250131").
            If None, the server default is used.

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

    chosen = random.choice(concepts)
    return {
        "code": chosen["code"],
        "system": "http://snomed.info/sct",
        "display": chosen["display"],
    }
