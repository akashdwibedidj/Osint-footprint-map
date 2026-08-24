from app.celery_app import celery_app
from app.tools.video_analysis import service


@celery_app.task(name="video_analysis.run")
def run_task(target_label: str, file_path: str, investigation_id: str) -> str:
    scan_id = service.run_from_path(target_label, file_path, investigation_id=investigation_id)
    return str(scan_id)