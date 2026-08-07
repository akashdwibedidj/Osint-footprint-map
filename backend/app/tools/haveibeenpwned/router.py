from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.neo4j import driver
from app.db.postgres import get_db
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.target import Target
from app.services import storage
from app.services.neo4j_query import get_target_graph
from app.tools.haveibeenpwned import service

TOOL_ID = "haveibeenpwned"
router = APIRouter(prefix="/haveibeenpwned", tags=["haveibeenpwned"])


@router.post("/email/{value}")
async def scan_haveibeenpwned(value: str, db: Session = Depends(get_db)):
    findings = await service.run(value)
    pg_result = storage.store_findings(TOOL_ID, value, findings, db)
    with driver.session() as session:
        storage.store_graph(
            tool_id=TOOL_ID,
            target_label=value,
            findings=findings,
            session=session,
            identifier_type="email",
        )
    return {"value": value, "findings_count": len(findings), **pg_result}


@router.get("/email/{value}")
def get_haveibeenpwned_findings(value: str, db: Session = Depends(get_db)):
    target = db.query(Target).filter(Target.label == value).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    scans = (
        db.query(Scan)
        .filter(Scan.target_id == target.id, Scan.tool_used == TOOL_ID)
        .all()
    )
    if not scans:
        raise HTTPException(status_code=404, detail="No haveibeenpwned scans found for this target")

    scan_ids = [scan.id for scan in scans]
    findings = db.query(Finding).filter(Finding.scan_id.in_(scan_ids)).all()

    return {"value": value, "findings_count": len(findings), "findings": findings}


@router.get("/graph/{value}")
def get_haveibeenpwned_graph(value: str):
    with driver.session() as session:
        graph = get_target_graph(value, session)
    return graph