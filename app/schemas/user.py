from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    type: Optional[str] = None


class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    national_id: str = Field(..., description="DNI o documento nacional")
    phone: Optional[str] = None


class PatientCreate(UserBase):
    password: str = Field(..., min_length=6)
    blood_type: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class PractitionerCreate(UserBase):
    password: str = Field(..., min_length=6)
    license_number: str = Field(..., description="Matrícula profesional")
    specialty: Optional[str] = Field(None, examples=["Clínica Médica"])


class PractitionerProfileResponse(BaseModel):
    id: int
    license_number: str
    specialty: Optional[str]
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


class PatientProfileResponse(BaseModel):
    id: int
    blood_type: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    practitioner_profile: Optional[PractitionerProfileResponse] = None
    patient_profile: Optional[PatientProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)