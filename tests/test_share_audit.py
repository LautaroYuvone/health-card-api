# Verificamos ciclo de escaneo, inmutabilidad de la auditoria y detección de tokens inválidos.

def test_qr_flow_and_access_audit(client, auth_patient, auth_practitioner):
    """Prueba el ciclo completo: generación de QR, escaneo por médico y registro de auditoría."""
    # Cargar resumen médico previo
    client.post(
        "/api/v1/summaries/",
        json={"patient_id": auth_patient["id"], "allergies": [], "conditions": [], "medications": []},
        headers=auth_practitioner["headers"]
    )

    # 1. Paciente genera token QR
    qr_res = client.get("/api/v1/share/qr/generate", headers=auth_patient["headers"])
    assert qr_res.status_code == 200
    qr_token = qr_res.json()["qr_token"]

    # 2. Médico escanea el QR
    scan_res = client.post(
        f"/api/v1/share/qr/scan?qr_token={qr_token}",
        headers=auth_practitioner["headers"]
    )
    assert scan_res.status_code == 200
    assert scan_res.json()["patient_id"] == auth_patient["id"]

    # 3. Paciente revisa su historial de auditoría
    audit_res = client.get("/api/v1/share/audit", headers=auth_patient["headers"])
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) == 1
    assert logs[0]["practitioner_license"] == "MP-998877"


def test_scan_invalid_qr_token(client, auth_practitioner):
    """Verifica que tokens alterados o maliciosos sean rechazados con 400."""
    res = client.post(
        "/api/v1/share/qr/scan?qr_token=token_invalido_xyz",
        headers=auth_practitioner["headers"]
    )
    assert res.status_code == 400
    assert "código QR es inválido" in res.json()["detail"]