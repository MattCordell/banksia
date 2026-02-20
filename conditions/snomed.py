"""SNOMED CT ECL expansion via Ontoserver FHIR ValueSet/$expand."""

import logging
import time
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

DEFAULT_TX_SERVER = "https://tx.ontoserver.csiro.au/fhir"
AU_MODULE = "http://snomed.info/sct/32506021000036107"

# Module-level cache: (ecl, tx_server, edition) -> list of {code, display}
_cache: Dict[Tuple[str, str, Optional[str]], List[Dict[str, str]]] = {}


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
