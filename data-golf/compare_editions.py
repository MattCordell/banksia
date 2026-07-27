"""
Compare ECL expansion sizes across SNOMED CT-AU editions.

Expands every criterion ECL used by analyse.py against each edition in PERIODS
and tabulates the member counts, so unstable expressions can be spotted before
a production dataset is generated. Writes edition_comparison.md.

An expansion that swings sharply between editions makes the corresponding
question edition-dependent for reasons unrelated to the patient. Two causes
are worth distinguishing:

* Genuine terminology drift -- concepts reclassified, added or inactivated
  between releases. Real, and arguably what an edition-aware dataset should
  reflect.
* A brittle ECL -- typically a navigation expression that silently resolves to
  almost nothing in older editions. This is a bug, and the fix is usually to
  match against a stable substance grouper instead.

Comparability
-------------
Every medicine expansion has a structural discontinuity at the 2025 edition:
|Medicinal product| (373873005) grows from 25,306 members to 166,511, a 6.6x
jump as AMT trade products land in the hierarchy. Non-oral criteria also swap
product template there ("product" -> "amt-tpuu", mirroring the generator). So
medicine counts either side of 2025 are not comparable no matter which
template is used -- all medicine rows are scored within each era separately
and the boundary step is reported as context rather than flagged.

Condition ECLs match against Clinical_Note_Code with no product template
involved, so they are scored across all six editions.

Usage:
    python data-golf/compare_editions.py [--threshold 20] [--tx-server URL]
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
for path in (PROJECT_ROOT, SCRIPT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from analyse import (  # noqa: E402
    CONDITION_ECLS,
    DEFAULT_TX_SERVER,
    MEDICINE_ECLS,
    PERIODS,
    ecl_code_set,
    product_ecl_template_for_edition,
    resolve_ecl_template,
)

EDITIONS = [period["edition"] for period in PERIODS]
AMT_ERA_START = "20250131"

# Editions grouped by the product template they use, for medicine ECLs that
# switch model at 2025. Must stay in sync with product_ecl_template_for_edition.
PRODUCT_ERA = [e for e in EDITIONS if e < AMT_ERA_START]
AMT_ERA = [e for e in EDITIONS if e >= AMT_ERA_START]


# |Medicinal product| members per edition. The whole hierarchy expands 6.6x at
# 2025 as AMT trade products arrive, so an individual criterion that shrinks
# across that boundary is behaving anomalously and is worth a look.
HIERARCHY_BASELINE = {
    "20210131": 22503,
    "20220131": 23215,
    "20230131": 24895,
    "20240131": 25306,
    "20250131": 166511,
    "20260131": 172840,
}


def load_cache(path):
    """Load the on-disk expansion cache, or an empty dict if absent/unreadable."""
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def save_cache(path, cache):
    if not path:
        return
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(cache, handle, indent=0, sort_keys=True)


def cached_count(ecl, tx_server, edition, cache):
    """Return the expansion size, consulting the on-disk cache first.

    Cached values are counts, not code sets -- this script only ever needs the
    size, and storing full expansions would run to hundreds of megabytes.
    Returns (count_or_None, was_cached).
    """
    key = f"{edition}::{ecl}"
    if key in cache:
        return cache[key], True
    try:
        count = len(ecl_code_set(ecl, tx_server, edition=edition))
    except Exception as exc:  # noqa: BLE001 - report, do not abort the sweep
        return exc, False
    cache[key] = count
    return count, False


def spread_pct(counts):
    """Return (max - min) / max as a percentage over a list of counts.

    100.0 when the largest value is positive and the smallest is zero -- an
    expansion that empties out entirely is the most severe swing there is.
    Returns None when there is nothing to compare.
    """
    values = [c for c in counts if c is not None]
    if len(values) < 2:
        return None
    high = max(values)
    if high == 0:
        return 0.0
    return (high - min(values)) / high * 100.0


def step_changes(counts, editions):
    """Return [(from_edition, to_edition, pct_change)] for consecutive editions.

    Percentage is relative to the earlier count. A step from zero is reported
    as None, since the relative change is undefined.
    """
    steps = []
    for i in range(1, len(counts)):
        before, after = counts[i - 1], counts[i]
        if before is None or after is None:
            steps.append((editions[i - 1], editions[i], None))
        elif before == 0:
            steps.append((editions[i - 1], editions[i], None))
        else:
            steps.append((editions[i - 1], editions[i], (after - before) / before * 100.0))
    return steps


def expand_all(tx_server, cache, verbose=True):
    """Expand every criterion ECL against every edition.

    Returns a list of row dicts with keys: group, key, ecl, template, counts
    (edition -> int or None on failure), and error (first failure message).
    """
    rows = []
    total = (len(CONDITION_ECLS) + len(MEDICINE_ECLS)) * len(EDITIONS)
    done = 0

    def resolve(label, ecl, edition):
        """Expand one ECL, record progress, and return (count_or_None, error_or_None)."""
        nonlocal done
        done += 1
        result, was_cached = cached_count(ecl, tx_server, edition, cache)
        if isinstance(result, Exception):
            if verbose:
                print(f"  [{done:3d}/{total}] {label:28s} {edition}  FAILED")
            return None, f"{type(result).__name__}: {result}"
        if verbose:
            suffix = " (cached)" if was_cached else ""
            print(f"  [{done:3d}/{total}] {label:28s} {edition}  {result}{suffix}")
        return result, None

    for key, ecl in CONDITION_ECLS.items():
        counts, error = {}, None
        for edition in EDITIONS:
            counts[edition], failure = resolve(key, ecl, edition)
            error = error or failure
        rows.append({
            "group": "condition",
            "key": key,
            "ecl": ecl,
            "template": "n/a (matched against Clinical_Note_Code)",
            "counts": counts,
            "error": error,
        })

    for key, spec in MEDICINE_ECLS.items():
        counts, error = {}, None
        for edition in EDITIONS:
            template_key = (
                "product-oral" if spec.oral_only else product_ecl_template_for_edition(edition)
            )
            template = resolve_ecl_template(template_key)
            expanded = template.format(ingredients=spec.ingredients)
            counts[edition], failure = resolve(key, expanded, edition)
            error = error or failure
        rows.append({
            "group": "medicine",
            "key": key,
            "ecl": spec.ingredients,
            "template": "product-oral" if spec.oral_only else "product -> amt-tpuu at 2025",
            "counts": counts,
            "error": error,
        })

    return rows


def score(row):
    """Attach comparability grouping and spread scores to a row.

    Adds:
        eras      list of (label, editions) that are directly comparable
        spreads   {era_label: spread percentage or None}
        worst     the largest spread across eras, or None
        boundary  pct change across the template switch, for split rows only
    """
    counts = row["counts"]
    # Every medicine expansion straddles the 2025 product-hierarchy jump, not
    # just the ones that also change template, so all of them are scored per era.
    split = row["group"] == "medicine"

    if split:
        eras = [("2021-2024", PRODUCT_ERA), ("2025-2026", AMT_ERA)]
    else:
        eras = [("all editions", EDITIONS)]

    spreads = {}
    for label, editions in eras:
        spreads[label] = spread_pct([counts[e] for e in editions])

    measured = [v for v in spreads.values() if v is not None]
    row["eras"] = eras
    row["spreads"] = spreads
    row["worst"] = max(measured) if measured else None

    # The 2025 step, and whether it runs against the hierarchy's own growth.
    # |Medicinal product| expands 6.6x there, so a criterion that shrinks is
    # suspicious: usually the ECL fails to reach the new product model rather
    # than the medicine genuinely disappearing from the market.
    row["boundary"] = None
    row["boundary_anomaly"] = False
    if split:
        before, after = counts[PRODUCT_ERA[-1]], counts[AMT_ERA[0]]
        if before not in (None, 0) and after is not None:
            row["boundary"] = (after - before) / before * 100.0
            row["boundary_anomaly"] = after < before

    return row


def fmt_pct(value):
    return "-" if value is None else f"{value:.0f}%"


def fmt_count(value):
    return "FAIL" if value is None else str(value)


def build_markdown(rows, threshold):
    lines = []
    lines.append("# ECL expansion comparison across SNOMED CT-AU editions")
    lines.append("")
    lines.append(
        f"Member counts for each criterion ECL, expanded against every edition in "
        f"`PERIODS`. Rows whose spread reaches **{threshold:.0f}%** are flagged."
    )
    lines.append("")
    lines.append(
        "Spread is `(max - min) / max` over the editions that are directly "
        "comparable. Condition ECLs are scored across all six editions. Medicine "
        "ECLs are scored within each era separately, because `|Medicinal product|` "
        "(373873005) grows 6.6x at the 2025 edition -- 25,306 members to 166,511 -- "
        "as AMT trade products land in the hierarchy. That boundary step is shown "
        "as context, not a defect."
    )
    lines.append("")
    lines.append(
        "| `<<373873005` baseline | "
        + " | ".join(EDITIONS)
        + " |\n|---|"
        + "|".join(["---"] * len(EDITIONS))
        + "|\n| members | 22503 | 23215 | 24895 | 25306 | 166511 | 172840 |"
    )
    lines.append("")

    flagged = [r for r in rows if r["worst"] is not None and r["worst"] >= threshold]
    anomalies = [r for r in rows if r.get("boundary_anomaly")]
    failed = [r for r in rows if r["error"]]

    lines.append(
        f"**{len(flagged)} of {len(rows)} expansions flagged** for within-era spread "
        f"at the {threshold:.0f}% threshold."
    )
    if anomalies:
        lines.append("")
        lines.append(
            f"**{len(anomalies)} medicine expansion(s) shrink across the 2025 boundary** "
            "while the product hierarchy grows 6.6x - see Boundary anomalies below."
        )
    if failed:
        lines.append("")
        lines.append(f"**{len(failed)} expansion(s) failed** - see Failures below.")
    lines.append("")

    for group, title in (("condition", "Condition ECLs"), ("medicine", "Medicine ECLs")):
        group_rows = [r for r in rows if r["group"] == group]
        if not group_rows:
            continue
        is_medicine = group == "medicine"
        lines.append(f"## {title}")
        lines.append("")
        header = ["Criterion"] + EDITIONS + ["Spread"]
        if is_medicine:
            header.append("2025 step")
        header.append("")
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for row in sorted(group_rows, key=lambda r: -(r["worst"] or 0)):
            cells = [f"`{row['key']}`"]
            cells += [fmt_count(row["counts"][e]) for e in EDITIONS]
            cells.append(fmt_pct(row["worst"]))
            if is_medicine:
                boundary = row["boundary"]
                cells.append("-" if boundary is None else f"{boundary:+.0f}%")
            notes = []
            if row["worst"] is not None and row["worst"] >= threshold:
                notes.append("FLAG")
            if row.get("boundary_anomaly"):
                notes.append("SHRINKS")
            cells.append(" ".join(notes))
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    if flagged:
        lines.append("## Flagged expansions")
        lines.append("")
        for row in sorted(flagged, key=lambda r: -r["worst"]):
            lines.append(f"### `{row['key']}` ({row['group']})")
            lines.append("")
            lines.append(f"- Ingredient/condition ECL: `{row['ecl']}`")
            lines.append(f"- Product template: {row['template']}")
            for label, editions in row["eras"]:
                counts = ", ".join(f"{e}={fmt_count(row['counts'][e])}" for e in editions)
                lines.append(f"- Spread {label}: **{fmt_pct(row['spreads'][label])}** ({counts})")
            if row["boundary"] is not None:
                lines.append(
                    f"- Template switch {PRODUCT_ERA[-1]} -> {AMT_ERA[0]}: "
                    f"{row['boundary']:+.0f}% (expected; different product model)"
                )
            steps = step_changes([row["counts"][e] for e in EDITIONS], EDITIONS)
            worst_step = max(
                (s for s in steps if s[2] is not None), key=lambda s: abs(s[2]), default=None
            )
            if worst_step:
                lines.append(
                    f"- Largest single step: {worst_step[0]} -> {worst_step[1]} "
                    f"{worst_step[2]:+.0f}%"
                )
            if row["error"]:
                lines.append(f"- Error: {row['error']}")
            lines.append("")

    if anomalies:
        lines.append("## Boundary anomalies")
        lines.append("")
        lines.append(
            "These medicine criteria have **fewer** matching products in the 2025 "
            "edition than in 2024, even though `|Medicinal product|` grew 6.6x. "
            "Sometimes that is real -- Australia may register fewer trade products "
            "for a substance than the international hierarchy lists -- but it is "
            "also the signature of an ECL that does not reach the AMT product model. "
            "Worth confirming against the actual products before publishing."
        )
        lines.append("")
        lines.append("| Criterion | 2024 | 2025 | Step | Template |")
        lines.append("|---|---|---|---|---|")
        for row in sorted(anomalies, key=lambda r: r["boundary"]):
            lines.append(
                f"| `{row['key']}` | {fmt_count(row['counts'][PRODUCT_ERA[-1]])} | "
                f"{fmt_count(row['counts'][AMT_ERA[0]])} | {row['boundary']:+.0f}% | "
                f"{row['template']} |"
            )
        lines.append("")

    if failed:
        lines.append("## Failures")
        lines.append("")
        for row in failed:
            lines.append(f"- `{row['key']}`: {row['error']}")
        lines.append("")

    lines.append("## ECL expressions")
    lines.append("")
    lines.append("| Criterion | Group | ECL |")
    lines.append("|---|---|---|")
    for row in rows:
        ecl = row["ecl"].replace("\n", " ").replace("|", "\\|")
        lines.append(f"| `{row['key']}` | {row['group']} | `{ecl}` |")
    lines.append("")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare ECL expansion sizes across SNOMED CT-AU editions."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="Flag expansions whose spread reaches this percentage (default: 20).",
    )
    parser.add_argument(
        "--tx-server",
        default=DEFAULT_TX_SERVER,
        help=f"FHIR terminology server base URL (default: {DEFAULT_TX_SERVER})",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(SCRIPT_DIR, "edition_comparison.md"),
        help="Path to the markdown report (default: data-golf/edition_comparison.md).",
    )
    parser.add_argument(
        "--cache",
        default=os.path.join(SCRIPT_DIR, ".ecl_expansion_cache.json"),
        help="On-disk cache of expansion sizes, so reruns do not re-hit Ontoserver. "
             "Pass an empty string to disable.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore cached counts and re-expand everything.",
    )
    args = parser.parse_args()

    cache = {} if args.refresh else load_cache(args.cache)
    if cache:
        print(f"Loaded {len(cache)} cached expansions from {args.cache}")

    print(
        f"Expanding {len(CONDITION_ECLS)} condition and {len(MEDICINE_ECLS)} medicine "
        f"ECLs across {len(EDITIONS)} editions..."
    )
    rows = [score(row) for row in expand_all(args.tx_server, cache)]
    save_cache(args.cache, cache)

    report = build_markdown(rows, args.threshold)
    with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(report)
    print(f"\nReport written to {args.output}")

    flagged = [r for r in rows if r["worst"] is not None and r["worst"] >= args.threshold]
    print(f"{len(flagged)} of {len(rows)} expansions flagged at {args.threshold:.0f}% spread:")
    for row in sorted(flagged, key=lambda r: -r["worst"]):
        print(f"  {row['worst']:5.0f}%  {row['group']:9s} {row['key']}")

    anomalies = [r for r in rows if r.get("boundary_anomaly")]
    if anomalies:
        print(f"{len(anomalies)} medicine expansion(s) shrink across the 2025 boundary:")
        for row in sorted(anomalies, key=lambda r: r["boundary"]):
            before = row["counts"][PRODUCT_ERA[-1]]
            after = row["counts"][AMT_ERA[0]]
            print(f"  {row['boundary']:+5.0f}%  {row['key']:20s} {before} -> {after}")


if __name__ == "__main__":
    main()
