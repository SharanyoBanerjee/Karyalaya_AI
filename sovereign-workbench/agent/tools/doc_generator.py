"""
Document Generator Tool for Sovereign AI Workbench.
Creates AI-drafted documents for human review, and finalizes official .docx deliverables upon explicit human approval.
Outputs directly into workspace/deliverables/ folder.
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from typing import Dict, Any, List

WORKSPACE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "workspace")
)
DELIVERABLES_DIR = os.path.join(WORKSPACE_DIR, "deliverables")


def create_approval_note_docx(
    title: str,
    ref_number: str,
    plant_unit: str,
    inspection_date: str,
    findings: List[str],
    sop_reference: str,
    recommendation: str,
    target_path: str,
    is_official: bool = False
) -> str:
    """Builds and saves .docx file at target_path."""
    doc = docx.Document()

    # Page Margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Header Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc_type_text = "OFFICIAL INSPECTION APPROVAL NOTE" if is_official else "DRAFT INSPECTION APPROVAL NOTE (PENDING HUMAN REVIEW)"
    r_title = p_title.add_run(doc_type_text)
    r_title.bold = True
    r_title.font.size = Pt(15)
    r_title.font.color.rgb = RGBColor(0, 51, 102) if is_official else RGBColor(180, 100, 0)

    # Subtitle
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run(f"SOVEREIGN AI WORKBENCH - {plant_unit.upper()}")
    r_sub.font.size = Pt(10)
    r_sub.font.italic = True

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Meta Table
    table = doc.add_table(rows=4, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    meta_data = [
        ("Document Title:", title),
        ("Reference No.:", ref_number),
        ("Plant / Facility Unit:", plant_unit),
        ("Inspection Date:", inspection_date)
    ]

    for idx, (label, val) in enumerate(meta_data):
        row = table.rows[idx]
        cell_lbl, cell_val = row.cells[0], row.cells[1]
        cell_lbl.text = label
        cell_val.text = val
        cell_lbl.paragraphs[0].runs[0].bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Section 1: Inspection Findings
    h1 = doc.add_heading("1. Key Inspection Findings", level=1)
    h1.runs[0].font.color.rgb = RGBColor(0, 51, 102)

    for finding in findings:
        p_f = doc.add_paragraph(style='List Bullet')
        p_f.add_run(finding)

    # Section 2: Applicable SOP Grounding
    h2 = doc.add_heading("2. Grounding & SOP Reference", level=1)
    h2.runs[0].font.color.rgb = RGBColor(0, 51, 102)
    p_sop = doc.add_paragraph()
    p_sop.add_run(sop_reference)

    # Section 3: Recommendation & Next Steps
    h3 = doc.add_heading("3. Recommendation & Next Steps", level=1)
    h3.runs[0].font.color.rgb = RGBColor(0, 51, 102)
    p_rec = doc.add_paragraph()
    p_rec.add_run(recommendation)

    # Sign-off Block
    doc.add_paragraph().paragraph_format.space_after = Pt(20)
    p_sign = doc.add_paragraph()
    sign_text = "Approved & Signed by:\n\n_______________________\nChief Inspection Officer / Unit Head" if is_official else "PENDING HUMAN REVIEW & SIGN-OFF\n\n_______________________\nAuthorized Approver Signature Required"
    p_sign.add_run(sign_text)
    p_sign.runs[0].bold = True

    doc.save(target_path)
    return target_path


def generate_approval_note(
    title: str,
    ref_number: str,
    plant_unit: str,
    inspection_date: str,
    findings: List[str],
    sop_reference: str,
    recommendation: str,
    filename: str = "Approval_Note.docx"
) -> Dict[str, Any]:
    """
    Step 1: Generates an AI Draft Approval Note (PENDING HUMAN APPROVAL).
    Requires explicit human confirmation before saving as official deliverable.
    """
    try:
        os.makedirs(DELIVERABLES_DIR, exist_ok=True)
        draft_filename = f"DRAFT_{filename}"
        draft_path = os.path.join(DELIVERABLES_DIR, draft_filename)

        create_approval_note_docx(
            title=title,
            ref_number=ref_number,
            plant_unit=plant_unit,
            inspection_date=inspection_date,
            findings=findings,
            sop_reference=sop_reference,
            recommendation=recommendation,
            target_path=draft_path,
            is_official=False
        )

        draft_payload = {
            "title": title,
            "ref_number": ref_number,
            "plant_unit": plant_unit,
            "inspection_date": inspection_date,
            "findings": findings,
            "sop_reference": sop_reference,
            "recommendation": recommendation,
            "target_filename": filename
        }

        return {
            "status": "draft_created",
            "requires_human_approval": True,
            "message": "AI Draft generated. Human sign-off required before finalizing official document.",
            "draft_file": draft_filename,
            "draft_payload": draft_payload
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


def finalize_official_document(draft_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 2: Finalizes official .docx deliverable upon human sign-off.
    """
    try:
        os.makedirs(DELIVERABLES_DIR, exist_ok=True)
        filename = draft_payload.get("target_filename", "Official_Approval_Note.docx")
        if not filename.endswith(".docx"):
            filename += ".docx"
        target_path = os.path.join(DELIVERABLES_DIR, filename)

        create_approval_note_docx(
            title=draft_payload.get("title", "Inspection Approval Note"),
            ref_number=draft_payload.get("ref_number", "REF-2026-001"),
            plant_unit=draft_payload.get("plant_unit", "Plant Unit"),
            inspection_date=draft_payload.get("inspection_date", "2026-08-27"),
            findings=draft_payload.get("findings", []),
            sop_reference=draft_payload.get("sop_reference", "Per SOP guidelines"),
            recommendation=draft_payload.get("recommendation", "Approved"),
            target_path=target_path,
            is_official=True
        )

        return {
            "status": "success",
            "official_filename": filename,
            "file_path": target_path,
            "message": f"Human approval confirmed. Official deliverable {filename} created successfully."
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}
