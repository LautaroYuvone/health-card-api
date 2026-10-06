import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import qrcode

from app.models.summary import ClinicalSummary
from app.models.user import Practitioner, User


def generate_summary_pdf(
        summary: ClinicalSummary,
        patient_user: User,
        practitioner: Practitioner,
        qr_token: str
) -> bytes:
    """
    Genera el archivo PDF imprimible de la Carta Sanitaria
    con el código QR embebido en memoria.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading3"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=8,
        spaceAfter=4
    )
    cell_bold = ParagraphStyle("CellBold", parent=styles["Normal"], fontSize=9, leading=11, fontName="Helvetica-Bold")
    cell_text = ParagraphStyle("CellText", parent=styles["Normal"], fontSize=9, leading=11)
    badge_alert = ParagraphStyle(
        "BadgeAlert",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#991b1b"),
        fontName="Helvetica-Bold"
    )

    story = []
    clinical_data = summary.clinical_data or {}
    doc_user = practitioner.user

    # Perfil del paciente seguro
    p_profile = getattr(patient_user, "patient_profile", None)
    em_name = (p_profile.emergency_contact_name if p_profile else None) or "N/A"
    em_phone = (p_profile.emergency_contact_phone if p_profile else None) or "N/A"

    # --- 1. ENCABEZADO ---
    story.append(Paragraph("CARTA SANITARIA DIGITAL", title_style))
    story.append(Paragraph("Perfil Clínico Esencial de Emergencia y Consulta (FHIR IPS)", subtitle_style))
    story.append(Spacer(1, 15))

    # --- 2. DATOS DEL PACIENTE ---
    patient_table_data = [
        [
            Paragraph("<b>Paciente:</b>", cell_bold),
            Paragraph(f"{patient_user.last_name}, {patient_user.first_name}", cell_text),
            Paragraph("<b>DNI:</b>", cell_bold),
            Paragraph(patient_user.national_id or "N/A", cell_text),
        ],
        [
            Paragraph("<b>Grupo Sanguíneo:</b>", cell_bold),
            Paragraph(clinical_data.get("blood_type") or "No registrado", cell_text),
            Paragraph("<b>Teléfono:</b>", cell_bold),
            Paragraph(patient_user.phone or "No registrado", cell_text),
        ],
        [
            Paragraph("<b>Contacto Emergencia:</b>", cell_bold),
            Paragraph(em_name, cell_text),
            Paragraph("<b>Tel. Emergencia:</b>", cell_bold),
            Paragraph(em_phone, cell_text),
        ]
    ]

    t_patient = Table(patient_table_data, colWidths=[100, 160, 90, 170])
    t_patient.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_patient)
    story.append(Spacer(1, 12))

    # --- 3. ALERGIAS ---
    story.append(Paragraph("Alergias e Intolerancias", section_title))
    allergies = clinical_data.get("allergies") or []
    if allergies:
        allergy_data = [[
            Paragraph("Sustancia / Fármaco", cell_bold),
            Paragraph("Criticidad", cell_bold),
            Paragraph("Reacción", cell_bold)
        ]]
        for a in allergies:
            substance_name = a.get("substance", {}).get("display") or "No identificada"
            allergy_data.append([
                Paragraph(substance_name, badge_alert),
                Paragraph((a.get("criticality") or "low").upper(), cell_text),
                Paragraph(a.get("reaction") or "No especificada", cell_text)
            ])
        t_allergies = Table(allergy_data, colWidths=[240, 120, 160])
        t_allergies.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#fca5a5")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fecaca")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_allergies)
    else:
        story.append(Paragraph("<i>Sin alergias conocidas registradas.</i>", cell_text))

    story.append(Spacer(1, 10))

    # --- 4. CONDICIONES ---
    story.append(Paragraph("Problemas de Salud y Patologías Crónicas", section_title))
    conditions = clinical_data.get("conditions") or []
    if conditions:
        cond_data = [[
            Paragraph("Diagnóstico / Condición", cell_bold),
            Paragraph("Código Estándar", cell_bold),
            Paragraph("Estado", cell_bold)
        ]]
        for c in conditions:
            cond_display = c.get("condition", {}).get("display") or "Diagnóstico no especificado"
            system_name = c.get("condition", {}).get("system", "").split("/")[-1]
            code_str = f"{c.get('condition', {}).get('code', '')} ({system_name})"
            cond_data.append([
                Paragraph(cond_display, cell_text),
                Paragraph(code_str, cell_text),
                Paragraph((c.get("clinical_status") or "activo").capitalize(), cell_text)
            ])
        t_conditions = Table(cond_data, colWidths=[240, 160, 120])
        t_conditions.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_conditions)
    else:
        story.append(Paragraph("<i>Sin antecedentes patológicos crónicos reportados.</i>", cell_text))

    story.append(Spacer(1, 10))

    # --- 5. MEDICACIÓN CRÓNICA ---
    story.append(Paragraph("Tratamiento Farmacológico Habitual", section_title))
    medications = clinical_data.get("medications") or []
    if medications:
        med_data = [[
            Paragraph("Medicamento", cell_bold),
            Paragraph("Dosis", cell_bold),
            Paragraph("Frecuencia", cell_bold)
        ]]
        for m in medications:
            med_display = m.get("medication", {}).get("display") or "Fármaco no especificado"
            med_data.append([
                Paragraph(med_display, cell_text),
                Paragraph(m.get("dosage") or "-", cell_text),
                Paragraph(m.get("frequency") or "-", cell_text)
            ])
        t_meds = Table(med_data, colWidths=[240, 120, 160])
        t_meds.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_meds)
    else:
        story.append(Paragraph("<i>No toma medicación crónica.</i>", cell_text))

    story.append(Spacer(1, 20))

    # --- 6. PIE DE PÁGINA: QR + CERTIFICACIÓN MÉDICA ---
    qr = qrcode.QRCode(box_size=3, border=1)
    qr.add_data(qr_token)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    qr_io = io.BytesIO()
    qr_img.save(qr_io, format="PNG")
    qr_io.seek(0)
    qr_flowable = Image(qr_io, width=85, height=85)

    footer_text = f"""
        <b>Certificado por:</b> Dr/a. {doc_user.first_name} {doc_user.last_name}<br/>
        <b>Matrícula Profesional:</b> {practitioner.license_number}<br/>
        <b>Especialidad:</b> {practitioner.specialty or 'Clínica'}<br/>
        <b>Versión de Carta:</b> v{summary.version} &nbsp;|&nbsp; <b>Fecha:</b> {datetime.now().strftime('%d/%m/%Y')}<br/>
        <i>Nota: Escaneo exclusivo para médicos habilitados mediante token firmado.</i>
        """

    footer_table = Table([
        [Paragraph(footer_text, cell_text), qr_flowable]
    ], colWidths=[420, 100])
    footer_table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(KeepTogether(footer_table))

    doc.build(story)
    return buffer.getvalue()