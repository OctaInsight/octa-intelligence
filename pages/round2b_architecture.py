"""Octa Intelligence — Round 2b: Proposal Architecture."""
import streamlit as st
import json
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, DARK)
from modules.database import (get_call_analyses, get_call_setup,
                               get_concept_evaluations,
                               get_proposal_architectures,
                               create_proposal_architecture,
                               update_proposal_architecture, get_proposal)
from modules.claude_client import run_round2b
from modules.word_export import export_architecture_docx
from config import DARK as D, PROGRAMMES, PROGRAMME_NAMES

st.set_page_config(page_title="Architecture — Octa", page_icon="🏗️",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

sel_pid = st.session_state.get("selected_proposal_id","")
if not sel_pid: st.switch_page("app.py"); st.stop()

proj    = get_proposal(sel_pid)
acronym = proj.get("acronym","") or sel_pid
page_header("Round 2b — Proposal Architecture",
            f"{acronym} — AI-annotated proposal skeleton with reviewer guidance",
            "🏗️")
if st.button("← Dashboard"): st.switch_page("app.py")

muted = D["muted"]; acc = D["accent"]
user_id = st.session_state.get("user_id")

analyses = get_call_analyses(sel_pid)
complete = [a for a in analyses if a.get("status")=="complete"]
setup    = get_call_setup(sel_pid)
concepts = get_concept_evaluations(sel_pid)
archs    = get_proposal_architectures(sel_pid)

if not complete:
    st.warning("Complete Round 1 analysis first.")
    if st.button("→ Round 1"): st.switch_page("pages/round1_analysis.py")
    st.stop()

analysis = complete[0]
latest_concept = concepts[0] if concepts else None

# ── Generate architecture ──────────────────────────────────────────────────────
section_label("🏗️ Generate Proposal Architecture")

programme = setup.get("programme","Horizon Europe — RIA") if setup else "Horizon Europe — RIA"
prog_info = PROGRAMMES.get(programme,{})

# Option: user can customise section titles before generating
with st.expander("⚙️ Customise Structure (optional)", expanded=not archs):
    st.markdown(
        f"<p style='color:{muted};font-size:0.84rem'>"
        f"Using pre-built structure for <strong>{programme}</strong>. "
        f"You can add custom titles for any section — the AI will use yours as a starting point "
        f"and suggest improvements.</p>",
        unsafe_allow_html=True)

    template_sections = prog_info.get("structure",[])
    user_titles = {}

    if template_sections:
        for sec in template_sections:
            sid   = sec.get("id","")
            level = sec.get("level",1)
            default_title = sec.get("title","")
            indent = "  " * (level - 1)
            custom = st.text_input(
                f"{indent}Section {sid}",
                value=default_title,
                key=f"title_{sid}"
            )
            if custom != default_title:
                user_titles[sid] = custom
    else:
        st.info("Using custom structure — AI will generate a structure based on the call.")

col_api1, col_api2 = st.columns(2)
with col_api1:
    api_mode = st.radio("API Mode",
        ["⚡ Real-time","💤 Batch (24h, 50% cheaper)"],
        horizontal=True, key="arch_api")
    is_batch = "Batch" in api_mode

if st.button("🏗️ Generate Architecture", type="primary", use_container_width=True):
    with st.spinner("Generating annotated proposal architecture… this may take 2-4 minutes…"):
        result = run_round2b(
            structure_template    = template_sections,
            call_analysis         = analysis,
            concept_evaluation    = latest_concept,
            programme             = programme,
            user_custom_titles    = user_titles if user_titles else None,
        )

    if result:
        sections      = result.get("sections",[])
        total_sections= sum(1 for s in sections if s.get("level",1) == 1)
        total_sub     = sum(1 for s in sections if s.get("level",1) > 1)
        from datetime import datetime, timezone
        ok, arch_id = create_proposal_architecture({
            "proposal_id":         sel_pid,
            "call_analysis_id":    analysis["id"],
            "concept_evaluation_id": latest_concept["id"] if latest_concept else None,
            "api_mode":            "realtime",
            "status":              "complete",
            "programme":           programme,
            "structure_type":      setup.get("structure_type","pre_built") if setup else "pre_built",
            "sections":            sections,
            "total_sections":      total_sections,
            "total_subsections":   total_sub,
            "raw_response":        str(result)[:5000],
            "completed_at":        datetime.now(timezone.utc).isoformat(),
        })
        if ok:
            st.success("✅ Architecture generated!"); st.rerun()
        else:
            st.error(f"❌ Save failed: {arch_id}")
    else:
        st.error("❌ Architecture generation failed. Please try again.")

# ── Display architecture ───────────────────────────────────────────────────────
if not archs:
    st.stop()

# Version selector
if len(archs) > 1:
    arch_idx = st.selectbox("Architecture version",
        range(len(archs)),
        format_func=lambda i: f"v{len(archs)-i}: {str(archs[i].get('created_at',''))[:10]}",
        key="arch_sel")
    arch = archs[arch_idx]
else:
    arch = archs[0]

if arch.get("status") != "complete":
    st.info("Architecture not yet complete."); st.stop()

sections = arch.get("sections",[])
if not sections:
    st.info("No sections in this architecture."); st.stop()

section_label("📋 Proposal Architecture")

# Download
doc_bytes = export_architecture_docx(arch, analysis, sel_pid, acronym)
st.download_button(
    "📥 Download Annotated Architecture (Word)",
    data=doc_bytes,
    file_name=f"{acronym}_Proposal_Architecture.docx",
    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    key="dl_arch"
)

st.markdown(
    f"<p style='color:{muted};font-size:0.84rem'>"
    f"🔴 Red = Reviewer guidance  · 🔵 Blue = Policy connections  · "
    f"🟢 Green = Keywords  · 🟡 Amber = Evidence needed</p>",
    unsafe_allow_html=True)

# General advice
if arch.get("general_advice"):
    with st.expander("💡 General Strategic Advice", expanded=True):
        bg2=D["bg2"]
        st.markdown(
            f"<div style='background:{bg2};border-radius:8px;padding:1rem'>"
            f"{arch['general_advice']}</div>",
            unsafe_allow_html=True)

# Section tree
for sec in sorted(sections, key=lambda s: s.get("order",0)):
    level = sec.get("level",1)
    title = sec.get("ai_title","") or sec.get("original_title","")
    orig  = sec.get("original_title","")

    # Indentation for sub-sections
    indent = "　" * (level - 1)
    header = f"{indent}{'#'*level} {sec.get('id','')} — {title}"

    with st.expander(header, expanded=(level==1)):
        # Title enhancement note
        if sec.get("ai_title") and sec.get("ai_title") != orig:
            warn=D["warning"]
            st.markdown(
                f"<div style='background:{warn}11;border-left:3px solid {warn};"
                f"border-radius:6px;padding:0.4rem 0.7rem;margin-bottom:0.5rem;font-size:0.8rem'>"
                f"💡 Original title: <em>{orig}</em> → Enhanced to align with call language</div>",
                unsafe_allow_html=True)
        if sec.get("title_rationale"):
            st.caption(f"Why this title works: {sec['title_rationale']}")

        # Reviewer guidance (RED)
        if sec.get("reviewer_guidance"):
            danger=D["danger"]
            st.markdown(
                f"<div style='background:{danger}11;border-left:4px solid {danger};"
                f"border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.5rem'>"
                f"<strong style='color:{danger}'>🔴 REVIEWER EXPECTS:</strong><br>"
                + "<br>".join(f"• {p}" for p in sec["reviewer_guidance"])
                + "</div>", unsafe_allow_html=True)

        # Policy connections (BLUE)
        if sec.get("policy_connections"):
            blue="#4488CC"
            st.markdown(
                f"<div style='background:{blue}11;border-left:4px solid {blue};"
                f"border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.5rem'>"
                f"<strong style='color:{blue}'>🔵 POLICY CONNECTIONS:</strong><br>"
                + "<br>".join(f"• {p.get('policy','')} — {p.get('how','')}" for p in sec["policy_connections"])
                + "</div>", unsafe_allow_html=True)

        # Keywords (GREEN)
        if sec.get("keywords_to_include"):
            green=D["success"]
            st.markdown(
                f"<div style='background:{green}11;border-left:4px solid {green};"
                f"border-radius:8px;padding:0.5rem 0.9rem;margin-bottom:0.5rem'>"
                f"<strong style='color:{green}'>🟢 KEYWORDS:</strong> "
                + " · ".join(sec["keywords_to_include"])
                + "</div>", unsafe_allow_html=True)

        # Evidence (AMBER)
        if sec.get("measures_and_evidence"):
            amber=D["warning"]
            st.markdown(
                f"<div style='background:{amber}11;border-left:4px solid {amber};"
                f"border-radius:8px;padding:0.5rem 0.9rem;margin-bottom:0.5rem'>"
                f"<strong style='color:{amber}'>🟡 EVIDENCE & MEASURES:</strong> "
                + sec["measures_and_evidence"]
                + "</div>", unsafe_allow_html=True)

        # Word count + common mistakes
        row_c1, row_c2 = st.columns(2)
        with row_c1:
            if sec.get("word_count_guidance"):
                st.caption(f"📏 {sec['word_count_guidance']}")
        with row_c2:
            if sec.get("common_mistakes"):
                with st.expander("⚠ Common mistakes to avoid"):
                    for m in sec["common_mistakes"]:
                        st.markdown(f"✗ {m}")

st.markdown("<br>")
if st.button("→ Run Mini Review of Architecture", type="primary"):
    st.switch_page("pages/mini_review.py")
