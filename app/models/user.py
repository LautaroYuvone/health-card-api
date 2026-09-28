from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    PRACTITIONER = "practitioner"
    PATIENT = "patient"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    national_id = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.PATIENT)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    practitioner_profile = relationship("Practitioner", back_populates="user", uselist=False)
    patient_profile = relationship("Patient", back_populates="user", uselist=False)


class Practitioner(Base):
    __tablename__ = "practitioners"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    license_number = Column(String, unique=True, index=True, nullable=False)
    specialty = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)

    user = relationship("User", back_populates="practitioner_profile")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    blood_type = Column(String, nullable=True)
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)

    user = relationship("User", back_populates="patient_profile")