"""Statistical distribution sampling helpers."""

from typing import Any, Dict

import numpy as np


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
    """Central dispatcher: sample from a distribution described by a params dict."""
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
