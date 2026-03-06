# Runware API - Developer Integration Brief

**Prepared for:** SPARKED HL7 AU Connectathon, March 2026

---

## 1. Overview

Runware is an AI image generation API platform designed for developers. It provides pay-as-you-go access to hundreds of image generation models via a simple REST API, with no subscriptions or minimum spend.

For this connectathon, Runware will be used to generate two categories of synthetic images:

- Profile photos for Patient and Practitioner FHIR resources
- Synthetic diagnostic imaging examples (X-ray, ultrasound, MRI) for DiagnosticReport resources

---

## 2. Account Setup

1. Sign up at `https://my.runware.ai/signup`
2. Retrieve your API key from the dashboard
3. Store the key in an environment variable: `RUNWARE_API_KEY`

> New accounts receive **$2 in free credits** on signup. You are only charged for successful image generation requests. No subscription or minimum spend required.

---

## 3. API Reference

### Endpoint

| Field | Value |
|---|---|
| Base URL | `https://api.runware.ai/v1` |
| Method | `POST` |
| Content-Type | `application/json` |
| Authentication | Bearer token (API key in Authorization header) |

### Authentication Header

```
Authorization: Bearer YOUR_RUNWARE_API_KEY
Content-Type: application/json
```

### Request Structure

All requests are arrays of task objects. Each task requires a `taskType` and a unique `taskUUID` (UUID v4).

```json
[
  {
    "taskType": "imageInference",
    "taskUUID": "a770f077-f413-47de-9dac-be0b26a35da6",
    "positivePrompt": "your prompt here",
    "model": "runware:101@1",
    "width": 1024,
    "height": 1024,
    "numberResults": 1,
    "outputType": "base64Data",
    "outputFormat": "JPG",
    "outputQuality": 85,
    "includeCost": true
  }
]
```

### Key Request Parameters

| Parameter | Required | Description |
|---|---|---|
| `taskType` | Yes | Always `"imageInference"` for image generation |
| `taskUUID` | Yes | Unique UUID v4 per request for response matching |
| `positivePrompt` | Yes | Text description of the image to generate |
| `model` | Yes | Model identifier (see Section 4 for recommended models) |
| `width` / `height` | Yes | Output dimensions in pixels (minimum 512, recommend 1024) |
| `numberResults` | No | Number of images to generate (default 1, max 4) |
| `outputType` | No | `base64Data`, `dataURI`, or `URL` (default `URL`) |
| `outputFormat` | No | `JPG`, `PNG`, or `WEBP` (default `JPG`) |
| `outputQuality` | No | Compression quality 20-99 (default 95). Use 85 for profile photos |
| `negativePrompt` | No | Things to avoid in the generated image |
| `includeCost` | No | Set `true` to receive cost per image in response |

### Response Structure

```json
{
  "data": [
    {
      "taskType": "imageInference",
      "taskUUID": "a770f077-f413-47de-9dac-be0b26a35da6",
      "imageBase64Data": "/9j/4AAQ...",
      "imageURL": "https://...",
      "imageUUID": "c64351d5-...",
      "cost": 0.0006,
      "NSFWContent": false
    }
  ]
}
```

Note: `imageBase64Data` is returned when `outputType` is `base64Data`. `imageURL` is returned when `outputType` is `URL`.

---

## 4. Recommended Models

Runware uses an AIR (Artificial Intelligence Resource) identifier system for models, in the format `provider:modelId@version`.

| Use Case | Model ID | Est. Cost/image | Notes |
|---|---|---|---|
| Profile photos | `runware:101@1` | ~$0.001 | Fast, good for character and portrait style images |
| Diagnostic imaging (budget) | `civitai:139562@297320` | ~$0.003 | SDXL - good balance of quality and cost |
| Diagnostic imaging (quality) | `black-forest-labs/flux-dev` | ~$0.025 | FLUX Dev - best quality for realistic medical imagery |
| Quick test / prototype | `runware:5@1` | ~$0.0006 | Cheapest option, lower quality |

Browse the full model library and test models in the playground at `https://runware.ai/models`.

---

## 5. Suggested Prompts

### Profile Photo - Tired Penguin Character

```
Profile photo of a tired-looking penguin character, shot in the style of a
1970s Polaroid photograph, faded warm tones, soft vignette, slight
overexposure, nostalgic film grain
```

### Diagnostic Imaging Examples

**Chest X-ray:**
```
Frontal chest X-ray radiograph, black and white, medical imaging style,
clear lung fields, normal anatomy, no pathology, professional diagnostic
quality, SYNTHETIC TRAINING IMAGE
```

**Abdominal Ultrasound:**
```
Abdominal ultrasound image, grayscale sonography, medical imaging,
liver and gallbladder view, normal anatomy, professional diagnostic
quality, SYNTHETIC TRAINING IMAGE
```

**Knee MRI:**
```
Knee MRI scan, sagittal view, T2 weighted, grayscale, medical imaging
style, normal anatomy, menisci and ligaments visible, professional
diagnostic quality, SYNTHETIC TRAINING IMAGE
```

> Include `SYNTHETIC TRAINING IMAGE` in all diagnostic image prompts. This makes it unambiguous to connectathon participants that images are AI-generated and not real patient data.

---

## 6. Full cURL Example

```bash
curl -X POST https://api.runware.ai/v1 \
  -H "Authorization: Bearer $RUNWARE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "taskType": "imageInference",
      "taskUUID": "a770f077-f413-47de-9dac-be0b26a35da6",
      "positivePrompt": "Profile photo of a tired-looking penguin",
      "model": "runware:101@1",
      "width": 1024,
      "height": 1024,
      "numberResults": 1,
      "outputType": "base64Data",
      "outputFormat": "JPG",
      "outputQuality": 85,
      "includeCost": true
    }
  ]'
```

---

## 7. Python Example

```python
import os, requests, base64, uuid
from PIL import Image
from io import BytesIO

API_KEY = os.environ["RUNWARE_API_KEY"]

def generate_image(prompt: str, output_path: str, size: int = 400):
    response = requests.post(
        "https://api.runware.ai/v1",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json=[{
            "taskType": "imageInference",
            "taskUUID": str(uuid.uuid4()),
            "positivePrompt": prompt,
            "model": "runware:101@1",
            "width": 1024,
            "height": 1024,
            "numberResults": 1,
            "outputType": "base64Data",
            "outputFormat": "JPG",
            "outputQuality": 85,
            "includeCost": True
        }]
    )
    response.raise_for_status()
    result = response.json()["data"][0]
    print(f"Cost: ${result['cost']}")

    # Decode and resize to target size
    img = Image.open(BytesIO(base64.b64decode(result["imageBase64Data"])))
    img = img.resize((size, size), Image.LANCZOS)
    img.save(output_path, format="JPEG", quality=85)
    print(f"Saved to {output_path}")


generate_image(
    "Profile photo of a tired-looking penguin, 1970s Polaroid style",
    "tired_penguin.jpg",
    size=400
)
```

Install dependencies:
```bash
pip install requests Pillow
```

---

## 8. FHIR Integration Notes

Images returned as base64 (`outputType: base64Data`) can be embedded directly into FHIR resources.

### Patient.photo (Profile Images)

```json
"photo": [{
  "contentType": "image/jpeg",
  "data": "<base64-encoded image>",
  "title": "AI-generated profile photo - SYNTHETIC"
}]
```

### DiagnosticReport.presentedForm (Diagnostic Images)

```json
"presentedForm": [{
  "contentType": "image/jpeg",
  "data": "<base64-encoded image>",
  "title": "Chest X-ray - SYNTHETIC AI GENERATED"
}]
```

---

## 9. Pricing Summary

| Scenario | Est. Cost | Notes |
|---|---|---|
| 100 profile photos | ~$0.10 | Using `runware:101@1` at ~$0.001/image |
| 50 diagnostic images (budget) | ~$0.15 | Using SDXL model at ~$0.003/image |
| 50 diagnostic images (quality) | ~$1.25 | Using FLUX Dev at ~$0.025/image |
| Full connectathon demo set | < $2.00 | Well within the $2 free credit allocation |

---

## 10. Useful Links

| Resource | URL |
|---|---|
| Sign up | https://my.runware.ai/signup |
| Dashboard | https://my.runware.ai |
| Full API docs | https://runware.ai/docs/getting-started/introduction |
| Image inference reference | https://runware.ai/docs/image-inference/api-reference |
| Model browser | https://runware.ai/models |
| Playground (test models) | https://runware.ai/playground |
| Pricing | https://runware.ai/pricing |

---

*SPARKED HL7 AU Connectathon 2026 | runware.ai*
