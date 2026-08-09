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
    try:
        findings = await service.run(value)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        pg_result = storage.store_findings(TOOL_ID, value, findings, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Postgres storage failed: {e}")

    try:
        with driver.session() as session:
            storage.store_graph(
                tool_id=TOOL_ID,
                target_label=value,
                findings=findings,
                session=session,
                identifier_type="email",
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j storage failed: {e}")

    return {"value": value, "findings_count": len(findings), **pg_result}


@router.get("/email/{value}")
def get_haveibeenpwned_findings(value: str, db: Session = Depends(get_db)):
    target = db.query(Target).filter(Target.label == value).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"No scans found for '{value}'")

    findings = (
        db.query(Finding)
        .join(Scan)
        .filter(Finding.target_id == target.id, Scan.tool_used == TOOL_ID)
        .all()
    )

    return {
        "value": value,
        "target_id": str(target.id),
        "total_findings": len(findings),
        "findings": [
            {
                "id": str(f.id),
                "source": f.source,
                "source_url": f.source_url,
                "raw_value": f.raw_value,
                "category": f.category.value,
                "risk_severity": f.risk_severity,
                "discovered_at": f.discovered_at.isoformat() if f.discovered_at else None,
                "extra_metadata": f.extra_metadata,
            }
            for f in findings
        ],
    }


@router.get("/graph/{value}")
def get_haveibeenpwned_graph(value: str):
    with driver.session() as session:
        graph = get_target_graph(value, session)
    if not graph["nodes"]:
        raise HTTPException(status_code=404, detail=f"No graph data found for '{value}'")
    return graph