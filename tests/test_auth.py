# Verificamos registrtos duplicados y validación de credenciales.

def test_register_duplicate_patient_email(client):
    payload = {
        "email": "duplicado@test.com",
        "first_name": "Carlos",
        "last_name": "Gómez",
        "national_id": "11111111",
        "password": "password123"
    }
    res1 = client.post("/api/v1/auth/register/patient", json=payload)
    assert res1.status_code == 201

    payload["national_id"] = "22222222"
    res2 = client.post("/api/v1/auth/register/patient", json=payload)
    assert res2.status_code == 400
    assert "correo ya está registrado" in res2.json()["detail"]


def test_login_invalid_password(client, auth_patient):
    res = client.post(
        "/api/v1/auth/login",
        data={"username": auth_patient["email"], "password": "wrong_password"}
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Credenciales inválidas."