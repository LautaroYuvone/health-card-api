from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User, UserRole, Practitioner, Patient
from app.schemas.user import TokenPayload

# Este módulo se encarga de:
# 1. Abrir y cerrar sesión e la base de datos por cada solicitud (get_db)
# 2. Extraer y verificar el token JWT de la cabecera --> Authorization: Bearer <Token>
# 3. Inyectar el usuario autenticado
# 4. Verificar roles: requerir estricamente rol DOCTOR (para crear/modificar historias clínicas o escanear QRs) o PATIENT (para emitir su propio QR)


# Endpoint donde FastAPI buscará el formulario de login OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_db() -> Generator[Session, None, None]:
    """Generador de sesión de base de datos relacional."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Valida el token de acceso e inyecta el usuario autenticado."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales de autenticación.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        # Evitar usar tokens de QR como si fuesen de sesión
        if user_id is None or token_type != "access":
            raise credentials_exception

        token_data = TokenPayload(sub=user_id, role=payload.get("role"), type=token_type)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verifica que la cuenta de usuario esté activa."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo en el sistema."
        )
    return current_user


def get_current_active_practitioner(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Practitioner:
    """
    Exige que el usuario actual sea un médico activo.
    Retorna directamente la entidad Doctor asociada.
    """
    if current_user.role != UserRole.PRACTITIONER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: se requieren permisos de profesional de la salud."
        )

    practitioner = db.query(Practitioner).filter(Practitioner.user_id == current_user.id).first()
    if not practitioner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil profesional no encontrado."
        )
    return practitioner


def get_current_active_patient(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Patient:
    """
    Exige que el usuario actual sea un paciente activo.
    Retorna directamente la entidad Patient asociada.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: se requiere perfil de paciente."
        )

    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de paciente no encontrado."
        )
    return patient