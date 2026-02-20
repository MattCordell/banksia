"""
Expand SNOMED CT ECL expressions across multiple SNOMED CT-AU editions
using Ontoserver FHIR ValueSet/$expand, and produce a CSV summary of
code counts and differences between editions.
"""

import csv
import sys
import time
import urllib.parse
from datetime import datetime

import requests

ONTOSERVER_BASE = "https://r4.ontoserver.csiro.au/fhir"
AU_MODULE = "http://snomed.info/sct/32506021000036107"
EDITIONS = ["20260131", "20250131", "20240131", "20230131", "20220131", "20210131"]

DISEASES = [
    ("Healthy", "<<102499006 OR 160245001"),
    ("Alcoholic Liver Disease", "<<41309000"),
    ("Chronic Liver Disease / Cirrhosis", "<<328383001"),
    ("Type 2 Diabetes Mellitus", "<<44054006"),
    ("Essential Hypertension", "<<38341003"),
    ("Hyperlipidaemia", "<<55822004"),
    ("Ischaemic Heart Disease", "<<414545008"),
    ("Heart Failure (Chronic)", "<<48447003"),
    ("Chronic Kidney Disease (Stage 3-4)", "<<709044004"),
    ("COPD", "<<13645005"),
    ("Nonalcoholic Fatty Liver Disease (NAFLD)", "<<197321007 MINUS <<50325005"),
    ("Osteoarthritis", "<<396275006"),
    ("Rheumatoid Arthritis", "<<69896004"),
    ("Hypothyroidism", "<<40930008"),
    ("Hyperthyroidism", "<<34486009"),
    ("Iron Deficiency Anaemia", "<<87522002"),
]


def expand_ecl(ecl: str, edition: str) -> set[str] | None:
    """Expand an ECL expression against a specific SNOMED CT-AU edition.
    Returns a set of SNOMED CT codes, or None on failure."""
    vs_url = f"{AU_MODULE}/version/{edition}?fhir_vs=ecl/{ecl}"
    params = {
        "url": vs_url,
        "count": 10000,
    }
    codes = set()
    offset = 0

    while True:
        params["offset"] = offset
        try:
            resp = requests.get(
                f"{ONTOSERVER_BASE}/ValueSet/$expand",
                params=params,
                headers={"Accept": "application/fhir+json"},
                timeout=60,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  ERROR: {e}")
            return None

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


def main():
    output_file = "ecl_expansion_summary.csv"

    # Collect all results: {disease_name: {edition: set_of_codes}}
    results: dict[str, dict[str, set[str] | None]] = {}

    total = len(DISEASES) * len(EDITIONS)
    current = 0

    for disease_name, ecl in DISEASES:
        results[disease_name] = {}
        for edition in EDITIONS:
            current += 1
            print(f"[{current}/{total}] {disease_name} — edition {edition} ...", end=" ", flush=True)
            codes = expand_ecl(ecl, edition)
            if codes is None:
                print("FAIL — retrying in 10s ...", end=" ", flush=True)
                time.sleep(10)
                codes = expand_ecl(ecl, edition)
            results[disease_name][edition] = codes
            count = len(codes) if codes is not None else "FAIL (after retry)"
            print(f"{count} codes")
            time.sleep(0.3)

    # Build CSV
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header row
        header = ["Disease", "ECL"]
        for ed in EDITIONS:
            header.append(f"Count ({ed})")
        # Diff columns between consecutive editions (newer vs older)
        for i in range(len(EDITIONS) - 1):
            newer, older = EDITIONS[i], EDITIONS[i + 1]
            header.append(f"Added ({older} -> {newer})")
            header.append(f"Retired ({older} -> {newer})")
        writer.writerow(header)

        # Data rows
        for disease_name, ecl in DISEASES:
            row = [disease_name, ecl]

            # Counts per edition
            for ed in EDITIONS:
                codes = results[disease_name][ed]
                row.append(len(codes) if codes is not None else "ERROR")

            # Diffs between consecutive editions
            for i in range(len(EDITIONS) - 1):
                newer_codes = results[disease_name][EDITIONS[i]]
                older_codes = results[disease_name][EDITIONS[i + 1]]
                if newer_codes is not None and older_codes is not None:
                    added = newer_codes - older_codes
                    retired = older_codes - newer_codes
                    row.append(len(added))
                    row.append(len(retired))
                else:
                    row.append("ERROR")
                    row.append("ERROR")

            writer.writerow(row)

    print(f"\nSummary written to {output_file}")


if __name__ == "__main__":
    main()
