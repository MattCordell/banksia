"""Generate one test profile image for each of the 13 problematic animals.

Usage:
    python -m image_generation.test_animals
"""

from common.types import PatientContext
from image_generation.generator import generate_profile_image

ANIMALS = [
    "Bettong",
    "Flying Fox",
    "Bilby",
    "Brush Turkey",
    "Frilled-Neck Lizard",
    "Tasmanian Tiger",
    "Bandicoot",
    "Galah",
    "Goanna",
    "Magpie",
    "Blue-tongued Lizard",
    "Cassowary",
    "Taipan",
]


def main():
    print(f"=== Generating test images for {len(ANIMALS)} problematic animals ===")
    for i, animal in enumerate(ANIMALS, 1):
        ctx = PatientContext(sex="female", age=35)
        ctx.given_name = "Test"
        ctx.family_name = animal
        print(f"  [{i}/{len(ANIMALS)}] {animal}...")
        path = generate_profile_image(ctx, output_dir="image_generation/output/test_animals")
        print(f"         -> {path}")

    print("\nDone! Check image_generation/output/test_animals/ for results.")


if __name__ == "__main__":
    main()
