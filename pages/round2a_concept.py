"""Octa Intelligence — Round 2a: Concept Note Evaluation."""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, score_badge, DARK)
from modules.database import (get_call_analyses, get_concept_evaluations,
                               create_concept_evaluation, get_proposal)
from modules.claude_client import run_round2a
from config import DARK as D

st.set_page_config(page_title="Concept Evaluation — Octa", page_icon="📝",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

sel_pid = st.session_state.get("selected_proposal_id","")
if not sel_pid: st.switch_page("app.py"); st.stop()

proj    = get_proposal(sel_pid)
acronym = proj.get("acronym","") or sel_pid
page_header("Round 2a — Concept Note Evaluation",
            f"{acronym} — Check how well your concept aligns with the call intelligence",
            "📝")
if st.button("← Dashboard"): st.switch_page("app.py")

muted = D["muted"]; acc = D["accent"]

analyses   = get_call_analyses(sel_pid)
complete   = [a for a in analyses if a.get("status")=="complete"]
evaluations= get_concept_evaluations(sel_pid)

if not complete:
    st.warning("Complete Round 1 analysis first.")
    if st.button("→ Round 1"): st.switch_page("pages/round1_analysis.py")
    st.stop()

analysis = complete[0]

# ── Input concept note ────────────────────────────────────────────────────────
section_label("📝 Your Concept Note")
st.markdown(
    f"<p style='color:{muted};font-size:0.85rem'>"
    f"Paste your concept note below. This can be a rough summary of your idea — "
    f"it doesn't need to be polished. The AI will evaluate how well it addresses "
    f"the call requirements identified in Round 1.</p>",
    unsafe_allow_html=True)

concept_text = st.text_area(
    "Concept Note",
    height=350,
    placeholder="Paste your concept note, project summary or proposal abstract here…\n\n"
                "Include:\n• What problem you're solving\n• Your approach/methodology\n"
                "• Expected outcomes and impacts\n• Who your partners are and what they bring\n"
                "• How this connects to EU policy priorities",
    label_visibility="collapsed"
)

if st.button("📝 Evaluate Concept Note", type="primary",
             use_container_width=True, disabled=not concept_text.strip()):
    with st.spinner("Evaluating your concept against the call intelligence…"):
        result, raw_text = run_round2a(concept_text, analysis)

    if raw_text:
        ok, eval_id = create_concept_evaluation({
            "proposal_id":             sel_pid,
            "call_analysis_id":        analysis["id"],
            "concept_text":            concept_text,
            "overall_alignment_score": result.get("overall_alignment_score", 0) if result else 0,
            "scores_by_dimension":     result.get("scores_by_dimension", {}) if result else {},
            "gaps":                    result.get("gaps", [])            if result else [],
            "strengths":               result.get("strengths", [])       if result else [],
            "recommendations":         result.get("recommendations", []) if result else [],
            "raw_response":            raw_text[:8000],
        })
        if ok:
            if result:
                st.success("✅ Evaluation complete!")
            else:
                st.warning("⚠ Response saved but JSON could not be parsed. "
                           "Click Re-Parse below to retry.")
            st.rerun()
    else:
        st.error("❌ Claude returned no response. Check your API key.")

# ── Results ───────────────────────────────────────────────────────────────────
if not evaluations:
    st.stop()

ev = evaluations[0]

# Check if structured data exists
_has_scores = bool(ev.get("scores_by_dimension") or ev.get("gaps") or ev.get("strengths"))
_raw_ev     = ev.get("raw_response", "")

if not _has_scores and _raw_ev:
    warn = D["warning"]
    st.markdown(
        f"<div style='background:{warn}22;border:1px solid {warn};border-radius:10px;"
        f"padding:0.9rem 1.2rem;margin-bottom:0.8rem'>"
        f"<strong style='color:{warn}'>⚠ Structured results could not be parsed.</strong><br>"
        f"<span style='color:{D["muted"]};font-size:0.84rem'>"
        f"The raw AI response is shown below. Click Re-Parse to try extracting structured data.</span>"
        f"</div>", unsafe_allow_html=True)

    if st.button("🔄 Re-Parse", type="primary", key="reparse_2a"):
        from modules.claude_client import _parse_json_response
        r2 = _parse_json_response(_raw_ev)
        if r2:
            from modules.database import db
            db().table("concept_evaluations").update({
                "overall_alignment_score": r2.get("overall_alignment_score", 0),
                "scores_by_dimension":     r2.get("scores_by_dimension", {}),
                "gaps":                    r2.get("gaps", []),
                "strengths":               r2.get("strengths", []),
                "recommendations":         r2.get("recommendations", []),
            }).eq("id", ev["id"]).execute()
            st.success("✅ Re-parsed!"); st.rerun()
        else:
            st.error("Still could not parse. See raw response below.")

    with st.expander("📄 Raw AI Response", expanded=True):
        st.markdown(
            f"<div style='background:{D["bg2"]};border-radius:8px;padding:1rem;"
            f"white-space:pre-wrap;font-size:0.83rem;color:{D["text"]}'>"
            f"{_raw_ev}</div>", unsafe_allow_html=True)
    st.stop()

section_label("📊 Evaluation Results")

# Score overview
overall = ev.get("overall_alignment_score",0)
verdict = ev.get("readiness_verdict","")
verdict_colors = {
    "strong":"#6fcf97","promising":"#00BCD4",
    "needs_work":"#f6cc52","significant_revision_needed":"#fc8181"
}
vcol = verdict_colors.get(verdict, D["muted"])

sc1,sc2 = st.columns([1,3])
with sc1:
    st.markdown(
        f"<div style='background:{D["bg2"]};border-radius:12px;padding:1.5rem;text-align:center'>"
        f"<div style='font-size:2.5rem;font-weight:700;color:{'#6fcf97' if overall>=75 else ('#f6cc52' if overall>=50 else '#fc8181')}'>"
        f"{overall:.0f}</div>"
        f"<div style='font-size:0.9rem;color:{D["muted"]}'>/ 100</div>"
        f"<div style='margin-top:0.5rem;background:{vcol}22;color:{vcol};"
        f"border-radius:8px;padding:4px 10px;font-size:0.78rem;font-weight:600'>"
        f"{verdict.replace('_',' ').title()}</div></div>",
        unsafe_allow_html=True)

with sc2:
    dims = ev.get("scores_by_dimension",{})
    for dim, data in dims.items():
        score = data.get("score",0) if isinstance(data,dict) else data
        comment = data.get("comment","") if isinstance(data,dict) else ""
        scolor = D["success"] if score>=75 else (D["warning"] if score>=50 else D["danger"])
        st.markdown(
            f"<div style='background:{D["bg2"]};border-left:4px solid {scolor};"
            f"border-radius:8px;padding:0.5rem 0.9rem;margin-bottom:0.4rem'>"
            f"<div style='display:flex;justify-content:space-between'>"
            f"<strong style='color:{D["text"]}'>{dim.title()}</strong>"
            f"<span style='color:{scolor};font-weight:700'>{score}/100</span></div>"
            + (f"<span style='color:{D["muted"]};font-size:0.8rem'>{comment}</span>" if comment else "")
            + "</div>", unsafe_allow_html=True)

# Overall comment
if ev.get("overall_comment"):
    bg2=D["bg2"]; border=D["border"]
    st.markdown(
        f"<div style='background:{bg2};border-left:4px solid {acc};"
        f"border-radius:8px;padding:0.9rem 1.1rem;margin:0.8rem 0'>"
        f"{ev['overall_comment']}</div>",
        unsafe_allow_html=True)

# Gaps and Strengths
gt1, gt2 = st.columns(2)
with gt1:
    section_label("❌ Gaps to Address")
    for gap in ev.get("gaps",[]):
        sev = gap.get("severity","medium")
        sc  = D["danger"] if sev=="high" else (D["warning"] if sev=="medium" else D["muted"])
        bg2=D["bg2"]
        st.markdown(
            f"<div style='background:{bg2};border-left:3px solid {sc};"
            f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.4rem'>"
            f"<strong style='color:{sc}'>[{sev.title()}] {gap.get('dimension','').title()}</strong><br>"
            f"<span style='color:{D["text"]};font-size:0.84rem'>{gap.get('description','')}</span><br>"
            + (f"<span style='color:{D["muted"]};font-size:0.78rem'>💡 {gap.get('suggestion','')}</span>" if gap.get("suggestion") else "")
            + "</div>", unsafe_allow_html=True)

with gt2:
    section_label("✅ Strengths")
    for strength in ev.get("strengths",[]):
        suc=D["success"]; bg2=D["bg2"]
        st.markdown(
            f"<div style='background:{bg2};border-left:3px solid {suc};"
            f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.4rem'>"
            f"<strong style='color:{suc}'>{strength.get('dimension','').title()}</strong><br>"
            f"<span style='color:{D["text"]};font-size:0.84rem'>{strength.get('description','')}</span>"
            + (f"<br><span style='color:{D["muted"]};font-size:0.78rem;font-style:italic'>{strength.get('evidence','')}</span>" if strength.get("evidence") else "")
            + "</div>", unsafe_allow_html=True)

section_label("💡 Recommendations")
for rec in sorted(ev.get("recommendations",[]), key=lambda r: r.get("priority",99)):
    bg2=D["bg2"]; acc2=D["accent"]
    st.markdown(
        f"<div style='background:{bg2};border-left:4px solid {acc2};"
        f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.4rem'>"
        f"<strong style='color:{acc2}'>Priority {rec.get('priority','')}: {rec.get('action','')}</strong><br>"
        f"<span style='color:{D["muted"]};font-size:0.82rem'>{rec.get('rationale','')}</span>"
        f"</div>", unsafe_allow_html=True)

st.markdown("<br>")
if st.button("→ Proceed to Round 2b — Proposal Architecture", type="primary"):
    st.switch_page("pages/round2b_architecture.py")
