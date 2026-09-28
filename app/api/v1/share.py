import io
from fastapi import APIRouter, Depends, HTTPException, status, Response
from jose import JWTError, jwt
import qrcode
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
    """Devuelve el token efímero en formato JSON/texto."""
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
    """
    Genera el token efímero y lo compila en una imagen PNG en memoria.
    El frontend móvil o web puede usar este endpoint directamente como src de un <img>.
    """
    token = create_qr_share_token(patient_id=current_patient.user_id)

    # Configuración del código QR
    qr = qrcode.QRCode(
        version=None,  # Ajusta automáticamente el tamaño según la longitud del JWT
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(token)
    qr.make(fit=True)

    # Renderizar imagen en blanco y negro
    img = qr.make_image(fill_color="black", back_color="white")

    # Guardar en un buffer de memoria sin escribir en disco
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(content=buf.getvalue(), media_type="image/png")


@router.post("/qr/scan", response_model=ClinicalSummaryResponse)
def scan_qr_token(
    qr_token: str,
    db: Session = Depends(get_db),
    current_practitioner: Practitioner = Depends(get_current_active_practitioner)
):
    """El profesional de salud escanea el QR y desbloquea el resumen activo."""
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