from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_patient, get_current_active_practitioner
from app.core.config import settings
from app.core.security import create_qr_share_token
from app.models.summary import ClinicalSummary
from app.models.user import Patient, Practitioner
from app.schemas.clinical import ClinicalSummaryResponse
from app.api.v1.summaries import _format_summary_response

router = APIRouter(prefix="/share", tags=["Compartir / Código QR"])


# Modulo de flujo de intercambio:
# 1. El paciente solicita un token temporal
# 2. El médico escanea el QR y envia dicho token para desbloquear la ficha clínica.


@router.get("/qr/generate")
def generate_qr_token(current_patient: Patient = Depends(get_current_active_patient)):
    token = create_qr_share_token(patient_id=current_patient.user_id)
    return {
        "qr_token": token,
        "expires_in_minutes": settings.QR_TOKEN_EXPIRE_MINUTES,
        "token_type": "Bearer"
    }


@router.post("/qr/scan", response_model=ClinicalSummaryResponse)
def scan_qr_token(
    qr_token: str,
    db: Session = Depends(get_db),
    current_practitioner: Practitioner = Depends(get_current_active_practitioner)
):
    invalid_token_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El código QR es inválido o ha expirado."
    )
    try:
        payload = jwt.decode(qr_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        patient_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if patient_id is None or token_type != "qr_share":
            raise invalid_token_exception
    except JWTError:
        raise invalid_token_exception

    summary = (
        db.query(ClinicalSummary)
        .filter(ClinicalSummary.patient_id == int(patient_id), ClinicalSummary.is_active == True)
        .first()
    )
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El paciente no tiene una Carta Sanitaria activa cargada."
        )

    author_practitioner = db.query(Practitioner).filter(Practitioner.id == summary.practitioner_id).first()
    return _format_summary_response(summary, author_practitioner)