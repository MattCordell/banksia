"""Laboratory result generator."""

import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from common.sampling import sample_value
from common.config import load_profiles, merge_profiles
from common.adjustments import apply_adjustments
from common.types import PatientContext

from .calculations import (
    calc_anion_gap,
    calc_egfr_ckd_epi_2021,
    calc_fbc_differential,
    find_wbc_key,
)

_DEFAULT_PANELS = Path(__file__).parent / "panels.json"
_DEFAULT_CONDITIONS = Path(__file__).parent / "conditions.json"


def _resolve_profiles(
    profiles: Optional[Union[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Resolve profiles argument to a loaded dict."""
    if profiles is None:
        return load_profiles(str(_DEFAULT_PANELS), str(_DEFAULT_CONDITIONS))
    elif isinstance(profiles, str):
        return load_profiles(profiles, profiles)
    return profiles


def generate_lab_results(
    context: PatientContext,
    profiles: Optional[Union[str, Dict[str, Any]]] = None,
    missing_panel_prob: float = 0.12,
    rng_seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate lab results for a single patient.

    Args:
        context: PatientContext with sex, age, lifestyle, condition.
        profiles: Loaded profiles dict or None for defaults.
        missing_panel_prob: Probability of omitting a whole panel.
        rng_seed: Optional seed for reproducibility.

    Returns:
        Dict with all result columns (flat). Keys are
        "Panel - Test Name" strings, plus "Sex", "Age", "Condition".
    """
    if rng_seed is not None:
        np.random.seed(rng_seed)
        random.seed(rng_seed)

    profiles_dict = _resolve_profiles(profiles)

    condition = context.condition
    sex = context.sex
    age = context.age
    lifestyle = context.lifestyle or []

    if condition not in profiles_dict["conditions"]:
        raise ValueError(f"Condition '{condition}' not found in profiles")

    base = {"panels": profiles_dict["panels"]}
    cond = profiles_dict["conditions"][condition]
    merged = merge_profiles(base, cond)
    # Allow single-level inheritance
    if cond.get("inherits"):
        parent = profiles_dict["conditions"].get(cond["inherits"])
        if parent:
            merged = merge_profiles(merged, parent)
            merged = merge_profiles(merged, cond)

    # Decide panels to omit (whole panel)
    panel_names = list(merged["panels"].keys())
    panels_to_omit: List[str] = []
    if random.random() < missing_panel_prob:
        panels_to_omit = random.sample(panel_names, random.choice([1, 2]))

    # Order panels so those with condition overrides are sampled first.
    overridden_panels = set(cond.get("panel_overrides", {}).keys())
    panel_order = [p for p in panel_names if p in overridden_panels] + \
                  [p for p in panel_names if p not in overridden_panels]

    shared_values: Dict[str, float] = {}
    results_per_panel: Dict[str, Optional[Dict[str, Optional[float]]]] = {}

    for panel in panel_order:
        if panel in panels_to_omit:
            results_per_panel[panel] = None
            continue
        panel_tests = merged["panels"][panel]
        panel_out: Dict[str, Optional[float]] = {}
        for test_name, params in panel_tests.items():
            if test_name == "differential_props":
                panel_out[test_name] = params
                continue
            if params.get("calculated"):
                continue
            if test_name in shared_values:
                val = shared_values[test_name]
            else:
                adj_mean, adj_sd = apply_adjustments(params, sex, age, lifestyle)
                tmp = {
                    "distribution": params.get("distribution", "normal"),
                    "mean": adj_mean,
                    "sd": adj_sd,
                    "min": params.get("min", params.get("min_val", None)),
                    "max": params.get("max", params.get("max_val", None)),
                }
                val = sample_value(tmp)
                shared_values[test_name] = val
            panel_out[test_name] = val
        results_per_panel[panel] = panel_out

    # Post-processing: calculated fields
    for pn in panel_names:
        if pn in panels_to_omit or results_per_panel.get(pn) is None:
            continue
        panel_def = merged["panels"][pn]
        pvals = results_per_panel[pn]
        for test_name, params in panel_def.items():
            if not params.get("calculated"):
                continue
            formula = params.get("formula", "")
            if formula == "anion_gap":
                val = calc_anion_gap(pvals)
                if val is not None:
                    pvals[test_name] = val
                    shared_values[test_name] = val
            elif formula == "ckd_epi_2021":
                creat_key = "Creatinine (\u00b5mol/L)"
                creat_val = shared_values.get(creat_key) or pvals.get(creat_key)
                if creat_val is not None:
                    val = calc_egfr_ckd_epi_2021(float(creat_val), age, sex)
                    pvals[test_name] = val
                    shared_values[test_name] = val

    # FBC differential
    fbc_panel = None
    for pn in panel_names:
        low = pn.lower()
        if "fbc" in low or ("full" in low and "blood" in low):
            fbc_panel = pn
            break

    if fbc_panel and results_per_panel.get(fbc_panel) is not None:
        fbc_vals = results_per_panel[fbc_panel]
        wbc_key = find_wbc_key(fbc_vals)
        calc_fbc_differential(fbc_vals, wbc_key)

    # Flatten into dict
    diff_names = ["Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils"]
    all_cols = ["Sex", "Age", "Condition"]
    for panel in panel_names:
        for test_name in merged["panels"][panel].keys():
            if test_name == "differential_props":
                if panel == fbc_panel:
                    for n in diff_names:
                        all_cols.append(f"{panel} - {n} (%)")
                        all_cols.append(f"{panel} - {n} (\u00d710^9/L)")
                continue
            all_cols.append(f"{panel} - {test_name}")

    # Dedupe while preserving order
    seen = set()
    cols = []
    for c in all_cols:
        if c not in seen:
            seen.add(c)
            cols.append(c)

    row: Dict[str, Any] = {c: None for c in cols}
    row["Sex"] = sex
    row["Age"] = age
    row["Condition"] = condition

    for panel, vals in results_per_panel.items():
        if vals is None:
            continue
        for tn, v in vals.items():
            if tn == "differential_props":
                continue
            col = f"{panel} - {tn}"
            row[col] = v

    return row
