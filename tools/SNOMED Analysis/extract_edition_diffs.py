"""
Extract detailed concept lists for dramatic changes between SNOMED CT-AU editions.
For each concept: SCTID, FSN, effectiveTime, active status, and inactivation reason
(if inactive, via 900000000000489007 | Concept inactivation indicator reference set).
"""

import csv
import time

import requests

ONTOSERVER_BASE = "https://r4.ontoserver.csiro.au/fhir"
AU_MODULE = "http://snomed.info/sct/32506021000036107"

# The three extracts to produce
EXTRACTS = [
    {
        "filename": "osteoarthritis_retired_2025_to_2026.csv",
        "label": "Osteoarthritis — retired between 20250131 and 20260131",
        "ecl": "<<396275006",
        "older_edition": "20250131",
        "newer_edition": "20260131",
        "diff_type": "retired",  # codes in older but not in newer
    },
    {
        "filename": "hyperthyroidism_retired_2021_to_2022.csv",
        "label": "Hyperthyroidism — retired between 20210131 and 20220131",
        "ecl": "<<34486009",
        "older_edition": "20210131",
        "newer_edition": "20220131",
        "diff_type": "retired",
    },
    {
        "filename": "rheumatoid_arthritis_added_2021_to_2022.csv",
        "label": "Rheumatoid Arthritis — added between 20210131 and 20220131",
        "ecl": "<<69896004",
        "older_edition": "20210131",
        "newer_edition": "20220131",
        "diff_type": "added",  # codes in newer but not in older
    },
]

INACTIVATION_REASONS = {
    "900000000000484002": "Ambiguous",
    "900000000000485001": "Erroneous",
    "900000000000486000": "Limited",
    "900000000000487009": "Moved elsewhere",
    "900000000000483008": "Outdated",
    "723277005": "Nonconformance to editorial policy",
    "900000000000482003": "Duplicate",
    "900000000000492006": "Pending move",
    "1186917008": "Classified as a subtype of a concept that has been inactivated",
    "1186924009": "Meaning of concept is too broad or too narrow",
}


def expand_ecl(ecl: str, edition: str) -> set[str]:
    """Expand an ECL expression and return the set of codes."""
    vs_url = f"{AU_MODULE}/version/{edition}?fhir_vs=ecl/{ecl}"
    params = {"url": vs_url, "count": 10000}
    codes = set()
    offset = 0

    while True:
        params["offset"] = offset
        resp = requests.get(
            f"{ONTOSERVER_BASE}/ValueSet/$expand",
            params=params,
            headers={"Accept": "application/fhir+json"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        expansion = data.get("expansion", {})
        contains = expansion.get("contains", [])
        if not contains:
            break
        for entry in contains:
            code = entry.get("code")
            if code:
                codes.add(code)
        total = expansion.get("total")
        if total is not None and len(codes) >= total:
            break
        offset += len(contains)
        time.sleep(0.2)

    return codes


def lookup_concept(code: str, edition: str) -> dict:
    """Look up a concept's display, effectiveTime, active status, and inactivation reason."""
    version = f"{AU_MODULE}/version/{edition}"
    params = [
        ("system", "http://snomed.info/sct"),
        ("code", code),
        ("version", version),
        ("property", "inactive"),
        ("property", "effectiveTime"),
    ]
    try:
        resp = requests.get(
            f"{ONTOSERVER_BASE}/CodeSystem/$lookup",
            params=params,
            headers={"Accept": "application/fhir+json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"    WARNING: lookup failed for {code}: {e}")
        return {"code": code, "fsn": "ERROR", "effectiveTime": "", "active": "", "inactivation_reason": ""}

    # Parse FHIR Parameters response
    params_list = data.get("parameter", [])

    fsn = ""
    inactive = False
    effective_time = ""
    for p in params_list:
        if p.get("name") == "display":
            fsn = p.get("valueString", "")
        elif p.get("name") == "property":
            parts = {part["name"]: part for part in p.get("part", [])}
            prop_code = parts.get("code", {}).get("valueCode", "")
            if prop_code == "inactive":
                inactive = parts.get("value", {}).get("valueBoolean", False)
            elif prop_code == "effectiveTime":
                effective_time = parts.get("value", {}).get("valueString", "")

    active = not inactive

    # If inactive, look up inactivation reason
    inactivation_reason = ""
    if inactive:
        inactivation_reason = get_inactivation_reason(code, edition)

    return {
        "code": code,
        "fsn": fsn,
        "effectiveTime": effective_time,
        "active": active,
        "inactivation_reason": inactivation_reason,
    }


def get_inactivation_reason(code: str, edition: str) -> str:
    """Query the concept inactivation indicator refset for a given concept."""
    # Use ECL to find the inactivation reason target via the attribute map
    # 900000000000489007 is the concept inactivation indicator refset
    # We query: ^900000000000489007 {{ M referencedComponentId = <code> }}
    ecl = f"^900000000000489007 {{{{ M referencedComponentId = \"{code}\" }}}}"
    vs_url = f"{AU_MODULE}/version/{edition}?fhir_vs=ecl/{ecl}"
    params = {"url": vs_url, "count": 10}

    try:
        resp = requests.get(
            f"{ONTOSERVER_BASE}/ValueSet/$expand",
            params=params,
            headers={"Accept": "application/fhir+json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        contains = data.get("expansion", {}).get("contains", [])
        if contains:
            reasons = []
            for entry in contains:
                reason_code = entry.get("code", "")
                reason_display = entry.get("display", INACTIVATION_REASONS.get(reason_code, "Unknown"))
                reasons.append(f"{reason_code} | {reason_display}")
            return "; ".join(reasons)
    except requests.RequestException:
        pass

    return ""


def process_extract(extract: dict):
    """Process a single extract: expand both editions, diff, look up details, write CSV."""
    label = extract["label"]
    ecl = extract["ecl"]
    older = extract["older_edition"]
    newer = extract["newer_edition"]
    diff_type = extract["diff_type"]
    filename = extract["filename"]

    print(f"\n{'='*60}")
    print(f"Processing: {label}")
    print(f"{'='*60}")

    print(f"  Expanding {ecl} against {older} ...", end=" ", flush=True)
    older_codes = expand_ecl(ecl, older)
    print(f"{len(older_codes)} codes")

    print(f"  Expanding {ecl} against {newer} ...", end=" ", flush=True)
    newer_codes = expand_ecl(ecl, newer)
    print(f"{len(newer_codes)} codes")

    if diff_type == "retired":
        diff_codes = older_codes - newer_codes
        # Look up in the NEWER edition so we can see inactivation status
        lookup_edition = newer
        print(f"  {len(diff_codes)} codes retired (in {older} but not in {newer})")
    else:
        diff_codes = newer_codes - older_codes
        lookup_edition = newer
        print(f"  {len(diff_codes)} codes added (in {newer} but not in {older})")

    print(f"  Looking up {len(diff_codes)} concepts in edition {lookup_edition} ...")
    rows = []
    for i, code in enumerate(sorted(diff_codes), 1):
        print(f"    [{i}/{len(diff_codes)}] {code}", flush=True)
        info = lookup_concept(code, lookup_edition)
        rows.append(info)
        time.sleep(0.2)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "fsn", "effectiveTime", "active", "inactivation_reason"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Written to {filename}")


def main():
    for extract in EXTRACTS:
        process_extract(extract)
    print("\nDone.")


if __name__ == "__main__":
    main()
