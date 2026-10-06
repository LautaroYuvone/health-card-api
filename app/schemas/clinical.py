from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class CodedConcept(BaseModel):
    """Representación mínima de un concepto codificado (SNOMED-CT, CIE-10, ATC)."""
    system: str = Field(..., examples=["http://snomed.info/sct"])
    code: str = Field(..., examples=["44054006"])
    display: str = Field(..., examples=["Diabetes mellitus tipo 2"])


class AllergyEntry(BaseModel):
    substance: CodedConcept
    criticality: Optional[str] = Field("low", examples=["high"])


class ConditionEntry(BaseModel):
    condition: CodedConcept
    clinical_status: str = Field("active", examples=["active"])


class MedicationEntry(BaseModel):
    medication: CodedConcept
    dosage: str = Field(..., examples=["500 mg"])
    frequency: str = Field(..., examples=["Cada 12 horas"])
    is_chronic: bool = True


class ProcedureEntry(BaseModel):
    procedure: CodedConcept
    performed_date: Optional[date] = None
    notes: Optional[str] = None


class ClinicalSummaryCreate(BaseModel):
    """Payload enviado por el médico al generar o actualizar el resumen."""
    patient_id: int
    allergies: List[AllergyEntry] = []
    conditions: List[ConditionEntry] = []
    medications: List[MedicationEntry] = []
    procedures: List[ProcedureEntry] = []
    blood_type: Optional[str] = Field(None, examples=["0+"])
    emergency_notes: Optional[str] = None


class ClinicalSummaryResponse(ClinicalSummaryCreate):
    id: int
    practitioner_id: int
    practitioner_license: str
    practitioner_name: str
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

