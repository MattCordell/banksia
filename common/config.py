"""Configuration loading and merging utilities."""

import json
from pathlib import Path
from typing import Any, Dict


def load_profiles(panels_path: str, conditions_path: str) -> Dict[str, Any]:
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
