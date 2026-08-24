import enum
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.postgres import Base


class ClassificationLog(Base):
    __tablename__ = "classification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    input_description = Column(String, nullable=False)
    suggested_tools = Column(JSON, nullable=False)  # list[str]
    confidence = Column(Float, nullable=True)

    feedback = Column(Boolean, nullable=True)  # True=good, False=bad, None=unreviewed
    created_at = Column(DateTime(timezone=True), server_default=func.now())