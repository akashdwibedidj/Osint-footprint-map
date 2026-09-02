"""
Single intake endpoint for mixed-input investigations. Accepts files
(any mix of audio/video/image, one call can include several) plus a
target label, saves files to disk, dispatches matching tools via Celery,
and returns immediately with investigation_id. Frontend polls
/orchestrator/status/{investigation_id} to list all scans spawned by
this run and their individual progress.
"""

import os
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.datastructures import UploadFile as StarletteUploadFile

from app.config import settings
from app.db.postgres import get_db
from app.models.scan import Scan
from app.orchestrator.dispatcher import InvestigationInput, dispatch_investigation
from fastapi import APIRouter, Depends, Request
from fastapi.datastructures import UploadFile as StarletteUploadFil

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

UPLOAD_DIR = os.path.join(settings.upload_dir, "orchestrator")
os.makedirs(UPLOAD_DIR, exist_ok=True)

EXTENSION_TYPE_MAP = {
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".ogg": "audio",
    ".mp4": "video", ".mov": "video", ".mkv": "video", ".avi": "video",
    ".jpg": "image", ".jpeg": "image", ".png": "image", ".webp": "image",
}


def _detect_type(filename: str) -> str | None:
    ext = os.path.splitext(filename)[1].lower()
    return EXTENSION_TYPE_MAP.get(ext)


@router.post("/investigate")
async def investigate(
    request: Request,
    label: str = Form(...),
    usernames: list[str] = Form(default=[]),
    repo_urls: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    import uuid
    from app.orchestrator.graph import investigation_graph

    form = await request.form()
    raw_files = form.getlist("files")
    files = [f for f in raw_files if isinstance(f, StarletteUploadFile) and f.filename]

    investigation_id = str(uuid.uuid4())
    inputs = []

    for file in files:
        ext = os.path.splitext(file.filename or "")[1]
        saved_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
        with open(saved_path, "wb") as f:
            f.write(await file.read())

        inputs.append({"file_path": saved_path, "raw_text": None, "input_type": None})

    for username in usernames:
        if username.strip():
            inputs.append({"file_path": None, "raw_text": username.strip().lstrip("@"), "input_type": "username"})

    for repo_url in repo_urls:
        if repo_url.strip():
            inputs.append({"file_path": None, "raw_text": repo_url.strip(), "input_type": "repo_url"})

    result_state = investigation_graph.invoke({
        "investigation_id": investigation_id,
        "target_label": label,
        "inputs": inputs,
        "dispatched": [],
    })

    return {
        "investigation_id": investigation_id,
        "target_label": label,
        "dispatched": result_state["dispatched"],
    }


@router.get("/status/{investigation_id}")
def investigation_status(investigation_id: uuid.UUID, db: Session = Depends(get_db)):
    scans = db.query(Scan).filter(Scan.investigation_id == investigation_id).all()
    return {
        "investigation_id": str(investigation_id),
        "tools": [
            {
                "scan_id": str(s.id),
                "tool_used": s.tool_used,
                "status": s.status,
                "stage": s.stage,
                "progress": s.progress,
                "error_message": s.error_message,
            }
            for s in scans
        ],
    }