"""Generate test profile images for all animal family names.

Usage:
    python -m image_generation.test_animals
"""

import random
from common.types import PatientContext
from image_generation.generator import generate_profile_image
from identity.generator import GIVEN_NAMES

PROBLEMATIC_ANIMALS = [
    "Bettong", "Flying Fox", "Bilby", "Brush Turkey", "Frilled-Neck Lizard",
    "Tasmanian Tiger", "Bandicoot", "Galah", "Goanna", "Magpie",
    "Blue-tongued Lizard", "Cassowary", "Taipan",
]

IMAGES_PER_ANIMAL = 1


def main():
    animals = PROBLEMATIC_ANIMALS
    total = len(animals) * IMAGES_PER_ANIMAL
    print(f"=== Generating {IMAGES_PER_ANIMAL} images each for {len(animals)} animals ({total} total) ===")
    count = 0
    for animal in animals:
        for j in range(IMAGES_PER_ANIMAL):
            count += 1
            sex = random.choice(["male", "female"])
            age = random.randint(5, 85)
            given_name = random.choice(GIVEN_NAMES)
            ctx = PatientContext(sex=sex, age=age)
            ctx.given_name = given_name
            ctx.family_name = animal
            print(f"  [{count}/{total}] {given_name} {animal}, age {age}, {sex}...")
            path = generate_profile_image(ctx, output_dir="image_generation/output/test_animals")
            print(f"         -> {path}")

    print(f"\nDone! Generated {total} images in image_generation/output/test_animals/")


if __name__ == "__main__":
    main()
