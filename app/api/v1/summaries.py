from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_practitioner, get_current_active_patient
from app.models.summary import ClinicalSummary
from app.models.user import Practitioner, Patient, User
from app.schemas.clinical import ClinicalSummaryCreate, ClinicalSummaryResponse

from app.schemas.fhir import create_fhir_ips_bundle

router = APIRouter(prefix="/summaries", tags=["Carta Sanitaria"])


def _format_summary_response(summary: ClinicalSummary, practitioner: Practitioner) -> ClinicalSummaryResponse:
    prac_user = practitioner.user
    data = summary.clinical_data.copy()
    return ClinicalSummaryResponse(
        id=summary.id,
        patient_id=summary.patient_id,
        practitioner_id=practitioner.id,
        practitioner_license=practitioner.license_number,
        practitioner_name=f"{prac_user.first_name} {prac_user.last_name}",
        version=summary.version,
        created_at=summary.created_at,
        **data
    )


@router.post("/", response_model=ClinicalSummaryResponse, status_code=status.HTTP_201_CREATED)
def save_clinical_summary(
    payload: ClinicalSummaryCreate,
    db: Session = Depends(get_db),
    current_practitioner: Practitioner = Depends(get_current_active_practitioner)
):
    patient_user = db.query(User).filter(User.id == payload.patient_id).first()
    if not patient_user:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")

    previous_summary = (
        db.query(ClinicalSummary)
        .filter(ClinicalSummary.patient_id == payload.patient_id, ClinicalSummary.is_active == True)
        .first()
    )

    new_version = 1
    if previous_summary:
        previous_summary.is_active = False
        new_version = previous_summary.version + 1

    clinical_payload = payload.model_dump(exclude={"patient_id"}, mode="json")

    new_summary = ClinicalSummary(
        patient_id=payload.patient_id,
        practitioner_id=current_practitioner.id,
        version=new_version,
        is_active=True,
        clinical_data=clinical_payload
    )
    db.add(new_summary)
    db.commit()
    db.refresh(new_summary)

    return _format_summary_response(new_summary, current_practitioner)


@router.get("/me", response_model=ClinicalSummaryResponse)
def get_my_summary(
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_active_patient)
):
    summary = (
        db.query(ClinicalSummary)
        .filter(ClinicalSummary.patient_id == current_patient.user_id, ClinicalSummary.is_active == True)
        .first()
    )
    if not summary:
        raise HTTPException(status_code=404, detail="Aún no tienes una Carta Sanitaria generada.")

    practitioner = db.query(Practitioner).filter(Practitioner.id == summary.practitioner_id).first()
    return _format_summary_response(summary, practitioner)


@router.get("/me/fhir", tags=["Interoperabilidad FHIR IPS"])
def get_my_summary_fhir(
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_active_patient)
):
    """
    Retorna la Carta Sanitaria activa del paciente en formato
    HL7 FHIR Document Bundle (IPS - International Patient Summary).
    """
    summary = (
        db.query(ClinicalSummary)
        .filter(ClinicalSummary.patient_id == current_patient.user_id, ClinicalSummary.is_active == True)
        .first()
    )
    if not summary:
        raise HTTPException(status_code=404, detail="No se encontró una Carta Sanitaria activa.")

    practitioner = db.query(Practitioner).filter(Practitioner.id == summary.practitioner_id).first()
    patient_user = current_patient.user

    return create_fhir_ips_bundle(
        summary=summary,
        patient_user=patient_user,
        practitioner=practitioner
    )