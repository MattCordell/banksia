"""
synthetic_lab_generator.py

Usage:
    from synthetic_lab_generator import generate_lab_results, generate_cohort, load_profiles
    profiles = load_profiles("panels.json", "conditions.json")
    df = generate_lab_results(condition="Alcoholic Liver Disease", sex="non-binary", age=54,
                              lifestyle=["heavy_drinker","smoker"], profiles=profiles)
    cohort = generate_cohort(100, profiles=profiles)
"""

import json
import math
import random
from pathlib import Path
from typing import Optional, Union, Dict, Any, List

import numpy as np
import pandas as pd

# -----------------------------
# Load / helper
# -----------------------------
def load_profiles(panels_path: str = "panels.json",
                  conditions_path: str = "conditions.json") -> Dict[str, Any]:
    """Load panels and conditions from separate JSON files.
    Returns a combined dict: {"panels": {...}, "conditions": {...}}
    """
    pp = Path(panels_path)
    cp = Path(conditions_path)
    if not pp.exists():
        raise FileNotFoundError(f"Panels JSON not found at {pp.resolve()}")
    if not cp.exists():
        raise FileNotFoundError(f"Conditions JSON not found at {cp.resolve()}")
    with pp.open("r", encoding="utf-8") as fh:
        panels = json.load(fh)
    with cp.open("r", encoding="utf-8") as fh:
        conditions = json.load(fh)
    return {"panels": panels, "conditions": conditions}


# Sampling helpers
def _sample_normal(mean: float, sd: float) -> float:
    return float(np.random.normal(mean, sd))

def _sample_lognormal(mean: float, sd: float) -> float:
    m = max(mean, 1e-9)
    s = max(sd, 1e-9)
    mu = np.log(m**2 / np.sqrt(s**2 + m**2))
    sigma = np.sqrt(np.log(1 + (s**2 / m**2)))
    return float(np.random.lognormal(mu, sigma))

def _sample_uniform(min_v: float, max_v: float) -> float:
    return float(np.random.uniform(min_v, max_v))

def _sample_gamma(mean: float, sd: float) -> float:
    m = max(mean, 1e-9)
    s = max(sd, 1e-9)
    k = (m**2) / (s**2)
    theta = (s**2) / m
    return float(np.random.gamma(shape=k, scale=theta))

def sample_value(params: Dict[str, Any]) -> float:
    dist = params.get("distribution", "normal").lower()
    mean = float(params["mean"])
    sd = float(params.get("sd", max(0.01, 0.1 * mean)))
    min_v = params.get("min", params.get("min_val", None))
    max_v = params.get("max", params.get("max_val", None))

    if dist == "normal":
        val = _sample_normal(mean, sd)
    elif dist == "lognormal":
        val = _sample_lognormal(mean, sd)
    elif dist == "uniform":
        if min_v is None or max_v is None:
            raise ValueError("uniform distribution requires min and max")
        val = _sample_uniform(min_v, max_v)
    elif dist == "gamma":
        val = _sample_gamma(mean, sd)
    else:
        raise ValueError(f"Unsupported distribution '{dist}'")

    if (min_v is not None) and (max_v is not None):
        val = float(np.clip(val, min_v, max_v))
    return round(val, 2)


# -----------------------------
# Calculated field functions
# -----------------------------
def calc_anion_gap(panel_vals: Dict[str, Any]) -> Optional[float]:
    """Calculate Anion Gap = Sodium - Chloride - Bicarbonate."""
    na = panel_vals.get("Sodium (mmol/L)")
    cl = panel_vals.get("Chloride (mmol/L)")
    hco3 = panel_vals.get("Bicarbonate (mmol/L)")
    if na is not None and cl is not None and hco3 is not None:
        return round(float(na) - float(cl) - float(hco3), 2)
    return None

def calc_egfr_ckd_epi_2021(creatinine_umol: float, age: int, sex: str) -> float:
    """2021 CKD-EPI equation (race-free).

    eGFR = 142 * min(Scr/kappa, 1)^alpha * max(Scr/kappa, 1)^(-1.200) * 0.9938^Age

    Where Scr is in mg/dL, kappa and alpha are sex-dependent.
    """
    scr_mgdl = creatinine_umol / 88.4
    sex_lower = (sex or "other").lower()

    if sex_lower == "female":
        kappa = 0.7
        alpha = -0.241
    elif sex_lower == "male":
        kappa = 0.9
        alpha = -0.302
    else:
        # Non-binary / other: average of male and female parameters
        kappa = 0.8
        alpha = -0.2715

    min_ratio = min(scr_mgdl / kappa, 1.0)
    max_ratio = max(scr_mgdl / kappa, 1.0)

    egfr = 142 * (min_ratio ** alpha) * (max_ratio ** -1.200) * (0.9938 ** age)
    return round(max(egfr, 1.0), 2)


# -----------------------------
# Profile merging
# -----------------------------
def merge_profiles(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge overrides into base panels structure. Returns a new dict."""
    merged = json.loads(json.dumps(base))  # deep copy
    panel_overrides = overrides.get("panel_overrides", {})
    for panel, tests in panel_overrides.items():
        if panel not in merged["panels"]:
            merged["panels"][panel] = {}
        for test, params in tests.items():
            merged["panels"][panel].setdefault(test, {})
            merged["panels"][panel][test].update(params)
    return merged


# -----------------------------
# Main generator
# -----------------------------
def generate_lab_results(condition: str,
                         sex: str = "other",
                         age: int = 50,
                         lifestyle: Optional[List[str]] = None,
                         profiles: Optional[Union[str, Dict[str, Any]]] = None,
                         missing_panel_prob: float = 0.12,
                         rng_seed: Optional[int] = None) -> pd.DataFrame:
    """Generate one patient row for a given condition.
    Panels omitted whole with probability missing_panel_prob.
    """
    if rng_seed is not None:
        np.random.seed(rng_seed)
        random.seed(rng_seed)

    if lifestyle is None:
        lifestyle = []

    # Load profiles if needed
    if profiles is None:
        profiles_dict = load_profiles()
    elif isinstance(profiles, str):
        profiles_dict = load_profiles(profiles)
    else:
        profiles_dict = profiles

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
    panels_to_omit = []
    if random.random() < missing_panel_prob:
        panels_to_omit = random.sample(panel_names, random.choice([1, 2]))

    # Order panels so those with condition overrides are sampled first.
    # This ensures overridden values (e.g. CKD creatinine=300) are placed
    # into shared_values before baseline panels (e.g. MBAP creatinine=80).
    overridden_panels = set(cond.get("panel_overrides", {}).keys())
    panel_order = [p for p in panel_names if p in overridden_panels] + \
                  [p for p in panel_names if p not in overridden_panels]

    # Shared values across panels (if same test name appears in two panels)
    shared_values: Dict[str, float] = {}

    results_per_panel: Dict[str, Optional[Dict[str, Optional[float]]]] = {}
    for panel in panel_order:
        if panel in panels_to_omit:
            results_per_panel[panel] = None
            continue
        panel_tests = merged["panels"][panel]
        panel_out: Dict[str, Optional[float]] = {}
        for test_name, params in panel_tests.items():
            # Copy metadata keys if present
            if test_name == "differential_props":
                panel_out[test_name] = params
                continue
            # Skip calculated fields (handled in post-processing)
            if params.get("calculated"):
                continue
            # If test already sampled by another panel, reuse
            if test_name in shared_values:
                val = shared_values[test_name]
            else:
                adj_mean = params.get("mean")
                adj_sd = params.get("sd", max(0.01, 0.1 * float(adj_mean)))
                # Sex adjustment: {'male':1.1, 'female':0.9}
                if "sex_adjustment" in params:
                    mult = params["sex_adjustment"].get(
                        str(sex).lower(),
                        params["sex_adjustment"].get("other", 1.0))
                    adj_mean = adj_mean * mult
                    adj_sd = adj_sd * mult
                # Age adjustment (slope-based): {'slope':0.005, 'ref_age':40}
                if "age_adjustment" in params:
                    age_adj = params["age_adjustment"]
                    if isinstance(age_adj, dict) and age_adj.get("slope"):
                        slope = float(age_adj.get("slope", 0.0))
                        ref = float(age_adj.get("ref_age", 40))
                        factor = 1.0 + slope * max(0, age - ref)
                        adj_mean = adj_mean * factor
                        adj_sd = adj_sd * factor
                # Lifestyle adjustments: {'heavy_drinker': {'mean_multiplier':1.4}}
                if lifestyle and "lifestyle" in params:
                    for fac in lifestyle:
                        if fac in params["lifestyle"]:
                            fac_info = params["lifestyle"][fac]
                            adj_mean = adj_mean * float(fac_info.get("mean_multiplier", 1.0))
                            adj_sd = adj_sd * float(fac_info.get("sd_multiplier", 1.0))
                tmp = {"distribution": params.get("distribution", "normal"),
                       "mean": adj_mean, "sd": adj_sd,
                       "min": params.get("min", params.get("min_val", None)),
                       "max": params.get("max", params.get("max_val", None))}
                val = sample_value(tmp)
                shared_values[test_name] = val
            panel_out[test_name] = val
        results_per_panel[panel] = panel_out

    # --- Post-processing: calculated fields ---

    # Anion Gap (MBAP panel)
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
                # Find creatinine value from shared_values or this panel
                creat_key = "Creatinine (\u00b5mol/L)"
                creat_val = shared_values.get(creat_key) or pvals.get(creat_key)
                if creat_val is not None:
                    val = calc_egfr_ckd_epi_2021(float(creat_val), age, sex)
                    pvals[test_name] = val
                    shared_values[test_name] = val

    # --- FBC differential (Dirichlet-based) ---
    fbc_panel = None
    for pn in panel_names:
        low = pn.lower()
        if "fbc" in low or ("full" in low and "blood" in low):
            fbc_panel = pn
            break

    if fbc_panel and results_per_panel.get(fbc_panel) is not None:
        fbc_vals = results_per_panel[fbc_panel]
        wbc_key = None
        for cand in ["WBC (\u00d710^9/L)", "WBC (10^9/L)", "WBC"]:
            if cand in fbc_vals:
                wbc_key = cand
                break
        if not wbc_key:
            for k in fbc_vals.keys():
                if "wbc" in k.lower():
                    wbc_key = k
                    break
        diff_names = ["Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils"]
        if wbc_key is None or fbc_vals.get(wbc_key) is None:
            for n in diff_names:
                fbc_vals[f"{n} (%)"] = None
                fbc_vals[f"{n} (\u00d710^9/L)"] = None
        else:
            total_wbc = float(fbc_vals[wbc_key])
            base_props = None
            if "differential_props" in fbc_vals:
                md = fbc_vals["differential_props"]
                try:
                    base_props = np.array([
                        float(md.get("neutrophils", 0.55)),
                        float(md.get("lymphocytes", 0.30)),
                        float(md.get("monocytes", 0.06)),
                        float(md.get("eosinophils", 0.07)),
                        float(md.get("basophils", 0.02))
                    ])
                    if base_props.sum() <= 0:
                        base_props = None
                except Exception:
                    base_props = None
            if base_props is None:
                base_props = np.array([0.55, 0.30, 0.06, 0.07, 0.02])
            alpha = base_props * 50.0
            sampled = np.random.dirichlet(alpha)
            abs_counts = np.round(sampled * total_wbc, 2)
            diff = round(total_wbc - abs_counts.sum(), 2)
            if abs(diff) >= 0.01:
                idx = int(np.argmax(abs_counts))
                abs_counts[idx] = round(abs_counts[idx] + diff, 2)
            for name, prop, abs_val in zip(diff_names, sampled, abs_counts):
                fbc_vals[f"{name} (%)"] = round(float(prop * 100.0), 2)
                fbc_vals[f"{name} (\u00d710^9/L)"] = float(abs_val)
            if "differential_props" in fbc_vals:
                del fbc_vals["differential_props"]
            results_per_panel[fbc_panel] = fbc_vals

    # --- Flatten into single consistent row ---
    all_cols = ["Sex", "Age", "Condition"]
    for panel in panel_names:
        for test_name in merged["panels"][panel].keys():
            if test_name == "differential_props":
                if panel == fbc_panel:
                    for n in ["Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils"]:
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

    row = {c: None for c in cols}
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

    df = pd.DataFrame([row])
    return df


# -----------------------------
# Cohort helper
# -----------------------------
def generate_cohort(n: int,
                    profiles: Optional[Union[str, Dict[str, Any]]] = None,
                    condition_sampler: Optional[List[str]] = None,
                    sex_choices: Optional[List[str]] = None,
                    age_range: Optional[List[int]] = None,
                    lifestyle_choices: Optional[List[List[str]]] = None,
                    missing_panel_prob: float = 0.12,
                    rng_seed: Optional[int] = None) -> pd.DataFrame:
    """Generate n patients. Returns a DataFrame concatenating rows."""
    if profiles is None:
        profiles_dict = load_profiles()
    elif isinstance(profiles, str):
        profiles_dict = load_profiles(profiles)
    else:
        profiles_dict = profiles

    conditions = condition_sampler if condition_sampler else list(profiles_dict["conditions"].keys())
    sex_choices = sex_choices if sex_choices else ["male", "female", "non-binary"]
    age_range = age_range if age_range else [20, 85]
    lifestyle_choices = lifestyle_choices if lifestyle_choices else [
        [], ["smoker"], ["heavy_drinker"], ["athlete"], ["high_bmi"], None
    ]
    rows = []
    for i in range(n):
        cond = random.choice(conditions)
        sex = random.choice(sex_choices)
        age = random.randint(age_range[0], age_range[1])
        lf = random.choice(lifestyle_choices)
        row = generate_lab_results(
            condition=cond, sex=sex, age=age, lifestyle=lf,
            profiles=profiles_dict, missing_panel_prob=missing_panel_prob,
            rng_seed=(None if rng_seed is None else rng_seed + i))
        rows.append(row)
    cohort = pd.concat(rows, ignore_index=True)
    return cohort


def get_random_condition(conditions_path: str = "conditions.json") -> str:
    """Returns the name of a randomly selected condition."""
    with open(conditions_path, "r", encoding="utf-8") as f:
        conditions = json.load(f)
    return random.choice(list(conditions.keys()))


# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    profiles = load_profiles("panels.json", "conditions.json")
    # Single patient
    df = generate_lab_results(
        condition="Hypothyroidism", sex="non-binary", age=54,
        lifestyle=["heavy_drinker", "smoker"], profiles=profiles)
    print("Single patient (transposed):\n", df.T.head(80))
    # Cohort of 10
    coh = generate_cohort(10, profiles=profiles)
    print("\nCohort head:\n", coh.head())
