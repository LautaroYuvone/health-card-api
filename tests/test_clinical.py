# Verificamos que solo los médicos certificados (matriculados y registrados) puedan cargar fichas y que las exportaciones cumplan la estructura esperada.

def test_patient_cannot_create_summary(client, auth_patient):
    """Verifica que un paciente no tenga permisos para redactar una Carta Sanitaria (403)."""
    payload = {
        "patient_id": auth_patient["id"],
        "allergies": [],
        "conditions": [],
        "medications": []
    }
    response = client.post(
        "/api/v1/summaries/",
        json=payload,
        headers=auth_patient["headers"]
    )
    assert response.status_code == 403


def test_practitioner_creates_summary_and_patient_retrieves_fhir(
    client, auth_patient, auth_practitioner
):
    """
    Verifica que el médico pueda crear la historia clínica y que el paciente
    pueda consumirla tanto en JSON estándar como en FHIR Bundle IPS.
    """
    summary_payload = {
        "patient_id": auth_patient["id"],
        "allergies": [
            {
                "substance": {"system": "http://snomed.info/sct", "code": "373270004", "display": "Penicilina"},
                "criticality": "high",
                "reaction": "Edema de glotis"
            }
        ],
        "conditions": [
            {
                "condition": {"system": "http://snomed.info/sct", "code": "44054006", "display": "Diabetes mellitus tipo 2"},
                "clinical_status": "active"
            }
        ],
        "medications": [
            {
                "medication": {"system": "http://snomed.info/sct", "code": "372567009", "display": "Metformina"},
                "dosage": "850 mg",
                "frequency": "Cada 12 horas",
                "is_chronic": True
            }
        ],
        "procedures": [],
        "blood_type": "0+"
    }

    # 1. Médico crea la carta
    create_res = client.post(
        "/api/v1/summaries/",
        json=summary_payload,
        headers=auth_practitioner["headers"]
    )
    assert create_res.status_code == 201
    assert create_res.json()["version"] == 1
    assert create_res.json()["practitioner_license"] == "MP-998877"

    # 2. Paciente consulta su resumen activo
    me_res = client.get("/api/v1/summaries/me", headers=auth_patient["headers"])
    assert me_res.status_code == 200
    assert me_res.json()["blood_type"] == "0+"

    # 3. Paciente consulta el bundle interoperable FHIR IPS
    fhir_res = client.get("/api/v1/summaries/me/fhir", headers=auth_patient["headers"])
    assert fhir_res.status_code == 200
    bundle = fhir_res.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "document"
    assert bundle["entry"][0]["resource"]["resourceType"] == "Composition"


def test_download_summary_pdf(client, auth_patient, auth_practitioner):
    """Verifica que el endpoint de PDF retorne el binario correspondiente."""
    # Crear resumen mínimo primero
    client.post(
        "/api/v1/summaries/",
        json={"patient_id": auth_patient["id"], "allergies": [], "conditions": [], "medications": []},
        headers=auth_practitioner["headers"]
    )

    pdf_res = client.get("/api/v1/summaries/me/pdf", headers=auth_patient["headers"])
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")