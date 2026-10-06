from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


# Modelo de base de datos que registra al profesional interviniente, la fecha/hora exacta, matrícula, IP y el user-agent.

class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    practitioner_id = Column(Integer, ForeignKey("practitioners.id"), nullable=False, index=True)
    summary_id = Column(Integer, ForeignKey("clinical_summaries.id"), nullable=True)

    accessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Relaciones
    patient = relationship("User", foreign_keys=[patient_id])
    practitioner = relationship("Practitioner", foreign_keys=[practitioner_id])
    summary = relationship("ClinicalSummary", foreign_keys=[summary_id])