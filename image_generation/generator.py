"""Image generation using Runware API.

Generates profile avatars, radiology images, and microscopy images for
synthetic patients. Uses the Runware REST API with per-type model selection.

This module is NOT part of the standard pipeline — it is intended for
on-demand use when producing FHIR-ready datasets with image attachments.
"""

import base64
import io
import json
import os
import random
import uuid
from pathlib import Path
from typing import Optional

import requests
from PIL import Image

from common.types import PatientContext

_MODULE_DIR = Path(__file__).parent
_PROJECT_ROOT = _MODULE_DIR.parent
_PROMPTS = json.loads((_MODULE_DIR / "prompts.json").read_text())

_RUNWARE_URL = "https://api.runware.ai/v1"


def _load_dotenv() -> None:
    """Load variables from .env file in the project root if it exists."""
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def _get_api_key() -> str:
    """Return the Runware API key, loading .env if needed."""
    _load_dotenv()
    api_key = os.environ.get("RUNWARE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "RUNWARE_API_KEY environment variable is not set. "
            "Sign up at https://my.runware.ai/signup to get an API key."
        )
    return api_key


# ---------------------------------------------------------------------------
# Core image generation
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3


def _generate_image(
    prompt: str,
    model: str,
    width: int = 1024,
    height: int = 1024,
    negative_prompt: str = "",
) -> bytes:
    """Generate an image from a text prompt and return raw image bytes.

    Args:
        prompt: The text prompt describing the image.
        model: Runware model AIR identifier.
        width: Output width in pixels.
        height: Output height in pixels.
        negative_prompt: Things to avoid in the generated image.

    Returns:
        Raw image bytes (JPEG).
    """
    api_key = _get_api_key()

    payload = [{
        "taskType": "imageInference",
        "taskUUID": str(uuid.uuid4()),
        "positivePrompt": prompt,
        "model": model,
        "width": width,
        "height": height,
        "numberResults": 1,
        "outputType": "base64Data",
        "outputFormat": "JPG",
        "outputQuality": 85,
        "includeCost": True,
    }]
    if negative_prompt:
        payload[0]["negativePrompt"] = negative_prompt

    for attempt in range(_MAX_RETRIES):
        resp = requests.post(
            _RUNWARE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )

        if resp.status_code == 429 and attempt < _MAX_RETRIES - 1:
            wait = 10 * (attempt + 1)
            print(f"[image_generation] 429 rate limited, retrying in {wait}s (attempt {attempt + 1})...")
            import time
            time.sleep(wait)
            continue

        resp.raise_for_status()
        data = resp.json()["data"][0]

        cost = data.get("cost")
        if cost is not None:
            print(f"[image_generation] Cost: ${cost}")

        return base64.b64decode(data["imageBase64Data"])

    raise RuntimeError("Max retries exceeded for image generation")


def _save_image(image_bytes: bytes, output_path: Path, target_size: tuple[int, int]) -> Path:
    """Resize raw image bytes to the target size and save as JPEG.

    Args:
        image_bytes: Raw image bytes from the API.
        output_path: Destination file path.
        target_size: (width, height) tuple for resizing.

    Returns:
        The output path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(io.BytesIO(image_bytes))
    img = img.resize(target_size, Image.LANCZOS)
    img = img.convert("RGB")
    img.save(output_path, format="JPEG", quality=85)
    return output_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_profile_image(
    ctx: PatientContext,
    output_dir: str | Path = None,
) -> Path:
    """Generate a profile/avatar image for a patient.

    Args:
        ctx: PatientContext with given_name, family_name, age, sex populated.
        output_dir: Directory to save the image.

    Returns:
        Path to the saved JPEG image.
    """
    if output_dir is None:
        output_dir = _MODULE_DIR / "output" / "profiles"

    cfg = _PROMPTS["profile"]

    family_name = ctx.family_name or "Person"
    animal_hints = cfg.get("animal_hints", {})
    animal_hint = animal_hints.get(family_name, family_name)

    prompt = cfg["template"].format(
        given_name=ctx.given_name or "Unknown",
        family_name=family_name,
        animal_hint=animal_hint,
        age=ctx.age,
        sex=ctx.sex,
    )

    image_bytes = _generate_image(
        prompt,
        model=cfg["model"],
        width=cfg["width"],
        height=cfg["height"],
        negative_prompt=cfg.get("negative_prompt", ""),
    )

    filename = f"{ctx.given_name}_{ctx.family_name}_{ctx.age}.jpg".replace(" ", "_")
    output_path = Path(output_dir) / filename

    return _save_image(image_bytes, output_path, target_size=(256, 256))


def generate_radiology_image(
    condition: str,
    output_dir: str | Path = None,
    modality: Optional[str] = None,
    body_region: Optional[str] = None,
) -> Path:
    """Generate a radiology image for a given condition.

    Args:
        condition: The clinical condition name (e.g. "Pneumonia").
        output_dir: Directory to save the image.
        modality: Imaging modality override (e.g. "chest X-ray").
        body_region: Body region override (e.g. "chest and lungs").

    Returns:
        Path to the saved JPEG image.
    """
    if output_dir is None:
        output_dir = _MODULE_DIR / "output" / "radiology"

    cfg = _PROMPTS["radiology"]

    if modality is None:
        modality = cfg["modalities"].get(condition, cfg["modalities"]["default"])
    if body_region is None:
        body_region = cfg["body_regions"].get(condition, cfg["body_regions"]["default"])

    prompt = cfg["template"].format(
        modality=modality,
        body_region=body_region,
        condition=condition,
    )

    image_bytes = _generate_image(
        prompt,
        model=cfg["model"],
        width=cfg["width"],
        height=cfg["height"],
        negative_prompt=cfg.get("negative_prompt", ""),
    )

    safe_condition = condition.replace(" ", "_")
    safe_modality = modality.replace(" ", "_")
    filename = f"{safe_condition}_{safe_modality}.jpg"
    output_path = Path(output_dir) / filename

    return _save_image(image_bytes, output_path, target_size=(1024, 1024))


def generate_microscopy_image(
    condition: str,
    output_dir: str | Path = None,
    specimen_type: Optional[str] = None,
    stain: Optional[str] = None,
) -> Path:
    """Generate a microscopy image for a given condition.

    Args:
        condition: The clinical condition name.
        output_dir: Directory to save the image.
        specimen_type: Specimen type override.
        stain: Staining method override.

    Returns:
        Path to the saved JPEG image.
    """
    if output_dir is None:
        output_dir = _MODULE_DIR / "output" / "microscopy"

    cfg = _PROMPTS["microscopy"]

    if specimen_type is None:
        specimen_type = cfg["specimen_types"].get(condition, cfg["specimen_types"]["default"])
    if stain is None:
        stain = cfg["stains"].get(condition, cfg["stains"]["default"])

    prompt = cfg["template"].format(
        specimen_type=specimen_type,
        stain=stain,
        condition=condition,
    )

    image_bytes = _generate_image(
        prompt,
        model=cfg["model"],
        width=cfg["width"],
        height=cfg["height"],
        negative_prompt=cfg.get("negative_prompt", ""),
    )

    safe_condition = condition.replace(" ", "_")
    safe_specimen = specimen_type.replace(" ", "_")
    filename = f"{safe_condition}_{safe_specimen}.jpg"
    output_path = Path(output_dir) / filename

    return _save_image(image_bytes, output_path, target_size=(1024, 1024))
