"""SNOMED CT ECL expansion via Ontoserver FHIR ValueSet/$expand."""

import json
import logging
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests

logger = logging.getLogger(__name__)

DEFAULT_TX_SERVER = "https://tx.ontoserver.csiro.au/fhir"
AU_MODULE = "http://snomed.info/sct/32506021000036107"

# Codes per ValueSet/$expand call when checking concept activity. 1000 keeps the
# request comfortably inside Ontoserver's limits at ~20 calls for a 250k dataset.
CONCEPT_STATUS_BATCH = 1000

# Module-level cache: (ecl, tx_server, edition) -> list of {code, display}
_cache: Dict[Tuple[str, str, Optional[str]], List[Dict[str, str]]] = {}

# Disk cache of doomed-code sets, keyed by "edition::reference_edition::tx_server::ecl".
# generate_data.py spawns a subprocess per period, so an in-memory cache alone
# would be discarded between periods; this persists across processes and does
# not depend on inactive_rate, so a tuning run only pays for it once.
_DOOMED_CACHE_PATH = Path(__file__).parent / ".doomed_cache.json"
_doomed_cache: Optional[Dict[str, List[str]]] = None


def expand_ecl(
    ecl: str,
    tx_server: str = DEFAULT_TX_SERVER,
    edition: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Expand a SNOMED CT ECL expression via FHIR ValueSet/$expand.

    Results are cached by (ecl, tx_server, edition) so repeated calls
    with the same parameters don't hit the server again. Changing the
    edition parameter naturally invalidates the cache for that ECL.

    Args:
        ecl: SNOMED CT Expression Constraint Language expression.
        tx_server: FHIR terminology server base URL.
        edition: Optional SNOMED CT edition version string (e.g. "20250131").
            If None, the server default edition is used.

    Returns:
        List of dicts with "code" and "display" keys.
    """
    cache_key = (ecl, tx_server, edition)
    if cache_key in _cache:
        return _cache[cache_key]

    concepts = _expand_ecl_remote(ecl, tx_server, edition)
    _cache[cache_key] = concepts
    return concepts


def _expand_ecl_remote(
    ecl: str,
    tx_server: str,
    edition: Optional[str],
) -> List[Dict[str, str]]:
    """Call the FHIR terminology server to expand an ECL expression."""
    if edition:
        vs_url = f"{AU_MODULE}/version/{edition}?fhir_vs=ecl/{ecl}"
    else:
        vs_url = f"http://snomed.info/sct?fhir_vs=ecl/{ecl}"

    params = {
        "url": vs_url,
        "count": 10000,
    }
    headers = {"Accept": "application/fhir+json"}

    concepts: List[Dict[str, str]] = []
    offset = 0

    while True:
        params["offset"] = offset
        try:
            resp = requests.get(
                f"{tx_server}/ValueSet/$expand",
                params=params,
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("ECL expansion failed for '%s': %s", ecl, e)
            # Retry once after a delay
            time.sleep(5)
            try:
                resp = requests.get(
                    f"{tx_server}/ValueSet/$expand",
                    params=params,
                    headers=headers,
                    timeout=60,
                )
                resp.raise_for_status()
            except requests.RequestException as e2:
                logger.error("ECL expansion retry failed for '%s': %s", ecl, e2)
                return concepts

        data = resp.json()
        expansion = data.get("expansion", {})
        contains = expansion.get("contains", [])
        if not contains:
            break

        for entry in contains:
            code = entry.get("code")
            display = entry.get("display", "")
            if code:
                concepts.append({"code": code, "display": display})

        total = expansion.get("total")
        if total is not None and len(concepts) >= total:
            break

        offset += len(contains)
        time.sleep(0.2)

    return concepts


def clear_cache() -> None:
    """Clear the expansion cache (useful for testing)."""
    _cache.clear()


def concept_status(codes, tx_server: str, edition: str) -> Dict[str, str]:
    """Classify SNOMED codes as active/inactive/absent in one SNOMED CT-AU edition.

    Batches the codes through ValueSet/$expand as an explicit ``compose.include.
    concept`` list with ``activeOnly=false``, reading the ``inactive`` flag off
    each returned concept.

    An ECL cannot answer this. Inactive concepts carry no relationships, so
    ``<<X`` never reaches them and an ECL expansion looks fully active no matter
    what activeOnly is set to. Listing the codes explicitly sidesteps the
    transitive closure and asks about each concept directly.

    Returns {code: "active" | "inactive" | "absent"}, where absent means the
    server did not echo the code back at all -- not in this edition in any state.
    """
    version = f"{AU_MODULE}/version/{edition}"
    ordered = sorted(codes)
    status: Dict[str, str] = {}

    for start in range(0, len(ordered), CONCEPT_STATUS_BATCH):
        batch = ordered[start:start + CONCEPT_STATUS_BATCH]
        body = {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "valueSet", "resource": {
                    "resourceType": "ValueSet",
                    "compose": {"include": [{
                        "system": "http://snomed.info/sct",
                        "version": version,
                        "concept": [{"code": code} for code in batch],
                    }]},
                }},
                {"name": "activeOnly", "valueBoolean": False},
                {"name": "count", "valueInteger": CONCEPT_STATUS_BATCH * 5},
                {"name": "includeDesignations", "valueBoolean": False},
            ],
        }
        resp = requests.post(
            f"{tx_server}/ValueSet/$expand",
            json=body,
            headers={
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json",
            },
            timeout=180,
        )
        resp.raise_for_status()

        returned = set()
        for entry in resp.json().get("expansion", {}).get("contains", []):
            code = entry.get("code")
            if code is None:
                continue
            status[code] = "inactive" if entry.get("inactive") else "active"
            returned.add(code)
        for code in batch:
            if code not in returned:
                status[code] = "absent"

    return status


def _load_doomed_cache() -> Dict[str, List[str]]:
    global _doomed_cache
    if _doomed_cache is None:
        if _DOOMED_CACHE_PATH.exists():
            try:
                with open(_DOOMED_CACHE_PATH, encoding="utf-8") as f:
                    _doomed_cache = json.load(f)
            except (OSError, ValueError):
                _doomed_cache = {}
        else:
            _doomed_cache = {}
    return _doomed_cache


def _save_doomed_cache() -> None:
    with open(_DOOMED_CACHE_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(_doomed_cache, f, indent=0, sort_keys=True)


def doomed_codes(
    ecl: str,
    tx_server: str = DEFAULT_TX_SERVER,
    edition: Optional[str] = None,
    reference_edition: Optional[str] = None,
) -> Set[str]:
    """Return the subset of *ecl*'s expansion at *edition* that is inactive at
    *reference_edition*.

    This is the "will-be-inactive" pool biasing draws toward -- a code that was
    correct when recorded and has since been retired. Cached to disk keyed on
    (ecl, tx_server, edition, reference_edition), mirroring expand_ecl's cache
    key; the result does not depend on inactive_rate, so every subsequent
    tuning run reuses it.
    """
    if not reference_edition:
        return set()

    cache = _load_doomed_cache()
    key = f"{edition}::{reference_edition}::{tx_server}::{ecl}"
    if key in cache:
        return set(cache[key])

    concepts = expand_ecl(ecl, tx_server=tx_server, edition=edition)
    codes = [c["code"] for c in concepts]

    doomed: Set[str] = set()
    if codes:
        status = concept_status(codes, tx_server, reference_edition)
        doomed = {c for c in codes if status.get(c) == "inactive"}
        if not doomed:
            logger.warning(
                "Doomed pool empty for ECL '%s' at edition %s against reference %s",
                ecl, edition, reference_edition,
            )

    cache[key] = sorted(doomed)
    _save_doomed_cache()
    return doomed


# Per-code selection boost. Codes listed here are weighted *_boost_factor*
# times more heavily than their peers whenever a draw includes them, letting a
# named set of concepts (e.g. the unrecoverable in-scope ones reported by
# data-golf/analyse.py) appear more often without changing the ECLs.
_boost_codes: Set[str] = set()
_boost_factor: float = 1.0


def set_code_boost(codes, factor: float = 1.0) -> None:
    """Set the codes to over-sample and by what multiple.

    A factor of 1.0 (or an empty code set) restores unweighted selection.
    """
    global _boost_codes, _boost_factor
    _boost_codes = set(codes or ())
    _boost_factor = float(factor)


def _weighted_choice(concepts: List[Dict[str, str]]) -> Dict[str, str]:
    """random.choice over *concepts*, weighting boosted codes by _boost_factor."""
    if not _boost_codes or _boost_factor == 1.0:
        return random.choice(concepts)
    weights = [
        _boost_factor if c["code"] in _boost_codes else 1.0 for c in concepts
    ]
    return random.choices(concepts, weights=weights, k=1)[0]


def choose_concept(
    concepts: List[Dict[str, str]],
    doomed: Set[str],
    inactive_rate: float,
) -> Dict[str, str]:
    """Pick a concept from *concepts*, biased toward the doomed pool.

    With probability *inactive_rate* returns a member of the doomed subset,
    otherwise a member of the remainder. Falls back to a draw over all of
    *concepts* when either partition is empty, so a criterion with no
    retirements (or none at all in scope) still yields a code. Within whichever
    pool is drawn from, codes registered via set_code_boost() are weighted up.
    """
    pool = [c for c in concepts if c["code"] in doomed]
    remainder = [c for c in concepts if c["code"] not in doomed]

    if not pool or not remainder:
        return _weighted_choice(concepts)

    if random.random() < inactive_rate:
        return _weighted_choice(pool)
    return _weighted_choice(remainder)
