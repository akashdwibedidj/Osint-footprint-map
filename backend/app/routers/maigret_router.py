from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.services.maigret_service import run_maigret_async
from app.services.scan_storage import store_maigret_findings
from app.services.neo4j_storage import store_maigret_graph
from app.services.neo4j_query import get_target_graph
from app.db.postgres import get_db
from app.db.neo4j import driver
from app.models.target import Target
from app.models.finding import Finding
from app.models.scan import Scan

router = APIRouter(prefix="/maigret", tags=["maigret"])


@router.post("/username/{username}")
async def scan_maigret_username(username: str, db: Session = Depends(get_db)):
    try:
        findings = await run_maigret_async(username)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Maigret scan failed: {e}")

    try:
        storage_result = store_maigret_findings(username, findings, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Postgres storage failed: {e}")

    try:
        with driver.session() as session:
            store_maigret_graph(username, findings, session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j storage failed: {e}")

    return {
        "username": username,
        "findings_count": len(findings),
        **storage_result,
    }


@router.get("/username/{username}")
def get_maigret_findings(username: str, db: Session = Depends(get_db)):
    target = db.query(Target).filter(Target.label == username).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"No scans found for '{username}'")

    findings = (
        db.query(Finding)
        .join(Scan)
        .filter(Finding.target_id == target.id, Scan.tool_used == "maigret")
        .all()
    )

    return {
        "username": username,
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


@router.get("/graph/{username}")
def get_maigret_graph(username: str):
    with driver.session() as session:
        graph = get_target_graph(username, session)

    if not graph["nodes"]:
        raise HTTPException(status_code=404, detail=f"No graph data found for '{username}'")

    return graph