"""Octa Intelligence — Round 1: Call Analysis."""
import streamlit as st
import json
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, DARK)
from modules.database import (get_call_setup, get_consortium_briefing,
                               get_policy_documents, get_policy_document,
                               get_call_analyses, create_call_analysis,
                               update_call_analysis, increment_doc_usage,
                               get_proposal)
from modules.claude_client import run_round1_realtime
from modules.word_export import export_round1_docx
from config import DARK as D

st.set_page_config(page_title="Round 1 Analysis — Octa", page_icon="🔍",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

sel_pid = st.session_state.get("selected_proposal_id","")
if not sel_pid:
    st.switch_page("app.py"); st.stop()

proj    = get_proposal(sel_pid)
acronym = proj.get("acronym","") or sel_pid
page_header("Round 1 — Call Intelligence Analysis",
            f"{acronym} — AI-powered strategic intelligence from call + policy + consortium briefing",
            "🔍")
if st.button("← Dashboard"): st.switch_page("app.py")

muted = D["muted"]; acc = D["accent"]

setup    = get_call_setup(sel_pid)
briefing = get_consortium_briefing(sel_pid)
analyses = get_call_analyses(sel_pid)

# ── Readiness check ───────────────────────────────────────────────────────────
if not setup:
    warn=D["warning"]
    st.markdown(
        f"<div style='background:{warn}22;border:1px solid {warn};border-radius:10px;"
        f"padding:1rem 1.3rem'>"
        f"<strong style='color:{warn}'>⚠ Call Setup Required</strong><br>"
        f"<span style='color:{muted}'>Complete the Call Setup before running the analysis.</span></div>",
        unsafe_allow_html=True)
    if st.button("→ Go to Call Setup"): st.switch_page("pages/call_setup.py")
    st.stop()

if not setup.get("call_text","").strip():
    st.error("❌ No call text found. Please upload the call text in Call Setup.")
    if st.button("→ Call Setup"): st.switch_page("pages/call_setup.py")
    st.stop()

# ── Run new analysis ──────────────────────────────────────────────────────────
section_label("🚀 Run New Analysis")

col_cfg1, col_cfg2 = st.columns(2)
with col_cfg1:
    api_mode = st.radio(
        "API Mode",
        ["⚡ Real-time (minutes)", "💤 Batch API (up to 24h, 50% cheaper)"],
        horizontal=True
    )
    is_batch = "Batch" in api_mode

with col_cfg2:
    # Show what will be included
    doc_ids   = setup.get("selected_policy_doc_ids",[])
    if isinstance(doc_ids, str):
        try:    doc_ids = json.loads(doc_ids)
        except: doc_ids = []
    has_guide = setup.get("has_reviewer_guide", False)
    has_brief = briefing is not None

    bg2=D["bg2"]; border=D["border"]; txt=D["text"]
    st.markdown(
        f"<div style='background:{bg2};border-radius:8px;padding:0.8rem 1rem;"
        f"font-size:0.83rem'>"
        f"<strong style='color:{txt}'>What will be analysed:</strong><br>"
        f"<span style='color:{acc}'>✅</span> Call text ({len(setup.get('call_text','').split()):,} words)<br>"
        f"<span style='color:{acc if doc_ids else muted}'>{'✅' if doc_ids else '○'}</span> {len(doc_ids)} policy document(s)<br>"
        f"<span style='color:{acc if has_guide else muted}'>{'✅' if has_guide else '○'}</span> Reviewer guidelines<br>"
        f"<span style='color:{acc if has_brief else muted}'>{'✅' if has_brief else '○'}</span> Consortium briefing"
        f"</div>", unsafe_allow_html=True)

if st.button("🔍 Run Round 1 Analysis", type="primary", use_container_width=True):
    if is_batch:
        st.info("🔄 Batch API mode — analysis will be submitted and results available within 24 hours. "
                "This feature requires additional setup. Using real-time for now.")

    with st.spinner("Reading documents and briefing the AI… this may take 2-3 minutes…"):
        # Load policy document texts
        policy_texts = {}
        for did in doc_ids:
            doc = get_policy_document(did)
            if doc:
                text = doc.get("text_content","") or doc.get("text_summary","")
                if text:
                    policy_texts[doc["title"]] = text[:40000]

        # Build briefing dict
        briefing_dict = {}
        if briefing:
            briefing_dict = {
                "coordinator_name":    proj.get("coordinator",""),
                "coordinator_type":    "",
                "consortium_strategy": briefing.get("consortium_strategy",""),
                "unique_selling_point":briefing.get("unique_selling_point",""),
                "competitive_advantage":briefing.get("competitive_advantage",""),
                "geographic_rationale":briefing.get("geographic_rationale",""),
                "innovation_type":     briefing.get("innovation_type",""),
                "additional_notes":    briefing.get("additional_notes",""),
                "partner_profiles":    briefing.get("partner_profiles",[]),
            }

        # Create analysis record
        ok, analysis_id = create_call_analysis({
            "proposal_id":   sel_pid,
            "call_setup_id": setup.get("id"),
            "api_mode":      "realtime",
            "status":        "processing",
        })

        if not ok:
            st.error("Failed to create analysis record."); st.stop()

        # Run the analysis
        result = run_round1_realtime(
            call_text    = setup.get("call_text",""),
            policy_texts = policy_texts,
            guide_text   = setup.get("guide_text","") if has_guide else "",
            briefing     = briefing_dict,
        )

        if result:
            from datetime import datetime, timezone
            update_call_analysis(analysis_id, {
                "status":                   "complete",
                "call_objectives":          result.get("call_objectives",[]),
                "expected_outcomes":        result.get("expected_outcomes",[]),
                "expected_impacts":         result.get("expected_impacts",[]),
                "expected_outputs":         result.get("expected_outputs",[]),
                "recommended_kpis":         result.get("recommended_kpis",[]),
                "policy_framing":           result.get("policy_framing",{}),
                "master_keywords":          result.get("master_keywords",[]),
                "synergy_initiatives":      result.get("synergy_initiatives",[]),
                "hidden_messages":          result.get("hidden_messages",""),
                "expected_partner_profiles":result.get("expected_partner_profiles",[]),
                "consortium_positioning":   result.get("consortium_positioning",""),
                "strategic_recommendations":result.get("strategic_recommendations",[]),
                "raw_response":             str(result)[:10000],
                "completed_at":             datetime.now(timezone.utc).isoformat(),
            })
            increment_doc_usage(doc_ids)
            st.success("✅ Analysis complete!"); st.rerun()
        else:
            update_call_analysis(analysis_id, {
                "status": "failed",
                "error_message": "Claude returned no result"
            })
            st.error("❌ Analysis failed. Please try again.")

# ── Display results ───────────────────────────────────────────────────────────
if not analyses:
    st.info("No analyses run yet. Click the button above to start.")
    st.stop()

# Select which analysis to view
if len(analyses) > 1:
    sel_analysis_idx = st.selectbox(
        "View analysis run",
        range(len(analyses)),
        format_func=lambda i: f"Run {len(analyses)-i}: {str(analyses[i].get('created_at',''))[:10]} — {analyses[i].get('status','')}",
        key="sel_analysis"
    )
    analysis = analyses[sel_analysis_idx]
else:
    analysis = analyses[0]

if analysis.get("status") != "complete":
    s = analysis.get("status","pending")
    st.warning(f"Analysis status: {s.title()}. Results will appear when complete.")
    st.stop()

section_label("📊 Analysis Results")

# Download Word doc
docx_bytes = export_round1_docx(analysis, sel_pid, acronym)
st.download_button(
    "📥 Download Full Analysis (Word)",
    data=docx_bytes,
    file_name=f"{acronym}_Round1_Analysis.docx",
    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    key="dl_r1"
)

st.markdown("<br>", unsafe_allow_html=True)

# Results in tabs
rt1,rt2,rt3,rt4,rt5,rt6 = st.tabs([
    "🎯 Objectives & Outcomes",
    "📋 Policy & Keywords",
    "🤝 Partners & Synergies",
    "💡 Hidden Messages",
    "📍 Our Positioning",
    "⭐ Recommendations",
])

def _list_items(items, key_field="", label_field=""):
    if not items: st.info("No data."); return
    for item in items:
        if isinstance(item, dict):
            title = item.get(label_field or list(item.keys())[0],"")
            rest  = {k:v for k,v in item.items() if k!=label_field}
            with st.expander(str(title)[:80], expanded=False):
                for k,v in rest.items():
                    if v:
                        st.markdown(f"**{k.replace('_',' ').title()}:** {v}")
        else:
            st.markdown(f"• {item}")

with rt1:
    st.markdown(f"#### 🎯 Call Objectives")
    _list_items(analysis.get("call_objectives",[]), label_field="title")
    st.markdown(f"#### 🎯 Expected Outcomes")
    _list_items(analysis.get("expected_outcomes",[]), label_field="outcome")
    st.markdown(f"#### 🎯 Expected Impacts")
    _list_items(analysis.get("expected_impacts",[]), label_field="impact")
    st.markdown(f"#### 🎯 Expected Outputs")
    _list_items(analysis.get("expected_outputs",[]), label_field="output")
    st.markdown(f"#### 📊 Recommended KPIs")
    _list_items(analysis.get("recommended_kpis",[]), label_field="kpi")

with rt2:
    pf = analysis.get("policy_framing",{})
    if pf.get("policy_narrative"):
        bg2=D["bg2"]; border=D["border"]
        st.markdown(
            f"<div style='background:{bg2};border-left:4px solid {acc};"
            f"border-radius:8px;padding:0.8rem 1rem;margin-bottom:0.8rem'>"
            f"{pf['policy_narrative']}</div>",
            unsafe_allow_html=True)
    st.markdown("#### Primary Policies")
    _list_items(pf.get("primary_policies",[]), label_field="policy")
    st.markdown("#### Keywords")
    kws = analysis.get("master_keywords",[])
    critical = [k.get("keyword","") for k in kws if k.get("importance")=="critical"]
    high     = [k.get("keyword","") for k in kws if k.get("importance")=="high"]
    if critical:
        danger=D["danger"]
        st.markdown(f"**🔴 Critical:** " + " · ".join(critical))
    if high:
        warn=D["warning"]
        st.markdown(f"**🟠 High:** " + " · ".join(high))

with rt3:
    st.markdown("#### Expected Partner Profiles")
    _list_items(analysis.get("expected_partner_profiles",[]), label_field="profile_type")
    st.markdown("#### Synergy Initiatives")
    _list_items(analysis.get("synergy_initiatives",[]), label_field="name")

with rt4:
    hidden = analysis.get("hidden_messages","")
    if hidden:
        bg2=D["bg2"]; border=D["border"]
        st.markdown(
            f"<div style='background:{bg2};border-left:4px solid {D['warning']};"
            f"border-radius:8px;padding:1rem 1.2rem'>{hidden}</div>",
            unsafe_allow_html=True)
    else:
        st.info("No hidden messages identified.")

with rt5:
    positioning = analysis.get("consortium_positioning","")
    if positioning:
        bg2=D["bg2"]
        st.markdown(
            f"<div style='background:{bg2};border-left:4px solid {D['success']};"
            f"border-radius:8px;padding:1rem 1.2rem'>{positioning}</div>",
            unsafe_allow_html=True)

with rt6:
    _list_items(analysis.get("strategic_recommendations",[]), label_field="recommendation")

st.markdown("<br>")
if st.button("→ Proceed to Round 2a — Concept Evaluation", type="primary"):
    st.switch_page("pages/round2a_concept.py")
