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
        result = run_round2a(concept_text, analysis)

    if result:
        ok, _ = create_concept_evaluation({
            "proposal_id":          sel_pid,
            "call_analysis_id":     analysis["id"],
            "concept_text":         concept_text,
            "overall_alignment_score": result.get("overall_alignment_score",0),
            "scores_by_dimension":  result.get("scores_by_dimension",{}),
            "gaps":                 result.get("gaps",[]),
            "strengths":            result.get("strengths",[]),
            "recommendations":      result.get("recommendations",[]),
            "raw_response":         str(result)[:5000],
        })
        if ok: st.success("✅ Evaluation complete!"); st.rerun()
    else:
        st.error("❌ Evaluation failed. Please try again.")

# ── Results ───────────────────────────────────────────────────────────────────
if not evaluations:
    st.stop()

ev = evaluations[0]
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
