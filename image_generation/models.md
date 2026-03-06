# Image Generation Models

Images are generated via the [Runware API](https://runware.ai). Each image type uses a dedicated model selected for quality and cost.

| Image Type | Model | Runware AIR ID | Cost/image | Output Size | Notes |
|---|---|---|---|---|---|
| Profile | Runware 101 | `runware:101@1` | ~$0.004 | 256x256 | Fast, good portrait quality with 70s polaroid style |
| Radiology | Runware 5 | `runware:5@1` | ~$0.002 | 1024x1024 | Budget model, produces convincing X-ray/CT/ultrasound imagery |
| Microscopy | Runware 5 | `runware:5@1` | ~$0.002 | 1024x1024 | Budget model, good histology and stain reproduction |

Models are configured per image type in `prompts.json` and can be changed without code modifications.
