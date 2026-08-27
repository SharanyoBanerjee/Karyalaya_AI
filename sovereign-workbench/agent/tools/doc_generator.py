"""
Document Generator Tool for Sovereign AI Workbench.
Creates official .docx approval notes and compliance documents using python-docx.
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
    Generates a structured, professional .docx approval note.
    Returns path to generated file and status.
    """
    try:
        os.makedirs(DELIVERABLES_DIR, exist_ok=True)
        if not filename.endswith(".docx"):
            filename += ".docx"
        target_path = os.path.join(DELIVERABLES_DIR, filename)

        doc = docx.Document()

        # Page setup - Margins
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

        # Header Title
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_title = p_title.add_run("OFFICIAL INSPECTION APPROVAL NOTE")
        r_title.bold = True
        r_title.font.size = Pt(16)
        r_title.font.color.rgb = RGBColor(0, 51, 102)

        # Subtitle
        p_sub = doc.add_paragraph()
        p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_sub = p_sub.add_run(f"SOVEREIGN AI WORKBENCH - {plant_unit.upper()}")
        r_sub.font.size = Pt(11)
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

        # Section 3: Recommendation & Action Plan
        h3 = doc.add_heading("3. Recommendation & Next Steps", level=1)
        h3.runs[0].font.color.rgb = RGBColor(0, 51, 102)
        p_rec = doc.add_paragraph()
        p_rec.add_run(recommendation)

        # Sign-off Block
        doc.add_paragraph().paragraph_format.space_after = Pt(24)
        p_sign = doc.add_paragraph()
        p_sign.add_run("Prepared & Approved by:\n\n_______________________\nChief Inspection Officer / Unit Head")
        p_sign.runs[0].bold = True

        doc.save(target_path)

        # Verify output exists and is readable
        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            return {
                "status": "success",
                "file_name": filename,
                "file_path": target_path,
                "message": f"Successfully generated {filename} ({os.path.getsize(target_path)} bytes)"
            }
        else:
            return {"status": "error", "error": "Generated document file is empty or missing."}

    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    res = generate_approval_note(
        title="Boiler Pressure Valve Inspection Sign-off",
        ref_number="SOP-APPROVAL-2026-089",
        plant_unit="Refinery Unit 4B",
        inspection_date="2026-08-27",
        findings=[
            "Pressure seal valve #3 displayed minimal surface wear within tolerance.",
            "Hydrostatic pressure test completed at 150 PSI for 45 minutes with zero leak.",
            "Gasket replaced per routine maintenance schedule."
        ],
        sop_reference="Grounded in SOP-702 Section 4.2 (High-Pressure Inspection Standards).",
        recommendation="Approved for regular operational commissioning for 12 calendar months."
    )
    print(res)
