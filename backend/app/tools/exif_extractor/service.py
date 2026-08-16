import asyncio
import io

import requests
from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

from app.models.finding import ExposureCategory
from app.services.storage import NormalizedFinding


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