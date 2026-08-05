from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.neo4j import driver
from app.db.postgres import get_db
from app.models.finding import Finding
from app.models.target import Target
from app.services import storage
from app.services.neo4j_query import get_target_graph
from app.tools.sherlock import service

TOOL_ID = "sherlock"

# Prefix kept as "/scan" (no /sherlock) to preserve existing frontend URLs.
router = APIRouter(prefix="/scan", tags=["sherlock"])


@router.post("/username/{username}")
async def scan_username(username: str, db: Session = Depends(get_db)):
    try:
        findings = await service.run(username)
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        pg_result = storage.store_findings(TOOL_ID, username, findings, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Postgres storage failed: {e}")

    try:
        with driver.session() as session:
            neo4j_result = storage.store_graph(TOOL_ID, username, findings, session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j storage failed: {e}")

    return {
        "username": username,
        "total_found": len(findings),
        "postgres": pg_result,
        "neo4j": neo4j_result,
    }


@router.get("/username/{username}")
def get_username_findings(username: str, db: Session = Depends(get_db)):
    """Fetch previously stored findings for a target WITHOUT re-scanning."""
    target = db.query(Target).filter(Target.label == username).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"No scans found for '{username}'")

    findings = db.query(Finding).filter(Finding.target_id == target.id).all()

    return {
        "username": username,
        "target_id": str(target.id),
        "total_findings": len(findings),
        "findings": [
            {
                "source": f.source,
                "source_url": f.source_url,
                "category": f.category.value,
                "risk_severity": f.risk_severity,
                "discovered_at": f.discovered_at.isoformat() if f.discovered_at else None,
            }
            for f in findings
        ],
    }


@router.get("/graph/{username}")
def get_graph(username: str):
    with driver.session() as session:
        graph = get_target_graph(username, session)
    if not graph["nodes"]:
        raise HTTPException(status_code=404, detail=f"No graph data found for '{username}'")
    return graph
