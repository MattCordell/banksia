"""Medicine assignment for synthetic patients based on condition."""

import json
import logging
import random
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.types import PatientContext
from conditions.snomed import choose_concept, doomed_codes, expand_ecl, DEFAULT_TX_SERVER

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


def resolve_ecl_template_chain(ecl_template: Optional[str]) -> List[str]:
    """Resolve an ECL template argument to an ordered list of templates.

    A named template may declare a ``"fallback"`` key naming another template
    to try when it expands to nothing. Following those links yields a
    preference-ordered chain, most specific first. Raw template strings and
    templates without a fallback produce a single-entry chain.

    Returns an empty list if *ecl_template* is ``None``.
    """
    if ecl_template is None:
        return []

    templates = _load_ecl_templates()
    chain: List[str] = []
    seen = set()
    key: Optional[str] = ecl_template

    while key is not None and key in templates and key not in seen:
        seen.add(key)
        chain.append(templates[key]["template"])
        key = templates[key].get("fallback")

    if not chain:
        # Assume it's a raw template string
        chain.append(ecl_template)

    return chain


def generate_medicines(
    context: PatientContext,
    tx_server: Optional[str] = None,
    edition: Optional[str] = None,
    no_snomed: bool = False,
    ecl_template: Optional[str] = None,
    inactive_rate: float = 0.0,
    inactive_reference_edition: Optional[str] = None,
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

            A named template may declare a ``"fallback"`` template, tried
            when the preferred one expands to nothing for an ingredient.
            ``"clinical-drug"`` falls back to ``"product"`` this way, so a
            category whose ingredients have no strength-bearing concept in
            the requested edition still yields a code.
        inactive_rate: Probability of biasing the pick toward the subset of
            the winning candidate's expansion that is active at `edition`
            but inactive at `inactive_reference_edition`. 0.0 (default)
            reproduces the unbiased behaviour exactly.
        inactive_reference_edition: SNOMED CT edition to classify concepts
            against when computing the doomed pool. Required for
            inactive_rate to have any effect.

    Returns:
        List of dicts with keys: category, code, display.
        At most MAX_MEDICINES entries. A category that rolls true but draws a
        code already selected for an earlier category in this call is
        dropped rather than re-drawn, so codes are unique within the
        returned list -- the list can end up shorter than MAX_MEDICINES even
        when more categories rolled true than there were unique codes to go
        around.
    """
    prescriptions = _load_prescriptions()
    condition_config = prescriptions.get(context.condition)
    if not condition_config:
        return []

    template_chain = resolve_ecl_template_chain(ecl_template)
    categories = condition_config.get("medicines", [])
    selected: List[Dict[str, Optional[str]]] = []
    used_codes: set = set()

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
                    kwargs: Dict[str, Any] = {}
                    if tx_server:
                        kwargs["tx_server"] = tx_server
                    if edition:
                        kwargs["edition"] = edition

                    if template_chain:
                        candidates = [t.format(ingredients=ecl) for t in template_chain]
                    else:
                        candidates = [ecl]

                    concepts: List[Dict[str, str]] = []
                    for i, candidate in enumerate(candidates):
                        concepts = expand_ecl(candidate, **kwargs)
                        if concepts:
                            break
                        if i + 1 < len(candidates):
                            logger.info(
                                "Empty expansion for %s (%s); falling back to next "
                                "template in chain",
                                cat["category"],
                                ecl,
                            )

                    if concepts:
                        doomed = set()
                        if inactive_rate > 0 and inactive_reference_edition:
                            # candidate is the winning template from the loop
                            # above (the for-loop variable survives the break),
                            # not the raw ingredient ecl -- the doomed lookup
                            # must be keyed on the same expansion concepts came
                            # from, or the clinical-drug -> product fallback
                            # rows would look up the wrong expansion.
                            doomed = doomed_codes(
                                candidate,
                                tx_server=tx_server or DEFAULT_TX_SERVER,
                                edition=edition,
                                reference_edition=inactive_reference_edition,
                            )
                        choice = choose_concept(concepts, doomed, inactive_rate)
                        if choice["code"] in used_codes:
                            continue
                        medicine["code"] = choice["code"]
                        medicine["display"] = choice["display"]
                        used_codes.add(choice["code"])

            selected.append(medicine)

    return selected
