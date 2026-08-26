"""
Celery application instance. Broker and result backend both use Redis.
Task modules are registered via `include` below - when you add a new
tool's task wrapper (app/tools/<name>/tasks.py), add it to this list.
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "osint_footprint",
    broker=getattr(settings, "redis_url", "redis://localhost:6379/0"),
    backend=getattr(settings, "redis_url", "redis://localhost:6379/0"),
        include=[
        "app.tools.audio_analysis.tasks",
        "app.tools.video_analysis.tasks",
        "app.tools.exif_extractor.tasks",
        "app.tools.instaloader.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)