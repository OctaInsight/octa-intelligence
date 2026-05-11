"""Octa Intelligence — Dashboard."""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url, set_token_in_url, get_token_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, kpi_card, score_badge, DARK)
from modules.database import (get_all_proposals, get_policy_documents,
                               get_call_setup, get_call_analyses,
                               get_concept_evaluations, get_proposal_architectures,
                               get_architecture_review)
from config import DARK as D

st.set_page_config(page_title="Proposal Intelligence — Octa",
                   page_icon="🧠", layout="wide",
                   initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth()
token = st.session_state.get("sso_token","") or get_token_from_url()
if token: set_token_in_url(token)
sidebar_nav()

muted = D["muted"]; acc = D["accent"]
page_header("Proposal Intelligence",
            "AI-powered call analysis, strategy and proposal positioning",
            "🧠")

# ── Policy Library stats ──────────────────────────────────────────────────────
all_docs  = get_policy_documents()
core_docs = [d for d in all_docs if d.get("tier")=="core"]
prog_docs = [d for d in all_docs if d.get("tier")=="programme"]
call_docs = [d for d in all_docs if d.get("tier")=="call_specific"]

section_label("📚 Policy Library Status")
k1,k2,k3,k4 = st.columns(4)
kpi_card(k1,"Total Documents", len(all_docs),  acc)
kpi_card(k2,"Core Policies",   len(core_docs), D["success"])
kpi_card(k3,"Programme-level", len(prog_docs), D["accent2"])
kpi_card(k4,"Call-specific",   len(call_docs), D["warning"])

if len(all_docs) == 0:
    bg2=D["bg2"]; border=D["border"]
    st.markdown(
        f"<div style='background:{bg2};border-left:4px solid {acc};"
        f"border-radius:10px;padding:1rem 1.3rem;margin:0.5rem 0'>"
        f"<strong style='color:{acc}'>Start by building your Policy Library</strong><br>"
        f"<span style='color:{muted};font-size:0.85rem'>"
        f"Go to 📚 Policy Library to upload your first policy documents "
        f"(European Green Deal, Horizon Europe Work Programme, etc.)</span></div>",
        unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Proposal selector ──────────────────────────────────────────────────────────
section_label("📋 Select Proposal to Work On")
proposals = get_all_proposals()
if not proposals:
    st.warning("No proposals found. Create proposals in the Proposal Tracking app first.")
    st.stop()

proj_opts = {
    f"{p.get('acronym','').strip() or p['proposal_id']} — {p.get('proposal_title','')[:50]}": p["proposal_id"]
    for p in proposals
}

cur_pid   = st.session_state.get("selected_proposal_id","")
cur_label = next((l for l,v in proj_opts.items() if v==cur_pid), None)
def_idx   = list(proj_opts.keys()).index(cur_label) if cur_label else 0

sel_label = st.selectbox("Select Proposal", list(proj_opts.keys()),
                          index=def_idx, key="intel_proj")
sel_pid   = proj_opts[sel_label]
if sel_pid != cur_pid:
    st.session_state["selected_proposal_id"] = sel_pid; st.rerun()

# ── Intelligence pipeline status ──────────────────────────────────────────────
section_label("🔄 Intelligence Pipeline")
call_setup  = get_call_setup(sel_pid)
analyses    = get_call_analyses(sel_pid)
concepts    = get_concept_evaluations(sel_pid)
archs       = get_proposal_architectures(sel_pid)

latest_analysis = analyses[0]    if analyses else None
latest_concept  = concepts[0]    if concepts else None
latest_arch     = archs[0]       if archs    else None
latest_review   = get_architecture_review(latest_arch["id"]) if latest_arch else None

steps = [
    {
        "icon": "⚙️",
        "label": "Call Setup",
        "done":  call_setup is not None,
        "status": "✅ Complete" if call_setup else "⭕ Not started",
        "detail": f"Programme: {call_setup.get('programme','')}" if call_setup else "Upload call text and select documents",
        "page":  "pages/call_setup.py",
    },
    {
        "icon": "🔍",
        "label": "Round 1 — Call Analysis",
        "done":  latest_analysis is not None and latest_analysis.get("status")=="complete",
        "status": ("✅ Complete" if latest_analysis and latest_analysis.get("status")=="complete"
                   else "🔄 Processing" if latest_analysis and latest_analysis.get("status")=="processing"
                   else "⭕ Not started"),
        "detail": f"Completed: {str(latest_analysis.get('completed_at',''))[:10]}" if latest_analysis and latest_analysis.get("completed_at") else "Run the call intelligence analysis",
        "page":  "pages/round1_analysis.py",
    },
    {
        "icon": "📝",
        "label": "Round 2a — Concept Check",
        "done":  latest_concept is not None,
        "status": f"✅ Score: {latest_concept.get('overall_alignment_score',0):.0f}/100" if latest_concept else "⭕ Optional",
        "detail": "Evaluate your concept note alignment" if not latest_concept else f"{len(latest_concept.get('gaps',[]))} gaps identified",
        "page":  "pages/round2a_concept.py",
    },
    {
        "icon": "🏗️",
        "label": "Round 2b — Architecture",
        "done":  latest_arch is not None and latest_arch.get("status")=="complete",
        "status": ("✅ Complete" if latest_arch and latest_arch.get("status")=="complete"
                   else "⭕ Not started"),
        "detail": f"{latest_arch.get('total_sections',0)} sections generated" if latest_arch and latest_arch.get("status")=="complete" else "Generate annotated proposal skeleton",
        "page":  "pages/round2b_architecture.py",
    },
    {
        "icon": "🎯",
        "label": "Mini Review",
        "done":  latest_review is not None,
        "status": f"✅ Score: {latest_review.get('overall_score',0):.0f}/100" if latest_review else "⭕ Not started",
        "detail": "Architecture review against reviewer criteria",
        "page":  "pages/mini_review.py",
    },
]

for step in steps:
    bg2=D["bg2"]; border=D["border"]; txt=D["text"]
    color = D["success"] if step["done"] else D["muted"]
    st.markdown(
        f"<div style='background:{bg2};border:1px solid {border};"
        f"border-left:5px solid {color};border-radius:10px;"
        f"padding:0.8rem 1.2rem;margin-bottom:0.5rem;"
        f"display:flex;align-items:center;gap:1.2rem;flex-wrap:wrap'>"
        f"<span style='font-size:1.3rem'>{step['icon']}</span>"
        f"<div style='flex:1'>"
        f"<strong style='color:{txt}'>{step['label']}</strong>"
        f"<span style='color:{color};margin-left:0.8rem;font-size:0.82rem'>{step['status']}</span>"
        f"<br><span style='color:{muted};font-size:0.8rem'>{step['detail']}</span>"
        f"</div></div>", unsafe_allow_html=True)
    if st.button(f"Open {step['label']}", key=f"step_{step['label']}", use_container_width=False):
        st.switch_page(step["page"])

# ── Recent analyses ───────────────────────────────────────────────────────────
if analyses:
    section_label(f"📊 Analysis History ({len(analyses)} runs)")
    for a in analyses[:5]:
        status    = a.get("status","pending")
        s_color   = D["success"] if status=="complete" else (D["warning"] if status=="processing" else D["muted"])
        api_mode  = a.get("api_mode","realtime")
        bg2=D["bg2"]; border=D["border"]; txt=D["text"]
        st.markdown(
            f"<div style='background:{bg2};border:1px solid {border};"
            f"border-radius:8px;padding:0.5rem 0.9rem;margin-bottom:0.3rem;"
            f"font-size:0.83rem;display:flex;gap:1.5rem;flex-wrap:wrap'>"
            f"<span style='color:{s_color};font-weight:600'>{status.title()}</span>"
            f"<span style='color:{muted}'>{str(a.get('created_at',''))[:10]}</span>"
            f"<span style='color:{muted}'>{api_mode}</span>"
            + (f"<span style='color:{D["success"]}'>✅ Complete</span>" if status=="complete" else "")
            + "</div>", unsafe_allow_html=True)
