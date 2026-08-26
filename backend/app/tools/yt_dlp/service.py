# app/tools/yt_dlp/service.py

import asyncio
import time
from pathlib import Path
import httpx

import imageio_ffmpeg
import yt_dlp

from app.core.tool_base import NormalizedFinding
from app.config import settings
from app.models.finding import ExposureCategory


def _output_dir(username: str) -> Path:
    d = Path(settings.yt_dlp_output_dir) / username
    d.mkdir(parents=True, exist_ok=True)
    return d


def _download_one_blocking(url: str, username: str, progress_cb=None) -> list[dict]:
    out_dir = _output_dir(username)
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    base_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,  # allow carousels to expand into entries
        "ffmpeg_location": ffmpeg_path,
    }
    probe_opts = {**base_opts, "skip_download": True, "ignore_no_formats_error": True, "extract_flat": False}

    with yt_dlp.YoutubeDL(probe_opts) as probe:
        info = probe.extract_info(url, download=False)

    entries = info.get("entries") if info.get("_type") == "playlist" else [info]

    results = []
    for entry in entries:
        results.append(_download_entry(entry, url, out_dir, ffmpeg_path, progress_cb))
    return results


def _download_entry(entry: dict, source_url: str, out_dir: Path, ffmpeg_path: str, progress_cb=None) -> dict:
    has_video = bool(entry.get("formats")) and entry.get("vcodec") not in (None, "none")
    entry_id = entry.get("id") or entry.get("display_id") or "item"

    if has_video:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "ffmpeg_location": ffmpeg_path,
            "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
            "format": "bestvideo+bestaudio/best",
        }
        if progress_cb:
            ydl_opts["progress_hooks"] = [progress_cb]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(entry.get("webpage_url") or entry.get("url") or source_url, download=True)
            filepath = ydl.prepare_filename(result)
        is_video = True
    else:
        image_url = entry.get("thumbnail") or entry.get("url")
        if not image_url:
            raise RuntimeError(f"No image URL found for entry {entry_id}")
        filename = f"{entry_id}.jpg"
        filepath = str(out_dir / filename)
        resp = httpx.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)
        is_video = False

    return {
        "source_url": source_url,
        "local_path": filepath,
        "filename": Path(filepath).name,
        "ext": Path(filepath).suffix.lstrip("."),
        "is_video": is_video,
        "duration": entry.get("duration"),
        "width": entry.get("width"),
        "height": entry.get("height"),
        "title": entry.get("title"),
        "uploader": entry.get("uploader"),
        "timestamp": entry.get("timestamp"),
    }


async def _download_one(url: str, username: str, progress_cb=None) -> list[dict]:
    return await asyncio.to_thread(_download_one_blocking, url, username, progress_cb)

def _to_finding(username: str, item: dict, elapsed: float) -> NormalizedFinding:
    served_url = f"/media/yt_dlp/{username}/{item['filename']}"
    return NormalizedFinding(
        source="yt_dlp",
        source_url=item["source_url"],
        raw_value=served_url,
        category=ExposureCategory.BEHAVIORAL_PATTERN,
        response_time_s=elapsed,
        extra_metadata={
            "field": "downloaded_media",
            "local_path": item["local_path"],
            "served_url": served_url,
            "filename": item["filename"],
            "ext": item["ext"],
            "is_video": item["is_video"],
            "duration": item["duration"],
            "width": item["width"],
            "height": item["height"],
            "title": item["title"],
            "uploader": item["uploader"],
        },
    )


async def run(target_value: str, urls: list[str]) -> list[NormalizedFinding]:
    username = target_value.strip().lstrip("@")
    start = time.monotonic()

    findings: list[NormalizedFinding] = []
    for url in urls:
        items = await _download_one(url, username)  # now a list
        elapsed = time.monotonic() - start
        for item in items:
            findings.append(_to_finding(username, item, elapsed))

    return findings