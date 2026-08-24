import asyncio
import io
import os
import uuid
from datetime import datetime, timezone

import requests
from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

from app.models.finding import ExposureCategory
from app.services.storage import NormalizedFinding
from app.db.postgres import SessionLocal
from app.models.scan import Scan
from app.models.target import Target
from app.services import storage

TOOL_ID = "exif_extractor"
ACCEPTED_INPUTS = {"image"}

def _convert_to_degrees(value):
    """Convert GPS coordinates stored as (deg, min, sec) rationals to decimal degrees."""
    d, m, s = value
    return float(d) + (float(m) / 60.0) + (float(s) / 3600.0)


def _extract_gps(gps_info: dict) -> dict | None:
    try:
        lat = _convert_to_degrees(gps_info["GPSLatitude"])
        if gps_info.get("GPSLatitudeRef") == "S":
            lat = -lat
        lon = _convert_to_degrees(gps_info["GPSLongitude"])
        if gps_info.get("GPSLongitudeRef") == "W":
            lon = -lon
        return {"latitude": lat, "longitude": lon}
    except (KeyError, TypeError, ZeroDivisionError):
        return None


def _extract_exif(image_bytes: bytes) -> dict:
    """Blocking image parse + EXIF extraction."""
    img = Image.open(io.BytesIO(image_bytes))
    raw_exif = img.getexif()

    if not raw_exif:
        return {}

    exif_data = {}
    gps_info = {}

    for tag_id, value in raw_exif.items():
        tag = TAGS.get(tag_id, tag_id)
        if tag == "GPSInfo":
            for gps_tag_id, gps_value in raw_exif.get_ifd(tag_id).items():
                gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                gps_info[gps_tag] = gps_value
        else:
            # Skip non-serializable / binary blobs
            if isinstance(value, (bytes, bytearray)):
                continue
            exif_data[str(tag)] = value

    if gps_info:
        coords = _extract_gps(gps_info)
        if coords:
            exif_data["GPSCoordinates"] = coords

    return exif_data


def _fetch_image_bytes(image_url: str) -> bytes:
    resp = requests.get(image_url, timeout=15)
    resp.raise_for_status()
    return resp.content


async def run(
    target_value: str,
    image_bytes: bytes | None = None,
    **kwargs,
) -> list[NormalizedFinding]:
    """
    target_value: a URL pointing to an image, OR a label/filename if image_bytes is supplied directly.
    image_bytes: raw bytes of an uploaded image. If provided, target_value is used only as a label
                 (source_url / raw_value context) and no HTTP fetch is performed.
    """
    if image_bytes is None:
        image_bytes = await asyncio.to_thread(_fetch_image_bytes, target_value)

    exif_data = await asyncio.to_thread(_extract_exif, image_bytes)

    if not exif_data:
        return []

    findings: list[NormalizedFinding] = []

    gps = exif_data.pop("GPSCoordinates", None)
    if gps:
        findings.append(
            NormalizedFinding(
                source="exif_extractor",
                source_url=target_value,
                raw_value=f"{gps['latitude']},{gps['longitude']}",
                category=ExposureCategory.BEHAVIORAL_PATTERN,
                extra_metadata={"gps": gps, "field": "GPSCoordinates"},
            )
        )

    device_fields = {"Make", "Model", "Software", "LensModel"}
    device_meta = {k: v for k, v in exif_data.items() if k in device_fields}
    if device_meta:
        findings.append(
            NormalizedFinding(
                source="exif_extractor",
                source_url=target_value,
                raw_value=" / ".join(str(v) for v in device_meta.values()),
                category=ExposureCategory.BEHAVIORAL_PATTERN,
                extra_metadata={"device_info": device_meta},
            )
        )

    remaining = {k: v for k, v in exif_data.items() if k not in device_fields}
    if remaining:
        findings.append(
            NormalizedFinding(
                source="exif_extractor",
                source_url=target_value,
                raw_value="full_exif_dump",
                category=ExposureCategory.BEHAVIORAL_PATTERN,
                extra_metadata={"raw_exif": {k: str(v) for k, v in remaining.items()}},
            )
        )

    return findings


def get_gps_coordinates(image_bytes: bytes) -> dict | None:
    """Public entry point for other tools that just need GPS, not the full finding pipeline."""
    exif_data = _extract_exif(image_bytes)
    return exif_data.get("GPSCoordinates")


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


def run_from_path(target_label: str, file_path: str, investigation_id: uuid.UUID | None = None) -> uuid.UUID:
    """
    Sync entry point for the Celery task. Wraps the existing async run()
    in asyncio.run() since this executes inside a worker process, not
    the FastAPI event loop.
    """
    db = SessionLocal()
    try:
        target = db.query(Target).filter(Target.label == target_label).first()
        if not target:
            target = Target(label=target_label)
            db.add(target)
            db.flush()

        scan = Scan(
            target_id=target.id,
            tool_used=TOOL_ID,
            status="pending",
            progress=0,
            investigation_id=investigation_id,
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        scan_id = scan.id
    finally:
        db.close()

    try:
        _set_scan(scan_id, status="running", stage="extracting_exif", progress=10)

        with open(file_path, "rb") as f:
            image_bytes = f.read()

        findings = asyncio.run(
            run(target_value=os.path.basename(file_path), image_bytes=image_bytes)
        )

        _set_scan(scan_id, progress=80)

        db = SessionLocal()
        try:
            storage.store_findings(TOOL_ID, target_label, findings, db)
        finally:
            db.close()

        from app.db.neo4j import driver
        with driver.session() as session:
            storage.store_graph(
                tool_id=TOOL_ID,
                target_label=target_label,
                findings=findings,
                session=session,
                identifier_type="image_upload",
            )

        _set_scan(
            scan_id,
            status="done",
            stage="extracting_exif",
            progress=100,
            finished_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        _set_scan(scan_id, status="failed", error_message=f"{type(e).__name__}: {e}")

    return scan_id