from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.scan import Scan
from app.services.sherlock_service import sherlock_service
from app.services.scan_storage import store_sherlock_results
from app.services.neo4j_storage import store_sherlock_graph
from app.services.neo4j_query import get_target_graph
from app.db.postgres import get_db
from app.db.neo4j import driver
from app.models.target import Target
from app.models.finding import Finding

router = APIRouter(tags=["sherlock"])

@router.post("/username/{username}")
async def scan_username(username: str, db: Session = Depends(get_db)):
    try:
        result = await sherlock_service.search_username(username)
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))

    try:
        postgres_result = store_sherlock_results(username, result, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Postgres storage failed: {e}")

    try:
        with driver.session() as session:
            neo4j_result = store_sherlock_graph(username, result, session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j storage failed: {e}")

    return {
        "username": username,
        "total_found": result["total_found"],
        "postgres": postgres_result,
        "neo4j": neo4j_result,
    }



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
@router.get("/username/{username}")
def get_username_findings(username: str, db: Session = Depends(get_db)):
    """
    Fetch previously stored findings for a target WITHOUT re-scanning.
    """
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
    """
    Returns the footprint graph (nodes + edges) for a target,
    ready for frontend visualization.
    """
    with driver.session() as session:
        graph = get_target_graph(username, session)

    if not graph["nodes"]:
        raise HTTPException(status_code=404, detail=f"No graph data found for '{username}'")

    return graph