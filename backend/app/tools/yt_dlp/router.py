# app/tools/yt_dlp/router.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.neo4j import driver
from app.db.postgres import get_db
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.target import Target
from app.services import storage
from app.services.neo4j_query import get_target_graph
from app.tools.yt_dlp import service

TOOL_ID = "yt_dlp"
router = APIRouter(prefix="/yt_dlp", tags=["yt_dlp"])


class DownloadRequest(BaseModel):
    urls: list[str]


def _run_and_store(scan_id: str, value: str, urls: list[str]):
    # runs in background; needs its own DB session since it's outside the request scope
    from app.db.postgres import SessionLocal
    import asyncio

    db = SessionLocal()
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    try:
        scan.status = "running"
        db.commit()

        findings = asyncio.run(service.run(value, urls))

        storage.store_findings(TOOL_ID, value, findings, db)
        with driver.session() as session:
            storage.store_graph(
                tool_id=TOOL_ID,
                target_label=value,
                findings=findings,
                session=session,
                identifier_type="username",
            )

        scan.status = "done"
        scan.finished_at = __import__("datetime").datetime.utcnow()
        db.commit()
    except Exception as e:
        scan.status = "failed"
        scan.error_message = str(e)
        db.commit()
    finally:
        db.close()


@router.post("/download/{value:path}")
def start_download(value: str, body: DownloadRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    target = db.query(Target).filter(Target.label == value).first()
    if not target:
        target = Target(label=value)
        db.add(target)
        db.commit()
        db.refresh(target)

    scan = Scan(target_id=target.id, tool_used=TOOL_ID, status="pending")
    db.add(scan)
    db.commit()
    db.refresh(scan)

    background_tasks.add_task(_run_and_store, str(scan.id), value, body.urls)

    return {"scan_id": str(scan.id), "status": scan.status}


@router.get("/status/{scan_id}")
def get_status(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {
        "scan_id": str(scan.id),
        "status": scan.status,
        "error_message": scan.error_message,
    }


@router.get("/profile/{value:path}")
def get_yt_dlp_findings(value: str, db: Session = Depends(get_db)):
    target = db.query(Target).filter(Target.label == value).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"No downloads found for '{value}'")

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
                "extra_metadata": f.extra_metadata,
            }
            for f in findings
        ],
    }


@router.get("/graph/{value:path}")
def get_yt_dlp_graph(value: str):
    with driver.session() as session:
        graph = get_target_graph(value, session)
    if not graph["nodes"]:
        raise HTTPException(status_code=404, detail=f"No graph data found for '{value}'")
    return graph