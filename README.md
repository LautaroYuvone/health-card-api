# Sanitary Card API (Tarjeta Sanitaria Digital)

Backend para la emisión, gestión y consulta interoperable de resúmenes clínicos (Tarjeta Sanitaria), diseñado bajo estándares internacionales de informática médica (**HL7 FHIR R4** e **IPS**) y terminologías clínicas controladas (**SNOMED-CT**, **LOINC**).

---

##  Problemática Clínica

En la medicina asistencial (tanto en guardias como en consultas programadas), la anamnesis es el pilar diagnóstico fundamental. Sin embargo, los pacientes suelen desconocer detalles críticos de su propio perfil sanitario (fármacos y dosis exactas, patologías de base, antecedentes quirúrgicos o alergias a drogas). 

Esta fragmentación de la información genera:
* Pérdida de minutos valiosos durante el interrogatorio inicial.
* Omisiones diagnósticas y riesgo de interacciones farmacológicas adversas.
* Dependencia de sistemas de historias clínicas cerrados (*silos de datos*) no interconectados.

---

## 💡 Solución

Una API REST orientada al **empoderamiento del paciente** y la **certificación profesional**:
1. **Certificación Médica:** Solo profesionales matriculados pueden emitir o actualizar la tarjeta sanitaria, sellando cada versión con su matrícula profesional.
2. **Versionado Inmutable:** Cada actualización desactiva la versión anterior y crea una nueva, preservando la trazabilidad y la validez médico-legal.
3. **Compartición Segura vía QR:** El paciente genera un token criptográfico efímero (15 minutos). La historia solo puede ser descifrada y visualizada por médicos autenticados en el sistema.
4. **Interoperabilidad Nativa:** Capacidad de exportar el resumen clínico completo en formato estándar **FHIR International Patient Summary (IPS)**.
5. **Auditoría Clínica Estricta (*Audit Trail*):** Registro inmutable de auditoría para cada lectura o escaneo de la tarjeta sanitaria (médico actuante, matrícula, marca temporal y paciente consultado), garantizando el cumplimiento de secreto profesional y normativas de datos de salud.
6. **Exportación Multiformato (Digital & PDF):** Generación dinámica de la Carta Sanitaria en formato PDF, estructurada con tipografía médica y código QR embebido para continuidad asistencial en entornos desconectados o soporte físico.

---

## 🩺 Estándares de Informática Médica Adoptados

* **HL7 FHIR R4 (Perfil IPS - International Patient Summary):**
  * Exportación del resumen como un `Bundle` de tipo `document`.
  * Cabecera e indexación clínica estructurada mediante el recurso `Composition` (código LOINC `60591-5`).
  * Recursos clínicos normalizados: `Patient`, `Practitioner`, `Condition`, `AllergyIntolerance` y `MedicationStatement`.
* **Terminologías Clínicas Codificadas:**
  * **SNOMED-CT:** Codificación de conceptos para diagnósticos, patologías activas, sustancias alergénicas y fármacos.
  * **LOINC:** Identificación unívoca de documentos clínicos y secciones médicas.
  * **CIE-10:** Mapeo de compatibilidad para diagnósticos internacionales.

---

## 🛠️ Stack Tecnológico & Arquitectura

* **Framework:** FastAPI (Python 3.10+) con tipado estricto y contratos validados mediante **Pydantic v2**.
* **Base de Datos:** PostgreSQL con arquitectura híbrida:
  * Modelado relacional para usuarios, roles y auditoría de versiones.
  * Columnas **JSONB** indexables para esquemas clínicos flexibles y consultas rápidas.
* **ORM:** SQLAlchemy.
* **Seguridad & Autenticación:**
  * Hashing de contraseñas con **bcrypt**.
  * Control de Acceso Basado en Roles (**RBAC**) mediante inyección de dependencias (`Practitioner` vs. `Patient`).
  * Tokens de sesión y tokens de compartición QR firmados mediante **JWT (JSON Web Tokens)**.
* **Aseguramiento de Calidad (QA):** Suite de pruebas automatizadas con **Pytest**, testeando flujos de autenticación, control de accesos, expiración de tokens efímeros y serialización FHIR IPS.

---

## 🚀 Endpoints Principales

| Módulo | Método | Ruta | Descripción | Acceso |
| :--- | :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/v1/auth/register/patient` | Registro de paciente | Público |
| **Auth** | `POST` | `/api/v1/auth/register/practitioner` | Registro de médico con matrícula profesional | Público |
| **Auth** | `POST` | `/api/v1/auth/login` | Autenticación unificada (OAuth2 Form) y emisión de JWT | Público |
| **Summaries**| `POST` | `/api/v1/summaries/` | Crear o versionar Carta Sanitaria | Solo Médicos |
| **Summaries**| `GET` | `/api/v1/summaries/me` | Consultar Carta Sanitaria vigente propia | Solo Pacientes |
| **Summaries**| `GET` | `/api/v1/summaries/me/pdf` | Descargar Carta Sanitaria oficial en formato PDF | Solo Pacientes |
| **Summaries**| `GET` | `/api/v1/summaries/me/fhir` | Exportar resumen a estándar HL7 FHIR (IPS Bundle) | Autenticado |
| **Share** | `GET` | `/api/v1/share/qr/generate` | Generar token efímero (15 min) para código QR | Solo Pacientes |
| **Share** | `GET` | `/api/v1/share/qr/image` | Descargar/Visualizar código QR en imagen PNG | Solo Pacientes |
| **Share** | `POST` | `/api/v1/share/qr/scan` | Validar token QR, visualizar resumen y registrar auditoría | Solo Médicos |
| **Audit** | `GET` | `/api/v1/audit/logs` | Consultar historial de accesos a la historia clínica | Pacientes / Auditores |
| **Terminology**| `GET` | `/api/v1/terminology/search`| Autocompletado normalizado con códigos SNOMED-CT | Autenticado |

---

## ⚙️ Instalación y Configuración Local

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/LautaroYuvone/sanitary-card-api.git
   cd sanitary-card-api
   
2. **Crear y activar el entorno virtual:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   
3. **Instalación de dependencias:**
    ```powershell
   pip install -r requirements.txt
   
4. **Configurar variables de entorno:** Copiar archivo '.env.example', renombrarlo a '.env' y configurar clave secreta y base de datos.

5. **Ejecutar la suite de pruebas automatizadas:**
    ```powershell
   pytest -v

6. **Iniciar el servidor:**
   ```powershell
   uvicorn app.main:app --reload
   
7. **Documentación Swagger UI:** Ingresar a http://127.0.0.1:8000/docs en el navegador