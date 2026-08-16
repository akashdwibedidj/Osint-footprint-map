"""
Visual intelligence signals for OSINT:
  1. EXIF GPS - exact, only when embedded in the file. The only source of
     a coordinate anywhere in this module.
  2. Landmark recognition - CLIP zero-shot against KNOWN_LANDMARKS.
  3. Terrain/structure matching - CLIP zero-shot against TERRAIN_TYPES.
  4. Environmental signatures - CLIP zero-shot against ENVIRONMENT_SIGNATURES.
  5. Full OCR - reads all visible text via pytesseract, reported raw.

IMPORTANT: signals 2-4 do NOT use softmax-argmax across their prompt list.
Softmax always produces a "winner" even when nothing in the list actually
matches the frame (this is what caused "the Great Wall of China" to
false-fire on nearly every frame of an unrelated cosplay video). Instead,
each candidate prompt's raw image-text similarity is compared against a
neutral baseline prompt ("a photograph") - a candidate is only accepted
if it beats the baseline by a real margin, so "no genuine match" can
correctly report as no match instead of a forced, misleading winner.
"""

import io

import pytesseract
from PIL import Image

from app.config import settings
from app.tools.exif_extractor.service import get_gps_coordinates
from app.tools.video_analysis import model_loader
from app.tools.video_analysis.prompts.environment import ENVIRONMENT_SIGNATURES
from app.tools.video_analysis.prompts.landmarks import KNOWN_LANDMARKS
from app.tools.video_analysis.prompts.terrain import TERRAIN_TYPES

pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

BASELINE_PROMPT = "a photograph"

# Minimum margin the best candidate must beat the neutral baseline by,
# in cosine similarity, to be accepted as a genuine match rather than
# noise. Tune these per signal type if you see too many/few matches.
LANDMARK_MARGIN = 0.05
TERRAIN_MARGIN = 0.03
ENVIRONMENT_MARGIN = 0.02


def _try_exif(image_bytes: bytes) -> dict | None:
    gps = get_gps_coordinates(image_bytes)
    if gps:
        return {"method": "exif_gps", "confidence": 1.0, **gps}
    return None


def _clip_best_match(image_bytes: bytes, candidate_prompts: list[str], margin: float) -> dict | None:
    """
    Encodes the image once, compares it against every candidate prompt
    PLUS a neutral baseline, using raw cosine similarity (not softmax
    over just the candidates - that forces a winner even among bad
    matches). The best candidate is only accepted if it beats the
    baseline's similarity by `margin`; otherwise there's genuinely no
    match in this frame and None is returned.
    """
    import torch
    import torch.nn.functional as F

    processor, model = model_loader.get_clip_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    all_prompts = candidate_prompts + [BASELINE_PROMPT]
    inputs = processor(text=all_prompts, images=image, return_tensors="pt", padding=True)

    with torch.no_grad():
        outputs = model(**inputs)
        image_embeds = F.normalize(outputs.image_embeds, dim=-1)
        text_embeds = F.normalize(outputs.text_embeds, dim=-1)
        similarities = (image_embeds @ text_embeds.T)[0]  # cosine similarity per prompt

    baseline_score = float(similarities[-1])
    candidate_scores = similarities[:-1]

    best_idx = int(candidate_scores.argmax())
    best_score = float(candidate_scores[best_idx])

    if (best_score - baseline_score) < margin:
        return None

    return {
        "label": candidate_prompts[best_idx],
        "confidence": round(best_score, 4),
        "margin_over_baseline": round(best_score - baseline_score, 4),
    }


def _try_landmark(image_bytes: bytes) -> dict | None:
    prompts = [entry["prompt"] for entry in KNOWN_LANDMARKS]
    match = _clip_best_match(image_bytes, prompts, LANDMARK_MARGIN)
    if not match:
        return None

    # match["label"] is the winning prompt string - look up its metadata
    matched_entry = next(e for e in KNOWN_LANDMARKS if e["prompt"] == match["label"])

    return {
        "landmark": matched_entry["prompt"],
        "state": matched_entry["state"],
        "country": matched_entry["country"],
        "confidence": match["confidence"],
    }


def _try_terrain(image_bytes: bytes) -> dict | None:
    prompts = [f"a photo of {t}" for t in TERRAIN_TYPES]
    match = _clip_best_match(image_bytes, prompts, TERRAIN_MARGIN)
    if not match:
        return None
    return {"terrain": match["label"], "confidence": match["confidence"]}


def _try_environment(image_bytes: bytes) -> dict | None:
    prompts = [f"a photo with {e}" for e in ENVIRONMENT_SIGNATURES]
    match = _clip_best_match(image_bytes, prompts, ENVIRONMENT_MARGIN)
    if not match:
        return None
    return {"environment": match["label"], "confidence": match["confidence"]}


def _try_ocr(image_bytes: bytes) -> dict | None:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    text = pytesseract.image_to_string(image).strip()
    if not text:
        return None
    return {"ocr_text": text}


def resolve_signals(image_bytes: bytes) -> dict:
    """
    Runs every applicable signal independently and returns whichever ones
    actually fired. Keys only present when that signal produced something
    real - never a fabricated fallback. 'gps' is the only key that can
    carry a coordinate.
    """
    signals: dict = {}

    gps = _try_exif(image_bytes)
    if gps:
        signals["gps"] = gps

    landmark = _try_landmark(image_bytes)
    if landmark:
        signals["landmark"] = landmark

    terrain = _try_terrain(image_bytes)
    if terrain:
        signals["terrain"] = terrain

    environment = _try_environment(image_bytes)
    if environment:
        signals["environment"] = environment

    ocr = _try_ocr(image_bytes)
    if ocr:
        signals["ocr"] = ocr

    return signals