# app/tools/audio_analysis/router.py

import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.db.neo4j import driver
from app.db.postgres import get_db
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.target import Target
from app.services.neo4j_query import get_target_graph
from app.tools.audio_analysis import service, utils

TOOL_ID = "audio_analysis"
router = APIRouter(prefix="/audio_analysis", tags=["audio_analysis"])

AUDIO_UPLOAD_DIR = os.path.join(settings.upload_dir, "audio")
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    label: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    label: the target identifier this audio belongs to (same role as
    'username' for instaloader) - e.g. a person's name or case reference
    you're grouping findings under.
    """
    target = db.query(Target).filter(Target.label == label).first()
    if not target:
        target = Target(label=label)
        db.add(target)
        db.flush()

    scan = Scan(target_id=target.id, tool_used=TOOL_ID, status="pending", progress=0)
    db.add(scan)
    db.commit()
    db.refresh(scan)

    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    original_path = os.path.join(AUDIO_UPLOAD_DIR, f"{scan.id}{ext}")
    wav_path = os.path.join(AUDIO_UPLOAD_DIR, f"{scan.id}.wav")

    with open(original_path, "wb") as f:
        f.write(await file.read())

    try:
        utils.convert_to_wav(original_path, wav_path)
    except Exception as e:
        scan.status = "failed"
        scan.error_message = f"Audio conversion failed: {type(e).__name__}: {e}"
        db.commit()
        raise HTTPException(status_code=400, detail=scan.error_message)

    background_tasks.add_task(
        service.process_audio_job,
        scan.id,
        label,
        original_path,
        wav_path,
    )

    return {
        "scan_id": str(scan.id),
        "target_id": str(target.id),
        "status": scan.status,
    }


@router.get("/status/{scan_id}")
def get_status(scan_id: uuid.UUID, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {
        "scan_id": str(scan.id),
        "status": scan.status,
        "stage": scan.stage,
        "progress": scan.progress,
        "error_message": scan.error_message,
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
    }


@router.get("/profile/{value:path}")
def get_audio_findings(value: str, db: Session = Depends(get_db)):
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


@router.get("/graph/{value:path}")
def get_audio_graph(value: str):
    with driver.session() as session:
        graph = get_target_graph(value, session)
    if not graph["nodes"]:
        raise HTTPException(status_code=404, detail=f"No graph data found for '{value}'")
    return graph