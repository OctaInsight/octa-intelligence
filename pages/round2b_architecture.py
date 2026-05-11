"""Octa Intelligence - Round 2b: Proposal Architecture."""
import streamlit as st
import json
import re
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, DARK)
from modules.database import (get_call_analyses, get_call_setup,
                               get_concept_evaluations,
                               get_proposal_architectures,
                               create_proposal_architecture,
                               update_proposal_architecture, get_proposal)
from modules.claude_client import run_round2b, _parse_json_response
from modules.word_export import export_architecture_docx
from config import DARK as D, PROGRAMMES

st.set_page_config(page_title="Architecture - Octa", page_icon="building_construction",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

sel_pid = st.session_state.get("selected_proposal_id","")
if not sel_pid: st.switch_page("app.py"); st.stop()

proj    = get_proposal(sel_pid)
acronym = proj.get("acronym","") or sel_pid
page_header("Round 2b - Proposal Architecture",
            f"{acronym} - AI-annotated skeleton with reviewer guidance", "building_construction")
if st.button("Back to Dashboard"): st.switch_page("app.py")

muted = D["muted"]; acc = D["accent"]
user_id = st.session_state.get("user_id")

analyses = get_call_analyses(sel_pid)
complete = [a for a in analyses if a.get("status")=="complete"]
setup    = get_call_setup(sel_pid)
concepts = get_concept_evaluations(sel_pid)
archs    = get_proposal_architectures(sel_pid)

if not complete:
    st.warning("Complete Round 1 analysis first.")
    if st.button("Go to Round 1"): st.switch_page("pages/round1_analysis.py")
    st.stop()

analysis       = complete[0]
latest_concept = concepts[0] if concepts else None
programme      = setup.get("programme","Horizon Europe - RIA") if setup else "Horizon Europe - RIA"
prog_info      = PROGRAMMES.get(programme,{})

section_label("Define Structure and Generate")

with st.expander("Structure Definition", expanded=not archs):
    template_sections = prog_info.get("structure",[])
    user_titles = {}

    if template_sections:
        st.markdown(f"<p style='color:{muted};font-size:0.84rem'>Edit titles to customise. AI will annotate each section.</p>",
                    unsafe_allow_html=True)
        for sec in template_sections:
            sid   = sec.get("id","")
            level = sec.get("level",1)
            dflt  = sec.get("title","")
            indent= "   " * (level - 1)
            val   = st.text_input(f"{indent}Section {sid}", value=dflt, key=f"ts_{sid}")
            if val != dflt:
                user_titles[sid] = val
    else:
        st.markdown(
            f"<p style='color:{muted};font-size:0.84rem'>"
            f"Custom structure selected. Enter sections one per line. "
            f"Use 2 spaces for subsections.</p>", unsafe_allow_html=True)

        bg2 = D["bg2"]
        st.markdown(
            f"<div style='background:{bg2};border-left:3px solid {acc};"
            f"border-radius:8px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;"
            f"font-size:0.78rem;color:{muted}'>"
            f"Example: <code style='color:{acc}'>1. Excellence</code> then "
            f"<code style='color:{acc}'>  1.1 Objectives</code> (2 spaces indent)"
            f"</div>", unsafe_allow_html=True)

        custom_text = st.text_area(
            "Your Proposed Structure", height=250, key="cst",
            placeholder=(
                "1. Excellence\n  1.1 Objectives and Ambition\n  1.2 Methodology\n"
                "  1.3 Innovation\n2. Impact\n  2.1 Expected Outcomes\n"
                "  2.2 Dissemination\n3. Implementation\n  3.1 Work Plan\n"
                "  3.2 Management\n  3.3 Consortium\n  3.4 Resources"
            )
        )

        if custom_text.strip():
            parsed_secs = []
            order = 0
            for line in custom_text.strip().splitlines():
                stripped = line.strip()
                if not stripped: continue
                leading = len(line) - len(line.lstrip(" -"))
                level   = 1 if leading == 0 else (2 if leading <= 3 else 3)
                m       = re.match(r"^[0-9.]+[.)]\s*", stripped)
                if m:
                    sec_id = m.group().strip().rstrip(".")
                    title  = stripped[m.end():].strip()
                else:
                    sec_id = str(len(parsed_secs) + 1)
                    title  = stripped.lstrip("- ").strip()
                order += 1
                parsed_secs.append({"id": sec_id, "level": level,
                                    "title": title, "order": order})
            template_sections = parsed_secs
            suc = D["success"]
            st.markdown(f"<span style='color:{suc}'>Ready: {len(parsed_secs)} sections defined</span>",
                        unsafe_allow_html=True)

if st.button("Generate Architecture", type="primary", use_container_width=True):
    if not template_sections:
        st.error("No sections defined. Add your structure above."); st.stop()

    n_batches = max(1, (len(template_sections) + 3) // 4)
    progress  = st.progress(0, text=f"Starting... 0/{n_batches} batches")
    status_box= st.empty()

    import math
    # Monkey-patch to show progress — we call run_round2b which does batches internally
    status_box.info(f"Processing {len(template_sections)} sections in ~{n_batches} batches "
                    f"(~{n_batches * 30} seconds)...")

    result, raw_text = run_round2b(
        structure_template = template_sections,
        call_analysis      = analysis,
        concept_evaluation = latest_concept,
        programme          = programme,
        user_custom_titles = user_titles if user_titles else None,
    )
    progress.progress(1.0, text="Done!")

    from datetime import datetime, timezone
    sections = result.get("sections",[]) if result else []

    ok, arch_id = create_proposal_architecture({
        "proposal_id":           sel_pid,
        "call_analysis_id":      analysis["id"],
        "concept_evaluation_id": latest_concept["id"] if latest_concept else None,
        "api_mode":              "realtime",
        "status":                "complete" if sections else "raw_only",
        "programme":             programme,
        "structure_type":        "pre_built" if prog_info.get("structure") else "custom",
        "sections":              sections,
        "general_advice":        result.get("general_advice","") if result else "",
        "top_5_priorities":      result.get("top_5_priorities",[]) if result else [],
        "total_sections":        sum(1 for s in sections if s.get("level",1)==1),
        "total_subsections":     sum(1 for s in sections if s.get("level",1)>1),
        "raw_response":          (raw_text or "")[:5000],
        "completed_at":          datetime.now(timezone.utc).isoformat(),
    })
    if ok:
        status_box.success(f"Architecture complete - {len(sections)} sections annotated!")
        st.rerun()
    else:
        st.error("Save failed.")

if not archs: st.stop()

arch = archs[0]
if len(archs) > 1:
    idx = st.selectbox("Version", range(len(archs)),
                       format_func=lambda i: (f"v{len(archs)-i}: "
                                              f"{str(archs[i].get('created_at',''))[:10]} "
                                              f"({archs[i].get('total_sections',0)} sections)"),
                       key="arch_v")
    arch = archs[idx]

sections  = arch.get("sections",[])
_raw_arch = arch.get("raw_response","")

if not sections and _raw_arch:
    warn = D["warning"]
    st.markdown(
        f"<div style='background:{warn}22;border:1px solid {warn};border-radius:10px;"
        f"padding:0.9rem 1.2rem;margin-bottom:0.8rem'>"
        f"<strong style='color:{warn}'>Sections could not be parsed.</strong> "
        f"Click Re-Parse to retry.</div>", unsafe_allow_html=True)
    if st.button("Re-Parse Architecture", type="primary"):
        r2 = _parse_json_response(_raw_arch)
        if r2 and r2.get("sections"):
            secs = r2["sections"]
            update_proposal_architecture(arch["id"], {
                "sections":         secs,
                "total_sections":   sum(1 for s in secs if s.get("level",1)==1),
                "total_subsections":sum(1 for s in secs if s.get("level",1)>1),
                "status":           "complete",
            })
            st.success("Re-parsed!"); st.rerun()
    with st.expander("Raw AI Response", expanded=True):
        st.markdown(
            f"<div style='background:{D["bg2"]};border-radius:8px;padding:1rem;"
            f"white-space:pre-wrap;font-size:0.82rem;color:{D["text"]}'>"
            f"{_raw_arch}</div>", unsafe_allow_html=True)
    st.stop()

if not sections:
    st.info("No sections yet. Generate an architecture above."); st.stop()

section_label(f"Annotated Architecture - {len(sections)} sections")

dc1, dc2 = st.columns(2)
with dc1:
    doc_bytes = export_architecture_docx(arch, analysis, sel_pid, acronym)
    st.download_button(
        "Download Architecture (Word - colour-coded guidance)",
        data=doc_bytes,
        file_name=f"{acronym}_Proposal_Architecture.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key="dl_arch"
    )
with dc2:
    st.markdown(
        f"<div style='background:{D["bg2"]};border-radius:8px;padding:0.6rem 0.9rem;"
        f"font-size:0.8rem;color:{muted}'>"
        f"Red = Reviewer guidance  Blue = Policy  Green = Keywords  Amber = Evidence"
        f"</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if arch.get("general_advice"):
    with st.expander("Strategic Advice", expanded=True):
        st.markdown(
            f"<div style='background:{D["bg2"]};border-left:4px solid {acc};"
            f"border-radius:8px;padding:1rem 1.2rem'>{arch['general_advice']}</div>",
            unsafe_allow_html=True)

if arch.get("top_5_priorities"):
    with st.expander("Top 5 Priorities", expanded=True):
        for i, p in enumerate(arch["top_5_priorities"], 1):
            suc = D["success"]
            st.markdown(
                f"<div style='background:{D["bg2"]};border-left:3px solid {suc};"
                f"border-radius:6px;padding:0.4rem 0.8rem;margin-bottom:0.3rem'>"
                f"<strong style='color:{suc}'>{i}.</strong> {p}</div>",
                unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
section_label("Section-by-Section Guidance")

for sec in sorted(sections, key=lambda x: x.get("order",0)):
    level = sec.get("level",1)
    orig  = sec.get("original_title","")
    title = sec.get("ai_title","") or orig or sec.get("title","")
    sid   = sec.get("id","")

    colors = [acc, D["accent2"], D["muted"]]
    bc     = colors[min(level-1, 2)]

    with st.expander(f"{'#'*level} {sid} - {title}", expanded=(level==1)):

        if title != orig and orig:
            warn = D["warning"]
            st.markdown(
                f"<div style='background:{warn}11;border-left:3px solid {warn};"
                f"border-radius:6px;padding:0.3rem 0.7rem;margin-bottom:0.4rem;"
                f"font-size:0.78rem;color:{warn}'>"
                f"Enhanced from: {orig}</div>", unsafe_allow_html=True)

        c1, c2 = st.columns([3, 2])

        with c1:
            rg = sec.get("reviewer_guidance",[])
            if rg:
                danger = D["danger"]
                items  = rg if isinstance(rg, list) else [str(rg)]
                pts    = "".join(f"<div style='margin:2px 0'>&#8226; {p}</div>" for p in items)
                st.markdown(
                    f"<div style='background:{danger}11;border-left:4px solid {danger};"
                    f"border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.5rem'>"
                    f"<strong style='color:{danger}'>REVIEWER EXPECTS:</strong><br>"
                    f"<div style='color:{D["text"]};font-size:0.84rem;margin-top:0.25rem'>"
                    f"{pts}</div></div>", unsafe_allow_html=True)

            pc = sec.get("policy_connections",[])
            if pc:
                blue  = "#4488CC"
                items = pc if isinstance(pc, list) else [str(pc)]
                if items and isinstance(items[0], dict):
                    pts = "".join(
                        f"<div style='margin:2px 0'>&#8226; <b>{p.get('policy','')}</b>"
                        + (f" - {p.get('how','')}" if p.get('how') else "") + "</div>"
                        for p in items)
                else:
                    pts = "".join(f"<div style='margin:2px 0'>&#8226; {p}</div>" for p in items)
                st.markdown(
                    f"<div style='background:{blue}11;border-left:4px solid {blue};"
                    f"border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.5rem'>"
                    f"<strong style='color:{blue}'>POLICY CONNECTIONS:</strong><br>"
                    f"<div style='color:{D["text"]};font-size:0.84rem;margin-top:0.25rem'>"
                    f"{pts}</div></div>", unsafe_allow_html=True)

        with c2:
            kws = sec.get("keywords_to_include",[])
            if kws:
                green = D["success"]
                kw_list = kws if isinstance(kws, list) else [str(kws)]
                st.markdown(
                    f"<div style='background:{green}11;border-left:4px solid {green};"
                    f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.4rem'>"
                    f"<strong style='color:{green}'>KEYWORDS:</strong><br>"
                    f"<span style='color:{D["text"]};font-size:0.82rem'>"
                    + " &nbsp;&#183;&nbsp; ".join(kw_list)
                    + "</span></div>", unsafe_allow_html=True)

            ev = sec.get("measures_and_evidence","")
            if ev:
                amber = D["warning"]
                st.markdown(
                    f"<div style='background:{amber}11;border-left:4px solid {amber};"
                    f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.4rem'>"
                    f"<strong style='color:{amber}'>EVIDENCE NEEDED:</strong><br>"
                    f"<span style='color:{D["text"]};font-size:0.82rem'>{ev}</span>"
                    f"</div>", unsafe_allow_html=True)

            wc = sec.get("word_count_guidance","")
            cm = sec.get("common_mistakes",[])
            if wc:
                st.caption(f"Length: {wc}")
            if cm:
                with st.expander("Common mistakes to avoid"):
                    for m in (cm if isinstance(cm,list) else [str(cm)]):
                        st.markdown(
                            f"<span style='color:{D["danger"]};font-size:0.81rem'>&#x2717; {m}</span>",
                            unsafe_allow_html=True)

st.markdown("<br>")
b1, b2 = st.columns(2)
with b1:
    if st.button("Run Mini Review", type="primary", use_container_width=True):
        st.switch_page("pages/mini_review.py")
with b2:
    if st.button("Back to Round 2a", use_container_width=True):
        st.switch_page("pages/round2a_concept.py")
