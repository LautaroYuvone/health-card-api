from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class ClinicalSummary(Base):
    __tablename__ = "clinical_summaries"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    practitioner_id = Column(Integer, ForeignKey("practitioners.id"), nullable=False)

    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, index=True)

    clinical_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    patient = relationship("User", foreign_keys=[patient_id])
    practitioner = relationship("Practitioner", foreign_keys=[practitioner_id])
