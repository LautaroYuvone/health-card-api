import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app

# Configuramos el motor de base de datos en memoria con "StaticPool", sobreeescribimos dependencia (get_db) y generamos fixtures con clientes y tokens ya autenticados para agilizar las pruebas.

# Base de datos SQLite volátil en memoria para testing aislado
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Crea una base de datos limpia para cada test y la destruye al finalizar."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Cliente HTTP de pruebas con la dependencia get_db sobreescrita."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_patient(client):
    """Registra y loguea un paciente de prueba, retornando sus headers y datos."""
    patient_data = {
        "email": "test_patient@hospital.com",
        "first_name": "Juan",
        "last_name": "Pérez",
        "national_id": "35123456",
        "phone": "3415551234",
        "password": "secret_password",
        "blood_type": "0+",
        "emergency_contact_name": "María Pérez",
        "emergency_contact_phone": "3415555678"
    }
    client.post("/api/v1/auth/register/patient", json=patient_data)

    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": patient_data["email"], "password": patient_data["password"]}
    )
    token = login_res.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "id": 1,
        "email": patient_data["email"]
    }


@pytest.fixture
def auth_practitioner(client):
    """Registra y loguea un profesional médico de prueba, retornando sus headers y datos."""
    doc_data = {
        "email": "test_doctor@hospital.com",
        "first_name": "Lautaro",
        "last_name": "Médico",
        "national_id": "32987654",
        "phone": "3415559999",
        "password": "secret_password",
        "license_number": "MP-998877",
        "specialty": "Clínica Médica"
    }
    client.post("/api/v1/auth/register/practitioner", json=doc_data)

    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": doc_data["email"], "password": doc_data["password"]}
    )
    token = login_res.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "id": 1,
        "email": doc_data["email"]
    }