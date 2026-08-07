import enum
import uuid
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Enum, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.postgres import Base


class ExposureCategory(str, enum.Enum):
    PERSONAL_IDENTIFIER = "personal_identifier"
    CONTACT_DETAIL = "contact_detail"
    CREDENTIAL = "credential"
    BEHAVIORAL_PATTERN = "behavioral_pattern"
    ORGANIZATIONAL_LINK = "organizational_link"


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("target_id", "content_hash", name="uq_target_content_hash"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id = Column(UUID(as_uuid=True), ForeignKey("targets.id"), nullable=False)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)

    source = Column(String, nullable=False)
    source_url = Column(String, nullable=False)
    raw_value = Column(String, nullable=False)

    category = Column(Enum(ExposureCategory), nullable=False, default=ExposureCategory.PERSONAL_IDENTIFIER)
    content_hash = Column(String, nullable=False, index=True)   # NEW

    sensitivity_score = Column(Integer, default=1)
    correlation_score = Column(Integer, default=1)
    exploitability_score = Column(Integer, default=1)
    recency_score = Column(Integer, default=1)
    risk_severity = Column(String, default="low")

    http_status = Column(Integer, nullable=True)
    response_time_s = Column(Float, nullable=True)

    extra_metadata = Column(JSON, nullable=True)

    discovered_at = Column(DateTime(timezone=True), server_default=func.now())