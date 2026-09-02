from app.celery_app import celery_app
from app.tools.gitleak_scanner import service


@celery_app.task(name="gitleak_scanner.run")
def run_task(target_label: str, repo_value: str, investigation_id: str) -> str:
    scan_id = service.run_from_repo_url(target_label, repo_value, investigation_id=investigation_id)
    return str(scan_id)