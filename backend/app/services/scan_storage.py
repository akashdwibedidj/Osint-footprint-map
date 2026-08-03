from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.models.target import Target
from app.models.scan import Scan
from app.models.finding import Finding, ExposureCategory


def store_sherlock_results(username: str, sherlock_result: dict, db: Session) -> dict:
    """
    Takes sherlock_service.search_username() output and:
    1. Creates (or reuses) a Target for this username
    2. Creates a Scan record
    3. Inserts one Finding row per found site
    (Risk scoring intentionally deferred until more tools/data are integrated.)
    """

    # 1. Get or create Target
    target = db.query(Target).filter(Target.label == username).first()
    if not target:
        target = Target(label=username)
        db.add(target)
        db.flush()

    # 2. Create Scan record
    scan = Scan(target_id=target.id, tool_used="sherlock")
    db.add(scan)
    db.flush()

    # 3. Insert Finding rows (neutral placeholder scores for now)
    findings = []
    for site in sherlock_result.get("found", []):
        http_status = site.get("http_status")
        response_time = site.get("response_time_s")

        finding = Finding(
            target_id=target.id,
            scan_id=scan.id,
            source=site.get("site"),
            source_url=site.get("url"),
            raw_value=username,
            category=ExposureCategory.PERSONAL_IDENTIFIER,
            http_status=int(http_status) if http_status and str(http_status).isdigit() else None,
            response_time_s=float(response_time) if response_time else None,
            sensitivity_score=1,
            correlation_score=1,
            exploitability_score=1,
            recency_score=1,
            risk_severity="unscored",
        )
        findings.append(finding)

    db.add_all(findings)

    scan.finished_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "target_id": str(target.id),
        "scan_id": str(scan.id),
        "findings_stored": len(findings),
    }

def store_maigret_findings(username: str, findings: List[Dict[str, Any]], db: Session) -> dict:
    """
    Store Maigret findings in Postgres.
    Reuses existing Target/Scan/Finding models.
    """
    # Get or create Target
    target = db.query(Target).filter(Target.label == username).first()
    if not target:
        target = Target(label=username)
        db.add(target)
        db.flush()

    # Create Scan row
    scan = Scan(
        target_id=target.id,
        tool_used="maigret",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    db.flush()

    # Create Finding rows (one per claimed platform)
    for f in findings:
        finding = Finding(
            target_id=target.id,
            scan_id=scan.id,
            source=f["platform"],
            source_url=f["url_user"],
            raw_value=f["username"],
            category=ExposureCategory.PERSONAL_IDENTIFIER,
            risk_severity="unscored",
            http_status=int(f["http_status"]) if f.get("http_status") else None,
            extra_metadata={
                "url_main": f["url_main"],
                "tool": "maigret",
            },
        )
        db.add(finding)

    db.commit()
    return {"target_id": str(target.id), "scan_id": str(scan.id)}