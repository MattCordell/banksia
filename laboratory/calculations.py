"""Laboratory-specific calculated fields and derived values."""

from typing import Any, Dict, Optional

import numpy as np


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
        kappa = 0.8
        alpha = -0.2715

    min_ratio = min(scr_mgdl / kappa, 1.0)
    max_ratio = max(scr_mgdl / kappa, 1.0)

    egfr = 142 * (min_ratio ** alpha) * (max_ratio ** -1.200) * (0.9938 ** age)
    return round(max(egfr, 1.0), 2)


def find_wbc_key(fbc_vals: Dict[str, Any]) -> Optional[str]:
    """Find the WBC key in FBC panel values."""
    for cand in ["WBC (\u00d710^9/L)", "WBC (10^9/L)", "WBC"]:
        if cand in fbc_vals:
            return cand
    for k in fbc_vals.keys():
        if "wbc" in k.lower():
            return k
    return None


def calc_fbc_differential(fbc_vals: Dict[str, Any], wbc_key: Optional[str]) -> Dict[str, Any]:
    """Calculate FBC differential counts using Dirichlet sampling.

    Modifies fbc_vals in-place and returns it.
    """
    diff_names = ["Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils"]

    if wbc_key is None or fbc_vals.get(wbc_key) is None:
        for n in diff_names:
            fbc_vals[f"{n} (%)"] = None
            fbc_vals[f"{n} (\u00d710^9/L)"] = None
        return fbc_vals

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

    return fbc_vals
