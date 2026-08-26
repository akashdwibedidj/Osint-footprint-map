from app.celery_app import celery_app
from app.tools.instaloader import service


@celery_app.task(name="instaloader.run")
def run_task(target_label: str, username: str, investigation_id: str) -> str:
    scan_id = service.run_from_username(target_label, username, investigation_id=investigation_id)
    return str(scan_id)