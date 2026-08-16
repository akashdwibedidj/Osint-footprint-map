import os
import uuid
from datetime import datetime, timezone

from app.core.tool_base import NormalizedFinding
from app.db.postgres import SessionLocal
from app.models.finding import ExposureCategory
from app.models.scan import Scan
from app.services import storage
from app.tools.video_analysis import frame_extractor, geolocation, model_loader, utils

TOOL_ID = "video_analysis"

STAGE_WEIGHTS_VIDEO = {
    "extracting_frames": (0, 15),
    "detecting_objects": (15, 40),
    "captioning": (40, 60),
    "analyzing_signals": (60, 95),
    "storing": (95, 100),
}
STAGE_WEIGHTS_IMAGE = {
    "detecting_objects": (0, 30),
    "captioning": (30, 55),
    "analyzing_signals": (55, 95),
    "storing": (95, 100),
}


def _set_scan(scan_id: uuid.UUID, **fields) -> None:
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return
        for k, v in fields.items():
            setattr(scan, k, v)
        db.commit()
    finally:
        db.close()


def _set_stage_progress(scan_id: uuid.UUID, weights: dict, stage: str, fraction: float) -> None:
    lo, hi = weights[stage]
    progress = int(lo + (hi - lo) * max(0.0, min(1.0, fraction)))
    _set_scan(scan_id, status="running", stage=stage, progress=progress)


def _detect_objects(image_bytes: bytes) -> list[dict]:
    import io
    from PIL import Image

    model = model_loader.get_yolo_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    results = model.predict(image, verbose=False)

    detections = []
    for r in results:
        for box in r.boxes:
            detections.append({
                "label": r.names[int(box.cls[0])],
                "confidence": round(float(box.conf[0]), 4),
            })
    return detections


def _caption_image(image_bytes: bytes) -> str:
    import io
    import torch
    from PIL import Image

    processor, model = model_loader.get_blip_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=50,
            repetition_penalty=1.5,
            no_repeat_ngram_size=3,
        )
    return processor.decode(out[0], skip_special_tokens=True).strip()


def _build_frame_findings(
    source_url: str, frame_index: int, timestamp_s: float,
    detections: list[dict], caption: str, signals: dict,
) -> list[NormalizedFinding]:
    findings: list[NormalizedFinding] = []
    frame_source_url = f"{source_url}#frame_{frame_index}"
    base_meta = {"frame_index": frame_index, "timestamp_s": timestamp_s}

    if detections:
        findings.append(NormalizedFinding(
            source=TOOL_ID,
            source_url=frame_source_url,
            raw_value=", ".join(sorted({d["label"] for d in detections})),
            category=ExposureCategory.BEHAVIORAL_PATTERN,
            extra_metadata={"field": "objects_detected", "detections": detections, **base_meta},
        ))

    if caption:
        findings.append(NormalizedFinding(
            source=TOOL_ID,
            source_url=frame_source_url,
            raw_value=caption,
            category=ExposureCategory.BEHAVIORAL_PATTERN,
            extra_metadata={"field": "image_caption", **base_meta},
        ))

    if "gps" in signals:
        gps = signals["gps"]
        findings.append(NormalizedFinding(
            source=TOOL_ID,
            source_url=frame_source_url,
            raw_value=f"{gps['latitude']},{gps['longitude']}",
            category=ExposureCategory.BEHAVIORAL_PATTERN,
            extra_metadata={"field": "gps_coordinates", "location": gps, **base_meta},
        ))

    if "landmark" in signals:
        lm = signals["landmark"]
        findings.append(NormalizedFinding(
            source=TOOL_ID,
            source_url=frame_source_url,
            raw_value=lm["landmark"],
            category=ExposureCategory.BEHAVIORAL_PATTERN,
            extra_metadata={"field": "landmark_recognition", **lm, **base_meta},
        ))

    if "terrain" in signals:
        tr = signals["terrain"]
        findings.append(NormalizedFinding(
            source=TOOL_ID,
            source_url=frame_source_url,
            raw_value=tr["terrain"],
            category=ExposureCategory.BEHAVIORAL_PATTERN,
            extra_metadata={"field": "terrain_structure", **tr, **base_meta},
        ))

    if "environment" in signals:
        env = signals["environment"]
        findings.append(NormalizedFinding(
            source=TOOL_ID,
            source_url=frame_source_url,
            raw_value=env["environment"],
            category=ExposureCategory.BEHAVIORAL_PATTERN,
            extra_metadata={"field": "environmental_signature", **env, **base_meta},
        ))

    if "ocr" in signals:
        ocr = signals["ocr"]
        findings.append(NormalizedFinding(
            source=TOOL_ID,
            source_url=frame_source_url,
            raw_value=ocr["ocr_text"],
            category=ExposureCategory.BEHAVIORAL_PATTERN,
            extra_metadata={"field": "ocr_text", **base_meta},
        ))

    return findings


def process_video_job(scan_id: uuid.UUID, target_label: str, original_path: str, filename: str) -> None:
    """
    Entry point run as a FastAPI BackgroundTask. Handles both images (single
    implicit frame) and videos (frame_extractor samples at fixed interval),
    running YOLO -> BLIP -> multi-signal analysis (gps/landmark/terrain/
    environment/ocr) per frame.
    """
    try:
        with open(original_path, "rb") as f:
            file_bytes = f.read()

        is_video = utils.is_video(filename)
        weights = STAGE_WEIGHTS_VIDEO if is_video else STAGE_WEIGHTS_IMAGE

        _set_scan(scan_id, status="running", stage=next(iter(weights)), progress=0)

        if is_video:
            _set_stage_progress(scan_id, weights, "extracting_frames", 0.0)
            frames = frame_extractor.extract_frames(original_path)
            _set_stage_progress(scan_id, weights, "extracting_frames", 1.0)
        else:
            frames = [(0, 0.0, file_bytes)]

        total = len(frames)
        all_findings: list[NormalizedFinding] = []
        source_url = f"local_upload://{os.path.basename(original_path)}"

        for i, (frame_index, timestamp_s, frame_bytes) in enumerate(frames):
            detections = _detect_objects(frame_bytes)
            _set_stage_progress(scan_id, weights, "detecting_objects", (i + 1) / total)

            caption = _caption_image(frame_bytes)
            _set_stage_progress(scan_id, weights, "captioning", (i + 1) / total)

            signals = geolocation.resolve_signals(frame_bytes)
            _set_stage_progress(scan_id, weights, "analyzing_signals", (i + 1) / total)

            all_findings.extend(_build_frame_findings(
                source_url, frame_index, timestamp_s, detections, caption, signals,
            ))

        _set_stage_progress(scan_id, weights, "storing", 0.0)

        db = SessionLocal()
        try:
            storage.store_findings(TOOL_ID, target_label, all_findings, db)
        finally:
            db.close()

        from app.db.neo4j import driver
        with driver.session() as session:
            storage.store_graph(
                tool_id=TOOL_ID,
                target_label=target_label,
                findings=all_findings,
                session=session,
                identifier_type="video_upload" if is_video else "image_upload",
            )

        _set_scan(
            scan_id,
            status="done",
            stage="storing",
            progress=100,
            finished_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        _set_scan(scan_id, status="failed", error_message=f"{type(e).__name__}: {e}")

    finally:
        utils.cleanup_file(original_path)