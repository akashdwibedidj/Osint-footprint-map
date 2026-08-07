from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.neo4j import driver
from app.db.postgres import get_db
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.target import Target
from app.services import storage
from app.services.neo4j_query import get_target_graph
from app.tools.exif_extractor import service

TOOL_ID = "exif_extractor"
router = APIRouter(prefix="/exif_extractor", tags=["exif_extractor"])


@router.post("/image_url/{value:path}")
async def scan_exif_extractor(value: str, db: Session = Depends(get_db)):
    findings = await service.run(value)
    pg_result = storage.store_findings(TOOL_ID, value, findings, db)
    with driver.session() as session:
        storage.store_graph(
            tool_id=TOOL_ID,
            target_label=value,
            findings=findings,
            session=session,
            identifier_type="image_url",
        )
    return {"value": value, "findings_count": len(findings), **pg_result}


@router.post("/upload")
async def scan_exif_extractor_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    image_bytes = await file.read()
    value = file.filename or "uploaded_image"

    findings = await service.run(value, image_bytes=image_bytes)
    pg_result = storage.store_findings(TOOL_ID, value, findings, db)
    with driver.session() as session:
        storage.store_graph(
            tool_id=TOOL_ID,
            target_label=value,
            findings=findings,
            session=session,
            identifier_type="image_filename",
        )
    return {"value": value, "findings_count": len(findings), **pg_result}


@router.get("/image_url/{value:path}")
def get_exif_extractor_findings(value: str, db: Session = Depends(get_db)):
    target = db.query(Target).filter(Target.value == value).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    scans = (
        db.query(Scan)
        .filter(Scan.target_id == target.id, Scan.tool_used == TOOL_ID)
        .all()
    )
    if not scans:
        raise HTTPException(status_code=404, detail="No exif_extractor scans found for this target")

    scan_ids = [scan.id for scan in scans]
    findings = db.query(Finding).filter(Finding.scan_id.in_(scan_ids)).all()

    return {"value": value, "findings_count": len(findings), "findings": findings}


@router.get("/graph/{value:path}")
def get_exif_extractor_graph(value: str):
    with driver.session() as session:
        graph = get_target_graph(value, session)   # swapped order
    return graph