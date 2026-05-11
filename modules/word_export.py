"""
Octa Intelligence — Word Document Export
Generates formatted Word documents for all analysis rounds.
"""
import io
from datetime import date


def _setup_doc():
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    for section in doc.sections:
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin   = Cm(3)
        section.right_margin  = Cm(2.5)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)
    return doc


def _heading(doc, text, level=1, color_hex="1B2A4A"):
    from docx.shared import Pt, RGBColor
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(
            int(color_hex[0:2],16),
            int(color_hex[2:4],16),
            int(color_hex[4:6],16)
        )
    return h


def _bullet(doc, text, style_name="List Bullet"):
    try:
        p = doc.add_paragraph(text, style=style_name)
    except Exception:
        p = doc.add_paragraph(f"• {text}")
    return p


def export_round1_docx(analysis: dict, proposal_id: str,
                        acronym: str) -> bytes:
    """Export Round 1 Call Intelligence Analysis as Word document."""
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = _setup_doc()

    # Title
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(f"Call Intelligence Analysis")
    run.bold = True; run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(0x1B,0x2A,0x4A)

    t2 = doc.add_paragraph()
    t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = t2.add_run(f"Proposal: {acronym} ({proposal_id})")
    run2.font.size = Pt(12); run2.font.color.rgb = RGBColor(0x88,0x99,0xB0)

    t3 = doc.add_paragraph()
    t3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t3.add_run(f"Generated: {date.today().isoformat()}").font.color.rgb = RGBColor(0x88,0x99,0xB0)

    doc.add_page_break()

    # 1. Objectives
    _heading(doc, "1. Call Objectives")
    for obj in analysis.get("call_objectives",[]):
        _heading(doc, f"1.{obj.get('id','')} — {obj.get('title','')}", level=2)
        doc.add_paragraph(obj.get("description",""))
        if obj.get("evidence"):
            p = doc.add_paragraph()
            run = p.add_run(f"Evidence: {obj['evidence']}")
            run.italic = True; run.font.color.rgb = RGBColor(0x88,0x99,0xB0)

    # 2. Expected Outcomes
    _heading(doc, "2. Expected Outcomes")
    for oc in analysis.get("expected_outcomes",[]):
        _bullet(doc, f"{oc.get('outcome','')} [{oc.get('timeframe','')}]")

    # 3. Expected Impacts
    _heading(doc, "3. Expected Impacts")
    for imp in analysis.get("expected_impacts",[]):
        _bullet(doc, f"[{imp.get('level','').upper()}] {imp.get('impact','')} — {imp.get('timeframe','')} term")

    # 4. Expected Outputs
    _heading(doc, "4. Expected Outputs")
    for out in analysis.get("expected_outputs",[]):
        _bullet(doc, f"[{out.get('type','').upper()}] {out.get('output','')}")

    # 5. Recommended KPIs
    _heading(doc, "5. Recommended KPIs")
    for kpi in analysis.get("recommended_kpis",[]):
        _bullet(doc, f"{kpi.get('kpi','')} — Unit: {kpi.get('unit','')} [{kpi.get('source','')}]")

    # 6. Policy Framing
    _heading(doc, "6. Policy Framing")
    pf = analysis.get("policy_framing",{})
    if pf.get("policy_narrative"):
        doc.add_paragraph(pf["policy_narrative"])
    _heading(doc, "Primary Policies", level=2)
    for pol in pf.get("primary_policies",[]):
        _heading(doc, f"{pol.get('policy','')} (Relevance: {pol.get('relevance_score',0)}/10)", level=3)
        doc.add_paragraph(pol.get("how_call_references",""))
        if pol.get("key_targets_to_mention"):
            doc.add_paragraph("Key targets to mention:")
            for t in pol["key_targets_to_mention"]:
                _bullet(doc, t)

    # 7. Master Keywords
    _heading(doc, "7. Critical Keywords")
    critical = [k for k in analysis.get("master_keywords",[]) if k.get("importance")=="critical"]
    high     = [k for k in analysis.get("master_keywords",[]) if k.get("importance")=="high"]
    medium   = [k for k in analysis.get("master_keywords",[]) if k.get("importance")=="medium"]
    if critical:
        _heading(doc, "Critical (must appear):", level=2)
        doc.add_paragraph(" · ".join(k.get("keyword","") for k in critical))
    if high:
        _heading(doc, "High importance:", level=2)
        doc.add_paragraph(" · ".join(k.get("keyword","") for k in high))
    if medium:
        _heading(doc, "Medium importance:", level=2)
        doc.add_paragraph(" · ".join(k.get("keyword","") for k in medium))

    # 8. Synergy Initiatives
    _heading(doc, "8. Synergy & Complementarity")
    for syn in analysis.get("synergy_initiatives",[]):
        _heading(doc, syn.get("name",""), level=2)
        doc.add_paragraph(syn.get("description",""))
        if syn.get("how_to_build_synergy"):
            p = doc.add_paragraph()
            p.add_run("How to build synergy: ").bold = True
            p.add_run(syn["how_to_build_synergy"])

    # 9. Hidden Messages
    _heading(doc, "9. Hidden Messages & Implicit Expectations")
    doc.add_paragraph(analysis.get("hidden_messages",""))

    # 10. Expected Partner Profiles
    _heading(doc, "10. Expected Partner Profiles")
    for prof in analysis.get("expected_partner_profiles",[]):
        _heading(doc, prof.get("profile_type",""), level=2)
        doc.add_paragraph(prof.get("description",""))
        if prof.get("is_mandatory"):
            p = doc.add_paragraph()
            p.add_run("⚠ MANDATORY profile").bold = True

    # 11. Consortium Positioning
    _heading(doc, "11. Our Consortium Positioning")
    doc.add_paragraph(analysis.get("consortium_positioning",""))

    # 12. Strategic Recommendations
    _heading(doc, "12. Strategic Recommendations")
    for rec in sorted(analysis.get("strategic_recommendations",[]),
                       key=lambda x: x.get("priority",99)):
        _heading(doc, f"Priority {rec.get('priority','')}: {rec.get('recommendation','')}", level=2)
        doc.add_paragraph(rec.get("rationale",""))
        if rec.get("action"):
            p = doc.add_paragraph()
            p.add_run("Action: ").bold = True
            p.add_run(rec["action"])

    doc.add_paragraph(f"\n\nGenerated by Octa Intelligence · {date.today().isoformat()}")

    buf = io.BytesIO()
    doc.save(buf); buf.seek(0)
    return buf.read()


def export_architecture_docx(architecture: dict, analysis: dict,
                              proposal_id: str, acronym: str) -> bytes:
    """
    Export Round 2b proposal architecture as Word document.
    Red-text guidance appears under each section heading.
    """
    from docx.shared import Pt, RGBColor
    from docx.oxml.ns import qn
    from docx.oxml    import OxmlElement

    RED   = RGBColor(0xC0,0x00,0x00)
    BLUE  = RGBColor(0x00,0x44,0x88)
    GREEN = RGBColor(0x00,0x66,0x33)
    AMBER = RGBColor(0xCC,0x66,0x00)

    doc = _setup_doc()
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    # Title page
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run("Proposal Writing Architecture")
    run.bold = True; run.font.size = Pt(20); run.font.color.rgb = RGBColor(0x1B,0x2A,0x4A)

    doc.add_paragraph()
    t2 = doc.add_paragraph()
    t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t2.add_run(f"{acronym} ({proposal_id})\n{architecture.get('programme','')}")

    doc.add_paragraph()
    t3 = doc.add_paragraph()
    t3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t3.add_run(f"Generated: {date.today().isoformat()}")

    # Legend
    doc.add_page_break()
    _heading(doc, "How to Use This Document")
    legend_items = [
        (RED,   "Reviewer guidance — what evaluators expect in this section"),
        (BLUE,  "Policy connections — which EU policies to reference here"),
        (GREEN, "Keywords — must appear in this section"),
        (AMBER, "Evidence & measures — specific data, KPIs or proof expected"),
    ]
    for color, desc in legend_items:
        p = doc.add_paragraph()
        run = p.add_run(f"■ {desc}")
        run.font.color.rgb = color
    doc.add_paragraph()

    if architecture.get("general_advice"):
        _heading(doc, "General Strategic Advice")
        doc.add_paragraph(architecture["general_advice"])

    if architecture.get("top_5_priorities"):
        _heading(doc, "Top 5 Priorities for This Proposal")
        for item in architecture["top_5_priorities"]:
            _bullet(doc, item)

    doc.add_page_break()
    _heading(doc, "PROPOSAL STRUCTURE")

    sections = architecture.get("sections",[])
    for sec in sorted(sections, key=lambda x: x.get("order",0)):
        level = sec.get("level",1)
        title = sec.get("ai_title","") or sec.get("original_title","")
        h     = _heading(doc, title, level=level)

        # Title rationale (italics, muted)
        if sec.get("title_rationale"):
            p = doc.add_paragraph()
            run = p.add_run(f"[{sec['title_rationale']}]")
            run.italic = True
            run.font.color.rgb = RGBColor(0x88,0x99,0xB0)
            run.font.size = Pt(9)

        # Reviewer guidance (RED)
        if sec.get("reviewer_guidance"):
            p = doc.add_paragraph()
            run = p.add_run("🔴 REVIEWER EXPECTS:")
            run.bold = True; run.font.color.rgb = RED
            for point in sec["reviewer_guidance"]:
                bp = doc.add_paragraph(f"  • {point}", style="List Bullet")
                for run in bp.runs:
                    run.font.color.rgb = RED

        # Policy connections (BLUE)
        if sec.get("policy_connections"):
            p = doc.add_paragraph()
            run = p.add_run("🔵 POLICY CONNECTIONS:")
            run.bold = True; run.font.color.rgb = BLUE
            for pol in sec["policy_connections"]:
                bp = doc.add_paragraph(
                    f"  • {pol.get('policy','')} — {pol.get('how','')}",
                    style="List Bullet"
                )
                for run in bp.runs:
                    run.font.color.rgb = BLUE

        # Keywords (GREEN)
        if sec.get("keywords_to_include"):
            p = doc.add_paragraph()
            run = p.add_run("🟢 KEYWORDS: ")
            run.bold = True; run.font.color.rgb = GREEN
            kw_run = p.add_run(" · ".join(sec["keywords_to_include"]))
            kw_run.font.color.rgb = GREEN

        # Evidence & measures (AMBER)
        if sec.get("measures_and_evidence"):
            p = doc.add_paragraph()
            run = p.add_run("🟡 EVIDENCE & MEASURES: ")
            run.bold = True; run.font.color.rgb = AMBER
            ev_run = p.add_run(sec["measures_and_evidence"])
            ev_run.font.color.rgb = AMBER

        # Word count guidance
        if sec.get("word_count_guidance"):
            p = doc.add_paragraph()
            run = p.add_run(f"📏 {sec['word_count_guidance']}")
            run.font.color.rgb = RGBColor(0x88,0x99,0xB0)
            run.font.size = Pt(9)

        # Common mistakes
        if sec.get("common_mistakes"):
            p = doc.add_paragraph()
            run = p.add_run("⚠ AVOID:")
            run.bold = True; run.font.color.rgb = RGBColor(0x99,0x33,0x00)
            for m in sec["common_mistakes"]:
                bp = doc.add_paragraph(f"  ✗ {m}", style="List Bullet")
                for run in bp.runs:
                    run.font.color.rgb = RGBColor(0x99,0x33,0x00)

        doc.add_paragraph()

    doc.add_paragraph(f"\nGenerated by Octa Intelligence · {date.today().isoformat()}")

    buf = io.BytesIO()
    doc.save(buf); buf.seek(0)
    return buf.read()
