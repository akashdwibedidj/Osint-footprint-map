"""
Celery task wrapper around service.run_from_path. Kept in its own module
(not tasks inside service.py) so celery_app.py can `include` it without
importing FastAPI/router concerns, and so service.py stays framework-free.
"""

from app.celery_app import celery_app
from app.tools.audio_analysis import service


@celery_app.task(name="audio_analysis.run")
def run_task(target_label: str, file_path: str, investigation_id: str) -> str:
    scan_id = service.run_from_path(target_label, file_path, investigation_id=investigation_id)
    return str(scan_id)