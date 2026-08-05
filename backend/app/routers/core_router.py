"""
Endpoints that aren't owned by any single tool (history spans all
tools). Mounted directly in main.py, not via the tool registry.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.target import Target

router = APIRouter(prefix="/scan", tags=["core"])


@router.get("/history")
def list_scanned_targets(db: Session = Depends(get_db)):
    targets = db.query(Target).order_by(Target.created_at.desc()).all()

    results = []
    for t in targets:
        count = db.query(Finding).filter(Finding.target_id == t.id).count()
        latest_scan = (
            db.query(Scan)
            .filter(Scan.target_id == t.id)
            .order_by(Scan.started_at.desc())
            .first()
        )
        results.append({
            "username": t.label,
            "target_id": str(t.id),
            "tool_id": latest_scan.tool_used if latest_scan else "unknown",
            "scanned_at": t.created_at.isoformat() if t.created_at else None,
            "findings_count": count,
        })

    return {"total_targets": len(results), "targets": results}
