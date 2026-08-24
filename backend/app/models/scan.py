import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.postgres import Base


class Scan(Base):
    __tablename__ = "scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id = Column(UUID(as_uuid=True), ForeignKey("targets.id"), nullable=False)
    investigation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    tool_used = Column(String, nullable=False, default="sherlock")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # --- job/progress tracking (added for audio_analysis, reusable by video_analysis) ---
    # NOTE: existing sync tools (exif_extractor, instaloader, etc.) never set these -
    # they'll just sit at the defaults below ("pending", progress=0) forever since those
    # tools store the finding synchronously and never touch status. That's harmless (nothing
    # reads status for those tools) but flagging it so it's not surprising later.
    status = Column(String, nullable=False, default="pending")   # pending | running | done | failed
    stage = Column(String, nullable=True)                        # e.g. "transcribing", "tagging_sounds"
    progress = Column(Integer, nullable=False, default=0)        # 0-100, reflects real work done only
    error_message = Column(String, nullable=True)

