"""Model comparison: generate 3 images per model for each prompt type.

Usage:
    python -m image_generation.test_models
"""

from common.types import PatientContext
from identity.generator import assign_identity
from image_generation.generator import _generate_image, _save_image
from pathlib import Path
import json

_MODULE_DIR = Path(__file__).parent
_PROMPTS = json.loads((_MODULE_DIR / "prompts.json").read_text())

# --- Profile models ---
PROFILE_MODELS = {
    "toonyou-beta6": "civitai:30240@125771",
    "flux1-schnell": "runware:100@1",
    "twinflow-z-image-turbo": "runware:z-image@turbo",
}

# --- Diagnostic models (radiology + microscopy) ---
DIAGNOSTIC_MODELS = {
    "flux1-schnell": "runware:100@1",
    "flux2-klein-4b": "runware:400@4",
    "z-image-turbo": "runware:z-image@turbo",
    "juggernaut-lightning": "rundiffusion:110@101",
    "twinflow-z-image-turbo": "runware:z-image@turbo",
}

# --- 3 varied patients for profile tests ---
PROFILE_PATIENTS = [
    PatientContext(sex="female", age=7),
    PatientContext(sex="male", age=42),
    PatientContext(sex="female", age=75),
]

# --- 3 conditions for radiology/microscopy tests ---
CONDITIONS = [
    "Pneumonia",
    "Chronic Kidney Disease",
    "Hypothyroidism",
]


def _build_profile_prompt(ctx: PatientContext) -> str:
    import random
    cfg = _PROMPTS["profile"]
    style = random.choice(cfg["styles"])
    return cfg["template"].format(
        given_name=ctx.given_name or "Unknown",
        family_name=ctx.family_name or "Person",
        age=ctx.age,
        sex=ctx.sex,
        style=style,
    )


def _build_radiology_prompt(condition: str) -> str:
    cfg = _PROMPTS["radiology"]
    modality = cfg["modalities"].get(condition, cfg["modalities"]["default"])
    body_region = cfg["body_regions"].get(condition, cfg["body_regions"]["default"])
    return cfg["template"].format(modality=modality, body_region=body_region, condition=condition)


def _build_microscopy_prompt(condition: str) -> str:
    cfg = _PROMPTS["microscopy"]
    specimen_type = cfg["specimen_types"].get(condition, cfg["specimen_types"]["default"])
    stain = cfg["stains"].get(condition, cfg["stains"]["default"])
    return cfg["template"].format(specimen_type=specimen_type, stain=stain, condition=condition)


def main():
    base_dir = Path("output/images/model_comparison")

    # --- Profiles ---
    for model_name, model_id in PROFILE_MODELS.items():
        print(f"\n=== Profile: {model_name} ({model_id}) ===")
        for i, ctx in enumerate(PROFILE_PATIENTS, 1):
            assign_identity(ctx)
            prompt = _build_profile_prompt(ctx)
            neg = _PROMPTS["profile"].get("negative_prompt", "")
            print(f"  [{i}/3] {ctx.given_name} {ctx.family_name}, age {ctx.age}, {ctx.sex}...")
            try:
                image_bytes = _generate_image(prompt, model=model_id, width=1024, height=1024,
                                              negative_prompt=neg)
                fname = f"{model_name}_{ctx.given_name}_{ctx.family_name}_{ctx.age}.jpg"
                out = _save_image(image_bytes, base_dir / "profiles" / model_name / fname,
                                  target_size=(256, 256))
                print(f"         -> {out}")
            except Exception as e:
                print(f"         !! FAILED: {e}")

    # --- Radiology ---
    # Deduplicate models (twinflow and z-image-turbo have same ID)
    seen_diag = set()
    for model_name, model_id in DIAGNOSTIC_MODELS.items():
        if model_id in seen_diag:
            print(f"\n=== Radiology: {model_name} — skipping (same ID as previous) ===")
            continue
        seen_diag.add(model_id)
        print(f"\n=== Radiology: {model_name} ({model_id}) ===")
        for i, condition in enumerate(CONDITIONS, 1):
            prompt = _build_radiology_prompt(condition)
            neg = _PROMPTS["radiology"].get("negative_prompt", "")
            print(f"  [{i}/3] {condition}...")
            try:
                image_bytes = _generate_image(prompt, model=model_id, width=1024, height=1024,
                                              negative_prompt=neg)
                safe = condition.replace(" ", "_")
                fname = f"{model_name}_{safe}.jpg"
                out = _save_image(image_bytes, base_dir / "radiology" / model_name / fname,
                                  target_size=(1024, 1024))
                print(f"         -> {out}")
            except Exception as e:
                print(f"         !! FAILED: {e}")

    # --- Microscopy ---
    seen_diag = set()
    for model_name, model_id in DIAGNOSTIC_MODELS.items():
        if model_id in seen_diag:
            print(f"\n=== Microscopy: {model_name} — skipping (same ID as previous) ===")
            continue
        seen_diag.add(model_id)
        print(f"\n=== Microscopy: {model_name} ({model_id}) ===")
        for i, condition in enumerate(CONDITIONS, 1):
            prompt = _build_microscopy_prompt(condition)
            neg = _PROMPTS["microscopy"].get("negative_prompt", "")
            print(f"  [{i}/3] {condition}...")
            try:
                image_bytes = _generate_image(prompt, model=model_id, width=1024, height=1024,
                                              negative_prompt=neg)
                safe = condition.replace(" ", "_")
                fname = f"{model_name}_{safe}.jpg"
                out = _save_image(image_bytes, base_dir / "microscopy" / model_name / fname,
                                  target_size=(1024, 1024))
                print(f"         -> {out}")
            except Exception as e:
                print(f"         !! FAILED: {e}")

    print("\nDone! Check output/images/model_comparison/ for results.")


if __name__ == "__main__":
    main()
