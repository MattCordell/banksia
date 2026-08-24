"""One-off script to generate and POST a cohort of FHIR Patients."""

import json
import random
import sys
from datetime import date

import numpy as np

from common.types import PatientContext
from conditions.generator import assign_condition
from identity.generator import assign_identity
from population.generator import generate_contexts
from formatters.fhir_writer import build_fhir_patient, post_to_fhir_server

FHIR_SERVER = "https://server.callistemon.site/fhir"
N = 100

print(f"Generating {N} patient contexts...")
contexts = generate_contexts(N)

for ctx in contexts:
    assign_identity(ctx)
    ctx.condition = assign_condition(ctx)

results = []
for i, ctx in enumerate(contexts):
    print(f"\n[{i+1}/{N}] {ctx.given_name} {ctx.family_name} ({ctx.sex}, age {ctx.age}, {ctx.state})...")
    try:
        resource = build_fhir_patient(ctx, include_photo=True)
        resp = post_to_fhir_server(resource, base_url=FHIR_SERVER)
        results.append({
            "id": resp["id"],
            "given_name": ctx.given_name,
            "family_name": ctx.family_name,
            "sex": ctx.sex,
            "age": ctx.age,
            "birth_date": ctx.birth_date.isoformat() if ctx.birth_date else "",
            "state": ctx.state,
            "city": ctx.city,
            "condition": ctx.condition,
            "has_photo": "photo" in resource,
        })
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({
            "id": "FAILED",
            "given_name": ctx.given_name,
            "family_name": ctx.family_name,
            "sex": ctx.sex,
            "age": ctx.age,
            "birth_date": ctx.birth_date.isoformat() if ctx.birth_date else "",
            "state": ctx.state,
            "city": ctx.city,
            "condition": ctx.condition,
            "has_photo": False,
        })

# Save results
with open("cohort_results.json", "w") as f:
    json.dump(results, f, indent=2)

# Generate markdown table
lines = ["| # | Server ID | Name | Sex | Age | Birth Date | State | City | Condition | Photo |",
         "|---|-----------|------|-----|-----|------------|-------|------|-----------|-------|"]
for i, r in enumerate(results):
    photo = "Yes" if r["has_photo"] else "No"
    lines.append(f"| {i+1} | {r['id']} | {r['given_name']} {r['family_name']} | {r['sex']} | {r['age']} | {r['birth_date']} | {r['state']} | {r['city']} | {r['condition']} | {photo} |")

md = "\n".join(lines)
with open("cohort_patients.md", "w") as f:
    f.write(f"# Banksia FHIR Patients on {FHIR_SERVER}\n\n")
    f.write(f"Generated: {date.today().isoformat()}\n\n")
    f.write(f"Total: {len([r for r in results if r['id'] != 'FAILED'])}/{N} created successfully\n\n")
    f.write(md + "\n")

print(f"\n\nDone! {len([r for r in results if r['id'] != 'FAILED'])}/{N} patients created.")
print("Results saved to cohort_results.json and cohort_patients.md")
