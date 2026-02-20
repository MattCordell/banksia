"""Demographic and lifestyle adjustment pipeline for test parameters."""

from typing import Any, Dict, List, Tuple


def apply_adjustments(
    params: Dict[str, Any],
    sex: str,
    age: int,
    lifestyle: List[str],
) -> Tuple[float, float]:
    """Apply sex, age, and lifestyle adjustments to a test's mean and sd.

    Returns:
        (adjusted_mean, adjusted_sd)
    """
    adj_mean = float(params.get("mean", 0))
    adj_sd = float(params.get("sd", max(0.01, 0.1 * adj_mean)))

    # Sex adjustment
    if "sex_adjustment" in params:
        mult = params["sex_adjustment"].get(
            str(sex).lower(),
            params["sex_adjustment"].get("other", 1.0)
        )
        adj_mean *= mult
        adj_sd *= mult

    # Age adjustment (slope-based)
    if "age_adjustment" in params:
        age_adj = params["age_adjustment"]
        if isinstance(age_adj, dict) and age_adj.get("slope"):
            slope = float(age_adj.get("slope", 0.0))
            ref = float(age_adj.get("ref_age", 40))
            factor = 1.0 + slope * max(0, age - ref)
            adj_mean *= factor
            adj_sd *= factor

    # Lifestyle adjustments
    if lifestyle and "lifestyle" in params:
        for fac in lifestyle:
            if fac in params["lifestyle"]:
                fac_info = params["lifestyle"][fac]
                adj_mean *= float(fac_info.get("mean_multiplier", 1.0))
                adj_sd *= float(fac_info.get("sd_multiplier", 1.0))

    return adj_mean, adj_sd
