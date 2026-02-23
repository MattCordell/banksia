"""Medicine assignment for synthetic patients based on condition."""

import json
import logging
import random
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.types import PatientContext
from conditions.snomed import expand_ecl

logger = logging.getLogger(__name__)

MAX_MEDICINES = 3

_CONFIG_PATH = Path(__file__).parent / "prescriptions.json"
_TEMPLATES_PATH = Path(__file__).parent / "ecl_templates.json"


@lru_cache(maxsize=1)
def _load_prescriptions() -> Dict[str, Any]:
    """Load the prescriptions config (cached)."""
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_ecl_templates() -> Dict[str, Any]:
    """Load the named ECL templates (cached)."""
    with open(_TEMPLATES_PATH, encoding="utf-8") as f:
        return json.load(f)


def resolve_ecl_template(ecl_template: Optional[str]) -> Optional[str]:
    """Resolve an ECL template argument to a template string.

    Accepts either a named key (e.g. ``"amt-tpuu"``) that is looked up in
    ``ecl_templates.json``, or a raw template string containing
    ``{ingredients}``. Returns ``None`` if *ecl_template* is ``None``.
    """
    if ecl_template is None:
        return None
    templates = _load_ecl_templates()
    if ecl_template in templates:
        return templates[ecl_template]["template"]
    # Assume it's a raw template string
    return ecl_template


def generate_medicines(
    context: PatientContext,
    tx_server: Optional[str] = None,
    edition: Optional[str] = None,
    no_snomed: bool = False,
    ecl_template: Optional[str] = None,
) -> List[Dict[str, Optional[str]]]:
    """Select medicines for a patient based on their condition.

    Each medicine category for the condition is rolled against its
    probability. Selected categories have their ECL expanded via
    the terminology server and a random code is picked.

    Args:
        context: The patient context (must have condition assigned).
        tx_server: FHIR terminology server URL (None = default Ontoserver).
        edition: SNOMED CT edition version string.
        no_snomed: If True, return category names only (code/display as None).
        ecl_template: Named template key (e.g. ``"amt-tpuu"``) or raw ECL
            template string with an ``{ingredients}`` placeholder. Named
            keys are looked up in ``ecl_templates.json``. When provided,
            the ingredient ECL is substituted into the template before
            expansion, allowing product-level selection. When None, the
            raw ingredient ECL is expanded directly.

    Returns:
        List of dicts with keys: category, code, display.
        At most MAX_MEDICINES entries.
    """
    prescriptions = _load_prescriptions()
    condition_config = prescriptions.get(context.condition)
    if not condition_config:
        return []

    resolved_template = resolve_ecl_template(ecl_template)
    categories = condition_config.get("medicines", [])
    selected: List[Dict[str, Optional[str]]] = []

    for cat in categories:
        if len(selected) >= MAX_MEDICINES:
            break
        if random.random() < cat["probability"]:
            medicine: Dict[str, Optional[str]] = {
                "category": cat["category"],
                "code": None,
                "display": None,
            }

            if not no_snomed:
                ecl = cat.get("ecl", "")
                if ecl:
                    if resolved_template:
                        ecl = resolved_template.format(ingredients=ecl)
                    kwargs: Dict[str, Any] = {}
                    if tx_server:
                        kwargs["tx_server"] = tx_server
                    if edition:
                        kwargs["edition"] = edition
                    concepts = expand_ecl(ecl, **kwargs)
                    if concepts:
                        choice = random.choice(concepts)
                        medicine["code"] = choice["code"]
                        medicine["display"] = choice["display"]

            selected.append(medicine)

    return selected
