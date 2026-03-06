"""
banksia: Synthetic patient data generator.

Usage:
    python generate.py --mode single --condition "Hypothyroidism" --sex female --age 54
    python generate.py --mode cohort --n 200 --output cohort.csv
    python generate.py --mode population --n 200 --output population.csv
"""

import argparse
import random
from datetime import date

import numpy as np
import pandas as pd

from common.types import PatientContext
from conditions.generator import assign_condition, resolve_snomed_code
from identity.generator import assign_identity
from laboratory.generator import generate_lab_results, _resolve_profiles
from population.generator import generate_contexts
from medicines.generator import generate_medicines
from formatters.csv_writer import contexts_to_dataframe, write_csv


def _assign_snomed(ctx, tx_server, snomed_edition, no_snomed):
    """Resolve a SNOMED code for the context's condition and populate it."""
    if no_snomed:
        return
    result = resolve_snomed_code(
        ctx.condition,
        sex=ctx.sex,
        age=ctx.age,
        tx_server=tx_server,
        edition=snomed_edition,
    )
    if result:
        ctx.snomed_code = result["code"]
        ctx.snomed_display = result["display"]


def generate_single(
    condition: str,
    sex: str = "female",
    age: int = 50,
    lifestyle: list = None,
    rng_seed: int = None,
    tx_server: str = None,
    snomed_edition: str = None,
    no_snomed: bool = False,
    med_ecl_template: str = None,
    episode_date: date = None,
):
    """Generate a single patient with demographics + lab results."""
    ctx = PatientContext(
        sex=sex,
        age=age,
        lifestyle=lifestyle or [],
        condition=condition,
    )
    assign_identity(ctx, episode_date=episode_date)
    _assign_snomed(ctx, tx_server, snomed_edition, no_snomed)
    ctx.medicines = generate_medicines(
        ctx, tx_server=tx_server, edition=snomed_edition, no_snomed=no_snomed,
        ecl_template=med_ecl_template,
    )
    profiles = _resolve_profiles()
    lab = generate_lab_results(ctx, profiles=profiles, rng_seed=rng_seed)
    return ctx, lab


def generate_cohort(
    n: int,
    abs_data_path: str = None,
    rng_seed: int = None,
    missing_panel_prob: float = 0.12,
    output_path: str = None,
    tx_server: str = None,
    snomed_edition: str = None,
    no_snomed: bool = False,
    med_ecl_template: str = None,
    episode_date: date = None,
):
    """Generate a cohort: population demographics + lab results for each."""
    if rng_seed is not None:
        np.random.seed(rng_seed)
        random.seed(rng_seed)

    # 1. Generate population contexts
    contexts = generate_contexts(n, file_path=abs_data_path)

    # 2. Assign identity and conditions
    profiles = _resolve_profiles()
    for ctx in contexts:
        assign_identity(ctx, episode_date=episode_date)
        ctx.condition = assign_condition(ctx)
        _assign_snomed(ctx, tx_server, snomed_edition, no_snomed)
        ctx.medicines = generate_medicines(
            ctx, tx_server=tx_server, edition=snomed_edition, no_snomed=no_snomed,
            ecl_template=med_ecl_template,
        )

    # 3. Generate lab results for each context
    lab_results = []
    for i, ctx in enumerate(contexts):
        seed = (rng_seed + i) if rng_seed is not None else None
        lab = generate_lab_results(
            ctx,
            profiles=profiles,
            missing_panel_prob=missing_panel_prob,
            rng_seed=seed,
        )
        lab_results.append(lab)

    # 4. Format and output
    df = contexts_to_dataframe(contexts, lab_results)
    if output_path:
        write_csv(df, output_path)
        print(f"Cohort of {n} patients saved to {output_path}")
    else:
        print(df.to_string())

    return df


def main():
    parser = argparse.ArgumentParser(description="banksia synthetic patient generator")
    parser.add_argument("--mode", choices=["single", "cohort", "population"],
                        default="cohort", help="Generation mode")
    parser.add_argument("--n", type=int, default=200, help="Number of patients (cohort/population)")
    parser.add_argument("--condition", type=str, default=None, help="Condition name (single mode)")
    parser.add_argument("--sex", type=str, default="female", help="Sex (single mode)")
    parser.add_argument("--age", type=int, default=50, help="Age (single mode)")
    parser.add_argument("--lifestyle", type=str, nargs="*", default=[], help="Lifestyle factors")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output CSV path")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--missing-panel-prob", type=float, default=0.12)
    parser.add_argument("--abs-data", type=str, default=None, help="Path to ABS Excel file")
    parser.add_argument("--tx-server", type=str, default=None,
                        help="FHIR terminology server URL (default: Ontoserver)")
    parser.add_argument("--snomed-edition", type=str, default=None,
                        help="SNOMED CT edition version (e.g. 20250131)")
    parser.add_argument("--no-snomed", action="store_true",
                        help="Skip SNOMED CT code resolution (offline mode)")
    parser.add_argument("--med-ecl-template", type=str, default=None,
                        help="Medicine ECL template: a named key from "
                             "medicines/ecl_templates.json (e.g. 'amt-tpuu', 'amt-mpuu', "
                             "'product') or a raw ECL string with {ingredients} placeholder")
    parser.add_argument("--episode-date", type=str, default=None,
                        help="Episode date for birth date calculation (YYYY-MM-DD). "
                             "Defaults to today.")

    args = parser.parse_args()
    episode_date = date.fromisoformat(args.episode_date) if args.episode_date else None

    if args.mode == "single":
        # Build a temporary context for condition assignment if needed
        if args.condition:
            condition = args.condition
        else:
            tmp_ctx = PatientContext(
                sex=args.sex, age=args.age, lifestyle=args.lifestyle
            )
            condition = assign_condition(tmp_ctx)

        ctx, lab = generate_single(
            condition=condition,
            sex=args.sex,
            age=args.age,
            lifestyle=args.lifestyle,
            rng_seed=args.seed,
            tx_server=args.tx_server,
            snomed_edition=args.snomed_edition,
            no_snomed=args.no_snomed,
            med_ecl_template=args.med_ecl_template,
            episode_date=episode_date,
        )
        df = contexts_to_dataframe([ctx], [lab])
        if args.output:
            write_csv(df, args.output)
            print(f"Single patient saved to {args.output}")
        else:
            print(df.T)

    elif args.mode == "cohort":
        generate_cohort(
            n=args.n,
            abs_data_path=args.abs_data,
            rng_seed=args.seed,
            missing_panel_prob=args.missing_panel_prob,
            output_path=args.output,
            tx_server=args.tx_server,
            snomed_edition=args.snomed_edition,
            no_snomed=args.no_snomed,
            med_ecl_template=args.med_ecl_template,
            episode_date=episode_date,
        )

    elif args.mode == "population":
        contexts = generate_contexts(args.n, file_path=args.abs_data)
        for ctx in contexts:
            assign_identity(ctx, episode_date=episode_date)
            ctx.condition = assign_condition(ctx)
            _assign_snomed(ctx, args.tx_server, args.snomed_edition, args.no_snomed)
            ctx.medicines = generate_medicines(
                ctx, tx_server=args.tx_server, edition=args.snomed_edition,
                no_snomed=args.no_snomed, ecl_template=args.med_ecl_template,
            )
        df = contexts_to_dataframe(contexts)
        if args.output:
            write_csv(df, args.output)
            print(f"Population of {args.n} saved to {args.output}")
        else:
            print(df.to_string())


if __name__ == "__main__":
    main()
