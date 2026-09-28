from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User, UserRole, Practitioner, Patient
from app.schemas.user import PatientCreate, PractitionerCreate, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["Autenticación"]) # Centraliza los "endpoints" bajo el prefijo "/auth"


# Implementamos flujo de registro diferenciado para asegurar que cada usuario tenga su perfil correspondiente ("Doctor" con matrícula o "Patient"), junto con el login estándar compatible con el formulario interactivo de Swagger UI (OAuth2PasswordRequestForm)


@router.post("/register/patient", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_patient(patient_in: PatientCreate, db: Session = Depends(get_db)):
    """Registra un nuevo usuario con rol de Paciente."""
    if db.query(User).filter(User.email == patient_in.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    if db.query(User).filter(User.national_id == patient_in.national_id).first():
        raise HTTPException(status_code=400, detail="El documento nacional ya está registrado.")

    new_user = User(
        email=patient_in.email,
        hashed_password=get_password_hash(patient_in.password),
        first_name=patient_in.first_name,
        last_name=patient_in.last_name,
        national_id=patient_in.national_id,
        phone=patient_in.phone,
        role=UserRole.PATIENT,
    )
    db.add(new_user)
    db.flush()  # Obtiene el new_user.id antes de confirmar la transacción

    new_patient = Patient(
        user_id=new_user.id,
        blood_type=patient_in.blood_type,
        emergency_contact_name=patient_in.emergency_contact_name,
        emergency_contact_phone=patient_in.emergency_contact_phone,
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/register/practitioner", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_practitioner(practitioner_in: PractitionerCreate, db: Session = Depends(get_db)):
    """Registra un nuevo profesional de salud con su matrícula."""
    if db.query(User).filter(User.email == practitioner_in.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    if db.query(Practitioner).filter(Practitioner.license_number == practitioner_in.license_number).first():
        raise HTTPException(status_code=400, detail="La matrícula ya se encuentra registrada.")

    new_user = User(
        email=practitioner_in.email,
        hashed_password=get_password_hash(practitioner_in.password),
        first_name=practitioner_in.first_name,
        last_name=practitioner_in.last_name,
        national_id=practitioner_in.national_id,
        phone=practitioner_in.phone,
        role=UserRole.PRACTITIONER,
    )
    db.add(new_user)
    db.flush()

    new_practitioner = Practitioner(
        user_id=new_user.id,
        license_number=practitioner_in.license_number,
        specialty=practitioner_in.specialty,
        is_verified=False,
    )
    db.add(new_practitioner)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Inicio de sesión unificado. Utiliza email en el campo 'username'."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo.")

    access_token = create_access_token(subject=user.id, role=user.role.value)
    return {"access_token": access_token, "token_type": "bearer"}