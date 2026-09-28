import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from app.models.summary import ClinicalSummary
from app.models.user import Practitioner, User


def create_fhir_ips_bundle(summary: ClinicalSummary, patient_user: User, practitioner: Practitioner) -> Dict[str, Any]:
    """
    Transforma la Carta Sanitaria interna en un FHIR Bundle oficial
    conforme al perfil International Patient Summary (IPS).
    """
    bundle_id = str(uuid.uuid4())
    composition_id = str(uuid.uuid4())
    patient_res_id = str(uuid.uuid4())
    practitioner_res_id = str(uuid.uuid4())

    now_iso = datetime.now(timezone.utc).isoformat()
    raw_data = summary.clinical_data or {}

    entries = []

    # --- 1. Recurso: Patient ---
    patient_full_url = f"urn:uuid:{patient_res_id}"
    patient_resource = {
        "resourceType": "Patient",
        "id": patient_res_id,
        "identifier": [
            {
                "system": "https://tribunal-electoral.gov.ar/dni",
                "value": patient_user.national_id
            }
        ],
        "name": [
            {
                "use": "official",
                "family": patient_user.last_name,
                "given": [patient_user.first_name]
            }
        ],
        "telecom": [
            {"system": "phone", "value": patient_user.phone or "", "use": "mobile"},
            {"system": "email", "value": patient_user.email}
        ]
    }

    # --- 2. Recurso: Practitioner ---
    doc_user = practitioner.user
    practitioner_full_url = f"urn:uuid:{practitioner_res_id}"
    practitioner_resource = {
        "resourceType": "Practitioner",
        "id": practitioner_res_id,
        "identifier": [
            {
                "system": "https://sisa.msal.gov.ar/matricula",
                "value": practitioner.license_number
            }
        ],
        "name": [
            {
                "use": "official",
                "family": doc_user.last_name,
                "given": [doc_user.first_name]
            }
        ]
    }

    # --- 3. Recursos Clínicos: Alergias ---
    allergy_refs = []
    for item in raw_data.get("allergies", []):
        substance = item.get("substance", {})
        res_id = str(uuid.uuid4())
        allergy_res = {
            "resourceType": "AllergyIntolerance",
            "id": res_id,
            "clinicalStatus": {
                "coding": [
                    {"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]
            },
            "criticality": item.get("criticality", "low"),
            "code": {
                "coding": [
                    {
                        "system": substance.get("system", "http://snomed.info/sct"),
                        "code": substance.get("code", ""),
                        "display": substance.get("display", "")
                    }
                ]
            },
            "patient": {"reference": patient_full_url}
        }
        entries.append({"fullUrl": f"urn:uuid:{res_id}", "resource": allergy_res})
        allergy_refs.append({"reference": f"urn:uuid:{res_id}"})

    # --- 4. Recursos Clínicos: Condiciones / Antecedentes ---
    condition_refs = []
    for item in raw_data.get("conditions", []):
        cond = item.get("condition", {})
        res_id = str(uuid.uuid4())
        condition_res = {
            "resourceType": "Condition",
            "id": res_id,
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": item.get("clinical_status", "active")
                }]
            },
            "code": {
                "coding": [
                    {
                        "system": cond.get("system", "http://snomed.info/sct"),
                        "code": cond.get("code", ""),
                        "display": cond.get("display", "")
                    }
                ]
            },
            "subject": {"reference": patient_full_url}
        }
        entries.append({"fullUrl": f"urn:uuid:{res_id}", "resource": condition_res})
        condition_refs.append({"reference": f"urn:uuid:{res_id}"})

    # --- 5. Recursos Clínicos: Medicación ---
    medication_refs = []
    for item in raw_data.get("medications", []):
        med = item.get("medication", {})
        res_id = str(uuid.uuid4())
        med_res = {
            "resourceType": "MedicationStatement",
            "id": res_id,
            "status": "active",
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": med.get("system", "http://snomed.info/sct"),
                        "code": med.get("code", ""),
                        "display": med.get("display", "")
                    }
                ]
            },
            "subject": {"reference": patient_full_url},
            "dosage": [
                {
                    "text": f"{item.get('dosage', '')} - {item.get('frequency', '')}"
                }
            ]
        }
        entries.append({"fullUrl": f"urn:uuid:{res_id}", "resource": med_res})
        medication_refs.append({"reference": f"urn:uuid:{res_id}"})

    # --- 6. Recurso: Composition (Cabecera IPS) ---
    composition_resource = {
        "resourceType": "Composition",
        "id": composition_id,
        "status": "final",
        "type": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "60591-5",
                    "display": "Patient summary Document"
                }
            ]
        },
        "subject": {"reference": patient_full_url},
        "date": now_iso,
        "author": [{"reference": practitioner_full_url}],
        "title": f"Carta Sanitaria - {patient_user.last_name}, {patient_user.first_name}",
        "section": [
            {
                "title": "Alergias e Intolerancias",
                "code": {"coding": [
                    {"system": "http://loinc.org", "code": "48765-2", "display": "Allergies and adverse reactions"}]},
                "entry": allergy_refs
            },
            {
                "title": "Problemas de Salud y Antecedentes",
                "code": {"coding": [{"system": "http://loinc.org", "code": "11450-4", "display": "Problem list"}]},
                "entry": condition_refs
            },
            {
                "title": "Medicación Crónica",
                "code": {"coding": [
                    {"system": "http://loinc.org", "code": "10160-0", "display": "History of Medication use"}]},
                "entry": medication_refs
            }
        ]
    }

    # Estructura del Bundle Documento: el primer entry SIEMPRE es el Composition
    final_bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {
            "profile": ["http://hl7.org/fhir/uv/ips/StructureDefinition/Bundle-uv-ips"]
        },
        "identifier": {
            "system": "urn:ietf:rfc:3986",
            "value": f"urn:uuid:{bundle_id}"
        },
        "type": "document",
        "timestamp": now_iso,
        "entry": [
            {"fullUrl": f"urn:uuid:{composition_id}", "resource": composition_resource},
            {"fullUrl": patient_full_url, "resource": patient_resource},
            {"fullUrl": practitioner_full_url, "resource": practitioner_resource},
            *entries
        ]
    }

    return final_bundle