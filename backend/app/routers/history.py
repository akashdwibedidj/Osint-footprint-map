from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.target import Target

router = APIRouter(tags=["history"])


@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    rows = (
        db.query(
            Target.id.label("target_id"),
            Target.label.label("username"),
            Scan.tool_used.label("tool_id"),
            func.max(Scan.finished_at).label("scanned_at"),
            func.count(Finding.id).label("findings_count"),
        )
        .join(Scan, Scan.target_id == Target.id)
        .outerjoin(Finding, Finding.scan_id == Scan.id)
        .group_by(Target.id, Target.label, Scan.tool_used)
        .order_by(func.max(Scan.finished_at).desc())
        .all()
    )

    return [
        {
            "username": r.username,
            "target_id": str(r.target_id),
            "tool_id": r.tool_id,
            "scanned_at": r.scanned_at.isoformat() if r.scanned_at else None,
            "findings_count": r.findings_count,
        }
        for r in rows
    ]