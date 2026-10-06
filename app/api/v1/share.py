import io
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError, jwt
import qrcode
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_patient, get_current_active_practitioner
from app.api.v1.summaries import _format_summary_response
from app.core.config import settings
from app.core.security import create_qr_share_token
from app.models.audit import AccessLog
from app.models.summary import ClinicalSummary
from app.models.user import Patient, Practitioner
from app.schemas.audit import AccessLogResponse
from app.schemas.clinical import ClinicalSummaryResponse


router = APIRouter(prefix="/share", tags=["Compartir y Auditoría"])


# Modulo de flujo de intercambio:
# 1. El paciente solicita un token temporal
# 2. El médico escanea el QR y envia dicho token para desbloquear la ficha clínica.


@router.get("/qr/generate")
def generate_qr_token(current_patient: Patient = Depends(get_current_active_patient)):
    """El paciente genera su token efímero firmado."""
    token = create_qr_share_token(patient_id=current_patient.user_id)
    return {
        "qr_token": token,
        "expires_in_minutes": settings.QR_TOKEN_EXPIRE_MINUTES,
        "token_type": "Bearer"
    }


@router.get(
    "/qr/image",
    summary="Descargar / Visualizar QR en PNG",
    response_class=Response,
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "Retorna la imagen del código QR renderizada en PNG."
        }
    }
)
def generate_qr_image(current_patient: Patient = Depends(get_current_active_patient)):
    """Genera y compila el código QR en una imagen PNG en memoria."""
    token = create_qr_share_token(patient_id=current_patient.user_id)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(token)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(content=buf.getvalue(), media_type="image/png")


@router.post("/qr/scan", response_model=ClinicalSummaryResponse)
def scan_qr_token(
    qr_token: str,
    request: Request,
    db: Session = Depends(get_db),
    current_practitioner: Practitioner = Depends(get_current_active_practitioner)
):
    """
    El profesional escanea el QR y desbloquea el resumen activo.
    Registra automáticamente una entrada de auditoría inmutable (AccessLog).
    """
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

    # Buscar el resumen activo del paciente
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


    # ------ REGISTRO DE AUDITORÍA ------
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    log_entry = AccessLog(
        patient_id=int(patient_id),
        practitioner_id=current_practitioner.id,
        summary_id=summary.id,
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(log_entry)
    db.commit()

    author_practitioner = db.query(Practitioner).filter(Practitioner.id == summary.practitioner_id).first()
    return _format_summary_response(summary, author_practitioner)


@router.get("/audit", response_model=List[AccessLogResponse])
def get_my_access_history(
    db: Session = Depends(get_db),
    current_patient: Patient = Depends(get_current_active_patient)
):
    """
    Permite al paciente consultar el historial completo de accesos a su Carta Sanitaria.
    Informa qué profesional accedió, su matrícula, especialidad y la marca temporal.
    """
    logs = (
        db.query(AccessLog)
        .filter(AccessLog.patient_id == current_patient.user_id)
        .order_by(AccessLog.accessed_at.desc())
        .all()
    )

    result = []
    for log in logs:
        prac = log.practitioner
        prac_user = prac.user
        result.append(
            AccessLogResponse(
                id=log.id,
                practitioner_name=f"{prac_user.first_name} {prac_user.last_name}",
                practitioner_license=prac.license_number,
                practitioner_specialty=prac.specialty,
                accessed_at=log.accessed_at,
                ip_address=log.ip_address
            )
        )

    return result