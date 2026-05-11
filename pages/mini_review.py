"""Octa Intelligence — Mini Review: Architecture vs Reviewer Criteria."""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, score_badge, DARK)
from modules.database import (get_proposal_architectures, get_call_setup,
                               get_architecture_review, create_architecture_review,
                               get_proposal)
from modules.claude_client import run_mini_review
from config import DARK as D

st.set_page_config(page_title="Mini Review — Octa", page_icon="🎯",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

sel_pid = st.session_state.get("selected_proposal_id","")
if not sel_pid: st.switch_page("app.py"); st.stop()

proj    = get_proposal(sel_pid)
acronym = proj.get("acronym","") or sel_pid
page_header("Mini Review — Architecture Quality Check",
            f"{acronym} — Quick scorecard against reviewer evaluation criteria",
            "🎯")
if st.button("← Dashboard"): st.switch_page("app.py")

muted = D["muted"]; acc = D["accent"]

archs  = get_proposal_architectures(sel_pid)
setup  = get_call_setup(sel_pid)
complete_archs = [a for a in archs if a.get("status")=="complete"]

if not complete_archs:
    st.warning("Generate a proposal architecture first.")
    if st.button("→ Round 2b"): st.switch_page("pages/round2b_architecture.py")
    st.stop()

arch   = complete_archs[0]
review = get_architecture_review(arch["id"])

# ── Run review ────────────────────────────────────────────────────────────────
section_label("🎯 Run Architecture Review")

has_guide = setup.get("has_reviewer_guide", False) if setup else False
guide_text= setup.get("guide_text","") if setup else ""
call_text = setup.get("call_text","") if setup else ""

reference_text  = guide_text if has_guide and guide_text else call_text
reference_used  = "guide" if has_guide and guide_text else "call_text"
reference_label = "Reviewer Guidelines" if reference_used == "guide" else "Call Text (no reviewer guide available)"

bg2=D["bg2"]; border=D["border"]; txt=D["text"]
st.markdown(
    f"<div style='background:{bg2};border-left:4px solid {acc};"
    f"border-radius:8px;padding:0.7rem 1rem;margin-bottom:0.8rem'>"
    f"<strong style='color:{txt}'>Reference document: {reference_label}</strong><br>"
    f"<span style='color:{muted};font-size:0.82rem'>"
    + ("Using your uploaded reviewer guidelines." if reference_used=="guide"
       else "No reviewer guide uploaded — using call text as evaluation reference instead.")
    + "</span></div>", unsafe_allow_html=True)

if st.button("🎯 Run Mini Review", type="primary", use_container_width=True,
             disabled=not reference_text.strip()):
    with st.spinner("Reviewing architecture against evaluation criteria…"):
        sections = arch.get("sections",[])
        result   = run_mini_review(
            architecture_sections = sections,
            reviewer_reference    = reference_text[:40000],
            has_guide             = (reference_used == "guide"),
        )

    if result:
        ok, _ = create_architecture_review({
            "proposal_id":           sel_pid,
            "architecture_id":       arch["id"],
            "overall_score":         result.get("overall_score",0),
            "section_scores":        result.get("section_scores",[]),
            "reviewer_reference_used": reference_used,
            "critical_gaps":         result.get("critical_gaps",[]),
            "quick_wins":            result.get("quick_wins",[]),
            "raw_response":          str(result)[:5000],
        })
        if ok: st.success("✅ Review complete!"); st.rerun()
    else:
        st.error("❌ Review failed. Please try again.")

if not reference_text.strip():
    st.warning("⚠ No call text found. Please complete the Call Setup first.")

# ── Display review ────────────────────────────────────────────────────────────
if not review:
    st.stop()

section_label("📊 Review Results")

overall = review.get("overall_score",0)
verdict = review.get("overall_verdict","")
VERDICT_COLORS = {
    "ready":"#6fcf97","mostly_ready":"#00BCD4",
    "needs_work":"#f6cc52","significant_gaps":"#fc8181"
}
vcol = VERDICT_COLORS.get(verdict, D["muted"])

# Score display
vc1,vc2,vc3,vc4 = st.columns(4)
for col, label, val, color in [
    (vc1,"Overall Score", f"{overall:.0f}/100", "#6fcf97" if overall>=75 else ("#f6cc52" if overall>=50 else "#fc8181")),
    (vc2,"Excellence",    f"{review.get('readiness_score_breakdown',{}).get('Excellence',0):.0f}/100", D["accent"]),
    (vc3,"Impact",        f"{review.get('readiness_score_breakdown',{}).get('Impact',0):.0f}/100", D["accent2"]),
    (vc4,"Implementation",f"{review.get('readiness_score_breakdown',{}).get('Implementation',0):.0f}/100", D["warning"]),
]:
    bg2=D["bg2"]
    col.markdown(
        f"<div style='background:{bg2};border-top:3px solid {color};"
        f"border:1px solid {color}44;border-radius:10px;padding:0.7rem;text-align:center'>"
        f"<div style='font-size:1.4rem;font-weight:700;color:{color}'>{val}</div>"
        f"<div style='font-size:0.72rem;color:{muted}'>{label}</div></div>",
        unsafe_allow_html=True)

# Verdict
if review.get("key_message"):
    st.markdown(
        f"<div style='background:{vcol}22;border:1px solid {vcol};border-radius:10px;"
        f"padding:0.9rem 1.1rem;margin:0.8rem 0'>"
        f"<strong style='color:{vcol}'>{verdict.replace('_',' ').title()}</strong><br>"
        f"{review['key_message']}</div>",
        unsafe_allow_html=True)

# Section scores
section_label("📋 Section-by-Section Scores")
RATING_COLORS = {"strong":D["success"],"needs_work":D["warning"],"weak":D["danger"],"missing":"#444"}
RATING_ICONS  = {"strong":"✅","needs_work":"🟡","weak":"🔴","missing":"⚫"}

for ss in review.get("section_scores",[]):
    rating  = ss.get("rating","needs_work")
    score   = ss.get("score",0)
    rc      = RATING_COLORS.get(rating, D["muted"])
    ri      = RATING_ICONS.get(rating,"○")
    bg2=D["bg2"]
    st.markdown(
        f"<div style='background:{bg2};border:1px solid {D["border"]};"
        f"border-left:4px solid {rc};border-radius:8px;"
        f"padding:0.6rem 0.9rem;margin-bottom:0.4rem'>"
        f"<div style='display:flex;justify-content:space-between;flex-wrap:wrap'>"
        f"<span style='color:{D["text"]};font-weight:600'>{ri} {ss.get('title','')}</span>"
        f"<span style='color:{rc};font-weight:700'>{score}/100</span></div>"
        f"<span style='color:{D["muted"]};font-size:0.82rem'>{ss.get('note','')}</span>"
        + (f"<br><span style='color:{D["success"]};font-size:0.78rem'>💡 {ss.get('quick_fix','')}</span>"
           if ss.get("quick_fix") else "")
        + "</div>", unsafe_allow_html=True)

# Critical gaps
if review.get("critical_gaps"):
    section_label("🔴 Critical Gaps")
    for gap in review["critical_gaps"]:
        danger=D["danger"]; bg2=D["bg2"]
        st.markdown(
            f"<div style='background:{bg2};border-left:4px solid {danger};"
            f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.4rem'>"
            f"<strong style='color:{danger}'>{gap.get('gap','')}</strong><br>"
            f"<span style='color:{D["muted"]};font-size:0.82rem'>Impact: {gap.get('impact','')}</span><br>"
            f"<span style='color:{D["success"]};font-size:0.82rem'>Fix: {gap.get('fix','')}</span>"
            f"</div>", unsafe_allow_html=True)

# Quick wins
if review.get("quick_wins"):
    section_label("⚡ Quick Wins")
    for qw in review["quick_wins"]:
        suc=D["success"]; bg2=D["bg2"]
        st.markdown(
            f"<div style='background:{bg2};border-left:4px solid {suc};"
            f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.4rem'>"
            f"<strong style='color:{suc}'>{qw.get('action','')}</strong><br>"
            f"<span style='color:{D["muted"]};font-size:0.82rem'>Expected gain: {qw.get('expected_gain','')}</span>"
            f"</div>", unsafe_allow_html=True)

st.markdown("<br>")
st.success("✅ Intelligence cycle complete! Your annotated architecture is ready. "
           "Download it from Round 2b and start writing.")
if st.button("← View Architecture", type="primary"):
    st.switch_page("pages/round2b_architecture.py")
