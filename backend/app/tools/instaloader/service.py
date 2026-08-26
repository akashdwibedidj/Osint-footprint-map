# app/tools/instaloader/service.py

import asyncio
import time
import uuid as uuid_module
from datetime import datetime, timezone

import instaloader

from app.core.tool_base import NormalizedFinding
from app.models.finding import ExposureCategory
from app.db.postgres import SessionLocal
from app.models.scan import Scan
from app.models.target import Target
from app.services import storage
from app.tools.yt_dlp import service as yt_dlp_service
from app.orchestrator.registry import tools_for_input

MAX_POSTS = 12          # anonymous scraping gets rate-limited fast; keep this small
REQUEST_DELAY_S = 2.5   # delay between post fetches to reduce 429 risk

TOOL_ID = "instaloader"
ACCEPTED_INPUTS = {"username"}


def _build_loader() -> instaloader.Instaloader:
    return instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=True,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )


def _fetch_profile_blocking(username: str) -> dict:
    """
    Runs synchronously in a thread (instaloader is blocking, same reasoning
    as gitleak_scanner's subprocess calls).
    Returns a dict with profile-level fields and a list of post dicts.
    """
    loader = _build_loader()
    profile = instaloader.Profile.from_username(loader.context, username)

    profile_data = {
        "userid": profile.userid,
        "username": profile.username,
        "full_name": profile.full_name,
        "biography": profile.biography,
        "external_url": profile.external_url,
        "followers": profile.followers,
        "followees": profile.followees,
        "mediacount": profile.mediacount,
        "is_private": profile.is_private,
        "is_verified": profile.is_verified,
        "is_business_account": profile.is_business_account,
        "business_category_name": getattr(profile, "business_category_name", None),
        "business_email": getattr(profile, "business_email", None),
        "business_phone_number": getattr(profile, "business_phone_number", None),
        "profile_pic_url": profile.profile_pic_url,
    }

    posts_data = []
    if not profile.is_private:
        try:
            for i, post in enumerate(profile.get_posts()):
                if i >= MAX_POSTS:
                    break
                posts_data.append({
                    "shortcode": post.shortcode,
                    "post_url": f"https://www.instagram.com/p/{post.shortcode}/",
                    "image_url": post.url,  # main display image URL
                    "is_video": post.is_video,
                    "video_url": post.video_url if post.is_video else None,
                    "caption": post.caption,
                    "date_utc": post.date_utc.isoformat() if post.date_utc else None,
                    "likes": post.likes,
                    "comments": post.comments,
                    "location": post.location.name if post.location else None,
                    "tagged_users": list(post.caption_mentions) if post.caption_mentions else [],
                })
                time.sleep(REQUEST_DELAY_S)
        except Exception:
            # Rate-limited or blocked mid-iteration - keep whatever we already got
            pass

    return {"profile": profile_data, "posts": posts_data}


async def _fetch_profile(username: str) -> dict:
    return await asyncio.to_thread(_fetch_profile_blocking, username)


def _profile_findings(username: str, profile: dict, elapsed: float) -> list[NormalizedFinding]:
    findings: list[NormalizedFinding] = []
    source_url = f"https://www.instagram.com/{username}/"

    if profile.get("full_name"):
        findings.append(NormalizedFinding(
            source="instaloader",
            source_url=source_url,
            raw_value=profile["full_name"],
            category=ExposureCategory.PERSONAL_IDENTIFIER,
            response_time_s=elapsed,
            extra_metadata={"field": "full_name"},
        ))

    if profile.get("biography"):
        findings.append(NormalizedFinding(
            source="instaloader",
            source_url=source_url,
            raw_value=profile["biography"],
            category=ExposureCategory.PERSONAL_IDENTIFIER,
            response_time_s=elapsed,
            extra_metadata={"field": "biography"},
        ))

    if profile.get("external_url"):
        findings.append(NormalizedFinding(
            source="instaloader",
            source_url=source_url,
            raw_value=profile["external_url"],
            category=ExposureCategory.CONTACT_DETAIL,
            response_time_s=elapsed,
            extra_metadata={"field": "external_url"},
        ))

    if profile.get("business_email"):
        findings.append(NormalizedFinding(
            source="instaloader",
            source_url=source_url,
            raw_value=profile["business_email"],
            category=ExposureCategory.CONTACT_DETAIL,
            response_time_s=elapsed,
            extra_metadata={"field": "business_email"},
        ))

    if profile.get("business_phone_number"):
        findings.append(NormalizedFinding(
            source="instaloader",
            source_url=source_url,
            raw_value=profile["business_phone_number"],
            category=ExposureCategory.CONTACT_DETAIL,
            response_time_s=elapsed,
            extra_metadata={"field": "business_phone_number"},
        ))

    if profile.get("profile_pic_url"):
        findings.append(NormalizedFinding(
            source="instaloader",
            source_url=source_url,
            raw_value=profile["profile_pic_url"],
            category=ExposureCategory.PERSONAL_IDENTIFIER,
            response_time_s=elapsed,
            extra_metadata={
                "field": "profile_pic_url",
                "followers": profile.get("followers"),
                "followees": profile.get("followees"),
                "mediacount": profile.get("mediacount"),
                "is_private": profile.get("is_private"),
                "is_verified": profile.get("is_verified"),
                "is_business_account": profile.get("is_business_account"),
                "business_category_name": profile.get("business_category_name"),
            },
        ))

    return findings


def _post_findings(username: str, posts: list[dict], elapsed: float) -> list[NormalizedFinding]:
    findings: list[NormalizedFinding] = []
    for post in posts:
        findings.append(NormalizedFinding(
            source="instaloader",
            source_url=post["post_url"],
            raw_value=post["image_url"],
            category=ExposureCategory.BEHAVIORAL_PATTERN,
            response_time_s=elapsed,
            extra_metadata={
                "field": "post_image",
                "shortcode": post["shortcode"],
                "is_video": post["is_video"],
                "video_url": post["video_url"],
                "caption": post["caption"],
                "date_utc": post["date_utc"],
                "likes": post["likes"],
                "comments": post["comments"],
                "location": post["location"],
                "tagged_users": post["tagged_users"],
            },
        ))
    return findings


async def run(target_value: str, **kwargs) -> list[NormalizedFinding]:
    """
    target_value: Instagram username (no @, no URL - just the handle).
    """
    username = target_value.strip().lstrip("@")
    start = time.monotonic()

    data = await _fetch_profile(username)
    elapsed = time.monotonic() - start

    findings = _profile_findings(username, data["profile"], elapsed)
    findings += _post_findings(username, data["posts"], elapsed)

    return findings


def _set_scan(scan_id, **fields) -> None:
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


def run_from_username(
    target_label: str, username: str, investigation_id: uuid_module.UUID | None = None
) -> uuid_module.UUID:
    """
    Sync entry point for the Celery task. Runs instaloader's own async
    scrape, stores its findings, then hands post URLs to yt_dlp for
    download, then dispatches each downloaded file to every matching
    tool (exif_extractor, video_analysis) via the normal registry -
    same dispatch mechanism as user-uploaded files, just triggered here
    instead of at intake.
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
        _set_scan(scan_id, status="running", stage="scraping_profile", progress=10)

        profile_findings = asyncio.run(run(target_value=username))

        db = SessionLocal()
        try:
            storage.store_findings(TOOL_ID, target_label, profile_findings, db)
        finally:
            db.close()

        _set_scan(scan_id, stage="downloading_media", progress=40)

        post_urls = [
            f["source_url"] for f in profile_findings
            if isinstance(f, NormalizedFinding) and f.extra_metadata.get("field") == "post_image"
        ]
        # profile_findings above is already-built NormalizedFinding objects from
        # _post_findings, whose source_url is the post URL (post["post_url"]).

        if post_urls:
            media_findings = asyncio.run(yt_dlp_service.run(username, post_urls))

            db = SessionLocal()
            try:
                storage.store_findings("yt_dlp", target_label, media_findings, db)
            finally:
                db.close()

            _set_scan(scan_id, stage="dispatching_downloads", progress=70)

            for mf in media_findings:
                local_path = mf.extra_metadata.get("local_path")
                if not local_path:
                    continue
                input_type = "video" if mf.extra_metadata.get("is_video") else "image"
                for tool in tools_for_input(input_type):
                    from app.celery_app import celery_app
                    celery_app.send_task(
                        tool.task_name,
                        args=[target_label, local_path, str(investigation_id) if investigation_id else None],
                    )

        _set_scan(
            scan_id,
            status="done",
            stage="dispatching_downloads",
            progress=100,
            finished_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        _set_scan(scan_id, status="failed", error_message=f"{type(e).__name__}: {e}")

    return scan_id