from enum import Enum
from typing import List
import unicodedata
from fastapi import APIRouter, Query
from app.schemas.clinical import CodedConcept

router = APIRouter(prefix="/terminology", tags=["Terminologías Médicas"])


class TerminologyDomain(str, Enum):
    CONDITION = "condition"
    ALLERGY = "allergy"
    MEDICATION = "medication"


# Catálogo semilla inicial con códigos SNOMED-CT y CIE-10 frecuentes
TERMINOLOGY_CATALOG = {
    TerminologyDomain.CONDITION: [
        {"system": "http://snomed.info/sct", "code": "44054006", "display": "Diabetes mellitus tipo 2"},
        {"system": "http://snomed.info/sct", "code": "38341003", "display": "Hipertensión arterial esencial"},
        {"system": "http://snomed.info/sct", "code": "195967001", "display": "Asma bronquial"},
        {"system": "http://snomed.info/sct", "code": "13645005", "display": "Enfermedad pulmonar obstructiva crónica (EPOC)"},
        {"system": "http://snomed.info/sct", "code": "414545008", "display": "Cardiopatía isquémica crónica"},
        {"system": "http://snomed.info/sct", "code": "73211009", "display": "Hipotiroidismo primario"},
        {"system": "http://hl7.org/fhir/sid/icd-10", "code": "I10", "display": "Hipertensión esencial (primaria)"},
        {"system": "http://hl7.org/fhir/sid/icd-10", "code": "E11", "display": "Diabetes mellitus no insulinodependiente"},
    ],
    TerminologyDomain.ALLERGY: [
        {"system": "http://snomed.info/sct", "code": "373270004", "display": "Penicilina (sustancia)"},
        {"system": "http://snomed.info/sct", "code": "387207008", "display": "Ibuprofeno (sustancia)"},
        {"system": "http://snomed.info/sct", "code": "387458008", "display": "Aspirina / Ácido acetilsalicílico"},
        {"system": "http://snomed.info/sct", "code": "91936005", "display": "Alergia a la penicilina"},
        {"system": "http://snomed.info/sct", "code": "300916003", "display": "Alergia al látex"},
        {"system": "http://snomed.info/sct", "code": "419474003", "display": "Alergia al veneno de abeja / avispa"},
        {"system": "http://snomed.info/sct", "code": "294805000", "display": "Alergia al huevo"},
    ],
    TerminologyDomain.MEDICATION: [
        {"system": "http://snomed.info/sct", "code": "372567009", "display": "Metformina"},
        {"system": "http://snomed.info/sct", "code": "372658000", "display": "Enalapril"},
        {"system": "http://snomed.info/sct", "code": "386864001", "display": "Losartán"},
        {"system": "http://snomed.info/sct", "code": "387584000", "display": "Atorvastatina"},
        {"system": "http://snomed.info/sct", "code": "387063004", "display": "Levotiroxina sódica"},
        {"system": "http://snomed.info/sct", "code": "387017005", "display": "Omeprazol"},
        {"system": "http://snomed.info/sct", "code": "372897005", "display": "Amlodipina"},
    ]
}


def normalize_text(text: str) -> str:
    """Elimina acentos y pasa a minúsculas para búsquedas flexibles."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )


@router.get("/search", response_model=List[CodedConcept])
def search_terms(
    q: str = Query(..., min_length=2, description="Texto de búsqueda (ej: 'diab', 'peni', 'hiper')"),
    domain: TerminologyDomain = Query(..., description="Dominio clínico a filtrar"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Buscador rápido para el autocompletado en la interfaz médica.
    Devuelve los conceptos coincidentes ordenados y limitados.
    """
    normalized_q = normalize_text(q)
    results = []

    domain_catalog = TERMINOLOGY_CATALOG.get(domain, [])

    for entry in domain_catalog:
        display_norm = normalize_text(entry["display"])
        code = entry["code"].lower()

        # Búsqueda tanto por coincidencia en texto como por código exacto
        if normalized_q in display_norm or normalized_q == code:
            results.append(entry)
            if len(results) >= limit:
                break

    return results