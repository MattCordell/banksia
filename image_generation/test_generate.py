"""Quick test script: generate 5 images for each prompt type (15 total).

Usage:
    python -m image_generation.test_generate
"""

from common.types import PatientContext
from identity.generator import assign_identity
from image_generation.generator import (
    generate_profile_image,
    generate_radiology_image,
    generate_microscopy_image,
)

# --- 5 profile images with varied patients ---
PROFILE_PATIENTS = [
    PatientContext(sex="female", age=7),
    PatientContext(sex="male", age=25),
    PatientContext(sex="female", age=42),
    PatientContext(sex="male", age=68),
    PatientContext(sex="female", age=85),
]

# --- 5 conditions for radiology and microscopy ---
CONDITIONS = [
    "Pneumonia",
    "Chronic Kidney Disease",
    "Osteoarthritis",
    "Hypothyroidism",
    "Iron Deficiency Anaemia",
]


def main():
    print("=== Generating 5 profile images ===")
    for i, ctx in enumerate(PROFILE_PATIENTS, 1):
        assign_identity(ctx)
        print(f"  [{i}/5] {ctx.given_name} {ctx.family_name}, age {ctx.age}, {ctx.sex}...")
        path = generate_profile_image(ctx)
        print(f"         -> {path}")

    print("\n=== Generating 5 radiology images ===")
    for i, condition in enumerate(CONDITIONS, 1):
        print(f"  [{i}/5] {condition}...")
        path = generate_radiology_image(condition)
        print(f"         -> {path}")

    print("\n=== Generating 5 microscopy images ===")
    for i, condition in enumerate(CONDITIONS, 1):
        print(f"  [{i}/5] {condition}...")
        path = generate_microscopy_image(condition)
        print(f"         -> {path}")

    print("\nDone! Check image_generation/output/ for results.")


if __name__ == "__main__":
    main()
