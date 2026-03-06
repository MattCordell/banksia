"""FHIR R4 Patient resource builder and server poster.

Builds Patient resources compliant with the AU eRequesting Patient profile
and optionally POSTs them to a FHIR server.
"""

import base64
import json
import random
import string
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from common.types import PatientContext

_PROFILE_URL = "http://hl7.org.au/fhir/ereq/StructureDefinition/au-erequesting-patient"
_IDENTIFIER_SYSTEM = "https://github.com/MattCordell/banksia/id/patient"


def _generate_identifier_value() -> str:
    """Generate a timestamp-based identifier with a short random suffix.

    Format: YYYYMMDDHHmmss-xxxx  (e.g. '20260306143022-a3x7')
    """
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{ts}-{suffix}"


def _map_gender(sex: str) -> str:
    """Map PatientContext.sex to FHIR administrative-gender code."""
    mapping = {
        "male": "male",
        "female": "female",
        "non-binary": "other",
    }
    return mapping.get(sex, "unknown")


def _build_photo(ctx: PatientContext) -> Optional[dict]:
    """Generate a profile photo and return a FHIR Attachment dict.

    Returns None if the RUNWARE_API_KEY is not configured or generation fails.
    """
    try:
        from image_generation.generator import generate_profile_image

        image_path = generate_profile_image(ctx)
        image_bytes = image_path.read_bytes()
        b64 = base64.b64encode(image_bytes).decode("ascii")

        # Clean up the temporary image file
        try:
            image_path.unlink()
        except OSError:
            pass

        return {
            "contentType": "image/jpeg",
            "data": b64,
            "title": "Profile photo",
        }
    except EnvironmentError:
        print("[fhir] RUNWARE_API_KEY not set — skipping photo generation")
        return None
    except Exception as exc:
        print(f"[fhir] Photo generation failed: {exc}")
        return None


def build_fhir_patient(ctx: PatientContext, include_photo: bool = True) -> dict:
    """Build a FHIR R4 Patient resource dict from a PatientContext.

    Args:
        ctx: Populated PatientContext (identity must be assigned first).
        include_photo: Whether to attempt photo generation.

    Returns:
        FHIR Patient resource as a dict.
    """
    resource = {
        "resourceType": "Patient",
        "meta": {
            "profile": [_PROFILE_URL],
        },
        "identifier": [
            {
                "use": "usual",
                "type": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR",
                            "display": "Medical record number",
                        }
                    ]
                },
                "system": _IDENTIFIER_SYSTEM,
                "value": _generate_identifier_value(),
            }
        ],
        "name": [
            {
                "use": "usual",
                "text": f"{ctx.given_name} {ctx.family_name}",
                "family": ctx.family_name,
                "given": [ctx.given_name],
            }
        ],
        "gender": _map_gender(ctx.sex),
        "birthDate": ctx.birth_date.isoformat() if ctx.birth_date else None,
    }

    # Address
    if ctx.street_address or ctx.city or ctx.state:
        address = {
            "use": "home",
            "line": [ctx.street_address] if ctx.street_address else [],
            "country": "AU",
        }
        if ctx.city:
            address["city"] = ctx.city
        if ctx.state:
            address["state"] = ctx.state
        if ctx.postcode:
            address["postalCode"] = ctx.postcode

        # Build display text
        parts = []
        if ctx.street_address:
            parts.append(ctx.street_address)
        locality = " ".join(
            p for p in [ctx.city, ctx.state, ctx.postcode] if p
        )
        if locality:
            parts.append(locality)
        address["text"] = ", ".join(parts)

        resource["address"] = [address]

    # Photo (optional)
    if include_photo:
        photo = _build_photo(ctx)
        if photo:
            resource["photo"] = [photo]

    return resource


def post_to_fhir_server(resource: dict, base_url: str = "https://server.fire.ly") -> dict:
    """POST a FHIR Patient resource to a FHIR server.

    Args:
        resource: FHIR Patient resource dict.
        base_url: FHIR server base URL.

    Returns:
        dict with 'status_code', 'id', and 'response' keys.
    """
    url = f"{base_url.rstrip('/')}/Patient"
    resp = requests.post(
        url,
        json=resource,
        headers={"Content-Type": "application/fhir+json"},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    server_id = body.get("id", "unknown")
    print(f"[fhir] Patient created: {base_url.rstrip('/')}/Patient/{server_id}")
    return {
        "status_code": resp.status_code,
        "id": server_id,
        "response": body,
    }
